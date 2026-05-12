
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
    return f"{int(value):,}".replace(",", ".")


# =========================
# 2. CARREGAR DADOS
# =========================
def load_data():
    preferred_files = [
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2023_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2024_limpo.xlsx"),
    ]

    files = [path for path in preferred_files if os.path.exists(path)]

    dfs = []
    for file in files:
        try:
            df_local = pd.read_excel(file)
        except Exception:
            continue

        filename = os.path.basename(file)
        digits = "".join(filter(str.isdigit, filename))
        if len(digits) >= 4:
            df_local["Ano"] = int(digits[:4])

        dfs.append(df_local)

    if not dfs:
        print("Aviso: não foi possível carregar os ficheiros de acidentes.")
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


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

ligeiros_col = find_column(df, [
    "# Veículos Ligeiros"
])

pesados_col = find_column(df, [
    "# Veículos Pesados"
])

motos_col = find_column(df, [
    "# Ciclomotores / Motociclos",
])

outros_col = find_column(df, [
    "# Outros Veículos",
])

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

if mortais_col and graves_col and leves_col:
    df["Vitimas_Totais"] = (
        df[mortais_col].fillna(0) +
        df[graves_col].fillna(0) +
        df[leves_col].fillna(0)
    )
else:
    df["Vitimas_Totais"] = 0

if mortais_col or graves_col:
    mortais_series = df[mortais_col].fillna(0) if mortais_col else 0
    graves_series = df[graves_col].fillna(0) if graves_col else 0
    df["Acidente_Grave"] = ((mortais_series > 0) | (graves_series > 0)).astype(int)
else:
    df["Acidente_Grave"] = 0


# =========================
# 4. ESTILOS
# =========================
PRIMARY = "#153B6D"
TEXT_DARK = "#1C3252"
TEXT_MID = "#66758C"
BG = "#F3F6FB"
CARD_BG = "#FFFFFF"
BORDER = "#E1E8F0"

ACCIDENT_LINE = "#5A67F2"
BAR_COLORS = ["#5A67F2", "#F25C54", "#F4A261", "#52A35E"]
treemap_COLORS = ["#5A67F2", "#F25C22", "#F9A11B", "#43A047", "#AB47BC", "#90A4AE"]

# =========================
# 4. ESTILOS (Ajustado para alinhamento)
# =========================
LINE_CHART_HEIGHT = 280  # Altura de cada gráfico de linha
GAP = 16                 # Espaçamento entre os cards (gap)
# Calculamos a altura do mapa para somar:
# (Gráfico 1 + Gráfico 2) + Gap + Ajuste para o botão "Limpar mês"
MAP_HEIGHT = (2 * LINE_CHART_HEIGHT) + GAP + 32


def card_style(padding="16px"):
    return {
        "background": CARD_BG,
        "borderRadius": "18px",
        "padding": padding,
        "boxShadow": "0 2px 10px rgba(28,50,82,0.06)",
        "border": f"1px solid {BORDER}",
    }


def section_title_style():
    return {
        "margin": "0",
        "fontSize": "18px",
        "fontWeight": "700",
        "color": PRIMARY,
        "fontFamily": "Arial, sans-serif"
    }


def kpi_style():
    return {
        "background": CARD_BG,
        "borderRadius": "18px",
        "padding": "18px 20px",
        "boxShadow": "0 2px 10px rgba(28,50,82,0.06)",
        "border": f"1px solid {BORDER}",
        "minHeight": "118px",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "textAlign": "center",
        "gap": "4px"
    }




def sidebar_style(is_open=False):
    return {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "width": "260px",
        "height": "100vh",
        "background": "#FFFFFF",
        "boxShadow": "2px 0 16px rgba(28,50,82,0.18)",
        "padding": "26px 20px",
        "zIndex": "999",
        "transition": "transform 0.3s ease",
        "transform": "translateX(0)" if is_open else "translateX(-320px)",
        "fontFamily": "Arial, sans-serif",
        "borderRight": "1px solid #E1E8F0",
        "boxSizing": "border-box",
    }


def hamburger_style():
    return {
        "position": "fixed",
        "top": "18px",
        "left": "20px",
        "zIndex": "1001",
        "width": "44px",
        "height": "44px",
        "border": "none",
        "borderRadius": "14px",
        "background": "#153B6D",
        "color": "white",
        "fontSize": "24px",
        "fontWeight": "700",
        "cursor": "pointer",
        "boxShadow": "0 4px 14px rgba(21,59,109,0.30)",
        "lineHeight": "1",
    }


