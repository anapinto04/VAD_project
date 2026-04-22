import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ==============================================================================
# 1. GERAÇÃO DE DADOS SIMULADOS (Para demonstração)
# ==============================================================================
def gerar_dados_dashboard_temporal():
    np.random.seed(42)
    anos = [2022, 2023, 2024]
    meses = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
    dias_semana = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']
    
    rows = []
    for ano in anos:
        for mes in meses:
            for dia in dias_semana:
                for hora in range(24):
                    # Simulação de tendência: aumento em 2024 e picos à tarde
                    base = np.random.randint(2, 15)
                    if ano == 2024: base += 8
                    if dia in ['SEX', 'SAB']: base += 10
                    if 17 <= hora <= 20: base += 20 # Picos de final de dia
                    
                    rows.append({
                        'Ano': ano, 'Mês': mes, 'Dia_Semana': dia, 
                        'Hora': hora, 'Acidentes': base
                    })
    df = pd.DataFrame(rows)
    # Definir ordens categóricas para garantir que os gráficos não fiquem desordenados
    df['Mês'] = pd.Categorical(df['Mês'], categories=meses, ordered=True)
    df['Dia_Semana'] = pd.Categorical(df['Dia_Semana'], categories=dias_semana, ordered=True)
    return df

df_temp = gerar_dados_dashboard_temporal()

# ==============================================================================
# 2. INICIALIZAÇÃO DA APP
# ==============================================================================
app = dash.Dash(__name__)

app.layout = html.Div(style={'fontFamily': 'Segoe UI, sans-serif', 'backgroundColor': '#f4f7f7', 'padding': '25px'}, children=[
    
    # CABEÇALHO (Header)
    html.Div(style={
        'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '12px',
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '25px'
    }, children=[
        html.H2("Evolução Temporal da Sinistralidade", style={'margin': '0', 'color': '#008080'}),
        
        # O DROPDOWN MULTI (As boxes de "Add" anos que pediste)
        html.Div(style={'display': 'flex', 'alignItems': 'center'}, children=[
            html.Span("Anos em análise:", style={'marginRight': '15px', 'fontWeight': 'bold', 'color': '#555'}),
            dcc.Dropdown(
                id='multi-drop-anos',
                options=[{'label': str(a), 'value': a} for a in [2022, 2023, 2024]],
                value=[2022, 2023, 2024], # Começa com todos selecionados
                multi=True,               # Permite múltiplas boxes
                clearable=False,
                style={'minWidth': '300px'}
            )
        ])
    ]),

    # 1. GRÁFICO SUPERIOR: EVOLUÇÃO MENSAL (LINHAS)
    html.Div(style={
        'backgroundColor': 'white', 'padding': '25px', 'borderRadius': '15px', 
        'boxShadow': '0 2px 8px rgba(0,0,0,0.05)', 'marginBottom': '25px'
    }, children=[
        html.H4("Registos Mensais Acumulados", style={'marginTop': '0', 'color': '#666'}),
        dcc.Graph(id='graph-linhas-mensal')
    ]),

    # FILA INFERIOR (Dois gráficos)
    html.Div(style={'display': 'flex', 'gap': '25px'}, children=[
        
        # 2. ESQUERDA: BARRAS POR DIA (Com seletor de mês)
        html.Div(style={
            'flex': '1', 'backgroundColor': 'white', 'padding': '25px', 
            'borderRadius': '15px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.05)'
        }, children=[
            html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '15px'}, children=[
                html.H4("Distribuição Semanal", style={'margin': '0', 'color': '#666'}),
                dcc.Dropdown(
                    id='drop-mes-inferior',
                    options=[{'label': m, 'value': m} for m in df_temp['Mês'].cat.categories],
                    value='JAN', clearable=False, style={'width': '110px'}
                )
            ]),
            dcc.Graph(id='graph-barras-dias')
        ]),

        # 3. DIREITA: HEATMAP HORÁRIO
        html.Div(style={
            'flex': '1.5', 'backgroundColor': 'white', 'padding': '25px', 
            'borderRadius': '15px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.05)'
        }, children=[
            html.H4("Concentração por Hora e Dia (Média)", style={'marginTop': '0', 'color': '#666'}),
            dcc.Graph(id='graph-heatmap-horas')
        ])
    ])
])

# ==============================================================================
# 3. LÓGICA DE INTERATIVIDADE (CALLBACKS)
# ==============================================================================
@app.callback(
    [Output('graph-linhas-mensal', 'figure'),
     Output('graph-barras-dias', 'figure'),
     Output('graph-heatmap-horas', 'figure')],
    [Input('multi-drop-anos', 'value'),
     Input('drop-mes-inferior', 'value')]
)
def update_dashboard(anos_selecionados, mes_selecionado):
    
    # Filtragem por anos selecionados nas boxes
    df_filtered = df_temp[df_temp['Ano'].isin(anos_selecionados)]

    # --- FIGURA 1: LINHAS MENSAL ---
    df_l = df_filtered.groupby(['Ano', 'Mês'], observed=True)['Acidentes'].sum().reset_index()
    fig_l = px.line(
        df_l, x='Mês', y='Acidentes', color='Ano',
        markers=True, line_shape='linear',
        color_discrete_map={2022: '#999', 2023: '#444', 2024: '#008080'} # Teal para 2024
    )
    fig_l.update_layout(
        plot_bgcolor='white', xaxis_title=None, yaxis_title="Total Acidentes",
        margin=dict(t=10, b=10, l=10, r=10), hovermode='x unified'
    )
    fig_l.update_xaxes(showgrid=True, gridcolor='#f0f0f0')
    fig_l.update_yaxes(showgrid=True, gridcolor='#f0f0f0')

    # --- FIGURA 2: BARRAS SEMANAIS (Filtrado por mês) ---
    df_b = df_filtered[df_filtered['Mês'] == mes_selecionado]
    df_b_sum = df_b.groupby(['Ano', 'Dia_Semana'], observed=True)['Acidentes'].sum().reset_index()
    
    fig_b = px.bar(
        df_b_sum, x='Dia_Semana', y='Acidentes', color='Ano',
        barmode='group',
        color_discrete_map={2022: '#CCC', 2023: '#888', 2024: '#008080'}
    )
    fig_b.update_layout(
        plot_bgcolor='white', xaxis_title=None, showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10)
    )

    # --- FIGURA 3: HEATMAP ---
    # Pivotagem para Dia vs Hora
    df_h = df_filtered.pivot_table(
        index='Dia_Semana', columns='Hora', values='Acidentes', aggfunc='mean'
    )
    
    fig_h = go.Figure(data=go.Heatmap(
        z=df_h.values,
        x=df_h.columns,
        y=df_h.index,
        colorscale='Viridis', # Tons de roxo a amarelo
        showscale=True
    ))
    fig_h.update_layout(
        xaxis=dict(title='Hora do Dia', dtick=1),
        yaxis=dict(title=None, autorange='reversed'), # SEG no topo
        margin=dict(t=10, b=10, l=10, r=10)
    )

    return fig_l, fig_b, fig_h

# ==============================================================================
# 4. EXECUÇÃO
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True)