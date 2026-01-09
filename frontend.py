import streamlit as st
from streamlit_option_menu import option_menu
import requests

# --- CONFIGURAÇÃO ---
# ⚠️ CONFIRA SE ESTE É O SEU LINK ATUAL DO RENDER
API_URL = "https://sst-backend-cxtpxb6lsng6vjjyqnaujp.onrender.com"

st.set_page_config(page_title="SST.AI Auditor", page_icon="🛡️", layout="wide")

# --- ESTILO CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .title-text {text-align: center; font-family: 'Helvetica', sans-serif; font-weight: 800; font-size: 3rem; color: #0f172a;}
    .blue-text { color: #2563eb; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input {border-radius: 20px; border: 1px solid #cbd5e1; padding: 10px 15px;}
    div.stButton > button {border-radius: 30px; background-color: #2563eb; color: white; border: none; padding: 0.5rem 2rem; width: 100%;}
    div.stButton > button:hover {background-color: #1d4ed8;}
    div[data-testid="stMetricValue"] {font-size: 1.5rem; color: #2563eb;}
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

# --- ABA 1: NORMAS (BUSCA COM FTS) ---
if selected == "Normas":
    st.write("")
    st.markdown("<h4 style='text-align: center; color: #64748b;'>Base de Conhecimento Normativo</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        termo = st.text_input("", placeholder="Digite um termo (ex: altura, eletricidade, EPI)...")
        if st.button("🔍 Consultar Normas"):
            with st.spinner("Pesquisando nos documentos..."):
                try:
                    resp = requests.post(f"{API_URL}/api/buscar", json={"termo": termo})
                    if resp.status_code == 200:
                        resultados = resp.json()
                        if not resultados:
                            st.warning("Nenhum resultado encontrado.")
                        else:
                            st.success(f"{len(resultados)} ocorrências encontradas.")
                            for item in resultados:
                                with st.expander(f"📄 {item['titulo']}"):
                                    # Renderiza HTML para mostrar o negrito no termo buscado
                                    st.markdown(f"... {item['trecho']} ...", unsafe_allow_html=True)
                                    if item['url'] != 'n/a':
                                        st.caption(f"Página: {item['pagina']} | Arquivo: {item['url']}")
                    else:
                        st.error("Erro na API.")
                except Exception as e:
                    st.error(f"Sistema offline: {e}")

# --- ABA 2: INSPEÇÃO (TODAS AS NRs) ---
elif selected == "Inspeção":
    st.subheader("📋 Checklist Digital")
    
    try:
        resp = requests.get(f"{API_URL}/api/checklists-options")
        opcoes = resp.json() if resp.status_code == 200 else []
    except: opcoes = []
    
    if not opcoes: st.warning("Conectando ao banco de dados...")
    
    escolha_checklist = st.selectbox("Selecione a Norma para Auditoria:", opcoes)
    
    dados_respostas = {}
    if escolha_checklist:
        try:
            resp_items = requests.post(f"{API_URL}/api/get-checklist-items", json={"nome": escolha_checklist})
            perguntas = resp_items.json()
            
            with st.form("form_checklist"):
                st.markdown(f"**Itens de Verificação: {escolha_checklist}**")
                st.write("---")
                
                for p in perguntas:
                    c_perg, c_resp = st.columns([3, 2])
                    with c_perg: st.write(p)
                    with c_resp:
                        dados_respostas[p] = st.radio("Status", ["Conforme", "Não Conforme", "N/A"], horizontal=True, key=p, label_visibility="collapsed")
                    st.write("")
                
                st.write("---")
                c_obs, c_cli = st.columns(2)
                with c_obs: obs = st.text_area("Observações / Evidências")
                with c_cli: cli = st.text_input("Cliente", value="Empresa Exemplo")

                if st.form_submit_button("✅ Gerar Relatório PDF"):
                    payload = {
                        "tipo": "checklist",
                        "meta": {"cliente": cli, "projeto": "Auditoria de Campo"},
                        "dados": dados_respostas
                    }
                    if obs: payload["dados"]["Observações"] = obs
                        
                    res_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json=payload)
                    if res_pdf.status_code == 200:
                        st.download_button("📥 Baixar PDF", res_pdf.content, "Checklist.pdf", "application/pdf")
        except: st.error("Erro ao carregar perguntas.")

# --- ABA 3: BRIGADA (DETALHADA) ---
elif selected == "Brigada":
    st.subheader("🔥 Dimensionamento de Brigada (NBR 14276)")
    
    OPCOES_DETALHADAS = {
        "Grupo A - Residencial": ["A-1: Habitação Unifamiliar", "A-2: Habitação Multifamiliar", "A-3: Habitação Coletiva"],
        "Grupo B - Hospedagem": ["B-1: Hotel e assemelhado", "B-2: Hotel residencial"],
        "Grupo C - Comercial": ["C-1: Comércio Geral", "C-2: Shopping Centers", "C-3: Centros Comerciais"],
        "Grupo D - Serviço": ["D-1: Escritório", "D-2: Banco", "D-3: Reparação", "D-4: Laboratório"],
        "Grupo E - Educacional": ["E-1: Escola", "E-2: Especial", "E-3: Cultura Física", "E-4: Treinamento"],
        "Grupo F - Público": ["F-1: Museu", "F-2: Templo", "F-3: Estádio", "F-4: Estação", "F-5: Teatro", "F-6: Clube", "F-7: Circo", "F-8: Restaurante"],
        "Grupo G - Garagem": ["G-1: Garagem", "G-2: Posto", "G-3: Oficina", "G-4: Hangar"],
        "Grupo H - Saúde": ["H-1: Veterinário", "H-2: Hospital", "H-3: Ambulatório", "H-4: Quartel", "H-5: Presídio"],
        "Grupo I - Indústria": [
            "I-1: Baixo Risco (Até 300 MJ/m² - ex: Metalúrgica, Mecânica)",
            "I-2: Médio Risco (300 a 1.200 MJ/m² - ex: Têxtil, Alimentos)",
            "I-3: Alto Risco (Acima de 1.200 MJ/m² - ex: Química, Borracha)"
        ],
        "Grupo J - Depósito": [
            "J-1: Material Incombustível (Pedra, Areia)",
            "J-2: Baixo Risco (Louças, Metais)",
            "J-3: Médio Risco (Alimentos, Peças)",
            "J-4: Alto Risco (Pneus, Papel)"
        ],
        "Grupo L - Explosivos": ["L-1: Comércio", "L-2: Indústria", "L-3: Depósito"],
        "Grupo M - Especial": ["M-1: Túnel", "M-2: Tanques", "M-3: Energia"]
    }

    c1, c2 = st.columns(2)
    with c1:
        grp = st.selectbox("Grupo:", list(OPCOES_DETALHADAS.keys()))
        div_full = st.selectbox("Divisão:", OPCOES_DETALHADAS[grp])
        div_cod = div_full.split(":")[0]
        pop = st.number_input("População:", min_value=1, value=50)
    
    with c2:
        st.write("###")
        if st.button("🔥 Calcular Brigada", type="primary"):
            try:
                resp = requests.post(f"{API_URL}/api/brigada", json={"funcionarios": int(pop), "divisao": div_cod})
                if resp.status_code == 200:
                    d = resp.json()
                    if d.get('qtd') == 0: st.error(d.get('memoria'))
                    else:
                        c_q, c_n = st.columns(2)
                        c_q.metric("Brigada", d.get('qtd')); c_n.metric("Nível", d.get('nivel'))
                        st.info(d.get('memoria'))
                        
                        pay = {"tipo": "brigada", "meta": {"cliente": "Web", "projeto": div_full}, "dados": d}
                        r_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json=pay)
                        if r_pdf.status_code == 200:
                            st.download_button("📥 PDF", r_pdf.content, "Brigada.pdf", "application/pdf")
            except Exception as e: st.error(f"Erro: {e}")

# --- ABAS CIPA / SESMT ---
else:
    mod = selected
    st.subheader(f"⚙️ {mod}")
    c1, c2 = st.columns(2)
    with c1:
        cnae = st.text_input("CNAE", value="4120400")
        funcs = st.number_input("Funcionários", min_value=1, value=100)
    with c2:
        st.write("###")
        if st.button("Calcular"):
            ep = "cipa" if mod == "CIPA" else "sesmt"
            try:
                resp = requests.post(f"{API_URL}/api/{ep}", json={"cnae": cnae, "funcionarios": int(funcs)})
                if resp.status_code == 200:
                    d = resp.json()
                    if mod == "CIPA":
                        c_a, c_b = st.columns(2)
                        c_a.metric("Efetivos", d['efetivos']); c_b.metric("Suplentes", d['suplentes'])
                    else:
                        st.json(d['equipe'])
                    
                    pay = {"tipo": ep, "meta": {"cliente": "Web", "projeto": mod}, "dados": d}
                    r = requests.post(f"{API_URL}/api/gerar_relatorio", json=pay)
                    if r.status_code == 200: st.download_button("📥 PDF", r.content, f"{mod}.pdf", "application/pdf")
            except: st.error("Erro")
