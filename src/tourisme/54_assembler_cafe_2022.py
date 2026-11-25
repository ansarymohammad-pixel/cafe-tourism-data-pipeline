"""Assembler les deux CSV Databricks CAFÉ 2022 en un classeur Excel.
Exécution : python src/tourisme/54_assembler_cafe_2022.py
Dépendances : pip install pandas openpyxl
"""
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data' / 'processed' / 'tourisme' / 'livraison_cafe_2022'
MONTHS = ['january','february','march','april','may','june','july','august','september','october','november','december']
SOURCES = {
    'MARCHAND_2022': 'marchand_2022_final.csv',
    'NON_MARCHAND_2022': 'non_marchand_2022_final.csv',
}
PREFIXES = {
    'MARCHAND_2022': ['hotel_nights','camping_nights','other_nights'],
    'NON_MARCHAND_2022': ['family_nights','secondary_residence'],
}

def locate(filename):
    candidates = [ROOT / filename, ROOT / 'data' / 'raw' / 'tourisme' / filename,
                  ROOT / 'data' / 'processed' / 'tourisme' / filename, OUT / filename]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(f'Fichier introuvable : {filename}. Place-le à la racine du projet CAFÉ.')

def prepare(sheet_name, filename):
    df = pd.read_csv(locate(filename), sep=';', dtype={'geocode': 'string'}, low_memory=False)
    df.columns = df.columns.str.strip()
    required = ['geocode','admin_level']
    if any(c not in df.columns for c in required):
        raise ValueError(f'{filename} : colonnes geocode/admin_level manquantes')
    df['geocode'] = df['geocode'].str.strip()
    df['admin_level'] = df['admin_level'].astype('string').str.strip().str.upper()
    df['geocode'] = df['geocode'].where(df['admin_level'] != 'COM', df['geocode'].str.zfill(5))
    df['geocode'] = df['geocode'].where(df['admin_level'] != 'DEP', df['geocode'].str.zfill(2))
    df['geocode'] = df['geocode'].where(df['admin_level'] != 'REG', df['geocode'].str.zfill(2))
    columns = ['geocode','admin_level']
    for prefix in PREFIXES[sheet_name]:
        columns.extend([prefix + '_year'] + [prefix + '_' + month for month in MONTHS])
    for c in columns:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[columns].copy()
    for c in columns[2:]:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['_ordre'] = df['admin_level'].map({'COM':0,'DEP':1,'REG':2}).fillna(3)
    df = df.sort_values(['_ordre','geocode'], kind='stable').drop(columns='_ordre')
    return df

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    datasets = {sheet: prepare(sheet, filename) for sheet, filename in SOURCES.items()}
    controls = []
    for sheet, df in datasets.items():
        for level in ['COM','DEP','REG']:
            part = df[df.admin_level.eq(level)]
            controls.append({'tableau':sheet,'niveau':level,'territoires':len(part),
                             'codes_uniques':part.geocode.nunique(),
                             'valeurs_manquantes':int(part.iloc[:,2:].isna().sum().sum()),
                             'nuitées_annuelles_disponibles':int(part.filter(regex='_year$').notna().sum().sum())})
    notes = pd.DataFrame([
        {'point':'Sources','description':'Fichiers CSV Databricks fournis ; valeurs non recalculées'},
        {'point':'Périmètre','description':'Les deux fichiers peuvent couvrir des géographies différentes ; aucune suppression automatique'},
        {'point':'Données manquantes','description':'Les cellules absentes restent vides, jamais remplacées par zéro'},
        {'point':'Géocodes','description':'Codes INSEE stockés comme texte afin de conserver les zéros initiaux'},
        {'point':'Statut','description':'Livraison de travail ; vérifier sources, méthodes et cohérence géographique avant validation'},
    ])
    target = OUT / 'CAFE_TOURISME_2022_DEUX_TABLEAUX.xlsx'
    with pd.ExcelWriter(target, engine='openpyxl') as writer:
        for name, df in datasets.items():
            df.to_excel(writer, sheet_name=name, index=False, na_rep='')
        pd.DataFrame(controls).to_excel(writer, sheet_name='CONTROLES', index=False)
        notes.to_excel(writer, sheet_name='METHODOLOGIE', index=False)
    wb = load_workbook(target)
    for ws in wb.worksheets:
        ws.freeze_panes = 'C2' if ws.title in datasets else 'A2'
        ws.auto_filter.ref = ws.dimensions
        ws.row_dimensions[1].height = 30
        for cell in ws[1]:
            cell.fill = PatternFill('solid', fgColor='163A5F')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(wrap_text=True, vertical='center')
        for col in range(1, ws.max_column+1):
            ws.column_dimensions[get_column_letter(col)].width = 18 if col > 2 else (16 if col == 1 else 17)
        if ws.title in datasets:
            for row in ws.iter_rows(min_row=2, min_col=1, max_col=1):
                row[0].number_format = '@'
            for row in ws.iter_rows(min_row=2, min_col=3):
                for cell in row:
                    if isinstance(cell.value, (float,int)):
                        cell.number_format = '#,##0.00'
    wb.save(target)
    print('Fichier créé :', target)
    for c in controls:
        print(f"{c['tableau']} {c['niveau']}: {c['territoires']} territoires, {c['valeurs_manquantes']} cellules manquantes")

if __name__ == '__main__':
    main()
