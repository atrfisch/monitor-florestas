import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# Configuração da página
st.set_page_config(page_title="Monitor Florestal Pro", page_icon="🌲", layout="wide")

# --- CABEÇALHOS DE NAVEGADOR (Para evitar bloqueio) ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://alerta.mapbiomas.org",
    "Referer": "https://alerta.mapbiomas.org/"
}

# --- FUNÇÕES DE BACKEND ---

def buscar_codigo_ibge(nome_cidade):
    # API do IBGE é estável e pública
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            municipios = response.json()
            for cidade in municipios:
                if cidade['nome'].lower() == nome_cidade.lower().strip():
                    return cidade['id'], cidade['nome']
    except Exception as e:
        st.error(f"Erro ao conectar com IBGE: {e}")
    return None, None

def buscar_alertas_mapbiomas(codigo_ibge=None, modo_global=False):
    # CORREÇÃO: Usando o subdomínio 'plataforma'
    url = "https://plataforma.alerta.mapbiomas.org/api/v1/alerts"
    
    params = {}
    
    if modo_global:
        # Busca 10 alertas recentes de todo o Brasil para teste
        params = {
            "limit": 10, 
            "sort_by": "published_at", 
            "sort_order": "desc"
        }
    else:
        # Busca específica por cidade
        params = {
            "geocode": codigo_ibge,
            "limit": 50,
            "sort_by": "published_at", 
            "sort_order": "desc"
        }
    
    try:
        # Timeout de 15s para garantir que não trave se a API for lenta
        response = requests.get(url, params=params, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            dados = response.json()
            # A API pode retornar dicionário com chave 'data' ou lista direta dependendo do endpoint
            if isinstance(dados, dict) and 'data' in dados:
                return dados['data']
            elif isinstance(dados, list):
                return dados
            return []
        else:
            st.error(f"A API respondeu com Erro {response.status_code}. URL tentada: {response.url}")
            return []
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return []

# --- INTERFACE ---
st.title("🌲 Monitor de Desmatamento (v3.0)")
st.markdown("Monitoramento cidadão utilizando dados abertos do **MapBiomas Alerta**.")

# 1. Painel de Diagnóstico Rápido
with st.expander("🛠️ Teste de Conexão (Clique aqui se não carregar dados)"):
    if st.button("Testar Conexão com Servidor MapBiomas"):
        with st.spinner("Conectando ao servidor..."):
            alertas_global = buscar_alertas_mapbiomas(modo_global=True)
            if alertas_global:
                st.success(f"✅ SUCESSO! Conexão estabelecida. Encontrados {len(alertas_global)} alertas recentes no Brasil.")
                st.write("Exemplo de dado recebido:", alertas_global[0]['alert_code'])
            else:
                st.error("❌ Falha. A API está online mas não retornou lista.")

st.divider()

# 2. Busca Principal
cidade_input = st.text_input("Digite o nome da cidade (Ex: Altamira, Apuí, Porto Velho):")

if cidade_input:
    # Passo 1: Achar o código IBGE
    codigo, nome_real = buscar_codigo_ibge(cidade_input)
    
    if codigo:
        st.info(f"📍 Buscando alertas para **{nome_real}** (Código IBGE: {codigo})...")
        
        # Passo 2: Buscar no MapBiomas
        alertas = buscar_alertas_mapbiomas(codigo_ibge=codigo)
        
        if alertas:
            # Cálculos
            total = len(alertas)
            area = sum([a['area_ha'] for a in alertas])
            
            # Métricas
            col1, col2 = st.columns(2)
            col1.metric("Alertas Recentes", total)
            col2.metric("Área Desmatada", f"{area:,.1f} ha")
            
            # Mapa
            map_data = []
            for a in alertas:
                # Proteção contra dados com erro de coordenada
                if 'coordinates' in a and a['coordinates']['coordinates']:
                    coords = a['coordinates']['coordinates'][0][0]
                    map_data.append({
                        'lat': coords[1], 
                        'lon': coords[0],
                        'area': a['area_ha'],
                        'codigo': a['alert_code']
                    })
            
            if map_data:
                df_map = pd.DataFrame(map_data)
                
                # Mapa com Pydeck
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    df_map,
                    get_position=["lon", "lat"],
                    get_color=[200, 30, 0, 160],
                    get_radius=5000, # Raio fixo grande para visibilidade
                    pickable=True,
                )
                view_state = pdk.ViewState(
                    latitude=df_map['lat'].mean(),
                    longitude=df_map['lon'].mean(),
                    zoom=7
                )
                r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Código: {codigo}\nÁrea: {area} ha"})
                st.pydeck_chart(r)
            
            st.success("Dados carregados!")
            
        else:
            st.warning(f"A conexão funcionou, mas não há alertas recentes (últimos 50 registros) para {nome_real}.")
            st.write("Tente uma cidade com histórico intenso de desmatamento como **Altamira** ou **Lábrea** para validar.")
    else:
        st.error("Cidade não encontrada no IBGE. Verifique a acentuação.")