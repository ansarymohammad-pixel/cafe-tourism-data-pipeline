from pathlib import Path
import argparse
import pandas as pd

# CAFÉ - 46 : EXTRACTION DES NUITEES NON MARCHANDES INSEE (2022-2025)
# Source : DS_SUIVI_DDE_TOUR telechargee par le script 09.
# Les totaux TRAVEL_DEST=_T sont toutes destinations confondues.
# Ces totaux NE SONT PAS autorises pour allocation aux communes de France.

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "tourisme"
OUT = ROOT / "data" / "processed" / "tourisme"
YEARS = (2022, 2023, 2024, 2025)
CATEGORIES = {
    "FRIENDS_FAMILY": "famille_amis",
    "SECOND_HOME": "residences_secondaires",
}

def charger():
    paths = [
        RAW / "tourisme_national_brut.csv",
        RAW / "DS_SUIVI_DDE_TOUR.csv",
    ]
    source = next((p for p in paths if p.is_file()), None)
    if source is None:
        raise FileNotFoundError(f"DS_SUIVI_DDE_TOUR absent de {RAW}")
    with source.open("r", encoding="utf-8-sig") as f:
        entete = f.readline()
    sep = ";" if entete.count(";") > entete.count(",") else ","
    df = pd.read_csv(source, sep=sep, dtype=str, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.upper()
    must = {
        "TIME_PERIOD", "FREQ", "TOUR_MEASURE",
        "TYPE_TOUR_ACCOMODATION", "OBS_VALUE_NIVEAU",
        "UNIT_MULT", "UNIT_MEASURE", "OBS_STATUS", "TRAVEL_DEST", "GEO"
    }
    missing = must - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans {source}: {sorted(missing)}")
    print(f"Source : {source} | {len(df)} observations")
    return df

def traiter(df, year):
    selection = (
        df["TIME_PERIOD"].eq(str(year))
        & df["FREQ"].eq("A")
        & df["TOUR_MEASURE"].eq("NIGHT_SPENT")
        & df["TYPE_TOUR_ACCOMODATION"].isin(CATEGORIES)
        & df["UNIT_MEASURE"].eq("NR")
        & df["OBS_STATUS"].eq("A")
    )
    d = df.loc[selection].copy()
    d["categorie"] = d["TYPE_TOUR_ACCOMODATION"].map(CATEGORIES)

    # 1 seule observation par categorie est attendue.
    # Ne jamais sommer d'autres dimensions sans verifier leur compatibilite.
    counts = d.groupby("categorie").size()
    if set(counts.index) != set(CATEGORIES.values()) or (counts != 1).any():
        raise ValueError(
            f"Annee {year} : il faut une unique observation par categorie. "
            f"Trouve : {counts.to_dict()}. "
            "Examiner TRAVEL_DEST, GEO et autres dimensions avant selection."
        )

    nombres = pd.to_numeric(
        d["OBS_VALUE_NIVEAU"].str.replace(",", ".", regex=False),
        errors="coerce"
    )
    puissances = pd.to_numeric(d["UNIT_MULT"], errors="coerce")
    if nombres.isna().any() or puissances.isna().any():
        raise ValueError(f"Valeur ou unite non numerique pour {year}")
    d["nuites"] = nombres * (10.0 ** puissances)
    if d["nuites"].isna().any() or (d["nuites"] < 0).any():
        raise ValueError(f"Nuitees invalides pour {year}")

    # Garder les metadonnees qui determinent le perimetre :
    # GEO=2025-FRANCE-FM designe la population de reference.
    # TRAVEL_DEST=_T regroupe toutes les destinations.
    d["annee"] = year
    d["perimetre_a_valider"] = True
    d["allocation_communale_autorisee"] = False
    d["avertissement"] = (
        "TRAVEL_DEST=_T : toutes destinations; "
        "ne pas repartir sur les communes metropolitaines sans validation"
    )
    folder = OUT / str(year)
    folder.mkdir(parents=True, exist_ok=True)
    detail = folder / f"nuites_non_marchandes_observations_{year}.csv"
    d.to_csv(detail, index=False, encoding="utf-8-sig")
    summary = d[[
        "annee", "categorie", "nuites", "GEO", "TRAVEL_DEST",
        "perimetre_a_valider", "allocation_communale_autorisee",
        "avertissement"
    ]].sort_values("categorie")
    result = folder / f"nuites_non_marchandes_{year}.csv"
    summary.to_csv(result, index=False, encoding="utf-8-sig")
    print(f"\n{year} :")
    print(summary[["categorie", "nuites", "TRAVEL_DEST"]].to_string(index=False))
    print(f"Fichier : {result}")
    print("ATTENTION : totaux non valides pour une allocation geographique.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, choices=YEARS)
    args = parser.parse_args()
    df = charger()
    years = [args.year] if args.year else YEARS
    for year in years:
        traiter(df, year)
    print("\nScript 46 termine. Ne pas lancer la repartition 49 sans "
          "totaux de destination metropolitaine valides.")

if __name__ == "__main__":
    main()
