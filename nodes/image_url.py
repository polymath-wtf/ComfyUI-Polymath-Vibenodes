import asyncio
import os
from io import BytesIO

import aiohttp
import numpy as np
import torch
from aiohttp import web
from comfy_api.latest import io
from PIL import Image, ImageOps, UnidentifiedImageError

from .video_url import MEDIA_TLS, download_url, public_socket, resolve_tmpfiles


def is_storage_origin(url):
    setting = os.environ.get("VIBENODE_IMAGE_STORAGE_ORIGIN", "").strip()
    if not setting:
        return False
    origin = download_url(setting)
    if origin.raw_path != "/" or origin.query_string or "#" in setting:
        raise ValueError("VIBENODE_IMAGE_STORAGE_ORIGIN must contain only scheme, host and port")
    return url.origin() == origin.origin()


async def fetch_image(url):
    target = download_url(url)
    storage = is_storage_origin(target)
    connector = aiohttp.TCPConnector(ssl=MEDIA_TLS, socket_factory=None if storage else public_socket)
    async with aiohttp.ClientSession(connector=connector, requote_redirect_url=False,
                                     timeout=aiohttp.ClientTimeout(total=90)) as session:
        if not storage:
            target = await resolve_tmpfiles(session, target)
        async with session.get(target, allow_redirects=not storage, max_redirects=5) as response:
            if storage and 300 <= response.status < 400:
                raise ValueError("Local storage returned a redirect; use a direct image URL")
            response.raise_for_status()
            if response.content_type == "text/html":
                raise ValueError("Received a web page instead of an image. Check the download link.")
            data = BytesIO()
            async for chunk in response.content.iter_chunked(65536):
                if data.tell() + len(chunk) > 64 * 1024**2:
                    raise ValueError("Image download exceeds 64 MiB")
                data.write(chunk)
            return data


def decode_image(data, preview=False):
    try:
        with Image.open(data, formats=("PNG", "JPEG", "WEBP", "GIF", "BMP", "TIFF")) as source:
            if source.width * source.height > 32_000_000:
                raise ValueError("Image exceeds 32 megapixels")
            if preview:
                source.thumbnail((512, 512))
            return ImageOps.exif_transpose(source).convert("RGBA")
    except UnidentifiedImageError as exc:
        raise ValueError("The downloaded file is not a supported image. Check the download link.") from exc


def thumbnail_png(data):
    out = BytesIO()
    decode_image(data, preview=True).save(out, "PNG")
    return out.getvalue()


async def image_preview(request):
    body = await request.json()
    if not isinstance(body, dict) or not isinstance(body.get("url"), str):
        raise web.HTTPBadRequest(text="Expected an image URL")
    try:
        data = await fetch_image(body["url"])
        png = await asyncio.to_thread(thumbnail_png, data)
    except (aiohttp.ClientError, TimeoutError, OSError, ValueError, Image.DecompressionBombError):
        raise web.HTTPBadRequest(text="Не удалось загрузить картинку. Проверь ссылку.")
    return web.Response(body=png, content_type="image/png")


class LoadImageURL(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodeLoadImageURL", display_name="Load image url", category="Vibenode",
            inputs=[io.String.Input("url", default="", tooltip="Image URL: public, tmpfiles.org or configured storage origin")],
            outputs=[io.Image.Output("image"), io.Mask.Output("mask")],
        )

    @classmethod
    async def execute(cls, url):
        rgba = decode_image(await fetch_image(url))
        pixels = torch.from_numpy(np.array(rgba)).float().div_(255).unsqueeze(0)
        return io.NodeOutput(pixels[..., :3].contiguous(), 1 - pixels[..., 3])
