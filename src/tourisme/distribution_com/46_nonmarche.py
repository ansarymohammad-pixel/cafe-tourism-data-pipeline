from pynsee.melodi import get_dataset

df = get_dataset("DS_SUIVI_DDE_TOUR")

print(df.columns.tolist())

df_2022 = df[
    df["TIME_PERIOD"].astype(str).str.startswith("2022")
]

print(df_2022["TYPE_TOUR_ACCOMODATION"].value_counts())
print(df_2022["TOUR_MEASURE"].value_counts())
print(df_2022["FREQ"].value_counts())


import pandas as pd

non_marchand = df_2022[
    df_2022["TYPE_TOUR_ACCOMODATION"].isin([
        "FRIENDS_FAMILY",
        "SECOND_HOME"
    ])
].copy()

colonnes = [
    "TIME_PERIOD",
    "FREQ",
    "TYPE_TOUR_ACCOMODATION",
    "TOUR_MEASURE",
    "GEO",
    "TRAVEL_DEST",
    "SEASONAL_ADJUST",
    "UNIT_MEASURE",
    "UNIT_MULT",
    "OBS_VALUE_NIVEAU",
    "OBS_STATUS"
]

print("\n=== TOURISME NON MARCHAND 2022 ===")
print(non_marchand[colonnes].to_string(index=False))

print("\n=== NUITÉES NON MARCHANDES ===")
nuitees = non_marchand[
    non_marchand["TOUR_MEASURE"].eq("NIGHT_SPENT")
]

print(nuitees[colonnes].to_string(index=False))
