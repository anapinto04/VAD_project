import json
import os
import unicodedata

import pandas as pd
import pyproj
from dash import Dash, html, dcc, Input, Output, callback_context
import plotly.express as px
import plotly.graph_objects as go
from shapely.geometry import shape, mapping
from shapely.ops import transform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Datasets_Limpos")

# =========================
# 1. FUNÇÕES AUXILIARES
# =========================
def normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.upper().split())


def find_column(df, possible_names):
    normalized_map = {normalize_text(col): col for col in df.columns}
    for name in possible_names:
        key = normalize_text(name)
        if key in normalized_map:
            return normalized_map[key]
    return None


def parse_mes_num(series):
    month_map = {
        "1": 1, "01": 1, "JANEIRO": 1, "JAN": 1,
        "2": 2, "02": 2, "FEVEREIRO": 2, "FEV": 2,
        "3": 3, "03": 3, "MARCO": 3, "MAR": 3,
        "4": 4, "04": 4, "ABRIL": 4, "ABR": 4,
        "5": 5, "05": 5, "MAIO": 5, "MAI": 5,
        "6": 6, "06": 6, "JUNHO": 6, "JUN": 6,
        "7": 7, "07": 7, "JULHO": 7, "JUL": 7,
        "8": 8, "08": 8, "AGOSTO": 8, "AGO": 8,
        "9": 9, "09": 9, "SETEMBRO": 9, "SET": 9,
        "10": 10, "OUTUBRO": 10, "OUT": 10,
        "11": 11, "NOVEMBRO": 11, "NOV": 11,
        "12": 12, "DEZEMBRO": 12, "DEZ": 12,
    }

    cleaned = series.astype(str).str.strip().map(normalize_text)
    parsed_text = cleaned.map(month_map)
    parsed_numeric = pd.to_numeric(cleaned, errors="coerce")
    return parsed_text.fillna(parsed_numeric).astype("Int64")


MONTH_LABELS = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

MONTH_ORDER = list(MONTH_LABELS.values())


def monthly_count(dataframe, month_column):
    temp = dataframe.copy()
    temp["Mes_Num"] = parse_mes_num(temp[month_column])

    result = (
        temp.dropna(subset=["Mes_Num"])
        .groupby("Mes_Num")
        .size()
        .reindex(range(1, 13), fill_value=0)
        .reset_index(name="Acidentes")
    )

    result["Mês"] = result["Mes_Num"].map(MONTH_LABELS)
    result["Mês"] = pd.Categorical(result["Mês"], categories=MONTH_ORDER, ordered=True)
    return result


def monthly_sum(dataframe, month_column, value_column, output_column):
    temp = dataframe.copy()
    temp["Mes_Num"] = parse_mes_num(temp[month_column])

    result = (
        temp.dropna(subset=["Mes_Num"])
        .groupby("Mes_Num")[value_column]
        .sum()
        .reindex(range(1, 13), fill_value=0)
        .reset_index(name=output_column)
    )

    result["Mês"] = result["Mes_Num"].map(MONTH_LABELS)
    result["Mês"] = pd.Categorical(result["Mês"], categories=MONTH_ORDER, ordered=True)
    return result


def format_int_pt(value):
    return f"{int(value):,}".replace(",", " ")


# =========================
# 2. CARREGAR DADOS
# =========================
def load_data():
    parquet_path = os.path.join(DATA_DIR, "dataset2324.parquet")

    # Se já existir parquet → carregar imediatamente
    if os.path.exists(parquet_path):
        print("A carregar dados do ficheiro Parquet (otimizado)...")
        return pd.read_parquet(parquet_path)

    # Caso não exista parquet → ler Excel
    print("Parquet não encontrado, a ler ficheiros Excel...")
    possible_files = [
        os.path.join(DATA_DIR, f"Tabela_acidentes_{ano}_limpo.xlsx")
        for ano in range(2023, 2025)
    ]

    dfs = []
    for file in possible_files:
        if os.path.exists(file):
            try:
                df_local = pd.read_excel(file)

                digits = "".join(filter(str.isdigit, os.path.basename(file)))
                if len(digits) >= 4:
                    df_local["Ano"] = int(digits[:4])

                dfs.append(df_local)

            except Exception as e:
                print(f"Erro a ler {file}: {e}")
                continue

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # =======================================================
    # 1) Pré-calcular Mes_Num
    # =======================================================
    mes_col = find_column(df, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])
    if mes_col:
        df["Mes_Num"] = parse_mes_num(df[mes_col])
    else:
        df["Mes_Num"] = pd.NA

    # =======================================================
    # 2) Converter todas as colunas object misturadas → string
    #    (resolve TODOS os erros de Parquet)
    # =======================================================
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                df[col] = df[col].astype(str)
            except:
                df[col] = df[col].astype(str)

    # =======================================================
    # 3) Guardar parquet seguro
    # =======================================================
    try:
        df.to_parquet(parquet_path, index=False)
        print("Parquet criado com sucesso.")
    except Exception as e:
        print(f"Não foi possível guardar Parquet: {e}")

    return df


    # =======================================================
    # 1) PRÉ-CÁLCULO DE Mes_Num (acelera callbacks)
    # =======================================================
    mes_col = find_column(df, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])
    if mes_col:
        df["Mes_Num"] = parse_mes_num(df[mes_col])
    else:
        df["Mes_Num"] = pd.NA

    # =======================================================
    # 2) DETEÇÃO AUTOMÁTICA DE COLUNAS OBJECT MISTAS
    #    (resolver todos os erros "Expected bytes, got int")
    # =======================================================
    for col in df.columns:
        if df[col].dtype == "object":
            # Se tiver mistura (int + str + None), converter tudo para str
            try:
                # Tenta converter sem erro — se falhar, força string
                df[col].astype(str)
                df[col] = df[col].astype(str)
            except Exception:
                df[col] = df[col].astype(str)

    # =======================================================
    # 3) GRAVAR PARQUET SEM ERROS (PyArrow agora aceita tudo)
    # =======================================================
    df.to_parquet(parquet_file, index=False)

    return df





def load_geojson_portugal():
    possible_files = [
        os.path.join(BASE_DIR, "ContinenteDistritos.geojson"),
        os.path.join(BASE_DIR, "data", "ContinenteDistritos.geojson")
    ]

    geojson_path = None
    for path in possible_files:
        if os.path.exists(path):
            geojson_path = path
            break

    if geojson_path is None:
        return None

    with open(geojson_path, encoding="utf-8-sig") as f:
        geojson_data = json.load(f)

    transformer = pyproj.Transformer.from_crs(
        "EPSG:3763", "EPSG:4326", always_xy=True
    ).transform

    for feature in geojson_data.get("features", []):
        try:
            geom = shape(feature["geometry"])
            feature["geometry"] = mapping(transform(transformer, geom))
        except Exception:
            continue

        distrito = feature.get("properties", {}).get("Distrito", "")
        feature.setdefault("properties", {})["DistritoNorm"] = normalize_text(distrito)

    return geojson_data


