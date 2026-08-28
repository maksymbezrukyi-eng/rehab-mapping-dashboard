"""Мапа надавачів послуг педіатричної реабілітації в Україні."""

import html
import json
import math
import random
import re
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = BASE_DIR / "NEW_Mapping_tracker_2506.xlsx"
GEOJSON_PATH = BASE_DIR / "ukraine_hromadas.geojson"
SHEET_NAME = "Provider Data"

COL_HROMADA = "Hromada"
COL_OBLAST = "Oblast"
COL_RAION = "Raion"
COL_ADDRESS = "Address"
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
NO_PROVIDER_SELECTED = None  # сентинель "надавача не обрано" для селектора

HIGHLIGHT_COLOR = "#e11d48"  # акцентний колір контуру обраної громади (відмінний від YlOrRd і від кольорів форми власності)

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

OWNERSHIP_ALIASES = {
    "public": "public",
    "communal": "communal",
    "communal (hromada)": "communal",
    "private": "private",
    "ngo-charitable": "ngo-charitable",
    "ngo/charitable": "ngo-charitable",
    "ngo/charity": "ngo-charitable",
    "donor": "donor",
    "mixed": "mixed",
}

# Значення області в Excel подані іменниковими англійськими назвами, тоді як
# GeoJSON містить офіційні українські назви. Явний невеликий словник робить
# перетворення аудованим і не дозволяє випадково змішати Київ із Київською обл.
EXCEL_OBLAST_TO_GEO = {
    "cherkasy": "Черкаська область",
    "chernihiv": "Чернігівська область",
    "chernivtsi": "Чернівецька область",
    "dnipropetrovsk": "Дніпропетровська область",
    "donetsk": "Донецька область",
    "ivano-frankivsk": "Івано-Франківська область",
    "kharkiv": "Харківська область",
    "kherson": "Херсонська область",
    "khmelnytskyi": "Хмельницька область",
    "kirovohrad": "Кіровоградська область",
    "kyiv": "Київська область",
    "kyiv oblast": "Київська область",
    "kyiv city": "Київ",
    "luhansk": "Луганська область",
    "lviv": "Львівська область",
    "mykolaiv": "Миколаївська область",
    "odesa": "Одеська область",
    "poltava": "Полтавська область",
    "rivne": "Рівненська область",
    "sumy": "Сумська область",
    "ternopil": "Тернопільська область",
    "vinnytsia": "Вінницька область",
    "volyn": "Волинська область",
    "zakarpattia": "Закарпатська область",
    "zaporizhzhia": "Запорізька область",
    "zhytomyr": "Житомирська область",
}

HROMADA_TYPE_ALIASES = {
    "miska": "city",
    "silska": "rural",
    "selyshchna": "settlement",
    "terytorialna": "territorial",
}

# Короткі іменникові назви районних центрів з Excel зводимо до прикметникових
# ключів районів у GeoJSON. Словник навмисно обмежений перевіреними конфліктами:
# він не застосовує нечітке зіставлення і не може перекинути рядок в іншу область.
EXCEL_RAION_TO_GEO_KEY = {
    "berdiansk": "berdianskyi",
    "brovary": "brovarskyi",
    "dnipro": "dniprovskyi",
    "nikopol": "nikopolskyi",
    "nizhyn": "nizhynskyi",
    "odesa": "odeskyi",
    "pervomaisk": "pervomaiskyi",
    "polohy": "polohivskyi",
    "pryluky": "prylutskyi",
    "rozdilna": "rozdilnianskyi",
    "sumy": "sumskyi",
    "synelnykove": "synelnykivskyi",
    "vasylivka": "vasylivskyi",
    "zaporizhzhia": "zaporizkyi",
}

# Перевірені орфографічні варіанти, де Excel і GeoJSON описують ту саму громаду.
EXCEL_HROMADA_ALIASES = {
    "andriivska": "andrivska",
}

