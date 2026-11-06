
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data/raw/tourisme"

print("Fichiers disponibles :")
for fichier in DOSSIER.glob("*.csv"):
    print("-", fichier.name)

fichiers = list(DOSSIER.glob("*capacite*.csv"))
fichiers += list(DOSSIER.glob("*capacity*.csv"))
fichiers += list(DOSSIER.glob("*tour_cap*.csv"))

fichiers = list(dict.fromkeys(fichiers))

if not fichiers:
    print("\nAucun fichier de capacités trouvé.")
    print("Vérifie le nom du CSV créé pour DS_TOUR_CAP.")
    raise SystemExit(1)

fichier = fichiers[0]
print("\nFichier analysé :", fichier.name)

df = pd.read_csv(fichier, low_memory=False)

print("\nDimensions :", df.shape)
print("\nColonnes :", df.columns.tolist())

if "TIME_PERIOD" in df.columns:
    print("\nAnnées disponibles :")
    print(df["TIME_PERIOD"].value_counts().head(20))

if "GEO" in df.columns:
    print("\nTypes de territoires :")
    print(
        df["GEO"].astype(str)
        .str.extract(r"-(COM|DEP|REG)-")[0]
        .value_counts(dropna=False)
    )

print("\nAperçu des données :")
colonnes = [
    c for c in df.columns
    if c not in ["title_en", "title_fr"]
]
print(df[colonnes].head(10).to_string(index=False))
