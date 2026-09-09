"""
CONECT AUTOMATION - BACKFILL com Selenium
Extrai dados de produtividade dos plantonistas automaticamente
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import base64
import requests
from openpyxl import load_workbook

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

CONECT_USER = os.getenv("CONECT_USER", "194237")
CONECT_PASS = os.getenv("CONECT_PASSWORD", "1234")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "rgjoaomarcos/conect-automation"
GITHUB_BRANCH = "main"

CONECT_LOGIN_URL = "https://modulos.conectew.com.br/conecte/modulos.jsf"
CONECT_ATENDIMENTOS_URL = "https://modulos.conectew.com.br/conecte/atendimento/site/recepcao/atendimentosRealizados/view.jsf"

DATA_INICIO = datetime(2026, 6, 1)
DATA_FIM = datetime(2026, 9, 6)

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
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    logger.info("✅ Chrome iniciado")
    return driver

def fazer_login(driver):
    """Faz login no CONECT"""
    logger.info("🔐 Fazendo login...")
    try:
        driver.get(CONECT_LOGIN_URL)
        wait = WebDriverWait(driver, 15)
        
        # Encontrar campos de input
        inputs = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "input")))
        
        if len(inputs) >= 3:
            inputs[0].send_keys("980")           # Unidade
            inputs[1].send_keys(CONECT_USER)     # Usuário
            inputs[2].send_keys(CONECT_PASS)     # Senha
            
            # Clicar botão de login
            buttons = driver.find_elements(By.TAG_NAME, "button")
            if buttons:
                buttons[0].click()
            
            # Aguardar redirecionamento
            wait.until(EC.url_changes(CONECT_LOGIN_URL))
            logger.info("✅ Login realizado com sucesso!")
            return True
        
        logger.error("❌ Não consegui localizar campos de login")
        return False
    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
        return False

def extrair_medicos_escala(data):
    """Extrai médicos da escala para uma data"""
    try:
        excel_path = Path("escalas_upa_tabelas_junho_setembro_2026.xlsx")
        if not excel_path.exists():
            logger.error("❌ Arquivo de escala não encontrado!")
            return []
        
        wb = load_workbook(excel_path)
        ws = wb["Todos os plantões"]
        
        medicos = set()
        data_str = data.strftime("%Y-%m-%d")
        
        for row in ws.iter_rows(min_row=4, values_only=True):
            if row[0]:
                row_date = str(row[0]).split()[0]
                if row_date == data_str and row[5]:
                    medicos.add(str(row[5]).strip())
        
        return list(medicos)
    except Exception as e:
        logger.error(f"❌ Erro ao ler escala: {e}")
        return []

def preencher_filtros_e_extrair(driver, medico, data):
    """Preenche filtros no CONECT e extrai dados da tabela"""
    try:
        logger.info(f"   📋 Processando {medico}...")
        
        # Navegar para página de atendimentos
        driver.get(CONECT_ATENDIMENTOS_URL)
        wait = WebDriverWait(driver, 15)
        
        # Aguardar campos carregarem
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "input")))
        
        # Encontrar e preencher campos de data
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        # Limpar e preencher campos (ordem pode variar, tentamos por padrão)
        data_formatada = data.strftime("%d/%m/%Y")
        
        # Procurar especificamente pelos campos de data
        for inp in inputs:
            placeholder = inp.get_attribute("placeholder") or ""
            name_attr = inp.get_attribute("name") or ""
            
            if "data" in placeholder.lower() or "data" in name_attr.lower():
                try:
                    inp.clear()
                    inp.send_keys(data_formatada)
                except:
                    pass
        
        # Preencher períodos (07:00 e 19:00)
        for inp in inputs:
            placeholder = inp.get_attribute("placeholder") or ""
            if "período" in placeholder.lower() or "hora" in placeholder.lower():
                try:
                    val = inp.get_attribute("value")
                    if not val or "07" not in val:
                        inp.clear()
                        inp.send_keys("07:00")
                    elif not val or "19" not in val:
                        inp.clear()
                        inp.send_keys("19:00")
                except:
                    pass
        
        # Selecionar médico (pode ser input com datalist ou select)
        for inp in inputs:
            placeholder = inp.get_attribute("placeholder") or ""
            name_attr = inp.get_attribute("name") or ""
            
            if "médico" in placeholder.lower() or "médico" in name_attr.lower():
                try:
                    inp.clear()
                    inp.send_keys(medico)
                    # Aguardar autocomplete se houver
                    import time
                    time.sleep(0.5)
                except:
                    pass
        
        # Clicar botão ATUALIZAR
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "ATUALIZAR" in btn.text.upper():
                btn.click()
                break
        
        # Aguardar tabela carregar
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))
        
        # Extrair dados da tabela
        atendimentos = []
        tabelas = driver.find_elements(By.TAG_NAME, "table")
        
        for tabela in tabelas:
            linhas = tabela.find_elements(By.TAG_NAME, "tr")
            
            for linha in linhas[1:]:  # Pular header
                try:
                    colunas = linha.find_elements(By.TAG_NAME, "td")
                    
                    if len(colunas) >= 2:
                        # Extrair dados conforme layout visto nas imagens
                        # Coluna 1: Nome do Paciente
                        # Coluna 2: Plano
                        # Coluna 3: Dados Atendimento
                        # Coluna 4: Tipo
                        # Coluna 5: Data Atendimento
                        # Coluna 6: Prontuário
                        # Coluna 7: Prestador
                        
                        paciente = colunas[1].text.strip() if len(colunas) > 1 else ""
                        plano = colunas[2].text.strip() if len(colunas) > 2 else ""
                        dados_atendimento = colunas[3].text.strip() if len(colunas) > 3 else ""
                        tipo = colunas[4].text.strip() if len(colunas) > 4 else ""
                        data_atendimento = colunas[5].text.strip() if len(colunas) > 5 else ""
                        prontuario = colunas[6].text.strip() if len(colunas) > 6 else ""
                        
                        if paciente:  # Só adicionar se houver nome
                            atendimento = {
                                'medico': medico,
                                'paciente': paciente,
                                'plano': plano,
                                'dados_atendimento': dados_atendimento,
                                'tipo': tipo,
                                'data_atendimento': data_atendimento,
                                'prontuario': prontuario,
                                'data_registro': data.strftime("%Y-%m-%d")
                            }
                            atendimentos.append(atendimento)
                except:
                    continue
        
        return atendimentos
    
    except TimeoutException:
        logger.warning(f"⚠️ Timeout ao processar {medico}")
        return []
    except Exception as e:
        logger.error(f"❌ Erro ao extrair: {e}")
        return []

# ============================================================================
# GITHUB
# ============================================================================

def salvar_no_github(data, atendimentos):
    """Salva CSV no GitHub"""
    if not GITHUB_TOKEN:
        logger.warning("⚠️ GITHUB_TOKEN não configurado")
        return False
    
    try:
        # Cabeçalho CSV
        conteudo = "medico,paciente,plano,dados_atendimento,tipo,data_atendimento,prontuario,data_registro\n"
        
        for atendimento in atendimentos:
            linha = f"{atendimento['medico']},{atendimento['paciente']},{atendimento['plano']},{atendimento['dados_atendimento']},{atendimento['tipo']},{atendimento['data_atendimento']},{atendimento['prontuario']},{atendimento['data_registro']}\n"
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
            "message": f"Backfill: {data_str} ({len(atendimentos)} atendimentos)",
            "content": content_b64,
            "branch": GITHUB_BRANCH
        }
        
        # Verificar se existe
        get_response = requests.get(url, headers=headers)
        if get_response.status_code == 200:
            payload["sha"] = get_response.json()["sha"]
        
        response = requests.put(url, json=payload, headers=headers)
        
        if response.status_code in [201, 200]:
            logger.info(f"✅ {data_str}: {len(atendimentos)} atendimentos")
            return True
        else:
            logger.error(f"❌ Erro GitHub: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Executa backfill completo"""
    logger.info("=" * 80)
    logger.info("🚀 CONECT AUTOMATION - BACKFILL (SELENIUM)")
    logger.info(f"📅 Período: {DATA_INICIO.strftime('%d/%m/%Y')} a {DATA_FIM.strftime('%d/%m/%Y')}")
    logger.info("=" * 80)
    
    driver = None
    try:
        driver = criar_driver()
        
        if not fazer_login(driver):
            return False
        
        data_atual = DATA_INICIO
        total_processado = 0
        total_atendimentos = 0
        
        while data_atual <= DATA_FIM:
            try:
                logger.info(f"\n📍 {data_atual.strftime('%d/%m/%Y')}")
                
                medicos = extrair_medicos_escala(data_atual)
                
                if not medicos:
                    logger.warning(f"⚠️ Nenhum médico na escala")
                    data_atual += timedelta(days=1)
                    continue
                
                logger.info(f"  Médicos: {len(medicos)}")
                
                todos_atendimentos = []
                for medico in medicos:
                    atendimentos = preencher_filtros_e_extrair(driver, medico, data_atual)
                    todos_atendimentos.extend(atendimentos)
                
                if todos_atendimentos or True:  # Salvar mesmo que vazio
                    if salvar_no_github(data_atual, todos_atendimentos):
                        total_processado += 1
                        total_atendimentos += len(todos_atendimentos)
                
                data_atual += timedelta(days=1)
            
            except Exception as e:
                logger.error(f"❌ Erro: {e}")
                data_atual += timedelta(days=1)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ Dias processados: {total_processado}")
        logger.info(f"📊 Total de atendimentos: {total_atendimentos}")
        logger.info("=" * 80)
        
        return True
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)
