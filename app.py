'''from dash import Dash, html, dcc
from dash.dependencies import Input, Output

import plotly.graph_objects as go 
app = Dash(__name__) 

#Layout of the app
app.layout = html.Div([ 
    html.P("Color:"), 
    dcc.Dropdown( 
        id="dropdown", 
        options=[ 
            {'label': x, 'value': x} 
            for x in ['Gold', 'MediumTurquoise', 'LightGreen'] 
        ], 
        value='Gold', 
    ), 
    dcc.Graph(id="graph", figure=go.Figure()), 
]) 

#interacão
@app.callback( 
    Output("graph", "figure"), 
    [Input("dropdown", "value")]) 
def display_color(color): 
    print(color) 
    fig = go.Figure( 
        data=go.Bar(y=[2, 3, 1], marker_color=color)) 
    return fig 

if __name__ == "__main__":
    app.run(debug=True)
'''   
import dash
from dash import dcc, html, Input, Output, callback_context
import plotly.express as px
import pandas as pd

# 1. Dados Centrais (Configurações de Drill-down)
capitais = {
    'Lisboa': {'lat': 38.7223, 'lon': -9.1393, 'zoom': 11},
    'Porto': {'lat': 41.1579, 'lon': -8.6291, 'zoom': 11},
    'Coimbra': {'lat': 40.2033, 'lon': -8.4103, 'zoom': 12},
    'Faro': {'lat': 37.0176, 'lon': -7.9304, 'zoom': 12}
}

# Dados mock (simulados)
df_distritos = pd.DataFrame({'Nome': list(capitais.keys()), 'lat': [c['lat'] for c in capitais.values()], 'lon': [c['lon'] for c in capitais.values()]})
df_acidentes = pd.DataFrame({'Distrito': ['Lisboa', 'Porto'], 'lat': [38.72, 41.15], 'lon': [-9.14, -8.62], 'gravidade': ['Grave', 'Mortal']})

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Button("Reset Portugal", id="btn-reset", n_clicks=0),
    dcc.Graph(id='mapa-dinamico', style={'height': '85vh'})
])

@app.callback(
    Output('mapa-dinamico', 'figure'),
    [Input('mapa-dinamico', 'clickData'),
     Input('btn-reset', 'n_clicks')]
)
def update_map(clickData, n_clicks):
    ctx = callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # Valores padrão: Portugal Continental
    lat_c, lon_c, zoom_c = 39.5, -8.0, 6
    data_to_show = df_distritos
    is_detail_view = False

    # Lógica de Drill-down (Se o gatilho foi um clique no mapa)
    if trigger_id == 'mapa-dinamico' and clickData:
        try:
            # Tenta obter o nome do distrito de várias formas possíveis (text ou location)
            point = clickData['points'][0]
            nome_clicado = point.get('text') or point.get('location') or point.get('hovertext')
            
            if nome_clicado in capitais:
                config = capitais[nome_clicado]
                lat_c, lon_c, zoom_c = config['lat'], config['lon'], config['zoom']
                data_to_show = df_acidentes[df_acidentes['Distrito'] == nome_clicado]
                is_detail_view = True
        except Exception as e:
            print(f"Erro no processamento do clique: {e}")

    # Criar a figura final
    if not is_detail_view:
        # Nível 1: Visão por Áreas/Distritos
        fig = px.scatter_map(data_to_show, lat="lat", lon="lon", text="Nome", zoom=zoom_c, center={"lat": lat_c, "lon": lon_c})
        fig.update_traces(marker=dict(size=25, color="RoyalBlue", opacity=0.6))
    else:
        # Nível 2: Visão Detalhada de Acidentes
        fig = px.scatter_map(data_to_show, lat="lat", lon="lon", color="gravidade", zoom=zoom_c, center={"lat": lat_c, "lon": lon_c})
        fig.update_traces(marker=dict(size=12))

    fig.update_layout(map_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
    return fig

if __name__ == '__main__':
    app.run(debug=True)