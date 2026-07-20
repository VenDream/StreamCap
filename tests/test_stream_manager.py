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
        self.run_coro = AsyncMock()
        self.snapshot_bridges = lambda: []
        self.process_manager = SimpleNamespace(add_process=lambda *_args, **_kwargs: None)
        self.output_dir = output_dir


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


if __name__ == "__main__":
    unittest.main()