df = load_data()
geojson_portugal = load_geojson_portugal()


# =========================
# 3. NORMALIZAÇÃO
# =========================
mes_col = find_column(df, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])
distrito_col = find_column(df, ["Distrito"])
natureza_col = find_column(df, ["Natureza"])
meteo_col = find_column(df, ["Factores Atmosféricos", "Fatores Atmosféricos", "Meteorologia"])
lat_col = find_column(df, ["Latitude GPS", "Latitude"])
lon_col = find_column(df, ["Longitude GPS", "Longitude"])

mortais_col = find_column(df, ["Vítimas mortais 30 dias", "Vitimas mortais 30 dias"])
graves_col = find_column(df, ["Feridos graves 30 dias"])
leves_col = find_column(df, ["Feridos leves 30 dias"])
tipo_via_col = find_column(df, ["Tipos Vias"])

ligeiros_col = find_column(df, ["# Veículos Ligeiros"])
pesados_col = find_column(df, ["# Veículos Pesados"])
motos_col = find_column(df, ["# Ciclomotores / Motociclos"])
outros_col = find_column(df, ["# Outros Veículos"])

if distrito_col:
    df[distrito_col] = df[distrito_col].astype(str)
    df["DistritoNorm"] = df[distrito_col].map(normalize_text)
else:
    df["DistritoNorm"] = None

for col in [
    mortais_col, graves_col, leves_col, lat_col, lon_col,
    ligeiros_col, pesados_col, motos_col, outros_col
]:
    if col:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Coluna de vítimas mortais
if mortais_col:
    df["Vitimas_Mortais"] = df[mortais_col].fillna(0)
else:
    df["Vitimas_Mortais"] = 0

# Coluna de acidentes com vítimas mortais (flag)
df["Acidente_Mortal"] = (df["Vitimas_Mortais"] > 0).astype(int)

# Coluna de feridos graves
if graves_col:
    df["Feridos_Graves"] = df[graves_col].fillna(0)
else:
    df["Feridos_Graves"] = 0

# Coluna de feridos leves
if leves_col:
    df["Feridos_Leves"] = df[leves_col].fillna(0)
else:
    df["Feridos_Leves"] = 0


# =========================
# 4. ESTILOS - CONFIGURAÇÃO CENTRALIZADA
# =========================

TEXT_DARK = "#000000"
TEXT_MID = "#000000"
TEXT_LIGHT = "#9CA3AF"

BG = "#F4F6F8"
CARD_BG = "#FFFFFF"
BORDER = "#E5E7EB"

PRIMARY = "#000000"
SECONDARY = "#000000"
ACCENT = "#78281F"
WARNING = "#F9A825"
INFO = "#1565C0"
NEUTRAL = "#BDC3C7"

RODOVIARIA_PRIMARY = "#2B506E"
RODOVIARIA_SECONDARY = "#455A64"

BAR_COLORS = [RODOVIARIA_SECONDARY]

CHOROPLETH_SCALE = [
    [0.0, "#FEACAC"],
    [0.2, "#FF8F82"],
    [0.4, "#FC6555"],
    [0.6, "#ED422F"],
    [0.8, "#A53428"],
    [1.0, "#7B241C"]
]


FONT_FAMILY = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

FONT_SIZES = {
    "xs": "11px",
    "sm": "12px",
    "base": "13px",
    "md": "14px",
    "lg": "15px",
    "xl": "16px",
    "2xl": "18px",
    "3xl": "22px",
    "4xl": "28px",
    "5xl": "32px",
    "kpi_value": "28px",
    "kpi_label": "20px",
    "kpi_subtitle": "14px",
    "kpi_prev": "16px",
    "section_title": "20px",
    "main_title": "32px",
    "main_subtitle": "24px",
    "graph_title": "20px",
    "axis": "14px",
    "menu_item": "14px",
    "menu_section": "11px",
    "button": "12px",
}

FONT_WEIGHTS = {
    "light": "300",
    "normal": "400",
    "medium": "500",
    "semibold": "600",
    "bold": "700",
}


def get_font_size(key):
    return FONT_SIZES.get(key, FONT_SIZES["base"])


def get_font_weight(key):
    return FONT_WEIGHTS.get(key, FONT_WEIGHTS["normal"])


def text_style(size_key="base", color=TEXT_DARK, weight_key="normal", extra=None):
    style = {
        "fontFamily": FONT_FAMILY,
        "fontSize": get_font_size(size_key),
        "color": color,
        "fontWeight": get_font_weight(weight_key),
    }
    if extra:
        style.update(extra)
    return style


def kpi_value_style(color=TEXT_DARK):
    return text_style("kpi_value", color, "bold", {"lineHeight": "1.1", "marginTop": "4px"})


def kpi_label_style():
    return text_style("kpi_label", TEXT_MID, "medium", {
        "textTransform": "uppercase",
        "letterSpacing": "0.5px"
    })


def kpi_subtitle_style():
    return text_style("kpi_subtitle", TEXT_MID, "normal", {"marginTop": "4px"})


def kpi_prev_style():
    return text_style("kpi_prev", TEXT_LIGHT, "normal")


def section_title_style():
    return text_style("graph_title", PRIMARY, "semibold", {"letterSpacing": "-0.2px", "margin": "0"})


def main_title_style():
    return text_style("main_title", PRIMARY, "bold", {"letterSpacing": "-0.5px", "margin": "0"})


def main_subtitle_style():
    return text_style("main_subtitle", TEXT_MID, "normal", {"margin": "4px 0 0 0"})


def button_style(bg_color="#F5F5F5", text_color=TEXT_DARK):
    return {
        "padding": "8px 16px",
        "border": "none",
        "borderRadius": "6px",
        "background": bg_color,
        "color": text_color,
        "cursor": "pointer",
        "fontSize": get_font_size("button"),
        "fontWeight": get_font_weight("medium"),
        "fontFamily": FONT_FAMILY,
        "transition": "all 0.2s ease"
    }


def toggle_button_style(active=False):
    if active:
        return {
            "padding": "10px 20px",
            "border": "none",
            "borderRadius": "8px",
            "background": ACCENT,
            "color": "white",
            "cursor": "pointer",
            "fontSize": get_font_size("md"),
            "fontWeight": get_font_weight("semibold"),
            "fontFamily": FONT_FAMILY,
            "transition": "all 0.2s ease",
            "boxShadow": "0 2px 8px rgba(231, 76, 60, 0.3)"
        }
    return {
        "padding": "10px 20px",
        "border": f"2px solid {BORDER}",
        "borderRadius": "8px",
        "background": "white",
        "color": TEXT_MID,
        "cursor": "pointer",
        "fontSize": get_font_size("md"),
        "fontWeight": get_font_weight("medium"),
        "fontFamily": FONT_FAMILY,
        "transition": "all 0.2s ease"
    }


