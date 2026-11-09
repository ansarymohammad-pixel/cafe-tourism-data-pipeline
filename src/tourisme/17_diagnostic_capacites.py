
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
fichier = BASE / "data/raw/tourisme/capacite_brut.csv"

# Colonnes nécessaires seulement
colonnes = [
    "GEO", "TIME_PERIOD", "ACTIVITY",
    "TOUR_MEASURE", "UNIT_LOC_RANKING",
    "L_STAY", "OBS_STATUS", "OBS_VALUE_NIVEAU"
]

df = pd.read_csv(
    fichier,
    usecols=colonnes,
    low_memory=False
)

print("\n=== ANNEES ===")
print(df["TIME_PERIOD"].value_counts(dropna=False))

print("\n=== ACTIVITES ===")
print(df["ACTIVITY"].value_counts(dropna=False))

print("\n=== MESURES ===")
print(df["TOUR_MEASURE"].value_counts(dropna=False))

print("\n=== CATEGORIES ===")
print(df["UNIT_LOC_RANKING"].value_counts(dropna=False))

print("\n=== DUREES DE SEJOUR ===")
print(df["L_STAY"].value_counts(dropna=False))

print("\n=== NOMBRE DE COMMUNES DISTINCTES ===")
communes = df[
    df["GEO"].astype(str).str.contains("-COM-", regex=False)
]
print(communes["GEO"].nunique())

print("\n=== COMBINAISONS PAR ACTIVITE ===")
print(
    df.groupby(
        ["ACTIVITY", "TOUR_MEASURE", "L_STAY"],
        dropna=False
    ).size().reset_index(name="nombre")
    .to_string(index=False)
)

print("\n=== EXEMPLES COMMUNAUX ===")
print(
    communes[
        ["GEO", "ACTIVITY", "TOUR_MEASURE",
         "UNIT_LOC_RANKING", "L_STAY",
         "OBS_VALUE_NIVEAU"]
    ].head(20).to_string(index=False)
)
