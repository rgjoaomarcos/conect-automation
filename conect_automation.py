"""
CONECT Automation - COM WEB SCRAPING REAL
Faz login no CONECT, extrai pacientes atendidos e salva no GitHub via API REST
"""

import os
import sys
import logging
import requests
import base64
from datetime import datetime, timedelta
from pathlib import Path
import csv
from bs4 import BeautifulSoup
from openpyxl import load_workbook
import urllib3

# Desabilitar warnings de SSL (CONECT pode ter certificado auto-assinado)
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

# ============================================================================
# FUNÇÕES DE CONECT SCRAPING
# ============================================================================

def fazer_login_conect(session):
    """Faz login no CONECT e retorna sessão autenticada"""
    try:
        logger.info("🔐 Fazendo login no CONECT...")
        
        # Acessar página de login primeira vez para pegar cookies/tokens
        response = session.get(CONECT_LOGIN_URL, verify=False, timeout=10)
        
        # Preparar dados de login
        login_data = {
            "codigo": "980",
            "usuario": CONECT_USER,
            "senha": CONECT_PASS,
            "j_username": CONECT_USER,
            "j_password": CONECT_PASS,
        }
        
        # Tentar fazer login
        response = session.post(CONECT_LOGIN_URL, data=login_data, verify=False, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Login realizado com sucesso!")
            return True
        else:
            logger.error(f"❌ Erro no login: Status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout ao conectar com CONECT")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao fazer login: {e}")
        return False

def extrair_medicos_escala_ontem():
    """Lê o arquivo Excel e retorna lista de médicos de ontem"""
    try:
        excel_path = Path("escalas_upa_tabelas_junho_setembro_2026.xlsx")
        if not excel_path.exists():
            logger.error("❌ Arquivo de escala não encontrado")
            return []
        
        data_ontem = datetime.now() - timedelta(days=1)
        data_str = data_ontem.strftime("%d/%m/%Y")
        
        logger.info(f"📄 Lendo escala para: {data_str}")
        
        wb = load_workbook(excel_path)
        ws = wb["Todos os plantões"]
        
        medicos = []
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            data_plantonista = row[0]
            medico_nome = row[5]
            
            if data_plantonista and medico_nome:
                try:
                    if isinstance(data_plantonista, str):
                        data_formatada = datetime.strptime(data_plantonista, "%d/%m/%Y")
                    else:
                        data_formatada = data_plantonista
                    
                    if data_formatada.date() == data_ontem.date():
                        medicos.append(medico_nome)
                        logger.info(f"  📋 Médico encontrado: {medico_nome}")
                except:
                    pass
        
        if medicos:
            logger.info(f"✅ Total de médicos encontrados: {len(medicos)}")
        else:
            logger.warning(f"⚠️ Nenhum médico encontrado para {data_str}")
        
        return medicos
        
    except Exception as e:
        logger.error(f"❌ Erro ao ler escala: {e}")
        return []

def extrair_atendimentos_medico(session, medico_nome, data_ontem):
    """Extrai atendimentos de um médico específico no CONECT"""
    try:
        logger.info(f"🔍 Buscando atendimentos de {medico_nome}...")
        
        data_str = data_ontem.strftime("%d/%m/%Y")
        
        params = {
            "dataInicial": data_str,
            "dataFinal": data_str,
            "medico": medico_nome,
            "filial": "UPA SAO LEOPOLDO MANDIC",
            "somenteMeus": "false"
        }
        
        response = session.get(CONECT_ATENDIMENTOS_URL, params=params, verify=False, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"  ⚠️ Status {response.status_code} para {medico_nome}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        tabelas = soup.find_all('table')
        atendimentos = []
        
        for tabela in tabelas:
            linhas = tabela.find_all('tr')
            for linha in linhas[1:]:
                colunas = linha.find_all('td')
                if len(colunas) >= 3:
                    try:
                        paciente = colunas[0].get_text(strip=True)
                        hora = colunas[1].get_text(strip=True) if len(colunas) > 1 else ""
                        descricao = colunas[2].get_text(strip=True) if len(colunas) > 2 else ""
                        
                        if paciente:
                            atendimentos.append({
                                "medico": medico_nome,
                                "paciente": paciente,
                                "hora": hora,
                                "descricao": descricao,
                                "data": data_str
                            })
                    except:
                        pass
        
        if atendimentos:
            logger.info(f"  ✅ {len(atendimentos)} atendimento(s) encontrado(s)")
        else:
            logger.info(f"  ℹ️  Nenhum atendimento encontrado")
        
        return atendimentos
        
    except Exception as e:
        logger.error(f"  ❌ Erro ao extrair atendimentos: {e}")
        return []

# ============================================================================
# FUNÇÕES DE GITHUB API
# ============================================================================

def salvar_arquivo_github(arquivo_path, arquivo_nome):
    """Salva arquivo no GitHub via API REST"""
    try:
        if not GITHUB_TOKEN:
            logger.warning("⚠️ GITHUB_TOKEN não configurado - arquivo não será salvo no GitHub")
            return False
        
        logger.info(f"📤 Salvando {arquivo_nome} no GitHub...")
        
        with open(arquivo_path, 'rb') as f:
            arquivo_conteudo = f.read()
        
        github_path = f"relatorios/{arquivo_nome}"
        
        content_base64 = base64.b64encode(arquivo_conteudo).decode('utf-8')
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"
        
        payload = {
            "message": f"Produtividade {arquivo_nome}",
            "content": content_base64,
            "branch": GITHUB_BRANCH
        }
        
        response = requests.put(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [201, 200]:
            logger.info(f"✅ Arquivo salvo no GitHub com sucesso!")
            logger.info(f"📍 Caminho: {github_path}")
            return True
        else:
            logger.error(f"❌ Erro ao salvar no GitHub: {response.status_code}")
            logger.error(f"Resposta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao salvar no GitHub: {e}")
        return False

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Função principal"""
    
    logger.info("=" * 80)
    logger.info("INICIANDO AUTOMAÇÃO CONECT - UPA SÃO LEOPOLDO MANDIC")
    logger.info("=" * 80)
    
    data_ontem = datetime.now() - timedelta(days=1)
    data_str = data_ontem.strftime("%d/%m/%Y")
    
    logger.info(f"📅 Processando: {data_str}")
    
    session = requests.Session()
    
    if not fazer_login_conect(session):
        logger.error("❌ Falha ao fazer login - abortando")
        return False
    
    medicos_escala = extrair_medicos_escala_ontem()
    if not medicos_escala:
        logger.warning("⚠️ Nenhum médico encontrado para hoje")
        return False
    
    todos_atendimentos = []
    for medico in medicos_escala:
        atendimentos = extrair_atendimentos_medico(session, medico, data_ontem)
        todos_atendimentos.extend(atendimentos)
    
    arquivo = f"{data_ontem.strftime('%Y-%m-%d')}_produtividade.csv"
    
    try:
        with open(arquivo, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['medico', 'paciente', 'hora', 'descricao', 'data'])
            writer.writeheader()
            writer.writerows(todos_atendimentos)
        
        logger.info(f"✅ Relatório salvo localmente: {arquivo}")
        logger.info(f"✅ Total de atendimentos: {len(todos_atendimentos)}")
        
    except Exception as e:
        logger.error(f"Erro ao salvar CSV: {e}")
        return False
    
    if GITHUB_TOKEN:
        salvar_arquivo_github(arquivo, arquivo)
    else:
        logger.warning("⚠️ GITHUB_TOKEN não configurado")
        logger.info("📝 Configure a variável GITHUB_TOKEN no Railway para salvar no GitHub")
    
    logger.info("=" * 80)
    logger.info("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO")
    logger.info("=" * 80)
    
    return True

# ============================================================================

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
