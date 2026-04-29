
import os
import unicodedata

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import numpy as np


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def format_int_pt(value):
    return f"{int(value):,}".replace(",", ".")


def load_data():
    possible_files = [
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2018_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2019_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2020_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2021_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2022_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2023_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2024_limpo.xlsx"),
    ]

    dfs = []

    for file in possible_files:
        if not os.path.exists(file):
            continue

        try:
            df_local = pd.read_excel(file)
        except Exception as e:
            print(f"Erro ao ler {file}: {e}")
            continue

        filename = os.path.basename(file)
        digits = "".join(filter(str.isdigit, filename))

        if len(digits) >= 4:
            df_local["Ano"] = int(digits[:4])

        dfs.append(df_local)

    if not dfs:
        print("Aviso: não foram encontrados ficheiros de acidentes.")
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


df_geo = load_data()

lat_col = find_column(df_geo, ["Latitude GPS", "Latitude", "Lat"])
lon_col = find_column(df_geo, ["Longitude GPS", "Longitude", "Lon", "Lng"])
natureza_col = find_column(df_geo, ["Natureza", "Natureza do Acidente", "Tipo de Acidente"])

if not df_geo.empty:
    if lat_col:
        df_geo[lat_col] = pd.to_numeric(df_geo[lat_col], errors="coerce")

    if lon_col:
        df_geo[lon_col] = pd.to_numeric(df_geo[lon_col], errors="coerce")

    if lat_col and lon_col:
        df_geo = df_geo.dropna(subset=[lat_col, lon_col]).copy()
    else:
        df_geo = pd.DataFrame()

    if not df_geo.empty:
        if natureza_col:
            df_geo["Natureza_Mapa"] = df_geo[natureza_col].fillna("Sem informação").astype(str)
        else:
            df_geo["Natureza_Mapa"] = "Sem informação"

        df_geo["Acidentes"] = 1

        df_geo = df_geo[
            (df_geo[lat_col].between(36.5, 42.5)) &
            (df_geo[lon_col].between(-10.5, -5.5))
        ].copy()


PRIMARY = "#153B6D"
TEXT_DARK = "#1C3252"
TEXT_MID = "#66758C"
BG = "#F3F6FB"
CARD_BG = "#FFFFFF"
BORDER = "#E1E8F0"

NATUREZA_COLORS = {
    "Colisão": "#0072B2",
    "Despiste": "#E69F00",
    "Atropelamento": "#D55E00",
    "Sem informação": "#999999",
}


def card_style(padding="18px"):
    return {
        "backgroundColor": CARD_BG,
        "padding": padding,
        "borderRadius": "18px",
        "boxShadow": "0 2px 10px rgba(28,50,82,0.06)",
        "border": f"1px solid {BORDER}",
    }


def menu_item_style(active=False):
    return {
        "display": "block",
        "padding": "12px 14px",
        "borderRadius": "12px",
        "color": PRIMARY if active else TEXT_DARK,
        "fontSize": "14px",
        "fontWeight": "700" if active else "600",
        "marginBottom": "10px",
        "background": "#EAF1FB" if active else "#F7FAFE",
        "border": "1px solid #D7E3F1",
        "textDecoration": "none",
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
        "borderRight": f"1px solid {BORDER}",
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
        "background": PRIMARY,
        "color": "white",
        "fontSize": "24px",
        "fontWeight": "700",
        "cursor": "pointer",
        "boxShadow": "0 4px 14px rgba(21,59,109,0.30)",
        "lineHeight": "1",
    }


app = dash.Dash(__name__)
app.title = "Lente Fish Eye & Volume de Acidentes"

