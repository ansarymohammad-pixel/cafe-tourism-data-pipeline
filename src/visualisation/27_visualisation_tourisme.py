
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from matplotlib.ticker import FuncFormatter

# ============================================================
# PROJET CAFÉ - VISUALISATION TOURISTIQUE
# Nuitées observées : 2022
# Nuitées communales estimées : capacités 2026
# ============================================================

BASE = Path(__file__).resolve().parent

DATA = BASE / "data/processed/tourisme"
ADMIN = BASE / "data/raw/administratif"

EXCEL = (
    DATA / "tableau_final"
    / "tourisme_2022_trois_niveaux.xlsx"
)

SORTIE = DATA / "visualisations_finales"
SORTIE.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# STYLE
# ------------------------------------------------------------

sns.set_theme(style="whitegrid", context="notebook")

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 250,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COULEURS = {
    "hotels": "#2563EB",
    "campings": "#F59E0B",
    "autres": "#10B981"
}

MESURES = [
    "nuites_hotels",
    "nuites_campings",
    "nuites_autres"
]

def format_millions(x, pos):
    return f"{x / 1_000_000:.1f} M"

def sauvegarder(nom):
    plt.tight_layout()
    plt.savefig(
        SORTIE / nom,
        bbox_inches="tight",
        facecolor="white"
    )
    plt.close()
    print("Créé :", nom)

# ------------------------------------------------------------
# CHARGEMENT DES DONNÉES
# ------------------------------------------------------------

if not EXCEL.exists():
    raise FileNotFoundError(
        f"Fichier Excel introuvable : {EXCEL}"
    )

regions = pd.read_excel(
    EXCEL,
    sheet_name="Regions",
    dtype={"code_region": str}
)

departements = pd.read_excel(
    EXCEL,
    sheet_name="Departements",
    dtype={"code_departement": str}
)

communes = pd.read_excel(
    EXCEL,
    sheet_name="Communes",
    dtype={
        "code_region": str,
        "code_departement": str,
        "code_commune": str
    }
)

for df in [regions, departements, communes]:
    for colonne in MESURES:
        df[colonne] = pd.to_numeric(
            df[colonne], errors="coerce"
        )

print("\n=== DONNÉES CHARGÉES ===")
print("Régions :", len(regions))
print("Départements :", len(departements))
print("Communes :", len(communes))

# ============================================================
# 1. RÉGIONS - CLASSEMENT HÔTELIER
# ============================================================

d = regions.dropna(
    subset=["nuites_hotels"]
).sort_values("nuites_hotels")

fig, ax = plt.subplots(figsize=(12, 7))

ax.barh(
    d["territoire"],
    d["nuites_hotels"],
    color=COULEURS["hotels"]
)

ax.xaxis.set_major_formatter(
    FuncFormatter(format_millions)
)

ax.set_title("Nuitées hôtelières par région - 2022")
ax.set_xlabel("Nuitées (millions)")
ax.set_ylabel("")

sauvegarder("01_regions_classement.png")

# ============================================================
# 2. RÉGIONS - COMPARAISON DES HÉBERGEMENTS
# ============================================================

d = regions.sort_values(
    "nuites_hotels", ascending=False
).copy()

fig, ax = plt.subplots(figsize=(15, 8))

x = np.arange(len(d))
largeur = 0.26

categories = [
    ("nuites_hotels", "Hôtels (année)", "#2563EB"),
    ("nuites_campings", "Campings (haute saison)", "#F59E0B"),
    ("nuites_autres", "Autres (année)", "#10B981")
]

for i, (col, label, couleur) in enumerate(categories):
    ax.bar(
        x + (i - 1) * largeur,
        d[col],
        largeur,
        color=couleur,
        label=label
    )

ax.set_xticks(x)
ax.set_xticklabels(
    d["territoire"],
    rotation=45,
    ha="right"
)

ax.yaxis.set_major_formatter(
    FuncFormatter(format_millions)
)

ax.set_title(
    "Nuitées par type d'hébergement et région - 2022"
)
ax.set_ylabel("Nuitées")
ax.legend()

sauvegarder("02_regions_hebergements.png")

# ============================================================
# 3. RÉGIONS - CARTE
# ============================================================

geo_reg = gpd.read_file(
    ADMIN / "REGION.shp"
)

geo_reg["INSEE_REG"] = (
    geo_reg["INSEE_REG"].astype(str)
)

carte_reg = geo_reg.merge(
    regions[["code_region", "nuites_hotels"]],
    left_on="INSEE_REG",
    right_on="code_region",
    how="left"
)

fig, ax = plt.subplots(figsize=(10, 10))

carte_reg.plot(
    column="nuites_hotels",
    cmap="Blues",
    legend=True,
    edgecolor="white",
    linewidth=0.8,
    missing_kwds={"color": "#E5E7EB"},
    ax=ax
)

ax.set_title(
    "Carte des nuitées hôtelières par région - 2022"
)
ax.axis("off")

sauvegarder("03_regions_carte.png")

# ============================================================
# 4. DÉPARTEMENTS - TOP 15
# ============================================================

d = (
    departements
    .dropna(subset=["nuites_hotels"])
    .nlargest(15, "nuites_hotels")
    .sort_values("nuites_hotels")
)

fig, ax = plt.subplots(figsize=(12, 8))

ax.barh(
    d["territoire"],
    d["nuites_hotels"],
    color="#0D9488"
)

