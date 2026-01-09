import streamlit as st
import requests

# --- CONFIGURAÇÃO ---
# ⚠️ COLOQUE SEU LINK DO RENDER AQUI (Sem a barra no final)
API_URL = "https://sst-auditor.onrender.com"  # Exemplo. Ponha o seu!

st.set_page_config(page_title="SST.AI Suite", page_icon="🛡️", layout="wide")

st.title("🛡️ SST.AI - Suíte de Engenharia")
st.markdown("Gerador de Documentação Técnica e Auditoria Automatizada")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Dados do Cliente")
    cliente = st.text_input("Nome da Empresa/Cliente", value="Cliente Padrão Ltda")
    projeto = st.text_input("Nome do Projeto/Área", value="Matriz")
    
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

dados_para_envio = {}
input_cnae = ""
input_funcs = 0
input_divisao = ""

with col1:
    st.subheader("Parâmetros Técnicos")
    
    # --- CIPA / SESMT ---
    if "CIPA" in tipo_relatorio or "SESMT" in tipo_relatorio:
        st.info("Necessário CNAE e Quantidade de Vidas.")
        input_cnae = st.text_input("CNAE (Apenas números)", value="4120400", help="Ex: Construção Civil")
        input_funcs = st.number_input("Nº Funcionários", min_value=1, value=100)
    
    # --- BRIGADA (NBR 14276 COMPLETA) ---
    elif "Brigada" in tipo_relatorio:
        st.info("Classificação da Edificação (NBR 14276).")
        divisoes_comuns = [
            "A-1 Habitação Unifamiliar", "A-2 Habitação Multifamiliar", "A-3 Habitação Coletiva",
            "B-1 Hotel e assemelhado", "B-2 Hotel residencial",
            "C-1 Comércio geral", "C-2 Shopping centers", "C-3 Centros comerciais",
            "D-1 Escritório", "D-2 Agência bancária", "D-3 Serviço de reparação", "D-4 Laboratório",
            "E-1 Escola geral", "E-2 Escola especial", "E-3 Espaço físico", "E-4 Centro de treinamento",
            "F-1 Museu", "F-2 Igreja/Templo", "F-3 Estádio", "F-4 Estação transporte", 
            "F-5 Teatro/Cinema", "F-6 Clube", "F-7 Circo", "F-8 Restaurante",
            "G-1 Garagem", "G-2 Posto de combustível", "G-3 Oficina/Hangar", "G-4 Marina",
            "H-1 Hospital veterinário", "H-2 Hospital c/ internação", "H-3 Hospital s/ internação", 
            "H-4 Repartição pública", "H-5 Manicômio",
            "I-1 Indústria (Baixo Risco)", "I-2 Indústria (Médio Risco)", "I-3 Indústria (Alto Risco)",
            "J-1 Depósito (Incombustível)", "J-2 Depósito (Baixo Risco)", "J-3 Depósito (Médio Risco)", 
            "J-4 Depósito (Alto Risco)",
            "L-1 Comércio Explosivos", "L-2 Indústria Explosivos", "L-3 Depósito Explosivos",
            "M-1 Túnel", "M-2 Parque de Tanques", "M-3 Centrais Elétricas"
        ]
        escolha_div = st.selectbox("Divisão de Ocupação", divisoes_comuns)
        input_divisao = escolha_div.split(" ")[0] # Extrai apenas o código (Ex: "A-2")
        
        input_funcs = st.number_input("População Fixa + Flutuante", min_value=1, value=50)

    # --- GENÉRICO ---
    else:
        st.markdown("### 📝 Detalhes da Inspeção")
        obs = st.text_area("Observações Técnicas", height=150)
        dados_para_envio = {"Observações": obs if obs else "Sem observações."}

with col2:
    st.subheader("Ação")
    st.write(f"Modulo ativo: **{tipo_relatorio}**")
    
    if st.button("🚀 Gerar Relatório PDF", type="primary"):
        with st.spinner('Processando cálculos normativos...'):
            try:
                tipo_backend = "geral"
                
                # CHAMADAS DE API (CÁLCULOS)
                if "CIPA" in tipo_relatorio:
                    tipo_backend = "cipa"
                    resp = requests.post(f"{API_URL}/api/cipa", json={"cnae": input_cnae, "funcionarios": int(input_funcs)})
                    if resp.status_code == 200:
                        dados_para_envio = resp.json()
                        st.success(f"CIPA Calculada: {dados_para_envio.get('efetivos')} Efetivos / {dados_para_envio.get('suplentes')} Suplentes")

                elif "SESMT" in tipo_relatorio:
                    tipo_backend = "sesmt"
                    resp = requests.post(f"{API_URL}/api/sesmt", json={"cnae": input_cnae, "funcionarios": int(input_funcs)})
                    if resp.status_code == 200:
                        dados_para_envio = resp.json()
                        st.success("Equipe SESMT Dimensionada!")
                        st.json(dados_para_envio.get('equipe'))

                elif "Brigada" in tipo_relatorio:
                    tipo_backend = "brigada"
                    req_brigada = {"funcionarios": int(input_funcs), "divisao": input_divisao}
                    resp = requests.post(f"{API_URL}/api/brigada", json=req_brigada)
                    
                    if resp.status_code == 200:
                        dados_para_envio = resp.json()
                        if dados_para_envio.get('qtd') == 0:
                            st.error(f"Erro: {dados_para_envio.get('memoria')}")
                            st.stop()
                        st.success(f"Brigada Mínima: {dados_para_envio.get('qtd')} brigadistas")
                
                # GERAÇÃO DO PDF
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
                        
                except Exception as e:
                    st.error(f"Erro Crítico: {e}")


