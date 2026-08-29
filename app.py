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
ORIGINAL_EXCEL_PATH = BASE_DIR / "NEW_Mapping_tracker_2506.xlsx"
EXCEL_PATH = (
    BASE_DIR
    / "outputs"
    / "01a0488c-da0f-77a2-a696-ccfac34afd2f"
    / "NEW_Mapping_tracker_2506_verified.xlsx"
)
GEOJSON_PATH = BASE_DIR / "ukraine_hromadas.geojson"
OBLAST_GEOJSON_PATH = BASE_DIR / "ukraine_oblasts.geojson"
SHEET_NAME = "Provider Data"

COL_HROMADA = "Hromada"
COL_OBLAST = "Oblast"
COL_RAION = "Raion"
COL_ADDRESS = "Address"
COL_PROVIDER_NAME = "Provider Name"
COL_NHSU = "NHSU package (25/53/54)"
COL_NSSU = "NSSU listing (Y/N + details)"
COL_SOCIAL_CODE = "Code of social services"
COL_OWNERSHIP = "Ownership / funding type (public / communal / private / NGO-charitable / donor / mixed)"
COL_VERIFIED_OBLAST = "Verified Oblast"
COL_VERIFIED_RAION = "Verified Raion"
COL_VERIFIED_HROMADA = "Verified Hromada"
COL_VERIFIED_KATOTTG = "Verified KATOTTG"
COL_VERIFIED_GEO_ID = "Verified Geo ID"
COL_VERIFICATION_STATUS = "Verification Status"
VERIFICATION_COLUMNS = {
    COL_VERIFIED_OBLAST,
    COL_VERIFIED_RAION,
    COL_VERIFIED_HROMADA,
    COL_VERIFIED_KATOTTG,
    COL_VERIFIED_GEO_ID,
    COL_VERIFICATION_STATUS,
    "Verification Method",
    "Verification Source",
    "Verification Note",
    "Verified On",
}

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
    "public": "#2a7f78",
    "communal": "#2a7f78",
    "private": "#e38b52",
    "ngo-charitable": "#6b5ca5",
    "donor": "#6b5ca5",
    "mixed": "#6b5ca5",
    UNSPECIFIED_KEY: "#8b9692",
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
        "app_title": "Педіатрична реабілітація в Україні",
        "app_eyebrow": "REHAB MAPPING · VERIFIED DATA",
        "app_subtitle": "Досліджуйте мережу медичних і соціальних надавачів — від огляду областей до окремої громади.",
        "filter_header": "Фільтри карти",
        "filter_hint": "Спочатку оберіть територію, потім уточніть тип надавача.",
        "lang_label": "Оберіть мову / Choose language",
        "oblast_label": "Територія",
        "oblast_all": "Вся Україна",
        "kyiv_city_label": "Київ — місто",
        "hromada_select_label": "Оберіть громаду",
        "hromada_select_placeholder": "— не обрано —",
        "hromada_detail_header": "📋 Заклади в громаді",
        "hromada_detail_total": "Всього закладів: **{n}**",
        "facility_medical_tag": "🏥 Медичний",
        "facility_social_tag": "🤝 Соціальний",
        "facility_both_tag": "Медичний + соціальний",
        "facility_unclassified_tag": "Тип не визначено",
        "no_facilities_matched": "Немає зіставлених закладів у базі для цієї громади.",
        "facility_name_fallback": "Без назви",
        "oblast_stats_header": "Обрана територія",
        "oblast_stats_hromadas": "Громад із закладами",
        "oblast_stats_total": "Усього закладів",
        "oblast_stats_medical": "З пакетом НСЗУ",
        "oblast_stats_social": "З кодом соцпослуги / НССУ",
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
        "layer_oblast_boundaries": "Межі областей",
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
        "tab_map": "Карта",
        "tab_data": "Дані та методологія",
        "view_mode_label": "Рівень огляду",
        "view_mode_oblasts": "Області",
        "view_mode_hromadas": "Громади",
        "view_mode_points": "Надавачі",
        "view_mode_oblasts_hint": "Контури областей і пропорційні маркери показують концентрацію надавачів.",
        "view_mode_hromadas_hint": "Громади показані контурами; бірюзовий акцент означає наявність записів.",
        "view_mode_points_hint": "Точки наближені до центру громади й не є адресною геолокацією.",
        "quality_header": "Покриття географічного зіставлення",
        "quality_source": "Записів у джерелі",
        "quality_mapped": "Показано на карті",
        "quality_unmatched": "Без полігона",
        "quality_note": "Усі раніше незматчені записи перевірено за КАТОТТГ; початкові поля джерела збережено без змін.",
        "kpi_total": "Закладів за фільтрами",
        "kpi_medical": "З пакетом НСЗУ",
        "kpi_social": "З кодом соцпослуги / НССУ",
        "kpi_hromadas": "Громад за фільтрами",
        "service_definition": "Медичний = заповнений пакет НСЗУ. Соціальний = заповнений код соціальної послуги або запис НССУ. Категорії можуть перетинатися.",
        "verification_badge": "100% записів мають перевірений полігон",
        "data_date": "КАТОТТГ · 07.07.2026",
        "tooltip_hromada": "Громада:",
        "tooltip_total": "Всього закладів:",
        "tooltip_medical": "Медичних:",
        "tooltip_social": "Соціальних:",
        "tooltip_ownership": "Форма власності:",
        "tooltip_oblast": "Область:",
        "legend_total": "Кількість закладів",
        "layer_choropleth": "Заклади за громадами",
        "layer_points": "📍 Заклади (наближені точки в межах громади)",
        "all_mapped_note": "✅ Усі записи мають перевірений полігон громади.",
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
            "invalid_verified_geo_id": "Перевірений Geo ID відсутній у GeoJSON",
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
        "app_title": "Paediatric rehabilitation in Ukraine",
        "app_eyebrow": "REHAB MAPPING · VERIFIED DATA",
        "app_subtitle": "Explore the network of medical and social providers — from the oblast overview to an individual hromada.",
        "filter_header": "Map filters",
        "filter_hint": "Choose a territory first, then refine the provider type.",
        "lang_label": "Оберіть мову / Choose language",
        "oblast_label": "Territory",
        "oblast_all": "All Ukraine",
        "kyiv_city_label": "Kyiv — city",
        "hromada_select_label": "Select hromada",
        "hromada_select_placeholder": "— none selected —",
        "hromada_detail_header": "📋 Facilities in hromada",
        "hromada_detail_total": "Total facilities: **{n}**",
        "facility_medical_tag": "🏥 Medical",
        "facility_social_tag": "🤝 Social",
        "facility_both_tag": "Medical + social",
        "facility_unclassified_tag": "Type not classified",
        "no_facilities_matched": "No matched facilities in the database for this hromada.",
        "facility_name_fallback": "Unnamed",
        "oblast_stats_header": "Selected territory",
        "oblast_stats_hromadas": "Hromadas with facilities",
        "oblast_stats_total": "Total facilities",
        "oblast_stats_medical": "With an NHSU package",
        "oblast_stats_social": "With a social-service code / NSSU",
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
        "layer_oblast_boundaries": "Oblast boundaries",
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
        "tab_map": "Map",
        "tab_data": "Data and methodology",
        "view_mode_label": "View level",
        "view_mode_oblasts": "Oblasts",
        "view_mode_hromadas": "Hromadas",
        "view_mode_points": "Providers",
        "view_mode_oblasts_hint": "Oblast outlines and proportional markers show provider concentration.",
        "view_mode_hromadas_hint": "Hromadas use outlines; teal accents indicate records are present.",
        "view_mode_points_hint": "Points are approximated inside each hromada and are not address geocoding.",
        "quality_header": "Geographic matching coverage",
        "quality_source": "Source records",
        "quality_mapped": "Shown on map",
        "quality_unmatched": "Without a polygon",
        "quality_note": "All previously unmatched records were verified against KATOTTG; original source fields remain unchanged.",
        "kpi_total": "Facilities after filters",
        "kpi_medical": "With an NHSU package",
        "kpi_social": "With a social-service code / NSSU",
        "kpi_hromadas": "Hromadas after filters",
        "service_definition": "Medical = an NHSU package is present. Social = a social-service code or NSSU record is present. Categories may overlap.",
        "verification_badge": "100% of records have a verified polygon",
        "data_date": "KATOTTG · 07 Jul 2026",
        "tooltip_hromada": "Hromada:",
        "tooltip_total": "Total facilities:",
        "tooltip_medical": "Medical:",
        "tooltip_social": "Social:",
        "tooltip_ownership": "Ownership type:",
        "tooltip_oblast": "Oblast:",
        "legend_total": "Number of facilities",
        "layer_choropleth": "Facilities by hromada",
        "layer_points": "📍 Facilities (approximate points inside each hromada)",
        "all_mapped_note": "✅ Every record has a verified hromada polygon.",
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
            "invalid_verified_geo_id": "Verified Geo ID is missing from GeoJSON",
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
    # Соціальний надавач визначається прямою ознакою в джерелі, а не як
    # арифметичний залишок ``total - medical``. Це важливо для двох записів,
    # де присутні і пакет НСЗУ, і код соціальної послуги, та двох записів без
    # жодної з цих ознак.
    df["_is_social"] = df[COL_SOCIAL_CODE].apply(is_filled) | df[COL_NSSU].apply(is_filled)
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


