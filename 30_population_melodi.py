
from pathlib import Path
import pandas as pd
from pynsee.melodi import get_catalog, get_dataset, get_range

ANNEE = 2022
DATASET = "DS_POPULATIONS_REFERENCE"

# 1. Vérifier que le dataset existe
catalogue = get_catalog(language="fr")

resultat = catalogue[
    catalogue["dataset_identifier"] == DATASET
]

print("Jeu de données trouvé :")
print(resultat.to_string(index=False))

# 2. Vérifier les modalités disponibles
modalites = get_range(
    DATASET,
    language="fr",
    include_values=True
)

print("\nModalités disponibles :")
print(modalites.head(30).to_string(index=False))

# 3. Télécharger les données
df = get_dataset(DATASET)

print("\nColonnes :", df.columns.tolist())
print("Nombre de lignes :", len(df))

# 4. Sélectionner l'année et la population municipale
df["TIME_PERIOD"] = pd.to_numeric(
    df["TIME_PERIOD"], errors="coerce"
)

print(
    "Années disponibles :",
    sorted(df["TIME_PERIOD"].dropna().unique())
)

population = df[
    (df["TIME_PERIOD"] == ANNEE)
    & (df["POPREF_MEASURE"] == "PMUN")
].copy()

if population.empty:
    raise ValueError(
        f"Aucune population municipale pour {ANNEE}. "
        "Vérifier les années disponibles."
    )

# 5. Normaliser les colonnes
population["geocode"] = population["GEO"].astype(str)

population["admin_level"] = population["GEO_OBJECT"].map({
    "REG": "1",
    "DEP": "2",
    "COM": "4"
})

colonne_valeur = (
    "OBS_VALUE_NIVEAU"
    if "OBS_VALUE_NIVEAU" in population.columns
    else "OBS_VALUE"
)

population["population"] = pd.to_numeric(
    population[colonne_valeur],
    errors="coerce"
)

population = population[
    ["geocode", "admin_level", "population"]
].dropna(subset=["admin_level"])

# 6. Sauvegarder
sortie = Path(
    "data/processed/population/"
    f"population_melodi_{ANNEE}.csv"
)

sortie.parent.mkdir(parents=True, exist_ok=True)

population.to_csv(
    sortie,
    index=False,
    encoding="utf-8-sig"
)

print("\nRésultat :")
print(population.head(10))
print("\nLignes :", len(population))
print("Fichier :", sortie)
