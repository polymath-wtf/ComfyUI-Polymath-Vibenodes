import asyncio
import importlib
import sys
import unittest
from pathlib import Path

import torch

package = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(package.parents[1]), str(package.parent)]
extension = asyncio.run(importlib.import_module(package.name).comfy_entrypoint())
nodes = {n.GET_SCHEMA().node_id: n for n in asyncio.run(extension.get_node_list())}


class CreatorTests(unittest.TestCase):
    images = torch.arange(12).view(12, 1, 1, 1).expand(-1, 2, 3, 3)

    def node(self, name):
        self.assertIn("Vibenode" + name, nodes)
        return nodes["Vibenode" + name]

    def test_selector(self):
        node = self.node("FramesSelector")
        self.assertEqual(tuple(node.OUTPUT_IS_LIST), (False, True))
        for start, length, stop in [(0, 8, 8), (0, -1, 12), (5, -1, 12), (10, 8, 12), (8, 1, 9)]:
            batch, frames = node.execute(self.images, start, length).result
            self.assertTrue(torch.equal(batch, self.images[start:stop]))
            self.assertEqual([len(f) for f in frames], [1] * len(batch))
            self.assertTrue(torch.equal(torch.cat(frames), batch))
        for start, length in [(12, 1), (0, 0)]:
            with self.assertRaises(ValueError):
                node.execute(self.images, start, length)

    def test_ping_pong(self):
        node = self.node("PingPong")
        for n, order in [(1, [0]), (2, [0, 1]), (4, [0, 1, 2, 3, 2, 1])]:
            self.assertTrue(torch.equal(node.execute(self.images[:n]).result[0], self.images[order]))

    def test_dimensions(self):
        self.assertEqual(self.node("BatchInfo").execute(self.images).result, (3, 2, 12))

    def test_prompt_lines(self):
        self.assertEqual(self.node("PromptLines").execute(" city  \r\n\n夜\ncity").result, (["city", "夜", "city"],))

    def test_mid_calc_selects_frames(self):
        images = torch.arange(1, 131).view(130, 1, 1, 1)
        result = self.node("NumberRange").execute(1, len(images), 3).result
        self.assertEqual(result[0], [1, 65, 130])
        self.assertEqual(result[1][1], 65.5)
        self.assertEqual(result[2:6], ("1,65,130", 1, 65, 130))
        frame = nodes["FrameSelectVibe"].execute(images, result[5]).result[0]
        self.assertTrue(torch.equal(frame, images[-1:]))
        select = self.node("ImageSelect")
        self.assertEqual(select.execute(images, result[2]).result[0].flatten().tolist(), [1, 65, 130])
        self.assertEqual(select.execute(images, "4, 1,4").result[0].flatten().tolist(), [4, 1, 4])
        for invalid in ["0", "131"]:
            with self.assertRaises(ValueError):
                select.execute(images, invalid)


if __name__ == "__main__":
    unittest.main()
