import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime

# Configuração Visual
st.set_page_config(page_title="Monitor TerraBrasilis", page_icon="🛰️", layout="wide")

# --- CABEÇALHOS (Para evitar bloqueio) ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# --- BANCO DE DADOS CIDADES (Para garantir velocidade) ---
CIDADES_PRINCIPAIS = {
    "altamira": {"id": "1500602", "nome": "Altamira (PA)"},
    "sao felix do xingu": {"id": "1507300", "nome": "São Félix do Xingu (PA)"},
    "porto velho": {"id": "1100205", "nome": "Porto Velho (RO)"},
    "labrea": {"id": "1302405", "nome": "Lábrea (AM)"},
    "apui": {"id": "1300029", "nome": "Apuí (AM)"},
    "novo progresso": {"id": "1505031", "nome": "Novo Progresso (PA)"},
    "colneza": {"id": "5103254", "nome": "Colniza (MT)"}
}

# --- FUNÇÕES ---

def normalizar_texto(texto):
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', texto)
    return u"".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()

def buscar_ibge(nome_cidade):
    # 1. Tenta banco local
    nome_norm = normalizar_texto(nome_cidade)
    if nome_norm in CIDADES_PRINCIPAIS:
        return CIDADES_PRINCIPAIS[nome_norm]['id'], CIDADES_PRINCIPAIS[nome_norm]['nome']
    
    # 2. Tenta API IBGE
    try:
        url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
        resp = requests.get(url, timeout=3)
        for cid in resp.json():
            if normalizar_texto(cid['nome']) == nome_norm:
                return cid['id'], cid['nome']
    except:
        pass
    return None, None

def buscar_terrabrasilis(codigo_ibge):
    """
    Busca dados agregados do sistema DETER (Alertas).
    Tenta primeiro Amazônia (deter-amz), depois Cerrado (deter-cerrado).
    """
    # URL da API de Dashboard do TerraBrasilis
    base_url = "https://terrabrasilis.dpi.inpe.br/api/v1/dashboard/verification/warnings/municipality"
    
    # Biomas para tentar (O código IBGE não diz o bioma, então testamos os dois principais)
    projetos = ["deter-amz", "deter-cerrado"]
    
    for projeto in projetos:
        try:
            # Endpoint que traz o histórico mensal
            url = f"{base_url}/{codigo_ibge}/history?project={projeto}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            
            if response.status_code == 200:
                dados = response.json()
                # Verifica se retornou dados válidos
                if dados and 'years' in dados and len(dados['years']) > 0:
                    return dados, projeto # Retorna os dados e qual bioma funcionou
        except Exception as e:
            continue # Tenta o próximo bioma
            
    return None, None

# --- INTERFACE ---

st.title("🛰️ Monitor Oficial INPE (TerraBrasilis)")
st.markdown("""
Este painel consome dados do **DETER**, o sistema oficial de alertas de desmatamento do governo brasileiro.
Diferente das queimadas, o DETER "enxerga" o corte raso da floresta mesmo sem fogo.
""")

cidade_input = st.text_input("Digite a cidade (ex: Altamira, Apuí):", placeholder="Pressione Enter para buscar")

if cidade_input:
    cod_ibge, nome_oficial = buscar_ibge(cidade_input)
    
    if cod_ibge:
        st.info(f"🔎 Buscando dados oficiais para **{nome_oficial}**...")
        
        dados_json, bioma_detectado = buscar_terrabrasilis(cod_ibge)
        
        if dados_json:
            # Processamento dos Dados
            # A API retorna uma estrutura complexa aninhada por anos. Vamos simplificar.
            lista_dados = []
            
            # Pega o ano atual e o anterior para comparar
            anos_disponiveis = sorted(dados_json['years'], key=lambda x: x['year'], reverse=True)
            
            for ano_obj in anos_disponiveis[:2]: # Pega os 2 últimos anos
                ano = ano_obj['year']
                for mes_obj in ano_obj['months']:
                    # O TerraBrasilis as vezes retorna meses vazios, filtramos
                    lista_dados.append({
                        "Mês": f"{mes_obj['month']}/{ano}",
                        "Data": datetime(ano, int(mes_obj['month']), 1), # Para ordenação
                        "Área (km²)": mes_obj['area'],
                        "Ano": str(ano)
                    })
            
            if lista_dados:
                df = pd.DataFrame(lista_dados)
                
                # --- VISUALIZAÇÃO ---
                st.success(f"✅ Dados encontrados! Bioma: **{bioma_detectado.upper()}**")
                
                # 1. Métricas Recentes
                # Pega o dado mais recente (último mês disponível)
                ultimo_dado = sorted(lista_dados, key=lambda x: x['Data'])[-1]
                total_ano_atual = df[df['Ano'] == str(datetime.now().year)]['Área (km²)'].sum()
                
                col1, col2 = st.columns(2)
                col1.metric(f"Alerta em {ultimo_dado['Mês']}", f"{ultimo_dado['Área (km²)']:.2f} km²")
                col2.metric(f"Total Acumulado em {datetime.now().year}", f"{total_ano_atual:.2f} km²")
                
                st.divider()
                
                # 2. Gráfico de Barras (Altair)
                st.subheader("📊 Evolução do Desmatamento (Alertas)")
                
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X('Mês', sort=None), # Mantém a ordem cronológica
                    y='Área (km²)',
                    color='Ano',
                    tooltip=['Mês', 'Área (km²)']
                ).properties(height=400)
                
                st.altair_chart(chart, use_container_width=True)
                
                # 3. Análise Crítica (Automática)
                st.warning(f"Nota: Estes dados representam {total_ano_atual:.1f} km² de floresta com alertas de alteração somente este ano. Isso equivale a aproximadamente {int(total_ano_atual * 100)} campos de futebol.")

            else:
                st.warning("O INPE não retornou dados mensais para este período.")
        else:
            st.error("Nenhum dado encontrado no TerraBrasilis.")
            st.write("Possíveis motivos:")
            st.write("1. A cidade não pertence aos biomas monitorados diariamente (Amazônia/Cerrado).")
            st.write("2. A cidade não teve alertas significativos recentemente.")
    else:
        st.error("Cidade não encontrada no IBGE.")

st.markdown("---")
st.caption("Fonte: INPE/TerraBrasilis (Sistema DETER). Desenvolvido para fins educativos e de ativismo.")