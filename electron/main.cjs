const { app, BrowserWindow, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");

let mainWindow;
let backendProcess;
let frontendProcess;

const BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health";
const FRONTEND_URL = "http://localhost:3000/chat";
const FRONTEND_READY_URL = "http://localhost:3000";

function waitForUrl(url, timeoutMs = 120000) {
  const start = Date.now();

  return new Promise((resolve, reject) => {
    function check() {
      http
        .get(url, (res) => {
          res.resume();
          console.log(`READY: ${url}`);
          resolve(true);
        })
        .on("error", () => {
          if (Date.now() - start > timeoutMs) {
            reject(new Error(`Timed out waiting for ${url}`));
            return;
          }
          setTimeout(check, 1000);
        });
    }

    check();
  });
}

function showPage(title, message, bg = "#111") {
  if (!mainWindow) return;

  mainWindow.loadURL(
    "data:text/html;charset=utf-8," +
      encodeURIComponent(`
        <html>
          <body style="margin:0;background:${bg};color:white;font-family:Arial;display:flex;align-items:center;justify-content:center;height:100vh;">
            <div style="text-align:center;max-width:360px;padding:20px;">
              <h2>${title}</h2>
              <p style="white-space:pre-wrap;line-height:1.5;">${message}</p>
            </div>
          </body>
        </html>
      `)
  );
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 460,
    height: 720,
    minWidth: 420,
    minHeight: 600,
    title: "S.A.I",
    autoHideMenuBar: true,
    backgroundColor: "#111111",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  showPage("S.A.I is starting...", "Starting backend and desktop interface.");

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

function startBackend() {
  const pythonPath = path.join(process.cwd(), ".venv", "Scripts", "python.exe");

  console.log("Python path:", pythonPath);

  backendProcess = spawn(
    pythonPath,
    ["-m", "uvicorn", "src.server:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: process.cwd(),
      shell: false,
      env: process.env,
    }
  );

  backendProcess.stdout.on("data", (data) => {
    console.log("[backend]", data.toString());
  });

  backendProcess.stderr.on("data", (data) => {
    console.error("[backend error]", data.toString());
  });

  backendProcess.on("exit", (code) => {
    console.log("[backend exited]", code);
  });
}

function startFrontend() {
  console.log("Starting frontend through Windows cmd...");

  frontendProcess = spawn("cmd.exe", ["/c", "npm", "run", "dev"], {
    cwd: process.cwd(),
    shell: false,
    env: {
      ...process.env,
      NEXT_PUBLIC_BACKEND_URL: "http://127.0.0.1:8000",
    },
  });

  frontendProcess.stdout.on("data", (data) => {
    console.log("[frontend]", data.toString());
  });

  frontendProcess.stderr.on("data", (data) => {
    console.error("[frontend error]", data.toString());
  });

  frontendProcess.on("error", (err) => {
    console.error("[frontend failed to start]", err);
    showPage("Frontend failed to start", err.message, "#300");
  });

  frontendProcess.on("exit", (code) => {
    console.log("[frontend exited]", code);
  });
}

app.whenReady().then(async () => {
  console.log("Creating S.A.I window...");
  createWindow();

  console.log("Starting backend...");
  showPage("S.A.I is starting...", "Starting Python backend...");
  startBackend();

  try {
    console.log("Waiting for backend...");
    await waitForUrl(BACKEND_HEALTH_URL);
  } catch (err) {
    console.error("Backend startup failed:", err.message);
    showPage("S.A.I backend failed", err.message, "#300");
    return;
  }

  console.log("Starting frontend...");
  showPage("S.A.I is starting...", "Starting frontend interface...");
  startFrontend();

  try {
    console.log("Waiting for frontend...");
    await waitForUrl(FRONTEND_READY_URL);

    console.log("Loading S.A.I chat...");
    mainWindow.loadURL(FRONTEND_URL);
  } catch (err) {
    console.error("Frontend startup failed:", err.message);
    showPage("S.A.I frontend failed", err.message, "#300");
  }
});

app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill();
  if (frontendProcess) frontendProcess.kill();

  if (process.platform !== "darwin") {
    app.quit();
  }
});