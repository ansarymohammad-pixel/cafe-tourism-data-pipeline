
import streamlit as st
import frontmatter
from pathlib import Path
from datetime import date

st.set_page_config(
    page_title="CAFÉ - Journal de bord",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CAFÉ — Suivi du projet")
st.caption("Journal de bord et traçabilité quotidienne")

dossier = Path("journal")
dossier.mkdir(exist_ok=True)

fichiers = sorted(
    dossier.glob("*.md"),
    reverse=True
)

if not fichiers:
    st.info("Aucune entrée de journal pour le moment.")
    st.stop()

# Charger les entrées Markdown
entrees = []

for fichier in fichiers:
    post = frontmatter.load(fichier)

    entrees.append({
        "date": str(post.get("date", fichier.stem)),
        "statut": post.get("statut", "Non renseigné"),
        "contenu": post.content
    })

# Indicateurs
col1, col2, col3 = st.columns(3)

col1.metric("Jours documentés", len(entrees))
col2.metric("Dernière mise à jour", entrees[0]["date"])
col3.metric("Statut actuel", entrees[0]["statut"])

st.divider()

# Navigation quotidienne
dates = [entree["date"] for entree in entrees]

jour = st.selectbox(
    "Choisir une journée",
    dates
)

selection = next(
    e for e in entrees if e["date"] == jour
)

st.subheader(f"Journal du {jour}")

# Affichage du Markdown
st.markdown(selection["contenu"])

st.divider()

# Historique
st.subheader("Historique du projet")

for entree in entrees:
    with st.expander(
        f"{entree['date']} — {entree['statut']}"
    ):
        st.markdown(entree["contenu"])


from pathlib import Path

st.divider()
st.header("📊 Visualisation des données RPG")

dossier = Path("data/processed")

graphiques = [
    ("Distribution des surfaces", "histogramme_surfaces.png"),
    ("Surfaces par culture", "surfaces_cultures.png"),
    ("Carte des parcelles", "carte_parcelles.png")
]

for titre, nom_fichier in graphiques:
    chemin = dossier / nom_fichier

    if chemin.exists():
        st.subheader(titre)
        st.image(str(chemin), use_container_width=True)
    else:
        st.warning(f"Fichier introuvable : {chemin}")
