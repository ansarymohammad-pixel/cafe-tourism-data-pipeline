"""CAFÉ — 53 : ventilation mensuelle du tourisme marchand, 2022–2025.

Sources : script 51 (annuel COM/DEP/REG), DS_TOUR_FREQ (séries mensuelles).
Hôtels : profil mensuel départemental, sinon régional, sinon national métropolitain.
Autres : profil régional, sinon national métropolitain.
Campings : haute saison seulement dans le script 51 ; aucun mois fabriqué.
Les mois sont des estimations par pondération, pas des mesures communales.
"""
from pathlib import Path
import argparse
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'data' / 'raw' / 'tourisme' / 'frequentation_brut.csv'
PROCESSED = ROOT / 'data' / 'processed' / 'tourisme'
YEARS = (2022, 2023, 2024, 2025)
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june',
          'july', 'august', 'september', 'october', 'november', 'december')
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
DEP_TO_REG = {dep: reg for reg, departments in REGIONS.items()
              for dep in departments.split()}
CATS = {'hotel': ('I551', 'nuites_hotels_estimees'),
        'other': ('I552', 'nuites_autres_estimees')}


def numeric(series):
    return pd.to_numeric(series.astype('string').str.replace(',', '.', regex=False),
                         errors='coerce')


def lire_mensuel():
    if not RAW.is_file():
        raise FileNotFoundError(f'Source mensuelle INSEE absente : {RAW}')
    cols = ['GEO', 'FREQ', 'TIME_PERIOD', 'ACTIVITY', 'TOUR_MEASURE',
            'TOUR_RESID', 'UNIT_LOC_RANKING', 'HOTEL_STA', 'EQUIP',
            'OBS_VALUE_NIVEAU', 'OBS_STATUS', 'UNIT_MULT', 'SEASONALITY']
    raw = pd.read_csv(RAW, usecols=cols, dtype=str, low_memory=False)
    mask = (raw['FREQ'].eq('M') & raw['ACTIVITY'].isin(['I551', 'I552'])
            & raw['TOUR_MEASURE'].eq('NIGHT_SPENT')
            & raw['TOUR_RESID'].eq('_T')
            & raw['UNIT_LOC_RANKING'].eq('_T')
            & raw['HOTEL_STA'].eq('_T')
            & raw['EQUIP'].eq('_Z')
            & raw['SEASONALITY'].eq('_Z')
            & raw['OBS_STATUS'].isin(['A', 'P'])
            & raw['TIME_PERIOD'].str.fullmatch(
                r'(2022|2023|2024|2025)-(0[1-9]|1[0-2])', na=False))
    d = raw.loc[mask].copy()
    d['annee'] = d['TIME_PERIOD'].str[:4].astype(int)
    d['mois'] = d['TIME_PERIOD'].str[-2:].astype(int)
    d['niveau'] = d['GEO'].str.extract(r'-(DEP|REG)-', expand=False)
    d['code'] = d['GEO'].str.extract(r'-(?:DEP|REG)-([0-9]{2}|2A|2B)$', expand=False)
    fm = d['GEO'].str.endswith('-FRANCE-FM', na=False)
    d.loc[fm, 'niveau'] = 'FM'
    d.loc[fm, 'code'] = 'FM'
    d = d.loc[(d['niveau'].eq('FM'))
              | (d['niveau'].eq('REG') & d['code'].isin(REGIONS))
              | (d['niveau'].eq('DEP') & d['code'].isin(DEP_TO_REG))].copy()
    d['valeur'] = numeric(d['OBS_VALUE_NIVEAU']) * (10.0 ** numeric(d['UNIT_MULT']))
    d = d.loc[d['valeur'].notna() & d['valeur'].ge(0)].copy()
    if d.duplicated(['annee', 'ACTIVITY', 'niveau', 'code', 'mois']).any():
        raise ValueError('Profils mensuels : observations en double après filtres INSEE')
    return d


