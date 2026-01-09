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

# Tenta importar checklists, se não existir, usa vazio (pra não quebrar)
try:
    from checklists import DADOS_CHECKLISTS
except ImportError:
    DADOS_CHECKLISTS = {}

app = FastAPI(title="SST.AI - Suite Master")

# Configuração de CORS (Permite que o Streamlit converse com o Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE DADOS (O Contrato da API) ---
class CalculoReq(BaseModel):
    cnae: str
    funcionarios: int

class BrigadaReq(BaseModel):
    funcionarios: int
    divisao: str 

class RelatorioReq(BaseModel):
    tipo: str
    dados: dict
    meta: dict = {}

# --- TABELAS DE ENGENHARIA (NBR 14276 / NR-04 / NR-05) ---
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
    'F-7': {'nome': 'Circo / Temporário', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'F-8': {'nome': 'Restaurantes / Bares', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'G-1': {'nome': 'Garagens / Estacionamentos', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'G-2': {'nome': 'Postos de Combustível', 'base': 4, 'pct': 0.10, 'nivel': 'Avançado'},
    'G-3': {'nome': 'Oficinas / Hangares', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'G-4': {'nome': 'Marinas / Iates', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'H-1': {'nome': 'Hospitais Veterinários', 'base': 6, 'pct': 0.07, 'nivel': 'Intermediário'},
    'H-2': {'nome': 'Hospitais (Com Internação)', 'base': 10, 'pct': 0.07, 'nivel': 'Intermediário'},
    'H-3': {'nome': 'Clínicas (Sem Internação)', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'H-4': {'nome': 'Repartições Públicas', 'base': 4, 'pct': 0.05, 'nivel': 'Básico'},
    'H-5': {'nome': 'Manicômios / Prisões', 'base': 10, 'pct': 0.07, 'nivel': 'Intermediário'},
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
    'M-2': {'nome': 'Líquidos Inflamáveis', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    'M-3': {'nome': 'Centrais Elétricas', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'}
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

# Labels para deixar o PDF bonito
LABELS_PDF = {
    "qtd": "Brigadistas (Qtd Mínima)", 
    "nivel": "Nível do Treinamento", 
    "divisao_desc": "Classificação da Edificação", 
    "memoria": "Memória de Cálculo Normativa", 
    "obs": "Observações Técnicas", 
    "risco": "Grau de Risco (NR-04)", 
    "atividade": "Atividade Econômica (CNAE)", 
    "efetivos": "Membros Efetivos (CIPA)", 
    "suplentes": "Membros Suplentes (CIPA)"
}

# --- ROTAS DA API (Endpoints) ---

@app.get("/api/checklists")
def listar_checklists():
    return DADOS_CHECKLISTS

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 1. Cabeçalho Corporativo
    p.setFillColor(colors.HexColor("#1e3a8a")) # Azul Escuro
    p.rect(0, height - 130, width, 130, fill=True, stroke=False)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(40, height - 50, "RELATÓRIO TÉCNICO SST")
    
    # Dados do Cliente no Cabeçalho
    cli = req.meta.get('cliente', 'Não Informado')
    aud = req.meta.get('auditor', 'Não Informado')
    setor = req.meta.get('setor', 'Geral')
    
    p.setFont("Helvetica", 12)
    p.drawString(40, height - 80, f"Cliente: {cli}")
    p.drawString(40, height - 100, f"Local/Setor: {setor}")
    
    p.drawRightString(width - 40, height - 50, "SST.AI Suite")
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 40, height - 80, f"Responsável: {aud}")
    p.drawRightString(width - 40, height - 100, f"Data: {datetime.now().strftime('%d/%m/%Y')}")

    # 2. Corpo do Relatório
    p.setFillColor(colors.black)
    y = height - 160
    
    # Título Dinâmico
    titulos = {
        'checklist': "RELATÓRIO DE INSPEÇÃO DE SEGURANÇA", 
        'brigada': "DIMENSIONAMENTO DE BRIGADA DE INCÊNDIO (NBR 14276)", 
        'cipa': "DIMENSIONAMENTO DE CIPA (NR-05)", 
        'sesmt': "DIMENSIONAMENTO DE SESMT (NR-04)",
        'geral': "RELATÓRIO GERAL"
    }
    titulo = titulos.get(req.tipo, "RELATÓRIO TÉCNICO")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, titulo)
    p.line(40, y-5, width-40, y-5)
    y -= 40
    
    # 3. Lógica de Impressão dos Dados
    if req.tipo == 'checklist':
        # ... Lógica de Checklist (Simplificada para caber) ...
        p.setFont("Helvetica", 10)
        for item, detalhes in req.dados.items():
            if y < 80: p.showPage(); y = height - 50
            status = detalhes.get("status", "NA")
            p.drawString(40, y, f"[{status}] {item[:90]}")
            y -= 15
    else:
        # Lógica Universal (CIPA, Brigada, SESMT)
        p.setFont("Helvetica", 12)
        for chave, valor in req.dados.items():
            if y < 60: p.showPage(); y = height - 60
            
            # Traduz a chave (ex: 'qtd' vira 'Brigadistas')
            label = LABELS_PDF.get(chave, chave.capitalize())
            
            # Se for um dicionário (ex: equipe do SESMT)
            if isinstance(valor, dict):
                p.setFont("Helvetica-Bold", 12)
                p.drawString(40, y, f"{label}:")
                y -= 20
                p.setFont("Helvetica", 11)
                for k, v in valor.items():
                    if v > 0: # Só imprime se tiver profissional
                        p.drawString(60, y, f"• {k}: {v}")
                        y -= 18
            else:
                # Linha normal
                p.setFont("Helvetica-Bold", 11)
                p.drawString(40, y, f"{label}:")
                
                # Se for a Memória de Cálculo, destaca em azul
                if chave == "memoria":
                    p.setFillColor(colors.darkblue)
                else:
                    p.setFillColor(colors.black)
                
                p.setFont("Helvetica", 11)
                # Quebra de linha se o texto for longo
                txt = str(valor)
                lines = textwrap.wrap(txt, width=80)
                for l in lines:
                    p.drawString(220, y, l)
                    y -= 15
                y -= 15 # Espaço extra entre itens

    # Rodapé
    p.setFillColor(colors.gray)
    p.setFont("Helvetica", 8)
    p.drawString(40, 30, "Documento gerado automaticamente pelo Sistema SST.AI")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

@app.post("/api/brigada")
def calcular_brigada(d: BrigadaReq):
    pop = d.funcionarios
    div = d.divisao
    regra = TABELA_NBR14276.get(div)
    
    if not regra:
        return {"qtd": 0, "memoria": f"Erro: A divisão '{div}' não foi encontrada na tabela NBR 14276."}
    
    if pop <= 10:
        brig = regra['base'] if pop >= regra['base'] else pop
        mem = f"População ({pop}) é baixa. Aplica-se a Base Fixa ou Total: {brig}."
    else:
        # Cálculo NBR: Base + % do que passar de 10
        exc = pop - 10
        add = math.ceil(exc * regra['pct'])
        brig = regra['base'] + add
        mem = f"Cálculo: Base Fixa ({regra['base']}) + {int(regra['pct']*100)}% sobre excedente de 10 vidas ({exc}). Adicional calculado: {add}."
    
    return {
        "divisao_desc": f"{div} - {regra['nome']}", 
        "qtd": brig, 
        "nivel": regra['nivel'], 
        "memoria": mem, 
        "obs": "Dimensionamento conforme NBR 14276. Verificar plantas de risco."
    }

@app.post("/api/cipa")
def calcular_cipa(d: CalculoReq):
    # Simulação de DB - Num app real, usaria SQL
    # Aqui vamos simplificar: CNAE de construção = Risco 3, etc.
    risco = 3 # Padrão para teste se não achar
    if d.cnae.startswith("41"): risco = 3 # Construção
    if d.cnae.startswith("01"): risco = 3 # Agro
    if d.cnae.startswith("62"): risco = 2 # TI
    if d.cnae.startswith("86"): risco = 3 # Hospital
    
    desc = f"Atividade CNAE {d.cnae}"
    
    ef, sup = 0, 0
    txt = "Fora da tabela"
    
    tabela_risco = TABELA_CIPA.get(risco, [])
    
    # Busca na faixa
    for f in tabela_risco:
        if f[0] <= d.funcionarios <= f[1]:
            ef, sup = f[2], f[3]
            txt = f"Enquadrado na faixa de {f[0]} a {f[1]} funcionários."
            break
            
    # Regra para gigantes (>10.000)
    if d.funcionarios > 10000:
        ef, sup = tabela_risco[-1][2], tabela_risco[-1][3]
        
    obs = "Necessário designar responsável." if d.funcionarios < 20 else "Comissão Eleita Obrigatória."
    
    return {
        "risco": risco, 
        "atividade": desc, 
        "efetivos": ef, 
        "suplentes": sup, 
        "memoria": f"Grau de Risco {risco} identificado pelo CNAE. {txt}", 
        "obs": obs
    }

@app.post("/api/sesmt")
def calcular_sesmt(d: CalculoReq):
    # Mesma lógica simplificada de risco
    risco = 3
    if d.cnae.startswith("41"): risco = 3
    if d.cnae.startswith("62"): risco = 2
    
    desc = f"Atividade CNAE {d.cnae}"
    eq = {"Tec. Seg":0, "Eng. Seg":0, "Aux. Enf":0, "Enfermeiro":0, "Médico":0}
    txt = "Empresa desobrigada de SESMT Próprio."
    
    tabela_risco = TABELA_SESMT.get(risco, [])
    
    for f in tabela_risco:
        if f[0] <= d.funcionarios <= f[1]:
            eq = {
                "Tec. Seg": f[2], "Eng. Seg": f[3], 
                "Aux. Enf": f[4], "Enfermeiro": f[5], "Médico": f[6]
            }
            if sum(eq.values()) > 0:
                txt = f"Enquadrado na faixa {f[0]}-{f[1]} vidas."
            break
            
    return {
        "risco": risco, 
        "atividade": desc, 
        "equipe": eq, 
        "memoria": f"Grau de Risco {risco}. {txt}", 
        "obs": "Verificar necessidade de SESMT Comum ou Compartilhado (NR-04)."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
