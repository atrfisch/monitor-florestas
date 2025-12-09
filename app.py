import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Monitor Florestal", page_icon="🌲", layout="wide")

# Barra Lateral de Configuração
st.sidebar.header("Configurações de Busca")
ano_inicio = st.sidebar.slider("Buscar alertas a partir de:", 2019, 2024, 2023)
limite_alertas = st.sidebar.slider("Máximo de alertas:", 10, 500, 100)

# Funções de busca
@st.cache_data # Cache para não chamar a API toda hora se a cidade for a mesma
def buscar_codigo_ibge(nome_cidade):
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            municipios = response.json()
            for cidade in municipios:
                # Remove acentos e joga tudo pra minusculo para comparar melhor poderia ser feito, 
                # mas aqui vamos pelo simples
                if cidade['nome'].lower() == nome_cidade.lower():
                    return cidade['id']
    except Exception as e:
        st.error(f"Erro ao conectar com IBGE: {e}")
    return None

def buscar_alertas_mapbiomas(codigo_ibge, ano):
    url = "https://alerta.mapbiomas.org/api/v1/alerts"
    params = {
        "geocode": codigo_ibge,
        "published_at_from": f"{ano}-01-01",
        "limit": limite_alertas
    }
    headers = {"User-Agent": "MonitorFlorestal/1.0"} # Boa prática
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()['data']
    except Exception as e:
        st.error(f"Erro ao conectar com MapBiomas: {e}")
    return []

# Interface Principal
st.title("🌲 Monitor Histórico de Desmatamento")
st.markdown(f"Visualizando dados validados pelo **MapBiomas Alerta** desde **{ano_inicio}**.")

cidade_input = st.text_input("Digite o nome da cidade (ex: Altamira, Apuí, São Félix do Xingu):")

if cidade_input:
    with st.spinner(f'Buscando histórico de {cidade_input}...'):
        codigo = buscar_codigo_ibge(cidade_input.strip())
        
        if codigo:
            alertas = buscar_alertas_mapbiomas(codigo, ano_inicio)
            
            if alertas:
                total_alertas = len(alertas)
                area_total = sum([a['area_ha'] for a in alertas])
                
                # Cria colunas para métricas
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Alertas", total_alertas)
                col2.metric("Área Total (hectares)", f"{area_total:,.1f} ha")
                col3.metric("Período", f"Desde {ano_inicio}")
                
                # --- VISUALIZAÇÃO NO MAPA ---
                map_data = []
                for a in alertas:
                    coords = a['coordinates']['coordinates'][0][0]
                    map_data.append({
                        'lat': coords[1], 
                        'lon': coords[0],
                        'area': a['area_ha'],
                        'data': a['published_at'][:10] # Pega só a data YYYY-MM-DD
                    })
                
                df_map = pd.DataFrame(map_data)
                
                # Mapa interativo com Pydeck (bolinhas variam de tamanho conforme a área)
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    df_map,
                    get_position=["lon", "lat"],
                    get_color=[255, 75, 75, 160], # Vermelho translúcido
                    get_radius="area * 100", # Tamanho baseado na área desmatada
                    pickable=True,
                )
                
                view_state = pdk.ViewState(
                    latitude=df_map['lat'].mean(),
                    longitude=df_map['lon'].mean(),
                    zoom=7,
                    pitch=0
                )
                
                r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Data: {data}\nÁrea: {area} ha"})
                st.pydeck_chart(r)
                
                # --- TABELA DE DADOS ---
                with st.expander("📄 Ver lista detalhada dos alertas"):
                    st.dataframe(df_map)

                # --- ÁREA DE AÇÃO ---
                st.divider()
                st.subheader("📢 Aja Agora")
                
                subject = f"Histórico de Desmatamento em {cidade_input}"
                body = f"Prezados, consultei o histórico do MapBiomas e constam {total_alertas} alertas desde {ano_inicio} em nosso município. A área total atinge {area_total:.1f} hectares. Solicito informações sobre embargos e multas aplicadas nestas áreas."
                
                link_email = f'<a href="mailto:?subject={subject}&body={body}" target="_blank" style="text-decoration:none;"><button style="background-color:#FF4B4B;color:white;border:none;padding:12px 24px;border-radius:5px;cursor:pointer;font-size:16px;">📧 Enviar Cobrança Oficial</button></a>'
                st.markdown(link_email, unsafe_allow_html=True)

            else:
                st.info(f"Nenhum alerta encontrado em {cidade_input} desde {ano_inicio}. Tente reduzir o ano na barra lateral.")
        else:
            st.error("Cidade não encontrada. Verifique a grafia.")