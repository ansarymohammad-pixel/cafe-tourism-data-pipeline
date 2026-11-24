
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parent
D = BASE / "data/processed/tourisme"
OUT = D / "livraison_cafe_2022"
OUT.mkdir(parents=True, exist_ok=True)

# 1. Chargement
communes = pd.read_csv(
    D / "capacites_metro_2022.csv",
    dtype={
        "geocode": str,
        "code_departement": str,
        "code_region": str
    }
)

nuites = pd.read_csv(
    D / "nuites_2022.csv",
    dtype={"GEO": str}
)

nuites = nuites[nuites["annee"] == 2022].copy()

for col in ["Hotels", "Campings", "Autres"]:
    nuites[col] = pd.to_numeric(
        nuites[col], errors="coerce"
    )

# 2. Extraire les codes INSEE
nuites["code"] = nuites["GEO"].str.extract(
    r"-(?:DEP|REG)-([0-9A-Z]+)$",
    expand=False
)

dep = nuites[nuites["niveau"] == "Département"].copy()
reg = nuites[nuites["niveau"] == "Région"].copy()

assert not dep["code"].duplicated().any()
assert not reg["code"].duplicated().any()

# 3. Répartir une observation selon les capacités
def repartir(df, observations, cle, capacite, valeur, sortie):
    obs = observations[["code", valeur]].rename(
        columns={"code": cle, valeur: "_total"}
    )

    result = df.merge(
        obs, on=cle, how="left", validate="many_to_one"
    )

    result[capacite] = pd.to_numeric(
        result[capacite], errors="coerce"
    ).fillna(0)

    total_capacite = result.groupby(cle)[capacite].transform("sum")

    valide = (
        result["_total"].notna()
        & (total_capacite > 0)
    )

    result[sortie] = np.nan

    result.loc[valide, sortie] = (
        result.loc[valide, "_total"]
        * result.loc[valide, capacite]
        / total_capacite.loc[valide]
    )

    return result[["geocode", sortie]]

# 4. Calcul des estimations
calculs = [
    (
        dep, "code_departement",
        "places_hotels", "Hotels",
        "hotel_nights_year"
    ),
    (
        dep, "code_departement",
        "places_campings", "Campings",
        "campings_nights_high_season"
    ),
    (
        reg, "code_region",
        "places_autres", "Autres",
        "other_nights_year"
    )
]

resultat = communes.copy()

for obs, cle, capacite, valeur, sortie in calculs:
    estimation = repartir(
        communes, obs, cle, capacite, valeur, sortie
    )

    resultat = resultat.merge(
        estimation,
        on="geocode",
        how="left",
        validate="one_to_one"
    )

# 5. Contrôles de conservation
controles = []

for obs, cle, capacite, valeur, sortie in calculs:
    estimations = (
        resultat.groupby(cle, dropna=False)[sortie]
        .sum(min_count=1)
        .rename("estime")
    )

    observations = (
        obs.set_index("code")[valeur]
        .rename("observe")
    )

    comparaison = pd.concat(
        [observations, estimations],
        axis=1
    )

    comparaison["ecart"] = (
        comparaison["estime"]
        - comparaison["observe"]
    )

    comparaison["indicateur"] = sortie
    comparaison["code_geo"] = comparaison.index

    controles.append(comparaison.reset_index(drop=True))

rapport = pd.concat(controles, ignore_index=True)

rapport["controle_ok"] = (
    rapport["observe"].notna()
    & rapport["estime"].notna()
    & np.isclose(
        rapport["observe"].fillna(0),
        rapport["estime"].fillna(0),
        rtol=1e-8,
        atol=1e-5
    )
)

# 6. Tableau communal CAFÉ
final = pd.DataFrame({
    "geocode": resultat["geocode"],
    "admin_level": "4",
    "hotel_capacity": resultat["places_hotels"],
    "camping_capacity": resultat["places_campings"],
    "other_capacity": resultat["places_autres"],
    "hotel_nights_year": resultat["hotel_nights_year"],
    "campings_nights_year": np.nan,
    "other_nights_year": resultat["other_nights_year"],
    "hotel_nights_january": np.nan,
    "campings_nights_january": np.nan,
    "other_nights_january": np.nan
})

# 7. Exporter
final.to_csv(
    OUT / "cafe_communes_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

rapport.to_csv(
    OUT / "controles_nuitees_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

# Export séparé de la haute saison camping
resultat[
    ["geocode", "campings_nights_high_season"]
].to_csv(
    OUT / "campings_haute_saison_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

with pd.ExcelWriter(
    OUT / "cafe_resultats_2022.xlsx"
) as writer:
    final.to_excel(
        writer, sheet_name="Communes", index=False
    )
    rapport.to_excel(
        writer, sheet_name="Controles", index=False
    )

print("\nCOMMUNES :", len(final))
print("\nCONTROLES :")
print(
    rapport.groupby("indicateur")["controle_ok"]
    .agg(["sum", "count"])
)

print("\nECARTS OU OBSERVATIONS MANQUANTES :")
print(
    rapport.loc[
        ~rapport["controle_ok"],
        ["indicateur", "code_geo",
         "observe", "estime", "ecart"]
    ].to_string(index=False)
)

print("\nFichiers créés dans :", OUT)
