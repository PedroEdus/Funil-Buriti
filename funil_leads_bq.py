import os
from datetime import datetime

import gspread
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2.service_account import Credentials
from unidecode import unidecode

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET    = os.getenv("BQ_DATASET", "buriti_marketing_silver")
TABELA     = "funil_leads"
SHEETS_ID  = os.getenv("SHEETS_ID")
ABA_FUNIL  = os.getenv("ABA_FUNIL", "funil")
ABA_VENDA  = os.getenv("ABA_VENDA", "venda")

if not PROJECT_ID:
    raise ValueError("GCP_PROJECT_ID não encontrado no .env")
if not SHEETS_ID:
    raise ValueError("SHEETS_ID não encontrado no .env")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

COLUNAS_ESPERADAS = [
    "Codigo", "Nome", "Produto", "Cidade", "DataCadastro", "DataAlteracao",
    "UtmCampaign", "UtmMedium", "UtmSource", "FormaCadastro", "OrigemContato",
    "Finalidade", "Etapa", "Status", "Email", "Telefone", "Formulario",
    "Responsavel", "TempoTotal",
]

COLUNAS_TEXTO = [
    "Nome", "Produto", "Cidade", "UtmCampaign", "UtmMedium", "UtmSource",
    "FormaCadastro", "OrigemContato", "Finalidade", "Etapa", "Status",
    "Formulario", "Responsavel",
]


# ── Clientes ──────────────────────────────────────────────────────────────────

def criar_clients():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    gc = gspread.authorize(creds)
    bq = bigquery.Client(project=PROJECT_ID)
    return gc, bq


# ── Extração ──────────────────────────────────────────────────────────────────

def ler_aba(gc: gspread.Client, aba: str, origem: str) -> pd.DataFrame:
    planilha = gc.open_by_key(SHEETS_ID)
    ws = planilha.worksheet(aba)
    dados = ws.get_all_records()
    df = pd.DataFrame(dados)
    df["origem"] = origem
    print(f"  [{aba}] {len(df)} linhas lidas")
    return df


# ── Transformação ─────────────────────────────────────────────────────────────

def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in COLUNAS_ESPERADAS if c in df.columns]
    df = df[cols + ["origem"]].copy()

    for col in COLUNAS_TEXTO:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.title()
                .replace({"": None, "Nan": None, "None": None})
            )

    for col_data in ["DataCadastro", "DataAlteracao"]:
        if col_data in df.columns:
            df[col_data] = pd.to_datetime(
                df[col_data], dayfirst=True, errors="coerce"
            ).dt.date

    for col in ("Email", "Telefone"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace({"": None, "Nan": None, "None": None})

    if "Codigo" in df.columns:
        df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce").astype("Int64")
    if "TempoTotal" in df.columns:
        df["TempoTotal"] = pd.to_numeric(df["TempoTotal"], errors="coerce").astype("Int64")

    return df


def _norm(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).apply(lambda x: unidecode(x).upper().strip())


def derivar_campos(df: pd.DataFrame) -> pd.DataFrame:
    df["On_Off"] = np.where(
        df["FormaCadastro"].str.contains(r"Meta|Google", case=False, na=False),
        "On",
        "Off",
    )

    etapa_n  = _norm(df.get("Etapa",  pd.Series([""] * len(df), index=df.index)))
    status_n = _norm(df.get("Status", pd.Series([""] * len(df), index=df.index)))

    conds = [
        (etapa_n == "FECHAMENTO") & (status_n == "VENDA GANHA"),
        etapa_n == "VENDA PERDIDA",
        etapa_n.isin(["FECHAMENTO", "NEGOCIACAO"]),
        status_n.str.contains(r"VISITA|AGENDAMENTO|AGENDADO", na=False),
        etapa_n == "MARKETING DIGITAL",
        etapa_n.isin(["PROSPECCAO", "QUALIFICACAO", "ATENDIMENTO"]),
        etapa_n == "ACOMPANHAMENTO",
    ]
    choices = [
        "Venda Ganha",
        "Venda Perdida",
        "Negociação",
        "Visita Agendada",
        "Aguardando Atendimento",
        "Em Atendimento",
        "Acompanhamento",
    ]
    df["Etapa_NF"] = np.select(conds, choices, default="Outros")

    return df


# ── Carga ─────────────────────────────────────────────────────────────────────

def carregar_bigquery(df: pd.DataFrame, client: bigquery.Client) -> None:
    table_full = f"{PROJECT_ID}.{DATASET}.{TABELA}"
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        autodetect=True,
    )
    job = client.load_table_from_dataframe(df, table_full, job_config=job_config)
    job.result()
    print(f"  Carga concluída: {table_full} ({len(df)} linhas)")


# ── Execução ──────────────────────────────────────────────────────────────────

def main():
    print("Criando clientes GCP / gspread...")
    gc, bq = criar_clients()

    print("\nLendo Google Sheets...")
    df_funil = ler_aba(gc, ABA_FUNIL, "funil")
    df_venda = ler_aba(gc, ABA_VENDA, "venda")

    df = pd.concat([df_funil, df_venda], ignore_index=True)
    print(f"\n{len(df)} linhas no total antes do tratamento")

    print("Normalizando colunas...")
    df = normalizar(df)

    print("Derivando On_Off e Etapa_NF...")
    df = derivar_campos(df)

    df["data_carga"] = datetime.now()

    print(f"\nPrevia ({len(df)} linhas):")
    cols_preview = [c for c in ["Codigo", "Etapa", "Status", "Etapa_NF", "On_Off", "origem"] if c in df.columns]
    print(df[cols_preview].head(10).to_string(index=False))

    print("\nCarregando no BigQuery...")
    carregar_bigquery(df, bq)

    print("\nProcesso finalizado.")


if __name__ == "__main__":
    main()