ax.xaxis.set_major_formatter(
    FuncFormatter(format_millions)
)

ax.set_title(
    "Top 15 des départements - Nuitées hôtelières 2022"
)
ax.set_xlabel("Nuitées (millions)")
ax.set_ylabel("")

sauvegarder("04_departements_top15.png")

# ============================================================
# 5. DÉPARTEMENTS - CARTE
# ============================================================

geo_dep = gpd.read_file(
    ADMIN / "DEPARTEMENT.shp"
)

geo_dep["INSEE_DEP"] = (
    geo_dep["INSEE_DEP"].astype(str)
)

carte_dep = geo_dep.merge(
    departements[
        ["code_departement", "nuites_hotels"]
    ],
    left_on="INSEE_DEP",
    right_on="code_departement",
    how="left"
)

fig, ax = plt.subplots(figsize=(10, 11))

carte_dep.plot(
    column="nuites_hotels",
    cmap="YlOrRd",
    legend=True,
    edgecolor="white",
    linewidth=0.5,
    missing_kwds={"color": "#E5E7EB"},
    ax=ax
)

ax.set_title(
    "Nuitées hôtelières par département - 2022"
)
ax.axis("off")

sauvegarder("05_departements_carte.png")

# ============================================================
# 6. DÉPARTEMENTS - COURBE DE CONCENTRATION
# ============================================================

d = (
    departements
    .dropna(subset=["nuites_hotels"])
    .sort_values("nuites_hotels", ascending=False)
    .copy()
)

d["part_cumulee"] = (
    d["nuites_hotels"].cumsum()
    / d["nuites_hotels"].sum()
    * 100
)

fig, ax = plt.subplots(figsize=(11, 6))

ax.plot(
    np.arange(1, len(d) + 1),
    d["part_cumulee"],
    color=COULEURS["hotels"],
    linewidth=2.5
)

ax.axhline(
    80,
    color="#EF4444",
    linestyle="--",
    label="80 %"
)

ax.set_title(
    "Concentration des nuitées hôtelières - 2022"
)
ax.set_xlabel(
    "Nombre de départements classés par fréquentation"
)
ax.set_ylabel("Part cumulée (%)")
ax.set_ylim(0, 105)
ax.legend()

sauvegarder("06_departements_concentration.png")

# ============================================================
# 7. COMMUNES - BOXPLOT CORRIGÉ
# ============================================================

long = communes.melt(
    id_vars=["code_commune"],
    value_vars=MESURES,
    var_name="hebergement",
    value_name="nuites"
)

long = long[long["nuites"] > 0].copy()

long["log_nuitees"] = np.log10(
    long["nuites"]
)

noms = {
    "nuites_hotels": "Hôtels",
    "nuites_campings": "Campings",
    "nuites_autres": "Autres"
}

long["hebergement"] = (
    long["hebergement"].map(noms)
)

fig, ax = plt.subplots(figsize=(11, 7))

sns.boxplot(
    data=long,
    x="hebergement",
    y="log_nuitees",
    hue="hebergement",
    palette={
        "Hôtels": COULEURS["hotels"],
        "Campings": COULEURS["campings"],
        "Autres": COULEURS["autres"]
    },
    legend=False,
    showfliers=False,
    ax=ax
)

ax.set_title(
    "Distribution des nuitées communales estimées - 2022"
)
ax.set_xlabel("Type d'hébergement")
ax.set_ylabel("log10(nuitées positives)")

sauvegarder("07_communes_boxplot.png")

# ============================================================
# 8. COMMUNES - HISTOGRAMME
# ============================================================

d = communes[
    communes["nuites_hotels"] > 0
].copy()

fig, ax = plt.subplots(figsize=(11, 7))

sns.histplot(
    np.log10(d["nuites_hotels"]),
    bins=40,
    color=COULEURS["hotels"],
    edgecolor="white",
    ax=ax
)

ax.set_title(
    "Distribution des nuitées hôtelières communales estimées"
)
ax.set_xlabel("log10(nuitées hôtelières)")
ax.set_ylabel("Nombre de communes")

sauvegarder("08_communes_histogramme.png")

# ============================================================
# 9. COMMUNES - CARTE
# ============================================================

geo_com = gpd.read_file(
    ADMIN / "COMMUNE.shp"
)

geo_com["INSEE_COM"] = (
    geo_com["INSEE_COM"].astype(str)
)

carte_com = geo_com.merge(
    communes[
        ["code_commune", "nuites_hotels"]
    ],
    left_on="INSEE_COM",
    right_on="code_commune",
    how="left"
)

fig, ax = plt.subplots(figsize=(12, 12))

carte_com.plot(
    column="nuites_hotels",
    cmap="YlOrRd",
    legend=True,
    linewidth=0,
    missing_kwds={"color": "#E5E7EB"},
    ax=ax
)

ax.set_title(
    "Nuitées hôtelières communales estimées - 2022"
)
ax.axis("off")

sauvegarder("09_communes_carte.png")

# ============================================================
# FIN
# ============================================================

print("\n=== VISUALISATIONS TERMINÉES ===")
print("Nombre de graphiques : 9")
print("Dossier :", SORTIE)
print("\nIMPORTANT :")
print("Régions et départements : données observées 2022.")
print("Communes : estimations avec capacités 2026.")
print("Campings : nuitées de haute saison.")
