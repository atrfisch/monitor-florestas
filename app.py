import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime, timedelta

# Configuração da Página
st.set_page_config(
    page_title="Dashboard MapBiomas",
    page_icon="📊",
    layout="wide"
)

# --- CONFIGURAÇÃO DA API ---
# Headers para evitar bloqueio (mimetizando um navegador real)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://plataforma.alerta.mapbiomas.org/"
}

URL_API = "https://plataforma.alerta.mapbiomas.org/api/v1/alerts"

# --- FUNÇÃO DE BUSCA DE DADOS ---
@st.cache_data(ttl=3600) # Cache de 1 hora para não sobrecarregar a API
def carregar_dados(dias_atras=30, limite=2000):
    """
    Busca os últimos X alertas para gerar as estatísticas.
    """
    data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
    
    params = {
        "published_at_from": data_inicio,
        "limit": limite,
        "sort_by": "published_at",
        "sort_order": "desc"
    }
    
    try:
        response = requests.get(URL_API, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        dados = response.json()
        
        # A API pode retornar dicionário {'data': [...]} ou lista direta [...]
        lista_alertas = dados.get('data', []) if isinstance(dados, dict) else dados
        
        if not lista_alertas:
            return pd.DataFrame()

        # Transformar em DataFrame para facilitar cálculos
        df = pd.DataFrame(lista_alertas)
        
        # Selecionar e limpar colunas importantes
        cols_desejadas = ['alert_code', 'area_ha', 'state', 'municipality', 'published_at']
        # Garante que as colunas existem antes de filtrar
        cols_existentes = [c for c in cols_desejadas if c in df.columns]
        df = df[cols_existentes]
        
        # Converter data
        df['published_at'] = pd.to_datetime(df['published_at'])
        df['Data'] = df['published_at'].dt.date # Cria coluna só com a data (sem hora)
        
        return df

    except Exception as e:
        st.error(f"Erro na conexão com MapBiomas: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("📊 Painel de Controle: Desmatamento Recente")
st.markdown("Análise baseada nos alertas validados publicados pelo **MapBiomas Alerta**.")

# Filtros na Barra Lateral
st.sidebar.header("Filtros")
dias = st.sidebar.slider("Período de Análise (dias):", 7, 90, 30)
limite_busca = st.sidebar.select_slider("Amostra de Alertas:", options=[500, 1000, 2000, 5000], value=1000)

if st.sidebar.button("Atualizar Dados"):
    st.cache_data.clear() # Limpa o cache para forçar nova busca

# Carregamento
with st.spinner(f"Baixando e processando os últimos {limite_busca} alertas..."):
    df = carregar_dados(dias_atras=dias, limite=limite_busca)

if not df.empty:
    # --- KPIs (Indicadores Principais) ---
    total_area = df['area_ha'].sum()
    total_alertas = len(df)
    estado_top = df['state'].value_counts().idxmax()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Área Total Detectada", f"{total_area:,.1f} ha")
    col2.metric("Total de Alertas", total_alertas)
    col3.metric("Estado + Crítico", estado_top)
    
    st.divider()

    # --- 1. EVOLUÇÃO TEMPORAL (Gráfico de Linha/Área) ---
    st.subheader("📅 Evolução Diária (Área Desmatada)")
    
    # Agrupar por dia
    df_tempo = df.groupby('Data')['area_ha'].sum().reset_index()
    
    chart_tempo = alt.Chart(df_tempo).mark_area(
        line={'color':'darkred'},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='white', offset=0),
                   alt.GradientStop(color='darkred', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('Data:T', title='Data de Publicação'),
        y=alt.Y('area_ha:Q', title='Área (ha)'),
        tooltip=['Data:T', 'area_ha:Q']
    ).properties(height=350)
    
    st.altair_chart(chart_tempo, use_container_width=True)
    
    # --- COLUNAS PARA RANKINGS ---
    col_est, col_mun = st.columns(2)
    
    # --- 2. RANKING DE ESTADOS (Gráfico de Barras) ---
    with col_est:
        st.subheader("🗺️ Top Estados (por Área)")
        df_uf = df.groupby('state')['area_ha'].sum().reset_index().sort_values('area_ha', ascending=False)
        
        chart_uf = alt.Chart(df_uf).mark_bar().encode(
            x=alt.X('area_ha:Q', title='Hectares'),
            y=alt.Y('state:N', sort='-x', title='Estado'),
            color=alt.value('#2E8B57'), # Cor Verde Floresta
            tooltip=['state', 'area_ha']
        )
        st.altair_chart(chart_uf, use_container_width=True)

    # --- 3. RANKING DE CIDADES (Tabela/Gráfico) ---
    with col_mun:
        st.subheader("🏙️ Top 10 Municípios")
        df_mun = df.groupby(['municipality', 'state'])['area_ha'].sum().reset_index()
        df_mun = df_mun.sort_values('area_ha', ascending=False).head(10)
        
        # Mostra como gráfico de barras horizontal
        chart_mun = alt.Chart(df_mun).mark_bar().encode(
            x=alt.X('area_ha:Q', title='Hectares'),
            y=alt.Y('municipality:N', sort='-x', title='Município'),
            color=alt.value('#FF8C00'), # Cor Laranja
            tooltip=['municipality', 'state', 'area_ha']
        )
        st.altair_chart(chart_mun, use_container_width=True)
        
    # --- TABELA DE DADOS BRUTOS ---
    with st.expander("📂 Ver lista completa dos dados baixados"):
        st.dataframe(df)

else:
    st.warning("Não foi possível carregar dados. O MapBiomas pode ter bloqueado a conexão ou não há alertas no período.")
    st.info("Tente clicar em 'Atualizar Dados' na barra lateral.")