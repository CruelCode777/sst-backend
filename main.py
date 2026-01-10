import sqlite3
import os
import math
import logging
import requests
from io import BytesIO
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- IMPORTAÇÕES OPCIONAIS (Evita travamento se faltar lib) ---
try:
    from pypdf import PdfReader
    TEM_PYPDF = True
except ImportError:
    TEM_PYPDF = False

# --- CONFIGURAÇÃO ---
DB_NAME = "sst_knowledge.db"
# Links do GitHub (substitua se mudar o repositório)
GITHUB_RAW = "https://raw.githubusercontent.com/CruelCode777/sst-backend/main/pdfs/"
GITHUB_VIEW = "https://github.com/CruelCode777/sst-backend/blob/main/pdfs/"

# Arquivos para baixar na inicialização
PDF_FILES = ["NR-04.pdf", "NR-05.pdf", "NR-06.pdf", "NR-10.pdf", "NR-35.pdf", "NBR-14276.pdf"]

# --- TABELA DE DADOS BRIGADA (NBR 14276) ---
TABELA_BRIGADA = {
    'A-2': {'base': 2, 'pct': 0.05, 'nivel': 'Básico', 'nome': 'Residencial Multifamiliar'},
    'C-1': {'base': 4, 'pct': 0.05, 'nivel': 'Intermediário', 'nome': 'Comércio Geral'},
    'C-2': {'base': 4, 'pct': 0.05, 'nivel': 'Intermediário', 'nome': 'Shopping Center'},
    'D-1': {'base': 2, 'pct': 0.05, 'nivel': 'Básico', 'nome': 'Escritório'},
    'I-1': {'base': 4, 'pct': 0.07, 'nivel': 'Intermediário', 'nome': 'Indústria Baixo Risco'},
    'I-2': {'base': 8, 'pct': 0.07, 'nivel': 'Intermediário', 'nome': 'Indústria Médio Risco'},
    'I-3': {'base': 10, 'pct': 0.10, 'nivel': 'Avançado', 'nome': 'Indústria Alto Risco'},
    'J-1': {'base': 2, 'pct': 0.05, 'nivel': 'Básico', 'nome': 'Depósito Incombustível'},
    'J-2': {'base': 4, 'pct': 0.07, 'nivel': 'Intermediário', 'nome': 'Depósito Baixo Risco'}
}

# --- FUNÇÕES DE BANCO DE DADOS ---
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(titulo, conteudo, url_view)")
        
        # Verifica se está vazio
        c.execute("SELECT count(*) FROM docs")
        if c.fetchone()[0] == 0:
            logger.info("Baixando PDFs do GitHub...")
            if TEM_PYPDF:
                for pdf in PDF_FILES:
                    try:
                        r = requests.get(f"{GITHUB_RAW}{pdf}", timeout=10)
                        if r.status_code == 200:
                            reader = PdfReader(BytesIO(r.content))
                            texto = ""
                            for page in reader.pages[:10]: texto += page.extract_text() + " "
                            link_view = f"{GITHUB_VIEW}{pdf}"
                            c.execute("INSERT INTO docs VALUES (?, ?, ?)", (pdf, texto, link_view))
                            logger.info(f"Indexado: {pdf}")
                    except Exception as e:
                        logger.warning(f"Falha ao indexar {pdf}: {e}")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro crítico DB: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- MODELOS DE DADOS ---
class BuscaReq(BaseModel): termo: str
class CalcReq(BaseModel): cnae: str = ""; funcionarios: int = 0; divisao: str = ""
class RelatorioReq(BaseModel): tipo: str; dados: dict; meta: dict

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Online", "msg": "API SST Funcionando"}

@app.post("/api/buscar")
def buscar(d: BuscaReq):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT titulo, snippet(docs, 1, '<b>', '</b>', '...', 20), url_view FROM docs WHERE docs MATCH ? LIMIT 10", (d.termo,))
        res = [{"titulo": r[0], "trecho": r[1], "url": r[2]} for r in c.fetchall()]
        conn.close()
        return res
    except:
        return []

