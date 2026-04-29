import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

app = dash.Dash(__name__)

# CSS inline para o menu hamburger
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Dashboard 4.2 - Volume de Acidentes</title>
        {%favicon%}
        {%css%}
        <style>
            .hamburger-menu {
                position: fixed;
                top: 20px;
                left: 20px;
                z-index: 1000;
                cursor: pointer;
                background: #fff;
                border: none;
                border-radius: 5px;
                padding: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }
            .hamburger-menu span {
                display: block;
                width: 25px;
                height: 3px;
                background: #333;
                margin: 5px 0;
                transition: 0.3s;
            }
            .sidebar {
                position: fixed;
                top: 0;
                left: -250px;
                width: 250px;
                height: 100%;
                background: #f8f9fa;
                box-shadow: 2px 0 10px rgba(0,0,0,0.2);
                transition: 0.3s;
                z-index: 999;
                padding-top: 60px;
            }
            .sidebar a {
                display: block;
                padding: 15px 20px;
                color: #333;
                text-decoration: none;
                border-bottom: 1px solid #ddd;
            }
            .sidebar a:hover {
                background: #e9ecef;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ==============================================================================
# 1. DADOS (Simulação com Volume de Acidentes)
# ==============================================================================
def gerar_dados_pro():
    np.random.seed(42)
    zonas_terra = [
        {'lat': 38.73, 'lon': -9.14}, # Centro
        {'lat': 38.75, 'lon': -9.11}, # Alvalade
        {'lat': 38.71, 'lon': -9.16}, # Campo de Ourique
        {'lat': 38.70, 'lon': -9.19}, # Belém
    ]
    
    rows = []
    for zona in zonas_terra:
        for i in range(40):
            rows.append({
                'id': i,
                'Latitude': zona['lat'] + np.random.uniform(-0.012, 0.012),
                'Longitude': zona['lon'] + np.random.uniform(-0.012, 0.012),
                'Natureza': np.random.choice(['Colisão', 'Despiste', 'Atropelamento']),
                'Acidentes': np.random.randint(1, 25) # O tamanho base vem daqui
            })
    return pd.DataFrame(rows)

df_geo = gerar_dados_pro()

# ==============================================================================
# 2. LAYOUT
# ==============================================================================
app.layout = html.Div(style={'fontFamily': 'Segoe UI', 'backgroundColor': '#f0f2f2', 'padding': '20px'}, children=[
    
    # Menu Hamburguer
    dcc.Store(id='menu-state', data=False),
    html.Button([html.Span(), html.Span(), html.Span()], className='hamburger-menu', id='hamburger-btn'),
    html.Button(id='overlay-btn', style={
        'position': 'fixed', 'top': '0', 'left': '0', 'width': '100%', 'height': '100%',
        'background': 'rgba(0,0,0,0.5)', 'border': 'none', 'cursor': 'pointer',
        'display': 'none', 'zIndex': '998'
    }),
    html.Div([
        html.H3("Dashboards", style={'padding': '20px', 'margin': '0', 'borderBottom': '1px solid #ddd'}),
        html.A('Mapa Principal', href='http://localhost:8051', style={'display': 'block', 'padding': '15px 20px', 'color': '#333', 'textDecoration': 'none', 'borderBottom': '1px solid #ddd'}),
        html.A('Dashboard 2', href='http://localhost:8052', style={'display': 'block', 'padding': '15px 20px', 'color': '#333', 'textDecoration': 'none', 'borderBottom': '1px solid #ddd'}),
        html.A('Dashboard 3', href='http://localhost:8053', style={'display': 'block', 'padding': '15px 20px', 'color': '#333', 'textDecoration': 'none', 'borderBottom': '1px solid #ddd'}),
        html.A('Dashboard 4', href='http://localhost:8054', style={'display': 'block', 'padding': '15px 20px', 'color': '#333', 'textDecoration': 'none', 'borderBottom': '1px solid #ddd'}),
        html.A('Dashboard Experiência', href='http://localhost:8055', style={'display': 'block', 'padding': '15px 20px', 'color': '#333', 'textDecoration': 'none', 'borderBottom': '1px solid #ddd'}),
    ], className='sidebar', id='sidebar', style={'left': '-250px'}),
    
    html.Div(style={'backgroundColor': '#008080', 'padding': '15px', 'borderRadius': '12px', 'color': 'white', 'marginBottom': '20px'}, children=[
        html.H2("Sinistralidade: Lente Fish Eye & Volume de Dados", style={'margin': '0', 'textAlign': 'center'})
    ]),

    html.Div(style={'display': 'flex', 'gap': '15px'}, children=[
        
        # MAPA PRINCIPAL COM EFEITO FISH EYE
        html.Div(style={'flex': '2', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '15px'}, children=[
            html.H4("Mapa Principal (O tamanho base indica o volume de acidentes)", 
                    style={'textAlign': 'center', 'color': '#666', 'marginTop': '0'}),
            dcc.Graph(id='mapa-fisheye', clear_on_unhover=True, style={'height': '65vh'})
        ]),

        # LENTE DE DETALHE (ZOOM FIXO)
        html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '15px', 'border': '3px solid #008080'}, children=[
            html.H4("🔍 Zoom de Contexto", style={'textAlign': 'center', 'color': '#008080', 'marginTop': '0'}),
            dcc.Graph(id='graph-detalhe', style={'height': '50vh'}),
            html.Div(id='texto-detalhe', style={'padding': '10px', 'marginTop': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px'})
        ])
    ])
])

# ==============================================================================
# 3. CALLBACK UNIFICADO
# ==============================================================================

# Callback do Menu Hamburguer
@app.callback(
    [Output('sidebar', 'style'),
     Output('overlay-btn', 'style'),
     Output('menu-state', 'data')],
    [Input('hamburger-btn', 'n_clicks'),
     Input('overlay-btn', 'n_clicks')],
    [State('menu-state', 'data')]
)
def toggle_menu(hamburger_clicks, overlay_clicks, menu_open):
    ctx = callback_context
    if not ctx.triggered:
        return {'left': '-250px'}, {'display': 'none'}, False
    
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger == 'hamburger-btn':
        new_state = not menu_open
    else:
        new_state = False
    
    if new_state:
        sidebar_style = {'left': '0px'}
        overlay_style = {'display': 'block', 'position': 'fixed', 'top': '0', 'left': '0', 
                        'width': '100%', 'height': '100%', 'background': 'rgba(0,0,0,0.5)', 
                        'border': 'none', 'cursor': 'pointer', 'zIndex': '998'}
    else:
        sidebar_style = {'left': '-250px'}
        overlay_style = {'display': 'none'}
    
    return sidebar_style, overlay_style, new_state

@app.callback(
    [Output('mapa-fisheye', 'figure'),
     Output('graph-detalhe', 'figure'),
     Output('texto-detalhe', 'children')],
    [Input('mapa-fisheye', 'hoverData')]
)
def update_all_viz(hoverData):
    dff = df_geo.copy()
    
    # 1. Definir Tamanho Base (Volume de Acidentes)
    # Normalizamos para que o tamanho base no mapa seja visível mas discreto
    tamanho_base = 5 + (dff['Acidentes'] / dff['Acidentes'].max() * 15)
    
    # 2. Lógica Fish Eye no Mapa Principal
    if hoverData:
        target_lat = hoverData['points'][0]['lat']
        target_lon = hoverData['points'][0]['lon']
        
        # Calcular distância euclidiana simples para o efeito de lente
        dist = np.sqrt((dff['Latitude'] - target_lat)**2 + (dff['Longitude'] - target_lon)**2)
        
        # Fator de ampliação Fish Eye: Exponencial inversa
        # Pontos muito próximos ao rato crescem até 4x o seu tamanho original
        multiplicador_lente = 1 + 3.5 * np.exp(-dist * 180)
        dff['tamanho_final'] = tamanho_base * multiplicador_lente
        
        zoom_lat, zoom_lon = target_lat, target_lon
        zoom_level = 16
        info = html.Div([
            html.B("Ponto Focado:", style={'color': '#008080'}),
            html.P(f"Coordenadas: {target_lat:.4f}, {target_lon:.4f}"),
            html.P(f"Volume Local: Alta Concentração")
        ])
    else:
        dff['tamanho_final'] = tamanho_base
        zoom_lat, zoom_lon = 38.72, -9.14
        zoom_level = 11
        info = "Passe o rato sobre os pontos para ativar a lente Fish Eye e o zoom de detalhe."

    # --- FIGURA PRINCIPAL (FISH EYE) ---
    fig_main = px.scatter_mapbox(
        dff, lat="Latitude", lon="Longitude", color="Natureza",
        size="tamanho_final", size_max=45,
        color_discrete_map={'Colisão': '#008080', 'Despiste': '#FF7F0E', 'Atropelamento': '#D62728'},
        zoom=12, center={"lat": 38.72, "lon": -9.14}
    )
    fig_main.update_layout(
        mapbox_style="carto-positron", 
        margin={"r":0,"t":0,"l":0,"b":0}, 
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        transition_duration=100 # Suaviza o crescimento dos pontos
    )

    # --- FIGURA DETALHE (ZOOM) ---
    fig_detalhe = px.scatter_mapbox(
        df_geo, lat="Latitude", lon="Longitude", color="Natureza",
        size="Acidentes", size_max=15,
        zoom=zoom_level, center={"lat": zoom_lat, "lon": zoom_lon}
    )
    fig_detalhe.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)

    return fig_main, fig_detalhe, info

if __name__ == '__main__':
    app.run(debug=True, port=8056)