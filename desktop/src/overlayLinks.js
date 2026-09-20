/** OBS browser-source URLs, built in one place so every window agrees. */
const API_ORIGIN = "http://127.0.0.1:8765";

export const CHAT_OVERLAY_SIZE = "400 x 900";

export function chatOverlayUrl() {
  return `${API_ORIGIN}/overlay`;
}

export function controllerOverlayUrl() {
  return `${API_ORIGIN}/controller`;
}

export function overlayTitle(url, size) {
  return `${url}\nOBS browser source — set size to ${size}`;
}

export async function copyOverlayUrl(url, setCopied) {
  try {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  } catch {
    /* clipboard unavailable */
  }
}
