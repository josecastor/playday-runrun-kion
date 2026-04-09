import calendar
import logging
from dataclasses import dataclass, field
from datetime import date

from runrun.client import RunrunClient
from runrun.time_worked import get_time_worked, get_time_worked_range
from runrun.tasks import get_task
from runrun.comments import get_my_comments_for_task

logger = logging.getLogger(__name__)


@dataclass
class TaskSummary:
    task_id: int
    task_code: str
    title: str
    project: str
    board_stage: str
    time_worked_day_seconds: int    # segundos trabalhados no dia
    time_worked_total_seconds: int  # segundos acumulados na tarefa
    time_worked_day_str: str        # ex: "1h 30min"
    time_worked_total_str: str      # ex: "12h 45min"
    comments: list[str] = field(default_factory=list)


@dataclass
class DailySummary:
    target_date: date
    user_id: str
    tasks: list[TaskSummary] = field(default_factory=list)
    total_day_seconds: int = 0
    total_day_str: str = ""


def _seconds_to_str(seconds: int) -> str:
    """Converte segundos em string legível. Ex: 5400 -> '1h 30min'"""
    if seconds <= 0:
        return "—"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}min"
    elif hours:
        return f"{hours}h"
    else:
        return f"{minutes}min"


def build_daily_summary(
    client: RunrunClient,
    user_id: str,
    target_date: date,
) -> DailySummary:
    """
    Orquestra todas as chamadas à API e monta o DailySummary do dia.

    Fonte de dados:
      - /work_periods  → quais tarefas e quanto tempo no dia (fonte de verdade)
      - /tasks/:id     → detalhes da tarefa (título, projeto, tempo total)
      - /tasks/:id/comments → comentários feitos pelo usuário no dia
    """
    summary = DailySummary(target_date=target_date, user_id=user_id)

    # Passo 1: work_periods — fonte de verdade de quem trabalhou no quê
    time_entries = get_time_worked(client, user_id, target_date)

    if not time_entries:
        logger.info("Nenhuma atividade com tempo registrado encontrada para o dia.")
        summary.total_day_str = "—"
        return summary

    # Passo 2: para cada tarefa, busca detalhes e comentários
    for entry in time_entries:
        task_id = entry["task_id"]

        # Busca detalhes da tarefa (título, projeto, tempo total acumulado)
        task_data = get_task(client, task_id)
        if not task_data:
            logger.warning(f"Não foi possível obter detalhes da tarefa #{task_id}, pulando.")
            continue

        title = task_data.get("title") or "Sem título"
        project = task_data.get("project") or "—"
        board_stage = task_data.get("board_stage") or "—"

        # Tempo total acumulado vem do /tasks/:id
        total_seconds = task_data.get("time_worked_total") or 0

        # Comentários feitos pelo usuário na data alvo
        comments = get_my_comments_for_task(client, task_id, user_id, target_date)

        day_seconds = entry["time_worked_day"]

        task_summary = TaskSummary(
            task_id=task_id,
            task_code=f"#{task_id}",
            title=title,
            project=project,
            board_stage=board_stage,
            time_worked_day_seconds=day_seconds,
            time_worked_total_seconds=total_seconds,
            time_worked_day_str=_seconds_to_str(day_seconds),
            time_worked_total_str=_seconds_to_str(total_seconds),
            comments=comments,
        )

        summary.tasks.append(task_summary)
        summary.total_day_seconds += day_seconds

    summary.total_day_str = _seconds_to_str(summary.total_day_seconds)

    logger.info(
        f"Resumo montado: {len(summary.tasks)} tarefa(s), "
        f"tempo no dia: {summary.total_day_str}"
    )
    return summary


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

    failed_task_ids: set[int] = set()
    task_cache: dict[int, dict] = {}

    for entry in time_entries:
        task_id = entry["task_id"]
        day = entry["day"]
        day_seconds = entry["time_worked_day"]

        if task_id in failed_task_ids:
            continue

        if task_id not in task_cache:
            try:
                task_data = get_task(client, task_id)
            except LookupError:
                logger.warning(f"Tarefa #{task_id} não encontrada, pulando.")
                failed_task_ids.add(task_id)
                continue
            if not task_data:
                logger.warning(f"Não foi possível obter detalhes da tarefa #{task_id}, pulando.")
                failed_task_ids.add(task_id)
                continue
            task_cache[task_id] = task_data

        task_data = task_cache[task_id]
        title = task_data.get("title") or "Sem título"
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
