import json
import pyproj
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc # Necessário: pip install dash-bootstrap-components
import plotly.express as px
from shapely.geometry import shape, mapping
from shapely.ops import transform

# =============================================================================
# 1. TRATAMENTO DO GEOJSON
# =============================================================================
project = pyproj.Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True).transform
with open('ContinenteDistritos.geojson', encoding='utf-8-sig') as f:
    geojson_data = json.load(f)

for feature in geojson_data['features']:
    geom = shape(feature['geometry'])
    new_geom = transform(project, geom)
    feature['geometry'] = mapping(new_geom)

# =============================================================================
# 2. DADOS E COORDENADAS
# =============================================================================
coords_capitais = {
    'AVEIRO': {'lat': 40.6405, 'lon': -8.6538}, 'BEJA': {'lat': 38.0151, 'lon': -7.8632},
    'BRAGA': {'lat': 41.5503, 'lon': -8.4201}, 'BRAGANÇA': {'lat': 41.8058, 'lon': -6.7572},
    'CASTELO BRANCO': {'lat': 39.8222, 'lon': -7.4909}, 'COIMBRA': {'lat': 40.2033, 'lon': -8.4103},
    'ÉVORA': {'lat': 38.5714, 'lon': -7.9135}, 'FARO': {'lat': 37.0176, 'lon': -7.9304},
    'GUARDA': {'lat': 40.5365, 'lon': -7.2684}, 'LEIRIA': {'lat': 39.7436, 'lon': -8.8071},
    'LISBOA': {'lat': 38.7223, 'lon': -9.1393}, 'PORTALEGRE': {'lat': 39.2938, 'lon': -7.4285},
    'PORTO': {'lat': 41.1579, 'lon': -8.6291}, 'SANTARÉM': {'lat': 39.2361, 'lon': -8.6850},
    'SETÚBAL': {'lat': 38.5244, 'lon': -8.8931}, 'VIANA DO CASTELO': {'lat': 41.6932, 'lon': -8.8329},
    'VILA REAL': {'lat': 41.3010, 'lon': -7.7422}, 'VISEU': {'lat': 40.6566, 'lon': -7.9125}
}

df_resumo = pd.DataFrame({'DISTRITO': list(coords_capitais.keys()), 'Acidentes': [120, 80, 150, 40, 60, 110, 45, 200, 35, 90, 450, 30, 380, 85, 130, 55, 65, 75]})
df_acidentes = pd.DataFrame({'DISTRITO': ['LISBOA', 'LISBOA', 'PORTO', 'PORTO', 'BRAGA', 'FARO'], 'lat': [38.725, 38.710, 41.150, 41.165, 41.555, 37.020], 'lon': [-9.140, -9.135, -8.620, -8.640, -8.425, -7.935], 'gravidade': ['Grave', 'Ligeiro', 'Mortal', 'Ligeiro', 'Grave', 'Mortal']})

# =============================================================================
# 3. LAYOUT COM BOOTSTRAP
# =============================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Monitorização de Sinistralidade", className="text-center mt-3"), width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Button("🔄 Reset Mapa", id="btn-reset", color="primary", className="me-2"),
            dbc.Checklist(
                options=[{"label": "🌙 Modo Escuro", "value": 1}],
                value=[],
                id="switch-tema",
                switch=True,
                inline=True,
                style={"display": "inline-block", "verticalAlign": "middle"}
            ),
        ], width=12, className="text-center mb-3")
    ]),
    
    dbc.Row([
        dbc.Col(dcc.Graph(id='mapa-principal', style={'height': '75vh'}), width=12)
    ])
], id="main-container", fluid=True, style={"transition": "all 0.5s"})

# =============================================================================
# 4. CALLBACK ÚNICO (Mapa + Tema)
# =============================================================================
@app.callback(
    [Output('mapa-principal', 'figure'),
     Output('main-container', 'style')],
    [Input('mapa-principal', 'clickData'),
     Input('btn-reset', 'n_clicks'),
     Input('switch-tema', 'value')]
)
def atualizar_dashboard(clickData, n_reset, dark_mode):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'btn-reset'
    
    # Definir cores do tema da página
    is_dark = len(dark_mode) > 0
    bg_color = "#1a1a1a" if is_dark else "white"
    text_color = "white" if is_dark else "black"
    container_style = {"backgroundColor": bg_color, "color": text_color, "minHeight": "100vh"}
    
    # Configuração visual do Plotly baseada no tema
    map_style = "carto-darkmatter" if is_dark else "carto-positron"
    template = "plotly_dark" if is_dark else "plotly_white"

    # --- LÓGICA DO MAPA ---
    # Se clicar no Reset ou no Switch de Tema sem ter um distrito selecionado
    if trigger in ['btn-reset', 'switch-tema'] and clickData is None:
        fig = px.choropleth_map(
            df_resumo, geojson=geojson_data, locations="DISTRITO",
            featureidkey="properties.Distrito", color="Acidentes",
            color_continuous_scale="Reds", center={"lat": 39.5, "lon": -8.0}, zoom=6,
            template=template
        )
        fig.update_layout(title="Visão por Distrito")

    # --- LÓGICA DE ZOOM ---
    else:
        distrito_clicado = clickData['points'][0]['location'] if clickData else 'LISBOA'
        df_filtrado = df_acidentes[df_acidentes['DISTRITO'] == distrito_clicado]
        coord = coords_capitais.get(distrito_clicado, {"lat": 39.5, "lon": -8.0})
        
        fig = px.scatter_map(
            df_filtrado, lat="lat", lon="lon", color="gravidade",
            color_discrete_map={'Mortal': 'black', 'Grave': 'red', 'Ligeiro': 'orange'},
            zoom=11, center=coord, template=template
        )
        fig.update_traces(marker=dict(size=14))
        fig.update_layout(title=f"Acidentes em {distrito_clicado}")

    fig.update_layout(map_style=map_style, margin={"r":0,"t":50,"l":0,"b":0})
    
    return fig, container_style

if __name__ == '__main__':
    app.run(debug=True)