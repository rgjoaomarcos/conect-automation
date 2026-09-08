"""
CONECT Automation - BACKFILL com Selenium
Extrai dados históricos de produtividade usando web browser automation
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import base64
import requests
from openpyxl import load_workbook

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
DATA_FIM = datetime.strptime("2026-09-06", "%Y-%m-%d")

# ============================================================================
# FUNÇÕES SELENIUM
# ============================================================================

def criar_driver():
    """Cria driver Chrome headless com webdriver_manager"""
    logger.info("🌐 Iniciando navegador Chrome...")
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Usar webdriver_manager para gerenciar chromedriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        logger.info("✅ Navegador iniciado com sucesso")
        return driver
    except Exception as e:
        logger.error(f"❌ Erro ao criar driver: {e}")
        raise

def fazer_login_selenium(driver):
    """Faz login no CONECT usando Selenium"""
    logger.info("🔐 Acessando CONECT...")
    
    try:
        driver.get(CONECT_LOGIN_URL)
        driver.implicitly_wait(10)
        
        logger.info("   Preenchendo credenciais...")
        
        # Tentar encontrar campos de entrada
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        if len(inputs) >= 3:
            inputs[0].send_keys("980")           # Unidade
            inputs[1].send_keys(CONECT_USER)     # Usuário
            inputs[2].send_keys(CONECT_PASS)     # Senha
            
            # Enviar formulário
            buttons = driver.find_elements(By.TAG_NAME, "button")
            if buttons:
                buttons[0].click()
                logger.info("   Login enviado...")
                driver.implicitly_wait(5)
        
        logger.info("✅ Login realizado")
        return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao fazer login: {e}")
        return False

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
        data_formatada = data.strftime("%Y-%m-%d")
        
        for row in ws.iter_rows(min_row=4, values_only=True):
            if row[0]:
                row_date = str(row[0]).split()[0]  # Pegar apenas a parte da data
                if row_date == data_formatada:
                    if row[5]:  # Coluna de plantonista
                        medicos.add(str(row[5]).strip())
        
        return list(medicos)
    
    except Exception as e:
        logger.error(f"❌ Erro ao ler escala: {e}")
        return []

def extrair_atendimentos_selenium(driver, medico, data):
    """Extrai atendimentos de um médico usando Selenium"""
    try:
        logger.info(f"   📋 Extraindo para {medico}...")
        
        # Navegar para página de atendimentos
        driver.get(CONECT_ATENDIMENTOS_URL)
        driver.implicitly_wait(5)
        
        atendimentos = []
        
        # Procurar por tabelas na página
        tabelas = driver.find_elements(By.TAG_NAME, "table")
        
        for tabela in tabelas:
            linhas = tabela.find_elements(By.TAG_NAME, "tr")
            
            for linha in linhas[1:]:  # Pular header
                try:
                    colunas = linha.find_elements(By.TAG_NAME, "td")
                    
                    if len(colunas) >= 4:
                        atendimento = {
                            'medico': medico,
                            'paciente': colunas[0].text.strip(),
                            'hora': colunas[1].text.strip(),
                            'descricao': colunas[2].text.strip(),
                            'data': data.strftime("%Y-%m-%d")
                        }
                        atendimentos.append(atendimento)
                except:
                    continue
        
        if not atendimentos:
            logger.debug(f"  Sem atendimentos para {medico}")
        
        return atendimentos
    
    except Exception as e:
        logger.error(f"❌ Erro ao extrair: {e}")
        return []

# ============================================================================
# FUNÇÕES DE GITHUB
# ============================================================================

def salvar_no_github(data, atendimentos):
    """Salva CSV no GitHub via API REST"""
    if not GITHUB_TOKEN:
        logger.warning("⚠️ GITHUB_TOKEN não configurado")
        return False
    
    try:
        # Gerar conteúdo CSV
        conteudo = "medico,paciente,hora,descricao,data\n"
        for atendimento in atendimentos:
            linha = f"{atendimento['medico']},{atendimento['paciente']},{atendimento['hora']},{atendimento['descricao']},{atendimento['data']}\n"
            conteudo += linha
        
        content_b64 = base64.b64encode(conteudo.encode()).decode()
        data_str = data.strftime("%Y-%m-%d")
        filename = f"relatorios/{data_str}_produtividade.csv"
        
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload = {
            "message": f"Backfill: {data_str}",
            "content": content_b64,
            "branch": GITHUB_BRANCH
        }
        
        # Verificar se existe
        get_response = requests.get(url, headers=headers)
        if get_response.status_code == 200:
            payload["sha"] = get_response.json()["sha"]
        
        response = requests.put(url, json=payload, headers=headers)
        
        if response.status_code in [201, 200]:
            logger.info(f"✅ {data_str}: {len(atendimentos)} atendimentos salvos")
            return True
        else:
            logger.error(f"❌ Erro GitHub: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
        return False

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Executa backfill com Selenium"""
    logger.info("=" * 80)
    logger.info("🚀 CONECT AUTOMATION - BACKFILL (SELENIUM)")
    logger.info(f"📅 Período: {DATA_INICIO.strftime('%d/%m/%Y')} a {DATA_FIM.strftime('%d/%m/%Y')}")
    logger.info("=" * 80)
    
    driver = None
    try:
        driver = criar_driver()
        
        if not fazer_login_selenium(driver):
            logger.error("❌ Falha no login - abortando")
            return False
        
        data_atual = DATA_INICIO
        total_processado = 0
        total_erros = 0
        
        while data_atual <= DATA_FIM:
            try:
                logger.info(f"\n📍 {data_atual.strftime('%d/%m/%Y')}")
                
                medicos = extrair_medicos_escala(data_atual)
                
                if not medicos:
                    logger.warning(f"⚠️ Nenhum médico encontrado")
                    data_atual += timedelta(days=1)
                    continue
                
                logger.info(f"  Médicos: {', '.join(medicos[:3])}{'...' if len(medicos) > 3 else ''}")
                
                todos_atendimentos = []
                for medico in medicos:
                    atendimentos = extrair_atendimentos_selenium(driver, medico, data_atual)
                    todos_atendimentos.extend(atendimentos)
                
                if todos_atendimentos:
                    if salvar_no_github(data_atual, todos_atendimentos):
                        total_processado += 1
                    else:
                        total_erros += 1
                else:
                    total_processado += 1
                
                data_atual += timedelta(days=1)
            
            except Exception as e:
                logger.error(f"❌ Erro processando: {e}")
                total_erros += 1
                data_atual += timedelta(days=1)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ Processados: {total_processado} | ❌ Erros: {total_erros}")
        logger.info("=" * 80)
        
        return total_erros == 0
    
    finally:
        if driver:
            driver.quit()
            logger.info("🔌 Navegador fechado")

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)
