
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent

fichier = (
    BASE / "data/processed/tourisme/nuites_2022.csv"
)

df = pd.read_csv(
    fichier,
    dtype=str,
    encoding="utf-8-sig"
)

print("\nDIMENSIONS :", df.shape)
print("\nCOLONNES :")
print(df.columns.tolist())

print("\nPREMIERES LIGNES :")
print(df.head(10).to_string(index=False))

print("\nVALEURS DISTINCTES :")
for col in [
    "ACTIVITY", "GEO_OBJECT", "GEO",
    "TIME_PERIOD", "FREQ", "L_STAY",
    "TOUR_MEASURE", "UNIT_MULT"
]:
    if col in df.columns:
        print(f"\n{col}:")
        print(df[col].dropna().unique()[:30])
