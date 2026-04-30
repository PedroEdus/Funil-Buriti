import os

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Painel CRM - Funil Digital",
    page_icon="📊",
    layout="wide"
)


@st.cache_data
def carregar_dados(arquivo):
    df = pd.read_excel(arquivo)

    df.columns = df.columns.str.strip()

    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    colunas_texto = [
        "Nome", "Produto", "Cidade", "UtmCampaign", "UtmMedium", "UtmSource",
        "FormaCadastro", "Etapa", "Status", "Email", "Telefone", "Formulario",
        "Responsavel", "On/Off", "Etapa_NF"
    ]

    for col in colunas_texto:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .fillna("Não informado")
                .str.strip()
            )

    if "DataCadastro" in df.columns:
        df["DataCadastro"] = pd.to_datetime(df["DataCadastro"], dayfirst=True, errors="coerce")

    if "DataAlteracao" in df.columns:
        df["DataAlteracao"] = pd.to_datetime(df["DataAlteracao"], dayfirst=True, errors="coerce")

    if "TempoTotal" in df.columns:
        df["TempoTotal"] = pd.to_numeric(df["TempoTotal"], errors="coerce").fillna(0)

    # Ajuste solicitado:
    # OUTROS deixa de ser categoria final do funil e passa a ser ACOMPANHAMENTO.
    # Isso evita o painel mostrar zero caso a base antiga ainda venha com OUTROS.
    if "Etapa_NF" in df.columns:
        df["Etapa_NF"] = df["Etapa_NF"].replace({"OUTROS": "ACOMPANHAMENTO"})

    return df


def filtro_multiselect(label, df, coluna):
    opcoes = sorted(df[coluna].dropna().unique().tolist())
    selecionados = st.sidebar.multiselect(label, opcoes)

    if selecionados:
        return df[df[coluna].isin(selecionados)]

    return df


def formatar_numero(valor):
    return f"{valor:,.0f}".replace(",", ".")


def exibir_logo():
    caminhos_logo = [
        "LOGO BRASIL TERRENOS_2_BRANCA.png",
        "logo.png",
        "Logo.png",
        "LOGO.png"
    ]

    for caminho in caminhos_logo:
        if os.path.exists(caminho):
            st.image(caminho, width=300)
            return

    st.caption("Logo não encontrada na pasta do app.")


# =========================
# CABEÇALHO
# =========================

exibir_logo()

st.title("Painel CRM - Funil Digital")
st.caption("Análise operacional dos leads por etapa, origem, campanha, produto e responsável.")

arquivo = st.sidebar.file_uploader(
    "Carregar base Excel",
    type=["xlsx", "xls"]
)

if arquivo is None:
    st.info("Carregue o arquivo Excel para visualizar o painel.")
    st.stop()


df = carregar_dados(arquivo)
df_filtrado = df.copy()

st.sidebar.header("Filtros")

# =========================
# FILTRO DE DATA
# =========================

if "DataCadastro" in df_filtrado.columns:
    data_min = df_filtrado["DataCadastro"].min()
    data_max = df_filtrado["DataCadastro"].max()

    if pd.notna(data_min) and pd.notna(data_max):
        periodo = st.sidebar.date_input(
            "Período de cadastro",
            value=(data_min.date(), data_max.date()),
            min_value=data_min.date(),
            max_value=data_max.date()
        )

        if len(periodo) == 2:
            inicio = pd.to_datetime(periodo[0])
            fim = pd.to_datetime(periodo[1])
            df_filtrado = df_filtrado[
                (df_filtrado["DataCadastro"] >= inicio) &
                (df_filtrado["DataCadastro"] <= fim)
            ]

# =========================
# FILTROS LATERAIS
# =========================

