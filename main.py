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

# --- IMPORTAÇÕES SEGURAS (Para o servidor não travar se faltar algo) ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    TEM_REPORTLAB = True
except ImportError:
    TEM_REPORTLAB = False

try:
    from pypdf import PdfReader
    TEM_PYPDF = True
except ImportError:
    TEM_PYPDF = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO ---
DB_NAME = "sst_knowledge.db"
# URLs do seu repositório (Pasta pdfs na raiz)
GITHUB_RAW = "https://raw.githubusercontent.com/CruelCode777/sst-backend/main/pdfs/"
GITHUB_VIEW = "https://github.com/CruelCode777/sst-backend/blob/main/pdfs/"

# Arquivos que o sistema vai tentar baixar e indexar
PDF_FILES = [
    "NR-04.pdf", "NR-05.pdf", "NR-06.pdf", "NR-10.pdf", 
    "NR-12.pdf", "NR-35.pdf", "NBR-14276.pdf"
]

# --- TABELA BRIGADA (NBR 14276 SIMPLIFICADA) ---
TABELA_BRIGADA = {
    'A-2': {'base': 2, 'pct': 0.05, 'nivel': 'Básico', 'nome': 'Residencial Multifamiliar'},
    'C-1': {'base': 4, 'pct': 0.05, 'nivel': 'Intermediário', 'nome': 'Comércio'},
    'D-1': {'base': 2, 'pct': 0.05, 'nivel': 'Básico', 'nome': 'Escritório'},
    'I-2': {'base': 8, 'pct': 0.07, 'nivel': 'Intermediário', 'nome': 'Indústria Médio Risco'},
    'J-2': {'base': 4, 'pct': 0.07, 'nivel': 'Intermediário', 'nome': 'Depósito'}
}

# --- BANCO DE DADOS ---
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(titulo, conteudo, url_view)")
        
        # Se vazio, tenta baixar do GitHub
        c.execute("SELECT count(*) FROM docs")
        if c.fetchone()[0] == 0:
            logger.info("Baixando PDFs do GitHub para memória...")
            sucesso = False
            
            if TEM_PYPDF:
                for pdf in PDF_FILES:
                    try:
                        # Timeout para não travar o servidor
                        r = requests.get(f"{GITHUB_RAW}{pdf}", timeout=5)
                        if r.status_code == 200:
                            reader = PdfReader(BytesIO(r.content))
                            texto = ""
                            for page in reader.pages[:10]: texto += page.extract_text() + " "
                            
                            link_view = f"{GITHUB_VIEW}{pdf}"
                            c.execute("INSERT INTO docs VALUES (?, ?, ?)", (pdf, texto, link_view))
                            sucesso = True
                            logger.info(f"Indexado: {pdf}")
                    except Exception as e:
                        logger.warning(f"Erro ao indexar {pdf}: {e}")
            
            # Insere dados de backup se o download falhar
            if not sucesso:
                BACKUP = [
                    ("NR-06", "EPI Equipamento Proteção Individual Capacete Bota", f"{GITHUB_VIEW}NR-06.pdf"),
                    ("NR-35", "Trabalho em Altura Cinto Paraquedista 2 metros", f"{GITHUB_VIEW}NR-35.pdf"),
                    ("NBR-14276", "Brigada de Incêndio Dimensionamento", f"{GITHUB_VIEW}NBR-14276.pdf")
                ]
                c.executemany("INSERT INTO docs VALUES (?, ?, ?)", BACKUP)
                
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro crítico no Banco de Dados: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- MODELOS ---
class BuscaReq(BaseModel): termo: str
class CalcReq(BaseModel): cnae: str = ""; funcionarios: int = 0; divisao: str = ""
class RelatorioReq(BaseModel): tipo: str; dados: dict; meta: dict

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Online", "msg": "SST API rodando"}

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

@app.post("/api/brigada")
def calc_brigada(d: CalcReq):
    # Lógica de Segurança (Fallback)
    div = d.divisao
    if div not in TABELA_BRIGADA:
        div = 'D-1' # Padrão seguro
    
    regra = TABELA_BRIGADA[div]
    pop = d.funcionarios
    
    if pop <= 10:
        qtd = regra['base'] if pop >= regra['base'] else pop
        mem = f"População ({pop}) <= 10. Base Fixa."
    else:
        exc = pop - 10
        add = math.ceil(exc * regra['pct'])
        qtd = regra['base'] + add
        mem = f"Base ({regra['base']}) + {int(regra['pct']*100)}% de {exc} (Excedente) = {qtd}."
        
    return {"qtd": qtd, "nivel": regra['nivel'], "memoria": mem, "classificacao": regra['nome']}

@app.post("/api/cipa")
def calc_cipa(d: CalcReq):
    # Lógica NR-05
    risco = 3 if d.cnae.startswith("41") else 2
    efetivos = 0
    if d.funcionarios >= 20:
        base = 1 if d.funcionarios < 50 else 2
        efetivos = base + (1 if risco >= 3 else 0)
    
    mem = f"NR-05 Quadro I: Grau Risco {risco} para {d.funcionarios} funcionários."
    return {"efetivos": efetivos, "suplentes": efetivos, "risco": risco, "memoria": mem}

@app.post("/api/sesmt")
def calc_sesmt(d: CalcReq):
    # Lógica NR-04
    risco = 3 if d.cnae.startswith("41") else 2
    eq = {}
    
    if d.funcionarios >= 50 and risco >= 3:
        eq["Técnico de Seg."] = 1
    elif d.funcionarios >= 101 and risco == 2:
        eq["Técnico de Seg."] = 1
        
    if d.funcionarios >= 500 and risco >= 3:
        eq["Engenheiro de Seg."] = 1
        eq["Técnico de Seg."] = 3
        
    msg = f"Dimensionamento NR-04 (Grau {risco})."
    if not eq: msg += " Empresa desobrigada de SESMT próprio."
        
    return {"equipe": eq, "memoria": msg}

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    if not TEM_REPORTLAB:
        return {"erro": "Biblioteca PDF não instalada no servidor"}

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Cabeçalho Azul
    p.setFillColor(colors.HexColor("#0f172a"))
    p.rect(0, h-80, w, 80, fill=1, stroke=0)
    p.setFillColor(colors.white); p.setFont("Helvetica-Bold", 16)
    p.drawString(30, h-50, f"RELATÓRIO: {req.tipo.upper()}")
    
    p.setFillColor(colors.black); p.setFont("Helvetica", 10)
    y = h - 100
    
    for k,v in req.meta.items():
        p.drawString(30, y, f"{k}: {v}"); y-=15
    y-=20; p.line(30, y, w-30, y); y-=30
    
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
