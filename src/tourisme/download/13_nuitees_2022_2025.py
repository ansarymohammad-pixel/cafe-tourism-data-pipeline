
from pathlib import Path
import argparse
import pandas as pd


# ============================================================
# PROJET CAFÉ - PRÉPARATION DES NUITÉES MARCHANDES INSEE
# Années : 2022, 2023, 2024, 2025
# Source : INSEE - DS_TOUR_FREQ
#
# Périmètre : France métropolitaine
# Niveaux : 96 départements, 13 régions, France métropolitaine
#
# ATTENTION :
# Les nuitées de camping correspondent à HIGH_SEASON.
# Elles ne représentent pas nécessairement l'année complète.
# ============================================================


# 1. CONFIGURATION DES CHEMINS

ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data" / "raw" / "tourisme"
    / "frequentation_brut.csv"
)

SORTIE = ROOT / "data" / "processed" / "tourisme"

YEARS = (2022, 2023, 2024, 2025)


# 2. CONFIGURATION DES CATÉGORIES

CATEGORIES = {
    "I551": ("Hotels", "FULL_YEAR"),
    "I553": ("Campings", "HIGH_SEASON"),
    "I552": ("Autres", "FULL_YEAR"),
}

COLONNES_OBLIGATOIRES = {
    "TIME_PERIOD",
    "FREQ",
    "TOUR_MEASURE",
    "UNIT_MEASURE",
    "TOUR_RESID",
    "UNIT_LOC_RANKING",
    "HOTEL_STA",
    "EQUIP",
    "ACTIVITY",
    "SEASONALITY",
    "OBS_VALUE_NIVEAU",
    "UNIT_MULT",
    "OBS_STATUS",
    "GEO",
}


# 3. RÉFÉRENTIEL GÉOGRAPHIQUE MÉTROPOLITAIN

# Codes des 13 régions métropolitaines
REGIONS_METRO = {
    "11", "24", "27", "28", "32",
    "44", "52", "53", "75", "76",
    "84", "93", "94",
}

# Départements métropolitains :
# 01 à 95, sauf 20, remplacé par 2A et 2B.
DEPARTEMENTS_METRO = (
    {f"{i:02d}" for i in range(1, 96) if i != 20}
    | {"2A", "2B"}
)


# 4. LECTURE DES ARGUMENTS

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Préparation des nuitées marchandes "
            "INSEE pour le projet CAFÉ"
        )
    )

    parser.add_argument(
        "--year",
        type=int,
        choices=YEARS,
        help="Année à traiter (sinon toutes les années)",
    )

    return parser.parse_args()


# 5. CHARGEMENT DES DONNÉES BRUTES

def charger_donnees():
    print("\n=== CHARGEMENT DES DONNÉES INSEE ===")
    print("Source :", SOURCE)

    if not SOURCE.is_file():
        raise FileNotFoundError(
            f"Fichier introuvable : {SOURCE}\n"
            "Exécuter d'abord le script 09."
        )

    df = pd.read_csv(
        SOURCE,
        dtype={
            "GEO": str,
            "TIME_PERIOD": str,
            "OBS_STATUS": str,
        },
        low_memory=False,
    )

    colonnes_manquantes = (
        COLONNES_OBLIGATOIRES - set(df.columns)
    )

    if colonnes_manquantes:
        raise ValueError(
            "Colonnes manquantes : "
            + ", ".join(sorted(colonnes_manquantes))
        )

    print("Nombre de lignes brutes :", len(df))

    return df


# 6. FILTRAGE DES NUITÉES

