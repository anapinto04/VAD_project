import os
import unicodedata

import dash
from dash import dcc, html, Input, Output, callback_context
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
    numeric = pd.to_numeric(series, errors="coerce")

    if numeric.notna().sum() > 0:
        return numeric.astype("Int64")

    parsed = pd.to_datetime(
        series.astype(str).str.strip(),
        format="%H:%M:%S",
        errors="coerce"
    )

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
# 2. CARREGAR DADOS
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
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


df_temp = load_data()

# ==============================================================================
# 3. NORMALIZAÇÃO
# ==============================================================================
mes_col = find_column(df_temp, ["Mês"])

dia_col = find_column(df_temp, [
    "Dia da Semana",
    "Dia Semana",
    "Dia_Semana",
    "Dia da semana",
    "Dia",
])

hora_col = find_column(df_temp, [
    "Hora",
    "Hora do Acidente",
    "Hora acidente",
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

    if dia_col:
        df_temp["Dia_Semana"] = normalizar_dia_semana(df_temp[dia_col])

        df_temp["Dia_Semana"] = pd.Categorical(
            df_temp["Dia_Semana"],
            categories=DAY_ORDER,
            ordered=True
        )

    if hora_col:
        df_temp["Hora"] = parse_hora_para_numero(df_temp[hora_col])

    df_temp["Ano"] = pd.to_numeric(
        df_temp["Ano"],
        errors="coerce"
    ).astype("Int64")

anos_disponiveis = sorted(
    df_temp["Ano"].dropna().astype(int).unique().tolist()
)

# ==============================================================================
# 4. ESTILOS
# ==============================================================================
TEXT_DARK = "#000000"
TEXT_MID = "#000000"
TEXT_LIGHT = "#9CA3AF"

BG = "#F4F6F8"
CARD_BG = "#FFFFFF"
BORDER = "#E5E7EB"

PRIMARY = "#000000"
ACCENT = "#E74C3C"

FONT_FAMILY = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

YEAR_COLORS = {
    2018: "#D1D5DB",  # Cinza muito claro (Referência distante)
    2019: "#9CA3AF",  # Cinza claro
    2020: "#6B7280",  # Cinza médio
    2021: "#4B5563",  # Cinza escuro
    2022: "#374151",  # Antracite
    2023: "#111827",  # Preto profundo
    2024: "#E74C3C",  # O Vermelho Accent (Destaque total para o ano atual)
}

GAP = 16


def card_style(padding="16px"):
    return {
        "background": CARD_BG,
        "borderRadius": "12px",
        "padding": padding,
        "boxShadow": "0 1px 3px rgba(0,0,0,0.08)",
        "border": f"1px solid {BORDER}",
    }


def sidebar_style(is_open=False):
    return {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "width": "280px",
        "height": "100vh",
        "background": PRIMARY,
        "boxShadow": "4px 0 20px rgba(0,0,0,0.15)",
        "padding": "0",
        "zIndex": "999",
        "transition": "transform 0.3s ease",
        "transform": "translateX(0)" if is_open else "translateX(-320px)",
        "fontFamily": FONT_FAMILY,
    }


def hamburger_style():
    return {
        "position": "fixed",
        "top": "16px",
        "left": "16px",
        "zIndex": "1001",
        "width": "48px",
        "height": "48px",
        "border": "none",
        "borderRadius": "12px",
        "background": "#333333",
        "color": "white",
        "fontSize": "20px",
        "cursor": "pointer",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.3)",
    }


def menu_item_style(active=False):
    return {
        "display": "block",
        "padding": "14px 18px",
        "borderRadius": "8px",
        "marginBottom": "4px",
        "background": "rgba(255,255,255,0.1)" if active else "transparent",
        "color": "#FFFFFF" if active else "rgba(255,255,255,0.7)",
        "textDecoration": "none",
        "fontSize": "14px",
        "fontWeight": "600",
        "borderLeft": f"3px solid {ACCENT}" if active else "3px solid transparent"
    }


def section_title_style():
    return {
        "fontSize": "20px",
        "fontWeight": "600",
        "color": PRIMARY,
        "margin": "0"
    }


def main_title_style():
    return {
        "fontSize": "32px",
        "fontWeight": "700",
        "color": PRIMARY,
        "margin": "0"
    }


def main_subtitle_style():
    return {
        "fontSize": "16px",
        "color": "#6B7280",
        "margin": "4px 0 0 0"
    }


def apply_common_figure_style(fig, height=300):

    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(
            family=FONT_FAMILY,
            size=12,
            color=TEXT_DARK
        )
    )

    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER
    )

    fig.update_yaxes(
        gridcolor="#ECF0F1",
        zeroline=False,
        linecolor=BORDER
    )

    return fig

