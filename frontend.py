import streamlit as st
import requests

# --- CONFIGURAÇÃO ---
# MUITO IMPORTANTE: Cole aqui o link do seu Render (sem o /docs no final)
API_URL = "https://SEU-APP-NO-RENDER.onrender.com"

st.set_page_config(page_title="SST.AI Suite", page_icon="🛡️", layout="wide")

# --- CABEÇALHO ---
st.title("🛡️ SST.AI - Suíte de Engenharia")
st.markdown("Gerador de Documentação Técnica e Auditoria Automatizada")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Dados do Cliente")
    cliente = st.text_input("Nome da Empresa/Cliente")
    projeto = st.text_input("Nome do Projeto/Área")
    tipo_relatorio = st.selectbox("Tipo de Documento", ["Checklist NR-12", "Laudo Elétrico", "Dimensionamento CIPA"])

# --- ÁREA PRINCIPAL ---
st.info(f"Conectado ao servidor: {API_URL}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Parâmetros Técnicos")
    # Aqui você pode adicionar inputs que sua API precisa
    obs = st.text_area("Observações para o Relatório")

with col2:
    st.subheader("Ação")
    st.write("O processamento é feito em nuvem segura.")
    
    if st.button("🚀 Gerar Relatório PDF", type="primary"):
        if not cliente:
            st.warning("Por favor, preencha o nome do cliente.")
        else:
            with st.spinner('O servidor está processando... (Pode demorar 1 min se estiver "frio")'):
                try:
                    # Prepara os dados para enviar
                    dados = {
                        "cliente": cliente,
                        "projeto": projeto,
                        "tipo": tipo_relatorio,
                        "obs": obs
                    }
                    
                    # ---------------------------------------------------------
                    # ATENÇÃO: Verifique no seu /docs qual o nome exato do endpoint
                    # Vou assumir que é /gerar_relatorio, mas pode ser outro.
                    # ---------------------------------------------------------
                    response = requests.post(f"{API_URL}/gerar_relatorio", json=dados)
                    
                    if response.status_code == 200:
                        st.success("Relatório Gerado com Sucesso!")
                        # Cria o botão de download
                        st.download_button(
                            label="📥 Baixar PDF Agora",
                            data=response.content,
                            file_name=f"Relatorio_{cliente}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.error(f"Erro no servidor: {response.status_code}")
                        st.write(response.text)
                        
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")