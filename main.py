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
from pypdf import PdfReader # Necessário para ler os PDFs

app = FastAPI(title="SST.AI - Suite Master")

# Configuração para servir os PDFs se necessário
caminho_pdfs = os.path.join(os.path.dirname(__file__), "pdfs")
if os.path.exists(caminho_pdfs):
    app.mount("/pdfs", StaticFiles(directory=caminho_pdfs), name="pdfs")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- BANCO DE DADOS DE BUSCA (SQLite com FTS) ---
DB_NAME = "dados_seguranca.db"

def inicializar_banco():
    """Lê a pasta 'pdfs' e indexa o conteúdo no SQLite"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Cria tabela de busca textual (Full Text Search)
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS normas_fts USING fts5(titulo, conteudo, url_pdf, pagina)")
    
    # Verifica se já tem dados (para não reindexar toda vez que reinicia)
    c.execute("SELECT count(*) FROM normas_fts")
    if c.fetchone()[0] > 0:
        conn.close()
        return # Já está indexado

    print("--- INICIANDO INDEXAÇÃO DE PDFs ---")
    
    # Lista de arquivos na pasta pdfs
    if os.path.exists(caminho_pdfs):
        arquivos = [f for f in os.listdir(caminho_pdfs) if f.endswith(".pdf")]
        
        for arq in arquivos:
            path_completo = os.path.join(caminho_pdfs, arq)
            try:
                reader = PdfReader(path_completo)
                for i, page in enumerate(reader.pages):
                    texto = page.extract_text()
                    if texto:
                        # Insere cada página no banco
                        c.execute("INSERT INTO normas_fts (titulo, conteudo, url_pdf, pagina) VALUES (?, ?, ?, ?)", 
                                  (arq, texto, f"/pdfs/{arq}", i+1))
                print(f"Indexado: {arq}")
            except Exception as e:
                print(f"Erro ao ler {arq}: {e}")
    else:
        # Se não tiver pasta PDF, insere dados dummy para não quebrar
        print("Pasta 'pdfs' não encontrada. Usando modo simulação.")
        c.execute("INSERT INTO normas_fts (titulo, conteudo, url_pdf, pagina) VALUES (?, ?, ?, ?)", 
                  ("NR-06 Simulado", "Para os fins desta Norma Regulamentadora - NR, considera-se Equipamento de Proteção Individual - EPI, todo dispositivo ou produto, de uso individual utilizado pelo trabalhador.", "n/a", 1))

    conn.commit()
    conn.close()

# Executa a indexação ao ligar o servidor
inicializar_banco()

# --- CHECKLISTS EXPANDIDOS ---
DADOS_CHECKLISTS = {
    "NR-01 - Gerenciamento de Riscos (PGR)": [
        "O PGR está atualizado e disponível na obra/empresa?",
        "Foi realizado o levantamento preliminar de perigos?",
        "Os trabalhadores foram ouvidos na identificação dos riscos?",
        "O plano de ação do PGR possui cronograma definido?",
        "As medidas de prevenção estão sendo acompanhadas?"
    ],
    "NR-05 - CIPA": [
        "A CIPA está constituída e dimensionada corretamente?",
        "O processo eleitoral seguiu os prazos da norma?",
        "As reuniões ordinárias ocorrem mensalmente com ata?",
        "O treinamento dos cipeiros (20h) foi realizado?",
        "O Mapa de Risco foi elaborado com participação da CIPA?"
    ],
    "NR-06 - EPI": [
        "Todos os EPIs possuem CA válido?",
        "Existe ficha de EPI assinada por cada funcionário?",
        "Os EPIs estão em perfeito estado de conservação?",
        "Há treinamento registrado sobre o uso correto?",
        "O empregador exige o uso durante as atividades?"
    ],
    "NR-10 - Elétrica": [
        "O Prontuário das Instalações Elétricas (PIE) está atualizado?",
        "Há esquemas unifilares atualizados nos quadros?",
        "Os trabalhadores têm curso Básico (40h) e SEP (40h)?",
        "Os quadros estão sinalizados e com bloqueio (LOTO)?",
        "As vestimentas são adequadas (risco 2 / arco elétrico)?"
    ],
    "NR-11 - Movimentação de Cargas": [
        "Os equipamentos (empilhadeira/ponte) têm manutenção em dia?",
        "O operador possui cartão de identificação e exame médico?",
        "A capacidade de carga está visível no equipamento?",
        "O sinal sonoro de ré está funcionando?",
        "Os cabos de aço e cintas estão inspecionados?"
    ],
    "NR-12 - Máquinas e Equipamentos": [
        "As zonas de perigo possuem proteções fixas ou móveis intertravadas?",
        "Os botões de emergência estão acessíveis e funcionais?",
        "O comando bimanual é obrigatório e está funcionando?",
        "Há sinalização de segurança em português?",
        "Foi feita a Análise de Risco (HRN) da máquina?"
    ],
    "NR-13 - Vasos de Pressão e Caldeiras": [
        "O vaso possui placa de identificação legível?",
        "A válvula de segurança está calibrada?",
        "O relatório de inspeção de segurança está em dia?",
        "O operador possui treinamento de segurança na operação?",
        "O manômetro está calibrado e com indicação de PMTA?"
    ],
    "NR-17 - Ergonomia": [
        "Foi realizada a AET (Análise Ergonômica do Trabalho)?",
        "O mobiliário permite ajuste (cadeira, mesa)?",
        "A iluminação está adequada à atividade?",
        "Há pausas para descanso em atividades repetitivas?",
        "O levantamento de peso manual é compatível com o trabalhador?"
    ],
    "NR-18 - Construção Civil": [
        "As áreas de vivência (banheiro, refeitório) estão adequadas?",
        "As proteções de periferia (guarda-corpo) estão instaladas?",
        "As escavações estão protegidas/escoradas?",
        "Os andaimes estão fixados, nivelados e com piso completo?",
        "A serra circular possui coifa e empurrador?"
    ],
    "NR-20 - Inflamáveis": [
        "Os tanques possuem bacia de contenção?",
        "As instalações elétricas são à prova de explosão (Ex)?",
        "Há extintores próximos aos pontos de abastecimento?",
        "Os trabalhadores possuem curso de NR-20 (Integração/Básico)?",
        "Há sinalização de 'Proibido Fumar/Chamas'?"
    ],
    "NR-23 - Combate a Incêndio": [
        "Os extintores estão com carga e inspeção válidas?",
        "As saídas de emergência estão desobstruídas e sinalizadas?",
        "A iluminação de emergência está funcionando?",
        "A brigada de incêndio possui treinamento válido?",
        "As portas corta-fogo fecham corretamente?"
    ],
    "NR-33 - Espaço Confinado": [
        "O espaço está sinalizado e bloqueado?",
        "Foi emitida a PET (Permissão de Entrada)?",
        "O monitoramento de gases foi feito antes da entrada?",
        "Existe vigia na parte externa com comunicação?",
        "O tripé/sistema de resgate está montado?"
    ],
    "NR-35 - Trabalho em Altura": [
        "A Permissão de Trabalho (PT) foi emitida?",
        "Os trabalhadores têm ASO para altura e treinamento?",
        "Estão usando cinto paraquedista com talabarte duplo?",
        "O ponto de ancoragem é seguro/certificado?",
        "A área abaixo está isolada (risco de queda de materiais)?"
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
@app.get("/api/checklists-options")
def get_checklists_options():
    return list(DADOS_CHECKLISTS.keys())

@app.post("/api/get-checklist-items")
def get_checklist_items(req: dict):
    return DADOS_CHECKLISTS.get(req.get("nome"), [])

@app.post("/api/buscar")
def buscar_normas(d: BuscaReq):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # Busca usando FTS5 e destaca o termo
        termo = d.termo.replace('"', '""') # Sanitização simples
        query = f"SELECT titulo, snippet(normas_fts, 1, '<b>', '</b>', '...', 15), url_pdf, pagina FROM normas_fts WHERE normas_fts MATCH ? ORDER BY rank LIMIT 20"
        c.execute(query, (termo,))
        res = [{"titulo": r[0], "trecho": r[1], "url": r[2], "pagina": r[3]} for r in c.fetchall()]
    except Exception as e:
        print(f"Erro na busca: {e}")
        res = []
    finally:
        conn.close()
    return res

@app.post("/api/gerar_relatorio")
def gerar_pdf(req: RelatorioReq):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFillColor(colors.HexColor("#1e3a8a"))
    p.rect(0, height - 100, width, 100, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(40, height - 50, "RELATÓRIO TÉCNICO - SST")
    p.setFont("Helvetica", 10)
    p.drawRightString(width-40, height-50, f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    
    p.setFillColor(colors.black)
    y = height - 150
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, f"Documento: {req.tipo.upper()}")
    y -= 30
    
    p.setFont("Helvetica", 12)
    for k, v in req.meta.items():
        p.drawString(40, y, f"{k}: {v}")
        y -= 20
    
    y -= 20
    p.line(40, y, width-40, y)
    y -= 30
    
    if req.tipo == "checklist":
        p.drawString(40, y, "RESULTADO DA INSPEÇÃO:")
        y -= 20
        p.setFont("Helvetica", 10)
        for item, status in req.dados.items():
            if y < 50: p.showPage(); y = height - 50
            if "Observações" in item:
                p.setFillColor(colors.blue); p.drawString(40, y, f"Obs: {status}")
            else:
                cor = colors.green if status == "Conforme" else colors.red if status == "Não Conforme" else colors.gray
                p.setFillColor(cor); p.circle(50, y+4, 4, fill=True, stroke=False)
                p.setFillColor(colors.black); p.drawString(60, y, f"{item[:80]} - {status}")
            y -= 15
    else:
        for k, v in req.dados.items():
            if y < 50: p.showPage(); y = height - 50
            label = LABELS_PDF.get(k, k.capitalize())
            if isinstance(v, dict):
                 p.drawString(40, y, f"{label}:")
                 y-=20
                 for sub_k, sub_v in v.items():
                     if sub_v > 0: p.drawString(60, y, f"- {sub_k}: {sub_v}"); y-=15
            else:
                p.drawString(40, y, f"{label}: {v}")
                y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=relatorio.pdf"})

@app.post("/api/brigada")
def calcular_brigada(d: BrigadaReq):
    pop, div = d.funcionarios, d.divisao
    regra = TABELA_NBR14276.get(div)
    if not regra: return {"qtd": 0, "memoria": f"Erro: Divisão '{div}' não encontrada."}
    
    if pop <= 10:
        brig = regra['base'] if pop >= regra['base'] else pop
        mem = f"População ({pop}) <= 10. Base Fixa: {brig}."
    else:
        exc = pop - 10
        add = math.ceil(exc * regra['pct'])
        brig = regra['base'] + add
        mem = f"Base ({regra['base']}) + {int(regra['pct']*100)}% de {exc} (Excedente) = {brig}."
    return {"qtd": brig, "nivel": regra['nivel'], "memoria": mem, "divisao_desc": regra['nome']}

@app.post("/api/cipa")
def calcular_cipa(d: CalculoReq):
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    # Em produção, você teria uma tabela CNAE x RISCO
    # Simulando risco 3 para construção
    risco = 3 if d.cnae.startswith("41") else 2 
    
    ef, sup = 0, 0
    tabela = TABELA_CIPA.get(risco, [])
    for f in tabela:
        if f[0] <= d.funcionarios <= f[1]:
            ef, sup = f[2], f[3]
            break
    if d.funcionarios > 10000: ef, sup = tabela[-1][2], tabela[-1][3]
            
    return {"efetivos": ef, "suplentes": sup, "risco": risco, "memoria": f"Risco {risco}, Quadro I da NR-05."}

@app.post("/api/sesmt")
def calcular_sesmt(d: CalculoReq):
    risco = 3 if d.cnae.startswith("41") else 2
    eq = {"Tec. Seg": 0, "Eng. Seg": 0, "Aux. Enf": 0, "Enfermeiro": 0, "Médico": 0}
    
    tabela = TABELA_SESMT.get(risco, [])
    for f in tabela:
        if f[0] <= d.funcionarios <= f[1]:
            eq = {"Tec. Seg": f[2], "Eng. Seg": f[3], "Aux. Enf": f[4], "Enfermeiro": f[5], "Médico": f[6]}
            break
            
    return {"equipe": eq, "risco": risco, "memoria": f"Risco {risco}, Quadro II da NR-04."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
