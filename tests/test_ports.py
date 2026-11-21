import unittest

from test_creator import nodes


class TemplatePorts(unittest.TestCase):
    def test_fragment_outputs(self):
        node = nodes["PM_JsonPrompt"]
        result = node.execute("{>day hello there}: {>character {pose},{emotion}} / {>qwe{pose}}",
                              pose="sitting", emotion="calm").result
        self.assertEqual(result[:4], ("hello there: sitting,calm / sitting", "hello there", "sitting,calm", "sitting"))

    def test_catalog_only_shows_starter_outputs(self):
        node = nodes["PM_JsonPrompt"]
        self.assertEqual(node.GET_NODE_INFO_V1()["output_name"], ["prompt", "subject", "shot"])
        self.assertGreater(len(node.RETURN_TYPES), 3)

    def test_plain_prompt_from_old_json_widget(self):
        node = nodes["PM_JsonPrompt"]
        result = node.execute("{character} in {scene} in {>detail}", format="JSON",
                              character="qwe", scene="123", detail="neon").result
        self.assertEqual(result[:2], ("qwe in 123 in neon", "neon"))

    def test_json_slot_and_literal(self):
        node = nodes["VibenodeJsonList"]
        values = node.execute('["{literal}", {scene}]', "$", scene='a"\nb').result[1]
        self.assertEqual(values, ["{literal}", 'a"\nb'])
