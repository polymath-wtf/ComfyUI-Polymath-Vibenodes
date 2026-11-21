import importlib
import unittest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import av

from test_creator import nodes, package


class VideoUrlTests(unittest.TestCase):
    def test_no_lazy_audio_for_silent_clip(self):
        video = importlib.import_module(f"{package.name}.nodes.video_url")
        placeholder = object()
        class Loader:
            def load_video(self, **kwargs):
                return "frames", 1, placeholder, {"fps": 24}

        with tempfile.TemporaryDirectory(dir=package) as tmp:
            for sound in (False, True):
                file = Path(tmp) / f"{sound}.mkv"
                with av.open(str(file), "w") as clip:
                    stream = clip.add_stream("mpeg4", rate=24)
                    if sound:
                        audio = clip.add_stream("pcm_s16le", rate=8000)
                        frame = av.AudioFrame(format="s16", layout="stereo", samples=80)
                        frame.sample_rate = 8000
                        clip.mux(audio.encode(frame))
                    clip.mux(stream.encode(av.VideoFrame(stream.width, stream.height, "yuv420p")))
                    clip.mux(stream.encode())
                with patch.dict(video.nodes.NODE_CLASS_MAPPINGS, VHS_LoadVideoPath=Loader), \
                        patch.object(video.LoadVideoURL, "hidden", create=True), \
                        patch.object(video, "fetch_video", AsyncMock(return_value=file)):
                    result = asyncio.run(video.LoadVideoURL.execute("https://example.org/clip")).result
                    self.assertEqual(result, ("frames", 1, placeholder if sound else None, {"fps": 24}))

    def test_url_input_and_vhs_outputs(self):
        self.assertIn("VibenodeLoadVideoURL", nodes)
        node = nodes["VibenodeLoadVideoURL"]
        self.assertEqual(node.INPUT_TYPES()["required"]["path"][0], "STRING")
        self.assertEqual(tuple(node.RETURN_NAMES), ("IMAGE", "frame_count", "audio", "video_info"))

    def test_tmpfiles_direct_and_signed_urls(self):
        video = importlib.import_module(f"{package.name}.nodes.video_url")
        url = "https://tmpfiles.org/abc/video.mp4"
        direct = url.replace("/abc", "/dl/abc")
        parser = video.TmpfilesPage()
        parser.feed(f'<a class="download" href="{direct}">Download</a>')
        self.assertEqual(parser.href, direct)
        self.assertEqual(str(video.download_url(direct)), direct)
        signed = "https://cdn.example.org/video?sig=a%2Fb%3D"
        self.assertEqual(str(video.download_url(signed)), signed)
