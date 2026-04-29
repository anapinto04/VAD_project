import os
import unicodedata

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==============================================================================
# 1. FUNÇÕES AUXILIARES
# ==============================================================================
def normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.upper().split())


def find_column(df, possible_names):
    normalized_map = {normalize_text(col): col for col in df.columns}

    for name in possible_names:
        key = normalize_text(name)
        if key in normalized_map:
            return normalized_map[key]

    return None


def parse_mes_num(series):
    month_map = {
        "1": 1, "01": 1, "JANEIRO": 1, "JAN": 1,
        "2": 2, "02": 2, "FEVEREIRO": 2, "FEV": 2,
        "3": 3, "03": 3, "MARCO": 3, "MAR": 3,
        "4": 4, "04": 4, "ABRIL": 4, "ABR": 4,
        "5": 5, "05": 5, "MAIO": 5, "MAI": 5,
        "6": 6, "06": 6, "JUNHO": 6, "JUN": 6,
        "7": 7, "07": 7, "JULHO": 7, "JUL": 7,
        "8": 8, "08": 8, "AGOSTO": 8, "AGO": 8,
        "9": 9, "09": 9, "SETEMBRO": 9, "SET": 9,
        "10": 10, "OUTUBRO": 10, "OUT": 10,
        "11": 11, "NOVEMBRO": 11, "NOV": 11,
        "12": 12, "DEZEMBRO": 12, "DEZ": 12,
    }

    cleaned = series.astype(str).str.strip().map(normalize_text)
    parsed_text = cleaned.map(month_map)
    parsed_numeric = pd.to_numeric(cleaned, errors="coerce")

    return parsed_text.fillna(parsed_numeric).astype("Int64")


def parse_hora_para_numero(series):
    """
    Converte a coluna Hora para número inteiro 0-23.
    Funciona com valores tipo:
    - 14
    - 14:30
    - 14:30:00
    """
    numeric = pd.to_numeric(series, errors="coerce")

    if numeric.notna().sum() > 0:
        return numeric.astype("Int64")

    parsed = pd.to_datetime(series.astype(str).str.strip(), format="%H:%M:%S", errors="coerce")

    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(
            series.astype(str).str.strip().loc[missing],
            format="%H:%M",
            errors="coerce"
        )

    return parsed.dt.hour.astype("Int64")


def normalizar_dia_semana(series):
    day_map = {
        "SEGUNDA": "SEG",
        "SEGUNDA FEIRA": "SEG",
        "SEGUNDA-FEIRA": "SEG",
        "SEG": "SEG",

        "TERCA": "TER",
        "TERCA FEIRA": "TER",
        "TERCA-FEIRA": "TER",
        "TER": "TER",

        "QUARTA": "QUA",
        "QUARTA FEIRA": "QUA",
        "QUARTA-FEIRA": "QUA",
        "QUA": "QUA",

        "QUINTA": "QUI",
        "QUINTA FEIRA": "QUI",
        "QUINTA-FEIRA": "QUI",
        "QUI": "QUI",

        "SEXTA": "SEX",
        "SEXTA FEIRA": "SEX",
        "SEXTA-FEIRA": "SEX",
        "SEX": "SEX",

        "SABADO": "SAB",
        "SAB": "SAB",

        "DOMINGO": "DOM",
        "DOM": "DOM",
    }

    cleaned = series.astype(str).str.strip().map(normalize_text)
    return cleaned.map(day_map).fillna(cleaned)


MONTH_LABELS_ABR = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR",
    5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

MONTH_LABELS_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

MONTH_ORDER_ABR = list(MONTH_LABELS_ABR.values())

MONTH_ORDER = list(MONTH_LABELS_FULL.values())
DAY_ORDER = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]


# ==============================================================================
# 2. CARREGAR DADOS REAIS
# ==============================================================================
def load_data():
    possible_files = [
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2018_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2019_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2020_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2021_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2022_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2023_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2024_limpo.xlsx")
    ]

    dfs = []

    for file in possible_files:
        if not os.path.exists(file):
            continue

        try:
            df_local = pd.read_excel(file)
        except Exception:
            continue

        filename = os.path.basename(file)
        digits = "".join(filter(str.isdigit, filename))

        if len(digits) >= 4:
            df_local["Ano"] = int(digits[:4])

        dfs.append(df_local)

    if not dfs:
        print("Aviso: não foram encontrados ficheiros de acidentes.")
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


df_temp = load_data()


