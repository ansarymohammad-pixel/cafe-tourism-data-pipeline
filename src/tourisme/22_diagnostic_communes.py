
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data/processed/tourisme"
ADMIN = BASE / "data/raw/administratif"

capacites = pd.read_csv(
    DOSSIER / "capacites_communales_2026.csv",
    dtype={
        "code_commune": str,
        "code_departement": str
    }
)

communes_2022 = gpd.read_file(
    ADMIN / "COMMUNE.shp",
    ignore_geometry=True
)

communes_2022["INSEE_COM"] = (
    communes_2022["INSEE_COM"].astype(str)
)

codes_2022 = set(communes_2022["INSEE_COM"])
codes_2026 = set(capacites["code_commune"])

# Communes présentes en 2026 mais absentes en 2022
nouvelles = capacites[
    ~capacites["code_commune"].isin(codes_2022)
].copy()

# Communes présentes en 2022 mais absentes en 2026
anciennes = communes_2022[
    ~communes_2022["INSEE_COM"].isin(codes_2026)
].copy()

print("=== COMPARAISON 2022 / 2026 ===")
print("Communes 2026 absentes en 2022 :", len(nouvelles))
print("Communes 2022 absentes en 2026 :", len(anciennes))

print("\n=== COMMUNES 2026 NON CONCORDANTES ===")
print(
    nouvelles[
        [
            "code_commune",
            "code_departement",
            "places_hotels",
            "places_campings",
            "places_autres"
        ]
    ].head(30).to_string(index=False)
)

print("\n=== COMMUNES 2022 NON CONCORDANTES ===")
print(
    anciennes[
        ["INSEE_COM", "NOM", "INSEE_DEP"]
    ].head(30).to_string(index=False)
)

nouvelles.to_csv(
    DOSSIER / "communes_2026_absentes_2022.csv",
    index=False,
    encoding="utf-8-sig"
)

anciennes.to_csv(
    DOSSIER / "communes_2022_absentes_2026.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nFichiers de diagnostic créés.")
