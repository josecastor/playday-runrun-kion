# playday-runrun-kion

Gera **resumos de atividades** do Runrun.it — diário e mensal — e publica automaticamente no mural de um time, em formato de tabela markdown.

## Exemplo de saída — Diário

```
## 🎯 PlayDay de José Castor — 08/04/2026

| Tarefa | Descrição         | Projeto                    | Tempo Dia | Tempo Total | Comentários |
|--------|-------------------|----------------------------|-----------|-------------|-------------|
| #1969  | 23 - Chão de Fábrica | Manutenção Corretiva (Bug) | 6h 38min | 60h 32min  | —           |

**⏱ Total do dia: 8h**
```

## Exemplo de saída — Mensal

```
## PlayDay Mensal de José Castor — Março/2026

| Dia   | Tarefa | Descrição              | Projeto                    | Tempo Dia |
|-------|--------|------------------------|----------------------------|-----------|
| 10/03 | #1960  | 14 - Movimentação Pessoal | Manutenção Corretiva (Bug) | 4h 26min |
| 10/03 | #1962  | 16 - Requisição de Desligamento | Manutenção Corretiva (Bug) | 2h 36min |
| ...   | ...    | ...                    | ...                        | ...       |

**Total do mês: 127h 39min**
```

---

## GitHub Actions (recomendado)

O workflow roda automaticamente todo dia útil às **07h BRT**, processa as atividades do dia anterior e publica no mural. No **dia 1 de cada mês**, roda também o resumo mensal do mês anterior.

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
    "bulletin_team_id": "496822",
    "bulletin_team_id_monthly": ""
  }
]
```

> `bulletin_team_id_monthly` é **opcional**. Se vazio ou ausente, o resumo mensal é publicado no mesmo mural que o diário (`bulletin_team_id`). Preencha para publicar o mensal em um mural diferente.

Para múltiplos usuários, adicione mais objetos no array. Veja `runrun-users.example.json` na raiz do projeto como referência (não versionado).

> **Como obter `app_key` e `user_token`:** No Runrun.it, acesse _Integrações e Apps → API e Webhooks_.

> **Como descobrir o `bulletin_team_id`:** `curl "https://runrun.it/api/v1.0/teams" -H "App-Key: ..." -H "User-Token: ..."`

### 2. Disparo manual (para validação)

Acesse **Actions → Daily Activity Summary → Run workflow** e preencha os campos:

| Campo | Descrição |
|-------|-----------|
| `date` | Data específica em `YYYY-MM-DD` (deixe em branco para ontem) |
| `dry_run` | Marque `true` para visualizar sem publicar no mural |
| `user_id` | Filtra para um usuário específico (deixe em branco para todos) |
| `monthly` | Marque `true` para forçar o resumo mensal do mês anterior |

O resultado aparece na aba **Summary** do run após a execução.

---

## Execução local

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar credenciais

Crie um arquivo `.env` na raiz (não versionado):

```dotenv
RUNRUN_APP_KEY=sua_app_key
RUNRUN_USER_TOKEN=seu_user_token
RUNRUN_USER_ID=jose-castor
RUNRUN_BULLETIN_TEAM_ID=496822
RUNRUN_BULLETIN_TEAM_ID_MONTHLY=   # opcional — mural separado para o resumo mensal
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

# Forçar resumo mensal do mês anterior (além do diário)
python main.py --monthly

# Combinações
python main.py --date 2026-03-25 --dry-run
python main.py --monthly --dry-run
python main.py --user-id jose-castor --monthly --dry-run
```

---

## Estrutura do projeto

```
playday-runrun-kion/
├── .github/
│   └── workflows/
│       └── daily-activity.yml   # Workflow GitHub Actions (07h BRT, dias úteis + mensal dia 1)
├── config/
│   └── settings.py              # Configurações e variáveis de ambiente
├── runrun/
│   ├── client.py                # Cliente HTTP base (auth, paginação automática, retry 429)
│   ├── time_worked.py           # get_time_worked (dia) + get_time_worked_range (intervalo)
│   ├── tasks.py                 # Busca detalhes de tarefas
│   ├── comments.py              # Busca comentários feitos pelo usuário
│   ├── users.py                 # Resolução de nome do usuário
│   └── bulletin.py              # Publica no mural do time
├── resume/
│   ├── builder.py               # DailySummary + MonthlySummary — orquestra e monta resumos
│   └── formatter.py             # Formata em markdown (diário e mensal)
├── tests/
│   ├── test_builder.py          # Testes do builder diário
│   ├── test_formatter.py        # Testes do formatter diário
│   ├── test_time_worked_range.py # Testes de get_time_worked_range
│   ├── test_monthly_builder.py  # Testes do builder mensal
│   └── test_monthly_formatter.py # Testes do formatter mensal
├── docs/
│   └── superpowers/
│       ├── specs/               # Design docs aprovados
│       └── plans/               # Planos de implementação
├── main.py                      # Entry point
├── runrun-users.example.json    # Exemplo de RUNRUN_USERS (não versionado)
└── requirements.txt
```

## Testes

```bash
python3.11 -m pytest tests/ -v
```

45 testes cobrindo `time_worked_range`, `builder` (diário e mensal) e `formatter` (diário e mensal). Chamadas de API são mockadas. Não há testes para `runrun/client.py` nem para o fluxo de publicação no mural.
