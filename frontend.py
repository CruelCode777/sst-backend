import streamlit as st
from streamlit_option_menu import option_menu
import requests

# ⚠️ LINK DO BACKEND
API_URL = "https://sst-backend-cxtpxb6lsng6vjjyqnaujp.onrender.com"

st.set_page_config(page_title="SST.AI Pro", page_icon="🏗️", layout="wide")

# CSS para Estilo Profissional
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background-color: #f1f5f9;}
    
    /* Botões */
    div.stButton > button {
        background-color: #0f172a; 
        color: white; 
        border-radius: 8px; 
        font-weight: 600;
        padding: 0.5rem 1rem;
        border: none;
        width: 100%;
    }
    div.stButton > button:hover {background-color: #334155;}
    
    /* Cards de Resultado */
    .result-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-left: 5px solid #0f172a;
    }
    .memoria-calc {
        font-family: monospace;
        background-color: #e2e8f0;
        padding: 10px;
        border-radius: 5px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Título
st.markdown("<h1 style='text-align: center; color: #0f172a;'>SST.AI <span style='color: #2563eb'>SUITE</span></h1>", unsafe_allow_html=True)

# Menu Superior
selected = option_menu(
    menu_title=None,
    options=["Normas", "Inspeção", "Brigada", "CIPA", "SESMT"],
    icons=["search", "clipboard-check", "fire", "shield", "people"],
    default_index=0,
    orientation="horizontal",
    styles={"nav-link-selected": {"background-color": "#0f172a"}}
)

# --- FUNÇÃO DE API SEGURA ---
def safe_request(method, endpoint, payload=None):
    try:
        url = f"{API_URL}{endpoint}"
        if method == "POST":
            r = requests.post(url, json=payload, timeout=15)
        else:
            r = requests.get(url, timeout=15)
        
        if r.status_code == 200:
            return r
    except:
        st.error("⚠️ Erro de conexão com o servidor. Aguarde alguns segundos.")
    return None

# ==============================================================================
# ABA 1: BUSCA DE NORMAS (COM LINK PDF)
# ==============================================================================
if selected == "Normas":
    st.markdown("### 🔍 Busca Inteligente")
    termo = st.text_input("Digite o termo (ex: Cinto, Extintor, Ruído):", placeholder="O que você procura?")
    
    if st.button("Pesquisar na Base de Dados"):
        if not termo:
            st.warning("Digite um termo.")
        else:
            with st.spinner("Consultando NRs e PDFs..."):
                r = safe_request("POST", "/api/buscar", {"termo": termo})
                if r:
                    dados = r.json()
                    if not dados:
                        st.info("Nenhum resultado encontrado.")
                    else:
                        st.success(f"{len(dados)} documentos encontrados.")
                        for item in dados:
                            # Monta o link completo para o PDF
                            link_pdf = f"{API_URL}{item['url']}" if item['url'] != 'n/a' else "#"
                            
                            st.markdown(f"""
                            <div class="result-card">
                                <h4>📄 {item['titulo']}</h4>
                                <p>...{item['trecho']}...</p>
                                <a href="{link_pdf}" target="_blank" style="
                                    background-color: #ef4444; 
                                    color: white; 
                                    padding: 5px 10px; 
                                    text-decoration: none; 
                                    border-radius: 5px; 
                                    font-size: 0.8rem;">
                                    👁️ Ver PDF Original
                                </a>
                            </div>
                            """, unsafe_allow_html=True)

# ==============================================================================
# ABA 2: INSPEÇÃO (CHECKLISTS COMPLETOS)
# ==============================================================================
elif selected == "Inspeção":
    st.markdown("### 📋 Auditoria Digital")
    
    r_opcoes = safe_request("GET", "/api/checklists-options")
    opcoes = r_opcoes.json() if r_opcoes else []
    
    escolha = st.selectbox("Selecione a Norma/Checklist:", opcoes)
    
    if escolha:
        r_itens = safe_request("POST", "/api/get-checklist-items", {"nome": escolha})
        perguntas = r_itens.json() if r_itens else []
        
        if perguntas:
            with st.form("form_audit"):
                st.write(f"**Itens de Verificação: {escolha}**")
                respostas = {}
                for p in perguntas:
                    respostas[p] = st.radio(p, ["Conforme", "Não Conforme", "N/A"], horizontal=True, key=p)
                
                st.write("---")
                c1, c2 = st.columns(2)
                cliente = c1.text_input("Cliente")
                auditor = c2.text_input("Auditor")
                
                if st.form_submit_button("✅ Gerar Relatório PDF"):
                    payload = {"tipo": "checklist", "meta": {"Cliente": cliente, "Auditor": auditor, "Norma": escolha}, "dados": respostas}
                    r_pdf = safe_request("POST", "/api/gerar_relatorio", payload)
                    if r_pdf:
                        st.download_button("📥 Baixar Relatório", r_pdf.content, "Checklist.pdf", "application/pdf")

# ==============================================================================
# ABA 3: BRIGADA (MENU GIGANTE/DETALHADO)
# ==============================================================================
elif selected == "Brigada":
    st.markdown("### 🔥 Dimensionamento de Brigada (NBR 14276)")
    
    # ESTRUTURA DO MENU CASCATA (DETALHADO)
    GRUPOS_BRIGADA = {
        "Grupo A - Residencial": [
            "A-1: Habitação Unifamiliar (Casas)", 
            "A-2: Habitação Multifamiliar (Prédios)", 
            "A-3: Habitação Coletiva (Pensionatos)"
        ],
        "Grupo B - Hospedagem": [
            "B-1: Hotel e assemelhado", 
            "B-2: Hotel residencial"
        ],
        "Grupo C - Comercial": [
            "C-1: Comércio em geral", 
            "C-2: Shopping centers"
        ],
        "Grupo D - Serviço Profissional": [
            "D-1: Escritório", 
            "D-2: Agência bancária"
        ],
        "Grupo I - Indústria": [
            "I-1: Carga Baixa (Metalúrgica, Mecânica)", 
            "I-2: Carga Média (Alimentos, Têxtil)", 
            "I-3: Carga Alta (Química, Borracha)"
        ],
        "Grupo J - Depósito": [
            "J-1: Incombustível", 
            "J-2: Carga Baixa", 
            "J-3: Carga Média", 
            "J-4: Carga Alta"
        ]
    }
    
    col_sel1, col_sel2 = st.columns(2)
    
    with col_sel1:
        grupo_selecionado = st.selectbox("1️⃣ Selecione o Grupo Principal", list(GRUPOS_BRIGADA.keys()))
    
    with col_sel2:
        divisao_detalhada = st.selectbox("2️⃣ Selecione a Divisão Específica", GRUPOS_BRIGADA[grupo_selecionado])
        # Extrai apenas o código (ex: "A-2")
        cod_divisao = divisao_detalhada.split(":")[0]
    
    populacao = st.number_input("População Total (Fixa + Flutuante)", min_value=1, value=50)
    
    if st.button("Calcular Dimensionamento"):
        r = safe_request("POST", "/api/brigada", {"funcionarios": int(populacao), "divisao": cod_divisao})
        if r:
            res = r.json()
            st.markdown(f"""
            <div class="result-card">
                <h2 style="color: #ef4444; text-align: center;">{res['qtd']} Brigadistas</h2>
                <p style="text-align: center;"><b>Nível de Treinamento:</b> {res['nivel']}</p>
                <hr>
                <p><b>Classificação:</b> {res['classificacao']}</p>
                <p class="memoria-calc"><b>🧮 Memória de Cálculo:</b><br>{res['memoria']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão PDF
            pay = {"tipo": "brigada", "meta": {"Divisão": divisao_detalhada, "População": populacao}, "dados": res}
            r_pdf = safe_request("POST", "/api/gerar_relatorio", pay)
            if r_pdf:
                st.download_button("📥 Baixar Laudo Técnico", r_pdf.content, "Brigada.pdf", "application/pdf")

# ==============================================================================
# ABAS: CIPA e SESMT (Calculadoras Corrigidas)
# ==============================================================================
else:
    modulo = selected
    st.markdown(f"### ⚙️ Dimensionamento {modulo}")
    
    c1, c2 = st.columns(2)
    with c1:
        n_funcs = st.number_input("Número de Funcionários (CLT)", min_value=1, value=100)
    with c2:
        cnae = st.text_input("CNAE Principal (apenas números)", value="4120400")
        st.caption("Ex: 4120400 para Construção Civil (Grau 3)")

    if st.button(f"Calcular {modulo}"):
        endpoint = "/api/cipa" if modulo == "CIPA" else "/api/sesmt"
        r = safe_request("POST", endpoint, {"cnae": cnae, "funcionarios": int(n_funcs)})
        
        if r:
            res = r.json()
            
            # Exibe resultado formatado
            with st.container():
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                
                if modulo == "CIPA":
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Efetivos", res['efetivos'])
                    col_b.metric("Suplentes", res['suplentes'])
                    col_c.metric("Grau de Risco", res['risco'])
                else:
                    st.write("#### Quadro Técnico Exigido:")
                    if not res['equipe']:
                        st.info("Nenhum profissional exigido para este porte.")
                    else:
                        for cargo, qtd in res['equipe'].items():
                            st.write(f"✅ **{qtd}x** {cargo}")
                
                st.markdown(f"<br><p class='memoria-calc'><b>🧮 Memória:</b> {res['memoria']}</p>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # PDF
            pay = {"tipo": modulo, "meta": {"CNAE": cnae, "Funcionários": n_funcs}, "dados": res}
            r_pdf = safe_request("POST", "/api/gerar_relatorio", pay)
            if r_pdf:
                st.download_button("📥 Baixar Relatório", r_pdf.content, f"{modulo}.pdf", "application/pdf")
