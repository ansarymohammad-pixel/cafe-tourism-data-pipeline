
from pathlib import Path
import pandas as pd

base = Path(__file__).resolve().parent
fichier = base / "data/raw/tourisme/frequentation_brut.csv"

if not fichier.exists():
    print("Fichier touristique introuvable.")
    print("Il faut d'abord extraire DS_TOUR_FREQ.")
    raise SystemExit(1)

df = pd.read_csv(fichier, low_memory=False)

print("\nDimensions :", df.shape)

print("\nColonnes :")
print(df.columns.tolist())

print("\nPériodes disponibles :")
if "TIME_PERIOD" in df.columns:
    print(df["TIME_PERIOD"].value_counts().head(20))

print("\nAperçu sans les colonnes descriptives longues :")
colonnes = [
    c for c in df.columns
    if c not in ["title_fr", "title_en"]
]

print(df[colonnes].head(10).to_string(index=False))

print("\nModalités des dimensions :")
for col in colonnes:
    if col in ["OBS_VALUE", "OBS_VALUE_NIVEAU"]:
        continue

    valeurs = df[col].dropna().unique()
    if len(valeurs) <= 30:
        print(f"{col} : {valeurs}")
