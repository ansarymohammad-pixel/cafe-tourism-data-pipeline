"""CAFÉ - Script 47, logements communaux 2022-2025.

Sources et règle de substitution :
- RP2022 : base INSEE 2022, variable P22_RSECOCC (zip téléchargé si besoin).
- RP2023 : export Melodi DS_RP_LOGEMENT_PRINC, OCS=DW_SEC_DW_OCC.
- RP2022 : vrai RP si disponible, sinon proxy communal RP2023.
- RP2024/2025 : vrai RP si disponible, sinon proxy communal RP2023.
- L'année du proxy est indiquée explicitement, jamais présentée comme observation.

ATTENTION : indicateur = résidences secondaires + logements occasionnels.
"""
from __future__ import annotations
import argparse
import csv
import io
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "tourisme"
OUT = ROOT / "data" / "processed" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)
METRO = {f"{i:02d}" for i in range(1, 96) if i != 20} | {"2A", "2B"}
URL_2022 = "https://www.insee.fr/fr/statistiques/fichier/8581474/base-cc-logement-2022_csv.zip"
ZIP_2022 = RAW / "base-cc-logement-2022_csv.zip"
TOTAL_DIMS = ("TDW", "TO", "CARPAR", "NOR", "TSH", "CARS", "UFS", "L_STA")


def parse():
    ap = argparse.ArgumentParser(description="CAFÉ | logements communaux observés 2022-2025")
    ap.add_argument("--year", type=int, choices=YEARS)
    ap.add_argument("--no-download", action="store_true", help="N'utilise que les fichiers déjà présents")
    ap.add_argument("--strict", action="store_true", help="Échec si une année est absente")
    ap.add_argument("--sans-proxy", action="store_true", help="Ne pas utiliser RP2023 comme proxy 2022, 2024, 2025")
    return ap.parse_args()


def code_commune(value):
    if pd.isna(value):
        return None
    s = str(value).strip().upper()
    if "-COM-" in s:
        s = s.rsplit("-COM-", 1)[-1]
    elif s.startswith("COM-"):
        s = s[4:]
    return s if re.fullmatch(r"(?:\d{5}|2[AB]\d{3})", s) else None


def numbers(s):
    return pd.to_numeric(s.astype("string").str.strip()
                         .str.replace("\u00a0", "", regex=False)
                         .str.replace("\u202f", "", regex=False)
                         .str.replace(" ", "", regex=False)
                         .str.replace(",", ".", regex=False), errors="coerce")


def delimiter(header):
    try:
        return csv.Sniffer().sniff(header, delimiters=";,\t").delimiter
    except csv.Error:
        return ";" if header.count(";") > header.count(",") else ","


def validate(data, year, source, indicator):
    data = data[["code_commune", "residences_secondaires_occasionnelles"]].copy()
    data["code_commune"] = data["code_commune"].map(code_commune)
    data = data.dropna(subset=["code_commune"]).copy()
    data["code_departement"] = data["code_commune"].str[:2]
    data = data[data["code_departement"].isin(METRO)].copy()
    if data.empty:
        raise ValueError(f"{year}: aucune commune métropolitaine dans {source}")
    if data.code_commune.duplicated().any():
        bad = data.loc[data.code_commune.duplicated(False), "code_commune"].head(6).tolist()
        raise ValueError(f"{year}: communes dupliquées {bad}; aucune somme automatique")
    x = data["residences_secondaires_occasionnelles"]
    if x.isna().any() or (x < 0).any():
        raise ValueError(f"{year}: {int(x.isna().sum())} valeurs manquantes et {int((x < 0).sum())} négatives")
    data.insert(0, "annee_logement", year)
    data["indicateur_insee"] = "DW_SEC_DW_OCC"
    data["source_indicateur"] = indicator
    data["source_fichier"] = source
    data["statut_donnee"] = "OBSERVEE_INSEE"
    data["annee_reference_logements"] = year
    return data[["annee_logement", "annee_reference_logements", "code_commune", "code_departement",
                 "residences_secondaires_occasionnelles", "indicateur_insee",
                 "source_indicateur", "source_fichier", "statut_donnee"]].sort_values("code_commune")


def download_2022():
    if ZIP_2022.is_file():
        return
    print("[DOWNLOAD] Base communale INSEE 2022 (environ 40 Mo)")
    req = urllib.request.Request(URL_2022, headers={"User-Agent": "Mozilla/5.0"})
    part = ZIP_2022.with_suffix(".part")
    try:
        with urllib.request.urlopen(req, timeout=180) as response, part.open("wb") as f:
            shutil.copyfileobj(response, f)
        if not zipfile.is_zipfile(part):
            raise ValueError("Le téléchargement 2022 ne contient pas une archive ZIP valide")
        part.replace(ZIP_2022)
    finally:
        part.unlink(missing_ok=True)


