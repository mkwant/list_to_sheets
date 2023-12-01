from pathlib import Path

import pandas as pd
from rich import print

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', 10)

EXCEL_FILE = Path('bowielist_12-11-23.xlsx')
SHEET_NAMES = [
    '7"-off',
    '7"-related',
    '12"-off',
    '12"-pro',
    'LP-off',
    'LP-related',
    'LP-pirate',
    'CD-single',
    'CD-pro'
]
CTY_ORDER = [
    'UK',
    'AU',
    'BEL',
    'CRO',
    'CZ',
    'DEN',
    'FI',
    'FRA',
    'GER',
    'GR',
    'IRE',
    'IS',
    'ITA',
    'NL',
    'NOR',
    'POL',
    'POR',
    'SCA',
    'SPA',
    'SWE',
    'SWI',
    'RUS',
    'TUR',
    'YUG',
    'USA',
    'CAN',
    'ARG',
    'BRA',
    'CHI',
    'COL',
    'CR',
    'GUA',
    'MEX',
    'PAR',
    'PER',
    'SV',
    'VEN',
    'JAP',
    'IND',
    'HK',
    'KOR',
    'MAL',
    'PHI',
    'SEA',
    'SIN',
    'TAI',
    'THA',
    'ISR',
    'AUS',
    'NZ',
    'SA',
    'ANG',
    'RHO',
    'ZIM',
    'EU'
]


def list_sorter(excel_file: Path, sheet_name: str, output_dir: Path, cty_order_list: list[str]):
    """Sort an Excel sheet based on the countries in an ordered country list."""
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    output_dir.mkdir(parents=True, exist_ok=True)

    sheet_name_str = "".join([c for c in sheet_name if c.isalnum()]).rstrip()
    new_excel = (output_dir / f"{sheet_name_str}_{excel_file.name}").with_suffix(suffix='.xlsx')

    sort_index = 0
    for index, row in df.iterrows():

        # Creating sort_index based on title (if title is different from previous row title, sort_index +1)
        title = row['TITLE']
        if index == 0:
            prev_title = ''
        else:
            prev_title = df.loc[int(index) - 1]['TITLE']

        if title != prev_title:
            sort_index += 1

        # Lookup sort_cty from country weight table
        try:
            sort_cty = cty_order_list.index(row['CTY'])
        except ValueError as e:
            print(f"{e} ({sheet_name=}: {row.values})")
            sort_cty = ''

        # Write both values to the dataframe
        df.at[index, 'SORT_INDEX'] = sort_index
        df.at[index, 'SORT_CTY'] = sort_cty

    # Cast values to int
    df['SORT_INDEX'] = df['SORT_INDEX'].astype('int')
    df['SORT_CTY'] = df['SORT_CTY'].astype('int')

    # Sort values, first by sort_index, than sort_cty
    df.sort_values(by=['SORT_INDEX', 'SORT_CTY'], inplace=True)

    # print and write to Excel
    # print(df.to_string())
    with new_excel.open(mode='wb') as f:
        df.to_excel(excel_writer=f,
                    index=False,
                    columns=list(df.columns)[:-2])


def get_country_list(excel_file: Path, sheet_names: list[str]):
    """Create a list of countries in all the sheet names combined.
    Can be used to create an ordered list of countries."""
    countries = []
    for sheet_name in sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        countries.extend(df['CTY'].values)
    return list(sorted(set(countries)))


def main():
    for sheet_name in SHEET_NAMES:
        list_sorter(
            excel_file=EXCEL_FILE,
            sheet_name=sheet_name,
            output_dir=Path('Output'),
            cty_order_list=CTY_ORDER
        )
    # print(get_country_list(excel_file=EXCEL_FILE, sheet_names=SHEET_NAMES))


if __name__ == '__main__':
    main()
