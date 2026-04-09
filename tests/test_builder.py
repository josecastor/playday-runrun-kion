import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from resume.builder import build_daily_summary, _seconds_to_str, DailySummary, TaskSummary


class TestSecondsToStr(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(_seconds_to_str(0), "—")

    def test_negative(self):
        self.assertEqual(_seconds_to_str(-10), "—")

    def test_minutes_only(self):
        self.assertEqual(_seconds_to_str(1800), "30min")

    def test_hours_only(self):
        self.assertEqual(_seconds_to_str(3600), "1h")

    def test_hours_and_minutes(self):
        self.assertEqual(_seconds_to_str(5400), "1h 30min")

    def test_two_hours(self):
        self.assertEqual(_seconds_to_str(7200), "2h")


class TestBuildDailySummary(unittest.TestCase):

    @patch("resume.builder.get_time_worked")
    @patch("resume.builder.get_task")
    @patch("resume.builder.get_my_comments_for_task")
    def test_empty_day(self, mock_comments, mock_task, mock_time):
        mock_time.return_value = []
        client = MagicMock()

        summary = build_daily_summary(client, "jose-castor", date(2026, 3, 26))

        self.assertEqual(summary.tasks, [])
        self.assertEqual(summary.total_day_seconds, 0)
        self.assertEqual(summary.total_day_str, "—")
        mock_task.assert_not_called()
        mock_comments.assert_not_called()

    @patch("resume.builder.get_time_worked")
    @patch("resume.builder.get_task")
    @patch("resume.builder.get_my_comments_for_task")
    def test_two_tasks_total_time(self, mock_comments, mock_task, mock_time):
        mock_time.return_value = [
            {"task_id": 101, "task_title": "Tarefa A", "time_worked_day": 3600},
            {"task_id": 102, "task_title": "Tarefa B", "time_worked_day": 1800},
        ]
        mock_task.side_effect = lambda client, task_id: {
            "id": task_id,
            "title": f"Tarefa {task_id}",
            "project": "Projeto X",
            "board_stage": "Em andamento",
        }
        mock_comments.return_value = []

        client = MagicMock()
        summary = build_daily_summary(client, "jose-castor", date(2026, 3, 26))

        self.assertEqual(len(summary.tasks), 2)
        self.assertEqual(summary.total_day_seconds, 5400)
        self.assertEqual(summary.total_day_str, "1h 30min")

    @patch("resume.builder.get_time_worked")
    @patch("resume.builder.get_task")
    @patch("resume.builder.get_my_comments_for_task")
    def test_comments_attached_to_correct_task(self, mock_comments, mock_task, mock_time):
        mock_time.return_value = [
            {"task_id": 101, "task_title": "Tarefa A", "time_worked_day": 3600},
            {"task_id": 102, "task_title": "Tarefa B", "time_worked_day": 1800},
        ]
        mock_task.side_effect = lambda client, task_id: {
            "id": task_id, "title": f"T{task_id}", "project": "P", "board_stage": "X"
        }
        mock_comments.side_effect = lambda client, task_id, user_id, d: (
            ["Meu comentario"] if task_id == 101 else []
        )

        client = MagicMock()
        summary = build_daily_summary(client, "jose-castor", date(2026, 3, 26))

        task_101 = next(t for t in summary.tasks if t.task_id == 101)
        task_102 = next(t for t in summary.tasks if t.task_id == 102)
        self.assertEqual(task_101.comments, ["Meu comentario"])
        self.assertEqual(task_102.comments, [])

    @patch("resume.builder.get_time_worked")
    @patch("resume.builder.get_task")
    @patch("resume.builder.get_my_comments_for_task")
    def test_task_with_empty_data_is_skipped(self, mock_comments, mock_task, mock_time):
        mock_time.return_value = [
            {"task_id": 999, "task_title": "", "time_worked_day": 3600},
        ]
        mock_task.return_value = {}  # simula falha ao buscar tarefa
        mock_comments.return_value = []

        client = MagicMock()
        summary = build_daily_summary(client, "jose-castor", date(2026, 3, 26))

        self.assertEqual(len(summary.tasks), 0)


if __name__ == "__main__":
    unittest.main()
