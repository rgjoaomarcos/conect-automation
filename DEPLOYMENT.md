# ⚡ Deployment Rápido no Railway

## Resumo Executivo

**Tempo**: ~10 minutos  
**Dificuldade**: Fácil  
**Resultado**: Script rodando automaticamente às 7h todo dia

---

## 📋 Checklist Pré-Deployment

- [ ] Código no GitHub (`rgjoaomarcos/conect-automation`)
- [ ] Arquivo `escalas_upa_tabelas_junho_setembro_2026.xlsx` no root
- [ ] Account Railway criada e logada
- [ ] GitHub conectado ao Railway

---

## 🚀 Deployment em 5 Passos

### PASSO 1: Conectar Repositório

1. Acesse **https://railway.app/dashboard**
2. Clique **"New Project"**
3. Selecione **"Deploy from GitHub repo"**
4. Selecione `rgjoaomarcos/conect-automation`
5. Clique **"Deploy"** e aguarde (2-3 min)

### PASSO 2: Adicionar Variáveis

1. No projeto Railway, clique na aba **"Variables"**
2. Adicione cada variável (clique "New Variable"):

```
CONECT_USER = 194237
CONECT_PASS = 1234
MICROSOFT_EMAIL = joaomarcosrg@hotmail.com
ONEDRIVE_FOLDER_ID = Produtividade_UPA
```

3. Clique **"Save"**

### PASSO 3: Configurar como Cron Job

1. No menu esquerdo, clique **"Services"**
2. Clique na engrenagem ⚙️ do seu serviço
3. Em **"Environment"**, mude **"Service Type"** de `web` para `worker`
4. Salve

### PASSO 4: Criar Agendamento

**Opção A: Usar Railway's Built-in Cron** (mais fácil)

1. Em "Services", clique "New Service"
2. Selecione "Cron Job"
3. Configure:
   - **Name**: `conect-daily`
   - **Cron Schedule**: `0 7 * * *`
   - **Command**: `python conect_productivity_automation.py`
4. Em "Variables", copie todas as variáveis do step 2
5. Clique "Deploy"

**Opção B: Usar Scheduler Python** (mais flexível)

1. Mantenha o serviço como `worker`
2. Atualize o `Procfile`:
   ```
   worker: python scheduler.py
   ```
3. Faça commit e push
4. Railway vai redeploy automaticamente

### PASSO 5: Teste Manual

1. No Railway, vá até seu serviço
2. Clique na aba "Deployments"
3. Procure o botão "Run" ou "Redeploy"
4. Clique para executar manualmente
5. Verifique os logs (deve ver ✅ success)
6. Confira OneDrive se arquivo foi criado

---

## ✅ Confirmar Sucesso

Após execução bem-sucedida, você verá no OneDrive:

```
OneDrive/
  └── Produtividade_UPA/
      └── Relatórios_2026/
          └── 2026-09-04_produtividade.csv ← Aqui!
```

---

## 📊 Monitorar Execuções

### Logs no Railway
1. Projeto → Deployments
2. Clique em cada execução para ver logs completos
3. Procure por "✅" (sucesso) ou "❌" (erro)

### Horários de Execução
- **Primeira execução**: ~7:05 AM (Railway sincroniza no início de cada hora)
- **Próximas execuções**: Todos os dias às 7h (timezone Brasil)

---

## 🔧 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| "Service Failed" | Verifique logs, check .env |
| "File not found" | Adicione Excel ao repo/root |
| "OneDrive auth error" | Execute manualmente 1ª vez |
| "Arquivo vazio" | Verificar credenciais CONECT |

---

## 📱 Monitorar do Celular

### Via OneDrive App
1. Abra app OneDrive
2. Vá em `Produtividade_UPA` → `Relatórios_2026`
3. Veja o arquivo CSV mais recente
4. Compartilhe/analise com Excel Mobile

### Via Railway Alerts (opcional)
1. No Railway, "Settings" → "Notifications"
2. Ative email alerts para deployments

---

## 🎯 Próximas Ações

- [ ] Testar primeira execução manual
- [ ] Confirmar arquivo no OneDrive
- [ ] Ativar agendamento automático
- [ ] Configurar alertas de erro (opcional)
- [ ] Compartilhar arquivo com Luiz/gestão (opcional)

---

## 💡 Dicas

1. **SSH no Railway**: `railway run bash` para debug
2. **Ver variáveis**: `railway var list`
3. **Redeploy**: Todo push no GitHub = redeploy automático
4. **Custo**: Railway gratuito até $5/mês (este projeto é grátis)

---

**✅ Pronto! Você tem automação 24/7!**
