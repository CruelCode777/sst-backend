import sqlite3
import os
import math
import io
import textwrap
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from checklists import DADOS_CHECKLISTS 

app = FastAPI(title="SST.AI - Suite Master")

caminho_pdfs = os.path.join(os.path.dirname(__file__), "pdfs")
if os.path.exists(caminho_pdfs):
    app.mount("/pdfs", StaticFiles(directory=caminho_pdfs), name="pdfs")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

DB_NAME = "dados_seguranca.db"

# --- MODELOS ---
class CalculoReq(BaseModel):
    cnae: str; funcionarios: int
class BrigadaReq(BaseModel):
    funcionarios: int; divisao: str 
class BuscaReq(BaseModel):
    termo: str
class RelatorioReq(BaseModel):
    tipo: str; dados: dict; meta: dict = {}

# --- TABELAS COMPLETAS ---
TABELA_NBR14276 = {
    'A-1': {'nome': 'Habitação Unifamiliar', 'base': 0, 'pct': 0, 'nivel': '-'},
    'A-2': {'nome': 'Habitação Multifamiliar', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'A-3': {'nome': 'Habitação Coletiva', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'B-1': {'nome': 'Hotel / Motel', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'B-2': {'nome': 'Flat / Apart Hotel', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'C-1': {'nome': 'Comércio em Geral', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'C-2': {'nome': 'Shopping Centers', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'C-3': {'nome': 'Centros Comerciais', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'D-1': {'nome': 'Escritórios / Adm', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'D-2': {'nome': 'Agência Bancária', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'D-3': {'nome': 'Serviço de Reparação', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'D-4': {'nome': 'Laboratórios / Estúdios', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'E-1': {'nome': 'Escolas em Geral', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'E-2': {'nome': 'Creches / Escolas Especiais', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'E-3': {'nome': 'Espaço de Cultura Física', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'E-4': {'nome': 'Centro de Treinamento', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-1': {'nome': 'Museus / Históricos', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-2': {'nome': 'Igrejas / Templos', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-3': {'nome': 'Estádios / Ginásios', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-4': {'nome': 'Estações de Transporte', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-5': {'nome': 'Teatros / Cinemas', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-6': {'nome': 'Clubes / Salões de Festa', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-8': {'nome': 'Restaurantes / Bares', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'G-1': {'nome': 'Garagens / Estacionamentos', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'G-2': {'nome': 'Postos de Combustível', 'base': 4, 'pct': 0.10, 'nivel': 'Avançado'},
    'G-3': {'nome': 'Oficinas / Hangares', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'H-1': {'nome': 'Hospitais Veterinários', 'base': 6, 'pct': 0.07, 'nivel': 'Intermediário'},
    'H-2': {'nome': 'Hospitais (Com Internação)', 'base': 10, 'pct': 0.07, 'nivel': 'Intermediário'},
    'H-3': {'nome': 'Clínicas (Sem Internação)', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'I-1': {'nome': 'Indústria (Baixo Risco)', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-2': {'nome': 'Indústria (Médio Risco)', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-3': {'nome': 'Indústria (Alto Risco)', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    'J-1': {'nome': 'Depósito (Incombustível)', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'J-2': {'nome': 'Depósito (Baixo Risco)', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'J-3': {'nome': 'Depósito (Médio Risco)', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'},
    'J-4': {'nome': 'Depósito (Alto Risco)', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    'L-1': {'nome': 'Comércio de Explosivos', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    'L-2': {'nome': 'Indústria de Explosivos', 'base': 10, 'pct': 0.15, 'nivel': 'Avançado'},
    'L-3': {'nome': 'Depósito de Explosivos', 'base': 10, 'pct': 0.15, 'nivel': 'Avançado'},
    'M-1': {'nome': 'Túneis', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    'M-2': {'nome': 'Líquidos Inflamáveis', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'}
}

TABELA_SESMT = {
    1: [(0,49,0,0,0,0,0),(50,100,0,0,0,0,0),(101,250,0,0,0,0,0),(251,500,0,0,0,0,0),(501,1000,0,0,0,0,0),(1001,2000,1,0,0,0,1),(2001,3500,1,0,0,0,1),(3501,5000,2,1,0,0,1),(5001,9999999,2,1,0,0,1)],
    2: [(0,49,0,0,0,0,0),(50,100,0,0,0,0,0),(101,250,0,0,0,0,0),(251,500,0,0,0,0,0),(501,1000,1,0,0,0,0),(1001,2000,1,0,0,0,1),(2001,3500,1,1,1,0,1),(3501,5000,2,1,1,0,1),(5001,9999999,2,1,1,0,1)],
    3: [(0,49,0,0,0,0,0),(50,100,0,0,0,0,0),(101,250,0,0,0,0,0),(251,500,1,0,0,0,0),(501,1000,2,0,0,0,0),(1001,2000,3,1,0,0,1),(2001,3500,4,1,0,0,1),(3501,5000,6,2,0,0,1),(5001,9999999,8,2,0,0,1)],
    4: [(0,49,0,0,0,0,0),(50,100,1,0,0,0,0),(101,250,2,0,0,0,0),(251,500,3,0,0,0,1),(501,1000,4,1,0,0,1),(1001,2000,5,1,0,0,1),(2001,3500,8,2,1,0,1),(3501,5000,10,3,1,0,1),(5001,9999999,10,3,1,0,1)]
}

TABELA_CIPA = {
    1: [(0,19,0,0),(20,29,1,1),(30,50,1,1),(51,100,2,2),(101,250,2,2),(251,500,3,3),(501,1000,4,4),(1001,2500,4,4),(2501,5000,5,5),(5001,10000,6,5)],
    2: [(0,19,0,0),(20,29,1,1),(30,50,3,3),(51,100,4,4),(101,250,4,4),(251,500,5,5),(501,1000,6,5),(1001,2500,7,6),(2501,5000,9,7),(5001,10000,10,8)],
    3: [(0,19,0,0),(20,29,1,1),(30,50,3,2),(51,100,4,3),(101,250,5,4),(251,500,7,5),(501,1000,9,7),(1001,2500,10,8),(2501,5000,12,9),(5001,10000,15,12)],
    4: [(0,19,0,0),(20,29,2,2),(30,50,4,3),(51,100,5,4),(101,250,6,5),(251,500,9,7),(501,1000,11,8),(1001,2500,13,10),(2501,5000,16,12),(5001,10000,18,15)]
}

LABELS_PDF = {"qtd": "Brigadistas Sugeridos", "nivel": "Nível do Treinamento", "divisao_desc": "Classificação", "memoria": "Memória de Cálculo", "obs": "Observações Técnicas", "risco": "Grau de Risco (NR-04)", "atividade": "CNAE / Atividade", "efetivos": "Membros Efetivos", "suplentes": "Membros Suplentes"}

# --- ROTAS ---
@app.post("/api/buscar")
def buscar_normas(d: BuscaReq):
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    try:
        c.execute("SELECT titulo, snippet(normas_fts, 1, '<b>', '</b>', '...', 15), url_pdf, pagina FROM normas_fts WHERE normas_fts MATCH ? ORDER BY rank LIMIT 50", (d.termo,))
        res = [{"titulo": r[0], "trecho": r[1], "url": r[2], "pagina": r[3]} for r in c.fetchall()]
    except: res = []
    conn.close(); return res

@app.get("/api/checklists")
def listar_checklists(): return DADOS_CHECKLISTS

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = io.BytesIO(); p = canvas.Canvas(buffer, pagesize=A4); width, height = A4
    
    p.setFillColor(colors.HexColor("#1e3a8a")); p.rect(0, height - 130, width, 130, fill=True, stroke=False)
    p.setFillColor(colors.white); p.setFont("Helvetica-Bold", 24); p.drawString(40, height - 50, "RELATÓRIO TÉCNICO SST")
    
    cli = req.meta.get('cliente', 'Não Informado'); aud = req.meta.get('auditor', 'Não Informado'); setor = req.meta.get('setor', 'Geral')
    p.setFont("Helvetica", 12); p.drawString(40, height - 80, f"Cliente: {cli}"); p.drawString(40, height - 100, f"Local/Setor: {setor}")
    p.drawRightString(width - 40, height - 50, "SST.AI"); p.setFont("Helvetica", 10)
    p.drawRightString(width - 40, height - 80, f"Auditor: {aud}"); p.drawRightString(width - 40, height - 100, f"Data: {datetime.now().strftime('%d/%m/%Y')}")

    p.setFillColor(colors.black); y = height - 160
    titulos = {'checklist': "RELATÓRIO DE INSPEÇÃO", 'brigada': "DIMENSIONAMENTO DE BRIGADA", 'cipa': "DIMENSIONAMENTO DE CIPA", 'sesmt': "DIMENSIONAMENTO DE SESMT"}
    titulo = titulos.get(req.tipo, "RELATÓRIO")
    
    p.setFont("Helvetica-Bold", 14); p.drawString(40, y, titulo); p.line(40, y-5, width-40, y-5); y -= 40
    
    if req.tipo == 'checklist':
        p.setFont("Helvetica", 10)
        for item, detalhes in req.dados.items():
            if y < 80: p.showPage(); y = height - 50; p.setFont("Helvetica", 10)
            status = detalhes.get("status", "NA"); obs = detalhes.get("obs", "")
            cor, txt = (colors.gray, "NA")
            if status == "C": cor, txt = (colors.green, "OK")
            elif status == "NC": cor, txt = (colors.red, "NC")
            
            p.setFillColor(cor); p.roundRect(40, y-2, 30, 14, 2, fill=True, stroke=False)
            p.setFillColor(colors.white); p.setFont("Helvetica-Bold", 9); p.drawCentredString(55, y+2, txt)
            p.setFillColor(colors.black); p.setFont("Helvetica", 10)
            lines = textwrap.wrap(item, width=85); 
            for l in lines: p.drawString(80, y, l); y -= 12
            if obs:
                p.setFillColor(colors.HexColor("#4b5563")); p.setFont("Helvetica-Oblique", 9)
                obl = textwrap.wrap(f"Obs: {obs}", width=85)
                for l in obl: p.drawString(80, y, l); y -= 12
            y -= 5; p.setStrokeColor(colors.lightgrey); p.line(40, y, width-40, y); y -= 15
    else:
        p.setFont("Helvetica", 12)
        for chave, valor in req.dados.items():
            if y < 60: p.showPage(); y = height - 60
            label = LABELS_PDF.get(chave, chave.capitalize())
            if isinstance(valor, dict):
                p.setFont("Helvetica-Bold", 12); p.drawString(40, y, f"{label}:"); y -= 20; p.setFont("Helvetica", 11)
                for k, v in valor.items():
                    if v > 0: p.drawString(60, y, f"• {k}: {v}"); y -= 18
            else:
                p.setFont("Helvetica-Bold", 11); p.drawString(40, y, f"{label}:"); 
                if chave == "memoria": p.setFillColor(colors.darkblue)
                else: p.setFillColor(colors.black)
                p.setFont("Helvetica", 11); txt = str(valor); lines = textwrap.wrap(txt, width=80)
                for l in lines: p.drawString(220, y, l); y -= 15; y -= 15

    p.setFillColor(colors.gray); p.setFont("Helvetica", 8); p.drawString(40, 30, "Documento gerado automaticamente."); p.showPage(); p.save(); buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

@app.post("/api/brigada")
def calcular_brigada(d: BrigadaReq):
    pop, div = d.funcionarios, d.divisao; regra = TABELA_NBR14276.get(div)
    if not regra: return {"qtd": 0, "memoria": "Divisão inválida"}
    if pop <= 10:
        brig = regra['base'] if pop >= regra['base'] else pop
        mem = f"População ({pop}) <= 10. Base Fixa: {regra['base']}."
    else:
        exc = pop - 10; add = math.ceil(exc * regra['pct']); brig = regra['base'] + add
        mem = f"Base ({regra['base']}) + {int(regra['pct']*100)}% de {exc} (Excedente) = {brig}."
    return {"divisao_desc": f"{div} ({regra['nome']})", "qtd": brig, "nivel": regra['nivel'], "memoria": mem, "obs": "Conforme NBR 14276."}

@app.post("/api/cipa")
def calcular_cipa(d: CalculoReq):
    conn = sqlite3.connect(DB_NAME); c = conn.cursor(); c.execute("SELECT descricao, grau_risco FROM cnae WHERE codigo = ?", (d.cnae,)); res_db = c.fetchone(); conn.close()
    if not res_db: desc, risco = f"CNAE {d.cnae} n/a", 3
    else: desc, risco = res_db
    ef, sup = 0, 0; txt = "Fora da tabela"
    for f in TABELA_CIPA.get(risco, []):
        if f[0] <= d.funcionarios <= f[1]: ef, sup = f[2], f[3]; txt = f"Faixa {f[0]}-{f[1]} funcs"; break
    if d.funcionarios > 10000: ef, sup = TABELA_CIPA[risco][-1][2], TABELA_CIPA[risco][-1][3]
    obs = "Designado" if d.funcionarios < 20 else ""
    return {"risco": risco, "atividade": desc, "efetivos": ef, "suplentes": sup, "memoria": f"Risco {risco}. {txt}.", "obs": obs}

@app.post("/api/sesmt")
def calcular_sesmt(d: CalculoReq):
    conn = sqlite3.connect(DB_NAME); c = conn.cursor(); c.execute("SELECT descricao, grau_risco FROM cnae WHERE codigo = ?", (d.cnae,)); res_db = c.fetchone(); conn.close()
    if not res_db: desc, risco = f"CNAE {d.cnae} n/a", 3
    else: desc, risco = res_db
    eq = {"Tec. Seg":0, "Eng. Seg":0, "Aux. Enf":0, "Enfermeiro":0, "Médico":0}; txt = "Fora da tabela"
    for f in TABELA_SESMT.get(risco, []):
        if f[0] <= d.funcionarios <= f[1]:
            eq = {"Tec. Seg": f[2], "Eng. Seg": f[3], "Aux. Enf": f[4], "Enfermeiro": f[5], "Médico": f[6]}; txt = f"Faixa {f[0]}-{f[1]} funcs"; break
    return {"risco": risco, "atividade": desc, "equipe": eq, "memoria": f"Risco {risco}. {txt}.", "obs": "NR-04"}

if __name__ == "__main__": import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8000)