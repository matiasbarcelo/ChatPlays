const { app, BrowserWindow, ipcMain, screen } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

const API_PORT = 8765;

// The main view renders at a fixed 360px column; this is the content box that
// fits it end to end so the window opens with no scrollbar.
const MAIN_CONTENT_WIDTH = 400;
const MAIN_CONTENT_HEIGHT = 800;
const isDev = !app.isPackaged;

let pythonProcess = null;
let mainWindow = null;
let setupWindow = null;
let monitorWindow = null;

function projectRoot() {
  if (isDev) {
    // electron/ -> desktop/ -> repo root
    return path.join(__dirname, "..", "..");
  }
  return path.join(process.resourcesPath, "python");
}

function pythonExecutable() {
  const root = projectRoot();
  const venvCandidates = [
    path.join(root, "virt", "Scripts", "python.exe"),
    path.join(root, "virt", "bin", "python"),
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
  const root = projectRoot();
  const script = path.join(root, "api_server.py");
  const env = { ...process.env, PYTHONUNBUFFERED: "1" };
  delete env.PYTHONPATH;
  pythonProcess = spawn(pythonExecutable(), [script], {
    cwd: root,
    stdio: "inherit",
    env,
  });
  pythonProcess.on("exit", (code) => {
    console.log(`Python backend exited with code ${code}`);
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

function loadWindow(win, page) {
  if (isDev) {
    win.loadURL(`http://127.0.0.1:5173/${page}`);
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
    title: "Setup / Test (dev)",
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
    title: "Chat Monitor (prod)",
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
