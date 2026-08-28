"""Мапа надавачів послуг педіатричної реабілітації в Україні."""

import html
import json
import math
import random
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = BASE_DIR / "NEW_Mapping_tracker_2506.xlsx"
GEOJSON_PATH = BASE_DIR / "ukraine_hromadas.geojson"
SHEET_NAME = "Provider Data"

COL_HROMADA = "Hromada"
COL_PROVIDER_NAME = "Provider Name"
COL_NHSU = "NHSU package (25/53/54)"
COL_OWNERSHIP = "Ownership / funding type (public / communal / private / NGO-charitable / donor / mixed)"

# Суфіксні слова, які прибираються при нормалізації назви громади (транслітеровані,
# бо і Excel, і транслітерована назва з GeoJSON зводяться до латиниці для зіставлення).
EN_SUFFIX_WORDS = ["terytorialna", "miska", "silska", "selyshchna", "hromada", "m.", "s.", "smt"]

# Таблиця транслітерації кирилиця -> латиниця за Постановою КМУ №55 (2010).
TRANSLIT_BASE = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "ж": "zh",
    "з": "z", "и": "y", "і": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "'": "", "’": "", "ъ": "",
}
TRANSLIT_INITIAL = {"є": "ye", "ї": "yi", "й": "y", "ю": "yu", "я": "ya"}
TRANSLIT_MID = {"є": "ie", "ї": "i", "й": "i", "ю": "iu", "я": "ia"}

UNSPECIFIED_KEY = "_unspecified"
ALL_OBLASTS = None  # сентинель "усі області" для селектора
NO_HROMADA_SELECTED = None  # сентинель "громаду не обрано" для селектора

# Колір точки на карті за формою власності (3 кольори + сірий для невказаних).
OWNERSHIP_COLOR = {
    "public": "blue",
    "communal": "blue",
    "private": "green",
    "ngo-charitable": "orange",
    "donor": "orange",
    "mixed": "orange",
    UNSPECIFIED_KEY: "gray",
}
# Порядок опцій у мультиселекті форми власності в сайдбарі.
OWNERSHIP_LABEL_KEYS_ORDER = ["public", "communal", "private", "ngo-charitable", "donor", "mixed", UNSPECIFIED_KEY]

# Excel часто записує обласні/великі районні центри іменниковою формою міста
# ("Kharkiv"), а не прикметниковою формою громади ("Харківська"), тому
# транслітерація+нормалізація їх не зматчить. Це прямий обхід для таких кейсів:
# ключ — сире значення Hromada з Excel, значення — офіційна назва-прикметник
# громади кирилицею (без слова "громада"), яка далі йде через ту саму
# транслітерацію+нормалізацію, що й GeoJSON.
CITY_TO_HROMADA_MAPPING = {
    "Kharkiv": "Харківська",
    "Dnipro": "Дніпровська",
    "Odesa": "Одеська",
    "Zaporizhzhia": "Запорізька",
    "Lviv": "Львівська",
    # "Kyiv" навмисно не мапиться: у GeoJSON Київ закодований окремим випадком
    # (region/rayon/hromada = "Київ", без прикметникової форми), тож сире
    # значення "Kyiv" з Excel і так коректно зматчиться стандартним шляхом.
    "Rivne": "Рівненська",
    "Lutsk": "Луцька",
    "Ternopil": "Тернопільська",
    "Ivano-Frankivsk": "Івано-Франківська",
    "Poltava": "Полтавська",
    "Sumy": "Сумська",
    "Chernihiv": "Чернігівська",
    "Zhytomyr": "Житомирська",
    "Vinnytsia": "Вінницька",
    "Khmelnytskyi": "Хмельницька",
    "Chernivtsi": "Чернівецька",
    "Uzhhorod": "Ужгородська",
    "Mykolaiv": "Миколаївська",
    "Kherson": "Херсонська",
    "Kropyvnytskyi": "Кропивницька",
    "Cherkasy": "Черкаська",
    "Kryvyi Rih": "Криворізька",
    "Kremenchuk": "Кременчуцька",
    "Bila Tserkva": "Білоцерківська",
    "Kamianske": "Кам'янська",
    "Kramatorsk": "Краматорська",
    # Наступні звірені напряму з ukraine_hromadas.geojson (великі районні центри
    # з топу незматчених після першого раунду словника).
    "Nikopol": "Нікопольська",
    "Mukachevo": "Мукачівська",
    "Sievierodonetska": "Сєверодонецька",
    "Brovary": "Броварська",
    "Kamianets-Podilskyi": "Кам'янець-Подільська",
    "Zalishchyky": "Заліщицька",
    # УВАГА: "Oleksandriia" неоднозначна в самому GeoJSON — після нормалізації
    # (відкидання "міська"/"сільська") норм-ключ "oleksandriiska" належить ОДРАЗУ
    # двом різним громадам: Олександрійська міська громада (Кіровоградська обл.)
    # і Олександрійська сільська громада (Рівненська обл.). Обидві отримають
    # однакові (об'єднані) цифри — це відома залишкова похибка схеми, а не баг
    # цього запису.
    "Oleksandriia": "Олександрійська",
    "Stryi": "Стрийська",
    "Drohobych": "Дрогобицька",
}