@st.cache_data(show_spinner=False)
def load_oblast_geojson(path: str) -> dict:
    with open(path, encoding="utf-8") as file:
        oblast_geo = json.load(file)
    aliases = {"Автономна Республіка Крим": "Автономна республіка Крим"}
    for feature in oblast_geo["features"]:
        raw_name = feature["properties"].get("region", "")
        oblast_ua = aliases.get(raw_name, raw_name)
        feature["properties"]["oblast_ua"] = oblast_ua
        feature["properties"]["oblast_en"] = transliterate_ua_to_en(oblast_ua)
    return oblast_geo


def complete_oblast_boundaries(oblast_geo: dict, hromada_geo: dict) -> dict:
    """Узгоджує регіональний GeoJSON з переліком регіонів у громадському шарі.

    Джерельний ``regiony.geojson`` містить Севастополь, але не окремий Київ;
    ``hromady.geojson`` — навпаки. Тому зайву фічу відсікаємо, а межу Києва
    беремо з єдиної Київської міської громади в тому самому наборі громад.
    """
    expected = {feature["properties"]["oblast_ua"] for feature in hromada_geo["features"]}
    features = [
        feature
        for feature in oblast_geo["features"]
        if feature["properties"]["oblast_ua"] in expected
    ]
    present = {feature["properties"]["oblast_ua"] for feature in features}
    for feature in hromada_geo["features"]:
        oblast_ua = feature["properties"]["oblast_ua"]
        if oblast_ua in expected - present:
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "oblast_ua": oblast_ua,
                        "oblast_en": feature["properties"]["oblast_en"],
                    },
                    "geometry": feature["geometry"],
                }
            )
            present.add(oblast_ua)
    return {"type": "FeatureCollection", "features": features}


