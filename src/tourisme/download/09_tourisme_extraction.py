
from pathlib import Path
import argparse
import pandas as pd
from pynsee.melodi import get_dataset

# Racine du projet CAFÉ
ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "tourisme"

DATASETS = {
    "frequentation": "DS_TOUR_FREQ",
    "capacite": "DS_TOUR_CAP",
    "tourisme_national": "DS_SUIVI_DDE_TOUR",
}

YEARS = ("2022", "2023", "2024", "2025")



def inspect_years(path):
    columns = pd.read_csv(path, nrows=0).columns.tolist()

    print("Colonnes :", columns)

    if "TIME_PERIOD" not in columns:
        print("Colonne TIME_PERIOD absente.")
        return

    counts = {}

    for chunk in pd.read_csv(
        path,
        usecols=["TIME_PERIOD"],
        dtype=str,
        chunksize=100_000,
    ):
        periods = chunk["TIME_PERIOD"].dropna()

        years = periods.str[:4]
        chunk_counts = years.value_counts()

        for year, count in chunk_counts.items():
            counts[year] = counts.get(year, 0) + int(count)

    print("\nAnnées disponibles dans le dataset :")

    for year, count in sorted(counts.items()):
        print(f"  {year} : {count:,} lignes")

    print("\nVérification du périmètre CAFÉ :")

    for year in YEARS:
        count = counts.get(year, 0)

        if count > 0:
            print(f"  [OK] {year} : {count:,} lignes")
        else:
            print(f"  [ABSENT] {year}")



def download_dataset(name, identifier, force=False):
    path = RAW / f"{name}_brut.csv"

    print(f"\n=== {identifier} ===")

    if path.exists() and not force:
        print(f"Fichier existant conservé : {path}")
    else:
        print(f"Téléchargement INSEE : {identifier}")

        df = get_dataset(identifier)

        if df.empty:
            raise ValueError(
                f"Le dataset {identifier} est vide."
            )

        print("Dimensions :", df.shape)

        # Enregistrer seulement après un téléchargement réussi
        temp = path.with_suffix(".csv.tmp")
        df.to_csv(temp, index=False, encoding="utf-8")
        temp.replace(path)

        print(f"Enregistré : {path}")

    inspect_years(path)


def main():
    parser = argparse.ArgumentParser(
        description="Extraction des sources INSEE pour CAFÉ"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Télécharger à nouveau les datasets",
    )

    parser.add_argument(
        "--dataset",
        choices=list(DATASETS) + ["all"],
        default="all",
        help="Choisir la source INSEE",
    )

    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)

    selected = (
        DATASETS
        if args.dataset == "all"
        else {args.dataset: DATASETS[args.dataset]}
    )

    for name, identifier in selected.items():
        download_dataset(name, identifier, force=args.force)


if __name__ == "__main__":
    main()
