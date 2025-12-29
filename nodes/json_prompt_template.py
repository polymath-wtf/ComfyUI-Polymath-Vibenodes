import json
import re
from typing import Any

from comfy_api.latest import IO
from comfy_api.latest._io import ComfyTypeI, DynamicInput, add_to_input_dict_v1, comfytype


_PLACEHOLDER_RE = re.compile(
    r"\{\{\s*\$json\[['\"](?P<key>[^'\"]+)['\"]\]\.prompt\s*\}\}"
)


@comfytype(io_type="COMFY_PM_DYNAMIC_INPUTS_V3")
class _PM_DynamicInputs(ComfyTypeI):
    Type = dict[str, Any]

    class Input(DynamicInput):
        def __init__(
            self,
            id: str,
            display_name: str | None = None,
            tooltip: str | None = None,
        ):
            super().__init__(id=id, display_name=display_name, optional=True, tooltip=tooltip)

        def expand_schema_for_dynamic(self, d: dict[str, Any], live_inputs: dict[str, Any], curr_prefix=""):
            for inner_dict in d.values():
                if self.id in inner_dict:
                    del inner_dict[self.id]

            dynamic_inputs = []
            for key in live_inputs.keys():
                if key == "template":
                    continue
                if key == self.id:
                    continue
                dynamic_inputs.append(IO.String.Input(key, optional=True, force_input=True))

            add_to_input_dict_v1(d, dynamic_inputs, live_inputs, curr_prefix)


class PM_JsonPrompt(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="PM_JsonPrompt",
            display_name="Polymath JSON Prompt",
            category="Polymath",
            inputs=[
                IO.String.Input(
                    "template",
                    default=(
                        """{
  "scene": {{ $json['scene'].prompt }},
  "character": [
    {
      "identity": {{ $json['identity'].prompt }},
      "pose": {{ $json['pose'].prompt }},
      "dress": {{ $json['dress'].prompt }},
      "emotion": {{ $json['emotion'].prompt }},
      "action": {{ $json['action'].prompt }}
    }
  ],
  "style": "...",
  "lighting": "...",
  "mood": "...",
  "camera": {
    "angle": "high angle",
    "distance": "medium shot",
    "focus": "Sharp focus on ... in frame",
    "lens-mm": 85,
    "f-number": "f/5.6",
    "ISO": 200
  }
}"""
                    ),
                    multiline=True,
                    tooltip="Strict JSON template. Use {{ $json['key'].prompt }} placeholders without quotes to inject external strings safely.",
                ),
                _PM_DynamicInputs.Input(
                    "_dyn",
                    tooltip="Internal dynamic inputs placeholder; real inputs are inferred from connected ports.",
                ),
            ],
            outputs=[IO.String.Output()],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float("nan")

    @classmethod
    def execute(cls, template: str, **kwargs) -> IO.NodeOutput:

        def replace(m: re.Match[str]) -> str:
            key = m.group("key")
            value = kwargs.get(key)
            if isinstance(value, (list, tuple)):
                value = value[0] if len(value) > 0 else ""
            value_str = "" if value is None else str(value)
            return json.dumps(value_str, ensure_ascii=False)

        rendered = _PLACEHOLDER_RE.sub(replace, template)

        try:
            obj = json.loads(rendered)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Rendered template is not valid JSON: {e.msg} (line {e.lineno}, col {e.colno})"
            )

        pretty = json.dumps(obj, ensure_ascii=False, indent=2)
        return (pretty,)


NODE_CLASS_MAPPINGS = {
    "PM_JsonPrompt": PM_JsonPrompt,
}
