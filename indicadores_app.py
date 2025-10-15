import pandas as pd 
import streamlit as st
import plotly.express as px 
import numpy as np
import re # Importa a biblioteca de expressões regulares
from datetime import timedelta, datetime
# Importa a função de carregamento de dados
from data_loader import load_data

st.set_page_config(
    layout="wide"
)

# Função para converter o tempo do formato "Xh Ym" para horas decimais
def converter_para_horas(tempo_str):
    if pd.isna(tempo_str) or tempo_str == '':
        return np.nan

    tempo_str = str(tempo_str).strip()
    
    # Tenta o formato "Xh Ym" 
    try:
        is_negative = tempo_str.startswith('-')
        clean_str = tempo_str[1:] if is_negative else tempo_str
        
        horas = 0
        minutos = 0

        match_h = re.search(r'(\d+)\s*h', clean_str)
        if match_h:
            horas = int(match_h.group(1))
        
        match_m = re.search(r'(\d+)\s*m', clean_str)
        if match_m:
            minutos = int(match_m.group(1))
        
        if match_h or match_m:
            total_horas = horas + minutos / 60.0
            return total_horas
    except:
        pass 

    # Tenta o formato "HH:MM:SS" como alternativa
    try:
        partes = tempo_str.split(':')
        if len(partes) == 2: # Formato MM:SS
            minutos, segundos = map(float, partes)
            return minutos / 60 + segundos / 3600
        elif len(partes) == 3: # Formato HH:MM:SS
            horas, minutos, segundos = map(float, partes[0:2] + [partes[2].split('.')[0]])
            return horas + minutos / 60 + segundos / 3600
    except (ValueError, IndexError):
        return np.nan 
        
    return np.nan


# --- CARREGAMENTO DE DADOS ---
# CORREÇÃO: A função retorna dois valores (o DataFrame e o timestamp)
# e agora estamos recebendo os dois corretamente.
df_jira, last_update_time = load_data()


# --- TÍTULO E ÚLTIMA ATUALIZAÇÃO ---
st.title("Indicadores SLA 📉")
# O timestamp reflete a atualização da API, não o refresh da página
st.caption(f"Última atualização dos dados: {last_update_time.strftime('%d/%m/%Y às %H:%M:%S')}")


# --- PRÉ-PROCESSAMENTO ---
if not df_jira.empty:
    df_jira['Created'] = pd.to_datetime(df_jira['Created'], errors='coerce')
    df_jira['primeira_resposta_horas'] = df_jira['Time to first response'].apply(converter_para_horas)
    df_jira['tempo_resolucao_horas'] = df_jira['Time to resolution'].apply(converter_para_horas)
else:
    st.warning("Nenhum dado foi carregado. Verifique a conexão e o nome da aba na função load_data.")

# --- BARRA LATERAL DE FILTROS ---
st.sidebar.title("Filtros Gerais")

