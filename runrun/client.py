import time
import logging
from typing import Any

import requests

from config import settings

logger = logging.getLogger(__name__)


class RunrunClient:
    """
    Cliente base para a API do Runrun.it.
    Gerencia autenticação, rate limit (429) e paginação automática.
    """

    BASE_URL = settings.API_BASE_URL
    MAX_RETRIES = 3
    RATE_LIMIT_WAIT = 61  # segundos de espera ao receber 429

    def __init__(self, app_key: str = None, user_token: str = None):
        if app_key is None or user_token is None:
            credentials = settings.get_credentials()
            app_key = app_key or credentials["app_key"]
            user_token = user_token or credentials["user_token"]
        self._session = requests.Session()
        self._session.headers.update({
            "App-Key": app_key,
            "User-Token": user_token,
            "Content-Type": "application/json",
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        for attempt in range(1, self.MAX_RETRIES + 1):
            response = self._session.request(method, url, **kwargs)

            if response.status_code == 429:
                wait = int(response.headers.get("RateLimit-Reset", self.RATE_LIMIT_WAIT))
                logger.warning(f"Rate limit atingido. Aguardando {wait}s antes de retentar...")
                time.sleep(wait)
                continue

            if response.status_code == 401:
                raise PermissionError("Credenciais inválidas (401). Verifique App-Key e User-Token.")

            if response.status_code == 404:
                raise LookupError(f"Recurso não encontrado (404): {url}")

            response.raise_for_status()
            return response

        raise RuntimeError(f"Falha após {self.MAX_RETRIES} tentativas: {url}")

    def get(self, endpoint: str, params: dict = None) -> list[Any] | dict[str, Any]:
        """
        Realiza GET com paginação automática.
        Se a resposta for uma lista, segue os headers Link rel='next' até o fim.
        """
        all_results = []
        url = endpoint
        current_params = params or {}

        while True:
            response = self._request("GET", url, params=current_params)
            data = response.json()

            if isinstance(data, list):
                all_results.extend(data)
            else:
                return data  # resposta única (ex: show task)

            # Verifica se há próxima página
            next_url = self._parse_next_link(response.headers.get("Link", ""))
            if not next_url:
                break

            # Na próxima iteração usa a URL direta sem params (já embutidos no Link)
            url = next_url.replace(self.BASE_URL, "")
            current_params = {}

        return all_results

    def post(self, endpoint: str, body: dict) -> dict[str, Any]:
        response = self._request("POST", endpoint, json=body)
        return response.json()

    @staticmethod
    def _parse_next_link(link_header: str) -> str | None:
        """
        Extrai a URL do rel='next' do header Link.
        Exemplo: </api/v1.0/tasks?page=2>; rel="next"
        """
        if not link_header:
            return None
        for part in link_header.split(","):
            part = part.strip()
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                return url
        return None
