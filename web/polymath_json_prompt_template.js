import { app } from "../../scripts/app.js";

const NODE_NAME = "PM_JsonPrompt";

function extractPlaceholderKeys(template) {
  if (!template) return [];
  const re = /\{\{\s*\$json\[['\"]([^'\"]+)['\"]\]\.prompt\s*\}\}/g;
  const keys = new Set();
  let m;
  while ((m = re.exec(template)) !== null) {
    keys.add(m[1]);
  }
  return Array.from(keys);
}

function syncInputsFromTemplate(node) {
  const templateWidget = node.widgets?.find((w) => w.name === "template");
  const template = templateWidget?.value ?? "";
  const desiredKeys = extractPlaceholderKeys(template);

  // Remove internal backend placeholder input if it exists
  for (let i = (node.inputs?.length || 0) - 1; i >= 0; i--) {
    const inp = node.inputs[i];
    if (inp?.name === "_dyn") {
      node.removeInput(i);
    }
  }

  const existing = new Map();
  (node.inputs || []).forEach((inp, idx) => {
    existing.set(inp.name, { inp, idx });
  });

  let changed = false;

  for (const key of desiredKeys) {
    if (!existing.has(key)) {
      node.addInput(key, "STRING");
      changed = true;
    }
  }

  // Remove inputs that are no longer referenced only if they are not connected
  for (let i = (node.inputs?.length || 0) - 1; i >= 0; i--) {
    const inp = node.inputs[i];
    if (!desiredKeys.includes(inp.name) && inp.link == null) {
      node.removeInput(i);
      changed = true;
    }
  }

  if (changed) {
    node.setDirtyCanvas(true, true);
  }
}

app.registerExtension({
  name: "Polymath.JsonPromptTemplate",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated?.apply(this, arguments);

      const attach = () => {
        const templateWidget = this.widgets?.find((w) => w.name === "template");
        if (!templateWidget) return;

        const oldCb = templateWidget.callback;
        templateWidget.callback = (...args) => {
          const rr = oldCb?.apply(templateWidget, args);
          syncInputsFromTemplate(this);
          return rr;
        };

        syncInputsFromTemplate(this);
      };

      setTimeout(attach, 0);
      return r;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const r = onConfigure?.apply(this, arguments);
      setTimeout(() => syncInputsFromTemplate(this), 0);
      return r;
    };

    const onConnectionsChange = nodeType.prototype.onConnectionsChange;
    nodeType.prototype.onConnectionsChange = function () {
      const r = onConnectionsChange?.apply(this, arguments);
      syncInputsFromTemplate(this);
      return r;
    };
  },
});
