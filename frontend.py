import streamlit as st
from streamlit_option_menu import option_menu
import requests
import time

# --- CONFIGURAÇÃO ---
API_URL = "https://sst-backend-cxtpxb6lsng6vjjyqnaujp.onrender.com"

st.set_page_config(page_title="SST.AI Auditor", page_icon="🛡️", layout="wide")

# --- ESTILO ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .title-text {text-align: center; font-family: 'Helvetica', sans-serif; font-weight: 800; font-size: 3rem; color: #0f172a;}
    .blue-text { color: #2563eb; }
    .stTextInput > div > div > input {border-radius: 20px;}
    div.stButton > button {border-radius: 30px; background-color: #2563eb; color: white; width: 100%;}
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

# --- FUNÇÃO AUXILIAR DE CONEXÃO ---
def api_request(method, endpoint, json=None):
    """Tenta conectar com retries automáticos"""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            return requests.get(url, timeout=10)
        else:
            return requests.post(url, json=json, timeout=10)
    except requests.exceptions.ConnectionError:
        st.error("🔌 Erro de Conexão: O servidor Backend está offline ou iniciando. Aguarde 30s e tente novamente.")
        return None
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return None

# --- ABA 1: NORMAS ---
if selected == "Normas":
    st.write("")
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        termo = st.text_input("", placeholder="Digite: Capacete, Extintor, Altura...")
        if st.button("🔍 Consultar"):
            if not termo:
                st.warning("Digite algo para buscar.")
            else:
                with st.spinner("Buscando na base de dados..."):
                    resp = api_request("POST", "/api/buscar", {"termo": termo})
                    if resp and resp.status_code == 200:
                        dados = resp.json()
                        if not dados:
                            st.info("Nenhum resultado exato encontrado.")
                        else:
                            st.success(f"{len(dados)} documentos encontrados.")
                            for i in dados:
                                with st.expander(f"📄 {i['titulo']}"):
                                    st.markdown(f"...{i['trecho']}...")
                                    if i['url'] != 'n/a':
                                        st.caption(f"Fonte: {i['url']} (Pág {i['pagina']})")
                    elif resp:
                        st.error("Erro no processamento da busca.")

# --- ABA 2: INSPEÇÃO (CHECKLIST) ---
elif selected == "Inspeção":
    st.subheader("📋 Checklist Digital")
    
    # Carregar Opções
    resp = api_request("GET", "/api/checklists-options")
    opcoes = resp.json() if resp and resp.status_code == 200 else []
    
    if not opcoes:
        st.warning("⚠️ Carregando lista de checklists... Se demorar, o servidor pode estar reiniciando.")
    
    escolha = st.selectbox("Selecione a Norma:", opcoes)
    
    if escolha:
        resp_items = api_request("POST", "/api/get-checklist-items", {"nome": escolha})
        perguntas = resp_items.json() if resp_items and resp_items.status_code == 200 else []
        
        if perguntas:
            dados_respostas = {}
            with st.form("audit_form"):
                st.write(f"**Itens: {escolha}**")
                for p in perguntas:
                    dados_respostas[p] = st.radio(p, ["Conforme", "Não Conforme", "N/A"], horizontal=True, key=p)
                
                cli = st.text_input("Cliente")
                if st.form_submit_button("Gerar PDF"):
                    pay = {"tipo": "checklist", "meta": {"cliente": cli}, "dados": dados_respostas}
                    r_pdf = api_request("POST", "/api/gerar_relatorio", pay)
                    if r_pdf and r_pdf.status_code == 200:
                        st.download_button("📥 Baixar PDF", r_pdf.content, "Checklist.pdf", "application/pdf")
                    else:
                        st.error("Falha ao gerar PDF.")

# --- ABA 3: BRIGADA ---
elif selected == "Brigada":
    st.subheader("🔥 Brigada de Incêndio (NBR 14276)")
    OPCOES = {
        "Residencial": ["A-2: Residencial Multifamiliar"],
        "Comercial": ["C-1: Comércio Geral", "C-2: Shopping Center"],
        "Serviço": ["D-1: Escritório"],
        "Indústria": ["I-1: Baixo Risco", "I-2: Médio Risco", "I-3: Alto Risco"],
        "Depósito": ["J-2: Baixo Risco", "J-3: Médio Risco", "J-4: Alto Risco"]
    }
    
    c1, c2 = st.columns(2)
    with c1:
        grp = st.selectbox("Grupo:", list(OPCOES.keys()))
        div_full = st.selectbox("Divisão:", OPCOES[grp])
        div_cod = div_full.split(":")[0]
        pop = st.number_input("População:", 50)
    
    with c2:
        st.write("###")
        if st.button("Calcular"):
            resp = api_request("POST", "/api/brigada", {"funcionarios": int(pop), "divisao": div_cod})
            if resp and resp.status_code == 200:
                d = resp.json()
                if d['qtd'] == 0:
                    st.error("Erro no cálculo.")
                else:
                    c_a, c_b = st.columns(2)
                    c_a.metric("Brigada", d['qtd'])
                    c_b.metric("Nível", d['nivel'])
                    st.info(d['memoria'])
                    
                    # PDF
                    pay = {"tipo": "brigada", "meta": {"cliente": "Web"}, "dados": d}
                    r_pdf = api_request("POST", "/api/gerar_relatorio", pay)
                    if r_pdf and r_pdf.status_code == 200:
                        st.download_button("📥 PDF", r_pdf.content, "Brigada.pdf", "application/pdf")

# --- ABAS SIMPLES ---
else:
    mod = selected
    st.subheader(f"⚙️ {mod}")
    c1, c2 = st.columns(2)
    with c1:
        funcs = st.number_input("Funcionários:", 100)
        cnae = st.text_input("CNAE:", "4120400")
    with c2:
        st.write("###")
        if st.button("Calcular"):
            ep = "cipa" if mod == "CIPA" else "sesmt"
            resp = api_request("POST", f"/api/{ep}", {"cnae": cnae, "funcionarios": int(funcs)})
            if resp and resp.status_code == 200:
                st.json(resp.json())
