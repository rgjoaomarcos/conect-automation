"""
CONECT Automation - BACKFILL
Extrai dados históricos de produtividade (período definido)
Sem afetar a automação diária existente
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import requests
import base64
from bs4 import BeautifulSoup
from pathlib import Path
from openpyxl import load_workbook
import urllib3

# Desabilitar warnings de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

CONECT_USER = os.getenv("CONECT_USER", "194237")
CONECT_PASS = os.getenv("CONECT_PASS", "1234")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "rgjoaomarcos/conect-automation"
GITHUB_BRANCH = "main"

CONECT_LOGIN_URL = "https://modulos.conectew.com.br/conecte/modulos.jsf"
CONECT_ATENDIMENTOS_URL = "https://modulos.conectew.com.br/conecte/atendimento/site/recepcao/atendimentosRealizados/view.jsf"

# Datas para backfill (YYYY-MM-DD)
DATA_INICIO = datetime.strptime("2026-06-01", "%Y-%m-%d")
DATA_FIM = datetime.strptime("2026-09-05", "%Y-%m-%d")

# ============================================================================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================================================================

def fazer_login():
    """Faz login no CONECT e retorna a sessão autenticada"""
    logger.info("🔐 Fazendo login no CONECT...")
    
    session = requests.Session()
    session.verify = False
    
    try:
        # Primeiro GET para pegar cookies e view state
        response = session.get(CONECT_LOGIN_URL, verify=False, timeout=15)
        if response.status_code != 200:
            logger.error(f"❌ Erro ao acessar login: Status {response.status_code}")
            return None
        
        # POST de login
        data = {
            "j_username": CONECT_USER,
            "j_password": CONECT_PASS,
            "javax.faces.ViewState": "",
            "j_idt5": "j_idt5"
        }
        
        response = session.post(CONECT_LOGIN_URL, data=data, verify=False, timeout=15)
        
        if response.status_code == 200:
            logger.info("✅ Login realizado com sucesso!")
            return session
        else:
            logger.error(f"❌ Erro no login: Status {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout ao conectar com CONECT")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao fazer login: {e}")
        return None

# ============================================================================
# FUNÇÕES DE EXTRAÇÃO DE DADOS
# ============================================================================

def extrair_medicos_escala(data):
    """Extrai lista de médicos da escala para uma data específica"""
    try:
        excel_path = Path("escalas_upa_tabelas_junho_setembro_2026.xlsx")
        if not excel_path.exists():
            logger.error("❌ Arquivo de escala não encontrado!")
            return []
        
        wb = load_workbook(excel_path)
        ws = wb["Todos os plantões"]
        
        medicos = set()
        data_str = data.strftime("%d/%m/%Y")
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] and str(row[0]).strip() == data_str:
                if row[4]:  # Coluna de plantonista
                    medicos.add(str(row[4]).strip())
        
        return list(medicos)
    
    except Exception as e:
        logger.error(f"❌ Erro ao ler escala: {e}")
        return []

def extrair_atendimentos(session, medico, data_inicio, data_fim):
    """Extrai atendimentos de um médico para um período"""
    try:
        params = {
            "dataInicial": data_inicio.strftime("%d/%m/%Y"),
            "dataFinal": data_fim.strftime("%d/%m/%Y"),
            "medico": medico,
            "filial": "UPA SÃO LEOPOLDO MANDIC",
            "somenteMeus": "false"
        }
        
        response = session.get(CONECT_ATENDIMENTOS_URL, params=params, verify=False, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Status {response.status_code} para médico {medico}")
            return []
        
        atendimentos = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Procurar pela tabela de atendimentos
        tabelas = soup.find_all('table')
        
        for tabela in tabelas:
            linhas = tabela.find_all('tr')
            
            for linha in linhas[1:]:  # Pular header
                colunas = linha.find_all('td')
                
                if len(colunas) >= 4:
                    try:
                        atendimento = {
                            'medico': medico,
                            'paciente': colunas[0].get_text(strip=True),
                            'hora': colunas[1].get_text(strip=True),
                            'descricao': colunas[2].get_text(strip=True),
                            'data': data_fim.strftime("%Y-%m-%d")
                        }
                        atendimentos.append(atendimento)
                    except Exception as e:
                        logger.debug(f"Erro ao parsear linha: {e}")
                        continue
        
        return atendimentos
    
    except Exception as e:
        logger.error(f"❌ Erro ao extrair atendimentos: {e}")
        return []

# ============================================================================
# FUNÇÕES DE GITHUB
# ============================================================================

def salvar_no_github(data, atendimentos):
    """Salva CSV no GitHub via API REST"""
    if not GITHUB_TOKEN:
        logger.warning("⚠️ GITHUB_TOKEN não configurado - pulando upload")
        return False
    
    try:
        # Gerar conteúdo CSV
        conteudo = "medico,paciente,hora,descricao,data\n"
        for atendimento in atendimentos:
            linha = f"{atendimento['medico']},{atendimento['paciente']},{atendimento['hora']},{atendimento['descricao']},{atendimento['data']}\n"
            conteudo += linha
        
        # Encode para base64
        content_b64 = base64.b64encode(conteudo.encode()).decode()
        
        # Nome do arquivo
        data_str = data.strftime("%Y-%m-%d")
        filename = f"relatorios/{data_str}_produtividade.csv"
        
        # URL da API GitHub
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload = {
            "message": f"Backfill: Produtividade {data_str}",
            "content": content_b64,
            "branch": GITHUB_BRANCH
        }
        
        # Verificar se arquivo já existe (para atualização)
        get_response = requests.get(url, headers=headers)
        if get_response.status_code == 200:
            payload["sha"] = get_response.json()["sha"]
        
        # Upload
        response = requests.put(url, json=payload, headers=headers)
        
        if response.status_code in [201, 200]:
            logger.info(f"✅ {filename} enviado para GitHub ({len(atendimentos)} atendimentos)")
            return True
        else:
            logger.error(f"❌ Erro ao enviar para GitHub: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Erro ao salvar no GitHub: {e}")
        return False

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Executa o backfill de dados históricos"""
    logger.info("=" * 80)
    logger.info("🚀 CONECT AUTOMATION - BACKFILL")
    logger.info(f"📅 Período: {DATA_INICIO.strftime('%d/%m/%Y')} a {DATA_FIM.strftime('%d/%m/%Y')}")
    logger.info("=" * 80)
    
    # Fazer login uma única vez
    session = fazer_login()
    if not session:
        logger.error("❌ Falha ao autenticar - abortando backfill")
        return False
    
    # Iterar sobre cada data
    data_atual = DATA_INICIO
    total_processado = 0
    total_erros = 0
    
    while data_atual <= DATA_FIM:
        try:
            logger.info(f"\n📍 Processando {data_atual.strftime('%d/%m/%Y')}...")
            
            # Extrair médicos da escala
            medicos = extrair_medicos_escala(data_atual)
            
            if not medicos:
                logger.warning(f"⚠️ Nenhum médico encontrado para {data_atual.strftime('%d/%m/%Y')}")
                data_atual += timedelta(days=1)
                continue
            
            logger.info(f"  Médicos: {', '.join(medicos)}")
            
            # Extrair atendimentos para cada médico
            todos_atendimentos = []
            for medico in medicos:
                atendimentos = extrair_atendimentos(session, medico, data_atual, data_atual)
                todos_atendimentos.extend(atendimentos)
            
            # Salvar no GitHub
            if todos_atendimentos:
                if salvar_no_github(data_atual, todos_atendimentos):
                    total_processado += 1
                else:
                    total_erros += 1
            else:
                logger.warning(f"ℹ️ Nenhum atendimento registrado para {data_atual.strftime('%d/%m/%Y')}")
                total_processado += 1
            
            # Próxima data
            data_atual += timedelta(days=1)
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar {data_atual.strftime('%d/%m/%Y')}: {e}")
            total_erros += 1
            data_atual += timedelta(days=1)
    
    # Resumo final
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESUMO DO BACKFILL")
    logger.info(f"✅ Dias processados: {total_processado}")
    logger.info(f"❌ Dias com erro: {total_erros}")
    logger.info("=" * 80)
    
    if total_erros == 0:
        logger.info("🎉 BACKFILL CONCLUÍDO COM SUCESSO!")
        return True
    else:
        logger.warning("⚠️ Backfill concluído com alguns erros")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n❌ Backfill interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)
