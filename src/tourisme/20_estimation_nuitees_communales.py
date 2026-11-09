
from pathlib import Path
import pandas as pd
import geopandas as gpd

# ============================================================
# PROJET CAFÉ - ESTIMATION DES NUITÉES COMMUNALES
#
# Nuitées : INSEE DS_TOUR_FREQ, 2022
# Capacités : INSEE DS_TOUR_CAP, 2026
# Géographie de référence : ADMIN EXPRESS COG CARTO 2022
#
# IMPORTANT :
# Estimation expérimentale, non observation directe.
# Campings : haute saison uniquement.
# ============================================================

BASE = Path(__file__).resolve().parent

DOSSIER = BASE / "data/processed/tourisme"
ADMIN = BASE / "data/raw/administratif"

F_NUITEES = DOSSIER / "nuites_2022.csv"
F_CAPACITES = DOSSIER / "capacites_communales_2026.csv"

SORTIE = DOSSIER / "estimations_communales"
SORTIE.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. LECTURE
# ------------------------------------------------------------

nuites = pd.read_csv(
    F_NUITEES,
    dtype={"GEO": str}
)

capacites = pd.read_csv(
    F_CAPACITES,
    dtype={
        "GEO": str,
        "code_commune": str,
        "code_departement": str
    }
)

print("=== DONNEES CHARGEES ===")
print("Nuitées :", len(nuites))
print("Communes avec capacités :", len(capacites))

# ------------------------------------------------------------
# 2. FRONTIERES ADMINISTRATIVES 2022
# ------------------------------------------------------------

communes_2022 = gpd.read_file(
    ADMIN / "COMMUNE.shp",
    ignore_geometry=True
)

departements_2022 = gpd.read_file(
    ADMIN / "DEPARTEMENT.shp",
    ignore_geometry=True
)

print("\nColonnes COMMUNE :", communes_2022.columns.tolist())
print("Colonnes DEPARTEMENT :", departements_2022.columns.tolist())

# Identifier les colonnes attendues
if "INSEE_COM" not in communes_2022.columns:
    raise ValueError(
        "Colonne INSEE_COM absente de COMMUNE.shp"
    )

if "INSEE_DEP" not in departements_2022.columns:
    raise ValueError(
        "Colonne INSEE_DEP absente de DEPARTEMENT.shp"
    )

# Associer les départements aux régions.
# Dans ADMIN EXPRESS, INSEE_REG est normalement disponible
# dans la couche DEPARTEMENT.
if "INSEE_REG" not in departements_2022.columns:
    raise ValueError(
        "Colonne INSEE_REG absente de DEPARTEMENT.shp"
    )

dep_reg = (
    departements_2022[
        ["INSEE_DEP", "INSEE_REG"]
    ]
    .drop_duplicates()
    .rename(columns={
        "INSEE_DEP": "code_departement",
        "INSEE_REG": "code_region"
    })
)

dep_reg["code_departement"] = (
    dep_reg["code_departement"].astype(str)
)
dep_reg["code_region"] = (
    dep_reg["code_region"].astype(str)
)

# ------------------------------------------------------------
# 3. JOINTURE COMMUNES / REGIONS
# ------------------------------------------------------------

capacites["code_commune"] = (
    capacites["code_commune"].astype(str)
)

capacites["code_departement"] = (
    capacites["code_departement"].astype(str)
)

# Vérifier les communes présentes dans la géographie 2022
codes_2022 = set(
    communes_2022["INSEE_COM"].astype(str)
)

capacites["commune_existe_2022"] = (
    capacites["code_commune"].isin(codes_2022)
)

# On ne réaffecte pas automatiquement les communes fusionnées.
# Les communes non concordantes seront exclues de l'estimation.
exclues = capacites[
    ~capacites["commune_existe_2022"]
].copy()

exclues.to_csv(
    SORTIE / "communes_non_concordantes_2022_2026.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nCommunes sans correspondance 2022 :", len(exclues))

communes = capacites[
    capacites["commune_existe_2022"]
].copy()

communes = communes.merge(
    dep_reg,
    on="code_departement",
    how="left",
    validate="many_to_one"
)

print(
    "Communes sans région :",
    communes["code_region"].isna().sum()
)

# ------------------------------------------------------------
# 4. PREPARATION DES NUITEES
# ------------------------------------------------------------

nuites["code_territoire"] = (
    nuites["GEO"].str.split("-").str[-1]
)

departement_nuites = nuites[
    nuites["niveau"] == "Département"
][
    ["code_territoire", "Hotels", "Campings"]
].rename(columns={
    "code_territoire": "code_departement",
    "Hotels": "nuites_dep_hotels",
    "Campings": "nuites_dep_campings"
})