def menu_item_text_style(active=False):
    return {
        "color": "#FFFFFF" if active else "rgba(255,255,255,0.7)",
        "fontSize": get_font_size("menu_item"),
        "fontWeight": get_font_weight("medium"),
        "fontFamily": FONT_FAMILY,
    }


def menu_section_text_style():
    return {
        "color": "rgba(255,255,255,0.4)",
        "fontSize": get_font_size("menu_section"),
        "fontWeight": get_font_weight("semibold"),
        "fontFamily": FONT_FAMILY,
        "letterSpacing": "1px",
        "margin": "20px 20px 12px 20px",
    }


def graph_title_font():
    return dict(
        size=int(get_font_size("graph_title").replace("px", "")),
        color=PRIMARY,
        family=f"{FONT_FAMILY}, bold",
    )


def axis_font():
    return dict(
        size=int(get_font_size("axis").replace("px", "")),
        color=TEXT_MID,
        family=FONT_FAMILY
    )


LINE_CHART_HEIGHT = 300
GAP = 16
MAP_HEIGHT = (2 * LINE_CHART_HEIGHT) + GAP + 75


def card_style(padding="16px"):
    return {
        "background": CARD_BG,
        "borderRadius": "12px",
        "padding": padding,
        "boxShadow": "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.12)",
        "border": f"1px solid {BORDER}",
    }


def kpi_card_style():
    return {
        "background": CARD_BG,
        "borderRadius": "12px",
        "padding": "20px 16px",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.12)",
        "border": f"1px solid {BORDER}",
        "minHeight": "130px",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "textAlign": "center",
        "gap": "6px",
        "position": "relative",
        "overflow": "hidden"
    }


def sidebar_style(is_open=False):
    return {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "width": "280px",
        "height": "100vh",
        "background": PRIMARY,
        "boxShadow": "4px 0 20px rgba(0,0,0,0.15)",
        "padding": "0",
        "zIndex": "999",
        "transition": "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "transform": "translateX(0)" if is_open else "translateX(-320px)",
        "fontFamily": FONT_FAMILY,
        "boxSizing": "border-box",
    }


def hamburger_style():
    return {
        "position": "fixed",
        "top": "16px",
        "left": "16px",
        "zIndex": "1001",
        "width": "48px",
        "height": "48px",
        "border": "none",
        "borderRadius": "12px",
        "background": PRIMARY,
        "color": "white",
        "fontSize": "20px",
        "fontWeight": "400",
        "cursor": "pointer",
        "boxShadow": "0 2px 8px rgba(26,26,46,0.3)",
        "lineHeight": "1",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "transition": "all 0.2s ease"
    }


def menu_item_style(active=False):
    base = menu_item_text_style(active)
    return {
        **base,
        "display": "block",
        "padding": "14px 20px",
        "borderRadius": "8px",
        "marginBottom": "4px",
        "background": "rgba(255,255,255,0.1)" if active else "transparent",
        "border": "none",
        "textDecoration": "none",
        "transition": "all 0.2s ease",
        "borderLeft": f"3px solid {ACCENT}" if active else "3px solid transparent"
    }


def apply_common_figure_style(fig, height=300):
    fig.update_layout(
        template="plotly_white",
        height=height,
        separators=" ",
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(
            x=0.02,
            xanchor="left",
            font=dict(
                family=FONT_FAMILY,
                size=int(get_font_size("graph_title").replace("px", "")),
                color=PRIMARY,
            )
        ),
        font=dict(family=FONT_FAMILY, size=12, color=TEXT_DARK),
        showlegend=False
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER,
        tickfont=axis_font(),
        title_font=axis_font(),
        tickformat=" ",
        gridcolor="#ECF0F1",
    )
    fig.update_yaxes(
        gridcolor="#ECF0F1",
        zeroline=False,
        linecolor=BORDER,
        tickfont=axis_font(),
        tickformat=" ",
        title_font=axis_font(),
    )
    return fig


def kpi_prev_label(prev_val):
    if prev_val is None:
        return html.Span("Ano anterior: N/A", style=kpi_prev_style())
    return html.Span(f"Ano anterior: {format_int_pt(prev_val)}", style=kpi_prev_style())


def kpi_pct_badge(current, previous, lower_is_better=True):
    if previous is None or previous == 0:
        return html.Span("Sem base", style=kpi_prev_style())

    pct = (current - previous) / previous * 100
    is_improvement = (pct < 0 and lower_is_better) or (pct > 0 and not lower_is_better)

    color = "#2E7D32" if is_improvement else ACCENT
    bg = "#E8F5E9" if is_improvement else "#FFEBEE"
    arrow = "▼" if pct < 0 else "▲"

    return html.Span(
        f"{arrow} {abs(pct):.1f}%",
        style={
            "fontSize": get_font_size("xs"),
            "color": color,
            "fontWeight": get_font_weight("semibold"),
            "fontFamily": FONT_FAMILY,
            "background": bg,
            "padding": "4px 10px",
            "borderRadius": "20px",
            "display": "inline-block"
        }
    )


def build_kpi_card_simple(label, value, accent_color, subtitle=None, prev_value=None, show_badge=True):
    children = [
        html.Div(label, style=kpi_label_style()),
        html.Div(format_int_pt(value), style=kpi_value_style()),
    ]

    if subtitle:
        children.append(html.Div(subtitle, style=kpi_subtitle_style()))

    if show_badge and prev_value is not None:
        children.append(
            html.Div(
                [kpi_pct_badge(value, prev_value, lower_is_better=True)],
                style={"marginTop": "8px" if not subtitle else "6px"}
            )
        )
        children.append(kpi_prev_label(prev_value))

    return html.Div(children, style=kpi_card_style())


# =========================
# 5. COORDENADAS
# =========================
coords_capitais = {
    "AVEIRO": {"lat": 40.6405, "lon": -8.6538},
    "BEJA": {"lat": 38.0151, "lon": -7.8632},
    "BRAGA": {"lat": 41.5503, "lon": -8.4201},
    "BRAGANCA": {"lat": 41.8058, "lon": -6.7572},
    "CASTELO BRANCO": {"lat": 39.8222, "lon": -7.4909},
    "COIMBRA": {"lat": 40.2033, "lon": -8.4103},
    "EVORA": {"lat": 38.5714, "lon": -7.9135},
    "FARO": {"lat": 37.0176, "lon": -7.9304},
    "GUARDA": {"lat": 40.5365, "lon": -7.2684},
    "LEIRIA": {"lat": 39.7436, "lon": -8.8071},
    "LISBOA": {"lat": 38.7223, "lon": -9.1393},
    "PORTALEGRE": {"lat": 39.2938, "lon": -7.4285},
    "PORTO": {"lat": 41.1579, "lon": -8.6291},
    "SANTAREM": {"lat": 39.2361, "lon": -8.6850},
    "SETUBAL": {"lat": 38.5244, "lon": -8.8931},
    "VIANA DO CASTELO": {"lat": 41.6932, "lon": -8.8329},
    "VILA REAL": {"lat": 41.3010, "lon": -7.7422},
    "VISEU": {"lat": 40.6566, "lon": -7.9125}
}


