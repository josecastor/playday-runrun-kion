# pkg-resume-activity-runrun

Gera um **resumo diário das atividades** trabalhadas no Runrun.it e publica automaticamente no mural de um time, em formato de tabela markdown com: código da tarefa, descrição, projeto, tempo trabalhado e comentários feitos no dia.

## Exemplo de saída no mural

```
## 📋 Resumo de Atividades — 26/03/2026

| Tarefa | Descrição | Projeto | Tempo | Comentários |
|--------|-----------|---------|-------|-------------|
| #1234  | Implementar login | Projeto Luna | 1h 30min | Ajustei lógica de validação |
| #1235  | Corrigir bug de sessão | Projeto Luna | 45min | — |
| #1240  | Reunião de alinhamento | Interno | 1h | Alinhamos entregas da sprint |

**⏱ Total trabalhado: 3h 15min**
```

## Configuração

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar credenciais

```bash
cp .env.example .env
```

Edite o `.env` com suas chaves:

```dotenv
RUNRUN_APP_KEY=sua_app_key
RUNRUN_USER_TOKEN=seu_user_token
RUNRUN_USER_ID=jose-castor
RUNRUN_BULLETIN_TEAM_ID=93625
```

> **Como obter suas chaves:** No Runrun.it, acesse *Integrações e Apps → API e Webhooks*.

> **Como descobrir o ID do time:** `curl "https://runrun.it/api/v1.0/teams" -H "App-Key: ..." -H "User-Token: ..."`

### 3. Executar

```bash
# Resumo do dia de hoje (publica no mural)
python main.py

# Resumo de uma data específica
python main.py --date 2026-03-25

# Apenas visualizar sem publicar
python main.py --dry-run
```

## Estrutura do Projeto

```
pkg-resume-activity-runrun/
├── config/settings.py       # Configurações e variáveis de ambiente
├── runrun/
│   ├── client.py            # Cliente HTTP base (auth, paginação, retry)
│   ├── time_worked.py       # Busca tempo trabalhado por usuário/dia
│   ├── tasks.py             # Busca detalhes de tarefas
│   ├── comments.py          # Busca comentários feitos pelo usuário
│   └── bulletin.py          # Publica no mural do time
├── resume/
│   ├── builder.py           # Orquestra coleta e monta o resumo
│   └── formatter.py         # Formata em markdown para o mural
├── tests/                   # Testes unitários
└── main.py                  # Entry point
```

## Testes

```bash
pytest tests/ -v
```

## Automação (opcional)

Para rodar automaticamente todo dia ao fim do expediente, adicione ao cron:

```bash
# Executa às 18h todo dia útil
0 18 * * 1-5 cd /caminho/para/pkg-resume-activity-runrun && python main.py
```