for label, coluna in [
    ("Etapa NF", "Etapa_NF"),
    ("On/Off", "On/Off"),
    ("Produto", "Produto"),
    ("Cidade", "Cidade"),
    ("Forma de cadastro", "FormaCadastro"),
    ("Campanha", "UtmCampaign"),
    ("Origem", "UtmSource"),
    ("Responsável", "Responsavel"),
]:
    if coluna in df_filtrado.columns:
        df_filtrado = filtro_multiselect(label, df_filtrado, coluna)


# =========================
# CARDS SUPERIORES — FUNIL
# =========================

total_leads = len(df_filtrado)

if "Etapa_NF" in df_filtrado.columns:
    aguardando = df_filtrado[df_filtrado["Etapa_NF"].eq("AGUARDANDO ATENDIMENTO")].shape[0]
    atendimento = df_filtrado[df_filtrado["Etapa_NF"].eq("EM ATENDIMENTO")].shape[0]
    visitas = df_filtrado[df_filtrado["Etapa_NF"].eq("VISITA AGENDADA")].shape[0]
    fechamento = df_filtrado[df_filtrado["Etapa_NF"].eq("NEGOCIAÇÃO")].shape[0]
    acompanhamento = df_filtrado[df_filtrado["Etapa_NF"].eq("ACOMPANHAMENTO")].shape[0]
else:
    aguardando = 0
    atendimento = 0
    visitas = 0
    fechamento = 0
    acompanhamento = 0

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Leads", formatar_numero(total_leads))
col2.metric("Aguardando", formatar_numero(aguardando))
col3.metric("Atendimento", formatar_numero(atendimento))
col4.metric("Visita", formatar_numero(visitas))
col5.metric("Negociação", formatar_numero(fechamento))
col6.metric("Acompanhamento", formatar_numero(acompanhamento))

st.divider()

# =========================
# ORDEM DO FUNIL
# =========================

ordem_funil = [
    "AGUARDANDO ATENDIMENTO",
    "EM ATENDIMENTO",
    "VISITA AGENDADA",
    "NEGOCIAÇÃO",
    "ACOMPANHAMENTO"
]

ordem_funil_principal = [
    "AGUARDANDO ATENDIMENTO",
    "EM ATENDIMENTO",
    "VISITA AGENDADA",
    "NEGOCIAÇÃO"
]

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "Funil",
    "Origem e Campanhas",
    "Cidades e Cadastro",
    "Operação",
    "Base Analítica"
])

# =========================
# ABA 1 — FUNIL
# =========================

with aba1:
    col_a, col_b = st.columns([1.35, 0.85])

    if "Etapa_NF" in df_filtrado.columns:
        funil = (
            df_filtrado
            .groupby("Etapa_NF", dropna=False)
            .size()
            .reset_index(name="Leads")
        )

        funil["Etapa_NF"] = pd.Categorical(
            funil["Etapa_NF"],
            categories=ordem_funil,
            ordered=True
        )
        funil = funil.sort_values("Etapa_NF")

        qtd_acompanhamento = int(
            funil.loc[funil["Etapa_NF"].astype(str).eq("ACOMPANHAMENTO"), "Leads"].sum()
        )
        perc_acompanhamento = (qtd_acompanhamento / total_leads) if total_leads else 0

        funil_principal = funil[funil["Etapa_NF"].astype(str).ne("ACOMPANHAMENTO")].copy()
        funil_principal["Etapa_NF"] = pd.Categorical(
            funil_principal["Etapa_NF"],
            categories=ordem_funil_principal,
            ordered=True
        )
        funil_principal = funil_principal.sort_values("Etapa_NF")

        fig_funil = px.funnel(
            funil_principal,
            x="Leads",
            y="Etapa_NF",
            title="Funil por Etapa NF"
        )
        fig_funil.update_layout(height=420)

        col_a.plotly_chart(fig_funil, use_container_width=True)

        with col_b:
            st.metric(
                "Acompanhamento",
                formatar_numero(qtd_acompanhamento),
                f"{perc_acompanhamento:.1%}".replace(".", ",") + " dos leads"
            )
            st.caption("Leads identificados como oportunidades futuras.")

            if "On/Off" in df_filtrado.columns:
                pizza_onoff = (
                    df_filtrado
                    .groupby("On/Off", dropna=False)
                    .size()
                    .reset_index(name="Leads")
                )

                fig_onoff = px.pie(
                    pizza_onoff,
                    names="On/Off",
                    values="Leads",
                    hole=0.45,
                    title="Distribuição On/Off"
                )
                fig_onoff.update_layout(height=340)

                st.plotly_chart(fig_onoff, use_container_width=True)
            else:
                st.warning("Coluna 'On/Off' não encontrada na base.")
    else:
        st.warning("Coluna 'Etapa_NF' não encontrada na base.")

    if "DataCadastro" in df_filtrado.columns:
        serie_diaria = (
            df_filtrado
            .dropna(subset=["DataCadastro"])
            .assign(Data=df_filtrado["DataCadastro"].dt.date)
            .groupby("Data")
            .size()
            .reset_index(name="Leads")
        )

        fig_linha = px.line(
            serie_diaria,
            x="Data",
            y="Leads",
            markers=True,
            title="Evolução diária de leads"
        )
        fig_linha.update_layout(height=360)
        st.plotly_chart(fig_linha, use_container_width=True)

