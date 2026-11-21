import { app } from "../../scripts/app.js";

const name = "[A-Za-z_][A-Za-z0-9_-]*";
const input = new RegExp(`\\{(${name})\\}`, "g");
const token = new RegExp(String.raw`\{\{\s*\$json\[['"]([^'"]+)['"]\]\.prompt\s*\}\}|\{(>)(${name})((?:[^{}]|\{${name}\})*)\}|\{(${name})\}`, "g");
const jsonToken = new RegExp(String.raw`"(?:\\.|[^"\\])*"|` + token.source, "g");
const fields = { PM_JsonPrompt: "template", VibenodeJsonList: "json_text" };

function sync(node, editing = false) {
    const field = fields[node.comfyClass];
    const widget = node.widgets?.find(w => w.name === field);
    if (!widget) return;
    const text = String(widget.value);
    const structured = field === "json_text" || (text.includes("$json[") && /^\s*[\[{]/.test(text));
    const keys = new Set(), exports = new Set();
    for (const m of text.matchAll(structured ? jsonToken : token)) {
        const key = m[1] ?? m[3] ?? m[5];
        if (!key) continue;
        if (m[4]) {
            for (const part of m[4].matchAll(input)) keys.add(part[1]);
        } else keys.add(key);
        if (m[2] === ">") exports.add(key);
    }
    const fixed = new Set([field, "cls", ...(field === "json_text" ? ["path"] : [])]);
    const old = node.inputs.filter(s => !fixed.has(s.name) && !keys.has(s.name));
    const added = [...keys].filter(k => !fixed.has(k) && !node.inputs.some(s => s.name === k));
    if (old.length === 1 && added.length === 1) {
        old[0].name = added.pop();
        if (old[0].label) old[0].label = old[0].name;
    } else if (!editing) {
        for (const slot of old.reverse()) node.removeInput(node.inputs.indexOf(slot));
    }
    for (const key of added) node.addInput(key, "STRING");
    if (field === "template") {
        // Output indices in the API prompt follow first occurrence in the template.
        const names = [...exports].slice(0, 32);
        if (editing && node.outputs.slice(1).some(s => s.links?.length && !names.includes(s.name))
            && names.length < node.outputs.length - 1) return;
        const stale = node.outputs.slice(1).filter(s => !names.includes(s.name));
        const fresh = names.filter(k => !node.outputs.slice(1).some(s => s.name === k));
        if (stale.length === 1 && fresh.length === 1) stale[0].name = fresh[0];
        else for (const s of stale.reverse()) node.removeOutput(node.outputs.indexOf(s));
        for (const [i, name] of names.entries()) {
            let slot = node.outputs.slice(1).find(s => s.name === name);
            if (!slot) { node.addOutput(name, "STRING"); slot = node.outputs.at(-1); }
            node.outputs.splice(node.outputs.indexOf(slot), 1);
            node.outputs.splice(i + 1, 0, slot);
            slot.label = name;
            slot.slot_index = i + 1;
            for (const id of slot.links ?? []) {
                const link = node.graph?.links[id];
                if (link) link.origin_slot = i + 1;
            }
        }
    }
    node.setDirtyCanvas(true, true);
}

function syncMidCalc(node) {
    const widget = node.widgets.find(w => w.name === "num");
    const count = Math.min(widget.options.max, Math.max(1, Math.trunc(widget.value)));
    // Saved Number Range nodes had only two outputs and a STRING list in slot 1.
    if (node.outputs[1]?.type === "STRING") {
        node.disconnectOutput(1);
        node.outputs[0].name = "float";
        node.outputs[1].name = "int";
        node.outputs[1].type = "INT";
    }
    if (node.outputs.length === 2) node.addOutput("indices", "STRING");
    if (node.outputs[0]?.type === "FLOAT" && node.outputs[1]?.type === "INT") {
        [node.outputs[0], node.outputs[1]] = [node.outputs[1], node.outputs[0]];
        for (const i of [0, 1]) {
            node.outputs[i].slot_index = i;
            for (const id of node.outputs[i].links ?? []) {
                const link = node.graph?.links[id];
                if (link) link.origin_slot = i;
            }
        }
    }
    while (node.outputs.length > count + 3) node.removeOutput(node.outputs.length - 1);
    while (node.outputs.length < count + 3) node.addOutput(String(node.outputs.length - 2), "INT");
    node.setDirtyCanvas(true, true);
}

function setupPreview(node) {
    const box = document.createElement("div");
    box.style.cssText = "display:flex;flex-direction:column;height:100%;gap:4px";
    const text = document.createElement("textarea");
    text.readOnly = true;
    text.style.cssText = "flex:1;min-height:40px;resize:none;color:var(--input-text);background:var(--comfy-input-bg)";
    const bar = document.createElement("div");
    const count = document.createElement("span");
    let items = [], index = 0;
    const button = (label, click) => {
        const el = document.createElement("button");
        el.textContent = label;
        el.onclick = click;
        bar.append(el);
        return el;
    };
    const prev = button("‹", () => { index--; draw(); });
    bar.append(count);
    const next = button("›", () => { index++; draw(); });
    const copy = button("Copy", async () => {
        try { await navigator.clipboard.writeText(text.value); }
        catch { text.focus(); text.select(); document.execCommand("copy"); }
    });
    function draw() {
        text.value = items[index] ?? "";
        count.textContent = ` ${items.length ? index + 1 : 0} / ${items.length} `;
        prev.disabled = index <= 0;
        next.disabled = index + 1 >= items.length;
        copy.disabled = !items.length;
    }
    box.append(bar, text);
    node.addDOMWidget("preview", "vibenode-preview", box, { serialize: false });
    node.setSize([Math.max(node.size[0], 330), Math.max(node.size[1], 200)]);
    const executed = node.onExecuted;
    node.onExecuted = function (message) {
        executed?.call(this, message);
        items = message.prompts ?? [];
        index = 0;
        draw();
    };
    draw();
}

app.registerExtension({
    name: "Vibenode.Prompts",
    nodeCreated(node) {
        if (node.comfyClass === "VibenodeNumberRange") {
            const widget = node.widgets.find(w => w.name === "num");
            const callback = widget.callback;
            widget.callback = function (...args) {
                const result = callback?.apply(this, args);
                syncMidCalc(node);
                return result;
            };
            queueMicrotask(() => syncMidCalc(node));
        }
        if (node.comfyClass === "VibenodePromptPreview") setupPreview(node);
        const field = fields[node.comfyClass];
        if (!field) return;
        const widget = node.widgets.find(w => w.name === field);
        if (!widget) return;
        const refresh = () => sync(node, !!widget.inputEl && document.activeElement === widget.inputEl);
        const callback = widget.callback;
        widget.callback = function (...args) {
            const result = callback?.apply(this, args);
            refresh();
            return result;
        };
        widget.inputEl?.addEventListener("input", () => queueMicrotask(refresh));
        widget.inputEl?.addEventListener("blur", () => queueMicrotask(() => sync(node)));
        queueMicrotask(() => sync(node));
    },
    loadedGraphNode(node) {
        if (node.comfyClass === "VibenodeNumberRange") queueMicrotask(() => syncMidCalc(node));
        if (fields[node.comfyClass]) queueMicrotask(() => sync(node));
    },
});
