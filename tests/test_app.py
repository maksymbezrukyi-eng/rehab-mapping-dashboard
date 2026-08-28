import unittest

import app


class OwnershipNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = app.load_excel_data(str(app.EXCEL_PATH))

    def test_known_aliases_are_canonicalized(self):
        cases = {
            "NGO / Charitable": "ngo-charitable",
            "NGO/Charitable": "ngo-charitable",
            "ngo - charitable": "ngo-charitable",
            "Communal (hromada)": "communal",
            "  PRIVATE  ": "private",
            None: app.UNSPECIFIED_KEY,
        }
        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(app.canonical_ownership_key(raw_value), expected)

    def test_current_workbook_has_no_unknown_ownership_categories(self):
        observed = set(self.df["_ownership_key"].unique())
        self.assertEqual(observed - set(app.OWNERSHIP_LABEL_KEYS_ORDER), set())

    def test_default_ownership_selection_keeps_every_loaded_row(self):
        selected = set(app.OWNERSHIP_LABEL_KEYS_ORDER)
        filtered = self.df[self.df["_ownership_key"].isin(selected)]
        self.assertEqual(len(filtered), len(self.df))


if __name__ == "__main__":
    unittest.main()
