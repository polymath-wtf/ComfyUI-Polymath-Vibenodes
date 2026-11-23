import importlib
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestServer
from PIL import Image
from test_creator import package


class BucketTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_get_direct_and_redirected(self):
        image = importlib.import_module(package.name + ".nodes.image_url")
        video = importlib.import_module(package.name + ".nodes.video_url")
        # GIF is a valid input for both loaders. The object key has no extension.
        payload = BytesIO()
        Image.new("RGB", (3, 2)).save(payload, "GIF")
        signed = "/bucket/a%20b%2Fc?X-Goog-Credential=test%2Fdate&X-Goog-SignedHeaders=host&X-Goog-Signature=abcd&v=%2B%3D"

        async def serve(request):
            if request.path == "/download":
                return web.Response(status=302, headers={"Location": signed})
            if request.method != "GET" or request.raw_path != signed:
                return web.Response(status=403)
            return web.Response(body=payload.getvalue(), content_type="application/octet-stream")

        app = web.Application()
        app.router.add_get("/{rest:.*}", serve)
        async with TestServer(app) as server:
            with patch.object(image, "public_socket", None), patch.object(video, "public_socket", None), \
                    tempfile.TemporaryDirectory(dir=package) as tmp:
                for path in (signed, "/download"):
                    url = str(server.make_url("/")).rstrip("/") + path
                    self.assertEqual(image.decode_image(await image.fetch_image(url)).size, (3, 2))
                    self.assertEqual((await video.fetch_video(url, Path(tmp))).read_bytes(), payload.getvalue())
