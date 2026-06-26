const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

const API_PORT = 8765;
const isDev = !app.isPackaged;

let pythonProcess = null;
let mainWindow = null;
let setupWindow = null;

function projectRoot() {
  if (isDev) {
    // electron/ -> desktop/ -> repo root
    return path.join(__dirname, "..", "..");
  }
  return path.join(process.resourcesPath, "python");
}

function pythonExecutable() {
  const root = projectRoot();
  const venvPython = path.join(root, "virt", "bin", "python");
  if (fs.existsSync(venvPython)) return venvPython;
  return process.platform === "win32" ? "python" : "python3";
}

function startPythonBackend() {
  const root = projectRoot();
  const script = path.join(root, "api_server.py");
  pythonProcess = spawn(pythonExecutable(), [script], {
    cwd: root,
    stdio: "inherit",
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
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
  mainWindow = new BrowserWindow({
    width: 380,
    height: 560,
    minWidth: 340,
    minHeight: 520,
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
    width: 860,
    height: 680,
    minWidth: 780,
    minHeight: 600,
    title: "Test/Setup ChatPlays Program",
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

app.whenReady().then(() => {
  ipcMain.handle("open-setup-window", () => {
    createSetupWindow();
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
