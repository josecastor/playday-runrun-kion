import json
import os
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv opcional — em produção as vars podem já estar no ambiente


def _require(key: str) -> str:
    """Lê uma variável obrigatória do ambiente. Falha com mensagem clara se ausente."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Variável de ambiente obrigatória não definida: '{key}'. "
            f"Configure o arquivo .env com base no .env.example."
        )
    return value


def get_credentials() -> dict:
    """
    Retorna as credenciais da API.
    Chamado apenas quando o cliente HTTP é instanciado,
    não no momento do import do módulo.
    """
    return {
        "app_key": _require("RUNRUN_APP_KEY"),
        "user_token": _require("RUNRUN_USER_TOKEN"),
    }


def get_users() -> list[dict]:
    """
    Retorna lista de configurações de usuário.

    Se RUNRUN_USERS (JSON array) estiver definido, usa ele.
    Caso contrário, constrói um único usuário a partir das envs individuais.

    Cada item da lista tem: app_key, user_token, user_id, bulletin_team_id
    """
    raw = os.getenv("RUNRUN_USERS", "").strip()
    if raw:
        try:
            users = json.loads(raw)
        except json.JSONDecodeError as e:
            raise EnvironmentError(f"RUNRUN_USERS contém JSON inválido: {e}") from e
        for i, u in enumerate(users):
            for field in ("app_key", "user_token", "user_id"):
                if not u.get(field):
                    raise EnvironmentError(
                        f"Usuário {i} em RUNRUN_USERS está sem o campo obrigatório '{field}'."
                    )
        return users

    # Fallback: modo single-user com as envs individuais
    creds = get_credentials()
    return [{
        "app_key": creds["app_key"],
        "user_token": creds["user_token"],
        "user_id": os.getenv("RUNRUN_USER_ID", "jose-castor"),
        "bulletin_team_id": os.getenv("RUNRUN_BULLETIN_TEAM_ID", ""),
    }]


# Configurações que podem ser lidas sem falhar (compatibilidade com modo single-user)
USER_ID: str = os.getenv("RUNRUN_USER_ID", "jose-castor")
BULLETIN_TEAM_ID: str = os.getenv("RUNRUN_BULLETIN_TEAM_ID", "")

# Data do resumo (padrão: hoje)
_raw_date = os.getenv("RESUME_DATE", "").strip()
RESUME_DATE: date = date.fromisoformat(_raw_date) if _raw_date else date.today()

# Base URL da API
API_BASE_URL = "https://runrun.it/api/v1.0"
