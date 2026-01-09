import streamlit as st
import requests

# --- CONFIGURAÇÃO ---
# MUITO IMPORTANTE: Cole aqui o link do seu Render (sem o /docs no final)
API_URL = "https://sst-ai-suite.onrender.com"

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
            with st.spinner('Processando no servidor...'):
                try:
                    # 1. TRADUÇÃO (Para o título do PDF sair bonito)
                    # Mapeia o que está no Dropdown para o código interno do Python
                    mapa_tipos = {
                        "Checklist NR-12": "checklist",
                        "Laudo Elétrico": "geral", 
                        "Dimensionamento CIPA": "cipa"
                    }
                    tipo_interno = mapa_tipos.get(tipo_relatorio, "geral")

                    # 2. ARRUMANDO A MALA (Estrutura exata do RelatorioReq)
                    payload = {
                        "tipo": tipo_interno,
                        "meta": {
                            "cliente": cliente,
                            "projeto": projeto,
                            "auditor": "Usuário Web",
                            "setor": "Geral"
                        },
                        "dados": {
                            # Aqui enviamos o conteúdo do relatório. 
                            # Como é um teste, vamos enviar a observação como dado principal.
                            "Conteúdo do Relatório": obs if obs else "Sem observações adicionais."
                        }
                    }
                    
                    # 3. ENVIO
                    # Note que agora enviamos 'payload' em vez de 'dados' soltos
                    response = requests.post(f"{API_URL}/api/gerar_relatorio", json=payload)
                    
                    if response.status_code == 200:
                        st.success("Relatório Gerado com Sucesso!")
                        st.download_button(
                            label="📥 Baixar PDF Agora",
                            data=response.content,
                            file_name=f"Relatorio_{cliente}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.error(f"Erro no servidor: {response.status_code}")
                        # Mostra o erro detalhado se não for 200
                        st.json(response.json())
                        
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
