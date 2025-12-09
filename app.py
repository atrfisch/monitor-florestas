import streamlit as st
import requests

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Monitor de Fumaça Brasil", page_icon="🌫️", layout="centered")

# --- SEGURANÇA ---
# Em vez de colocar a chave aqui, mandamos o Streamlit buscar nos "segredos" do servidor
try:
    API_KEY = st.secrets["OPENWEATHER_KEY"]
except FileNotFoundError:
    st.error("Chave de API não encontrada. Configure os 'Secrets' no painel do Streamlit Cloud.")
    st.stop()
# --- FUNÇÕES ---

def get_lat_lon(nome_cidade):
    """
    Converte o nome da cidade (ex: 'Cuiabá') em Latitude e Longitude reais.
    """
    # Adicionamos ",BR" para garantir que busque no Brasil
    query = f"{nome_cidade},BR"
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=1&appid={API_KEY}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if not data:
            return None, None, "Cidade não encontrada. Tente verificar a grafia."
            
        lat = data[0]['lat']
        lon = data[0]['lon']
        nome_oficial = f"{data[0]['name']} - {data[0]['state']}"
        return lat, lon, nome_oficial
        
    except Exception as e:
        return None, None, f"Erro de conexão: {str(e)}"

def get_air_quality(lat, lon):
    """
    Busca os dados de poluição para a coordenada exata.
    """
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        # Retorna o primeiro item da lista (dados atuais)
        return data['list'][0]
    except:
        return None

def traduzir_aqi(aqi):
    """
    Traduz o índice numérico (1-5) para texto e cor.
    1 = Bom, 5 = Péssimo
    """
    if aqi == 1: return "Ótima", "#2ecc71", "O ar está limpo. Aproveite o dia."
    if aqi == 2: return "Razoável", "#f1c40f", "Aceitável, mas sensíveis devem ter cautela."
    if aqi == 3: return "Moderada", "#e67e22", "Grupos sensíveis (idosos/crianças) podem sentir efeitos."
    if aqi == 4: return "Ruim", "#e74c3c", "Atenção: Evite exercícios ao ar livre."
    if aqi == 5: return "Péssima (Perigo)", "#8e44ad", "ALERTA: Fumaça intensa. Use máscara e feche janelas."
    return "Erro", "#95a5a6", "Sem dados"

# --- INTERFACE DO USUÁRIO ---

st.title("🌫️ Monitor de Fumaça Brasil")
st.markdown("Verifique a qualidade do ar em **qualquer cidade** do país em tempo real.")

# 1. Entrada de Dados
cidade_input = st.text_input("Digite o nome da cidade:", placeholder="Ex: Manaus, Cuiabá, São Paulo...")

if cidade_input:
    with st.spinner(f"Procurando '{cidade_input}' no mapa..."):
        # Passo 1: Geocoding (Achar a cidade)
        lat, lon, nome_encontrado = get_lat_lon(cidade_input)
        
    if lat and lon:
        st.success(f"Localizado: **{nome_encontrado}**")
        
        # Passo 2: Buscar Poluição Real
        with st.spinner("Analisando sensores de ar..."):
            dados = get_air_quality(lat, lon)
            
        if dados:
            # Extrair dados principais
            aqi = dados['main']['aqi']
            pm25 = dados['components']['pm2_5'] # Partículas finas (Fumaça)
            co = dados['components']['co']       # Monóxido de Carbono
            
            status_texto, cor, recomendacao = traduzir_aqi(aqi)
            
            # --- EXIBIÇÃO DO RESULTADO ---
            st.markdown("---")
            
            # Card Principal Colorido
            st.markdown(f"""
            <div style="background-color: {cor}; padding: 20px; border-radius: 10px; text-align: center; color: white; text-shadow: 1px 1px 2px black;">
                <h3 style="margin:0">Qualidade do Ar</h3>
                <h1 style="font-size: 60px; margin:0">{status_texto}</h1>
                <p style="font-size: 18px;">{recomendacao}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("") # Espaço
            
            # Métricas Detalhadas
            c1, c2, c3 = st.columns(3)
            c1.metric("PM2.5 (Fumaça Fina)", f"{pm25} µg/m³", delta="-15 (OMS)" if pm25 > 15 else "Ok")
            c2.metric("Índice AQI", f"{aqi}/5")
            c3.metric("CO (Monóxido)", f"{co} µg/m³")
            
            st.info("""
            **O que é PM2.5?** São partículas muito finas (2.5 micra) geradas principalmente por **queimadas** e escapamentos. 
            Elas entram fundo no pulmão e corrente sanguínea. A OMS recomenda níveis abaixo de 15 µg/m³.
            """)
            
            # --- BOTÃO DE ENGAJAMENTO ---
            st.markdown("### 📢 Faça barulho")
            texto_share = f"Atenção {nome_encontrado}: A qualidade do ar está {status_texto} (PM2.5: {pm25}). Dados do Monitor de Fumaça."
            link_twitter = f"https://twitter.com/intent/tweet?text={texto_share}"
            
            st.markdown(f"[🐦 Compartilhar Situação no Twitter]({link_twitter})")
            
        else:
            st.error("Erro ao obter dados meteorológicos.")
            
    else:
        st.warning(nome_encontrado) # Mostra mensagem de erro da função get_lat_lon
        
