from pathlib import Path
import argparse
import pandas as pd
import numpy as np

# CAFÉ - Désagrégation statistique des nuitées 2022-2025
# Hôtels/campings : département -> communes
# Autres hébergements : région -> communes
# Camping = haute saison (ne pas assimiler à un total annuel homogène).

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / 'data' / 'processed' / 'tourisme'
YEARS = (2022, 2023, 2024, 2025)

# Correspondance des départements métropolitains avec les régions actuelles.
REGIONS = {
    '11': '75 77 78 91 92 93 94 95',
    '24': '18 28 36 37 41 45',
    '27': '21 25 39 58 70 71 89 90',
    '28': '14 27 50 61 76',
    '32': '02 59 60 62 80',
    '44': '08 10 51 52 54 55 57 67 68 88',
    '52': '44 49 53 72 85',
    '53': '22 29 35 56',
    '75': '16 17 19 23 24 33 40 47 64 79 86 87',
    '76': '09 11 12 30 31 32 34 46 48 65 66 81 82',
    '84': '01 03 07 15 26 38 42 43 63 69 73 74',
    '93': '04 05 06 13 83 84',
    '94': '2A 2B',
}
DEP_TO_REG = {dep: reg for reg, deps in REGIONS.items() for dep in deps.split()}
assert len(DEP_TO_REG) == 96

CONFIG = (
    ('hotels', 'code_departement', 'Hotels', 'capacite_hotels'),
    ('campings', 'code_departement', 'Campings', 'capacite_campings'),
    ('autres', 'code_region', 'Autres', 'capacite_autres'),
)


def read_csv(path, required):
    if not path.is_file():
        raise FileNotFoundError(f'Source manquante : {path}')
    df = pd.read_csv(path, dtype=str, encoding='utf-8-sig', low_memory=False)
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f'{path.name} : colonnes manquantes {sorted(missing)}')
    return df


def territory_code(geo, kind):
    # Supporte 2026-DEP-75, 2024-REG-84, DEP-75, REG-84, etc.
    geo = geo.astype('string').str.strip().str.upper()
    return geo.str.extract(rf'(?:^|-)'+kind+r'-([0-9]{2}|2A|2B)$', expand=False)


def prepare_nights(year):
    path = PROCESSED / str(year) / f'nuites_{year}.csv'
    n = read_csv(path, ('niveau', 'GEO', 'Hotels', 'Campings', 'Autres'))
    if 'annee' in n.columns:
        years = n['annee'].dropna().unique().tolist()
        if years != [str(year)]:
            raise ValueError(f'{path.name} : années inattendues {years}')
    n['code_departement'] = territory_code(n['GEO'], 'DEP')
    n['code_region'] = territory_code(n['GEO'], 'REG')
    for category in ('Hotels', 'Campings', 'Autres'):
        n[category] = pd.to_numeric(n[category], errors='coerce')
    return n


def prepare_capacities(year):
    path = PROCESSED / str(year) / f'capacites_communales_{year}.csv'
    cols = ('code_commune', 'code_departement', 'capacite_hotels',
            'capacite_campings', 'capacite_autres')
    c = read_csv(path, cols)
    if 'annee_capacite' in c.columns:
        years = c['annee_capacite'].dropna().unique().tolist()
        if years != [str(year)]:
            raise ValueError(f'{path.name} : années de capacités inattendues {years}')
    c['code_commune'] = c['code_commune'].str.upper().str.strip()
    c['code_departement'] = c['code_departement'].str.upper().str.strip()
    if c['code_commune'].duplicated().any():
        raise ValueError(f'{year} : codes communaux dupliqués')
    c['code_region'] = c['code_departement'].map(DEP_TO_REG)
    if c['code_region'].isna().any():
        bad = c.loc[c['code_region'].isna(), 'code_departement'].unique().tolist()
        raise ValueError(f'{year} : départements sans région {bad}')
    for col in ('capacite_hotels', 'capacite_campings', 'capacite_autres'):
        c[col] = pd.to_numeric(c[col], errors='coerce')
        if c[col].lt(0).any():
            raise ValueError(f'{year} : capacités négatives dans {col}')
    return c


