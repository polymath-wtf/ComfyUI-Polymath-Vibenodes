import json
import math
import re
from dataclasses import replace as replace_schema

from comfy_api.latest import io


NAME = r"[A-Za-z_][A-Za-z0-9_-]*"
INPUT = re.compile(rf"\{{({NAME})\}}")
TOKEN = re.compile(r"""\{\{\s*\$json\[['"]([^'"]+)['"]\]\.prompt\s*\}\}""" +
                   rf"|\{{(>)({NAME})((?:[^{{}}]|\{{{NAME}\}})*)\}}|\{{({NAME})\}}")
JSON_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|' + TOKEN.pattern)
MAX_EXPORTS = 32
DEFAULT_TEMPLATE = ("{>subject {character} in {scene}, {action}, {pose}}.\n"
                    "{>shot {camera}, lit by {light}}. Inspired by {style}.")


def render(template, slots, *, structured=False):
    exports = {}

    def read(key):
        value = slots.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"Connect a STRING to {key}")
        return value

    def replace(match):
        if match[0].startswith('"'):
            return match[0]
        key = match[1] or match[3] or match[5]
        body = match[4]
        value = INPUT.sub(lambda m: read(m[1]), body.lstrip()) if body else read(key)
        if match[2] == ">":
            exports[key] = value
        return json.dumps(value, ensure_ascii=False) if structured else value

    return (JSON_TOKEN if structured else TOKEN).sub(replace, template), exports


class PromptSchema(io.Schema):
    preview_outputs = 3

    def get_v1_info(self, cls):
        # The catalog describes a new instance; execution also accepts saved custom ports.
        return io.Schema.get_v1_info(replace_schema(self, outputs=self.outputs[:self.preview_outputs]), cls)


class PromptTemplate(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return PromptSchema(
            node_id="PM_JsonPrompt", display_name="Vibenode Polyprompt JSON", category="Vibenode",
            accept_all_inputs=True,
            inputs=[io.String.Input("template", multiline=True, default=DEFAULT_TEMPLATE,
                                    tooltip="{name}: input. {>name text with {input}}: named fragment.")],
            outputs=[io.String.Output(name) for name in
                     ["prompt", "subject", "shot", *(f"export_{i}" for i in range(2, MAX_EXPORTS))]],
        )

    @classmethod
    def execute(cls, template, **slots):
        # Legacy JSON expressions supply their own JSON string delimiters.
        if "$json[" in template and template.lstrip().startswith(("{", "[")):
            rendered, exports = render(template, slots, structured=True)
        else:
            rendered, exports = render(template, slots)
        if len(exports) > MAX_EXPORTS:
            raise ValueError(f"Use at most {MAX_EXPORTS} named outputs per template")
        return io.NodeOutput(rendered, *exports.values(), *([""] * (MAX_EXPORTS - len(exports))))


class JsonList(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodeJsonList", display_name="Vibenode JSON List", category="Vibenode",
            accept_all_inputs=True,
            inputs=[io.String.Input("json_text", multiline=True, default='{"scenes":["forest","city"]}'),
                    io.String.Input("path", default="$")],
            outputs=[io.String.Output("keys", is_output_list=True), io.String.Output("values", is_output_list=True),
                     io.Int.Output("int", is_output_list=True), io.Float.Output("float", is_output_list=True),
                     io.Int.Output("count")],
        )

    @classmethod
    def execute(cls, json_text, path, **slots):
        obj = json.loads(render(json_text, slots, structured=True)[0])
        parts = path.strip().split(".")
        if parts[0] != "$":
            raise ValueError("Start the path with $, e.g. $.scenes")
        for key in parts[1:]:
            if isinstance(obj, list) and key.isascii() and key.isdecimal() and int(key) < len(obj):
                obj = obj[int(key)]
            elif isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                raise ValueError(f"No entry {key!r} in path {path!r}")
        if not isinstance(obj, (dict, list)):
            raise ValueError(f"{path} must select an object or array")
        keys, values, ints, floats = [], [], [], []
        for key, value in (obj.items() if isinstance(obj, dict) else enumerate(obj)):
            keys.append(str(key))
            values.append(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
            if type(value) in (int, float) and math.isfinite(value):
                ints.append(int(value))
                floats.append(float(value))
        return io.NodeOutput(keys, values, ints, floats, len(values))


class MidCalcSchema(PromptSchema):
    preview_outputs = 6


MAX_POINTS = 256


class NumberRange(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return MidCalcSchema(
            node_id="VibenodeNumberRange", display_name="Vibe Mid Calc", category="Vibenode",
            inputs=[io.Int.Input("start", default=1, min=-10**12, max=10**12),
                    io.Int.Input("end", default=16, min=-10**12, max=10**12),
                    io.Int.Input("num", display_name="output count", default=3, min=1, max=MAX_POINTS)],
            outputs=[io.Int.Output("int", is_output_list=True), io.Float.Output("float", is_output_list=True),
                     io.String.Output("indices"), *(io.Int.Output(str(i)) for i in range(1, MAX_POINTS + 1))],
        )

    @classmethod
    def execute(cls, start, end, num):
        numbers = [float(start)] if num == 1 else [start + (end - start) * i / (num - 1) for i in range(num - 1)] + [float(end)]
        integers = [int(n) for n in numbers]
        return io.NodeOutput(integers, numbers, ",".join(map(str, integers)), *integers, *([None] * (MAX_POINTS - num)))


class PromptPreview(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodePromptPreview", display_name="Vibenode Prompt Preview", category="Vibenode",
            is_input_list=True, is_output_node=True, inputs=[io.String.Input("prompts", force_input=True)],
        )

    @classmethod
    def execute(cls, prompts):
        return io.NodeOutput(ui={"prompts": prompts})
