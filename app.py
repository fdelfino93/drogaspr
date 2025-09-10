# app_drogas.py
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
from unidecode import unidecode

st.set_page_config(page_title="Apreensão de Drogas no Paraná", layout="wide")

st.title("🚔 Apreensões de Drogas no Paraná (por município)")

# ------------------------------
# Função para carregar dados
# ------------------------------
@st.cache_data
def carregar_dados(path):
    df = pd.read_csv(path)
    return df

# ------------------------------
# Carregar planilhas
# ------------------------------
dados = {
    "Maconha": carregar_dados("MaconhaV2.csv"),
    "Cocaína": carregar_dados("CocainaV2.csv"),
    "Crack": carregar_dados("CrackV2.csv"),
}

# ------------------------------
# Sidebar - seleção de droga, município e mês
# ------------------------------
st.sidebar.header("Filtros")

droga = st.sidebar.selectbox("Selecione a droga", list(dados.keys()))
df = dados[droga]

# filtro municípios
municipios = st.sidebar.multiselect(
    "Selecione municípios",
    options=df["Municipio"].unique(),
    default=["CURITIBA", "FOZ DO IGUACU", "LONDRINA"]
)

# filtro meses (identifica todas as colunas mensais)
colunas_mensais = [c for c in df.columns if c not in ("Municipio", "Total")]
meses_selecionados = st.sidebar.multiselect(
    "Selecione meses",
    options=colunas_mensais,
    default=colunas_mensais  # todos marcados por padrão
)

# aplica filtros
df_filtrado = df[df["Municipio"].isin(municipios)].copy()

# tabela mostra apenas meses selecionados + Municipio + Total
colunas_tabela = ["Municipio"] + meses_selecionados + (["Total"] if "Total" in df.columns else [])
df_tabela = df_filtrado[colunas_tabela]

# ------------------------------
# VISUALIZAÇÃO TABELA
# ------------------------------
st.subheader(f"📋 Tabela filtrada - {droga}")
st.dataframe(df_tabela, use_container_width=True)

# ------------------------------
# RANKING (continua usando Total anual)
# ------------------------------
st.subheader(f"🏆 Maiores apreensões de {droga} (Total anual)")
ranking = df.sort_values("Total", ascending=False).head(10)
fig_rank = px.bar(ranking, x="Municipio", y="Total", title=f"Top 10 Municípios - {droga} (Total Anual)")
st.plotly_chart(fig_rank, use_container_width=True)

# ------------------------------
# EVOLUÇÃO MENSAL (apenas meses selecionados)
# ------------------------------
st.subheader(f"📈 Evolução mensal por município - {droga}")
df_melt = df_filtrado.melt(
    id_vars=["Municipio"],
    value_vars=meses_selecionados,
    var_name="Mes",
    value_name="Kg"
)
fig_line = px.line(
    df_melt, x="Mes", y="Kg", color="Municipio",
    markers=True, title=f"Evolução das apreensões mensais - {droga}"
)
st.plotly_chart(fig_line, use_container_width=True)

# ------------------------------
# SOMA ESTADUAL (apenas meses selecionados)
# ------------------------------
st.subheader(f"📊 Total estadual por mês - {droga}")
df_total_mes = df[meses_selecionados].sum()
fig_state = px.bar(
    x=df_total_mes.index, y=df_total_mes.values,
    labels={"x": "Mês", "y": "Total (kg)"},
    title=f"Total estadual por mês - {droga}"
)
st.plotly_chart(fig_state, use_container_width=True)

# ------------------------------
# PARTICIPAÇÃO POR MUNICÍPIO (pizza - meses selecionados)
# ------------------------------
st.subheader(f"🍕 Participação por município - {droga} (meses selecionados)")
df_pizza = df_filtrado.copy()
df_pizza["TotalSelecionado"] = df_pizza[meses_selecionados].sum(axis=1)

# (opcional) remove municípios zerados para evitar fatias nulas
df_pizza = df_pizza[df_pizza["TotalSelecionado"] > 0]

