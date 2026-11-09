
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data/processed/tourisme"
ADMIN = BASE / "data/raw/administratif"
SORTIE = DATA / "tableau_final"
SORTIE.mkdir(parents=True, exist_ok=True)

# 1. Charger les nuitées observées 2022
nuites = pd.read_csv(
    DATA / "nuites_2022.csv",
    dtype={"GEO": str}
)

# 2. Charger les estimations communales
communes = pd.read_csv(
    DATA / "estimations_communales"
    / "nuites_communales_estimees_2022.csv",
    dtype={
        "code_region": str,
        "code_departement": str,
        "code_commune": str
    }
)

# 3. Charger les noms géographiques
reg_geo = gpd.read_file(
    ADMIN / "REGION.shp",
    ignore_geometry=True
)

dep_geo = gpd.read_file(
    ADMIN / "DEPARTEMENT.shp",
    ignore_geometry=True
)

com_geo = gpd.read_file(
    ADMIN / "COMMUNE.shp",
    ignore_geometry=True
)

regions_noms = dict(zip(
    reg_geo["INSEE_REG"].astype(str),
    reg_geo["NOM"].astype(str)
))

departements_noms = dict(zip(
    dep_geo["INSEE_DEP"].astype(str),
    dep_geo["NOM"].astype(str)
))

communes_noms = dict(zip(
    com_geo["INSEE_COM"].astype(str),
    com_geo["NOM"].astype(str)
))

# Noms des départements d'outre-mer
departements_noms.update({
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte"
})

# 4. Préparer les codes
nuites["code"] = nuites["GEO"].str.split("-").str[-1]

# 5. Tableau régional
regions = nuites[
    nuites["niveau"] == "Région"
].copy()

regions["code_region"] = regions["code"]
regions["territoire"] = (
    regions["code_region"].map(regions_noms)
)

regions = regions.rename(columns={
    "Hotels": "nuites_hotels",
    "Campings": "nuites_campings",
    "Autres": "nuites_autres"
})

regions["niveau"] = "Région"
regions["source_nuitees"] = "Observées INSEE 2022"

regions = regions[
    [
        "niveau", "code_region", "territoire",
        "nuites_hotels", "nuites_campings",
        "nuites_autres", "source_nuitees"
    ]
]

# 6. Tableau départemental
departements = nuites[
    nuites["niveau"] == "Département"
].copy()

departements["code_departement"] = departements["code"]
departements["territoire"] = (
    departements["code_departement"].map(
        departements_noms
    )
)

departements = departements.rename(columns={
    "Hotels": "nuites_hotels",
    "Campings": "nuites_campings",
    "Autres": "nuites_autres"
})

departements["niveau"] = "Département"
departements["source_nuitees"] = "Observées INSEE 2022"

departements = departements[
    [
        "niveau", "code_departement", "territoire",
        "nuites_hotels", "nuites_campings",
        "nuites_autres", "source_nuitees"
    ]
]

# 7. Tableau communal
communes["territoire"] = (
    communes["code_commune"].map(communes_noms)
)

communes = communes.rename(columns={
    "nuites_hotels_estimees": "nuites_hotels",
    "nuites_campings_estimees": "nuites_campings",
    "nuites_autres_estimees": "nuites_autres"
})

communes["niveau"] = "Commune"
communes["source_nuitees"] = (
    "Estimées avec capacités 2026"
)

communes = communes[
    [
        "niveau", "code_region", "code_departement",
        "code_commune", "territoire",
        "nuites_hotels", "nuites_campings",
        "nuites_autres", "source_nuitees"
    ]
]

# 8. Tableau global avec colonnes communes
colonnes_finales = [
    "niveau",
    "code_region",
    "code_departement",
    "code_commune",
    "territoire",
    "nuites_hotels",
    "nuites_campings",
    "nuites_autres",
    "source_nuitees"
]

global_df = pd.concat(
    [regions, departements, communes],
    ignore_index=True
)

global_df = global_df.reindex(columns=colonnes_finales)

# 9. Export CSV
global_df.to_csv(
    SORTIE / "tourisme_2022_trois_niveaux.csv",
    index=False,
    encoding="utf-8-sig"
)

# 10. Export Excel
fichier_excel = (
    SORTIE / "tourisme_2022_trois_niveaux.xlsx"
)

with pd.ExcelWriter(
    fichier_excel,
    engine="openpyxl"
) as writer:

    regions.to_excel(
        writer, sheet_name="Regions", index=False
    )

    departements.to_excel(
        writer, sheet_name="Departements", index=False
    )

    communes.to_excel(
        writer, sheet_name="Communes", index=False
    )

    global_df.to_excel(
        writer, sheet_name="Toutes_donnees", index=False
    )

print("\n=== TABLEAU FINAL CAFÉ ===")
print("Régions :", len(regions))
print("Départements :", len(departements))
print("Communes :", len(communes))
print("Total lignes :", len(global_df))
print("\nFichier Excel :", fichier_excel)
print("\nTraitement terminé.")
