import os
import unicodedata

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Datasets_Limpos")

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


def format_int_pt(value):
    return f"{int(value):,}".replace(",", " ")


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
    parquet_path = os.path.join(DATA_DIR, "acidentes_total.parquet")

    # Se já existir parquet → carregar imediatamente
    if os.path.exists(parquet_path):
        print("A carregar dados do ficheiro Parquet (otimizado)...")
        return pd.read_parquet(parquet_path)

    # Caso não exista parquet → ler Excel
    print("Parquet não encontrado, a ler ficheiros Excel...")
    possible_files = [
        os.path.join(DATA_DIR, f"Tabela_acidentes_{ano}_limpo.xlsx")
        for ano in range(2018, 2025)
    ]

    dfs = []
    for file in possible_files:
        if os.path.exists(file):
            try:
                df_local = pd.read_excel(file)

                digits = "".join(filter(str.isdigit, os.path.basename(file)))
                if len(digits) >= 4:
                    df_local["Ano"] = int(digits[:4])

                dfs.append(df_local)

            except Exception as e:
                print(f"Erro a ler {file}: {e}")
                continue

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # =======================================================
    # 1) Pré-calcular Mes_Num
    # =======================================================
    mes_col = find_column(df, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])
    if mes_col:
        df["Mes_Num"] = parse_mes_num(df[mes_col])
    else:
        df["Mes_Num"] = pd.NA

    # =======================================================
    # 2) Converter todas as colunas object misturadas → string
    #    (resolve TODOS os erros de Parquet)
    # =======================================================
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                df[col] = df[col].astype(str)
            except:
                df[col] = df[col].astype(str)

    # =======================================================
    # 3) Guardar parquet seguro
    # =======================================================
    try:
        df.to_parquet(parquet_path, index=False)
        print("Parquet criado com sucesso.")
    except Exception as e:
        print(f"Não foi possível guardar Parquet: {e}")

    return df


    # =======================================================
    # 1) PRÉ-CÁLCULO DE Mes_Num (acelera callbacks)
    # =======================================================
    mes_col = find_column(df, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])
    if mes_col:
        df["Mes_Num"] = parse_mes_num(df[mes_col])
    else:
        df["Mes_Num"] = pd.NA

    # =======================================================
    # 2) DETEÇÃO AUTOMÁTICA DE COLUNAS OBJECT MISTAS
    #    (resolver todos os erros "Expected bytes, got int")
    # =======================================================
    for col in df.columns:
        if df[col].dtype == "object":
            # Se tiver mistura (int + str + None), converter tudo para str
            try:
                # Tenta converter sem erro — se falhar, força string
                df[col].astype(str)
                df[col] = df[col].astype(str)
            except Exception:
                df[col] = df[col].astype(str)

    # =======================================================
    # 3) GRAVAR PARQUET SEM ERROS (PyArrow agora aceita tudo)
    # =======================================================
    df.to_parquet(parquet_file, index=False)

    return df


df_principal = load_data()
# ==============================================================================
# 4. PREPARAR COLUNAS REAIS
# ==============================================================================
mes_col = find_column(df_principal, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])

ligeiros_col = find_column(df_principal, ["# Veículos Ligeiros"])
pesados_col = find_column(df_principal, ["# Veículos Pesados"])
motos_col = find_column(df_principal, ["# Ciclomotores / Motociclos"])
outros_col = find_column(df_principal, ["# Outros Veículos"])

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

tipo_via_col = find_column(df_principal, ["Tipos Vias"])

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
# 5. ESTILOS - CONFIGURAÇÃO CENTRALIZADA
# ==============================================================================

# CORES PRINCIPAIS
TEXT_DARK = "#000000"
TEXT_MID = "#000000"
TEXT_LIGHT = "#9CA3AF"

BG = "#F4F6F8"
CARD_BG = "#FFFFFF"
BORDER = "#E5E7EB"

PRIMARY = "#000000"
SECONDARY = "#000000"
ACCENT = "#E74C3C"
WARNING = "#F9A825"
INFO = "#1565C0"
NEUTRAL = "#BDC3C7"

