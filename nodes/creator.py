import torch
from comfy_api.latest import io


class _EdgeFrame(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id=cls.__name__, display_name=cls.title, category="Vibenode",
            inputs=[io.Image.Input("images")], outputs=[io.Image.Output("image")],
        )

    @classmethod
    def execute(cls, images):
        return io.NodeOutput(images[cls.index].unsqueeze(0).clone())


class FirstFrameVibe(_EdgeFrame):
    title = "First Frame Vibe"
    index = 0


class LastFrameVibe(_EdgeFrame):
    title = "Last Frame Vibe"
    index = -1


class FrameSelectVibe(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="FrameSelectVibe", display_name="Frame Select Vibe", category="Vibenode",
            inputs=[io.Image.Input("images"), io.Int.Input("index", force_input=True, default=1, min=1)],
            outputs=[io.Image.Output("image")],
        )

    @classmethod
    def execute(cls, images, index):
        if not 1 <= index <= len(images):
            raise ValueError(f"Frame {index} outside range 1..{len(images)}")
        return io.NodeOutput(images[index - 1:index].clone())


class FramesSelector(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodeFramesSelector", display_name="Vibenode Image Cut Select", category="Vibenode",
            inputs=[io.Image.Input("images"), io.Int.Input("start", default=0, min=0),
                    io.Int.Input("length", default=-1, min=-1, tooltip="Frame count, or -1 for all remaining frames.")],
            outputs=[io.Image.Output("batch"), io.Image.Output("frames", is_output_list=True)],
        )

    @classmethod
    def execute(cls, images, start, length):
        if not 0 <= start < len(images):
            raise ValueError(f"start={start} is outside the input batch ({len(images)} frames)")
        if length == 0 or length < -1:
            raise ValueError("Use a positive length, or -1 for all remaining frames")
        batch = images[start:None if length == -1 else start + length]
        if len(batch) < len(images):
            batch = batch.clone()
        return io.NodeOutput(batch, list(batch.split(1)))


class ImageSelect(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodeImageSelect", display_name="Vibenode Image Select", category="Vibenode",
            inputs=[io.Image.Input("images"), io.String.Input("indices", default="1", tooltip="Frame numbers starting at 1, e.g. 1,65,130")],
            outputs=[io.Image.Output("images")],
        )

    @classmethod
    def execute(cls, images, indices):
        parts = [part.strip() for part in indices.split(",")]
        if not all(part.isascii() and part.isdecimal() for part in parts):
            raise ValueError("Enter frame numbers separated by commas, e.g. 1,65,130")
        selected = list(map(int, parts))
        for frame in selected:
            if not 1 <= frame <= len(images):
                raise ValueError(f"Frame {frame} outside range 1..{len(images)}")
        return io.NodeOutput(images[[frame - 1 for frame in selected]])


class PingPong(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodePingPong", display_name="Vibenode Ping Pong", category="Vibenode",
            inputs=[io.Image.Input("images")], outputs=[io.Image.Output("loop")],
        )

    @classmethod
    def execute(cls, images):
        loop = torch.cat((images, images[1:-1].flip((0,)))) if len(images) > 2 else images
        return io.NodeOutput(loop)


class BatchInfo(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodeBatchInfo", display_name="Vibenode Batch Info", category="Vibenode",
            inputs=[io.Image.Input("images")],
            outputs=[io.Int.Output("width"), io.Int.Output("height"), io.Int.Output("count")],
        )

    @classmethod
    def execute(cls, images):
        count, height, width, _ = images.shape
        return io.NodeOutput(width, height, count)


class TextVibe(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodeText", display_name="Text Vibe", category="Vibenode",
            search_aliases=["text", "textvibe", "text_vibe"],
            inputs=[io.String.Input("text", multiline=True, default="")],
            outputs=[io.String.Output("text")],
        )

    @classmethod
    def execute(cls, text):
        return io.NodeOutput(text)


class PromptLines(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VibenodePromptLines", display_name="Vibenode Prompt Lines", category="Vibenode",
            inputs=[io.String.Input("text", multiline=True)], outputs=[io.String.Output("lines", is_output_list=True)],
        )

    @classmethod
    def execute(cls, text):
        return io.NodeOutput([line.strip() for line in text.splitlines() if line.strip()])
