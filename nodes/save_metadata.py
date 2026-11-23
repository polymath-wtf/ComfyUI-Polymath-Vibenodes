import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import folder_paths
import torch
from comfy.cli_args import args
from comfy_api.latest import io
from PIL import Image, PngImagePlugin


def packed(value, ascii_only=False):
    return json.dumps(value, ensure_ascii=ascii_only, allow_nan=False, separators=(",", ":"))


def field_text(value):
    return value if isinstance(value, str) else packed(value)


def xmp_fields(metadata):
    root = ET.Element("x:xmpmeta", {"xmlns:x": "adobe:ns:meta/"})
    rdf = ET.SubElement(root, "rdf:RDF", {"xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"})
    desc = ET.SubElement(rdf, "rdf:Description", {
        "rdf:about": "", "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        "xmlns:xmp": "http://ns.adobe.com/xap/1.0/", "xmlns:vibe": "urn:vibenode:metadata:1/",
        "xmlns:photoshop": "http://ns.adobe.com/photoshop/1.0/"})
    names = {"title": ("dc:title", "Alt"), "description": ("dc:description", "Alt"),
             "author": ("dc:creator", "Seq"), "keywords": ("dc:subject", "Bag"),
             "copyrights": ("dc:rights", "Alt"), "copyright": ("dc:rights", "Alt"),
             "rating": ("xmp:Rating", None), "software": ("xmp:CreatorTool", None),
             "category": ("photoshop:Category", None)}
    for key, value in metadata.items():
        if key.lower() in ("createdate", "modifydate"):
            continue  # These are native EXIF fields.
        if not re.fullmatch(r"[^\W\d][\w.-]*", key):
            raise ValueError(f"Недопустимое имя XMP-поля: {key!r}. Используйте буквы, цифры, _, . или -.")
        tag, container = names.get(key.lower(), (f"vibe:{key}", None))
        field = ET.SubElement(desc, tag)
        if container:
            items = ET.SubElement(field, "rdf:" + container)
            for item in value if isinstance(value, list) else [value]:
                attrs = {"xml:lang": "x-default"} if container == "Alt" else {}
                ET.SubElement(items, "rdf:li", attrs).text = field_text(item)
        else:
            field.text = field_text(value)
    return ET.tostring(root, encoding="utf-8") if len(desc) else b""


def encoder_options(ext, settings, data):
    metadata = data["metadata"]
    if ext == "png":
        info = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            if key.lower() in ("workflow", "prompt") or not re.fullmatch(r"[\x20-\x7e\xa1-\xff]{1,79}", key):
                raise ValueError(f"Недопустимый или зарезервированный ключ PNG: {key!r}")
            info.add_itxt(key, field_text(value))
        for key in ("prompt", "workflow"):
            if key in data:
                info.add_itxt(key, packed(data[key]))
        return {"pnginfo": info, "compress_level": settings.get("compression", 6)}
    if ext == "gif":
        return {"comment": packed(data).encode(), "loop": settings.get("loop", 0)}

    exif = Image.Exif()
    for key, value in metadata.items():
        if key.lower() == "createdate":
            exif[34665] = {36868: value}
        elif key.lower() == "modifydate":
            exif[306] = value
    xmp = xmp_fields(metadata)
    for key, tag in (("prompt", 272), ("workflow", 271)):
        if key in data:
            exif[tag] = key + ":" + packed(data[key], True)
    raw = exif.tobytes() if exif else b""
    if ext == "webp":
        return dict(exif=raw, xmp=xmp, quality=settings.get("quality", 90), method=6, lossless=settings.get("lossless", False))
    if len(raw) > 65533 or len(xmp) > 65504:
        raise ValueError("Метаданные не помещаются в сегмент JPEG (64 КиБ). Выберите PNG или WebP.")
    return dict(exif=raw, xmp=xmp, quality=settings.get("quality", 95), optimize=True, progressive=True,
                subsampling=settings.get("subsampling", "4:4:4"))


def pil_frame(tensor, ext):
    pixels = tensor.detach().float().clamp(0, 1).mul(255).round().to(torch.uint8).cpu().numpy()
    image = Image.fromarray(pixels[..., 0] if pixels.shape[-1] == 1 else pixels)
    if ext in ("gif", "jpg", "jpeg") and image.mode == "RGBA":
        matte = Image.new("RGB", image.size, "white")
        matte.paste(image, mask=image.getchannel("A"))
        return matte
    return image


class SaveImageMetadata(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        option = io.DynamicCombo.Option
        return io.Schema(
            node_id="VibenodeSaveImageMetadata", display_name="Vibenode Save Image Metadata", category="Vibenode",
            is_output_node=True, hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
            inputs=[io.Image.Input("images"), io.String.Input("filename_prefix", default="Vibenode/image"),
                    io.String.Input("metadata_json", default="{}", multiline=True),
                    io.Boolean.Input("with_workflow", default=False),
                    io.DynamicCombo.Input("format", options=[
                        option("png", [io.Int.Input("compression", default=6, min=0, max=9)]),
                        *(option(ext, [io.Int.Input("quality", default=95, min=1, max=100),
                                       io.Combo.Input("subsampling", options=["4:4:4", "4:2:2", "4:2:0"])])
                          for ext in ("jpg", "jpeg")),
                        option("webp", [io.Boolean.Input("lossless", default=False),
                                        io.Int.Input("quality", default=90, min=0, max=100)]),
                        option("gif", [io.Float.Input("fps", default=12, min=0.1, max=100, step=0.1),
                                       io.Int.Input("loop", default=0, min=0, max=65535)]),
                    ])], outputs=[])

    @classmethod
    def execute(cls, images, filename_prefix, metadata_json, with_workflow, format):
        ext = format["format"]
        if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
            raise ValueError("Неизвестный формат изображения")
        metadata = json.loads(metadata_json.strip() or "{}")
        if not isinstance(metadata, dict):
            raise ValueError("metadata_json должен содержать JSON-объект {...}")
        data = {"metadata": metadata}
        if with_workflow and not args.disable_metadata:
            if cls.hidden.prompt is not None:
                data["prompt"] = cls.hidden.prompt
            workflow = (cls.hidden.extra_pnginfo or {}).get("workflow")
            if workflow is not None:
                data["workflow"] = workflow
        options = encoder_options(ext, format, data)
        folder, stem, counter, subfolder, _ = folder_paths.get_save_image_path(
            filename_prefix, folder_paths.get_output_directory(), images.shape[2], images.shape[1])
        frames = (pil_frame(t, ext) for t in images)
        entries = []
        for index, frame in enumerate(frames):
            if ext == "gif":
                fps = format.get("fps", 12)
                ticks = [round(i * 100 / fps) for i in range(len(images) + 1)]
                options.update(save_all=True, append_images=frames,
                               duration=[10 * (b - a) for a, b in zip(ticks, ticks[1:])])
            while True:
                name = f"{stem.replace('%batch_num%', str(index))}_{counter:05}_.{ext}"
                path = Path(folder) / name
                counter += 1
                try:
                    file = path.open("xb")
                    break
                except FileExistsError:
                    continue
            try:
                with file:
                    frame.save(file, "JPEG" if ext == "jpg" else ext.upper(), **options)
            except Exception:
                path.unlink()
                raise
            entries.append(dict(filename=name, subfolder=subfolder, type="output"))
        return io.NodeOutput(ui={"images": entries})