# ==============================================================================
# 3. PREPARAR COLUNAS REAIS
# ==============================================================================
mes_col = find_column(df_temp, ["Mês"])
dia_col = find_column(df_temp, [
    "Dia da Semana",
    "Dia Semana",
    "Dia_Semana",
    "Dia da semana",
    "Dia",
    "DiaSemana"
])
hora_col = find_column(df_temp, [
    "Hora",
    "Hora do Acidente",
    "Hora acidente",
    "Hora_Ocorrencia",
    "Hora Ocorrencia"
])

if not df_temp.empty:
    if mes_col:
        df_temp["Mes_Num"] = parse_mes_num(df_temp[mes_col])

        df_temp["Mês"] = df_temp["Mes_Num"].map(MONTH_LABELS_ABR)
        df_temp["Mês"] = pd.Categorical(
            df_temp["Mês"],
            categories=MONTH_ORDER_ABR,
            ordered=True
        )
    else:
        df_temp["Mes_Num"] = pd.NA
        df_temp["Mês"] = pd.NA

    if dia_col:
        df_temp["Dia_Semana"] = normalizar_dia_semana(df_temp[dia_col])
        df_temp["Dia_Semana"] = pd.Categorical(df_temp["Dia_Semana"], categories=DAY_ORDER, ordered=True)
    else:
        df_temp["Dia_Semana"] = pd.NA

    if hora_col:
        df_temp["Hora"] = parse_hora_para_numero(df_temp[hora_col])
    else:
        df_temp["Hora"] = pd.NA

    df_temp["Ano"] = pd.to_numeric(df_temp["Ano"], errors="coerce").astype("Int64")


anos_disponiveis = (
    sorted(df_temp["Ano"].dropna().astype(int).unique().tolist())
    if not df_temp.empty and "Ano" in df_temp.columns
    else []
)

valor_inicial_anos = anos_disponiveis


# ==============================================================================
# 4. ESTILOS
# ==============================================================================
PRIMARY = "#153B6D"
TEXT_DARK = "#1C3252"
TEXT_MID = "#66758C"
BG = "#F3F6FB"
CARD_BG = "#FFFFFF"
BORDER = "#E1E8F0"
TEAL = "#008080"

YEAR_COLORS = {
    2018: "#0072B2",  # azul
    2019: "#E69F00",  # laranja
    2020: "#009E73",  # verde
    2021: "#D55E00",  # vermelho escuro
    2022: "#CC79A7",  # rosa
    2023: "#56B4E9",  # azul claro
    2024: "#000000",  # preto (destaque)
}

category_orders={"Ano": sorted(YEAR_COLORS.keys())}

def card_style(padding="25px"):
    return {
        "backgroundColor": CARD_BG,
        "padding": padding,
        "borderRadius": "18px",
        "boxShadow": "0 2px 10px rgba(28,50,82,0.06)",
        "border": f"1px solid {BORDER}",
    }


def menu_item_style(active=False):
    return {
        "display": "block",
        "padding": "12px 14px",
        "borderRadius": "12px",
        "color": PRIMARY if active else TEXT_DARK,
        "fontSize": "14px",
        "fontWeight": "700" if active else "600",
        "marginBottom": "10px",
        "background": "#EAF1FB" if active else "#F7FAFE",
        "border": "1px solid #D7E3F1",
        "textDecoration": "none",
    }


def sidebar_style(is_open=False):
    return {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "width": "260px",
        "height": "100vh",
        "background": "#FFFFFF",
        "boxShadow": "2px 0 16px rgba(28,50,82,0.18)",
        "padding": "26px 20px",
        "zIndex": "999",
        "transition": "transform 0.3s ease",
        "transform": "translateX(0)" if is_open else "translateX(-320px)",
        "fontFamily": "Arial, sans-serif",
        "borderRight": f"1px solid {BORDER}",
        "boxSizing": "border-box",
    }


def hamburger_style():
    return {
        "position": "fixed",
        "top": "18px",
        "left": "20px",
        "zIndex": "1001",
        "width": "44px",
        "height": "44px",
        "border": "none",
        "borderRadius": "14px",
        "background": PRIMARY,
        "color": "white",
        "fontSize": "24px",
        "fontWeight": "700",
        "cursor": "pointer",
        "boxShadow": "0 4px 14px rgba(21,59,109,0.30)",
        "lineHeight": "1",
    }


# ==============================================================================
# 5. APP
# ==============================================================================
app = dash.Dash(__name__)
app.title = "Evolução Temporal da Sinistralidade"

