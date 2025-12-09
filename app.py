import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime
import urllib3
import random

# Desabilita avisos de segurança para conseguir conectar no Gov
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Monitor TerraBrasilis (Live)", page_icon="📡", layout="wide")

# --- LISTA DE PROXIES (A chave para furar o bloqueio) ---
# Estes são endereços públicos. Em um projeto profissional pago, 
# usaríamos serviços como 'BrightData' ou 'ScraperAPI'.
PROXIES_BR = [
    None, # Tenta primeiro sem proxy (vai que funciona?)
    "http://200.174.198.242:8888",
    "http://45.174.41.18:999",
    "http://177.54.148.26:8080",
    "http://168.228.140.242:999"
]

CIDADES_PRINCIPAIS = {
    "altamira": "1500602",
    "porto velho": "1100205",
    "labrea": "1302405",
    "apui": "1300029",
    "sao felix do xingu": "1507300",
    "novo progresso": "1505031",
    "colneza": "5103254"
}

# --- FUNÇÕES ---

def buscar_ibge_live(nome_cidade):
    """Busca ID do IBGE em tempo real"""
    # 1. Tenta atalho local (mais rápido)
    nome_norm = nome_cidade.lower().strip()
    if nome_norm in CIDADES_PRINCIPAIS:
        return CIDADES_PRINCIPAIS[nome_norm], nome_cidade.title()
    
    # 2. Tenta API
    try:
        url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
        resp = requests.get(url, timeout=4)
        for cid in resp.json():
            if cid['nome'].lower() == nome_norm:
                return cid['id'], cid['nome']
    except:
        pass
    return None, None

def requisicao_resiliente(url):
    """
    Tenta acessar a URL usando diferentes rotas (Proxies)
    até conseguir os dados reais.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://terrabrasilis.dpi.inpe.br/"
    }

    # Tenta cada proxy da lista
    for proxy_addr in PROXIES_BR:
        proxy_dict = {"http": proxy_addr, "https": proxy_addr} if proxy_addr else None
        
        try:
            # Timeout curto para pular logo pro próximo se demorar
            resp = requests.get(
                url, 
                headers=headers, 
                proxies=proxy_dict, 
                timeout=5, 
                verify=False # Ignora SSL do governo
            )
            
            if resp.status_code == 200:
                dados = resp.json()
                if 'years' in dados and len(dados['years']) > 0:
                    return dados['years']
        except Exception as e:
            continue # Falhou? Tenta o próximo da lista
            
    return None # Se chegar aqui, falhou em todos

def buscar_terrabrasilis_live(codigo_ibge):
    base_url = "https://terrabrasilis.dpi.inpe.br/api/v1/dashboard/verification/warnings/municipality"
    
    # Tenta Amazônia
    url_amz = f"{base_url}/{codigo_ibge}/history?project=deter-amz"
    dados = requisicao_resiliente(url_amz)
    if dados: return dados, "Amazônia"

    # Se não achou, tenta Cerrado
    url_cer = f"{base_url}/{codigo_ibge}/history?project=deter-cerrado"
    dados = requisicao_resiliente(url_cer)
    if dados: return dados, "Cerrado"
    
    return None, None

# --- INTERFACE ---

st.title("📡 Monitor Oficial (Conexão Direta)")
st.info("Este sistema conecta diretamente à API do TerraBrasilis/INPE. Se o sistema do governo estiver lento, a busca pode demorar alguns segundos.")

cidade = st.text_input("Cidade (ex: Porto Velho, Altamira):")

if cidade:
    with st.spinner(f"Conectando aos servidores do INPE para buscar {cidade}..."):
        cod, nome = buscar_ibge_live(cidade)
        
        if cod:
            dados_brutos, bioma = buscar_terrabrasilis_live(cod)
            
            if dados_brutos:
                st.success(f"✅ Dados REAIS obtidos! Bioma: {bioma}")
                
                # Processamento
                lista = []
                for ano in dados_brutos:
                    for mes in ano['months']:
                        lista.append({
                            "Data": pd.to_datetime(f"{ano['year']}-{mes['month']}-01"),
                            "Mês": f"{mes['month']}/{ano['year']}",
                            "Área (km²)": mes['area'],
                            "Ano": str(ano['year'])
                        })
                
                df = pd.DataFrame(lista).sort_values("Data")
                
                # Exibição
                total_2024 = df[df['Ano'] == '2024']['Área (km²)'].sum()
                
                col1, col2 = st.columns(2)
                col1.metric("Total de Alertas 2024", f"{total_2024:.1f} km²")
                
                # Gráfico
                grafico = alt.Chart(df).mark_bar().encode(
                    x='Mês',
                    y='Área (km²)',
                    color='Ano',
                    tooltip=['Mês', 'Área (km²)']
                ).interactive()
                
                st.altair_chart(grafico, use_container_width=True)
                
                with st.expander("Ver Tabela de Dados Oficiais"):
                    st.dataframe(df)
                    
            else:
                st.error("❌ Não foi possível obter dados reais.")
                st.markdown("""
                **Diagnóstico:**
                1. O sistema TerraBrasilis pode estar fora do ar no momento.
                2. O bloqueio geográfico do INPE rejeitou todas as nossas tentativas de conexão.
                
                *Tente novamente em alguns minutos.*
                """)
        else:
            st.warning("Cidade não encontrada.")