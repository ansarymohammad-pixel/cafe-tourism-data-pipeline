
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
from matplotlib.ticker import FuncFormatter

# ============================================================
# CAFÉ - VISUALISATION TOURISTIQUE 2022
# ============================================================

BASE = Path(__file__).resolve().parent
DATA = BASE / "data/processed/tourisme"
SOURCE = DATA / "tableau_final"
ADMIN = BASE / "data/raw/administratif"
OUT = SOURCE / "graphiques"
OUT.mkdir(parents=True, exist_ok=True)

# Style général
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 250,
    "font.size": 11,
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COLORS = {
    "hotels": "#2563EB",
    "campings": "#F59E0B",
    "autres": "#10B981"
}

def millions(x, pos):
    return f"{x / 1_000_000:.1f} M"

def sauvegarder(nom):
    plt.tight_layout()
    plt.savefig(
        OUT / nom,
        bbox_inches="tight",
        facecolor="white"
    )
    plt.close()
    print("Graphique créé :", nom)

# Charger les données
regions = pd.read_excel(
    SOURCE / "tourisme_2022_trois_niveaux.xlsx",
    sheet_name="Regions",
    dtype={"code_region": str}
)

deps = pd.read_excel(
    SOURCE / "tourisme_2022_trois_niveaux.xlsx",
    sheet_name="Departements",
    dtype={"code_departement": str}
)

communes = pd.read_excel(
    SOURCE / "tourisme_2022_trois_niveaux.xlsx",
    sheet_name="Communes",
    dtype={"code_commune": str}
)

mesures = [
    "nuites_hotels",
    "nuites_campings",
    "nuites_autres"
]

for df in [regions, deps, communes]:
    for col in mesures:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

# ============================================================
# GRAPHIQUE 1 : REGIONS - HOTELS
# ============================================================

d = regions.dropna(
    subset=["nuites_hotels"]
).sort_values("nuites_hotels")

fig, ax = plt.subplots(figsize=(11, 7))

ax.barh(
    d["territoire"],
    d["nuites_hotels"],
    color=COLORS["hotels"]
)

ax.xaxis.set_major_formatter(FuncFormatter(millions))
ax.set_title("Nuitées hôtelières par région - 2022")
ax.set_xlabel("Nuitées (millions)")
ax.set_ylabel("")

sauvegarder("01_regions_hotels.png")

# ============================================================
# GRAPHIQUE 2 : HEBERGEMENTS PAR REGION
# Barres groupées pour ne pas présenter une somme annuelle
# non homogène.
# ============================================================

d = regions.sort_values(
    "nuites_hotels", ascending=False
).copy()

fig, ax = plt.subplots(figsize=(14, 7))
x = np.arange(len(d))
largeur = 0.26

for i, (col, label, couleur) in enumerate([
    ("nuites_hotels", "Hôtels (année)", COLORS["hotels"]),
    ("nuites_campings", "Campings (haute saison)", COLORS["campings"]),
    ("nuites_autres", "Autres (année)", COLORS["autres"])
]):
    ax.bar(
        x + (i - 1) * largeur,
        d[col],
        largeur,
        label=label,
        color=couleur
    )

ax.set_xticks(x)
ax.set_xticklabels(
    d["territoire"], rotation=55, ha="right"
)
ax.yaxis.set_major_formatter(FuncFormatter(millions))
ax.set_title("Nuitées par type d'hébergement et région - 2022")
ax.set_ylabel("Nuitées")
ax.legend()

sauvegarder("02_hebergements_regions.png")

# ============================================================
# GRAPHIQUE 3 : CAPACITE HOTELIERE ET NUITEES
# ============================================================

d = pd.read_csv(
    DATA / "estimations_communales"
    / "nuites_communales_estimees_2022.csv"
)

d = d[
    (d["places_hotels"] > 0)
    & (d["nuites_hotels_estimees"] > 0)
].copy()

fig, ax = plt.subplots(figsize=(10, 7))

