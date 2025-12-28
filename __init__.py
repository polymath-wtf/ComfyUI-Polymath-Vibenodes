from .nodes.json_prompt_template import NODE_CLASS_MAPPINGS


NODE_DISPLAY_NAME_MAPPINGS = {
    "PM_JsonPrompt": "Polymath JSON Prompt",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
