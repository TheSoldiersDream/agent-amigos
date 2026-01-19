/**
 * Agent Amigos - Electron Main Process
 * Copyright (c) 2025 Darrell Buttigieg. All Rights Reserved.
 * Owned and developed by Darrell Buttigieg.
 */
const {
  app,
  BrowserWindow,
  Tray,
  Menu,
  globalShortcut,
  ipcMain,
  session,
  shell,
} = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow;
let tray;
let backendProcess;

function createWindow() {
  const { screen } = require("electron");
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: Math.min(1600, width),
    height: Math.min(1000, height),
    show: true, // Start shown
    frame: true, // Enable window frame for dragging
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false, // For simple prototype
      webviewTag: true, // Enable <webview> tag for Mini Browser
    },
    resizable: true,
    alwaysOnTop: false, // Don't force on top by default for large window
    skipTaskbar: false, // Show in taskbar if tray is disabled
  });

  // Maximize if the screen is small
  if (width <= 1600) {
    mainWindow.maximize();
  }

  // Load the React app (in dev mode, localhost:5173, or build file)
  // For this scaffold, we'll load a simple HTML file if React isn't running
  mainWindow.loadURL("http://localhost:5173").catch(() => {
    mainWindow.loadFile(path.join(__dirname, "../frontend/index.html"));
  });

  // In Electron, anchors with target="_blank" won't necessarily open unless we handle it.
  // Route external links (bookmakers, docs, etc.) to the user's default browser.
  const isAppUrl = (url) => {
    if (!url) return false;
    return (
      url.startsWith("http://localhost:5173") ||
      url.startsWith("http://127.0.0.1:5173") ||
      url.startsWith("file:")
    );
  };

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      if (!isAppUrl(url)) {
        shell.openExternal(url);
        return { action: "deny" };
      }

      // Standalone app windows (RaceSight, Analytics, etc)
      // We allow them to be created as top-level windows that can be moved to other monitors.
      return {
        action: "allow",
        overrideBrowserWindowOptions: {
          width: 900,
          height: 850,
          autoHideMenuBar: true,
          title: "Agent Amigos Standalone Console",
          webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
          },
        },
      };
    } catch (_) {}
    return { action: "allow" };
  });

  mainWindow.webContents.on("will-navigate", (event, url) => {
    try {
      if (!isAppUrl(url)) {
        event.preventDefault();
        shell.openExternal(url);
      }
    } catch (_) {}
  });

  // Open DevTools for debugging (remove in production)
  mainWindow.webContents.openDevTools({ mode: "detach" });

  // Removed blur handler - was hiding window when clicking outside
}

function startBackend() {
  // Start the Python FastAPI backend
  const backendPath = path.join(__dirname, "../backend/agent_init.py");
  const venvPython = path.join(__dirname, "../backend/venv/Scripts/python.exe");
  const pythonExec = require("fs").existsSync(venvPython)
    ? venvPython
    : "python";

  console.log("Starting backend from:", backendPath, "using", pythonExec);

  backendProcess = spawn(pythonExec, [backendPath]);

  backendProcess.stdout.on("data", (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`Backend Error: ${data}`);
  });
}

app.whenReady().then(() => {
  // Grant microphone permission automatically
  session.defaultSession.setPermissionRequestHandler(
    (webContents, permission, callback) => {
      const allowedPermissions = ["media", "microphone", "audioCapture"];
      if (allowedPermissions.includes(permission)) {
        console.log(`Granting permission: ${permission}`);
        callback(true);
      } else {
        callback(false);
      }
    }
  );

  // Backend is started separately, don't start here to avoid port conflicts
  // startBackend();
  createWindow();

  // System Tray
  /*
  tray = new Tray(path.join(__dirname, 'icon.ico')); // Placeholder icon
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show Agent Amigos', click: () => mainWindow.show() },
    { label: 'Quit', click: () => app.quit() }
  ]);
  tray.setToolTip('Agent Amigos (2025)');
  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    toggleWindow();
  });
  */

  // Global Hotkey
  globalShortcut.register("CommandOrControl+Alt+A", () => {
    toggleWindow();
  });
});

function toggleWindow() {
  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    // Position window near tray or center
    mainWindow.show();
    mainWindow.focus();
  }
}

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  if (backendProcess) {
    backendProcess.kill();
  }
});
