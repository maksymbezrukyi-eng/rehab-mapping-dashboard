import unittest

import pandas as pd

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

    def test_service_type_flags_use_explicit_source_fields(self):
        expected_medical = self.df[app.COL_NHSU].apply(app.is_filled)
        expected_social = self.df[app.COL_SOCIAL_CODE].apply(app.is_filled) | self.df[
            app.COL_NSSU
        ].apply(app.is_filled)
        pd.testing.assert_series_equal(self.df["_is_medical"], expected_medical, check_names=False)
        pd.testing.assert_series_equal(self.df["_is_social"], expected_social, check_names=False)
        self.assertEqual(int(expected_medical.sum()), 1384)
        self.assertEqual(int(expected_social.sum()), 4206)

    def test_raw_table_contains_only_the_21_source_columns(self):
        display = app.prepare_source_display(self.df)
        self.assertEqual(len(display.columns), 21)
        self.assertFalse(any(column.startswith("_") for column in display.columns))
        self.assertNotIn("hromada_norm", display.columns)
        self.assertNotIn("hromada_norm_baseline", display.columns)

    def test_verified_workbook_preserves_every_original_source_cell(self):
        original = pd.read_excel(
            app.ORIGINAL_EXCEL_PATH,
            sheet_name=app.SHEET_NAME,
            skiprows=3,
            dtype=object,
        )
        verified = pd.read_excel(
            app.EXCEL_PATH,
            sheet_name=app.SHEET_NAME,
            skiprows=3,
            dtype=object,
        )
        pd.testing.assert_frame_equal(original, verified.iloc[:, :21])

    def test_ukrainian_and_english_ui_have_the_same_keys(self):
        uk = app.UI_TEXTS["uk"]
        en = app.UI_TEXTS["en"]
        self.assertEqual(set(uk), set(en))
        self.assertEqual(set(uk["ownership_labels"]), set(en["ownership_labels"]))
        self.assertEqual(set(uk["columns"]), set(en["columns"]))
        self.assertEqual(set(uk["match_status_labels"]), set(en["match_status_labels"]))


class GeographyResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = app.load_excel_data(str(app.EXCEL_PATH))
        cls.geo = app.load_geojson(str(app.GEOJSON_PATH))
        cls.oblast_geo = app.complete_oblast_boundaries(
            app.load_oblast_geojson(str(app.OBLAST_GEOJSON_PATH)), cls.geo
        )
        cls.df = app.resolve_facility_geography(source, cls.geo)
        cls.geocoded = app.geocode_facilities(cls.df, cls.geo)
        cls.features_by_id = {
            feature["properties"]["geo_id"]: feature["properties"]
            for feature in cls.geo["features"]
        }

    def test_geo_ids_are_unique(self):
        geo_ids = list(self.features_by_id)
        self.assertEqual(len(geo_ids), len(self.geo["features"]))

    def test_oblast_boundaries_cover_every_oblast(self):
        expected = {feature["properties"]["oblast_ua"] for feature in self.geo["features"]}
        boundaries = self.oblast_geo["features"]
        self.assertEqual({feature["properties"]["oblast_ua"] for feature in boundaries}, expected)
        self.assertTrue(
            all(feature["geometry"]["type"] in {"Polygon", "MultiPolygon"} for feature in boundaries)
        )
        self.assertTrue(all(feature["geometry"]["coordinates"] for feature in boundaries))

    def test_kyiv_city_is_distinct_and_has_no_social_service_rows(self):
        kyiv_geo_ids = {
            feature["properties"]["geo_id"]
            for feature in self.geo["features"]
            if feature["properties"]["oblast_ua"] == "Київ"
        }
        kyiv = self.df[self.df["_geo_id"].isin(kyiv_geo_ids)]
        self.assertEqual(len(kyiv), 154)
        self.assertEqual(int(kyiv["_is_medical"].sum()), 154)
        self.assertEqual(int(kyiv["_is_social"].sum()), 0)
        self.assertEqual(app.display_oblast_name("Київ", "uk", app.UI_TEXTS["uk"]), "Київ — місто")

    def test_current_workbook_maps_all_rows(self):
        status_counts = self.df["_match_status"].value_counts().to_dict()
        self.assertEqual(status_counts.get("ambiguous", 0), 0)
        self.assertEqual(status_counts.get("unknown_oblast", 0), 0)
        self.assertEqual(status_counts.get("name_not_found", 0), 0)
        self.assertEqual(status_counts.get("invalid_verified_geo_id", 0), 0)
        self.assertEqual(status_counts.get("matched", 0), 5027)
        self.assertEqual(status_counts.get("verified_katottg", 0), 563)
        self.assertEqual(int(self.df["_geo_id"].notna().sum()), 5590)

    def test_every_verified_geo_id_exists_in_geojson(self):
        verified = self.df[self.df[app.COL_VERIFICATION_STATUS] == "verified"]
        self.assertEqual(len(verified), 563)
        self.assertEqual(verified[app.COL_VERIFIED_GEO_ID].isna().sum(), 0)
        self.assertEqual(
            set(verified[app.COL_VERIFIED_GEO_ID]) - set(self.features_by_id),
            set(),
        )

    def test_every_match_stays_inside_its_excel_oblast(self):
        matched = self.df[self.df["_geo_id"].notna()]
        for _, row in matched.iterrows():
            expected_oblast = app.normalize_oblast_from_excel(row[app.COL_OBLAST])
            actual_oblast = self.features_by_id[row["_geo_id"]]["oblast_ua"]
            self.assertEqual(actual_oblast, expected_oblast)

    def test_duplicate_names_resolve_by_raion_and_locality_type(self):
        cases = [
            ("Chernihiv", "Nizhyn", "Talalaivska", "geo:340"),
            ("Chernihiv", "Pryluky", "Talalaivska", "geo:341"),
            ("Dnipropetrovsk", "Dnipro", "Mykolaivska", "geo:325"),
            ("Dnipropetrovsk", "Synelnykove", "Mykolaivska", "geo:326"),
            ("Kyiv", "Brovary", "Kalynivska", "geo:626"),
            ("Mykolaiv", "Pervomaisk", "Pervomaiska", "geo:1367"),
            ("Odesa", "Odesa", "Chornomorska", "geo:1358"),
            ("Odesa", "Rozdilna", "Lymanska", "geo:837"),
            ("Zaporizhzhia", "Zaporizhzhia", "Mykhailivska", "geo:392"),
            ("Zaporizhzhia", "Vasylivka", "Mykhailivska", "geo:1440"),
        ]
        for oblast, raion, hromada, expected_geo_id in cases:
            with self.subTest(oblast=oblast, raion=raion, hromada=hromada):
                selected = self.df[
                    (self.df[app.COL_OBLAST] == oblast)
                    & (self.df[app.COL_RAION] == raion)
                    & (self.df[app.COL_HROMADA] == hromada)
                ]
                self.assertGreater(len(selected), 0)
                self.assertEqual(set(selected["_geo_id"]), {expected_geo_id})

    def test_aggregate_has_one_row_per_geo_feature(self):
        aggregate = app.compute_hromada_stats(self.df)
        self.assertFalse(aggregate["geo_id"].duplicated().any())
        self.assertEqual(int(aggregate["total"].sum()), 5590)

    def test_every_marker_is_inside_its_hromada_polygon(self):
        geometries = {
            feature["properties"]["geo_id"]: feature["geometry"]
            for feature in self.geo["features"]
        }
        matched = self.geocoded[self.geocoded["_geo_id"].notna()]
        outside = []
        for index, row in matched.iterrows():
            if not app.geometry_contains_point(
                geometries[row["_geo_id"]], row["lon"], row["lat"]
            ):
                outside.append(index)
        self.assertEqual(outside, [])

    def test_unmatched_rows_do_not_receive_coordinates(self):
        unmatched = self.geocoded[self.geocoded["_geo_id"].isna()]
        self.assertEqual(len(unmatched), 0)
        self.assertTrue(unmatched["lat"].isna().all())
        self.assertTrue(unmatched["lon"].isna().all())


if __name__ == "__main__":
    unittest.main()
