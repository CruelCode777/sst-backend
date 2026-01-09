import streamlit as st
from streamlit_option_menu import option_menu
import requests

# --- CONFIGURAÇÃO ---
# ⚠️ Mantenha o link do seu backend aqui
API_URL = "https://sst-backend-cxtpxb6lsng6vjjyqnaujp.onrender.com"

st.set_page_config(page_title="SST.AI Auditor", page_icon="🛡️", layout="wide")

# --- ESTILO CSS (Visual Profissional/Limpo) ---
st.markdown("""
<style>
    /* Remove itens padrão do Streamlit para parecer um App Nativo */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Título Centralizado */
    .title-text {
        text-align: center;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        font-size: 3rem;
        color: #0f172a;
    }
    .blue-text { color: #2563eb; }

    /* Inputs Arredondados */
    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        border-radius: 20px;
        border: 1px solid #cbd5e1;
        padding: 10px 15px;
    }
    
    /* Botões Arredondados e Azuis */
    div.stButton > button {
        border-radius: 30px;
        background-color: #2563eb;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 2rem;
        width: 100%;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #1d4ed8;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        transform: translateY(-2px);
    }
    
    /* Cards de Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        color: #2563eb;
    }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
st.markdown('<h1 class="title-text">SST.AI <span class="blue-text">AUDITOR</span></h1>', unsafe_allow_html=True)

# --- MENU DE NAVEGAÇÃO SUPERIOR ---
selected = option_menu(
    menu_title=None,
    options=["Normas", "Inspeção", "Brigada", "CIPA", "SESMT"],
    icons=["search", "clipboard-check", "fire", "shield-check", "person-badge"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#ffffff"},
        "icon": {"color": "#2563eb", "font-size": "18px"}, 
        "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px"},
        "nav-link-selected": {"background-color": "#2563eb", "color": "white"},
    }
)

# ==============================================================================
# ABA 1: NORMAS (BUSCA INTELIGENTE)
# ==============================================================================
if selected == "Normas":
    st.write("")
    st.markdown("<h4 style='text-align: center; color: #64748b;'>Base de Conhecimento Normativo</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        termo = st.text_input("", placeholder="Digite um termo (ex: altura, eletricidade, extintor)...")
        if st.button("🔍 Consultar Normas"):
            with st.spinner("Pesquisando na base de dados..."):
                try:
                    resp = requests.post(f"{API_URL}/api/buscar", json={"termo": termo})
                    if resp.status_code == 200:
                        resultados = resp.json()
                        if not resultados:
                            st.warning("Nenhum resultado encontrado na base simulada.")
                        else:
                            st.success(f"{len(resultados)} normas encontradas.")
                            for item in resultados:
                                with st.expander(f"📘 {item['norma']} - {item['titulo']}"):
                                    st.write(item['texto'])
                                    st.caption("Fonte: Normas Regulamentadoras MTE")
                    else:
                        st.error("Erro ao conectar com a API.")
                except Exception as e:
                    st.error(f"Sistema offline: {e}")

# ==============================================================================
# ABA 2: INSPEÇÃO (CHECKLISTS)
# ==============================================================================
elif selected == "Inspeção":
    st.subheader("📋 Checklist Digital de Campo")
    
    # 1. Busca opções disponíveis no backend
    try:
        resp = requests.get(f"{API_URL}/api/checklists-options")
        opcoes = resp.json() if resp.status_code == 200 else []
    except: opcoes = []
    
    if not opcoes:
        st.warning("Não foi possível carregar os modelos de checklist. Verifique a conexão.")
    
    escolha_checklist = st.selectbox("Selecione o Modelo de Inspeção:", opcoes)
    
    # 2. Se escolheu, busca as perguntas
    dados_respostas = {}
    if escolha_checklist:
        try:
            resp_items = requests.post(f"{API_URL}/api/get-checklist-items", json={"nome": escolha_checklist})
            perguntas = resp_items.json()
            
            with st.form("form_checklist"):
                st.markdown(f"**Auditando: {escolha_checklist}**")
                st.write("---")
                
                for p in perguntas:
                    # Layout: Pergunta na esquerda, Opções na direita
                    c_perg, c_resp = st.columns([3, 2])
                    with c_perg: st.write(p)
                    with c_resp:
                        dados_respostas[p] = st.radio("Status", ["Conforme", "Não Conforme", "N/A"], horizontal=True, key=p, label_visibility="collapsed")
                    st.write("") # Espaço entre linhas
                
                st.write("---")
                col_obs, col_meta = st.columns(2)
                with col_obs:
                    obs = st.text_area("Observações Gerais / Evidências")
                with col_meta:
                    cliente_check = st.text_input("Cliente", value="Empresa Exemplo")
                    auditor_check = st.text_input("Auditor Responsável", value="Eng. Segurança")

                enviar = st.form_submit_button("✅ Finalizar e Gerar Relatório")
                
                if enviar:
                    payload = {
                        "tipo": "checklist",
                        "meta": {"cliente": cliente_check, "projeto": "Auditoria de Campo", "auditor": auditor_check},
                        "dados": dados_respostas
                    }
                    # Adiciona obs se tiver
                    if obs: payload["dados"]["Observações Finais"] = obs
                        
                    res_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json=payload)
                    if res_pdf.status_code == 200:
                        st.success("Relatório gerado com sucesso!")
                        st.download_button("📥 Baixar PDF Assinado", res_pdf.content, "Checklist_Auditoria.pdf", "application/pdf")
                    else:
                        st.error("Erro ao gerar PDF.")
        except:
            st.error("Erro ao carregar itens do checklist.")

# ==============================================================================
# ABA 3: BRIGADA (MENU EM CASCATA DETALHADO)
# ==============================================================================
elif selected == "Brigada":
    st.subheader("🔥 Dimensionamento de Brigada (NBR 14276)")
    
    # --- MENU EM CASCATA (DADOS DETALHADOS) ---
    OPCOES_DETALHADAS = {
        "Grupo A - Residencial": [
            "A-1: Habitação Unifamiliar (Casas térreas/sobrados)",
            "A-2: Habitação Multifamiliar (Edifícios de apartamentos)",
            "A-3: Habitação Coletiva (Pensionatos, alojamentos)"
        ],
        "Grupo B - Serviços de Hospedagem": [
            "B-1: Hotel e assemelhado (Hotéis, motéis)",
            "B-2: Hotel residencial (Flat)"
        ],
        "Grupo C - Comercial": [
            "C-1: Comércio com acesso ao público (Lojas, mercados)",
            "C-2: Comércio em grandes galerias (Shoppings)",
            "C-3: Centros comerciais (Atacadistas)"
        ],
        "Grupo D - Serviço Profissional": [
            "D-1: Local para prestação de serviço (Escritórios)",
            "D-2: Agência bancária",
            "D-3: Serviço de reparação",
            "D-4: Laboratório"
        ],
        "Grupo E - Educacional": [
            "E-1: Escola em geral",
            "E-2: Escola especial",
            "E-3: Espaço para cultura física",
            "E-4: Centro de treinamento"
        ],
        "Grupo F - Reunião de Público": [
            "F-1: Museus/Bibliotecas",
            "F-2: Religiosos (Igrejas)",
            "F-3: Esportivos (Estádios)",
            "F-4: Estações de Passageiros",
            "F-5: Artes cênicas (Teatro)",
            "F-6: Clubes sociais",
            "F-7: Construções provisórias",
            "F-8: Restaurantes"
        ],
        "Grupo G - Serviços Automotivos": [
            "G-1: Garagens/Estacionamentos",
            "G-2: Posto de abastecimento",
            "G-3: Oficinas",
            "G-4: Hangares/Marinas"
        ],
        "Grupo H - Saúde": [
            "H-1: Hospital veterinário",
            "H-2: Hospital com internação",
            "H-3: Ambulatório sem internação",
            "H-4: Edifício público",
            "H-5: Manicômio/Presídio"
        ],
        # --- ATUALIZAÇÃO DETALHADA AQUI ---
        "Grupo I - Indústria": [
            "I-1: Baixo Risco (Até 300 MJ/m² - ex: Metalúrgica, Mecânica, Gesso, Cerâmica, Vidro)",
            "I-2: Médio Risco (300 a 1.200 MJ/m² - ex: Bebidas, Alimentos, Cimento, Têxtil, Calçados)",
            "I-3: Alto Risco (Acima de 1.200 MJ/m² - ex: Borracha, Plásticos, Químicos, Espumas, Tintas)"
        ],
        "Grupo J - Depósito": [
            "J-1: Material Incombustível (Ex: Areia, Cimento, Metais, Pedras)",
            "J-2: Baixo Risco (Até 300 MJ/m² - ex: Cerâmicas, Louças, Metais em peças)",
            "J-3: Médio Risco (300 a 1.200 MJ/m² - ex: Alimentos, Mercadorias em geral, Livros)",
            "J-4: Alto Risco (Acima de 1.200 MJ/m² - ex: Pneus, Plásticos, Papel, Inflamáveis)"
        ],
        "Grupo L - Explosivos": [
            "L-1: Comércio",
            "L-2: Indústria",
            "L-3: Depósito"
        ],
        "Grupo M - Especial": [
            "M-1: Túnel",
            "M-2: Parque de tanques",
            "M-3: Central de energia"
        ]
    }

    c1, c2 = st.columns(2)
    
    with c1:
        st.info("Passo 1: Caracterização da Edificação")
        
        # 1. Escolha do GRUPO
        grupo_selecionado = st.selectbox("Selecione o Grupo Principal:", list(OPCOES_DETALHADAS.keys()))
        
        # 2. Escolha da DIVISÃO (Lista dinâmica baseada no grupo)
        divisao_completa = st.selectbox("Selecione a Atividade Específica:", OPCOES_DETALHADAS[grupo_selecionado])
        
        # Pega só o código (ex: "A-2")
        divisao_codigo = divisao_completa.split(":")[0]
        
        pop = st.number_input("População Total (Fixa + Flutuante)", min_value=1, value=50, help="Somatório de todos os ocupantes.")
        
    with c2:
        st.info("Passo 2: Dimensionamento")
        st.write("###")
        
        if st.button("🔥 Calcular Brigada", type="primary"):
            try:
                resp = requests.post(f"{API_URL}/api/brigada", json={"funcionarios": int(pop), "divisao": divisao_codigo})
                if resp.status_code == 200:
                    d = resp.json()
                    
                    # Se vier zero/erro
                    if d.get('qtd') == 0:
                        st.error(d.get('memoria'))
                    else:
                        # Exibe Resultado Visual
                        k1, k2 = st.columns(2)
                        k1.metric("Brigadistas Mínimos", f"{d.get('qtd')}", delta="Membros")
                        k2.metric("Nível Treinamento", d.get('nivel'))
                        
                        st.markdown(f"""
                        <div style='background-color: #eff6ff; padding: 15px; border-radius: 10px; border-left: 5px solid #2563eb;'>
                            <b>Memória de Cálculo:</b><br>
                            {d.get('memoria')}
                        </div>
                        """, unsafe_allow_html=True)
                        st.write("")
                        
                        # Gerar PDF
                        pay = {"tipo": "brigada", "meta": {"cliente": "Usuário Web", "projeto": divisao_completa}, "dados": d}
                        r_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json=pay)
                        if r_pdf.status_code == 200:
                            st.download_button("📥 Baixar Laudo Técnico PDF", r_pdf.content, "Brigada_NBR14276.pdf", "application/pdf")
                else:
                    st.error("Erro de comunicação com o servidor.")
            except Exception as e: st.error(f"Erro: {e}")

# ==============================================================================
# ABA 4 e 5: CIPA e SESMT (SIMPLES)
# ==============================================================================
else:
    # Define se é CIPA ou SESMT baseado no menu
    modulo = selected
    st.subheader(f"⚙️ Dimensionamento de {modulo} (NR-{ '05' if modulo=='CIPA' else '04' })")
    
    col_input, col_res = st.columns(2)
    
    with col_input:
        st.write("Dados da Empresa")
        in_cnae = st.text_input("CNAE Principal", value="4120400", help="Somente números")
        in_funcs = st.number_input("Número de Funcionários (CLT)", min_value=1, value=100)
        
        nome_cliente = st.text_input("Razão Social", value="Empresa Modelo Ltda")
    
    with col_res:
        st.write("Resultado")
        if st.button(f"Calcular {modulo}", type="primary"):
            endpoint = "cipa" if modulo == "CIPA" else "sesmt"
            
            try:
                resp = requests.post(f"{API_URL}/api/{endpoint}", json={"cnae": in_cnae, "funcionarios": int(in_funcs)})
                
                if resp.status_code == 200:
                    dados = resp.json()
                    
                    if modulo == "CIPA":
                        c1, c2 = st.columns(2)
                        c1.metric("Efetivos", dados.get('efetivos'))
                        c2.metric("Suplentes", dados.get('suplentes'))
                        st.info(f"Grau de Risco: {dados.get('risco')}")
                        
                    else: # SESMT
                        st.write("**Quadro Técnico Exigido:**")
                        st.json(dados.get('equipe'))
                    
                    # Botão PDF
                    pay = {"tipo": endpoint, "meta": {"cliente": nome_cliente, "projeto": f"Dimensionamento {modulo}"}, "dados": dados}
                    r_pdf = requests.post(f"{API_URL}/api/gerar_relatorio", json=pay)
                    if r_pdf.status_code == 200:
                        st.download_button(f"📥 Baixar Relatório {modulo}", r_pdf.content, f"Relatorio_{modulo}.pdf", "application/pdf")
            
            except Exception as e:
                st.error(f"Erro: {e}")