def resolve_facility_geography(df: pd.DataFrame, geo: dict) -> pd.DataFrame:
    """Однозначно зіставляє рядок Excel із конкретною фічею GeoJSON.

    Пошук завжди обмежується областю. Якщо в області є кілька однойменних
    громад, додатково використовуються район і тип громади. Неоднозначний
    випадок не вгадується: він лишається unmatched із відповідним статусом.
    """
    candidates_by_region_and_name: dict[tuple[str, str], list[dict]] = {}
    features_by_geo_id: dict[str, dict] = {}
    for feature in geo["features"]:
        props = feature["properties"]
        features_by_geo_id[props["geo_id"]] = feature
        candidates_by_region_and_name.setdefault((props["oblast_ua"], props["norm_key"]), []).append(feature)

    geo_ids: list[str | None] = []
    statuses: list[str] = []
    candidate_counts: list[int] = []

    for _, row in df.iterrows():
        # Перевірені вручну/за КАТОТТГ записи мають пряме посилання на полігон.
        # Воно використовується лише коли статус підтверджений, а Geo ID справді
        # існує у поточному GeoJSON; пошкоджене посилання не підміняється здогадом.
        verification_status = (
            str(row.get(COL_VERIFICATION_STATUS)).strip().lower()
            if is_filled(row.get(COL_VERIFICATION_STATUS))
            else ""
        )
        verified_geo_id = (
            str(row.get(COL_VERIFIED_GEO_ID)).strip()
            if is_filled(row.get(COL_VERIFIED_GEO_ID))
            else ""
        )
        if verification_status == "verified" and verified_geo_id:
            if verified_geo_id in features_by_geo_id:
                geo_ids.append(verified_geo_id)
                statuses.append("verified_katottg")
                candidate_counts.append(1)
            else:
                geo_ids.append(None)
                statuses.append("invalid_verified_geo_id")
                candidate_counts.append(0)
            continue

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
        if not column.startswith("_")
        and column not in technical_columns
        and column not in VERIFICATION_COLUMNS
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
        social = int(group["_is_social"].sum())
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
    matched = int(df["_geo_id"].notna().sum())

    print("=" * 60)
    print("[GEOGRAPHY MATCHING] Summary")
    print(f"  Source facility records: {total}")
    print(f"  Uniquely matched: {matched} ({matched / total:.1%})")
    print(f"  verified_katottg: {int(counts.get('verified_katottg', 0))}")
    for status in ("name_not_found", "ambiguous", "unknown_oblast", "invalid_verified_geo_id"):
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
                "social": int(group["_is_social"].sum()),
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
    m = folium.Map(location=UKRAINE_CENTER, zoom_start=6, tiles="OpenStreetMap")
    # Приглушена підкладка залишає географічний контекст, але не конкурує з
    # контурами областей і маркерами надавачів.
    m.get_root().html.add_child(
        folium.Element(
            "<style>.leaflet-tile-pane{filter:saturate(.42) contrast(.92) brightness(1.06)}"
            ".leaflet-container{font-family:Inter,Segoe UI,sans-serif;background:#e9ece8}"
            ".region-count{background:#f2b84b;border:1px solid #173f43;border-radius:999px;"
            "color:#102a2e;font-weight:800;font-size:11px;padding:2px 6px;box-shadow:none}</style>"
        )
    )
    return m


