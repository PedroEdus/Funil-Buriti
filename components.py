import base64
import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ── Assets ────────────────────────────────────────────────────────────────────

_ASSETS     = os.path.join(os.path.dirname(__file__), "assets")
LOGO_CLARA  = os.path.join(_ASSETS, "logo_preta.png")
LOGO_ESCURA = os.path.join(_ASSETS, "logo_branca.png")

# Funil: topo = entrada (mais leads) → base = conversão
ORDEM_FUNIL = [
    "Venda Ganha",
    "Negociação",
    "Visita Agendada",
    "Em Atendimento",
    "Aguardando Atendimento",
]

# Paleta: verde #008140 + variantes · branco/cinza como secundária
_VERDE_BASE  = "#008140"
_VERDE_ESCURO = "#004d26"
_VERDE_MEDIO  = "#006633"
_VERDE_CLARO  = "#00a851"
_VERDE_BRILHO = "#00cc66"
_BRANCO      = "#ffffff"
COLOR_MAP = {
    "Aguardando Atendimento": _VERDE_ESCURO,
    "Em Atendimento":         _VERDE_MEDIO,
    "Visita Agendada":        _VERDE_BASE,
    "Negociação":             _VERDE_CLARO,
    "Venda Ganha":            _VERDE_BRILHO,
    "Venda Perdida":          _BRANCO,
    "Acompanhamento":         "#335544",
    "Outros":                 "#444444",
    "On":                     _VERDE_BASE,
    "Off":                    _BRANCO,
}

# Sequência padrão para gráficos de 2 séries: verde + branco
_SEQ2 = [_VERDE_BASE, _BRANCO]


# ── Logo ──────────────────────────────────────────────────────────────────────

