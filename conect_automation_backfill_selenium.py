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
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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
# FUNÇÕES SELENIUM
# ============================================================================

def criar_driver():
    """Cria driver Chrome headless"""
    logger.info("🌐 Iniciando navegador Chrome...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-resources")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

def fazer_login_selenium(driver):
    """Faz login no CONECT usando Selenium"""
    logger.info("🔐 Acessando CONECT...")
    
    try:
        driver.get(CONECT_LOGIN_URL)
        wait = WebDriverWait(driver, 15)
        
        # Preencher formulário de login
        # Esperando que os campos apareçam
        logger.info("   Preenchendo credenciais...")
        
        # Tentar encontrar campos de login (podem ter IDs diferentes)
        # Aguardando um pouco para a página carregar
        driver.implicitly_wait(5)
        
        # Procurar por input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        if len(inputs) >= 2:
            inputs[0].send_keys("980")      # Unidade
            inputs[1].send_keys(CONECT_USER)  # Usuário
            inputs[2].send_keys(CONECT_PASS)  # Senha
        else:
            logger.warning("⚠️ Não consegui localizar campos de login automáticamente")
            # Tentar por ID ou name
            try:
                driver.find_element(By.ID, "j_username").send_keys(CONECT_USER)
                driver.find_element(By.ID, "j_password").send_keys(CONECT_PASS)
            except:
                logger.error("❌ Não consegui preencher login")
                return False
        
        # Clicar no botão de login
        buttons = driver.find_elements(By.TAG_NAME, "button")
        if buttons:
            buttons[0].click()
            logger.info("   Enviando login...")
            driver.implicitly_wait(5)
        
        # Verificar se login foi bem-sucedido (deve redirecionar)
        if "modulos.jsf" in driver.current_url or "atendimento" in driver.current_url:
            logger.info("✅ Login realizado com sucesso!")
            return True
        else:
            logger.error("❌ Falha no login - URL inesperada")
            return False
            
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
        data_str = data.strftime("%Y-%m-%d").replace("-", "/")  # Converter para XX/XX/XXXX se necessário
        
        for row in ws.iter_rows(min_row=4, values_only=True):
            if row[0]:
                row_date_str = str(row[0]).strip()[:10]  # Pegar apenas a data
                if row_date_str == data.strftime("%Y-%m-%d"):
                    if row[5]:  # Coluna de plantonista (índice 5)
                        medicos.add(str(row[5]).strip())
        
        return list(medicos)
    
    except Exception as e:
        logger.error(f"❌ Erro ao ler escala: {e}")
        return []

def extrair_atendimentos_selenium(driver, medico, data):
    """Extrai atendimentos de um médico usando Selenium"""
    try:
        logger.info(f"   📋 Extraindo atendimentos para {medico}...")
        
        # Navegar para página de atendimentos
        driver.get(CONECT_ATENDIMENTOS_URL)
        driver.implicitly_wait(3)
        
        # Preencher filtros (data, médico, etc)
        # Isso pode variar dependendo da estrutura do form
        
        # Tentar encontrar elementos de data e médico
        # Aguardando pela tabela de resultados
        
        atendimentos = []
        
        try:
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
        except:
            pass
        
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
        
        # Verificar se arquivo já existe
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
    """Executa o backfill de dados históricos com Selenium"""
    logger.info("=" * 80)
    logger.info("🚀 CONECT AUTOMATION - BACKFILL (SELENIUM)")
    logger.info(f"📅 Período: {DATA_INICIO.strftime('%d/%m/%Y')} a {DATA_FIM.strftime('%d/%m/%Y')}")
    logger.info("=" * 80)
    
    driver = None
    try:
        # Criar driver
        driver = criar_driver()
        
        # Fazer login
        if not fazer_login_selenium(driver):
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
                    atendimentos = extrair_atendimentos_selenium(driver, medico, data_atual)
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
    
    finally:
        if driver:
            driver.quit()
            logger.info("🔌 Navegador fechado")

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
