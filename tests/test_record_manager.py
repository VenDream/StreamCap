import asyncio
import unittest
from contextlib import suppress
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.core.platforms.platform_handlers import StreamData
from app.core.recording.record_manager import RecordingManager
from app.models.recording.recording_model import Recording
from app.models.recording.recording_status_model import RecordingStatus


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


class LiveStatusValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_stream_without_record_url_does_not_enter_recording_state(self):
        settings = SimpleNamespace(
            user_config={"language": "zh_CN"},
            get_video_save_path=Mock(return_value="/tmp"),
        )
        services = SimpleNamespace(
            settings_config=settings,
            recording_enabled=True,
            run_coro=Mock(),
            broadcast_card_update=Mock(),
            broadcast_pubsub=Mock(),
            snapshot_bridges=lambda: [],
            tray_manager=None,
        )
        manager = RecordingManager.__new__(RecordingManager)
        manager.services = services
        manager.settings = settings
        manager.active_recorders = {}
        manager.platform_semaphores = {"douyu": asyncio.Semaphore(1)}
        manager.loop_time_seconds = 180
        manager._ = {
            "OD": "Original",
            "live_room": "Live Room",
            "is_live": "Live",
            "notify": "Notify",
            "live_recording_started_message": "Recording started",
            "push_content": "[room_name] [time] [title]",
        }
        manager.check_free_space = AsyncMock()

        recording = Recording(
            rec_id="douyu-no-url",
            url="https://www.douyu.com/8722582",
            streamer_name="惹妹Libra",
            record_format="flv",
            quality="OD",
            segment_record=True,
            segment_time="3600",
            monitor_status=True,
            scheduled_recording=False,
            scheduled_start_time=None,
            monitor_hours=None,
            recording_dir=None,
            enabled_message_push=False,
            only_notify_no_record=False,
            flv_use_direct_download=False,
        )
        recording.platform = "斗鱼直播"
        recording.platform_key = "douyu"
        recording.showed_checking_status = True
        stream_info = StreamData(
            anchor_name="惹妹Libra",
            is_live=True,
            title="今天是7分主播~",
            live_url=recording.url,
        )
        recorder = SimpleNamespace(
            fetch_stream=AsyncMock(return_value=stream_info),
            _get_record_url=Mock(return_value=None),
            start_recording=Mock(),
        )

        message_pusher = SimpleNamespace(should_push_message=Mock(return_value=False))
        with (
            patch("app.core.recording.record_manager.LiveStreamRecorder", return_value=recorder),
            patch("app.core.recording.record_manager.message_pusher.MessagePusher", return_value=message_pusher),
            patch("app.core.recording.record_manager.desktop_notify.should_push_notification", return_value=False),
        ):
            await manager.check_if_live(recording)

        assert recording.is_recording is False
        assert recording.is_live is False
        assert recording.status_info == RecordingStatus.LIVE_STATUS_CHECK_ERROR
        recorder.start_recording.assert_not_called()


if __name__ == "__main__":
    unittest.main()
