# ComfyUI-Polymath

## Polymath JSON Prompt

A custom ComfyUI node that lets you author **strict JSON** prompts with a simple placeholder templating syntax, while automatically creating **dynamic input ports** for any referenced placeholders.

### Why

Building structured prompts (JSON) in ComfyUI is annoying when parts of the JSON must come from other nodes.
This node solves it by letting you write a JSON template and inject external strings safely.

### Node

- **Name**: Polymath JSON Prompt
- **Category**: Polymath
- **Output**: `STRING` (pretty-printed valid JSON)

### Placeholder syntax

Use placeholders **without quotes**:

```json
{
  "scene": {{ $json['scene'].prompt }},
  "identity": {{ $json['identity'].prompt }}
}
```

Rules:

- Placeholders are matched by the pattern:

  `{{ $json['KEY'].prompt }}`

- `KEY` becomes a **dynamic input port** on the node.
- The incoming value is treated as a **string**, JSON-escaped, and inserted into the template.
- The final rendered result is validated with `json.loads()`.
  If it is not valid JSON, the node throws an error.

### Example template

```json
{
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
}
```

### Install

1. Copy this folder into:

   `ComfyUI/custom_nodes/ComfyUI-Polymath`

2. Restart ComfyUI.

### Development notes

- Dynamic ports are added/removed by `web/polymath_json_prompt_template.js`.
- Backend is implemented using the ComfyUI V3 API (`comfy_api.latest.IO`).

