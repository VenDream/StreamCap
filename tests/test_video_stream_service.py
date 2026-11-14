import unittest

from fastapi.testclient import TestClient

from app.api.video_stream_service import app


class VideoStreamServiceTests(unittest.TestCase):
    def test_player_page_allows_embedding_from_flet_coep_page(self):
        response = TestClient(app).get(
            "/api/player",
            params={
                "stream_url": "http://example.com/live.flv",
                "stream_type": "flv",
            },
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "*"
        assert response.headers.get("cross-origin-embedder-policy") == "require-corp"
        assert response.headers.get("cross-origin-resource-policy") == "cross-origin"

    def test_m3u8_player_prefers_hls_js_and_sets_coep_safe_attributes(self):
        response = TestClient(app).get(
            "/api/player",
            params={
                "stream_url": "https://example.com/live.m3u8",
                "stream_type": "m3u8",
            },
        )

        html = response.text
        assert response.status_code == 200
        assert '<meta name="referrer" content="no-referrer" />' in html
        assert 'crossorigin="anonymous"' in html
        assert html.index("window.Hls && window.Hls.isSupported()") < html.index(
            'video.canPlayType("application/vnd.apple.mpegurl")'
        )
        assert 'error.name === "NotAllowedError"' in html
        assert 'errorBox.addEventListener("click"' in html
        assert "playerInstance.on(Hls.Events.MANIFEST_PARSED, () => tryPlay());" in html

    def test_flv_player_handles_errors_and_uses_player_play(self):
        response = TestClient(app).get(
            "/api/player",
            params={
                "stream_url": "https://example.com/live.flv",
                "stream_type": "flv",
            },
        )

        html = response.text
        assert response.status_code == 200
        assert "flvjs.Events.ERROR" in html
        assert "await tryPlay(() => playerInstance.play());" in html


if __name__ == "__main__":
    unittest.main()
