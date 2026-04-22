import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import numpy as np

# ==============================================================================
# 1. DADOS (Simulação completa)
# ==============================================================================
app = dash.Dash(__name__)

def gerar_dados():
    np.random.seed(42)
    anos = [2022, 2023, 2024]
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    rows = []
    for _ in range(2500):
        rows.append({
            'Ano': np.random.choice(anos),
            'Mês': np.random.choice(meses),
            'Tipo_Veiculo': np.random.choice(['Ligeiro', 'Pesado', 'Motociclo']),
            'Meteorologia': np.random.choice(['Céu Limpo', 'Chuva', 'Nevoeiro']),
            'Natureza': np.random.choice(['Colisão', 'Despiste', 'Atropelamento']),
            'Tipo_Via': np.random.choice(['Autoestrada', 'Estrada Nacional', 'Via Urbana']),
            'Acidentes': np.random.randint(1, 5)
        })
    df = pd.DataFrame(rows)
    df['Mês'] = pd.Categorical(df['Mês'], categories=meses, ordered=True)
    return df

df_principal = gerar_dados()

# ==============================================================================
# 2. LAYOUT
# ==============================================================================
app.layout = html.Div(style={'fontFamily': 'Segoe UI, sans-serif', 'backgroundColor': '#f8f9f9', 'padding': '20px'}, children=[
    
    # CABEÇALHO (Agora com os 4 filtros juntos)
    html.Div(style={
        'backgroundColor': '#008080', 'padding': '15px 30px', 'borderRadius': '12px', 
        'color': 'white', 'marginBottom': '25px', 'display': 'flex', 
        'justifyContent': 'space-between', 'alignItems': 'center',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
    }, children=[
        html.H2("Dashboard de Sinistralidade", style={'margin': '0', 'fontSize': '22px'}),
        
        html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
            # SELETOR DE ATRIBUTO (Agora como Dropdown dentro da box)
            html.Div([
                html.Label("Analisar por", style={'fontSize': '11px', 'display': 'block', 'marginBottom': '5px'}),
                dcc.Dropdown(
                    id='atributo-dinamico',
                    options=[
                        {'label': 'Tipo de Veículo', 'value': 'Tipo_Veiculo'},
                        {'label': 'Meteorologia', 'value': 'Meteorologia'},
                        {'label': 'Natureza', 'value': 'Natureza'},
                        {'label': 'Tipo de Via', 'value': 'Tipo_Via'}
                    ],
                    value='Tipo_Veiculo',
                    clearable=False,
                    style={'width': '180px', 'color': 'black'}
                )
            ]),
            # Ano Base
            html.Div([
                html.Label("Ano Base", style={'fontSize': '11px', 'display': 'block', 'marginBottom': '5px'}),
                dcc.Dropdown(id='ano-1', options=[{'label': str(a), 'value': a} for a in [2022, 2023, 2024]], value=2024, clearable=False, style={'width': '100px', 'color': 'black'})
            ]),
            # Ano Comparação
            html.Div([
                html.Label("Comparar", style={'fontSize': '11px', 'display': 'block', 'marginBottom': '5px'}),
                dcc.Dropdown(id='ano-2', options=[{'label': str(a), 'value': a} for a in [2022, 2023, 2024]], value=2023, clearable=False, style={'width': '100px', 'color': 'black'})
            ]),
            # Mês
            html.Div([
                html.Label("Mês", style={'fontSize': '11px', 'display': 'block', 'marginBottom': '5px'}),
                dcc.Dropdown(id='mes-filtro', options=[{'label': 'Todos', 'value': 'Geral'}] + [{'label': m, 'value': m} for m in df_principal['Mês'].cat.categories], value='Geral', clearable=False, style={'width': '110px', 'color': 'black'})
            ])
        ])
    ]),

    # ÁREA DOS GRÁFICOS
    html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
        # Painel Ano 1
        html.Div(style={
            'flex': '1', 'backgroundColor': 'white', 'padding': '20px', 
            'borderRadius': '15px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
            'borderTop': '4px solid #008080'
        }, children=[
            html.H4(id='tit-1', style={'textAlign': 'center', 'margin': '0 0 15px 0', 'color': '#008080'}),
            dcc.Graph(id='graph-1', config={'displayModeBar': False})
        ]),
        
        # Painel Ano 2
        html.Div(style={
            'flex': '1', 'backgroundColor': 'white', 'padding': '20px', 
            'borderRadius': '15px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
            'borderTop': '4px solid #FF7F0E'
        }, children=[
            html.H4(id='tit-2', style={'textAlign': 'center', 'margin': '0 0 15px 0', 'color': '#FF7F0E'}),
            dcc.Graph(id='graph-2', config={'displayModeBar': False})
        ])
    ])
])

# ==============================================================================
# 3. CALLBACK
# ==============================================================================
@app.callback(
    [Output('graph-1', 'figure'), Output('tit-1', 'children'),
     Output('graph-2', 'figure'), Output('tit-2', 'children')],
    [Input('ano-1', 'value'), Input('ano-2', 'value'), 
     Input('mes-filtro', 'value'), Input('atributo-dinamico', 'value')]
)
def update_comparison(ano1, ano2, mes, atributo):
    
    def get_fig(ano, cor_principal):
        dff = df_principal[df_principal['Ano'] == ano]
        if mes != 'Geral':
            dff = dff[dff['Mês'] == mes]
        
        data = dff.groupby(atributo)['Acidentes'].sum().reset_index()
        
        # Lógica Adaptativa
        if atributo == 'Tipo_Veiculo':
            fig = px.bar(data, x=atributo, y='Acidentes', color_discrete_sequence=[cor_principal], template='plotly_white')
        elif atributo == 'Meteorologia':
            fig = px.pie(data, values='Acidentes', names=atributo, hole=0.5, color_discrete_sequence=px.colors.qualitative.T10)
            fig.update_traces(textinfo='percent+label')
        elif atributo == 'Natureza':
            fig = px.bar(data, y=atributo, x='Acidentes', orientation='h', color_discrete_sequence=[cor_principal], template='plotly_white')
        else: # Tipo_Via
            fig = px.funnel(data.sort_values('Acidentes', ascending=False), y=atributo, x='Acidentes', color_discrete_sequence=[cor_principal])
            
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400, xaxis_title=None, yaxis_title=None, showlegend=(atributo == 'Meteorologia'))
        return fig

    fig1 = get_fig(ano1, '#008080')
    fig2 = get_fig(ano2, '#FF7F0E')
    
    label_tempo = f" ({mes})" if mes != 'Geral' else " (Ano Inteiro)"
    return fig1, f"Registos de {ano1}{label_tempo}", fig2, f"Registos de {ano2}{label_tempo}"

if __name__ == '__main__':
    app.run(debug=True)