app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "backgroundColor": BG,
        "padding": "18px 20px 24px 20px",
        "minHeight": "100vh",
    },
    children=[
        html.Button(
            "☰",
            id="hamburger-btn",
            n_clicks=0,
            title="Abrir menu",
            style=hamburger_style(),
        ),

        html.Div(
            id="sidebar-menu",
            children=[
                html.H2(
                    "Menu",
                    style={
                        "margin": "0",
                        "color": PRIMARY,
                        "fontSize": "24px",
                        "fontWeight": "800",
                    },
                ),
                html.P(
                    "Dashboards",
                    style={
                        "margin": "4px 0 24px 0",
                        "color": TEXT_MID,
                        "fontSize": "13px",
                    },
                ),

                html.A("Mapa Principal", href="http://127.0.0.1:8050", style=menu_item_style()),
                html.A("Evolução Temporal", href="http://127.0.0.1:8052", style=menu_item_style()),
                html.A("Análise Comparativa", href="http://127.0.0.1:8053", style=menu_item_style()),
                html.A("Fish Eye / Volume", href="http://127.0.0.1:8056", style=menu_item_style(active=True)),

                html.Div(
                    "Clica novamente em ☰ para fechar o menu.",
                    style={
                        "position": "absolute",
                        "bottom": "28px",
                        "left": "20px",
                        "right": "20px",
                        "fontSize": "12px",
                        "color": TEXT_MID,
                        "lineHeight": "1.4",
                    },
                ),
            ],
            style=sidebar_style(False),
        ),

        html.Div(
            style={
                "maxWidth": "1320px",
                "margin": "0 auto",
            },
            children=[
                html.Div(
                    style={
                        **card_style("20px"),
                        "marginBottom": "16px",
                        "textAlign": "center",
                    },
                    children=[
                        html.H1(
                            "Sinistralidade: Lente Fish Eye & Volume de Dados",
                            style={
                                "margin": "0",
                                "color": PRIMARY,
                                "fontSize": "34px",
                                "fontWeight": "800",
                            },
                        ),
                        html.P(
                            "Passe o rato sobre um ponto para ampliar a zona envolvente e observar o detalhe no painel lateral.",
                            style={
                                "margin": "8px 0 0 0",
                                "color": TEXT_MID,
                                "fontSize": "14px",
                            },
                        ),
                    ],
                ),

                html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "2fr 1fr",
                        "gap": "16px",
                        "alignItems": "stretch",
                    },
                    children=[
                        html.Div(
                            style=card_style("16px"),
                            children=[
                                html.H3(
                                    "Mapa Principal",
                                    style={
                                        "textAlign": "center",
                                        "color": PRIMARY,
                                        "margin": "0 0 12px 0",
                                        "fontSize": "18px",
                                        "fontWeight": "700",
                                    },
                                ),
                                dcc.Graph(
                                    id="mapa-fisheye",
                                    clear_on_unhover=True,
                                    style={"height": "65vh"},
                                    config={"displaylogo": False},
                                ),
                            ],
                        ),

                        html.Div(
                            style={**card_style("16px"), "border": f"2px solid {PRIMARY}"},
                            children=[
                                html.H3(
                                    "Zoom de Contexto",
                                    style={
                                        "textAlign": "center",
                                        "color": PRIMARY,
                                        "margin": "0 0 12px 0",
                                        "fontSize": "18px",
                                        "fontWeight": "700",
                                    },
                                ),
                                dcc.Graph(
                                    id="graph-detalhe",
                                    style={"height": "50vh"},
                                    config={"displaylogo": False},
                                ),
                                html.Div(
                                    id="texto-detalhe",
                                    style={
                                        "padding": "12px",
                                        "marginTop": "12px",
                                        "backgroundColor": "#F7FAFE",
                                        "borderRadius": "12px",
                                        "border": f"1px solid {BORDER}",
                                        "color": TEXT_DARK,
                                        "fontSize": "13px",
                                        "lineHeight": "1.5",
                                    },
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("sidebar-menu", "style"),
    Input("hamburger-btn", "n_clicks"),
)
def toggle_sidebar(n_clicks):
    is_open = bool(n_clicks and n_clicks % 2 == 1)
    return sidebar_style(is_open)


@app.callback(
    Output("mapa-fisheye", "figure"),
    Output("graph-detalhe", "figure"),
    Output("texto-detalhe", "children"),
    Input("mapa-fisheye", "hoverData"),
)
def update_all_viz(hoverData):
    if df_geo.empty or lat_col is None or lon_col is None:
        fig_empty = px.scatter()
        fig_empty.update_layout(
            template="plotly_white",
            height=500,
            annotations=[
                dict(
                    text="Sem dados geográficos disponíveis. Verifica as colunas de Latitude e Longitude.",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=15, color=TEXT_MID),
                )
            ],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )

        return fig_empty, fig_empty, "Não foram encontradas coordenadas válidas nos ficheiros."

    dff = df_geo.copy()

    tamanho_base = np.full(len(dff), 7.0)

    if hoverData:
        target_lat = hoverData["points"][0]["lat"]
        target_lon = hoverData["points"][0]["lon"]

        dist = np.sqrt(
            (dff[lat_col] - target_lat) ** 2 +
            (dff[lon_col] - target_lon) ** 2
        )

        multiplicador_lente = 1 + 3.5 * np.exp(-dist * 180)
        dff["tamanho_final"] = tamanho_base * multiplicador_lente

        zoom_lat = target_lat
        zoom_lon = target_lon
        zoom_level = 13

        raio = 0.02
        proximos = dff[
            (abs(dff[lat_col] - target_lat) <= raio) &
            (abs(dff[lon_col] - target_lon) <= raio)
        ]

        natureza_top = (
            proximos["Natureza_Mapa"].value_counts().idxmax()
            if not proximos.empty
            else "Sem informação"
        )

        info = html.Div([
            html.B("Ponto focado", style={"color": PRIMARY}),
            html.P(f"Coordenadas: {target_lat:.4f}, {target_lon:.4f}", style={"margin": "6px 0"}),
            html.P(f"Acidentes próximos: {format_int_pt(len(proximos))}", style={"margin": "6px 0"}),
            html.P(f"Natureza mais comum: {natureza_top}", style={"margin": "6px 0"}),
        ])
    else:
        dff["tamanho_final"] = tamanho_base
        zoom_lat = 39.7
        zoom_lon = -8.1
        zoom_level = 6

        info = "Passe o rato sobre os pontos para ativar a lente Fish Eye e o zoom de detalhe."

    fig_main = px.scatter_mapbox(
        dff,
        lat=lat_col,
        lon=lon_col,
        color="Natureza_Mapa",
        size="tamanho_final",
        size_max=42,
        color_discrete_map=NATUREZA_COLORS,
        zoom=6,
        center={"lat": 39.7, "lon": -8.1},
        hover_name="Natureza_Mapa",
        hover_data={
            lat_col: False,
            lon_col: False,
            "tamanho_final": False,
            "Acidentes": False,
            "Ano": True if "Ano" in dff.columns else False,
        },
    )

    fig_main.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=True,
        legend=dict(
            title="Natureza",
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
        ),
        transition_duration=100,
        paper_bgcolor="white",
    )

    fig_detalhe = px.scatter_mapbox(
        df_geo,
        lat=lat_col,
        lon=lon_col,
        color="Natureza_Mapa",
        size="Acidentes",
        size_max=12,
        color_discrete_map=NATUREZA_COLORS,
        zoom=zoom_level,
        center={"lat": zoom_lat, "lon": zoom_lon},
        hover_name="Natureza_Mapa",
        hover_data={
            lat_col: False,
            lon_col: False,
            "Acidentes": False,
            "Ano": True if "Ano" in df_geo.columns else False,
        },
    )

    fig_detalhe.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=False,
        paper_bgcolor="white",
    )

    return fig_main, fig_detalhe, info


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=8056)
