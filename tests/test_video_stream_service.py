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


if __name__ == "__main__":
    unittest.main()
