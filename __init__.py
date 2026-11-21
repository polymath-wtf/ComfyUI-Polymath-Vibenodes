from comfy_api.latest import ComfyExtension

from .nodes.creator import BatchInfo, FirstFrameVibe, FrameSelectVibe, FramesSelector, ImageSelect, LastFrameVibe, PingPong, PromptLines, TextVibe
from .nodes.vibenodes import JsonList, NumberRange, PromptPreview, PromptTemplate
from .nodes.video_url import LoadVideoURL
from .nodes.image_url import LoadImageURL, image_preview

WEB_DIRECTORY = "./web"


class VibenodeExtension(ComfyExtension):
    async def on_load(self):
        from server import PromptServer
        PromptServer.instance.routes.post("/vibenode/image-preview")(image_preview)

    async def get_node_list(self):
        return [TextVibe, PromptTemplate, JsonList, NumberRange, PromptPreview, FramesSelector, ImageSelect,
                FirstFrameVibe, LastFrameVibe, FrameSelectVibe, PingPong, BatchInfo, PromptLines, LoadVideoURL, LoadImageURL]


async def comfy_entrypoint():
    return VibenodeExtension()