def menu_item_style(active=False):
    return {
        "display": "block",
        "padding": "13px 15px",
        "borderRadius": "12px",
        "color": "#153B6D" if active else "#1C3252",
        "fontSize": "14px",
        "fontWeight": "700" if active else "600",
        "marginBottom": "10px",
        "background": "#EAF1FB" if active else "#F7FAFE",
        "border": "1px solid #D7E3F1",
        "textDecoration": "none",
    }

def apply_common_figure_style(fig, height=260):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=18, r=18, t=48, b=18),
        title=dict(
            x=0.02,
            xanchor="left",
            font=dict(size=18, color=PRIMARY, family="Arial, sans-serif")
        ),
        font=dict(family="Arial, sans-serif", size=12, color=TEXT_DARK),
        showlegend=False
    )
    fig.update_xaxes(showgrid=False, linecolor="#D8E1EC", tickfont=dict(size=11, color=TEXT_DARK))
    fig.update_yaxes(gridcolor="#EAEFF5", zeroline=False, linecolor="#D8E1EC", tickfont=dict(size=11, color=TEXT_DARK))
    return fig


def kpi_prev_label(prev_val):
    if prev_val is None:
        return html.Span("Ano anterior: N/A", style={"fontSize": "11px", "color": "#8a94a6"})

    return html.Span(
        f"Ano anterior: {format_int_pt(prev_val)}",
        style={"fontSize": "11px", "color": "#8a94a6"}
    )


def kpi_pct_badge(current, previous, lower_is_better=True):
    if previous is None or previous == 0:
        return html.Span(
            "Sem base",
            style={
                "fontSize": "11px",
                "color": "#8a94a6",
                "fontWeight": "600"
            }
        )

    pct = (current - previous) / previous * 100
    is_improvement = (pct < 0 and lower_is_better) or (pct > 0 and not lower_is_better)

    color = "#1b8a5a" if is_improvement else "#cf3c3c"
    bg = "#eaf7f1" if is_improvement else "#fff1f1"
    arrow = "▼" if pct < 0 else "▲"

    return html.Span(
        f"{arrow} {abs(pct):.1f}%",
        style={
            "fontSize": "11px",
            "color": color,
            "fontWeight": "700",
            "background": bg,
            "padding": "4px 8px",
            "borderRadius": "999px",
            "display": "inline-block"
        }
    )


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
# 6. MAPA
# =========================
def build_map_figure(dff, selected_district):
    if distrito_col is None:
        fig = go.Figure()
        fig.update_layout(title="Coluna Distrito não encontrada", height=MAP_HEIGHT)
        return fig

    if selected_district is None or geojson_portugal is None:
        mapa_df = (
            dff.groupby(["DistritoNorm", distrito_col])
            .size()
            .reset_index(name="Acidentes")
        )

        if geojson_portugal is not None:
            fig = px.choropleth_mapbox(
                mapa_df,
                geojson=geojson_portugal,
                locations="DistritoNorm",
                featureidkey="properties.DistritoNorm",
                color="Acidentes",
                hover_name=distrito_col,
                hover_data={"DistritoNorm": False, "Acidentes": True},
                color_continuous_scale="Reds",
                center={"lat": 39.7, "lon": -8.1},
                zoom=5.5,
                opacity=0.78
            )

            fig.update_layout(
                mapbox_style="carto-positron",
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                paper_bgcolor="white",
                height=MAP_HEIGHT,
                coloraxis_colorbar=dict(
                    title="Acidentes",
                    thickness=14,
                    len=0.85,
                    x=0.20,
                    y=0.5
                )
            )

            return fig

        fig = px.bar(mapa_df, x=distrito_col, y="Acidentes", title="Acidentes por Distrito")
        apply_common_figure_style(fig, MAP_HEIGHT)
        return fig

    if lat_col is None or lon_col is None:
        fig = go.Figure()
        fig.update_layout(title="Coordenadas não encontradas", height=MAP_HEIGHT)
        return fig

    df_filtrado = dff[
        (dff["DistritoNorm"] == selected_district) &
        dff[lat_col].notna() &
        dff[lon_col].notna()
    ].copy()

    if df_filtrado.empty:
        fig = go.Figure()
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=MAP_HEIGHT)
        return fig

    df_filtrado["gravidade"] = "Ligeiro"
    if graves_col:
        df_filtrado.loc[df_filtrado[graves_col].fillna(0) > 0, "gravidade"] = "Grave"
    if mortais_col:
        df_filtrado.loc[df_filtrado[mortais_col].fillna(0) > 0, "gravidade"] = "Mortal"

    coord = coords_capitais.get(selected_district, {"lat": 39.5, "lon": -8.0})

    fig = px.scatter_mapbox(
        df_filtrado,
        lat=lat_col,
        lon=lon_col,
        color="gravidade",
        hover_name=natureza_col if natureza_col else None,
        hover_data={lat_col: False, lon_col: False},
        color_discrete_map={
            "Mortal": "#111111",
            "Grave": "#d62828",
            "Ligeiro": "#f77f00"
        },
        zoom=9.0,
        center=coord
    )

    fig.update_traces(marker=dict(size=9, opacity=0.82))

    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="white",
        height=MAP_HEIGHT,
        legend=dict(
            title="Gravidade",
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.75)"
        )
    )

    return fig


