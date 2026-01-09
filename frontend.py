import streamlit as st
import requests

# --- CONFIGURAÇÃO ---
API_URL = "https://sst-auditor.onrender.com"  # <--- CONFIRA SEU LINK DO RENDER AQUI

st.set_page_config(page_title="SST.AI Suite", page_icon="🛡️", layout="wide")

st.title("🛡️ SST.AI - Suíte de Engenharia")
st.markdown("Gerador de Documentação Técnica e Auditoria Automatizada")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Dados do Cliente")
    cliente = st.text_input("Nome da Empresa/Cliente", value="Cliente Padrão Ltda")
    projeto = st.text_input("Nome do Projeto/Área", value="Matriz")
    
    # AGORA A LISTA ESTÁ COMPLETA
    tipo_relatorio = st.selectbox(
        "Tipo de Documento", 
        [
            "Dimensionamento CIPA (NR-05)", 
            "Dimensionamento de Brigada (NBR 14276)",
            "Dimensionamento SESMT (NR-04)",
            "Checklist NR-12", 
            "Laudo Elétrico"
        ]
    )

# --- ÁREA PRINCIPAL ---
col1, col2 = st.columns(2)

# Variáveis globais para guardar o que o usuário digitar
dados_para_envio = {}
input_cnae = ""
input_funcs = 0
input_divisao = ""

with col1:
    st.subheader("Parâmetros Técnicos")
    
    # --- CENÁRIO 1: CIPA ou SESMT (Precisam de CNAE + Funcionários) ---
    if "CIPA" in tipo_relatorio or "SESMT" in tipo_relatorio:
        st.info("Necessário CNAE e Quantidade de Vidas.")
        input_cnae = st.text_input("CNAE (Apenas números)", value="4120400", help="Ex: Construção Civil")
        input_funcs = st.number_input("Nº Funcionários", min_value=1, value=100)
    
    # --- CENÁRIO 2: BRIGADA (Precisa de Divisão + População) ---
    elif "Brigada" in tipo_relatorio:
        st.info("Necessário Classificação da Edificação (NBR 14276).")
        # Lista simplificada das divisões mais comuns
        divisoes_comuns = [
            "A-2 (Multifamiliar)", "B-1 (Hotel)", "C-1 (Comércio)", 
            "D-1 (Escritório)", "E-1 (Escola)", "G-1 (Garagem)",
            "I-1 (Indústria Baixo Risco)", "I-2 (Indústria Médio Risco)", 
            "I-3 (Indústria Alto Risco)", "J-1 (Depósito)"
        ]
        escolha_div = st.selectbox("Divisão de Ocupação", divisoes_comuns)
        input_divisao = escolha_div.split(" ")[0] # Pega só o "A-2"
        
        input_funcs = st.number_input("População Fixa + Flutuante", min_value=1, value=50)
        st.caption("Considerar funcionários + visitantes.")

    # --- CENÁRIO 3: OUTROS RELATÓRIOS ---
    else:
        st.markdown("### 📝 Detalhes da Inspeção")
        obs = st.text_area("Observações Técnicas", height=150)
        dados_para_envio = {"Observações": obs if obs else "Sem observações."}

with col2:
    st.subheader("Ação")
    st.write(f"Modulo ativo: **{tipo_relatorio}**")
    
    if st.button("🚀 Gerar Relatório PDF", type="primary"):
        if not cliente:
            st.warning("Preencha o nome do cliente.")
        else:
            with st.spinner('Processando cálculos normativos...'):
                try:
                    tipo_backend = "geral" # Padrão
                    
                    # --- LÓGICA DO CÉREBRO (CHAMADAS DE API) ---
                    
                    # 1. CÁLCULO CIPA
                    if "CIPA" in tipo_relatorio:
                        tipo_backend = "cipa"
                        resp = requests.post(f"{API_URL}/api/cipa", json={"cnae": input_cnae, "funcionarios": int(input_funcs)})
                        if resp.status_code == 200:
                            dados_para_envio = resp.json()
                            st.success(f"CIPA Calculada: {dados_para_envio.get('efetivos')} Efetivos / {dados_para_envio.get('suplentes')} Suplentes")
                    
                    # 2. CÁLCULO SESMT
                    elif "SESMT" in tipo_relatorio:
                        tipo_backend = "sesmt"
                        resp = requests.post(f"{API_URL}/api/sesmt", json={"cnae": input_cnae, "funcionarios": int(input_funcs)})
                        if resp.status_code == 200:
                            dados_para_envio = resp.json()
                            st.success("Equipe SESMT Dimensionada!")
                            st.json(dados_para_envio.get('equipe'))

                    # 3. CÁLCULO BRIGADA
                    elif "Brigada" in tipo_relatorio:
                        tipo_backend = "brigada"
                        req_brigada = {"funcionarios": int(input_funcs), "divisao": input_divisao}
                        resp = requests.post(f"{API_URL}/api/brigada", json=req_brigada)
                        
                        if resp.status_code == 200:
                            dados_para_envio = resp.json()
                            # Se a divisão não existir no backend, ele retorna qtd 0
                            if dados_para_envio.get('qtd') == 0:
                                st.error("Erro: Divisão não encontrada na tabela NBR.")
                                st.stop()
                            st.success(f"Brigada Mínima: {dados_para_envio.get('qtd')} brigadistas")
                        else:
                            st.error("Erro ao calcular Brigada.")
                            st.stop()
                    
                    # --- GERAÇÃO DO PDF ---
                    payload = {
                        "tipo": tipo_backend,
                        "meta": {
                            "cliente": cliente,
                            "projeto": projeto,
                            "auditor": "SST.AI Suite",
                            "setor": "Geral"
                        },
                        "dados": dados_para_envio
                    }
                    
                    response = requests.post(f"{API_URL}/api/gerar_relatorio", json=payload)
                    
                    if response.status_code == 200:
                        st.download_button(
                            label="📥 Baixar PDF Finalizado",
                            data=response.content,
                            file_name=f"Relatorio_{tipo_backend}_{cliente}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.error(f"Erro no PDF: {response.text}")
                        
                except Exception as e:
                    st.error(f"Erro Crítico: {e}")

