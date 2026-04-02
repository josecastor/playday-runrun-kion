import logging

from runrun.client import RunrunClient

logger = logging.getLogger(__name__)


def get_task(client: RunrunClient, task_id: int) -> dict:
    """
    Retorna detalhes de uma tarefa pelo ID.

    Campos retornados:
      - id: int
      - title: str
      - project: str
      - board_stage: str
      - time_worked_total: int (segundos acumulados na tarefa)
    """
    logger.debug(f"Buscando detalhes da tarefa #{task_id}...")
    data = client.get(f"/tasks/{task_id}")

    if not isinstance(data, dict):
        logger.warning(f"Resposta inesperada para tarefa #{task_id}")
        return {}

    return {
        "id": data.get("id", task_id),
        "title": data.get("title", ""),
        "project": data.get("project_name") or data.get("project", {}).get("title") or "—",
        "board_stage": data.get("board_stage_name") or data.get("board_stage", {}).get("name") or "—",
        "time_worked_total": int(data.get("time_worked") or 0),
    }
