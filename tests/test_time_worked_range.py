import unittest
from datetime import date
from unittest.mock import MagicMock

from runrun.time_worked import get_time_worked_range


class TestGetTimeWorkedRange(unittest.TestCase):

    def _make_client(self, work_periods: list[dict]) -> MagicMock:
        client = MagicMock()
        client.get.return_value = work_periods
        return client

    def test_empty_response(self):
        client = self._make_client([])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(result, [])

    def test_filters_by_date_range(self):
        """Apenas work_periods dentro do intervalo [start_date, end_date] sao retornados."""
        client = self._make_client([
            {"start": "2026-02-28T18:00:00Z", "worked_time": 3600, "task_id": 100},
            {"start": "2026-03-01T09:00:00Z", "worked_time": 1800, "task_id": 101},
            {"start": "2026-03-15T14:00:00Z", "worked_time": 7200, "task_id": 102},
            {"start": "2026-03-31T23:59:00Z", "worked_time": 900, "task_id": 103},
            {"start": "2026-04-01T00:00:00Z", "worked_time": 3600, "task_id": 104},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        task_ids = [r["task_id"] for r in result]
        self.assertNotIn(100, task_ids)
        self.assertIn(101, task_ids)
        self.assertIn(102, task_ids)
        self.assertIn(103, task_ids)
        self.assertNotIn(104, task_ids)

    def test_groups_by_day_and_task_id(self):
        """Mesma tarefa no mesmo dia = uma entrada com tempo somado."""
        client = self._make_client([
            {"start": "2026-03-05T09:00:00Z", "worked_time": 1800, "task_id": 200},
            {"start": "2026-03-05T14:00:00Z", "worked_time": 1200, "task_id": 200},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], 200)
        self.assertEqual(result[0]["day"], date(2026, 3, 5))
        self.assertEqual(result[0]["time_worked_day"], 3000)

    def test_same_task_different_days_separate_entries(self):
        """Mesma tarefa em dias diferentes = entradas separadas."""
        client = self._make_client([
            {"start": "2026-03-05T09:00:00Z", "worked_time": 1800, "task_id": 300},
            {"start": "2026-03-07T10:00:00Z", "worked_time": 3600, "task_id": 300},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(len(result), 2)
        days = [r["day"] for r in result]
        self.assertIn(date(2026, 3, 5), days)
        self.assertIn(date(2026, 3, 7), days)

    def test_skips_zero_and_negative_worked_time(self):
        client = self._make_client([
            {"start": "2026-03-10T09:00:00Z", "worked_time": 0, "task_id": 400},
            {"start": "2026-03-10T10:00:00Z", "worked_time": -5, "task_id": 401},
            {"start": "2026-03-10T11:00:00Z", "worked_time": 600, "task_id": 402},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], 402)

    def test_skips_entries_without_task_id(self):
        client = self._make_client([
            {"start": "2026-03-10T09:00:00Z", "worked_time": 600, "task_id": None},
            {"start": "2026-03-10T09:00:00Z", "worked_time": 600},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(result, [])

    def test_non_list_response_returns_empty(self):
        client = MagicMock()
        client.get.return_value = {"error": "unexpected"}
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(result, [])

    def test_result_sorted_by_day_then_task_id(self):
        client = self._make_client([
            {"start": "2026-03-10T09:00:00Z", "worked_time": 600, "task_id": 502},
            {"start": "2026-03-05T09:00:00Z", "worked_time": 600, "task_id": 501},
            {"start": "2026-03-05T09:00:00Z", "worked_time": 600, "task_id": 500},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        keys = [(r["day"], r["task_id"]) for r in result]
        self.assertEqual(keys, [
            (date(2026, 3, 5), 500),
            (date(2026, 3, 5), 501),
            (date(2026, 3, 10), 502),
        ])

    def test_raises_when_start_after_end(self):
        client = self._make_client([])
        with self.assertRaises(ValueError):
            get_time_worked_range(client, "jose-castor", date(2026, 3, 31), date(2026, 3, 1))

    def test_skips_entries_with_invalid_date_format(self):
        client = self._make_client([
            {"start": "not-a-date", "worked_time": 600, "task_id": 999},
            {"start": "2026-03-10T09:00:00Z", "worked_time": 600, "task_id": 100},
        ])
        result = get_time_worked_range(client, "jose-castor", date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], 100)


if __name__ == "__main__":
    unittest.main()
