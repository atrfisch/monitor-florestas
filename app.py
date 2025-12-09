import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import random
from datetime import datetime

# Configuração Visual
st.set_page_config(page_title="Vigia da Floresta", page_icon="🔥", layout="wide")

# --- FUNÇÕES DE DADOS ---

def buscar_coords_cidade(nome_cidade):
    """Busca lat/lon e código da cidade no IBGE"""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    try:
        response = requests.get(url, timeout=5)
        for cidade in response.json():
            if cidade['nome'].lower() == nome_cidade.lower().strip():
                # O IBGE retorna lat/lon em outro endpoint, mas vamos simplificar
                # Usando uma API aberta de geocoding para pegar o centro da cidade
                geo_url = f"https://nominatim.openstreetmap.org/search?city={nome_cidade}&country=Brazil&format=json"
                geo_res = requests.get(geo_url, headers={'User-Agent': 'MonitorApp/1.0'})
                if geo_res.json():
                    lat = float(geo_res.json()[0]['lat'])
                    lon = float(geo_res.json()[0]['lon'])
                    return cidade['id'], cidade['nome'], lat, lon
    except Exception as e:
        pass
    return None, None, None, None

def gerar_dados_simulados(lat_centro, lon_centro, qtd=20):
    """
    Gera dados falsos PERTO da cidade apenas para demonstração
    caso a API oficial esteja fora do ar.
    """
    dados = []
    for _ in range(qtd):
        # Cria pontos aleatórios num raio próximo ao centro da cidade
        desvio_lat = random.uniform(-0.1, 0.1)
        desvio_lon = random.uniform(-0.1, 0.1)
        dados.append({
            'lat': lat_centro + desvio_lat,
            'lon': lon_centro + desvio_lon,
            'risco': random.randint(50, 100), # Risco de fogo
            'data': datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    return dados

def buscar_focos_inpe(codigo_ibge):
    """
    Tenta buscar dados reais do INPE.
    Obs: A API do INPE é aberta mas pode ser lenta.
    URL: http://queimadas.dgi.inpe.br/api/focos/
    """
    # URL oficial de focos das últimas 48h
    url = "https://queimadas.dgi.inpe.br/api/focos/?pais_id=33" 
    try:
        # Timeout curto para não travar o app se o INPE demorar
        response = requests.get(url, timeout=4) 
        if response.status_code == 200:
            focos = response.json()
            # Filtra apenas para o município escolhido (código IBGE)
            # O INPE as vezes usa código de 6 ou 7 digitos, verificamos ambos
            cod_6 = str(codigo_ibge)[:6]
            focos_cidade = [
                {
                    'lat': f['properties']['latitude'],
                    'lon': f['properties']['longitude'],
                    'risco': f['properties'].get('risco_fogo', 0),
                    'data': f['properties']['data_hora']
                }
                for f in focos 
                if str(f['properties']['id_municipio']) == str(codigo_ibge) or str(f['properties']['id_municipio']) == cod_6
            ]
            return focos_cidade, True # True = Dados Reais
    except:
        pass
    return [], False # False = Falha na API

# --- INTERFACE DO USUÁRIO ---

st.title("🔥 Vigia da Floresta: Monitor de Queimadas")
st.markdown("""
Este painel monitora focos de calor usando dados do **INPE (Programa Queimadas)**.
Focos de calor são o principal indicador de desmatamento em tempo real.
""")

cidade_input = st.text_input("Digite o nome da cidade para monitorar (ex: Altamira, Apuí):")

if cidade_input:
    with st.spinner(f"Localizando {cidade_input} no mapa..."):
        id_ibge, nome_oficial, lat, lon = buscar_coords_cidade(cidade_input)
        
    if id_ibge:
        st.success(f"📍 Monitorando: **{nome_oficial}**")
        
        # Tenta pegar dados reais, se falhar, gera simulados
        with st.spinner("Consultando satélites do INPE..."):
            dados, sao_reais = buscar_focos_inpe(id_ibge)
            
            if not sao_reais:
                st.warning(f"⚠️ A API do INPE está instável ou sem focos recentes para esta cidade. **Exibindo DADOS SIMULADOS** para fins de demonstração do sistema.")
                dados = gerar_dados_simulados(lat, lon)
            else:
                if len(dados) == 0:
                    st.info("Nenhum foco de calor detectado nas últimas 48h (Isso é uma boa notícia!). Gerando simulação para você ver o mapa.")
                    dados = gerar_dados_simulados(lat, lon)
                    sao_reais = False
                else:
                    st.success(f"📡 Dados oficiais obtidos! {len(dados)} focos detectados.")

        # --- EXIBIÇÃO DOS DADOS ---
        
        # 1. Métricas
        col1, col2 = st.columns(2)
        col1.metric("Focos Detectados", len(dados))
        risco_medio = sum([d['risco'] if isinstance(d['risco'], (int, float)) else 0 for d in dados]) / len(dados)
        col2.metric("Risco Médio de Fogo", f"{risco_medio:.0f}%")
        
        # 2. Mapa
        df_map = pd.DataFrame(dados)
        
        # Configuração do Mapa (Fogo = Vermelho/Laranja)
        layer = pdk.Layer(
            "ScatterplotLayer",
            df_map,
            get_position=["lon", "lat"],
            get_color=[255, 69, 0, 200], # Cor Laranja Fogo
            get_radius=800,
            pickable=True,
        )
        
        view_state = pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=8,
            pitch=0
        )
        
        r = pdk.Deck(
            layers=[layer], 
            initial_view_state=view_state,
            tooltip={"text": "Foco de Calor\nRisco: {risco}%"}
        )
        st.pydeck_chart(r)
        
        # 3. Ação (Ativismo)
        st.divider()
        st.subheader("📢 Tomar Atitude")
        
        tipo_dado = "Reais do INPE" if sao_reais else "Simulados (Teste)"
        msg = f"Olá, verifiquei no sistema Vigia da Floresta que há {len(dados)} focos de calor ativos na região de {nome_oficial}. Gostaria de solicitar fiscalização urgente."
        
        st.write(f"Envie um alerta baseado nesses dados ({tipo_dado}):")
        
        # Botão de Email
        link_email = f'<a href="mailto:?subject=Alerta de Fogo em {nome_oficial}&body={msg}" target="_blank"><button style="background-color:#d93025;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;">📧 Denunciar por E-mail</button></a>'
        st.markdown(link_email, unsafe_allow_html=True)

    else:
        st.error("Cidade não encontrada. Tente verificar a acentuação.")