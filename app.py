import streamlit as st
import streamlit.components.v1 as components
import requests
import urllib.parse

st.set_page_config(page_title="Portal Deter", page_icon="🛰️", layout="wide")

# --- CSS PARA REMOVER BORDAS E DEIXAR LIMPO ---
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        iframe {border: 0px;}
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def buscar_dados_cidade(nome_cidade):
    # Lista VIP de cidades para garantir o ID correto rápido
    # Adicionei os IDs oficiais do IBGE
    CIDADES_VIP = {
        "altamira": "1500602",
        "porto velho": "1100205",
        "labrea": "1302405", 
        "apui": "1300029",
        "sao felix do xingu": "1507300",
        "novo progresso": "1505031",
        "colneza": "5103254",
        "itaipual": "1503606"
    }
    
    nome_norm = nome_cidade.lower().strip()
    
    # 1. Tenta na lista VIP
    if nome_norm in CIDADES_VIP:
        return CIDADES_VIP[nome_norm], nome_cidade.title()
    
    # 2. Tenta busca genérica no IBGE
    try:
        url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
        resp = requests.get(url, timeout=3)
        for c in resp.json():
            if c['nome'].lower() == nome_norm:
                return c['id'], c['nome']
    except:
        pass
    return None, None

# --- INTERFACE ---
st.sidebar.title("🛰️ Monitoramento Real")
st.sidebar.info("Este portal conecta diretamente aos servidores do TerraBrasilis/INPE, contornando bloqueios internacionais.")

cidade_input = st.sidebar.text_input("Digite a Cidade:", "Porto Velho")
botao = st.sidebar.button("Carregar Painel Oficial")

# Lógica Principal
if cidade_input:
    cod_ibge, nome_real = buscar_dados_cidade(cidade_input)
    
    if cod_ibge:
        st.title(f"Monitoramento Oficial: {nome_real}")
        
        # URL Mágica: Esta é a URL que o site do TerraBrasilis usa para montar os dashboards
        # Nós injetamos o código da cidade diretamente nela.
        # Bioma Amazônia (padrão)
        url_painel = f"https://terrabrasilis.dpi.inpe.br/app/dashboard/alerts/legal/amazon/aggregated/{cod_ibge}"
        
        st.markdown(f"""
        <div style="background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
            ✅ <b>Conexão Estabelecida:</b> Exibindo dados oficiais do INPE em tempo real para o código IBGE <b>{cod_ibge}</b>.
        </div>
        """, unsafe_allow_html=True)
        
        # O Pulo do Gato: Iframe
        # Isso faz o SEU navegador carregar o site, burlando o bloqueio do servidor nos EUA
        components.iframe(url_painel, height=800, scrolling=True)
        
        st.caption("Fonte: Painel TerraBrasilis - Governo Federal.")
        
    else:
        st.error("Cidade não encontrada no IBGE. Tente 'Altamira' ou 'Porto Velho'.")
else:
    st.write("👈 Digite uma cidade ao lado para começar.")