def construire_profils(d):
    """Garder uniquement 12 mois complets, sommer strictement positivement."""
    profils = {}
    for (year, activity, level, code), group in d.groupby(
            ['annee', 'ACTIVITY', 'niveau', 'code']):
        if set(group['mois']) != set(range(1, 13)) or len(group) != 12:
            continue
        group = group.sort_values('mois')
        total = group['valeur'].sum()
        if not np.isfinite(total) or total <= 0:
            continue
        poids = group['valeur'].to_numpy(dtype=float) / total
        profils[(year, activity, level, code)] = (
            poids, 'P' if group['OBS_STATUS'].eq('P').any() else 'A')
    return profils


def profil_pour(profils, year, activity, dep, region):
    if activity == 'I551':
        choices = [('DEP', dep), ('REG', region), ('FM', 'FM')]
    else:
        choices = [('REG', region), ('FM', 'FM')]
    for level, code in choices:
        result = profils.get((year, activity, level, code))
        if result is not None:
            weights, quality = result
            return weights, level, quality
    return None, 'INDISPONIBLE', None


def lire_annuel(year):
    source = PROCESSED / str(year) / f'tourisme_marchand_com_dep_reg_{year}.csv'
    if not source.is_file():
        raise FileNotFoundError(f'Exécuter le script 51 : {source}')
    df = pd.read_csv(source, dtype=str, encoding='utf-8-sig', low_memory=False)
    required = {'annee', 'admin_level', 'geocode', 'code_departement',
                'code_region', 'nuites_hotels_estimees',
                'nuites_campings_estimees', 'nuites_autres_estimees'}
    if missing := required - set(df.columns):
        raise ValueError(f'Script 51 : colonnes manquantes : {sorted(missing)}')
    if df.empty or not df['annee'].eq(str(year)).all():
        raise ValueError(f'Script 51 : année incohérente {year}')
    if not df['admin_level'].isin(['COM', 'DEP', 'REG']).all():
        raise ValueError('Niveau géographique inattendu')
    if df.duplicated(['admin_level', 'geocode']).any():
        raise ValueError('Territoires en double')
    for col in ('nuites_hotels_estimees', 'nuites_campings_estimees',
                'nuites_autres_estimees'):
        df[col] = numeric(df[col])
        if df[col].lt(0).any():
            raise ValueError(f'Nuitées négatives : {col}')
    return df


