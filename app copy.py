import json
import glob
import os
import unicodedata

import pandas as pd
import pyproj
from dash import Dash, html, dcc, Input, Output, callback_context
import plotly.express as px
import plotly.graph_objects as go
from shapely.geometry import shape, mapping
from shapely.ops import transform


# =========================
# 1. FUNÇÕES AUXILIARES
# =========================
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
        "1": 1, "01": 1,"JANEIRO": 1, "JAN": 1,
        "2": 2, "02": 2,"FEVEREIRO": 2, "FEV": 2,
        "3": 3, "03": 3,"MARCO": 3, "MAR": 3,
        "4": 4, "04": 4,"ABRIL": 4, "ABR": 4,
        "5": 5, "05": 5,"MAIO": 5, "MAI": 5,
        "6": 6, "06": 6,"JUNHO": 6, "JUN": 6,
        "7": 7, "07": 7,"JULHO": 7, "JUL": 7,
        "8": 8, "08": 8,"AGOSTO": 8, "AGO": 8,
        "9": 9, "09": 9,"SETEMBRO": 9, "SET": 9,
        "10": 10, "OUTUBRO": 10, "OUT": 10,
        "11": 11, "NOVEMBRO": 11, "NOV": 11,
        "12": 12, "DEZEMBRO": 12, "DEZ": 12,
    }

    cleaned = series.astype(str).str.strip().map(normalize_text)
    parsed_text = cleaned.map(month_map)
    parsed_numeric = pd.to_numeric(cleaned, errors="coerce")
    return parsed_text.fillna(parsed_numeric).astype("Int64")


def parse_hora(series):
    cleaned = series.astype(str).str.strip()
    parsed = pd.to_datetime(cleaned, format="%H:%M:%S", errors="coerce")

    missing_mask = parsed.isna()
    if missing_mask.any():
        parsed.loc[missing_mask] = pd.to_datetime(
            cleaned.loc[missing_mask],
            format="%H:%M",
            errors="coerce"
        )

    return parsed


MONTH_LABELS = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

MONTH_ORDER = list(MONTH_LABELS.values())


def aggregate_by_month(dataframe, month_column, value_column=None, output_column="Total"):
    month_numbers = parse_mes_num(dataframe[month_column])
    valid_mask = month_numbers.notna()

    if not valid_mask.any():
        return pd.DataFrame({
            "Mês": pd.Categorical(MONTH_ORDER, categories=MONTH_ORDER, ordered=True),
            output_column: [0] * 12,
        })

    month_numbers = month_numbers.loc[valid_mask].astype(int)
    filtered = dataframe.loc[valid_mask]

    if value_column is None:
        grouped = filtered.groupby(month_numbers).size()
    else:
        grouped = filtered.groupby(month_numbers)[value_column].sum()

    grouped = grouped.reindex(range(1, 13), fill_value=0)
    result = grouped.rename(output_column).reset_index()
    result.columns = ["Mes_Ordem", output_column]
    result["Mês"] = result["Mes_Ordem"].map(MONTH_LABELS)
    result["Mês"] = pd.Categorical(result["Mês"], categories=MONTH_ORDER, ordered=True)

    return result[["Mês", output_column]]


