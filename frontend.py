import streamlit as st
from streamlit_option_menu import option_menu
import requests

# --- CONFIGURAÇÃO ---
# ⚠️ COLOQUE SEU LINK DO RENDER AQUI
API_URL = "https://sst-backend-cxtpxb6lsng6vjjyqnaujp.onrender.com"
st.set_page_config(page_title="SST.AI Auditor", page_icon="🛡️", layout="wide")

# --- ESTILO ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .title-text {text-align: center; font-family: 'Helvetica', sans-serif; font-weight: 800; font-size: 3rem; color: #0f172a;}
    .blue-text { color: #2563eb; }
    .stTextInput > div > div > input {border-radius: 30px; border: 2px solid #e2e8f0; padding: 10px 20px;}
    div.stButton > button {border-radius: 30px; background-color: #2563eb; color: white; border: none; padding: 0.5rem 2rem; width: 100%;}
    div.stButton > button:hover {background-color: #1d4ed8;}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-text">SST.AI <span class="blue-text">AUDITOR</span></h1>', unsafe_allow_html=True)

# --- MENU ---
selected = option_menu(
    menu_title=None,
    options=["Normas", "Inspeção", "Brigada", "CIPA", "SESMT"],
    icons=["search", "clipboard-check", "fire", "shield-check", "person-badge"],
    default_index=0,
    orientation="horizontal"
)

# --- ABA 1: NORMAS (BUSCA) ---
if selected == "Normas":
    st.write("")
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        termo = st.text_input("", placeholder="Digite um termo (ex: altura, eletricidade, fogo)...")
        if st.button("🔍 Buscar na Base"):
            try:
                resp = requests.post(f"{API_URL}/api/buscar", json={"termo": termo})
                if resp.status_code == 200:
                    resultados = resp.json()
                    if not resultados:
                        st.warning("Nenhum resultado encontrado na base simulada.")
                    for item in resultados:
                        with st.expander(f"{item['norma']} - {item['titulo']}"):
                            st.write(item['texto'])
                else:
                    st.error("Erro na API.")
            except: st.error("Servidor offline.")

# --- ABA 2: INSPEÇÃO (CHECKLISTS) ---
elif selected == "Inspeção":
    st.subheader("📋 Checklist Digital")
    
    # 1. Busca opções no backend
    try:
        resp = requests.get(f"{API_URL}/api/checklists-options")
        opcoes = resp.json() if resp.status_code == 200 else []
    except: opcoes = []
    
    escolha_checklist = st.selectbox("Selecione a Norma/Checklist", opcoes)
    
    # 2. Se escolheu, busca as perguntas
    dados_respostas = {}
    if escolha_checklist:
        resp_items = requests.post(f"{API_URL}/api/get-checklist-items", json={"nome": escolha_checklist})
        perguntas = resp_items.json()
        
        with st.form("form_checklist"):
            st.write(f"**Auditando: {escolha_checklist}**")
            for p in perguntas:
                dados_respostas[p] = st.radio(p, ["Conforme", "Não Conforme", "N/A"], horizontal=True, key=p)
            
            obs = st.text_area("Observações Gerais")
            enviar = st.form_submit_button("Gerar Relatório de Inspeção")
            
            if enviar:
                payload = {
                    "tipo": "checklist",
                    "meta": {"cliente": "Empresa Teste", "projeto": "Auditoria"},
                    "dados": dados_respostas
                }
                res_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json=payload)
                if res_pdf.status_code == 200:
                    st.download_button("📥 Baixar PDF", res_pdf.content, "Checklist.pdf", "application/pdf")

# --- ABA 3: BRIGADA (LISTA COMPLETA) ---
elif selected == "Brigada":
    st.subheader("🔥 Dimensionamento de Brigada (NBR 14276)")
    c1, c2 = st.columns(2)
    
    with c1:
        # LISTA COMPLETA RESTAURADA
        divisoes_comuns = [
            "A-1 Habitação Unifamiliar", "A-2 Habitação Multifamiliar", "A-3 Habitação Coletiva",
            "B-1 Hotel e assemelhado", "B-2 Hotel residencial",
            "C-1 Comércio geral", "C-2 Shopping centers", "C-3 Centros comerciais",
            "D-1 Escritório", "D-2 Agência bancária", "D-3 Serviço de reparação", "D-4 Laboratório",
            "E-1 Escola geral", "E-2 Escola especial", "E-3 Espaço físico", "E-4 Centro de treinamento",
            "F-1 Museu", "F-2 Igreja/Templo", "F-3 Estádio", "F-4 Estação transporte", "F-5 Teatro/Cinema", "F-6 Clube", "F-7 Circo", "F-8 Restaurante",
            "G-1 Garagem", "G-2 Posto de combustível", "G-3 Oficina/Hangar", "G-4 Marina",
            "H-1 Hospital veterinário", "H-2 Hospital c/ internação", "H-3 Hospital s/ internação", "H-4 Repartição pública", "H-5 Manicômio",
            "I-1 Indústria (Baixo Risco)", "I-2 Indústria (Médio Risco)", "I-3 Indústria (Alto Risco)",
            "J-1 Depósito (Incombustível)", "J-2 Depósito (Baixo Risco)", "J-3 Depósito (Médio Risco)", "J-4 Depósito (Alto Risco)",
            "L-1 Comércio Explosivos", "L-2 Indústria Explosivos", "L-3 Depósito Explosivos",
            "M-1 Túnel", "M-2 Parque de Tanques", "M-3 Centrais Elétricas"
        ]
        escolha = st.selectbox("Classificação da Edificação", divisoes_comuns)
        divisao_codigo = escolha.split(" ")[0]
        pop = st.number_input("População", min_value=1, value=50)
        
    with c2:
        st.write("###")
        if st.button("Calcular Brigada"):
            try:
                resp = requests.post(f"{API_URL}/api/brigada", json={"funcionarios": int(pop), "divisao": divisao_codigo})
                if resp.status_code == 200:
                    d = resp.json()
                    st.success(f"Brigada Mínima: {d.get('qtd')} pessoas")
                    st.info(f"Nível: {d.get('nivel')}")
                    st.caption(d.get('memoria'))
                    
                    # Gerar PDF
                    pay = {"tipo": "brigada", "meta": {"cliente": "Teste", "projeto": "Brigada"}, "dados": d}
                    r_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json=pay)
                    if r_pdf.status_code == 200:
                        st.download_button("📥 Baixar Laudo", r_pdf.content, "Brigada.pdf", "application/pdf")
            except Exception as e: st.error(f"Erro: {e}")

# --- OUTRAS ABAS (Mantidas Simples) ---
else:
    st.info("Módulo em desenvolvimento.")
