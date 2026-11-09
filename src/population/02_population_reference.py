
from pynsee.melodi import get_dataset

# Identifier le jeu de données
dataset_id = "DS_POPULATIONS_REFERENCE"

# Télécharger les données
population = get_dataset(dataset_id)

# Examiner le résultat
print("Dimensions :", population.shape)

print("\nColonnes disponibles :")
print(population.columns.tolist())

print("\nPremières lignes :")
print(population.head().to_string())
population.to_csv(
    "population_brute.csv",
    index=False,
    encoding="utf-8-sig"
)

print("CSV créé avec succès !")