# --- CALCULADORA DE BRIGADA (LÓGICA CORRIGIDA) ---
@app.post("/api/brigada")
def calc_brigada(d: CalcReq):
    logger.info(f"Calculando Brigada: {d.divisao} | Pop: {d.funcionarios}")
    
    # 1. Limpeza da String (Pega "A-2" de "A-2: Residencial")
    div_limpa = d.divisao.split(":")[0].strip()
    
    # 2. Busca na Tabela (Com Fallback/Segurança)
    regra = TABELA_BRIGADA.get(div_limpa)
    
    if not regra:
        # Se não achou exato, tenta achar algo parecido ou usa padrão
        if div_limpa.startswith("A"): regra = TABELA_BRIGADA['A-2']
        elif div_limpa.startswith("C"): regra = TABELA_BRIGADA['C-1']
        elif div_limpa.startswith("I"): regra = TABELA_BRIGADA['I-2']
        else: regra = TABELA_BRIGADA['D-1'] # Padrão Escritório
        
    pop = d.funcionarios
    
    # 3. Matemática NBR 14276
    if pop <= 10:
        qtd = regra['base'] if pop >= regra['base'] else pop
        memoria = f"População Baixa ({pop}). Qtd = Base Fixa ({qtd})."
    else:
        exc = pop - 10
        adicional = math.ceil(exc * regra['pct'])
        qtd = regra['base'] + adicional
        memoria = f"Base ({regra['base']}) + {int(regra['pct']*100)}% de {exc} (Excedente) = {qtd}."
        
    return {
        "qtd": qtd, 
        "nivel": regra['nivel'], 
        "memoria": memoria, 
        "classificacao": regra['nome']
    }

@app.post("/api/cipa")
def calc_cipa(d: CalcReq):
    risco = 3 if d.cnae.startswith("41") else 2
    efetivos = 0
    if d.funcionarios >= 20:
        base = 1 if d.funcionarios < 50 else 2
        efetivos = base + (1 if risco >= 3 else 0)
    
    return {
        "efetivos": efetivos, 
        "suplentes": efetivos, 
        "risco": risco, 
        "memoria": f"Quadro I (NR-05) - Grau de Risco {risco}"
    }

@app.post("/api/sesmt")
def calc_sesmt(d: CalcReq):
    risco = 3 if d.cnae.startswith("41") else 2
    eq = {}
    if d.funcionarios >= 50 and risco >= 3: eq["Tec. Seg."] = 1
    elif d.funcionarios >= 101 and risco == 2: eq["Tec. Seg."] = 1
    
    if d.funcionarios >= 500 and risco >= 3:
        eq["Eng. Seg."] = 1
        eq["Tec. Seg."] = 3

    return {
        "equipe": eq, 
        "memoria": f"Quadro II (NR-04) - Grau de Risco {risco}"
    }

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Cabeçalho
    p.setFillColor(colors.HexColor("#0f172a"))
    p.rect(0, h-80, w, 80, fill=1, stroke=0)
    p.setFillColor(colors.white); p.setFont("Helvetica-Bold", 16)
    p.drawString(30, h-50, f"RELATÓRIO TÉCNICO: {req.tipo.upper()}")
    
    p.setFillColor(colors.black); p.setFont("Helvetica", 10)
    y = h - 100
    
    # Metadados
    for k,v in req.meta.items():
        p.drawString(30, y, f"{k}: {v}"); y-=15
    y-=10; p.line(30, y, w-30, y); y-=30
    
    # Dados
    if req.dados:
        for k, v in req.dados.items():
            if y < 50: p.showPage(); y=h-50
            if isinstance(v, dict):
                p.setFont("Helvetica-Bold", 11); p.drawString(30, y, f"{k}:"); y-=15
                p.setFont("Helvetica", 10)
                for sk, sv in v.items(): p.drawString(40, y, f"- {sk}: {sv}"); y-=15
            else:
                p.setFont("Helvetica-Bold", 10); p.drawString(30, y, f"{k}:")
                p.setFont("Helvetica", 10); p.drawString(150, y, str(v))
            y-=20
            
    p.showPage()
    p.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
