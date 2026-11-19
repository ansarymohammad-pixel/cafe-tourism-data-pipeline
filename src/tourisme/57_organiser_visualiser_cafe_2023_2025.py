"""CAFÉ : organiser et visualiser six tableaux 2023-2025.

Installation : python -m pip install XlsxWriter
Execution (dans cafe/) : python src/tourisme/57_organiser_visualiser_cafe_2023_2025.py
Option : --input-dir C:/chemin/vers/csv --output-dir C:/chemin/vers/sorties

Aucune donnée n'est estimée ou modifiée : les CSV sont repris tels quels.
"""
from __future__ import annotations

import argparse
import csv
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path
import xlsxwriter

YEARS = (2023, 2024, 2025)
TYPES = ('MARCHAND', 'NON_MARCHAND')
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june',
          'july', 'august', 'september', 'october', 'november', 'december')
LABELS = {
    'hotel_nights_year': 'Hôtels',
    'camping_nights_year': 'Campings*',
    'other_nights_year': 'Autres hébergements',
    'family_nights_year': 'Famille / amis',
    'secondary_residence_year': 'Résidences secondaires',
}
LEVEL_ORDER = {'COM': 0, 'DEP': 1, 'REG': 2}


def input_path(folder: Path, year: int, category: str) -> Path:
    filename = f'CAFE_TOURISME_{year}_{category}_V2.csv'
    alternatives = [folder / filename, folder / str(year) / filename,
                    folder / 'data' / 'raw' / 'tourisme' / filename]
    for path in alternatives:
        if path.is_file():
            return path
    raise FileNotFoundError(f'Fichier manquant : {filename}\nDossier recherché : {folder}')