UI_TEXTS = {
    "uk": {
        "app_title": "🗺️ Мапа надавачів послуг педіатричної реабілітації в Україні",
        "lang_label": "Оберіть мову / Choose language",
        "oblast_label": "Оберіть область",
        "oblast_all": "Усі області",
        "hromada_select_label": "Оберіть громаду",
        "hromada_select_placeholder": "— не обрано —",
        "hromada_detail_header": "📋 Заклади в громаді",
        "hromada_detail_total": "Всього закладів: **{n}**",
        "facility_medical_tag": "🏥 Медичний",
        "facility_social_tag": "🤝 Соціальний",
        "no_facilities_matched": "Немає зіставлених закладів у базі для цієї громади.",
        "facility_name_fallback": "Без назви",
        "ownership_filter_label": "Форма власності",
        "nhsu_filter_label": "Пакет НСЗУ",
        "nhsu_filter_all": "Усі",
        "nhsu_filter_yes": "Так",
        "nhsu_filter_no": "Ні",
        "popup_ownership": "Форма власності",
        "popup_address": "Адреса",
        "popup_nhsu": "Пакет НСЗУ",
        "popup_nhsu_none": "Немає",
        "legend_ownership_title": "Форма власності",
        "legend_public_communal": "Комунальні / Державні",
        "legend_private": "Приватні",
        "legend_ngo_donor": "ГО / Благодійні / Донорські",
        "legend_unspecified": "Не вказано",
        "tab_map": "🗺️ Карта громад",
        "tab_data": "📊 Сирі дані (Таблиця)",
        "kpi_total": "Загальна кількість закладів",
        "kpi_medical": "Медичні заклади",
        "kpi_social": "Соціальні заклади",
        "kpi_hromadas": "Громад з даними",
        "tooltip_hromada": "Громада:",
        "tooltip_total": "Всього закладів:",
        "tooltip_medical": "Медичних:",
        "tooltip_social": "Соціальних:",
        "tooltip_ownership": "Форма власності:",
        "legend_total": "Кількість закладів",
        "layer_choropleth": "Заклади за громадами",
        "layer_points": "📍 Заклади (точки) — очікує геокодування",
        "unmatched_expander": "⚠️ Громади з Excel, не зіставлені з картою ({n})",
        "unmatched_col_key": "Нормалізована назва",
        "unmatched_col_total": "Всього закладів",
        "unmatched_col_medical": "Медичних",
        "unmatched_col_social": "Соціальних",
        "unmatched_col_ownership": "Форма власності",
        "download_unmatched_button": "⬇️ Завантажити список незматчених (CSV)",
        "not_specified": "Не вказано",
        "ownership_labels": {
            "public": "Державні",
            "communal": "Комунальні",
            "private": "Приватні",
            "ngo-charitable": "ГО/Фонди",
            "donor": "Донорські",
            "mixed": "Змішані",
        },
        "columns": {
            "ID": "ID",
            "Provider Name": "Назва надавача",
            "Name in English": "Назва англійською",
            "Oblast": "Область",
            "Raion": "Район",
            COL_HROMADA: "Громада",
            "Address": "Адреса",
            COL_NHSU: "Пакет НСЗУ (25/53/54)",
            "NSSU listing (Y/N + details)": "Реєстр НССУ (Так/Ні + деталі)",
            "Other source (non-PMG / private / grey lit)": "Інше джерело",
            "Source link / reference": "Посилання на джерело",
            COL_OWNERSHIP: "Форма власності / фінансування",
            "Service format (inpatient/outpatient/home/day care)": "Формат надання послуг",
            "Code of social services": "Код соціальних послуг",
            "Target population (0-3 / 3-18 / other)": "Цільова група",
            "Primary rehabilitation focus": "Основний напрям реабілітації",
            "MDT (multidisciplinary team)": "МДК (мультидисциплінарна команда)",
            "Key professionals present": "Ключові фахівці",
            "Volume (patients/year — if available)": "Обсяг (пацієнтів/рік)",
            "Strengths / Good practices": "Сильні сторони / Практики",
            "Gaps / Challenges": "Прогалини / Виклики",
            "hromada_norm": "Ключ зіставлення",
        },
    },
    "en": {
        "app_title": "🗺️ Map of Paediatric Rehabilitation Service Providers in Ukraine",
        "lang_label": "Оберіть мову / Choose language",
        "oblast_label": "Select oblast",
        "oblast_all": "All oblasts",
        "hromada_select_label": "Select hromada",
        "hromada_select_placeholder": "— none selected —",
        "hromada_detail_header": "📋 Facilities in hromada",
        "hromada_detail_total": "Total facilities: **{n}**",
        "facility_medical_tag": "🏥 Medical",
        "facility_social_tag": "🤝 Social",
        "no_facilities_matched": "No matched facilities in the database for this hromada.",
        "facility_name_fallback": "Unnamed",
        "ownership_filter_label": "Ownership type",
        "nhsu_filter_label": "NHSU package",
        "nhsu_filter_all": "All",
        "nhsu_filter_yes": "Yes",
        "nhsu_filter_no": "No",
        "popup_ownership": "Ownership",
        "popup_address": "Address",
        "popup_nhsu": "NHSU package",
        "popup_nhsu_none": "None",
        "legend_ownership_title": "Ownership type",
        "legend_public_communal": "Communal / Public",
        "legend_private": "Private",
        "legend_ngo_donor": "NGO / Charity / Donor",
        "legend_unspecified": "Not specified",
        "tab_map": "🗺️ Hromada Map",
        "tab_data": "📊 Raw Data (Table)",
        "kpi_total": "Total facilities",
        "kpi_medical": "Medical facilities",
        "kpi_social": "Social facilities",
        "kpi_hromadas": "Hromadas with data",
        "tooltip_hromada": "Hromada:",
        "tooltip_total": "Total facilities:",
        "tooltip_medical": "Medical:",
        "tooltip_social": "Social:",
        "tooltip_ownership": "Ownership type:",
        "legend_total": "Number of facilities",
        "layer_choropleth": "Facilities by hromada",
        "layer_points": "📍 Facilities (points) — pending geocoding",
        "unmatched_expander": "⚠️ Hromadas from Excel not matched to the map ({n})",
        "unmatched_col_key": "Normalized name",
        "unmatched_col_total": "Total facilities",
        "unmatched_col_medical": "Medical",
        "unmatched_col_social": "Social",
        "unmatched_col_ownership": "Ownership",
        "download_unmatched_button": "⬇️ Download unmatched list (CSV)",
        "not_specified": "Not specified",
        "ownership_labels": {
            "public": "Public",
            "communal": "Communal",
            "private": "Private",
            "ngo-charitable": "NGO/Charity",
            "donor": "Donor",
            "mixed": "Mixed",
        },
        "columns": {
            "ID": "ID",
            "Provider Name": "Provider Name",
            "Name in English": "Name in English",
            "Oblast": "Oblast",
            "Raion": "Raion",
            COL_HROMADA: "Hromada",
            "Address": "Address",
            COL_NHSU: "NHSU package (25/53/54)",
            "NSSU listing (Y/N + details)": "NSSU listing (Y/N + details)",
            "Other source (non-PMG / private / grey lit)": "Other source",
            "Source link / reference": "Source link / reference",
            COL_OWNERSHIP: "Ownership / funding type",
            "Service format (inpatient/outpatient/home/day care)": "Service format",
            "Code of social services": "Code of social services",
            "Target population (0-3 / 3-18 / other)": "Target population",
            "Primary rehabilitation focus": "Primary rehabilitation focus",
            "MDT (multidisciplinary team)": "MDT (multidisciplinary team)",
            "Key professionals present": "Key professionals present",
            "Volume (patients/year — if available)": "Volume (patients/year)",
            "Strengths / Good practices": "Strengths / Good practices",
            "Gaps / Challenges": "Gaps / Challenges",
            "hromada_norm": "Match key",
        },
    },
}


