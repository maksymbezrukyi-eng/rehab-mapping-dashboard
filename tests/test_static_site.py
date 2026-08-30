import json
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app
from scripts import build_static_site


class StaticSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_static_site.build()
        cls.site = ROOT / "_site"
        with (cls.site / "data" / "hromadas.geojson").open(encoding="utf-8") as stream:
            cls.hromadas = json.load(stream)
        with (cls.site / "data" / "providers.json").open(encoding="utf-8") as stream:
            cls.providers = json.load(stream)

    def test_build_preserves_verified_coverage(self):
        self.assertEqual(self.summary["providers"], 5590)
        self.assertEqual(self.summary["hromadas"], 1472)
        self.assertEqual(len(self.providers), 5590)
        self.assertEqual(len(self.hromadas["features"]), 1472)

    def test_distance_enrichment_covers_all_kse_hromadas(self):
        self.assertEqual(self.summary["distanceMatches"], 1469)
        self.assertEqual(self.summary["unmatchedDistance"], 3)
        records = [feature["properties"] for feature in self.hromadas["features"]]
        kse_records = [record for record in records if record["distanceSource"] == "KSE Loc Data Hub"]
        self.assertEqual(len(kse_records), 1469)
        self.assertTrue(all(record["distanceRaionKm"] is not None for record in kse_records))
        self.assertTrue(all(record["distanceOblastKm"] is not None for record in kse_records))

    def test_raion_centre_inference_is_reviewable(self):
        kse = build_static_site.load_kse_geography(build_static_site.KSE_GEOGRAPHY_PATH)
        centres, audit = build_static_site.select_raion_centres(kse)
        self.assertEqual(len(centres), 126)
        self.assertGreaterEqual(min(row["similarity"] for row in audit), 0.78)

    def test_public_provider_bundle_excludes_addresses(self):
        forbidden = {"address", "verified_geo_id", "verification_note"}
        self.assertFalse(forbidden & set(self.providers[0]))
        self.assertTrue(all(provider["hromadaId"] for provider in self.providers))

    def test_hromada_totals_reconcile(self):
        records = [feature["properties"] for feature in self.hromadas["features"]]
        self.assertEqual(sum(record["total"] for record in records), 5590)
        self.assertEqual(sum(record["medical"] for record in records), sum(provider["medical"] for provider in self.providers))
        self.assertEqual(sum(record["social"] for record in records), sum(provider["social"] for provider in self.providers))

    def test_static_ui_has_no_selection_basket(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("кошик", html)
        self.assertNotIn("0 / 6", html)
        self.assertIn("до районного центру", html)
        self.assertIn("до обласного центру", html)


if __name__ == "__main__":
    unittest.main()
