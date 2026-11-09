
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data/processed/tourisme"

df = pd.read_csv(
    DOSSIER / "capacites_geo_corrigees_2022.csv",
    dtype={"geocode": str}
)

# Identifier les 45 arrondissements municipaux
arrondissements = (
    df["geocode"].str.fullmatch(r"751\d{2}")
    | df["geocode"].str.fullmatch(r"6938[1-9]")
    | df["geocode"].str.fullmatch(r"132(0[1-9]|1[0-6])")
)

# Conserver une seule granularité communale
communes = df.loc[~arrondissements].copy()

# Isoler les communes sans rattachement géographique
metro = communes[
    communes["code_departement"].notna()
].copy()

drom = communes[
    communes["code_departement"].isna()
].copy()

colonnes = [
    "places_hotels",
    "places_campings",
    "places_autres"
]

print("Lignes initiales :", len(df))
print("Arrondissements exclus :", arrondissements.sum())
print("Communes après correction :", len(communes))
print("Communes métropolitaines :", len(metro))
print("Communes DROM à traiter :", len(drom))

print("\nCapacités métropolitaines :")
print(metro[colonnes].sum())

# Contrôles
assert arrondissements.sum() == 45
assert len(communes) == len(df) - 45
assert not communes["geocode"].duplicated().any()

# Exporter sans écraser les sources
communes.to_csv(
    DOSSIER / "capacites_communes_sans_doublons_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

metro.to_csv(
    DOSSIER / "capacites_metro_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

drom.to_csv(
    DOSSIER / "capacites_drom_a_traiter_2022.csv",
    index=False,
    encoding="utf-8-sig"
)
