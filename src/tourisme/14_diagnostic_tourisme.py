
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
fichier = BASE / "data/raw/tourisme/frequentation_brut.csv"

df = pd.read_csv(fichier, low_memory=False)

# Nuitées 2022, sans filtres trop restrictifs
data = df[
    (df["TIME_PERIOD"].astype(str) == "2022")
    & (df["TOUR_MEASURE"] == "NIGHT_SPENT")
].copy()

print("\nNombre d'observations :", len(data))

print("\nActivités disponibles :")
print(data["ACTIVITY"].value_counts(dropna=False))

# Examiner les combinaisons utilisées par l'INSEE
dimensions = [
    "ACTIVITY",
    "FREQ",
    "SEASONALITY",
    "TOUR_RESID",
    "UNIT_LOC_RANKING",
    "HOTEL_STA",
    "EQUIP",
    "UNIT_MEASURE",
    "UNIT_MULT",
]

print("\nCombinaisons de dimensions :")
print(
    data.groupby(dimensions, dropna=False)
    .size()
    .reset_index(name="nombre")
    .to_string(index=False)
)

print("\nExemples de campings :")
campings = data[data["ACTIVITY"] == "I553"]

print(
    campings[
        ["GEO", "TIME_PERIOD", "SEASONALITY",
         "TOUR_RESID", "UNIT_LOC_RANKING",
         "HOTEL_STA", "OBS_VALUE_NIVEAU",
         "OBS_STATUS", "CONF_STATUS"]
    ].head(15).to_string(index=False)
)

print("\nExemples autres hébergements :")
autres = data[data["ACTIVITY"].isin(["I552", "I552B"])]

print(
    autres[
        ["GEO", "ACTIVITY", "SEASONALITY",
         "TOUR_RESID", "OBS_VALUE_NIVEAU"]
    ].head(15).to_string(index=False)
)