# =========================
# 2. CARREGAR DADOS
# =========================
def load_data():
    clean_files = sorted(glob.glob("Datasets_Limpos/*.xlsx"))
    original_files = sorted(glob.glob("Datasets originais/*.xlsx"))
    data_files = sorted(glob.glob("data/*.xlsx"))

    if clean_files:
        search_files = clean_files
    elif original_files:
        search_files = original_files
    else:
        search_files = []

    search_files.extend(data_files)
    files = sorted(set(search_files))

    cache_dir = ".cache"
    cache_data_path = os.path.join(cache_dir, "accidents_cache.parquet")
    cache_meta_path = os.path.join(cache_dir, "accidents_cache_meta.json")

    source_state = {
        os.path.normpath(path): os.path.getmtime(path)
        for path in files
        if os.path.exists(path)
    }

    if os.path.exists(cache_data_path) and os.path.exists(cache_meta_path):
        try:
            with open(cache_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            cached_state = meta.get("source_state", {})

            if cached_state == source_state:
                return pd.read_parquet(cache_data_path)
        except Exception:
            pass

    dfs = []
    for file in files:
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

    combined = pd.concat(dfs, ignore_index=True)

    try:
        os.makedirs(cache_dir, exist_ok=True)
        combined.to_parquet(cache_data_path, index=False)
        with open(cache_meta_path, "w", encoding="utf-8") as f:
            json.dump({"source_state": source_state}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return combined


def load_geojson_portugal():
    possible_files = [
        "ContinenteDistritos.geojson",
        "data/ContinenteDistritos.geojson"
    ]

    geojson_path = None
    for path in possible_files:
        if os.path.exists(path):
            geojson_path = path
            break

    if geojson_path is None:
        return None

    with open(geojson_path, encoding="utf-8-sig") as f:
        geojson_data = json.load(f)

    transformer = pyproj.Transformer.from_crs(
        "EPSG:3763", "EPSG:4326", always_xy=True
    ).transform

    for feature in geojson_data.get("features", []):
        try:
            geom = shape(feature["geometry"])
            feature["geometry"] = mapping(transform(transformer, geom))
        except Exception:
            continue

        distrito = feature.get("properties", {}).get("Distrito", "")
        feature.setdefault("properties", {})["DistritoNorm"] = normalize_text(distrito)

    return geojson_data


df = load_data()
geojson_portugal = load_geojson_portugal()


# =========================
# 3. NORMALIZAÇÃO / LIMPEZA
# =========================
if df.empty:
    print("Aviso: não foi encontrado nenhum ficheiro Excel válido.")

mes_col = find_column(df, ["Mês", "Mes", "Mês do Ano", "Mes do Ano"])
hora_col = find_column(df, ["Hora"])
distrito_col = find_column(df, ["Distrito"])
natureza_col = find_column(df, ["Natureza"])
meteo_col = find_column(df, ["Factores Atmosféricos", "Fatores Atmosféricos", "Meteorologia"])
lat_col = find_column(df, ["Latitude GPS", "Latitude"])
lon_col = find_column(df, ["Longitude GPS", "Longitude"])

mortais_col = find_column(df, ["Vítimas mortais 30 dias", "Vitimas mortais 30 dias"])
graves_col = find_column(df, ["Feridos graves 30 dias"])
leves_col = find_column(df, ["Feridos leves 30 dias"])

ligeiros_col = find_column(df, [
    "Nº de Ligeiros", "No de Ligeiros", "Num Ligeiros",
    "Num veículos ligeiros", "Num veiculos ligeiros"
])

pesados_col = find_column(df, [
    "Nº de Pesados", "No de Pesados", "Num Pesados",
    "Num veículos pesados", "Num veiculos pesados"
])

motos_col = find_column(df, [
    "Nº de Motociclos",
    "No de Motociclos",
    "Num Motociclos",
    "Num veículos de duas rodas",
    "Num veiculos de duas rodas",
    "Num ciclomotores/motociclos",
    "Num ciclomotores e motociclos",
    "Num ciclomotores",
])

outros_col = find_column(df, [
    "Num outros veículos",
    "Num outros veiculos",
    "Nº de Outros",
    "No de Outros",
    "Num Outros",
])

if hora_col:
    df[hora_col] = parse_hora(df[hora_col])

if distrito_col:
    df[distrito_col] = df[distrito_col].astype(str)
    df["DistritoNorm"] = df[distrito_col].map(normalize_text)
else:
    df["DistritoNorm"] = None

for col in [
    mortais_col, graves_col, leves_col, lat_col, lon_col,
    ligeiros_col, pesados_col, motos_col, outros_col
]:
    if col:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if mortais_col and graves_col and leves_col:
    df["Vitimas_Totais"] = (
        df[mortais_col].fillna(0) +
        df[graves_col].fillna(0) +
        df[leves_col].fillna(0)
    )
else:
    df["Vitimas_Totais"] = 0

if mortais_col or graves_col:
    mortais_series = df[mortais_col].fillna(0) if mortais_col else 0
    graves_series = df[graves_col].fillna(0) if graves_col else 0
    df["Acidente_Grave"] = ((mortais_series > 0) | (graves_series > 0)).astype(int)
else:
    df["Acidente_Grave"] = 0


# =========================
# 4. COORDENADAS DAS CAPITAIS
# =========================
coords_capitais = {
    "AVEIRO": {"lat": 40.6405, "lon": -8.6538},
    "BEJA": {"lat": 38.0151, "lon": -7.8632},
    "BRAGA": {"lat": 41.5503, "lon": -8.4201},
    "BRAGANCA": {"lat": 41.8058, "lon": -6.7572},
    "CASTELO BRANCO": {"lat": 39.8222, "lon": -7.4909},
    "COIMBRA": {"lat": 40.2033, "lon": -8.4103},
    "EVORA": {"lat": 38.5714, "lon": -7.9135},
    "FARO": {"lat": 37.0176, "lon": -7.9304},
    "GUARDA": {"lat": 40.5365, "lon": -7.2684},
    "LEIRIA": {"lat": 39.7436, "lon": -8.8071},
    "LISBOA": {"lat": 38.7223, "lon": -9.1393},
    "PORTALEGRE": {"lat": 39.2938, "lon": -7.4285},
    "PORTO": {"lat": 41.1579, "lon": -8.6291},
    "SANTAREM": {"lat": 39.2361, "lon": -8.6850},
    "SETUBAL": {"lat": 38.5244, "lon": -8.8931},
    "VIANA DO CASTELO": {"lat": 41.6932, "lon": -8.8329},
    "VILA REAL": {"lat": 41.3010, "lon": -7.7422},
    "VISEU": {"lat": 40.6566, "lon": -7.9125}
}

PORTUGAL_BOUNDS = {
    "west": -9.6,
    "east": -6.0,
    "south": 36.8,
    "north": 42.3,
}


# =========================
# 5. FUNÇÃO DO MAPA
# =========================
def build_map_figure(dff, selected_district):
    # Sem distrito selecionado: mostra mapa coroplético por distrito.
    if selected_district is None or geojson_portugal is None:
        if "DistritoNorm" in dff.columns and distrito_col:
            mapa_df = (
                dff.groupby(["DistritoNorm", distrito_col])
                .size()
                .reset_index(name="Acidentes")
            )

            fig = px.choropleth_mapbox(
                mapa_df,
                geojson=geojson_portugal,
                locations="DistritoNorm",
                featureidkey="properties.DistritoNorm",
                color="Acidentes",
                hover_name=distrito_col,
                hover_data={"DistritoNorm": False, "Acidentes": True},
                color_continuous_scale="Reds",
                center={"lat": 39.5, "lon": -8.0},
                zoom=-0.9,
                opacity=0.7
            )

            fig.update_layout(
                mapbox_style="carto-positron",
                mapbox={"bounds": PORTUGAL_BOUNDS},
                margin={"r": 0, "t": 10, "l": 0, "b": 0}
            )
            return fig

        fig = go.Figure()
        fig.update_layout(
            mapbox={"bounds": PORTUGAL_BOUNDS},
            margin={"r": 0, "t": 10, "l": 0, "b": 0}
        )
        return fig

    # Com distrito selecionado: filtra acidentes desse distrito com coordenadas válidas.
    if lat_col and lon_col and "DistritoNorm" in dff.columns:
        df_filtrado = dff[
            (dff["DistritoNorm"] == selected_district) &
            dff[lat_col].notna() &
            dff[lon_col].notna()
        ].copy()
    else:
        df_filtrado = pd.DataFrame()

    if df_filtrado.empty:
        fig = go.Figure()
        fig.update_layout(margin={"r": 0, "t": 10, "l": 0, "b": 0})
        return fig

    # Classificação de gravidade para colorir os pontos no mapa.
    if mortais_col and graves_col:
        df_filtrado["gravidade"] = "Ligeiro"
        df_filtrado.loc[df_filtrado[graves_col].fillna(0) > 0, "gravidade"] = "Grave"
        df_filtrado.loc[df_filtrado[mortais_col].fillna(0) > 0, "gravidade"] = "Mortal"
    else:
        df_filtrado["gravidade"] = "Acidente"

    coord = coords_capitais.get(selected_district, {"lat": 39.5, "lon": -8.0})
    selected_boundary = None
    if geojson_portugal is not None:
        for feature in geojson_portugal.get("features", []):
            props = feature.get("properties", {})
            feature_district = props.get("DistritoNorm") or normalize_text(props.get("Distrito", ""))
            if feature_district == selected_district:
                # Usa o centroide do polígono para centrar o mapa no distrito clicado.
                try:
                    district_geom = shape(feature.get("geometry"))
                    centroid = district_geom.centroid
                    if centroid and centroid.is_valid:
                        coord = {"lat": centroid.y, "lon": centroid.x}
                except Exception:
                    pass

                selected_boundary = {
                    "type": "FeatureCollection",
                    "features": [feature]
                }
                break

    # Cada ponto representa um registo de acidente no distrito selecionado.
    fig = px.scatter_mapbox(
        df_filtrado,
        lat=lat_col,
        lon=lon_col,
        color="gravidade",
        hover_name=natureza_col if natureza_col else None,
        hover_data={lat_col: False, lon_col: False},
        color_discrete_map={
            "Mortal": "black",
            "Grave": "red",
            "Ligeiro": "orange",
            "Acidente": "blue"
        },
        zoom=8,
        center=coord
    )

    fig.update_traces(marker=dict(size=9))
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox={"bounds": PORTUGAL_BOUNDS},
        margin={"r": 0, "t": 10, "l": 0, "b": 0}
    )

    if selected_boundary is not None:
        fig.update_layout(
            mapbox_layers=[
                {
                    "sourcetype": "geojson",
                    "source": selected_boundary,
                    "type": "line",
                    "color": "#b1afaf",
                    "line": {"width": 2}
                }
            ]
        )

    return fig


# =========================
# 6. FUNÇÃO ESTILO KPI
# =========================
def kpi_style():
    return {
        "background": "white",
        "borderRadius": "14px",
        "padding": "18px",
        "textAlign": "center",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"
    }


def format_int_pt(value):
    return f"{int(value):,}".replace(",", ".")


def kpi_prev_label(prev_val):
    if prev_val is None:
        return html.Span("Ano anterior: N/A", style={"fontSize": "11px", "color": "#888"})
    return html.Span(
        f"Ano anterior: {format_int_pt(prev_val)}",
        style={"fontSize": "11px", "color": "#888"}
    )


def kpi_pct_badge(current, previous, lower_is_better=True):
    if previous is None or previous == 0:
        return html.Span("Sem base", style={"fontSize": "12px", "color": "#888", "fontWeight": "bold"})

    pct = (current - previous) / previous * 100
    is_improvement = (pct < 0 and lower_is_better) or (pct > 0 and not lower_is_better)
    color = "#2e7d32" if is_improvement else "#c62828"
    arrow = "▼" if pct < 0 else "▲"
    return html.Span(
        f"{arrow} {abs(pct):.1f}%",
        style={"fontSize": "12px", "color": color, "fontWeight": "bold"}
    )


# =========================
# 7. APP DASH
# =========================
app = Dash(__name__)
app.title = "Acidentes Rodoviários em Portugal"

anos_disponiveis = sorted(df["Ano"].dropna().unique()) if "Ano" in df.columns else []

app.layout = html.Div([
    dcc.Store(id="selected-district", data=None),

    html.H1(
        "Acidentes Rodoviários em Portugal",
        style={"textAlign": "center", "marginBottom": "16px"}
    ),

    html.Div([
        html.Div([
            html.Label("Selecionar Ano:"),
            dcc.Dropdown(
                id="year-filter",
                options=[{"label": str(y), "value": y} for y in anos_disponiveis],
                value=anos_disponiveis[-1] if anos_disponiveis else None,
                clearable=False
            )
        ], style={"width": "250px"})
    ], style={
        "display": "flex",
        "alignItems": "end",
        "marginBottom": "20px"
    }),

    html.Div([
        html.Div(id="kpi-vitimas", className="kpi-card"),
        html.Div(id="kpi-graves", className="kpi-card"),
        html.Div(id="kpi-distrito", className="kpi-card"),
        html.Div(id="kpi-natureza", className="kpi-card"),
    ], style={
        "display": "grid",
        "gridTemplateColumns": "repeat(4, 1fr)",
        "gap": "15px",
        "marginBottom": "20px"
    }),

    html.Div([
        html.Div([
            html.Div([
                html.Div(
                    id="mapa-titulo",
                    style={
                        "margin": "0",
                        "color": "#2b4a74",
                        "fontSize": "22px",
                        "fontWeight": "600"
                    }
                ),
                html.Button(
                    "Limpar seleção do mapa",
                    id="btn-reset",
                    n_clicks=0,
                    style={
                        "padding": "8px 12px",
                        "border": "1px solid #cfcfcf",
                        "borderRadius": "8px",
                        "background": "#f7f9fc",
                        "color": "#1f2a44",
                        "cursor": "pointer",
                        "fontSize": "14px",
                        "fontWeight": "600"
                    }
                )
            ], style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "8px",
                "gap": "12px"
            }),

            dcc.Graph(
                id="mapa-distritos",
                style={"height": "620px"},
                config={"displaylogo": False}
            )
        ], style={"width": "48%", "display": "flex", "flexDirection": "column"}),

        html.Div([
            dcc.Graph(id="line-acidentes"),
            dcc.Graph(id="line-vitimas")
        ], style={"width": "48%"})
    ], style={
        "display": "flex",
        "justifyContent": "space-between",
        "marginBottom": "20px"
    }),

    html.Div([
        html.Div([
            dcc.Graph(id="bar-veiculos")
        ], style={"width": "48%"}),

        html.Div([
            dcc.Graph(id="pie-meteorologia")
        ], style={"width": "48%"})
    ], style={
        "display": "flex",
        "justifyContent": "space-between"
    })
], style={
    "padding": "20px",
    "backgroundColor": "#f5f7fb",
    "fontFamily": "Arial, sans-serif"
})


