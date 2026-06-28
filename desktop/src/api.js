const DEFAULT_API = "http://127.0.0.1:8765";

export async function getApiBase() {
  if (window.chatplays?.getApiBase) {
    return window.chatplays.getApiBase();
  }
  return DEFAULT_API;
}

async function apiFetch(path, options = {}) {
  const base = await getApiBase();
  const response = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  getState: () => apiFetch("/api/state"),
  submitInput: (text) =>
    apiFetch("/api/setup/submit-input", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
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
};

export function connectStateSocket(onMessage) {
  let ws;
  let closed = false;

  async function connect() {
    const base = await getApiBase();
    const url = base.replace(/^http/, "ws") + "/ws";
    ws = new WebSocket(url);
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
