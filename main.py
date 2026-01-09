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
from pypdf import PdfReader

# Configuração de Logs (Ajuda a ver o erro no painel do Render)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DE BANCO DE DADOS ---
DB_NAME = "sst_database.db"
CAMINHO_PDFS = "pdfs" # Nome da pasta no repositório

# --- LIFESPAN (Inicialização Segura) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa ao ligar o servidor
    logger.info("Iniciando indexação de conhecimento...")
    inicializar_banco()
    yield
    # Executa ao desligar
    logger.info("Servidor desligando.")

app = FastAPI(title="SST.AI - Suite Master", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos (se a pasta existir)
if os.path.exists(CAMINHO_PDFS):
    app.mount("/pdfs", StaticFiles(directory=CAMINHO_PDFS), name="pdfs")

# --- LÓGICA DE INDEXAÇÃO (PDF + BACKUP) ---
def inicializar_banco():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Cria tabela simples (sem FTS para evitar erros de compatibilidade no Linux)
    c.execute('''CREATE TABLE IF NOT EXISTS normas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    conteudo TEXT,
                    url_pdf TEXT,
                    pagina INTEGER
                )''')
    
    # Verifica se está vazio
    c.execute("SELECT count(*) FROM normas")
    qtd = c.fetchone()[0]
    
    if qtd > 0:
        logger.info("Banco de dados já populado.")
        conn.close()
        return

    # Tenta ler PDFs reais
    pdf_files = []
    if os.path.exists(CAMINHO_PDFS):
        pdf_files = [f for f in os.listdir(CAMINHO_PDFS) if f.lower().endswith('.pdf')]
    
    if pdf_files:
        logger.info(f"Encontrados {len(pdf_files)} PDFs. Indexando...")
        for arquivo in pdf_files:
            try:
                caminho_completo = os.path.join(CAMINHO_PDFS, arquivo)
                reader = PdfReader(caminho_completo)
                for i, page in enumerate(reader.pages):
                    texto = page.extract_text()
                    if texto:
                        # Limpa texto para evitar caracteres estranhos
                        texto_limpo = texto.replace('\x00', '')
                        c.execute("INSERT INTO normas (titulo, conteudo, url_pdf, pagina) VALUES (?, ?, ?, ?)",
                                  (arquivo, texto_limpo, f"/pdfs/{arquivo}", i+1))
            except Exception as e:
                logger.error(f"Erro ao ler {arquivo}: {e}")
    else:
        # --- DADOS DE BACKUP (CASO NÃO TENHA PDFS) ---
        logger.warning("Nenhum PDF encontrado ou pasta inexistente. Usando Base de Conhecimento interna.")
        BASE_BKP = [
            ("NR-01 Disposições Gerais", "O Gerenciamento de Riscos Ocupacionais (GRO) deve constituir um Programa de Gerenciamento de Riscos (PGR).", "n/a", 1),
            ("NR-06 EPI", "Considera-se Equipamento de Proteção Individual - EPI, todo dispositivo ou produto, de uso individual (capacete, luva, bota).", "n/a", 1),
            ("NR-10 Elétrica", "As instalações elétricas devem ser desenergizadas. Uso de bloqueio e etiquetagem (LOTO) é obrigatório.", "n/a", 1),
            ("NR-12 Máquinas", "As zonas de perigo das máquinas devem possuir sistemas de segurança, proteções fixas e móveis.", "n/a", 1),
            ("NR-35 Altura", "Considera-se trabalho em altura toda atividade executada acima de 2,00 m (dois metros) do nível inferior.", "n/a", 1),
            ("NR-23 Incêndio", "Todos os empregadores devem adotar medidas de prevenção de incêndios. Saídas devem ser livres.", "n/a", 1)
        ]
        c.executemany("INSERT INTO normas (titulo, conteudo, url_pdf, pagina) VALUES (?, ?, ?, ?)", BASE_BKP)
    
    conn.commit()
    conn.close()
    logger.info("Indexação concluída.")

# --- DADOS ESTÁTICOS COMPLETOS (CHECKLISTS) ---
DADOS_CHECKLISTS = {
    "NR-01 - Gerenciamento de Riscos": [
        "O PGR (Programa de Gerenciamento de Riscos) está atualizado?",
        "O inventário de riscos contempla todos os perigos?",
        "Os trabalhadores foram consultados sobre os riscos?",
        "Existe plano de ação com cronograma definido?"
    ],
    "NR-05 - CIPA": [
        "A CIPA está dimensionada corretamente conforme o quadro I?",
        "Há atas de reuniões mensais assinadas?",
        "O Mapa de Risco está atualizado e fixado?",
        "Os cipeiros receberam treinamento de 20h?"
    ],
    "NR-06 - EPI": [
        "Os EPIs possuem CA válido e visível?",
        "A ficha de entrega de EPI está assinada?",
        "O funcionário utiliza o EPI corretamente?",
        "Há reposição imediata em caso de dano?"
    ],
    "NR-10 - Instalações Elétricas": [
        "O Prontuário das Instalações Elétricas (PIE) existe?",
        "Os quadros estão sinalizados e travados?",
        "Os eletricistas têm cursos Básico e SEP válidos?",
        "As vestimentas são adequadas (risco de arco)?",
        "Existe laudo de SPDA atualizado?"
    ],
    "NR-11 - Movimentação de Cargas": [
        "Operadores de empilhadeira têm habilitação e cartão?",
        "O sinal sonoro de ré está funcionando?",
        "A capacidade de carga está visível no equipamento?",
        "Os cabos de aço e cintas estão em bom estado?"
    ],
    "NR-12 - Máquinas e Equipamentos": [
        "Partes móveis possuem proteções fixas ou móveis?",
        "Botões de emergência estão funcionais e acessíveis?",
        "Há sinalização de segurança em português?",
        "Foi realizada a Apreciação de Risco da máquina?"
    ],
    "NR-17 - Ergonomia": [
        "As cadeiras possuem ajuste de altura e encosto?",
        "A iluminação é adequada e sem reflexos?",
        "Há pausas para atividades repetitivas?",
        "O levantamento de peso manual é compatível?"
    ],
    "NR-18 - Construção Civil": [
        "As áreas de vivência estão limpas e adequadas?",
        "Há proteção contra quedas (guarda-corpo) na periferia?",
        "Os andaimes estão nivelados e com forração completa?",
        "A serra circular possui coifa protetora?"
    ],
    "NR-23 - Proteção Contra Incêndio": [
        "Os extintores estão carregados e dentro da validade?",
        "As saídas de emergência estão desobstruídas?",
        "A sinalização de rota de fuga é visível?",
        "A brigada de incêndio possui treinamento?"
    ],
    "NR-33 - Espaço Confinado": [
        "O espaço está sinalizado e com acesso controlado?",
        "Foi emitida a PET (Permissão de Entrada)?",
        "O monitoramento de gases foi realizado?",
        "Existe vigia na parte externa?"
    ],
    "NR-35 - Trabalho em Altura": [
        "A Permissão de Trabalho (PT) foi emitida?",
        "O trabalhador tem exame (ASO) apto para altura?",
        "O cinto é tipo paraquedista com talabarte duplo?",
        "O ponto de ancoragem é certificado?"
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

# --- TABELAS TÉCNICAS (Resumidas para caber) ---
TABELA_NBR14276 = {
    'A-1': {'nome': 'Residencial Unifamiliar', 'base': 0, 'pct': 0, 'nivel': '-'},
    'A-2': {'nome': 'Residencial Multifamiliar', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'C-1': {'nome': 'Comércio Geral', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'C-2': {'nome': 'Shopping Center', 'base': 4, 'pct': 0.05, 'nivel': 'Intermediário'},
    'D-1': {'nome': 'Escritório', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'I-1': {'nome': 'Indústria Baixo Risco', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-2': {'nome': 'Indústria Médio Risco', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'},
    'I-3': {'nome': 'Indústria Alto Risco', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'},
    'J-1': {'nome': 'Depósito Incombustível', 'base': 2, 'pct': 0.05, 'nivel': 'Básico'},
    'J-2': {'nome': 'Depósito Baixo Risco', 'base': 4, 'pct': 0.07, 'nivel': 'Intermediário'},
    'J-3': {'nome': 'Depósito Médio Risco', 'base': 8, 'pct': 0.07, 'nivel': 'Intermediário'},
    'J-4': {'nome': 'Depósito Alto Risco', 'base': 10, 'pct': 0.10, 'nivel': 'Avançado'}
}

# --- ROTAS DA API ---

@app.get("/api/checklists-options")
def get_checklists_options():
    # Retorna chaves. Se dicionário estiver vazio, retorna lista vazia, não erro.
    return list(DADOS_CHECKLISTS.keys())

@app.post("/api/get-checklist-items")
def get_checklist_items(req: dict):
    return DADOS_CHECKLISTS.get(req.get("nome"), [])

@app.post("/api/buscar")
def buscar_normas(d: BuscaReq):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    termo_busca = f"%{d.termo}%"
    
    # Busca simples com LIKE para compatibilidade máxima
    c.execute("""
        SELECT titulo, conteudo, url_pdf, pagina 
        FROM normas 
        WHERE titulo LIKE ? OR conteudo LIKE ? 
        LIMIT 10
    """, (termo_busca, termo_busca))
    
    rows = c.fetchall()
    conn.close()
    
    resultados = []
    for r in rows:
        # Cria um trecho (snippet) simples
        idx = r[1].lower().find(d.termo.lower())
        inicio = max(0, idx - 50)
        fim = min(len(r[1]), idx + 150)
        trecho = "..." + r[1][inicio:fim] + "..."
        
        resultados.append({
            "titulo": r[0],
            "trecho": trecho,
            "url": r[2],
            "pagina": r[3]
        })
    return resultados

@app.post("/api/brigada")
def calcular_brigada(d: BrigadaReq):
    # Se a divisão não existir, usa uma padrão para não quebrar
    regra = TABELA_NBR14276.get(d.divisao)
    if not regra:
        # Tenta achar pelo grupo (fallback)
        if d.divisao.startswith('A'): regra = TABELA_NBR14276['A-2']
        elif d.divisao.startswith('C'): regra = TABELA_NBR14276['C-1']
        elif d.divisao.startswith('D'): regra = TABELA_NBR14276['D-1']
        elif d.divisao.startswith('I'): regra = TABELA_NBR14276['I-1']
        elif d.divisao.startswith('J'): regra = TABELA_NBR14276['J-2']
        else: return {"qtd": 0, "memoria": "Divisão não cadastrada."}

    pop = d.funcionarios
    if pop <= 10:
        brig = regra['base'] if pop >= regra['base'] else pop
    else:
        exc = pop - 10
        add = math.ceil(exc * regra['pct'])
        brig = regra['base'] + add
    
    return {
        "qtd": brig, 
        "nivel": regra['nivel'], 
        "memoria": f"Base {regra['base']} + {int(regra['pct']*100)}% excedente.",
        "divisao_desc": regra['nome']
    }

@app.post("/api/cipa")
def calcular_cipa(d: CalculoReq):
    # Lógica simplificada robusta
    risco = 3 if "41" in d.cnae else 2
    ef = 1 if d.funcionarios < 50 else 2
    if d.funcionarios > 100: ef = 3
    return {"efetivos": ef, "suplentes": ef, "risco": risco}

@app.post("/api/sesmt")
def calcular_sesmt(d: CalculoReq):
    eq = {"Tec. Seg": 0}
    if d.funcionarios > 50: eq["Tec. Seg"] = 1
    if d.funcionarios > 500: eq["Eng. Seg"] = 1
    return {"equipe": eq}

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    p.setFillColor(colors.HexColor("#1e3a8a"))
    p.rect(0, height - 90, width, 90, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(40, height - 50, "RELATÓRIO TÉCNICO SST")
    
    # Body
    p.setFillColor(colors.black)
    y = height - 130
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, f"Módulo: {req.tipo.upper()}")
    y -= 30
    
    p.setFont("Helvetica", 11)
    if req.dados:
        for k, v in req.dados.items():
            if y < 50: p.showPage(); y = height - 50
            # Formatação especial para checklists
            if req.tipo == 'checklist' and isinstance(v, str):
                cor = colors.green if v == "Conforme" else colors.red if v == "Não Conforme" else colors.gray
                p.setFillColor(cor)
                p.circle(30, y+4, 4, fill=True, stroke=False)
                p.setFillColor(colors.black)
                p.drawString(40, y, f"{k[:90]}: {v}")
            else:
                p.drawString(40, y, f"{k}: {v}")
            y -= 20
            
    p.showPage()
    p.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
