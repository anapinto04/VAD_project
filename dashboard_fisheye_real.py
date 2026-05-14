import os
import json
import unicodedata
import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from shapely.geometry import shape, mapping
from shapely.ops import transform
import pyproj

# =====================================================
# CONFIG INICIAL
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Datasets_Limpos")
RAIO_AGRUPAMENTO_METROS = 500
RAIO_AGRUPAMENTO_DEG = RAIO_AGRUPAMENTO_METROS / 111000  # 500 m ≈ graus


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


# =====================================================
# 1. CARREGAMENTO DE DADOS
# =====================================================

def load_data():
    """Lê ficheiros Excel e guarda/usa um Parquet otimizado"""
    parquet_path = os.path.join(DATA_DIR, "acidentes_total.parquet")

    if os.path.exists(parquet_path):
        print(" A carregar dados do ficheiro Parquet...")
        return pd.read_parquet(parquet_path)

    dfs = []
    for year in range(2018, 2025):
        path = os.path.join(DATA_DIR, f"Tabela_acidentes_{year}_limpo.xlsx")
        if os.path.exists(path):
            try:
                df_local = pd.read_excel(path)
                df_local["Ano"] = year
                dfs.append(df_local)
            except Exception:
                continue

    df_combined = pd.concat(dfs, ignore_index=True)

    for col in df_combined.columns:
        try:
            if df_combined[col].dtype == "object":
                df_combined[col] = df_combined[col].astype(str)
        except Exception:
            pass

    df_combined.to_parquet(parquet_path, index=False)
    return df_combined


def load_geojson_portugal():
    possible_paths = [
        os.path.join(BASE_DIR, "ContinenteDistritos.geojson"),
        os.path.join(BASE_DIR, "data", "ContinenteDistritos.geojson")
    ]
    geojson_path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not geojson_path:
        return None

    with open(geojson_path, encoding="utf-8-sig") as f:
        geojson_data = json.load(f)

    transformer = pyproj.Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True).transform
    for feature in geojson_data.get("features", []):
        try:
            geom = shape(feature["geometry"])
            feature["geometry"] = mapping(transform(transformer, geom))
        except Exception:
            continue
    return geojson_data


# =====================================================
# 2. Cores e tipos de letra
# =====================================================

TEXT_DARK = "#000000"
TEXT_MID = "#000000"
TEXT_LIGHT = "#9CA3AF"
BG = "#F4F6F8"
CARD_BG = "#FFFFFF"
BORDER = "#E5E7EB"
PRIMARY = "#000000"
ACCENT = "#E74C3C"
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


def main_title_style():
    return text_style("main_title", PRIMARY, "bold", {"letterSpacing": "-0.5px", "margin": "0"})


def main_subtitle_style():
    return text_style("main_subtitle", TEXT_MID, "normal", {"margin": "4px 0 0 0"})


def section_title_style():
    return text_style("graph_title", PRIMARY, "semibold", {"letterSpacing": "-0.2px", "margin": "0 0 12px 0"})


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


def card_style(padding="16px"):
    return {
        "background": CARD_BG,
        "borderRadius": "12px",
        "padding": padding,
        "boxShadow": "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.12)",
        "border": f"1px solid {BORDER}",
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
        "zIndex": "999",
        "padding": "0",
        "transition": "transform 0.3s ease",
        "transform": "translateX(0)" if is_open else "translateX(-320px)",
        "fontFamily": FONT_FAMILY,
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
        "background": "#333333",
        "color": "white",
        "fontSize": "20px",
        "cursor": "pointer",
        "boxShadow": "0 2px 8px rgba(26,26,46,0.3)",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }


def menu_item_text_style(active=False):
    return {
        "color": "#FFFFFF" if active else "rgba(255,255,255,0.7)",
        "fontSize": get_font_size("menu_item"),
        "fontWeight": get_font_weight("medium"),
        "fontFamily": FONT_FAMILY,
    }


