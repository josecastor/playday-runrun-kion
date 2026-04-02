import logging

from runrun.client import RunrunClient

logger = logging.getLogger(__name__)

# Endpoint correto descoberto via testes — sem versão v1.0
COMMENTS_ENDPOINT = "/comments"
# Sobrescreve a base URL para usar /api em vez de /api/v1.0
COMMENTS_BASE_URL = "https://runrun.it/api"


def post_to_team_bulletin(
    client: RunrunClient, team_id: str, text: str,
    app_key: str = None, user_token: str = None,
) -> dict:
    """
    Publica um comentário no mural de um time no Runrun.it.

    Endpoint: POST https://runrun.it/api/comments
    Body: {"text": "...", "team_id": 496822}

    Args:
        client: instância do RunrunClient
        team_id: ID do time onde publicar
        text: conteúdo em markdown/texto do resumo
        app_key: App-Key do usuário (opcional, usa settings se omitido)
        user_token: User-Token do usuário (opcional, usa settings se omitido)

    Returns:
        Resposta da API com o comentário criado
    """
    import requests

    if app_key is None or user_token is None:
        from config import settings
        credentials = settings.get_credentials()
        app_key = app_key or credentials["app_key"]
        user_token = user_token or credentials["user_token"]

    url = f"{COMMENTS_BASE_URL}/comments"
    headers = {
        "App-Key": app_key,
        "User-Token": user_token,
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "team_id": int(team_id),
    }

    logger.info(f"Publicando resumo no mural do time {team_id}...")
    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 401:
        raise PermissionError("Credenciais inválidas (401). Verifique App-Key e User-Token.")
    if response.status_code == 404:
        raise LookupError(f"Time não encontrado (404): team_id={team_id}")

    response.raise_for_status()

    data = response.json()
    logger.info(f"Resumo publicado com sucesso! Comment ID: {data.get('id')}")
    return data
