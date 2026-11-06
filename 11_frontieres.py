
from pathlib import Path
import geopandas as gpd

BASE = Path(__file__).resolve().parent
DOSSIER = BASE / "data" / "raw" / "administratif"

for nom in ["COMMUNE", "DEPARTEMENT", "REGION"]:
    fichiers = list(DOSSIER.rglob(f"{nom}.shp"))

    if not fichiers:
        print(f"Fichier {nom}.shp introuvable")
        continue

    fichier = fichiers[0]
    gdf = gpd.read_file(fichier)

    print(f"\n=== {nom} ===")
    print("Chemin :", fichier)
    print("Nombre d'entités :", len(gdf))
    print("Projection :", gdf.crs)
    print("Colonnes :", gdf.columns.tolist())
    print(gdf.drop(columns="geometry").head(3).to_string(index=False))