sns.scatterplot(
    data=d,
    x="places_hotels",
    y="nuites_hotels_estimees",
    alpha=0.35,
    s=18,
    color=COLORS["hotels"],
    ax=ax
)

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_title("Capacité hôtelière et nuitées communales estimées")
ax.set_xlabel("Places hôtelières 2026 (échelle log)")
ax.set_ylabel("Nuitées estimées 2022 (échelle log)")

sauvegarder("03_capacite_vs_nuitees.png")


# ============================================================
# GRAPHIQUE 4 : DISTRIBUTION DES NUITEES COMMUNALES
# Communes avec nuitées strictement positives
# ============================================================

long = communes.melt(
    id_vars=["code_commune"],
    value_vars=[
        "nuites_hotels",
        "nuites_campings",
        "nuites_autres"
    ],
    var_name="hebergement",
    value_name="nuites"
)

# Convertir en nombres
long["nuites"] = pd.to_numeric(
    long["nuites"],
    errors="coerce"
)

# Conserver uniquement les valeurs positives
long = long[long["nuites"] > 0].copy()

# Transformation logarithmique
long["log_nuitees"] = np.log10(long["nuites"])

noms = {
    "nuites_hotels": "Hôtels",
    "nuites_campings": "Campings",
    "nuites_autres": "Autres"
}

long["hebergement"] = long["hebergement"].map(noms)

# Afficher quelques statistiques
print("\n=== DISTRIBUTION DES NUITEES POSITIVES ===")
print(
    long.groupby("hebergement")["nuites"]
    .describe()
)

# Créer le graphique
fig, ax = plt.subplots(figsize=(11, 7))

sns.boxplot(
    data=long,
    x="hebergement",
    y="log_nuitees",
    hue="hebergement",
    palette={
        "Hôtels": "#2563EB",
        "Campings": "#F59E0B",
        "Autres": "#10B981"
    },
    legend=False,
    showfliers=False,
    ax=ax
)

ax.set_title(
    "Distribution des nuitées communales estimées - 2022"
)

ax.set_xlabel("Type d'hébergement")
ax.set_ylabel("log10(nuitées estimées)")

ax.grid(axis="y", alpha=0.25)

sauvegarder("04_distribution_communes_corrigee.png")


# ============================================================
# GRAPHIQUE 5 : CARTE DES NUITEES HOTELIERES
# ============================================================

geo = gpd.read_file(ADMIN / "DEPARTEMENT.shp")
geo["INSEE_DEP"] = geo["INSEE_DEP"].astype(str)
deps["code_departement"] = (
    deps["code_departement"].astype(str)
)

carte = geo.merge(
    deps[["code_departement", "nuites_hotels"]],
    left_on="INSEE_DEP",
    right_on="code_departement",
    how="left"
)

fig, ax = plt.subplots(figsize=(10, 11))

carte.plot(
    column="nuites_hotels",
    cmap="Blues",
    legend=True,
    edgecolor="white",
    linewidth=0.5,
    missing_kwds={"color": "#E5E7EB"},
    ax=ax
)

ax.set_title("Nuitées hôtelières par département - 2022")
ax.axis("off")

sauvegarder("05_carte_departements.png")

# ============================================================
# GRAPHIQUE 6 : COURBE DE CONCENTRATION
# ============================================================

d = deps.dropna(
    subset=["nuites_hotels"]
).sort_values(
    "nuites_hotels", ascending=False
).copy()

d["part_cumulee"] = (
    d["nuites_hotels"].cumsum()
    / d["nuites_hotels"].sum()
    * 100
)

fig, ax = plt.subplots(figsize=(11, 6))

ax.plot(
    np.arange(1, len(d) + 1),
    d["part_cumulee"],
    color=COLORS["hotels"],
    linewidth=2.5
)

ax.axhline(
    80, color="#EF4444",
    linestyle="--", label="80 %"
)

ax.set_title("Concentration des nuitées hôtelières")
ax.set_xlabel("Nombre de départements (ordre décroissant)")
ax.set_ylabel("Part cumulée des nuitées (%)")
ax.set_ylim(0, 105)
ax.legend()

sauvegarder("06_concentration_nuitees.png")

print("\n=== VISUALISATIONS TERMINEES ===")
print("Dossier :", OUT)
print("Nombre de graphiques : 6")
