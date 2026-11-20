"""Focused tests for workbook extraction without a database."""
from io import BytesIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from xml.etree.ElementTree import Element, SubElement, tostring
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_Python"))
from extract_routes_workbook import HEADERS, NS, extract, validate_row, worksheet_rows


def workbook_bytes(row, bad_cell=None):
    grid = SubElement(Element(f"{NS}worksheet"), f"{NS}sheetData")
    for index, values in enumerate((HEADERS, row), start=1):
        element = SubElement(grid, f"{NS}row", r=str(index))
        for column, value in enumerate(values):
            cell = SubElement(element, f"{NS}c", r=f"{chr(65 + column)}{index}")
            if index == 1 or column == 6:
                cell.set("t", "inlineStr")
                SubElement(SubElement(cell, f"{NS}is"), f"{NS}t").text = value
            else:
                SubElement(cell, f"{NS}v").text = value
            if index == 2 and column == bad_cell:
                SubElement(cell, f"{NS}f").text = "1+1"
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", tostring(grid))
    return payload.getvalue()


class ExtractionTests(unittest.TestCase):
    row = ["0", "1", "2", "3", "0", "1", "Monday", "0", "1", "3.00000000000000001",
           "0", "3", "0", "1.00000000000000000e-4", "0", "1"]

    def test_lineage_and_numeric_lexemes(self):
        [(number, row)] = list(worksheet_rows(workbook_bytes(self.row)))
        self.assertEqual((number, row), (2, self.row))
        arrival, _, latest, _ = validate_row(row)
        self.assertGreater(arrival, latest)

    def test_formula_rejected(self):
        with self.assertRaisesRegex(ValueError, "Sheet1 J2"):
            list(worksheet_rows(workbook_bytes(self.row, bad_cell=9)))

    def test_required_and_invalid_numbers(self):
        for index, value in [(0, ""), (1, "-1"), (5, "2"), (9, "NaN"), (10, "4"), (12, "1")]:
            with self.subTest(index=index, value=value):
                row = self.row.copy()
                row[index] = value
                with self.assertRaises(ValueError):
                    validate_row(row)

    def test_wrong_hash_leaves_existing_output_untouched(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.xlsx"
            output = Path(directory) / "existing.csv"
            source.write_bytes(workbook_bytes(self.row))
            output.write_bytes(b"existing")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                extract(source, output)
            self.assertEqual(output.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