# ==============================================================================
# 5. APP
# ==============================================================================
app = dash.Dash(__name__)
app.title = "Evolução Temporal"

app.layout = html.Div([

    html.Button(
        "☰",
        id="hamburger-btn",
        n_clicks=0,
        style=hamburger_style()
    ),

    # ==========================================================================
    # SIDEBAR
    # ==========================================================================
    html.Div(
        id="sidebar-menu",
        children=[

            html.Div([
                html.H2(
                    "Acidentes",
                    style={
                        "color": "white",
                        "margin": "0"
                    }
                ),

                html.P(
                    "Rodoviários Portugal",
                    style={
                        "color": "rgba(255,255,255,0.6)",
                        "margin": "0"
                    }
                )
            ], style={
                "padding": "24px 20px",
                "borderBottom": "1px solid rgba(255,255,255,0.1)"
            }),

            html.Div([
                html.A(
                    "Dashboard Principal",
                    href="http://127.0.0.1:8050",
                    style=menu_item_style()
                ),

                html.A(
                    "Evolução Temporal",
                    href="http://127.0.0.1:8051",
                    style=menu_item_style(active=True)
                ),

                html.A(
                    "Comparação entre anos",
                    href="http://127.0.0.1:8052",
                    style=menu_item_style()
                ),

            ], style={"padding": "20px 12px"})

        ],
        style=sidebar_style(False)
    ),

    # ==========================================================================
    # CONTEÚDO
    # ==========================================================================
    html.Div([

        # HEADER
        html.Div([

            html.H1(
                "Evolução Temporal da Sinistralidade",
                style=main_title_style()
            ),

            html.P(
                "Análise temporal dos acidentes rodoviários",
                style=main_subtitle_style()
            )

        ], style={
            "textAlign": "center",
            "marginBottom": "24px"
        }),

        # DROPDOWN
        html.Div([

            dcc.Dropdown(
                id="multi-drop-anos",
                options=[
                    {"label": str(a), "value": a}
                    for a in anos_disponiveis
                ],
                value=anos_disponiveis,
                multi=True,
                clearable=False
            )

        ], style={
            **card_style(),
            "marginBottom": "20px"
        }),

        # GRÁFICO LINHAS
        html.Div([

            html.H3(
                "Registos Mensais Acumulados",
                style=section_title_style()
            ),

            dcc.Loading(
                type="circle",
                color=ACCENT,
                children=dcc.Graph(
                    id="graph-linhas-mensal"
                )
            )

        ], style={
            **card_style(),
            "marginBottom": "20px"
        }),

        # BOTTOM
        html.Div([

            # BARRAS
            html.Div([

                html.Div([

                    html.H3(
                        "Distribuição Semanal",
                        style=section_title_style()
                    ),

                    dcc.Dropdown(
                        id="drop-mes-inferior",
                        options=[
                            {
                                "label": MONTH_LABELS_FULL[i],
                                "value": MONTH_LABELS_ABR[i]
                            }
                            for i in range(1, 13)
                        ],
                        value="JAN",
                        clearable=False,
                        style={"width": "180px"}
                    )

                ], style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "12px"
                }),

                dcc.Loading(
                    type="circle",
                    color=ACCENT,
                    children=dcc.Graph(
                        id="graph-barras-dias"
                    )
                )

            ], style={
                **card_style(),
                "width": "40%"
            }),

            # HEATMAP
            html.Div([

                html.H3(
                    "Número de Acidentes por Hora e Dia",
                    style=section_title_style()
                ),

                dcc.Loading(
                    type="circle",
                    color=ACCENT,
                    children=dcc.Graph(
                        id="graph-heatmap-horas"
                    )
                )

            ], style={
                **card_style(),
                "width": "60%"
            })

        ], style={
            "display": "flex",
            "gap": f"{GAP}px"
        })

    ], style={
        "maxWidth": "1400px",
        "margin": "0 auto"
    })

], style={
    "padding": "20px 24px 32px 24px",
    "backgroundColor": BG,
    "fontFamily": FONT_FAMILY,
    "minHeight": "100vh"
})