# У вихідному GeoJSON дві різні Талалаївські громади мають однакові підписи.
# Геометрія geo:341 відповідає селищній громаді Прилуцького району; geo:340 —
# сільській громаді Ніжинського району. Це підтверджено складом районів на
# державному порталі decentralization.gov.ua.
GEO_PROPERTY_CORRECTIONS = {
    341: {
        "hromada": "Талалаївська селищна громада",
        "rayon": "Прилуцький район",
    },
}

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
    # Назва "Oleksandriia" повторюється в кількох областях, але новий складений
    # ключ (область + назва + конкретний geo_id) розділяє ці громади коректно.
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
        "oblast_stats_header": "📊 Статистика по області",
        "oblast_stats_hromadas": "Громад із закладами",
        "oblast_stats_total": "Усього закладів",
        "oblast_stats_medical": "Медичних",
        "oblast_stats_social": "Соціальних",
        "provider_select_label": "Оберіть надавача",
        "provider_select_placeholder": "— не обрано —",
        "provider_card_header": "🏷️ Картка надавача",
        "provider_card_address": "Адреса",
        "provider_card_oblast": "Область",
        "provider_card_raion": "Район",
        "provider_card_hromada": "Громада",
        "provider_card_ownership": "Форма власності",
        "provider_card_nhsu": "Пакет НСЗУ",
        "provider_card_service_format": "Формат надання послуг",
        "provider_card_target_population": "Цільова група",
        "provider_card_focus": "Основний напрям реабілітації",
        "provider_card_mdt": "МДК (мультидисциплінарна команда)",
        "provider_card_staff": "Ключові фахівці",
        "provider_card_volume": "Обсяг (пацієнтів/рік)",
        "show_boundaries_label": "Показувати межі громад",
        "layer_boundaries": "Межі громад",
        "layer_highlight": "Обрана громада",
        "selected_hromada_caption": "🔴 Обрана громада: {name}",
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
        "view_mode_label": "Режим карти",
        "view_mode_polygons": "🗺️ Карта громад (полігони)",
        "view_mode_points": "📍 Карта точок (надавачі послуг)",
        "quality_header": "Покриття географічного зіставлення",
        "quality_source": "Записів у джерелі",
        "quality_mapped": "Показано на карті",
        "quality_unmatched": "Без полігона",
        "quality_note": "Незіставлені записи не втрачаються: вони доступні в сирій таблиці та у CSV-звіті нижче.",
        "kpi_total": "Закладів за фільтрами",
        "kpi_medical": "Медичні заклади",
        "kpi_social": "Соціальні заклади",
        "kpi_hromadas": "Громад за фільтрами",
        "tooltip_hromada": "Громада:",
        "tooltip_total": "Всього закладів:",
        "tooltip_medical": "Медичних:",
        "tooltip_social": "Соціальних:",
        "tooltip_ownership": "Форма власності:",
        "legend_total": "Кількість закладів",
        "layer_choropleth": "Заклади за громадами",
        "layer_points": "📍 Заклади (точки) — очікує геокодування",
        "unmatched_expander": "⚠️ Незіставлені назви громад ({groups}; записів: {rows})",
        "unmatched_col_key": "Нормалізована назва",
        "unmatched_col_status": "Причина",
        "unmatched_col_total": "Всього закладів",
        "unmatched_col_medical": "Медичних",
        "unmatched_col_social": "Соціальних",
        "unmatched_col_ownership": "Форма власності",
        "download_unmatched_button": "⬇️ Завантажити список незматчених (CSV)",
        "match_status_labels": {
            "name_not_found": "Полігон із такою назвою відсутній",
            "ambiguous": "Потрібне уточнення громади",
            "unknown_oblast": "Область не розпізнано",
        },
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
        "oblast_stats_header": "📊 Oblast statistics",
        "oblast_stats_hromadas": "Hromadas with facilities",
        "oblast_stats_total": "Total facilities",
        "oblast_stats_medical": "Medical",
        "oblast_stats_social": "Social",
        "provider_select_label": "Select provider",
        "provider_select_placeholder": "— none selected —",
        "provider_card_header": "🏷️ Provider card",
        "provider_card_address": "Address",
        "provider_card_oblast": "Oblast",
        "provider_card_raion": "Raion",
        "provider_card_hromada": "Hromada",
        "provider_card_ownership": "Ownership type",
        "provider_card_nhsu": "NHSU package",
        "provider_card_service_format": "Service format",
        "provider_card_target_population": "Target population",
        "provider_card_focus": "Primary rehabilitation focus",
        "provider_card_mdt": "MDT (multidisciplinary team)",
        "provider_card_staff": "Key professionals",
        "provider_card_volume": "Volume (patients/year)",
        "show_boundaries_label": "Show hromada boundaries",
        "layer_boundaries": "Hromada boundaries",
        "layer_highlight": "Selected hromada",
        "selected_hromada_caption": "🔴 Selected hromada: {name}",
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
        "view_mode_label": "Map view",
        "view_mode_polygons": "🗺️ Hromada map (polygons)",
        "view_mode_points": "📍 Points map (service providers)",
        "quality_header": "Geographic matching coverage",
        "quality_source": "Source records",
        "quality_mapped": "Shown on map",
        "quality_unmatched": "Without a polygon",
        "quality_note": "Unmatched records are retained in the raw table and in the downloadable CSV report below.",
        "kpi_total": "Facilities after filters",
        "kpi_medical": "Medical facilities",
        "kpi_social": "Social facilities",
        "kpi_hromadas": "Hromadas after filters",
        "tooltip_hromada": "Hromada:",
        "tooltip_total": "Total facilities:",
        "tooltip_medical": "Medical:",
        "tooltip_social": "Social:",
        "tooltip_ownership": "Ownership type:",
        "legend_total": "Number of facilities",
        "layer_choropleth": "Facilities by hromada",
        "layer_points": "📍 Facilities (points) — pending geocoding",
        "unmatched_expander": "⚠️ Unmatched hromada names ({groups}; records: {rows})",
        "unmatched_col_key": "Normalized name",
        "unmatched_col_status": "Reason",
        "unmatched_col_total": "Total facilities",
        "unmatched_col_medical": "Medical",
        "unmatched_col_social": "Social",
        "unmatched_col_ownership": "Ownership",
        "download_unmatched_button": "⬇️ Download unmatched list (CSV)",
        "match_status_labels": {
            "name_not_found": "No polygon with this name",
            "ambiguous": "Hromada needs clarification",
            "unknown_oblast": "Oblast is not recognized",
        },
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
    base = EXCEL_HROMADA_ALIASES.get(base, base)
    mapped_ua_adj = _CITY_TO_HROMADA_LOOKUP.get(base)
    if mapped_ua_adj is not None:
        return normalize_text_en(transliterate_ua_to_en(mapped_ua_adj))
    return base


