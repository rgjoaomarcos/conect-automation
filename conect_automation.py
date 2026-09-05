"""
CONECT Automation - Com salvamento no GitHub
Gera CSV e faz commit automático no repositório
"""

import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import csv

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

# ============================================================================
# FUNÇÕES DE GIT
# ============================================================================

def fazer_commit_github(arquivo, data_str):
    """Faz commit e push do arquivo para GitHub"""
    try:
        logger.info(f"📤 Fazendo commit no GitHub...")
        
        # Configurar git
        subprocess.run(
            ["git", "config", "user.email", "automation@upa.com"],
            check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "UPA Automation"],
            check=True, capture_output=True
        )
        
        # Add arquivo
        subprocess.run(
            ["git", "add", arquivo],
            check=True, capture_output=True
        )
        
        # Commit
        subprocess.run(
            ["git", "commit", "-m", f"Produtividade {data_str}"],
            check=True, capture_output=True
        )
        
        # Push (com token no URL)
        remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        subprocess.run(
            ["git", "push", remote_url, "main"],
            check=True, capture_output=True
        )
        
        logger.info(f"✅ Commit feito com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro ao fazer commit: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro geral git: {e}")
        return False

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Função principal"""
    
    logger.info("=" * 80)
    logger.info("INICIANDO AUTOMAÇÃO - UPA SÃO LEOPOLDO MANDIC")
    logger.info("=" * 80)
    
    data_target = datetime.now() - timedelta(days=1)
    data_str = data_target.strftime("%d/%m/%Y")
    
    logger.info(f"Processando: {data_str}")
    
    # Verificar se arquivo existe
    excel_path = Path("escalas_upa_tabelas_junho_setembro_2026.xlsx")
    if not excel_path.exists():
        logger.error("❌ Arquivo de escala não encontrado")
        return False
    
    logger.info(f"✅ Arquivo de escala encontrado: {excel_path}")
    
    # Criar CSV
    arquivo = f"{data_target.strftime('%Y-%m-%d')}_produtividade.csv"
    
    # Cabeçalhos
    headers = ["medico", "paciente", "data_hora"]
    
    # Dados de exemplo (em produção, isso viria do CONECT)
    dados = [
        ["Dr. João", "Paciente A", f"{data_str} 08:30"],
        ["Dr. Maria", "Paciente B", f"{data_str} 09:15"],
    ]
    
    # Salvar CSV
    try:
        with open(arquivo, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(dados)
        
        logger.info(f"✅ Relatório salvo localmente: {arquivo}")
        logger.info(f"✅ Linhas: {len(dados)}")
        
    except Exception as e:
        logger.error(f"Erro ao salvar CSV: {e}")
        return False
    
    # Fazer commit no GitHub
    if GITHUB_TOKEN:
        if not fazer_commit_github(arquivo, data_str):
            logger.warning("⚠️ Falha ao fazer commit, mas CSV foi criado localmente")
            # Continua mesmo que o git falhe
    else:
        logger.warning("⚠️ GITHUB_TOKEN não configurado - CSV não será salvo no GitHub")
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
