"""CAFÉ — estimation provisoire des nuitées non marchandes 2022, COM/DEP/REG.

Clés de répartition : population municipale et résidences secondaires 2023.
Les communes sans correspondance sont exclues et tracées ; les totaux nationaux
2022 sont redistribués sur le périmètre apparié (pas des observations locales).
Les mois restent vides faute de ventilation justifiée.
"""
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "processed" / "tourisme"
OUT = BASE / "livraison_cafe_2022"
POP = ROOT / "population_brute.csv"
RES = BASE / "residences_secondaires_2023_communes.csv"
CAP = BASE / "capacites_metro_2022.csv"
FAMILY_TOTAL = 398_500_000
SECONDARY_TOTAL = 117_300_000
MONTHS = ("january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december")


def col(columns, choices):
    lookup = {str(c).strip().lower(): c for c in columns}
    return next((lookup[c.lower()] for c in choices if c.lower() in lookup), None)


def com_code(x):
    if pd.isna(x):
        return None
    match = re.fullmatch(r"(?:\d{4}-COM-)?(\d{2}[0-9AB]\d{2})", str(x).strip().upper())
    return match.group(1) if match else None


def dep_code(x):
    if pd.isna(x):
        return None
    s = re.sub(r"^\d{4}-DEP-", "", str(x).strip().upper())
    return s if re.fullmatch(r"(?:\d{2,3}|2A|2B)", s) else None


def reg_code(x):
    if pd.isna(x):
        return None
    s = re.sub(r"^\d{4}-REG-", "", str(x).strip().upper())
    return s.zfill(2) if re.fullmatch(r"\d{1,2}", s) else None