def _imagem_base64(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode()


def exibir_logo() -> None:
    existe_clara  = os.path.exists(LOGO_CLARA)
    existe_escura = os.path.exists(LOGO_ESCURA)
    if not existe_clara and not existe_escura:
        return

    caminho_claro  = LOGO_CLARA  if existe_clara  else LOGO_ESCURA
    caminho_escuro = LOGO_ESCURA if existe_escura else LOGO_CLARA

    clara_b64  = _imagem_base64(caminho_claro)
    escura_b64 = _imagem_base64(caminho_escuro)

    st.markdown(
        f"""
        <style>
            .logo-container {{
                display: flex;
                justify-content: flex-start;
                margin-bottom: 0.75rem;
            }}
            .logo-container img {{
                width: min(260px, 60vw);
                height: auto;
            }}
            .logo-dark {{ display: none; }}
            @media (prefers-color-scheme: dark) {{
                .logo-light {{ display: none; }}
                .logo-dark  {{ display: block; }}
            }}
        </style>
        <div class="logo-container">
            <img class="logo-light" src="data:image/png;base64,{clara_b64}">
            <img class="logo-dark"  src="data:image/png;base64,{escura_b64}">
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Tema ──────────────────────────────────────────────────────────────────────

def _tema() -> str:
    return "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"


def _layout(fig, altura: int = 500):
    fig.update_layout(
        height=altura,
        template=_tema(),
        margin=dict(l=20, r=60, t=60, b=20),
        font=dict(color="#ffffff"),
        legend=dict(font=dict(color="#ffffff")),
    )
    return fig


# ── Helper: agrupar descartando nulos ────────────────────────────────────────

def _agrupar(df: pd.DataFrame, coluna: str, top: int | None = None) -> pd.DataFrame:
    """Agrupa por coluna descartando nulos/vazios e retorna contagem."""
    resumo = (
        df[coluna]
        .dropna()
        .loc[lambda s: s.astype(str).str.strip() != ""]
        .value_counts()
        .reset_index()
    )
    resumo.columns = [coluna, "Leads"]
    if top:
        resumo = resumo.head(top)
    return resumo


def _resolver_origem(df: pd.DataFrame) -> pd.Series:
    """
    Preenche UtmSource nulo com base no FormaCadastro:
    - FormaCadastro contém 'Meta'   → 'Meta'
    - FormaCadastro contém 'Google' → 'Google'
    - Demais nulos                  → 'Não Informado'
    """
    source = df["UtmSource"].astype(str).str.strip().copy()
    nulo   = source.isin(["", "None", "nan", "NaN"])

    forma = df.get("FormaCadastro", pd.Series([""] * len(df), index=df.index))
    forma = forma.fillna("").astype(str).str.lower()

    source.loc[nulo & forma.str.contains("meta",   na=False)] = "Meta"
    source.loc[nulo & forma.str.contains("google", na=False)] = "Google"
    source.loc[nulo & ~forma.str.contains("meta|google", na=False)] = "Não Informado"

    return source


# ── KPIs ──────────────────────────────────────────────────────────────────────

def kpis(df: pd.DataFrame) -> None:
    total = len(df)

    def _conta(etapa: str) -> int:
        if "Etapa_NF" not in df.columns:
            return 0
        return int(df["Etapa_NF"].eq(etapa).sum())

    aguardando  = _conta("Aguardando Atendimento")
    atendimento = _conta("Em Atendimento")
    visita      = _conta("Visita Agendada")
    negociacao  = _conta("Negociação")
    ganhas      = _conta("Venda Ganha")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total de Leads",  f"{total:,.0f}")
    c2.metric("Aguardando",      f"{aguardando:,.0f}")
    c3.metric("Em Atendimento",  f"{atendimento:,.0f}")
    c4.metric("Visita Agendada", f"{visita:,.0f}")
    c5.metric("Negociação",      f"{negociacao:,.0f}")
    c6.metric("🏆 Venda Ganha",  f"{ganhas:,.0f}")


# ── Helper barras horizontais ─────────────────────────────────────────────────

def _barras_h(
    df_plot: pd.DataFrame,
    x: str,
    y: str,
    titulo: str,
    altura: int = 500,
    color: str | None = None,
    color_map: dict | None = None,
) -> None:
    if df_plot.empty:
        st.info(f"Sem dados para exibir em '{titulo}'.")
        return

    df_plot = df_plot.copy()
    df_plot["_texto"] = df_plot[x].map(lambda v: f"{v:,.0f}")

    kwargs: dict = dict(
        x=x, y=y, orientation="h",
        text="_texto", title=titulo,
        labels={x: "Leads", y: y},
        height=max(altura, len(df_plot) * 36),
    )
    if color:
        kwargs["color"] = color
        if color_map:
            kwargs["color_discrete_map"] = color_map
    else:
        # sem coluna de cor → todas as barras no verde da marca
        kwargs["color_discrete_sequence"] = [_VERDE_BASE]

    fig = px.bar(df_plot, **kwargs)
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont_size=11,
        textfont_color="#ffffff",
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        template=_tema(),
        margin=dict(l=20, r=80, t=60, b=20),
        font=dict(color="#ffffff"),
        legend=dict(font=dict(color="#ffffff")),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Aba Funil ─────────────────────────────────────────────────────────────────

def grafico_funil(df: pd.DataFrame) -> None:
    if "Etapa_NF" not in df.columns:
        st.warning("Coluna Etapa_NF não encontrada.")
        return

    contagem = df["Etapa_NF"].value_counts().to_dict()
    # Ordem invertida: Aguardando no topo, Venda Ganha na base
    funil_data = [
        {"Etapa_NF": e, "Leads": contagem.get(e, 0)}
        for e in ORDEM_FUNIL
        if contagem.get(e, 0) > 0
    ]

    if not funil_data:
        st.info("Sem dados de funil para o período selecionado.")
        return

    funil_df = pd.DataFrame(funil_data)
    fig = px.funnel(
        funil_df,
        x="Leads", y="Etapa_NF",
        title="Funil de Vendas",
        color="Etapa_NF",
        color_discrete_map=COLOR_MAP,
        template=_tema(),
    )
    fig.update_traces(
        texttemplate="%{value:,.0f}",
        textposition="outside",
        textfont=dict(size=13, color=_BRANCO, family="sans-serif"),
    )
    fig.update_layout(showlegend=False)
    fig = _layout(fig, altura=440)
    st.plotly_chart(fig, use_container_width=True)


def cards_resultado(df: pd.DataFrame) -> None:
    """Cards de Venda Ganha e Venda Perdida lado a lado."""
    if "Etapa_NF" not in df.columns:
        return

    total     = len(df)
    ganhas    = int(df["Etapa_NF"].eq("Venda Ganha").sum())
    perdidas  = int(df["Etapa_NF"].eq("Venda Perdida").sum())
    p_ganhas  = f"{ganhas  / total:.1%}" if total else "0%"
    p_perdidas= f"{perdidas / total:.1%}" if total else "0%"

    c1, c2 = st.columns(2)
    c1.metric("Venda Ganha",   f"{ganhas:,.0f}",   f"{p_ganhas} do total",  delta_color="normal")
    c2.metric("Venda Perdida", f"{perdidas:,.0f}", f"{p_perdidas} do total", delta_color="inverse")


def card_acompanhamento(df: pd.DataFrame) -> None:
    """Card de Acompanhamento — leads de remarketing, fora do funil ativo."""
    if "Etapa_NF" not in df.columns:
        return

    total = len(df)
    qtd   = int(df["Etapa_NF"].eq("Acompanhamento").sum())
    perc  = f"{qtd / total:.1%}" if total else "0%"

    st.metric(
        label="Acompanhamento (remarketing)",
        value=f"{qtd:,.0f}",
        delta=f"{perc} do total",
        delta_color="off",
    )
    st.caption("Leads identificados como oportunidades futuras — fora do funil ativo.")


def grafico_onoff(df: pd.DataFrame) -> None:
    if "On_Off" not in df.columns:
        st.warning("Coluna On_Off não encontrada.")
        return

    resumo = _agrupar(df, "On_Off")
    if resumo.empty:
        return

    fig = px.pie(
        resumo,
        names="On_Off", values="Leads",
        hole=0.45, title="Distribuição On / Off",
        color="On_Off", color_discrete_map=COLOR_MAP,
    )
    fig.update_traces(
        textinfo="label+value+percent",
        textfont=dict(color="#ffffff", size=12),
    )
    fig = _layout(fig, altura=320)
    st.plotly_chart(fig, use_container_width=True)


def grafico_evolucao_diaria(df: pd.DataFrame) -> None:
    if "DataCadastro" not in df.columns:
        return

    serie = (
        df.dropna(subset=["DataCadastro"])
        .assign(Data=lambda d: d["DataCadastro"].dt.date)
        .groupby("Data")
        .size()
        .reset_index(name="Leads")
    )
    if serie.empty:
        return

    fig = px.line(
        serie, x="Data", y="Leads",
        markers=True, text="Leads",
        title="Evolução diária de leads",
        color_discrete_sequence=[_VERDE_BASE],
    )
    fig.update_traces(
        textposition="top center",
        textfont_color="#ffffff",
        line=dict(width=2),
        marker=dict(size=7),
    )
    fig = _layout(fig, altura=360)
    st.plotly_chart(fig, use_container_width=True)


# ── Aba Origem e Campanhas ────────────────────────────────────────────────────

def grafico_origem(df: pd.DataFrame) -> None:
    if "UtmSource" not in df.columns:
        st.warning("Coluna UtmSource não encontrada.")
        return
    df2 = df.copy()
    df2["UtmSource"] = _resolver_origem(df2)
    resumo = _agrupar(df2, "UtmSource", top=15)
    _barras_h(resumo, "Leads", "UtmSource", "Top origens de leads")


def grafico_campanha(df: pd.DataFrame) -> None:
    if "UtmCampaign" not in df.columns:
        st.warning("Coluna UtmCampaign não encontrada.")
        return
    resumo = _agrupar(df, "UtmCampaign", top=15)
    _barras_h(resumo, "Leads", "UtmCampaign", "Top campanhas")


def matriz_origem_etapa(df: pd.DataFrame) -> None:
    if not {"UtmSource", "Etapa_NF"}.issubset(df.columns):
        return
    df2 = df.copy()
    df2["UtmSource"] = _resolver_origem(df2)
    df2 = df2.dropna(subset=["Etapa_NF"])
    if df2.empty:
        return
    st.subheader("Matriz origem × etapa")
    st.dataframe(
        pd.crosstab(df2["UtmSource"], df2["Etapa_NF"]),
        use_container_width=True,
    )


# ── Aba Cidades e Cadastro ────────────────────────────────────────────────────

def grafico_cidades(df: pd.DataFrame) -> None:
    if "Cidade" not in df.columns:
        st.warning("Coluna Cidade não encontrada.")
        return
    resumo = _agrupar(df, "Cidade", top=20)
    _barras_h(resumo, "Leads", "Cidade", "Top cidades", altura=600)


def grafico_forma_cadastro(df: pd.DataFrame) -> None:
    if "FormaCadastro" not in df.columns:
        st.warning("Coluna FormaCadastro não encontrada.")
        return
    resumo = _agrupar(df, "FormaCadastro")
    _barras_h(resumo, "Leads", "FormaCadastro", "Leads por forma de cadastro", altura=400)


def matrizes_cidade_forma(df: pd.DataFrame) -> None:
    col_c, col_d = st.columns(2)
    if {"Cidade", "Etapa_NF"}.issubset(df.columns):
        df_v = df.dropna(subset=["Cidade", "Etapa_NF"])
        if not df_v.empty:
            m = pd.crosstab(df_v["Cidade"], df_v["Etapa_NF"])
            m["Total"] = m.sum(axis=1)
            col_c.subheader("Matriz cidade × etapa")
            col_c.dataframe(m.sort_values("Total", ascending=False).head(30), use_container_width=True)
    if {"FormaCadastro", "Etapa_NF"}.issubset(df.columns):
        df_v = df.dropna(subset=["FormaCadastro", "Etapa_NF"])
        if not df_v.empty:
            m = pd.crosstab(df_v["FormaCadastro"], df_v["Etapa_NF"])
            m["Total"] = m.sum(axis=1)
            col_d.subheader("Matriz forma de cadastro × etapa")
            col_d.dataframe(m.sort_values("Total", ascending=False), use_container_width=True)


# ── Aba Operação ──────────────────────────────────────────────────────────────

def grafico_produto(df: pd.DataFrame) -> None:
    if "Produto" not in df.columns:
        st.warning("Coluna Produto não encontrada.")
        return
    resumo = _agrupar(df, "Produto", top=20)
    _barras_h(resumo, "Leads", "Produto", "Leads por produto", altura=500)


def grafico_responsavel(df: pd.DataFrame) -> None:
    if not {"Responsavel", "Codigo"}.issubset(df.columns):
        st.warning("Colunas Responsavel e/ou Codigo não encontradas.")
        return

    df_valido = df.dropna(subset=["Responsavel"])
    df_valido = df_valido[df_valido["Responsavel"].astype(str).str.strip() != ""]

    if df_valido.empty:
        st.info("Sem dados de responsável para o período.")
        return

    agg: dict = {"Leads": ("Codigo", "count")}
    if "TempoTotal" in df_valido.columns:
        agg["Tempo Médio (dias)"] = ("TempoTotal", "mean")

    resumo = (
        df_valido.groupby("Responsavel")
        .agg(**agg)
        .reset_index()
        .sort_values("Leads", ascending=False)
        .head(20)
    )
    if "Tempo Médio (dias)" in resumo.columns:
        resumo["Tempo Médio (dias)"] = resumo["Tempo Médio (dias)"].round(1)

    _barras_h(resumo, "Leads", "Responsavel", "Leads por responsável", altura=500)

    st.subheader("Resumo por responsável")
    st.dataframe(resumo, hide_index=True, use_container_width=True)


# ── Aba Base Analítica ────────────────────────────────────────────────────────

def tabela_base(df: pd.DataFrame) -> None:
    colunas = [
        "Codigo", "Nome", "Produto", "Cidade", "DataCadastro",
        "FormaCadastro", "UtmCampaign", "UtmMedium", "UtmSource",
        "Etapa", "Status", "Etapa_NF", "On_Off", "Responsavel", "TempoTotal",
    ]
    df_exibir = df[[c for c in colunas if c in df.columns]]

    st.dataframe(df_exibir, hide_index=True, use_container_width=True)

    csv = df_exibir.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "Baixar base filtrada (CSV)",
        data=csv,
        file_name="base_crm_filtrada.csv",
        mime="text/csv",
    )
