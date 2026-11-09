import pandas as pd
from pathlib import Path

fichier = "data/raw/tourisme/base-cc-tourisme-2022-geo2022.csv"

df = pd.read_csv(
    fichier,
    sep=";",
    encoding="utf-8-sig",
    dtype={"CODGEO": str}
)

# Colonnes de capacité à conserver
colonnes = [
    "CODGEO",
    "HTCH22",
    "CPGEO22",
    "VVLIT22",
    "RTLIT22",
    "AJCSLIT22"
]

capacites = df[colonnes].copy()

# Convertir les capacités en nombres
for col in colonnes[1:]:
    capacites[col] = pd.to_numeric(
        capacites[col],
        errors="coerce"
    )

# Construire les indicateurs
capacites["places_hotels"] = capacites["HTCH22"]

capacites["places_campings"] = capacites["CPGEO22"]

capacites["places_autres"] = capacites[
    ["VVLIT22", "RTLIT22", "AJCSLIT22"]
].sum(axis=1, min_count=1)

# Normaliser les codes
capacites["geocode"] = capacites["CODGEO"]
capacites["admin_level"] = "4"
capacites["annee_capacite"] = 2022

# Tableau final
resultat = capacites[
    [
        "geocode",
        "admin_level",
        "annee_capacite",
        "places_hotels",
        "places_campings",
        "places_autres"
    ]
]

sortie = Path(
    "data/processed/tourisme/"
    "capacites_communales_2022.csv"
)

sortie.parent.mkdir(parents=True, exist_ok=True)

resultat.to_csv(
    sortie,
    index=False,
    encoding="utf-8-sig"
)

print("Dimensions :", resultat.shape)
print(resultat.head(10).to_string(index=False))

print("\nCapacités totales :")
print(
    resultat[
        ["places_hotels", "places_campings", "places_autres"]
    ].sum()
)
# Conserver les codes géographiques comme texte
resultat["geocode"] = resultat["geocode"].astype(str)

# Extraire le code département
resultat["code_departement"] = resultat["geocode"].str[:2]

# Adapter pour les départements d'outre-mer
masque_drom = resultat["geocode"].str.startswith(("97", "98"))

resultat.loc[masque_drom, "code_departement"] = (
    resultat.loc[masque_drom, "geocode"].str[:3]
)

print(resultat[
    ["geocode", "code_departement", "admin_level"]
].head(10))