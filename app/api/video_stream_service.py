import asyncio
import hashlib
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiofiles
from cachetools import TTLCache
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.core.runtime.paths import default_recordings_dir

from .video_stream_utils import (
    STREAM_CHUNK_SIZE,
    InvalidByteRangeError,
    InvalidVideoPathError,
    file_sender_range,
    parse_range_header,
    resolve_video_path,
)

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
CUSTOM_VIDEO_ROOT_DIR = os.getenv("CUSTOM_VIDEO_ROOT_DIR")
VIDEO_API_PORT = os.getenv("VIDEO_API_PORT") or 6007

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_VIDEO_ROOT_DIR = default_recordings_dir
VIDEO_DIR = Path(CUSTOM_VIDEO_ROOT_DIR or DEFAULT_VIDEO_ROOT_DIR)
os.makedirs(VIDEO_DIR, exist_ok=True)

VIDEO_META_CACHE = TTLCache(maxsize=50, ttl=300)
PLAYER_EMBED_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "cross-origin",
}

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not VIDEO_DIR.exists():
        logger.error(f"Video directory does not exist: {VIDEO_DIR}")
        raise RuntimeError(f"Video directory does not exist: {VIDEO_DIR}")
    _app.mount("/api/videos", StaticFiles(directory=VIDEO_DIR), name="videos")
    yield

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    _app.mount("/api/videos", StaticFiles(directory=None))
    logger.info("Shutting down the application.")


app = FastAPI(lifespan=lifespan)


@app.get("/api/player", response_class=HTMLResponse)
async def stream_player(
    stream_url: str = Query(...),
    stream_type: str = Query(..., pattern="^(m3u8|flv)$"),
):
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Stream Preview</title>
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      background: #000;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    #player {{
      width: 100%;
      height: 100%;
      background: #000;
      object-fit: contain;
    }}
    #error {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 24px;
      color: #fff;
      background: rgba(0, 0, 0, 0.82);
      text-align: center;
      line-height: 1.5;
      font-size: 14px;
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/flv.js@1.6.2/dist/flv.min.js"></script>
</head>
<body>
  <video
    id="player"
    controls
    autoplay
    playsinline
    webkit-playsinline="true"
    x5-playsinline="true"
    x5-video-player-type="h5"
    x5-video-player-fullscreen="true"
  ></video>
  <div id="error"></div>
  <script>
    const streamUrl = {json.dumps(stream_url)};
    const streamType = {json.dumps(stream_type)};
    const video = document.getElementById("player");
    const errorBox = document.getElementById("error");
    let playerInstance = null;

    function showError(message) {{
      errorBox.textContent = message;
      errorBox.style.display = "flex";
    }}

    async function tryPlay() {{
      try {{
        await video.play();
      }} catch (_error) {{
        video.muted = true;
        try {{
          await video.play();
        }} catch (_mutedError) {{
          showError("Autoplay blocked. Tap play to continue.");
        }}
      }}
    }}

    function destroyPlayer() {{
      try {{
        if (playerInstance && typeof playerInstance.destroy === "function") {{
          playerInstance.destroy();
        }}
      }} catch (_error) {{
        // Ignore cleanup errors in the embedded player page.
      }}
    }}

    async function initPlayer() {{
      if (streamType === "m3u8") {{
        if (video.canPlayType("application/vnd.apple.mpegurl")) {{
          video.src = streamUrl;
          await tryPlay();
          return;
        }}

        if (window.Hls && window.Hls.isSupported()) {{
          playerInstance = new Hls({{
            enableWorker: true,
            lowLatencyMode: true,
          }});
          playerInstance.loadSource(streamUrl);
          playerInstance.attachMedia(video);
          playerInstance.on(Hls.Events.MANIFEST_PARSED, tryPlay);
          playerInstance.on(Hls.Events.ERROR, (_event, data) => {{
            if (data && data.fatal) {{
              showError("HLS playback failed.");
            }}
          }});
          return;
        }}

        showError("This browser does not support HLS playback.");
        return;
      }}

      if (streamType === "flv") {{
        if (window.flvjs && window.flvjs.isSupported()) {{
          playerInstance = flvjs.createPlayer({{
            type: "flv",
            url: streamUrl,
            isLive: true,
          }});
          playerInstance.attachMediaElement(video);
          playerInstance.load();
          try {{
            await playerInstance.play();
          }} catch (_error) {{
            video.muted = true;
            try {{
              await playerInstance.play();
            }} catch (_mutedError) {{
              showError("FLV autoplay blocked. Tap play to continue.");
            }}
          }}
          return;
        }}

        showError("This browser does not support FLV playback.");
        return;
      }}

      showError("Unsupported stream type.");
    }}

    window.addEventListener("beforeunload", destroyPlayer);
    initPlayer();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html, headers=PLAYER_EMBED_HEADERS)


@app.get("/api/videos")
async def get_video(request: Request, filename: str = Query(...), subfolder: str | None = None):

    cache_key = f"{filename}-{subfolder}"
    if meta := VIDEO_META_CACHE.get(cache_key):
        if_none_match = request.headers.get("If-None-Match")
        if_modified_since = request.headers.get("If-Modified-Since")

        if if_none_match and if_none_match == meta["etag"]:
            return Response(status_code=304)

        if if_modified_since:
            last_modified = datetime.fromisoformat(meta["last_modified"])
            if datetime.strptime(if_modified_since, "%a, %d %b %Y %H:%M:%S GMT") >= last_modified:
                return Response(status_code=304)

    try:
        video_path = resolve_video_path(VIDEO_DIR, filename, subfolder)
    except InvalidVideoPathError as exc:
        logger.warning("Invalid video path: %s/%s", subfolder, filename)
        raise HTTPException(status_code=400, detail="Invalid file path") from exc

    if not video_path.is_file():
        logger.error(f"File not found: {video_path}")
        raise HTTPException(status_code=404, detail="Video file not found")

    stat = video_path.stat()
    file_size = stat.st_size
    last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
    etag = hashlib.md5(f"{file_size}-{last_modified}".encode()).hexdigest()

    VIDEO_META_CACHE[cache_key] = {"etag": etag, "last_modified": last_modified, "file_size": file_size}

    # Parse Range header
    range_header = request.headers.get("Range")
    if range_header:
        try:
            start, end = parse_range_header(range_header, file_size)
        except InvalidByteRangeError as exc:
            raise HTTPException(
                status_code=416,
                detail="Requested range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            ) from exc

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(
            file_sender_range(video_path, start, end),
            status_code=206,
            headers=headers,
        )

    # If no Range header, return the whole file
    headers = {
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=300",
        "ETag": etag,
        "Last-Modified": datetime.fromisoformat(last_modified).strftime("%a, %d %b %Y %H:%M:%S GMT"),
    }
    try:
        return StreamingResponse(file_sender(video_path), headers=headers)
    except Exception:
        logger.exception("Streaming error")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Async file sender (full content)
async def file_sender(video_path: Path):
    async with aiofiles.open(video_path, "rb") as file:
        while True:
            chunk = await file.read(STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(VIDEO_API_PORT), log_level="debug")
