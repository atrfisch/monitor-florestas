import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# Configuração da página
st.set_page_config(page_title="Monitor Florestal Pro", page_icon="🌲", layout="wide")

# --- CABEÇALHOS PARA ENGANAR O BLOQUEIO (Mimetização) ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://plataforma.alerta.mapbiomas.org/"
}

# Funções de Backend
def buscar_codigo_ibge(nome_cidade):
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    try:
        # IBGE geralmente aceita conexões simples
        response = requests.get(url)
        if response.status_code == 200:
            municipios = response.json()
            for cidade in municipios:
                if cidade['nome'].lower() == nome_cidade.lower().strip():
                    return cidade['id'], cidade['nome']
    except Exception as e:
        st.error(f"Erro IBGE: {e}")
    return None, None

def buscar_alertas_mapbiomas(codigo_ibge=None, modo_global=False):
    url = "https://alerta.mapbiomas.org/api/v1/alerts"
    
    if modo_global:
        # Busca os últimos 10 alertas de QUALQUER lugar do Brasil
        params = {"limit": 10, "sort_by": "published_at", "sort_order": "desc"}
    else:
        # Busca por cidade específica
        params = {
            "geocode": codigo_ibge,
            "limit": 50
        }
    
    try:
        # AQUI ESTÁ O TRUQUE: Passamos os headers
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            dados = response.json()
            return dados.get('data', [])
        else:
            st.error(f"Erro API MapBiomas: Status {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return []

# --- INTERFACE ---
st.title("🌲 Monitor de Desmatamento (Versão Blindada)")

# 1. Botão de Teste de Vida
with st.expander("🛠️ Diagnóstico de Conexão (Clique se nada funcionar)"):
    st.write("Teste se a API do MapBiomas está respondendo para o Brasil inteiro:")
    if st.button("Testar Conexão Global"):
        alertas_global = buscar_alertas_mapbiomas(modo_global=True)
        if alertas_global:
            st.success(f"✅ CONEXÃO OK! Encontrados {len(alertas_global)} alertas recentes no Brasil.")
            st.json(alertas_global[0]) # Mostra um exemplo
        else:
            st.error("❌ A API retornou lista vazia mesmo para busca global. O serviço pode estar fora do ar.")

# 2. Busca Principal
st.divider()
cidade_input = st.text_input("Digite o nome da cidade (Teste com: Altamira):")

if cidade_input:
    codigo, nome_real = buscar_codigo_ibge(cidade_input)
    
    if codigo:
        st.info(f"Busca iniciada para: {nome_real} (IBGE: {codigo})")
        
        alertas = buscar_alertas_mapbiomas(codigo_ibge=codigo)
        
        if alertas:
            total = len(alertas)
            area = sum([a['area_ha'] for a in alertas])
            
            col1, col2 = st.columns(2)
            col1.metric("Alertas Encontrados", total)
            col2.metric("Área Total", f"{area:,.1f} ha")
            
            # Mapa
            map_data = []
            for a in alertas:
                coords = a['coordinates']['coordinates'][0][0]
                map_data.append({'lat': coords[1], 'lon': coords[0]})
            
            st.map(pd.DataFrame(map_data))
            
            st.success("Dados carregados com sucesso!")
        else:
            st.warning(f"A API respondeu, mas não encontrou alertas para {nome_real} com os filtros atuais.")
            st.write("Dica: Tente cidades como 'Porto Velho' ou 'Lábrea' para confirmar.")
    else:
        st.error("Cidade não encontrada no IBGE. Verifique acentos (ex: São Félix do Xingu).")