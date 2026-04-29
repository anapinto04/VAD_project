import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ==============================================================================
# 1. DADOS
# ==============================================================================
app = dash.Dash(__name__)

# CSS inline para o menu hamburger
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Dashboard 3.2 - Análise Avançada</title>
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

def gerar_dados():
    np.random.seed(42)
    anos = [2022, 2023, 2024]
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    rows = []
    for _ in range(4000):
        rows.append({
            'Ano': np.random.choice(anos),
            'Mês': np.random.choice(meses),
            'Tipo_Veiculo': np.random.choice(['Ligeiro', 'Pesado', 'Motociclo']),
            'Meteorologia': np.random.choice(['Céu Limpo', 'Chuva', 'Nevoeiro']),
            'Natureza': np.random.choice(['Colisão', 'Despiste', 'Atropelamento']),
            'Tipo_Via': np.random.choice(['Autoestrada', 'Nacional', 'Urbana']),
            'Acidentes': np.random.randint(1, 5)
        })
    df = pd.DataFrame(rows)
    df['Mês'] = pd.Categorical(df['Mês'], categories=meses, ordered=True)
    return df

df_principal = gerar_dados()

OPCOES_ATRIB = [
    {'label': 'Tipo de Veículo (Barras)', 'value': 'Tipo_Veiculo'},
    {'label': 'Meteorologia (Donuts)', 'value': 'Meteorologia'},
    {'label': 'Natureza (Barras H)', 'value': 'Natureza'},
    {'label': 'Tipo de Via (Funil)', 'value': 'Tipo_Via'}
]

# ==============================================================================
# 2. LAYOUT
# ==============================================================================
app.layout = html.Div(style={'fontFamily': 'Segoe UI, sans-serif', 'backgroundColor': '#f4f7f7', 'padding': '20px'}, children=[
    
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
    
    # HEADER
    html.Div(style={
        'backgroundColor': '#008080', 'padding': '15px 30px', 'borderRadius': '12px', 
        'color': 'white', 'marginBottom': '20px', 'display': 'flex', 
        'justifyContent': 'space-between', 'alignItems': 'center'
    }, children=[
        html.H2("Dashboard de Sinistralidade Inteligente", style={'margin': '0', 'fontSize': '20px'}),
        
        html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
            html.Div([
                html.Label("Ano 1", style={'fontSize': '11px'}),
                dcc.Dropdown(id='ano-1', options=[{'label': str(a), 'value': a} for a in [2022, 2023, 2024]], value=2024, clearable=False, style={'width': '90px', 'color': 'black'})
            ]),
            html.Div([
                html.Label("Ano 2", style={'fontSize': '11px'}),
                dcc.Dropdown(id='ano-2', options=[{'label': str(a), 'value': a} for a in [2022, 2023, 2024]], value=2023, clearable=False, style={'width': '90px', 'color': 'black'})
            ]),
            html.Div([
                html.Label("Mês", style={'fontSize': '11px'}),
                dcc.Dropdown(id='mes-filtro', options=[{'label': 'Todos', 'value': 'Geral'}] + [{'label': m, 'value': m} for m in df_principal['Mês'].cat.categories], value='Geral', clearable=False, style={'width': '100px', 'color': 'black'})
            ])
        ])
    ]),

    # GRÁFICOS
    html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
        # LADO ESQUERDO
        html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '15px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.05)'}, children=[
            html.Label("Seletor A:", style={'fontWeight': 'bold', 'fontSize': '13px'}),
            dcc.Dropdown(id='atrib-1', options=OPCOES_ATRIB, value='Tipo_Veiculo', clearable=False, style={'marginBottom': '20px'}),
            dcc.Graph(id='graph-1')
        ]),
        
        # LADO DIREITO
        html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '15px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.05)'}, children=[
            html.Label("Seletor B:", style={'fontWeight': 'bold', 'fontSize': '13px'}),
            dcc.Dropdown(id='atrib-2', options=OPCOES_ATRIB, value='Meteorologia', clearable=False, style={'marginBottom': '20px'}),
            dcc.Graph(id='graph-2')
        ])
    ])
])

# ==============================================================================
# 3. CALLBACK
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
    [Output('graph-1', 'figure'), Output('graph-2', 'figure')],
    [Input('ano-1', 'value'), Input('ano-2', 'value'), 
     Input('mes-filtro', 'value'), 
     Input('atrib-1', 'value'), Input('atrib-2', 'value')]
)
def update_graphs(ano1, ano2, mes, atrib1, atrib2):
    
    def criar_figura_adaptativa(atributo):
        # Filtragem
        dff = df_principal[df_principal['Ano'].isin([ano1, ano2])]
        if mes != 'Geral':
            dff = dff[dff['Mês'] == mes]
        
        # Agrupamento base
        data = dff.groupby([atributo, 'Ano'])['Acidentes'].sum().reset_index()
        data['Ano'] = data['Ano'].astype(str)
        
        # --- LÓGICA DE VISUALIZAÇÃO ---
        
        if atributo == 'Tipo_Veiculo':
            # BARRAS AGRUPADAS VERTICAIS
            fig = px.bar(data, x=atributo, y='Acidentes', color='Ano', barmode='group',
                         color_discrete_map={str(ano1): '#008080', str(ano2): '#FF7F0E'})
            
        elif atributo == 'Meteorologia':
            # DONUTS LADO A LADO (Subplots)
            fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]],
                                subplot_titles=[str(ano1), str(ano2)])
            
            d1 = data[data['Ano'] == str(ano1)]
            d2 = data[data['Ano'] == str(ano2)]
            
            fig.add_trace(go.Pie(labels=d1[atributo], values=d1['Acidentes'], name=str(ano1), hole=.4), 1, 1)
            fig.add_trace(go.Pie(labels=d2[atributo], values=d2['Acidentes'], name=str(ano2), hole=.4), 1, 2)
            fig.update_traces(textinfo='percent')

        elif atributo == 'Natureza':
            # BARRAS AGRUPADAS HORIZONTAIS
            fig = px.bar(data, y=atributo, x='Acidentes', color='Ano', barmode='group', orientation='h',
                         color_discrete_map={str(ano1): '#008080', str(ano2): '#FF7F0E'})

        else: # Tipo_Via
            # FUNIL COMPARATIVO
            fig = px.funnel(data, y=atributo, x='Acidentes', color='Ano',
                            color_discrete_map={str(ano1): '#008080', str(ano2): '#FF7F0E'})

        fig.update_layout(
            margin=dict(t=50, b=20, l=20, r=20),
            height=400,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    return criar_figura_adaptativa(atrib1), criar_figura_adaptativa(atrib2)

if __name__ == '__main__':
    app.run(debug=True, port=8054)