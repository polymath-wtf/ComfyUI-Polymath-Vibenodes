import hashlib
import errno
import ipaddress
import socket
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile

import aiohttp
import av
import folder_paths
import nodes
from comfy_api.latest import io
from yarl import URL


def download_url(path):
    url = URL(path.strip(), encoded=True)
    if url.scheme not in {"http", "https"} or not url.host or url.user is not None:
        raise ValueError("Expected a public HTTP(S) URL")
    return url.with_fragment(None)


class TmpfilesPage(HTMLParser):
    href = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "download" in attrs.get("class", "").split():
            self.href = attrs.get("href")


def public_socket(addr):
    family, kind, proto, _, address = addr
    ip = ipaddress.ip_address(address[0])
    if not ip.is_global or ip.is_multicast:
        # aiohappyeyeballs collects OSError from each candidate socket.
        raise PermissionError(errno.EACCES, "URL must point to a public server")
    return socket.socket(family, kind, proto)


async def resolve_tmpfiles(session, url):
    if url.host != "tmpfiles.org":
        return url
    if url.raw_path.startswith("/dl/"):
        # /dl/id/name redirects to the page; /dl/signature/id/name serves the file.
        if len(url.raw_path.split("/")) != 4:
            return url
        url = url.with_path(url.raw_path[3:], encoded=True, keep_query=True)
    async with session.get(url, max_redirects=5) as page:
        page.raise_for_status()
        parser = TmpfilesPage()
        data = bytearray()
        async for chunk in page.content.iter_chunked(8192):
            data.extend(chunk)
            if len(data) > 262144:
                raise ValueError("Unexpected tmpfiles.org download page")
        parser.feed(data.decode("utf-8", errors="replace"))
        if not parser.href:
            raise ValueError("No download link on tmpfiles.org; the file may have expired")
        return download_url(str(page.url.join(URL(parser.href, encoded=True))))


async def fetch_video(path, directory):
    url = download_url(path)
    key = hashlib.sha256(str(url).encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    for ext in ("mp4", "webm", "mkv", "mov", "gif"):
        cached = directory / f"{key}.{ext}"
        if cached.is_file():
            return cached
    limit = 1024**3
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(socket_factory=public_socket),
                                     timeout=aiohttp.ClientTimeout(total=600, sock_read=45)) as session:
        url = await resolve_tmpfiles(session, url)
        async with session.get(url, max_redirects=5) as response:
            if response.status != 200:
                raise ValueError(f"Video host returned HTTP {response.status}; check the download link")
            if (response.content_length or 0) > limit:
                raise ValueError("Video download exceeds 1 GiB")
            header = await response.content.readexactly(12)
            if header[4:8] in (b"ftyp", b"moov", b"mdat", b"wide", b"free"):
                ext = "mov" if response.url.path.lower().endswith(".mov") else "mp4"
            elif header.startswith(b"\x1aE\xdf\xa3"):
                ext = "webm" if response.url.path.lower().endswith(".webm") else "mkv"
            elif header.startswith((b"GIF87a", b"GIF89a")):
                ext = "gif"
            else:
                raise ValueError("Expected a video file (MP4, MOV, MKV, WebM or GIF); check the direct link")
            target = directory / f"{key}.{ext}"
            with NamedTemporaryFile(dir=directory, suffix=".part", delete=False) as out:
                partial = Path(out.name)
            try:
                with partial.open("wb") as out:
                    out.write(header)
                    async for chunk in response.content.iter_chunked(256 * 1024):
                        if out.tell() + len(chunk) > limit:
                            raise ValueError("Video download exceeds 1 GiB")
                        out.write(chunk)
                partial.replace(target)
            finally:
                partial.unlink(missing_ok=True)
            return target


class LoadVideoURL(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        loader = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideoPath")
        formats, options = loader.INPUT_TYPES()["optional"]["format"] if loader else (["AnimateDiff"], {})
        max_frames = 2**53 - 1
        return io.Schema(
            node_id="VibenodeLoadVideoURL", display_name="Load video url api", category="Vibenode",
            hidden=[io.Hidden.unique_id],
            inputs=[io.String.Input("path", default="", tooltip="Public video URL or tmpfiles.org link"),
                    io.Float.Input("force_rate", default=0, min=0, max=60, step=1),
                    io.Int.Input("custom_width", default=0, min=0, max=8192),
                    io.Int.Input("custom_height", default=0, min=0, max=8192),
                    io.Int.Input("frame_load_cap", default=0, min=0, max=max_frames),
                    io.Int.Input("skip_first_frames", default=0, min=0, max=max_frames),
                    io.Int.Input("select_every_nth", default=1, min=1, max=max_frames),
                    io.Custom("VHS_BatchManager").Input("meta_batch", optional=True),
                    io.Vae.Input("vae", optional=True),
                    io.Combo.Input("format", options=formats, default="AnimateDiff", optional=True,
                                   extra_dict=options)],
            outputs=[io.Custom(loader.RETURN_TYPES[0] if loader else "IMAGE").Output("IMAGE"),
                     io.Int.Output("frame_count"), io.Audio.Output("audio"), io.Custom("VHS_VIDEOINFO").Output("video_info")],
        )

    @classmethod
    async def execute(cls, path, **settings):
        loader = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideoPath")
        if loader is None:
            raise RuntimeError("Load video url api requires ComfyUI-VideoHelperSuite")
        file = await fetch_video(path, Path(folder_paths.get_temp_directory()) / "vibenode-video")
        frames, count, audio, info = loader().load_video(video=str(file), unique_id=cls.hidden.unique_id, **settings)
        # Iterating VHS's lazy audio during cache accounting decodes it.
        with av.open(str(file), options={"protocol_whitelist": "file"}) as container:
            if not container.streams.audio:
                audio = None
        return io.NodeOutput(frames, count, audio, info, ui={"video_file": [file.name]})
