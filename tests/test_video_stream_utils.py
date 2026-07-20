import tempfile
import unittest
from pathlib import Path

from app.api.video_stream_utils import (
    InvalidByteRangeError,
    InvalidVideoPathError,
    parse_range_header,
    resolve_video_path,
)


class VideoStreamUtilsTests(unittest.TestCase):
    def test_resolve_video_path_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            try:
                resolve_video_path(Path(root), "../outside.mp4")
            except InvalidVideoPathError:
                return
            self.fail("Parent traversal should be rejected")

    def test_parse_range_header_supports_bounded_and_suffix_ranges(self):
        assert parse_range_header("bytes=2-5", 10) == (2, 5)
        assert parse_range_header("bytes=-3", 10) == (7, 9)

    def test_parse_range_header_rejects_multiple_ranges(self):
        try:
            parse_range_header("bytes=0-1,4-5", 10)
        except InvalidByteRangeError:
            return
        self.fail("Multiple ranges should be rejected")


if __name__ == "__main__":
    unittest.main()
