"""CAFÉ — 50 : agrégation du tourisme non marchand 2022-2025.

Entrée principale : script 49 / cles_repartition_non_marchand_{annee}.csv.
Sortie : poids COM/DEP/REG. Agrégation des nuitées seulement lorsque
le script 49 a déjà produit un fichier d'estimations validé.
AUCUN total TRAVEL_DEST=_T n'est converti en nuitées métropolitaines.
"""
from pathlib import Path
import argparse
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)

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
    for region, depts in REGION_DEPARTEMENTS.items()
    for dep in depts.split()
}
WEIGHTS = ["poids_famille_amis", "poids_residences_secondaires"]
NIGHTS = [
    "nuites_famille_amis_estimees",
    "nuites_residences_secondaires_estimees",
]
META = [
    "annee_reference_population", "statut_population",
    "annee_reference_logements", "statut_logements",
]


def number(s):
    return pd.to_numeric(
        s.astype("string").str.replace(",", ".", regex=False),
        errors="coerce"
    )


def read_communes(year):
    path = PROCESSED / str(year) / f"cles_repartition_non_marchand_{year}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Exécuter le script 49 : {path}")
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", low_memory=False)
    required = {"annee", "code_commune", "code_departement", *WEIGHTS,
                "population_municipale", "residences_secondaires_occasionnelles"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"49 : colonnes manquantes {sorted(missing)}")
    if df.empty or not df["annee"].eq(str(year)).all():
        raise ValueError(f"49 : année erronée ou fichier vide pour {year}")

    df["code_commune"] = df["code_commune"].str.strip().str.upper()
    df["code_departement"] = df["code_departement"].str.strip().str.upper()
    if not df["code_commune"].str.fullmatch(r"(?:\d{5}|2[AB]\d{3})", na=False).all():
        raise ValueError("49 : codes communaux invalides")
    if df["code_commune"].duplicated().any():
        raise ValueError("49 : codes communaux en double")

    # Recalcul de la géographie depuis les codes de commune.
    derived_dep = df["code_commune"].str[:2]
    if not derived_dep.eq(df["code_departement"]).all():
        raise ValueError("49 : incohérence code commune / département")
    df["code_region"] = df["code_departement"].map(DEP_TO_REG)
    if df["code_region"].isna().any():
        raise ValueError("50 : département sans région")

    for col in WEIGHTS + [
        "population_municipale", "residences_secondaires_occasionnelles"
    ]:
        df[col] = number(df[col])
        if df[col].isna().any() or df[col].lt(0).any():
            raise ValueError(f"49 : données manquantes ou négatives : {col}")

    for weight in WEIGHTS:
        err = abs(float(df[weight].sum()) - 1.0)
        if err > 1e-7:
            raise ValueError(f"50 : somme des poids {weight} = {df[weight].sum()}, attendu 1")
    return df


def provenance(df):
    info = {}
    for col in META:
        if col in df.columns:
            unique = df[col].dropna().unique()
            if len(unique) > 1:
                raise ValueError(f"Provenance incohérente pour {col} : {unique}")
            info[col] = unique[0] if len(unique) else pd.NA
        else:
            info[col] = pd.NA
    return info


def aggreger(df, year, metrics):
    frames = []
    for level, code in (
        ("COM", "code_commune"),
        ("DEP", "code_departement"),
        ("REG", "code_region"),
    ):
        if level == "COM":
            part = df[[code] + metrics].copy().rename(columns={code: "geocode"})
        else:
            part = (
                df.groupby(code, as_index=False, dropna=False)[metrics]
                .sum(min_count=1)
                .rename(columns={code: "geocode"})
            )
        part.insert(0, "annee", year)
        part.insert(1, "admin_level", level)
        frames.append(part)
    result = pd.concat(frames, ignore_index=True)
    for metric in metrics:
        total_com = result.loc[result.admin_level.eq("COM"), metric].sum()
        for level in ("DEP", "REG"):
            total = result.loc[result.admin_level.eq(level), metric].sum()
            if abs(float(total) - float(total_com)) > max(0.01, 1e-9 * abs(float(total_com))):
                raise ValueError(f"Agrégation non conservée : {metric}, {level}")
    return result


