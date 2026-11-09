
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "data/raw/tourisme/frequentation_brut.csv"
SORTIE = BASE / "data/processed/tourisme"
SORTIE.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SOURCE, low_memory=False)

# Configuration des catégories
categories = {
    "I551": ("Hotels", "FULL_YEAR"),
    "I553": ("Campings", "HIGH_SEASON"),
    "I552": ("Autres", "FULL_YEAR"),
}

# Filtres communs
base = df[
    (df["TIME_PERIOD"].astype(str) == "2022")
    & (df["FREQ"] == "A")
    & (df["TOUR_MEASURE"] == "NIGHT_SPENT")
    & (df["UNIT_MEASURE"] == "NR")
    & (df["TOUR_RESID"] == "_T")
    & (df["UNIT_LOC_RANKING"] == "_T")
    & (df["HOTEL_STA"] == "_T")
    & (df["EQUIP"] == "_Z")
].copy()

resultats = []

for code, (nom, saison) in categories.items():
    partie = base[
        (base["ACTIVITY"] == code)
        & (base["SEASONALITY"] == saison)
    ].copy()

    partie["categorie"] = nom
    resultats.append(partie)

nuites = pd.concat(resultats, ignore_index=True)

# Conversion des milliers en unités
nuites["nuites"] = (
    pd.to_numeric(nuites["OBS_VALUE_NIVEAU"], errors="coerce")
    * 10 ** pd.to_numeric(nuites["UNIT_MULT"], errors="coerce")
)

# Niveau géographique
def niveau_geo(geo):
    geo = str(geo)
    if "-DEP-" in geo:
        return "Département"
    if "-REG-" in geo:
        return "Région"
    return "Autre"

nuites["niveau"] = nuites["GEO"].apply(niveau_geo)

# Contrôle de doublons
cles = ["GEO", "categorie"]
doublons = nuites[nuites.duplicated(cles, keep=False)]

if not doublons.empty:
    print("Doublons détectés :")
    print(doublons[cles].to_string(index=False))
    raise SystemExit("Vérifier les dimensions avant agrégation.")

# Tableau récapitulatif
tableau = nuites.pivot(
    index=["niveau", "GEO"],
    columns="categorie",
    values="nuites"
).reset_index()

tableau.columns.name = None

for col in ["Hotels", "Campings", "Autres"]:
    if col not in tableau.columns:
        tableau[col] = float("nan")

# Total uniquement si les trois catégories sont présentes
tableau["Total"] = tableau[
    ["Hotels", "Campings", "Autres"]
].sum(axis=1, min_count=3)

tableau.insert(0, "annee", 2022)

tableau = tableau[
    ["annee", "niveau", "GEO",
     "Hotels", "Campings", "Autres", "Total"]
]

# Export
fichier_sortie = SORTIE / "nuites_2022.csv"

tableau.to_csv(
    fichier_sortie,
    index=False,
    encoding="utf-8-sig"
)

print("\nObservations sélectionnées :")
print(nuites.groupby(["niveau", "categorie"]).size())

print("\nTableau :")
print(tableau.head(25).to_string(index=False))

print("\nEnregistré :", fichier_sortie)
