# Design: Resumo Mensal Runrun.it

**Data:** 2026-04-09  
**Projeto:** pkg-resume-activity-runrun  
**Status:** Aprovado

---

## Contexto

O projeto já gera resumos diários de atividades do Runrun.it e publica no mural do time. Esta evolução adiciona um **resumo mensal** que roda automaticamente no dia 1 de cada mês (referente ao mês anterior) e também pode ser disparado manualmente via CLI e GitHub Actions.

---

## Requisitos

1. O fluxo diário existente continua funcionando sem alteração.
2. No dia 1 do mês, o script roda o diário normalmente e, em seguida, executa o resumo mensal do mês anterior.
3. O resumo mensal pode ser forçado manualmente via `--monthly` (CLI) e input `monthly` (GitHub Actions).
4. O resumo mensal lista todas as tarefas trabalhadas em cada dia do mês anterior em uma única tabela com coluna **Dia**.
5. Dias sem trabalho não aparecem na tabela.
6. O resumo mensal é publicado no `bulletin_team_id` do usuário por padrão; se `bulletin_team_id_monthly` estiver configurado, usa esse mural.

---

## Abordagem escolhida

**Uma única chamada à API** para buscar todos os `work_periods` do usuário, filtrando localmente pelo intervalo do mês anterior. Evita 20–23 chamadas por usuário e reduz risco de rate limit (429).

---

## Arquitetura

### 1. `runrun/time_worked.py` — nova função

```python
def get_time_worked_range(
    client: RunrunClient,
    user_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Retorna tarefas trabalhadas pelo usuário no intervalo [start_date, end_date].
    Faz uma única chamada à API e filtra localmente.

    Cada item retornado tem:
      - task_id: int
      - day: date           ← novo campo (dia do trabalho)
      - time_worked_day: int (segundos trabalhados naquele dia)

    Agrupamento: por (day, task_id). A mesma tarefa trabalhada em dias
    diferentes gera entradas separadas — cada uma com seu próprio 'day'.
    """
```

O `get_time_worked` existente não é alterado.

### 2. `resume/builder.py` — novos dataclasses e função

```python
@dataclass
class MonthlyTaskEntry:
    day: date
    task_id: int
    task_code: str
    title: str
    project: str
    board_stage: str
    time_worked_day_seconds: int
    time_worked_day_str: str

@dataclass
class MonthlySummary:
    year: int
    month: int
    user_id: str
    entries: list[MonthlyTaskEntry]   # ordenado por (day, task_id)
    total_month_seconds: int
    total_month_str: str

def build_monthly_summary(
    client: RunrunClient,
    user_id: str,
    year: int,
    month: int,
) -> MonthlySummary:
    """
    Orquestra busca e montagem do MonthlySummary.
    Usa get_time_worked_range para o intervalo dia 1 ao último dia do mês.
    Para cada entry, busca detalhes da tarefa via get_task (título, projeto, board_stage).
    Não busca comentários (muito volume para visão mensal).
    """
```

### 3. `resume/formatter.py` — nova função

```python
def format_monthly_for_bulletin(summary: MonthlySummary, user_name: str = "") -> str:
    """
    Formata o MonthlySummary em markdown.
    Colunas: Dia | Tarefa | Descrição | Projeto | Tempo Dia
    """
```

**Exemplo de saída:**
```
## 📅 PlayDay Mensal de José Castor — Março/2026

| Dia   | Tarefa | Descrição         | Projeto | Tempo Dia |
|-------|--------|-------------------|---------|-----------|
| 01/03 | #123   | Fix login button   | Web     | 2h        |
| 01/03 | #456   | Deploy staging     | Infra   | 1h        |
| 03/03 | #123   | Fix login button   | Web     | 30min     |

**⏱ Total do mês: 48h 30min**
```

### 4. `main.py` — flag `--monthly` e detecção automática

```python
# Novo argumento CLI
--monthly   # força execução do resumo mensal (mês anterior)

# Lógica
run_daily_for_all_users()
if date.today().day == 1 or args.monthly:
    run_monthly_for_all_users()   # mês anterior calculado automaticamente
```

Nova função `process_user_monthly(user_cfg, year, month, dry_run)`:
- Instancia `RunrunClient`
- Chama `build_monthly_summary`
- Chama `format_monthly_for_bulletin`
- Imprime no terminal e escreve em `GITHUB_STEP_SUMMARY`
- Publica no mural (usando `bulletin_team_id_monthly` se presente, senão `bulletin_team_id`)

### 5. `config/settings.py` — propriedade opcional

`bulletin_team_id_monthly` lido do JSON `RUNRUN_USERS` ou do `.env` (`RUNRUN_BULLETIN_TEAM_ID_MONTHLY`). Não obrigatório — fallback para `bulletin_team_id`.

### 6. `.github/workflows/daily-activity.yml` — novo input

```yaml
monthly:
  description: 'Forçar resumo mensal do mês anterior'
  type: boolean
  default: false
```

Script de execução passa `--monthly` se o input for `true`.

---

## Fluxo de execução no dia 1

```
main()
  ├── process_user(user, ontem, dry_run)         ← diário, como hoje
  │     └── build_daily_summary → format → publish
  │
  └── [day==1 or --monthly]
        └── process_user_monthly(user, mês_anterior, dry_run)
              └── build_monthly_summary → format_monthly → publish
```

---

## Tratamento de erros

- Erro no diário não impede execução do mensal (blocos `try/except` independentes).
- Erro no mensal não afeta o resultado do diário.
- `LookupError` em `get_task` → loga warning e pula a entrada (mesmo comportamento do diário).
- `bulletin_team_id` ausente → loga erro e pula publicação (não quebra o job).

---

## Testes

- `tests/test_monthly_builder.py` — cobre `build_monthly_summary` com mocks da API.
- `tests/test_monthly_formatter.py` — cobre `format_monthly_for_bulletin` com entradas variadas (mês vazio, múltiplos dias, tarefas repetidas em dias diferentes).
- `get_time_worked_range` coberto via mock do client (sem chamadas reais à API).

---

## O que não muda

- Interface de `get_time_worked` (assinatura preservada).
- `DailySummary`, `TaskSummary`, `build_daily_summary`, `format_for_bulletin` (sem alteração).
- Formato do secret `RUNRUN_USERS` (apenas `bulletin_team_id_monthly` é novo e opcional).
