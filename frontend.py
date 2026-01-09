import streamlit as st
from streamlit_option_menu import option_menu
import requests

# --- CONFIGURAÇÃO ---
API_URL = "https://sst-ai-suite.onrender.com"  # <--- SEU LINK DO RENDER AQUI
st.set_page_config(page_title="SST.AI Auditor", page_icon="🛡️", layout="wide")

# --- ESTILO CSS (VISUAL IGUAL À IMAGEM) ---
st.markdown("""
<style>
    /* 1. Remover Menu Padrão e Rodapé */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 2. Centralizar Título Principal */
    .title-text {
        text-align: center;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        font-size: 3rem;
        color: #0f172a;
        margin-bottom: 0px;
    }
    .blue-text { color: #2563eb; }

    /* 3. Estilizar a Barra de Busca (Arredondada e Sombra) */
    .stTextInput > div > div > input {
        border-radius: 30px;
        border: 2px solid #e2e8f0;
        padding: 10px 20px;
        font-size: 1.1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* 4. Botões primários arredondados */
    div.stButton > button {
        border-radius: 30px;
        background-color: #2563eb;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 2rem;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
    }
    div.stButton > button:hover {
        background-color: #1d4ed8;
    }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
st.markdown('<h1 class="title-text">SST.AI <span class="blue-text">AUDITOR</span></h1>', unsafe_allow_html=True)
st.write("") # Espaço

# --- MENU DE NAVEGAÇÃO (TOPO) ---
selected = option_menu(
    menu_title=None,
    options=["Normas", "Inspeção", "Brigada", "CIPA", "SESMT"],
    icons=["search", "clipboard-check", "fire", "shield-check", "person-badge"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#ffffff"},
        "icon": {"color": "#2563eb", "font-size": "18px"}, 
        "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px", "--hover-color": "#eff6ff"},
        "nav-link-selected": {"background-color": "#2563eb", "font-weight": "bold"},
    }
)

# --- LÓGICA DAS ABAS ---

# === ABA 1: BUSCA DE NORMAS (Visual da Imagem) ===
if selected == "Normas":
    st.write("")
    st.write("")
    
    # Layout centralizado para a busca
    col_vazia1, col_busca, col_btn, col_vazia2 = st.columns([1, 4, 1, 1])
    
    with col_busca:
        termo = st.text_input("", placeholder="Digite o termo para buscar na NR...", label_visibility="collapsed")
    
    with col_btn:
        st.button("🔍 Buscar")
        
    st.info("👆 Digite um termo acima (ex: 'Escadas', 'EPI') para buscar na base de dados.")


# === ABA 2, 3, 4, 5: CÁLCULOS E RELATÓRIOS ===
else:
    # Define qual relatório estamos fazendo
    tipo_backend = "geral"
    nome_relatorio = ""
    
    if selected == "Inspeção": 
        nome_relatorio = "Checklist NR-12"
        tipo_backend = "checklist"
    elif selected == "Brigada": 
        nome_relatorio = "Dimensionamento Brigada"
        tipo_backend = "brigada"
    elif selected == "CIPA": 
        nome_relatorio = "Dimensionamento CIPA"
        tipo_backend = "cipa"
    elif selected == "SESMT": 
        nome_relatorio = "Dimensionamento SESMT"
        tipo_backend = "sesmt"

    # --- ÁREA DE DADOS (Card Branco) ---
    with st.container():
        st.markdown(f"### ⚙️ Configuração: {selected}")
        
        c1, c2 = st.columns(2)
        
        # Variáveis globais
        input_cnae = ""
        input_funcs = 0
        input_divisao = ""
        cliente = ""
        projeto = ""
        dados_para_envio = {}

        with c1:
            cliente = st.text_input("Cliente", value="Empresa Modelo S.A.")
            projeto = st.text_input("Unidade/Projeto", value="Matriz")

            # Inputs Específicos
            if selected in ["CIPA", "SESMT"]:
                input_cnae = st.text_input("CNAE", value="4120400")
                input_funcs = st.number_input("Funcionários", min_value=1, value=100)
            
            elif selected == "Brigada":
                divisoes = ["A-2 Habitação Multifamiliar", "D-1 Escritório", "I-2 Indústria Médio Risco", "C-2 Shopping"]
                escolha_div = st.selectbox("Divisão (NBR 14276)", divisoes)
                input_divisao = escolha_div.split(" ")[0]
                input_funcs = st.number_input("População", min_value=1, value=50)
            
            elif selected == "Inspeção":
                obs = st.text_area("Observações da Inspeção")
                dados_para_envio = {"Observações": obs if obs else "Nenhuma observação."}

        with c2:
            st.write("###") # Espaço
            if st.button(f"🚀 Calcular e Gerar PDF de {selected}", type="primary"):
                with st.spinner('Conectando ao servidor...'):
                    try:
                        # LOGICA DE CÁLCULO (CÓPIADA DO ANTERIOR)
                        if selected == "CIPA":
                            resp = requests.post(f"{API_URL}/api/cipa", json={"cnae": input_cnae, "funcionarios": int(input_funcs)})
                            if resp.status_code == 200:
                                dados_para_envio = resp.json()
                                st.success(f"Efetivos: {dados_para_envio.get('efetivos')} | Suplentes: {dados_para_envio.get('suplentes')}")
                        
                        elif selected == "SESMT":
                            resp = requests.post(f"{API_URL}/api/sesmt", json={"cnae": input_cnae, "funcionarios": int(input_funcs)})
                            if resp.status_code == 200:
                                dados_para_envio = resp.json()
                                st.json(dados_para_envio.get('equipe'))

                        elif selected == "Brigada":
                            req_brigada = {"funcionarios": int(input_funcs), "divisao": input_divisao}
                            resp = requests.post(f"{API_URL}/api/brigada", json=req_brigada)
                            if resp.status_code == 200:
                                dados_para_envio = resp.json()
                                if dados_para_envio.get('qtd') == 0:
                                    st.error("Divisão inválida/não encontrada.")
                                    st.stop()
                                st.success(f"Brigada Mínima: {dados_para_envio.get('qtd')} pessoas")

                        # GERA PDF
                        payload = {
                            "tipo": tipo_backend,
                            "meta": {"cliente": cliente, "projeto": projeto, "auditor": "SST Auditor", "setor": "Geral"},
                            "dados": dados_para_envio
                        }
                        response = requests.post(f"{API_URL}/api/gerar_relatorio", json=payload)
                        
                        if response.status_code == 200:
                            st.download_button("📥 Baixar Relatório PDF", data=response.content, file_name=f"Relatorio_{selected}.pdf", mime="application/pdf")
                        else:
                            st.error("Erro ao gerar PDF.")

                    except Exception as e:
                        st.error(f"Erro: {e}")
