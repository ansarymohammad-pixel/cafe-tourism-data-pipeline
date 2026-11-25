"""CAFÉ - 51 : agrégation des nuitées marchandes 2022-2025.

Entrées : nuites_communales_estimees_{year}.csv (script 20)
          nuites_{year}.csv (script 13, vérification indépendante)
Sortie : tourisme_marchand_com_dep_reg_{year}.csv et contrôles.

Hôtels et autres : année complète ; camping : HAUTE SAISON seulement.
Les agrégations sont des estimations issues du script 20, pas des mesures
communales observées. Les valeurs manquantes ne sont jamais remplacées par 0.
"""
from pathlib import Path
import argparse
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)

REGIONS = {
    "11": "75 77 78 91 92 93 94 95",
    "24": "18 28 36 37 41 45",
    "27": "21 25 39 58 70 71 89 90",
    "28": "14 27 50 61 76",
    "32": "02 59 60 62 80",
    "44": "08 10 51 52 54 55 57 67 68 88",
    "52": "44 49 53 72 85",
    "53": "22 29 35 56",
    "75": "16 17 19 23 24 33 40 47 64 79 86 87",
    "76": "09 11 12 30 31 32 34 46 48 65 66 81 82",
    "84": "01 03 07 15 26 38 42 43 63 69 73 74",
    "93": "04 05 06 13 83 84",
    "94": "2A 2B",
}
DEP_TO_REG = {d: r for r, deps in REGIONS.items() for d in deps.split()}
assert len(DEP_TO_REG) == 96

CATEGORIES = {
    "hotels": ("nuites_hotels_estimees", "Hotels", "DEP"),
    "campings": ("nuites_campings_estimees", "Campings", "DEP"),
    "autres": ("nuites_autres_estimees", "Autres", "REG"),
}
MEASURES = [v[0] for v in CATEGORIES.values()]


def lire(path, required):
    if not path.is_file():
        raise FileNotFoundError(f"Source absente : {path}")
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", low_memory=False)
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} : colonnes manquantes {sorted(missing)}")
    return df


def convertir(s):
    return pd.to_numeric(
        s.astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    )


def code_geo(series, niveau):
    # Codes INSEE comme 2026-DEP-75 / 2026-REG-84 ; géographie source
    # pas nécessairement identique à l'année des nuitées.
    return series.astype("string").str.extract(
        rf"(?:^|-)({niveau})-([0-9]{{2}}|2A|2B)$", expand=True
    )[1]


def charger_communes(year):
    path = PROCESSED / str(year) / f"nuites_communales_estimees_{year}.csv"
    required = ["annee_nuitees", "code_commune", "code_departement",
                "code_region", *MEASURES,
                "statut_hotels", "statut_campings", "statut_autres"]
    df = lire(path, required)
    if df.empty or not df["annee_nuitees"].eq(str(year)).all():
        raise ValueError(f"{year} : millésime incorrect ou fichier vide")
    for field in ["code_commune", "code_departement", "code_region"]:
        df[field] = df[field].str.strip().str.upper()
    if not df["code_commune"].str.fullmatch(r"(?:[0-9]{5}|2[AB][0-9]{3})", na=False).all():
        raise ValueError(f"{year} : codes de communes invalides")
    if df["code_commune"].duplicated().any():
        raise ValueError(f"{year} : communes en double")
    if not df["code_departement"].eq(df["code_commune"].str[:2]).all():
        raise ValueError(f"{year} : incohérence commune-département")
    mapped_reg = df["code_departement"].map(DEP_TO_REG)
    if mapped_reg.isna().any() or not mapped_reg.eq(df["code_region"]).all():
        raise ValueError(f"{year} : code région incorrect")
    for col in MEASURES:
        df[col] = convertir(df[col])
        if df[col].lt(0).any():
            raise ValueError(f"{year} : nuitées négatives : {col}")
    for category, (value_col, _, _) in CATEGORIES.items():
        status_col = f"statut_{category}"
        estimated = df[status_col].eq("estimé")
        if not estimated.eq(df[value_col].notna()).all():
            raise ValueError(
                f"{year} : discordance entre statut et nuitées pour {category}"
            )
    return df


def charger_observations(year):
    path = PROCESSED / str(year) / f"nuites_{year}.csv"
    df = lire(path, ["GEO", "Hotels", "Campings", "Autres"])
    if "annee" in df and not df["annee"].eq(str(year)).all():
        raise ValueError(f"{path.name} : année incohérente")
    df["DEP"] = code_geo(df["GEO"], "DEP")
    df["REG"] = code_geo(df["GEO"], "REG")
    for _, (col, _, _) in CATEGORIES.items():
        pass
    for col in ("Hotels", "Campings", "Autres"):
        df[col] = convertir(df[col])
    return df


