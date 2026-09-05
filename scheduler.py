"""
Scheduler simples - executa script diariamente às 7h
"""

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime

# Timezone Brasil
os.environ['TZ'] = 'America/Sao_Paulo'

def executar():
    """Executa o script"""
    print(f"\n{'='*80}")
    print(f"[{datetime.now()}] Executando automação...")
    print(f"{'='*80}\n")
    
    resultado = subprocess.run(
        [sys.executable, "conect_automation_simple.py"],
        capture_output=False
    )
    
    if resultado.returncode == 0:
        print(f"\n{'='*80}")
        print(f"[{datetime.now()}] ✅ Sucesso!")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}")
        print(f"[{datetime.now()}] ❌ Falha!")
        print(f"{'='*80}\n")

# Agendar execução diária às 7h
schedule.every().day.at("07:00").do(executar)

print(f"🚀 Scheduler iniciado")
print(f"📅 Execução agendada para: 07:00 (Brasil)")
print(f"⏰ Hora atual: {datetime.now()}")
print(f"💤 Aguardando horário agendado...\n")

# Loop contínuo
while True:
    try:
        schedule.run_pending()
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n⛔ Scheduler parado")
        break
    except Exception as e:
        print(f"❌ Erro: {e}")
        time.sleep(60)
