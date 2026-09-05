"""
CONECT Productivity Automation - Versão Simplificada
Extrai produtividade dos plantonistas via web scraping
Salva resultados no GitHub automaticamente
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from playwright.async_api import async_playwright
import aiohttp

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
CONECT_USER = os.getenv("CONECT_USER", "194237")
CONECT_PASS = os.getenv("CONECT_PASS", "1234")
CONECT_CLIENT_CODE = "980"

FILIAL_NAME = "UPA SAO LEOPOLDO MANDIC"

TURNOS = {
    "Diurno": {"inicio": "07:00", "fim": "19:00"},
    "Noturno": {"inicio": "19:00", "fim": "07:00"},
    "Cinderela": {"inicio": "08:00", "fim": "20:00"},
}

# ============================================================================
# CLASSE CONECT AUTOMATION
# ============================================================================

class ConectAutomation:
    """Automatiza extração de dados do CONECT via Playwright"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
    async def start(self):
        """Inicia navegador"""
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
            await self.page.goto(CONECT_URL, wait_until="networkidle")
            
            # Preencher campos
            logger.info("Preenchendo credenciais...")
            
            # Tenta preencher cliente
            try:
                await self.page.fill('input[type="text"]', CONECT_CLIENT_CODE)
            except:
                pass
            
            # Tenta preencher usuário
            try:
                inputs = await self.page.locator('input[type="text"]').all()
                if len(inputs) > 0:
                    await inputs[0].fill(CONECT_USER)
            except:
                pass
            
            # Tenta preencher senha
            try:
                senha_inputs = await self.page.locator('input[type="password"]').all()
                if len(senha_inputs) > 0:
                    await senha_inputs[0].fill(CONECT_PASS)
            except:
                pass
            
            # Clicar botão
            try:
                await self.page.click('button:has-text("ENTRAR")')
                await self.page.wait_for_load_state("networkidle", timeout=30000)
            except:
                logger.warning("Botão de login não encontrado")
                return False
            
            logger.info("✅ Login realizado")
            return True
            
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            return False
    
    async def navigate_to_atendimentos(self):
        """Navega para Atendimentos"""
        try:
            logger.info("Navegando para Atendimentos...")
            
            # Clica em Atendimento
            try:
                await self.page.click('text=Atendimento')
                await self.page.wait_for_load_state("networkidle", timeout=30000)
            except:
                logger.warning("Menu Atendimento não encontrado")
            
            # Clica em Receptação
            try:
                await self.page.click('text=Receptação')
                await self.page.wait_for_load_state("networkidle", timeout=30000)
            except:
                logger.warning("Menu Receptação não encontrado")
            
            # Clica em Atendimentos
            try:
                await self.page.click('text=Atendimentos')
                await self.page.wait_for_load_state("networkidle", timeout=30000)
            except:
                logger.warning("Menu Atendimentos não encontrado")
            
            logger.info("✅ Navegação concluída")
            return True
            
        except Exception as e:
            logger.error(f"Erro na navegação: {e}")
            return False
    
    async def extract_data(self, medico, data_str, periodo_inicio, periodo_fim):
        """Extrai dados de atendimentos"""
        try:
            # Preencher filtros
            await self.page.fill('input[name="dataInicial"]', data_str)
            await self.page.fill('input[name="dataFinal"]', data_str)
            await self.page.fill('input[name="periodoInicial"]', periodo_inicio)
            await self.page.fill('input[name="periodoFinal"]', periodo_fim)
            
            # Buscar médico
            await self.page.fill('input[name="medico"]', medico)
            await self.page.wait_for_timeout(1000)
            
            # Clica primeira opção autocomplete
            try:
                await self.page.click(f'text={medico}')
            except:
                pass
            
            # Clica atualizar
            await self.page.click('button:has-text("ATUALIZAR")')
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            
            # Extrai tabela
            rows = await self.page.locator('table tbody tr').all()
            atendimentos = []
            
            for row in rows:
                try:
                    cells = await row.locator('td').all()
                    if len(cells) >= 7:
                        atendimento = {
                            "medico": medico,
                            "paciente": (await cells[1].text_content()).strip(),
                            "data_hora": (await cells[5].text_content()).strip(),
                        }
                        atendimentos.append(atendimento)
                except:
                    pass
            
            logger.info(f"✅ Extraídos {len(atendimentos)} atendimentos para {medico}")
            return atendimentos
            
        except Exception as e:
            logger.error(f"Erro ao extrair: {e}")
            return []
    
    async def close(self):
        """Fecha navegador"""
        if self.browser:
            await self.browser.close()

# ============================================================================
# LEITURA DE ESCALA
# ============================================================================

def ler_escala(arquivo_excel, data_target):
    """Lê escala do Excel"""
    try:
        logger.info(f"Lendo escala para {data_target.strftime('%Y-%m-%d')}...")
        
        df = pd.read_excel(arquivo_excel, sheet_name="Todos os plantões", header=1)
        df['Data'] = pd.to_datetime(df['Data'])
        
        data_date = pd.Timestamp(data_target.date())
        df_dia = df[df['Data'].dt.date == data_date.date()]
        
        escala = {}
        for turno in TURNOS.keys():
            try:
                medicos = df_dia[df_dia['Categoria'].str.contains(turno[:3], case=False, na=False)]['Plantonista'].dropna().unique().tolist()
                escala[turno] = [m for m in medicos if pd.notna(m) and str(m).strip()]
            except:
                escala[turno] = []
        
        logger.info(f"✅ Escala: {escala}")
        return escala
        
    except Exception as e:
        logger.error(f"Erro ao ler escala: {e}")
        return {}

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

async def main():
    """Função principal"""
    
    logger.info("=" * 80)
    logger.info("INICIANDO AUTOMAÇÃO - UPA SÃO LEOPOLDO MANDIC")
    logger.info("=" * 80)
    
    data_target = datetime.now() - timedelta(days=1)
    data_str = data_target.strftime("%d/%m/%Y")
    
    logger.info(f"Processando: {data_str}")
    
    # Ler escala
    excel_path = Path("escalas_upa_tabelas_junho_setembro_2026.xlsx")
    if not excel_path.exists():
        logger.error("❌ Arquivo de escala não encontrado")
        return False
    
    escala = ler_escala(excel_path, data_target)
    if not escala or not any(escala.values()):
        logger.error("❌ Nenhum plantonista encontrado")
        return False
    
    # Iniciar CONECT
    conect = ConectAutomation()
    if not await conect.start():
        return False
    
    if not await conect.login():
        await conect.close()
        return False
    
    if not await conect.navigate_to_atendimentos():
        await conect.close()
        return False
    
    # Extrair dados
    todos_atendimentos = []
    
    for turno, medicos in escala.items():
        if not medicos:
            continue
        
        turno_config = TURNOS[turno]
        
        for medico in medicos:
            dados = await conect.extract_data(
                medico, data_str,
                turno_config["inicio"],
                turno_config["fim"]
            )
            todos_atendimentos.extend(dados)
    
    await conect.close()
    
    # Salvar CSV
    if not todos_atendimentos:
        logger.warning("⚠️ Nenhum atendimento encontrado")
        return False
    
    df = pd.DataFrame(todos_atendimentos)
    arquivo = f"{data_target.strftime('%Y-%m-%d')}_produtividade.csv"
    
    df.to_csv(arquivo, index=False, encoding='utf-8-sig')
    logger.info(f"✅ Relatório salvo: {arquivo}")
    
    logger.info("=" * 80)
    logger.info("✅ PROCESSAMENTO CONCLUÍDO")
    logger.info("=" * 80)
    
    return True

# ============================================================================

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
