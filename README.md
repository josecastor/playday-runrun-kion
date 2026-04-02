# playday-runrun-kion

Gera um **resumo diário das atividades** trabalhadas no Runrun.it e publica automaticamente no mural de um time, em formato de tabela markdown com: código da tarefa, descrição, projeto, tempo trabalhado no dia, tempo total e comentários feitos no dia.

## Exemplo de saída no mural

```
## 🎯 PlayDay de José Castor — 01/04/2026

| Tarefa | Descrição         | Projeto                    | Tempo Dia | Tempo Total | Comentários |
|--------|-------------------|----------------------------|-----------|-------------|-------------|
| #2122  | Alteração SDTI    | Manutenção Processos Fluig | 8h        | 54h 50min   | —           |

**⏱ Total do dia: 8h**
```

---

## GitHub Actions (recomendado)

O workflow roda automaticamente todo dia útil às **07h BRT**, processa as atividades do dia anterior e publica no mural.

### 1. Configurar o Secret `RUNRUN_USERS`

No repositório, acesse **Settings → Secrets and variables → Actions → New repository secret**.

- **Name:** `RUNRUN_USERS`
- **Secret:** JSON array com a configuração de cada usuário:

```json
[
  {
    "app_key": "sua_app_key",
    "user_token": "seu_user_token",
    "user_id": "jose-castor",
    "bulletin_team_id": "496822"
  }
]
```

Para múltiplos usuários, adicione mais objetos no array:

```json
[
  {
    "app_key": "app_key_usuario1",
    "user_token": "user_token_usuario1",
    "user_id": "jose-castor",
    "bulletin_team_id": "496822"
  },
  {
    "app_key": "app_key_usuario2",
    "user_token": "user_token_usuario2",
    "user_id": "outro-usuario",
    "bulletin_team_id": "496822"
  }
]
```

> **Como obter `app_key` e `user_token`:** No Runrun.it, acesse _Integrações e Apps → API e Webhooks_.

> **Como descobrir o `bulletin_team_id`:** `curl "https://runrun.it/api/v1.0/teams" -H "App-Key: ..." -H "User-Token: ..."`

### 2. Disparo manual (para validação)

Acesse **Actions → Daily Activity Summary → Run workflow** e preencha os campos:

| Campo | Descrição |
|-------|-----------|
| `date` | Data específica em `YYYY-MM-DD` (deixe em branco para ontem) |
| `dry_run` | Marque `true` para visualizar sem publicar no mural |
| `user_id` | Filtra para um usuário específico (deixe em branco para todos) |

O resultado aparece na aba **Summary** do run após a execução.

---

## Execução local

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar credenciais

```bash
cp .env.example .env
```

Edite o `.env` com suas chaves (modo single-user):

```dotenv
RUNRUN_APP_KEY=sua_app_key
RUNRUN_USER_TOKEN=seu_user_token
RUNRUN_USER_ID=jose-castor
RUNRUN_BULLETIN_TEAM_ID=496822
```

Ou use a variável `RUNRUN_USERS` (mesmo formato do Secret) para testar com múltiplos usuários.

### 3. Executar

```bash
# Resumo de ontem (publica no mural)
python main.py

# Resumo de uma data específica
python main.py --date 2026-03-25

# Apenas visualizar sem publicar
python main.py --dry-run

# Processar apenas um usuário específico
python main.py --user-id jose-castor

# Combinações
python main.py --date 2026-03-25 --dry-run
python main.py --user-id jose-castor --dry-run
```

---

## Estrutura do projeto

```
playday-runrun-kion/
├── .github/
│   └── workflows/
│       └── daily-activity.yml   # Workflow GitHub Actions (07h BRT, dias úteis)
├── config/
│   └── settings.py              # Configurações e variáveis de ambiente
├── runrun/
│   ├── client.py                # Cliente HTTP base (auth, paginação, retry)
│   ├── time_worked.py           # Busca tempo trabalhado por usuário/dia
│   ├── tasks.py                 # Busca detalhes de tarefas
│   ├── comments.py              # Busca comentários feitos pelo usuário
│   ├── users.py                 # Resolução de nome do usuário
│   └── bulletin.py              # Publica no mural do time
├── resume/
│   ├── builder.py               # Orquestra coleta e monta o resumo
│   └── formatter.py             # Formata em markdown para o mural
├── tests/                       # Testes unitários
├── main.py                      # Entry point
└── requirements.txt
```

## Testes

```bash
pytest tests/ -v
```
