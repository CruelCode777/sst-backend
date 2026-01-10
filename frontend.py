import streamlit as st
from streamlit_option_menu import option_menu
import requests

# ⚠️ SEU LINK DO RENDER
API_URL = "https://sst-backend-cxtpxb6lsng6vjjyqnaujp.onrender.com"

st.set_page_config(page_title="SST.AI Suite", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background-color: #f1f5f9;}
    div.stButton > button {background-color: #0f172a; color: white; border-radius: 8px; width: 100%; font-weight: bold;}
    div.stButton > button:hover {background-color: #334155;}
    
    .card {background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;}
    .memoria {font-family: monospace; background: #e2e8f0; padding: 10px; border-radius: 5px; font-size: 0.85em; color: #334155;}
    .pdf-btn {background-color: #ef4444; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; font-size: 0.8rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color:#0f172a;'>SST.AI <span style='color:#2563eb'>SUITE</span></h1>", unsafe_allow_html=True)

# MENU SEM CHECKLIST
selected = option_menu(
    menu_title=None,
    options=["Normas", "Brigada", "CIPA", "SESMT"],
    icons=["search", "fire", "shield", "people"],
    orientation="horizontal",
    default_index=0,
    styles={"nav-link-selected": {"background-color": "#0f172a"}}
)

# HELPER
def req(endpoint, data=None):
    try:
        url = f"{API_URL}{endpoint}"
        if data: return requests.post(url, json=data, timeout=15)
        return requests.get(url, timeout=15)
    except: return None

# --- ABA NORMAS ---
if selected == "Normas":
    st.markdown("### 🔍 Busca Inteligente (NRs e Manuais)")
    termo = st.text_input("Digite o termo (ex: Cinto, Extintor):")
    
    if st.button("Pesquisar na Base"):
        if termo:
            with st.spinner("Consultando GitHub e Base de Dados..."):
                r = req("/api/buscar", {"termo": termo})
                if r and r.status_code == 200:
                    dados = r.json()
                    if dados:
                        st.success(f"{len(dados)} resultados.")
                        for i in dados:
                            st.markdown(f"""
                            <div class="card">
                                <h4>📄 {i['titulo']}</h4>
                                <p>...{i['trecho']}...</p>
                                <a href="{i['url']}" target="_blank" class="pdf-btn">👁️ Ver PDF Original</a>
                            </div>
                            """, unsafe_allow_html=True)
                    else: st.warning("Nada encontrado.")
                else: st.error("Servidor iniciando. Tente novamente em 30s.")

# --- ABA BRIGADA (MENU GIGANTE) ---
elif selected == "Brigada":
    st.markdown("### 🔥 Dimensionamento NBR 14276")
    
    # MENU CASCATA
    GRUPOS = {
        "Residencial (A)": ["A-2: Multifamiliar"],
        "Comercial (C)": ["C-1: Comércio Geral"],
        "Serviço (D)": ["D-1: Escritório"],
        "Indústria (I)": ["I-2: Médio Risco"],
        "Depósito (J)": ["J-2: Baixo Risco"]
    }
    
    c1, c2 = st.columns(2)
    grp = c1.selectbox("1. Selecione o Grupo", list(GRUPOS.keys()))
    div = c2.selectbox("2. Selecione a Divisão", GRUPOS[grp])
    cod_div = div.split(":")[0]
    
    pop = st.number_input("População Fixa + Flutuante", min_value=1, value=50)
    
    if st.button("Calcular Brigada"):
        r = req("/api/brigada", {"funcionarios": int(pop), "divisao": cod_div})
        if r and r.status_code == 200:
            d = r.json()
            st.markdown(f"""
            <div class="card">
                <h2 style='color:#ef4444; text-align:center'>{d['qtd']} Brigadistas</h2>
                <p style='text-align:center'><b>Nível:</b> {d['nivel']} | <b>Classificação:</b> {d['classificacao']}</p>
                <div class="memoria">🧮 <b>Cálculo:</b> {d['memoria']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # PDF
            rp = requests.post(f"{API_URL}/api/gerar_relatorio", json={"tipo":"brigada", "meta":{"Div":div}, "dados":d})
            if rp.status_code == 200:
                st.download_button("📥 Baixar Relatório", rp.content, "Brigada.pdf", "application/pdf")

# --- ABAS CIPA / SESMT ---
elif selected in ["CIPA", "SESMT"]:
    mod = selected
    st.markdown(f"### ⚙️ Dimensionamento {mod}")
    
    c1, c2 = st.columns(2)
    n = c1.number_input("Funcionários", 100)
    cnae = c2.text_input("CNAE", "4120400")
    
    if st.button("Calcular"):
        ep = "/api/cipa" if mod == "CIPA" else "/api/sesmt"
        r = req(ep, {"cnae": cnae, "funcionarios": int(n)})
        
        if r and r.status_code == 200:
            d = r.json()
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
                    else: st.info("Isento de Quadro Próprio.")
                
                st.markdown(f"<div class='memoria'>🧮 {d['memoria']}</div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            rp = requests.post(f"{API_URL}/api/gerar_relatorio", json={"tipo":mod, "meta":{"CNAE":cnae}, "dados":d})
            if rp.status_code == 200:
                st.download_button("📥 Baixar Relatório", rp.content, f"{mod}.pdf", "application/pdf")
