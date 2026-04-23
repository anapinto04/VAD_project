import json
import pyproj
import pandas as pd
import dash
from dash import dcc, html, Input, Output, callback_context
import plotly.express as px
from shapely.geometry import shape, mapping
from shapely.ops import transform

# =============================================================================
# 1. TRATAMENTO DO GEOJSON (Conversão de ETRS89 para WGS84)
# =============================================================================
project = pyproj.Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True).transform

with open('ContinenteDistritos.geojson', encoding='utf-8-sig') as f:
    geojson_data = json.load(f)

for feature in geojson_data['features']:
    geom = shape(feature['geometry'])
    new_geom = transform(project, geom)
    feature['geometry'] = mapping(new_geom)

# =============================================================================
# 2. CONFIGURAÇÃO DE DADOS E COORDENADAS
# =============================================================================
coords_capitais = {
    'AVEIRO': {'lat': 40.6405, 'lon': -8.6538},
    'BEJA': {'lat': 38.0151, 'lon': -7.8632},
    'BRAGA': {'lat': 41.5503, 'lon': -8.4201},
    'BRAGANÇA': {'lat': 41.8058, 'lon': -6.7572},
    'CASTELO BRANCO': {'lat': 39.8222, 'lon': -7.4909},
    'COIMBRA': {'lat': 40.2033, 'lon': -8.4103},
    'ÉVORA': {'lat': 38.5714, 'lon': -7.9135},
    'FARO': {'lat': 37.0176, 'lon': -7.9304},
    'GUARDA': {'lat': 40.5365, 'lon': -7.2684},
    'LEIRIA': {'lat': 39.7436, 'lon': -8.8071},
    'LISBOA': {'lat': 38.7223, 'lon': -9.1393},
    'PORTALEGRE': {'lat': 39.2938, 'lon': -7.4285},
    'PORTO': {'lat': 41.1579, 'lon': -8.6291},
    'SANTARÉM': {'lat': 39.2361, 'lon': -8.6850},
    'SETÚBAL': {'lat': 38.5244, 'lon': -8.8931},
    'VIANA DO CASTELO': {'lat': 41.6932, 'lon': -8.8329},
    'VILA REAL': {'lat': 41.3010, 'lon': -7.7422},
    'VISEU': {'lat': 40.6566, 'lon': -7.9125}
}

# Dados de Exemplo para o Mapa Coroplético (Visão Geral)
df_resumo = pd.DataFrame({
    'DISTRITO': list(coords_capitais.keys()),
    'Acidentes': [120, 80, 150, 40, 60, 110, 45, 200, 35, 90, 450, 30, 380, 85, 130, 55, 65, 75]
})

df_acidentes = pd.DataFrame({
    'DISTRITO': ['LISBOA', 'LISBOA', 'PORTO', 'PORTO', 'BRAGA', 'FARO'],
    'lat': [38.725, 38.710, 41.150, 41.165, 41.555, 37.020],
    'lon': [-9.140, -9.135, -8.620, -8.640, -8.425, -7.935],
    'gravidade': ['Grave', 'Ligeiro', 'Mortal', 'Ligeiro', 'Grave', 'Mortal']
})

# =============================================================================
# 3. LAYOUT DA APP
# =============================================================================
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Monitorização de Sinistralidade - Portugal", style={'textAlign': 'center', 'fontFamily': 'Arial'}),
    
    html.Div([
        html.Button("🔄 Ver Portugal Continental", id="btn-reset", n_clicks=0, 
                    style={'padding': '10px', 'fontSize': '15px', 'cursor': 'pointer'})
    ], style={'textAlign': 'center', 'marginBottom': '10px'}),
    
    dcc.Graph(id='mapa-principal', style={'height': '85vh'})
])

# =============================================================================
# 4. CALLBACK DE INTERATIVIDADE
# =============================================================================
@app.callback(
    Output('mapa-principal', 'figure'),
    [Input('mapa-principal', 'clickData'),
     Input('btn-reset', 'n_clicks')]
)
def atualizar_mapa(clickData, n_clicks):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'btn-reset'

    # --- ESTADO INICIAL / RESET: Mostrar Áreas Coloridas ---
    if trigger == 'btn-reset' or clickData is None:
        fig = px.choropleth_map(
            df_resumo,
            geojson=geojson_data,
            locations="DISTRITO",
            featureidkey="properties.Distrito",
            color="Acidentes",
            color_continuous_scale="Reds",
            center={"lat": 39.5, "lon": -8.0},
            zoom=6
        )
        fig.update_layout(title="Clique num distrito para ver detalhes dos acidentes")

    # --- ESTADO ZOOM: Mapa Limpo com Pontos (Scatter) ---
    else:
        distrito_clicado = clickData['points'][0]['location']
        df_filtrado = df_acidentes[df_acidentes['DISTRITO'] == distrito_clicado]
        coord = coords_capitais.get(distrito_clicado, {"lat": 39.5, "lon": -8.0})
    
        fig = px.scatter_map(
            df_filtrado,
            lat="lat",
            lon="lon",
            color="gravidade",
            color_discrete_map={'Mortal': 'black', 'Grave': 'red', 'Ligeiro': 'orange'},
            zoom=11,
            center=coord
        )
        fig.update_traces(marker=dict(size=12))
        fig.update_layout(title=f"Distribuição de Acidentes: {distrito_clicado}")

    fig.update_layout(
        map_style="carto-positron", 
        margin={"r":0,"t":50,"l":0,"b":0}
    )
    
    return fig

if __name__ == '__main__':
    app.run(debug=True, port=8051)