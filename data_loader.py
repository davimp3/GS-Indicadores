import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

# O nome exato da sua aba na planilha
WORKSHEET_NAME = "Dados Brutos Jira"

@st.cache_data(ttl=600) # Cache de 10 minutos
def load_data():
    """
    Se conecta ao Google Sheets, carrega todos os dados e agora
    retorna o DataFrame E o timestamp exato da busca.
    """
    try:
        creds = st.secrets["connections"]["gsheets"]
        sa = gspread.service_account_from_dict(creds)
        spreadsheet = sa.open_by_url(creds["spreadsheet"])
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        
        all_values = worksheet.get_values()
        
        # O momento exato da busca, que será cacheado junto com os dados
        fetch_time = datetime.now()

        if not all_values:
            # Retorna uma tupla com um DataFrame vazio e o horário
            return pd.DataFrame(), fetch_time 

        headers = all_values[0]
        data = all_values[1:]
        df = pd.DataFrame(data, columns=headers)
        
        # Retorna a tupla com os dois valores
        return df, fetch_time

    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
        # Retorna a tupla mesmo em caso de erro
        return pd.DataFrame(), datetime.now()

