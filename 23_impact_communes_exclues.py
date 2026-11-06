
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data/processed/tourisme"

capacites = pd.read_csv(
    DOSSIER / "capacites_communales_2026.csv",
    dtype={"code_commune": str}
)

exclues = pd.read_csv(
    DOSSIER / "estimations_communales"
    / "communes_non_concordantes_2022_2026.csv",
    dtype={"code_commune": str}
)

colonnes = [
    "places_hotels",
    "places_campings",
    "places_autres"
]

# Capacités des communes exclues
impact = exclues[
    ["code_commune"] + colonnes
].copy()

impact["places_total"] = impact[colonnes].sum(
    axis=1, min_count=1
)

impact = impact.sort_values(
    "places_total",
    ascending=False
)

# Comparaison avec l'ensemble des capacités
total_france = capacites[colonnes].sum()
total_exclu = impact[colonnes].sum()

bilan = pd.DataFrame({
    "capacite_totale": total_france,
    "capacite_exclue": total_exclu
})

bilan["pourcentage_exclu"] = (
    100
    * bilan["capacite_exclue"]
    / bilan["capacite_totale"].replace(0, float("nan"))
)

print("\n=== IMPACT DES COMMUNES EXCLUES ===")
print("Nombre de communes exclues :", len(impact))

print("\nCapacités exclues :")
print(bilan.to_string())

print("\nTop 20 des communes exclues :")
print(impact.head(20).to_string(index=False))

print("\nCommunes exclues avec capacité positive :")
print((impact["places_total"] > 0).sum())

impact.to_csv(
    DOSSIER / "impact_communes_exclues.csv",
    index=False,
    encoding="utf-8-sig"
)

bilan.to_csv(
    DOSSIER / "bilan_impact_communes_exclues.csv",
    encoding="utf-8-sig"
)

print("\nFichiers créés.")
