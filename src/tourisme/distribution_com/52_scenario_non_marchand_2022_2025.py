"""CAFÉ | Script 52 — solution B, scénario France + outre-mer, 2022–2025.

Sources :
  data/raw/tourisme/tourisme_national_brut.csv (INSEE SDT, agrégats destination)
  data/processed/tourisme/{annee}/nuites_non_marchandes_{annee}.csv (script 46)
  data/processed/tourisme/{annee}/cles_non_marchandes_com_dep_reg_{annee}.csv (script 50)
Sortie : scenario_non_marchand_com_dep_reg_{annee}.csv (lu par script 54).

HYPOTHÈSES (NE PAS INTERPRÉTER COMME DES OBSERVATIONS MÉTROPOLITAINES) :
  1. Le ratio toutes catégories France + outre-mer / toutes destinations
     est supposé identique pour famille/amis et résidences secondaires.
  2. Les totaux ainsi ajustés sont attribués aux communes métropolitaines
     à l'aide des poids population et logements (proxies 2023).
  3. Profil mensuel uniforme (1/12), NON observé.
Les contrôles de sommes COM -> DEP -> REG et mensuels sont intégrés.

Commande : python src/tourisme/distribution_com/52_scenario_non_marchand_2022_2025.py
Option : --year 2022
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'data' / 'raw' / 'tourisme' / 'tourisme_national_brut.csv'
PROCESSED = ROOT / 'data' / 'processed' / 'tourisme'
YEARS = (2022, 2023, 2024, 2025)
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june',
          'july', 'august', 'september', 'october', 'november', 'december')
CATEGORIES = {
    'famille_amis': ('family_nights', 'poids_famille_amis'),
    'residences_secondaires': ('secondary_residence', 'poids_residences_secondaires'),
}
REGIONS = {
    '11': '75 77 78 91 92 93 94 95', '24': '18 28 36 37 41 45',
    '27': '21 25 39 58 70 71 89 90', '28': '14 27 50 61 76',
    '32': '02 59 60 62 80', '44': '08 10 51 52 54 55 57 67 68 88',
    '52': '44 49 53 72 85', '53': '22 29 35 56',
    '75': '16 17 19 23 24 33 40 47 64 79 86 87',
    '76': '09 11 12 30 31 32 34 46 48 65 66 81 82',
    '84': '01 03 07 15 26 38 42 43 63 69 73 74',
    '93': '04 05 06 13 83 84', '94': '2A 2B',
}
DEP_REG = {dep: reg for reg, deps in REGIONS.items() for dep in deps.split()}
VALUE_COLS = [col for prefix, _ in CATEGORIES.values()
              for col in ([prefix + '_year'] + [prefix + '_' + m for m in MONTHS])]


def float_col(frame, name):
    values = pd.to_numeric(frame[name].astype(str).str.replace(',', '.', regex=False),
                           errors='coerce')
    if values.isna().any() or not np.isfinite(values).all() or values.lt(0).any():
        raise ValueError(f'Donnée absente, infinie ou négative : {name}')
    return values.astype(float)


def assert_equal(actual, expected, what):
    if not np.isclose(float(actual), float(expected), atol=0.01, rtol=0):
        raise ValueError(f'[ECHEC SOMMES] {what} : {actual} != {expected}')


def destination_ratios():
    if not RAW.is_file():
        raise FileNotFoundError(f'Source SDT introuvable : {RAW}')
    fields = ['GEO', 'SEASONAL_ADJUST', 'TOUR_MEASURE', 'TRAVEL_DEST',
              'MODE_TRANSPORT', 'FREQ', 'TIME_PERIOD', 'UNIT_MEASURE',
              'TYPE_TOUR_ACCOMODATION', 'TRAVEL_REASON', 'OBS_STATUS',
              'UNIT_MULT', 'OBS_VALUE_NIVEAU']
    raw = pd.read_csv(RAW, usecols=fields, dtype=str, low_memory=False)
    mask = (raw['FREQ'].eq('A') & raw['TIME_PERIOD'].isin([str(y) for y in YEARS])
            & raw['TOUR_MEASURE'].eq('NIGHT_SPENT')
            & raw['TYPE_TOUR_ACCOMODATION'].eq('_T')
            & raw['TRAVEL_REASON'].eq('_T')
            & raw['TRAVEL_DEST'].isin(['250', '_T'])
            & raw['GEO'].str.endswith('FRANCE-FM', na=False)
            & raw['SEASONAL_ADJUST'].eq('N')
            & raw['MODE_TRANSPORT'].eq('_T')
            & raw['UNIT_MEASURE'].eq('NR')
            & raw['OBS_STATUS'].isin(['A', 'P']))
    sub = raw.loc[mask].copy()
    sub['nuites'] = float_col(sub, 'OBS_VALUE_NIVEAU') * (10 ** float_col(sub, 'UNIT_MULT'))
    if sub.duplicated(['TIME_PERIOD', 'TRAVEL_DEST']).any():
        raise ValueError('Doublon de séries SDT destination : préciser les filtres')
    table = sub.pivot(index='TIME_PERIOD', columns='TRAVEL_DEST', values='nuites')
    if any(str(y) not in table.index for y in YEARS) or not {'250', '_T'}.issubset(table.columns):
        raise ValueError('Séries annuelles France+outre-mer et toutes destinations incomplètes')
    result = {}
    for y in YEARS:
        domestic = float(table.loc[str(y), '250'])
        all_dest = float(table.loc[str(y), '_T'])
        if not (0 < domestic <= all_dest):
            raise ValueError(f'Ratio géographique impossible pour {y}')
        result[y] = (domestic / all_dest, domestic, all_dest)
    return result


def perform(year, ratios):
    print(f'\n=== SCÉNARIO B NON MARCHAND {year} ===')
    folder = PROCESSED / str(year)
    paths = (folder / f'cles_non_marchandes_com_dep_reg_{year}.csv',
             folder / f'nuites_non_marchandes_{year}.csv')
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(f'Exécuter les scripts 46 et 50 avant le 52 : {p}')
    keys = pd.read_csv(paths[0], dtype=str, encoding='utf-8-sig')
    totals = pd.read_csv(paths[1], dtype=str, encoding='utf-8-sig')
    if not {'annee', 'admin_level', 'geocode', *(v[1] for v in CATEGORIES.values())}.issubset(keys):
        raise ValueError('Colonnes manquantes dans les clés du script 50')
    if not {'annee', 'categorie', 'nuites', 'TRAVEL_DEST'}.issubset(totals):
        raise ValueError('Colonnes manquantes dans les totaux du script 46')
    if not keys['annee'].eq(str(year)).all() or not totals['annee'].eq(str(year)).all():
        raise ValueError('Année incohérente')
    if not totals['TRAVEL_DEST'].eq('_T').all():
        raise ValueError('Le périmètre des totaux a changé : réexaminer le scénario')
    if len(totals) != 2 or set(totals['categorie']) != set(CATEGORIES):
        raise ValueError('Il faut exactement famille_amis et residences_secondaires')
    if keys.duplicated(['admin_level', 'geocode']).any():
        raise ValueError('Doublon COM/DEP/REG')

    com = keys.loc[keys['admin_level'].eq('COM')].copy()
    if com.empty:
        raise ValueError('Aucune commune disponible')
    com['geocode'] = com['geocode'].str.strip().str.upper().str.zfill(5)
    if com['geocode'].duplicated().any():
        raise ValueError('Communes en double')
    com['code_departement'] = com['geocode'].str[:2]
    com['code_region'] = com['code_departement'].map(DEP_REG)
    if com['code_region'].isna().any():
        raise ValueError('Commune sans région reconnue')

    ratio, domestic, all_dest = ratios[year]
    print(f'  Coefficient France+outre-mer : {domestic / 1e6:.1f} / '
          f'{all_dest / 1e6:.1f} = {ratio:.6%}')
    adjusted = {}
    for category, (prefix, weight) in CATEGORIES.items():
        total_source = float(float_col(totals.loc[totals['categorie'].eq(category)], 'nuites').iloc[0])
        estimated_total = total_source * ratio
        adjusted[category] = estimated_total
        weights = float_col(com, weight).to_numpy(dtype=float)
        if not np.isclose(weights.sum(), 1, atol=1e-7, rtol=0):
            raise ValueError(f'Poids {weight} ne somment pas à 1')
        weights = weights / weights.sum()
        com[prefix + '_year'] = estimated_total * weights
        for month in MONTHS:
            com[prefix + '_' + month] = com[prefix + '_year'] / 12
        assert_equal(com[prefix + '_year'].sum(), estimated_total, f'{year} {prefix} TOTAL AJUSTÉ')
        print(f'  {category} : {total_source / 1e6:.2f} M -> {estimated_total / 1e6:.2f} M (scénario)')

    parts = [com[['geocode', 'admin_level', *VALUE_COLS]].copy()]
    for level, col in [('DEP', 'code_departement'), ('REG', 'code_region')]:
        aggregate = com.groupby(col, as_index=False)[VALUE_COLS].sum()
        aggregate = aggregate.rename(columns={col: 'geocode'})
        aggregate.insert(1, 'admin_level', level)
        parts.append(aggregate[['geocode', 'admin_level', *VALUE_COLS]])
    result = pd.concat(parts, ignore_index=True)
    # Contrôles INTÉGRÉS : chaque colonne, les 3 niveaux, et les 12 mois.
    for metric in VALUE_COLS:
        a = result.loc[result.admin_level.eq('COM'), metric].sum()
        b = result.loc[result.admin_level.eq('DEP'), metric].sum()
        c = result.loc[result.admin_level.eq('REG'), metric].sum()
        assert_equal(a, b, f'{year} {metric}: COM = DEP')
        assert_equal(a, c, f'{year} {metric}: COM = REG')
    for category, (prefix, _) in CATEGORIES.items():
        assert_equal(result.loc[result.admin_level.eq('COM'), prefix+'_year'].sum(),
                     adjusted[category], f'{year} {prefix}: conservation de la source ajustée')
        for level in ('COM', 'DEP', 'REG'):
            slice_ = result[result.admin_level.eq(level)]
            sum_months = slice_[[prefix + '_' + month for month in MONTHS]].sum(axis=1)
            if not np.allclose(sum_months, slice_[prefix + '_year'], atol=0.01, rtol=0):
                raise ValueError(f'[ECHEC SOMMES] {year} {level} {prefix}: 12 mois != annuel')
    actual_levels = result.groupby('admin_level').size().to_dict()
    if actual_levels.get('DEP') != 96 or actual_levels.get('REG') != 13:
        raise ValueError(f'Nombre de DEP/REG incorrect : {actual_levels}')

    result['annee'] = year
    result['scenario'] = 'EXPLORATOIRE_NON_VALIDE'
    result['hypothese_geographique'] = ('ratio_tous_hebergements_FRANCE_PLUS_OUTREMER_'
                                        'applique_aux_categories_et_alloue_en_metropole')
    result['hypothese_mensuelle'] = 'UNIFORME_1_SUR_12_NON_OBSERVEE'
    result['perimetre_destination'] = 'FRANCE_PLUS_OUTREMER_PROXY_METROPOLE'
    result['ratio_france_outremer'] = ratio
    result['source_totaux'] = 'DS_SUIVI_DDE_TOUR_TRAVEL_DEST__T'
    result['source_ratio'] = 'DS_SUIVI_DDE_TOUR_TRAVEL_DEST_250_sur__T'
    for meta in ('annee_reference_population', 'statut_population',
                 'annee_reference_logements', 'statut_logements'):
        if meta in keys.columns:
            values = keys[meta].dropna().unique()
            result[meta] = values[0] if len(values) == 1 else ''

    output = folder / f'scenario_non_marchand_com_dep_reg_{year}.csv'
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, sep=';', index=False, encoding='utf-8-sig')
    notes = folder / f'scenario_non_marchand_hypotheses_{year}.txt'
    notes.write_text(
        f'CAFÉ {year} — SCÉNARIO B EXPLORATOIRE NON VALIDÉ\n'
        f'Ratio de destination : France + outre-mer = {domestic:.0f}; toutes destinations = {all_dest:.0f}; coefficient = {ratio:.9f}.\n'
        'Hypothèse : appliquer le ratio global tous hébergements aux deux types non marchands.\n'
        'Limite : France + outre-mer N’EST PAS la France métropolitaine.\n'
        'Allocation fictive des nuitées ajustées vers les communes métropolitaines selon les clés 49/50.\n'
        'Mensualisation uniforme 1/12 sans observation saisonnière.\n'
        'Contrôles intégrés : 12 mois = année ; COM = DEP = REG ; totaux = source × ratio.\n'
        'Ne pas qualifier ces chiffres de données INSEE communales observées.\n',
        encoding='utf-8')
    print(f'  [OK] SOMMES : COM = DEP = REG ; somme 12 mois = annuel ; {actual_levels}')
    print(f'  [OK] Export : {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, choices=YEARS, help='Une année (défaut : toutes)')
    args = parser.parse_args()
    ratios = destination_ratios()
    for year in ((args.year,) if args.year else YEARS):
        perform(year, ratios)
    print('\n=== SCÉNARIO B : 2022-2025 TERMINÉ (NON VALIDÉ GÉOGRAPHIQUEMENT) ===')

if __name__ == '__main__':
    main()