_APOSTROPHE_CHARS = ("'", "’", "ʼ", "′")


def normalize_text(text: str, suffix_words: list[str]) -> str:
    """Нижній регістр, видалення апострофів, суфіксних слів і зайвих пробілів."""
    if not isinstance(text, str) or not text.strip():
        return ""
    result = text.lower()
    for ch in _APOSTROPHE_CHARS:
        result = result.replace(ch, "")
    for word in suffix_words:
        result = result.replace(word.lower(), " ")
    return " ".join(result.split())


def normalize_text_en(text: str) -> str:
    return normalize_text(text, EN_SUFFIX_WORDS)


# Ключі словника винятків нормалізуються так само, як і Hromada з Excel, щоб
# зіставлення працювало незалежно від суфіксів на кшталт "Miska Hromada",
# доданих чи ні до назви міста в конкретному рядку.
_CITY_TO_HROMADA_LOOKUP = {normalize_text_en(city): ua_adj for city, ua_adj in CITY_TO_HROMADA_MAPPING.items()}


def normalize_hromada_from_excel(raw_value: str) -> str:
    """Ключ зіставлення для сирого значення Hromada з Excel.

    Спершу нормалізує значення як завжди, тоді перевіряє словник винятків
    (обласні/великі районні центри, які Excel іноді записує іменниковою
    формою міста, напр. "Kharkiv", замість прикметникової форми громади).
    """
    base = normalize_text_en(raw_value)
    mapped_ua_adj = _CITY_TO_HROMADA_LOOKUP.get(base)
    if mapped_ua_adj is not None:
        return normalize_text_en(transliterate_ua_to_en(mapped_ua_adj))
    return base


