import logging
from datetime import date

from runrun.client import RunrunClient

logger = logging.getLogger(__name__)


def get_time_worked(client: RunrunClient, user_id: str, target_date: date) -> list[dict]:
    """
    Retorna tarefas trabalhadas pelo usuário em uma data específica.

    Usa /work_periods?user_id=... que retorna períodos reais de trabalho
    (start, end, worked_time) por tarefa e usuário — fonte de verdade.

    Filtra localmente pelo campo 'start' que começa com a data alvo.
    Agrupa por task_id somando worked_time.

    Cada item retornado tem:
      - task_id: int
      - task_title: str (vazio — será preenchido pelo builder via /tasks)
      - time_worked_day: int  (segundos trabalhados NO DIA alvo)
      - time_worked_total: int (sempre 0 aqui — preenchido pelo builder)
      - project_name: str
      - board_stage_name: str
      - client_name: str
    """
    today = date.today()
    days_ago = (today - target_date).days

    if days_ago < 0:
        raise ValueError(
            f"Data alvo ({target_date}) é no futuro. "
            f"Informe uma data passada ou omita para usar ontem."
        )

    date_str = str(target_date)  # "2026-03-26"
    logger.info(f"Buscando work_periods para '{user_id}' em {date_str}...")

    params = {
        "user_id": user_id,
        "limit": 100,
    }

    results = client.get("/work_periods", params=params)

    if not isinstance(results, list):
        logger.warning("Resposta inesperada de /work_periods, esperava lista.")
        return []

    # Agrupa por task_id somando worked_time dos períodos do dia alvo
    totals: dict[int, int] = {}
    for item in results:
        start = item.get("start") or ""
        if not start.startswith(date_str):
            continue
        worked = item.get("worked_time") or 0
        if worked <= 0:
            continue
        task_id = item.get("task_id")
        if not task_id:
            continue
        totals[int(task_id)] = totals.get(int(task_id), 0) + worked

    if not totals:
        logger.info(f"Nenhum período de trabalho encontrado em {date_str}.")
        return []

    normalized = [
        {
            "task_id": task_id,
            "task_title": "",       # preenchido pelo builder via /tasks/:id
            "time_worked_day": seconds,
            "time_worked_total": 0, # preenchido pelo builder via /tasks/:id
            "project_name": "—",
            "board_stage_name": "—",
            "client_name": "—",
        }
        for task_id, seconds in totals.items()
    ]

    logger.info(f"Encontradas {len(normalized)} tarefa(s) com trabalho em {date_str}.")
    return normalized
