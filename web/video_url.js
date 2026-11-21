import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "Vibenode.VideoURL",
    nodeCreated(node) {
        if (node.comfyClass !== "VibenodeLoadVideoURL") return;
        const connected = node.onConnectionsChange;
        node.onConnectionsChange = function (...args) {
            const result = connected?.apply(this, args);
            const vae = this.inputs.find(input => input.name === "vae");
            const type = vae?.link != null ? "LATENT" : "IMAGE";
            this.outputs[0].type = this.outputs[0].name = type;
            return result;
        };
        const executed = node.onExecuted;
        let video;
        node.onExecuted = function (message) {
            executed?.call(this, message);
            const filename = message.video_file?.[0];
            if (!filename) return;
            if (!video) {
                video = document.createElement("video");
                video.controls = true;
                video.playsInline = true;
                video.style.cssText = "width:100%;height:100%;object-fit:contain";
                this.addDOMWidget("preview", "video", video, { serialize: false });
            }
            const params = new URLSearchParams({ filename, type: "temp", subfolder: "vibenode-video" });
            video.src = api.apiURL(`/view?${params}`);
        };
    },
});
