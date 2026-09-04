# 🏥 CONECT Productivity Automation

Automação completa para extração de produtividade dos plantonistas da **UPA São Leopoldo Mandic** através do sistema **CONECT**.

## 📋 O que faz?

Todos os dias às 7h da manhã:

1. 📖 **Lê a escala** de plantões do Excel (Junho-Setembro 2026)
2. 🔍 **Identifica os plantonistas** de ontem
3. 🤖 **Acessa o CONECT automaticamente** (sem intervenção manual)
4. 📊 **Extrai a tabela de atendimentos** para cada plantonista
5. 💾 **Salva um relatório consolidado** em CSV
6. ☁️ **Faz upload no OneDrive** para análise posterior

---

## 🚀 Quick Start

### Requisitos
- Python 3.9+
- Conta GitHub
- Conta Railway.app
- Conta Microsoft (OneDrive)
- Arquivo de escala (Excel)
- Acesso ao CONECT

### Instalação Local (Teste)

```bash
# Clone o repositório
git clone https://github.com/rgjoaomarcos/conect-automation.git
cd conect-automation

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# Execute manualmente
python conect_productivity_automation.py
```

### Deploy no Railway

Veja o arquivo [SETUP_RAILWAY.md](SETUP_RAILWAY.md) para guia completo passo-a-passo.

---

## 📁 Estrutura do Projeto

```
conect-automation/
├── conect_productivity_automation.py  # Script principal
├── requirements.txt                    # Dependências Python
├── .env.example                        # Exemplo de variáveis
├── Procfile                            # Configuração para Railway
├── README.md                           # Este arquivo
├── SETUP_RAILWAY.md                    # Guia de deployment
└── escalas_upa_tabelas_junho_setembro_2026.xlsx  # Escala de turnos
```

---

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```env
# Credenciais CONECT
CONECT_USER=194237              # Seu usuário
CONECT_PASS=1234                # Sua senha

# Microsoft OneDrive
MICROSOFT_EMAIL=seu_email@hotmail.com

# Configuração OneDrive
ONEDRIVE_FOLDER_ID=Produtividade_UPA
```

### Turnos Configurados

```python
Diurno:    07:00 - 19:00  (2 plantonistas)
Noturno:   19:00 - 07:00  (2 plantonistas)
Cinderela: 08:00 - 20:00  (1 plantonista)
```

---

## 📊 Formato de Saída

Cada arquivo gerado segue o padrão:

**Nome**: `YYYY-MM-DD_produtividade.csv`

**Colunas**:
| Coluna | Descrição |
|--------|-----------|
| medico | Nome do plantonista |
| paciente | Nome do paciente atendido |
| plano | Plano de saúde |
| tipo | Tipo de atendimento |
| data_hora | Data e hora do atendimento |
| prontuario | Número do prontuário |
| prestador | Nome do prestador |

**Exemplo**:
```csv
medico,paciente,plano,tipo,data_hora,prontuario,prestador
João Marcos,Maria Silva,BPA,Ambulatorial,02/09/2026 08:30,123456,João Marcos
João Marcos,Carlos Santos,BPA,Ambulatorial,02/09/2026 09:15,123457,João Marcos
```

---

## 🔄 Fluxo de Execução

```
[7:00 AM] Railway dispara cron job
    ↓
[Lê escala do Excel]
    ↓
[Extrai plantonistas de ontem]
    ↓
[Inicia navegador (Playwright)]
    ↓
[Login no CONECT]
    ↓
[Para cada plantonista:]
    ├─ Navega até Atendimentos
    ├─ Filtra por: médico + data + período
    ├─ Extrai tabela
    ├─ Salva dados
    └─ Limpa filtros
    ↓
[Consolida todos os dados]
    ↓
[Gera CSV]
    ↓
[Upload no OneDrive]
    ↓
[✅ Relatório pronto para análise]
```

---

## 📝 Logs

Os logs são salvos em tempo real e exibem:

- `✅ LOGIN REALIZADO` = Autenticação bem-sucedida
- `✅ NAVEGAÇÃO CONCLUÍDA` = Módulo Atendimentos acessado
- `✅ Extraídos X atendimentos` = Dados coletados com sucesso
- `✅ Arquivo enviado para OneDrive` = Upload concluído
- `❌ Erro...` = Algo deu errado (verifique a mensagem)

---

## 🔐 Segurança

### Credenciais
- ✅ **NÃO** são armazenadas no código
- ✅ Usam variáveis de ambiente no Railway
- ✅ Arquivo `.env` local não deve ser commitado

### Autenticação OneDrive
- ✅ Usa Device Code Flow (seguro)
- ✅ Primeira execução pede confirmação manual
- ✅ Token é temporal (expires automaticamente)

---

## 🐛 Troubleshooting

### "Acesso temporariamente restrito"
Se o GitHub estiver bloqueado:
1. Use GitLab ao invés (gitlab.com)
2. Ou use VPN

### "Arquivo de escala não encontrado"
- Certifique-se que `escalas_upa_tabelas_junho_setembro_2026.xlsx` está na raiz do repositório

### "Nenhum médico encontrado para esta data"
- Verifique se a data tem registros na escala
- Confira o formato da data (DD/MM/YYYY)

### "Tabela vazia"
- Pode ser que não houve atendimentos neste período
- Verifique manualmente no CONECT

---

## 📞 Suporte

Erros comuns e soluções:

| Erro | Causa | Solução |
|------|-------|---------|
| Login falha | Credenciais incorretas | Verificar CONECT_USER e CONECT_PASS |
| Tabela não encontra | Seletor CSS mudou | Atualizar localizadores HTML |
| OneDrive falha | Pasta não existe | Criar `Produtividade_UPA` manualmente |
| Timezone errado | Cron usa UTC | Definir TZ=America/Sao_Paulo no Railway |

---

## 🎯 Próximos Passos

1. ✅ Clone/fork este repositório
2. ✅ Configure no Railway (veja SETUP_RAILWAY.md)
3. ✅ Teste manualmente uma vez
4. ✅ Ative agendamento automático (cron)
5. ✅ Monitore os logs
6. ✅ Analise os dados no OneDrive

---

## 📄 Licença

MIT - Sinta-se livre para usar, modificar e distribuir.

---

## 👨‍💻 Desenvolvido para

**UPA São Leopoldo Mandic** - Araras, São Paulo

Automação de coleta de produtividade dos plantonistas - 2026

**Criado por**: Claude (Anthropic)
**Para**: João Marcos Rodrigues Gonçalves
**Data**: Setembro 2026