def as_number(text: str):
    raw = (text or '').strip()
    if not raw:
        return None
    try:
        val = float(raw.replace(',', '.'))
        return val if math.isfinite(val) else None
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument('--input-dir', type=Path, default=default_root)
    parser.add_argument('--output-dir', type=Path,
                        default=default_root / 'data' / 'final' / 'tourisme')
    parser.add_argument('--full', action='store_true',
                        help='Ajouter les 6 tableaux complets (plus lent et volumineux)')
    parser.add_argument('--no-copy', action='store_true',
                        help='Ne pas copier les CSV dans data/processed/tourisme/annee/')
    args = parser.parse_args()
    inputs = args.input_dir.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    paths = {(y, t): input_path(inputs, y, t) for y in YEARS for t in TYPES}
    outfile = out / 'CAFE_TOURISME_2023_2025.xlsx'

    wb = xlsxwriter.Workbook(str(outfile), {'constant_memory': True})
    wb.set_properties({'title': 'CAFÉ | Tourisme 2023–2025',
                       'subject': 'Consolidation des fichiers marchands et non marchands',
                       'comments': 'Données d origine conservées; controles et visualisations sans correction automatique.'})
    navy, blue, teal, pale = '#16324F', '#1769AA', '#0F766E', '#E8F1F8'
    title = wb.add_format({'bold': True, 'font_size': 19, 'font_color': navy})
    sub = wb.add_format({'font_color': '#64748B', 'font_size': 10})
    header = wb.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': navy,
                            'text_wrap': True, 'valign': 'vcenter', 'bottom': 1, 'bottom_color': blue})
    header2 = wb.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': teal})
    normal = wb.add_format({'num_format': '#,##0.00;[Red](#,##0.00);–'})
    code = wb.add_format({'num_format': '@'})
    missing = wb.add_format({'font_color': '#A1A1AA'})
    integer = wb.add_format({'num_format': '#,##0'})
    big = wb.add_format({'bold': True, 'font_color': navy, 'font_size': 14,
                         'num_format': '#,##0'})
    warn = wb.add_format({'font_color': '#9A3412', 'bg_color': '#FFF4E5', 'text_wrap': True})

    summaries = {}
    # Un seul passage par fichier : lignes + calcul de controles.
    for year in YEARS:
        for category in TYPES:
            source = paths[(year, category)]
            if not args.no_copy:
                root = default_root / 'data' / 'processed' / 'tourisme' / str(year)
                root.mkdir(parents=True, exist_ok=True)
                dest = root / source.name
                if source.resolve() != dest.resolve():
                    shutil.copy2(source, dest)
            ws = wb.add_worksheet(f'{category}_{year}') if args.full else None
            counts = Counter()
            totals = defaultdict(float)
            monthly = defaultdict(float)
            blanks = Counter()
            diff = defaultdict(float)
            duplicate = 0
            seen = set()
            bad_numeric = 0
            with source.open('r', encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream, delimiter=';')
                fields = reader.fieldnames or []
                required = {'geocode', 'admin_level'}
                if not required.issubset(fields):
                    raise ValueError(f'{source.name}: colonnes geographiques manquantes: {fields[:10]}')
                metric_years = [x for x in fields if x.endswith('_year')]
                prefixes = {x: x[:-5] for x in metric_years}
                if ws is not None:
                    for idx, name in enumerate(fields):
                        ws.write(0, idx, name, header)
                    ws.set_row(0, 36)
                    ws.set_column(0, 0, 13, code)
                    ws.set_column(1, 1, 13)
                    ws.set_column(2, len(fields) - 1, 18, normal)
                    ws.freeze_panes(1, 2)
                for ridx, row in enumerate(reader, start=1):
                    level = (row.get('admin_level') or '').strip().upper()
                    geocode = (row.get('geocode') or '').strip()
                    counts[level] += 1
                    key = (level, geocode)
                    duplicate += key in seen
                    seen.add(key)
                    if ridx > 1048575:
                        raise ValueError(f'{source.name}: limite de lignes Excel depassee')
                    if ws is not None:
                        ws.write_string(ridx, 0, geocode, code)
                        ws.write_string(ridx, 1, level)
                    rowvals = {}
                    for cidx, field in enumerate(fields[2:], start=2):
                        raw = (row.get(field) or '').strip()
                        num = as_number(raw)
                        rowvals[field] = num
                        if num is None:
                            blanks[field] += 1
                            if raw:
                                bad_numeric += 1
                                if ws is not None: ws.write_string(ridx, cidx, raw)
                            # Une cellule vide reste vide, jamais convertie en zero.
                        else:
                            if ws is not None: ws.write_number(ridx, cidx, num, normal)
                            if field in metric_years:
                                totals[(level, field)] += num
                            if field.endswith(tuple('_' + m for m in MONTHS)):
                                monthly[(level, field)] += num
                    for field, prefix in prefixes.items():
                        yearly = rowvals.get(field)
                        monthvals = [rowvals.get(prefix + '_' + m) for m in MONTHS]
                        if yearly is not None and all(v is not None for v in monthvals):
                            diff[(level, field)] += sum(monthvals) - yearly
                if ws is not None:
                    ws.autofilter(0, 0, ridx if 'ridx' in locals() else 0, len(fields) - 1)
            summaries[(year, category)] = dict(counts=counts, totals=totals,
                                               monthly=monthly, missing=blanks,
                                               discrepancy=diff, duplicates=duplicate,
                                               invalid=bad_numeric, fields=fields)
            print(f'{year} {category}: {sum(counts.values()):,} lignes / {dict(counts)}')

    # Page d accueil et graphiques : aucune colonne brute n est retouchee.
    dash = wb.add_worksheet('SYNTHESE')
    dash.hide_gridlines(2)
    dash.set_tab_color(teal)
    dash.set_column('A:A', 13)
    dash.set_column('B:B', 25)
    dash.set_column('C:E', 17)
    dash.set_column('F:M', 13)
    dash.merge_range('A1:H2', 'CAFÉ | Tourisme 2023–2025', title)
    dash.merge_range('A3:H3', 'Synthèse issue des 6 CSV fournis · nuitées calculées à partir des lignes REG', sub)
    dash.write('A5', 'Année', header)
    dash.write('B5', 'Catégorie', header)
    dash.write('C5', 'COM', header)
    dash.write('D5', 'DEP', header)
    dash.write('E5', 'REG', header)
    records = []
    rr = 5
    for year in YEARS:
        for t in TYPES:
            s = summaries[(year, t)]
            dash.write_number(rr, 0, year)
            dash.write(rr, 1, t.replace('_', ' ').capitalize())
            for col, lev in [(2, 'COM'), (3, 'DEP'), (4, 'REG')]:
                dash.write_number(rr, col, s['counts'][lev], integer)
            rr += 1
            for var in [c for c in s['fields'] if c.endswith('_year')]:
                records.append((year, t, var, s['totals'][('REG', var)]))

    dash.write('A14', 'Nuitées nationales par catégorie (somme des régions)', header2)
    dash.write_row('A15', ['Catégorie', '2023', '2024', '2025'], header)
    order = list(LABELS)
    for i, metric in enumerate(order, start=15):
        dash.write(i, 0, LABELS[metric])
        typ = 'MARCHAND' if metric in ('hotel_nights_year', 'camping_nights_year', 'other_nights_year') else 'NON_MARCHAND'
        for j, year in enumerate(YEARS, 1):
            dash.write_number(i, j, summaries[(year, typ)]['totals'][('REG', metric)], big)
    chart = wb.add_chart({'type': 'column'})
    for j, year in enumerate(YEARS, 1):
        chart.add_series({'name': ['SYNTHESE', 14, j],
                          'categories': ['SYNTHESE', 15, 0, 19, 0],
                          'values': ['SYNTHESE', 15, j, 19, j]})
    chart.set_title({'name': 'Nuitées par catégorie et année'})
    chart.set_y_axis({'name': 'Nuitées', 'num_format': '0,," M"'})
    chart.set_legend({'position': 'bottom'})
    chart.set_size({'width': 800, 'height': 385})
    dash.insert_chart('F5', chart)
    dash.merge_range('A23:H24',
       'Attention : les valeurs des campings peuvent correspondre à une saison observée et non à 12 mois complets. '
       'Les données des CSV sont conservées sans correction automatique. Les ecarts COM/DEP/REG et annee/mois sont controles dans CONTROLES.', warn)

    ctrl = wb.add_worksheet('CONTROLES')
    ctrl.freeze_panes(1, 2)
    columns = ['année', 'type', 'indicateur', 'nb_COM', 'nb_DEP', 'nb_REG',
               'somme_COM', 'somme_DEP', 'somme_REG', 'écart_COM_REG',
               'écart_DEP_REG', 'écart_mois_REG', 'cellules_vides', 'doublons_geo', 'valeurs_invalides']
    ctrl.write_row(0, 0, columns, header)
    ctrl.set_row(0, 40)
    ctrl.set_column('A:B', 17)
    ctrl.set_column('C:C', 27)
    ctrl.set_column('D:O', 20)
    idx = 1
    for year in YEARS:
        for t in TYPES:
            s = summaries[(year, t)]
            for metric in [c for c in s['fields'] if c.endswith('_year')]:
                vals = [year, t, metric, s['counts']['COM'], s['counts']['DEP'], s['counts']['REG'],
                        s['totals'][('COM', metric)], s['totals'][('DEP', metric)],
                        s['totals'][('REG', metric)],
                        s['totals'][('COM', metric)] - s['totals'][('REG', metric)],
                        s['totals'][('DEP', metric)] - s['totals'][('REG', metric)],
                        s['discrepancy'][('REG', metric)],
                        sum(s['missing'][f] for f in s['fields'] if f == metric or f.startswith(metric[:-5] + '_')),
                        s['duplicates'], s['invalid']]
                for j, value in enumerate(vals):
                    if isinstance(value, (float, int)):
                        ctrl.write_number(idx, j, value, integer if j in (0, 3, 4, 5, 12, 13, 14) else normal)
                    else:
                        ctrl.write_string(idx, j, value)
                idx += 1
    ctrl.autofilter(0, 0, idx-1, len(columns)-1)
    ctrl.conditional_format(1, 9, idx-1, 11, {'type': 'cell', 'criteria': '!=', 'value': 0,
                                              'format': wb.add_format({'bg_color': '#FFF3CD'})})

    method = wb.add_worksheet('METHODOLOGIE')
    method.set_column('A:A', 30)
    method.set_column('B:B', 90)
    method.write_row('A1', ['Point', 'Description'], header)
    notes = [
        ('Sources', 'Six fichiers CSV CAFÉ TOURISME 2023–2025 V2 fournis. Sources INSEE détaillées à documenter selon pipeline.'),
        ('Structure', 'COM = commune; DEP = département; REG = région. Chaque année et type possède son onglet.'),
        ('Données', 'Les valeurs sont transcrites sans recalcul, sans imputation et sans remplacer les blancs par zéro.'),
        ('Indicateurs', 'Nuitées hôtels, campings, autres hébergements; famille/amis; résidences secondaires.'),
        ('Données REG', 'Les totaux nationaux de SYNTHESE sont les sommes des lignes REG et non une série nationale vérifiée.'),
        ('Campings', 'Vérifier la période annuelle couverte (souvent avril à septembre). Ne pas assimiler automatiquement ce total à 12 mois.'),
        ('Contrôle spatial', 'Comparer COM, DEP et REG ; les écarts ne sont pas corrigés automatiquement.'),
        ('Contrôle temporel', 'Écart mois-année calculé lorsque les 12 valeurs mensuelles existent pour une ligne.'),
        ('Évolution géographique', 'Les périmètres communaux peuvent changer entre années; comparaison territoriale à harmoniser.'),
        ('Publication', 'Données CSV organisées dans data/processed/tourisme/<annee>, livrable dans data/final/tourisme.'),
    ]
    for i, (a,b) in enumerate(notes, 1):
        method.write(i,0,a);method.write(i,1,b)
    method.freeze_panes(1,0)
    wb.close()
    print(f'\nEXCEL : {outfile}')
    print('Onglets: SYNTHESE, CONTROLES, METHODOLOGIE' + (', six tableaux annuels' if args.full else ' (CSV preserves separement)'))


if __name__ == '__main__':
    main()