RODOVIARIA_PRIMARY = "#2B506E"
RODOVIARIA_SECONDARY = "#455A64"

YEAR_COLORS = {
    2018: "#8C8C8C",  # Cinza Médio Claro (Perfeita visibilidade no fundo branco)
    2019: "#7A7A7A",  # Cinza Mineral
    2020: "#696969",  # Cinza Dim (Cinza escuro intermédio)
    2021: "#595959",  # Cinza Técnico
    2022: "#4A4A4A",  # Cinza Carbono
    2023: "#3B3B3B",  # Cinza Antracite
    2024: "#2C2C2C",  # Cinza Escuro Profundo (Longe do preto total)
}
load_color = "#144B6E"



def color_for_year(year):
    if year in YEAR_COLORS:
        return YEAR_COLORS[year]
    if not anos_disponiveis:
        return PRIMARY
    idx = anos_disponiveis.index(year) if year in anos_disponiveis else 0
    return YEAR_COLORS[idx % len(YEAR_COLORS)]


# TIPOGRAFIA
FONT_FAMILY = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

FONT_SIZES = {
    "xs": "11px",
    "sm": "12px",
    "base": "13px",
    "md": "14px",
    "lg": "15px",
    "xl": "16px",
    "2xl": "18px",
    "3xl": "22px",
    "4xl": "28px",
    "5xl": "32px",
    "main_title": "32px",
    "main_subtitle": "24px",
    "graph_title": "20px",
    "axis": "14px",
    "menu_item": "14px",
    "menu_section": "11px",
    "button": "12px",
}

FONT_WEIGHTS = {
    "light": "300",
    "normal": "400",
    "medium": "500",
    "semibold": "600",
    "bold": "700",
}


def get_font_size(key):
    return FONT_SIZES.get(key, FONT_SIZES["base"])


def get_font_weight(key):
    return FONT_WEIGHTS.get(key, FONT_WEIGHTS["normal"])


def text_style(size_key="base", color=TEXT_DARK, weight_key="normal", extra=None):
    style = {
        "fontFamily": FONT_FAMILY,
        "fontSize": get_font_size(size_key),
        "color": color,
        "fontWeight": get_font_weight(weight_key),
    }
    if extra:
        style.update(extra)
    return style


def section_title_style():
    return text_style("graph_title", PRIMARY, "semibold", {"letterSpacing": "-0.2px", "margin": "0"})


def main_title_style():
    return text_style("main_title", PRIMARY, "bold", {"letterSpacing": "-0.5px", "margin": "0"})


def main_subtitle_style():
    return text_style("main_subtitle", TEXT_MID, "normal", {"margin": "4px 0 0 0"})


def card_style(padding="16px"):
    return {
        "background": CARD_BG,
        "borderRadius": "12px",
        "padding": padding,
        "boxShadow": "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.12)",
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
        "transition": "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "transform": "translateX(0)" if is_open else "translateX(-320px)",
        "fontFamily": FONT_FAMILY,
        "boxSizing": "border-box",
    }


def hamburger_style():
    return {
        "position": "fixed",
        "top": "12px",          # Reduzido de 16px para 12px (mais ajustado)
        "left": "12px",         # Reduzido de 16px para 12px
        "zIndex": "1001",
        "width": "36px",        # Reduzido de 48px para 36px (caixa menor)
        "height": "36px",       # Reduzido de 48px para 36px (caixa menor)
        "border": "none",
        "borderRadius": "8px",  # Reduzido de 12px para 8px para manter a proporção
        "background": "#333333",
        "color": "white",
        "fontSize": "16px",     # Reduzido de 20px para 16px (símbolo menor)
        "cursor": "pointer",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.2)",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }


def menu_item_text_style(active=False):
    return {
        "color": "#FFFFFF" if active else "rgba(255,255,255,0.7)",
        "fontSize": get_font_size("menu_item"),
        "fontWeight": get_font_weight("medium"),
        "fontFamily": FONT_FAMILY,
    }