def effectuer(year, profiles):
    print(f'\n=== SCRIPT 53 — MENSUEL {year} ===')
    df = lire_annuel(year)
    # La logique utilise le territoire de chaque ligne COM/DEP/REG.
    # Un DEP suit son profil propre ; tous ses COM le même profil.
    # Une REG peut avoir un profil distinct de ses DEP : on reconstruit donc
    # DEP/REG par sommation des estimations communales pour garder l'additivité.
    com = df.loc[df['admin_level'].eq('COM')].copy()
    if com.empty or com['geocode'].duplicated().any():
        raise ValueError('Communes absentes ou en double dans le script 51')
    if com['code_departement'].isna().any() or com['code_region'].isna().any():
        raise ValueError('Codes département / région manquants')

    report = []
    for prefix, (activity, annual) in CATS.items():
        month_cols = [f'{prefix}_nights_{m}' for m in MONTHS]
        weights_cache = {}
        for dep, sub in com.groupby('code_departement'):
            reg = sub['code_region'].iloc[0]
            weights_cache[dep] = profil_pour(profiles, year, activity, dep, reg)
        for month_col in month_cols:
            com[month_col] = np.nan
        com[f'{prefix}_profil_source'] = 'INDISPONIBLE'
        com[f'{prefix}_profil_statut_insee'] = pd.NA
        for dep, sub in com.groupby('code_departement'):
            weights, method, quality = weights_cache[dep]
            if weights is None:
                continue
            valid = sub[annual].notna()
            idx = sub.index[valid]
            if len(idx):
                values = com.loc[idx, annual].to_numpy(dtype=float)
                for k, month_col in enumerate(month_cols):
                    com.loc[idx, month_col] = values * weights[k]
                com.loc[idx, f'{prefix}_profil_source'] = method
                com.loc[idx, f'{prefix}_profil_statut_insee'] = quality
        # Contrôle de conservation sur toutes les communes renseignées.
        complete = com[month_cols].notna().all(axis=1)
        if complete.ne(com[annual].notna()).any():
            raise ValueError(f'Profil mensuel manquant pour une commune {prefix}')
        differences = (com.loc[complete, month_cols].sum(axis=1) -
                       com.loc[complete, annual]).abs()
        if len(differences) and differences.max() > 0.01:
            raise ValueError(f'12 mois ≠ annuel : {prefix}')
        report.append({'annee': year, 'categorie': prefix,
                       'communes_mensuelles': int(complete.sum()),
                       'communes_total': len(com),
                       'profil_dep': int(com[f'{prefix}_profil_source'].eq('DEP').sum()),
                       'profil_reg': int(com[f'{prefix}_profil_source'].eq('REG').sum()),
                       'profil_france': int(com[f'{prefix}_profil_source'].eq('FM').sum())})

    # Campings : ne pas réinterpréter un total haute saison comme annuel.
    for m in MONTHS:
        com[f'camping_nights_{m}'] = np.nan
    com['camping_mensuel_statut'] = 'NON_ESTIME_HAUTE_SAISON'

    generated = [f'{prefix}_nights_{m}' for prefix in ('hotel', 'other', 'camping')
                 for m in MONTHS]
    # Repartir du fichier annuel du 51 pour garder ses statuts, taux de
    # couverture et totaux annuels ; calculer les mois depuis COM seulement.
    all_frames = [com]
    for level, code_col in [('DEP', 'code_departement'), ('REG', 'code_region')]:
        base = df.loc[df['admin_level'].eq(level)].copy()
        grouped = com.groupby(code_col)[generated].agg(
            lambda col: col.sum() if col.notna().all() else np.nan
        )
        base = base.merge(grouped, left_on='geocode', right_index=True,
                          how='left', validate='one_to_one')
        for prefix in ('hotel', 'other'):
            months = [f'{prefix}_nights_{m}' for m in MONTHS]
            valid = base[months].notna().all(axis=1)
            if valid.ne(base[CATS[prefix][1]].notna()).any():
                raise ValueError(f'{year} {level}: couverture des mois incohérente ({prefix})')
            err = (base.loc[valid, months].sum(axis=1) -
                   base.loc[valid, CATS[prefix][1]]).abs()
            if len(err) and err.max() > 0.01:
                raise ValueError(f'{year} {level}: 12 mois ≠ annuel ({prefix})')
        base['hotel_profil_source'] = 'AGREGATION_COM'
        base['other_profil_source'] = 'AGREGATION_COM'
        base['hotel_profil_statut_insee'] = pd.NA
        base['other_profil_statut_insee'] = pd.NA
        base['camping_mensuel_statut'] = 'NON_ESTIME_HAUTE_SAISON'
        all_frames.append(base)
    output = pd.concat(all_frames, ignore_index=True)
    output['methode_mensuelle'] = ('profils mensuels observés INSEE, '
                                   'application aux nuitées annuelles estimées; '
                                   'campings haute saison non ventilés')
    dest = PROCESSED / str(year) / f'tourisme_marchand_mensuel_com_dep_reg_{year}.csv'
    profile_path = PROCESSED / str(year) / f'controle_profils_mensuels_{year}.csv'
    output.to_csv(dest, index=False, encoding='utf-8-sig')
    pd.DataFrame(report).to_csv(profile_path, index=False, encoding='utf-8-sig')
    for row in report:
        print(f"  {row['categorie']}: {row['communes_mensuelles']:,} communes | "
              f"profil DEP {row['profil_dep']:,}, REG {row['profil_reg']:,}, "
              f"FM {row['profil_france']:,}")
    print('  Export :', dest)
    print('  Contrôle :', profile_path)
    print('  Camping : haute saison uniquement ; mois laissés vides')


def main():
    parser = argparse.ArgumentParser(description='CAFÉ 53 : ventilation 2022-2025')
    parser.add_argument('--year', type=int, choices=YEARS)
    args = parser.parse_args()
    raw = lire_mensuel()
    profiles = construire_profils(raw)
    print(f'Profils mensuels INSEE complets : {len(profiles)}')
    for year in ([args.year] if args.year else YEARS):
        effectuer(year, profiles)
    print('\n=== SCRIPT 53 TERMINÉ ===')


if __name__ == '__main__':
    main()