# =========================
# 8. CALLBACK DO DISTRITO SELECIONADO
# =========================
@app.callback(
    Output("selected-district", "data"),
    Input("mapa-distritos", "clickData"),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True
)
def manage_selected_district(click_data, reset_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return None

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "btn-reset":
        # Limpa seleção e volta ao mapa principal (distritos).
        return None

    if trigger == "mapa-distritos" and click_data is not None:
        point = click_data["points"][0]
        # No coroplético, a chave "location" traz o distrito clicado.
        if "location" in point:
            return point["location"]

    return None


# =========================
# 9. CALLBACK PRINCIPAL
# =========================
@app.callback(
    Output("kpi-vitimas", "children"),
    Output("kpi-graves", "children"),
    Output("kpi-distrito", "children"),
    Output("kpi-natureza", "children"),
    Output("mapa-titulo", "children"),
    Output("mapa-distritos", "figure"),
    Output("line-acidentes", "figure"),
    Output("line-vitimas", "figure"),
    Output("bar-veiculos", "figure"),
    Output("pie-meteorologia", "figure"),
    Input("year-filter", "value"),
    Input("selected-district", "data")
)
def update_dashboard(selected_year, selected_district):
    dff = df.copy()

    # Filtro global por ano aplicado a todos os gráficos/KPIs.
    if selected_year is not None and "Ano" in dff.columns:
        dff = dff[dff["Ano"] == selected_year]

    total_vitimas = int(dff["Vitimas_Totais"].sum()) if "Vitimas_Totais" in dff.columns else 0
    total_graves = int(dff["Acidente_Grave"].sum()) if "Acidente_Grave" in dff.columns else 0

    distrito_critico = "N/A"
    distrito_count = 0
    if distrito_col and distrito_col in dff.columns:
        counts = dff[distrito_col].value_counts()
        if not counts.empty:
            distrito_critico = counts.idxmax()
            distrito_count = int(counts.iloc[0])

    natureza_top = "N/A"
    natureza_count = 0
    if natureza_col and natureza_col in dff.columns:
        counts = dff[natureza_col].astype(str).value_counts()
        if not counts.empty:
            natureza_top = counts.idxmax()
            natureza_count = int(counts.iloc[0])

    prev_vitimas = None
    prev_graves = None
    prev_distrito_count = None
    prev_natureza_count = None

    if selected_year is not None and "Ano" in df.columns:
        prev_year = selected_year - 1
        dff_prev = df[df["Ano"] == prev_year]

        if not dff_prev.empty:
            if "Vitimas_Totais" in dff_prev.columns:
                prev_vitimas = int(dff_prev["Vitimas_Totais"].sum())

            if "Acidente_Grave" in dff_prev.columns:
                prev_graves = int(dff_prev["Acidente_Grave"].sum())

            if distrito_col and distrito_col in dff_prev.columns and distrito_critico != "N/A":
                prev_distrito_count = int((dff_prev[distrito_col] == distrito_critico).sum())

            if natureza_col and natureza_col in dff_prev.columns and natureza_top != "N/A":
                prev_natureza_count = int((dff_prev[natureza_col].astype(str) == natureza_top).sum())

    kpi1 = html.Div([
        html.H4("Vítimas Totais"),
        html.H2(format_int_pt(total_vitimas)),
        kpi_pct_badge(total_vitimas, prev_vitimas, lower_is_better=True),
        kpi_prev_label(prev_vitimas)
    ], style=kpi_style())

    kpi2 = html.Div([
        html.H4("Acidentes Graves"),
        html.H2(format_int_pt(total_graves)),
        kpi_pct_badge(total_graves, prev_graves, lower_is_better=True),
        kpi_prev_label(prev_graves)
    ], style=kpi_style())

    kpi3 = html.Div([
        html.H4("Distrito Crítico"),
        html.H2(str(distrito_critico)),
        html.Span(f"{format_int_pt(distrito_count)} acidentes", style={"fontSize": "12px", "color": "#555"}),
        kpi_pct_badge(distrito_count, prev_distrito_count, lower_is_better=True),
        kpi_prev_label(prev_distrito_count)
    ], style=kpi_style())

    kpi4 = html.Div([
        html.H4("Natureza"),
        html.H2(str(natureza_top)),
        html.Span(f"{format_int_pt(natureza_count)} acidentes", style={"fontSize": "12px", "color": "#555"}),
        kpi_pct_badge(natureza_count, prev_natureza_count, lower_is_better=True),
        kpi_prev_label(prev_natureza_count)
    ], style=kpi_style())

    mapa_titulo = (
        f"Distribuição de Acidentes: {selected_district}"
        if selected_district
        else "Distribuição de Acidentes"
    )

    fig_mapa = build_map_figure(dff, selected_district)

    if mes_col and mes_col in dff.columns:
        acidentes_mes = aggregate_by_month(dff, mes_col, output_column="Acidentes")
        fig_line_ac = px.line(
            acidentes_mes,
            x="Mês",
            y="Acidentes",
            markers=True,
            title="Evolução Mensal (Acidentes)"
        )
        fig_line_ac.update_layout(
            xaxis_title="Mês",
            yaxis_title="Nº de Acidentes",
            xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER)
        )
    else:
        fig_line_ac = go.Figure()
        fig_line_ac.update_layout(title="Evolução Mensal (Acidentes)")

    if mes_col and mes_col in dff.columns and "Vitimas_Totais" in dff.columns:
        vitimas_mes = aggregate_by_month(
            dff,
            mes_col,
            value_column="Vitimas_Totais",
            output_column="Vitimas_Totais"
        )
        fig_line_vit = px.line(
            vitimas_mes,
            x="Mês",
            y="Vitimas_Totais",
            markers=True,
            title="Evolução Mensal (Vítimas)"
        )
        fig_line_vit.update_layout(
            xaxis_title="Mês",
            yaxis_title="Nº de Vítimas",
            xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER)
        )
    else:
        fig_line_vit = go.Figure()
        fig_line_vit.update_layout(title="Evolução Mensal (Vítimas)")

    veiculos = []
    valores = []

    if ligeiros_col:
        veiculos.append("Ligeiros")
        valores.append(dff[ligeiros_col].fillna(0).sum())

    if pesados_col:
        veiculos.append("Pesados")
        valores.append(dff[pesados_col].fillna(0).sum())

    if motos_col:
        veiculos.append("Motociclos")
        valores.append(dff[motos_col].fillna(0).sum())

    if outros_col:
        veiculos.append("Outros")
        valores.append(dff[outros_col].fillna(0).sum())

    if veiculos:
        df_veiculos = pd.DataFrame({"Tipo": veiculos, "Total": valores})
        fig_bar = px.bar(
            df_veiculos,
            x="Tipo",
            y="Total",
            title="Tipos de Veículo Envolvidos",
            text_auto=True
        )
        fig_bar.update_layout(xaxis_title="Tipo de Veículo", yaxis_title="Total")
    else:
        fig_bar = go.Figure()
        fig_bar.update_layout(title="Tipos de Veículo Envolvidos")

    if meteo_col and meteo_col in dff.columns:
        meteo_df = dff[meteo_col].astype(str).value_counts().reset_index()
        meteo_df.columns = ["Meteorologia", "Total"]
        fig_pie = px.pie(
            meteo_df,
            names="Meteorologia",
            values="Total",
            title="Meteorologia"
        )
    else:
        fig_pie = go.Figure()
        fig_pie.update_layout(title="Meteorologia")

    return (
        kpi1,
        kpi2,
        kpi3,
        kpi4,
        mapa_titulo,
        fig_mapa,
        fig_line_ac,
        fig_line_vit,
        fig_bar,
        fig_pie
    )


# =========================
# 10. RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)