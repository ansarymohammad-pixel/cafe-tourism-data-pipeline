
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent
fichier = BASE / "data/raw/tourisme/frequentation_brut.csv"

df = pd.read_csv(fichier, low_memory=False)

print("\nColonnes disponibles :")
for colonne in df.columns:
    print("-", colonne)

if "TIME_PERIOD" not in df.columns:
    raise ValueError("Colonne TIME_PERIOD introuvable")

# Conserver les observations annuelles de 2022
df_2022 = df[
    df["TIME_PERIOD"].astype(str).eq("2022")
].copy()

print("\nObservations pour 2022 :", len(df_2022))

print("\nValeurs des dimensions :")
for colonne in df_2022.columns:
    if colonne not in [
        "OBS_VALUE_NIVEAU",
        "OBS_VALUE",
        "title_fr",
        "title_en",
    ]:
        valeurs = df_2022[colonne].dropna().unique()
        if len(valeurs) <= 30:
            print(colonne, ":", valeurs)

print("\nAperçu :")
print(df_2022.head(10).to_string(index=False))

sortie = BASE / "data/processed/tourisme"
sortie.mkdir(parents=True, exist_ok=True)

df_2022.to_csv(
    sortie / "frequentation_2022_a_verifier.csv",
    index=False
)
