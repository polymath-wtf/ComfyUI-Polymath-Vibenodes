import importlib
import os
import unittest
from io import BytesIO
from unittest.mock import patch

from aiohttp import ClientConnectorError, web
from aiohttp.test_utils import TestServer
from PIL import Image

from test_creator import package

image = importlib.import_module(f"{package.name}.nodes.image_url")
SETTING = "VIBENODE_IMAGE_STORAGE_ORIGIN"


class LocalStorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        data = BytesIO()
        Image.new("RGBA", (2, 1), (255, 0, 0, 0)).save(data, "PNG")

        async def portrait(request):
            return web.Response(body=data.getvalue(), content_type="image/png")

        async def redirect(request):
            raise web.HTTPFound("/storage/ref.png")

        app = web.Application()
        app.router.add_get("/storage/ref.png", portrait)
        app.router.add_get("/redirect", redirect)
        self.server = TestServer(app)
        await self.server.start_server()
        self.addAsyncCleanup(self.server.close)
        self.origin = str(self.server.make_url("/").origin()).replace("127.0.0.1", "localhost")

    async def test_configured_laravel_url_loads_image_and_mask(self):
        with patch.dict(os.environ, {SETTING: self.origin}):
            pixels, mask = (await image.LoadImageURL.execute(self.origin + "/storage/ref.png")).result
        self.assertEqual(tuple(pixels.shape), (1, 1, 2, 3))
        self.assertEqual(mask.tolist(), [[[1.0, 1.0]]])

    async def test_unconfigured_localhost_reports_policy_error(self):
        for origin in ("", "https://localhost", "http://localhost:1"):
            with self.subTest(origin=origin), patch.dict(os.environ, {SETTING: origin}):
                with self.assertRaisesRegex(ClientConnectorError, "public server"):
                    await image.fetch_image(self.origin + "/storage/ref.png")

    async def test_storage_requires_direct_image_link(self):
        with patch.dict(os.environ, {SETTING: self.origin}):
            with self.assertRaisesRegex(ValueError, "redirect"):
                await image.fetch_image(self.origin + "/redirect")