fig_pizza = px.pie(
    df_pizza,
    names="Municipio",
    values="TotalSelecionado",
    title=f"Distribuição das apreensões por município - {droga}",
    hole=0.3  # donut; troque para 0 se quiser pizza tradicional
)
st.plotly_chart(fig_pizza, use_container_width=True)

# ------------------------------
# EXPORTAR
# ------------------------------
st.subheader("💾 Exportar dados")
csv = df_tabela.to_csv(index=False).encode("utf-8")
st.download_button(f"Baixar CSV filtrado ({droga})", csv, f"apreensao_{droga.lower()}_filtrada.csv", "text/csv")

# ------------------------------
# 🗺️ MAPA: Apreensões por município (meses selecionados) + contorno do PR
# ------------------------------

st.subheader(f"🗺️ Mapa de apreensões por município - {droga}")

@st.cache_data
def carregar_geojson_municipios_pr():
    # GeoJSON dos municípios do PR (UF 41)
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-41-mun.json"
    gj = requests.get(url, timeout=30).json()
    # Normaliza nomes para casar com o CSV
    for f in gj["features"]:
        f["properties"]["name_ascii"] = unidecode(f["properties"]["name"]).upper()
    return gj

@st.cache_data
def carregar_geojson_contorno_pr():
    # GeoJSON do perímetro do estado do PR (uma feature)
    url = "https://raw.githubusercontent.com/giuliano-macedo/geodata-br-states/main/geojson/br_states/br_pr.json"
    return requests.get(url, timeout=30).json()

def adicionar_contorno_uf(fig, uf_geojson, cor="black", largura=2.5):
    """Desenha o contorno da UF por cima do mapa (Polygon/MultiPolygon)."""
    geom = uf_geojson["features"][0]["geometry"]
    coords = geom["coordinates"]
    multipoligonos = coords if geom["type"] == "MultiPolygon" else [coords]

    for poligono in multipoligonos:   # poligono = [anel_externo, aneis_internos...]
        for anel in poligono:         # anel = lista de [lon, lat]
            lons, lats = zip(*anel)
            fig.add_trace(go.Scattergeo(
                lon=lons, lat=lats,
                mode="lines",
                line=dict(color=cor, width=largura),
                hoverinfo="skip",
                showlegend=False
            ))
    return fig

# --- Dados e pré-processamento
geojson_mun = carregar_geojson_municipios_pr()
geojson_uf = carregar_geojson_contorno_pr()

df_mapa = df_filtrado.copy()
df_mapa["TotalSelecionado"] = df_mapa[meses_selecionados].sum(axis=1)
df_mapa["Municipio_ascii"] = df_mapa["Municipio"].map(lambda s: unidecode(str(s)).upper())

# Remove municípios com zero (opcional: deixa o mapa mais limpo)
df_mapa = df_mapa[df_mapa["TotalSelecionado"] > 0]

# --- Controle de tamanho pela sidebar
tamanho_mapa = st.sidebar.select_slider(
    "Tamanho do mapa",
    options=["Pequeno", "Médio", "Grande", "Tela cheia"],
    value="Grande"
)
alturas = {"Pequeno": 450, "Médio": 600, "Grande": 800, "Tela cheia": 950}

if df_mapa.empty:
    st.info("Sem dados para os filtros atuais (municípios/meses). Ajuste os filtros para visualizar o mapa.")
else:
    # --- Choropleth por município
    fig_map = px.choropleth(
        df_mapa,
        geojson=geojson_mun,
        locations="Municipio_ascii",
        featureidkey="properties.name_ascii",
        color="TotalSelecionado",
        color_continuous_scale="Plasma",  # Aqui você muda a escala de cores
        projection="mercator",
        labels={"TotalSelecionado": "Kg"},
        title=f"Mapa de apreensões – {droga} (meses selecionados)"
    )

    # --- Contorno da UF
    fig_map = adicionar_contorno_uf(fig_map, geojson_uf, cor="black", largura=2.5)

    # --- Enquadramento e layout (área maior + margens pequenas)
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(
        height=alturas[tamanho_mapa],
        margin=dict(l=0, r=0, t=60, b=0)
    )

    st.plotly_chart(fig_map, use_container_width=True)
