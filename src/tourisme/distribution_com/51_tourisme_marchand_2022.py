"""CAFÉ — tourisme marchand 2022, livraison rapide COM/DEP/REG.

Estimation PROVISOIRE. Hôtels et autres : totaux nationaux annuels fournis
(à confirmer dans la source INSEE). Camping : haute saison uniquement,
JAMAIS convertie en total annuel. Mois sans données observées = vides.
Répartition spatiale : capacité par type si colonne identifiable, sinon
population 2023 (proxy dérivé du fichier non marchand). Ce n'est pas une
observation communale. Géographie : celle du non marchand provisoire.
"""
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data' / 'processed' / 'tourisme'
OUT = BASE / 'livraison_cafe_2022'
NON = OUT / 'TOURISME_NON_MARCHAND_2022_COM_DEP_REG_PROVISOIRE.csv'
CAP = BASE / 'capacites_metro_2022.csv'
FAMILY_TOTAL = 398_500_000
HOTEL_TOTAL = 207_301_000  # valeur arrondie, à vérifier avec source nationale
OTHER_TOTAL = 96_343_000  # valeur arrondie, à vérifier avec source nationale
CAMPING_HIGH_SEASON = 135_708_000  # NON annuel, information documentaire seulement
MONTHS = ('january','february','march','april','may','june','july',
          'august','september','october','november','december')

def col(cols, names):
    lookup = {str(c).strip().lower(): c for c in cols}
    return next((lookup[n.lower()] for n in names if n.lower() in lookup), None)

def code(x):
    if pd.isna(x): return None
    s = str(x).strip().upper()
    m = re.fullmatch(r'(?:\d{4}-COM-)?((?:\d{2}|2[AB])\d{3})', s)
    return m.group(1) if m else None