region_nuites = nuites[
    nuites["niveau"] == "Région"
][
    ["code_territoire", "Autres"]
].rename(columns={
    "code_territoire": "code_region",
    "Autres": "nuites_reg_autres"
})

communes = communes.merge(
    departement_nuites,
    on="code_departement",
    how="left",
    validate="many_to_one"
)

communes = communes.merge(
    region_nuites,
    on="code_region",
    how="left",
    validate="many_to_one"
)

# ------------------------------------------------------------
# 5. FONCTION DE REPARTITION
# ------------------------------------------------------------

def repartir_nuitees(
    df,
    groupe,
    colonne_capacite,
    colonne_nuitees,
    colonne_resultat
):
    """
    Répartit les nuitées selon la capacité communale.

    Ne calcule pas d'estimation si :
    - le total de capacités est nul ou manquant ;
    - la valeur de nuitées est manquante ;
    - certaines capacités du groupe sont manquantes.
    """

    capacite = pd.to_numeric(
        df[colonne_capacite],
        errors="coerce"
    )

    n = pd.to_numeric(
        df[colonne_nuitees],
        errors="coerce"
    )

    somme = capacite.groupby(
        df[groupe]
    ).transform("sum")

    nb_manquants = capacite.isna().groupby(
        df[groupe]
    ).transform("sum")

    # Calcul uniquement lorsque le groupe est exploitable
    valide = (
        (somme > 0)
        & (nb_manquants == 0)
        & capacite.ge(0)
        & n.notna()
    )

    df[colonne_resultat] = float("nan")

    df.loc[valide, colonne_resultat] = (
        n[valide]
        * capacite[valide]
        / somme[valide]
    )

    return df

# ------------------------------------------------------------
# 6. HOTELS : DEPARTEMENT -> COMMUNES
# ------------------------------------------------------------

communes = repartir_nuitees(
    communes,
    groupe="code_departement",
    colonne_capacite="places_hotels",
    colonne_nuitees="nuites_dep_hotels",
    colonne_resultat="nuites_hotels_estimees"
)

# ------------------------------------------------------------
# 7. CAMPINGS : DEPARTEMENT -> COMMUNES
# ------------------------------------------------------------

communes = repartir_nuitees(
    communes,
    groupe="code_departement",
    colonne_capacite="places_campings",
    colonne_nuitees="nuites_dep_campings",
    colonne_resultat="nuites_campings_estimees"
)

# ------------------------------------------------------------
# 8. AUTRES : REGION -> COMMUNES
# ------------------------------------------------------------

communes = repartir_nuitees(
    communes,
    groupe="code_region",
    colonne_capacite="places_autres",
    colonne_nuitees="nuites_reg_autres",
    colonne_resultat="nuites_autres_estimees"
)

# ------------------------------------------------------------
# 9. METADONNEES ET TABLEAU FINAL
# ------------------------------------------------------------

communes["annee_nuitees"] = 2022
communes["annee_capacites"] = 2026

communes["methode"] = (
    "Repartition proportionnelle aux capacites 2026"
)

communes["nuites_total_mixte_estime"] = (
    communes[
        [
            "nuites_hotels_estimees",
            "nuites_campings_estimees",
            "nuites_autres_estimees"
        ]
    ].sum(axis=1, min_count=3)
)

colonnes_finales = [
    "annee_nuitees",
    "annee_capacites",
    "code_region",
    "code_departement",
    "code_commune",
    "places_hotels",
    "places_campings",
    "places_autres",
    "nuites_hotels_estimees",
    "nuites_campings_estimees",
    "nuites_autres_estimees",
    "nuites_total_mixte_estime",
    "methode"
]

resultat = communes[colonnes_finales].copy()

# ------------------------------------------------------------
# 10. EXPORT
# ------------------------------------------------------------

fichier_csv = SORTIE / "nuites_communales_estimees_2022.csv"

resultat.to_csv(
    fichier_csv,
    index=False,
    encoding="utf-8-sig"
)

print("\n=== RESULTATS ===")
print("Communes estimées :", len(resultat))

print("\nNuitées calculées (lignes non nulles) :")
for colonne in [
    "nuites_hotels_estimees",
    "nuites_campings_estimees",
    "nuites_autres_estimees"
]:
    print(colonne, ":", resultat[colonne].notna().sum())

print("\nPremières lignes :")
print(resultat.head(15).to_string(index=False))

print("\nFichier créé :", fichier_csv)
print("\nTraitement terminé.")