def transliterate_ua_to_en(text: str) -> str:
    """Транслітерує українську назву кирилицею в латиницю (КМУ №55)."""
    if not isinstance(text, str) or not text:
        return ""
    lower = text.lower()
    out = []
    word_start = True
    i = 0
    n = len(lower)
    while i < n:
        ch = lower[i]
        if ch in (" ", "-", "’"):
            out.append(ch)
            word_start = True
            i += 1
            continue
        if ch == "з" and i + 1 < n and lower[i + 1] == "г":
            out.append("zgh")
            i += 2
            word_start = False
            continue
        if ch in TRANSLIT_INITIAL:
            out.append(TRANSLIT_INITIAL[ch] if word_start else TRANSLIT_MID[ch])
        else:
            out.append(TRANSLIT_BASE.get(ch, ch))
        word_start = False
        i += 1
    return "".join(out).title()


@st.cache_data(show_spinner=False)
def load_excel_data(path: str) -> pd.DataFrame:
    # Реальні заголовки колонок — у 4-му рядку файлу (3-й рядок — це групові
    # заголовки розділів "A. IDENTIFICATION" тощо), тому skiprows=3, а не 2.
    df = pd.read_excel(path, sheet_name=SHEET_NAME, skiprows=3)
    df = df.dropna(how="all")
    df = df[df[COL_HROMADA].notna() & (df[COL_HROMADA].astype(str).str.strip() != "")]
    # Без словника винятків (для порівняння "до/після" у діагностиці нижче).
    df["hromada_norm_baseline"] = df[COL_HROMADA].apply(normalize_text_en)
    df["hromada_norm"] = df[COL_HROMADA].apply(normalize_hromada_from_excel)
    # Обчислені один раз тут, а не в кожному фільтрі/агрегації нижче — і для
    # групувань (compute_hromada_stats), і для інтерактивних фільтрів у сайдбарі.
    df["_is_medical"] = df[COL_NHSU].apply(is_filled)
    df["_ownership_key"] = df[COL_OWNERSHIP].apply(canonical_ownership_key)
    return df


