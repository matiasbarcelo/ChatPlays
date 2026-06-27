/** Open the setup/test window (Electron second window, or browser popup in Vite-only dev). */
export async function openSetupWindow() {
  if (window.chatplays?.openSetupWindow) {
    await window.chatplays.openSetupWindow();
    return;
  }

  const url = new URL("/setup.html", window.location.origin).href;
  const opened = window.open(
    url,
    "chatplays-setup",
    "width=1060,height=800,menubar=no,toolbar=no",
  );

  if (!opened) {
    window.location.assign(url);
  }
}

/** Return to the main ChatPlays window. */
export async function closeSetupWindow() {
  if (window.chatplays?.closeSetupWindow) {
    await window.chatplays.closeSetupWindow();
    return;
  }

  if (window.opener) {
    window.close();
    return;
  }

  window.location.assign(new URL("/", window.location.origin).href);
}

export function isElectronApp() {
  return Boolean(window.chatplays?.isElectron);
}
