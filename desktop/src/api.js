const DEFAULT_API = "http://127.0.0.1:8765";
const TOKEN_HEADER = "X-ChatPlays-Token";
const TOKEN_STORAGE_KEY = "chatplays-api-token";

export async function getApiBase() {
  if (window.chatplays?.getApiBase) {
    return window.chatplays.getApiBase();
  }
  return DEFAULT_API;
}

let tokenPromise = null;

async function loadApiToken() {
  if (window.chatplays?.getApiToken) {
    return (await window.chatplays.getApiToken()) || "";
  }
  // Browser-only dev: a standalone api_server.py prints a link carrying ?token=.
  const fromUrl = new URLSearchParams(window.location.search).get("token");
  try {
    if (fromUrl) localStorage.setItem(TOKEN_STORAGE_KEY, fromUrl);
    return fromUrl || localStorage.getItem(TOKEN_STORAGE_KEY) || "";
  } catch {
    return fromUrl || "";
  }
}

function getApiToken() {
  if (!tokenPromise) tokenPromise = loadApiToken();
  return tokenPromise;
}

async function apiFetch(path, options = {}) {
  const [base, token] = await Promise.all([getApiBase(), getApiToken()]);
  const { headers, ...rest } = options;
  const response = await fetch(`${base}${path}`, {
    ...rest,
    headers: { "Content-Type": "application/json", [TOKEN_HEADER]: token, ...headers },
  });
  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  getState: () => apiFetch("/api/state"),
  getOverlayState: () => apiFetch("/api/overlay/state"),
  submitInput: (text) =>
    apiFetch("/api/setup/submit-input", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  startFakeChatRoll: (count = 0) =>
    apiFetch("/api/setup/fake-chat-roll", {
      method: "POST",
      body: JSON.stringify({ count }),
    }),
  stopFakeChatRoll: () =>
    apiFetch("/api/setup/fake-chat-roll/stop", { method: "POST" }),
  controllerButton: (button) =>
    apiFetch("/api/setup/controller-button", {
      method: "POST",
      body: JSON.stringify({ button }),
    }),
  generalSetup: () => apiFetch("/api/setup/general-setup", { method: "POST" }),
  manualSetup: () => apiFetch("/api/setup/manual-setup", { method: "POST" }),
  cancelManualSetup: () =>
    apiFetch("/api/setup/manual-setup/cancel", { method: "POST" }),
  scanEmulator: () => apiFetch("/api/setup/scan-emulator", { method: "POST" }),
  scanMainEmulator: () => apiFetch("/api/main/scan-emulator", { method: "POST" }),
  listWindows: () => apiFetch("/api/windows"),
  selectSetupEmulatorWindow: (window) =>
    apiFetch("/api/setup/select-emulator-window", {
      method: "POST",
      body: JSON.stringify({ window }),
    }),
  selectMainEmulatorWindow: (window) =>
    apiFetch("/api/main/select-emulator-window", {
      method: "POST",
      body: JSON.stringify({ window }),
    }),
  autoLinkEmulator: () => apiFetch("/api/setup/auto-link", { method: "POST" }),
  toggleDemocracyTimer: () =>
    apiFetch("/api/setup/toggle-democracy-timer", { method: "POST" }),
  toggleSetupMode: () => apiFetch("/api/setup/toggle-mode", { method: "POST" }),
  updateSetupSettings: (payload) =>
    apiFetch("/api/setup/settings", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateKeyBinding: (input_name, key) =>
    apiFetch("/api/setup/key-binding", {
      method: "POST",
      body: JSON.stringify({ input_name, key }),
    }),
  resetVirtualBindings: () =>
    apiFetch("/api/setup/reset-virtual-bindings", { method: "POST" }),
  toggleDisabledInput: (input_name) =>
    apiFetch("/api/setup/toggle-disabled-input", {
      method: "POST",
      body: JSON.stringify({ input_name }),
    }),
  togglePower: () => apiFetch("/api/main/toggle-power", { method: "POST" }),
  updateMainSettings: (payload) =>
    apiFetch("/api/main/settings", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  verifyUsername: (username, platform = "twitch") => {
    const params = new URLSearchParams({ username, platform });
    return apiFetch(`/api/main/verify-username?${params}`);
  },
};

export function connectStateSocket(onMessage, { overlay = false } = {}) {
  let ws;
  let closed = false;

  async function connect() {
    const [base, token] = await Promise.all([getApiBase(), overlay ? "" : getApiToken()]);
    if (closed) return;
    const url = base.replace(/^http/, "ws") + (overlay ? "/ws/overlay" : "/ws");
    ws = new WebSocket(url);
    if (!overlay) {
      ws.onopen = () => ws.send(token);
    }
    ws.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch (error) {
        console.error("WebSocket parse error", error);
      }
    };
    ws.onclose = () => {
      if (!closed) setTimeout(connect, 1000);
    };
  }

  connect();

  return () => {
    closed = true;
    ws?.close();
  };
}