def read_2022(allow_download):
    if not ZIP_2022.is_file():
        if not allow_download:
            raise FileNotFoundError(f"Archive INSEE 2022 absente : {ZIP_2022}")
        download_2022()
    with zipfile.ZipFile(ZIP_2022) as z:
        matches = []
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            with z.open(name) as f:
                header = f.readline().decode("utf-8-sig", errors="replace")
            sep = delimiter(header)
            columns = {s.strip().strip('"').upper() for s in header.strip().split(sep)}
            if {"CODGEO", "P22_RSECOCC"} <= columns:
                matches.append((z.getinfo(name).file_size, name, sep))
        if not matches:
            raise ValueError("ZIP INSEE 2022 sans CSV contenant CODGEO + P22_RSECOCC")
        _, name, sep = max(matches)
        print(f"  Source RP2022 : {name}")
        with z.open(name) as file:
            df = pd.read_csv(file, sep=sep, encoding="utf-8-sig", dtype=str,
                             usecols=["CODGEO", "P22_RSECOCC"])
    df["code_commune"] = df["CODGEO"]
    df["residences_secondaires_occasionnelles"] = numbers(df["P22_RSECOCC"])
    return validate(df, 2022, ZIP_2022.name + ":" + name, "P22_RSECOCC")


def find_melodi(year):
    candidates = [RAW / f"DS_RP_LOGEMENT_PRINC_{year}_data.csv",
                  RAW / f"DS_RP_LOGEMENT_PRINC_{year}.csv"]
    candidates += sorted(RAW.glob(f"*RP_LOGEMENT_PRINC*{year}*.csv"))
    candidates += [RAW / "DS_RP_LOGEMENT_PRINC_data.csv"]
    return next((p for p in dict.fromkeys(candidates) if p.is_file()), None)


def read_melodi(year):
    path = find_melodi(year)
    if path is None:
        raise FileNotFoundError(f"DS_RP_LOGEMENT_PRINC {year} absent dans {RAW}")
    with path.open(encoding="utf-8-sig") as file:
        header = file.readline()
    sep = delimiter(header)
    columns = pd.read_csv(path, sep=sep, nrows=0, encoding="utf-8-sig").columns
    names = {str(c).strip().upper(): str(c) for c in columns}
    required = {"GEO", "TIME_PERIOD", "OCS"}
    if not required <= set(names):
        raise ValueError(f"{path.name} : colonnes requises manquantes {sorted(required - set(names))}")
    val = next((c for c in ("OBS_VALUE", "OBS_VALUE_NIVEAU") if c in names), None)
    if val is None:
        raise ValueError(f"{path.name} : OBS_VALUE et OBS_VALUE_NIVEAU absents")
    use = [names[c] for c in (required | {val, "GEO_OBJECT", "UNIT_MULT", "FREQ", "MEASURE"} | set(TOTAL_DIMS)) if c in names]
    fragments = []
    for chunk in pd.read_csv(path, sep=sep, usecols=use, dtype=str,
                             encoding="utf-8-sig", chunksize=180000):
        chunk.columns = chunk.columns.str.strip().str.upper()
        mask = chunk["TIME_PERIOD"].eq(str(year)) & chunk["OCS"].eq("DW_SEC_DW_OCC")
        if "GEO_OBJECT" in chunk:
            mask &= chunk["GEO_OBJECT"].eq("COM")
        if "FREQ" in chunk:
            mask &= chunk["FREQ"].eq("A")
        if "MEASURE" in chunk:
            mask &= chunk["MEASURE"].eq("DWELLINGS")
        for dim in TOTAL_DIMS:
            if dim in chunk:
                mask &= chunk[dim].isin(("_T", "T", "L_T"))
        selected = chunk.loc[mask].copy()
        if selected.empty:
            continue
        selected["code_commune"] = selected["GEO"].map(code_commune)
        selected["residences_secondaires_occasionnelles"] = numbers(selected[val])
        if "UNIT_MULT" in selected:
            selected["residences_secondaires_occasionnelles"] *= 10 ** numbers(selected["UNIT_MULT"])
        fragments.append(selected[["code_commune", "residences_secondaires_occasionnelles"]])
    if not fragments:
        raise ValueError(f"{path.name} : aucune observation communale du RP{year} avec OCS=DW_SEC_DW_OCC")
    return validate(pd.concat(fragments, ignore_index=True), year, path.name, "OCS=DW_SEC_DW_OCC")


def fichier_annuel(year):
    return OUT / str(year) / f"residences_secondaires_occasionnelles_{year}_communes.csv"


def sauvegarder(df, year):
    path = fichier_annuel(year)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[OK] {year} : {len(df):,} communes / {df.code_departement.nunique()} départements")
    print(f"     Total logements : {df.residences_secondaires_occasionnelles.sum():,.0f}")
    print(f"     Statut : {df.statut_donnee.iloc[0]} | référence : {df.annee_reference_logements.iloc[0]}")
    print(f"     Fichier : {path}")
    return path


