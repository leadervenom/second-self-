const { app, BrowserWindow, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const fs = require("fs");

let mainWindow;
let backendProcess;
let frontendProcess;
let staticServer;

const BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health";

const DEV_FRONTEND_READY_URL = "http://localhost:3000";
const DEV_FRONTEND_URL = "http://localhost:3000/chat";

const PROD_FRONTEND_READY_URL = "http://127.0.0.1:3000";
const PROD_FRONTEND_URL = "http://127.0.0.1:3000/chat.html";

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

function getResourcePath(...parts) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, ...parts);
  }

  return path.join(process.cwd(), ...parts);
}

function startBackend() {
  if (app.isPackaged) {
    const backendExe = getResourcePath("backend", "sai-backend.exe");

    console.log("Packaged backend path:", backendExe);

    if (!fs.existsSync(backendExe)) {
      throw new Error(`Backend exe not found: ${backendExe}`);
    }

    backendProcess = spawn(backendExe, [], {
      cwd: path.dirname(backendExe),
      shell: false,
      env: process.env,
    });
  } else {
    const pythonPath = path.join(process.cwd(), ".venv", "Scripts", "python.exe");

    console.log("Dev Python path:", pythonPath);

    backendProcess = spawn(
      pythonPath,
      ["-m", "uvicorn", "src.server:app", "--host", "127.0.0.1", "--port", "8000"],
      {
        cwd: process.cwd(),
        shell: false,
        env: process.env,
      }
    );
  }

  backendProcess.stdout.on("data", (data) => {
    console.log("[backend]", data.toString());
  });

  backendProcess.stderr.on("data", (data) => {
    console.error("[backend error]", data.toString());
  });

  backendProcess.on("error", (err) => {
    console.error("[backend failed]", err);
    showPage("Backend failed", err.message, "#300");
  });

  backendProcess.on("exit", (code) => {
    console.log("[backend exited]", code);
  });
}

function contentType(filePath) {
  if (filePath.endsWith(".html")) return "text/html";
  if (filePath.endsWith(".js")) return "application/javascript";
  if (filePath.endsWith(".css")) return "text/css";
  if (filePath.endsWith(".json")) return "application/json";
  if (filePath.endsWith(".png")) return "image/png";
  if (filePath.endsWith(".jpg") || filePath.endsWith(".jpeg")) return "image/jpeg";
  if (filePath.endsWith(".gif")) return "image/gif";
  if (filePath.endsWith(".svg")) return "image/svg+xml";
  if (filePath.endsWith(".ico")) return "image/x-icon";
  if (filePath.endsWith(".txt")) return "text/plain";
  return "application/octet-stream";
}

function startStaticFrontendServer() {
  const frontendDir = getResourcePath("frontend");

  console.log("Static frontend path:", frontendDir);

  if (!fs.existsSync(frontendDir)) {
    throw new Error(`Frontend folder not found: ${frontendDir}`);
  }

  staticServer = http.createServer((req, res) => {
    let reqPath = decodeURIComponent(req.url.split("?")[0]);

    if (reqPath === "/") {
      reqPath = "/index.html";
    }

    if (reqPath === "/chat") {
      reqPath = "/chat.html";
    }

    if (reqPath.endsWith("/")) {
      reqPath += "index.html";
    }

    let filePath = path.join(frontendDir, reqPath);

    if (!filePath.startsWith(frontendDir)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    if (!fs.existsSync(filePath)) {
      const htmlFallback = path.join(frontendDir, `${reqPath}.html`);
      const indexFallback = path.join(frontendDir, "index.html");

      if (fs.existsSync(htmlFallback)) {
        filePath = htmlFallback;
      } else if (fs.existsSync(indexFallback)) {
        filePath = indexFallback;
      } else {
        res.writeHead(404);
        res.end("Not found");
        return;
      }
    }

    res.writeHead(200, { "Content-Type": contentType(filePath) });
    fs.createReadStream(filePath).pipe(res);
  });

  staticServer.listen(3000, "127.0.0.1", () => {
    console.log("Static frontend server running on http://127.0.0.1:3000");
  });
}

function startDevFrontend() {
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
    console.error("[frontend failed]", err);
    showPage("Frontend failed", err.message, "#300");
  });

  frontendProcess.on("exit", (code) => {
    console.log("[frontend exited]", code);
  });
}

app.whenReady().then(async () => {
  console.log("Creating S.A.I window...");
  createWindow();

  try {
    console.log("Starting backend...");
    showPage("S.A.I is starting...", "Starting Python backend...");
    startBackend();

    console.log("Waiting for backend...");
    await waitForUrl(BACKEND_HEALTH_URL);

    if (app.isPackaged) {
      console.log("Starting packaged static frontend...");
      showPage("S.A.I is starting...", "Starting packaged interface...");
      startStaticFrontendServer();

      await waitForUrl(PROD_FRONTEND_READY_URL);
      mainWindow.loadURL(PROD_FRONTEND_URL);
    } else {
      console.log("Starting dev frontend...");
      showPage("S.A.I is starting...", "Starting frontend interface...");
      startDevFrontend();

      await waitForUrl(DEV_FRONTEND_READY_URL);
      mainWindow.loadURL(DEV_FRONTEND_URL);
    }
  } catch (err) {
    console.error("S.A.I startup failed:", err.message);
    showPage("S.A.I failed to start", err.message, "#300");
  }
});

app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill();
  if (frontendProcess) frontendProcess.kill();
  if (staticServer) staticServer.close();

  if (process.platform !== "darwin") {
    app.quit();
  }
});