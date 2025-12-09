import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# Configuração da página
st.set_page_config(page_title="Monitor Florestal", page_icon="🌲")

# Funções de busca
def buscar_codigo_ibge(nome_cidade):
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    response = requests.get(url)
    if response.status_code == 200:
        municipios = response.json()
        for cidade in municipios:
            if cidade['nome'].lower() == nome_cidade.lower():
                return cidade['id']
    return None

def buscar_alertas_mapbiomas(codigo_ibge):
    url = "https://alerta.mapbiomas.org/api/v1/alerts"
    # Busca alertas desde o início de 2024
    params = {
        "geocode": codigo_ibge,
        "published_at_from": "2024-01-01",
        "limit": 50
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['data']
    return []

# Interface Visual
st.title("🌲 Meu Município, Minha Floresta")
st.markdown("Veja os alertas de desmatamento validados pelo **MapBiomas** e cobre sua prefeitura.")

cidade_input = st.text_input("Digite o nome da sua cidade (ex: Altamira, Apuí):")

if cidade_input:
    with st.spinner(f'Buscando dados de {cidade_input}...'):
        codigo = buscar_codigo_ibge(cidade_input)

        if codigo:
            alertas = buscar_alertas_mapbiomas(codigo)

            if alertas:
                total_alertas = len(alertas)
                area_total = sum([a['area_ha'] for a in alertas])

                # Métricas
                col1, col2 = st.columns(2)
                col1.metric("Alertas (2024)", total_alertas)
                col2.metric("Área Desmatada", f"{area_total:.1f} ha")

                # Mapa
                map_data = []
                for a in alertas:
                    # Pega a coordenada central do polígono
                    coords = a['coordinates']['coordinates'][0][0]
                    # MapBiomas entrega [lon, lat], Pydeck usa isso mesmo
                    map_data.append({'lat': coords[1], 'lon': coords[0]})

                df_map = pd.DataFrame(map_data)
                st.map(df_map)

                # Área de Ação
                st.divider()
                st.subheader("📢 Faça a sua parte")
                st.warning("Estes dados são públicos e validados. Use-os para cobrar fiscalização.")

                subject = f"Denúncia de Desmatamento em {cidade_input}"
                body = f"Prezados, o sistema MapBiomas indica {total_alertas} novos alertas de desmatamento em nosso município, somando {area_total:.1f} hectares. Solicito informações sobre as ações de fiscalização."

                # Link mailto seguro
                link_email = f'<a href="mailto:?subject={subject}&body={body}" target="_blank" style="text-decoration:none;"><button style="background-color:#FF4B4B;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;">📧 Gerar E-mail de Cobrança</button></a>'
                st.markdown(link_email, unsafe_allow_html=True)

            else:
                st.info(f"Nenhum alerta encontrado pelo MapBiomas em {cidade_input} com os filtros atuais.")
        else:
            st.error("Cidade não encontrada no IBGE. Verifique acentos e grafia.")