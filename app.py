import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime

# Configuração
st.set_page_config(page_title="Monitor de Ar & Fumaça", page_icon="😷", layout="wide")

# --- SUA CHAVE DE API AQUI ---
# Para funcionar com dados reais, coloque sua chave entre as aspas abaixo.
# Exemplo: API_KEY = "a1b2c3d4e5..."
API_KEY = "0b4997e4bd1695c97b76a29a2222ec37" 

# --- CIDADES ALVO (AMAZÔNIA) ---
CIDADES = {
    "Porto Velho (RO)": {"lat": -8.7612, "lon": -63.9039},
    "Altamira (PA)": {"lat": -3.2033, "lon": -52.2064},
    "Manaus (AM)": {"lat": -3.1190, "lon": -60.0217},
    "Rio Branco (AC)": {"lat": -9.9754, "lon": -67.8249},
    "Lábrea (AM)": {"lat": -7.2590, "lon": -64.7981},
    "São Paulo (SP)": {"lat": -23.5505, "lon": -46.6333} # Para comparação
}

# --- FUNÇÕES ---
def buscar_poluicao(lat, lon):
    """
    Busca dados de qualidade do ar (PM2.5) na API OpenWeatherMap.
    PM2.5 é a principal partícula gerada por queimadas.
    """
    if not API_KEY:
        return None, "Sem Chave"

    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # O OpenWeather retorna um índice AQI (1=Bom, 5=Péssimo) e componentes brutos
            return data['list'][0], "Sucesso"
        else:
            return None, f"Erro {response.status_code}"
    except Exception as e:
        return None, str(e)

def classificar_aqi(aqi_valor):
    """Traduz o índice numérico para texto e cor"""
    mapa = {
        1: ("Boa", "#00e400"),      # Verde
        2: ("Razoável", "#ffff00"), # Amarelo
        3: ("Moderada", "#ff7e00"), # Laranja
        4: ("Ruim", "#ff0000"),     # Vermelho
        5: ("Péssima (Fumaça)", "#8f3f97") # Roxo
    }
    return mapa.get(aqi_valor, ("Desconhecido", "#grey"))

# --- INTERFACE ---
st.title("🌫️ Monitor de Fumaça na Amazônia")
st.markdown("""
As queimadas na floresta liberam partículas finas (**PM2.5**) que viajam quilômetros e destroem a saúde humana.
Este painel monitora a qualidade do ar em tempo real usando dados globais.
""")

if not API_KEY:
    st.warning("⚠️ **Atenção:** O app está rodando em **Modo de Simulação** porque a API Key não foi configurada.")
    st.info("Para ver dados reais, crie uma conta grátis no OpenWeatherMap.org e cole a chave no código.")

# Seletor de Cidade
cidade_escolhida = st.selectbox("Escolha uma cidade para monitorar:", list(CIDADES.keys()))

if cidade_escolhida:
    coords = CIDADES[cidade_escolhida]
    
    # Busca Dados
    dados_ar, status = buscar_poluicao(coords['lat'], coords['lon'])
    
    # --- SIMULAÇÃO (Se não tiver chave) ---
    if status == "Sem Chave":
        import random
        # Simula um dado realista de cidade com queimada
        aqi_simulado = random.choice([3, 4, 5]) if "SP" not in cidade_escolhida else 2
        pm2_5_simulado = aqi_simulado * 25.5
        dados_ar = {
            "main": {"aqi": aqi_simulado},
            "components": {"pm2_5": pm2_5_simulado, "co": 300.0, "no2": 10.0}
        }
    # ---------------------------------------

    if dados_ar:
        aqi = dados_ar['main']['aqi']
        pm25 = dados_ar['components']['pm2_5']
        
        texto_qualidade, cor_indicador = classificar_aqi(aqi)
        
        # EXIBIÇÃO VISUAL DE IMPACTO
        st.divider()
        col_destaque, col_detalhe = st.columns([1, 2])
        
        with col_destaque:
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border-radius: 10px; background-color: {cor_indicador}; color: black;">
                <h2 style="margin:0">Qualidade do Ar</h2>
                <h1 style="font-size: 60px; margin:0">{texto_qualidade}</h1>
                <p>Índice AQI: {aqi}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_detalhe:
            st.subheader("Concentração de Partículas")
            c1, c2 = st.columns(2)
            c1.metric("PM2.5 (Fumaça Fina)", f"{pm25} µg/m³", help="Partículas finas geradas por combustão (fogo). São as mais perigosas pois entram na corrente sanguínea.")
            c2.metric("CO (Monóxido de Carbono)", f"{dados_ar['components']['co']} µg/m³", help="Gás tóxico liberado por queimadas.")
            
            # Barrinha de progresso visual
            st.write("Nível de Perigo (PM2.5):")
            st.progress(min(pm25/150, 1.0)) # 150 é muito alto
            
            if aqi >= 4:
                st.error("🚨 ALERTA DE SAÚDE: A concentração de fumaça está alta. Isso indica prováveis queimadas próximas ou transporte de fumaça pela atmosfera.")
            elif aqi == 3:
                st.warning("⚠️ Atenção: Grupos sensíveis (crianças e idosos) podem sofrer efeitos respiratórios.")
            else:
                st.success("✅ O ar está limpo neste momento.")

        # --- AÇÃO ATIVISTA ---
        st.divider()
        st.subheader("📢 Transforme esse dado em ação")
        msg = f"Alerta de Fumaça: A qualidade do ar em {cidade_escolhida} está classificada como '{texto_qualidade}' (PM2.5: {pm25}). As queimadas estão sufocando nossa cidade."
        
        # Link para compartilhar no Twitter/X
        import urllib.parse
        msg_encoded = urllib.parse.quote(msg)
        st.markdown(f'[🐦 Postar no X (Twitter)](https://twitter.com/intent/tweet?text={msg_encoded})', unsafe_allow_html=True)

    else:
        st.error("Erro ao obter dados. Verifique a conexão.")