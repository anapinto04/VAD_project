import os
import unicodedata
import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuração do agrupamento: 100 metros convertidos para graus aproximados
RAIO_AGRUPAMENTO_DEG = 100 / 111000 

# =========================
# 1. FUNÇÕES DE DADOS
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

def load_data():
    preferred_years = range(2018, 2025)
    dfs = []
    for year in preferred_years:
        path = os.path.join(BASE_DIR, "Datasets_Limpos", f"Tabela_acidentes_{year}_limpo.xlsx")
        if os.path.exists(path):
            try:
                df_local = pd.read_excel(path)
                df_local["Ano"] = year
                dfs.append(df_local)
            except: continue
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# --- PROCESSAMENTO ---
df_geo = load_data()
lat_col = find_column(df_geo, ["Latitude GPS", "Latitude"])
lon_col = find_column(df_geo, ["Longitude GPS", "Longitude"])
natureza_col = find_column(df_geo, ["Natureza"])

if not df_geo.empty and lat_col and lon_col:
    df_geo[lat_col] = pd.to_numeric(df_geo[lat_col], errors="coerce")
    df_geo[lon_col] = pd.to_numeric(df_geo[lon_col], errors="coerce")
    df_geo = df_geo.dropna(subset=[lat_col, lon_col]).copy()
    df_geo["Natureza_Mapa"] = df_geo[natureza_col].fillna("Sem informação").astype(str) if natureza_col else "Sem informação"
    
    # Criar Clusters de 100m para o Mapa da Esquerda
    df_geo["grid_lat"] = (df_geo[lat_col] / RAIO_AGRUPAMENTO_DEG).round()
    df_geo["grid_lon"] = (df_geo[lon_col] / RAIO_AGRUPAMENTO_DEG).round()
    
    df_clusters = df_geo.groupby(["grid_lat", "grid_lon"]).agg({
        lat_col: "mean",
        lon_col: "mean",
        "Natureza_Mapa": lambda x: x.value_counts().idxmax() # Natureza predominante no grupo
    }).reset_index()
    
    # Contagem de acidentes por cluster para a cor
    counts = df_geo.groupby(["grid_lat", "grid_lon"]).size().reset_index(name="Total_Acidentes")
    df_clusters = df_clusters.merge(counts, on=["grid_lat", "grid_lon"])

# =========================
# 2. INTERFACE (LAYOUT)
# =========================
PRIMARY = "#153B6D"
BG = "#F3F6FB"

app = dash.Dash(__name__)

app.layout = html.Div(style={"fontFamily": "Arial", "backgroundColor": BG, "padding": "20px"}, children=[
    html.Div(style={"maxWidth": "1400px", "margin": "0 auto"}, children=[
        html.H1("Análise por Clusters (100m) e Lupa de Detalhe", style={"textAlign": "center", "color": PRIMARY}),
        
        html.Div(style={"display": "grid", "gridTemplateColumns": "1.2fr 1fr", "gap": "20px"}, children=[
            # Mapa Esquerda: Agrupado por 100m
            html.Div(children=[
                html.H3("Zonas de Concentração (Cor = Volume)", style={"textAlign": "center"}),
                dcc.Graph(id="mapa-principal", style={"height": "70vh"}, config={"displaylogo": False}, clear_on_unhover=True)
            ], style={"backgroundColor": "white", "padding": "15px", "borderRadius": "15px"}),
            
            # Mapa Direita: Lupa Individual
            html.Div(children=[
                html.H3("Lupa de Detalhe (Pontos Reais)", style={"textAlign": "center", "color": PRIMARY}),
                dcc.Graph(id="mapa-lupa", style={"height": "50vh"}, config={"displaylogo": False}),
                html.Div(id="info-detalhe", style={"marginTop": "10px", "padding": "10px", "background": "#f0f4f9", "borderRadius": "10px"})
            ], style={"backgroundColor": "white", "padding": "15px", "borderRadius": "15px", "border": f"2px solid {PRIMARY}"})
        ])
    ])
])

# =========================
# 3. LÓGICA (CALLBACKS)
# =========================
@app.callback(
    [Output("mapa-principal", "figure"),
     Output("mapa-lupa", "figure"),
     Output("info-detalhe", "children")],
    [Input("mapa-principal", "hoverData")]
)
def update_viz(hoverData):
    # 1. MAPA PRINCIPAL (CLUSTERS)
    # Escala de cor: do rosa claro ao vermelho escuro/preto
    fig_main = px.scatter_mapbox(
        df_clusters, lat=lat_col, lon=lon_col,
        color="Total_Acidentes",
        size="Total_Acidentes",
        size_max=15,
        color_continuous_scale=["#ffcdd2", "#e53935", "#b71c1c", "#1a0000"],
        zoom=6, center={"lat": 39.7, "lon": -8.1},
        mapbox_style="carto-positron",
        hover_data={"Total_Acidentes": True, lat_col: False, lon_col: False}
    )
    fig_main.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_showscale=False)

    # 2. LÓGICA DA LUPA
    if hoverData:
        target_lat = hoverData["points"][0]["lat"]
        target_lon = hoverData["points"][0]["lon"]

        # Filtro para a lupa (raio de ~800m ao redor do cluster)
        df_lupa = df_geo[
            (np.abs(df_geo[lat_col] - target_lat) < 0.008) & 
            (np.abs(df_geo[lon_col] - target_lon) < 0.008)
        ].copy()

        fig_lupa = px.scatter_mapbox(
            df_lupa, lat=lat_col, lon=lon_col, color="Natureza_Mapa",
            zoom=15, center={"lat": target_lat, "lon": target_lon}
        )
        info = f"Cluster focado. Ocorrências individuais nesta zona: {len(df_lupa)}"
    else:
        fig_lupa = px.scatter_mapbox(lat=[39.7], lon=[-8.1], zoom=5)
        info = "Passe o rato sobre as bolas escuras do mapa principal."

    fig_lupa.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)

    return fig_main, fig_lupa, info

if __name__ == "__main__":
    app.run(debug=True, port=8056)