@st.cache_data(show_spinner=False)
def load_geojson(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        geo = json.load(f)

    for feature in geo["features"]:
        props = feature["properties"]
        hromada_ua = props.get("hromada", "")
        hromada_en = transliterate_ua_to_en(hromada_ua)
        oblast_ua = props.get("region", "")
        oblast_en = transliterate_ua_to_en(oblast_ua)
        props["hromada_ua"] = hromada_ua
        props["hromada_en"] = hromada_en
        props["oblast_ua"] = oblast_ua
        props["oblast_en"] = oblast_en
        props["norm_key"] = normalize_text_en(hromada_en)
    return geo


def is_filled(value) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip() != ""


def canonical_ownership_key(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return UNSPECIFIED_KEY
    return str(value).strip().lower()


def ownership_label_for_value(value, lang: str) -> str:
    key = canonical_ownership_key(value)
    if key == UNSPECIFIED_KEY:
        return UI_TEXTS[lang]["not_specified"]
    return UI_TEXTS[lang]["ownership_labels"].get(key, str(value).strip())


def format_ownership_str(counts: dict, lang: str) -> str:
    labels = UI_TEXTS[lang]["ownership_labels"]
    not_specified = UI_TEXTS[lang]["not_specified"]
    parts = []
    for key, count in counts.items():
        label = not_specified if key == UNSPECIFIED_KEY else labels.get(key, key.title())
        parts.append(f"{label}: {count}")
    return ", ".join(parts) if parts else not_specified


def compute_hromada_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Групує заклади за hromada_norm. Не кешована навмисно: викликається і на

    повному df (через aggregate_providers нижче — кешовано, важкий шлях), і на
    інтерактивно відфільтрованому df (форма власності/НСЗУ у сайдбарі — тут
    кешування не дало б користі, бо вхід міняється щовидгету, а групування
    ~5600 рядків саме по собі займає одиниці мілісекунд).
    """
    columns = ["norm_key", "total", "medical", "social", "ownership_counts", "oblasts", "raions"]
    if df.empty:
        # Порожній вхід (наприклад, фільтри в сайдбарі відсікли всі заклади) —
        # повертаємо DataFrame з правильними колонками, а не порожній без жодної,
        # інакше .set_index("norm_key") нижче по коду впаде з KeyError.
        return pd.DataFrame(columns=columns)

    records = []
    for norm_key, group in df.groupby("hromada_norm"):
        total = len(group)
        medical = int(group["_is_medical"].sum())
        social = total - medical
        ownership_counts = group["_ownership_key"].value_counts().to_dict()
        # Список областей/районів, звідки походять рядки з цим ключем — потрібен
        # для ручної звірки колізій на кшталт "Городок" (Львівська vs Хмельницька).
        oblasts = "; ".join(sorted(group["Oblast"].dropna().astype(str).str.strip().unique()))
        raions = "; ".join(sorted(group["Raion"].dropna().astype(str).str.strip().unique()))
        records.append(
            {
                "norm_key": norm_key,
                "total": total,
                "medical": medical,
                "social": social,
                "ownership_counts": ownership_counts,
                "oblasts": oblasts,
                "raions": raions,
            }
        )
    return pd.DataFrame(records)


@st.cache_data(show_spinner=False)
def aggregate_providers(df: pd.DataFrame) -> pd.DataFrame:
    return compute_hromada_stats(df)


@st.cache_data(show_spinner=False)
def log_mapping_impact(df: pd.DataFrame, geo: dict) -> None:
    """Друкує в консоль ефект словника винятків CITY_TO_HROMADA_MAPPING.

    Кешовано через st.cache_data, тому виконується (і друкує) лише один раз
    для конкретних df/geo, а не на кожен st.rerun() від перемикачів у UI.
    """
    geo_keys = {f["properties"]["norm_key"] for f in geo["features"]}
    before_unmatched = int((~df["hromada_norm_baseline"].isin(geo_keys)).sum())
    after_unmatched = int((~df["hromada_norm"].isin(geo_keys)).sum())
    total = len(df)

    print("=" * 60)
    print("[CITY_TO_HROMADA_MAPPING] Ефект словника винятків")
    print(f"  Усього рядків закладів: {total}")
    print(f"  Незматчено ДО словника:   {before_unmatched} ({before_unmatched / total:.1%})")
    print(f"  Незматчено ПІСЛЯ словника: {after_unmatched} ({after_unmatched / total:.1%})")
    print(f"  Довиправлено рядків: {before_unmatched - after_unmatched}")
    print("=" * 60)


@st.cache_data(show_spinner=False)
def find_unmatched(geo: dict, agg: pd.DataFrame) -> pd.DataFrame:
    """Громади з Excel, для яких немає жодного полігону в GeoJSON.

    Більше не мутує geo (раніше writing total/medical/social напряму в
    properties тут створювало "застиглі" непрофільтровані цифри — build_map
    тепер сам щоразу свіжо пише ці властивості з переданого agg, включно з
    відфільтрованим за формою власності/НСЗУ, тож тут лишається тільки
    обчислення unmatched).
    """
    geo_keys = {f["properties"]["norm_key"] for f in geo["features"]}
    return agg[~agg["norm_key"].isin(geo_keys)].sort_values("total", ascending=False)


def polygon_ring_centroid(ring: list) -> tuple[float, float, float]:
    """(area, cx, cy) для одного кільця координат [lon, lat] за формулою центроїда полігону."""
    n = len(ring)
    if n < 3:
        x, y = (ring[0][0], ring[0][1]) if ring else (0.0, 0.0)
        return 0.0, x, y
    area_sum = cx_sum = cy_sum = 0.0
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        cross = x0 * y1 - x1 * y0
        area_sum += cross
        cx_sum += (x0 + x1) * cross
        cy_sum += (y0 + y1) * cross
    area = area_sum / 2.0
    if abs(area) < 1e-12:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return abs(area), cx_sum / (6.0 * area), cy_sum / (6.0 * area)


def geometry_centroid_and_extent(geometry: dict) -> tuple[float, float, float] | None:
    """(lon, lat, extent_degrees) — центроїд Polygon/MultiPolygon і приблизний розмір
    його bounding box (для масштабування jitter-розкиду точок навколо центру)."""
    gtype = geometry.get("type")
    if gtype == "Polygon":
        polygons = [geometry["coordinates"]]
    elif gtype == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return None

    weighted_x = weighted_y = total_area = 0.0
    all_lons, all_lats = [], []
    for poly in polygons:
        if not poly:
            continue
        exterior = poly[0]
        area, cx, cy = polygon_ring_centroid(exterior)
        weighted_x += area * cx
        weighted_y += area * cy
        total_area += area
        all_lons.extend(p[0] for p in exterior)
        all_lats.extend(p[1] for p in exterior)

    if not all_lons:
        return None
    if total_area > 0:
        centroid_lon, centroid_lat = weighted_x / total_area, weighted_y / total_area
    else:
        centroid_lon, centroid_lat = sum(all_lons) / len(all_lons), sum(all_lats) / len(all_lats)

    extent = max(max(all_lons) - min(all_lons), max(all_lats) - min(all_lats))
    return centroid_lon, centroid_lat, extent


def jitter_point(lon: float, lat: float, extent: float, seed: int) -> tuple[float, float]:
    """Невеликий випадковий (але детермінований за seed) зсув точки навколо центру
    громади, щоб заклади в одній громаді не накладались один на одного."""
    rng = random.Random(seed)
    radius = rng.uniform(0, max(extent * 0.12, 0.01))
    angle = rng.uniform(0, 2 * math.pi)
    return lon + radius * math.cos(angle), lat + radius * math.sin(angle)


def geocode_facilities(df: pd.DataFrame, geo: dict) -> pd.DataFrame:
    """Координати закладу = центроїд полігону його громади + jitter-розкид.

    Миттєво і без зовнішніх залежностей (жодних мережевих запитів), тому не
    потребує власного @st.cache_data — і так виконується лише в момент
    cache-miss всередині prepare_data (див. коментар там). Заклади з громадою,
    якої немає серед полігонів (unmatched), отримують lat/lon = None і просто
    пропускаються при малюванні точок — без падіння коду.
    """
    centroids: dict[str, tuple[float, float, float]] = {}
    for feature in geo["features"]:
        key = feature["properties"]["norm_key"]
        result = geometry_centroid_and_extent(feature["geometry"])
        if result is not None:
            centroids[key] = result

    lats: list[float | None] = []
    lons: list[float | None] = []
    for idx, hromada_norm in df["hromada_norm"].items():
        center = centroids.get(hromada_norm)
        if center is None:
            lats.append(None)
            lons.append(None)
            continue
        lon, lat, extent = center
        jlon, jlat = jitter_point(lon, lat, extent, seed=int(idx))
        lats.append(jlat)
        lons.append(jlon)

    df = df.copy()
    df["lat"] = lats
    df["lon"] = lons
    return df


@st.cache_data(show_spinner="Обробка Excel і GeoJSON…")
def prepare_data(excel_path: str, geojson_path: str) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """Уся важка частина ETL за одним викликом, ключованим лише шляхами до файлів.

    Важливо тримати це одним cache_data-викликом: якщо замість цього main()
    ланцюжком викликає load_excel_data -> aggregate_providers ->
    find_unmatched з df/geo як аргументами, Streamlit змушений на КОЖЕН
    st.rerun() (наприклад, перемикання мови) заново хешувати ці важкі об'єкти
    (DataFrame на 5590 рядків, GeoJSON на ~4 МБ), що коштує майже стільки ж,
    скільки сам розрахунок. Тут же кеш-ключ — два коротких рядки шляхів, тож
    на повторних rerun'ах ця функція не виконується взагалі.
    """
    df = load_excel_data(excel_path)
    geo = load_geojson(geojson_path)
    log_mapping_impact(df, geo)
    df = geocode_facilities(df, geo)
    agg = aggregate_providers(df)
    unmatched = find_unmatched(geo, agg)
    return df, geo, agg, unmatched


def build_ownership_legend_html(ui: dict) -> str:
    rows = [
        (OWNERSHIP_COLOR["communal"], ui["legend_public_communal"]),
        (OWNERSHIP_COLOR["private"], ui["legend_private"]),
        (OWNERSHIP_COLOR["ngo-charitable"], ui["legend_ngo_donor"]),
        (OWNERSHIP_COLOR[UNSPECIFIED_KEY], ui["legend_unspecified"]),
    ]
    items = "".join(
        f'<div style="margin:2px 0;">'
        f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
        f'background:{color};margin-right:6px;"></span>{html.escape(label)}</div>'
        for color, label in rows
    )
    return (
        '<div style="position: fixed; bottom: 30px; left: 10px; z-index: 9999; '
        'background: white; color: #111; padding: 8px 12px; border-radius: 6px; '
        'box-shadow: 0 1px 4px rgba(0,0,0,0.35); font-size: 12px; line-height: 1.4;">'
        f'<b>{html.escape(ui["legend_ownership_title"])}</b>{items}</div>'
    )


def build_map(geo: dict, agg: pd.DataFrame, facility_df: pd.DataFrame, lang: str, ui: dict) -> folium.Map:
    # OpenStreetMap — безкоштовний тайл без API-ключа (CartoDB positron вимагав
    # ключ і показував водяний знак "API key required").
    m = folium.Map(location=[48.3794, 31.1656], zoom_start=6, tiles="OpenStreetMap")

    # Свіжий per-render мердж статистики (agg тут може бути вже відфільтрованим
    # за формою власності/НСЗУ) у properties полігонів — без мутації кешованого
    # geo, тож build_map лишається дешевим і безпечним для повторних викликів.
    name_field = "hromada_ua" if lang == "uk" else "hromada_en"
    stats_by_key = agg.set_index("norm_key").to_dict("index")
    for feature in geo["features"]:
        props = feature["properties"]
        stats = stats_by_key.get(props["norm_key"], {"total": 0, "medical": 0, "social": 0, "ownership_counts": {}})
        props["total"] = int(stats["total"])
        props["medical"] = int(stats["medical"])
        props["social"] = int(stats["social"])
        props["ownership_display"] = format_ownership_str(stats.get("ownership_counts", {}), lang)

    choropleth = folium.Choropleth(
        geo_data=geo,
        data=agg,
        columns=["norm_key", "total"],
        key_on="feature.properties.norm_key",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.3,
        nan_fill_color="lightgray",
        legend_name=ui["legend_total"],
        name=ui["layer_choropleth"],
    ).add_to(m)

    choropleth.geojson.add_child(
        folium.GeoJsonTooltip(
            fields=[name_field, "total", "medical", "social", "ownership_display"],
            aliases=[
                ui["tooltip_hromada"],
                ui["tooltip_total"],
                ui["tooltip_medical"],
                ui["tooltip_social"],
                ui["tooltip_ownership"],
            ],
            sticky=True,
        )
    )

    # --- Точковий шар (окремі заклади) ---
    # MarkerCluster — бо закладів може бути кілька тисяч, і без кластеризації
    # карта стає непридатною для використання (тисячі маркерів одночасно).
    points_layer = MarkerCluster(name=ui["layer_points"])
    for _, row in facility_df.iterrows():
        if pd.isna(row["lat"]) or pd.isna(row["lon"]):
            continue
        color = OWNERSHIP_COLOR.get(row["_ownership_key"], OWNERSHIP_COLOR[UNSPECIFIED_KEY])
        name = str(row[COL_PROVIDER_NAME]).strip() if is_filled(row[COL_PROVIDER_NAME]) else ui["facility_name_fallback"]
        address = str(row["Address"]).strip() if is_filled(row["Address"]) else ""
        nhsu_value = row[COL_NHSU]
        nhsu_display = str(nhsu_value).strip() if is_filled(nhsu_value) else ui["popup_nhsu_none"]
        popup_html = (
            f"<b>{html.escape(name)}</b><br>"
            f"{html.escape(ui['popup_ownership'])}: {html.escape(ownership_label_for_value(row[COL_OWNERSHIP], lang))}<br>"
            f"{html.escape(ui['popup_address'])}: {html.escape(address or '—')}<br>"
            f"{html.escape(ui['popup_nhsu'])}: {html.escape(nhsu_display)}"
        )
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5,
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(points_layer)
    points_layer.add_to(m)

    m.get_root().html.add_child(folium.Element(build_ownership_legend_html(ui)))
    folium.LayerControl().add_to(m)
    return m


def main() -> None:
    st.set_page_config(page_title="Мапа надавачів послуг реабілітації", layout="wide")

    lang_choice = st.sidebar.radio(
        UI_TEXTS["uk"]["lang_label"],
        ["🇺🇦 Українська", "🇬🇧 English"],
        index=0,
    )
    lang = "uk" if "Українська" in lang_choice else "en"
    ui = UI_TEXTS[lang]

    st.title(ui["app_title"])

    df, geo, agg, unmatched = prepare_data(str(EXCEL_PATH), str(GEOJSON_PATH))

    oblasts_ua = sorted({f["properties"]["oblast_ua"] for f in geo["features"] if f["properties"]["oblast_ua"]})
    oblast_display = {
        ua: (ua if lang == "uk" else transliterate_ua_to_en(ua)) for ua in oblasts_ua
    }
    selected_oblast = st.sidebar.selectbox(
        ui["oblast_label"],
        options=[ALL_OBLASTS] + oblasts_ua,
        format_func=lambda x: ui["oblast_all"] if x is ALL_OBLASTS else oblast_display[x],
    )

    if selected_oblast is ALL_OBLASTS:
        features = geo["features"]
    else:
        features = [f for f in geo["features"] if f["properties"]["oblast_ua"] == selected_oblast]
    geo_view = {"type": "FeatureCollection", "features": features}
    keys_in_view = {f["properties"]["norm_key"] for f in features}

    # --- Фільтри форми власності та пакету НСЗУ ---
    ownership_options = list(OWNERSHIP_LABEL_KEYS_ORDER)
    selected_ownership_keys = st.sidebar.multiselect(
        ui["ownership_filter_label"],
        options=ownership_options,
        default=ownership_options,
        format_func=lambda k: UI_TEXTS[lang]["not_specified"] if k == UNSPECIFIED_KEY else ui["ownership_labels"][k],
    )
    nhsu_filter = st.sidebar.radio(
        ui["nhsu_filter_label"],
        options=["all", "yes", "no"],
        format_func=lambda v: {"all": ui["nhsu_filter_all"], "yes": ui["nhsu_filter_yes"], "no": ui["nhsu_filter_no"]}[v],
        horizontal=True,
    )

    df_scope = df[df["hromada_norm"].isin(keys_in_view)]
    df_filtered = df_scope[df_scope["_ownership_key"].isin(selected_ownership_keys)]
    if nhsu_filter == "yes":
        df_filtered = df_filtered[df_filtered["_is_medical"]]
    elif nhsu_filter == "no":
        df_filtered = df_filtered[~df_filtered["_is_medical"]]

    agg_view = compute_hromada_stats(df_filtered)

    # Список громад для випадаючого списку — каскадно звужується разом з
    # фільтром області вище (features вже відфільтровані за оболастю).
    # Це суто географічний вибір, тому не залежить від фільтрів власності/НСЗУ.
    name_field = "hromada_ua" if lang == "uk" else "hromada_en"
    hromada_display_by_key = {f["properties"]["norm_key"]: f["properties"][name_field] for f in features}
    selected_hromada_key = st.sidebar.selectbox(
        ui["hromada_select_label"],
        options=[NO_HROMADA_SELECTED] + sorted(hromada_display_by_key, key=lambda k: hromada_display_by_key[k]),
        format_func=lambda k: ui["hromada_select_placeholder"] if k is NO_HROMADA_SELECTED else hromada_display_by_key[k],
    )

    if selected_hromada_key is not NO_HROMADA_SELECTED:
        hromada_display_name = hromada_display_by_key[selected_hromada_key]
        # Список закладів відповідає активним фільтрам власності/НСЗУ, щоб не
        # суперечити тому, що показано на карті.
        facility_rows = df_filtered[df_filtered["hromada_norm"] == selected_hromada_key]
        with st.sidebar.expander(f"{ui['hromada_detail_header']}: {hromada_display_name}", expanded=True):
            if facility_rows.empty:
                st.caption(ui["no_facilities_matched"])
            else:
                st.markdown(ui["hromada_detail_total"].format(n=len(facility_rows)))
                for _, row in facility_rows.iterrows():
                    name = row[COL_PROVIDER_NAME]
                    name = str(name).strip() if is_filled(name) else ui["facility_name_fallback"]
                    ownership = ownership_label_for_value(row[COL_OWNERSHIP], lang)
                    nhsu_value = row[COL_NHSU]
                    if is_filled(nhsu_value):
                        tag = f"{ui['facility_medical_tag']} ({str(nhsu_value).strip()})"
                    else:
                        tag = ui["facility_social_tag"]
                    st.markdown(f"- **{name}** — {ownership} · {tag}")

    tab1, tab2 = st.tabs([ui["tab_map"], ui["tab_data"]])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(ui["kpi_total"], int(agg_view["total"].sum()) if not agg_view.empty else 0)
        col2.metric(ui["kpi_medical"], int(agg_view["medical"].sum()) if not agg_view.empty else 0)
        col3.metric(ui["kpi_social"], int(agg_view["social"].sum()) if not agg_view.empty else 0)
        col4.metric(ui["kpi_hromadas"], int((agg_view["total"] > 0).sum()) if not agg_view.empty else 0)

        m = build_map(geo_view, agg_view, df_filtered, lang, ui)
        st_folium(m, width=None, height=700, returned_objects=[])

    with tab2:
        df_display = df.drop(columns=["hromada_norm", "hromada_norm_baseline"]).rename(columns=ui["columns"])
        st.dataframe(df_display, use_container_width=True)

        unmatched_display = unmatched.copy()
        unmatched_display["ownership_str"] = unmatched_display["ownership_counts"].apply(
            lambda c: format_ownership_str(c, lang)
        )
        unmatched_display = unmatched_display.drop(columns=["ownership_counts"]).rename(
            columns={
                "norm_key": ui["unmatched_col_key"],
                "oblasts": ui["columns"]["Oblast"],
                "raions": ui["columns"]["Raion"],
                "total": ui["unmatched_col_total"],
                "medical": ui["unmatched_col_medical"],
                "social": ui["unmatched_col_social"],
                "ownership_str": ui["unmatched_col_ownership"],
            }
        )
        unmatched_display = unmatched_display[
            [
                ui["unmatched_col_key"],
                ui["columns"]["Oblast"],
                ui["columns"]["Raion"],
                ui["unmatched_col_total"],
                ui["unmatched_col_medical"],
                ui["unmatched_col_social"],
                ui["unmatched_col_ownership"],
            ]
        ]
        with st.expander(ui["unmatched_expander"].format(n=len(unmatched))):
            st.dataframe(unmatched_display, use_container_width=True)
            st.download_button(
                label=ui["download_unmatched_button"],
                data=unmatched_display.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"unmatched_hromadas_{lang}.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
