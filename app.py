"""Мапа надавачів послуг педіатричної реабілітації в Україні."""

import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = BASE_DIR / "NEW_Mapping_tracker_2506.xlsx"
GEOJSON_PATH = BASE_DIR / "ukraine_hromadas.geojson"
SHEET_NAME = "Provider Data"

COL_HROMADA = "Hromada"
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


def format_ownership_str(counts: dict, lang: str) -> str:
    labels = UI_TEXTS[lang]["ownership_labels"]
    not_specified = UI_TEXTS[lang]["not_specified"]
    parts = []
    for key, count in counts.items():
        label = not_specified if key == UNSPECIFIED_KEY else labels.get(key, key.title())
        parts.append(f"{label}: {count}")
    return ", ".join(parts) if parts else not_specified


@st.cache_data(show_spinner=False)
def aggregate_providers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_is_medical"] = df[COL_NHSU].apply(is_filled)
    df["_ownership_key"] = df[COL_OWNERSHIP].apply(canonical_ownership_key)

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
def merge_stats_into_geojson(geo: dict, agg: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    agg_by_key = agg.set_index("norm_key")
    geo_keys = set()

    for feature in geo["features"]:
        props = feature["properties"]
        key = props["norm_key"]
        geo_keys.add(key)
        if key in agg_by_key.index:
            row = agg_by_key.loc[key]
            props["total"] = int(row["total"])
            props["medical"] = int(row["medical"])
            props["social"] = int(row["social"])
            props["ownership_counts"] = row["ownership_counts"]
        else:
            props["total"] = 0
            props["medical"] = 0
            props["social"] = 0
            props["ownership_counts"] = {}

    unmatched = agg[~agg["norm_key"].isin(geo_keys)].sort_values("total", ascending=False)
    return geo, unmatched


@st.cache_data(show_spinner="Обробка Excel і GeoJSON…")
def prepare_data(excel_path: str, geojson_path: str) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """Уся важка частина ETL за одним викликом, ключованим лише шляхами до файлів.

    Важливо тримати це одним cache_data-викликом: якщо замість цього main()
    ланцюжком викликає load_excel_data -> aggregate_providers ->
    merge_stats_into_geojson з df/geo як аргументами, Streamlit змушений на
    КОЖЕН st.rerun() (наприклад, перемикання мови) заново хешувати ці важкі
    об'єкти (DataFrame на 5590 рядків, GeoJSON на ~4 МБ), що коштує майже
    стільки ж, скільки сам розрахунок. Тут же кеш-ключ — два коротких рядки
    шляхів, тож на повторних rerun'ах ця функція не виконується взагалі.
    """
    df = load_excel_data(excel_path)
    geo = load_geojson(geojson_path)
    log_mapping_impact(df, geo)
    agg = aggregate_providers(df)
    geo, unmatched = merge_stats_into_geojson(geo, agg)
    return df, geo, agg, unmatched


def build_map(geo: dict, agg: pd.DataFrame, lang: str, ui: dict) -> folium.Map:
    m = folium.Map(location=[48.3794, 31.1656], zoom_start=6, tiles="cartodbpositron")

    name_field = "hromada_ua" if lang == "uk" else "hromada_en"
    for feature in geo["features"]:
        props = feature["properties"]
        props["ownership_display"] = format_ownership_str(props.get("ownership_counts", {}), lang)

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
    # Заглушка: в таблиці є лише Address, координат Lat/Lon поки немає.
    # Після геокодування адрес сюди додати FeatureGroup з CircleMarker/Marker.
    points_layer = folium.FeatureGroup(name=ui["layer_points"], show=False)
    points_layer.add_to(m)

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
    agg_view = agg[agg["norm_key"].isin(keys_in_view)]

    tab1, tab2 = st.tabs([ui["tab_map"], ui["tab_data"]])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(ui["kpi_total"], int(agg_view["total"].sum()))
        col2.metric(ui["kpi_medical"], int(agg_view["medical"].sum()))
        col3.metric(ui["kpi_social"], int(agg_view["social"].sum()))
        col4.metric(ui["kpi_hromadas"], int((agg_view["total"] > 0).sum()))

        m = build_map(geo_view, agg_view, lang, ui)
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
