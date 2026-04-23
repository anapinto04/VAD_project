import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ==============================================================================
# 1. DADOS
# ==============================================================================
app = dash.Dash(__name__)

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