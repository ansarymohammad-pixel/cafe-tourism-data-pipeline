"""CAFÉ — 52 : scénario EXPLORATOIRE non marchand (2022–2025).

Entrées : nuites_non_marchandes_{annee}.csv (script 46)
          cles_non_marchandes_com_dep_reg_{annee}.csv (script 50).
Sorties : data/processed/tourisme/{annee}/
          scenario_non_marchand_com_dep_reg_{annee}.csv
          scenario_non_marchand_hypotheses_{annee}.txt

ATTENTION : TRAVEL_DEST=_T signifie toutes destinations, et NON la France
métropolitaine. L'allocation aux communes françaises est donc une
SIMULATION et non une estimation géographique validée.
La mensualisation uniforme (1/12) est une HYPOTHÈSE EXPLORATOIRE, sans
fondement saisonnier dans le jeu de données ici utilisé.

Conservation : somme des communes = département/région = total source,
pour chacune des deux catégories et chacun des 12 mois.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)
MONTHS = ("january", "february", "march", "april", "may", "june",
          "july", "august", "september", "october", "november", "december")
CATEGORIES = {
    "famille_amis": ("family_nights", "poids_famille_amis"),
    "residences_secondaires": ("secondary_residence", "poids_residences_secondaires"),
}
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
DEP_REG = {dep: reg for reg, deps in REGIONS.items() for dep in deps.split()}
OUTPUT_COLS = (
    ["geocode", "admin_level"]
    + [col for prefix, _ in CATEGORIES.values()
       for col in ([prefix + "_year"] + [prefix + "_" + m for m in MONTHS])]
)
META = {
    "scenario": "EXPLORATOIRE_NON_VALIDE",
    "hypothese_geographique": "TRAVEL_DEST=_T toutes destinations réparties sur communes métropolitaines",
    "hypothese_mensuelle": "UNIFORME_1_SUR_12_NON_OBSERVEE",
}


def path(year, filename):
    return PROCESSED / str(year) / filename.format(year=year)


def num_col(df, name):
    x = pd.to_numeric(df[name].astype(str).str.replace(",", ".", regex=False),
                      errors="coerce")
    if x.isna().any() or (x < 0).any():
        raise ValueError(f"Valeurs manquantes, non numériques ou négatives : {name}")
    return x.astype(float)


def code(s, level):
    s = str(s).strip().upper()
    return s.zfill(5 if level == "COM" else 2) if s.isdigit() else s


def ensure_close(actual, expected, label):
    if not np.isclose(actual, expected, rtol=0, atol=0.01):
        raise ValueError(f"Conservation échouée {label} : {actual} != {expected}")


def effectuer(year):
    print(f"\n=== SCÉNARIO NON MARCHAND {year} ===")
    keys_file = path(year, "cles_non_marchandes_com_dep_reg_{year}.csv")
    totals_file = path(year, "nuites_non_marchandes_{year}.csv")
    if not keys_file.is_file() or not totals_file.is_file():
        raise FileNotFoundError(f"Fichier du script 46/50 absent : {keys_file} / {totals_file}")
    keys = pd.read_csv(keys_file, dtype=str, encoding="utf-8-sig")
    totals = pd.read_csv(totals_file, dtype=str, encoding="utf-8-sig")
    required = {"annee", "admin_level", "geocode",
                "poids_famille_amis", "poids_residences_secondaires"}
    if not required.issubset(keys):
        raise ValueError(f"Clés 50 : colonnes absentes : {sorted(required - set(keys))}")
    if not {"annee", "categorie", "nuites", "TRAVEL_DEST"}.issubset(totals):
        raise ValueError("Script 46 : colonnes requises absentes")
    if not keys["annee"].eq(str(year)).all() or not totals["annee"].eq(str(year)).all():
        raise ValueError("Années incohérentes")
    if not totals["TRAVEL_DEST"].eq("_T").all():
        raise ValueError("La source a changé de périmètre : revoir les hypothèses")
    if len(totals) != 2 or set(totals["categorie"]) != set(CATEGORIES):
        raise ValueError("Il faut exactement deux catégories non marchandes")
    if keys.duplicated(["admin_level", "geocode"]).any():
        raise ValueError("Codes géographiques doublonnés dans les clés")

    # NE PAS utiliser les clés agrégées en tant qu'observations supplémentaires :
    # on commence exclusivement par les communes pour éviter le triple comptage.
    com = keys.loc[keys["admin_level"].eq("COM")].copy()
    if com.empty:
        raise ValueError("Aucune commune dans les clés 50")
    com["geocode"] = com["geocode"].map(lambda x: code(x, "COM"))
    com["code_departement"] = com["geocode"].str[:2]
    com["code_region"] = com["code_departement"].map(DEP_REG)
    if com["code_region"].isna().any():
        raise ValueError("Commune sans région métropolitaine")
    com["admin_level"] = "COM"
    for cat, (prefix, weight_name) in CATEGORIES.items():
        poids = num_col(com, weight_name).to_numpy()
        s = poids.sum()
        ensure_close(s, 1.0, f"poids {cat} {year}")
        # Renormaliser les flottants pour conserver exactement le total.
        poids = poids / s
        total = float(num_col(totals.loc[totals["categorie"].eq(cat)],
                              "nuites").iloc[0])
        com[prefix + "_year"] = total * poids
        for month in MONTHS:
            com[prefix + "_" + month] = com[prefix + "_year"] / 12
    metrics = OUTPUT_COLS[2:]
    frames = [com[["geocode", "admin_level"] + metrics].copy()]
    for level, geo_col in (("DEP", "code_departement"), ("REG", "code_region")):
        agg = com.groupby(geo_col, as_index=False)[metrics].sum()
        agg = agg.rename(columns={geo_col: "geocode"})
        agg.insert(1, "admin_level", level)
        frames.append(agg[OUTPUT_COLS])

    out = pd.concat(frames, ignore_index=True)
    for col in metrics:
        ensure_close(out.loc[out.admin_level.eq("COM"), col].sum(),
                     out.loc[out.admin_level.eq("DEP"), col].sum(),
                     f"COM/DEP {year}/{col}")
        ensure_close(out.loc[out.admin_level.eq("COM"), col].sum(),
                     out.loc[out.admin_level.eq("REG"), col].sum(),
                     f"COM/REG {year}/{col}")
    for category, (prefix, _) in CATEGORIES.items():
        total = float(num_col(totals.loc[totals["categorie"].eq(category)],
                              "nuites").iloc[0])
        ensure_close(out.loc[out.admin_level.eq("COM"), prefix+"_year"].sum(),
                     total, f"total source {year}/{category}")
    for key, value in META.items():
        out[key] = value
    out["annee"] = year
    out["source_totaux"] = "DS_SUIVI_DDE_TOUR_TRAVEL_DEST__T"
    out["annee_reference_population"] = (
        keys["annee_reference_population"].dropna().iloc[0]
        if "annee_reference_population" in keys else "")
    out["annee_reference_logements"] = (
        keys["annee_reference_logements"].dropna().iloc[0]
        if "annee_reference_logements" in keys else "")

    dest = path(year, "scenario_non_marchand_com_dep_reg_{year}.csv")
    out.to_csv(dest, index=False, encoding="utf-8-sig", sep=";")
    note = path(year, "scenario_non_marchand_hypotheses_{year}.txt")
    note.write_text(
        f"CAFÉ {year} — SCÉNARIO EXPLORATOIRE NON VALIDÉ\n\n"
        "Origine : INSEE DS_SUIVI_DDE_TOUR, TRAVEL_DEST=_T = toutes destinations.\n"
        "Les nuitées ne sont PAS des totaux de destinations métropolitaines.\n"
        "Hypothèse géographique : affecter fictivement tous ces totaux aux\n"
        "communes métropolitaines avec poids population/logements (scripts 49/50).\n"
        "Hypothèse mensuelle : répartition UNIFORME 1/12 (aucun profil observé).\n"
        "Chaque commune somme sur 12 mois à son total annuel scénarisé.\n"
        "Départements et régions = somme des communes (sans doubles comptes).\n"
        "NE PAS utiliser comme mesure officielle ni mélanger aux données validées.\n",
        encoding="utf-8",
    )
    print(f"  [OK] {len(com):,} COM / 96 DEP / 13 REG")
    print(f"  [OK] Conservation COM -> DEP -> REG")
    print(f"  [SCÉNARIO] Mensualisation exploratoire uniforme 1/12")
    print(f"  Export : {dest}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, choices=YEARS)
    args = parser.parse_args()
    for year in ([args.year] if args.year else YEARS):
        effectuer(year)


if __name__ == "__main__":
    main()