# =========================
# ABA 2 — ORIGEM E CAMPANHAS
# =========================

with aba2:
    col_a, col_b = st.columns(2)

    if "UtmSource" in df_filtrado.columns:
        origem = (
            df_filtrado
            .groupby("UtmSource", dropna=False)
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
            .head(15)
        )

        fig_origem = px.bar(
            origem,
            x="Leads",
            y="UtmSource",
            orientation="h",
            title="Top origens de leads"
        )
        fig_origem.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        col_a.plotly_chart(fig_origem, use_container_width=True)
    else:
        col_a.warning("Coluna 'UtmSource' não encontrada na base.")

    if "UtmCampaign" in df_filtrado.columns:
        campanha = (
            df_filtrado
            .groupby("UtmCampaign", dropna=False)
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
            .head(15)
        )

        fig_campanha = px.bar(
            campanha,
            x="Leads",
            y="UtmCampaign",
            orientation="h",
            title="Top campanhas"
        )
        fig_campanha.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        col_b.plotly_chart(fig_campanha, use_container_width=True)
    else:
        col_b.warning("Coluna 'UtmCampaign' não encontrada na base.")

    if {"UtmSource", "Etapa_NF"}.issubset(df_filtrado.columns):
        matriz_origem_etapa = pd.crosstab(
            df_filtrado["UtmSource"],
            df_filtrado["Etapa_NF"]
        )

        st.subheader("Matriz origem x etapa")
        st.dataframe(matriz_origem_etapa, use_container_width=True)
    else:
        st.warning("Não foi possível montar a matriz origem x etapa.")

# =========================
# ABA 3 — CIDADES E CADASTRO
# =========================