def display_oblast_name(oblast_ua: str, lang: str, ui: dict) -> str:
    if oblast_ua == "Київ":
        return ui["kyiv_city_label"]
    return oblast_ua if lang == "uk" else transliterate_ua_to_en(oblast_ua)


def oblast_stats(df: pd.DataFrame, geo: dict) -> list[dict]:
    """Агрегація та центр маркерів на рівні областей для активних фільтрів."""
    oblast_by_geo_id = {
        feature["properties"]["geo_id"]: feature["properties"]["oblast_ua"]
        for feature in geo["features"]
    }
    scoped = df[df["_geo_id"].notna()].copy()
    scoped["_oblast_ua"] = scoped["_geo_id"].map(oblast_by_geo_id)
    records = []
    for oblast, group in scoped.groupby("_oblast_ua"):
        records.append(
            {
                "oblast_ua": oblast,
                "total": len(group),
                "medical": int(group["_is_medical"].sum()),
                "social": int(group["_is_social"].sum()),
                "lat": float(group["lat"].mean()),
                "lon": float(group["lon"].mean()),
            }
        )
    return records


def add_oblast_boundaries(
    m: folium.Map,
    boundaries: dict,
    lang: str,
    ui: dict,
    visible_oblasts: set[str] | None = None,
) -> None:
    features = [
        feature
        for feature in boundaries["features"]
        if visible_oblasts is None or feature["properties"]["oblast_ua"] in visible_oblasts
    ]
    name_field = "oblast_ua" if lang == "uk" else "oblast_en"
    folium.GeoJson(
        {"type": "FeatureCollection", "features": features},
        style_function=lambda _: {
            "color": "#173f43",
            "weight": 2.4,
            "opacity": 0.9,
            "fillOpacity": 0,
        },
        highlight_function=lambda _: {
            "color": "#e38b52",
            "weight": 3.4,
            "opacity": 1,
            "fillOpacity": 0.035,
        },
        tooltip=folium.GeoJsonTooltip(fields=[name_field], aliases=[ui["tooltip_oblast"]], sticky=True),
        name=ui["layer_oblast_boundaries"],
        control=False,
    ).add_to(m)


