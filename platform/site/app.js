"use strict";

const SAFE_PATH = /^\/artifacts\/[a-z0-9][a-z0-9-]*\/$/;

async function fetchJson(url) {
  try {
    const response = await fetch(url, { cache: "no-cache" });
    if (!response.ok) return { ok: false, data: null };
    return { ok: true, data: await response.json() };
  } catch {
    return { ok: false, data: null };
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function validArtifacts(document) {
  return document && Array.isArray(document.artifacts)
    ? document.artifacts.filter((artifact) => artifact && typeof artifact === "object")
    : [];
}

function safePublicUrl(value) {
  if (typeof value !== "string") return "";
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" ? parsed.origin + parsed.pathname.replace(/\/$/, "") : "";
  } catch {
    return "";
  }
}

function artifactHref(artifact, baseUrl) {
  const slug = typeof artifact.slug === "string" ? artifact.slug : "";
  const proposed = typeof artifact.path === "string" ? artifact.path : `/artifacts/${slug}/`;
  if (!SAFE_PATH.test(proposed)) return "";
  if (!baseUrl) return proposed;
  const safeBase = safePublicUrl(baseUrl);
  return safeBase ? safeBase + proposed : "";
}

function launchControl() {
  const control = element("span", "launch-control", "OPEN");
  control.append(element("span", "launch-mark"));
  return control;
}

function artifactRow(artifact, baseUrl, index) {
  const title =
    (typeof artifact.title === "string" && artifact.title) ||
    (typeof artifact.slug === "string" && artifact.slug) ||
    "Untitled artifact";
  const href = artifactHref(artifact, baseUrl);
  const row = element(href ? "a" : "div", "artifact-row");
  if (href) {
    row.href = href;
    row.setAttribute("aria-label", `Open ${title}`);
  }

  row.append(element("span", "artifact-index", String(index + 1).padStart(2, "0")));
  const copy = element("div", "artifact-copy");
  copy.append(element("div", "artifact-title", title));
  if (typeof artifact.description === "string" && artifact.description) {
    copy.append(element("p", "artifact-description", artifact.description));
  }
  row.append(copy);
  if (href) row.append(launchControl());
  return row;
}

function emptyState(title, detail) {
  const state = element("div", "empty-state");
  state.append(element("strong", null, title));
  const message = element("span");
  message.append(...detail);
  state.append(message);
  return state;
}

function renderLocal(manifest) {
  const container = document.getElementById("local");
  const artifacts = validArtifacts(manifest);
  if (!artifacts.length) {
    const command = element("code", null, "scripts/new-artifact.sh <slug>");
    container.replaceChildren(
      emptyState("No local artifacts", ["Scaffold the first one with ", command, "."]),
    );
    return artifacts;
  }
  container.replaceChildren(...artifacts.map((artifact, index) => artifactRow(artifact, "", index)));
  return artifacts;
}

function peerGroup(peer) {
  const section = element("section", "peer-group");
  const header = element("header", "peer-header");
  const identity = element("div");
  identity.append(element("h3", "peer-name", peer.hostname || "Unknown node"));
  identity.append(element("div", "peer-dns", peer.dns_name || "Identity unavailable"));
  header.append(identity);

  const badges = element("div", "peer-badges");
  const state = typeof peer.state === "string" ? peer.state : "online";
  badges.append(element("span", `badge badge-${state}`, state));
  if (typeof peer.source === "string") badges.append(element("span", "badge", peer.source));
  header.append(badges);
  section.append(header);

  const artifacts = validArtifacts(peer);
  if (!artifacts.length) {
    section.append(emptyState("No published artifacts", ["This node is connected but currently empty."]));
  } else {
    const list = element("div", "artifact-list");
    list.append(...artifacts.map((artifact, index) => artifactRow(artifact, peer.url, index)));
    section.append(list);
  }
  return section;
}

function renderPeers(peerDocument) {
  const container = document.getElementById("peers");
  const peers = peerDocument && Array.isArray(peerDocument.peers)
    ? peerDocument.peers.filter((peer) => peer && typeof peer === "object")
    : [];
  if (!peers.length) {
    container.replaceChildren(
      emptyState("No peer signal", ["Eligible nodes appear after the next discovery pass."]),
    );
    return peers;
  }
  container.replaceChildren(...peers.map(peerGroup));
  return peers;
}

function formatTime(value) {
  if (typeof value !== "string") return "Pending";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "Pending";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function renderTopology(peerCount) {
  const track = document.getElementById("mesh-track");
  track.querySelectorAll(".mesh-node").forEach((node) => node.remove());
  const visibleNodes = Math.min(peerCount, 5);
  for (let index = 0; index < visibleNodes; index += 1) {
    const node = element("span", "mesh-node");
    node.style.left = `${22 + index * (70 / Math.max(visibleNodes, 1))}%`;
    node.dataset.label = String(index + 1).padStart(2, "0");
    track.append(node);
  }
}

function updateSummary(manifestResult, peersResult, localArtifacts, peers) {
  const remoteCount = peers.reduce((total, peer) => total + validArtifacts(peer).length, 0);
  const total = localArtifacts.length + remoteCount;
  document.getElementById("artifact-count").textContent = `${total} ${total === 1 ? "artifact" : "artifacts"}`;
  document.getElementById("node-count").textContent = String(peers.length + 1);
  document.getElementById("last-sync").textContent = formatTime(
    peersResult.data?.generated_at || manifestResult.data?.generated_at,
  );
  document.getElementById("mesh-channel").textContent = `CH ${String(peers.length + 1).padStart(2, "0")}`;
  document.getElementById("mesh-readout").textContent = peers.length
    ? `${peers.length} peer ${peers.length === 1 ? "link" : "links"} responding`
    : "Local node standing by";
  renderTopology(peers.length);
}

async function loadCatalog() {
  const [manifestResult, peersResult] = await Promise.all([
    fetchJson("/manifest.json"),
    fetchJson("/peers.json"),
  ]);

  const localArtifacts = renderLocal(manifestResult.data);
  const peers = renderPeers(peersResult.data);
  const device = manifestResult.data?.device;
  if (device && typeof device.dns_name === "string" && device.dns_name) {
    document.getElementById("device-name").textContent = device.dns_name;
  } else {
    document.getElementById("device-name").textContent = "Local identity pending";
  }

  const healthy = manifestResult.ok && peersResult.ok;
  document.getElementById("degraded-state").hidden = healthy;
  document.getElementById("connection-state").classList.toggle("is-degraded", !healthy);
  document.getElementById("connection-label").textContent = healthy ? "Mesh synchronized" : "Signal degraded";
  document.getElementById("footer-status").textContent = healthy
    ? "Discovery nominal"
    : "Automatic retry armed";
  updateSummary(manifestResult, peersResult, localArtifacts, peers);
}

loadCatalog();
