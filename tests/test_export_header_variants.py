#!/usr/bin/env python3
"""
Tests for exports whose column headers differ from the documented spelling.

Empower (formerly Personal Capital) has shipped transaction exports with
lower-cased headers, and a CSV that has been opened in a spreadsheet and saved
again can arrive carrying a UTF-8 byte-order mark on the first header. Both
variants used to produce a structurally valid output file in which every Date,
Merchant and Amount was empty, while the script still reported that it had
converted the file successfully -- a migration that silently lost the entire
transaction history.

These tests pin the three behaviours that fix it: raw headers are folded onto the
canonical field names the transform reads, a file that still cannot produce a Date
or an Amount is refused loudly instead of being written, and such a run exits
non-zero instead of reporting success.

Run with: python -m pytest tests/test_export_header_variants.py -v
"""

import csv
import sys
from pathlib import Path
from typing import List, Optional

import pytest

# Add root directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from migrate_pc_to_monarch import (
    canonicalize_headers,
    canonicalize_row,
    convert_pc_to_monarch,
    main,
    read_pc_transactions,
    validate_monarch_rows,
)

# Date, Description, Category, Tags, Amount
FORMAT2_HEADER = 'Date,Description,Category,Tags,Amount'
FORMAT2_ROWS = [
    ['2024-08-01', 'Payment - Thank You', 'Transfers', 'monthly', '104.93'],
    ['2024-06-27', 'Grand Gas Union San Jose Ca', 'Gasoline/Fuel', '', '-48.92'],
]
MONARCH_HEADER = ['Date', 'Merchant', 'Category', 'Account', 'Original Statement',
                  'Notes', 'Amount', 'Tags']


def write_export(path: Path, header: str, rows: Optional[List[List[str]]] = None) -> Path:
    """Write a minimal export file, exactly as an export would deliver it."""
    body = FORMAT2_ROWS if rows is None else rows
    text = header + '\n' + '\n'.join(','.join(row) for row in body)
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)
    return path


