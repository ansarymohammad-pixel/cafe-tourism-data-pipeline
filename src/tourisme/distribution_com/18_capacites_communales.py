
from pathlib import Path
import argparse
import csv
import re
import pandas as pd


# ============================================================
# PROJET CAFÉ - CAPACITÉS TOURISTIQUES COMMUNALES
# Années : 2022, 2023, 2024, 2025
# Source : INSEE - Capacités touristiques
# Périmètre : France métropolitaine
#
# Fonction :
# Préparer les capacités communales pour la répartition
# statistique des nuitées dans le script 20.
#
# Formats acceptés :
# - INSEE historique : HTCH22, CPGE22, VVLIT22, etc.
# - INSEE Melodi : GEO, ACTIVITY, OBS_VALUE
# - INSEE Melodi : GEO, ACTIVITY, OBS_VALUE_NIVEAU
# ============================================================


# 1. CONFIGURATION

ROOT = Path(__file__).resolve().parents[3]

RAW = ROOT / "data" / "raw" / "tourisme"
PROCESSED = ROOT / "data" / "processed" / "tourisme"

YEARS = (2022, 2023, 2024, 2025)

SOURCES = {
    year: RAW / f"capacites_{year}.csv"
    for year in YEARS
}

ACTIVITES = {
    "I551": "capacite_hotels",
    "I553": "capacite_campings",
    "I552": "capacite_autres",
}

COLONNES_CAPACITE = list(ACTIVITES.values())

DEPARTEMENTS_METRO = (
    {f"{i:02d}" for i in range(1, 96) if i != 20}
    | {"2A", "2B"}
)


# 2. ARGUMENTS DU TERMINAL

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Capacités communales CAFÉ 2022-2025"
    )

    parser.add_argument(
        "--year",
        type=int,
        choices=YEARS,
        help="Année à traiter ; par défaut toutes les années",
    )

    return parser.parse_args()


# 3. CHARGEMENT DES SOURCES

def charger_donnees(year):
    path = SOURCES[year]

    print(f"\n=== CAPACITÉS {year} ===")
    print("Source :", path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier introuvable : {path}"
        )

    # Détection simple du séparateur
    with open(
        path,
        "r",
        encoding="utf-8-sig",
    ) as f:
        entete = f.readline()

    try:
        sep = csv.Sniffer().sniff(
            entete,
            delimiters=",;\t",
        ).delimiter
    except csv.Error:
        sep = ";" if entete.count(";") > entete.count(",") else ","

    df = pd.read_csv(
        path,
        sep=sep,
        dtype=str,
        encoding="utf-8-sig",
        low_memory=False,
    )

    df.columns = [
        str(col).strip().upper()
        for col in df.columns
    ]

    print("Lignes brutes :", len(df))
    print("Colonnes :", df.columns.tolist())

    return df


# 4. IDENTIFICATION DES COMMUNES

def extraire_commune(value):
    if pd.isna(value):
        return None

    code = str(value).strip().upper()

    # Exemples :
    # 2024-COM-75056 -> 75056
    # COM-75056 -> 75056
    # 75056 -> 75056

    if "-COM-" in code:
        code = code.rsplit("-COM-", 1)[-1]

    elif code.startswith("COM-"):
        code = code[4:]

    if re.fullmatch(
        r"(?:\d{5}|2[AB]\d{3})",
        code,
    ):
        return code

    return None


def obtenir_departement(code):
    if code is None or pd.isna(code):
        return None

    code = str(code)

    if code.startswith(("2A", "2B")):
        return code[:2]

    if code.startswith(("97", "98")):
        return code[:3]

    return code[:2]


def filtrer_metropole(df):
    df = df.copy()

    df["code_departement"] = (
        df["code_commune"].apply(obtenir_departement)
    )

    return df.loc[
        df["code_departement"].isin(DEPARTEMENTS_METRO)
    ].copy()


# 5. CONVERSION NUMÉRIQUE