def normalize_oblast_from_excel(raw_value) -> str | None:
    if not is_filled(raw_value):
        return None
    return EXCEL_OBLAST_TO_GEO.get(re.sub(r"\s+", " ", str(raw_value).strip().lower()))


def normalize_raion(text) -> str:
    if not is_filled(text):
        return ""
    base = normalize_text(str(text), ["raion"])
    return EXCEL_RAION_TO_GEO_KEY.get(base, base)


def detect_hromada_type(text) -> str | None:
    if not is_filled(text):
        return None
    transliterated = transliterate_ua_to_en(str(text)).lower()
    tokens = set(re.findall(r"[a-z]+", transliterated))
    for token, canonical in HROMADA_TYPE_ALIASES.items():
        if token in tokens:
            return canonical
    return None


def detect_hromada_type_from_row(row: pd.Series) -> str | None:
    """Визначає тип громади з назви, а для коротких назв — з адреси."""
    explicit_type = detect_hromada_type(row.get(COL_HROMADA))
    if explicit_type:
        return explicit_type

    if not is_filled(row.get(COL_ADDRESS)):
        return None
    address = str(row.get(COL_ADDRESS)).lower()
    # Порядок важливий: у деяких адресах одночасно трапляються "с." і "смт".
    if re.search(r"(?:^|[\s,])(?:смт|с-ще|селище)\.?\s", address):
        return "settlement"
    if re.search(r"(?:^|[\s,])(?:м\.|місто\s)", address):
        return "city"
    if re.search(r"(?:^|[\s,])(?:с\.|село\s)", address):
        return "rural"
    return None


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

    for index, feature in enumerate(geo["features"]):
        props = feature["properties"]
        correction = GEO_PROPERTY_CORRECTIONS.get(props.get("id"))
        if correction:
            props.update(correction)
        hromada_ua = props.get("hromada", "")
        hromada_en = transliterate_ua_to_en(hromada_ua)
        oblast_ua = props.get("region", "")
        oblast_en = transliterate_ua_to_en(oblast_ua)
        rayon_ua = props.get("rayon", "")
        rayon_en = transliterate_ua_to_en(rayon_ua)
        props["hromada_ua"] = hromada_ua
        props["hromada_en"] = hromada_en
        props["oblast_ua"] = oblast_ua
        props["oblast_en"] = oblast_en
        props["rayon_ua"] = rayon_ua
        props["rayon_en"] = rayon_en
        props["norm_key"] = normalize_text_en(hromada_en)
        props["raion_key"] = normalize_raion(rayon_en)
        props["hromada_type"] = detect_hromada_type(hromada_en)
        props["geo_id"] = f"geo:{props.get('id', index)}"
    return geo


def resolve_facility_geography(df: pd.DataFrame, geo: dict) -> pd.DataFrame:
    """Однозначно зіставляє рядок Excel із конкретною фічею GeoJSON.

    Пошук завжди обмежується областю. Якщо в області є кілька однойменних
    громад, додатково використовуються район і тип громади. Неоднозначний
    випадок не вгадується: він лишається unmatched із відповідним статусом.
    """
    candidates_by_region_and_name: dict[tuple[str, str], list[dict]] = {}
    for feature in geo["features"]:
        props = feature["properties"]
        candidates_by_region_and_name.setdefault((props["oblast_ua"], props["norm_key"]), []).append(feature)

    geo_ids: list[str | None] = []
    statuses: list[str] = []
    candidate_counts: list[int] = []

    for _, row in df.iterrows():
        oblast_ua = normalize_oblast_from_excel(row.get(COL_OBLAST))
        if oblast_ua is None:
            geo_ids.append(None)
            statuses.append("unknown_oblast")
            candidate_counts.append(0)
            continue

        candidates = list(candidates_by_region_and_name.get((oblast_ua, row["hromada_norm"]), []))
        candidate_counts.append(len(candidates))
        if not candidates:
            geo_ids.append(None)
            statuses.append("name_not_found")
            continue

        narrowed = candidates
        raion_key = normalize_raion(row.get(COL_RAION))
        if raion_key:
            by_raion = [f for f in narrowed if f["properties"]["raion_key"] == raion_key]
            if by_raion:
                narrowed = by_raion

        hromada_type = detect_hromada_type_from_row(row)
        if hromada_type:
            by_type = [f for f in narrowed if f["properties"]["hromada_type"] == hromada_type]
            if by_type:
                narrowed = by_type

        if len(narrowed) == 1:
            geo_ids.append(narrowed[0]["properties"]["geo_id"])
            statuses.append("matched")
        else:
            geo_ids.append(None)
            statuses.append("ambiguous")

    resolved = df.copy()
    resolved["_geo_id"] = geo_ids
    resolved["_match_status"] = statuses
    resolved["_match_candidate_count"] = candidate_counts
    return resolved


def is_filled(value) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip() != ""


