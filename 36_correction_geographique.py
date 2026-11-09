
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data/processed/tourisme"

capacites = pd.read_csv(
    DOSSIER / "capacites_communales_2022.csv",
    dtype={"geocode": str}
)

geo = pd.read_csv(
    DOSSIER / "correspondance_geo_2022.csv",
    dtype=str
)

# Associer les communes au référentiel IGN
df = capacites.merge(
    geo,
    on="geocode",
    how="left",
    validate="one_to_one"
)

# Rattacher les arrondissements municipaux
# à leur département et à leur région
groupes = [
    (range(75101, 75121), "75", "11", "75056"),
    (range(69381, 69390), "69", "84", "69123"),
    (range(13201, 13217), "13", "93", "13055")
]

df["commune_mere"] = df["geocode"]

for codes, dep, reg, mere in groupes:
    masque = df["geocode"].isin(
        [str(code) for code in codes]
    )

    df.loc[masque, "code_departement"] = dep
    df.loc[masque, "code_region"] = reg
    df.loc[masque, "commune_mere"] = mere

# Identifier les territoires sans correspondance
non_appariees = df[
    df["code_departement"].isna()
]

print("Lignes totales :", len(df))
print("Sans département :", len(non_appariees))

print("\nCapacités sans département :")
print(
    non_appariees[
        ["places_hotels", "places_campings", "places_autres"]
    ].sum()
)

sortie = DOSSIER / "capacites_geo_corrigees_2022.csv"

df.to_csv(
    sortie,
    index=False,
    encoding="utf-8-sig"
)

print("\nFichier créé :", sortie)
