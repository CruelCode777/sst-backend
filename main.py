import sqlite3
import os
import math
import logging
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO

# Import pypdf safely
try:
    from pypdf import PdfReader
    TEM_PYPDF = True
except ImportError:
    TEM_PYPDF = False

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DB_NAME = "sst_knowledge.db"

# URLs for your PDFs on GitHub (RAW for text extraction, BLOB for viewing)
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/CruelCode777/sst-backend/main/pdfs/"
GITHUB_VIEW_BASE = "https://github.com/CruelCode777/sst-backend/blob/main/pdfs/"

# List of expected files (Add exact names here)
PDF_FILES = [
    "NR-01.pdf", "NR-04.pdf", "NR-05.pdf", "NR-06.pdf", 
    "NR-10.pdf", "NR-12.pdf", "NR-17.pdf", "NR-18.pdf", 
    "NR-23.pdf", "NR-33.pdf", "NR-35.pdf", "NBR-14276.pdf"
]

# --- TECHNICAL TABLES (NBR 14276 & NR-04/05) ---
TABELA_BRIGADA = {
    'A-2': {'nome': 'Habitação Multifamiliar', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'C-1': {'nome': 'Comércio em geral', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'C-2': {'nome': 'Shopping centers', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'D-1': {'nome': 'Escritório', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'I-1': {'nome': 'Indústria (Baixo Risco)', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-2': {'nome': 'Indústria (Médio Risco)', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-3': {'nome': 'Indústria (Alto Risco)', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    'J-2': {'nome': 'Depósito (Baixo Risco)', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'J-3': {'nome': 'Depósito (Médio Risco)', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'}
}

CHECKLISTS_DATA = {
    "NR-06 - EPI": ["EPIs possuem CA válido?", "Ficha de entrega assinada?", "Uso fiscalizado?"],
    "NR-10 - Elétrica": ["Prontuário atualizado?", "Bloqueio/LOTO utilizado?", "Treinamento em dia?"],
    "NR-35 - Altura": ["PT emitida?", "ASO apto para altura?", "Cinto paraquedista ok?"],
    # Add more as needed
}

# --- DATABASE & INDEXING LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(titulo, conteudo, url_view)")
    
    # Check if empty
    c.execute("SELECT count(*) FROM docs")
    count = c.fetchone()[0]
    
    if count == 0 and TEM_PYPDF:
        logger.info("Database empty. Downloading and indexing PDFs from GitHub...")
        
        for filename in PDF_FILES:
            try:
                # 1. Download file content into memory
                raw_url = f"{GITHUB_RAW_BASE}{filename}"
                response = requests.get(raw_url)
                
                if response.status_code == 200:
                    # 2. Extract Text
                    f_stream = BytesIO(response.content)
                    reader = PdfReader(f_stream)
                    text_content = ""
                    # Limit pages to speed up startup
                    for page in reader.pages[:15]: 
                        text_content += page.extract_text() + " "
                    
                    # 3. Save to DB with View URL
                    view_url = f"{GITHUB_VIEW_BASE}{filename}"
                    c.execute("INSERT INTO docs (titulo, conteudo, url_view) VALUES (?, ?, ?)", 
                              (filename, text_content, view_url))
                    logger.info(f"Indexed: {filename}")
                else:
                    logger.warning(f"Could not download {filename} (Status {response.status_code})")
            except Exception as e:
                logger.error(f"Error indexing {filename}: {e}")
                
    conn.commit()
    conn.close()

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="SST.AI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- MODELS ---
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
    # Search logic
    c.execute("SELECT titulo, snippet(docs, 1, '<b>', '</b>', '...', 20), url_view FROM docs WHERE docs MATCH ? ORDER BY rank LIMIT 10", (d.termo,))
    results = [{"titulo": r[0], "trecho": r[1], "url": r[2]} for r in c.fetchall()]
    conn.close()
    return results

@app.post("/api/brigada")
def calc_brigada(d: CalcReq):
    # Default to A-2 if division not found
    regra = TABELA_BRIGADA.get(d.divisao, TABELA_BRIGADA['A-2'])
    
    pop = d.funcionarios
    
    # NBR 14276 Logic
    if pop <= 10:
        qtd = regra['base'] if pop >= regra['base'] else pop
        memoria = f"População ({pop}) ≤ 10. Base fixa adotada: {qtd} brigadistas."
    else:
        exc = pop - 10
        adicional = math.ceil(exc * regra['pct'])
        qtd = regra['base'] + adicional
        memoria = f"Base ({regra['base']}) + {int(regra['pct']*100)}% de {exc} (Excedente) = {qtd} brigadistas."
        
    return {
        "qtd": qtd,
        "nivel": regra['nivel'],
        "memoria": memoria,
        "classificacao": f"{d.divisao} - {regra['nome']}"
    }

@app.post("/api/cipa")
def calc_cipa(d: CalcReq):
    # NR-05 Logic
    risco = 3 if d.cnae.startswith("41") else 2 # Example logic
    efetivos = 0
    suplentes = 0
    
    if d.funcionarios >= 20:
        base = 1 if d.funcionarios < 50 else 2
        efetivos = base + (1 if risco > 2 else 0)
        suplentes = efetivos
        
    memoria = f"NR-05 (Quadro I): Grau de Risco {risco} para {d.funcionarios} funcionários."
    return {"efetivos": efetivos, "suplentes": suplentes, "risco": risco, "memoria": memoria}

@app.post("/api/sesmt")
def calc_sesmt(d: CalcReq):
    # NR-04 Logic
    eq = {}
    risco = 3 if d.cnae.startswith("41") else 2
    
    if d.funcionarios >= 50 and risco >= 3:
        eq["Tec. Seg. Trabalho"] = 1
    elif d.funcionarios >= 100 and risco == 2:
        eq["Tec. Seg. Trabalho"] = 1
        
    if d.funcionarios >= 500 and risco >= 3:
        eq["Eng. Seg. Trabalho"] = 1
        eq["Médico Trabalho"] = 1
        
    memoria = f"NR-04 (Quadro II): Grau de Risco {risco}. Dimensionamento para {d.funcionarios} funcionários."
    return {"equipe": eq, "memoria": memoria}

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    p.setFillColor(colors.HexColor("#0f172a"))
    p.rect(0, h-80, w, 80, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(30, h-50, f"SST.AI RELATÓRIO: {req.tipo.upper()}")
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    y = h - 100
    
    # Metadata
    for k, v in req.meta.items():
        p.drawString(30, y, f"{k}: {v}")
        y -= 15
    y -= 10
    p.line(30, y, w-30, y)
    y -= 30
    
    # Body Data
    if req.dados:
        for k, v in req.dados.items():
            if y < 50: p.showPage(); y = h-50
            
            if isinstance(v, dict):
                p.setFont("Helvetica-Bold", 11)
                p.drawString(30, y, f"{k}:")
                y -= 15
                p.setFont("Helvetica", 10)
                for sk, sv in v.items():
                    p.drawString(40, y, f"- {sk}: {sv}")
                    y -= 15
            else:
                p.setFont("Helvetica-Bold", 10)
                p.drawString(30, y, f"{k}:")
                p.setFont("Helvetica", 10)
                p.drawString(180, y, str(v))
            y -= 20
            
    p.showPage()
    p.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
