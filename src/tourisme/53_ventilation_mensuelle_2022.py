"""CAFÉ 2022 — ventilation mensuelle régionale des nuitées marchandes.

Entrées : fréquentation INSEE brute + tableau marchand annuel provisoire.
Sortie : tableau COM/DEP/REG avec mois estimés hôtels et autres hébergements.
Les campings restent sans total annuel et sans allocation communale.
Les chiffres mensuels sont des estimations, non des observations communales.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data' / 'processed' / 'tourisme' / 'livraison_cafe_2022'
RAW = ROOT / 'data' / 'raw' / 'tourisme' / 'frequentation_brut.csv'
SOURCE = BASE / 'TOURISME_MARCHAND_2022_COM_DEP_REG_PROVISOIRE.csv'
OUTPUT = BASE / 'TOURISME_MARCHAND_2022_MENSUEL_PROVISOIRE.csv'
PROFILES = BASE / 'PROFILS_MENSUELS_INSEE_2022.csv'
MONTHS = ['january','february','march','april','may','june','july','august','september','october','november','december']
# Correspondances administratives métropolitaines officielles (codes INSEE des régions)
REG_DEPS = {
 '11':'75 77 78 91 92 93 94 95',
 '24':'18 28 36 37 41 45',
 '27':'21 25 39 58 70 71 89 90',
 '28':'14 27 50 61 76',
 '32':'02 59 60 62 80',
 '44':'08 10 51 52 54 55 57 67 68 88',
 '52':'44 49 53 72 85',
 '53':'22 29 35 56',
 '75':'16 17 19 23 24 33 40 47 64 79 86 87',
 '76':'09 11 12 30 31 32 34 46 48 65 66 81 82',
 '84':'01 03 07 15 26 38 42 43 63 69 73 74',
 '93':'04 05 06 13 83 84',
 '94':'2A 2B',
}
DEP_TO_REG = {dep:reg for reg, deps in REG_DEPS.items() for dep in deps.split()}

def department(code):
    code = str(code).upper()
    return code[:2] if code.startswith(('2A','2B')) else (code[:3] if code.startswith(('97','98')) else code[:2])

def main():
    for path in (RAW, SOURCE):
        if not path.exists():
            raise FileNotFoundError(f'Fichier introuvable : {path}')
    print('1/3 — Extraction des profils mensuels INSEE 2022')
    cols = ['GEO','FREQ','TIME_PERIOD','TOUR_MEASURE','ACTIVITY','TOUR_RESID',
            'UNIT_LOC_RANKING','HOTEL_STA','EQUIP','OBS_VALUE_NIVEAU','OBS_STATUS','UNIT_MULT']
    raw = pd.read_csv(RAW, usecols=cols, dtype=str, low_memory=False)
    raw = raw.loc[
        raw.FREQ.eq('M') & raw.TIME_PERIOD.str.fullmatch(r'2022-(0[1-9]|1[0-2])', na=False)
        & raw.TOUR_MEASURE.eq('NIGHT_SPENT') & raw.ACTIVITY.isin(['I551','I552'])
        & raw.TOUR_RESID.eq('_T') & raw.UNIT_LOC_RANKING.eq('_T')
        & raw.HOTEL_STA.eq('_T') & raw.EQUIP.eq('_Z')
        & raw.OBS_STATUS.eq('A') & raw.UNIT_MULT.eq('3')
        & raw.GEO.str.fullmatch(r'\d{4}-(REG-\d{2}|FRANCE-FM)', na=False)
    ].copy()
    raw['value'] = pd.to_numeric(raw.OBS_VALUE_NIVEAU, errors='coerce') * 1000
    raw['month'] = raw.TIME_PERIOD.str[-2:].astype(int)
    raw['region'] = raw.GEO.str.extract(r'REG-(\d{2})', expand=False)
    if raw.duplicated(['GEO','ACTIVITY','month']).any():
        raise ValueError('Séries mensuelles ambiguës : doublons après filtrage.')
    profiles = []
    for activity in ['I551','I552']:
        subset = raw.loc[raw.ACTIVITY.eq(activity)]
        national = subset[subset.GEO.str.endswith('FRANCE-FM')].set_index('month').value
        if set(national.index) != set(range(1,13)) or national.isna().any() or national.sum() <= 0:
            raise ValueError(f'Profil national incomplet : {activity}')
        national = national / national.sum()
        for region in sorted(REG_DEPS):
            r = subset[subset.region.eq(region)].set_index('month').value
            if set(r.index) == set(range(1,13)) and r.notna().all() and r.sum() > 0:
                weights, method = r/r.sum(), 'profil régional INSEE 2022'
            else:
                weights, method = national, 'repli sur profil national INSEE 2022'
            for month in range(1,13):
                profiles.append({'region':region,'activity':activity,'month':month,
                                 'weight':float(weights.loc[month]),'method':method})
    p = pd.DataFrame(profiles)
    p.to_csv(PROFILES, index=False, encoding='utf-8-sig')
    print('2/3 — Application aux communes, agrégation aux départements/régions')
    annual = pd.read_csv(SOURCE, dtype={'geocode':str,'admin_level':str}, low_memory=False)
    com = annual.loc[annual.admin_level.eq('COM')].copy()
    if com.empty or com.geocode.duplicated().any():
        raise ValueError('Tableau annuel : communes absentes ou dupliquées.')
    com['dep'] = com.geocode.map(department)
    com['region'] = com.dep.map(DEP_TO_REG)
    if com.region.isna().any():
        raise ValueError(f'Communes sans région : {com.loc[com.region.isna(), "geocode"].head(10).tolist()}')
    for activity, prefix in [('I551','hotel_nights'),('I552','other_nights')]:
        pivot = p[p.activity.eq(activity)].pivot(index='region', columns='month', values='weight')
        weights = pivot.reindex(com.region).to_numpy()
        yearly = pd.to_numeric(com[f'{prefix}_year'], errors='coerce').to_numpy()
        if pd.isna(yearly).any():
            raise ValueError(f'Annuel manquant : {prefix}')
        for m, name in enumerate(MONTHS):
            com[f'{prefix}_{name}'] = yearly * weights[:,m]
    # Ne pas fabriquer des nuitées camping : annuel indisponible.
    for name in MONTHS:
        com[f'camping_nights_{name}'] = pd.NA
    com['camping_nights_year'] = pd.NA
    metrics = [f'{prefix}_{name}' for prefix in ('hotel_nights','other_nights') for name in MONTHS]
    annual_cols = ['hotel_nights_year','other_nights_year']
    def aggregate(key, level):
        grouped = com.groupby(key, as_index=False)[annual_cols+metrics].sum()
        grouped = grouped.rename(columns={key:'geocode'})
        grouped.insert(1,'admin_level',level)
        return grouped
    dep = aggregate('dep','DEP')
    reg = aggregate('region','REG')
    result = pd.concat([com.drop(columns=['dep','region']),dep,reg], ignore_index=True)
    result['camping_nights_year'] = pd.NA
    for name in MONTHS:
        result[f'camping_nights_{name}'] = pd.NA
    # Vérification des agrégations et des 12 mois par territoire.
    print('3/3 — Contrôles et export')
    for prefix in ('hotel_nights','other_nights'):
        months = [f'{prefix}_{m}' for m in MONTHS]
        err = (result[months].sum(axis=1)-result[f'{prefix}_year']).abs().max()
        if err > 0.01:
            raise ValueError(f'Écart mois/annuel : {prefix}, {err}')
        for level in ('COM','DEP','REG'):
            total = result.loc[result.admin_level.eq(level),f'{prefix}_year'].sum()
            print(f'{level} {prefix} : {total:,.0f} nuitées')
    result.to_csv(OUTPUT,index=False,encoding='utf-8-sig')
    print(f'Communes : {len(com)} | départements : {len(dep)} | régions : {len(reg)}')
    print('Sortie :',OUTPUT)
    print('Profils :',PROFILES)
    print('ATTENTION : mensuels estimés, camping non renseigné, couverture géographique provisoire.')

if __name__ == '__main__':
    main()