def find_weight_column(columns, kind):
    """Only accept explicit capacity columns; never confuse nights with beds."""
    patterns = {
        'hotel': (r'(?:hotel|h[oô]tel)',),
        'camping': (r'(?:camping|plein.air)',),
        'other': (r'(?:autre|other|collectif|touris.*residen|residen.*touris)',),
    }
    candidates=[]
    for c in columns:
        s=str(c).lower()
        if not any(re.search(p,s) for p in patterns[kind]): continue
        if any(t in s for t in ('nuitee','nuitée','night','taux','rate','part','share','annee','year')): continue
        if any(t in s for t in ('capac','lit','bed','place','chambre','room','emplacement','unit')):
            candidates.append(c)
    return candidates[0] if len(candidates)==1 else None

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not NON.exists():
        raise FileNotFoundError(f'Exécuter d’abord le script 50 : {NON}')
    print('1/3 — Reprise des communes et des correspondances géographiques validées')
    nm = pd.read_csv(NON, dtype={'geocode':str, 'admin_level':str})
    for c in ('geocode','admin_level','family_nights_year'):
        if c not in nm.columns: raise ValueError(f'Colonne absente du fichier non marchand : {c}')
    com = nm.loc[nm.admin_level.eq('COM'), ['geocode','family_nights_year']].copy()
    if com.empty: raise ValueError('Aucune commune COM dans le fichier non marchand.')
    if com.geocode.duplicated().any(): raise ValueError('Doublons COM.')
    com['population_proxy'] = pd.to_numeric(com.family_nights_year,errors='coerce')
    if com.population_proxy.isna().any() or com.population_proxy.sum()<=0:
        raise ValueError('Poids population indisponibles.')

    # Geographic crosswalk from capacity file; fallback to a documented national DEP->REG map.
    if not CAP.exists(): raise FileNotFoundError(CAP)
    caps = pd.read_csv(CAP,dtype=str,low_memory=False)
    gc=col(caps.columns,('geocode','GEO','CODGEO','code_commune'))
    dc=col(caps.columns,('code_departement','departement','DEP'))
    rc=col(caps.columns,('code_region','region','REG'))
    if gc is None: raise ValueError(f'Code commune absent de {CAP.name}: {list(caps.columns)}')
    caps['geocode_norm']=caps[gc].map(code)
    caps=caps.dropna(subset=['geocode_norm'])
    if dc and rc:
        geo=caps[['geocode_norm',dc,rc]].drop_duplicates('geocode_norm').rename(columns={'geocode_norm':'geocode',dc:'dep',rc:'reg'})
        geo['dep']=geo.dep.astype(str).str.replace(r'^\d{4}-DEP-','',regex=True).str.upper().str.zfill(2)
        geo['reg']=geo.reg.astype(str).str.replace(r'^\d{4}-REG-','',regex=True).str.zfill(2)
    else:
        geo=caps[['geocode_norm']].drop_duplicates().rename(columns={'geocode_norm':'geocode'})
        geo['dep']=geo.geocode.str[:2]
        geo.loc[geo.geocode.str.startswith('97'),'dep']=geo.geocode.str[:3]
        geo['reg']=pd.NA
    # Robust department-region mapping (metropolitan INSEE regions since 2016).
    regions={
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
    dep_to_reg={d:r for r,ds in regions.items() for d in ds.split()}
    geo['reg']=geo.dep.map(dep_to_reg)  # do not trust invalid source region labels
    com=com.merge(geo[['geocode','dep','reg']],on='geocode',how='left',validate='one_to_one')
    missing_geo=com.dep.isna() | com.reg.isna()
    if missing_geo.any():
        com.loc[missing_geo].to_csv(OUT/'MARCHAND_COMMUNES_SANS_GEOGRAPHIE.csv',index=False,encoding='utf-8-sig')
        print(f'Communes sans géographie exclues : {missing_geo.sum()}')
        com=com.loc[~missing_geo].copy()
    if com.empty: raise ValueError('Aucune commune géographiquement appariée.')

    print('2/3 — Répartition provisoire des nuitées annuelles')
    methods=[]
    for kind,total,target in [('hotel',HOTEL_TOTAL,'hotel_nights_year'),('other',OTHER_TOTAL,'other_nights_year')]:
        wc=find_weight_column(caps.columns,kind)
        weights=None
        if wc:
            temp=caps[['geocode_norm',wc]].copy()
            temp[wc]=pd.to_numeric(temp[wc].astype(str).str.replace(',','.',regex=False),errors='coerce')
            temp=temp.groupby('geocode_norm')[wc].sum(min_count=1)
            candidate=com.geocode.map(temp).fillna(0)
            if candidate.ge(0).all() and candidate.sum()>0:
                weights=candidate
        if weights is None:
            weights=com.population_proxy
            method='population 2023 (proxy)'
        else:
            method=f'capacité 2022 : {wc}'
        com[target]=total*weights/weights.sum()
        methods.append((target,method))
    # Only high-season camping observations available, not a yearly figure.
    com['camping_nights_year']=pd.NA
    cols=['hotel_nights_year','camping_nights_year','other_nights_year']
    out=[]
    for level,key in [('COM','geocode'),('DEP','dep'),('REG','reg')]:
        if level=='COM': part=com[['geocode']+cols].copy()
        else:
            part=com.groupby(key,as_index=False)[['hotel_nights_year','other_nights_year']].sum().rename(columns={key:'geocode'})
            part['camping_nights_year']=pd.NA
        part.insert(1,'admin_level',level)
        out.append(part)
    result=pd.concat(out,ignore_index=True)
    ordered=['geocode','admin_level']
    for kind in ('hotel','camping','other'):
        ordered.append(f'{kind}_nights_year')
        for m in MONTHS:
            c=f'{kind}_nights_{m}'
            result[c]=pd.NA
            ordered.append(c)
    result=result[ordered]
    output=OUT/'TOURISME_MARCHAND_2022_COM_DEP_REG_PROVISOIRE.csv'
    result.to_csv(output,index=False,encoding='utf-8-sig')
    metadata=OUT/'METHODOLOGIE_MARCHAND_2022.txt'
    metadata.write_text('\n'.join([
      'CAFÉ 2022 — TOURISME MARCHAND, ESTIMATION PROVISOIRE',
      'Les nuitées COM/DEP/REG ne sont pas des mesures observées localement.',
      f'Hôtels annuel national : {HOTEL_TOTAL:,} (arrondi, source à vérifier).',
      f'Autres annuel national : {OTHER_TOTAL:,} (arrondi, source à vérifier).',
      f'Campings : {CAMPING_HIGH_SEASON:,} haute saison seulement ; annuel NON RENSEIGNÉ.',
      'Mois non renseignés faute de série mensuelle complète et validée.',
      'Répartition géographique alignée sur le référentiel non marchand provisoire.',
      *[f'{k} : {v}' for k,v in methods],
      'Les capacités sont des clés de répartition, pas des nuitées.',
      'Validation requise avant publication définitive.',
    ]),encoding='utf-8')
    print('3/3 — Contrôle')
    for level in ('COM','DEP','REG'):
        x=result.loc[result.admin_level.eq(level)]
        assert abs(x.hotel_nights_year.sum()-HOTEL_TOTAL)<0.01
        assert abs(x.other_nights_year.sum()-OTHER_TOTAL)<0.01
        print(f'{level}: {len(x)} territoires | hôtels {x.hotel_nights_year.sum():,.0f} | autres {x.other_nights_year.sum():,.0f} | camping annuel manquant')
    print('Méthodes :',methods)
    print('Livraison :',output)
    print('Note :',metadata)

if __name__=='__main__':
    main()
