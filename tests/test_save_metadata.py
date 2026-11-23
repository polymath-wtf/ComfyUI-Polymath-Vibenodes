import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import folder_paths
import torch
from PIL import Image
from test_creator import nodes, package


class SaveMetadataTests(unittest.TestCase):
    def test_saved_files(self):
        node = nodes["VibenodeSaveImageMetadata"]
        frames = torch.zeros(2, 8, 8, 3)
        frames[1, :, :, 0] = 1
        hidden = SimpleNamespace(prompt={"source": "private"}, extra_pnginfo={"workflow": {"id": "private"}})
        date = "2026:07:03 15:42:18"
        custom = {"Title": "Кадр", "values": [1, False], "CreateDate": date, "ModifyDate": date}
        for ext in ("png", "jpg", "jpeg", "webp", "gif"):
            for include in (True, False):
                with self.subTest(ext=ext, include=include), tempfile.TemporaryDirectory(dir=package) as tmp, \
                        patch.object(folder_paths, "get_output_directory", return_value=tmp), \
                        patch.object(node, "hidden", hidden, create=True):
                    node.execute(frames, "test/image", json.dumps(custom), include, {"format": ext})
                    files = list(Path(tmp).rglob(f"*.{ext}"))
                    self.assertEqual(len(files), 1 if ext == "gif" else 2)
                    for file in files:
                        with Image.open(file) as im:
                            if ext == "png":
                                self.assertEqual(im.text["Title"], "Кадр")
                                self.assertEqual(im.text["CreateDate"], date)
                                self.assertEqual(im.text["ModifyDate"], date)
                                self.assertEqual(json.loads(im.text["values"]), [1, False])
                                data = {k: json.loads(v) for k, v in im.text.items() if k not in custom}
                            elif ext == "gif":
                                data = json.loads(im.info["comment"])
                                self.assertEqual(data.pop("metadata"), custom)
                                self.assertEqual(im.n_frames, 2)
                            else:
                                exif = im.getexif()
                                self.assertNotIn(270, exif)
                                self.assertEqual(exif.get(306), date)
                                self.assertEqual(exif.get_ifd(34665)[36868], date)
                                xml = ET.fromstring(im.info["xmp"])
                                self.assertEqual(list(xml.find(".//{http://purl.org/dc/elements/1.1/}title").itertext()), ["Кадр"])
                                self.assertEqual(json.loads(xml.find(".//{*}values").text), [1, False])
                                data = {}
                                for tag in (271, 272):
                                    if tag in exif:
                                        key, text = exif[tag].split(":", 1)
                                        data[key] = json.loads(text)
                            expected = {}
                            if include:
                                expected.update(prompt=hidden.prompt, workflow=hidden.extra_pnginfo["workflow"])
                            self.assertEqual(data, expected)
