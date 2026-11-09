
from pathlib import Path
import geopandas as gpd
import pandas as pd

BASE = Path(__file__).resolve().parent

geo = gpd.read_file(
    BASE / "data/raw/administratif/COMMUNE.shp"
)

correspondance = (
    geo[["INSEE_COM", "INSEE_DEP", "INSEE_REG"]]
    .drop_duplicates(subset=["INSEE_COM"])
    .rename(columns={
        "INSEE_COM": "geocode",
        "INSEE_DEP": "code_departement",
        "INSEE_REG": "code_region"
    })
)

for col in correspondance.columns:
    correspondance[col] = correspondance[col].astype(str)

assert not correspondance["geocode"].duplicated().any()

sortie = (
    BASE / "data/processed/tourisme/"
    "correspondance_geo_2022.csv"
)

correspondance.to_csv(
    sortie, index=False, encoding="utf-8-sig"
)

print("Correspondances :", len(correspondance))
print(correspondance.head())