def canonical_ownership_key(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return UNSPECIFIED_KEY
    normalized = re.sub(r"\s+", " ", str(value).strip().lower())
    normalized = re.sub(r"\s*/\s*", "/", normalized)
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    return OWNERSHIP_ALIASES.get(normalized, normalized)


def prepare_source_display(df: pd.DataFrame) -> pd.DataFrame:
    """Повертає лише вихідні колонки Excel у безпечному для Streamlit вигляді."""
    technical_columns = {"hromada_norm", "hromada_norm_baseline"}
    source_columns = [
        column
        for column in df.columns
        if not column.startswith("_") and column not in technical_columns
    ]
    display = df[source_columns].copy()
    if "ID" in display.columns:
        display["ID"] = display["ID"].map(
            lambda value: None
            if pd.isna(value)
            else str(int(value))
            if isinstance(value, float) and value.is_integer()
            else str(value)
        )
    # Excel-колонки на кшталт NHSU package містять суміш чисел і тексту.
    # Уніфікуємо лише відображувану копію, щоб Arrow/Streamlit не вгадував типи.
    for column in display.columns:
        dtype = display[column].dtype
        if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
            display[column] = display[column].map(
                lambda value: None if pd.isna(value) else str(value)
            )
    return display


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
    """Групує зіставлені заклади за унікальним geo_id. Не кешована навмисно: викликається і на

    повному df (через aggregate_providers нижче — кешовано, важкий шлях), і на
    інтерактивно відфільтрованому df (форма власності/НСЗУ у сайдбарі — тут
    кешування не дало б користі, бо вхід міняється щовидгету, а групування
    ~5600 рядків саме по собі займає одиниці мілісекунд).
    """
    columns = ["geo_id", "total", "medical", "social", "ownership_counts", "oblasts", "raions"]
    if df.empty:
        # Порожній вхід (наприклад, фільтри в сайдбарі відсікли всі заклади) —
        # повертаємо DataFrame з правильними колонками, а не порожній без жодної,
        # інакше .set_index("geo_id") нижче по коду впаде з KeyError.
        return pd.DataFrame(columns=columns)

    records = []
    for geo_id, group in df.dropna(subset=["_geo_id"]).groupby("_geo_id"):
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
                "geo_id": geo_id,
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
def log_mapping_impact(df: pd.DataFrame) -> None:
    """Друкує підсумок однозначного географічного зіставлення."""
    total = len(df)
    counts = df["_match_status"].value_counts().to_dict()
    matched = int(counts.get("matched", 0))

    print("=" * 60)
    print("[GEOGRAPHY MATCHING] Summary")
    print(f"  Source facility records: {total}")
    print(f"  Uniquely matched: {matched} ({matched / total:.1%})")
    for status in ("name_not_found", "ambiguous", "unknown_oblast"):
        print(f"  {status}: {int(counts.get(status, 0))}")
    print("=" * 60)


@st.cache_data(show_spinner=False)
def find_unmatched(df: pd.DataFrame) -> pd.DataFrame:
    """Агрегує рядки, які не вдалося однозначно зіставити з GeoJSON."""
    unmatched_df = df[df["_geo_id"].isna()]
    columns = ["norm_key", "match_status", "total", "medical", "social", "ownership_counts", "oblasts", "raions"]
    if unmatched_df.empty:
        return pd.DataFrame(columns=columns)

    records = []
    for (norm_key, match_status), group in unmatched_df.groupby(["hromada_norm", "_match_status"]):
        total = len(group)
        medical = int(group["_is_medical"].sum())
        records.append(
            {
                "norm_key": norm_key,
                "match_status": match_status,
                "total": total,
                "medical": medical,
                "social": total - medical,
                "ownership_counts": group["_ownership_key"].value_counts().to_dict(),
                "oblasts": "; ".join(sorted(group[COL_OBLAST].dropna().astype(str).str.strip().unique())),
                "raions": "; ".join(sorted(group[COL_RAION].dropna().astype(str).str.strip().unique())),
            }
        )
    return pd.DataFrame(records, columns=columns).sort_values("total", ascending=False)


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


def point_on_ring_boundary(lon: float, lat: float, ring: list, tolerance: float = 1e-10) -> bool:
    """Перевіряє, чи лежить точка на відрізку межі кільця."""
    for index in range(len(ring)):
        x1, y1 = ring[index][0], ring[index][1]
        x2, y2 = ring[(index + 1) % len(ring)][0], ring[(index + 1) % len(ring)][1]
        cross = (lon - x1) * (y2 - y1) - (lat - y1) * (x2 - x1)
        if abs(cross) > tolerance:
            continue
        if min(x1, x2) - tolerance <= lon <= max(x1, x2) + tolerance and min(y1, y2) - tolerance <= lat <= max(y1, y2) + tolerance:
            return True
    return False


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    """Ray-casting для одного кільця; його межа вважається частиною полігона."""
    if len(ring) < 3:
        return False
    if point_on_ring_boundary(lon, lat, ring):
        return True

    inside = False
    previous = len(ring) - 1
    for current in range(len(ring)):
        x1, y1 = ring[current][0], ring[current][1]
        x2, y2 = ring[previous][0], ring[previous][1]
        if (y1 > lat) != (y2 > lat):
            intersection_x = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lon < intersection_x:
                inside = not inside
        previous = current
    return inside


def point_in_polygon(lon: float, lat: float, polygon: list) -> bool:
    if not polygon or not point_in_ring(lon, lat, polygon[0]):
        return False
    # Точка всередині отвору не належить полігону; межа отвору теж не є
    # безпечною позицією для маркера, тому виключаємо її разом із внутрішністю.
    return not any(point_in_ring(lon, lat, hole) for hole in polygon[1:])


def geometry_contains_point(geometry: dict, lon: float, lat: float) -> bool:
    gtype = geometry.get("type")
    if gtype == "Polygon":
        return point_in_polygon(lon, lat, geometry.get("coordinates", []))
    if gtype == "MultiPolygon":
        return any(
            point_in_polygon(lon, lat, polygon)
            for polygon in geometry.get("coordinates", [])
        )
    return False


def geometry_interior_point(geometry: dict) -> tuple[float, float, float] | None:
    """Повертає гарантовано внутрішню опорну точку та розмір геометрії."""
    centroid = geometry_centroid_and_extent(geometry)
    if centroid is None:
        return None
    centroid_lon, centroid_lat, extent = centroid
    if geometry_contains_point(geometry, centroid_lon, centroid_lat):
        return centroid

    gtype = geometry.get("type")
    polygons = [geometry["coordinates"]] if gtype == "Polygon" else geometry.get("coordinates", [])
    polygons_by_area = sorted(
        (polygon for polygon in polygons if polygon and polygon[0]),
        key=lambda polygon: polygon_ring_centroid(polygon[0])[0],
        reverse=True,
    )

    # Спершу пробуємо центроїд кожної окремої частини MultiPolygon.
    for polygon in polygons_by_area:
        _, lon, lat = polygon_ring_centroid(polygon[0])
        if point_in_polygon(lon, lat, polygon):
            return lon, lat, extent

    # Для сильно увігнутих полігонів знаходимо найближчу до центроїда точку
    # на регулярній внутрішній сітці. 25×25 достатньо для поточного GeoJSON.
    candidates: list[tuple[float, float, float]] = []
    for polygon in polygons_by_area:
        exterior = polygon[0]
        min_lon = min(point[0] for point in exterior)
        max_lon = max(point[0] for point in exterior)
        min_lat = min(point[1] for point in exterior)
        max_lat = max(point[1] for point in exterior)
        for x_index in range(25):
            lon = min_lon + (x_index + 0.5) * (max_lon - min_lon) / 25
            for y_index in range(25):
                lat = min_lat + (y_index + 0.5) * (max_lat - min_lat) / 25
                if point_in_polygon(lon, lat, polygon):
                    distance = (lon - centroid_lon) ** 2 + (lat - centroid_lat) ** 2
                    candidates.append((distance, lon, lat))
    if candidates:
        _, lon, lat = min(candidates)
        return lon, lat, extent

    # Вкрай вироджена геометрія: координата межі все одно належить полігону.
    if polygons_by_area:
        lon, lat = polygons_by_area[0][0][0][:2]
        return lon, lat, extent
    return None


def geometry_bounds(geometry: dict) -> tuple[float, float, float, float] | None:
    """(min_lon, min_lat, max_lon, max_lat) для Polygon/MultiPolygon — для fit_bounds()."""
    gtype = geometry.get("type")
    if gtype == "Polygon":
        polygons = [geometry["coordinates"]]
    elif gtype == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return None

    lons, lats = [], []
    for poly in polygons:
        if not poly:
            continue
        lons.extend(p[0] for p in poly[0])
        lats.extend(p[1] for p in poly[0])
    if not lons:
        return None
    return min(lons), min(lats), max(lons), max(lats)


def union_bounds(features: list) -> tuple[float, float, float, float] | None:
    """Об'єднані межі кількох фіч — для фокусування карти на цілій області."""
    all_bounds = [b for b in (geometry_bounds(f["geometry"]) for f in features) if b is not None]
    if not all_bounds:
        return None
    return (
        min(b[0] for b in all_bounds),
        min(b[1] for b in all_bounds),
        max(b[2] for b in all_bounds),
        max(b[3] for b in all_bounds),
    )


def fit_map_to_bounds(m: folium.Map, bounds: tuple[float, float, float, float] | None) -> None:
    if bounds is not None:
        min_lon, min_lat, max_lon, max_lat = bounds
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])