def filtrer_nuitees(df, year):
    print(f"\n=== FILTRAGE DES NUITÉES {year} ===")

    base = df[
        (df["TIME_PERIOD"] == str(year))
        & (df["FREQ"] == "A")
        & (df["TOUR_MEASURE"] == "NIGHT_SPENT")
        & (df["UNIT_MEASURE"] == "NR")
        & (df["TOUR_RESID"] == "_T")
        & (df["UNIT_LOC_RANKING"] == "_T")
        & (df["HOTEL_STA"] == "_T")
        & (df["EQUIP"] == "_Z")
    ].copy()

    resultats = []

    for code, (nom, saison) in CATEGORIES.items():
        partie = base[
            (base["ACTIVITY"] == code)
            & (base["SEASONALITY"] == saison)
        ].copy()

        partie["categorie"] = nom
        resultats.append(partie)

        print(
            f"{nom} : {len(partie)} observations brutes"
        )

    nuites = pd.concat(
        resultats,
        ignore_index=True,
    )

    if nuites.empty:
        raise ValueError(
            f"Aucune nuitée trouvée pour {year}. "
            "Vérifier les filtres INSEE."
        )

    return nuites


# 7. CONVERSION DES UNITÉS

def convertir_unites(nuites):
    nuites = nuites.copy()

    valeurs = pd.to_numeric(
        nuites["OBS_VALUE_NIVEAU"],
        errors="coerce",
    )

    multiplicateurs = pd.to_numeric(
        nuites["UNIT_MULT"],
        errors="coerce",
    )

    # OBS_VALUE_NIVEAU × 10^UNIT_MULT
    nuites["nuites"] = (
        valeurs * (10.0 ** multiplicateurs)
    )

    print(
        "Valeurs de nuitées manquantes :",
        nuites["nuites"].isna().sum(),
    )

    return nuites


# 8. IDENTIFICATION DU NIVEAU GÉOGRAPHIQUE

def niveau_geo(geo):
    geo = str(geo)

    if "-DEP-" in geo:
        return "DEP"

    if "-REG-" in geo:
        return "REG"

    if geo.endswith("-FRANCE-FM"):
        return "FRANCE_METRO"

    return "AUTRE"


# 9. FILTRAGE FRANCE MÉTROPOLITAINE

def filtrer_metropole(nuites):
    print("\n=== FILTRAGE GÉOGRAPHIQUE ===")

    nuites = nuites.copy()

    # Extraire le code département ou région
    nuites["code_dep"] = nuites["GEO"].str.extract(
        r"^\d{4}-DEP-(.+)$",
        expand=False,
    )

    nuites["code_reg"] = nuites["GEO"].str.extract(
        r"^\d{4}-REG-(.+)$",
        expand=False,
    )

    # Sélection des départements métropolitains
    masque_dep = nuites["code_dep"].isin(
        DEPARTEMENTS_METRO
    )

    # Sélection des régions métropolitaines
    masque_reg = nuites["code_reg"].isin(
        REGIONS_METRO
    )

    # Total France métropolitaine
    masque_france = nuites["GEO"].str.fullmatch(
        r"\d{4}-FRANCE-FM",
        na=False,
    )

    # Conserver uniquement le périmètre souhaité
    masque_metropole = (
        masque_dep | masque_reg | masque_france
    )

    exclues = nuites.loc[
        ~masque_metropole
    ].copy()

    nuites = nuites.loc[
        masque_metropole
    ].copy()

    nuites["niveau"] = (
        nuites["GEO"].apply(niveau_geo)
    )

    print(
        "Observations exclues :",
        len(exclues),
    )

    print(
        "Géographies exclues :",
        sorted(exclues["GEO"].dropna().unique()),
    )

    print(
        "\nTerritoires conservés :"
    )

    for niveau in ["DEP", "REG", "FRANCE_METRO"]:
        codes = nuites.loc[
            nuites["niveau"] == niveau, "GEO"
        ].nunique()

        print(f"  {niveau} : {codes}")

    # Contrôle du référentiel
    nb_dep = nuites.loc[
        nuites["niveau"] == "DEP", "GEO"
    ].nunique()

    nb_reg = nuites.loc[
        nuites["niveau"] == "REG", "GEO"
    ].nunique()

    nb_france = nuites.loc[
        nuites["niveau"] == "FRANCE_METRO", "GEO"
    ].nunique()

    if (nb_dep, nb_reg, nb_france) != (96, 13, 1):
        raise ValueError(
            "Périmètre géographique inattendu : "
            f"{nb_dep} DEP, {nb_reg} REG, "
            f"{nb_france} FRANCE_METRO."
        )

    return nuites


