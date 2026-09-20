/**
 * OBS browser-source URLs, built in one place so dev and prod stay consistent.
 *
 * The `env` parameter is deliberate groundwork for the dev/prod split (see
 * DEV_PROD_SPLIT.md). Both values currently resolve to the same backend state —
 * it exists so links already pasted into OBS keep working once the split lands.
 */
const API_ORIGIN = "http://127.0.0.1:8765";

export const CHAT_OVERLAY_SIZE = "400 x 900";

export function chatOverlayUrl(env = "prod") {
  return `${API_ORIGIN}/overlay?env=${env}`;
}

export function controllerOverlayUrl(env = "prod") {
  return `${API_ORIGIN}/controller?env=${env}`;
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
