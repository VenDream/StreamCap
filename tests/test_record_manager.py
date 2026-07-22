import asyncio
import unittest
from contextlib import suppress
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.recording.record_manager import RecordingManager


class PeriodicLiveCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_periodic_check_runs_immediately_without_browser_session(self):
        manager = RecordingManager.__new__(RecordingManager)
        manager.services = SimpleNamespace(
            settings_config=SimpleNamespace(user_config={"check_live_on_browser_refresh": True}),
            recording_enabled=True,
        )
        manager.periodic_task_started = False
        manager.check_free_space = AsyncMock()
        checked = asyncio.Event()

        async def check_all_live_status():
            checked.set()

        manager.check_all_live_status = AsyncMock(side_effect=check_all_live_status)
        created_tasks = []
        create_task = asyncio.create_task

        RecordingManager.set_periodic_task_running(False)
        try:
            with patch(
                "app.core.recording.record_manager.asyncio.create_task",
                side_effect=lambda coro: created_tasks.append(create_task(coro)) or created_tasks[-1],
            ):
                await manager.setup_periodic_live_check(interval=3600)

            await asyncio.wait_for(checked.wait(), timeout=0.1)

            manager.check_free_space.assert_awaited_once_with()
            manager.check_all_live_status.assert_awaited_once_with()
        finally:
            for task in created_tasks:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            RecordingManager.set_periodic_task_running(False)


if __name__ == "__main__":
    unittest.main()
