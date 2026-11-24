
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data/processed/tourisme"

# Charger les fichiers
capacites = pd.read_csv(
    DOSSIER / "capacites_communales_2022.csv",
    dtype={"geocode": str}
)

geo = pd.read_csv(
    DOSSIER / "correspondance_geo_2022.csv",
    dtype=str
)

nuites = pd.read_csv(
    DOSSIER / "nuites_2022.csv",
    dtype=str
)

# Jointure géographique
communes = capacites.merge(
    geo,
    on="geocode",
    how="left",
    validate="one_to_one",
    indicator=True
)

print("\nJointure géographique :")
print(communes["_merge"].value_counts())

# Ne pas perdre les communes non appariées
communes = communes.drop(columns="_merge")

# Vérifier les données de nuitées
colonnes_requises = {
    "GEO", "ACTIVITY", "OBS_VALUE_NIVEAU"
}

manquantes = colonnes_requises - set(nuites.columns)

if manquantes:
    raise ValueError(
        f"Colonnes manquantes : {manquantes}. "
        "Vérifier le diagnostic du fichier."
    )

# Normaliser les valeurs numériques
nuites["valeur"] = pd.to_numeric(
    nuites["OBS_VALUE_NIVEAU"],
    errors="coerce"
)

if "UNIT_MULT" in nuites.columns:
    multiplicateur = pd.to_numeric(
        nuites["UNIT_MULT"],
        errors="coerce"
    ).fillna(0)
    nuites["valeur"] *= 10 ** multiplicateur

# Identifier les catégories
categories = {
    "I551": "hotel",
    "I553": "campings",
    "I552": "other"
}

nuites["categorie"] = nuites["ACTIVITY"].map(categories)

nuites = nuites[
    nuites["categorie"].notna()
].copy()

# Examiner les codes et les périodes
print("\nExemples de données :")
print(
    nuites[
        ["GEO", "categorie", "valeur"]
    ].head(15)
)

print("\nCommunes préparées :", len(communes))
print("Observations touristiques :", len(nuites))
