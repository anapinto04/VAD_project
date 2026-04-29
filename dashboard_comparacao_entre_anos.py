import os
import unicodedata

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
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


# ==============================================================================
# 2. MESES
# ==============================================================================
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


# ==============================================================================
# 3. CARREGAR DADOS REAIS
# ==============================================================================
def load_data():
    possible_files = [
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2018_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2019_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2020_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2021_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2022_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2023_limpo.xlsx"),
        os.path.join(BASE_DIR, "Datasets_Limpos", "Tabela_acidentes_2024_limpo.xlsx"),
    ]

    dfs = []

    for file in possible_files:
        if not os.path.exists(file):
            continue

        try:
            df_local = pd.read_excel(file)
        except Exception as e:
            print(f"Erro ao ler {file}: {e}")
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


df_principal = load_data()


# ==============================================================================
# 4. PREPARAR COLUNAS REAIS
# ==============================================================================
mes_col = find_column(df_principal, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])

ligeiros_col = find_column(df_principal, [
    "# Veículos Ligeiros"
])

pesados_col = find_column(df_principal, [
    "# Veículos Pesados"
])


motos_col = find_column(df_principal, [
    "# Ciclomotores / Motociclos"
])

outros_col = find_column(df_principal, [
    "# Outros Veículos"
])

meteo_col = find_column(df_principal, [
    "Factores Atmosféricos",
    "Fatores Atmosféricos",
    "Meteorologia",
    "Condições Atmosféricas",
    "Condicoes Atmosfericas"
])

natureza_col = find_column(df_principal, [
    "Natureza",
    "Natureza do Acidente",
    "Tipo de Acidente"
])

tipo_via_col = find_column(df_principal, [
    "Tipos de Via",
])

if not df_principal.empty:
    if mes_col:
        df_principal["Mes_Num"] = parse_mes_num(df_principal[mes_col])
        df_principal["Mês"] = df_principal["Mes_Num"].map(MONTH_LABELS_ABR)
        df_principal["Mês"] = pd.Categorical(
            df_principal["Mês"],
            categories=MONTH_ORDER_ABR,
            ordered=True
        )
    else:
        df_principal["Mes_Num"] = pd.NA
        df_principal["Mês"] = pd.NA

    df_principal["Ano"] = pd.to_numeric(df_principal["Ano"], errors="coerce").astype("Int64")

    for col in [ligeiros_col, pesados_col, motos_col, outros_col]:
        if col:
            df_principal[col] = pd.to_numeric(df_principal[col], errors="coerce")


anos_disponiveis = (
    sorted(df_principal["Ano"].dropna().astype(int).unique().tolist())
    if not df_principal.empty and "Ano" in df_principal.columns
    else []
)

ano_base_default = max(anos_disponiveis) if anos_disponiveis else None
ano_comp_default = anos_disponiveis[-2] if len(anos_disponiveis) >= 2 else ano_base_default


# ==============================================================================
# 5. ESTILOS
# ==============================================================================
PRIMARY = "#153B6D"
TEXT_DARK = "#1C3252"
TEXT_MID = "#66758C"
BG = "#F3F6FB"
CARD_BG = "#FFFFFF"
BORDER = "#E1E8F0"

YEAR_COLORS = {
    2018: "#0072B2",
    2019: "#E69F00",
    2020: "#009E73",
    2021: "#D55E00",
    2022: "#CC79A7",
    2023: "#56B4E9",
    2024: "#000000",
}

FALLBACK_COLORS = [
    "#0072B2", "#E69F00", "#009E73", "#D55E00",
    "#CC79A7", "#56B4E9", "#000000", "#F0E442"
]


def color_for_year(year):
    if year in YEAR_COLORS:
        return YEAR_COLORS[year]

    if not anos_disponiveis:
        return PRIMARY

    idx = anos_disponiveis.index(year) if year in anos_disponiveis else 0
    return FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]


def card_style(padding="22px"):
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


def dropdown_label_style():
    return {
        "fontSize": "12px",
        "display": "block",
        "marginBottom": "6px",
        "fontWeight": "700",
        "color": TEXT_MID
    }


def dropdown_style(width):
    return {
        "width": width,
        "color": TEXT_DARK,
        "fontSize": "13px"
    }


# ==============================================================================
# 6. FUNÇÃO PARA AGREGAR DADOS
# ==============================================================================
def get_comparison_data(dff, atributo):
    if atributo == "Tipo_Veiculo":
        veiculos = []
        valores = []

        if ligeiros_col and ligeiros_col in dff.columns:
            veiculos.append("Veículos Ligeiros")
            valores.append(dff[ligeiros_col].fillna(0).sum())

        if pesados_col and pesados_col in dff.columns:
            veiculos.append("Veículos Pesados")
            valores.append(dff[pesados_col].fillna(0).sum())

        if motos_col and motos_col in dff.columns:
            veiculos.append("Ciclomotores/ Motociclos")
            valores.append(dff[motos_col].fillna(0).sum())

        if outros_col and outros_col in dff.columns:
            veiculos.append("Outros Veículos")
            valores.append(dff[outros_col].fillna(0).sum())

        return pd.DataFrame({
            "Categoria": veiculos,
            "Acidentes": valores
        })

    col_map = {
        "Meteorologia": meteo_col,
        "Natureza": natureza_col,
        "Tipo_Via": tipo_via_col
    }

    col = col_map.get(atributo)

    if col is None or col not in dff.columns:
        return pd.DataFrame(columns=["Categoria", "Acidentes"])

    data = (
        dff[col]
        .fillna("Sem informação")
        .astype(str)
        .replace({"nan": "Sem informação", "None": "Sem informação"})
        .value_counts()
        .reset_index()
    )

    data.columns = ["Categoria", "Acidentes"]

    return data