app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "backgroundColor": BG,
        "padding": "18px 20px 24px 20px",
        "minHeight": "100vh"
    },
    children=[
        html.Button(
            "☰",
            id="hamburger-btn",
            n_clicks=0,
            title="Abrir menu",
            style=hamburger_style()
        ),

        html.Div(
            id="sidebar-menu",
            children=[
                html.H2(
                    "Menu",
                    style={
                        "margin": "0",
                        "color": PRIMARY,
                        "fontSize": "24px",
                        "fontWeight": "800"
                    }
                ),
                html.P(
                    "Dashboards",
                    style={
                        "margin": "4px 0 24px 0",
                        "color": TEXT_MID,
                        "fontSize": "13px"
                    }
                ),

                html.A("Mapa Principal", href="http://127.0.0.1:8050", style=menu_item_style()),
                html.A("Evolução Temporal", href="http://127.0.0.1:8051", style=menu_item_style(active=True)),
                html.A("Comparação entre anos", href="http://127.0.0.1:8052", style=menu_item_style()),
                


                
                html.Div(
                    "Clica novamente em ☰ para fechar o menu.",
                    style={
                        "position": "absolute",
                        "bottom": "28px",
                        "left": "20px",
                        "right": "20px",
                        "fontSize": "12px",
                        "color": TEXT_MID,
                        "lineHeight": "1.4"
                    }
                )
            ],
            style=sidebar_style(False)
        ),

        html.Div(
            style={
                "maxWidth": "1320px",
                "margin": "0 auto"
            },
            children=[
                html.Div(
                    style={
                        **card_style("20px"),
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginBottom": "16px"
                    },
                    children=[
                        html.H1(
                            "Evolução Temporal da Sinistralidade",
                            style={
                                "margin": "0",
                                "color": PRIMARY,
                                "fontSize": "34px",
                                "fontWeight": "800"
                            }
                        ),

                        html.Div(
                            style={"display": "flex", "alignItems": "center"},
                            children=[
                                html.Span(
                                    "Anos em análise:",
                                    style={
                                        "marginRight": "15px",
                                        "fontWeight": "700",
                                        "color": TEXT_MID,
                                        "fontSize": "14px"
                                    }
                                ),
                                dcc.Dropdown(
                                    id="multi-drop-anos",
                                    options=[
                                        {"label": str(a), "value": a}
                                        for a in anos_disponiveis
                                    ],
                                    value=valor_inicial_anos,
                                    multi=True,
                                    clearable=False,
                                    style={"minWidth": "300px"}
                                )
                            ]
                        )
                    ]
                ),

                html.Div(
                    style={**card_style("25px"), "marginBottom": "16px"},
                    children=[
                        html.H3(
                            "Registos Mensais Acumulados",
                            style={
                                "margin": "0 0 14px 0",
                                "color": PRIMARY,
                                "fontSize": "18px",
                                "fontWeight": "700"
                            }
                        ),
                        dcc.Graph(
                            id="graph-linhas-mensal",
                            config={"displaylogo": False}
                        )
                    ]
                ),

                html.Div(
                    style={
                        "display": "flex",
                        "gap": "16px",
                        "alignItems": "stretch"
                    },
                    children=[
                        html.Div(
                            style={**card_style("25px"), "flex": "1"},
                            children=[
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "justifyContent": "space-between",
                                        "alignItems": "center",
                                        "marginBottom": "15px"
                                    },
                                    children=[
                                        html.H3(
                                            "Distribuição Semanal",
                                            style={
                                                "margin": "0",
                                                "color": PRIMARY,
                                                "fontSize": "18px",
                                                "fontWeight": "700"
                                            }
                                        ),
                                    dcc.Dropdown( #mês para filtrar o gráfico de barras
                                        id="drop-mes-inferior",
                                        options=[
                                            {"label": MONTH_LABELS_FULL[i], "value": MONTH_LABELS_ABR[i]}
                                            for i in range(1, 13)
                                        ],
                                        value="JAN",
                                        clearable=False,
                                        style={"width": "160px"}
                                    )
                                    ]
                                ),
                                dcc.Graph(
                                    id="graph-barras-dias",
                                    config={"displaylogo": False}
                                )
                            ]
                        ),

                        html.Div(
                            style={**card_style("25px"), "flex": "1.5"},
                            children=[
                                html.H3(
                                    "Número de Acidentes por Hora e Dia",
                                    style={
                                        "margin": "0 0 14px 0",
                                        "color": PRIMARY,
                                        "fontSize": "18px",
                                        "fontWeight": "700"
                                    }
                                ),
                                dcc.Graph(
                                    id="graph-heatmap-horas",
                                    config={"displaylogo": False}
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)


# ==============================================================================
# 6. CALLBACK DO MENU
# ==============================================================================
@app.callback(
    Output("sidebar-menu", "style"),
    Input("hamburger-btn", "n_clicks")
)
def toggle_sidebar(n_clicks):
    is_open = bool(n_clicks and n_clicks % 2 == 1)
    return sidebar_style(is_open)


# ==============================================================================
# 7. CALLBACK DOS GRÁFICOS
# ==============================================================================
@app.callback(
    Output("graph-linhas-mensal", "figure"),
    Output("graph-barras-dias", "figure"),
    Output("graph-heatmap-horas", "figure"),
    Input("multi-drop-anos", "value"),
    Input("drop-mes-inferior", "value")
)
def update_dashboard(anos_selecionados, mes_selecionado):
    if df_temp.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Sem dados disponíveis",
            height=360
        )
        return empty_fig, empty_fig, empty_fig

    if not anos_selecionados:
        anos_selecionados = anos_disponiveis

    df_filtered = df_temp[df_temp["Ano"].isin(anos_selecionados)].copy()

    # --------------------------------------------------------------------------
    # Gráfico 1: Evolução mensal real
    # --------------------------------------------------------------------------
    df_l = (
        df_filtered
        .dropna(subset=["Mês"])
        .groupby(["Ano", "Mês"], observed=True)
        .size()
        .reset_index(name="Acidentes")
    )

    fig_l = px.line(
        df_l,
        x="Mês",
        y="Acidentes",
        color="Ano",
        markers=True,
        line_shape="linear",
        color_discrete_map=YEAR_COLORS
    )

    fig_l.update_traces(
        line=dict(width=2.5),
        marker=dict(size=7)
    )

    fig_l.update_layout(
        template="plotly_white",
        height=360,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="",
        yaxis_title="Total de Acidentes",
        margin=dict(t=10, b=20, l=20, r=20),
        hovermode="x unified",
        legend_title_text="Ano",
        font=dict(family="Arial, sans-serif", size=12, color=TEXT_DARK),
        xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER)
    )

    fig_l.update_xaxes(showgrid=False)
    fig_l.update_yaxes(showgrid=True, gridcolor="#EAEFF5", zeroline=False)

    # --------------------------------------------------------------------------
    # Gráfico 2: Distribuição semanal real
    # --------------------------------------------------------------------------
    df_b = df_filtered[df_filtered["Mês"] == mes_selecionado].copy()

    df_b_sum = (
        df_b
        .dropna(subset=["Dia_Semana"])
        .groupby(["Ano", "Dia_Semana"], observed=True)
        .size()
        .reset_index(name="Acidentes")
    )

    fig_b = px.bar(
        df_b_sum,
        x="Dia_Semana",
        y="Acidentes",
        color="Ano",
        barmode="group",
        color_discrete_map=YEAR_COLORS,
        category_orders={"Ano": sorted(YEAR_COLORS.keys())}
    )
    
    fig_b.update_layout(
        template="plotly_white",
        height=360,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="",
        yaxis_title="Acidentes",
        showlegend=False,
        margin=dict(t=10, b=20, l=20, r=20),
        font=dict(family="Arial, sans-serif", size=12, color=TEXT_DARK),
        xaxis=dict(categoryorder="array", categoryarray=DAY_ORDER)
    )

    fig_b.update_xaxes(showgrid=False)
    fig_b.update_yaxes(showgrid=True, gridcolor="#EAEFF5", zeroline=False)

    # --------------------------------------------------------------------------
    # Gráfico 3: Heatmap real Hora x Dia da Semana
    # --------------------------------------------------------------------------

    df_heat = df_filtered[
        df_filtered["Mês"] == mes_selecionado
    ].dropna(subset=["Dia_Semana", "Hora"]).copy()

    df_h = df_heat.pivot_table(
        index="Dia_Semana",
        columns="Hora",
        values="Ano",
        aggfunc="count",
        observed=True,
        fill_value=0
    )

    df_h = df_h.reindex(index=DAY_ORDER)
    df_h = df_h.reindex(columns=list(range(24)), fill_value=0)

    fig_h = go.Figure(
        data=go.Heatmap(
            z=df_h.values,
            x=df_h.columns,
            y=df_h.index,
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Acidentes")
        )
    )

    fig_h.update_layout(
        template="plotly_white",
        height=360,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title="Hora do Dia", dtick=1),
        yaxis=dict(title="", autorange="reversed"),
        margin=dict(t=10, b=20, l=20, r=20),
        font=dict(family="Arial, sans-serif", size=12, color=TEXT_DARK)
    )

    return fig_l, fig_b, fig_h


# ==============================================================================
# 8. RUN
# ==============================================================================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=8051)