# 10. CONTRÔLE DES VALEURS MANQUANTES

def verifier_valeurs_manquantes(nuites):
    print("\n=== CONTRÔLE DES VALEURS MANQUANTES ===")

    manquantes = nuites[
        nuites["nuites"].isna()
    ]

    if manquantes.empty:
        print("Aucune valeur manquante.")
    else:
        print(
            manquantes[
                [
                    "GEO",
                    "categorie",
                    "OBS_STATUS",
                ]
            ].to_string(index=False)
        )

    print(
        "Total de valeurs manquantes :",
        len(manquantes),
    )


# 11. CONSTRUCTION DU TABLEAU FINAL

def construire_tableau(nuites, year):
    print("\n=== CONSTRUCTION DU TABLEAU ===")

    nuites = nuites.copy()

    # Vérification des doublons
    cles = ["GEO", "categorie"]

    doublons = nuites[
        nuites.duplicated(cles, keep=False)
    ]

    if not doublons.empty:
        print(
            doublons[
                cles + ["TIME_PERIOD", "nuites"]
            ].head(20).to_string(index=False)
        )

        raise ValueError(
            "Doublons détectés : vérifier "
            "les dimensions INSEE."
        )

    # Passage du format long au format large
    tableau = nuites.pivot(
        index=["niveau", "GEO"],
        columns="categorie",
        values="nuites",
    ).reset_index()

    tableau.columns.name = None

    # Garantir les 3 colonnes
    for col in ["Hotels", "Campings", "Autres"]:
        if col not in tableau.columns:
            tableau[col] = float("nan")

    # Somme uniquement si les 3 catégories sont présentes
    tableau["Total"] = tableau[
        ["Hotels", "Campings", "Autres"]
    ].sum(axis=1, min_count=3)

    tableau.insert(0, "annee", year)

    tableau = tableau[
        [
            "annee",
            "niveau",
            "GEO",
            "Hotels",
            "Campings",
            "Autres",
            "Total",
        ]
    ]

    # Organiser les niveaux et les géographies
    ordre = {
        "COM": 0,
        "DEP": 1,
        "REG": 2,
        "FRANCE_METRO": 3,
    }

    tableau["_ordre"] = tableau[
        "niveau"
    ].map(ordre)

    tableau = (
        tableau.sort_values(
            ["_ordre", "GEO"]
        )
        .drop(columns="_ordre")
        .reset_index(drop=True)
    )

    print("\nLignes par niveau géographique :")
    print(tableau["niveau"].value_counts())

    print("\nValeurs manquantes par catégorie :")
    print(
        tableau[
            ["Hotels", "Campings", "Autres", "Total"]
        ].isna().sum()
    )

    return tableau


# 12. EXPORT CSV

def exporter_tableau(tableau, year):
    dossier_annee = SORTIE / str(year)

    dossier_annee.mkdir(
        parents=True,
        exist_ok=True,
    )

    fichier_sortie = (
        dossier_annee / f"nuites_{year}.csv"
    )

    tableau.to_csv(
        fichier_sortie,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nFichier créé :", fichier_sortie)


# 13. FONCTION PRINCIPALE

def main():
    args = parse_arguments()

    df = charger_donnees()

    annees = (
        [args.year]
        if args.year is not None
        else YEARS
    )

    for year in annees:
        nuites = filtrer_nuitees(df, year)

        nuites = convertir_unites(nuites)

        nuites = filtrer_metropole(nuites)

        verifier_valeurs_manquantes(nuites)

        tableau = construire_tableau(
            nuites,
            year,
        )

        exporter_tableau(
            tableau,
            year,
        )

        print(
            f"\n[OK] Année {year} terminée."
        )

    print("\n=== TRAITEMENT CAFÉ TERMINÉ ===")


if __name__ == "__main__":
    main()