def traiter(year):
    folder = PROCESSED / str(year)
    df = read_communes(year)
    info = provenance(df)

    # 1. Agréger les CLÉS, même sans nuitées validées.
    # Ce ne sont PAS des nuitées.
    key_metrics = [
        "population_municipale", "residences_secondaires_occasionnelles",
        *WEIGHTS,
    ]
    keys = aggreger(df, year, key_metrics)
    for col, value in info.items():
        keys[col] = value
    keys["type_donnee"] = "CLES_REPARTITION_NON_MARCHAND"
    path_keys = folder / f"cles_non_marchandes_com_dep_reg_{year}.csv"
    keys.to_csv(path_keys, index=False, encoding="utf-8-sig")

    counts = keys.groupby("admin_level").size().to_dict()
    print(f"  [OK] Clés : {counts} | {path_keys}")

    # 2. Nuitées : uniquement si le 49 a créé un fichier réel
    # issu de totaux validés pour des DESTINATIONS métropolitaines.
    path_nights = folder / f"nuites_non_marchandes_communales_estimees_{year}.csv"
    path_result = folder / f"nuites_non_marchandes_com_dep_reg_{year}.csv"
    if not path_nights.is_file():
        # Supprimer un ancien export éventuel, pour ne pas le prendre pour
        # une livraison de cette exécution.
        print("  [ATTENTE] Aucune estimation validée du script 49 :")
        print("            export de clés uniquement, sans inventer de nuitées.")
        return "CLES_SEULEMENT"

    nights = pd.read_csv(path_nights, dtype=str, encoding="utf-8-sig")
    required = {"code_commune", "annee_nuitees", "type_donnee",
                "source_totaux", *NIGHTS}
    missing = required - set(nights.columns)
    if missing:
        raise ValueError(f"Estimations 49 : colonnes manquantes {sorted(missing)}")
    if (not nights["annee_nuitees"].eq(str(year)).all()
        or not nights["type_donnee"].eq("ESTIMATION_COMMUNALE").all()
        or not nights["source_totaux"].eq("nuitees_non_marchandes_metropole_validees").all()):
        raise ValueError("Estimations 49 : année, type ou source non validée")
    if nights["code_commune"].duplicated().any():
        raise ValueError("Estimations 49 : communes doublonnées")
    if set(nights["code_commune"]) != set(df["code_commune"]):
        raise ValueError("Estimations 49 : périmètre communal différent des clés")
    for metric in NIGHTS:
        nights[metric] = number(nights[metric])
        if nights[metric].isna().any() or nights[metric].lt(0).any():
            raise ValueError(f"Nuitées invalides : {metric}")

    joint = df[["code_commune", "code_departement", "code_region"]].merge(
        nights[["code_commune"] + NIGHTS], on="code_commune",
        how="left", validate="one_to_one"
    )
    result = aggreger(joint, year, NIGHTS)
    for col, value in info.items():
        result[col] = value
    result["type_donnee"] = "ESTIMATION_NUITEES_NON_MARCHANDES"
    result["source_totaux"] = "nuitees_non_marchandes_metropole_validees"
    result.to_csv(path_result, index=False, encoding="utf-8-sig")
    print(f"  [OK] Nuitées COM/DEP/REG : {path_result}")
    return "NUITEES_AGREGEES"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, choices=YEARS)
    args = parser.parse_args()
    years = [args.year] if args.year else YEARS
    status = {}
    for year in years:
        print(f"\n=== SCRIPT 50 — {year} ===")
        try:
            status[year] = traiter(year)
        except (ValueError, FileNotFoundError) as exc:
            status[year] = "ERREUR"
            print("  [ERREUR]", exc)
    print("\n=== BILAN SCRIPT 50 ===")
    for year, value in status.items():
        print(f"{year} : {value}")
    if "ERREUR" in status.values():
        raise SystemExit("Des années nécessitent une correction avant livraison.")


if __name__ == "__main__":
    main()
