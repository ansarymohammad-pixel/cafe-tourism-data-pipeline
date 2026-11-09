
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parent

CAPACITES = (
    BASE / "data/processed/tourisme/"
    "capacites_communales_2022.csv"
)

DOSSIER_GEO = BASE / "data/raw/administratif"

SORTIE = BASE / "data/processed/tourisme/tableau_final"
SORTIE.mkdir(parents=True, exist_ok=True)

# 1. Charger les capacités 2022
df = pd.read_csv(
    CAPACITES,
    dtype={"geocode": str, "admin_level": str}
)

# 2. Charger les correspondances géographiques
communes_geo = gpd.read_file(
    DOSSIER_GEO / "COMMUNE.shp"
)

departements_geo = gpd.read_file(
    DOSSIER_GEO / "DEPARTEMENT.shp"
)

# Code commune -> département
correspondance = communes_geo[
    ["INSEE_COM", "INSEE_DEP", "INSEE_REG"]
].drop_duplicates(subset=["INSEE_COM"])

correspondance = correspondance.rename(columns={
    "INSEE_COM": "geocode",
    "INSEE_DEP": "code_departement",
    "INSEE_REG": "code_region"
})

# 3. Ajouter les départements et régions
communes = df.merge(
    correspondance,
    on="geocode",
    how="left",
    validate="one_to_one",
    indicator=True
)

print("Résultat de la jointure géographique :")
print(communes["_merge"].value_counts())

communes = communes.drop(columns="_merge")

# Attention : IGN FXX couvre la métropole.
# Les communes DROM restent sans code_region
# dans cette jointure et doivent être traitées
# séparément avant une couverture France entière.

# 4. Créer le niveau communal
capacites_cols = [
    "places_hotels",
    "places_campings",
    "places_autres"
]

communes_final = communes[
    ["geocode", "admin_level"] + capacites_cols
].copy()

# 5. Agréger au niveau départemental
departements = (
    communes.dropna(subset=["code_departement"])
    .groupby("code_departement", as_index=False)[
        capacites_cols
    ].sum(min_count=1)
)

departements = departements.rename(columns={
    "code_departement": "geocode"
})

departements["admin_level"] = "2"

# 6. Agréger au niveau régional
regions = (
    communes.dropna(subset=["code_region"])
    .groupby("code_region", as_index=False)[
        capacites_cols
    ].sum(min_count=1)
)

regions = regions.rename(columns={
    "code_region": "geocode"
})

regions["admin_level"] = "1"

# 7. Assembler les trois niveaux
final = pd.concat(
    [
        regions,
        departements,
        communes_final
    ],
    ignore_index=True
)

# 8. Renommer les capacités
final = final.rename(columns={
    "places_hotels": "hotel_capacity",
    "places_campings": "camping_capacity",
    "places_autres": "other_capacity"
})

# 9. Ajouter les colonnes des nuitées
colonnes_nuitees = [
    "hotel_nights_year",
    "campings_nights_year",
    "other_nights_year",
    "hotel_nights_january",
    "campings_nights_january",
    "other_nights_january"
]

for col in colonnes_nuitees:
    final[col] = pd.NA

# 10. Ordonner les colonnes
final = final[
    [
        "geocode",
        "admin_level",
        "hotel_capacity",
        "camping_capacity",
        "other_capacity"
    ] + colonnes_nuitees
]

# 11. Exporter
csv_path = SORTIE / "cafe_tourisme_2022_final.csv"
xlsx_path = SORTIE / "cafe_tourisme_2022_final.xlsx"

final.to_csv(
    csv_path,
    index=False,
    encoding="utf-8-sig"
)

with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
    final.to_excel(
        writer,
        sheet_name="Toutes_donnees",
        index=False
    )

    for niveau, nom in [
        ("1", "Regions"),
        ("2", "Departements"),
        ("4", "Communes")
    ]:
        final[final["admin_level"] == niveau].to_excel(
            writer,
            sheet_name=nom,
            index=False
        )

print("\nDimensions finales :", final.shape)
print("\nLignes par niveau :")
print(final["admin_level"].value_counts())

print("\nFichiers générés :")
print(csv_path)
print(xlsx_path)
