
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

df = capacites.merge(
    geo,
    on="geocode",
    how="left",
    indicator=True,
    validate="one_to_one"
)

absentes = df[df["_merge"] == "left_only"].copy()

print("\nCOMMUNES NON APPARIEES :", len(absentes))

print("\nCODES DES COMMUNES :")
print(absentes["geocode"].tolist())

print("\nCAPACITES NON APPARIEES :")
print(
    absentes[
        ["places_hotels", "places_campings", "places_autres"]
    ].sum()
)

# Identifier les codes d'outre-mer
absentes["outre_mer"] = absentes["geocode"].str.match(
    r"^(97|98)"
)

print("\nREPARTITION :")
print(absentes["outre_mer"].value_counts())

print("\nCOMMUNES METROPOLITAINES NON APPARIEES :")
print(
    absentes.loc[
        ~absentes["outre_mer"],
        ["geocode", "places_hotels",
         "places_campings", "places_autres"]
    ].to_string(index=False)
)

sortie = DOSSIER / "communes_non_appariees_2022.csv"

absentes.to_csv(
    sortie,
    index=False,
    encoding="utf-8-sig"
)

print("\nFichier exporté :", sortie)