def menu_item_style(active=False):
    base = menu_item_text_style(active)
    return {
        **base,
        "display": "block",
        "padding": "14px 18px",
        "borderRadius": "8px",
        "marginBottom": "4px",
        "background": "rgba(255,255,255,0.1)" if active else "transparent",
        "border": "none",
        "textDecoration": "none",
        "transition": "all 0.2s ease",
        "borderLeft": f"3px solid {ACCENT}" if active else "3px solid transparent"
    }


# =====================================================
# 3. Carregar e preparar dados geográficos
# =====================================================

df_geo = load_data()
geojson_portugal = load_geojson_portugal()

lat_col = find_column(df_geo, ["Latitude GPS", "Latitude"])
lon_col = find_column(df_geo, ["Longitude GPS", "Longitude"])
natureza_col = find_column(df_geo, ["Natureza"])

if not df_geo.empty and lat_col and lon_col:
    df_geo[lat_col] = pd.to_numeric(df_geo[lat_col], errors="coerce")
    df_geo[lon_col] = pd.to_numeric(df_geo[lon_col], errors="coerce")
    df_geo = df_geo.dropna(subset=[lat_col, lon_col]).copy()
    df_geo["Natureza_Mapa"] = (
        df_geo[natureza_col].fillna("Sem informação").astype(str)
        if natureza_col else "Sem informação"
    )
    df_geo["grid_lat"] = (df_geo[lat_col] / RAIO_AGRUPAMENTO_DEG).round()
    df_geo["grid_lon"] = (df_geo[lon_col] / RAIO_AGRUPAMENTO_DEG).round()

    df_clusters = (
        df_geo.groupby(["grid_lat", "grid_lon"])
        .agg({
            lat_col: "mean",
            lon_col: "mean",
            "Natureza_Mapa": lambda x: x.value_counts().idxmax(),
        })
        .reset_index()
    )

    counts = df_geo.groupby(["grid_lat", "grid_lon"]).size().reset_index(name="Total_Acidentes")
    df_clusters = df_clusters.merge(counts, on=["grid_lat", "grid_lon"])

    # maiores clusters desenhados ficam por cima
    df_clusters = df_clusters.sort_values(by="Total_Acidentes", ascending=True).reset_index(drop=True)
else:
    df_clusters = pd.DataFrame(columns=[lat_col, lon_col, "Total_Acidentes"])


# =====================================================
# 4. App e layout
# =====================================================

app = Dash(__name__)
app.title = "Mapa de Clusters - Acidentes Rodoviários"

app.layout = html.Div([
    # Botão hamburguer
    html.Button(
        html.Div([
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "marginBottom": "5px"}),
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "marginBottom": "5px"}),
            html.Div(style={"width": "20px", "height": "2px", "background": "white"})
        ]),
        id="hamburger-btn",
        n_clicks=0,
        style=hamburger_style()
    ),

    # Sidebar
    html.Div(
        id="sidebar-menu",
        children=[
            html.Div([
                html.H2("Menu", style=text_style("20px", "#FFFFFF", "bold", {"textAlign": "center"})),
                html.Hr(style={"borderColor": "rgba(255,255,255,0.3)"}),
                html.A("Dashboard Principal", href="[127.0.0.1](http://127.0.0.1:8050)", style=menu_item_style(active=False)),
                html.A("Evolução Temporal", href="[127.0.0.1](http://127.0.0.1:8051)", style=menu_item_style(active=False)),
                html.A("Comparação entre anos", href="[127.0.0.1](http://127.0.0.1:8052)", style=menu_item_style(active=False)),
                html.A("Mapa Portugal", href="[127.0.0.1](http://127.0.0.1:8056)", style=menu_item_style(active=True)),
            ], style={"padding": "0 12px"})
        ],
        style=sidebar_style(False)
    ),

    # Contentor Principal
    html.Div([
        # Cabeçalho Centralizado
        html.Div([
            html.H1(id="main-title", style=main_title_style()),
        ], style={
            "width": "100%",
            "textAlign": "center",
            "marginBottom": "30px"
        }),

        # Grelha de Mapas
        html.Div([
            # Mapa Principal (sem loading spinner)
            html.Div([
                html.H3("Mapa de Clusters", style=section_title_style()),
                dcc.Graph(id="mapa-principal", style={"height": "70vh"}, config={"displaylogo": False}),
            ], style=card_style()),

            # Lupa (com loading spinner)
            html.Div([
                html.H3("Detalhe da Zona", style=section_title_style()),
                dcc.Loading(
                    type="circle",
                    delay_show=200,
                    delay_hide=200,
                    color=ACCENT,
                    children=[
                        dcc.Graph(id="mapa-lupa", style={"height": "55vh"}, config={"displaylogo": False}),
                    ]
                ),
                html.Div(id="info-detalhe", style={
                    "marginTop": "10px",
                    "padding": "10px",
                    "background": "#f0f4f9",
                    "borderRadius": "10px",
                    "textAlign": "center",
                    "fontFamily": FONT_FAMILY
                })
            ], style=card_style())
        ], style={
            "display": "grid",
            "gridTemplateColumns": "1.3fr 1fr",
            "gap": "24px",
            "marginTop": "20px"
        })
    ], style={"maxWidth": "1400px", "margin": "0 auto"})

], style={"backgroundColor": BG, "padding": "24px", "minHeight": "100vh", "fontFamily": FONT_FAMILY})


