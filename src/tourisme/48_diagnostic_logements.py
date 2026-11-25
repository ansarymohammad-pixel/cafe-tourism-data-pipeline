
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# Remplacer par le chemin réel de ton CSV téléchargé
FICHIER = ROOT / "data/raw/tourisme/DS_RP_LOGEMENT_PRINC_2023_data.csv"

df = pd.read_csv(
    FICHIER,
    dtype=str,
    sep=None,
    engine="python"
)

print("Nombre de lignes :", len(df))
print("Colonnes :", df.columns.tolist())

for col in [
    "TIME_PERIOD",
    "GEO_OBJECT",
    "OCS",
    "RP_MEASURE",
    "FREQ"
]:
    print(f"\n=== {col} ===")
    print(df[col].value_counts(dropna=False).head(30))

# Examiner uniquement les résidences secondaires de 2023
selection = df[
    (df["TIME_PERIOD"] == "2023") &
    (df["OCS"] == "DW_SEC_DW_OCC") &
    (df["RP_MEASURE"] == "DWELLINGS")
]

print("\nLignes présélectionnées :", len(selection))

# Contrôle des autres dimensions pour identifier
# les totaux non ventilés et éviter les doublons
dimensions = [
    "GEO_OBJECT", "L_STAY", "TDW", "CARS",
    "CARPARK", "NOR", "TSH", "BUILD_END", "NRG_SRC"
]

for col in dimensions:
    print(f"\n{col}")
    print(selection[col].value_counts(dropna=False).head(20))


# ÉTAPE 1 : sélectionner les résidences secondaires
# et logements occasionnels, au niveau communal

filtres = {
    "TIME_PERIOD": "2023",
    "GEO_OBJECT": "COM",
    "OCS": "DW_SEC_DW_OCC",
    "RP_MEASURE": "DWELLINGS",
    "TDW": "_T",
    "L_STAY": "_T",
    "CARS": "_T",
    "CARPARK": "_T",
    "NOR": "_T",
    "TSH": "_T",
    "BUILD_END": "_T",
    "NRG_SRC": "_T",
    "FREQ": "A",
}

selection = df.copy()

for colonne, valeur in filtres.items():
    selection = selection[
        selection[colonne] == valeur
    ]

print("Communes sélectionnées :", len(selection))
print("GEO uniques :", selection["GEO"].nunique())
print("Doublons GEO :", selection["GEO"].duplicated().sum())
print(selection[["GEO", "OBS_VALUE"]].head(10))

# Vérifier les valeurs numériques
selection["OBS_VALUE"] = pd.to_numeric(
    selection["OBS_VALUE"],
    errors="coerce"
)

print("Valeurs manquantes :", selection["OBS_VALUE"].isna().sum())
print("Total logements :", selection["OBS_VALUE"].sum())

# Ne pas écraser les données sources
sortie = ROOT / "data/processed/tourisme/residences_secondaires_2023_communes.csv"

selection[["GEO", "OBS_VALUE"]].to_csv(
    sortie,
    index=False,
    encoding="utf-8-sig"
)

print("Fichier créé :", sortie)

# ÉTAPE 2 — EXTRACTION DES RÉSIDENCES SECONDAIRES 2023

filtres = {
    "TIME_PERIOD": "2023",
    "GEO_OBJECT": "COM",
    "OCS": "DW_SEC_DW_OCC",
    "RP_MEASURE": "DWELLINGS",
    "TDW": "_T",
    "L_STAY": "_T",
    "CARS": "_T",
    "CARPARK": "_T",
    "NOR": "_T",
    "TSH": "_T",
    "BUILD_END": "_T",
    "NRG_SRC": "_T",
    "FREQ": "A",
}

selection = df.copy()

for colonne, valeur in filtres.items():
    selection = selection[selection[colonne] == valeur]

selection = selection.copy()

selection["OBS_VALUE"] = pd.to_numeric(
    selection["OBS_VALUE"],
    errors="coerce"
)

print("\n=== RÉSULTATS COMMUNAUX 2023 ===")
print("Nombre de lignes :", len(selection))
print("Codes GEO uniques :", selection["GEO"].nunique())
print("Doublons GEO :", selection["GEO"].duplicated().sum())
print("Valeurs manquantes :", selection["OBS_VALUE"].isna().sum())
print("Total résidences :", selection["OBS_VALUE"].sum())
print("Statuts :", selection["OBS_STATUS"].value_counts(dropna=False))

print("\nExemples :")
print(selection[["GEO", "OBS_VALUE"]].head(10))

sortie = (
    ROOT / "data/processed/tourisme/"
    "residences_secondaires_2023_communes.csv"
)

sortie.parent.mkdir(parents=True, exist_ok=True)

selection[["GEO", "OBS_VALUE", "OBS_STATUS"]].to_csv(
    sortie,
    index=False,
    encoding="utf-8-sig"
)

print("\nFichier créé :", sortie)

