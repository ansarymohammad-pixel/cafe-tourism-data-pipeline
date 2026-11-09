from pathlib import Path
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title='CAFÉ | Tourisme 2022', page_icon='📊', layout='wide')
st.title('CAFÉ · Tourisme 2022')
st.caption('Exploration des capacités d’hébergement et des nuitées estimées — France métropolitaine')

BASE = Path(__file__).resolve().parent
DEFAULT_ROOT = BASE.parent / 'data' / 'processed' / 'tourisme'
ROOT = Path(st.sidebar.text_input('Dossier des données', str(DEFAULT_ROOT))).expanduser()

@st.cache_data(show_spinner=False)
def load_data(path, modified):
    return pd.read_csv(path, dtype={'geocode': str, 'code_departement': str, 'code_region': str})

source = ROOT / 'livraison_cafe_2022' / 'cafe_communes_2022.csv'
geo_source = ROOT / 'capacites_metro_2022.csv'
camping_source = ROOT / 'livraison_cafe_2022' / 'campings_haute_saison_2022.csv'
qa_source = ROOT / 'livraison_cafe_2022' / 'controles_nuitees_2022.csv'

missing = [str(p) for p in (source, geo_source) if not p.exists()]
if missing:
    st.error('Fichiers nécessaires introuvables :\n' + '\n'.join(missing))
    st.info('Exécute d’abord les scripts 38 et 39. Si app.py est placé à la racine du projet cafe, le chemin par défaut fonctionne.')
    st.stop()

df = load_data(str(source), source.stat().st_mtime)
geo = load_data(str(geo_source), geo_source.stat().st_mtime)
required = {'geocode', 'hotel_capacity', 'camping_capacity', 'other_capacity', 'hotel_nights_year', 'other_nights_year'}
if not required.issubset(df.columns):
    st.error('Colonnes absentes : ' + ', '.join(sorted(required - set(df.columns))))
    st.stop()

geo = geo[['geocode', 'code_region', 'code_departement']].drop_duplicates('geocode')
df = df.merge(geo, on='geocode', how='left', validate='one_to_one')
if camping_source.exists():
    camping = load_data(str(camping_source), camping_source.stat().st_mtime)
    df = df.merge(camping[['geocode', 'campings_nights_high_season']], on='geocode', how='left', validate='one_to_one')
else:
    df['campings_nights_high_season'] = float('nan')

categories = {
    'Hôtels': ('hotel_capacity', 'hotel_nights_year', 'Chambres', 'Nuitées annuelles estimées'),
    'Campings': ('camping_capacity', 'campings_nights_high_season', 'Emplacements de passage', 'Nuitées haute saison estimées'),
    'Autres hébergements': ('other_capacity', 'other_nights_year', 'Lits', 'Nuitées annuelles estimées'),
}

st.sidebar.header('Filtres')
category = st.sidebar.selectbox('Catégorie touristique', list(categories))
regions = sorted(df['code_region'].dropna().unique().tolist())
region = st.sidebar.selectbox('Région (code INSEE)', ['Toutes'] + regions)
scoped = df if region == 'Toutes' else df[df['code_region'] == region]
deps = sorted(scoped['code_departement'].dropna().unique().tolist())
department = st.sidebar.selectbox('Département (code INSEE)', ['Tous'] + deps)
filtered = scoped if department == 'Tous' else scoped[scoped['code_departement'] == department]

cap_col, night_col, cap_unit, night_unit = categories[category]
for col in (cap_col, night_col):
    filtered = filtered.copy()
    filtered[col] = pd.to_numeric(filtered[col], errors='coerce')

st.subheader('Vue d’ensemble')
a,b,c,d = st.columns(4)
a.metric('Communes', f'{len(filtered):,}'.replace(',', ' '))
b.metric(f'Capacité · {cap_unit}', f'{filtered[cap_col].sum():,.0f}'.replace(',', ' '))
c.metric(night_unit, f'{filtered[night_col].sum(min_count=1):,.0f}'.replace(',', ' ') if filtered[night_col].notna().any() else 'Indisponible')
d.metric('Communes avec nuitées', f'{filtered[night_col].notna().sum():,}'.replace(',', ' '))

if category == 'Campings':
    st.warning('Les nuitées camping disponibles correspondent uniquement à la haute saison, et non à l’année complète.')
st.info('Les nuitées communales sont des estimations réparties au prorata des capacités. Les capacités des différentes catégories ne sont pas directement additionnables.')

left, right = st.columns(2)
with left:
    st.subheader('Top 20 communes · capacité')
    top = filtered.nlargest(20, cap_col)[['geocode', cap_col]].sort_values(cap_col)
    if len(top):
        chart = alt.Chart(top).mark_bar().encode(
            x=alt.X(f'{cap_col}:Q', title=cap_unit),
            y=alt.Y('geocode:N', sort=None, title='Code commune'),
            tooltip=['geocode', alt.Tooltip(f'{cap_col}:Q', format=',.0f')]
        ).properties(height=440)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write('Aucune commune pour ce filtre.')
with right:
    st.subheader('Capacité par département')
    grouped = filtered.groupby('code_departement', dropna=False, as_index=False)[cap_col].sum()
    grouped = grouped.sort_values(cap_col, ascending=False).head(25)
    if len(grouped):
        chart = alt.Chart(grouped).mark_bar().encode(
            x=alt.X('code_departement:N', sort='-y', title='Département'),
            y=alt.Y(f'{cap_col}:Q', title=cap_unit),
            tooltip=['code_departement', alt.Tooltip(f'{cap_col}:Q', format=',.0f')]
        ).properties(height=440)
        st.altair_chart(chart, use_container_width=True)

st.subheader('Capacité et nuitées estimées')
points = filtered.loc[filtered[night_col].notna(), ['geocode', cap_col, night_col]]
if len(points):
    scatter = alt.Chart(points).mark_circle(opacity=.5, size=45).encode(
        x=alt.X(f'{cap_col}:Q', title=cap_unit),
        y=alt.Y(f'{night_col}:Q', title=night_unit),
        tooltip=['geocode', alt.Tooltip(f'{cap_col}:Q', format=',.0f'), alt.Tooltip(f'{night_col}:Q', format=',.0f')]
    ).interactive().properties(height=360)
    st.altair_chart(scatter, use_container_width=True)
else:
    st.warning('Aucune nuitée disponible pour les filtres sélectionnés.')

st.subheader('Données filtrées')
cols = ['geocode', 'code_region', 'code_departement', cap_col, night_col]
st.dataframe(filtered[cols], use_container_width=True, hide_index=True)
st.download_button('Télécharger les données filtrées (CSV)', filtered[cols].to_csv(index=False).encode('utf-8-sig'), file_name='cafe_tourisme_2022_filtre.csv', mime='text/csv')

with st.expander('Contrôles qualité et limites'):
    st.write('Périmètre : France métropolitaine. Les 112 lignes DROM sont exclues du jeu métropolitain. Les 45 arrondissements municipaux sont exclus pour éviter de compter deux fois Paris, Lyon et Marseille.')
    st.write('Les nuitées de janvier ne sont pas renseignées. Les nuitées annuelles camping ne sont pas disponibles dans ce jeu de données.')
    if qa_source.exists():
        qa = load_data(str(qa_source), qa_source.stat().st_mtime)
        st.dataframe(qa, use_container_width=True, hide_index=True)
        if 'controle_ok' in qa.columns:
            bad = qa['controle_ok'].astype(str).str.lower().ne('true')
            st.metric('Contrôles non validés', int(bad.sum()))
    else:
        st.warning('Rapport de contrôles introuvable : exécute le script 39.')
