# app_drogas.py
import pandas as pd
import streamlit as st
import plotly.express as px

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