# =========================
# 6. MAPA (VÍTIMAS MORTAIS)
# =========================
def build_map_figure(dff, selected_district):
    if distrito_col is None:
        fig = go.Figure()
        fig.update_layout(title="Coluna Distrito não encontrada", height=MAP_HEIGHT)
        return fig

    if selected_district is None or geojson_portugal is None:
        # Agregar por vítimas mortais em vez de acidentes
        mapa_df = (
            dff.groupby(["DistritoNorm", distrito_col])["Vitimas_Mortais"]
            .sum()
            .reset_index(name="Vítimas Mortais")
        )

        if geojson_portugal is not None:
            fig = px.choropleth_mapbox(
                mapa_df,
                geojson=geojson_portugal,
                locations="DistritoNorm",
                featureidkey="properties.DistritoNorm",
                color="Vítimas Mortais",
                hover_name=distrito_col,
                hover_data={"DistritoNorm": False, "Vítimas Mortais": True},
                color_continuous_scale=CHOROPLETH_SCALE,
                center={"lat": 39.7, "lon": -8.1},
                zoom=5.5,
                opacity=0.85
            )

            fig.update_layout(
                mapbox_style="carto-positron",
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                paper_bgcolor="white",
                height=MAP_HEIGHT,
                coloraxis_colorbar=dict(
                    title=dict(text="Vítimas Mortais", font=dict(size=12, color=TEXT_MID)),
                    thickness=12,
                    len=0.8,
                    x=0.02,
                    y=0.5,
                    tickfont=dict(size=10, color=TEXT_MID)
                )
            )

            return fig

        fig = px.bar(mapa_df, x=distrito_col, y="Vítimas Mortais", title="Vítimas Mortais por Distrito")
        apply_common_figure_style(fig, MAP_HEIGHT)
        return fig

    if lat_col is None or lon_col is None:
        fig = go.Figure()
        fig.update_layout(title="Coordenadas não encontradas", height=MAP_HEIGHT)
        return fig

    # Filtrar apenas acidentes com vítimas mortais para o mapa de pontos
    df_filtrado = dff[
        (dff["DistritoNorm"] == selected_district) &
        (dff["Vitimas_Mortais"] > 0) &
        dff[lat_col].notna() &
        dff[lon_col].notna()
    ].copy()

    if df_filtrado.empty:
        fig = go.Figure()
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=MAP_HEIGHT)
        return fig

    # Classificar por número de vítimas mortais
    df_filtrado["num_vitimas"] = df_filtrado["Vitimas_Mortais"].astype(int).astype(str) + " vítima(s)"

    coord = coords_capitais.get(selected_district, {"lat": 39.5, "lon": -8.0})

    fig = px.scatter_mapbox(
        df_filtrado,
        lat=lat_col,
        lon=lon_col,
        color="Vitimas_Mortais",
        hover_name=natureza_col if natureza_col else None,
        hover_data={lat_col: False, lon_col: False, "Vitimas_Mortais": True},
        color_continuous_scale=CHOROPLETH_SCALE,
        zoom=9.0,
        center=coord,
        size="Vitimas_Mortais",
        size_max=20
    )

    fig.update_traces(marker=dict(opacity=0.85))

    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="white",
        height=MAP_HEIGHT,
        coloraxis_colorbar=dict(
            title=dict(text="Vítimas", font=dict(size=12, color=TEXT_DARK)),
            thickness=12,
            len=0.5,
            x=0.02,
            y=0.5,
            tickfont=dict(size=10, color=TEXT_MID)
        )
    )

    return fig


# =========================
# 7. APP
# =========================
app = Dash(__name__)
app.title = "Vítimas Mortais em Portugal"

