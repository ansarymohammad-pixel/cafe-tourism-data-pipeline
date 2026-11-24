
from pathlib import Path
import pandas as pd

# ============================================================
# PROJET CAFÉ - CAPACITÉS TOURISTIQUES COMMUNALES
# Source : INSEE / DS_TOUR_CAP
# Année des capacités : 2026
# ============================================================

# 1. CHEMINS
BASE = Path(__file__).resolve().parent
SOURCE = BASE / "data/raw/tourisme/capacite_brut.csv"
SORTIE = BASE / "data/processed/tourisme"

SORTIE.mkdir(parents=True, exist_ok=True)

if not SOURCE.exists():
    raise FileNotFoundError(f"Fichier introuvable : {SOURCE}")

# 2. CHARGEMENT
colonnes = [
    "GEO",
    "TIME_PERIOD",
    "ACTIVITY",
    "TOUR_MEASURE",
    "UNIT_LOC_RANKING",
    "L_STAY",
    "OBS_VALUE_NIVEAU",
]

df = pd.read_csv(
    SOURCE,
    usecols=colonnes,
    dtype={"GEO": "string"},
    low_memory=False
)

print("=== DONNÉES BRUTES ===")
print("Nombre de lignes :", len(df))

# 3. FILTRAGE
# Accepte les codes communaux ordinaires et corses
masque_commune = df["GEO"].str.fullmatch(
    r"2026-COM-(?:[0-9]{5}|2[AB][0-9]{3})",
    na=False
)

annees = pd.to_numeric(
    df["TIME_PERIOD"], errors="coerce"
)

masque = (
    masque_commune
    & (annees == 2026)
    & (df["UNIT_LOC_RANKING"] == "_T")
    & (df["L_STAY"] == "_T")
    & (df["ACTIVITY"].isin(["I551", "I553", "I552"]))
    & (df["TOUR_MEASURE"] == "PLACE")
)

df = df.loc[masque].copy()

# 4. CONVERSION NUMÉRIQUE
df["capacite"] = pd.to_numeric(
    df["OBS_VALUE_NIVEAU"],
    errors="coerce"
)

print("\n=== APRÈS FILTRAGE ===")
print("Observations :", len(df))
print("Communes distinctes :", df["GEO"].nunique())

print("\nObservations par activité :")
print(df["ACTIVITY"].value_counts())

# 5. CONTRÔLE DES DOUBLONS
cles = ["GEO", "ACTIVITY"]

doublons = df[df.duplicated(cles, keep=False)]

if not doublons.empty:
    print("\nATTENTION : doublons détectés")
    print(doublons.head(20).to_string(index=False))
    raise SystemExit("Arrêt : vérifier les doublons.")

# 6. TABLEAU COMMUNAL
tableau = df.pivot(
    index="GEO",
    columns="ACTIVITY",
    values="capacite"
).reset_index()

tableau.columns.name = None

tableau = tableau.rename(columns={
    "I551": "places_hotels",
    "I553": "places_campings",
    "I552": "places_autres",
})

# Vérifier les colonnes attendues
colonnes_capacite = [
    "places_hotels",
    "places_campings",
    "places_autres",
]

for colonne in colonnes_capacite:
    if colonne not in tableau.columns:
        tableau[colonne] = float("nan")

# 7. IDENTIFIANTS GÉOGRAPHIQUES
tableau["code_commune"] = tableau["GEO"].str[-5:]

def obtenir_departement(code):
    if code.startswith(("2A", "2B")):
        return code[:2]
    if code.startswith(("97", "98")):
        return code[:3]
    return code[:2]

tableau["code_departement"] = (
    tableau["code_commune"].apply(obtenir_departement)
)

tableau.insert(0, "annee_capacite", 2026)

# 8. ORGANISATION
tableau = tableau[
    [
        "annee_capacite",
        "GEO",
        "code_commune",
        "code_departement",
        "places_hotels",
        "places_campings",
        "places_autres",
    ]
].sort_values("code_commune").reset_index(drop=True)

# 9. CONTRÔLES DE QUALITÉ
print("\n=== CONTRÔLES QUALITÉ ===")
print("Nombre de communes :", len(tableau))

print("\nValeurs manquantes :")
print(tableau.isna().sum())

print("\nCapacités négatives :")
print((tableau[colonnes_capacite] < 0).sum())

print("\nNombre de départements :")
print(tableau["code_departement"].nunique())

print("\nCommunes corses :")
print(
    tableau["code_departement"]
    .isin(["2A", "2B"])
    .sum()
)

# 10. EXPORT
fichier_csv = SORTIE / "capacites_communales_2026.csv"

tableau.to_csv(
    fichier_csv,
    index=False,
    encoding="utf-8-sig"
)

print("\n=== APERÇU DU TABLEAU ===")
print(tableau.head(15).to_string(index=False))

print("\nFichier créé :", fichier_csv)
print("\nTraitement terminé.")