with aba3:
    col_a, col_b = st.columns(2)

    if "Cidade" in df_filtrado.columns:
        cidades = (
            df_filtrado
            .groupby("Cidade", dropna=False)
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
            .head(20)
        )

        fig_cidades = px.bar(
            cidades,
            x="Leads",
            y="Cidade",
            orientation="h",
            title="Top cidades por volume de leads"
        )
        fig_cidades.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
        col_a.plotly_chart(fig_cidades, use_container_width=True)
    else:
        col_a.warning("Coluna 'Cidade' não encontrada na base.")

    if "FormaCadastro" in df_filtrado.columns:
        forma_cadastro = (
            df_filtrado
            .groupby("FormaCadastro", dropna=False)
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
            .head(20)
        )

        fig_forma = px.bar(
            forma_cadastro,
            x="Leads",
            y="FormaCadastro",
            orientation="h",
            title="Leads por forma de cadastro"
        )
        fig_forma.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
        col_b.plotly_chart(fig_forma, use_container_width=True)
    else:
        col_b.warning("Coluna 'FormaCadastro' não encontrada na base.")

    col_c, col_d = st.columns(2)

    if {"Cidade", "Etapa_NF"}.issubset(df_filtrado.columns):
        matriz_cidade_etapa = pd.crosstab(
            df_filtrado["Cidade"],
            df_filtrado["Etapa_NF"]
        )
        matriz_cidade_etapa["Total"] = matriz_cidade_etapa.sum(axis=1)
        matriz_cidade_etapa = matriz_cidade_etapa.sort_values("Total", ascending=False).head(30)

        col_c.subheader("Matriz cidade x etapa")
        col_c.dataframe(matriz_cidade_etapa, use_container_width=True)

    if {"FormaCadastro", "Etapa_NF"}.issubset(df_filtrado.columns):
        matriz_forma_etapa = pd.crosstab(
            df_filtrado["FormaCadastro"],
            df_filtrado["Etapa_NF"]
        )
        matriz_forma_etapa["Total"] = matriz_forma_etapa.sum(axis=1)
        matriz_forma_etapa = matriz_forma_etapa.sort_values("Total", ascending=False)

        col_d.subheader("Matriz forma de cadastro x etapa")
        col_d.dataframe(matriz_forma_etapa, use_container_width=True)

# =========================
# ABA 4 — OPERAÇÃO
# =========================

with aba4:
    col_a, col_b = st.columns(2)

    if "Produto" in df_filtrado.columns:
        produto = (
            df_filtrado
            .groupby("Produto", dropna=False)
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
            .head(20)
        )

        fig_produto = px.bar(
            produto,
            x="Leads",
            y="Produto",
            orientation="h",
            title="Top produtos"
        )
        fig_produto.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
        col_a.plotly_chart(fig_produto, use_container_width=True)
    else:
        col_a.warning("Coluna 'Produto' não encontrada na base.")

    if {"Responsavel", "Codigo"}.issubset(df_filtrado.columns):
        agregacoes = {"Leads": ("Codigo", "count")}

        if "TempoTotal" in df_filtrado.columns:
            agregacoes["TempoMedio"] = ("TempoTotal", "mean")

        responsavel = (
            df_filtrado
            .groupby("Responsavel", dropna=False)
            .agg(**agregacoes)
            .reset_index()
            .sort_values("Leads", ascending=False)
            .head(20)
        )

        fig_resp = px.bar(
            responsavel,
            x="Leads",
            y="Responsavel",
            orientation="h",
            title="Top responsáveis por volume de leads"
        )
        fig_resp.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
        col_b.plotly_chart(fig_resp, use_container_width=True)

        st.subheader("Resumo por responsável")
        st.dataframe(responsavel, use_container_width=True)
    else:
        col_b.warning("Colunas 'Responsavel' e/ou 'Codigo' não encontradas na base.")

# =========================
# ABA 5 — BASE ANALÍTICA
# =========================

with aba5:
    st.subheader("Base filtrada")

    colunas_exibir = [
        "Codigo", "Nome", "Produto", "Cidade", "DataCadastro", "FormaCadastro",
        "UtmCampaign", "UtmMedium", "UtmSource", "Etapa", "Status", "Etapa_NF",
        "On/Off", "Responsavel", "TempoTotal"
    ]

    colunas_exibir = [col for col in colunas_exibir if col in df_filtrado.columns]

    st.dataframe(
        df_filtrado[colunas_exibir],
        use_container_width=True,
        hide_index=True
    )

    csv = df_filtrado[colunas_exibir].to_csv(index=False, sep=";", encoding="utf-8-sig")

    st.download_button(
        "Baixar base filtrada em CSV",
        data=csv,
        file_name="base_crm_filtrada.csv",
        mime="text/csv"
    )
