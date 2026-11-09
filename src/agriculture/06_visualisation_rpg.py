
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

# Dossiers
fichier = Path("data/raw/RPG_Parcelles.gpkg")
sortie = Path("data/processed")
sortie.mkdir(parents=True, exist_ok=True)

# Lire 10 000 parcelles
rpg = gpd.read_file(fichier, rows=10000)

# Calculer les surfaces en hectares
rpg["surface_ha"] = rpg.geometry.area / 10000

# GRAPHIQUE 1 : Histogramme des surfaces
plt.figure(figsize=(9, 5))

plt.hist(
    rpg["surface_ha"],
    bins=40,
    edgecolor="black"
)

plt.title("Distribution des surfaces agricoles")
plt.xlabel("Surface (hectares)")
plt.ylabel("Nombre de parcelles")
plt.tight_layout()

plt.savefig(sortie / "histogramme_surfaces.png", dpi=150)
plt.show()

# GRAPHIQUE 2 : Surfaces par culture
surfaces = (
    rpg.groupby("code_cultu")["surface_ha"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

plt.figure(figsize=(10, 6))

surfaces.sort_values().plot(kind="barh")

plt.title("Top 10 des codes de cultures par surface")
plt.xlabel("Surface totale (hectares)")
plt.ylabel("Code de culture")
plt.tight_layout()

plt.savefig(sortie / "surfaces_cultures.png", dpi=150)
plt.show()

# GRAPHIQUE 3 : Carte des parcelles
fig, ax = plt.subplots(figsize=(9, 8))

rpg.plot(
    ax=ax,
    column="code_cultu",
    categorical=True,
    legend=False,
    linewidth=0
)

ax.set_title("Parcelles RPG - échantillon de 10 000 lignes")
ax.set_axis_off()

plt.tight_layout()
plt.savefig(sortie / "carte_parcelles.png", dpi=150)
plt.show()

print("Les trois graphiques ont été enregistrés.")