def convertir_nombre(serie):
    valeurs = (
        serie.astype("string")
        .str.strip()
        .str.replace("\u00a0", "", regex=False)
        .str.replace("\u202f", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(
        valeurs,
        errors="coerce",
    ).astype("float64")


# 6. TRAITEMENT DES SOURCES MELODI

def preparer_melodi(df, year):
    """Prépare 2024/2025 : catégories, unités et séjour sans double comptage."""
    print("\nFormat détecté : MELODI")
    data = df.copy()
    if "OBS_VALUE_NIVEAU" not in data.columns and "OBS_VALUE" in data.columns:
        data = data.rename(columns={"OBS_VALUE": "OBS_VALUE_NIVEAU"})

    requis = {"GEO", "GEO_OBJECT", "TIME_PERIOD", "ACTIVITY", "TOUR_MEASURE",
              "UNIT_LOC_RANKING", "L_STAY", "OBS_VALUE_NIVEAU"}
    absents = requis - set(data.columns)
    if absents:
        raise ValueError(f"Colonnes Melodi absentes : {sorted(absents)}")

    for col in requis - {"OBS_VALUE_NIVEAU"}:
        data[col] = data[col].astype("string").str.strip().str.upper()

    masque = (
        data["TIME_PERIOD"].eq(str(year))
        & data["GEO_OBJECT"].eq("COM")
        & data["UNIT_LOC_RANKING"].eq("_T")
        & data["ACTIVITY"].isin(["I551", "I553", "I552"])
    ).fillna(False)
    if "FREQ" in data.columns:
        masque &= data["FREQ"].astype("string").str.strip().str.upper().eq("A").fillna(False)
    data = data.loc[masque].copy()
    data["code_commune"] = data["GEO"].apply(extraire_commune)
    data = filtrer_metropole(data.loc[data["code_commune"].notna()].copy())
    if data.empty:
        raise ValueError(f"Aucune observation communale métropolitaine pour {year}")

    data["capacite"] = convertir_nombre(data["OBS_VALUE_NIVEAU"])
    if (data["capacite"] < 0).any():
        raise ValueError("Capacités négatives INSEE")

    # I551/PLACE = chambres ; I553/PLACE = emplacements ;
    # I552/BEDPLACE = lits. Ne pas additionner I552 et I552A/B/C.
    specifications = {
        "I551": ("capacite_hotels", "PLACE", "chambres"),
        "I553": ("capacite_campings", "PLACE", "emplacements"),
        "I552": ("capacite_autres", "BEDPLACE", "lits"),
    }
    tables = []
    unites = {}

    for activite, (colonne, mesure, unite) in specifications.items():
        subset = data.loc[
            data["ACTIVITY"].eq(activite)
            & data["TOUR_MEASURE"].eq(mesure)
        ].copy()
        if subset.empty:
            raise ValueError(f"{year}: aucune observation {activite}/{mesure}")

        # Hôtels et autres : généralement L_STAY = _T.
        # Campings : deux composantes LONG et SHORT ;
        # les sommer UNIQUEMENT s'il n'existe pas déjà un total _T.
        sejours = set(subset["L_STAY"].dropna().unique())
        if "_T" in sejours:
            subset = subset.loc[subset["L_STAY"].eq("_T")].copy()
        elif activite == "I553" and {"LONG", "SHORT"}.issubset(sejours):
            subset = subset.loc[subset["L_STAY"].isin(["LONG", "SHORT"])].copy()
        else:
            raise ValueError(
                f"{year} {activite}/{mesure}: valeurs L_STAY non prises en charge : {sorted(sejours)}"
            )

        # Une seule valeur par commune et par sous-catégorie de séjour.
        cles = ["code_commune", "L_STAY"]
        if subset.duplicated(cles).any():
            raise ValueError(f"{year}: doublons après sélection pour {activite}/{mesure}")

        if activite == "I553" and "_T" not in sejours:
            # Le total camping doit réunir LONG et SHORT pour chaque commune.
            comptes = subset.groupby("code_commune")["L_STAY"].nunique()
            if not comptes.eq(2).all():
                raise ValueError(f"{year}: campings LONG/SHORT incomplets pour certaines communes")
            serie = subset.groupby("code_commune")["capacite"].sum(min_count=2)
        else:
            serie = subset.set_index("code_commune")["capacite"]

        print(f"  {activite}/{mesure} : {len(serie):,} communes ; unité {unite}")
        tables.append(serie.rename(colonne))
        unites[{"I551": "unite_hotels", "I553": "unite_campings", "I552": "unite_autres"}[activite]] = unite

    tableau = pd.concat(tables, axis=1).reset_index()
    tableau["millesime_geo"] = "NON_PRECISE_DANS_GEO"
    return tableau, unites, "MELODI"


# 7. IDENTIFICATION DES COLONNES HISTORIQUES

def trouver_colonne(df, prefix, year):
    suffixe = str(year)[-2:]

    candidats = [
        f"{prefix}{suffixe}",
        prefix,
    ]

    for col in candidats:
        if col in df.columns:
            return col

    raise ValueError(
        f"Colonne historique absente pour {prefix}, "
        f"année {year}. Colonnes recherchées : {candidats}"
    )


# 8. TRAITEMENT DES SOURCES HISTORIQUES

def preparer_historique(df, year):
    print("\nFormat détecté : HISTORIQUE")

    geo = next(
        (
            col for col in
            ["CODGEO", "GEO", "CODE_COMMUNE"]
            if col in df.columns
        ),
        None,
    )

    if geo is None:
        raise ValueError(
            "Colonne géographique absente."
        )

    hotel = trouver_colonne(df, "HTCH", year)
    camping = trouver_colonne(df, "CPGE", year)

    autres = [
        trouver_colonne(df, "VVLIT", year),
        trouver_colonne(df, "RTLIT", year),
        trouver_colonne(df, "AJCSLIT", year),
    ]

    tableau = pd.DataFrame(
        index=df.index
    )

    tableau["code_commune"] = (
        df[geo].apply(extraire_commune)
    )

    tableau["capacite_hotels"] = (
        convertir_nombre(df[hotel])
    )

    tableau["capacite_campings"] = (
        convertir_nombre(df[camping])
    )

    valeurs_autres = pd.DataFrame(
        {
            col: convertir_nombre(df[col])
            for col in autres
        },
        index=df.index,
    )

    # Conserver NaN si toutes les composantes sont absentes.
    # Une somme partielle reste identifiable comme telle.
    tableau["capacite_autres"] = (
        valeurs_autres.sum(
            axis=1,
            min_count=3,
        )
    )

    tableau = filtrer_metropole(tableau)

    if tableau.empty:
        raise ValueError(
            f"Aucune commune métropolitaine pour {year}."
        )

    if tableau["code_commune"].duplicated().any():
        raise ValueError(
            "Doublons de communes dans la source historique."
        )

    unites = {
        "unite_hotels": "chambres",
        "unite_campings": "emplacements",
        "unite_autres": "lits",
    }

    return tableau, unites, "HISTORIQUE"


# 9. HARMONISATION

def construire_tableau(df, year):
    print("\n=== HARMONISATION ===")

    # Déterminer automatiquement le format INSEE
    if {
        "ACTIVITY",
        "TOUR_MEASURE",
        "TIME_PERIOD",
    }.issubset(df.columns):

        tableau, unites, format_source = (
            preparer_melodi(df, year)
        )

    else:
        tableau, unites, format_source = (
            preparer_historique(df, year)
        )

    tableau = tableau.copy()

    tableau["code_departement"] = (
        tableau["code_commune"].apply(obtenir_departement)
    )

    tableau.insert(
        0,
        "annee_capacite",
        year,
    )

    tableau["format_source"] = format_source
    if "millesime_geo" not in tableau.columns:
        tableau["millesime_geo"] = str(year)

    for col, unite in unites.items():
        tableau[col] = unite

    colonnes_finales = [
        "annee_capacite",
        "code_commune",
        "code_departement",
        "capacite_hotels",
        "capacite_campings",
        "capacite_autres",
        "unite_hotels",
        "unite_campings",
        "unite_autres",
        "format_source",
        "millesime_geo",
    ]

    tableau = tableau[
        colonnes_finales
    ].sort_values(
        "code_commune"
    ).reset_index(drop=True)

    return tableau


# 10. CONTRÔLES DE QUALITÉ

def verifier_tableau(tableau, year):
    print(f"\n=== CONTRÔLES {year} ===")

    print(
        "Nombre de communes :",
        len(tableau)
    )

    print(
        "Nombre de départements :",
        tableau["code_departement"].nunique()
    )

    if tableau["code_commune"].isna().any():
        raise ValueError(
            "Codes communaux manquants."
        )

    if tableau["code_commune"].duplicated().any():
        raise ValueError(
            "Codes communaux en double."
        )

    if not tableau["code_departement"].isin(
        DEPARTEMENTS_METRO
    ).all():
        raise ValueError(
            "Territoires hors métropole détectés."
        )

    print("\nCapacités :")

    for col in COLONNES_CAPACITE:
        valeurs = tableau[col]

        print(
            f"{col} : "
            f"{valeurs.notna().sum()} disponibles, "
            f"{valeurs.isna().sum()} manquantes"
        )

        if (valeurs < 0).any():
            raise ValueError(
                f"Capacités négatives dans {col}."
            )

    print("\nUnités :")
    print(
        tableau[
            ["unite_hotels", "unite_campings", "unite_autres"]
        ].iloc[0].to_dict()
    )

    print("\nTotaux par catégorie :")
    print(
        tableau[
            COLONNES_CAPACITE
        ].sum(min_count=1)
    )


# 11. EXPORT CSV

def exporter(tableau, year):
    dossier = PROCESSED / str(year)

    dossier.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        dossier
        / f"capacites_communales_{year}.csv"
    )

    tableau.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nFichier créé :", path)


# 12. FONCTION PRINCIPALE

def main():
    args = parse_arguments()

    annees = (
        [args.year]
        if args.year is not None
        else YEARS
    )

    # Vérifier la présence des sources historiques
    absentes = [
        year for year in annees
        if not SOURCES[year].is_file()
    ]

    if absentes:
        raise FileNotFoundError(
            "Sources historiques manquantes : "
            + ", ".join(map(str, absentes))
            + "\nDossier attendu : " + str(RAW)
        )

    for year in annees:
        df = charger_donnees(year)

        tableau = construire_tableau(
            df,
            year,
        )

        verifier_tableau(
            tableau,
            year,
        )

        exporter(
            tableau,
            year,
        )

        print(
            f"\n[OK] Année {year} terminée."
        )

    print("\n=== CAPACITÉS CAFÉ TERMINÉES ===")


if __name__ == "__main__":
    main()
