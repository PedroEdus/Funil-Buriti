
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

    df["DataCadastro"] = pd.to_datetime(df["DataCadastro"], dayfirst=True, errors="coerce")
    df["DataAlteracao"] = pd.to_datetime(df["DataAlteracao"], dayfirst=True, errors="coerce")

    if "TempoTotal" in df.columns:
        df["TempoTotal"] = pd.to_numeric(df["TempoTotal"], errors="coerce").fillna(0)

    return df


def filtro_multiselect(label, df, coluna):
    opcoes = sorted(df[coluna].dropna().unique().tolist())
    selecionados = st.sidebar.multiselect(label, opcoes)
    if selecionados:
        return df[df[coluna].isin(selecionados)]
    return df


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


total_leads = len(df_filtrado)
leads_digitais = df_filtrado[df_filtrado["On/Off"].eq("On")].shape[0] if "On/Off" in df_filtrado.columns else 0
visitas = df_filtrado[df_filtrado["Etapa_NF"].eq("VISITA AGENDADA")].shape[0] if "Etapa_NF" in df_filtrado.columns else 0
fechamento = df_filtrado[df_filtrado["Etapa_NF"].eq("FECHAMENTO")].shape[0] if "Etapa_NF" in df_filtrado.columns else 0
tempo_medio = df_filtrado["TempoTotal"].mean() if "TempoTotal" in df_filtrado.columns else 0

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Leads", f"{total_leads:,.0f}".replace(",", "."))
col2.metric("Leads On", f"{leads_digitais:,.0f}".replace(",", "."))
col3.metric("Visitas", f"{visitas:,.0f}".replace(",", "."))
col4.metric("Fechamento", f"{fechamento:,.0f}".replace(",", "."))
col5.metric("Tempo médio", f"{tempo_medio:,.1f}".replace(".", ",") if pd.notna(tempo_medio) else "0")

st.divider()

ordem_funil = [
    "AGUARDANDO ATENDIMENTO",
    "EM ATENDIMENTO",
    "VISITA AGENDADA",
    "FECHAMENTO",
    "OUTROS"
]

ordem_funil_principal = [etapa for etapa in ordem_funil if etapa != "OUTROS"]

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "Funil",
    "Origem e Campanhas",
    "Cidades e Cadastro",
    "Operação",
    "Base Analítica"
])

with aba1:
    col_a, col_b = st.columns([1.35, 0.85])

    funil = (
        df_filtrado
        .groupby("Etapa_NF", dropna=False)
        .size()
        .reset_index(name="Leads")
    )

    funil["Etapa_NF"] = pd.Categorical(funil["Etapa_NF"], categories=ordem_funil, ordered=True)
    funil = funil.sort_values("Etapa_NF")

    qtd_outros = int(
        funil.loc[funil["Etapa_NF"].astype(str).eq("OUTROS"), "Leads"].sum()
    )
    perc_outros = (qtd_outros / total_leads) if total_leads else 0

    funil_principal = funil[funil["Etapa_NF"].astype(str).ne("OUTROS")].copy()
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
            "Outros",
            f"{qtd_outros:,.0f}".replace(",", "."),
            f"{perc_outros:.1%}".replace(".", ",") + " dos leads"
        )
        st.caption("Leads que não se encaixaram nas etapas principais do funil.")

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

with aba2:
    col_a, col_b = st.columns(2)

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

    matriz_origem_etapa = pd.crosstab(
        df_filtrado["UtmSource"],
        df_filtrado["Etapa_NF"]
    )

    st.subheader("Matriz origem x etapa")
    st.dataframe(matriz_origem_etapa, use_container_width=True)

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

with aba4:
    col_a, col_b = st.columns(2)

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

    responsavel = (
        df_filtrado
        .groupby("Responsavel", dropna=False)
        .agg(
            Leads=("Codigo", "count"),
            TempoMedio=("TempoTotal", "mean")
        )
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
