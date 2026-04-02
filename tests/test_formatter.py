import unittest
from datetime import date

from resume.builder import DailySummary, TaskSummary
from resume.formatter import format_for_bulletin


def make_task(task_id=1, title="Tarefa Teste", project="Proj", time_str="1h", comments=None):
    return TaskSummary(
        task_id=task_id,
        task_code=f"#{task_id}",
        title=title,
        project=project,
        board_stage="Em andamento",
        time_worked_seconds=3600,
        time_worked_str=time_str,
        comments=comments or [],
    )


class TestFormatter(unittest.TestCase):

    def test_format_empty_summary(self):
        summary = DailySummary(target_date=date(2026, 3, 26), user_id="jose-castor")
        result = format_for_bulletin(summary)
        self.assertIn("Nenhuma atividade registrada", result)
        self.assertIn("26/03/2026", result)

    def test_format_with_tasks(self):
        summary = DailySummary(
            target_date=date(2026, 3, 26),
            user_id="jose-castor",
            tasks=[make_task(101, "Implementar login", "Projeto X", "1h 30min", ["Ajustei validacao"])],
            total_time_seconds=5400,
            total_time_str="1h 30min",
        )
        result = format_for_bulletin(summary)
        self.assertIn("26/03/2026", result)
        self.assertIn("#101", result)
        self.assertIn("Implementar login", result)
        self.assertIn("Projeto X", result)
        self.assertIn("1h 30min", result)
        self.assertIn("Ajustei validacao", result)
        self.assertIn("Total trabalhado: 1h 30min", result)

    def test_format_task_without_comments(self):
        summary = DailySummary(
            target_date=date(2026, 3, 26),
            user_id="jose-castor",
            tasks=[make_task(200, "Sem comentarios", "Proj", "30min", [])],
            total_time_seconds=1800,
            total_time_str="30min",
        )
        result = format_for_bulletin(summary)
        self.assertIn("| — |", result)

    def test_format_escapes_pipe_in_title(self):
        task = make_task(300, "Tarefa com | pipe no titulo", "Proj")
        summary = DailySummary(
            target_date=date(2026, 3, 26),
            user_id="jose-castor",
            tasks=[task],
            total_time_seconds=3600,
            total_time_str="1h",
        )
        result = format_for_bulletin(summary)
        self.assertIn("\\|", result)

    def test_format_multiple_comments(self):
        task = make_task(400, "Multi", "Proj", "1h", ["Comentario 1", "Comentario 2"])
        summary = DailySummary(
            target_date=date(2026, 3, 26),
            user_id="jose-castor",
            tasks=[task],
            total_time_seconds=3600,
            total_time_str="1h",
        )
        result = format_for_bulletin(summary)
        self.assertIn("Comentario 1 \u00b7 Comentario 2", result)

    def test_format_header_contains_table_columns(self):
        summary = DailySummary(
            target_date=date(2026, 3, 26),
            user_id="jose-castor",
            tasks=[make_task()],
            total_time_seconds=3600,
            total_time_str="1h",
        )
        result = format_for_bulletin(summary)
        self.assertIn("| Tarefa |", result)
        self.assertIn("| Tempo |", result)
        self.assertIn("| Comentários |", result)


if __name__ == "__main__":
    unittest.main()
