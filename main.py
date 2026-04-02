"""
pkg-resume-activity-runrun
--------------------------
Gera um resumo das atividades trabalhadas no Runrun.it
e publica automaticamente no mural do time configurado.

Uso:
    python main.py                          # usa ontem (padrão), todos os usuários
    python main.py --date 2026-03-25        # data específica
    python main.py --dry-run                # exibe o resumo sem publicar
    python main.py --user-id jose-castor    # processa apenas um usuário específico
"""

import argparse
import logging
import sys
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resumo diário Runrun.it",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py                          # resume de ontem (padrão), todos os usuários
  python main.py --date 2026-03-25        # data específica
  python main.py --dry-run                # visualiza sem publicar no mural
  python main.py --user-id jose-castor    # processa apenas este usuário
  python main.py --date 2026-03-25 --dry-run
        """
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Data do resumo (padrão: ontem).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exibe o resumo no terminal sem publicar no mural",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        metavar="USER_ID",
        help="Processa apenas este usuário (padrão: todos os usuários configurados).",
    )
    return parser.parse_args()


def process_user(user_cfg: dict, target_date: date, dry_run: bool) -> None:
    """Gera e (opcionalmente) publica o resumo de um único usuário."""
    from runrun.client import RunrunClient
    from runrun.users import get_user_name
    from resume.builder import build_daily_summary
    from resume.formatter import format_for_bulletin
    from runrun.bulletin import post_to_team_bulletin

    user_id = user_cfg["user_id"]
    app_key = user_cfg["app_key"]
    user_token = user_cfg["user_token"]
    bulletin_team_id = user_cfg.get("bulletin_team_id", "")

    logger.info(f"Gerando resumo — usuário: {user_id} | data: {target_date}")

    client = RunrunClient(app_key=app_key, user_token=user_token)

    user_name = get_user_name(client, user_id)
    logger.info(f"Nome: {user_name}")

    summary = build_daily_summary(client, user_id, target_date)
    bulletin_text = format_for_bulletin(summary, user_name=user_name)

    print("\n" + "=" * 60)
    print(bulletin_text)
    print("=" * 60 + "\n")

    if dry_run:
        logger.info(f"[{user_id}] Modo dry-run: resumo NÃO publicado no mural.")
        return

    if not bulletin_team_id:
        logger.error(
            f"[{user_id}] bulletin_team_id não configurado. "
            "Use --dry-run para apenas visualizar."
        )
        return

    post_to_team_bulletin(
        client, bulletin_team_id, bulletin_text,
        app_key=app_key, user_token=user_token,
    )
    logger.info(f"[{user_id}] Concluído!")


def main():
    args = parse_args()

    try:
        from config.settings import get_users
        users = get_users()
    except EnvironmentError as e:
        logger.error(str(e))
        logger.error("Configure RUNRUN_USERS ou o arquivo .env e tente novamente.")
        sys.exit(1)

    # Define a data alvo — padrão é ontem
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error(f"Formato de data inválido: '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = date.today() - timedelta(days=1)

    if target_date > date.today():
        logger.error(f"Data '{target_date}' é no futuro. Informe uma data passada.")
        sys.exit(1)

    # Filtra por usuário específico se --user-id foi passado
    if args.user_id:
        users = [u for u in users if u["user_id"] == args.user_id]
        if not users:
            logger.error(f"Usuário '{args.user_id}' não encontrado na configuração.")
            sys.exit(1)

    logger.info(f"Processando {len(users)} usuário(s) para {target_date}.")

    errors = []
    for user_cfg in users:
        try:
            process_user(user_cfg, target_date, args.dry_run)
        except Exception as e:
            logger.error(f"[{user_cfg['user_id']}] Erro: {e}")
            errors.append(user_cfg["user_id"])

    if errors:
        logger.error(f"Falha em {len(errors)} usuário(s): {', '.join(errors)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
