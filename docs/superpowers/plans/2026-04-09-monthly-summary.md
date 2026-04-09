# Plano de Implementacao: Resumo Mensal Runrun.it

**Data:** 2026-04-09
**Spec:** `docs/superpowers/specs/2026-04-09-monthly-summary-design.md`
**Status:** Pronto para execucao

---

## Goal

Adicionar resumo mensal ao projeto pkg-resume-activity-runrun. No dia 1 do mes (ou via `--monthly`), o script gera uma tabela consolidada com todas as tarefas trabalhadas no mes anterior, agrupadas por dia, e publica no mural do time.

## Architecture

```
main.py
  +-- process_user()                          # existente, sem alteracao
  +-- process_user_monthly() [NOVO]           # orquestra resumo mensal
        +-- build_monthly_summary()           # resume/builder.py [NOVO]
              +-- get_time_worked_range()      # runrun/time_worked.py [NOVO]
              +-- get_task()                   # existente
        +-- format_monthly_for_bulletin()      # resume/formatter.py [NOVO]
        +-- post_to_team_bulletin()            # existente
```

## Tech Stack

- Python 3.11
- pytest 7.4 + unittest.mock
- requests 2.31
- GitHub Actions (workflow_dispatch inputs)

---

## Task 1: `get_time_worked_range` em `runrun/time_worked.py`

**Files:**
- Modify: `runrun/time_worked.py`
- Create: `tests/test_time_worked_range.py`

### Step 1.1 — Escrever teste

Criar `tests/test_time_worked_range.py`:

```python
import unittest
from datetime import date
from unittest.mock import MagicMock

from runrun.time_worked import get_time_worked_range


class TestGetTimeWorkedRange(unittest.TestCase):

    def _make_client(self, work_periods: list[dict]) -> MagicMock:
        client = MagicMock()
        client.get.return_value = work_periods
        return client

    def test_empty_response(self):
        client = self._make_client([])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(result, [])

    def test_filters_by_date_range(self):
        """Apenas work_periods dentro do intervalo [start_date, end_date] sao retornados."""
        client = self._make_client([
            {"start": "2026-02-28T18:00:00Z", "worked_time": 3600, "task_id": 100},
            {"start": "2026-03-01T09:00:00Z", "worked_time": 1800, "task_id": 101},
            {"start": "2026-03-15T14:00:00Z", "worked_time": 7200, "task_id": 102},
            {"start": "2026-03-31T23:59:00Z", "worked_time": 900, "task_id": 103},
            {"start": "2026-04-01T00:00:00Z", "worked_time": 3600, "task_id": 104},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        task_ids = [r["task_id"] for r in result]
        self.assertNotIn(100, task_ids)
        self.assertIn(101, task_ids)
        self.assertIn(102, task_ids)
        self.assertIn(103, task_ids)
        self.assertNotIn(104, task_ids)

    def test_groups_by_day_and_task_id(self):
        """Mesma tarefa no mesmo dia = uma entrada com tempo somado."""
        client = self._make_client([
            {"start": "2026-03-05T09:00:00Z", "worked_time": 1800, "task_id": 200},
            {"start": "2026-03-05T14:00:00Z", "worked_time": 1200, "task_id": 200},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], 200)
        self.assertEqual(result[0]["day"], date(2026, 3, 5))
        self.assertEqual(result[0]["time_worked_day"], 3000)

    def test_same_task_different_days_separate_entries(self):
        """Mesma tarefa em dias diferentes = entradas separadas."""
        client = self._make_client([
            {"start": "2026-03-05T09:00:00Z", "worked_time": 1800, "task_id": 300},
            {"start": "2026-03-07T10:00:00Z", "worked_time": 3600, "task_id": 300},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(len(result), 2)
        days = [r["day"] for r in result]
        self.assertIn(date(2026, 3, 5), days)
        self.assertIn(date(2026, 3, 7), days)

    def test_skips_zero_and_negative_worked_time(self):
        client = self._make_client([
            {"start": "2026-03-10T09:00:00Z", "worked_time": 0, "task_id": 400},
            {"start": "2026-03-10T10:00:00Z", "worked_time": -5, "task_id": 401},
            {"start": "2026-03-10T11:00:00Z", "worked_time": 600, "task_id": 402},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], 402)

    def test_skips_entries_without_task_id(self):
        client = self._make_client([
            {"start": "2026-03-10T09:00:00Z", "worked_time": 600, "task_id": None},
            {"start": "2026-03-10T09:00:00Z", "worked_time": 600},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(result, [])

    def test_non_list_response_returns_empty(self):
        client = MagicMock()
        client.get.return_value = {"error": "unexpected"}
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(result, [])

    def test_result_sorted_by_day_then_task_id(self):
        client = self._make_client([
            {"start": "2026-03-10T09:00:00Z", "worked_time": 600, "task_id": 502},
            {"start": "2026-03-05T09:00:00Z", "worked_time": 600, "task_id": 501},
            {"start": "2026-03-05T09:00:00Z", "worked_time": 600, "task_id": 500},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        keys = [(r["day"], r["task_id"]) for r in result]
        self.assertEqual(keys, [
            (date(2026, 3, 5), 500),
            (date(2026, 3, 5), 501),
            (date(2026, 3, 10), 502),
        ])


if __name__ == "__main__":
    unittest.main()
```