# Correspondance département -> région (France métropolitaine, régions depuis 2016).
REGION_DEPARTEMENTS = {
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
DEP_TO_REG = {
    dep: region
    for region, departments in REGION_DEPARTEMENTS.items()
    for dep in departments.split()
}


def dept_from_commune(code):
    if pd.isna(code):
        return None
    if code.startswith(("2A", "2B")):
        return code[:2]
    return code[:2]


def load_reference():
    caps = pd.read_csv(CAP, dtype=str, low_memory=False)
    gc = col(caps.columns, ("geocode", "GEO", "CODGEO", "code_commune"))
    if gc is None:
        raise ValueError(f"Colonne commune absente : {list(caps.columns)}")
    # Le fichier capacités peut avoir des codes DEP/REG vides ou non normalisés.
    # On reconstruit la hiérarchie à partir du code communal INSEE.
    ref = pd.DataFrame({"geocode": caps[gc].map(com_code)})
    ref = ref.dropna(subset=["geocode"]).drop_duplicates().copy()
    ref["code_departement"] = ref["geocode"].map(dept_from_commune)
    ref["code_region"] = ref["code_departement"].map(DEP_TO_REG)
    missing_geo = ref[["code_departement", "code_region"]].isna().any(axis=1)
    ref.loc[missing_geo].to_csv(
        OUT / "DIAGNOSTIC_CODES_DEP_REG.csv", index=False, encoding="utf-8-sig"
    )
    print(f"Communes sans DEP/REG : {missing_geo.sum()}")
    return ref.loc[~missing_geo].copy(), ref.loc[missing_geo].copy()


def load_population():
    columns = pd.read_csv(POP, nrows=0).columns
    geo = col(columns, ("GEO", "CODGEO"))
    year = col(columns, ("TIME_PERIOD",))
    measure = col(columns, ("POPREF_MEASURE",))
    value = col(columns, ("OBS_VALUE_NIVEAU", "OBS_VALUE"))
    if not all((geo, year, measure, value)):
        raise ValueError(f"Colonnes population inattendues : {list(columns)}")
    parts = []
    for chunk in pd.read_csv(POP, usecols=[geo, year, measure, value], dtype=str, chunksize=100_000):
        mask = (chunk[year].eq("2023") & chunk[measure].eq("PMUN") &
                chunk[geo].str.contains("-COM-", regex=False, na=False))
        if mask.any():
            part = chunk.loc[mask, [geo, value]].copy()
            part.columns = ["geocode", "population_2023"]
            part["geocode"] = part.geocode.map(com_code)
            parts.append(part.dropna(subset=["geocode"]))
    if not parts:
        raise ValueError("Population PMUN 2023 absente.")
    pop = pd.concat(parts, ignore_index=True)
    pop["population_2023"] = pd.to_numeric(pop.population_2023, errors="coerce")
    if pop.geocode.duplicated().any():
        raise ValueError("Doublons PMUN 2023.")
    return pop


def load_residences():
    raw = pd.read_csv(RES, dtype=str)
    geo = col(raw.columns, ("GEO", "geocode", "CODGEO"))
    val = col(raw.columns, ("OBS_VALUE", "OBS_VALUE_NIVEAU", "residences_2023"))
    if not all((geo, val)):
        raise ValueError(f"Colonnes résidences inattendues : {list(raw.columns)}")
    res = pd.DataFrame({
        "geocode": raw[geo].map(com_code),
        "residences_2023": pd.to_numeric(raw[val], errors="coerce"),
    }).dropna(subset=["geocode"])
    if res.geocode.duplicated().any():
        raise ValueError("Doublons logements 2023.")
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for path in (CAP, POP, RES):
        if not path.is_file():
            raise FileNotFoundError(path)

    print("1/4 — Référentiel et données 2023")
    ref, excluded_geo = load_reference()
    df = ref.merge(load_population(), on="geocode", how="left", validate="one_to_one")
    df = df.merge(load_residences(), on="geocode", how="left", validate="one_to_one")
    missing = df[["population_2023", "residences_2023"]].isna().any(axis=1)
    excluded = df.loc[missing].copy()
    excluded["motif"] = "population_2023_ou_residences_2023_manquantes"
    excluded_geo = excluded_geo.copy()
    excluded_geo["motif"] = "departement_ou_region_manquant"
    pd.concat([excluded_geo, excluded], ignore_index=True).to_csv(
        OUT / "NON_MARCHAND_COMMUNES_EXCLUES.csv", index=False, encoding="utf-8-sig"
    )
    df = df.loc[~missing].copy()
    if df.empty or (df[["population_2023", "residences_2023"]] < 0).any().any():
        raise ValueError("Aucune commune valide ou valeurs négatives.")
    total_pop = df.population_2023.sum()
    total_res = df.residences_2023.sum()
    if total_pop <= 0 or total_res <= 0:
        raise ValueError("Clés de répartition nulles.")

    print("2/4 — Allocation annuelle")
    df["family_nights_year"] = FAMILY_TOTAL * df.population_2023 / total_pop
    df["secondary_residence_year"] = SECONDARY_TOTAL * df.residences_2023 / total_res
    metrics = ["family_nights_year", "secondary_residence_year"]
    com = df[["geocode"] + metrics].copy()
    com.insert(1, "admin_level", "COM")
    dep = df.groupby("code_departement", as_index=False)[metrics].sum().rename(
        columns={"code_departement": "geocode"})
    dep.insert(1, "admin_level", "DEP")
    reg = df.groupby("code_region", as_index=False)[metrics].sum().rename(
        columns={"code_region": "geocode"})
    reg.insert(1, "admin_level", "REG")
    result = pd.concat([com, dep, reg], ignore_index=True)

    print("3/4 — Export")
    for prefix in ("family_nights", "secondary_residence"):
        for month in MONTHS:
            result[f"{prefix}_{month}"] = pd.NA
    result.to_csv(OUT / "TOURISME_NON_MARCHAND_2022_COM_DEP_REG_PROVISOIRE.csv",
                  index=False, encoding="utf-8-sig")
    com.to_csv(OUT / "TOURISME_NON_MARCHAND_2022_COMMUNES_PROVISOIRE.csv",
               index=False, encoding="utf-8-sig")

    print("4/4 — Synthèse")
    print(result.groupby("admin_level")[metrics].agg(["count", "sum"]).to_string())
    for level in ("COM", "DEP", "REG"):
        subset = result[result.admin_level.eq(level)]
        if abs(subset.family_nights_year.sum() - FAMILY_TOTAL) > 0.01:
            raise ValueError(f"Total famille non conservé : {level}")
        if abs(subset.secondary_residence_year.sum() - SECONDARY_TOTAL) > 0.01:
            raise ValueError(f"Total résidences non conservé : {level}")
    print(f"Communes référentiel : {len(ref) + len(excluded_geo)} | "
          f"appariées : {len(df)} | exclues : {len(excluded) + len(excluded_geo)}")
    print("Fichier :", OUT / "TOURISME_NON_MARCHAND_2022_COM_DEP_REG_PROVISOIRE.csv")
    print("Estimations 2022, clés 2023, couverture provisoire, mois non renseignés.")


if __name__ == "__main__":
    main()