def build_oblast_map(
    geo: dict,
    oblast_boundaries: dict,
    facility_df: pd.DataFrame,
    lang: str,
    ui: dict,
    selected_oblast: str | None = None,
) -> folium.Map:
    """Огляд областей: чисті контури + пропорційні маркери, без заливки."""
    m = new_base_map()
    visible = {selected_oblast} if selected_oblast is not None else None
    add_oblast_boundaries(m, oblast_boundaries, lang, ui, visible)

    for record in oblast_stats(facility_df, geo):
        if visible is not None and record["oblast_ua"] not in visible:
            continue
        label = display_oblast_name(record["oblast_ua"], lang, ui)
        popup = (
            f"<b>{html.escape(label)}</b><br>"
            f"{html.escape(ui['tooltip_total'])} {record['total']}<br>"
            f"{html.escape(ui['tooltip_medical'])} {record['medical']}<br>"
            f"{html.escape(ui['tooltip_social'])} {record['social']}"
        )
        radius = max(7, min(22, 5 + math.sqrt(record["total"]) * 0.65))
        marker = folium.CircleMarker(
            location=[record["lat"], record["lon"]],
            radius=radius,
            color="#173f43",
            weight=1.5,
            fill=True,
            fill_color="#f2b84b",
            fill_opacity=0.88,
            popup=folium.Popup(popup, max_width=260),
        ).add_to(m)
        marker.add_child(
            folium.Tooltip(str(record["total"]), permanent=True, direction="center", class_name="region-count")
        )

    if selected_oblast is None:
        fit_map_to_bounds(m, union_bounds(geo["features"]))
    else:
        selected_features = [
            feature for feature in geo["features"] if feature["properties"]["oblast_ua"] == selected_oblast
        ]
        fit_map_to_bounds(m, union_bounds(selected_features))
    return m


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
    geo: dict,
    agg: pd.DataFrame,
    lang: str,
    ui: dict,
    selected_geo_id: str | None = None,
    oblast_boundaries: dict | None = None,
) -> folium.Map:
    """Контурна карта громад без суцільної кольорової заливки."""
    m = new_base_map()
    name_field = "hromada_ua" if lang == "uk" else "hromada_en"
    stats_by_key = agg.set_index("geo_id").to_dict("index")
    view_features = []
    for feature in geo["features"]:
        props = dict(feature["properties"])
        stats = stats_by_key.get(props["geo_id"], {"total": 0, "medical": 0, "social": 0, "ownership_counts": {}})
        props["total"] = int(stats["total"])
        props["medical"] = int(stats["medical"])
        props["social"] = int(stats["social"])
        props["ownership_display"] = format_ownership_str(stats.get("ownership_counts", {}), lang)
        view_features.append({"type": "Feature", "properties": props, "geometry": feature["geometry"]})

    geo_layer = folium.GeoJson(
        {"type": "FeatureCollection", "features": view_features},
        style_function=lambda feature: {
            "fillColor": "#73b8ad" if feature["properties"]["total"] else "#ffffff",
            "fillOpacity": 0.09 if feature["properties"]["total"] else 0.015,
            "color": "#38867e" if feature["properties"]["total"] else "#aeb8b5",
            "weight": 1.05 if feature["properties"]["total"] else 0.55,
            "opacity": 0.9,
        },
        highlight_function=lambda feature: {
            "fillOpacity": 0.18 if feature["properties"]["total"] else 0.06,
            "color": "#e38b52",
            "weight": 2.4,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[name_field, "total", "medical", "social", "ownership_display"],
            aliases=[
                ui["tooltip_hromada"],
                ui["tooltip_total"],
                ui["tooltip_medical"],
                ui["tooltip_social"],
                ui["tooltip_ownership"],
            ],
            sticky=True,
        ),
        name=ui["layer_choropleth"],
        control=False,
    ).add_to(m)

    if oblast_boundaries is not None:
        visible_oblasts = {feature["properties"]["oblast_ua"] for feature in geo["features"]}
        add_oblast_boundaries(m, oblast_boundaries, lang, ui, visible_oblasts)

    _apply_focus_and_highlight(m, geo, selected_geo_id, lang, ui)
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
    oblast_boundaries: dict | None = None,
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

    if oblast_boundaries is not None:
        visible_oblasts = {feature["properties"]["oblast_ua"] for feature in geo_view["features"]}
        add_oblast_boundaries(m, oblast_boundaries, lang, ui, visible_oblasts)

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