app.layout = html.Div([
    dcc.Location(id="url", refresh=True),
    dcc.Store(id="selected-district", data=None),
    dcc.Store(id="selected-month", data=None),
    dcc.Store(id="dashboard-mode", data="mortais"),  # "mortais" ou "acidentes"

    html.Button(
        html.Div([
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "marginBottom": "5px", "borderRadius": "1px"}),
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "marginBottom": "5px", "borderRadius": "1px"}),
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "borderRadius": "1px"})
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"}),
        id="hamburger-btn",
        n_clicks=0,
        title="Abrir menu",
        style=hamburger_style()
    ),

    # =========================
    # SIDEBAR
    # =========================
    html.Div(
        id="sidebar-menu",
        children=[
            html.Div([
                html.Div([
                    html.Div(style={
                        "width": "40px",
                        "height": "40px",
                        "borderRadius": "10px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "marginRight": "12px"
                    }, children=[
                        html.Span("AR", style=text_style("md", "white", "bold"))
                    ]),
                    html.Div([
                        html.H2(
                            "Acidentes",
                            style=text_style("2xl", "#FFFFFF", "bold", {"margin": "0", "letterSpacing": "-0.3px"})
                        ),
                        html.P(
                            "Rodoviários Portugal",
                            style=text_style("sm", "rgba(255,255,255,0.6)", "normal", {"margin": "0"})
                        )
                    ])
                ], style={"display": "flex", "alignItems": "center"})
            ], style={
                "padding": "24px 20px",
                "borderBottom": "1px solid rgba(255,255,255,0.1)"
            }),

            html.Div([
                html.P("DASHBOARDS", style=menu_section_text_style()),

                html.Div([
                    html.A(
                        "Dashboard Principal",
                        href="(http://127.0.0.1:8053)",
                        style=menu_item_style(active=True)
                    ),

                    html.A(
                        "Evolução Temporal",
                        href="(http://127.0.0.1:8051)",
                        style=menu_item_style()
                    ),

                    html.A(
                        "Comparação entre anos",
                        href="(http://127.0.0.1:8052)",
                        style=menu_item_style()
                    ),
                ], style={"padding": "0 12px"})
            ]),

            html.Div([
                html.Div(
                    "Clique novamente no menu para fechar",
                    style=text_style("xs", "rgba(255,255,255,0.4)", "normal", {"lineHeight": "1.4", "textAlign": "center"})
                )
            ], style={
                "position": "absolute",
                "bottom": "0",
                "left": "0",
                "right": "0",
                "padding": "20px",
                "borderTop": "1px solid rgba(255,255,255,0.1)"
            })

        ],
        style=sidebar_style(False)
    ),

    # =========================
    # CONTEÚDO PRINCIPAL
    # =========================
    html.Div([

        # =========================
        # HEADER COM TOGGLE
        # =========================
        html.Div([
            html.Div([

                # 1. BLOCO ESQUERDA (Vazio, serve apenas para equilibrar o layout)
                html.Div(style={"width": "20%"}),

                # 2. TÍTULO (Ocupa o centro)
                html.Div([
                    html.H1(id="main-title", style=main_title_style()),
                    html.P("Análise de sinistralidade rodoviária", style=main_subtitle_style())
                ], style={
                    "width": "60%", 
                    "textAlign": "center"
                }),

                # 3. BOTÕES À DIREITA (Alinhados ao fim do bloco)
                html.Div([
                    html.Button(
                        "Acidentes",
                        id="btn-acidentes",
                        n_clicks=0,
                        style=toggle_button_style(active=False)
                    ),
                    html.Button(
                        "Vítimas Mortais",
                        id="btn-mortais",
                        n_clicks=0,
                        style=toggle_button_style(active=True)
                    ),
                ], style={
                    "width": "20%",
                    "display": "flex",
                    "justifyContent": "flex-end", # Encosta os botões à direita
                    "gap": "12px"
                })

            ], style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center", # Mudado para center
                "marginBottom": "24px",
                "paddingTop": "8px",
                "width": "100%"
            }),
        ]),
        # =========================
        # KPI CARDS
        # =========================
        html.Div([
            html.Div(id="kpi-vitimas"),
            html.Div(id="kpi-graves"),
            html.Div(id="kpi-distrito"),
            html.Div(id="kpi-natureza"),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
            "gap": f"{GAP}px",
            "marginBottom": "20px"
        }),

        # =========================
        # MAPA + LINHAS
        # =========================
        html.Div([

            html.Div([
                html.Div([
                    html.Div([
                        html.H3(id="mapa-titulo", style=section_title_style()),
                        html.Button(
                            "Limpar seleção",
                            id="btn-reset",
                            n_clicks=0,
                            style=button_style()
                        )
                    ], style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginBottom": "12px"
                    }),

                    dcc.Loading(
                        type="circle",
                        delay_show=200,
                        delay_hide=200,
                        color=ACCENT,
                        children=dcc.Graph(
                            id="mapa-distritos",
                            style={"height": f"{MAP_HEIGHT}px"},
                            config={"displaylogo": False}
                        )
                    )
                ], style=card_style("16px"))
            ], style={"width": "50%"}),

            html.Div([
                html.Div([
                    html.Div([
                        html.H3(id="line-acidentes-titulo", style=section_title_style()),
                        html.Button(
                            "Limpar mês",
                            id="btn-reset-month",
                            n_clicks=0,
                            style=button_style()
                        )
                    ], style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginBottom": "12px"
                    }),

                    dcc.Loading(
                        type="circle",
                        delay_show=200,
                        delay_hide=200,
                        color=ACCENT,
                        children=dcc.Graph(
                            id="line-acidentes",
                            style={"height": f"{LINE_CHART_HEIGHT}px"},
                            config={"displaylogo": False}
                        )
                    )
                ], style=card_style("16px")),

                html.Div([
                    html.Div([
                        html.H3(id="line-vitimas-titulo", style=section_title_style()),
                    ], style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginBottom": "12px"
                    }),

                    dcc.Loading(
                        type="circle",
                        delay_show=200,
                        delay_hide=200,
                        color=ACCENT,
                        children=dcc.Graph(
                            id="line-vitimas",
                            style={"height": f"{LINE_CHART_HEIGHT}px"},
                            config={"displaylogo": False}
                        )
                    )
                ], style=card_style("16px"))

            ], style={
                "width": "50%",
                "display": "flex",
                "flexDirection": "column",
                "justifyContent": "space-between",
                "gap": f"{GAP}px"
            })

        ], style={
            "display": "flex",
            "gap": f"{GAP}px",
            "alignItems": "stretch",
            "marginBottom": "20px",
            "width": "100%"
        }),

        # =========================
        # BOTTOM CHARTS
        # =========================
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Vítimas Mortais por Tipo de Veículo", style=section_title_style()),
                ], style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "12px"
                }),
                dcc.Loading(
                    type="circle",
                    color=ACCENT,
                    children=dcc.Graph(
                        id="bar-veiculos",
                        style={"height": f"{LINE_CHART_HEIGHT}px"},
                        config={"displaylogo": False}
                    )
                )
            ], style={**card_style("16px"), "width": "50%"}),

            html.Div([
                html.Div([
                    html.H3("Distribuição de Vítimas Mortais por Tipo de Via", id="treemap-titulo", style=section_title_style()),
                ], style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "12px"
                }),
                dcc.Loading(
                    type="circle",
                    color="ACCENT",
                    children=dcc.Graph(
                        id="treemap-meteorologia",
                        style={"height": f"{LINE_CHART_HEIGHT}px"},
                        config={"displaylogo": False}
                    )
                )
            ], style={**card_style("16px"), "width": "50%"})

        ], style={
            "display": "flex",
            "gap": f"{GAP}px",
            "alignItems": "stretch",
            "marginBottom": "20px"
        })

    ], style={
        "maxWidth": "1400px",
        "margin": "0 auto"
    })

], style={
    "padding": "20px 24px 32px 24px",
    "backgroundColor": BG,
    "fontFamily": FONT_FAMILY,
    "minHeight": "100vh"
})


# =========================
# 8. CALLBACK MENU
# =========================
@app.callback(
    Output("sidebar-menu", "style"),
    Input("hamburger-btn", "n_clicks")
)
def toggle_sidebar(n_clicks):
    is_open = bool(n_clicks and n_clicks % 2 == 1)
    return sidebar_style(is_open)


# =========================
# CALLBACK TOGGLE DASHBOARD MODE
# =========================
@app.callback(
    Output("dashboard-mode", "data"),
    Output("btn-acidentes", "style"),
    Output("btn-mortais", "style"),
    Input("btn-acidentes", "n_clicks"),
    Input("btn-mortais", "n_clicks"),
    prevent_initial_call=True
)
def toggle_dashboard_mode(n_acidentes, n_mortais):
    ctx = callback_context
    if not ctx.triggered:
        return "mortais", toggle_button_style(False), toggle_button_style(True)

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "btn-acidentes":
        return "acidentes", toggle_button_style(True), toggle_button_style(False)
    else:
        return "mortais", toggle_button_style(False), toggle_button_style(True)


# =========================
# 9. CALLBACK DISTRITO
# =========================
@app.callback(
    Output("selected-district", "data"),
    Input("mapa-distritos", "clickData"),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True
)
def manage_selected_district(click_data, reset_clicks):
    ctx = callback_context

    if not ctx.triggered:
        return None

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "btn-reset":
        return None

    if trigger == "mapa-distritos" and click_data is not None:
        point = click_data["points"][0]
        if "location" in point:
            return point["location"]

    return None


# =========================
# CALLBACK MES
# =========================
@app.callback(
    Output("selected-month", "data"),
    Input("line-acidentes", "clickData"),
    Input("line-vitimas", "clickData"),
    Input("btn-reset-month", "n_clicks"),
    prevent_initial_call=True
)
def update_selected_month(click_acidentes, click_vitimas, reset_clicks):
    ctx = callback_context

    if not ctx.triggered:
        return None

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "btn-reset-month":
        return None

    data = click_acidentes if trigger == "line-acidentes" else click_vitimas

    if data and "points" in data:
        x = data["points"][0]["x"]

        try:
            return int(x)
        except:
            pass

        x_norm = normalize_text(x)
        inv_map = {normalize_text(v): k for k, v in MONTH_LABELS.items()}
        return inv_map.get(x_norm)

    return None


