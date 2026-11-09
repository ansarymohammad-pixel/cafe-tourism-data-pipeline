
import pandas as pd
from pathlib import Path

fichier = Path("data/raw/SISPEA_FR_2023_AC.xls")

# Lire les données des entités de gestion
df = pd.read_excel(
    fichier,
    sheet_name="Entités de gestion"
)

# Calculer les valeurs manquantes
missing = pd.DataFrame({
    "colonne": df.columns,
    "nb_manquants": df.isna().sum().values,
    "pourcentage": (
        df.isna().mean().values * 100
    ).round(2)
})

# Trier du plus manquant au moins manquant
missing = missing.sort_values(
    "pourcentage",
    ascending=False
)

print("Nombre de lignes :", len(df))
print("Nombre de colonnes :", len(df.columns))

print("\nValeurs manquantes par colonne :")
print(missing.to_string(index=False))

# Exporter le diagnostic
Path("data/processed").mkdir(
    parents=True,
    exist_ok=True
)

missing.to_csv(
    "data/processed/missing_values_report.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nRapport CSV créé !")
