import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from resume.builder import (
    build_monthly_summary,
    MonthlyTaskEntry,
    MonthlySummary,
    _seconds_to_str,
)


class TestBuildMonthlySummary(unittest.TestCase):

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_empty_month(self, mock_task, mock_range):
        mock_range.return_value = []
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertIsInstance(summary, MonthlySummary)
        self.assertEqual(summary.year, 2026)
        self.assertEqual(summary.month, 3)
        self.assertEqual(summary.user_id, "jose-castor")
        self.assertEqual(summary.entries, [])
        self.assertEqual(summary.total_month_seconds, 0)
        self.assertEqual(summary.total_month_str, "—")
        mock_task.assert_not_called()

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_single_entry(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 101, "day": date(2026, 3, 5), "time_worked_day": 3600},
        ]
        mock_task.return_value = {
            "id": 101,
            "title": "Fix login",
            "project": "Web",
            "board_stage": "Em andamento",
            "time_worked_total": 7200,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 1)
        entry = summary.entries[0]
        self.assertIsInstance(entry, MonthlyTaskEntry)
        self.assertEqual(entry.day, date(2026, 3, 5))
        self.assertEqual(entry.task_id, 101)
        self.assertEqual(entry.task_code, "#101")
        self.assertEqual(entry.title, "Fix login")
        self.assertEqual(entry.project, "Web")
        self.assertEqual(entry.board_stage, "Em andamento")
        self.assertEqual(entry.time_worked_day_seconds, 3600)
        self.assertEqual(entry.time_worked_day_str, "1h")
        self.assertEqual(summary.total_month_seconds, 3600)
        self.assertEqual(summary.total_month_str, "1h")

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_multiple_days_total(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 200, "day": date(2026, 3, 1), "time_worked_day": 3600},
            {"task_id": 201, "day": date(2026, 3, 1), "time_worked_day": 1800},
            {"task_id": 200, "day": date(2026, 3, 3), "time_worked_day": 900},
        ]
        mock_task.side_effect = lambda client, task_id: {
            "id": task_id,
            "title": f"Tarefa {task_id}",
            "project": "Proj",
            "board_stage": "Doing",
            "time_worked_total": 0,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 3)
        self.assertEqual(summary.total_month_seconds, 3600 + 1800 + 900)
        self.assertEqual(summary.total_month_str, _seconds_to_str(6300))

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_entries_sorted_by_day_then_task_id(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 302, "day": date(2026, 3, 10), "time_worked_day": 600},
            {"task_id": 300, "day": date(2026, 3, 5), "time_worked_day": 600},
            {"task_id": 301, "day": date(2026, 3, 5), "time_worked_day": 600},
        ]
        mock_task.side_effect = lambda client, task_id: {
            "id": task_id,
            "title": f"T{task_id}",
            "project": "P",
            "board_stage": "X",
            "time_worked_total": 0,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        keys = [(e.day, e.task_id) for e in summary.entries]
        self.assertEqual(keys, [
            (date(2026, 3, 5), 300),
            (date(2026, 3, 5), 301),
            (date(2026, 3, 10), 302),
        ])

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_get_task_lookup_error_skips_entry(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 400, "day": date(2026, 3, 5), "time_worked_day": 3600},
            {"task_id": 401, "day": date(2026, 3, 5), "time_worked_day": 1800},
        ]

        def side_effect(client, task_id):
            if task_id == 400:
                raise LookupError("Tarefa nao encontrada")
            return {
                "id": 401,
                "title": "OK Task",
                "project": "Proj",
                "board_stage": "Done",
                "time_worked_total": 0,
            }

        mock_task.side_effect = side_effect
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 1)
        self.assertEqual(summary.entries[0].task_id, 401)
        self.assertEqual(summary.total_month_seconds, 1800)

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_get_task_empty_dict_skips_entry(self, mock_task, mock_range):
        mock_range.return_value = [
            {"task_id": 500, "day": date(2026, 3, 5), "time_worked_day": 3600},
        ]
        mock_task.return_value = {}
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 0)
        self.assertEqual(summary.total_month_seconds, 0)
        self.assertEqual(summary.total_month_str, "—")

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_date_range_covers_full_month(self, mock_task, mock_range):
        """Verifica que get_time_worked_range e chamado com dia 1 e ultimo dia do mes."""
        mock_range.return_value = []
        client = MagicMock()

        build_monthly_summary(client, "jose-castor", 2026, 2)

        mock_range.assert_called_once_with(client, "jose-castor", date(2026, 2, 1), date(2026, 2, 28))

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_date_range_leap_year_february(self, mock_task, mock_range):
        """Fevereiro em ano bissexto termina no dia 29."""
        mock_range.return_value = []
        client = MagicMock()

        build_monthly_summary(client, "jose-castor", 2028, 2)

        mock_range.assert_called_once_with(client, "jose-castor", date(2028, 2, 1), date(2028, 2, 29))

    @patch("resume.builder.get_time_worked_range")
    @patch("resume.builder.get_task")
    def test_caches_task_details(self, mock_task, mock_range):
        """Mesma tarefa em dias diferentes nao deve fazer get_task duplicado."""
        mock_range.return_value = [
            {"task_id": 600, "day": date(2026, 3, 1), "time_worked_day": 1800},
            {"task_id": 600, "day": date(2026, 3, 3), "time_worked_day": 900},
        ]
        mock_task.return_value = {
            "id": 600,
            "title": "Repeated",
            "project": "P",
            "board_stage": "X",
            "time_worked_total": 0,
        }
        client = MagicMock()

        summary = build_monthly_summary(client, "jose-castor", 2026, 3)

        self.assertEqual(len(summary.entries), 2)
        mock_task.assert_called_once_with(client, 600)


if __name__ == "__main__":
    unittest.main()