def read_output(path: Path) -> List[dict]:
    with open(path, 'r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


class TestCanonicalizeHeaders:
    """Header folding must be by canonical name, not by exact spelling."""

    def test_exact_headers_fold_onto_themselves(self):
        header_map, unrecognized = canonicalize_headers(FORMAT2_HEADER.split(','))

        assert header_map == {name: name for name in FORMAT2_HEADER.split(',')}
        assert unrecognized == []

    def test_lowercase_and_padded_headers_are_folded(self):
        header_map, unrecognized = canonicalize_headers([' date ', 'AMOUNT', 'Description'])

        assert header_map[' date '] == 'Date'
        assert header_map['AMOUNT'] == 'Amount'
        assert header_map['Description'] == 'Description'
        assert unrecognized == []

    def test_unknown_headers_are_reported_and_left_alone(self):
        header_map, unrecognized = canonicalize_headers(['Date', 'Amount', 'Checking Account'])

        assert header_map['Checking Account'] == 'Checking Account'
        assert unrecognized == ['Checking Account']

    def test_duplicate_fold_lets_only_the_first_header_claim_the_field(self):
        header_map, unrecognized = canonicalize_headers(['Date', 'date', 'Amount'])

        assert header_map['Date'] == 'Date'
        assert header_map['date'] == 'date'
        assert unrecognized == ['date']


class TestCanonicalizeRow:
    """Re-keying must never discard a value that was actually present."""

    def test_row_is_rekeyed_onto_canonical_fields(self):
        header_map, _ = canonicalize_headers(['date', 'description', 'amount'])
        row = {'date': '2024-06-27', 'description': 'Valero Energy', 'amount': '-62.19'}

        assert canonicalize_row(row, header_map) == {
            'Date': '2024-06-27', 'Description': 'Valero Energy', 'Amount': '-62.19'}

    def test_extra_columns_survive_the_fold(self):
        header_map, _ = canonicalize_headers(['Date', 'Amount', 'Status'])
        row = {'Date': '2024-06-27', 'Amount': '-1.00', 'Status': 'Posted'}

        assert canonicalize_row(row, header_map)['Status'] == 'Posted'

    def test_later_duplicate_fills_a_blank_but_never_a_populated_value(self):
        header_map = {'Date': 'Date', 'date': 'Date', 'Amount': 'Amount'}

        filled = canonicalize_row(
            {'Date': '', 'date': '2024-06-27', 'Amount': '-1.00'}, header_map)
        kept = canonicalize_row(
            {'Date': '2024-06-27', 'date': '2099-01-01', 'Amount': '-1.00'}, header_map)

        assert filled['Date'] == '2024-06-27'
        assert kept['Date'] == '2024-06-27'


class TestFormatDetectionFollowsFoldedHeaders:
    """Folding has to happen before detection or investment exports mis-detect."""

    def test_lowercase_investment_export_detects_as_format1(self, tmp_path):
        source = write_export(
            tmp_path / 'investments.csv',
            'date,description,action,quantity,price,amount',
            [['2024-03-01', 'VTI', 'Buy', '10', '220.15', '-2201.50']],
        )

        _, detected_format = read_pc_transactions(str(source))

        assert detected_format == 'format1'

    def test_standard_export_still_detects_as_format2(self, tmp_path):
        source = write_export(tmp_path / 'checking.csv', FORMAT2_HEADER)

        _, detected_format = read_pc_transactions(str(source))

        assert detected_format == 'format2'


class TestByteOrderMark:
    """A BOM must not glue itself onto the first header name."""

    def test_bom_prefixed_export_keeps_date_and_amount(self, tmp_path):
        source = tmp_path / 'bom.csv'
        source.write_text(FORMAT2_HEADER + '\n' + ','.join(FORMAT2_ROWS[0]), encoding='utf-8-sig')
        output_file = tmp_path / 'bom-monarch.csv'

        convert_pc_to_monarch(str(source), str(output_file))

        rows = read_output(output_file)
        assert rows[0]['Date'] == '2024-08-01'
        assert rows[0]['Amount'] == '104.93'

    def test_bom_prefixed_export_is_not_read_as_an_unrecognised_column(self, tmp_path):
        source = tmp_path / 'bom.csv'
        source.write_text('\ufeff' + FORMAT2_HEADER, encoding='utf-8')

        transactions, _ = read_pc_transactions(str(source))

        assert transactions == []


class TestFailLoudOnUnusableRows:
    """Missing dates and amounts are lost history, not a formatting nit."""

    def test_export_without_an_amount_column_is_refused(self, tmp_path):
        source = write_export(
            tmp_path / 'noamount.csv', 'Date,Description,Category,Tags',
            [['2024-06-27', 'Valero Energy', 'Gasoline/Fuel', '']],
        )
        output_file = tmp_path / 'noamount-monarch.csv'

        with pytest.raises(ValueError) as error:
            convert_pc_to_monarch(str(source), str(output_file))

        assert 'Amount' in str(error.value)
        assert not output_file.exists()

    def test_row_with_a_blank_amount_names_the_offending_line(self, tmp_path):
        source = write_export(
            tmp_path / 'blank.csv', FORMAT2_HEADER,
            [['2024-06-27', 'Valero Energy', 'Gasoline/Fuel', '', '-62.19'],
             ['', 'Mystery Merchant', 'Gasoline/Fuel', '', '-11.00']],
        )
        output_file = tmp_path / 'blank-monarch.csv'

        with pytest.raises(ValueError) as error:
            convert_pc_to_monarch(str(source), str(output_file))

        assert 'data row 2' in str(error.value)
        assert 'no Date' in str(error.value)
        assert not output_file.exists()

    def test_zero_is_a_real_amount_and_is_not_treated_as_blank(self, tmp_path):
        source = write_export(
            tmp_path / 'zero.csv', FORMAT2_HEADER,
            [['2024-06-27', 'Rewards', 'Gifts & Donations', '', '0'],
             ['2024-06-28', 'Reimbursement', 'Transfer', '', '0.00']],
        )
        output_file = tmp_path / 'zero-monarch.csv'

        convert_pc_to_monarch(str(source), str(output_file))

        assert [row['Amount'] for row in read_output(output_file)] == ['0', '0.00']

    def test_header_only_export_still_converts(self, tmp_path):
        source = write_export(tmp_path / 'empty.csv', FORMAT2_HEADER, [])
        output_file = tmp_path / 'empty-monarch.csv'

        count, _ = convert_pc_to_monarch(str(source), str(output_file))

        assert count == 0
        assert read_output(output_file) == []

    def test_validation_reports_every_offending_row(self):
        rows = [{'Date': '2024-06-27', 'Amount': '-1.00'},
                {'Date': '', 'Amount': ''},
                {'Date': '2024-06-28', 'Amount': ''}]

        with pytest.raises(ValueError) as error:
            validate_monarch_rows(rows, 'ledger.csv')

        assert '2 of 3 rows' in str(error.value)
        assert 'data row 2, file line 3' in str(error.value)
        assert 'data row 3, file line 4' in str(error.value)


class TestExitCode:
    """A run that converted nothing must not report success to a calling script."""

    def _run_main(self, tmp_path, monkeypatch) -> None:
        (tmp_path / 'input').mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, 'argv',
                            ['migrate_pc_to_monarch.py', '-i', 'input', '-o', 'output'])

    def test_unusable_export_exits_nonzero(self, tmp_path, monkeypatch):
        self._run_main(tmp_path, monkeypatch)
        write_export(tmp_path / 'input' / 'gap.csv', FORMAT2_HEADER,
                     [['', 'Gap Merchant', 'Groceries', '', '-1.00']])

        with pytest.raises(SystemExit) as exited:
            main()

        assert exited.value.code == 1

    def test_fully_convertible_export_does_not_exit(self, tmp_path, monkeypatch):
        self._run_main(tmp_path, monkeypatch)
        write_export(tmp_path / 'input' / 'good.csv', FORMAT2_HEADER)

        assert main() is None
        assert (tmp_path / 'output' / 'good-monarch.csv').exists()