# =========================
# 7. APP
# =========================
app = Dash(__name__)
app.title = "Acidentes Rodoviários em Portugal"

app.layout = html.Div([

    dcc.Store(id="selected-district", data=None),
    dcc.Store(id="selected-month", data=None),

    html.Button(
        "☰",
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

            html.H2(
                "Menu",
                style={
                    "margin": "0",
                    "color": PRIMARY,
                    "fontSize": "24px",
                    "fontWeight": "800"
                }
            ),

            html.P(
                "Dashboards",
                style={
                    "margin": "4px 0 24px 0",
                    "color": TEXT_MID,
                    "fontSize": "13px"
                }
            ),

            html.A(
                "Dashboard Principal",
                href="http://127.0.0.1:8050",
                style=menu_item_style()
            ),

            html.A(
                "Evolução Temporal",
                href="http://127.0.0.1:8051",
                style=menu_item_style()
            ),

            html.A(
                "Comparação entre anos",
                href="http://127.0.0.1:8052",
                style=menu_item_style(active=True)
            ),

            html.Div(
                "Clica novamente em ☰ para fechar o menu.",
                style={
                    "position": "absolute",
                    "bottom": "28px",
                    "left": "20px",
                    "right": "20px",
                    "fontSize": "12px",
                    "color": TEXT_MID,
                    "lineHeight": "1.4"
                }
            )

        ],
        style=sidebar_style(False)
    ),

    # =========================
    # CONTEÚDO PRINCIPAL
    # =========================
    html.Div([

        # =========================
        # TÍTULO
        # =========================
        html.H1(
            id="main-title",
            style={
                "textAlign": "center",
                "margin": "0 0 18px 0",
                "color": PRIMARY,
                "fontSize": "38px",
                "fontWeight": "800",
                "fontFamily": "Arial, sans-serif"
            }
        ),

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
            "gap":f"{GAP}px",
            "marginBottom": "16px"
        }),

        # =========================
        # MAPA + LINHAS
        # =========================
        html.Div([

            # =========================
            # COLUNA ESQUERDA - MAPA
            # =========================
            html.Div([

                html.Div([

                    html.Div([
                        html.H3(
                            id="mapa-titulo",
                            style=section_title_style()
                        ),

                        html.Button(
                            "Limpar seleção",
                            id="btn-reset",
                            n_clicks=0,
                            style={
                                "padding": "7px 12px",
                                "border": f"1px solid {BORDER}",
                                "borderRadius": "10px",
                                "background": "#F7FAFE",
                                "color": PRIMARY,
                                "cursor": "pointer",
                                "fontSize": "13px",
                                "fontWeight": "600"
                            }
                        )

                    ], style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginBottom": "10px"
                    }),

                    dcc.Loading(
                        type="circle",
                        delay_show=200,
                        delay_hide=200,
                        children=dcc.Graph(
                            id="mapa-distritos",
                            style={"height": f"{MAP_HEIGHT}px"},
                            config={"displaylogo": False}
                        )
                    )

                ], style=card_style("10px 12px"))

            ], style={
                "width": "50%"
            }),

            # =========================
            # COLUNA DIREITA - LINHAS
            # =========================
            html.Div([

                # =========================
                # GRÁFICO ACIDENTES
                # =========================
                html.Div([

                    html.Button(
                        "Limpar mês",
                        id="btn-reset-month",
                        n_clicks=0,
                        style={
                            "padding": "7px 12px",
                            "border": f"1px solid {BORDER}",
                            "borderRadius": "10px",
                            "background": "#F7FAFE",
                            "color": PRIMARY,
                            "cursor": "pointer",
                            "fontSize": "13px",
                            "fontWeight": "600",
                            "marginBottom": "10px"
                        }
                    ),

                    dcc.Loading(
                        type="circle",
                        delay_show=200,
                        delay_hide=200,
                        children=dcc.Graph(
                            id="line-acidentes",
                            style={"height": f"{LINE_CHART_HEIGHT}px"},
                            config={"displaylogo": False}
                        )
                    )

                ], style=card_style("10px 12px")),

                # =========================
                # GRÁFICO VÍTIMAS
                # =========================
                html.Div([

                    dcc.Loading(
                        type="circle",
                        delay_show=200,
                        delay_hide=200,
                        children=dcc.Graph(
                            id="line-vitimas",
                            style={"height": f"{LINE_CHART_HEIGHT}px"},
                            config={"displaylogo": False}
                        )
                    )

                ], style=card_style("10px 12px"))

            ], style={
                "width": "50%",
                "display": "flex",
                "flexDirection": "column",
                "justifyContent": "space-between", # Isto ajuda a distribuir o espaço uniformemente
                "gap": f"{GAP}px"
            })

        ], style={
            "display": "flex",
            "gap": f"{GAP}px",
            "alignItems": "stretch",
            "marginBottom": "14px",
            "width": "100%"
        }),


        # =========================
        # BOTTOM CHARTS
        # =========================
    html.Div([

            html.Div([
                dcc.Loading(
                    type="circle",
                    delay_show=200,
                    delay_hide=200,
                    children=dcc.Graph(
                        id="bar-veiculos",
                        style={"height": f"{LINE_CHART_HEIGHT}px"},
                        config={"displaylogo": False}
                    )
                )

            ], style={
                **card_style("10px 12px"),
                "width": "50%"
            }),

            html.Div([
                dcc.Loading(
                    type="circle",
                    delay_show=200,
                    delay_hide=200,
                    children=dcc.Graph(
                        id="treemap-meteorologia",
                        style={"height": f"{LINE_CHART_HEIGHT}px"},
                        config={"displaylogo": False}
                    )
                )

            ], style={
                **card_style("10px 12px"),
                "width": "50%"
            })

        ], style={
            "display": "flex",
            "gap": f"{GAP}px",
            "alignItems": "stretch"
        })

    ], style={
        "maxWidth": "1320px",
        "margin": "0 auto"
    })

], style={
    "padding": "18px 20px 24px 20px",
    "backgroundColor": BG,
    "fontFamily": "Arial, sans-serif",
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
'''
@app.callback(
    Output("selected-month", "data"),
    Input("line-acidentes", "hoverData"),
    Input("line-vitimas", "hoverData"),
    Input("btn-reset-month", "n_clicks"),
    prevent_initial_call=True
)
def update_selected_month(hover_acidentes, hover_vitimas,reset_clicks):
    ctx = callback_context

    if not ctx.triggered:
        return None
    
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

            # 👉 Se clicou no botão → limpa mês
    if trigger == "btn-reset-month":
        return None
    hover_data = None
    if trigger == "line-acidentes":
        hover_data = hover_acidentes
    elif trigger == "line-vitimas":
        hover_data = hover_vitimas
    # 👉 Se veio de hover → seleciona mês

    if hover_data and "points" in hover_data:
        mes = hover_data["points"][0]["x"]
        return mes

    return None
'''
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

        # se já for número
        try:
            return int(x)
        except:
            pass

        # se for texto ("Janeiro", etc.)
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
    Output("mapa-distritos", "figure"),
    Output("line-acidentes", "figure"),
    Output("line-vitimas", "figure"),
    Output("bar-veiculos", "figure"),
    Output("treemap-meteorologia", "figure"),
    Input("selected-district", "data"),
    Input("selected-month", "data")
)
def update_dashboard(selected_district, selected_month):

    base_df = df.copy()

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
    df_year = base_df.copy()

    if selected_year is not None:
        df_year = df_year[pd.to_numeric(df_year["Ano"], errors="coerce") == selected_year]

    df_prev_year = base_df.copy()

    if selected_year is not None:
        df_prev_year = df_prev_year[pd.to_numeric(df_prev_year["Ano"], errors="coerce") == selected_year - 1]

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
    # 4. DATASET PARA LINHAS (SÓ ANO + DISTRITO 🚨 SEM MÊS)
    # =========================
    line_df = df_year.copy()

    if selected_district and distrito_col:
        line_df = line_df[line_df["DistritoNorm"] == selected_district]

    # =========================
    # 5. KPIs ATUAIS
    # =========================
    total_vitimas = int(kpi_df["Vitimas_Totais"].sum()) if "Vitimas_Totais" in kpi_df.columns else 0
    total_graves = int(kpi_df["Acidente_Grave"].sum()) if "Acidente_Grave" in kpi_df.columns else 0

    # =========================
    # 6. KPIs DISTRITO
    # =========================
    distrito_critico = "N/A"
    distrito_count = len(kpi_df)

    if selected_district:
        distrito_critico = selected_district.title()
    elif distrito_col and distrito_col in kpi_df.columns:
        counts = kpi_df[distrito_col].value_counts()
        if not counts.empty:
            distrito_critico = counts.idxmax()
            distrito_count = int(counts.iloc[0])

    # =========================
    # 7. NATUREZA
    # =========================
    natureza_top = "N/A"
    natureza_count = 0

    if natureza_col and natureza_col in kpi_df.columns:
        counts = kpi_df[natureza_col].astype(str).value_counts()
        if not counts.empty:
            natureza_top = counts.idxmax()
            natureza_count = int(counts.iloc[0])

    # =========================
    # 8. KPIs ANO ANTERIOR
    # =========================
    prev_vitimas = None
    prev_graves = None
    prev_distrito_count = None
    prev_natureza_count = None

    if not kpi_prev_df.empty:
        prev_vitimas = int(kpi_prev_df["Vitimas_Totais"].sum()) if "Vitimas_Totais" in kpi_prev_df.columns else None
        prev_graves = int(kpi_prev_df["Acidente_Grave"].sum()) if "Acidente_Grave" in kpi_prev_df.columns else None
        prev_distrito_count = len(kpi_prev_df)

        if natureza_col and natureza_col in kpi_prev_df.columns and natureza_top != "N/A":
            prev_natureza_count = int(
                (kpi_prev_df[natureza_col].astype(str) == natureza_top).sum()
            )

    # =========================
    # KPIs UI
    # =========================
    kpi1 = html.Div([
        html.Div("Vítimas Totais", style={"fontSize": "13px", "fontWeight": "600", "color": TEXT_MID}),
        html.Div(format_int_pt(total_vitimas), style={"fontSize": "26px", "fontWeight": "800", "color": TEXT_DARK}),
        html.Div([kpi_pct_badge(total_vitimas, prev_vitimas, lower_is_better=True)], style={"marginTop": "6px"}),
        kpi_prev_label(prev_vitimas)
    ], style=kpi_style())

    kpi2 = html.Div([
        html.Div("Acidentes Graves", style={"fontSize": "13px", "fontWeight": "600", "color": TEXT_MID}),
        html.Div(format_int_pt(total_graves), style={"fontSize": "26px", "fontWeight": "800", "color": TEXT_DARK}),
        html.Div([kpi_pct_badge(total_graves, prev_graves, lower_is_better=True)], style={"marginTop": "6px"}),
        kpi_prev_label(prev_graves)
    ], style=kpi_style())

    if selected_district:
        kpi3 = html.Div([
            html.Div("Distrito Selecionado", style={"fontSize": "13px", "fontWeight": "600", "color": TEXT_MID}),
            html.Div(str(distrito_critico), style={"fontSize": "24px", "fontWeight": "800", "color": TEXT_DARK}),
            html.Div(f"{format_int_pt(distrito_count)} acidentes", style={"fontSize": "12px", "color": TEXT_MID}),
            html.Div([kpi_pct_badge(distrito_count, prev_distrito_count, lower_is_better=True)], style={"marginTop": "6px"}),
            kpi_prev_label(prev_distrito_count)
        ], style=kpi_style())
    else:
        kpi3 = html.Div([
            html.Div("Distrito Crítico", style={"fontSize": "13px", "fontWeight": "600", "color": TEXT_MID}),
            html.Div(str(distrito_critico), style={"fontSize": "24px", "fontWeight": "800", "color": TEXT_DARK})
        ], style=kpi_style())

    kpi4 = html.Div([
        html.Div("Natureza", style={"fontSize": "13px", "fontWeight": "600", "color": TEXT_MID}),
        html.Div(str(natureza_top), style={"fontSize": "24px", "fontWeight": "800", "color": TEXT_DARK}),
        html.Div(f"{format_int_pt(natureza_count)} acidentes", style={"fontSize": "12px", "color": TEXT_MID}),
        html.Div([kpi_pct_badge(natureza_count, prev_natureza_count, lower_is_better=True)], style={"marginTop": "6px"}),
        kpi_prev_label(prev_natureza_count)
    ], style=kpi_style())

    # =========================
    # MAPA
    # =========================
    mapa_titulo = (
        f"Distribuição de Acidentes - {selected_district.title()}"
        if selected_district
        else "Distribuição de Acidentes"
    )

    fig_mapa = build_map_figure(kpi_df, selected_district)

    # =========================
    # LINHA ACIDENTES (SEM MÊS 🚨)
    # =========================
    if mes_col and mes_col in line_df.columns:
        acidentes_mes = monthly_count(line_df, mes_col)

        fig_line_ac = px.line(
            acidentes_mes,
            x="Mês",
            y="Acidentes",
            markers=True,
            title="Evolução Mensal (Acidentes)"
        )

        # =========================
        # LINHA VERTICAL (MÊS SELECIONADO)
        # =========================
        selected_month_label = None
        if selected_month:
            try:
                selected_month_label = MONTH_LABELS.get(int(selected_month))
            except:
                selected_month_label = selected_month

        if selected_month_label:
            fig_line_ac.add_vline(
                x=selected_month_label,
                line_width=2,
                line_dash="dash",
                line_color="rgba(90, 103, 242, 0.8)"
            )

    else:
        fig_line_ac = go.Figure()

    apply_common_figure_style(fig_line_ac, height=LINE_CHART_HEIGHT)


    # =========================
    # LINHA VÍTIMAS (SEM MÊS 🚨)
    # =========================
    if mes_col and mes_col in line_df.columns and "Vitimas_Totais" in line_df.columns:
        vitimas_mes = monthly_sum(
            line_df,
            mes_col,
            "Vitimas_Totais",
            "Vitimas_Totais"
        )

        fig_line_vit = px.line(
            vitimas_mes,
            x="Mês",
            y="Vitimas_Totais",
            markers=True,
            title="Evolução Mensal (Vítimas)"
        )

        # =========================
        # LINHA VERTICAL (MESMO MÊS)
        # =========================
        if selected_month:
            try:
                selected_month_label = MONTH_LABELS.get(int(selected_month))
            except:
                selected_month_label = selected_month

            if selected_month_label:
                fig_line_vit.add_vline(
                    x=selected_month_label,
                    line_width=2,
                    line_dash="dash",
                    line_color="rgba(90, 103, 242, 0.8)"
                )

    else:
        fig_line_vit = go.Figure()

    apply_common_figure_style(fig_line_vit, height=LINE_CHART_HEIGHT)

    # =========================
    # VEÍCULOS
    # =========================
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
        df_veiculos = pd.DataFrame({"Tipo": veiculos, "Total": valores})

        fig_bar = px.bar(
            df_veiculos,
            x="Tipo",
            y="Total",
            color="Tipo",
            title="Tipos de Veículo Envolvidos",
            text=df_veiculos["Total"].apply(format_int_pt),
            color_discrete_sequence=BAR_COLORS
        )
        apply_common_figure_style(fig_bar, height=260)
    else:
        fig_bar = go.Figure()

    # =========================
    # METEOROLOGIA (FIX DO BUG dff → kpi_df)
    # =========================
