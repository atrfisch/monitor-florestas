import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import random
from datetime import datetime

# Configuração Visual
st.set_page_config(page_title="Vigia da Floresta", page_icon="🔥", layout="wide")

# --- BANCO DE DADOS INTERNO (Para não depender de APIs externas) ---
# Adicionei as principais cidades do arco do desmatamento aqui
CIDADES_FIXAS = {
    "altamira": {"id": "1500602", "lat": -3.2033, "lon": -52.2064, "nome": "Altamira (PA)"},
    "apui": {"id": "1300029", "lat": -7.1947, "lon": -59.8961, "nome": "Apuí (AM)"},
    "labrea": {"id": "1302405", "lat": -7.2590, "lon": -64.7981, "nome": "Lábrea (AM)"},
    "porto velho": {"id": "1100205", "lat": -8.7612, "lon": -63.9039, "nome": "Porto Velho (RO)"},
    "sao felix do xingu": {"id": "1507300", "lat": -6.6447, "lon": -51.9950, "nome": "São Félix do Xingu (PA)"},
    "novo progresso": {"id": "1505031", "lat": -7.0390, "lon": -55.4339, "nome": "Novo Progresso (PA)"},
    "itaituba": {"id": "1503606", "lat": -4.2758, "lon": -55.9836, "nome": "Itaituba (PA)"},
    "colniza": {"id": "5103254", "lat": -9.3444, "lon": -59.0253, "nome": "Colniza (MT)"},
    "manaus": {"id": "1302603", "lat": -3.1190, "lon": -60.0217, "nome": "Manaus (AM)"}
}

# --- FUNÇÕES ---

def normalizar_texto(texto):
    """Remove acentos e deixa minusculo para facilitar busca"""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', texto)
    return u"".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()

def buscar_coords_cidade(nome_cidade):
    nome_norm = normalizar_texto(nome_cidade)
    
    # 1. Tenta buscar no nosso banco interno (Mais rápido e seguro)
    if nome_norm in CIDADES_FIXAS:
        cidade = CIDADES_FIXAS[nome_norm]
        return cidade['id'], cidade['nome'], cidade['lat'], cidade['lon']
    
    # 2. Se não achar, tenta buscar na API do IBGE/OpenStreet (Fallback)
    try:
        # Busca ID no IBGE
        url_ibge = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
        res_ibge = requests.get(url_ibge, timeout=3)
        municipios = res_ibge.json()
        
        id_ibge = None
        nome_oficial = None
        
        for mun in municipios:
            if normalizar_texto(mun['nome']) == nome_norm:
                id_ibge = mun['id']
                nome_oficial = mun['nome']
                break
        
        if id_ibge:
            # Busca Coordenadas no Nominatim (Pode falhar por bloqueio)
            headers = {'User-Agent': 'MonitorAppStudent/1.0'}
            url_geo = f"https://nominatim.openstreetmap.org/search?city={nome_cidade}&country=Brazil&format=json"
            res_geo = requests.get(url_geo, headers=headers, timeout=3)
            if res_geo.status_code == 200 and len(res_geo.json()) > 0:
                lat = float(res_geo.json()[0]['lat'])
                lon = float(res_geo.json()[0]['lon'])
                return id_ibge, nome_oficial, lat, lon
            else:
                # Se achou a cidade mas não as coordenadas, chuta o centro do PA
                return id_ibge, nome_oficial, -3.0, -52.0
                
    except Exception as e:
        st.error(f"Erro técnico na busca: {e}")
    
    return None, None, None, None

def gerar_dados_simulados(lat_centro, lon_centro, qtd=30):
    dados = []
    for _ in range(qtd):
        desvio_lat = random.uniform(-0.15, 0.15)
        desvio_lon = random.uniform(-0.15, 0.15)
        dados.append({
            'lat': lat_centro + desvio_lat,
            'lon': lon_centro + desvio_lon,
            'risco': random.randint(40, 100),
            'data': datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    return dados

def buscar_focos_inpe(codigo_ibge):
    # Tenta buscar dados reais
    url = "https://queimadas.dgi.inpe.br/api/focos/?pais_id=33" 
    try:
        response = requests.get(url, timeout=3) 
        if response.status_code == 200:
            focos = response.json()
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
            return focos_cidade, True
    except:
        pass
    return [], False

# --- INTERFACE ---

st.title("🔥 Vigia da Floresta: Monitor de Queimadas")
st.info("Dica: Tente buscar por **Altamira**, **Apui**, **Labrea** ou **Porto Velho**.")

cidade_input = st.text_input("Digite o nome da cidade:")

if cidade_input:
    id_ibge, nome_oficial, lat, lon = buscar_coords_cidade(cidade_input)
    
    if id_ibge:
        st.success(f"📍 Cidade localizada: **{nome_oficial}**")
        
        # Busca dados (Reais ou Simulados)
        dados, sao_reais = buscar_focos_inpe(id_ibge)
        
        if not sao_reais or len(dados) == 0:
            st.warning("⚠️ Dados em tempo real indisponíveis ou sem focos agora. **Exibindo SIMULAÇÃO**.")
            dados = gerar_dados_simulados(lat, lon)
            sao_reais = False
        else:
            st.success(f"📡 Dados REAIS do INPE obtidos! {len(dados)} focos.")

        # Mapa
        df_map = pd.DataFrame(dados)
        
        layer = pdk.Layer(
            "ScatterplotLayer",
            df_map,
            get_position=["lon", "lat"],
            get_color=[255, 50, 0, 180],
            get_radius=1000,
            pickable=True,
        )
        
        view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=8)
        
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
        
        # Ação
        st.divider()
        msg = f"Denúncia: O sistema detectou {len(dados)} focos de calor em {nome_oficial}."
        link = f'<a href="mailto:?subject=Fogo em {nome_oficial}&body={msg}" target="_blank"><button>📧 Denunciar</button></a>'
        st.markdown(link, unsafe_allow_html=True)

    else:
        st.error("Cidade não encontrada no banco de dados interno nem no IBGE.")
        st.write("Tente digitar **Altamira** (sem acento) para testar.")