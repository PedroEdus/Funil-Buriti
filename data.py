import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv()

PROJECT_ID = "buriti-marketing-analytics"
DATASET    = "buriti_marketing_silver"
TABELA     = "funil_leads"

_QUERY = f"""
SELECT * EXCEPT(row_num)
FROM (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY Codigo
      ORDER BY data_carga DESC
    ) AS row_num
  FROM `{PROJECT_ID}.{DATASET}.{TABELA}`
)
WHERE row_num = 1
"""


def _criar_client() -> bigquery.Client:
    try:
        if "gcp_service_account" in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return bigquery.Client(credentials=credentials, project=PROJECT_ID)
    except Exception:
        pass
    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=3600)
def carregar_leads() -> pd.DataFrame:
    client = _criar_client()
    df = client.query(_QUERY).to_dataframe()

    for col in ("DataCadastro", "DataAlteracao"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "TempoTotal" in df.columns:
        df["TempoTotal"] = pd.to_numeric(df["TempoTotal"], errors="coerce")

    return df
