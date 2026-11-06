
import geopandas as gpd
import pandas as pd
from pathlib import Path

fichier = Path("data/raw/RPG_Parcelles.gpkg")

# Lire un échantillon de 10 000 parcelles
rpg = gpd.read_file(fichier, rows=10000)

# Calculer les surfaces géométriques
rpg["surface_ha"] = rpg.geometry.area / 10000

# Comparer avec les surfaces déclarées
rpg["difference"] = (
    rpg["surf_parc"] - rpg["surface_ha"]
)

print("Nombre de parcelles :", len(rpg))

print("\nStatistiques des surfaces :")
print(
    rpg[["surf_parc", "surface_ha"]].describe()
)

print("\nNombre de surfaces déclarées nulles :")
print((rpg["surf_parc"] == 0).sum())

print("\nNombre de surfaces calculées nulles :")
print((rpg["surface_ha"] == 0).sum())

print("\nCorrespondance avec un arrondi à 2 décimales :")
print(
    (
        rpg["surf_parc"]
        == rpg["surface_ha"].round(2)
    ).mean() * 100
)

print("\nExemples de parcelles plus grandes :")
print(
    rpg.loc[
        rpg["surface_ha"] > 0.1,
        ["id_parcel", "surf_parc", "surface_ha"]
    ].head(10).to_string(index=False)
)


# Statistiques des surfaces
print("\nDistribution des surfaces (ha) :")

print(
    rpg["surface_ha"].describe(
        percentiles=[0.25, 0.5, 0.75, 0.9, 0.99]
    )
)

# Les 10 plus grandes parcelles de l'échantillon
print("\nLes 10 plus grandes parcelles :")

print(
    rpg.nlargest(10, "surface_ha")[
        ["id_parcel", "code_cultu",
         "surf_parc", "surface_ha"]
    ].to_string(index=False)
)

# Surface totale par code de culture
surfaces_cultures = (
    rpg.groupby("code_cultu")
    .agg(
        nombre_parcelles=("id_parcel", "count"),
        surface_totale_ha=("surface_ha", "sum")
    )
    .sort_values(
        "surface_totale_ha",
        ascending=False
    )
)

print("\nSurfaces par culture :")
print(surfaces_cultures.head(15))


import geopandas as gpd

fichier = "data/raw/RPG_Parcelles.gpkg"

# Lire trois portions différentes du fichier
for debut in [0, 100000, 500000]:

    rpg_test = gpd.read_file(
        fichier,
        skip_features=debut,
        max_features=100,
        engine="pyogrio"
    )

    surfaces = rpg_test.geometry.area / 10000

    print(f"\nÀ partir de la ligne {debut} :")
    print("Nombre de lignes :", len(rpg_test))
    print("Surface moyenne :", surfaces.mean())
    print("Surface maximale :", surfaces.max())