def consolider(df, year, level, geo_col):
    if level == "COM":
        result = df[["code_commune", "code_departement", "code_region", *MEASURES]].copy()
        result = result.rename(columns={"code_commune": "geocode"})
        result["nb_communes"] = 1
        for cat, (value, _, _) in CATEGORIES.items():
            result[f"nb_communes_renseignees_{cat}"] = result[value].notna().astype(int)
            result[f"couverture_complete_{cat}"] = result[value].notna()
    else:
        records = []
        for code, group in df.groupby(geo_col, sort=True):
            item = {
                "geocode": code,
                "code_departement": code if level == "DEP" else pd.NA,
                "code_region": DEP_TO_REG[code] if level == "DEP" else code,
                "nb_communes": len(group),
            }
            for cat, (value, _, _) in CATEGORIES.items():
                present = int(group[value].notna().sum())
                complete = present == len(group)
                item[f"nb_communes_renseignees_{cat}"] = present
                item[f"couverture_complete_{cat}"] = complete
                item[value] = group[value].sum() if complete else np.nan
            records.append(item)
        result = pd.DataFrame.from_records(records)
    result.insert(0, "annee", year)
    result.insert(1, "admin_level", level)
    # Jamais de total annuel homogène si les campings ne couvrent que la haute saison.
    result["nuites_total_mixte_estime"] = result[MEASURES].sum(axis=1, min_count=3)
    result["periode_total_mixte"] = "campings haute saison; hôtels et autres année complète"
    result["type_donnee"] = "ESTIMATION_ISSUE_SCRIPT_20"
    return result


def verifier(df, observations, year):
    # Comparer uniquement les totaux de référence dont les territoires sont
    # entièrement estimés, sans transformer une lacune en zéro.
    controle = []
    for level, field in (("DEP", "DEP"), ("REG", "REG")):
        territory = df[df["admin_level"].eq(level)].copy()
        for category, (estimated_col, observed_col, source_level) in CATEGORIES.items():
            if level != source_level:
                continue
            ref = observations.loc[observations[field].notna(), [field, observed_col]].copy()
            if ref[field].duplicated().any():
                raise ValueError(f"{year} : référence observée dupliquée pour {category}")
            merged = territory.merge(ref, left_on="geocode", right_on=field,
                                     how="left", validate="one_to_one")
            for _, row in merged.iterrows():
                observed = row[observed_col]
                est = row[estimated_col]
                complete = bool(row[f"couverture_complete_{category}"])
                if complete and pd.notna(observed):
                    if pd.isna(est) or not np.isclose(est, observed, atol=0.01, rtol=1e-10):
                        raise ValueError(
                            f"{year} : conservation non respectée, "
                            f"{category} {row['geocode']}: {est} != {observed}"
                        )
                if pd.isna(observed) and pd.notna(est):
                    raise ValueError(
                        f"{year} : estimation sans total INSEE pour "
                        f"{category} {row['geocode']}"
                    )
                controle.append({
                    "annee": year, "niveau": level,
                    "categorie": category, "geocode": row["geocode"],
                    "nuites_source_insee": observed,
                    "nuites_estimees": est,
                    "couverture_complete": complete,
                    "ecart": est - observed if pd.notna(est) and pd.notna(observed) else np.nan,
                })
    return pd.DataFrame(controle)


def run_year(year):
    print(f"\n=== SCRIPT 51 - TOURISME MARCHAND {year} ===")
    communes = charger_communes(year)
    observations = charger_observations(year)
    com = consolider(communes, year, "COM", "code_commune")
    dep = consolider(communes, year, "DEP", "code_departement")
    reg = consolider(communes, year, "REG", "code_region")
    if len(dep) != 96 or len(reg) != 13:
        raise ValueError(f"{year} : couverture géographique inattendue ({len(dep)} DEP, {len(reg)} REG)")
    result = pd.concat([com, dep, reg], ignore_index=True)
    check = verifier(result, observations, year)
    folder = PROCESSED / str(year)
    output = folder / f"tourisme_marchand_com_dep_reg_{year}.csv"
    controls = folder / f"controle_tourisme_marchand_{year}.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")
    check.to_csv(controls, index=False, encoding="utf-8-sig")
    print(f"  Territoires : {len(com)} COM, {len(dep)} DEP, {len(reg)} REG")
    for cat, (col, _, _) in CATEGORIES.items():
        for lvl, part in (("COM", com), ("DEP", dep), ("REG", reg)):
            print(f"  {cat:9s} {lvl}: {part[col].notna().sum():5d} / {len(part)} territoires avec total complet")
    print("  Export :", output)
    print("  Contrôle :", controls)


def main():
    parser = argparse.ArgumentParser(description="CAFÉ 51 : tourisme marchand 2022-2025")
    parser.add_argument("--year", type=int, choices=YEARS)
    args = parser.parse_args()
    years = [args.year] if args.year is not None else YEARS
    for year in years:
        run_year(year)
    print("\n=== SCRIPT 51 TERMINÉ ===")
    print("ATTENTION : campings = haute saison uniquement; valeurs manquantes conservées.")


if __name__ == "__main__":
    main()
