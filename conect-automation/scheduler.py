"""
Scheduler para executar o script de automação diariamente às 7h
Roda no Railway em background permanente
"""

import schedule
import time
import logging
from datetime import datetime
import subprocess
import sys
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Timezone Brasil
os.environ['TZ'] = 'America/Sao_Paulo'
if hasattr(time, 'tzset'):
    time.tzset()

# ============================================================================

def executar_automacao():
    """Executa o script de automação"""
    logger.info("=" * 80)
    logger.info("INICIANDO EXECUÇÃO AGENDADA")
    logger.info("=" * 80)
    
    try:
        resultado = subprocess.run(
            [sys.executable, "conect_productivity_automation.py"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos de timeout
        )
        
        # Log da saída
        if resultado.stdout:
            logger.info("STDOUT:\n" + resultado.stdout)
        if resultado.stderr:
            logger.warning("STDERR:\n" + resultado.stderr)
        
        if resultado.returncode == 0:
            logger.info("✅ Execução bem-sucedida")
        else:
            logger.error(f"❌ Execução falhou com código: {resultado.returncode}")
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout na execução (10 minutos excedido)")
    except Exception as e:
        logger.error(f"❌ Erro ao executar: {e}")
    
    logger.info("=" * 80)

# ============================================================================

def main():
    """Função principal - schedula execução diária"""
    
    logger.info("🚀 SCHEDULER INICIADO")
    logger.info(f"   Hora atual: {datetime.now()}")
    logger.info(f"   Execução agendada para: 07:00 Brasil")
    logger.info("   Timezone: America/Sao_Paulo")
    
    # Agendar execução diária às 7h da manhã
    schedule.every().day.at("07:00").do(executar_automacao)
    
    logger.info("✅ Scheduler aguardando agendamento...")
    
    # Loop contínuo
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
        except KeyboardInterrupt:
            logger.info("Scheduler parado pelo usuário")
            break
        except Exception as e:
            logger.error(f"Erro no scheduler: {e}")
            time.sleep(60)

# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
