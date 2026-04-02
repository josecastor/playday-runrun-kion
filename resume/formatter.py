from resume.builder import DailySummary


def format_for_bulletin(summary: DailySummary, user_name: str = "") -> str:
    """
    Formata o DailySummary em markdown para o mural do Runrun.it.

    Colunas: Tarefa | Descrição | Projeto | Tempo Dia | Tempo Total | Comentários
    """
    date_str = summary.target_date.strftime("%d/%m/%Y")
    display_name = user_name or summary.user_id

    if not summary.tasks:
        return (
            f"## 🎯 PlayDay de {display_name} — {date_str}\n\n"
            f"Nenhuma atividade registrada neste dia."
        )

    lines = [
        f"## 🎯 PlayDay de {display_name} — {date_str}",
        "",
        "| Tarefa | Descrição | Projeto | Tempo Dia | Tempo Total | Comentários |",
        "|--------|-----------|---------|-----------|-------------|-------------|",
    ]

    for task in summary.tasks:
        comments_text = _format_comments(task.comments)
        title = _escape_md(task.title)
        project = _escape_md(task.project)

        lines.append(
            f"| {task.task_code}"
            f" | {title}"
            f" | {project}"
            f" | {task.time_worked_day_str}"
            f" | {task.time_worked_total_str}"
            f" | {comments_text} |"
        )

    lines.append("")
    lines.append(f"**⏱ Total do dia: {summary.total_day_str}**")

    return "\n".join(lines)


def _format_comments(comments: list[str]) -> str:
    if not comments:
        return "—"
    formatted = []
    for c in comments:
        c = _escape_md(c)
        if len(c) > 100:
            c = c[:97] + "..."
        formatted.append(c)
    return " · ".join(formatted)


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", "")
