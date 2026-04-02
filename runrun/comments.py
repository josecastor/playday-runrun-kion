import logging
from datetime import date

from runrun.client import RunrunClient

logger = logging.getLogger(__name__)


def get_my_comments_for_task(
    client: RunrunClient,
    task_id: int,
    user_id: str,
    target_date: date,
) -> list[str]:
    """
    Retorna lista de textos dos comentários feitos pelo usuário
    em uma tarefa específica na data alvo.

    Filtra localmente por:
      - user.id == user_id
      - created_at no mesmo dia que target_date
      - apenas comentários textuais (ignora comentários de sistema sem texto)
    """
    logger.debug(f"Buscando comentários da tarefa #{task_id}...")

    try:
        results = client.get(f"/tasks/{task_id}/comments")
    except LookupError:
        logger.warning(f"Comentários não encontrados para tarefa #{task_id}")
        return []

    if not isinstance(results, list):
        return []

    my_comments = []
    for comment in results:
        # Verifica autor
        user = comment.get("user") or {}
        if user.get("id") != user_id:
            continue

        # Verifica data
        created_at = comment.get("created_at", "")
        if not created_at.startswith(str(target_date)):
            continue

        # Verifica se tem texto (ignora comentários de sistema)
        text = (comment.get("text") or "").strip()
        if not text:
            continue

        my_comments.append(text)

    return my_comments