def jitter_point(lon: float, lat: float, extent: float, seed: int) -> tuple[float, float]:
    """Невеликий випадковий (але детермінований за seed) зсув точки навколо центру
    громади, щоб заклади в одній громаді не накладались один на одного."""
    rng = random.Random(seed)
    radius = rng.uniform(0, max(extent * 0.12, 0.01))
    angle = rng.uniform(0, 2 * math.pi)
    return lon + radius * math.cos(angle), lat + radius * math.sin(angle)


def jitter_point_inside_geometry(
    lon: float,
    lat: float,
    extent: float,
    geometry: dict,
    seed: int,
) -> tuple[float, float]:
    """Розводить маркери, але ніколи не виносить їх за межі громади."""
    for attempt in range(48):
        jlon, jlat = jitter_point(lon, lat, extent, seed=seed * 97 + attempt)
        if geometry_contains_point(geometry, jlon, jlat):
            return jlon, jlat
    return lon, lat


def geocode_facilities(df: pd.DataFrame, geo: dict) -> pd.DataFrame:
    """Координати закладу = центроїд полігону його громади + jitter-розкид.

    Миттєво і без зовнішніх залежностей (жодних мережевих запитів), тому не
    потребує власного @st.cache_data — і так виконується лише в момент
    cache-miss всередині prepare_data (див. коментар там). Заклади з громадою,
    якої немає серед полігонів (unmatched), отримують lat/lon = None і просто
    пропускаються при малюванні точок — без падіння коду.
    """
    locations: dict[str, tuple[float, float, float, dict]] = {}
    for feature in geo["features"]:
        key = feature["properties"]["geo_id"]
        result = geometry_interior_point(feature["geometry"])
        if result is not None:
            lon, lat, extent = result
            locations[key] = lon, lat, extent, feature["geometry"]

    lats: list[float | None] = []
    lons: list[float | None] = []
    for idx, geo_id in df["_geo_id"].items():
        center = locations.get(geo_id)
        if center is None:
            lats.append(None)
            lons.append(None)
            continue
        lon, lat, extent, geometry = center
        jlon, jlat = jitter_point_inside_geometry(
            lon, lat, extent, geometry, seed=int(idx)
        )
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
    df = resolve_facility_geography(df, geo)
    log_mapping_impact(df)
    df = geocode_facilities(df, geo)
    agg = aggregate_providers(df)
    unmatched = find_unmatched(df)
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