# =========================
# 10. CALLBACK PRINCIPAL
# =========================
@app.callback(
    Output("main-title", "children"),
    Output("kpi-vitimas", "children"),
    Output("kpi-graves", "children"),
    Output("kpi-distrito", "children"),
    Output("kpi-natureza", "children"),
    Output("mapa-titulo", "children"),
    Output("line-acidentes-titulo", "children"),
    Output("line-vitimas-titulo", "children"),
    Output("mapa-distritos", "figure"),
    Output("line-acidentes", "figure"),
    Output("line-vitimas", "figure"),
    Output("bar-veiculos", "figure"),
    Output("treemap-meteorologia", "figure"),
    Input("selected-district", "data"),
    Input("selected-month", "data"),
    Input("dashboard-mode", "data")
)
def update_dashboard(selected_district, selected_month, dashboard_mode):

    base_df = df

    # Modo do dashboard
    is_mortais = dashboard_mode == "mortais"

    # =========================
    # 1. ANO ATUAL
    # =========================
    selected_year = None
    if "Ano" in base_df.columns:
        anos = pd.to_numeric(base_df["Ano"], errors="coerce").dropna().astype(int)
        if not anos.empty:
            selected_year = int(anos.max())

    # =========================
    # 2. DATASETS POR NÍVEL
    # =========================

    # Filtra ano atual
    if selected_year is not None:
        df_year = base_df[base_df["Ano"] == selected_year]
    else:
        df_year = base_df  # fallback

    # Filtra ano anterior
    if selected_year is not None:
        df_prev_year = base_df[base_df["Ano"] == selected_year - 1]
    else:
        df_prev_year = base_df.iloc[0:0]  # dataframe vazio


    # =========================
    # 3. DATASET PARA KPIs (COM MÊS + DISTRITO)
    # =========================
    kpi_df = df_year.copy()
    kpi_prev_df = df_prev_year.copy()

    if selected_month and mes_col:
        kpi_df["Mes_Num"] = parse_mes_num(kpi_df[mes_col])
        kpi_prev_df["Mes_Num"] = parse_mes_num(kpi_prev_df[mes_col])

        kpi_df = kpi_df[kpi_df["Mes_Num"] == selected_month]
        kpi_prev_df = kpi_prev_df[kpi_prev_df["Mes_Num"] == selected_month]

    if selected_district and distrito_col:
        kpi_df = kpi_df[kpi_df["DistritoNorm"] == selected_district]
        kpi_prev_df = kpi_prev_df[kpi_prev_df["DistritoNorm"] == selected_district]

    # =========================
    # 4. DATASET PARA LINHAS (SÓ ANO + DISTRITO SEM MÊS)
    # =========================
    line_df = df_year

    if selected_district and distrito_col:
        line_df = line_df[line_df["DistritoNorm"] == selected_district]

    # =========================
    # 5. KPIs - MODO VÍTIMAS MORTAIS
    # =========================
    if is_mortais:
        # KPI 1: Total de vítimas mortais
        total_mortais = int(kpi_df["Vitimas_Mortais"].sum())
        prev_mortais = int(kpi_prev_df["Vitimas_Mortais"].sum()) if not kpi_prev_df.empty else None

        # KPI 2: Acidentes com vítimas mortais
        total_acidentes_mortais = int(kpi_df["Acidente_Mortal"].sum())
        prev_acidentes_mortais = int(kpi_prev_df["Acidente_Mortal"].sum()) if not kpi_prev_df.empty else None

        # KPI 3: Distrito com mais vítimas mortais
        distrito_critico = "N/A"
        distrito_count = 0

        if selected_district:
            distrito_critico = selected_district.title()
            distrito_count = total_mortais
        elif distrito_col and distrito_col in kpi_df.columns:
            distrito_mortais = kpi_df.groupby(distrito_col)["Vitimas_Mortais"].sum()
            if not distrito_mortais.empty:
                distrito_critico = distrito_mortais.idxmax()
                distrito_count = int(distrito_mortais.max())

        prev_distrito_count = None
        if not kpi_prev_df.empty and distrito_col:
            if selected_district:
                prev_distrito_count = int(kpi_prev_df["Vitimas_Mortais"].sum())
            else:
                distrito_prev_mortais = kpi_prev_df.groupby(distrito_col)["Vitimas_Mortais"].sum()
                if distrito_critico in distrito_prev_mortais.index:
                    prev_distrito_count = int(distrito_prev_mortais[distrito_critico])

        # KPI 4: Natureza mais frequente em acidentes mortais
        natureza_top = "N/A"
        natureza_count = 0

        df_mortais_only = kpi_df[kpi_df["Vitimas_Mortais"] > 0]
        if natureza_col and natureza_col in df_mortais_only.columns:
            counts = df_mortais_only[natureza_col].astype(str).value_counts()
            if not counts.empty:
                natureza_top = counts.idxmax()
                natureza_count = int(counts.iloc[0])

        prev_natureza_count = None
        if not kpi_prev_df.empty and natureza_col:
            df_prev_mortais_only = kpi_prev_df[kpi_prev_df["Vitimas_Mortais"] > 0]
            if natureza_col in df_prev_mortais_only.columns and natureza_top != "N/A":
                prev_natureza_count = int(
                    (df_prev_mortais_only[natureza_col].astype(str) == natureza_top).sum()
                )

        # KPIs UI
        kpi1 = build_kpi_card_simple(
            label="Vítimas Mortais",
            value=total_mortais,
            accent_color=ACCENT,
            prev_value=prev_mortais
        )

        kpi2 = build_kpi_card_simple(
            label="Acidentes Mortais",
            value=total_acidentes_mortais,
            accent_color=ACCENT,
            prev_value=prev_acidentes_mortais
        )

        if selected_district:
            kpi3 = html.Div([
                html.Div("Distrito Selecionado", style=kpi_label_style()),
                html.Div(str(distrito_critico), style=text_style("3xl", TEXT_DARK, "bold", {"lineHeight": "1.1", "marginTop": "4px"})),
                html.Div(f"{format_int_pt(distrito_count)} vítimas mortais", style=kpi_subtitle_style()),
                html.Div([kpi_pct_badge(distrito_count, prev_distrito_count, lower_is_better=True)], style={"marginTop": "6px"}),
                kpi_prev_label(prev_distrito_count)
            ], style=kpi_card_style())
        else:
            kpi3 = html.Div([
                html.Div("Distrito Mais Afetado", style=kpi_label_style()),
                html.Div(str(distrito_critico), style=text_style("3xl", TEXT_DARK, "bold", {"lineHeight": "1.1", "marginTop": "4px"})),
                html.Div(f"{format_int_pt(distrito_count)} vítimas mortais", style=kpi_subtitle_style()),
            ], style=kpi_card_style())

        kpi4 = html.Div([
            html.Div("Natureza Mais Letal", style=kpi_label_style()),
            html.Div(str(natureza_top), style=text_style("3xl", TEXT_DARK, "bold", {"lineHeight": "1.1", "marginTop": "4px"})),
            html.Div([kpi_pct_badge(natureza_count, prev_natureza_count, lower_is_better=True)], style={"marginTop": "6px"}),
            kpi_prev_label(prev_natureza_count)
        ], style=kpi_card_style())

        # Títulos
        titulo = (
            f"Vítimas Mortais - {MONTH_LABELS.get(selected_month)}"
            if selected_month
            else "Vítimas Mortais em Portugal"
        )

        mapa_titulo = (
            f"Distribuição de Vítimas Mortais - {selected_district.title()}"
            if selected_district
            else "Distribuição de Vítimas Mortais por Distrito"
        )

        line_ac_titulo = "Evolução Mensal de Vítimas Mortais"
        line_vit_titulo = "Evolução Mensal de Feridos Graves"

    else:
        # =========================
        # MODO ACIDENTES (ORIGINAL)
        # =========================
        total_vitimas = int(kpi_df["Vitimas_Mortais"].sum() + kpi_df["Feridos_Graves"].sum() + kpi_df["Feridos_Leves"].sum())
        total_graves = int(kpi_df["Acidente_Mortal"].sum())

        prev_vitimas = None
        prev_graves = None
        if not kpi_prev_df.empty:
            prev_vitimas = int(kpi_prev_df["Vitimas_Mortais"].sum() + kpi_prev_df["Feridos_Graves"].sum() + kpi_prev_df["Feridos_Leves"].sum())
            prev_graves = int(kpi_prev_df["Acidente_Mortal"].sum())

        distrito_critico = "N/A"
        distrito_count = len(kpi_df)

        if selected_district:
            distrito_critico = selected_district.title()
        elif distrito_col and distrito_col in kpi_df.columns:
            counts = kpi_df[distrito_col].value_counts()
            if not counts.empty:
                distrito_critico = counts.idxmax()
                distrito_count = int(counts.iloc[0])

        prev_distrito_count = len(kpi_prev_df) if not kpi_prev_df.empty else None

        natureza_top = "N/A"
        natureza_count = 0

        if natureza_col and natureza_col in kpi_df.columns:
            counts = kpi_df[natureza_col].astype(str).value_counts()
            if not counts.empty:
                natureza_top = counts.idxmax()
                natureza_count = int(counts.iloc[0])

        prev_natureza_count = None
        if not kpi_prev_df.empty and natureza_col:
            if natureza_col in kpi_prev_df.columns and natureza_top != "N/A":
                prev_natureza_count = int(
                    (kpi_prev_df[natureza_col].astype(str) == natureza_top).sum()
                )

        kpi1 = build_kpi_card_simple(
            label="Vítimas Totais",
            value=total_vitimas,
            accent_color=ACCENT,
            prev_value=prev_vitimas
        )

        kpi2 = build_kpi_card_simple(
            label="Acidentes Graves",
            value=total_graves,
            accent_color=ACCENT,
            prev_value=prev_graves
        )

        if selected_district:
            kpi3 = html.Div([
                html.Div("Distrito Selecionado", style=kpi_label_style()),
                html.Div(str(distrito_critico), style=text_style("3xl", TEXT_DARK, "bold", {"lineHeight": "1.1", "marginTop": "4px"})),
                html.Div(f"{format_int_pt(distrito_count)} acidentes", style=kpi_subtitle_style()),
                html.Div([kpi_pct_badge(distrito_count, prev_distrito_count, lower_is_better=True)], style={"marginTop": "6px"}),
                kpi_prev_label(prev_distrito_count)
            ], style=kpi_card_style())
        else:
            kpi3 = html.Div([
                html.Div("Distrito Crítico", style=kpi_label_style()),
                html.Div(str(distrito_critico), style=text_style("3xl", TEXT_DARK, "bold", {"lineHeight": "1.1", "marginTop": "4px"}))
            ], style=kpi_card_style())

        kpi4 = html.Div([
            html.Div("Natureza Mais Frequente", style=kpi_label_style()),
            html.Div(str(natureza_top), style=text_style("3xl", TEXT_DARK, "bold", {"lineHeight": "1.1", "marginTop": "4px"})),
            html.Div([kpi_pct_badge(natureza_count, prev_natureza_count, lower_is_better=True)], style={"marginTop": "6px"}),
            kpi_prev_label(prev_natureza_count)
        ], style=kpi_card_style())

        titulo = (
            f"Acidentes Rodoviários - {MONTH_LABELS.get(selected_month)}"
            if selected_month
            else "Acidentes Rodoviários em Portugal"
        )

        mapa_titulo = (
            f"Distribuição de Acidentes - {selected_district.title()}"
            if selected_district
            else "Distribuição de Acidentes por Distrito"
        )

        line_ac_titulo = "Evolução Mensal do Número de Acidentes"
        line_vit_titulo = "Evolução Mensal do Número de Vítimas"

    # =========================
    # MAPA
    # =========================
    fig_mapa = build_map_figure(kpi_df, selected_district)

    # =========================
    # GRÁFICOS DE LINHA
    # =========================
    if mes_col and mes_col in line_df.columns:
        if is_mortais:
            # Linha 1: Vítimas mortais por mês
            mortais_mes = monthly_sum(line_df, mes_col, "Vitimas_Mortais", "Vitimas_Mortais")

            fig_line_ac = go.Figure()
            fig_line_ac.add_trace(go.Scatter(
                x=mortais_mes["Mês"],
                y=mortais_mes["Vitimas_Mortais"],
                mode="lines+markers",
                name="Vítimas Mortais",
                line=dict(color=ACCENT, width=2.5),
                marker=dict(size=8, color=ACCENT, line=dict(width=2, color="white")),
                fill="tozeroy",
                fillcolor="rgba(231, 76, 60, 0.1)"
            ))

            # Linha 2: Feridos graves por mês
            graves_mes = monthly_sum(line_df, mes_col, "Feridos_Graves", "Feridos_Graves")

            fig_line_vit = go.Figure()
            fig_line_vit.add_trace(go.Scatter(
                x=graves_mes["Mês"],
                y=graves_mes["Feridos_Graves"],
                mode="lines+markers",
                name="Feridos Graves",
                line=dict(color=ACCENT, width=2.5),
                marker=dict(size=8, color=ACCENT, line=dict(width=2, color="white")),
                fill="tozeroy",
                fillcolor="rgba(231, 76, 60, 0.1)"
            ))
        else:
            # Modo acidentes original
            acidentes_mes = monthly_count(line_df, mes_col)

            fig_line_ac = go.Figure()
            fig_line_ac.add_trace(go.Scatter(
                x=acidentes_mes["Mês"],
                y=acidentes_mes["Acidentes"],
                mode="lines+markers",
                name="Acidentes",
                line=dict(color=RODOVIARIA_PRIMARY, width=2.5),
                marker=dict(size=8, color=RODOVIARIA_SECONDARY, line=dict(width=2, color="white")),
                fill="tozeroy",
                fillcolor="rgba(69, 90, 100, 0.1)"
            ))

            vitimas_totais = line_df["Vitimas_Mortais"] + line_df["Feridos_Graves"] + line_df["Feridos_Leves"]
            line_df_temp = line_df.copy()
            line_df_temp["Vitimas_Totais"] = vitimas_totais
            vitimas_mes = monthly_sum(line_df_temp, mes_col, "Vitimas_Totais", "Vitimas_Totais")

            fig_line_vit = go.Figure()
            fig_line_vit.add_trace(go.Scatter(
                x=vitimas_mes["Mês"],
                y=vitimas_mes["Vitimas_Totais"],
                mode="lines+markers",
                name="Vítimas",
                line=dict(color=RODOVIARIA_PRIMARY, width=2.5),
                marker=dict(size=8, color=RODOVIARIA_SECONDARY, line=dict(width=2, color="white")),
                fill="tozeroy",
                fillcolor="rgba(69, 90, 100, 0.1)"
            ))

        fig_line_ac.update_layout(title="")
        fig_line_vit.update_layout(title="")

        # Linha vertical para mês selecionado
        if selected_month:
            selected_month_label = MONTH_LABELS.get(int(selected_month)) if selected_month else None
            if selected_month_label:
                fig_line_ac.add_vline(
                    x=selected_month_label,
                    line_width=2,
                    line_dash="dash",
                    line_color="rgba(17, 24, 39, 0.4)"
                )
                fig_line_vit.add_vline(
                    x=selected_month_label,
                    line_width=2,
                    line_dash="dash",
                    line_color="rgba(17, 24, 39, 0.4)"
                )
    else:
        fig_line_ac = go.Figure()
        fig_line_vit = go.Figure()

    apply_common_figure_style(fig_line_ac, height=LINE_CHART_HEIGHT)
    apply_common_figure_style(fig_line_vit, height=LINE_CHART_HEIGHT)

    # =========================
    # GRÁFICO DE BARRAS - VEÍCULOS
    # =========================
    if is_mortais:
        # Filtrar apenas acidentes com vítimas mortais
        df_mortais_veiculos = kpi_df[kpi_df["Vitimas_Mortais"] > 0]

        veiculos = []
        valores = []

        if ligeiros_col and ligeiros_col in df_mortais_veiculos.columns:
            veiculos.append("Ligeiros")
            valores.append(df_mortais_veiculos[ligeiros_col].fillna(0).sum())

        if pesados_col and pesados_col in df_mortais_veiculos.columns:
            veiculos.append("Pesados")
            valores.append(df_mortais_veiculos[pesados_col].fillna(0).sum())

        if motos_col and motos_col in df_mortais_veiculos.columns:
            veiculos.append("Motociclos")
            valores.append(df_mortais_veiculos[motos_col].fillna(0).sum())

        if outros_col and outros_col in df_mortais_veiculos.columns:
            veiculos.append("Outros")
            valores.append(df_mortais_veiculos[outros_col].fillna(0).sum())
    else:
        veiculos = []
        valores = []

        if ligeiros_col and ligeiros_col in kpi_df.columns:
            veiculos.append("Ligeiros")
            valores.append(kpi_df[ligeiros_col].fillna(0).sum())

        if pesados_col and pesados_col in kpi_df.columns:
            veiculos.append("Pesados")
            valores.append(kpi_df[pesados_col].fillna(0).sum())

        if motos_col and motos_col in kpi_df.columns:
            veiculos.append("Motociclos")
            valores.append(kpi_df[motos_col].fillna(0).sum())

        if outros_col and outros_col in kpi_df.columns:
            veiculos.append("Outros")
            valores.append(kpi_df[outros_col].fillna(0).sum())

    if veiculos:
        df_veiculos = pd.DataFrame({"Tipo de Veículo": veiculos, "Quantidade": valores})

        fig_bar = px.bar(
            df_veiculos,
            x="Tipo de Veículo",
            y="Quantidade",
            color="Tipo de Veículo",
            text=df_veiculos["Quantidade"].apply(format_int_pt),
            color_discrete_sequence=[ACCENT if is_mortais else RODOVIARIA_SECONDARY]
        )

        fig_bar.update_traces(
            textposition="outside",
            textfont=dict(size=11, color=TEXT_DARK)
        )
        fig_bar.update_yaxes(range=[0, df_veiculos["Quantidade"].max() * 1.15])

        apply_common_figure_style(fig_bar, height=260)
    else:
        fig_bar = go.Figure()

    # =========================
    # TREEMAP - TIPOS DE VIA
    # =========================
    if tipo_via_col and tipo_via_col in kpi_df.columns:
        if is_mortais:
            # Agregar vítimas mortais por tipo de via
            tipo_via_df = kpi_df.groupby(tipo_via_col)["Vitimas_Mortais"].sum().reset_index()
            tipo_via_df.columns = ["Tipos de vias", "Total"]
            tipo_via_df = tipo_via_df[tipo_via_df["Total"] > 0]
        else:
            tipo_via_df = kpi_df[tipo_via_col].astype(str).value_counts().reset_index()
            tipo_via_df.columns = ["Tipos de vias", "Total"]

        if not tipo_via_df.empty:
            fig_treemap = px.treemap(
                tipo_via_df,
                path=["Tipos de vias"],
                values="Total",
                title="",
                color="Total",
                color_continuous_scale=CHOROPLETH_SCALE
            )

            apply_common_figure_style(fig_treemap, height=260)

            fig_treemap.update_layout(
                margin=dict(t=40, l=0, r=0, b=0),
                paper_bgcolor="white",
                plot_bgcolor="white",
                coloraxis_showscale=False
            )

            fig_treemap.update_traces(
                root_color="white",
                marker=dict(pad=dict(b=0, l=0, r=0, t=0)),
                textfont=dict(size=12, color="white"),
                hovertemplate="<b>%{label}</b><br>Total: %{value}<extra></extra>"
            )
        else:
            fig_treemap = go.Figure()
    else:
        fig_treemap = go.Figure()

    return (
        titulo,
        kpi1,
        kpi2,
        kpi3,
        kpi4,
        mapa_titulo,
        line_ac_titulo,
        line_vit_titulo,
        fig_mapa,
        fig_line_ac,
        fig_line_vit,
        fig_bar,
        fig_treemap
    )

@app.callback(
    Output("url", "href"),
    Input("btn-acidentes", "n_clicks"),
    prevent_initial_call=True
)
def abrir_dashboard_acidentes(n_clicks):
    return "http://127.0.0.1:8050"
# =========================
# 11. RUNs
# =========================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=8053)