# ==============================================================================
# 7. APP
# ==============================================================================
app = dash.Dash(__name__)
app.title = "Análise Comparativa da Sinistralidade"

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

                html.A("Dashboard Principal", href="http://127.0.0.1:8050", style=menu_item_style()),
                html.A("Evolução Temporal", href="http://127.0.0.1:8051", style=menu_item_style()),
                html.A("Comparação entre anos", href="http://127.0.0.1:8052", style=menu_item_style(active=True)),

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
                        "marginBottom": "16px",
                        "gap": "20px"
                    },
                    children=[
                        html.Div([
                            html.H1(
                                "Análise Comparativa da Sinistralidade",
                                style={
                                    "margin": "0",
                                    "color": PRIMARY,
                                    "fontSize": "34px",
                                    "fontWeight": "800"
                                }
                            ),
                            html.P(
                                "Comparação entre anos por tipo de veículo, meteorologia, natureza ou tipo de via.",
                                style={
                                    "margin": "6px 0 0 0",
                                    "color": TEXT_MID,
                                    "fontSize": "14px"
                                }
                            )
                        ]),

                        html.Div(
                            style={
                                "display": "flex",
                                "gap": "14px",
                                "alignItems": "flex-end",
                                "flexWrap": "wrap",
                                "justifyContent": "flex-end"
                            },
                            children=[
                                html.Div([
                                    html.Label("Analisar por", style=dropdown_label_style()),
                                    dcc.Dropdown(
                                        id="atributo-dinamico",
                                        options=[
                                            {"label": "Tipo de Veículo", "value": "Tipo_Veiculo"},
                                            {"label": "Meteorologia", "value": "Meteorologia"},
                                            {"label": "Natureza do acidente", "value": "Natureza"},
                                            {"label": "Tipo de Via", "value": "Tipo_Via"},
                                        ],
                                        value="Tipo_Veiculo",
                                        clearable=False,
                                        style=dropdown_style("190px")
                                    )
                                ]),

                                html.Div([
                                    html.Label("Ano Base", style=dropdown_label_style()),
                                    dcc.Dropdown(
                                        id="ano-1",
                                        options=[{"label": str(a), "value": a} for a in anos_disponiveis],
                                        value=ano_base_default,
                                        clearable=False,
                                        style=dropdown_style("110px")
                                    )
                                ]),

                                html.Div([
                                    html.Label("Comparar", style=dropdown_label_style()),
                                    dcc.Dropdown(
                                        id="ano-2",
                                        options=[{"label": str(a), "value": a} for a in anos_disponiveis],
                                        value=ano_comp_default,
                                        clearable=False,
                                        style=dropdown_style("110px")
                                    )
                                ]),

                                html.Div([
                                    html.Label("Mês", style=dropdown_label_style()),
                                    dcc.Dropdown(
                                        id="mes-filtro",
                                        options=[{"label": "Todos", "value": "Geral"}] + [
                                            {"label": MONTH_LABELS_FULL[i], "value": MONTH_LABELS_ABR[i]}
                                            for i in range(1, 13)
                                        ],
                                        value="Geral",
                                        clearable=False,
                                        style=dropdown_style("160px")
                                    )
                                ])
                            ]
                        )
                    ]
                ),

                html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
                        "gap": "16px"
                    },
                    children=[
                        html.Div(
                            style={**card_style("20px")},
                            children=[
                                html.Div(id="tit-1", style={
                                    "textAlign": "center",
                                    "margin": "0 0 14px 0",
                                    "color": TEXT_DARK,
                                    "fontSize": "18px",
                                    "fontWeight": "800"
                                }),
                                html.Div(id="subtit-1", style={
                                    "textAlign": "center",
                                    "margin": "-8px 0 10px 0",
                                    "color": TEXT_MID,
                                    "fontSize": "13px"
                                }),
                                dcc.Graph(id="graph-1", config={"displaylogo": False})
                            ]
                        ),

                        html.Div(
                            style={**card_style("20px")},
                            children=[
                                html.Div(id="tit-2", style={
                                    "textAlign": "center",
                                    "margin": "0 0 14px 0",
                                    "color": TEXT_DARK,
                                    "fontSize": "18px",
                                    "fontWeight": "800"
                                }),
                                html.Div(id="subtit-2", style={
                                    "textAlign": "center",
                                    "margin": "-8px 0 10px 0",
                                    "color": TEXT_MID,
                                    "fontSize": "13px"
                                }),
                                dcc.Graph(id="graph-2", config={"displaylogo": False})
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)


# ==============================================================================
# 8. CALLBACK DO MENU
# ==============================================================================
@app.callback(
    Output("sidebar-menu", "style"),
    Input("hamburger-btn", "n_clicks")
)
def toggle_sidebar(n_clicks):
    is_open = bool(n_clicks and n_clicks % 2 == 1)
    return sidebar_style(is_open)


# ==============================================================================
# 9. CALLBACK PRINCIPAL
# ==============================================================================
@app.callback(
    Output("graph-1", "figure"),
    Output("tit-1", "children"),
    Output("subtit-1", "children"),
    Output("graph-2", "figure"),
    Output("tit-2", "children"),
    Output("subtit-2", "children"),
    Input("ano-1", "value"),
    Input("ano-2", "value"),
    Input("mes-filtro", "value"),
    Input("atributo-dinamico", "value")
)
def update_comparison(ano1, ano2, mes, atributo):
    atributo_labels = {
        "Tipo_Veiculo": "Tipo de Veículo",
        "Meteorologia": "Meteorologia",
        "Natureza": "Natureza",
        "Tipo_Via": "Tipo de Via"
    }

    def make_empty_fig(message):
        fig = px.scatter()
        fig.update_layout(
            template="plotly_white",
            height=420,
            annotations=[
                dict(
                    text=message,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=16, color=TEXT_MID)
                )
            ],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(t=20, b=20, l=20, r=20)
        )
        return fig

    def get_fig(ano):
        if df_principal.empty or ano is None:
            return make_empty_fig("Sem dados disponíveis")

        dff = df_principal[df_principal["Ano"] == ano].copy()

        if mes != "Geral":
            dff = dff[dff["Mês"] == mes]

        data = get_comparison_data(dff, atributo)

        if data.empty:
            return make_empty_fig("Sem dados para este filtro")

        data = data.sort_values("Acidentes", ascending=False)

        year_color = color_for_year(int(ano))

        if atributo == "Meteorologia":
            fig = px.pie(
                data,
                values="Acidentes",
                names="Categoria",
                hole=0.55,
                color_discrete_sequence=FALLBACK_COLORS
            )

            fig.update_traces(
                textinfo="percent+label",
                textfont_size=12,
                marker=dict(line=dict(color="white", width=2))
            )

            fig.update_layout(
                template="plotly_white",
                height=420,
                paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=True,
                font=dict(family="Arial, sans-serif", size=12, color=TEXT_DARK)
            )

            return fig

        if atributo in ["Natureza", "Tipo_Via"]:
            data = data.sort_values("Acidentes", ascending=True)

            fig = px.bar(
                data,
                y="Categoria",
                x="Acidentes",
                orientation="h",
                text="Acidentes",
                color_discrete_sequence=[year_color]
            )

            fig.update_traces(
                texttemplate="%{text}",
                textposition="outside",
                marker_line_width=0
            )

            fig.update_layout(
                template="plotly_white",
                height=420,
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis_title="Acidentes",
                yaxis_title="",
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=45),
                font=dict(family="Arial, sans-serif", size=12, color=TEXT_DARK)
            )

            fig.update_xaxes(showgrid=True, gridcolor="#EAEFF5", zeroline=False)
            fig.update_yaxes(showgrid=False)

            return fig

        fig = px.bar(
            data,
            x="Categoria",
            y="Acidentes",
            text="Acidentes",
            color_discrete_sequence=[year_color]
        )

        fig.update_traces(
            texttemplate="%{text}",
            textposition="outside",
            marker_line_width=0
        )

        fig.update_layout(
            template="plotly_white",
            height=420,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis_title="",
            yaxis_title="Acidentes",
            showlegend=False,
            margin=dict(t=20, b=20, l=20, r=35),
            font=dict(family="Arial, sans-serif", size=12, color=TEXT_DARK)
        )

        fig.update_xaxes(showgrid=False, tickangle=0)
        fig.update_yaxes(showgrid=True, gridcolor="#EAEFF5", zeroline=False)

        return fig

    fig1 = get_fig(ano1)
    fig2 = get_fig(ano2)

    mes_label = "Ano Inteiro" if mes == "Geral" else next(
        (MONTH_LABELS_FULL[i] for i in range(1, 13) if MONTH_LABELS_ABR[i] == mes),
        mes
    )

    tit1 = f"{ano1} - {atributo_labels.get(atributo, atributo)}"
    tit2 = f"{ano2} - {atributo_labels.get(atributo, atributo)}"

    subtit1 = f"Filtro temporal: {mes_label}"
    subtit2 = f"Filtro temporal: {mes_label}"

    return fig1, tit1, subtit1, fig2, tit2, subtit2


# ==============================================================================
# 10. RUN
# ==============================================================================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=8052)