DASHBOARD_CSS = """
<style>
:root {
  --ink: #102a2e;
  --muted: #60716f;
  --paper: #f4f1e9;
  --card: #fffdf8;
  --teal: #2a7f78;
  --amber: #f2b84b;
  --coral: #e38b52;
  --line: #d8ddd8;
}
[data-testid="stAppViewContainer"] { background: var(--paper); color: var(--ink); }
[data-testid="stHeader"] { background: rgba(244,241,233,.86); }
[data-testid="stSidebar"] { background: #e7ece8; border-right: 1px solid #ccd6d1; }
[data-testid="stSidebar"] > div { padding-top: 1.25rem; }
.block-container { max-width: 1500px; padding-top: 1.6rem; padding-bottom: 3rem; }
h1, h2, h3 { color: var(--ink); letter-spacing: -.025em; }
.hero-shell {
  position: relative; overflow: hidden; border-radius: 22px; padding: 34px 38px 30px;
  background: var(--ink); color: #fffdf8; margin-bottom: 16px;
  box-shadow: 0 16px 40px rgba(16,42,46,.12);
}
.hero-shell:after {
  content: ""; position: absolute; right: -80px; top: -120px; width: 330px; height: 330px;
  border-radius: 50%; border: 58px solid rgba(242,184,75,.17);
}
.hero-eyebrow { color: var(--amber); font-size: 12px; letter-spacing: .16em; font-weight: 800; }
.hero-title { max-width: 820px; font-size: clamp(34px,4vw,58px); line-height: .98; font-weight: 760; margin: 14px 0 16px; }
.hero-copy { max-width: 760px; color: #d8e2df; font-size: 17px; line-height: 1.55; }
.status-row { display:flex; gap:10px; flex-wrap:wrap; margin-top:22px; }
.status-chip { border:1px solid rgba(255,255,255,.18); border-radius:999px; padding:7px 11px; color:#edf4f2; font-size:12px; }
.status-chip strong { color: #fff; }
.filter-brand { font-size:12px; letter-spacing:.14em; font-weight:800; color:var(--teal); margin-bottom:2px; }
.filter-title { font-size:25px; line-height:1.1; font-weight:780; color:var(--ink); margin:3px 0 7px; }
.filter-hint { color:var(--muted); font-size:13px; line-height:1.45; margin-bottom:15px; }
.kpi-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:10px 0 14px; }
.kpi-card { background:var(--card); border:1px solid var(--line); border-radius:15px; padding:16px 17px; min-height:105px; }
.kpi-card:nth-child(1) { border-top:4px solid var(--ink); }
.kpi-card:nth-child(2) { border-top:4px solid var(--teal); }
.kpi-card:nth-child(3) { border-top:4px solid var(--coral); }
.kpi-card:nth-child(4) { border-top:4px solid var(--amber); }
.kpi-value { font-size:31px; line-height:1; font-weight:790; color:var(--ink); }
.kpi-label { margin-top:9px; color:var(--muted); font-size:12px; line-height:1.35; }
.method-note { color:var(--muted); font-size:12px; margin:0 0 13px; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:8px; }
[data-testid="stTabs"] [data-baseweb="tab"] { border-radius:999px; padding:9px 16px; background:#e6ebe7; }
[data-testid="stTabs"] [aria-selected="true"] { background:var(--ink); color:white; }
[data-testid="stIFrame"] { border-radius:18px; overflow:hidden; border:1px solid var(--line); }
[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; }
@media (max-width: 900px) {
  .hero-shell { padding:26px 22px; border-radius:16px; }
  .kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
</style>
"""