# =========================
# METEOROLOGIA (TREEMAP)
# =========================tipo_via_col
    if tipo_via_col and tipo_via_col in kpi_df.columns:
        tipo_via_df = kpi_df[tipo_via_col].astype(str).value_counts().reset_index()
        tipo_via_df.columns = ["Tipos de vias", "Total"]

        fig_treemap = px.treemap(
            tipo_via_df,
            path=["Tipos de vias"],
            values="Total",
            title="Tipos de Vias",
            color="Total",
            color_continuous_scale="Blues"
        )

        apply_common_figure_style(fig_treemap, height=260)

        fig_treemap.update_layout(
            margin=dict(t=40, l=10, r=10, b=10),
            coloraxis_showscale=False
        )
    else:
        fig_treemap = go.Figure()

  


    # =========================
    # TÍTULO
    # =========================
    titulo = (
        f"Acidentes Rodoviários em Portugal - {MONTH_LABELS.get(selected_month)}"
        if selected_month
        else "Acidentes Rodoviários em Portugal"
    )

    return (
        titulo,
        kpi1,
        kpi2,
        kpi3,
        kpi4,
        mapa_titulo,
        fig_mapa,
        fig_line_ac,
        fig_line_vit,
        fig_bar,
        fig_treemap
    )
# =========================
# 11. RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=8050)