import streamlit as st
from streamlit_option_menu import option_menu
import requests

# ⚠️ LINK DO RENDER (Certifique-se que está correto)
API_URL = "https://sst-backend-cxtpxb6lsng6vjjyqnaujp.onrender.com"

st.set_page_config(page_title="SST.AI Suite", page_icon="🏗️", layout="wide")

# CSS Style
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background-color: #f1f5f9;}
    div.stButton > button {background-color: #0f172a; color: white; border-radius: 8px; width: 100%;}
    div.stButton > button:hover {background-color: #334155;}
    
    .card {background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .memoria {font-family: monospace; background: #e2e8f0; padding: 10px; border-radius: 5px; font-size: 0.9em; color: #334155;}
    .link-pdf {background-color: #ef4444; color: white !important; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 0.8em;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color:#0f172a;'>SST.AI <span style='color:#2563eb'>SUITE</span></h1>", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None,
    options=["Normas", "Inspeção", "Brigada", "CIPA", "SESMT"],
    icons=["search", "clipboard-check", "fire", "shield", "people"],
    orientation="horizontal",
    styles={"nav-link-selected": {"background-color": "#0f172a"}}
)

# API Helper
def req(endpoint, data=None):
    try:
        url = f"{API_URL}{endpoint}"
        if data: r = requests.post(url, json=data, timeout=20)
        else: r = requests.get(url, timeout=20)
        
        if r.status_code == 200: return r.json()
        return None
    except:
        st.error("⚠️ Servidor Backend indisponível ou iniciando. Aguarde...")
        return None

# --- NORMAS (BUSCA) ---
if selected == "Normas":
    st.markdown("### 🔍 Busca na Base de Conhecimento (PDFs)")
    termo = st.text_input("Digite o termo:", placeholder="Ex: Cinto, Extintor, Ruído")
    
    if st.button("Pesquisar"):
        if termo:
            with st.spinner("Buscando nos arquivos do GitHub..."):
                res = req("/api/buscar", {"termo": termo})
                if res:
                    st.success(f"{len(res)} resultados encontrados.")
                    for item in res:
                        st.markdown(f"""
                        <div class="card">
                            <h4>📄 {item['titulo']}</h4>
                            <p>...{item['trecho']}...</p>
                            <a href="{item['url']}" target="_blank" class="link-pdf">👁️ Ver PDF Original</a>
                        </div>
                        """, unsafe_allow_html=True)
                elif res == []:
                    st.warning("Nenhum termo encontrado.")

# --- BRIGADA (MENU GIGANTE) ---
elif selected == "Brigada":
    st.markdown("### 🔥 Dimensionamento de Brigada (NBR 14276)")
    
    # MENU CASCATA DETALHADO
    GRUPOS = {
        "Residencial (Grupo A)": ["A-2: Multifamiliar"],
        "Comercial (Grupo C)": ["C-1: Comércio Geral", "C-2: Shopping Center"],
        "Serviço (Grupo D)": ["D-1: Escritório"],
        "Indústria (Grupo I)": ["I-1: Baixo Risco", "I-2: Médio Risco", "I-3: Alto Risco"],
        "Depósito (Grupo J)": ["J-2: Baixo Risco", "J-3: Médio Risco"]
    }
    
    c1, c2 = st.columns(2)
    grp = c1.selectbox("1. Selecione o Grupo", list(GRUPOS.keys()))
    div = c2.selectbox("2. Selecione a Divisão", GRUPOS[grp])
    cod_div = div.split(":")[0]
    
    pop = st.number_input("População Total", 50)
    
    if st.button("Calcular"):
        d = req("/api/brigada", {"funcionarios": int(pop), "divisao": cod_div})
        if d:
            st.markdown(f"""
            <div class="card">
                <h2 style='text-align:center; color:#ef4444'>{d['qtd']} Brigadistas</h2>
                <p style='text-align:center'><b>Nível:</b> {d['nivel']} | <b>Classificação:</b> {d['classificacao']}</p>
                <div class="memoria">🧮 <b>Memória de Cálculo:</b><br>{d['memoria']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # PDF
            try:
                r_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json={"tipo":"brigada", "meta":{"Divisão":div}, "dados":d})
                st.download_button("📥 Baixar Relatório", r_pdf.content, "Brigada.pdf", "application/pdf")
            except: pass

# --- CIPA / SESMT ---
elif selected in ["CIPA", "SESMT"]:
    mod = selected
    st.markdown(f"### ⚙️ {mod}")
    
    c1, c2 = st.columns(2)
    n = c1.number_input("Nº Funcionários", 100)
    cnae = c2.text_input("CNAE", "4120400")
    
    if st.button("Calcular"):
        ep = "/api/cipa" if mod == "CIPA" else "/api/sesmt"
        d = req(ep, {"cnae": cnae, "funcionarios": int(n)})
        
        if d:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                if mod == "CIPA":
                    c_a, c_b = st.columns(2)
                    c_a.metric("Efetivos", d['efetivos'])
                    c_b.metric("Suplentes", d['suplentes'])
                else:
                    st.write("#### Quadro Técnico:")
                    if d['equipe']:
                        for k,v in d['equipe'].items(): st.write(f"✅ {v}x {k}")
                    else: st.info("Não há exigência para este porte.")
                
                st.markdown(f"<div class='memoria'>🧮 {d['memoria']}</div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            try:
                r_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json={"tipo":mod, "meta":{"CNAE":cnae}, "dados":d})
                st.download_button("📥 Baixar Relatório", r_pdf.content, f"{mod}.pdf", "application/pdf")
            except: pass

# --- INSPEÇÃO ---
elif selected == "Inspeção":
    st.markdown("### 📋 Checklist")
    opts = req("/api/checklists-options") or []
    sel = st.selectbox("Norma:", opts)
    
    if sel:
        items = req("/api/get-checklist-items", {"nome": sel}) or []
        with st.form("check"):
            resps = {}
            for i in items: resps[i] = st.radio(i, ["Conforme", "Não Conforme"], horizontal=True)
            cli = st.text_input("Cliente")
            if st.form_submit_button("Gerar PDF"):
                try:
                    r_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json={"tipo":"checklist", "meta":{"Cliente":cli}, "dados":resps})
                    st.download_button("📥 Baixar PDF", r_pdf.content, "Checklist.pdf", "application/pdf")
                except: st.error("Erro PDF")
