

import pandas as pd
from pynsee.melodi import get_catalog

# Récupérer le catalogue INSEE
catalogue = get_catalog()

# Sélectionner uniquement les colonnes intéressantes
colonnes = [
    "dataset_identifier",
    "title_fr",
    "description_fr",
    "startPeriod",
    "endPeriod"
]

resultat = catalogue[colonnes]

# Afficher les 10 premières lignes
print(resultat.head(10).to_string(index=False))

print("\nNombre de jeux de données :", len(resultat))


# Rechercher les jeux de données liés à la population
population = catalogue[
    catalogue["title_fr"].fillna("").str.contains(
        "population",
        case=False,
        regex=False
    )
]

# Afficher les résultats
print("\nJeux de données sur la population :")

print(
    population[
        ["dataset_identifier", "title_fr"]
    ].to_string(index=False)
)

print("\nNombre de résultats :", len(population))
