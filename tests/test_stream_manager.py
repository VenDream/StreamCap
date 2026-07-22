import asyncio
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.recording.stream_manager import LiveStreamRecorder


class StubLanguageManager:
    def __init__(self):
        self.language = {
            "recording_manager": {"live_room": "Live Room", "status_notify": "Status Notify"},
            "stream_manager": {},
        }

    def add_observer(self, *_args, **_kwargs):
        return None


class StubServices:
    def __init__(self, output_dir):
        self.settings_config = SimpleNamespace(
            user_config={},
            accounts_config={},
            cookies_config={},
        )
        self.language_manager = StubLanguageManager()
        self.subprocess_start_up_info = None
        self.recording_manager = SimpleNamespace()
        self.recording_enabled = True
        self.run_coro = AsyncMock()
        self.snapshot_bridges = lambda: []
        self.process_manager = SimpleNamespace(add_process=lambda *_args, **_kwargs: None)
        self.broadcast_card_update = lambda *_args, **_kwargs: None
        self.broadcast_pubsub = lambda *_args, **_kwargs: None
        self.broadcast_snack = lambda *_args, **_kwargs: None
        self.output_dir = output_dir


class StubProcess:
    def __init__(self):
        self.returncode = None
        self.stdin = None
        self.stderr = asyncio.StreamReader()
        self.stderr.feed_eof()

    def kill(self):
        self.returncode = -9

    async def wait(self):
        return self.returncode


class LiveStreamRecorderTests(unittest.TestCase):
    def test_set_preview_url_uses_video_api_external_scheme_in_services_mode(self):
        with tempfile.TemporaryDirectory() as output_dir:
            services = StubServices(output_dir)
            recording = SimpleNamespace(
                streamer_name="主播",
                preview_url=None,
                flv_use_direct_download=False,
                recording_dir=None,
            )
            recording_info = {
                "platform": "bilibili",
                "platform_key": "bilibili",
                "live_url": "https://example.com/room",
                "output_dir": output_dir,
                "quality": "source",
                "save_format": "mp4",
                "segment_record": False,
            }
            stream_info = SimpleNamespace(m3u8_url="http://example.com/live.m3u8", flv_url=None)

            with patch.dict("os.environ", {"VIDEO_API_EXTERNAL_URL": "https://proxy.example.com"}):
                recorder = LiveStreamRecorder(services, recording, recording_info)
                recorder.set_preview_url(stream_info)

            assert recording.preview_url == "https://example.com/live.m3u8"

    def test_set_preview_url_prefers_huya_record_url(self):
        with tempfile.TemporaryDirectory() as output_dir:
            services = StubServices(output_dir)
            recording = SimpleNamespace(
                streamer_name="主播",
                preview_url=None,
                flv_use_direct_download=False,
                recording_dir=None,
            )
            recording_info = {
                "platform": "huya",
                "platform_key": "huya",
                "live_url": "https://www.huya.com/136829",
                "output_dir": output_dir,
                "quality": "source",
                "save_format": "mp4",
                "segment_record": False,
            }
            stream_info = SimpleNamespace(
                m3u8_url="http://tx.hls.huya.com/live.m3u8?token=abc",
                flv_url="http://tx.flv.huya.com/live.flv?token=abc",
                record_url="http://tx.flv.huya.com/live.flv?token=abc",
            )

            recorder = LiveStreamRecorder(services, recording, recording_info)
            recorder.set_preview_url(stream_info)

            assert recording.preview_url == "http://tx.flv.huya.com/live.flv?token=abc"

    def test_set_preview_url_falls_back_to_record_url_when_bilibili_has_no_hls_or_flv(self):
        with tempfile.TemporaryDirectory() as output_dir:
            services = StubServices(output_dir)
            recording = SimpleNamespace(
                streamer_name="主播",
                preview_url=None,
                flv_use_direct_download=False,
                recording_dir=None,
            )
            recording_info = {
                "platform": "bilibili",
                "platform_key": "bilibili",
                "live_url": "https://live.bilibili.com/5472071",
                "output_dir": output_dir,
                "quality": "source",
                "save_format": "mp4",
                "segment_record": False,
            }
            stream_info = SimpleNamespace(
                m3u8_url=None,
                flv_url=None,
                record_url="http://example.com/live.flv?token=abc",
            )

            with patch.dict("os.environ", {"VIDEO_API_EXTERNAL_URL": "https://proxy.example.com"}):
                recorder = LiveStreamRecorder(services, recording, recording_info)
                recorder.set_preview_url(stream_info)

            assert recording.preview_url == "https://example.com/live.flv?token=abc"


class StreamTailCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_stream_tail_drains_stream_and_keeps_bounded_tail(self):
        stream = asyncio.StreamReader()
        payload = b"a" * 5000 + b"stderr-tail"
        stream.feed_data(payload)
        stream.feed_eof()

        result = await LiveStreamRecorder._capture_stream_tail(stream, max_bytes=1024)

        assert result == payload[-1024:]


class RecordingLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_ffmpeg_releases_active_recorder_when_loop_raises(self):
        with tempfile.TemporaryDirectory() as output_dir:
            services = StubServices(output_dir)
            recording = SimpleNamespace(
                rec_id="douyu-repro",
                is_recording=False,
                force_stop=False,
                status_info=None,
                record_url=None,
                speed="",
            )
            active_recorders = {}

            def stop_recording(current_recording):
                current_recording.is_recording = False

            services.recording_manager = SimpleNamespace(
                active_recorders=active_recorders,
                stop_recording=stop_recording,
            )

            recorder = LiveStreamRecorder.__new__(LiveStreamRecorder)
            recorder.services = services
            recorder.recording = recording
            recorder.subprocess_start_info = None
            recorder.should_stop = False
            recorder._ = {"no_ffmpeg_tip": "FFmpeg error"}
            active_recorders[recording.rec_id] = recorder

            process = StubProcess()
            with (
                patch(
                    "app.core.recording.stream_manager.asyncio.create_subprocess_exec",
                    new=AsyncMock(return_value=process),
                ),
                patch.object(
                    LiveStreamRecorder,
                    "_resolve_current_output_file",
                    side_effect=OSError("injected file probe failure"),
                ),
            ):
                result = await recorder.start_ffmpeg(
                    "Douyu repro",
                    "https://www.douyu.com/repro",
                    "https://example.invalid/live.flv",
                    ["ffmpeg", "/tmp/douyu-repro.ts"],
                    "ts",
                )

            assert result is False
            assert recording.is_recording is False
            assert recording.speed == ""
            assert recording.record_url is None
            assert recording.rec_id not in active_recorders

    async def test_stale_recorder_cleanup_does_not_clear_new_recording_state(self):
        with tempfile.TemporaryDirectory() as output_dir:
            services = StubServices(output_dir)
            recording = SimpleNamespace(
                rec_id="douyu-repro",
                is_recording=True,
                record_url="https://example.invalid/new-live.flv",
                speed="512.0 KB/s",
            )
            recorder = LiveStreamRecorder.__new__(LiveStreamRecorder)
            recorder.services = services
            recorder.recording = recording
            recorder._runtime_state_released = False
            new_recorder = object()
            services.recording_manager = SimpleNamespace(
                active_recorders={recording.rec_id: new_recorder},
            )

            cleaned = await recorder._cleanup_recording_runtime_state()

            assert cleaned is False
            assert services.recording_manager.active_recorders[recording.rec_id] is new_recorder
            assert recording.is_recording is True
            assert recording.record_url == "https://example.invalid/new-live.flv"
            assert recording.speed == "512.0 KB/s"

    async def test_recording_runtime_cleanup_is_idempotent(self):
        with tempfile.TemporaryDirectory() as output_dir:
            services = StubServices(output_dir)
            recording = SimpleNamespace(
                rec_id="douyu-repro",
                is_recording=True,
                force_stop=True,
                record_url="https://example.invalid/live.flv",
                speed="512.0 KB/s",
            )
            recorder = LiveStreamRecorder.__new__(LiveStreamRecorder)
            recorder.services = services
            recorder.recording = recording
            recorder._runtime_state_released = False
            services.recording_manager = SimpleNamespace(
                active_recorders={recording.rec_id: recorder},
            )

            first_cleanup = await recorder._cleanup_recording_runtime_state()
            second_cleanup = await recorder._cleanup_recording_runtime_state()

            assert first_cleanup is True
            assert second_cleanup is False
            assert recording.rec_id not in services.recording_manager.active_recorders
            assert recording.is_recording is False
            assert recording.force_stop is False
            assert recording.record_url is None
            assert recording.speed == ""


if __name__ == "__main__":
    unittest.main()
