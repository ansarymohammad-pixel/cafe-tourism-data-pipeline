"""CAFÉ — estimation communale des nuitées non marchandes 2022.

Clés de répartition : population municipale 2023 et résidences secondaires 2023.
Les résultats sont des estimations, pas des observations communales.
"""
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / 'data' / 'processed' / 'tourisme'
OUTPUT = PROCESSED / 'livraison_cafe_2022'
POP_FILE = ROOT / 'population_brute.csv'
RES_FILE = PROCESSED / 'residences_secondaires_2023_communes.csv'
CAP_FILE = PROCESSED / 'capacites_metro_2022.csv'
FAMILY_FR = 398_500_000
SECONDARY_FR = 117_300_000
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june',
          'july', 'august', 'september', 'october', 'november', 'december')


def code_commune(value):
    if pd.isna(value):
        return None
    match = re.fullmatch(r'(?:\d{4}-COM-)?(\d{2}[0-9AB]\d{2})', str(value).strip().upper())
    return match.group(1) if match else None


def colonne(columns, possibilities):
    lookup = {str(c).strip().upper(): c for c in columns}
    return next((lookup[x.upper()] for x in possibilities if x.upper() in lookup), None)


def require_columns(cols, names, source):
    if any(c is None for c in names):
        raise ValueError(f'Colonnes manquantes dans {source}. Disponibles : {list(cols)}')


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in (POP_FILE, RES_FILE, CAP_FILE):
        if not path.is_file():
            raise FileNotFoundError(path)

    print('[1/5] Référentiel communal CAFÉ')
    caps = pd.read_csv(CAP_FILE, dtype=str, low_memory=False)
    cg = colonne(caps.columns, ('GEO', 'geocode', 'CODGEO'))
    require_columns(caps.columns, (cg,), CAP_FILE)
    codes = caps[cg].map(code_commune)
    if codes.isna().any():
        print(f'  Attention : {codes.isna().sum()} codes non communaux ignorés')
    communes = pd.DataFrame({'geocode': codes.dropna().drop_duplicates().values})
    print(f'  {len(communes):,} communes')

    print('[2/5] Résidences secondaires 2023')
    raw_res = pd.read_csv(RES_FILE, dtype=str, low_memory=False)
    rg = colonne(raw_res.columns, ('GEO', 'geocode', 'CODGEO'))
    rv = colonne(raw_res.columns, ('OBS_VALUE', 'OBS_VALUE_NIVEAU', 'residences_2023'))
    require_columns(raw_res.columns, (rg, rv), RES_FILE)
    res = pd.DataFrame({'geocode': raw_res[rg].map(code_commune),
                        'residences_2023': pd.to_numeric(raw_res[rv], errors='coerce')})
    res = res.dropna(subset=['geocode'])
    if res.geocode.duplicated().any():
        raise ValueError('Doublons dans les résidences secondaires : vérifier la source.')

    print('[3/5] Population municipale 2023')
    header = pd.read_csv(POP_FILE, nrows=0).columns
    pg = colonne(header, ('GEO', 'CODGEO'))
    py = colonne(header, ('TIME_PERIOD', 'ANNEE'))
    pm = colonne(header, ('POPREF_MEASURE', 'POP_MEASURE', 'POPULATION_MEASURE'))
    pv = colonne(header, ('OBS_VALUE_NIVEAU', 'OBS_VALUE'))
    require_columns(header, (pg, py, pm, pv), POP_FILE)
    parts = []
    for chunk in pd.read_csv(POP_FILE, usecols=[pg, py, pm, pv], dtype=str, chunksize=100_000):
        keep = (chunk[py].eq('2023') & chunk[pm].eq('PMUN') &
                chunk[pg].str.contains('-COM-', regex=False, na=False))
        if keep.any():
            part = chunk.loc[keep, [pg, pv]].copy()
            part.columns = ['geocode', 'population_2023']
            part['geocode'] = part['geocode'].map(code_commune)
            parts.append(part.dropna(subset=['geocode']))
    if not parts:
        raise ValueError('Aucune observation PMUN communale 2023 dans population_brute.csv')
    pop = pd.concat(parts, ignore_index=True)
    pop['population_2023'] = pd.to_numeric(pop['population_2023'], errors='coerce')
    if pop.geocode.duplicated().any():
        raise ValueError('Doublons PMUN 2023 : vérifier les dimensions de population_brute.csv')

    print('[4/5] Jointure et vérification de couverture')
    df = communes.merge(pop, on='geocode', how='left', validate='one_to_one')
    df = df.merge(res, on='geocode', how='left', validate='one_to_one')
    missing = df.population_2023.isna() | df.residences_2023.isna()
    print('  Population manquante :', int(df.population_2023.isna().sum()))
    print('  Résidences manquantes :', int(df.residences_2023.isna().sum()))
    if missing.any():
        diagnostic = OUTPUT / 'DIAGNOSTIC_NON_MARCHAND_2022.csv'
        df.loc[missing].to_csv(diagnostic, index=False, encoding='utf-8-sig')
        raise ValueError(f'{missing.sum()} communes non appariées. Diagnostic : {diagnostic}. '
                         'Aucune allocation réalisée : harmoniser les millésimes géographiques.')
    if ((df[['population_2023', 'residences_2023']] < 0).any().any() or
            df[['population_2023', 'residences_2023']].isna().any().any()):
        raise ValueError('Valeurs invalides dans les clés de répartition.')
    total_pop = df.population_2023.sum()
    total_res = df.residences_2023.sum()
    if total_pop <= 0 or total_res <= 0:
        raise ValueError('Dénominateur nul.')

    print('[5/5] Estimations annuelles et export')
    df['family_nights_year'] = FAMILY_FR * df.population_2023 / total_pop
    df['secondary_residence_year'] = SECONDARY_FR * df.residences_2023 / total_res
    df['admin_level'] = 4  # convention à confirmer avec CAFÉ
    for month in MONTHS:
        df[f'family_nights_{month}'] = pd.NA
        df[f'secondary_residence_{month}'] = pd.NA
    fields = ['geocode', 'admin_level', 'family_nights_year', 'secondary_residence_year']
    fields += [f'{prefix}_{month}' for month in MONTHS
               for prefix in ('family_nights', 'secondary_residence')]
    output = OUTPUT / 'TOURISME_NON_MARCHAND_2022_COMMUNES.csv'
    df[fields].to_csv(output, index=False, encoding='utf-8-sig')
    print('  Nuitées famille / amis :', round(df.family_nights_year.sum()))
    print('  Nuitées résidences secondaires :', round(df.secondary_residence_year.sum()))
    print('  Fichier :', output)
    print('  MÉTHODE : allocation 2022 selon des clés 2023, résultats estimés.')
    print('  À VALIDER : cohérence périmètre national métropolitain / communes retenues.')


if __name__ == '__main__':
    main()