# ==============================================================================
# 6. CALLBACK SIDEBAR
# ==============================================================================
@app.callback(
    Output("sidebar-menu", "style"),
    Input("hamburger-btn", "n_clicks")
)
def toggle_sidebar(n_clicks):

    is_open = bool(n_clicks and n_clicks % 2 == 1)

    return sidebar_style(is_open)

# ==========================================================================
# 7. CALLBACK GRÁFICOS (AJUSTADO PARA BARRAS EMPILHADAS)
# ==========================================================================
@app.callback(
    Output("graph-linhas-mensal", "figure"),
    Output("graph-barras-dias", "figure"),
    Output("graph-heatmap-horas", "figure"),
    Input("multi-drop-anos", "value"),
    Input("drop-mes-inferior", "value")
)
def update_dashboard(anos_selecionados, mes_selecionado):

    if not anos_selecionados:
        anos_selecionados = anos_disponiveis

    df_filtered = df_temp[
        df_temp["Ano"].isin(anos_selecionados)
    ].copy()

    # --- GRÁFICO DE LINHAS ---
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
        color_discrete_map=YEAR_COLORS
    )
    apply_common_figure_style(fig_l, 360)

    # --- GRÁFICO DE BARRAS EMPILHADAS (STACKED) ---
    df_b = df_filtered[df_filtered["Mês"] == mes_selecionado].copy()

    df_b_sum = (
        df_b
        .dropna(subset=["Dia_Semana"])
        .groupby(["Ano", "Dia_Semana"], observed=True)
        .size()
        .reset_index(name="Acidentes")
    )

    # Converter Ano para string para garantir cores discretas e legenda correta
    df_b_sum["Ano"] = df_b_sum["Ano"].astype(str)

    fig_b = px.bar(
        df_b_sum,
        x="Dia_Semana",
        y="Acidentes",
        color="Ano",
        barmode="stack",  # ALTERADO: de 'group' para 'stack'
        color_discrete_map={str(k): v for k, v in YEAR_COLORS.items()},
        category_orders={
            "Ano": [str(a) for a in sorted(YEAR_COLORS.keys())],
            "Dia_Semana": DAY_ORDER
        }
    )

    apply_common_figure_style(fig_b, 360)

    # Ajustar legenda das barras para ser vertical à direita (como as linhas)
    fig_b.update_layout(
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02
        )
    )

    # --- HEATMAP ---
    df_heat = df_filtered[
        df_filtered["Mês"] == mes_selecionado
    ].dropna(subset=["Dia_Semana", "Hora"])

    df_h = df_heat.pivot_table(
        index="Dia_Semana",
        columns="Hora",
        values="Ano",
        aggfunc="count",
        fill_value=0,
        observed=True
    )

    df_h = df_h.reindex(index=DAY_ORDER)
    df_h = df_h.reindex(columns=list(range(24)), fill_value=0)

    fig_h = go.Figure(
        data=go.Heatmap(
            z=df_h.values,
            x=df_h.columns,
            y=df_h.index,
            colorscale="Reds"
        )
    )
    apply_common_figure_style(fig_h, 360)

    return fig_l, fig_b, fig_h

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    app.run(debug=True, port=8051)