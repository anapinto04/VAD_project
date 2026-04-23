import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import numpy as np

app = dash.Dash(__name__)

# ==============================================================================
# 1. DADOS (Simulação Melhorada para evitar água)
# ==============================================================================
def gerar_dados_limpos():
    np.random.seed(42)
    # Coordenadas de Lisboa (Terra Firme)
    # Criamos clusters em zonas específicas para evitar o Tejo
    zonas_terra = [
        {'lat': 38.73, 'lon': -9.14}, # Centro
        {'lat': 38.75, 'lon': -9.11}, # Alvalade
        {'lat': 38.71, 'lon': -9.16}, # Campo de Ourique
        {'lat': 38.70, 'lon': -9.19}, # Belém
    ]
    
    rows = []
    for zona in zonas_terra:
        for _ in range(30):
            rows.append({
                'Latitude': zona['lat'] + np.random.uniform(-0.01, 0.01),
                'Longitude': zona['lon'] + np.random.uniform(-0.01, 0.01),
                'Natureza': np.random.choice(['Colisão', 'Despiste', 'Atropelamento']),
                'Gravidade': np.random.choice(['Leve', 'Grave']),
                'Vitimas': np.random.randint(1, 4)
            })
    return pd.DataFrame(rows)

df_geo = gerar_dados_limpos()

# ==============================================================================
# 2. LAYOUT COM "MAGIC LENS" (LADO A LADO)
# ==============================================================================
app.layout = html.Div(style={'fontFamily': 'Segoe UI', 'backgroundColor': '#f0f2f2', 'padding': '20px'}, children=[
    
    html.Div(style={'backgroundColor': '#008080', 'padding': '15px', 'borderRadius': '12px', 'color': 'white', 'marginBottom': '20px'}, children=[
        html.H2("Mapa de Precisão e Lente de Detalhe", style={'margin': '0', 'textAlign': 'center'})
    ]),

    html.Div(style={'display': 'flex', 'gap': '15px'}, children=[
        
        # MAPA PRINCIPAL (VISÃO GERAL)
        html.Div(style={'flex': '2', 'backgroundColor': 'white', 'padding': '10px', 'borderRadius': '15px'}, children=[
            html.H4("Visão Geral (Passe o rato para ativar a Lente)", style={'textAlign': 'center', 'color': '#666'}),
            dcc.Graph(id='mapa-principal', clear_on_unhover=True)
        ]),

        # A "MAGIC LENS" (MAPA DE ZOOM AUTOMÁTICO)
        html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '10px', 'borderRadius': '15px', 'border': '3px solid #008080'}, children=[
            html.H4("🔍 Lente de Detalhe", style={'textAlign': 'center', 'color': '#008080'}),
            dcc.Graph(id='magic-lens-graph'),
            html.Div(id='info-lente', style={'padding': '10px', 'fontSize': '13px', 'color': '#333'})
        ])
    ])
])

# ==============================================================================
# 3. CALLBACK PARA A LENTE MÁGICA
# ==============================================================================
@app.callback(
    [Output('mapa-principal', 'figure'),
     Output('magic-lens-graph', 'figure'),
     Output('info-lente', 'children')],
    [Input('mapa-principal', 'hoverData')]
)
def update_lens(hoverData):
    # --- MAPA PRINCIPAL ---
    fig_main = px.scatter_mapbox(
        df_geo, lat="Latitude", lon="Longitude", color="Natureza",
        color_discrete_map={'Colisão': '#008080', 'Despiste': '#FF7F0E', 'Atropelamento': '#D62728'},
        zoom=11, center={"lat": 38.72, "lon": -9.14}
    )
    fig_main.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)

    # --- LÓGICA DA LENTE (ZOOM NO PONTO) ---
    if hoverData is None:
        # Se não houver hover, a lente foca no centro
        lat_zoom, lon_zoom = 38.72, -9.14
        zoom_level = 11
        info = "Passe o cursor sobre um ponto no mapa à esquerda."
    else:
        # Foca exatamente nas coordenadas onde o rato está
        lat_zoom = hoverData['points'][0]['lat']
        lon_zoom = hoverData['points'][0]['lon']
        zoom_level = 16 # Zoom ultra aproximado (Lente)
        natureza = hoverData['points'][0]['customdata'] if 'customdata' in hoverData['points'][0] else "Sinistro"
        info = html.Div([
            html.B(f"Localização Focada: {lat_zoom:.4f}, {lon_zoom:.4f}"),
            html.P(f"Alerta de zona crítica detetado.")
        ])

    fig_lens = px.scatter_mapbox(
        df_geo, lat="Latitude", lon="Longitude", color="Natureza",
        size_max=15, zoom=zoom_level, center={"lat": lat_zoom, "lon": lon_zoom}
    )
    fig_lens.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    
    return fig_main, fig_lens, info

if __name__ == '__main__':
    app.run(debug=True, port=8055)