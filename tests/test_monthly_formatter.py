import unittest
from datetime import date

from resume.builder import MonthlyTaskEntry, MonthlySummary
from resume.formatter import format_monthly_for_bulletin


def make_entry(
    day=date(2026, 3, 5),
    task_id=101,
    title="Tarefa Teste",
    project="Proj",
    time_seconds=3600,
    time_str="1h",
):
    return MonthlyTaskEntry(
        day=day,
        task_id=task_id,
        task_code=f"#{task_id}",
        title=title,
        project=project,
        board_stage="Em andamento",
        time_worked_day_seconds=time_seconds,
        time_worked_day_str=time_str,
    )


class TestFormatMonthlyForBulletin(unittest.TestCase):

    def test_empty_month(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[], total_month_seconds=0, total_month_str="—",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("Nenhuma atividade registrada", result)
        self.assertIn("Março/2026", result)

    def test_single_entry(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[make_entry()],
            total_month_seconds=3600, total_month_str="1h",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("05/03", result)
        self.assertIn("#101", result)
        self.assertIn("Tarefa Teste", result)
        self.assertIn("Proj", result)
        self.assertIn("1h", result)
        self.assertIn("Total do mês: 1h", result)
        self.assertIn("Março/2026", result)

    def test_multiple_days(self):
        entries = [
            make_entry(day=date(2026, 3, 1), task_id=200, title="T200", time_str="2h"),
            make_entry(day=date(2026, 3, 1), task_id=201, title="T201", time_str="30min"),
            make_entry(day=date(2026, 3, 15), task_id=202, title="T202", time_str="1h 15min"),
        ]
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=entries,
            total_month_seconds=12300, total_month_str="3h 25min",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("01/03", result)
        self.assertIn("15/03", result)
        self.assertIn("#200", result)
        self.assertIn("#201", result)
        self.assertIn("#202", result)
        self.assertIn("Total do mês: 3h 25min", result)

    def test_same_task_different_days(self):
        entries = [
            make_entry(day=date(2026, 3, 1), task_id=300, title="Recorrente", time_str="1h"),
            make_entry(day=date(2026, 3, 5), task_id=300, title="Recorrente", time_str="2h"),
        ]
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=entries,
            total_month_seconds=10800, total_month_str="3h",
        )
        result = format_monthly_for_bulletin(summary)
        lines = result.split("\n")
        data_rows = [l for l in lines if l.startswith("| 0")]
        self.assertEqual(len(data_rows), 2)
        self.assertIn("01/03", data_rows[0])
        self.assertIn("05/03", data_rows[1])

    def test_header_columns(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[make_entry()],
            total_month_seconds=3600, total_month_str="1h",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("| Dia", result)
        self.assertIn("| Tarefa", result)
        self.assertIn("| Descrição", result)
        self.assertIn("| Projeto", result)
        self.assertIn("| Tempo Dia", result)

    def test_user_name_displayed(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[], total_month_seconds=0, total_month_str="—",
        )
        result = format_monthly_for_bulletin(summary, user_name="Jose Castor")
        self.assertIn("Jose Castor", result)
        self.assertNotIn("jose-castor", result)

    def test_user_id_fallback_when_no_name(self):
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[], total_month_seconds=0, total_month_str="—",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("jose-castor", result)

    def test_escapes_pipe_in_title(self):
        entry = make_entry(title="Fix | bug")
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[entry],
            total_month_seconds=3600, total_month_str="1h",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("Fix \\| bug", result)

    def test_escapes_pipe_in_project(self):
        entry = make_entry(project="Projeto | X")
        summary = MonthlySummary(
            year=2026, month=3, user_id="jose-castor",
            entries=[entry],
            total_month_seconds=3600, total_month_str="1h",
        )
        result = format_monthly_for_bulletin(summary)
        self.assertIn("Projeto \\| X", result)

    def test_month_names_portuguese(self):
        """Verifica que cada mes tem o nome correto em portugues."""
        month_names = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
        }
        for month_num, month_name in month_names.items():
            summary = MonthlySummary(
                year=2026, month=month_num, user_id="u",
                entries=[], total_month_seconds=0, total_month_str="—",
            )
            result = format_monthly_for_bulletin(summary)
            self.assertIn(f"{month_name}/2026", result, f"Falhou para mes {month_num}")


if __name__ == "__main__":
    unittest.main()
