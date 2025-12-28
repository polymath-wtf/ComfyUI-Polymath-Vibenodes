# ComfyUI-Polymath

## Polymath JSON Prompt

A custom ComfyUI node that lets you make auto json prompts with a simple placeholder templating syntax, while automatically creating **dynamic input ports** for any referenced placeholders.


### Why

Чтобы автоматизировать json промпты, работая с n8n и создавая dataset for lora with qwen-edit in one click

<img width="420" height="420" alt="polymath json node" src="https://github.com/user-attachments/assets/0f1cfd41-a19b-406d-a517-fa36daa0335d" />


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

1. Manual git clone into ComfyUI/custom_nodes:

   ```
   git clone https://github.com/polymath-wtf/ComfyUI-Polymath-Vibenodes.git
   ```

3. Restart UI.

### Development notes

- First VibeNode&VibeCode, Enjoy
- Backend is implemented using the ComfyUI V3 API (`comfy_api.latest.IO`). v3? wtf? idk