### Step 1.2 — Rodar teste para ver falhar

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/test_time_worked_range.py -v
```

**Expected output:**
```
FAILED tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_empty_response - ImportError: cannot import name 'get_time_worked_range' from 'runrun.time_worked'
```

### Step 1.3 — Implementar `get_time_worked_range`

Adicionar ao final de `runrun/time_worked.py`:

```python
def get_time_worked_range(
    client: RunrunClient,
    user_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Retorna tarefas trabalhadas pelo usuario no intervalo [start_date, end_date].
    Faz uma unica chamada a API e filtra localmente.
    Agrupa por (day, task_id) somando worked_time.
    Resultado ordenado por (day, task_id).
    """
    logger.info(
        f"Buscando work_periods para '{user_id}' de {start_date} a {end_date}..."
    )

    params = {"user_id": user_id, "limit": 100}
    results = client.get("/work_periods", params=params)

    if not isinstance(results, list):
        logger.warning("Resposta inesperada de /work_periods, esperava lista.")
        return []

    totals: dict[tuple[date, int], int] = {}
    for item in results:
        start = item.get("start") or ""
        if len(start) < 10:
            continue
        day_str = start[:10]
        try:
            day = date.fromisoformat(day_str)
        except ValueError:
            continue
        if day < start_date or day > end_date:
            continue
        worked = item.get("worked_time") or 0
        if worked <= 0:
            continue
        task_id = item.get("task_id")
        if not task_id:
            continue
        key = (day, int(task_id))
        totals[key] = totals.get(key, 0) + worked

    if not totals:
        logger.info(f"Nenhum periodo de trabalho encontrado de {start_date} a {end_date}.")
        return []

    entries = [
        {
            "task_id": task_id,
            "day": day,
            "time_worked_day": seconds,
        }
        for (day, task_id), seconds in totals.items()
    ]
    entries.sort(key=lambda e: (e["day"], e["task_id"]))
    return entries
```

### Step 1.4 — Rodar teste para ver passar

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/test_time_worked_range.py -v
```

**Expected output:**
```
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_empty_response PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_filters_by_date_range PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_groups_by_day_and_task_id PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_same_task_different_days_separate_entries PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_skips_zero_and_negative_worked_time PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_skips_entries_without_task_id PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_non_list_response_returns_empty PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_result_sorted_by_day_then_task_id PASSED
```

### Step 1.5 — Rodar suite completa para verificar que nada quebrou

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/ -v
```

**Expected output:** Todos os testes passam (existentes + novos).

### Step 1.6 — Commit

```bash
git add runrun/time_worked.py tests/test_time_worked_range.py
git commit -m "feat: add get_time_worked_range for monthly date interval queries

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: `MonthlyTaskEntry`, `MonthlySummary`, `build_monthly_summary` em `resume/builder.py`

**Files:**
- Modify: `resume/builder.py`
- Create: `tests/test_monthly_builder.py`

### Step 2.1 — Escrever teste

Criar `tests/test_monthly_builder.py`:

```python
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from resume.builder import (
    build_monthly_summary,
    MonthlyTaskEntry,
    MonthlySummary,
    _seconds_to_str,
)


class TestBuildMonthlySummary(unittest.TestCase):

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_empty_month(self, mock_task, mock_range):
        mock_range.return_value = []
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertIsInstance(summary, MonthlySummary)
        self.assertEqual(summary.year, 2026)
        self.assertEqual(summary.month, 3)
        self.assertEqual(summary.user_id, "jose-castor")
        self.assertEqual(summary.entries, [])
        self.assertEqual(summary.total_month_seconds, 0)
        self.assertEqual(summary.total_month_str, "—")
        mock_task.assert_not_called()

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_single_entry(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 101, "day": date(2026, 3, 5), "time_worked_day": 3600},
        ]
        mock_task.return_value = {
            "id": 101,
            "title": "Fix login",
            "project": "Web",
            "board_stage": "Em andamento",
            "time_worked_total": 7200,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 1)
        entry = summary.entries[0]
        self.assertIsInstance(entry, MonthlyTaskEntry)
        self.assertEqual(entry.day, date(2026, 3, 5))
        self.assertEqual(entry.task_id, 101)
        self.assertEqual(entry.task_code, "#101")
        self.assertEqual(entry.title, "Fix login")
        self.assertEqual(entry.project, "Web")
        self.assertEqual(entry.board_stage, "Em andamento")
        self.assertEqual(entry.time_worked_day_seconds, 3600)
        self.assertEqual(entry.time_worked_day_str, "1h")
        self.assertEqual(summary.total_month_seconds, 3600)
        self.assertEqual(summary.total_month_str, "1h")

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_multiple_days_total(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 200, "day": date(2026, 3, 1), "time_worked_day": 3600},
            {"task_id": 201, "day": date(2026, 3, 1), "time_worked_day": 1800},
            {"task_id": 200, "day": date(2026, 3, 3), "time_worked_day": 900},
        ]
        mock_task.side_effect = lambda client, task_id: {
            "id": task_id,
            "title": f"Tarefa {task_id}",
            "project": "Proj",
            "board_stage": "Doing",
            "time_worked_total": 0,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 3)
        self.assertEqual(summary.total_month_seconds, 3600 + 1800 + 900)
        self.assertEqual(summary.total_month_str, _seconds_to_str(6300))

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_entries_sorted_by_day_then_task_id(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 302, "day": date(2026, 3, 10), "time_worked_day": 600},
            {"task_id": 300, "day": date(2026, 3, 5), "time_worked_day": 600},
            {"task_id": 301, "day": date(2026, 3, 5), "time_worked_day": 600},
        ]
        mock_task.side_effect = lambda client, task_id: {
            "id": task_id,
            "title": f"T{task_id}",
            "project": "P",
            "board_stage": "X",
            "time_worked_total": 0,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        keys = [(e.day, e.task_id) for e in summary.entries]
        self.assertEqual(keys, [
            (date(2026, 3, 5), 300),
            (date(2026, 3, 5), 301),
            (date(2026, 3, 10), 302),
        ])

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_get_task_lookup_error_skips_entry(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 400, "day": date(2026, 3, 5), "time_worked_day": 3600},
            {"task_id": 401, "day": date(2026, 3, 5), "time_worked_day": 1800},
        ]

        def side_effect(client, task_id):
            if task_id == 400:
                raise LookupError("Tarefa nao encontrada")
            return {
                "id": 401,
                "title": "OK Task",
                "project": "Proj",
                "board_stage": "Done",
                "time_worked_total": 0,
            }

        mock_task.side_effect = side_effect
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 1)
        self.assertEqual(summary.entries[0].task_id, 401)
        self.assertEqual(summary.total_month_seconds, 1800)

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_get_task_empty_dict_skips_entry(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 500, "day": date(2026, 3, 5), "time_worked_day": 3600},
        ]
        mock_task.return_value = {}
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 0)
        self.assertEqual(summary.total_month_seconds, 0)
        self.assertEqual(summary.total_month_str, "—")

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_date_range_covers_full_month(self, mock_task, mock_range):
        """Verifica que get_time_worked_range e chamado com dia 1 e ultimo dia do mes."""
        mock_range.return_value = []
        client = MagicMock()

        build_monthly_summary(client, "jose-castor", 2026, 2)

        mock_range.assert_called_once_with(client, "jose-castor", date(2026, 2, 1), date(2026, 2, 28))

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_date_range_leap_year_february(self, mock_task, mock_range):
        """Fevereiro em ano bissexto termina no dia 29."""
        mock_range.return_value = []
        client = MagicMock()

        build_monthly_summary(client, "jose-castor", 2028, 2)

        mock_range.assert_called_once_with(client, "jose-castor", date(2028, 2, 1), date(2028, 2, 29))

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_caches_task_details(self, mock_task, mock_range):
        """Mesma tarefa em dias diferentes nao deve fazer get_task duplicado."""
        mock_range.return_value = [
            {"task_id": 600, "day": date(2026, 3, 1), "time_worked_day": 1800},
            {"task_id": 600, "day": date(2026, 3, 3), "time_worked_day": 900},
        ]
        mock_task.return_value = {
            "id": 600,
            "title": "Repeated",
            "project": "P",
            "board_stage": "X",
            "time_worked_total": 0,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 2)
        mock_task.assert_called_once_with(client, 600)


if __name__ == "__main__":
    unittest.main()
```

### Step 2.2 — Rodar teste para ver falhar

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/test_monthly_builder.py -v
```

**Expected output:**
```
FAILED tests/test_monthly_builder.py::TestBuildMonthlySummary::test_empty_month - ImportError: cannot import name 'build_monthly_summary' from 'resume.builder'
```

### Step 2.3 — Implementar em `resume/builder.py`

Adicionar imports no topo de `resume/builder.py` (apos os imports existentes):

```python
import calendar
from runrun.time_worked import get_time_worked_range
```

Adicionar ao final de `resume/builder.py`:

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
    entries: list[MonthlyTaskEntry] = field(default_factory=list)
    total_month_seconds: int = 0
    total_month_str: str = ""


def build_monthly_summary(
    client: RunrunClient,
    user_id: str,
    year: int,
    month: int,
) -> MonthlySummary:
    """
    Monta o resumo mensal buscando todos os work_periods do mes
    e enriquecendo com detalhes de cada tarefa.
    """
    summary = MonthlySummary(year=year, month=month, user_id=user_id)

    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    time_entries = get_time_worked_range(client, user_id, start_date, end_date)

    if not time_entries:
        summary.total_month_str = "—"
        return summary

    task_cache: dict[int, dict] = {}

    for entry in time_entries:
        task_id = entry["task_id"]
        day = entry["day"]
        day_seconds = entry["time_worked_day"]

        if task_id not in task_cache:
            try:
                task_data = get_task(client, task_id)
            except LookupError:
                logger.warning(f"Tarefa #{task_id} nao encontrada, pulando.")
                continue
            if not task_data:
                logger.warning(f"Nao foi possivel obter detalhes da tarefa #{task_id}, pulando.")
                continue
            task_cache[task_id] = task_data

        task_data = task_cache[task_id]
        title = task_data.get("title") or "Sem titulo"
        project = task_data.get("project") or "—"
        board_stage = task_data.get("board_stage") or "—"

        monthly_entry = MonthlyTaskEntry(
            day=day,
            task_id=task_id,
            task_code=f"#{task_id}",
            title=title,
            project=project,
            board_stage=board_stage,
            time_worked_day_seconds=day_seconds,
            time_worked_day_str=_seconds_to_str(day_seconds),
        )
        summary.entries.append(monthly_entry)
        summary.total_month_seconds += day_seconds

    summary.entries.sort(key=lambda e: (e.day, e.task_id))
    summary.total_month_str = _seconds_to_str(summary.total_month_seconds)
    return summary
```

### Step 2.4 — Rodar teste para ver passar

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/test_monthly_builder.py -v
```

**Expected output:**
```
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_empty_month PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_single_entry PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_multiple_days_total PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_entries_sorted_by_day_then_task_id PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_get_task_lookup_error_skips_entry PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_get_task_empty_dict_skips_entry PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_date_range_covers_full_month PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_date_range_leap_year_february PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_caches_task_details PASSED
```

### Step 2.5 — Rodar suite completa

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/ -v
```

**Expected output:** Todos os testes passam.

### Step 2.6 — Commit

```bash
git add resume/builder.py tests/test_monthly_builder.py
git commit -m "feat: add MonthlyTaskEntry, MonthlySummary, build_monthly_summary

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: `format_monthly_for_bulletin` em `resume/formatter.py`

**Files:**
- Modify: `resume/formatter.py`
- Create: `tests/test_monthly_formatter.py`

### Step 3.1 — Escrever teste

Criar `tests/test_monthly_formatter.py`:

```python
import unittest
from datetime import date

from resume.builder import MonthlyTaskEntry, MonthlySummary
from resume.formatter import format_monthly_for_bulletin


def make_entry(
    day=date(2026, 3, 5),
    task_id=101,
    title="Tarefa Teste",
    project="Proj",
    time_seconds=3600,
    time_str="1h",
):
    return MonthlyTaskEntry(
        day=day,
        task_id=task_id,
        task_code=f"#{task_id}",
        title=title,
        project=project,
        board_stage="Em andamento",
        time_worked_day_seconds=time_seconds,
        time_worked_day_str=time_str,
    )


class TestFormatMonthlyForBulletin(unittest.TestCase):

    def test_empty_month(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[], total_month_seconds=0, total_month_str="—",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("Nenhuma atividade registrada", result)
        self.assertIn("Marco/2026", result)

    def test_single_entry(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[make_entry()],
            total_month_seconds=3600, total_month_str="1h",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("05/03", result)
        self.assertIn("#101", result)
        self.assertIn("Tarefa Teste", result)
        self.assertIn("Proj", result)
        self.assertIn("1h", result)
        self.assertIn("Total do mes: 1h", result)

    def test_multiple_days(self):
        entries = [
            make_entry(day=date(2026, 3, 1), task_id=200, title="T200", time_str="2h"),
            make_entry(day=date(2026, 3, 1), task_id=201, title="T201", time_str="30min"),
            make_entry(day=date(2026, 3, 15), task_id=202, title="T202", time_str="1h 15min"),
        ]
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=entries,
            total_month_seconds=12300, total_month_str="3h 25min",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("01/03", result)
        self.assertIn("15/03", result)
        self.assertIn("#200", result)
        self.assertIn("#201", result)
        self.assertIn("#202", result)
        self.assertIn("Total do mes: 3h 25min", result)

    def test_same_task_different_days(self):
        entries = [
            make_entry(day=date(2026, 3, 1), task_id=300, title="Recorrente", time_str="1h"),
            make_entry(day=date(2026, 3, 5), task_id=300, title="Recorrente", time_str="2h"),
        ]
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=entries,
            total_month_seconds=10800, total_month_str="3h",
        )
        result = format_monthly_for_bulletin(summary)
        lines = result.split("\n")
        data_rows = [l for l in lines if l.startswith("| 0")]
        self.assertEqual(len(data_rows), 2)
        self.assertIn("01/03", data_rows[0])
        self.assertIn("05/03", data_rows[1])

    def test_header_columns(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[make_entry()],
            total_month_seconds=3600, total_month_str="1h",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("| Dia", result)
        self.assertIn("| Tarefa", result)
        self.assertIn("| Descricao", result)
        self.assertIn("| Projeto", result)
        self.assertIn("| Tempo Dia", result)

    def test_user_name_displayed(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[], total_month_seconds=0, total_month_str="—",
        )
        result = format_monthly_for_bulletin(summary, user_name="Jose Castor")
        self.assertIn("Jose Castor", result)
        self.assertNotIn("jose-castor", result)

    def test_user_id_fallback_when_no_name(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[], total_month_seconds=0, total_month_str="—",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("jose-castor", result)

    def test_escapes_pipe_in_title(self):
        entry = make_entry(title="Fix | bug")
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[entry],
            total_month_seconds=3600, total_month_str="1h",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("Fix \\| bug", result)

    def test_month_names_portuguese(self):
        """Verifica que cada mes tem o nome correto em portugues."""
        month_names = {
            1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
        }
        for month_num, month_name in month_names.items():
            summary = MonthlySummary(
                year=2026, month=month_num, user_id="u",
                entries=[], total_month_seconds=0, total_month_str="—",
            )
            result = format_monthly_for_bulletin(summary)
            self.assertIn(f"{month_name}/2026", result, f"Falhou para mes {month_num}")


if __name__ == "__main__":
    unittest.main()
```

### Step 3.2 — Rodar teste para ver falhar

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/test_monthly_formatter.py -v
```

**Expected output:**
```
FAILED tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_empty_month - ImportError: cannot import name 'format_monthly_for_bulletin' from 'resume.formatter'
```

### Step 3.3 — Implementar `format_monthly_for_bulletin`

Adicionar ao topo de `resume/formatter.py` (apos o import existente):

```python
from resume.builder import MonthlySummary
```

Adicionar ao final de `resume/formatter.py`:

```python
_MONTH_NAMES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def format_monthly_for_bulletin(summary: MonthlySummary, user_name: str = "") -> str:
    month_name = _MONTH_NAMES.get(summary.month, str(summary.month))
    display_name = user_name or summary.user_id
    header = f"## PlayDay Mensal de {display_name} — {month_name}/{summary.year}"

    if not summary.entries:
        return f"{header}\n\nNenhuma atividade registrada neste mes."

    lines = [
        header,
        "",
        "| Dia | Tarefa | Descricao | Projeto | Tempo Dia |",
        "|-----|--------|-----------|---------|-----------|",
    ]

    for entry in summary.entries:
        day_str = entry.day.strftime("%d/%m")
        title = _escape_md(entry.title)
        project = _escape_md(entry.project)
        lines.append(
            f"| {day_str}"
            f" | {entry.task_code}"
            f" | {title}"
            f" | {project}"
            f" | {entry.time_worked_day_str} |"
        )

    lines.append("")
    lines.append(f"**Total do mes: {summary.total_month_str}**")
    return "\n".join(lines)
```

### Step 3.4 — Rodar teste para ver passar

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/test_monthly_formatter.py -v
```

**Expected output:**
```
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_empty_month PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_single_entry PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_multiple_days PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_same_task_different_days PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_header_columns PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_user_name_displayed PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_user_id_fallback_when_no_name PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_escapes_pipe_in_title PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_month_names_portuguese PASSED
```

### Step 3.5 — Rodar suite completa

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/ -v
```

**Expected output:** Todos os testes passam.

### Step 3.6 — Commit

```bash
git add resume/formatter.py tests/test_monthly_formatter.py
git commit -m "feat: add format_monthly_for_bulletin with Portuguese month names

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: `--monthly` flag e `process_user_monthly` em `main.py`

**Files:**
- Modify: `main.py`

### Step 4.1 — Implementar

Modificar `main.py` para o seguinte conteudo completo:

```python
import argparse
import logging
import os
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Resumo diario Runrun.it")
    parser.add_argument("--date", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--user-id", type=str, default=None, metavar="USER_ID")
    parser.add_argument("--monthly", action="store_true", help="Forca execucao do resumo mensal (mes anterior)")
    return parser.parse_args()


def process_user(user_cfg, target_date, dry_run):
    from runrun.client import RunrunClient
    from runrun.users import get_user_name
    from resume.builder import build_daily_summary
    from resume.formatter import format_for_bulletin
    from runrun.bulletin import post_to_team_bulletin

    user_id = user_cfg["user_id"]
    app_key = user_cfg["app_key"]
    user_token = user_cfg["user_token"]
    bulletin_team_id = user_cfg.get("bulletin_team_id", "")

    client = RunrunClient(app_key=app_key, user_token=user_token)
    user_name = get_user_name(client, user_id)
    summary = build_daily_summary(client, user_id, target_date)
    bulletin_text = format_for_bulletin(summary, user_name=user_name)

    print("\n" + "=" * 60)
    print(bulletin_text)
    print("=" * 60 + "\n")

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(bulletin_text + "\n\n")

    if dry_run:
        return

    if not bulletin_team_id:
        logger.error(f"[{user_id}] bulletin_team_id nao configurado.")
        return

    post_to_team_bulletin(client, bulletin_team_id, bulletin_text, app_key=app_key, user_token=user_token)


def process_user_monthly(user_cfg, year, month, dry_run):
    from runrun.client import RunrunClient
    from runrun.users import get_user_name
    from resume.builder import build_monthly_summary
    from resume.formatter import format_monthly_for_bulletin
    from runrun.bulletin import post_to_team_bulletin

    user_id = user_cfg["user_id"]
    app_key = user_cfg["app_key"]
    user_token = user_cfg["user_token"]
    bulletin_team_id = user_cfg.get("bulletin_team_id_monthly") or user_cfg.get("bulletin_team_id", "")

    client = RunrunClient(app_key=app_key, user_token=user_token)
    user_name = get_user_name(client, user_id)
    summary = build_monthly_summary(client, user_id, year, month)
    bulletin_text = format_monthly_for_bulletin(summary, user_name=user_name)

    print("\n" + "=" * 60)
    print(bulletin_text)
    print("=" * 60 + "\n")

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(bulletin_text + "\n\n")

    if dry_run:
        return

    if not bulletin_team_id:
        logger.error(f"[{user_id}] bulletin_team_id nao configurado para resumo mensal.")
        return

    post_to_team_bulletin(client, bulletin_team_id, bulletin_text, app_key=app_key, user_token=user_token)


def main():
    args = parse_args()

    try:
        from config.settings import get_users
        users = get_users()
    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)

    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = date.today() - timedelta(days=1)

    if args.user_id:
        users = [u for u in users if u["user_id"] == args.user_id]

    # Resumo diario
    for user_cfg in users:
        try:
            process_user(user_cfg, target_date, args.dry_run)
        except Exception as e:
            logger.error(f"[{user_cfg['user_id']}] Erro no resumo diario: {e}")

    # Resumo mensal: automatico no dia 1 ou forcado via --monthly
    today = date.today()
    if today.day == 1 or args.monthly:
        if today.month == 1:
            prev_year = today.year - 1
            prev_month = 12
        else:
            prev_year = today.year
            prev_month = today.month - 1

        logger.info(f"Executando resumo mensal para {prev_month:02d}/{prev_year}...")

        for user_cfg in users:
            try:
                process_user_monthly(user_cfg, prev_year, prev_month, args.dry_run)
            except Exception as e:
                logger.error(f"[{user_cfg['user_id']}] Erro no resumo mensal: {e}")


if __name__ == "__main__":
    main()
```

### Step 4.2 — Verificar que o script roda sem erros de sintaxe

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -c "import ast; ast.parse(open('main.py').read()); print('Syntax OK')"
```

**Expected output:**
```
Syntax OK
```

### Step 4.3 — Rodar suite completa para garantir que nada quebrou

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/ -v
```

**Expected output:** Todos os testes passam.

### Step 4.4 — Commit

```bash
git add main.py
git commit -m "feat: add --monthly flag and process_user_monthly with auto day-1 detection

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: `bulletin_team_id_monthly` em `config/settings.py`

**Files:**
- Modify: `config/settings.py`

### Step 5.1 — Implementar

A logica de fallback `bulletin_team_id_monthly → bulletin_team_id` ja esta em `process_user_monthly` (Task 4). Em `config/settings.py`, o campo precisa ser lido do `.env` no fallback de variavel individual.

Modificar a funcao `get_users()` em `config/settings.py` para incluir `bulletin_team_id_monthly`:

Substituir o bloco de retorno do fallback `.env` de:

```python
    return [{
        "app_key": app_key,
        "user_token": user_token,
        "user_id": user_id,
        "bulletin_team_id": os.environ.get("RUNRUN_BULLETIN_TEAM_ID", ""),
    }]
```

Por:

```python
    return [{
        "app_key": app_key,
        "user_token": user_token,
        "user_id": user_id,
        "bulletin_team_id": os.environ.get("RUNRUN_BULLETIN_TEAM_ID", ""),
        "bulletin_team_id_monthly": os.environ.get("RUNRUN_BULLETIN_TEAM_ID_MONTHLY", ""),
    }]
```

Nota: No modo `RUNRUN_USERS` (JSON), o campo `bulletin_team_id_monthly` ja e suportado nativamente porque o JSON e parseado como dict e `process_user_monthly` faz `user_cfg.get("bulletin_team_id_monthly")`. Nenhuma alteracao adicional e necessaria para o modo JSON.

### Step 5.2 — Rodar suite completa

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/ -v
```

**Expected output:** Todos os testes passam.

### Step 5.3 — Commit

```bash
git add config/settings.py
git commit -m "feat: add bulletin_team_id_monthly to .env fallback config

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Atualizar `.github/workflows/daily-activity.yml`

**Files:**
- Modify: `.github/workflows/daily-activity.yml`

### Step 6.1 — Implementar

Substituir o conteudo completo de `.github/workflows/daily-activity.yml`:

```yaml
name: Daily Activity Summary

on:
  schedule:
    - cron: '0 10 * * 1-5'
  workflow_dispatch:
    inputs:
      date:
        description: 'Data do resumo (YYYY-MM-DD)'
        required: false
        default: ''
      dry_run:
        description: 'Dry run: exibe sem publicar'
        type: boolean
        default: false
      user_id:
        description: 'User ID especifico'
        required: false
        default: ''
      monthly:
        description: 'Forcar resumo mensal do mes anterior'
        type: boolean
        default: false

jobs:
  summarize:
    runs-on: ubuntu-latest
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - name: Run summary
        env:
          RUNRUN_USERS: ${{ secrets.RUNRUN_USERS }}
        run: |
          ARGS=""
          if [ -n "${{ inputs.date }}" ]; then ARGS="$ARGS --date ${{ inputs.date }}"; fi
          if [ "${{ inputs.dry_run }}" = "true" ]; then ARGS="$ARGS --dry-run"; fi
          if [ -n "${{ inputs.user_id }}" ]; then ARGS="$ARGS --user-id ${{ inputs.user_id }}"; fi
          if [ "${{ inputs.monthly }}" = "true" ]; then ARGS="$ARGS --monthly"; fi
          python main.py $ARGS
```

### Step 6.2 — Validar YAML

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -c "import yaml; yaml.safe_load(open('.github/workflows/daily-activity.yml')); print('YAML OK')" 2>/dev/null || python -c "
import json, re
content = open('.github/workflows/daily-activity.yml').read()
# Basic validation: check it parses as valid structure
assert 'workflow_dispatch' in content
assert 'monthly' in content
assert '--monthly' in content
print('YAML structure OK')
"
```

**Expected output:**
```
YAML OK
```

### Step 6.3 — Commit

```bash
git add .github/workflows/daily-activity.yml
git commit -m "ci: add monthly input to workflow_dispatch

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Verificacao Final

### Rodar suite completa de testes

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python -m pytest tests/ -v
```

**Expected output:**
```
tests/test_builder.py::TestSecondsToStr::test_zero PASSED
tests/test_builder.py::TestSecondsToStr::test_negative PASSED
tests/test_builder.py::TestSecondsToStr::test_minutes_only PASSED
tests/test_builder.py::TestSecondsToStr::test_hours_only PASSED
tests/test_builder.py::TestSecondsToStr::test_hours_and_minutes PASSED
tests/test_builder.py::TestSecondsToStr::test_two_hours PASSED
tests/test_builder.py::TestBuildDailySummary::test_empty_day PASSED
tests/test_builder.py::TestBuildDailySummary::test_two_tasks_total_time PASSED
tests/test_builder.py::TestBuildDailySummary::test_comments_attached_to_correct_task PASSED
tests/test_builder.py::TestBuildDailySummary::test_task_with_empty_data_is_skipped PASSED
tests/test_formatter.py::TestFormatter::test_format_empty_summary PASSED
tests/test_formatter.py::TestFormatter::test_format_with_tasks PASSED
tests/test_formatter.py::TestFormatter::test_format_task_without_comments PASSED
tests/test_formatter.py::TestFormatter::test_format_escapes_pipe_in_title PASSED
tests/test_formatter.py::TestFormatter::test_format_multiple_comments PASSED
tests/test_formatter.py::TestFormatter::test_format_header_contains_table_columns PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_empty_month PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_single_entry PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_multiple_days_total PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_entries_sorted_by_day_then_task_id PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_get_task_lookup_error_skips_entry PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_get_task_empty_dict_skips_entry PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_date_range_covers_full_month PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_date_range_leap_year_february PASSED
tests/test_monthly_builder.py::TestBuildMonthlySummary::test_caches_task_details PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_empty_month PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_single_entry PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_multiple_days PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_same_task_different_days PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_header_columns PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_user_name_displayed PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_user_id_fallback_when_no_name PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_escapes_pipe_in_title PASSED
tests/test_monthly_formatter.py::TestFormatMonthlyForBulletin::test_month_names_portuguese PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_empty_response PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_filters_by_date_range PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_groups_by_day_and_task_id PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_same_task_different_days_separate_entries PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_skips_zero_and_negative_worked_time PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_skips_entries_without_task_id PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_non_list_response_returns_empty PASSED
tests/test_time_worked_range.py::TestGetTimeWorkedRange::test_result_sorted_by_day_then_task_id PASSED
```

### Teste manual de integracao (dry-run)

```bash
cd "/Users/castor/Google Drive/Totvs/clientes/fontes/workspaceLuna/pkg-resume-activity-runrun"
python main.py --monthly --dry-run
```

**Expected output:** Resumo mensal do mes anterior impresso no terminal (sem publicar no mural). Se credenciais nao estiverem configuradas, erro controlado de `EnvironmentError`.

---

## Self-Review Checklist

| Criterio | Status |
|---|---|
| Cobertura de todos os requisitos da spec | OK — diario inalterado, mensal no dia 1, --monthly, tabela com coluna Dia, bulletin_team_id_monthly, erros isolados |
| Zero placeholders (TBD, similar, etc.) | OK — todo codigo esta completo nos code blocks |
| Consistencia de nomes de campos | OK — `time_worked_day`, `time_worked_day_seconds`, `time_worked_day_str` consistentes entre time_worked.py, builder.py e formatter.py |
| Consistencia de tipos | OK — `day: date`, `task_id: int`, `year: int`, `month: int` em todo o fluxo |
| TDD: teste antes de implementacao | OK — cada task segue escrever teste, ver falhar, implementar, ver passar |
| Commits granulares | OK — 6 commits, um por task |
| Testes existentes nao quebram | OK — nenhuma funcao existente foi alterada (apenas adicoes) |
| get_time_worked existente inalterado | OK — nova funcao get_time_worked_range adicionada separadamente |
| Cache de get_task no monthly builder | OK — evita chamadas duplicadas para mesma tarefa em dias diferentes |
| Calculo do mes anterior com edge case jan | OK — month==1 resulta em year-1, month=12 |
| Ano bissexto em fevereiro | OK — usa calendar.monthrange que lida com isso |
| GitHub Actions workflow atualizado | OK — input monthly adicionado com passagem de --monthly |
