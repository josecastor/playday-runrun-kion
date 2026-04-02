import logging

from runrun.client import RunrunClient

logger = logging.getLogger(__name__)


def get_user_name(client: RunrunClient, user_id: str) -> str:
    """
    Retorna o nome completo do usuário pelo ID.
    Em caso de falha, retorna o próprio user_id como fallback.
    """
    logger.debug(f"Buscando nome do usuário '{user_id}'...")
    try:
        data = client.get(f"/users/{user_id}")
        if isinstance(data, dict):
            return data.get("name") or data.get("full_name") or user_id
    except Exception as e:
        logger.warning(f"Não foi possível obter nome do usuário: {e}")
    return user_id
