const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("chatplays", {
  openSetupWindow: () => ipcRenderer.invoke("open-setup-window"),
  closeSetupWindow: () => ipcRenderer.invoke("close-setup-window"),
  openMonitorWindow: () => ipcRenderer.invoke("open-monitor-window"),
  getApiBase: () => ipcRenderer.invoke("get-api-base"),
  getApiToken: () => ipcRenderer.invoke("get-api-token"),
  getFileIcon: (filePath) => ipcRenderer.invoke("get-file-icon", filePath),
  isElectron: true,
});
