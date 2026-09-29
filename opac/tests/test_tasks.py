# coding: utf-8

from unittest.mock import Mock, patch

from webapp import tasks

from .base import BaseTestCase


class TasksTestCase(BaseTestCase):
    @patch("webapp.tasks.Scheduler")
    @patch("webapp.tasks.Queue")
    @patch("webapp.tasks.Redis")
    def test_get_scheduler_builds_queue_and_scheduler(
        self, mock_redis_cls, mock_queue_cls, mock_scheduler_cls
    ):
        redis_conn = Mock(name="redis_conn")
        queue = Mock(name="queue")
        scheduler = Mock(name="scheduler")
        mock_redis_cls.return_value = redis_conn
        mock_queue_cls.return_value = queue
        mock_scheduler_cls.return_value = scheduler

        result = tasks.get_scheduler("mailing")

        mock_redis_cls.assert_called_once_with(**self.app.config["RQ_REDIS_SETTINGS"])
        mock_queue_cls.assert_called_once_with("mailing", connection=redis_conn)
        mock_scheduler_cls.assert_called_once_with(queue=queue, connection=redis_conn)
        self.assertIs(result, scheduler)

    @patch("webapp.tasks.get_scheduler")
    def test_setup_scheduler_registers_cron_job(self, mock_get_scheduler):
        scheduler = Mock()
        mock_get_scheduler.return_value = scheduler
        task_function = Mock(name="task_function")
        original_timeout = self.app.config.get("DEFAULT_SCHEDULER_TIMEOUT")
        self.app.config["DEFAULT_SCHEDULER_TIMEOUT"] = 42

        try:
            tasks.setup_scheduler(task_function, "mailing", "0 7 * * *")
        finally:
            self.app.config["DEFAULT_SCHEDULER_TIMEOUT"] = original_timeout

        mock_get_scheduler.assert_called_once_with("mailing")
        scheduler.cron.assert_called_once_with(
            "0 7 * * *",
            func=task_function,
            queue_name="mailing",
            timeout=42,
        )

    @patch("webapp.tasks.get_scheduler")
    def test_setup_scheduler_uses_explicit_timeout(self, mock_get_scheduler):
        scheduler = Mock()
        mock_get_scheduler.return_value = scheduler
        task_function = Mock(name="task_function")

        tasks.setup_scheduler(task_function, "mailing", "0 0 * * 6", timeout=3600)

        scheduler.cron.assert_called_once_with(
            "0 0 * * 6",
            func=task_function,
            queue_name="mailing",
            timeout=3600,
        )

    @patch("webapp.tasks.get_scheduler")
    def test_clear_scheduler_cancels_only_jobs_from_queue(self, mock_get_scheduler):
        scheduler = Mock()
        matching_job = Mock(id="job-1", origin="mailing")
        other_job = Mock(id="job-2", origin="other")
        scheduler.get_jobs.return_value = [matching_job, other_job]
        mock_get_scheduler.return_value = scheduler

        with patch("builtins.print") as mock_print:
            tasks.clear_scheduler("mailing")

        mock_get_scheduler.assert_called_once_with("mailing")
        scheduler.get_jobs.assert_called_once_with()
        scheduler.cancel.assert_called_once_with(matching_job)
        mock_print.assert_called_once_with("removendo job job-1 do scheduler")

    @patch("webapp.tasks.get_scheduler")
    def test_clear_scheduler_does_nothing_when_no_matching_jobs(
        self, mock_get_scheduler
    ):
        scheduler = Mock()
        scheduler.get_jobs.return_value = [Mock(id="job-2", origin="other")]
        mock_get_scheduler.return_value = scheduler

        with patch("builtins.print") as mock_print:
            tasks.clear_scheduler("mailing")

        scheduler.cancel.assert_not_called()
        mock_print.assert_not_called()

    @patch("webapp.tasks.get_scheduler")
    def test_clear_scheduler_with_empty_job_list(self, mock_get_scheduler):
        scheduler = Mock()
        scheduler.get_jobs.return_value = []
        mock_get_scheduler.return_value = scheduler

        tasks.clear_scheduler("mailing")

        scheduler.cancel.assert_not_called()