def allocate(c, n, category, group_col, night_col, capacity_col):
    groups = n.loc[n[group_col].notna(), [group_col, night_col]].copy()
    if groups[group_col].duplicated().any():
        raise ValueError(f'{category} : plusieurs totaux pour un même territoire')
    groups = groups.rename(columns={night_col: 'total_observe'})
    merged = c[[group_col, capacity_col]].merge(groups, on=group_col, how='left', validate='many_to_one')
    capacity = merged[capacity_col]
    capacity_sum = capacity.groupby(merged[group_col]).transform('sum', min_count=1)
    incomplete = capacity.isna().groupby(merged[group_col]).transform('any')
    valid = merged['total_observe'].notna() & (capacity_sum > 0) & (~incomplete)
    estimates = (merged['total_observe'] * capacity / capacity_sum).where(valid)
    result_col = f'nuites_{category}_estimees'
    status_col = f'statut_{category}'
    c[result_col] = estimates.to_numpy()
    c[status_col] = np.select(
        [merged['total_observe'].isna(), incomplete, capacity_sum.isna() | capacity_sum.le(0)],
        ['nuitées territoriales absentes', 'capacités communales incomplètes', 'capacité territoriale nulle'],
        default='estimé',
    )

    # Contrôle des totaux sur les seuls territoires entièrement répartis.
    check = c.loc[c[status_col].eq('estimé')].groupby(group_col)[result_col].sum()
    ref = groups.set_index(group_col)['total_observe'].reindex(check.index)
    if not np.allclose(check.to_numpy(), ref.to_numpy(), rtol=1e-10, atol=1e-5):
        raise ValueError(f'{category} : échec du contrôle de conservation des nuitées')
    nb_groups = int(check.shape[0])
    nb_communities = int(c[result_col].notna().sum())
    print(f'  {category}: {nb_groups} territoires répartis, {nb_communities} communes estimées')
    return c


def run_year(year):
    print(f'\n=== RÉPARTITION {year} ===')
    capacities = prepare_capacities(year)
    nights = prepare_nights(year)
    for category, group_col, night_col, capacity_col in CONFIG:
        capacities = allocate(capacities, nights, category, group_col, night_col, capacity_col)
    capacities.insert(0, 'annee_nuitees', year)
    capacities['methode'] = 'Nuitées observées réparties proportionnellement aux capacités communales de même année'
    capacities['nuites_total_mixte_estime'] = capacities[
        ['nuites_hotels_estimees', 'nuites_campings_estimees', 'nuites_autres_estimees']
    ].sum(axis=1, min_count=3)
    # ATTENTION : total mixte = hôtels et autres sur année complète, campings haute saison.
    capacities['periode_total_mixte'] = 'mixte : campings haute saison uniquement'
    out_dir = PROCESSED / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f'nuites_communales_estimees_{year}.csv'
    columns = ['annee_nuitees', 'code_region', 'code_departement', 'code_commune',
               'capacite_hotels', 'capacite_campings', 'capacite_autres',
               'nuites_hotels_estimees', 'nuites_campings_estimees', 'nuites_autres_estimees',
               'statut_hotels', 'statut_campings', 'statut_autres',
               'nuites_total_mixte_estime', 'periode_total_mixte', 'methode']
    capacities[columns].to_csv(path, index=False, encoding='utf-8-sig')
    print('  Fichier créé :', path)


def main():
    parser = argparse.ArgumentParser(description='Estimation communale des nuitées CAFÉ')
    parser.add_argument('--year', type=int, choices=YEARS, help='Sinon toutes les années')
    args = parser.parse_args()
    years = [args.year] if args.year is not None else YEARS
    for year in years:
        run_year(year)
    print('\n=== RÉPARTITION TERMINÉE ===')


if __name__ == '__main__':
    main()
