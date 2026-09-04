# 🚀 GUIA DE SETUP - RAILWAY + CONECT AUTOMATION

## Pré-requisitos
- ✅ Conta GitHub (rgjoaomarcos) - **JÁ TEM**
- ✅ Conta Railway.app - **JÁ TEM**
- ✅ Pasta no OneDrive (`Produtividade_UPA`) - **JÁ TEM**
- ✅ Arquivo Excel com escala - **JÁ TEM**

---

## PASSO 1: Preparar os Arquivos Localmente

### 1.1 Criar pasta do projeto
```bash
mkdir conect-automation
cd conect-automation
```

### 1.2 Copiar arquivos para a pasta
- `conect_productivity_automation.py` (script principal)
- `requirements.txt` (dependências)
- `.env.example` (exemplo de variáveis)
- `escalas_upa_tabelas_junho_setembro_2026.xlsx` (escala)
- `README.md` (documentação)

### 1.3 Criar arquivo `.env` (cópia do .env.example)
```
CONECT_USER=194237
CONECT_PASS=1234
MICROSOFT_EMAIL=joaomarcosrg@hotmail.com
ONEDRIVE_FOLDER_ID=Produtividade_UPA
```

---

## PASSO 2: Fazer Upload no GitHub

### 2.1 Inicializar repositório git
```bash
git init
git add .
git commit -m "Initial commit: CONECT automation script"
```

### 2.2 Criar repositório no GitHub
1. Acesse https://github.com/new
2. Nome: `conect-automation`
3. Descrição: "Automação de extração de produtividade do CONECT"
4. Deixe como "Public" (Railway funciona melhor)
5. Clique "Create repository"

### 2.3 Fazer push do código
```bash
git remote add origin https://github.com/rgjoaomarcos/conect-automation.git
git branch -M main
git push -u origin main
```

---

## PASSO 3: Configurar no Railway

### 3.1 Acessar Railway
1. Acesse https://railway.app
2. Faça login com GitHub (use "Login with GitHub")
3. Autorize se pedido

### 3.2 Criar novo projeto
1. Clique "New Project"
2. Selecione "Deploy from GitHub repo"
3. Conecte sua conta GitHub (se não estiver já conectada)
4. Selecione repositório `conect-automation`
5. Clique "Deploy"

### 3.3 Aguardar build (pode levar 2-3 minutos)
- Railway vai baixar o código
- Instalar dependências do `requirements.txt`
- Preparar o ambiente

---

## PASSO 4: Configurar Variáveis de Ambiente

### 4.1 No painel do Railway
1. Vá até seu projeto `conect-automation`
2. Clique na aba "Variables"
3. Adicione cada variável:

```
CONECT_USER = 194237
CONECT_PASS = 1234
MICROSOFT_EMAIL = joaomarcosrg@hotmail.com
ONEDRIVE_FOLDER_ID = Produtividade_UPA
```

4. Clique "Add" para cada uma
5. Clique "Save"

---

## PASSO 5: Configurar Agendamento (Cron Job)

### 5.1 No Railway, criar job agendado
1. Clique em "New Service"
2. Escolha "Cron Job"
3. Nome: `conect-automation-daily`

### 5.2 Configurar o cron
- **Cron Expression**: `0 7 * * *` (7h da manhã todo dia)
- **Command**: `python conect_productivity_automation.py`
- **Timezone**: `America/Sao_Paulo`

### 5.3 Vincular variáveis de ambiente
1. Clique no serviço Cron
2. Aba "Variables"
3. Copie todas as variáveis que criou antes

---

## PASSO 6: Teste Manual (Primeira Vez)

### 6.1 Executar manualmente antes de ativar
1. No Railway, clique no serviço cron
2. Clique "Run Now"
3. Aguarde (pode levar 30-60 segundos)
4. Verifique os logs

### 6.2 Verificar resultado
1. Acesse seu OneDrive
2. Vá para `Produtividade_UPA/Relatórios_2026/`
3. Procure arquivo com padrão: `YYYY-MM-DD_produtividade.csv`
4. Se tiver arquivo = ✅ **SUCESSO!**

---

## PASSO 7: Ativar Automação Diária

### 7.1 Após confirmar que funciona
1. No Railway, abra seu cron job
2. Clique no switch para "Enable"
3. Agora roda automaticamente às 7h todo dia

---

## 🔍 Monitorar Execuções

### No Railway
1. Vá até seu projeto
2. Clique na aba "Deployments"
3. Veja histórico de execuções
4. Clique em cada uma para ver logs

### Logs úteis
- ✅ `✅ LOGIN REALIZADO` = login funcionou
- ✅ `✅ NAVEGAÇÃO CONCLUÍDA` = CONECT acessado
- ✅ `✅ Extraídos X atendimentos` = dados coletados
- ✅ `✅ Arquivo enviado para OneDrive` = upload ok
- ❌ Se ver `❌` = erro na execução

---

## ⚠️ Troubleshooting

### Erro: "Arquivo de escala não encontrado"
- Railway precisa que o arquivo esteja no repositório
- Solução: Coloque `escalas_upa_tabelas_junho_setembro_2026.xlsx` no root do repo

### Erro: "Autenticação OneDrive falha"
- Primeira execução pede autorização manual
- Solução: Executar manualmente uma vez para confirmar

### Erro: "Tabela vazia"
- Pode ser que o médico não tenha atendimentos naquele dia
- Verificar no CONECT manualmente

### Erro: "Período inválido"
- Verificar se "Noturno" que cruza de 19:00 para 07:00 do dia seguinte

---

## 📋 Checklist Final

- [ ] Repositório GitHub criado e com código
- [ ] Railway conectado ao GitHub
- [ ] Variáveis de ambiente configuradas
- [ ] Arquivo Excel no repositório
- [ ] Cron job criado com horário `0 7 * * *`
- [ ] Teste manual executado com sucesso
- [ ] Arquivo CSV gerado no OneDrive
- [ ] Cron job ativado (Enable = ON)
- [ ] Logs monitorados no Railway

---

## 🎯 Pronto!

A partir de amanhã, **às 7h da manhã**:
1. Railway dispara o script automaticamente
2. Script acessa CONECT
3. Extrai produtividade de ontem
4. Salva no OneDrive
5. Você pode ver os dados no celular via OneDrive app

**Sem fazer nada!** ✅
