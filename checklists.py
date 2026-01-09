# BASE DE DADOS DE AUDITORIA E INSPEÇÃO (SST COMPLIANCE)
# Baseado nas Normas Regulamentadoras (NRs) vigentes
# Arquivo: backend/checklists.py

DADOS_CHECKLISTS = {
    "NR-01: Disposições Gerais e GRO": [
        "1.5.3 - A organização implementou o Gerenciamento de Riscos Ocupacionais (GRO)?",
        "1.5.7 - O Inventário de Riscos Ocupacionais está atualizado e disponível?",
        "1.5.5 - Foram identificados os perigos e avaliados os riscos de cada atividade?",
        "1.5.5.2 - O nível de risco ocupacional foi classificado para cada perigo?",
        "1.5.6 - Existe um Plano de Ação com cronograma para controle dos riscos?",
        "1.4.1 - Os trabalhadores foram consultados durante a identificação dos perigos?",
        "1.5.8 - O PGR é revisto a cada 2 anos (ou após mudanças no processo)?",
        "1.6.1 - A empresa investiga e analisa todos os acidentes de trabalho?",
        "1.4.3 - Os trabalhadores receberam treinamento sobre os riscos de suas funções?",
        "1.5.3.3 - A empresa considera as condições de trabalho de prestadores de serviço?"
    ],
    
    "NR-05: CIPA (Comissão Interna de Prevenção)": [
        "5.3.1 - A CIPA está dimensionada corretamente conforme o Quadro I da NR-05?",
        "5.4 - O processo eleitoral seguiu os prazos (edital, votação, apuração)?",
        "5.6.2 - As reuniões ordinárias ocorrem mensalmente em local apropriado?",
        "5.6.4 - As atas de reunião são assinadas e arquivadas?",
        "5.7.2 - Os membros (titulares e suplentes) realizaram o treinamento de 20h?",
        "5.3.3 - O Mapa de Riscos (ou ferramenta similar) foi elaborado com a CIPA?",
        "5.8 - A CIPA participa da análise das causas de acidentes de trabalho?",
        "5.5.1 - A SIPAT (Semana Interna) foi realizada nos últimos 12 meses?",
        "5.6 - O calendário anual de reuniões foi aprovado e divulgado?",
        "5.9.1 - Nas empresas sem CIPA, há um 'Designado' treinado conforme a norma?"
    ],

    "NR-06: Equipamento de Proteção Individual (EPI)": [
        "6.3 - O EPI é fornecido gratuitamente e em perfeito estado de conservação?",
        "6.6.1 - O EPI possui Certificado de Aprovação (CA) válido no momento da compra?",
        "6.6.1 - Há registro de entrega (Ficha de EPI) física ou biométrica para cada item?",
        "6.6.1 - É feita a reposição imediata quando o EPI é extraviado ou danificado?",
        "6.6.1 - O trabalhador foi treinado sobre o uso, guarda e conservação correta?",
        "6.6.1 - A empresa exige o uso e aplica medidas disciplinares em caso de recusa?",
        "6.5 - O EPI é adequado tecnicamente ao risco apontado no PGR?",
        "6.9.3 - É realizada a higienização e manutenção periódica dos EPIs?",
        "6.7 - Para EPIs de altura (cinto), a inspeção é feita antes de cada uso?",
        "6.6.1 - O empregador orienta sobre as limitações de proteção do EPI?"
    ],

    "NR-10: Segurança em Instalações Elétricas": [
        "10.2.3 - O Prontuário das Instalações Elétricas (PIE) está organizado e atualizado?",
        "10.2.3 - Existem diagramas unifilares atualizados dos quadros e painéis?",
        "10.2.8 - Há medidas de proteção coletiva (desenergização, isolamento, barreiras)?",
        "10.2.9 - As vestimentas são adequadas (FR) para arco elétrico e fogo repentino?",
        "10.5.1 - É utilizado o procedimento de LOTO (Bloqueio e Etiquetagem) na manutenção?",
        "10.8 - Os trabalhadores são autorizados formalmente (carta de anuência) pela empresa?",
        "10.6.1 - Os equipamentos e ferramentas possuem isolamento elétrico testado?",
        "10.10 - A sinalização de segurança (placas de advertência) está adequada?",
        "10.2.4 - O sistema de aterramento e SPDA possui laudo de medição vigente?",
        "10.8.8 - Os trabalhadores possuem curso NR-10 Básico (e SEP se aplicável) válido?"
    ],

    "NR-11: Transporte e Movimentação de Cargas": [
        "11.1.5 - Os equipamentos (empilhadeiras/pontes) possuem indicação de carga máxima?",
        "11.1.6 - Os operadores possuem cartão de identificação com foto e validade?",
        "11.1.7 - Os equipamentos possuem sinal sonoro de ré funcionando?",
        "11.1.8 - A inspeção diária (checklist do operador) é realizada e registrada?",
        "11.1.3 - Os pisos suportam as cargas e estão livres de buracos ou obstruções?",
        "11.2 - O transporte manual de sacos respeita a distância máxima (60m)?",
        "11.1.3.2 - As peças transportadas estão estivadas/amarradas para evitar queda?",
        "11.1.10 - Em locais fechados, há controle de gases (monóxido) das empilhadeiras?",
        "11.1 - A manutenção preventiva dos equipamentos está em dia?",
        "11.3 - O armazenamento de materiais respeita o distanciamento das estruturas?"
    ],

    "NR-12: Máquinas e Equipamentos": [
        "12.3 - As zonas de perigo (polias, correias, serras) possuem proteções fixas/móveis?",
        "12.4 - Os dispositivos de parada de emergência estão acessíveis e funcionam?",
        "12.4 - O rearme da máquina exige ação manual (não liga sozinha ao voltar energia)?",
        "12.5 - Os sistemas de segurança possuem categoria adequada (relés de segurança)?",
        "12.9 - O piso ao redor da máquina é antiderrapante, nivelado e livre de óleo?",
        "12.11 - A manutenção é feita com a máquina parada e bloqueada (LOTO)?",
        "12.13 - A máquina possui Manual de Instruções em português disponível?",
        "12.16 - O operador foi capacitado especificamente para esta máquina?",
        "12.6 - As instalações elétricas da máquina estão protegidas contra choques?",
        "12.15 - As máquinas possuem sinalização clara de riscos e advertências?"
    ],

    "NR-13: Caldeiras e Vasos de Pressão": [
        "13.4 - A caldeira/vaso possui placa de identificação com PMTA e categoria?",
        "13.4 - O manômetro e a válvula de segurança estão calibrados e lacrados?",
        "13.6 - O Registro de Segurança (Livro de Ocorrências) está no local e atualizado?",
        "13.4 - A inspeção de segurança (inicial/periódica) está dentro do prazo?",
        "13.5 - O operador de caldeira possui treinamento e estágio supervisionado?",
        "13.4 - A saída da válvula de segurança está direcionada para local seguro?",
        "13.3 - O ambiente de instalação possui ventilação permanente e iluminação de emergência?",
        "13.4 - Existe sensor de nível de água com intertravamento na caldeira?",
        "13.6 - Há projeto de instalação assinado por Profissional Habilitado (PH)?",
        "13.8 - O teste hidrostático foi realizado conforme a periodicidade exigida?"
    ],

    "NR-17: Ergonomia": [
        "17.3 - O mobiliário (mesas/cadeiras) permite ajuste para a altura do trabalhador?",
        "17.3 - Os assentos possuem apoio lombar, regulagem de altura e borda arredondada?",
        "17.4 - O levantamento manual de cargas é compatível com a capacidade física?",
        "17.5 - A iluminação é difusa, distribuída e adequada à tarefa (sem reflexos)?",
        "17.5 - A temperatura e ruído proporcionam conforto térmico e acústico?",
        "17.6 - Há pausas obrigatórias para atividades de entrada de dados (digitação)?",
        "17.3 - Existe suporte para documentos ou monitor na altura dos olhos?",
        "17.4 - Os equipamentos de transporte possuem rodízios em bom estado?",
        "17.8 - Foi realizada a AET (Análise Ergonômica) para situações complexas?",
        "17.6 - A organização do trabalho evita ritmo excessivo ou metas inalcançáveis?"
    ],

    "NR-18: Indústria da Construção": [
        "18.4 - As áreas de vivência (banheiros/refeitório) estão limpas e dimensionadas?",
        "18.5 - As escavações >1,25m possuem escoramento e escada de acesso?",
        "18.6 - As instalações elétricas temporárias estão protegidas contra impactos/água?",
        "18.8 - As armações de aço têm pontas protegidas (fungos) contra empalamento?",
        "18.9 - Os andaimes estão com piso completo, rodapé e guarda-corpo duplo?",
        "18.9 - Os andaimes fachadeiros estão ancorados na estrutura da edificação?",
        "18.11 - O trabalho em altura possui sistema de proteção contra quedas (SPIQ)?",
        "18.10 - As aberturas no piso (vãos) estão fechadas ou protegidas?",
        "18.12 - O elevador de cremalheira possui cancela e freio de emergência?",
        "18.13 - As áreas de circulação estão desobstruídas e iluminadas?"
    ],

    "NR-23: Proteção Contra Incêndios": [
        "23.2 - Os extintores estão desobstruídos, sinalizados e com carga válida?",
        "23.2 - O tipo de extintor corresponde à classe de incêndio do local?",
        "23.3 - As saídas de emergência abrem no sentido do fluxo (para fora)?",
        "23.3 - A sinalização de rota de fuga é fotoluminescente e visível no escuro?",
        "23.3 - As portas corta-fogo estão fechadas (sem calços) e funcionais?",
        "23.4 - O alarme de incêndio é audível em todos os setores?",
        "23.5 - Os hidrantes possuem mangueiras, esguichos e chaves engatadas?",
        "23.1 - A Brigada de Incêndio está treinada e identificada?",
        "23.1 - O AVCB (Auto de Vistoria do Bombeiro) está válido?",
        "23.3 - A iluminação de emergência funciona ao cortar a energia?"
    ],

    "NR-33: Segurança em Espaços Confinados": [
        "33.3 - O espaço confinado está sinalizado e com acesso bloqueado?",
        "33.3 - Foi emitida a Permissão de Entrada e Trabalho (PET) antes do início?",
        "33.3 - Foi realizada a medição atmosférica (O2, LEL, CO, H2S) antes de entrar?",
        "33.3 - Existe monitoramento contínuo da atmosfera durante o trabalho?",
        "33.4 - Existe um Vigia dedicado exclusivamente à função na entrada?",
        "33.3 - O sistema de ventilação/exaustão está instalado e operante?",
        "33.5 - A equipe de resgate está disponível com equipamentos (tripé, maca)?",
        "33.3 - Todos os trabalhadores (Entrantes e Vigias) têm curso NR-33?",
        "33.3 - Os equipamentos elétricos são EX (intrinsecamente seguros/blindados)?",
        "33.2 - O cadastro dos espaços confinados da planta está atualizado?"
    ],

    "NR-35: Trabalho em Altura": [
        "35.4 - Foi realizada a Análise de Risco (AR) e emitida a PT?",
        "35.4 - O trabalhador possui ASO específico com aptidão para altura?",
        "35.5 - O sistema de ancoragem possui projeto e pontos de resistência (1.500kgf)?",
        "35.5 - O cinto é do tipo paraquedista e o talabarte/trava-quedas é compatível?",
        "35.5 - O Talabarte duplo é usado para garantir 100% de conexão?",
        "35.2 - A área abaixo do trabalho está isolada e sinalizada (risco de queda de materiais)?",
        "35.3 - O trabalhador realizou treinamento (8h) teórico e prático?",
        "35.6 - Existe plano de resgate para remover a vítima em caso de suspensão?",
        "35.5 - As escadas móveis estão amarradas e em bom estado?",
        "35.4 - O trabalho é suspenso em caso de chuva ou ventos fortes?"
    ]
}