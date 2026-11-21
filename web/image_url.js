import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "Vibenode.ImageURLPreview",
    nodeCreated(node) {
        if (node.comfyClass !== "VibenodeLoadImageURL") return;
        const field = node.widgets.find(w => w.name === "url");
        const box = document.createElement("div");
        box.style.cssText = "height:100%;display:grid;place-items:center;overflow:hidden;text-align:center";
        const img = document.createElement("img");
        img.style.cssText = "width:100%;height:100%;object-fit:contain;min-height:0";
        node.addDOMWidget("thumbnail", "image-preview", box, { serialize: false });
        node.setSize([Math.max(node.size[0], 260), Math.max(node.size[1], 240)]);
        let timer, request, blobUrl, previous;
        function reset() {
            clearTimeout(timer);
            request?.abort();
            if (blobUrl) URL.revokeObjectURL(blobUrl);
            blobUrl = null;
            box.replaceChildren();
        }
        function update(value) {
            const url = String(value ?? "").trim();
            if (url === previous) return;
            previous = url;
            reset();
            if (!/^https?:\/\/\S+$/i.test(url)) return;
            const controller = request = new AbortController();
            box.textContent = "Загрузка…";
            timer = setTimeout(async () => {
                try {
                    const res = await api.fetchApi("/vibenode/image-preview", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ url }), signal: controller.signal,
                    });
                    if (!res.ok) throw new Error();
                    const blob = await res.blob();
                    if (controller.signal.aborted) return;
                    img.src = blobUrl = URL.createObjectURL(blob);
                    box.replaceChildren(img);
                } catch {
                    if (!controller.signal.aborted) box.textContent = "Не удалось загрузить превью";
                }
            }, 350);
        }
        const callback = field.callback;
        field.callback = function (value, ...args) {
            const result = callback?.call(this, value, ...args);
            update(value);
            return result;
        };
        field.inputEl?.addEventListener("input", e => update(e.target.value));
        queueMicrotask(() => update(field.value));
        const removed = node.onRemoved;
        node.onRemoved = function (...args) {
            reset();
            return removed?.apply(this, args);
        };
    },
});
