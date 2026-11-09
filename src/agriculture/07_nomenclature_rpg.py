
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

dossier = Path("data/processed")
dossier.mkdir(parents=True, exist_ok=True)

# Nomenclature de travail : libellés à valider
# avec le dictionnaire officiel du millésime RPG.
nomenclature = {
    "SNE": "Surface temporairement non exploitée",
    "BOR": "Bordure de champ",
    "PPH": "Prairie permanente",
    "BTA": "Bande tampon",
    "BFS": "Bande le long d'une forêt",
    "PTR": "Prairie temporaire",
    "JAC": "Jachère",
    "MDI": "Maïs doux",
    "PFR": "Prairie avec ligneux",
    "NOX": "Noix"
}

# Enregistrer la nomenclature provisoire
pd.DataFrame(
    nomenclature.items(),
    columns=["code_cultu", "nom_culture"]
).to_csv(
    dossier / "nomenclature_rpg_provisoire.csv",
    index=False
)

# Charger les données géographiques
rpg = gpd.read_file(
    "data/raw/RPG_Parcelles.gpkg",
    rows=10000
)

rpg["surface_ha"] = rpg.geometry.area / 10000

# Ajouter les libellés
rpg["nom_culture"] = (
    rpg["code_cultu"]
    .map(nomenclature)
    .fillna(rpg["code_cultu"])
)

# Agréger les surfaces
surfaces = (
    rpg.groupby("nom_culture")["surface_ha"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

# Visualiser
plt.figure(figsize=(11, 6))

surfaces.sort_values().plot(
    kind="barh",
    color="seagreen"
)

plt.title("Surfaces RPG par type de culture")
plt.xlabel("Surface totale (ha)")
plt.ylabel("Type de culture")
plt.tight_layout()

plt.savefig(
    dossier / "cultures_avec_noms.png",
    dpi=180
)
plt.show()
