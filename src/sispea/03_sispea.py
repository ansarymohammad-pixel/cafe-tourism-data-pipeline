
from pathlib import Path
import pandas as pd

# Rechercher les fichiers téléchargés
dossier = Path("data/raw")

fichiers = [
    f for f in dossier.iterdir()
    if f.suffix.lower() in [".xls", ".xlsx", ".ods"]
]

print("Fichiers disponibles :")
for i, fichier in enumerate(fichiers, 1):
    print(i, fichier.name)

if not fichiers:
    raise FileNotFoundError(
        "Aucun fichier Excel ou ODS dans data/raw"
    )

# Choisir le premier fichier
fichier = fichiers[0]

# Examiner les feuilles du classeur
excel = pd.ExcelFile(fichier)

print("\nFeuilles disponibles :")
print(excel.sheet_names)

# Lire les cinq premières lignes de chaque feuille
for feuille in excel.sheet_names:
    print(f"\n--- {feuille} ---")
    df = pd.read_excel(
        excel,
        sheet_name=feuille,
        nrows=5
    )
    print(df.to_string(index=False))