def menu_section_text_style():
    return {
        "color": "rgba(255,255,255,0.4)",
        "fontSize": get_font_size("menu_section"),
        "fontWeight": get_font_weight("semibold"),
        "fontFamily": FONT_FAMILY,
        "letterSpacing": "1px",
        "margin": "20px 20px 12px 20px",
    }


def menu_item_style(active=False):
    base = menu_item_text_style(active)
    return {
        **base,
        "display": "block",
        "padding": "14px 18px",
        "borderRadius": "8px",
        "marginBottom": "4px",
        "background": "rgba(255,255,255,0.1)" if active else "transparent",
        "border": "none",
        "textDecoration": "none",
        "transition": "all 0.2s ease",
        "borderLeft": f"3px solid {ACCENT}" if active else "3px solid transparent"
    }


def dropdown_label_style():
    return {
        "fontSize": "12px",
        "display": "block",
        "marginBottom": "6px",
        "fontWeight": "700",
        "color": TEXT_MID,
        "fontFamily": FONT_FAMILY,
    }


def dropdown_style(width):
    return {
        "width": width,
        "color": TEXT_DARK,
        "fontSize": "13px",
        "fontFamily": FONT_FAMILY,
    }


def axis_font():
    return dict(
        size=int(get_font_size("axis").replace("px", "")),
        color=TEXT_MID,
        family=FONT_FAMILY
    )


def apply_common_figure_style(fig, height=300):
    fig.update_layout(
        template="plotly_white",
        height=height,
        separators=" ",
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(
            x=0.02,
            xanchor="left",
            font=dict(
                family=FONT_FAMILY,
                size=int(get_font_size("graph_title").replace("px", "")),
                color=PRIMARY,
            )
        ),
        font=dict(family=FONT_FAMILY, size=12, color=TEXT_DARK),
        showlegend=True
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER,
        tickfont=axis_font(),
        title_font=axis_font(),
        tickformat=" ",
        gridcolor="#ECF0F1",
    )
    fig.update_yaxes(
        gridcolor="#ECF0F1",
        zeroline=False,
        linecolor=BORDER,
        tickfont=axis_font(),
        tickformat=" ",
        title_font=axis_font(),
    )
    return fig


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