def render_hero(ui: dict, source_count: int, mapped_count: int) -> None:
    st.markdown(
        f"""
        <section class="hero-shell">
          <div class="hero-eyebrow">{html.escape(ui['app_eyebrow'])}</div>
          <div class="hero-title">{html.escape(ui['app_title'])}</div>
          <div class="hero-copy">{html.escape(ui['app_subtitle'])}</div>
          <div class="status-row">
            <span class="status-chip"><strong>{mapped_count:,}</strong> / {source_count:,} · {html.escape(ui['verification_badge'])}</span>
            <span class="status-chip">{html.escape(ui['data_date'])}</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(ui: dict, total: int, medical: int, social: int, hromadas: int) -> None:
    cards = [
        (total, ui["kpi_total"]),
        (medical, ui["kpi_medical"]),
        (social, ui["kpi_social"]),
        (hromadas, ui["kpi_hromadas"]),
    ]
    markup = "".join(
        f'<div class="kpi-card"><div class="kpi-value">{value:,}</div>'
        f'<div class="kpi-label">{html.escape(label)}</div></div>'
        for value, label in cards
    )
    st.markdown(f'<div class="kpi-grid">{markup}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="method-note">{html.escape(ui["service_definition"])}</div>', unsafe_allow_html=True)


def facility_service_tag(row: pd.Series, ui: dict) -> str:
    medical = bool(row["_is_medical"])
    social = bool(row["_is_social"])
    if medical and social:
        return ui["facility_both_tag"]
    if medical:
        nhsu_value = row[COL_NHSU]
        suffix = f" ({str(nhsu_value).strip()})" if is_filled(nhsu_value) else ""
        return f"{ui['facility_medical_tag']}{suffix}"
    if social:
        return ui["facility_social_tag"]
    return ui["facility_unclassified_tag"]


def main() -> None:
    st.set_page_config(
        page_title="Rehab Mapping Ukraine",
        page_icon="◉",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
    st.sidebar.markdown('<div class="filter-brand">SPARC · UKRAINE</div>', unsafe_allow_html=True)

    lang_choice = st.sidebar.radio(
        UI_TEXTS["uk"]["lang_label"],
        ["🇺🇦 Українська", "🇬🇧 English"],
        index=0,
        horizontal=True,
    )
    lang = "uk" if "Українська" in lang_choice else "en"
    ui = UI_TEXTS[lang]
    st.sidebar.markdown(
        f'<div class="filter-title">{html.escape(ui["filter_header"])}</div>'
        f'<div class="filter-hint">{html.escape(ui["filter_hint"])}</div>',
        unsafe_allow_html=True,
    )

    df, geo, agg, unmatched = prepare_data(str(EXCEL_PATH), str(GEOJSON_PATH))
    oblast_geo = complete_oblast_boundaries(load_oblast_geojson(str(OBLAST_GEOJSON_PATH)), geo)
    mapped_count = int(df["_geo_id"].notna().sum())
    render_hero(ui, len(df), mapped_count)

    oblasts_ua = sorted({f["properties"]["oblast_ua"] for f in geo["features"] if f["properties"]["oblast_ua"]})
    oblast_display = {
        ua: display_oblast_name(ua, lang, ui) for ua in oblasts_ua
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
                    tag = facility_service_tag(row, ui)
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
                display_oblast = (
                    provider.get(COL_VERIFIED_OBLAST)
                    if is_filled(provider.get(COL_VERIFIED_OBLAST))
                    else provider[COL_OBLAST]
                )
                display_raion = (
                    provider.get(COL_VERIFIED_RAION)
                    if is_filled(provider.get(COL_VERIFIED_RAION))
                    else provider[COL_RAION]
                )
                display_hromada = (
                    provider.get(COL_VERIFIED_HROMADA)
                    if is_filled(provider.get(COL_VERIFIED_HROMADA))
                    else provider[COL_HROMADA]
                )
                st.markdown(f"{ui['provider_card_oblast']}: {_field(display_oblast)}")
                st.markdown(f"{ui['provider_card_raion']}: {_field(display_raion)}")
                st.markdown(f"{ui['provider_card_hromada']}: {_field(display_hromada)}")
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
        render_kpis(
            ui,
            int(agg_view["total"].sum()) if not agg_view.empty else 0,
            int(agg_view["medical"].sum()) if not agg_view.empty else 0,
            int(agg_view["social"].sum()) if not agg_view.empty else 0,
            int((agg_view["total"] > 0).sum()) if not agg_view.empty else 0,
        )

        view_mode = st.radio(
            ui["view_mode_label"],
            options=["points", "oblasts", "hromadas"],
            format_func=lambda value: {
                "points": ui["view_mode_points"],
                "oblasts": ui["view_mode_oblasts"],
                "hromadas": ui["view_mode_hromadas"],
            }[value],
            horizontal=True,
        )
        st.caption(ui[f"view_mode_{view_mode}_hint"])
        show_boundaries = False
        if view_mode == "points":
            show_boundaries = st.checkbox(ui["show_boundaries_label"], value=False)

        if view_mode == "oblasts":
            m = build_oblast_map(
                geo,
                oblast_geo,
                df_filtered,
                lang,
                ui,
                None if selected_oblast is ALL_OBLASTS else selected_oblast,
            )
        elif view_mode == "hromadas":
            m = build_polygon_map(
                geo_view,
                agg_view,
                lang,
                ui,
                selected_geo_id,
                oblast_geo,
            )
        else:
            m = build_points_map(
                df_filtered,
                geo_view,
                lang,
                ui,
                selected_geo_id,
                show_boundaries,
                oblast_geo,
            )
        st_folium(m, width=None, height=680, returned_objects=[])

    with tab2:
        st.info(ui["quality_note"])
        st.caption(ui["service_definition"])
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
        if unmatched.empty:
            st.success(ui["all_mapped_note"])
        else:
            with st.expander(
                ui["unmatched_expander"].format(
                    groups=len(unmatched),
                    rows=int(unmatched["total"].sum()),
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
