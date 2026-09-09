import asyncio
import unittest
from contextlib import suppress
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.ui.components.business.recording_card import RecordingCardManager
from main import handle_connect, handle_disconnect


class TaskPage:
    def __init__(self):
        self.started_tasks = []

    def run_task(self, handler, *args, **kwargs):
        task = asyncio.create_task(handler(*args, **kwargs))
        self.started_tasks.append(task)
        return task


class RecordingCardManagerTests(unittest.IsolatedAsyncioTestCase):
    def _make_manager(self, page, recordings=None):
        manager = RecordingCardManager.__new__(RecordingCardManager)
        manager.app = SimpleNamespace(
            is_web_mode=True,
            page=page,
            record_manager=SimpleNamespace(recordings=recordings or []),
        )
        manager.cards_obj = {}
        manager.update_duration_tasks = {}
        return manager

    async def test_update_duration_exits_and_is_removed_when_web_session_is_dead(self):
        page = TaskPage()
        manager = self._make_manager(page)
        recording = SimpleNamespace(rec_id="recording-1", is_recording=False)
        manager.cards_obj[recording.rec_id] = {}

        async def sleep_immediately(_delay):
            return None

        with (
            patch(
                "app.ui.components.business.recording_card.utils.is_web_session_alive",
                return_value=False,
            ),
            patch(
                "app.ui.components.business.recording_card.asyncio.sleep",
                side_effect=sleep_immediately,
            ),
        ):
            assert manager.start_update_task(recording) is True
            task = manager.update_duration_tasks[recording.rec_id]
            await asyncio.wait_for(task, timeout=0.1)

        assert task.done()
        assert recording.rec_id not in manager.update_duration_tasks

    async def test_cancel_update_tasks_cancels_tasks_and_clears_registry(self):
        manager = self._make_manager(TaskPage())
        release = asyncio.Event()

        async def wait_for_release():
            await release.wait()

        task = asyncio.create_task(wait_for_release())
        manager.update_duration_tasks["recording-1"] = task

        assert manager.cancel_update_tasks() == 1
        assert manager.update_duration_tasks == {}

        with suppress(asyncio.CancelledError):
            await task
        assert task.cancelled()

    def test_start_update_task_does_not_replace_running_task(self):
        page = TaskPage()
        page.run_task = Mock(return_value=SimpleNamespace(done=lambda: False))
        manager = self._make_manager(page)
        recording = SimpleNamespace(rec_id="recording-1", is_recording=False)
        existing_task = SimpleNamespace(done=lambda: False)
        manager.update_duration_tasks[recording.rec_id] = existing_task

        assert manager.start_update_task(recording) is False
        assert manager.update_duration_tasks[recording.rec_id] is existing_task
        page.run_task.assert_not_called()

    def test_restart_update_tasks_only_restarts_visible_recordings(self):
        page = TaskPage()
        page.run_task = Mock(return_value=Mock(done=Mock(return_value=False)))
        recording_1 = SimpleNamespace(rec_id="recording-1", is_recording=False)
        recording_2 = SimpleNamespace(rec_id="recording-2", is_recording=False)
        hidden_recording = SimpleNamespace(rec_id="hidden-recording", is_recording=False)
        manager = self._make_manager(page, [recording_1, recording_2, hidden_recording])
        manager.cards_obj = {recording_1.rec_id: {}, recording_2.rec_id: {}}

        assert manager.restart_update_tasks() == 2
        assert set(manager.update_duration_tasks) == {recording_1.rec_id, recording_2.rec_id}
        assert page.run_task.call_count == 2


class WebConnectionHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_disconnect_cancels_duration_tasks_and_unregisters_bridge(self):
        card_manager = SimpleNamespace(cancel_update_tasks=Mock(return_value=3))
        services = SimpleNamespace(unregister_ui_bridge=Mock())
        app = SimpleNamespace(
            record_card_manager=card_manager,
            settings=SimpleNamespace(user_config={}),
            config_manager=SimpleNamespace(save_user_config=AsyncMock()),
            services=services,
        )
        page = SimpleNamespace(
            pubsub=SimpleNamespace(unsubscribe_all=Mock()),
            route="/recordings",
        )

        await handle_disconnect(page, app)(None)

        card_manager.cancel_update_tasks.assert_called_once_with()
        page.pubsub.unsubscribe_all.assert_called_once_with()
        app.config_manager.save_user_config.assert_awaited_once_with(app.settings.user_config)
        services.unregister_ui_bridge.assert_called_once_with(app)
        assert app.settings.user_config["last_route"] == "/recordings"

    async def test_handle_connect_restarts_duration_tasks(self):
        card_manager = SimpleNamespace(restart_update_tasks=Mock(return_value=2))
        app = SimpleNamespace(record_card_manager=card_manager)

        await handle_connect(SimpleNamespace(), app)(None)

        card_manager.restart_update_tasks.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
