"""
Script de Automação de Produtividade - UPA São Leopoldo Mandic
Extrai dados de atendimentos do CONECT para cada plantonista
Salva relatório consolidado no OneDrive
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from playwright.async_api import async_playwright, expect
import aiohttp
from msal import PublicClientApplication
from microsoft_graph_beta import GraphServiceClient
from azure.identity import DeviceCodeCredential

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

CONECT_URL = "https://modulos.conectew.com.br/conecte/modulos.jsf"
CONECT_LOGIN_USER = os.getenv("CONECT_USER", "194237")
CONECT_LOGIN_PASS = os.getenv("CONECT_PASS", "1234")
CONECT_CLIENT_CODE = "980"

FILIAL_NAME = "UPA SAO LEOPOLDO MANDIC"

TURNOS = {
    "Diurno": {"inicio": "07:00", "fim": "19:00", "qtd": 2},
    "Noturno": {"inicio": "19:00", "fim": "07:00", "qtd": 2},
    "Cinderela": {"inicio": "08:00", "fim": "20:00", "qtd": 1},
}

ONEDRIVE_FOLDER_ID = os.getenv("ONEDRIVE_FOLDER_ID", "Produtividade_UPA")
ONEDRIVE_REPORTS_FOLDER = "Relatórios_2026"

# ============================================================================
# CLASSE PARA GERENCIAR ONEDRIVE
# ============================================================================

class OneDriveManager:
    """Gerencia acesso ao OneDrive via Microsoft Graph API"""
    
    def __init__(self, email):
        self.email = email
        self.token = None
        self.client = None
        
    async def authenticate(self):
        """Autentica com OneDrive usando Device Code Flow"""
        try:
            logger.info("Iniciando autenticação com OneDrive...")
            
            app = PublicClientApplication(
                client_id="1950a258-227b-4e31-a9cf-717495945fc2",  # CLI do Azure
                authority="https://login.microsoftonline.com/common"
            )
            
            # Device code flow
            flow = app.initiate_device_flow(scopes=["https://graph.microsoft.com/.default"])
            print("\n" + flow['message'])  # Mostrar código ao usuário
            
            result = app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                self.token = result["access_token"]
                logger.info("✅ Autenticação bem-sucedida!")
                return True
            else:
                logger.error("❌ Falha na autenticação:", result.get("error_description"))
                return False
                
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return False
    
    async def get_folder_id(self, folder_name):
        """Obtém ID da pasta pelo nome"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.token}"}
                
                # Buscar pasta no OneDrive
                url = f"https://graph.microsoft.com/v1.0/me/drive/root/children"
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    
                    for item in data.get("value", []):
                        if item.get("name") == folder_name:
                            return item.get("id")
                            
                logger.warning(f"Pasta '{folder_name}' não encontrada")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar pasta: {e}")
            return None
    
    async def upload_file(self, file_path, onedrive_path):
        """Faz upload de arquivo para OneDrive"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.token}"}
                
                with open(file_path, 'rb') as f:
                    # Upload simples
                    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_path}:/content"
                    async with session.put(url, data=f, headers=headers) as resp:
                        if resp.status in [200, 201]:
                            logger.info(f"✅ Arquivo '{onedrive_path}' enviado para OneDrive")
                            return True
                        else:
                            logger.error(f"Erro no upload: {await resp.text()}")
                            return False
                            
        except Exception as e:
            logger.error(f"Erro ao fazer upload: {e}")
            return False

# ============================================================================
# CLASSE PARA GERENCIAR CONECT
# ============================================================================

class ConectAutomation:
    """Automatiza extração de dados do CONECT via Playwright"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    async def start_browser(self):
        """Inicia navegador Playwright"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            logger.info("✅ Navegador iniciado")
            return True
        except Exception as e:
            logger.error(f"Erro ao iniciar navegador: {e}")
            return False
    
    async def login(self):
        """Faz login no CONECT"""
        try:
            logger.info("Acessando CONECT...")
            await self.page.goto(CONECT_URL)
            await self.page.wait_for_load_state("networkidle")
            
            # Preencher formulário de login
            logger.info("Preenchendo credenciais...")
            
            # Campo de código de cliente
            await self.page.fill('input[type="text"]', CONECT_CLIENT_CODE)
            
            # Campo de usuário
            await self.page.fill('input[type="password"][placeholder*="194237"]', CONECT_LOGIN_USER)
            
            # Campo de senha (tentando múltiplos seletores)
            senha_inputs = await self.page.locator('input[type="password"]').all()
            if len(senha_inputs) >= 2:
                await senha_inputs[1].fill(CONECT_LOGIN_PASS)
            
            # Clicar botão Entrar
            await self.page.click('button:has-text("ENTRAR")')
            await self.page.wait_for_load_state("networkidle")
            
            logger.info("✅ Login realizado")
            return True
            
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            return False
    
    async def navigate_to_atendimentos(self):
        """Navega até módulo de Atendimentos -> Receptação -> Atendimentos"""
        try:
            logger.info("Navegando para Atendimentos...")
            
            # Clicar no módulo Atendimento
            await self.page.click('text=Atendimento')
            await self.page.wait_for_load_state("networkidle")
            
            # Clicar em Receptação
            await self.page.click('text=Receptação')
            await self.page.wait_for_load_state("networkidle")
            
            # Clicar em Atendimentos
            await self.page.click('text=Atendimentos')
            await self.page.wait_for_load_state("networkidle")
            
            logger.info("✅ Navegação concluída")
            return True
            
        except Exception as e:
            logger.error(f"Erro na navegação: {e}")
            return False
    
    async def extract_atendimentos(self, medico_nome, data_inicio, data_fim, 
                                   periodo_inicio, periodo_fim):
        """Extrai dados de atendimentos para um médico específico"""
        try:
            logger.info(f"Extraindo atendimentos: {medico_nome} ({periodo_inicio}-{periodo_fim})")
            
            # Preencher data inicial
            await self.page.fill('input[name="dataInicial"]', data_inicio)
            
            # Preencher data final
            await self.page.fill('input[name="dataFinal"]', data_fim)
            
            # Preencher período inicial
            await self.page.fill('input[name="periodoInicial"]', periodo_inicio)
            
            # Preencher período final
            await self.page.fill('input[name="periodoFinal"]', periodo_fim)
            
            # Buscar médico
            await self.page.fill('input[name="medico"]', medico_nome)
            await self.page.wait_for_timeout(500)  # Aguardar autocomplete
            
            # Clicar na primeira opção do autocomplete
            await self.page.click('text=' + medico_nome)
            
            # Clicar em ATUALIZAR
            await self.page.click('button:has-text("ATUALIZAR")')
            await self.page.wait_for_load_state("networkidle")
            
            # Extrair dados da tabela
            rows = await self.page.locator('table tbody tr').all()
            atendimentos = []
            
            for row in rows:
                cells = await row.locator('td').all()
                if len(cells) >= 8:  # Verificar se tem todas as colunas
                    atendimento = {
                        "medico": medico_nome,
                        "paciente": await cells[1].text_content(),
                        "plano": await cells[2].text_content(),
                        "tipo": await cells[4].text_content(),
                        "data_hora": await cells[5].text_content(),
                        "prontuario": await cells[6].text_content(),
                        "prestador": await cells[7].text_content(),
                    }
                    atendimentos.append(atendimento)
            
            logger.info(f"✅ Extraídos {len(atendimentos)} atendimentos")
            return atendimentos
            
        except Exception as e:
            logger.error(f"Erro ao extrair atendimentos: {e}")
            return []
    
    async def close(self):
        """Fecha navegador"""
        if self.browser:
            await self.browser.close()
            logger.info("Navegador fechado")

# ============================================================================
# LEITURA DE ESCALA DO EXCEL
# ============================================================================

def ler_escala_excel(arquivo_excel, data_target):
    """Lê escala do Excel para uma data específica"""
    try:
        logger.info(f"Lendo escala do Excel para {data_target.strftime('%Y-%m-%d')}...")
        
        df = pd.read_excel(arquivo_excel, sheet_name="Todos os plantões", header=1)
        
        # Filtrar por data
        df['Data'] = pd.to_datetime(df['Data'])
        data_date = pd.Timestamp(data_target.date())
        
        df_dia = df[df['Data'].dt.date == data_date.date()]
        
        escala = {}
        for turno in TURNOS.keys():
            escala[turno] = df_dia[df_dia['Categoria'].str.contains(turno[:3], case=False, na=False)]['Plantonista'].unique().tolist()
        
        logger.info(f"✅ Escala carregada: {escala}")
        return escala
        
    except Exception as e:
        logger.error(f"Erro ao ler escala: {e}")
        return {}

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

async def main():
    """Função principal - orquestra todo o fluxo"""
    
    logger.info("=" * 80)
    logger.info("INICIANDO AUTOMAÇÃO DE PRODUTIVIDADE - UPA SÃO LEOPOLDO MANDIC")
    logger.info("=" * 80)
    
    # Data a processar (ontem)
    data_target = datetime.now() - timedelta(days=1)
    data_str = data_target.strftime("%d/%m/%Y")
    
    logger.info(f"Processando dados de: {data_str}")
    
    # ====== 1. LER ESCALA ======
    excel_path = Path("escalas_upa_tabelas_junho_setembro_2026.xlsx")
    if not excel_path.exists():
        logger.error("❌ Arquivo de escala não encontrado!")
        return False
    
    escala = ler_escala_excel(excel_path, data_target)
    if not escala:
        logger.error("❌ Nenhum plantonista encontrado para esta data")
        return False
    
    # ====== 2. INICIAR CONECT ======
    conect = ConectAutomation()
    if not await conect.start_browser():
        return False
    
    if not await conect.login():
        await conect.close()
        return False
    
    if not await conect.navigate_to_atendimentos():
        await conect.close()
        return False
    
    # ====== 3. EXTRAIR DADOS PARA CADA PLANTONISTA ======
    todos_atendimentos = []
    
    for turno, medicos in escala.items():
        if not medicos or pd.isna(medicos[0]):
            logger.warning(f"⚠️ Nenhum plantonista para turno {turno}")
            continue
        
        turno_config = TURNOS[turno]
        
        for medico in medicos:
            atendimentos = await conect.extract_atendimentos(
                medico_nome=medico,
                data_inicio=data_str,
                data_fim=data_str,
                periodo_inicio=turno_config["inicio"],
                periodo_fim=turno_config["fim"]
            )
            todos_atendimentos.extend(atendimentos)
    
    await conect.close()
    
    # ====== 4. SALVAR RELATÓRIO ======
    if not todos_atendimentos:
        logger.warning("⚠️ Nenhum atendimento encontrado")
        return False
    
    df_relatorio = pd.DataFrame(todos_atendimentos)
    
    # Salvar localmente primeiro
    arquivo_saida = f"{data_target.strftime('%Y-%m-%d')}_produtividade.csv"
    df_relatorio.to_csv(arquivo_saida, index=False, encoding='utf-8-sig')
    logger.info(f"✅ Relatório salvo: {arquivo_saida}")
    
    # ====== 5. FAZER UPLOAD NO ONEDRIVE ======
    onedrive = OneDriveManager(os.getenv("MICROSOFT_EMAIL"))
    
    if await onedrive.authenticate():
        folder_id = await onedrive.get_folder_id(ONEDRIVE_FOLDER_ID)
        if folder_id:
            onedrive_path = f"{ONEDRIVE_FOLDER_ID}/{ONEDRIVE_REPORTS_FOLDER}/{arquivo_saida}"
            await onedrive.upload_file(arquivo_saida, onedrive_path)
    
    logger.info("=" * 80)
    logger.info("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO")
    logger.info("=" * 80)
    
    return True

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Processo interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
