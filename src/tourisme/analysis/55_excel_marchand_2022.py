"""Corrige UNIQUEMENT l'onglet MARCHAND_2022 du classeur CAFÉ.

Usage (depuis C:/Users/ansar/Desktop/cafe):
  python -m pip install lxml
  python src/tourisme/56_corriger_marchand.py

Place les 2 fichiers sources a la racine du projet ou dans le dossier de livraison.
Les colonnes sans observations restent vides, dont les mois des campings.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import csv
import re
import zipfile
from lxml import etree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data' / 'processed' / 'tourisme' / 'livraison_cafe_2022'
SOURCE = next((p for p in (ROOT / 'tourisme_marchand_2022_final.csv', BASE / 'tourisme_marchand_2022_final.csv') if p.exists()), None)
CLASSEUR = BASE / 'CAFE_TOURISME_2022_DEUX_TABLEAUX.xlsx'
SORTIE = BASE / 'CAFE_TOURISME_2022_MARCHAND_CORRIGE.xlsx'
N = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december')
COLUMNS = (['geocode', 'admin_level'] + [f'{type_}_nights_{period}' for type_ in ('hotel', 'camping', 'other') for period in ('year', *MONTHS)])
CSV_C = {'hotel': 'hotels', 'camping': 'campings', 'other': 'autres'}


def xlcol(num):
    result = ''
    while num:
        num, r = divmod(num - 1, 26)
        result = chr(65 + r) + result
    return result


def normalize(code, level):
    code = str(code).strip().upper()
    if level == 'COM' and re.fullmatch(r'\d{1,5}', code):
        return code.zfill(5)
    if level == 'DEP' and re.fullmatch(r'\d{1,3}', code):
        return code.zfill(2)
    if level == 'REG' and code.isdigit():
        return code.zfill(2)
    return code


def get_value(cell, strings):
    if cell is None:
        return None
    v = cell.find(N + 'v')
    if cell.get('t') == 's' and v is not None:
        return strings[int(v.text)]
    if v is not None:
        return v.text
    return ''.join(cell.itertext()) if cell.get('t') == 'inlineStr' else None


def put_value(cell, val, text=False):
    for ch in list(cell):
        if ch.tag in (N + 'v', N + 'is', N + 'f'):
            cell.remove(ch)
    if val is None or val == '':
        cell.attrib.pop('t', None)
        return
    if text:
        cell.set('t', 'inlineStr')
        is_ = ET.SubElement(cell, N + 'is')
        ET.SubElement(is_, N + 't').text = str(val)
    else:
        cell.attrib.pop('t', None)
        ET.SubElement(cell, N + 'v').text = str(float(val))


def make_row(row, data, index):
    row.set('r', str(index))
    existing = {re.match(r'[A-Z]+', c.get('r')).group(): c for c in row if c.tag == N + 'c'}
    new = []
    for j, name in enumerate(COLUMNS):
        col = xlcol(j + 1)
        cell = existing.get(col)
        if cell is None:
            cell = ET.Element(N + 'c')
            # Retenir le format numerique de la ligne d'origine.
            if j >= 2 and existing.get('C') is not None and existing['C'].get('s'):
                cell.set('s', existing['C'].get('s'))
        cell.set('r', f'{col}{index}')
        if j == 0:
            put_value(cell, normalize(data['geocode'], data['admin_level']), text=True)
        elif j == 1:
            put_value(cell, data['admin_level'], text=True)
        else:
            prefix, suffix = name.split('_nights_')
            oldname = CSV_C[prefix] + ('' if suffix == 'year' else '_' + suffix)
            raw = data.get(oldname, '')
            put_value(cell, raw, text=False)
        new.append(cell)
    for item in list(row):
        if item.tag == N + 'c':
            row.remove(item)
    row.extend(new)
    return row


def main():
    if SOURCE is None:
        raise FileNotFoundError('tourisme_marchand_2022_final.csv introuvable')
    if not CLASSEUR.exists():
        raise FileNotFoundError(CLASSEUR)
    BASE.mkdir(parents=True, exist_ok=True)
    with SOURCE.open(newline='', encoding='utf-8-sig') as f:
        lines = list(csv.DictReader(f, delimiter=';'))
    if not lines or any(x['admin_level'] not in ('COM', 'DEP', 'REG') for x in lines):
        raise ValueError('Structure CSV inattendue')
    with zipfile.ZipFile(CLASSEUR) as src:
        shared = ET.fromstring(src.read('xl/sharedStrings.xml'))
        strings = [''.join(si.itertext()) for si in shared]
        sheet = ET.fromstring(src.read('xl/worksheets/sheet1.xml'))
        sd = sheet.find(N + 'sheetData')
        rows = sd.findall(N + 'row')
        template = {}
        for row in rows[1:]:
            cells = {re.match(r'[A-Z]+', c.get('r')).group(): c for c in row if c.tag == N + 'c'}
            level = get_value(cells.get('B'), strings)
            geo = get_value(cells.get('A'), strings)
            if level and geo:
                template[(level, normalize(geo, level))] = row
        old_com = next(r for (lev, _), r in template.items() if lev == 'COM')
        old_dep = next(r for (lev, _), r in template.items() if lev == 'DEP')
        old_reg = next(r for (lev, _), r in template.items() if lev == 'REG')
        newrows = [rows[0]]
        done = set()
        for item in sorted(lines, key=lambda x: (('COM', 'DEP', 'REG').index(x['admin_level']), normalize(x['geocode'], x['admin_level']))):
            key = (item['admin_level'], normalize(item['geocode'], item['admin_level']))
            if key in done:
                raise ValueError(f'Doublon dans le CSV : {key}')
            done.add(key)
            chosen = deepcopy(template.get(key, {'COM': old_com, 'DEP': old_dep, 'REG': old_reg}[item['admin_level']]))
            newrows.append(make_row(chosen, item, len(newrows) + 1))
        sd[:] = newrows
        dim = sheet.find(N + 'dimension')
        if dim is not None:
            dim.set('ref', f'A1:AO{len(newrows)}')
        for af in sheet.findall('.//' + N + 'autoFilter'):
            if af.get('ref', '').startswith('A1:'):
                af.set('ref', f'A1:AO{len(newrows)}')
        replacement = ET.tostring(sheet, encoding='UTF-8', xml_declaration=True)
        # Mettre a jour uniquement les controles du tableau marchand.
        control = ET.fromstring(src.read('xl/worksheets/sheet3.xml'))
        controls = control.find(N + 'sheetData')
        for controlrow in controls:
            rid = int(controlrow.get('r'))
            if rid not in (2, 3, 4):
                continue
            level = {2: 'COM', 3: 'DEP', 4: 'REG'}[rid]
            subset = [line for line in lines if line['admin_level'] == level]
            missing = sum(sum(not line.get(CSV_C[type_] + ('' if suffix == 'year' else '_' + suffix), '').strip()
                              for type_ in ('hotel', 'camping', 'other')
                              for suffix in ('year', *MONTHS)) for line in subset)
            available_annual = sum(sum(bool(line.get(CSV_C[type_], '').strip())
                                       for type_ in ('hotel', 'camping', 'other')) for line in subset)
            mapping = {'C': len(subset), 'D': len(set(normalize(line['geocode'], level) for line in subset)),
                       'E': missing, 'F': available_annual}
            for cell in controlrow:
                if cell.tag == N + 'c':
                    letter = re.match(r'[A-Z]+', cell.get('r')).group()
                    if letter in mapping:
                        put_value(cell, mapping[letter])
        control_bytes = ET.tostring(control, encoding='UTF-8', xml_declaration=True)
        with zipfile.ZipFile(SORTIE, 'w') as dest:
            for item in src.infolist():
                updated = {'xl/worksheets/sheet1.xml': replacement, 'xl/worksheets/sheet3.xml': control_bytes}
                dest.writestr(item, updated.get(item.filename, src.read(item.filename)))
    print('Classeur corrigé :', SORTIE)
    print('Lignes marchand :', dict(Counter(x['admin_level'] for x in lines)))
    print('Non marchand : conservé sans modification.')
    print('Campings : mois non renseignés dans le CSV, laissés vides.')
    print('CONTROLES : lignes marchand mises à jour ; contrôles non marchand inchangés.')


if __name__ == '__main__':
    main()
