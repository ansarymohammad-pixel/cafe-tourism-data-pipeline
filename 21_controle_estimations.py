
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data/processed/tourisme"

observations = pd.read_csv(
    DOSSIER / "nuites_2022.csv",
    dtype={"GEO": str}
)

estimations = pd.read_csv(
    DOSSIER / "estimations_communales"
    / "nuites_communales_estimees_2022.csv",
    dtype={
        "code_region": str,
        "code_departement": str,
        "code_commune": str
    }
)

observations["code"] = (
    observations["GEO"].str.split("-").str[-1]
)

tests = [
    (
        "Département",
        "code_departement",
        "Hotels",
        "nuites_hotels_estimees",
        "Hôtels"
    ),
    (
        "Département",
        "code_departement",
        "Campings",
        "nuites_campings_estimees",
        "Campings"
    ),
    (
        "Région",
        "code_region",
        "Autres",
        "nuites_autres_estimees",
        "Autres hébergements"
    )
]

resultats = []

for niveau, code_col, col_obs, col_est, categorie in tests:

    reference = observations[
        observations["niveau"] == niveau
    ][["code", col_obs]].rename(
        columns={col_obs: "observe"}
    )

    calcule = (
        estimations.groupby(code_col)[col_est]
        .sum(min_count=1)
        .reset_index()
        .rename(columns={
            code_col: "code",
            col_est: "estime"
        })
    )

    controle = reference.merge(
        calcule,
        on="code",
        how="outer",
        indicator=True
    )

    controle["ecart"] = (
        controle["estime"] - controle["observe"]
    )

    controle["ecart_pct"] = np.where(
        controle["observe"].notna()
        & (controle["observe"] != 0),
        100 * controle["ecart"] / controle["observe"],
        np.nan
    )

    controle["categorie"] = categorie
    controle["niveau"] = niveau

    controle["statut"] = np.select(
        [
            controle["observe"].isna(),
            controle["estime"].isna(),
            controle["ecart"].abs() > 1
        ],
        [
            "OBSERVATION ABSENTE",
            "ESTIMATION ABSENTE",
            "ECART"
        ],
        default="OK"
    )

    resultats.append(controle)

bilan = pd.concat(resultats, ignore_index=True)

colonnes = [
    "niveau", "categorie", "code",
    "observe", "estime", "ecart",
    "ecart_pct", "statut"
]

bilan = bilan[colonnes]

sortie = (
    DOSSIER / "estimations_communales"
    / "controle_conservation_nuitees.csv"
)

bilan.to_csv(
    sortie,
    index=False,
    encoding="utf-8-sig"
)

print("\n=== BILAN DES CONTROLES ===")
print(bilan.groupby(["categorie", "statut"]).size())

print("\n=== ECARTS ET DONNEES MANQUANTES ===")
problemes = bilan[bilan["statut"] != "OK"]

print(problemes.head(30).to_string(index=False))

print("\nNombre de problèmes :", len(problemes))
print("\nFichier créé :", sortie)
