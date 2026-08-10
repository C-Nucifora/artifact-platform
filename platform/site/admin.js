"use strict";

const state = {
  config: { version: 1, excluded_peers: [], peers: {} },
  revision: "",
  discovered: [],
  dirty: false,
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function field(labelText, name, value, placeholder) {
  const label = element("label", "peer-field");
  label.append(element("span", null, labelText));
  const input = element("input");
  input.name = name;
  input.value = value || "";
  input.placeholder = placeholder;
  input.setAttribute("aria-label", labelText);
  label.append(input);
  return label;
}

function peerIds() {
  const discovered = state.discovered.map((peer) => peer.dns_name).filter(Boolean);
  return [...new Set([...discovered, ...Object.keys(state.config.peers)])].sort();
}

function peerSource(peerId, rule) {
  const discovered = state.discovered.some((peer) => peer.dns_name === peerId);
  if (rule.manual && !discovered) return "manual";
  if (Object.keys(rule).length) return "overridden";
  return "discovered";
}

function peerRow(peerId) {
  const rule = state.config.peers[peerId] || {};
  const row = element("fieldset", "peer-editor-row");
  row.dataset.peerId = peerId;
  row.dataset.manual = rule.manual ? "true" : "false";
  row.dataset.testid = `peer-${peerId.replace(/[^a-z0-9]+/gi, "-").replace(/-$/, "")}`;

  const legend = element("legend");
  const identity = element("span", "peer-editor-identity");
  identity.append(element("strong", null, peerId.split(".")[0]));
  identity.append(element("span", null, peerId));
  legend.append(identity);
  legend.append(element("span", "badge", peerSource(peerId, rule)));
  row.append(legend);

  const fields = element("div", "peer-fields");
  fields.append(
    field("SSH target", "ssh_target", rule.ssh_target, "node.tailnet.ts.net"),
    field("Public HTTPS endpoint", "public_url", rule.public_url, "https://artifacts.example.com"),
    field(
      "Excluded artifact slugs",
      "excluded_artifacts",
      Array.isArray(rule.excluded_artifacts) ? rule.excluded_artifacts.join(", ") : "",
      "private-demo, internal",
    ),
  );
  row.append(fields);

  const controls = element("div", "peer-row-controls");
  const excludeLabel = element("label", "switch-control");
  const checkbox = element("input");
  checkbox.type = "checkbox";
  checkbox.name = "excluded";
  checkbox.checked = state.config.excluded_peers.includes(peerId);
  checkbox.setAttribute("aria-label", "Exclude peer");
  excludeLabel.append(checkbox, element("span", null, "Exclude peer"));
  controls.append(excludeLabel);

  if (rule.manual) {
    const remove = element("button", "text-button", "Remove manual peer");
    remove.type = "button";
    remove.addEventListener("click", () => {
      state.config = collectConfig();
      delete state.config.peers[peerId];
      markDirty();
      renderPeers();
    });
    controls.append(remove);
  }
  row.append(controls);
  return row;
}

function renderPeers() {
  const editor = document.getElementById("peer-editor");
  const ids = peerIds();
  if (!ids.length) {
    editor.replaceChildren(
      element("p", "empty-state", "No peers discovered yet. Add one manually or run discovery."),
    );
    return;
  }
  editor.replaceChildren(...ids.map(peerRow));
}

function setSaveState(message, mode = "") {
  const node = document.getElementById("save-state");
  node.textContent = message;
  node.className = `save-state ${mode}`.trim();
}

function markDirty() {
  state.dirty = true;
  setSaveState("Unsaved changes", "is-dirty");
}

function normalizedRule(row) {
  const rule = {};
  if (row.dataset.manual === "true") rule.manual = true;
  for (const name of ["ssh_target", "public_url"]) {
    const value = row.elements[name].value.trim();
    if (value) rule[name] = value;
  }
  const excluded = row.elements.excluded_artifacts.value
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  if (excluded.length) rule.excluded_artifacts = excluded;
  return rule;
}

function collectConfig() {
  const excluded = [];
  const peers = {};
  for (const row of document.querySelectorAll(".peer-editor-row")) {
    const peerId = row.dataset.peerId;
    if (row.elements.excluded.checked) excluded.push(peerId);
    const rule = normalizedRule(row);
    if (Object.keys(rule).length) peers[peerId] = rule;
  }
  return { version: 1, excluded_peers: excluded.sort(), peers };
}

async function loadConfig() {
  try {
    const response = await fetch("/api/admin/config", { cache: "no-store" });
    if (!response.ok) throw new Error("load failed");
    const payload = await response.json();
    state.config = payload.config;
    state.revision = payload.revision;
    state.discovered = Array.isArray(payload.discovered_peers) ? payload.discovered_peers : [];
    state.dirty = false;
    document.getElementById("revision-label").textContent = `Revision ${state.revision.slice(0, 8)}`;
    setSaveState("Configuration current", "is-saved");
    renderPeers();
  } catch {
    setSaveState("Configuration unavailable. Reload to retry.", "is-error");
  }
}

async function saveConfig(event) {
  event.preventDefault();
  setSaveState("Saving configuration");
  try {
    const response = await fetch("/api/admin/config", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "If-Match": `"${state.revision}"`,
      },
      body: JSON.stringify(collectConfig()),
    });
    if (response.status === 409) {
      setSaveState("Configuration changed elsewhere. Reload before saving.", "is-error");
      return;
    }
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "save failed");
    state.config = payload.config;
    state.revision = payload.revision;
    state.dirty = false;
    document.getElementById("revision-label").textContent = `Revision ${state.revision.slice(0, 8)}`;
    setSaveState("Configuration saved", "is-saved");
    renderPeers();
  } catch {
    setSaveState("Save failed. Check the fields and try again.", "is-error");
  }
}

function addManualPeer() {
  const input = document.getElementById("manual-peer-id");
  const error = document.getElementById("manual-peer-error");
  const peerId = input.value.trim().toLowerCase();
  if (!/^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$/.test(peerId)) {
    error.textContent = "Use a hostname-style identifier with letters, numbers, dots, or hyphens.";
    return;
  }
  if (peerIds().includes(peerId)) {
    error.textContent = "That peer already exists.";
    return;
  }
  error.textContent = "";
  state.config = collectConfig();
  state.config.peers[peerId] = { manual: true };
  input.value = "";
  markDirty();
  renderPeers();
  document.querySelector(`[data-peer-id="${CSS.escape(peerId)}"] input`).focus();
}

async function runDiscovery() {
  const button = document.getElementById("discover-now");
  button.disabled = true;
  try {
    const response = await fetch("/api/admin/discover", { method: "POST" });
    setSaveState(response.ok ? "Discovery pass queued" : "Discovery is already pending");
  } catch {
    setSaveState("Could not start discovery.", "is-error");
  } finally {
    button.disabled = false;
  }
}

document.getElementById("config-form").addEventListener("input", markDirty);
document.getElementById("config-form").addEventListener("submit", saveConfig);
document.getElementById("add-manual-peer").addEventListener("click", addManualPeer);
document.getElementById("discover-now").addEventListener("click", runDiscovery);
loadConfig();
