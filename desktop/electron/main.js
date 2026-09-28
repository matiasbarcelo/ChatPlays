const { app, BrowserWindow, ipcMain, screen } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const { pathToFileURL } = require("url");

const API_PORT = 8765;
const API_TOKEN = crypto.randomBytes(32).toString("hex");
const DEV_SERVER_URL = "http://127.0.0.1:5173";

// The main view renders at a fixed 360px column; this is the content box that
// fits it end to end so the window opens with no scrollbar.
const MAIN_CONTENT_WIDTH = 400;
const MAIN_CONTENT_HEIGHT = 800;
const isDev = !app.isPackaged;

const BACKEND_RESTART_DELAY_MS = 2000;
const BACKEND_QUICK_FAILURE_MS = 10000;
const BACKEND_MAX_QUICK_FAILURES = 5;

let pythonProcess = null;
let backendStartedAt = 0;
let backendQuickFailures = 0;
let backendStopping = false;
let mainWindow = null;
let setupWindow = null;
let monitorWindow = null;

// electron/ -> desktop/ -> repo root
const REPO_ROOT = path.join(__dirname, "..", "..");

function pythonExecutable() {
  const venvCandidates = [
    path.join(REPO_ROOT, "virt", "Scripts", "python.exe"),
    // MSYS/MinGW-created venvs use the POSIX layout but keep the .exe suffix
    path.join(REPO_ROOT, "virt", "bin", "python.exe"),
    path.join(REPO_ROOT, "virt", "bin", "python"),
  ];
  for (const candidate of venvCandidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  if (process.platform === "win32") {
    const localAppData = process.env.LOCALAPPDATA || "";
    const versionedCandidates = ["Python312", "Python311", "Python310"].map((folder) =>
      path.join(localAppData, "Programs", "Python", folder, "python.exe")
    );
    for (const candidate of versionedCandidates) {
      if (candidate && fs.existsSync(candidate)) return candidate;
    }
  }

  return process.platform === "win32" ? "python" : "python3";
}

function startPythonBackend() {
  if (backendStopping) return;
  const env = { ...process.env, PYTHONUNBUFFERED: "1", CHATPLAYS_API_TOKEN: API_TOKEN };
  delete env.PYTHONPATH;
  let child;

  if (isDev) {
    child = spawn(pythonExecutable(), [path.join(REPO_ROOT, "api_server.py")], {
      cwd: REPO_ROOT,
      stdio: "inherit",
      env,
    });
  } else {
    const userData = app.getPath("userData");
    const logDir = app.getPath("logs");
    fs.mkdirSync(userData, { recursive: true });
    fs.mkdirSync(logDir, { recursive: true });
    // Append after a restart so the crash that caused it stays in the log.
    const log = fs.openSync(path.join(logDir, "backend.log"), backendStartedAt ? "a" : "w");
    child = spawn(
      path.join(process.resourcesPath, "backend", "chatplays-backend.exe"),
      [],
      {
        cwd: userData,
        stdio: ["ignore", log, log],
        windowsHide: true,
        env: {
          ...env,
          CHATPLAYS_USER_DATA: userData,
          CHATPLAYS_FRONTEND_DIST: path.join(process.resourcesPath, "frontend"),
        },
      }
    );
    fs.closeSync(log);
  }

  pythonProcess = child;
  backendStartedAt = Date.now();
  child.on("exit", (code) => {
    console.log(`Python backend exited with code ${code}`);
    if (pythonProcess !== child) return;
    pythonProcess = null;
    if (backendStopping) return;

    // Keep a long-running stream alive through a crash, but stop retrying if
    // it dies immediately every time (e.g. the port is already in use).
    const quickFailure = Date.now() - backendStartedAt < BACKEND_QUICK_FAILURE_MS;
    backendQuickFailures = quickFailure ? backendQuickFailures + 1 : 0;
    if (backendQuickFailures >= BACKEND_MAX_QUICK_FAILURES) {
      console.log("Python backend keeps failing on startup; not restarting it.");
      return;
    }
    console.log("Restarting Python backend...");
    setTimeout(startPythonBackend, BACKEND_RESTART_DELAY_MS);
  });
}

function stopPythonBackend() {
  backendStopping = true;
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// Pages opened from inside the app (e.g. external help links) inherit the
// preload script, so only hand the API token to the app's own pages.
function isAppPage(url) {
  const appRoot = isDev
    ? `${DEV_SERVER_URL}/`
    : `${pathToFileURL(path.join(__dirname, "..", "dist")).href}/`;
  return typeof url === "string" && url.startsWith(appRoot);
}

function loadWindow(win, page) {
  if (isDev) {
    win.loadURL(`${DEV_SERVER_URL}/${page}`);
  } else {
    win.loadFile(path.join(__dirname, "../dist", page));
  }
}

function createMainWindow() {
  // Never open taller than the display's work area, or the OS shrinks the
  // window and the scrollbar comes back anyway.
  const { height: workAreaHeight } = screen.getPrimaryDisplay().workAreaSize;
  const contentHeight = Math.min(MAIN_CONTENT_HEIGHT, workAreaHeight);

  mainWindow = new BrowserWindow({
    width: MAIN_CONTENT_WIDTH,
    height: contentHeight,
    useContentSize: true,
    minWidth: 360,
    minHeight: Math.min(620, contentHeight),
    title: "ChatPlays",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  loadWindow(mainWindow, "index.html");
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function createSetupWindow() {
  if (setupWindow) {
    setupWindow.focus();
    return;
  }
  setupWindow = new BrowserWindow({
    width: 1060,
    height: 960,
    minWidth: 900,
    minHeight: 820,
    title: "Setup/Test ChatPlays Program",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  loadWindow(setupWindow, "setup.html");
  setupWindow.on("closed", () => {
    setupWindow = null;
  });
}

function createMonitorWindow() {
  if (monitorWindow) {
    monitorWindow.focus();
    return;
  }
  monitorWindow = new BrowserWindow({
    width: 520,
    height: 680,
    minWidth: 420,
    minHeight: 500,
    title: "Chat Monitor",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  loadWindow(monitorWindow, "monitor.html");
  monitorWindow.on("closed", () => {
    monitorWindow = null;
  });
}

app.whenReady().then(() => {
  ipcMain.handle("open-setup-window", () => {
    createSetupWindow();
  });

  ipcMain.handle("open-monitor-window", () => {
    createMonitorWindow();
  });

  ipcMain.handle("close-setup-window", () => {
    if (setupWindow) {
      setupWindow.close();
      setupWindow = null;
    }
    if (mainWindow) {
      mainWindow.focus();
    }
  });

  ipcMain.handle("get-api-base", () => `http://127.0.0.1:${API_PORT}`);

  ipcMain.handle("get-api-token", (event) =>
    isAppPage(event.senderFrame?.url) ? API_TOKEN : null
  );

  ipcMain.handle("get-file-icon", async (_event, filePath) => {
    if (!filePath || typeof filePath !== "string") return null;
    try {
      const icon = await app.getFileIcon(filePath, { size: "normal" });
      return icon.toDataURL();
    } catch {
      return null;
    }
  });

  startPythonBackend();
  createMainWindow();
});

app.on("window-all-closed", () => {
  stopPythonBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
});

app.on("before-quit", () => {
  stopPythonBackend();
});