UKRAINE_CENTER = [48.3794, 31.1656]


def new_base_map() -> folium.Map:
    # OpenStreetMap — безкоштовний тайл без API-ключа (CartoDB positron вимагав
    # ключ і показував водяний знак "API key required"). Використовується для
    # ОБОХ режимів карти (полігони і точки), щоб водяний знак не повернувся
    # десь одним випадковим забутим tiles=.
    return folium.Map(location=UKRAINE_CENTER, zoom_start=6, tiles="OpenStreetMap")


def _apply_focus_and_highlight(m: folium.Map, geo: dict, selected_geo_id: str | None, lang: str, ui: dict) -> None:
    """Спільна для обох режимів карти логіка фокусу/підсвітки.

    Без обраної громади — фокус (fit_bounds) на всі фічі geo (тобто на область,
    якщо вона обрана у сайдбарі, або на всю Україну, якщо ні). З обраною
    громадою — фокус лише на неї + товстий контурний оверлей акцентного кольору
    поверх решти шарів.
    """
    if selected_geo_id is None:
        fit_map_to_bounds(m, union_bounds(geo["features"]))
        return

    target = next((f for f in geo["features"] if f["properties"]["geo_id"] == selected_geo_id), None)
    if target is None:
        fit_map_to_bounds(m, union_bounds(geo["features"]))
        return

    fit_map_to_bounds(m, geometry_bounds(target["geometry"]))
    folium.GeoJson(
        {"type": "FeatureCollection", "features": [target]},
        style_function=lambda _: {"fillOpacity": 0, "color": HIGHLIGHT_COLOR, "weight": 4},
        control=False,
    ).add_to(m)
    name_field = "hromada_ua" if lang == "uk" else "hromada_en"
    caption = ui["selected_hromada_caption"].format(name=target["properties"][name_field])
    caption_html = (
        '<div style="position: fixed; top: 80px; left: 10px; z-index: 9999; '
        'background: white; color: #111; padding: 6px 12px; border-radius: 6px; '
        'box-shadow: 0 1px 4px rgba(0,0,0,0.35); font-size: 13px;">'
        f"{html.escape(caption)}</div>"
    )
    m.get_root().html.add_child(folium.Element(caption_html))


