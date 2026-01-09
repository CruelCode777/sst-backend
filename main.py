import sqlite3
import os
import math
import io
import textwrap
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = FastAPI(title="SST.AI - Suite Master")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DADOS "MOCK" (Para funcionar sem banco de dados externo) ---

# 1. Base de Busca (Simulada para testar)
BASE_CONHECIMENTO = [
    {"norma": "NR-10", "titulo": "Segurança em Instalações Elétricas", "texto": "10.2.8.2 As medidas de proteção coletiva compreendem, prioritariamente, a desenergização elétrica das instalações elétricas."},
    {"norma": "NR-12", "titulo": "Segurança em Máquinas", "texto": "12.3.1 O empregador deve adotar medidas de proteção para o trabalho em máquinas e equipamentos, capazes de garantir a saúde e a integridade física dos trabalhadores."},
    {"norma": "NR-35", "titulo": "Trabalho em Altura", "texto": "35.3.2 Considera-se trabalhador capacitado para trabalho em altura aquele que foi submetido e aprovado em treinamento, teórico e prático, com carga horária mínima de oito horas."},
    {"norma": "NR-23", "titulo": "Proteção Contra Incêndios", "texto": "23.1 Todos os empregadores devem adotar medidas de prevenção de incêndios, em conformidade com a legislação estadual e as normas técnicas aplicáveis."},
    {"norma": "NR-06", "titulo": "EPI", "texto": "6.3 A empresa é obrigada a fornecer aos empregados, gratuitamente, EPI adequado ao risco, em perfeito estado de conservação e funcionamento."}
]

# 2. Checklists Prontos
DADOS_CHECKLISTS = {
    "NR-10 (Elétrica)": [
        "O prontuário das instalações elétricas está atualizado?",
        "Os esquemas unifilares estão disponíveis e atualizados?",
        "Existe laudo de SPDA atualizado?",
        "Os quadros elétricos possuem sinalização de advertência?",
        "Os trabalhadores possuem treinamento NR-10 (Básico/SEP) válido?"
    ],
    "NR-12 (Máquinas)": [
        "As zonas de perigo das máquinas possuem proteções fixas ou móveis?",
        "Os dispositivos de parada de emergência estão funcionais?",
        "Há sinalização de segurança nas máquinas?",
        "O piso ao redor da máquina está limpo e desobstruído?",
        "Foi realizada a Análise de Risco (HRN/Outra)?"
    ],
    "NR-35 (Altura)": [
        "Foi emitida a Permissão de Trabalho (PT) para a atividade?",
        "O trabalhador está utilizando cinto de segurança tipo paraquedista?",
        "O ponto de ancoragem foi inspecionado?",
        "A área abaixo do trabalho está isolada e sinalizada?",
        "Os exames médicos (ASO) indicam aptidão para altura?"
    ]
}

# --- MODELOS ---
class CalculoReq(BaseModel):
    cnae: str; funcionarios: int
class BrigadaReq(BaseModel):
    funcionarios: int; divisao: str 
class BuscaReq(BaseModel):
    termo: str
class RelatorioReq(BaseModel):
    tipo: str; dados: dict; meta: dict = {}

# --- TABELAS ---
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

# --- ROTAS ---

@app.get("/api/checklists-options")
def get_checklists_options():
    # Retorna apenas as chaves (ex: "NR-12 (Máquinas)") para o menu
    return list(DADOS_CHECKLISTS.keys())

@app.post("/api/get-checklist-items")
def get_checklist_items(req: dict):
    # Retorna as perguntas do checklist selecionado
    nome = req.get("nome")
    return DADOS_CHECKLISTS.get(nome, [])

@app.post("/api/buscar")
def buscar_normas(d: BuscaReq):
    # Busca simples no Mock
    termo = d.termo.lower()
    resultados = []
    for item in BASE_CONHECIMENTO:
        if termo in item['titulo'].lower() or termo in item['texto'].lower() or termo in item['norma'].lower():
            resultados.append(item)
    return resultados

@app.post("/api/brigada")
def calcular_brigada(d: BrigadaReq):
    pop = d.funcionarios
    div = d.divisao
    regra = TABELA_NBR14276.get(div)
    
    if not regra:
        return {"qtd": 0, "memoria": f"Erro: A divisão '{div}' não foi encontrada na tabela NBR 14276."}
    
    if pop <= 10:
        brig = regra['base'] if pop >= regra['base'] else pop
        mem = f"População ({pop}) <= 10. Base Fixa: {brig}."
    else:
        exc = pop - 10
        add = math.ceil(exc * regra['pct'])
        brig = regra['base'] + add
        mem = f"Base ({regra['base']}) + {int(regra['pct']*100)}% de {exc} (Excedente) = {brig}."
    
    return {"qtd": brig, "nivel": regra['nivel'], "memoria": mem, "divisao_desc": regra['nome']}

@app.post("/api/sesmt")
def calcular_sesmt(d: CalculoReq):
    # Lógica simplificada de SESMT
    return {"equipe": {"Tec. Seg": 1, "Eng. Seg": 0}, "memoria": "Cálculo simplificado demonstrativo.", "risco": 3}

@app.post("/api/cipa")
def calcular_cipa(d: CalculoReq):
     # Lógica simplificada de CIPA
    return {"efetivos": 2, "suplentes": 2, "risco": 3, "memoria": "Cálculo simplificado demonstrativo."}

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Cabeçalho
    p.setFillColor(colors.HexColor("#1e3a8a"))
    p.rect(0, height - 100, width, 100, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(40, height - 50, f"RELATÓRIO: {req.tipo.upper()}")
    
    p.setFillColor(colors.black)
    y = height - 150
    p.setFont("Helvetica", 12)
    
    # Dados Gerais
    p.drawString(40, y, f"Cliente: {req.meta.get('cliente')}"); y -= 20
    p.drawString(40, y, f"Projeto: {req.meta.get('projeto')}"); y -= 40
    
    # Dados do Relatório
    if req.tipo == "checklist":
        p.setFont("Helvetica-Bold", 14); p.drawString(40, y, "ITENS INSPECIONADOS:"); y -= 20
        p.setFont("Helvetica", 10)
        for item, status in req.dados.items():
            if y < 50: p.showPage(); y = height - 50
            if status == "Conforme": cor = colors.green
            elif status == "Não Conforme": cor = colors.red
            else: cor = colors.gray
            
            p.setFillColor(cor)
            p.circle(50, y+4, 4, fill=True, stroke=False)
            p.setFillColor(colors.black)
            p.drawString(60, y, f"{item} - {status}")
            y -= 15
            
    else:
        for k, v in req.dados.items():
            p.drawString(40, y, f"{k}: {v}"); y -= 20
            
    p.showPage()
    p.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