# =====================================================
# 5. Callbacks
# =====================================================

@app.callback(
    Output("sidebar-menu", "style"),
    Input("hamburger-btn", "n_clicks")
)
def toggle_sidebar(n_clicks):
    is_open = bool(n_clicks and n_clicks % 2 == 1)
    return sidebar_style(is_open)


@app.callback(
    Output("main-title", "children"),
    Output("mapa-principal", "figure"),
    Output("mapa-lupa", "figure"),
    Output("info-detalhe", "children"),
    Input("mapa-principal", "clickData"),
)
def update_viz(clickData):
    titulo_texto = "Clusters de Acidentes Rodoviários"

    # --- Mapa Principal ---
    fig_main = px.scatter_mapbox(
        df_clusters,
        lat=lat_col,
        lon=lon_col,
        color="Total_Acidentes",
        size="Total_Acidentes",
        size_max=28,
        color_continuous_scale=["#ffcdd2", "#e53935", "#b71c1c", "#1a0000"],
        zoom=6,
        center={"lat": 39.7, "lon": -8.1},
        mapbox_style="carto-positron",
        hover_data={"Total_Acidentes": True, lat_col: False, lon_col: False},
    )

    if geojson_portugal:
        fig_main.update_layout(mapbox_layers=[
            {"source": geojson_portugal, "type": "line", "color": "black", "line": {"width": 1.2}}
        ])

    fig_main.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, coloraxis_showscale=False)

    # --- LUPA ---
    if clickData:
        lat_c = clickData["points"][0]["lat"]
        lon_c = clickData["points"][0]["lon"]
        df_lupa = df_geo[
            (np.abs(df_geo[lat_col] - lat_c) < 0.015)  # raio de 1.5 km para mostrar detalhes próximos
            & (np.abs(df_geo[lon_col] - lon_c) < 0.015)
        ]
        fig_lupa = px.scatter_mapbox(
            df_lupa,
            lat=lat_col,
            lon=lon_col,
            color="Natureza_Mapa",
            zoom=13,
            center={"lat": lat_c, "lon": lon_c},
            mapbox_style="carto-positron",
        )
        fig_lupa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, legend=dict(font=dict(size=10)))
        total_acidentes = len(df_lupa)
        info = f"Total de acidentes nesta zona: {total_acidentes}"
    else:
        fig_lupa = px.scatter_mapbox(lat=[39.7], lon=[-8.1], zoom=5, mapbox_style="carto-positron")
        fig_lupa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        info = "Clique numa bolha no mapa principal para ver os detalhes dessa zona."

    return titulo_texto, fig_main, fig_lupa, info


# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == "__main__":
    app.run(debug=False, port=8056)