app.layout = html.Div([
    # Hamburger Button
    html.Button(
        html.Div([
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "marginBottom": "5px", "borderRadius": "1px"}),
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "marginBottom": "5px", "borderRadius": "1px"}),
            html.Div(style={"width": "20px", "height": "2px", "background": "white", "borderRadius": "1px"})
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"}),
        id="hamburger-btn",
        n_clicks=0,
        title="Abrir menu",
        style=hamburger_style()
    ),

    # Sidebar
    html.Div(
        id="sidebar-menu",
        children=[
            # Header da sidebar
            html.Div([
                html.Div([
                    html.Div(style={
                        "width": "40px",
                        "height": "40px",
                        "borderRadius": "10px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "marginRight": "12px"
                    }, children=[
                        html.Span("AR", style=text_style("md", "white", "bold"))
                    ]),
                    html.Div([
                        html.H2(
                            "Acidentes",
                            style=text_style("2xl", "#FFFFFF", "bold", {"margin": "0", "letterSpacing": "-0.3px"})
                        ),
                        html.P(
                            "Rodoviários Portugal",
                            style=text_style("sm", "rgba(255,255,255,0.6)", "normal", {"margin": "0"})
                        )
                    ])
                ], style={"display": "flex", "alignItems": "center"})
            ], style={
                "padding": "24px 20px",
                "borderBottom": "1px solid rgba(255,255,255,0.1)"
            }),

            # Menu items
            html.Div([
                html.P("DASHBOARDS", style=menu_section_text_style()),

                html.Div([
                    html.A(
                        "Dashboard Principal",
                        href="http://127.0.0.1:8050",
                        style=menu_item_style(active=False)
                    ),
                    html.A(
                        "Evolução Temporal",
                        href="http://127.0.0.1:8051",
                        style=menu_item_style(active=False)
                    ),
                    html.A(
                        "Comparação entre anos",
                        href="http://127.0.0.1:8052",
                        style=menu_item_style(active=True)
                    ),
                    html.A(
                        "Mapa de Portugal",
                        href="http://127.0.0.1:8056",
                        style=menu_item_style(active=False)
                    ),
                ], style={"padding": "0 12px"})
            ]),

            # Footer da sidebar
            html.Div([
                html.Div(
                    "Clique novamente no menu para fechar",
                    style=text_style("xs", "rgba(255,255,255,0.4)", "normal", {"lineHeight": "1.4", "textAlign": "center"})
                )
            ], style={
                "position": "absolute",
                "bottom": "0",
                "left": "0",
                "right": "0",
                "padding": "20px",
                "borderTop": "1px solid rgba(255,255,255,0.1)"
            })
        ],
        style=sidebar_style(False)
    ),

    # Conteúdo Principal
    html.Div([
        # Header
        html.Div([
            html.Div([
                # Bloco esquerda (vazio para equilibrar)
                html.Div(style={"width": "20%"}),

                # Título central
                html.Div([
                    html.H1(
                        "Análise Comparativa da Sinistralidade",
                        style=main_title_style()
                    ),
                    html.P(
                        "Comparação entre diferentes anos",
                        style=main_subtitle_style()
                    )
                ], style={
                    "width": "60%",
                    "textAlign": "center"
                }),
                        # Filtros à direita
                        # Filtros à direita (No Header)
            html.Div([
                html.Div([
                    html.Label("Anos", style=dropdown_label_style()),
                    dcc.Dropdown(
                        id="anos-selecionados",
                        options=[{"label": str(a), "value": a} for a in anos_disponiveis],
                        value=[ano_comp_default, ano_base_default],
                        multi=True,
                        clearable=True,
                        style=dropdown_style("200px")
                    )
                ], style={"marginRight": "12px"}),

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
                        style=dropdown_style("150px")
                    )
                ])
            ], style={
                "display": "flex", 
                "alignItems": "flex-end", 
                "paddingTop": "45px" # Ajusta conforme preferires
            })

            ], style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "marginBottom": "24px",
                "paddingTop": "8px",
                "width": "100%"
            }),
        ]),

        # Card do gráfico
        # Card do gráfico (Caixa Branca)
        html.Div([
            html.Div([
                # Título e Subtítulo à esquerda
                html.Div([
                    html.H3(id="titulo-comparacao", style=section_title_style()),
                    html.Div(id="subtitulo-comparacao", style={"marginTop": "4px", "color": TEXT_MID}),
                ]),
                
                # O Dropdown "Analisar por" aqui dentro!
                html.Div([
                    html.Label("Analisar dados por:", style=dropdown_label_style()),
                    dcc.Dropdown(
                        id="atributo-dinamico",
                        options=[
                            {"label": "Tipo de Veículo", "value": "Tipo_Veiculo"},
                            {"label": "Meteorologia", "value": "Meteorologia"},
                            {"label": "Natureza do acidente", "value": "Natureza"},
                            {"label": "Tipos de Vias", "value": "Tipo_Via"},
                        ],
                        value="Tipo_Veiculo",
                        clearable=False,
                        style=dropdown_style("200px")
                    )
                ])
            ], style={
                "display": "flex",
                "justifyContent": "space-between", # Empurra o título para a esquerda e o filtro para a direita
                "alignItems": "flex-start",
                "marginBottom": "20px"
            }),

            dcc.Loading(
                type='circle',
                delay_show=200,
                delay_hide=200,
                color=load_color,
                children=dcc.Graph(
                    id="graph-comparacao",
                    config={"displaylogo": False}
                )
            )
        ], style=card_style("20px"))

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
# 9. CALLBACK PRINCIPAL (CORES FIXAS E ORDEM CRONOLÓGICA)
# ==============================================================================
@app.callback(
    Output("graph-comparacao", "figure"),
    Output("titulo-comparacao", "children"),
    Output("subtitulo-comparacao", "children"),
    Input("anos-selecionados", "value"),
    Input("mes-filtro", "value"),
    Input("atributo-dinamico", "value")
)
def update_comparison(anos_selecionados, mes, atributo):

    atributo_labels = {
        "Tipo_Veiculo": "Tipo de Veículo",
        "Meteorologia": "Meteorologia",
        "Natureza": "Natureza",
        "Tipo_Via": "Tipos de Vias"
    }

    def make_empty_fig(message):
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            height=500,
            annotations=[
                dict(
                    text=message,
                    x=0.5, y=0.5,
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=16, color=TEXT_MID, family=FONT_FAMILY)
                )
            ],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(t=20, b=20, l=20, r=20)
        )
        return fig

    # Validar dados
    if df_principal.empty:
        return make_empty_fig("Sem dados disponíveis"), "", ""

    if not anos_selecionados:
        return make_empty_fig("Selecione pelo menos um ano para visualizar os dados"), "", ""

    dataframes = []

    # Filtrar e recolher dados
    for ano in anos_selecionados:
        dff = df_principal[df_principal["Ano"] == ano].copy()

        if mes != "Geral":
            dff = dff[dff["Mês"] == mes]

        data_temp = get_comparison_data(dff, atributo)

        if not data_temp.empty:
            data_temp["Ano"] = str(ano)
            dataframes.append(data_temp)

    if not dataframes:
        return make_empty_fig("Sem dados para este filtro"), "", ""

    data = pd.concat(dataframes, ignore_index=True)

    # Ordenar categorias alfabeticamente no eixo do gráfico
    total_order = sorted(data["Categoria"].unique())
    data["Categoria"] = pd.Categorical(
        data["Categoria"],
        categories=total_order,
        ordered=True
    )

    # 1. FORÇAR A ORDEM CRONOLÓGICA CRESCENTE NA LEGENDA (2018, 2019, 2020...)
    anos_cronologicos = [str(ano) for ano in sorted([int(a) for a in anos_selecionados])]

    # 2. MAPEAMENTO DE CORES FIXAS (Cada ano mantém sempre o seu tom de YEAR_COLORS)
    color_map = {str(ano): color_for_year(int(ano)) for ano in anos_selecionados}

    # Criar gráfico baseado no atributo
    if atributo in ["Natureza", "Tipo_Via"]:
        # Barras horizontais
        fig = px.bar(
            data,
            y="Categoria",
            x="Acidentes",
            color="Ano",
            orientation="h",
            barmode="group",
            color_discrete_map=color_map,
            category_orders={"Ano": anos_cronologicos} # Força ordem cronológica
        )

        apply_common_figure_style(fig, height=600)
        fig.update_layout(
            xaxis_title="Acidentes",
            yaxis_title="",
            legend_title="Ano",
            margin=dict(t=30, b=20, l=20, r=60),
        )
        fig.update_xaxes(showgrid=True, gridcolor="#ECF0F1", zeroline=False)
        fig.update_yaxes(showgrid=False)

    else:
        # Barras verticais
        fig = px.bar(
            data,
            x="Categoria",
            y="Acidentes",
            color="Ano",
            barmode="group",
            color_discrete_map=color_map,
            category_orders={"Ano": anos_cronologicos} # Força ordem cronológica
        )

        apply_common_figure_style(fig, height=520)
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Acidentes",
            legend_title="Ano",
            margin=dict(t=30, b=60, l=20, r=20),
        )
        fig.update_xaxes(showgrid=False, tickangle=20 if atributo == "Meteorologia" else 0)
        fig.update_yaxes(showgrid=True, gridcolor="#ECF0F1", zeroline=False)

    # GARANTIR QUE NÃO HÁ TEXTOS POR CIMA DAS BARRAS
    fig.update_traces(texttemplate=None, textposition="none")

    # Label do mês
    mes_label = (
        "Ano Inteiro"
        if mes == "Geral"
        else next(
            (MONTH_LABELS_FULL[i] for i in range(1, 13) if MONTH_LABELS_ABR[i] == mes),
            mes
        )
    )

    anos_texto = ", ".join(map(str, sorted([int(a) for a in anos_selecionados])))
    titulo = f"Comparação entre {anos_texto} - {atributo_labels.get(atributo)}"
    subtitulo = f"Filtro temporal: {mes_label}"

    return fig, titulo, subtitulo


# ==============================================================================
# 10. RUN
# ==============================================================================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=8052)
