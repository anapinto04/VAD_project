import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# Dados fictícios
dados_distritos = {
    "Coimbra": {"vitimas": 12, "acidentes": 40, "natureza": "Colisão"},
    "Porto": {"vitimas": 8, "acidentes": 35, "natureza": "Atropelamento"},
    "Lisboa": {"vitimas": 45, "acidentes": 61, "natureza": "Despiste"}
}

# Estilo para as caixas de texto ficarem iguais aos gráficos
estilo_caixa_texto = {
    "height": "80x", 
    "display": "flex", 
    "flexDirection": "column", 
    "justifyContent": "center", 
    "alignItems": "center",
    "textAlign": "center"
}

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Acidentes Rodoviários em Portugal", className="text-center my-3"))),

    # LINHA DE KPIs
    dbc.Row([
        # 1. Vítimas (Gráfico)
        dbc.Col(dbc.Card(dbc.CardBody([
            dcc.Graph(id='kpi-vitimas-totais', config={'displayModeBar': False})
        ], style={'padding': '0px'}), className="shadow-sm"), width=3),
        
        # 2. Acidentes (Gráfico)
        dbc.Col(dbc.Card(dbc.CardBody([
            dcc.Graph(id='kpi-acidentes-graves', config={'displayModeBar': False})
        ], style={'padding': '0px'}), className="shadow-sm"), width=3),
        
        # 3. Distrito Crítico (Texto)
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Distrito Crítico", className="text-muted mb-1", style={'fontSize': '13px'}),
            html.H3(id="res-distrito", className="mb-0", style={'color': '#2c3e50', 'fontWeight': 'bold'})
        ], style=estilo_caixa_texto), className="shadow-sm"), width=3),
        
        # 4. Natureza (Texto)
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Natureza Principal", className="text-muted mb-1", style={'fontSize': '13px'}),
            html.H3(id="res-natureza", className="mb-0", style={'color': '#2c3e50', 'fontWeight': 'bold'})
        ], style=estilo_caixa_texto), className="shadow-sm"), width=3),
    ], className="g-2 mb-4"),

    # Seletor
    dbc.Row(dbc.Col(dcc.Dropdown(
        id='mapa-portugal',
        options=[{'label': k, 'value': k} for k in dados_distritos.keys()],
        value='Lisboa',
        clearable=False,
        style={'width': '200px', 'margin': '0 auto'}
    )))
], fluid=True)

# CALLBACK ÚNICO PARA AS 4 BOXES
@app.callback(
    [Output('kpi-vitimas-totais', 'figure'),
     Output('kpi-acidentes-graves', 'figure'),
     Output('res-distrito', 'children'),
     Output('res-natureza', 'children')],
    [Input('mapa-portugal', 'value')]
)
def atualizar_dashboard(distrito_selecionado):
    info = dados_distritos.get(distrito_selecionado, dados_distritos["Lisboa"])
    
    # Layout dos gráficos
    layout_kpi = dict(
        height=80,
        margin=dict(t=40, b=10, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # Figuras Plotly
    fig_v = go.Figure(go.Indicator(
        mode="number+delta", value=info['vitimas'],
        title={"text": f"Vítimas: {distrito_selecionado}", "font": {"size": 13}},
        number={'font': {'size': 35, 'color': "#e74c3c"}},
        delta={'reference': info['vitimas'] - 2}
    )).update_layout(layout_kpi)

    fig_a = go.Figure(go.Indicator(
        mode="number+delta", value=info['acidentes'],
        title={"text": f"Acidentes: {distrito_selecionado}", "font": {"size": 13}},
        number={'font': {'size': 35, 'color': "#2c3e50"}},
        delta={'reference': info['acidentes'] + 5}
    )).update_layout(layout_kpi)

    # Retorna os 4 outputs na ordem correta
    return fig_v, fig_a, distrito_selecionado, info['natureza']

if __name__ == '__main__':
    app.run(debug=True, port=8057)