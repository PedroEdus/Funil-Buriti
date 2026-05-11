import pandas as pd
import streamlit as st
from datetime import date

from components import (
    card_acompanhamento,
    cards_resultado,
    exibir_logo,
    grafico_campanha,
    grafico_cidades,
    grafico_evolucao_diaria,
    grafico_forma_cadastro,
    grafico_funil,
    grafico_onoff,
    grafico_origem,
    grafico_produto,
    grafico_responsavel,
    kpis,
    matrizes_cidade_forma,
    matriz_origem_etapa,
    tabela_base,
)
from data import carregar_leads

st.set_page_config(
    page_title="Funil de Leads — Buriti",
    page_icon="📊",
    layout="wide",
)

# ── Toque visual mínimo ────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { color: #008140 !important; font-weight: 700; }
[data-testid="stSidebar"]     { border-right: 2px solid #008140; }
</style>
""", unsafe_allow_html=True)

# ── Cabeçalho ─────────────────────────────────────────────────────────────────

exibir_logo()
st.title("Painel CRM — Funil de Leads")
st.caption("Análise operacional dos leads por etapa, origem, campanha, produto e responsável.")

# ── Dados ─────────────────────────────────────────────────────────────────────

df = carregar_leads()

if df.empty:
    st.warning("Nenhum lead encontrado na tabela BigQuery.")
    st.stop()

# ── Filtros ───────────────────────────────────────────────────────────────────

st.sidebar.header("Filtros")

if "DataCadastro" in df.columns:
    data_min = df["DataCadastro"].min()
    data_max = df["DataCadastro"].max()
    if pd.notna(data_min) and pd.notna(data_max):
        default_inicio = max(date(2026, 1, 1), data_min.date())
        periodo = st.sidebar.date_input(
            "Período de cadastro",
            value=(default_inicio, data_max.date()),
            min_value=data_min.date(),
            max_value=data_max.date(),
        )
        if len(periodo) == 2:
            df = df[
                (df["DataCadastro"] >= pd.to_datetime(periodo[0])) &
                (df["DataCadastro"] <= pd.to_datetime(periodo[1]))
            ]

FILTROS = [
    ("Etapa NF",          "Etapa_NF"),
    ("On / Off",          "On_Off"),
    ("Produto",           "Produto"),
    ("Cidade",            "Cidade"),
    ("Forma de cadastro", "FormaCadastro"),
    ("Campanha",          "UtmCampaign"),
    ("Origem",            "UtmSource"),
    ("Responsável",       "Responsavel"),
]

df_filtrado = df.copy()
for label, coluna in FILTROS:
    if coluna not in df_filtrado.columns:
        continue
    opcoes = sorted(df_filtrado[coluna].dropna().unique().tolist())
    sel = st.sidebar.multiselect(label, opcoes)
    if sel:
        df_filtrado = df_filtrado[df_filtrado[coluna].isin(sel)]

st.caption(f"{len(df_filtrado):,} lead(s) exibido(s)")

# ── KPIs ──────────────────────────────────────────────────────────────────────

kpis(df_filtrado)
st.divider()

# ── Abas ──────────────────────────────────────────────────────────────────────

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "Funil",
    "Origem e Campanhas",
    "Cidades e Cadastro",
    "Operação",
    "Base Analítica",
])

with aba1:
    col_a, col_b = st.columns([1.4, 0.9])
    with col_a:
        grafico_funil(df_filtrado)
    with col_b:
        grafico_onoff(df_filtrado)
        st.divider()
        cards_resultado(df_filtrado)
        st.divider()
        card_acompanhamento(df_filtrado)
    grafico_evolucao_diaria(df_filtrado)

with aba2:
    col_a, col_b = st.columns(2)
    with col_a:
        grafico_origem(df_filtrado)
    with col_b:
        grafico_campanha(df_filtrado)
    matriz_origem_etapa(df_filtrado)

with aba3:
    col_a, col_b = st.columns(2)
    with col_a:
        grafico_cidades(df_filtrado)
    with col_b:
        grafico_forma_cadastro(df_filtrado)
    matrizes_cidade_forma(df_filtrado)

with aba4:
    col_a, col_b = st.columns(2)
    with col_a:
        grafico_produto(df_filtrado)
    with col_b:
        grafico_responsavel(df_filtrado)

with aba5:
    st.subheader("Base filtrada")
    tabela_base(df_filtrado)
