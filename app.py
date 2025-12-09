import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Configuração da Página
st.set_page_config(page_title="Minha Caixa D'Água", page_icon="💧")

# --- CSS para desenhar a Caixa D'Água ---
def desenhar_caixa(nivel):
    # Cor muda conforme o nível (Azul -> Amarelo -> Vermelho)
    cor = "#3498db" # Azul
    if nivel < 40: cor = "#f1c40f" # Amarelo
    if nivel < 20: cor = "#e74c3c" # Vermelho
    
    # Altura do líquido (limitada a 100%)
    altura = min(max(nivel, 0), 100)
    
    html = f"""
    <div style="display: flex; justify-content: center; margin-top: 20px; margin-bottom: 20px;">
        <div style="
            width: 200px;
            height: 300px;
            border: 4px solid #2c3e50;
            border-top: 0;
            border-radius: 0 0 15px 15px;
            position: relative;
            background-color: #ecf0f1;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);">
            
            <div style="
                position: absolute;
                bottom: 0;
                left: 0;
                width: 100%;
                height: {altura}%;
                background-color: {cor};
                transition: height 1s ease-in-out;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0.8;">
                <span style="font-size: 24px; font-weight: bold; color: rgba(255,255,255,0.9); text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                    {nivel:.1f}%
                </span>
            </div>
            
            <div style="position: absolute; bottom: {altura}%; width: 100%; height: 10px; background: {cor}; opacity: 0.8; border-radius: 50% 50% 0 0; transform: scaleX(1.5);"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- Função para pegar dados da ANA ---
@st.cache_data(ttl=3600) # Cache de 1 hora
def pegar_dados_reservatorio(codigo):
    # Data de hoje e de alguns dias atrás para garantir que achamos o último dado
    hoje = datetime.now()
    inicio = hoje - timedelta(days=5) # Procura nos últimos 5 dias
    
    data_final = hoje.strftime("%d/%m/%Y")
    data_inicial = inicio.strftime("%d/%m/%Y")
    
    # URL oficial da API do SAR-B (Sistema de Acompanhamento de Reservatórios)
    url = f"http://sarws.ana.gov.br/SarService.asmx/DadosHistoricos?boletim=sin&reservatorio={codigo}&dataInicial={data_inicial}&dataFinal={data_final}"
    
    try:
        response = requests.get(url, timeout=10)
        # O retorno é um XML
        root = ET.fromstring(response.content)
        
        # Pega o último registro disponível
        registros = root.findall("./Reservatorio")
        if not registros:
            return None
            
        ultimo = registros[-1] # O mais recente
        nome = ultimo.find("NomeReservatorio").text.strip()
        # Às vezes o VolumePercentual vem vazio, usamos tratamento de erro
        try:
            volume = float(ultimo.find("VolumePercentual").text.replace(",", "."))
        except:
            return None
            
        data_med