def obtenir_reference_2023():
    """Préférer le RP2023 effectivement chargé; sinon le CSV 2023 déjà validé."""
    try:
        return read_melodi(2023)
    except (FileNotFoundError, ValueError) as exc:
        existing = fichier_annuel(2023)
        if not existing.is_file():
            raise FileNotFoundError(
                f"RP2023 nécessaire au proxy, fichier source et sortie absents : {exc}"
            ) from exc
        df = pd.read_csv(existing, dtype={"code_commune": str,
                                         "code_departement": str}, encoding="utf-8-sig")
        if df.empty or not {"annee_logement", "code_commune",
                           "residences_secondaires_occasionnelles",
                           "indicateur_insee"}.issubset(df.columns):
            raise ValueError(f"Référence 2023 non exploitable : {existing}")
        if not df["annee_logement"].eq(2023).all():
            raise ValueError("Référence 2023 : année non conforme")
        if not df["indicateur_insee"].eq("DW_SEC_DW_OCC").all():
            raise ValueError("Référence 2023 : mauvais indicateur")
        x = df["residences_secondaires_occasionnelles"] = numbers(
            df["residences_secondaires_occasionnelles"]
        )
        if x.isna().any() or x.lt(0).any() or df.code_commune.duplicated().any():
            raise ValueError("Référence 2023 : données invalides ou communes dupliquées")
        if "source_fichier" not in df:
            df["source_fichier"] = existing.name
        if "source_indicateur" not in df:
            df["source_indicateur"] = "OCS=DW_SEC_DW_OCC"
        df["annee_reference_logements"] = 2023
        df["statut_donnee"] = "OBSERVEE_INSEE"
        return df


def proxy_2023(year, reference):
    """Copie des poids communaux RP2023; pas une mesure RP de l'année cible."""
    df = reference.copy()
    df["annee_logement"] = year  # année cible, et NON millésime réel de la source
    df["annee_reference_logements"] = 2023
    df["statut_donnee"] = "PROXY_2023"
    df["source_fichier"] = "RP2023:" + reference["source_fichier"].astype(str)
    return df


def main():
    options = parse()
    RAW.mkdir(parents=True, exist_ok=True)
    years = [options.year] if options.year else YEARS
    states = []
    reference = None
    for year in years:
        print(f"\n=== LOGEMENTS {year} ===")
        try:
            if year == 2022:
                # Priorité à une véritable mesure RP2022. Si elle est absente
                # ou inexploitable, RP2023 sert seulement de proxy spatial.
                try:
                    df = read_2022(not options.no_download)
                except (FileNotFoundError, ValueError, OSError, zipfile.BadZipFile) as exc:
                    if options.sans_proxy:
                        raise
                    print(f"  [INFO] RP2022 non exploitable : {exc}")
                    print("  [PROXY] Utilisation des logements communaux RP2023 pour 2022")
                    if reference is None:
                        reference = obtenir_reference_2023()
                    df = proxy_2023(year, reference)
            elif year == 2023:
                df = obtenir_reference_2023()
            else:
                # Une donnée réellement publiée prime toujours sur le proxy.
                try:
                    df = read_melodi(year)
                except (FileNotFoundError, ValueError) as exc:
                    if options.sans_proxy:
                        raise
                    print(f"  [INFO] RP{year} non exploitable : {exc}")
                    print("  [PROXY] Utilisation des logements communaux RP2023")
                    if reference is None:
                        reference = obtenir_reference_2023()
                    df = proxy_2023(year, reference)
            if year == 2023:
                reference = df
            output = sauvegarder(df, year)
            states.append({
                "annee": year, "statut": df.statut_donnee.iloc[0],
                "annee_reference_logements": int(df.annee_reference_logements.iloc[0]),
                "nb_communes": len(df), "source": str(df.source_fichier.iloc[0]),
                "fichier": str(output),
            })
        except (FileNotFoundError, ValueError, OSError, zipfile.BadZipFile) as exc:
            print(f"[INDISPONIBLE] {year} : {exc}")
            states.append({"annee": year, "statut": "NON_DISPONIBLE",
                           "annee_reference_logements": pd.NA, "nb_communes": 0,
                           "source": "", "fichier": ""})
            if options.strict:
                raise
    OUT.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(states)
    status = OUT / "bilan_logements_sources_2022_2025.csv"
    summary.to_csv(status, index=False, encoding="utf-8-sig")
    print("\n=== BILAN LOGEMENTS CAFÉ ===")
    print(summary[["annee", "statut", "annee_reference_logements", "nb_communes"]].to_string(index=False))
    print("Bilan :", status)
    print("Attention : RP2023 sert de proxy géographique pour 2022, 2024 ou 2025, jamais de mesure réelle pour ces années.")
    print("Attention : harmoniser les codes des communes fusionnées avec les autres jeux CAFÉ.")


if __name__ == "__main__":
    main()
