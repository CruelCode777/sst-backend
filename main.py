import sqlite3
import os
import math
import io
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# Importação Segura do Leitor de PDF
try:
    from pypdf import PdfReader
    TEM_PYPDF = True
except ImportError:
    TEM_PYPDF = False

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DE CAMINHOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PDFS = os.path.join(BASE_DIR, "pdfs")
DB_NAME = "sst_master_db.db"

# --- TABELAS TÉCNICAS (CONFORME NORMAS) ---

# NBR 14276 (Tabela A.1 Simplificada para uso prático)
TABELA_BRIGADA = {
    # GRUPO A - RESIDENCIAL
    'A-1': {'nome': 'Habitação Unifamiliar', 'base': 2, 'pct': 0.0, 'nivel': 'Básico'},
    'A-2': {'nome': 'Habitação Multifamiliar', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'A-3': {'nome': 'Habitação Coletiva', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    # GRUPO B - HOSPEDAGEM
    'B-1': {'nome': 'Hotel e assemelhado', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'B-2': {'nome': 'Hotel residencial', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    # GRUPO C - COMERCIAL
    'C-1': {'nome': 'Comércio em geral', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'C-2': {'nome': 'Shopping centers', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    # GRUPO D - SERVIÇO
    'D-1': {'nome': 'Escritório', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'D-2': {'nome': 'Agência bancária', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    # GRUPO I - INDÚSTRIA
    'I-1': {'nome': 'Indústria (Carga Baixa)', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-2': {'nome': 'Indústria (Carga Média)', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-3': {'nome': 'Indústria (Carga Alta)', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    # GRUPO J - DEPÓSITO
    'J-1': {'nome': 'Depósito (Incombustível)', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'J-2': {'nome': 'Depósito (Carga Baixa)', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'J-3': {'nome': 'Depósito (Carga Média)', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'},
    'J-4': {'nome': 'Depósito (Carga Alta)', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'}
}

# CHECKLISTS COMPLETOS (NRs)
CHECKLISTS_DATA = {
    "NR-01 - Gerenciamento de Riscos (PGR)": [
        "O PGR contempla todos os perigos identificados na etapa preliminar?",
        "A matriz de risco utilizada está definida e documentada?",
        "Os trabalhadores foram consultados sobre a percepção de riscos?",
        "O plano de ação possui datas definidas e responsáveis nomeados?",
        "Há evidências da implementação das medidas de controle?",
        "O PGR é revisado a cada 2 anos ou quando há mudanças?"
    ],
    "NR-05 - CIPA": [
        "A CIPA está dimensionada corretamente (Quadro I da NR-05)?",
        "O edital de convocação foi publicado no prazo (45 dias antes)?",
        "A eleição teve participação de mais de 50% dos empregados?",
        "O treinamento dos cipeiros (20h) foi realizado antes da posse?",
        "O calendário de reuniões ordinárias está sendo cumprido?",
        "As atas de reunião estão assinadas e arquivadas?",
        "A CIPA participa da análise de acidentes de trabalho?"
    ],
    "NR-06 - Equipamento de Proteção (EPI)": [
        "Todos os EPIs possuem CA (Certificado de Aprovação) válido?",
        "Existe ficha de EPI individual assinada para cada funcionário?",
        "A empresa fiscaliza e exige o uso do EPI?",
        "É realizada a higienização e manutenção periódica dos EPIs?",
        "Os EPIs danificados são substituídos imediatamente?",
        "Foi realizado treinamento sobre uso, guarda e conservação?"
    ],
    "NR-10 - Instalações Elétricas": [
        "O Prontuário das Instalações Elétricas (PIE) está atualizado?",
        "Os diagramas unifilares correspondem à realidade em campo?",
        "Os quadros elétricos estão sinalizados (raio) e travados?",
        "O sistema de bloqueio e etiquetagem (LOTO) é utilizado?",
        "Os trabalhadores possuem curso Básico (40h) e SEP (40h)?",
        "As vestimentas são adequadas para Classe de Risco 2 (Arco)?",
        "O Laudo de SPDA e Aterramento está vigente?"
    ],
    "NR-12 - Máquinas e Equipamentos": [
        "As transmissões de força (correias/polias) possuem proteções fixas?",
        "As zonas de perigo possuem proteções móveis com intertravamento?",
        "Os botões de emergência estão acessíveis e funcionais?",
        "O reset do sistema de segurança é manual e intencional?",
        "A sinalização de segurança está em português e legível?",
        "Foi realizada a Análise de Risco (HRN ou similar) da máquina?",
        "O piso ao redor da máquina está limpo e desobstruído?"
    ],
    "NR-23 - Proteção Contra Incêndio": [
        "Os extintores estão com carga, lacre e validade em dia?",
        "Os extintores estão desobstruídos e sinalizados (piso/parede)?",
        "As saídas de emergência abrem para fora e têm barra antipânico?",
        "A iluminação de emergência funciona ao cortar a energia?",
        "A sinalização de rota de fuga é fotoluminescente?",
        "A brigada de incêndio possui treinamento e reciclagens em dia?",
        "O alarme de incêndio é audível em toda a edificação?"
    ],
    "NR-35 - Trabalho em Altura": [
        "A Análise de Risco (AR) foi feita antes da atividade?",
        "A Permissão de Trabalho (PT) foi emitida e assinada?",
        "O trabalhador possui ASO com aptidão para altura?",
        "O treinamento de NR-35 (8h) está válido?",
        "O cinto é do tipo paraquedista com talabarte duplo?",
        "O ponto de ancoragem é certificado ou inspecionado?",
        "A área abaixo do trabalho está isolada e sinalizada?"
    ]
}

# --- FUNÇÕES AUXILIARES ---
def init_db():
    """Inicializa o banco e indexa os PDFs se existirem."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(titulo, conteudo, url)")
    
    # Verifica se já indexou
    c.execute("SELECT count(*) FROM docs")
    if c.fetchone()[0] == 0:
        logger.info("Indexando PDFs pela primeira vez...")
        if os.path.exists(CAMINHO_PDFS) and TEM_PYPDF:
            arquivos = [f for f in os.listdir(CAMINHO_PDFS) if f.endswith(".pdf")]
            for arq in arquivos:
                try:
                    reader = PdfReader(os.path.join(CAMINHO_PDFS, arq))
                    texto = ""
                    # Lê até 10 páginas para performance
                    for page in reader.pages[:10]:
                        texto += page.extract_text() + " "
                    
                    # URL Pública para o Frontend
                    url_publica = f"/pdfs/{arq}"
                    c.execute("INSERT INTO docs (titulo, conteudo, url) VALUES (?, ?, ?)", 
                              (arq, texto, url_publica))
                except Exception as e:
                    logger.error(f"Erro ao ler {arq}: {e}")
        else:
            # DADOS DE BACKUP (Para não quebrar se não tiver PDF)
            BKP = [
                ("NR-06.pdf", "Equipamento de Proteção Individual EPI Capacete Luva", "n/a"),
                ("NR-10.pdf", "Segurança em Instalações Elétricas Bloqueio LOTO", "n/a"),
                ("NR-35.pdf", "Trabalho em Altura Cinto Paraquedista Ancoragem", "n/a")
            ]
            c.executemany("INSERT INTO docs (titulo, conteudo, url) VALUES (?, ?, ?)", BKP)
            
    conn.commit()
    conn.close()

# --- LIFESPAN (INICIALIZAÇÃO) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Monta a pasta PDF para acesso público (ex: site.com/pdfs/nr10.pdf)
if os.path.exists(CAMINHO_PDFS):
    app.mount("/pdfs", StaticFiles(directory=CAMINHO_PDFS), name="pdfs")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- MODELOS ---
class BuscaReq(BaseModel): termo: str
class CalcReq(BaseModel): cnae: str = ""; funcionarios: int = 0; divisao: str = ""
class RelatorioReq(BaseModel): tipo: str; dados: dict; meta: dict

# --- ENDPOINTS ---

@app.get("/api/checklists-options")
def get_checklists():
    return list(CHECKLISTS_DATA.keys())

@app.post("/api/get-checklist-items")
def get_items(req: dict):
    return CHECKLISTS_DATA.get(req.get("nome"), [])

@app.post("/api/buscar")
def buscar(d: BuscaReq):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Snippet cria um resumo do texto encontrado
    c.execute("SELECT titulo, snippet(docs, 1, '<b>', '</b>', '...', 20), url FROM docs WHERE docs MATCH ? ORDER BY rank LIMIT 10", (d.termo,))
    res = [{"titulo": r[0], "trecho": r[1], "url": r[2]} for r in c.fetchall()]
    conn.close()
    return res

@app.post("/api/brigada")
def calc_brigada(d: CalcReq):
    # Lógica NBR 14276 Exata
    regra = TABELA_BRIGADA.get(d.divisao)
    
    # Fallback de segurança se a divisão vier errada
    if not regra:
        if d.divisao.startswith('A'): regra = TABELA_BRIGADA['A-2']
        elif d.divisao.startswith('C'): regra = TABELA_BRIGADA['C-1']
        elif d.divisao.startswith('I'): regra = TABELA_BRIGADA['I-2']
        else: regra = TABELA_BRIGADA['D-1']

    pop = d.funcionarios
    
    # Cálculo NBR
    if pop <= 10:
        qtd = regra['base'] if pop >= regra['base'] else pop
        memoria = f"População ({pop}) ≤ 10. Adotado Base Fixa ou População total: {qtd}."
    else:
        exc = pop - 10
        adicional = math.ceil(exc * regra['pct'])
        qtd = regra['base'] + adicional
        memoria = f"Base ({regra['base']}) + {int(regra['pct']*100)}% sobre excedente de 10 ({exc} pessoas = {adicional}) = Total {qtd}."

    return {
        "qtd": qtd,
        "nivel": regra['nivel'],
        "memoria": memoria,
        "classificacao": f"{d.divisao} - {regra['nome']}"
    }

@app.post("/api/cipa")
def calc_cipa(d: CalcReq):
    # Lógica NR-05 (Simplificada para Robustez)
    # Grau de Risco baseado no CNAE (Simulação: Construção=3, Outros=2)
    risco = 3 if d.cnae.startswith("41") else 2
    
    # Tabela Quadro I (Resumida)
    if d.funcionarios < 20:
        efetivos, suplentes = 0, 0
        obs = "Designado (NR-05.4.13)"
    elif 20 <= d.funcionarios <= 29:
        efetivos, suplentes = 1, 1
        obs = "Quadro I"
    elif 30 <= d.funcionarios <= 50:
        efetivos, suplentes = (1, 1) if risco <= 2 else (2, 2)
        obs = "Quadro I"
    elif 51 <= d.funcionarios <= 100:
        efetivos, suplentes = (2, 2) if risco <= 2 else (3, 3)
        obs = "Quadro I"
    else:
        efetivos, suplentes = 4, 3
        obs = "Quadro I (Faixa > 100)"

    return {
        "efetivos": efetivos, 
        "suplentes": suplentes, 
        "risco": risco, 
        "memoria": f"Dimensionamento p/ Grau de Risco {risco} e {d.funcionarios} func. ({obs})"
    }

@app.post("/api/sesmt")
def calc_sesmt(d: CalcReq):
    # Lógica NR-04 (Simplificada para Robustez)
    eq = {}
    risco = 3 if d.cnae.startswith("41") else 2
    
    if d.funcionarios >= 50 and risco >= 3:
        eq["Técnico de Seg."] = 1
    elif d.funcionarios >= 101 and risco == 2:
        eq["Técnico de Seg."] = 1
        
    if d.funcionarios >= 500 and risco >= 3:
        eq["Engenheiro de Seg."] = 1
        eq["Médico do Trabalho"] = 1
        eq["Técnico de Seg."] = 3
        
    memoria = f"Quadro II NR-04 (Grau {risco}, {d.funcionarios} func)."
    if not eq:
        memoria += " Não há exigência de quadro próprio, apenas assistência."
        
    return {"equipe": eq, "memoria": memoria}

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Cabeçalho
    p.setFillColor(colors.HexColor("#003366"))
    p.rect(0, h-80, w, 80, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(30, h-50, f"RELATÓRIO TÉCNICO: {req.tipo.upper()}")
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    y = h - 110
    
    # Metadados
    for k, v in req.meta.items():
        p.drawString(30, y, f"{k}: {v}")
        y -= 15
    y -= 10
    p.line(30, y, w-30, y)
    y -= 25
    
    # Dados
    if req.dados:
        for k, v in req.dados.items():
            if y < 50: p.showPage(); y = h-50
            
            # Formatação Específica
            if req.tipo == "checklist":
                txt_status = str(v)
                if "Conforme" in txt_status and "Não" not in txt_status:
                    p.setFillColor(colors.green)
                elif "Não Conforme" in txt_status:
                    p.setFillColor(colors.red)
                else:
                    p.setFillColor(colors.gray)
                p.circle(20, y+3, 3, fill=1, stroke=0)
                p.setFillColor(colors.black)
                p.drawString(30, y, f"{k}: {v}")
            
            elif isinstance(v, dict):
                p.setFont("Helvetica-Bold", 11)
                p.drawString(30, y, f"{k}:")
                y -= 15
                p.setFont("Helvetica", 10)
                for sub_k, sub_v in v.items():
                    p.drawString(40, y, f"- {sub_k}: {sub_v}")
                    y -= 15
            else:
                p.setFont("Helvetica-Bold", 10)
                p.drawString(30, y, f"{k}:")
                p.setFont("Helvetica", 10)
                p.drawString(150, y, str(v))
            
            y -= 20
            
    p.showPage()
    p.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