def build_polygon_map(
    geo: dict, agg: pd.DataFrame, lang: str, ui: dict, selected_geo_id: str | None = None
) -> folium.Map:
    """Режим 1: хороплет громад за кількістю закладів + тултип зі статистикою.

    Якщо обрано конкретну громаду (з каскадного селектора в сайдбарі) — карта
    фокусується на ній (fit_bounds) і додає окремий контурний шар поверх
    хороплету (товща лінія акцентного кольору), бо стилізувати єдину фічу
    всередині вбудованого folium.Choropleth напряму неможливо.
    """
    m = new_base_map()

    # Свіжий per-render мердж статистики (agg тут може бути вже відфільтрованим
    # за формою власності/НСЗУ) у properties полігонів — без мутації кешованого
    # geo, тож функція лишається дешевою і безпечною для повторних викликів.
    name_field = "hromada_ua" if lang == "uk" else "hromada_en"
    stats_by_key = agg.set_index("geo_id").to_dict("index")
    for feature in geo["features"]:
        props = feature["properties"]
        stats = stats_by_key.get(props["geo_id"], {"total": 0, "medical": 0, "social": 0, "ownership_counts": {}})
        props["total"] = int(stats["total"])
        props["medical"] = int(stats["medical"])
        props["social"] = int(stats["social"])
        props["ownership_display"] = format_ownership_str(stats.get("ownership_counts", {}), lang)

    choropleth = folium.Choropleth(
        geo_data=geo,
        data=agg,
        columns=["geo_id", "total"],
        key_on="feature.properties.geo_id",
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

    _apply_focus_and_highlight(m, geo, selected_geo_id, lang, ui)

    folium.LayerControl().add_to(m)
    return m


# JS-колбек для FastMarkerCluster: один спільний рядок JS замість тисяч окремих
# folium.CircleMarker+Popup Python-об'єктів. Дані (лат/лон/колір/попап) йдуть
# як компактний масив, безпечно серіалізований через Jinja |tojson (folium
# сам це робить у своєму шаблоні) — це і прибирає зависання браузера.
FAST_CLUSTER_CALLBACK = """
function (row) {
    var marker = L.circleMarker(new L.LatLng(row[0], row[1]), {
        radius: 5,
        color: row[2],
        weight: 1,
        fill: true,
        fillColor: row[2],
        fillOpacity: 0.85
    });
    marker.bindPopup(row[3], {maxWidth: 280});
    return marker;
}
"""


def build_points_map(
    facility_df: pd.DataFrame,
    geo_view: dict,
    lang: str,
    ui: dict,
    selected_geo_id: str | None = None,
    show_boundaries: bool = True,
) -> folium.Map:
    """Режим 2: точки окремих закладів, кольорові за формою власності.

    FastMarkerCluster, а не folium.plugins.MarkerCluster: останній все одно
    створює Python-об'єкт CircleMarker+Popup на кожен із ~5000 закладів і
    серіалізує їх повністю в HTML (сторінка виходила ~6+ МБ) — саме це
    "вішало" браузер ще до того, як спрацьовувала кластеризація (перевірено
    емпірично на цьому ж датасеті). FastMarkerCluster передає лише компактний
    масив даних і будує маркери в браузері одним спільним JS-колбеком.
    """
    m = new_base_map()

    if show_boundaries and geo_view["features"]:
        folium.GeoJson(
            geo_view,
            style_function=lambda _: {"fillOpacity": 0, "color": "#94a3b8", "weight": 1},
            name=ui["layer_boundaries"],
            control=False,
        ).add_to(m)

    rows = []
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
        rows.append([float(row["lat"]), float(row["lon"]), color, popup_html])

    FastMarkerCluster(data=rows, callback=FAST_CLUSTER_CALLBACK, name=ui["layer_points"]).add_to(m)

    _apply_focus_and_highlight(m, geo_view, selected_geo_id, lang, ui)

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

    st.caption(f"**{ui['quality_header']}**")
    quality_source, quality_mapped, quality_unmatched = st.columns(3)
    mapped_count = int(df["_geo_id"].notna().sum())
    unmatched_count = len(df) - mapped_count
    quality_source.metric(ui["quality_source"], len(df))
    quality_mapped.metric(ui["quality_mapped"], mapped_count)
    quality_unmatched.metric(ui["quality_unmatched"], unmatched_count)
    st.caption(ui["quality_note"])

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
    geo_ids_in_view = {f["properties"]["geo_id"] for f in features}

    # --- Фільтри форми власності та пакету НСЗУ ---
    observed_ownership_keys = set(df["_ownership_key"].unique())
    ownership_options = [key for key in OWNERSHIP_LABEL_KEYS_ORDER if key in observed_ownership_keys]
    ownership_options.extend(sorted(observed_ownership_keys - set(ownership_options)))
    selected_ownership_keys = st.sidebar.multiselect(
        ui["ownership_filter_label"],
        options=ownership_options,
        default=ownership_options,
        format_func=lambda k: UI_TEXTS[lang]["not_specified"]
        if k == UNSPECIFIED_KEY
        else ui["ownership_labels"].get(k, k.title()),
    )
    nhsu_filter = st.sidebar.radio(
        ui["nhsu_filter_label"],
        options=["all", "yes", "no"],
        format_func=lambda v: {"all": ui["nhsu_filter_all"], "yes": ui["nhsu_filter_yes"], "no": ui["nhsu_filter_no"]}[v],
        horizontal=True,
    )

    df_scope = df[df["_geo_id"].isin(geo_ids_in_view)]
    df_filtered = df_scope[df_scope["_ownership_key"].isin(selected_ownership_keys)]
    if nhsu_filter == "yes":
        df_filtered = df_filtered[df_filtered["_is_medical"]]
    elif nhsu_filter == "no":
        df_filtered = df_filtered[~df_filtered["_is_medical"]]

    agg_view = compute_hromada_stats(df_filtered)

    # --- Зведена статистика по обраній області (лише коли область конкретна) ---
    if selected_oblast is not ALL_OBLASTS:
        with st.sidebar.container(border=True):
            st.markdown(f"**{ui['oblast_stats_header']}**")
            st.caption(oblast_display[selected_oblast])
            st.markdown(f"{ui['oblast_stats_hromadas']}: **{int((agg_view['total'] > 0).sum()) if not agg_view.empty else 0}**")
            st.markdown(f"{ui['oblast_stats_total']}: **{int(agg_view['total'].sum()) if not agg_view.empty else 0}**")
            st.markdown(f"{ui['oblast_stats_medical']}: **{int(agg_view['medical'].sum()) if not agg_view.empty else 0}**")
            st.markdown(f"{ui['oblast_stats_social']}: **{int(agg_view['social'].sum()) if not agg_view.empty else 0}**")

    # Список громад для випадаючого списку — каскадно звужується разом з
    # фільтром області вище (features вже відфільтровані за оболастю).
    # Це суто географічний вибір, тому не залежить від фільтрів власності/НСЗУ.
    name_field = "hromada_ua" if lang == "uk" else "hromada_en"
    hromada_display_by_key = {f["properties"]["geo_id"]: f["properties"][name_field] for f in features}
    selected_geo_id = st.sidebar.selectbox(
        ui["hromada_select_label"],
        options=[NO_HROMADA_SELECTED] + sorted(hromada_display_by_key, key=lambda k: hromada_display_by_key[k]),
        format_func=lambda k: ui["hromada_select_placeholder"] if k is NO_HROMADA_SELECTED else hromada_display_by_key[k],
    )

    if selected_geo_id is not NO_HROMADA_SELECTED:
        hromada_display_name = hromada_display_by_key[selected_geo_id]
        # Список закладів відповідає активним фільтрам власності/НСЗУ, щоб не
        # суперечити тому, що показано на карті.
        facility_rows = df_filtered[df_filtered["_geo_id"] == selected_geo_id]
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

        # --- Вибір конкретного надавача в межах обраної громади ---
        provider_display_by_idx = {
            idx: (
                f"{str(row[COL_PROVIDER_NAME]).strip() if is_filled(row[COL_PROVIDER_NAME]) else ui['facility_name_fallback']}"
            )
            for idx, row in facility_rows.iterrows()
        }
        selected_provider_idx = st.sidebar.selectbox(
            ui["provider_select_label"],
            options=[NO_PROVIDER_SELECTED] + list(provider_display_by_idx),
            format_func=lambda idx: ui["provider_select_placeholder"]
            if idx is NO_PROVIDER_SELECTED
            else provider_display_by_idx[idx],
        )
        if selected_provider_idx is not NO_PROVIDER_SELECTED:
            provider = facility_rows.loc[selected_provider_idx]
            provider_name = provider_display_by_idx[selected_provider_idx]

            def _field(value) -> str:
                return str(value).strip() if is_filled(value) else ui["not_specified"]

            with st.sidebar.container(border=True):
                st.markdown(f"**{ui['provider_card_header']}**")
                st.markdown(f"**{provider_name}**")
                st.markdown(f"{ui['provider_card_address']}: {_field(provider['Address'])}")
                st.markdown(f"{ui['provider_card_oblast']}: {_field(provider['Oblast'])}")
                st.markdown(f"{ui['provider_card_raion']}: {_field(provider['Raion'])}")
                st.markdown(f"{ui['provider_card_hromada']}: {_field(provider[COL_HROMADA])}")
                st.markdown(f"{ui['provider_card_ownership']}: {ownership_label_for_value(provider[COL_OWNERSHIP], lang)}")
                st.markdown(f"{ui['provider_card_nhsu']}: {_field(provider[COL_NHSU])}")
                st.markdown(f"{ui['provider_card_service_format']}: {_field(provider.get('Service format (inpatient/outpatient/home/day care)'))}")
                st.markdown(f"{ui['provider_card_target_population']}: {_field(provider.get('Target population (0-3 / 3-18 / other)'))}")
                st.markdown(f"{ui['provider_card_focus']}: {_field(provider.get('Primary rehabilitation focus'))}")
                st.markdown(f"{ui['provider_card_mdt']}: {_field(provider.get('MDT (multidisciplinary team)'))}")
                st.markdown(f"{ui['provider_card_staff']}: {_field(provider.get('Key professionals present'))}")
                st.markdown(f"{ui['provider_card_volume']}: {_field(provider.get('Volume (patients/year — if available)'))}")

    tab1, tab2 = st.tabs([ui["tab_map"], ui["tab_data"]])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(ui["kpi_total"], int(agg_view["total"].sum()) if not agg_view.empty else 0)
        col2.metric(ui["kpi_medical"], int(agg_view["medical"].sum()) if not agg_view.empty else 0)
        col3.metric(ui["kpi_social"], int(agg_view["social"].sum()) if not agg_view.empty else 0)
        col4.metric(ui["kpi_hromadas"], int((agg_view["total"] > 0).sum()) if not agg_view.empty else 0)

        view_mode = st.radio(
            ui["view_mode_label"],
            options=["polygons", "points"],
            format_func=lambda v: ui["view_mode_polygons"] if v == "polygons" else ui["view_mode_points"],
            horizontal=True,
        )
        show_boundaries = False
        if view_mode == "points":
            show_boundaries = st.checkbox(ui["show_boundaries_label"], value=False)

        if view_mode == "polygons":
            m = build_polygon_map(geo_view, agg_view, lang, ui, selected_geo_id)
        else:
            m = build_points_map(df_filtered, geo_view, lang, ui, selected_geo_id, show_boundaries)
        st_folium(m, width=None, height=700, returned_objects=[])

    with tab2:
        df_display = prepare_source_display(df).rename(columns=ui["columns"])
        st.dataframe(df_display, width="stretch")

        unmatched_display = unmatched.copy()
        unmatched_display["ownership_str"] = unmatched_display["ownership_counts"].apply(
            lambda c: format_ownership_str(c, lang)
        )
        unmatched_display["match_status"] = unmatched_display["match_status"].map(
            lambda status: ui["match_status_labels"].get(status, status)
        )
        unmatched_display = unmatched_display.drop(columns=["ownership_counts"]).rename(
            columns={
                "norm_key": ui["unmatched_col_key"],
                "match_status": ui["unmatched_col_status"],
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
                ui["unmatched_col_status"],
                ui["columns"]["Oblast"],
                ui["columns"]["Raion"],
                ui["unmatched_col_total"],
                ui["unmatched_col_medical"],
                ui["unmatched_col_social"],
                ui["unmatched_col_ownership"],
            ]
        ]
        with st.expander(
            ui["unmatched_expander"].format(
                groups=len(unmatched),
                rows=int(unmatched["total"].sum()) if not unmatched.empty else 0,
            )
        ):
            st.dataframe(unmatched_display, width="stretch")
            st.download_button(
                label=ui["download_unmatched_button"],
                data=unmatched_display.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"unmatched_hromadas_{lang}.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