if not df_jira.empty and 'Created' in df_jira.columns and not df_jira['Created'].isnull().all():
    min_date = df_jira['Created'].min().date()
    max_date = df_jira['Created'].max().date()

    filtro_data_geral = st.sidebar.date_input(
        "Selecione uma Data",
        min_value=min_date, 
        max_value=max_date,
        value=(min_date, max_date)
    )
    st.sidebar.divider()
    
    st.sidebar.write("Cliente")
    lista_clientes = df_jira['Organizations'].dropna().unique().tolist()
    filtro_cliente = st.sidebar.multiselect("Selecione o(s) Cliente(s)", options=lista_clientes)
    
    st.sidebar.divider()
    
    st.sidebar.write("Issue Type")
    lista_issuetype = df_jira['Issue Type'].dropna().unique().tolist()
    filtro_issuetype = st.sidebar.multiselect("Selecione o(s) Issue Type(s)", options=lista_issuetype)

    lista_status = df_jira['Status'].dropna().unique().tolist()
    filtro_status = st.sidebar.multiselect("Selecione o(s) Status", options=lista_status)

    # --- APLICAÇÃO DOS FILTROS ---
    if len(filtro_data_geral) == 2:
        start_date, end_date = filtro_data_geral
        mask_data = (df_jira['Created'].dt.date >= start_date) & (df_jira['Created'].dt.date <= end_date)
        df_filtrado = df_jira[mask_data]
        st.write(f"Período Selecionado: de {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
    else:
        df_filtrado = pd.DataFrame()
        st.write("Por favor, selecione um período de data válido (início e fim).")

    if filtro_cliente:
        df_filtrado = df_filtrado[df_filtrado['Organizations'].isin(filtro_cliente)]

    if filtro_issuetype:
        df_filtrado = df_filtrado[df_filtrado['Issue Type'].isin(filtro_issuetype)]

    if filtro_status:
        df_final_filtrado = df_filtrado[df_filtrado['Status'].isin(filtro_status)]
    else:
        df_final_filtrado = df_filtrado

    # --- CÁLCULO DE MÉTRICAS (COM MEDIANA) ---
    status_finalizados = ['Entregue', 'Resolvido']
    ticket_aberto = df_final_filtrado[~df_final_filtrado['Status'].isin(status_finalizados)].shape[0]
    ticket_entregue = df_final_filtrado[df_final_filtrado['Status'].isin(status_finalizados)].shape[0]
    
    # FOCO NA MEDIANA: O cálculo agora usa .median() para o tempo "típico"
    primeira_resposta_mediana = df_final_filtrado['primeira_resposta_horas'].median() * 60 # Em minutos
    tempo_conclusao_mediana = df_final_filtrado['tempo_resolucao_horas'].median() # Em horas
    
    total_tickets = df_final_filtrado.shape[0]
    clientes_atendidos = df_final_filtrado['Organizations'].nunique()

    # --- CÁLCULOS DO PERÍODO ANTERIOR (COM MEDIANA) ---
    if len(filtro_data_geral) == 2:
        duration = end_date - start_date
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - duration

        df_anterior = df_jira[(df_jira['Created'].dt.date >= prev_start_date) & (df_jira['Created'].dt.date <= prev_end_date)]
        if filtro_cliente:
            df_anterior = df_anterior[df_anterior['Organizations'].isin(filtro_cliente)]
        if filtro_issuetype:
            df_anterior = df_anterior[df_anterior['Issue Type'].isin(filtro_issuetype)]
        if filtro_status:
            df_anterior_filtrado = df_anterior[df_anterior['Status'].isin(filtro_status)]
        else:
            df_anterior_filtrado = df_anterior
            
        total_ticket_anterior = df_anterior_filtrado.shape[0]
        ticket_aberto_anterior = df_anterior_filtrado[~df_anterior_filtrado['Status'].isin(status_finalizados)].shape[0]
        ticket_entregue_anterior = df_anterior_filtrado[df_anterior_filtrado['Status'].isin(status_finalizados)].shape[0]
        clientes_atendidos_anterior = df_anterior_filtrado['Organizations'].nunique()
        # FOCO NA MEDIANA: Comparação com a mediana do período anterior
        primeira_resposta_anterior = df_anterior_filtrado['primeira_resposta_horas'].median() * 60 # Em minutos
        tempo_conclusao_anterior = df_anterior_filtrado['tempo_resolucao_horas'].median() # Em horas
    else: 
        total_ticket_anterior, ticket_aberto_anterior, ticket_entregue_anterior, clientes_atendidos_anterior, primeira_resposta_anterior, tempo_conclusao_anterior = (0, 0, 0, 0, 0, 0)

    def calcular_delta(atual, anterior):
        if pd.isna(anterior) or anterior == 0 or pd.isna(atual): return None
        variacao = ((atual - anterior) / anterior) * 100
        return f"{variacao:.1f}%"

    # FOCO NA MEDIANA: Deltas calculados com base na mediana
    delta_pr = calcular_delta(primeira_resposta_mediana, primeira_resposta_anterior)
    delta_tc = calcular_delta(tempo_conclusao_mediana, tempo_conclusao_anterior)
    clientes_atendidos_delta = calcular_delta(clientes_atendidos, clientes_atendidos_anterior)
    ticket_delta_total = calcular_delta(total_tickets, total_ticket_anterior)
    ticket_delta_aberto = calcular_delta(ticket_aberto, ticket_aberto_anterior)
    ticket_delta_encerrado = calcular_delta(ticket_entregue, ticket_entregue_anterior)

    # --- VISUALIZAÇÃO ---
    st.divider()
    colquantidade, coltickets, coltempo = st.columns([30,30,40])
    with colquantidade:
        st.subheader("Relatório de Tickets")
        st.metric("Total de Tickets:", value=total_tickets, delta=ticket_delta_total, delta_color="inverse")
        st.metric("Tickets em Aberto:", value=ticket_aberto, delta=ticket_delta_aberto, delta_color="inverse")
    with coltickets: 
        st.subheader("Clientes")
        st.metric("Total de Clientes Atendidos:", value=clientes_atendidos, delta=clientes_atendidos_delta, delta_color="inverse") 
        st.metric("Tickets Finalizados:", value=ticket_entregue, delta=ticket_delta_encerrado, delta_color="inverse")
    with coltempo:
        st.subheader("Tempo de Resposta (Mediana)")
        # FOCO NA MEDIANA: Exibe apenas a mediana e seu delta
        st.metric("Primeira Resposta:", value=f"{primeira_resposta_mediana:.2f} min" if not pd.isna(primeira_resposta_mediana) else "N/A", delta=delta_pr, delta_color="inverse")
        st.metric("Resolução:", value=f"{tempo_conclusao_mediana:.1f} horas" if not pd.isna(tempo_conclusao_mediana) else "N/A", delta=delta_tc, delta_color="inverse")

    st.divider()

    st.subheader("Ranking de Chamados por Cliente")
    ranking_data = df_final_filtrado.groupby(['Organizations', 'Issue Type']).size().reset_index(name='Quantidade')
    if not ranking_data.empty:
        total_por_org = ranking_data.groupby('Organizations')['Quantidade'].sum().sort_values(ascending=False).index
        ranking_data['Organizations'] = pd.Categorical(ranking_data['Organizations'], categories=total_por_org, ordered=True)
        ranking_data = ranking_data.sort_values('Organizations')
        color_map = {'Bug': '#591C21', 'HelpDesk Support': '#D8B08C', 'New Feature': '#034159'}
        grafico_ranking = px.bar(
            ranking_data, x='Organizations', y='Quantidade', color='Issue Type',
            title="Ranking de Chamados por Cliente e Tipo",
            labels={'Organizations': 'Cliente', 'Quantidade': 'Total de Tickets', 'Issue Type': 'Tipo de Chamado'},
            color_discrete_map=color_map, text_auto=True
        )
        st.plotly_chart(grafico_ranking, use_container_width=True)

    st.divider()

    colissuetype, colticketstatus = st.columns([50, 50])
    with colissuetype:
        st.subheader("Distribuição por Issue Type")
        data_pie = df_final_filtrado['Issue Type'].value_counts().reset_index()
        data_pie.columns = ['Issue Type', 'Quantidade']
        color_map_pie = {'Bug': '#591C21', 'HelpDesk Support': '#D8B08C', 'New Feature': '#034159'}
        pie_chart = px.pie(data_pie, values='Quantidade', names='Issue Type', color='Issue Type', color_discrete_map=color_map_pie)
        pie_chart.update_traces(textinfo='percent+value')
        st.plotly_chart(pie_chart, use_container_width=True)

    with colticketstatus:
        st.subheader("Distribuição por Status")
        data_bar = df_final_filtrado['Status'].value_counts().reset_index()
        data_bar.columns = ['Status', 'Quantidade']
        data_bar['Categoria'] = np.where(data_bar['Status'].isin(['Resolvido', 'Entregue']), 'Finalizado', 'Em Andamento')
        color_map_bar = {'Finalizado': '#D2E8E3', 'Em Andamento': '#69A6D1'}
        bar_chart = px.bar(data_bar, x='Quantidade', y='Status', orientation='h', text_auto=True, color='Categoria', color_discrete_map=color_map_bar)
        st.plotly_chart(bar_chart, use_container_width=True)

else:
    st.warning("Nenhum dado foi carregado. Verifique a conexão e o nome da aba na função load_data.")

