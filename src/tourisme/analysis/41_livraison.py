
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
D = BASE / "data/processed/tourisme"
OUT = D / "livraison_cafe_2022"
OUT.mkdir(exist_ok=True)

# Données communales calculées
communes = pd.read_csv(
    OUT / "cafe_communes_2022.csv",
    dtype={"geocode": str}
)

# Correspondance géographique
geo = pd.read_csv(
    D / "capacites_metro_2022.csv",
    dtype={
        "geocode": str,
        "code_departement": str,
        "code_region": str
    }
)[["geocode", "code_departement", "code_region"]]

communes = communes.merge(
    geo, on="geocode",
    how="left", validate="one_to_one"
)

# Observations de nuitées
nuites = pd.read_csv(
    D / "nuites_2022.csv",
    dtype={"GEO": str}
)

nuites["code"] = nuites["GEO"].str.extract(
    r"-(?:DEP|REG)-([0-9A-Z]+)$"
)

for col in ["Hotels", "Campings", "Autres"]:
    nuites[col] = pd.to_numeric(
        nuites[col], errors="coerce"
    )

capacites = [
    "hotel_capacity",
    "camping_capacity",
    "other_capacity"
]

# Niveaux départemental et régional
def agreger(cle, niveau, libelle):
    table = communes.groupby(cle, as_index=False)[
        capacites
    ].sum(min_count=1)

    table = table.rename(columns={cle: "geocode"})
    table["admin_level"] = niveau

    observations = nuites[
        nuites["niveau"] == libelle
    ][["code", "Hotels", "Campings", "Autres"]]

    table = table.merge(
        observations,
        left_on="geocode",
        right_on="code",
        how="left",
        validate="one_to_one"
    )

    table["hotel_nights_year"] = table["Hotels"]
    table["other_nights_year"] = table["Autres"]

    # Camping : haute saison ≠ année entière
    table["campings_nights_year"] = pd.NA

    return table

departements = agreger(
    "code_departement", "3", "Département"
)

regions = agreger(
    "code_region", "2", "Région"
)

# Colonnes finales
colonnes = [
    "geocode",
    "admin_level",
    "hotel_capacity",
    "camping_capacity",
    "other_capacity",
    "hotel_nights_year",
    "campings_nights_year",
    "other_nights_year",
    "hotel_nights_january",
    "campings_nights_january",
    "other_nights_january"
]

final = pd.concat(
    [communes, departements, regions],
    ignore_index=True
)

for col in colonnes:
    if col not in final.columns:
        final[col] = pd.NA

final = final[colonnes]

assert final["geocode"].notna().all()
assert not final[
    ["geocode", "admin_level"]
].duplicated().any()

# CSV final
final.to_csv(
    OUT / "TABLEAU_CAFE_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

# Excel final
with pd.ExcelWriter(
    OUT / "TABLEAU_CAFE_2022.xlsx"
) as writer:
    final.to_excel(
        writer,
        sheet_name="Donnees_2022",
        index=False
    )

print("\nTABLEAU FINAL")
print("Lignes :", len(final))
print("\nRépartition par niveau :")
print(final["admin_level"].value_counts())
print("\nValeurs disponibles :")
print(final.notna().sum())
print("\nFichiers créés dans :", OUT)
