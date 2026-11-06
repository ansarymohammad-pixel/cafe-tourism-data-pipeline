
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent

brut = pd.read_csv(
    BASE / "data/raw/tourisme/capacite_brut.csv",
    usecols=["GEO", "TIME_PERIOD"],
    low_memory=False
)

final = pd.read_csv(
    BASE / "data/processed/tourisme/capacites_communales_2026.csv",
    dtype={"code_commune": str}
)

# Codes communaux du fichier brut
codes_bruts = set(
    brut.loc[
        brut["GEO"].astype(str).str.contains(
            "-COM-", regex=False, na=False
        ),
        "GEO"
    ].dropna()
)

# Codes conservés
codes_finaux = set(final["GEO"].dropna())

manquants = sorted(codes_bruts - codes_finaux)

print("Communes dans le brut :", len(codes_bruts))
print("Communes dans le résultat :", len(codes_finaux))
print("Communes écartées :", len(manquants))

print("\nExemples de codes écartés :")
print(manquants[:30])

pd.DataFrame({
    "GEO": manquants
}).to_csv(
    BASE / "data/processed/tourisme/communes_ecartees.csv",
    index=False
)
