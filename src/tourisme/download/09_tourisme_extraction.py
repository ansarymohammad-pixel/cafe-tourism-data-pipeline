
from pathlib import Path
import pandas as pd
from pynsee.melodi import get_dataset

BASE = Path(__file__).resolve().parent
RAW = BASE / "data" / "raw" / "tourisme"
RAW.mkdir(parents=True, exist_ok=True)

datasets = {
    "frequentation": "DS_TOUR_FREQ",
    "capacite": "DS_TOUR_CAP",
    "tourisme_national": "DS_SUIVI_DDE_TOUR",
}

for nom, identifiant in datasets.items():
    print(f"\n=== {identifiant} ===")

    try:
        df = get_dataset(identifiant)

        print("Dimensions :", df.shape)
        print("Colonnes :", df.columns.tolist())
        print(df.head(5).to_string(index=False))

        # Sauvegarder les données brutes
        chemin = RAW / f"{nom}_brut.csv"
        df.to_csv(chemin, index=False)

        print("Enregistré :", chemin)

        # Examiner les années disponibles
        if "TIME_PERIOD" in df.columns:
            annees = df["TIME_PERIOD"].astype(str)
            print(
                "Périodes contenant 2022 :",
                sorted(annees[annees.str.contains("2022")].unique())
            )

    except Exception as erreur:
        print("Erreur :", erreur)
        print("Vérifier le jeu de données et sa disponibilité.")
