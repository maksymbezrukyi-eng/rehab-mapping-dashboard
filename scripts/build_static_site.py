"""Build the public, static GitHub Pages dashboard.

The verified provider workbook remains the authoritative service source.  The
KSE geography extract is used only for hromada-centre coordinates and derived
straight-line distances.  No addresses are included in the public bundle.
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app  # noqa: E402


WEB_DIR = ROOT / "web"
OUTPUT_DIR = ROOT / "_site"
KSE_GEOGRAPHY_PATH = ROOT / "data_sources" / "kse_hromada_geography.csv"

PUBLIC_COLUMNS = [
    "hromada_code",
    "hromada_name",
    "raion_code",
    "raion_name",
    "oblast_code",
    "oblast_name",
    "type",
    "hromada_full_name",
    "hromada_center_code",
    "hromada_center",
    "lat_center",
    "lon_center",
    "travel_time",
    "oblast_center",
]


def clean_oblast(value: object) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+область$", "", text)


def hromada_key(value: object) -> str:
    text = str(value or "")
    for apostrophe in ("'", "’", "ʼ", "′"):
        text = text.replace(apostrophe, "")
    return app.normalize_text_en(app.transliterate_ua_to_en(text))


def raion_key(value: object) -> str:
    return app.normalize_raion(app.transliterate_ua_to_en(str(value or "")))


def text_key(value: object) -> str:
    text = str(value or "").lower().replace("’", "'").replace("ʼ", "'")
    return re.sub(r"[^а-щьюяєіїґa-z0-9]+", "", text)


def hromada_type_key(value: object) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "міська": "city",
        "селищна": "settlement",
        "сільська": "rural",
        "територіальна": "territorial",
    }
    return aliases.get(raw, raw)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_kse_geography(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = set(PUBLIC_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"KSE geography extract misses columns: {sorted(missing)}")
    frame = frame[PUBLIC_COLUMNS].copy()
    for column in ("lat_center", "lon_center", "travel_time", "oblast_center"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def select_raion_centres(kse: pd.DataFrame) -> tuple[dict[str, pd.Series], list[dict]]:
    centres: dict[str, pd.Series] = {}
    audit: list[dict] = []
    for raion_code, group in kse.groupby("raion_code", sort=True):
        raion_name = str(group.iloc[0]["raion_name"])
        target = text_key(raion_name)
        candidates: list[tuple[float, int, pd.Series]] = []
        for index, row in group.iterrows():
            scores = [
                SequenceMatcher(None, target, text_key(row["hromada_center"])).ratio(),
                SequenceMatcher(None, target, text_key(row["hromada_name"])).ratio(),
            ]
            candidates.append((max(scores), int(index), row))
        score, _, centre = max(candidates, key=lambda item: (item[0], -item[1]))
        centres[str(raion_code)] = centre
        audit.append(
            {
                "raion_code": str(raion_code),
                "raion_name": raion_name,
                "centre": str(centre["hromada_center"]),
                "centre_hromada": str(centre["hromada_name"]),
                "similarity": round(score, 4),
            }
        )
    return centres, audit


def select_oblast_centres(kse: pd.DataFrame) -> dict[str, pd.Series]:
    centres: dict[str, pd.Series] = {}
    for _, row in kse[kse["oblast_center"] == 1].iterrows():
        centres[clean_oblast(row["oblast_name"])] = row
    return centres


def match_kse_rows(geo: dict, kse: pd.DataFrame) -> tuple[dict[str, pd.Series], list[dict]]:
    exact: dict[tuple[str, str, str, str], list[pd.Series]] = defaultdict(list)
    by_hromada: dict[tuple[str, str, str], list[pd.Series]] = defaultdict(list)
    by_hromada_any_type: dict[tuple[str, str], list[pd.Series]] = defaultdict(list)
    by_region_raion: dict[tuple[str, str], list[pd.Series]] = defaultdict(list)

    for _, row in kse.iterrows():
        oblast = clean_oblast(row["oblast_name"])
        h_key = hromada_key(row["hromada_name"])
        r_key = raion_key(row["raion_name"])
        type_key = hromada_type_key(row["type"])
        exact[(oblast, r_key, h_key, type_key)].append(row)
        by_hromada[(oblast, h_key, type_key)].append(row)
        by_hromada_any_type[(oblast, h_key)].append(row)
        by_region_raion[(oblast, r_key)].append(row)

    matched: dict[str, pd.Series] = {}
    audit: list[dict] = []

    for feature in geo["features"]:
        props = feature["properties"]
        geo_id = props["geo_id"]
        oblast = clean_oblast(props["oblast_ua"])
        exact_candidates = exact.get(
            (oblast, props["raion_key"], hromada_key(props["hromada_ua"]), props["hromada_type"]),
            [],
        )
        fallback_candidates = by_hromada.get(
            (oblast, hromada_key(props["hromada_ua"]), props["hromada_type"]),
            [],
        )
        any_type_candidates = by_hromada_any_type.get(
            (oblast, hromada_key(props["hromada_ua"])),
            [],
        )
        method = ""
        score = 1.0
        candidate: pd.Series | None = None

        if len(exact_candidates) == 1:
            candidate = exact_candidates[0]
            method = "oblast_raion_name"
        elif len(fallback_candidates) == 1:
            candidate = fallback_candidates[0]
            method = "oblast_name"
        elif len(any_type_candidates) == 1:
            candidate = any_type_candidates[0]
            method = "oblast_name_untyped"
        else:
            pool = by_region_raion.get((oblast, props["raion_key"]), [])
            if not pool:
                pool = [
                    row
                    for rows in by_hromada.values()
                    for row in rows
                    if clean_oblast(row["oblast_name"]) == oblast
                    and hromada_type_key(row["type"]) == props["hromada_type"]
                ]
            scored = sorted(
                (
                    SequenceMatcher(
                        None,
                        hromada_key(props["hromada_ua"]),
                        hromada_key(row["hromada_name"]),
                    ).ratio(),
                    str(row["hromada_code"]),
                    row,
                )
                for row in pool
            )
            if scored:
                best_score, _, best = scored[-1]
                second_score = scored[-2][0] if len(scored) > 1 else 0
                if best_score >= 0.9 and best_score - second_score >= 0.04:
                    candidate = best
                    score = best_score
                    method = "reviewable_fuzzy"

        if candidate is not None:
            matched[geo_id] = candidate
        audit.append(
            {
                "geo_id": geo_id,
                "hromada": props["hromada_ua"],
                "raion": props["rayon_ua"],
                "oblast": props["oblast_ua"],
                "kse_code": "" if candidate is None else str(candidate["hromada_code"]),
                "kse_name": "" if candidate is None else str(candidate["hromada_name"]),
                "method": method or "unmatched",
                "similarity": round(score, 4) if candidate is not None else "",
            }
        )
    return matched, audit


def rounded(value: object, digits: int = 1) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), digits)


def provider_label(row: pd.Series, fallback_index: int) -> str:
    value = row.get(app.COL_PROVIDER_NAME)
    if app.is_filled(value):
        return str(value).strip()
    return f"Надавач {fallback_index + 1}"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))


def build() -> dict:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    shutil.copytree(WEB_DIR, OUTPUT_DIR)
    data_dir = OUTPUT_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    facilities, geo, aggregate, unmatched = app.prepare_data(
        str(app.EXCEL_PATH), str(app.GEOJSON_PATH)
    )
    if len(facilities) != 5590 or facilities["_geo_id"].isna().any() or not unmatched.empty:
        raise ValueError("Verified provider mapping regression detected")

    kse = load_kse_geography(KSE_GEOGRAPHY_PATH)
    geo_matches, geo_audit = match_kse_rows(geo, kse)
    raion_centres, raion_audit = select_raion_centres(kse)
    oblast_centres = select_oblast_centres(kse)
    stats = aggregate.set_index("geo_id").to_dict("index")

    kyiv_feature = next(
        feature for feature in geo["features"] if feature["properties"]["oblast_ua"] == "Київ"
    )
    kyiv_point = app.geometry_interior_point(kyiv_feature["geometry"])
    if kyiv_point is None:
        raise ValueError("Kyiv representative point is unavailable")
    kyiv_lon, kyiv_lat, _ = kyiv_point

    public_features = []
    hromada_records = []
    for feature in geo["features"]:
        props = feature["properties"]
        geo_id = props["geo_id"]
        service = stats.get(
            geo_id,
            {"total": 0, "medical": 0, "social": 0, "ownership_counts": {}},
        )
        kse_row = geo_matches.get(geo_id)

        centre_lat = centre_lon = None
        centre_name = ""
        kse_code = ""
        raion_distance = oblast_distance = None
        oblast_travel_minutes = None
        distance_source = "unavailable"

        if kse_row is not None:
            centre_lat = float(kse_row["lat_center"])
            centre_lon = float(kse_row["lon_center"])
            centre_name = str(kse_row["hromada_center"])
            kse_code = str(kse_row["hromada_code"])
            raion_centre = raion_centres.get(str(kse_row["raion_code"]))
            oblast_centre = oblast_centres.get(clean_oblast(kse_row["oblast_name"]))
            if raion_centre is not None:
                raion_distance = haversine_km(
                    centre_lat,
                    centre_lon,
                    float(raion_centre["lat_center"]),
                    float(raion_centre["lon_center"]),
                )
            if oblast_centre is None and clean_oblast(kse_row["oblast_name"]) == "київська":
                oblast_distance = haversine_km(centre_lat, centre_lon, kyiv_lat, kyiv_lon)
            elif oblast_centre is not None:
                oblast_distance = haversine_km(
                    centre_lat,
                    centre_lon,
                    float(oblast_centre["lat_center"]),
                    float(oblast_centre["lon_center"]),
                )
            oblast_travel_minutes = rounded(kse_row["travel_time"], 0)
            distance_source = "KSE Loc Data Hub"
        elif props["oblast_ua"] == "Київ":
            centre_lat, centre_lon = kyiv_lat, kyiv_lon
            centre_name = "Київ"
            raion_distance = oblast_distance = 0.0
            distance_source = "geometry proxy"

        record = {
            "id": geo_id,
            "katottg": kse_code,
            "name": props["hromada_ua"],
            "nameEn": props["hromada_en"],
            "raion": props["rayon_ua"],
            "raionEn": props["rayon_en"],
            "oblast": props["oblast_ua"],
            "oblastEn": props["oblast_en"],
            "type": props.get("hromada_type") or "territorial",
            "centre": centre_name,
            "centreEn": app.transliterate_ua_to_en(centre_name),
            "centreLat": rounded(centre_lat, 5),
            "centreLon": rounded(centre_lon, 5),
            "distanceRaionKm": rounded(raion_distance),
            "distanceOblastKm": rounded(oblast_distance),
            "travelOblastMinutes": oblast_travel_minutes,
            "distanceSource": distance_source,
            "total": int(service["total"]),
            "medical": int(service["medical"]),
            "social": int(service["social"]),
            "ownership": service["ownership_counts"],
        }
        hromada_records.append(record)
        public_features.append(
            {
                "type": "Feature",
                "properties": record,
                "geometry": feature["geometry"],
            }
        )

    provider_records = []
    for index, row in facilities.iterrows():
        provider_records.append(
            {
                "id": int(index),
                "hromadaId": str(row["_geo_id"]),
                "name": provider_label(row, int(index)),
                "lat": rounded(row["lat"], 5),
                "lon": rounded(row["lon"], 5),
                "medical": bool(row["_is_medical"]),
                "social": bool(row["_is_social"]),
                "ownership": str(row["_ownership_key"]),
            }
        )

    oblast_geo = app.complete_oblast_boundaries(
        app.load_oblast_geojson(str(app.OBLAST_GEOJSON_PATH)), geo
    )
    public_oblasts = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": feature["properties"]["oblast_ua"],
                    "nameEn": feature["properties"]["oblast_en"],
                },
                "geometry": feature["geometry"],
            }
            for feature in oblast_geo["features"]
        ],
    }

    write_json(data_dir / "hromadas.geojson", {"type": "FeatureCollection", "features": public_features})
    write_json(data_dir / "providers.json", provider_records)
    write_json(data_dir / "oblasts.geojson", public_oblasts)
    write_json(
        data_dir / "metadata.json",
        {
            "providers": len(provider_records),
            "hromadas": len(hromada_records),
            "matchedDistanceHromadas": sum(r["distanceSource"] == "KSE Loc Data Hub" for r in hromada_records),
            "medical": sum(r["medical"] for r in hromada_records),
            "social": sum(r["social"] for r in hromada_records),
            "distanceMethod": "great-circle distance between administrative-centre coordinates",
            "providerLocationMethod": "deterministic approximate point inside verified hromada polygon",
        },
    )

    audit_dir = ROOT / "outputs" / "static_site_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    with (audit_dir / "kse_geo_matching.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=geo_audit[0].keys())
        writer.writeheader()
        writer.writerows(geo_audit)
    with (audit_dir / "raion_centres.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=raion_audit[0].keys())
        writer.writeheader()
        writer.writerows(raion_audit)

    summary = {
        "providers": len(provider_records),
        "hromadas": len(hromada_records),
        "distanceMatches": len(geo_matches),
        "unmatchedDistance": len(hromada_records) - len(geo_matches),
        "raionCentres": len(raion_centres),
        "lowestRaionCentreSimilarity": min(item["similarity"] for item in raion_audit),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    build()
