
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parent

SOURCE = (
    BASE / "data/processed/tourisme/nuites_2022.csv"
)

ADMIN = BASE / "data/raw/administratif"

SORTIE = BASE / "data/processed/tourisme"
SORTIE.mkdir(parents=True, exist_ok=True)

# 1. Lire le tableau des nuitées
df = pd.read_csv(SOURCE, dtype={"GEO": str})

# 2. Lire les couches géographiques
regions = gpd.read_file(
    ADMIN / "REGION.shp"
)

departements = gpd.read_file(
    ADMIN / "DEPARTEMENT.shp"
)

# 3. Construire les dictionnaires de noms
noms_regions = dict(
    zip(
        regions["INSEE_REG"].astype(str),
        regions["NOM"]
    )
)

noms_departements = dict(
    zip(
        departements["INSEE_DEP"].astype(str),
        departements["NOM"]
    )
)
noms_departements.update({
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte"
})
# 4. Extraire le code territorial
df["code_territoire"] = (
    df["GEO"].str.split("-").str[-1]
)

# 5. Ajouter les noms
def obtenir_nom(ligne):
    code = ligne["code_territoire"]

    if ligne["niveau"] == "Région":
        return noms_regions.get(code, "Inconnu")

    if ligne["niveau"] == "Département":
        return noms_departements.get(code, "Inconnu")

    return ligne["GEO"]

df["territoire"] = df.apply(
    obtenir_nom, axis=1
)

# 6. Organiser les colonnes
colonnes = [
    "annee",
    "niveau",
    "code_territoire",
    "territoire",
    "Hotels",
    "Campings",
    "Autres",
    "Total",
]

tableau = df[colonnes].copy()

# 7. Export CSV et Excel
tableau.to_csv(
    SORTIE / "tableau_nuitees_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

tableau.to_excel(
    SORTIE / "tableau_nuitees_2022.xlsx",
    index=False
)

print("\n=== TABLEAU CAFÉ ===")
print(tableau.head(20).to_string(index=False))

print("\nTerritoires inconnus :")
print(
    tableau[
        tableau["territoire"] == "Inconnu"
    ][["niveau", "code_territoire"]]
)

print("\nFichiers créés avec succès.")
