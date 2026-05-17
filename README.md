# S.A.I (Second Self) - Windows Fork

This repository is a **Windows-adapted fork** of the original project by `23jomo`.

This fork focuses on a practical goal:
- run reliably on Windows
- keep a lightweight assistant loop (onboard + chat + safe local actions)
- skip macOS-specific systems and heavy deep-memory features during normal use

---

## What This Project Is (Current Reality)

S.A.I on this branch is a **Windows desktop/web assistant runtime** made of:
- **Python FastAPI backend** (`src/server.py`)
- **Next.js frontend** (`src/app/*`)
- **Electron shell** (`electron/main.cjs`) for desktop packaging

The active flow is:
1. User opens UI (web or Electron)
2. UI calls backend `/onboard` and `/chat`
3. Backend returns a demo profile and handles chat/tool routing
4. Optional Gemini responses are used when API key is present

---

## What Works

### Core runtime
- Windows setup script: `setup-windows.ps1`
- Backend start script: `start-backend.ps1`
- Frontend start script: `start-frontend.ps1`
- Health endpoint: `GET /health`
- Onboard endpoint: `POST /onboard`
- Chat endpoint: `POST /chat`

### Local tool actions (when enabled)
If `ALLOW_LOCAL_TOOLS=true`, chat can trigger safe local actions:
- open URLs (Google, YouTube, GitHub, ChatGPT)
- open common apps from an allowlist (Notepad, VS Code, Chrome, Edge, etc.)
- search local folders/files under a safe root
- open matching folders/files (optionally in VS Code)
- launch a workspace bundle (`open my workspace`) using `.env` toggles

### Packaging path
- PyInstaller backend entrypoint exists (`backend_launcher.py`, `sai-backend.spec`)
- Electron build config packages backend exe + static frontend into `release/`

---

## What Is Not Working / Intentionally Disabled

### Disabled in this Windows fork (by design)
- **Voice feature is not active** in the Windows runtime
- **Email reading/sending flow is not active** in the current runtime path
- Original macOS notch app stack is not part of this Windows runtime

### Not wired into active server path
These modules exist but are not the default runtime path for `start-backend.ps1`:
- deep Gmail/Calendar/Tavily memory pipeline
- rich profile generation + full "digital twin memory layers"
- old auth/session routes used in earlier server versions

### UI note
- The repo contains a Next.js UI for this branch.
- If you are using your own external/custom UI, treat this bundled UI as reference/testing UI.

---

## Hidden but Important Features

These are easy to miss but useful:
- **Safe path guardrails**: local file/folder opening is constrained by `SAFE_SEARCH_ROOT`
- **Search limits**: `MAX_SEARCH_DEPTH` and `MAX_SEARCH_ITEMS` prevent runaway scans
- **Command routing layers**:
  - deterministic phrase router first
  - optional AI JSON tool router second
  - normal Gemini chat fallback last
- **Session URL memory**: supports follow-up commands like `open it`
- **Workspace macro flags**:
  - `WORKSPACE_OPEN_YOUTUBE`
  - `WORKSPACE_OPEN_VSCODE`
  - `WORKSPACE_OPEN_CHATGPT`
  - `WORKSPACE_OPEN_GITHUB`
  - `WORKSPACE_OPEN_ELEARNING`

---

## Quick Start (Windows)

From project root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup-windows.ps1
```

Start backend:

```powershell
.\start-backend.ps1
```

Start frontend in a new terminal:

```powershell
.\start-frontend.ps1
```

Open:

```text
http://localhost:3000
```

Optional backend check:

```powershell
.\test-backend.ps1
```

---

## Build Windows Desktop App

Generated desktop files are **not committed** to GitHub.

Do **not** commit generated build outputs such as:

```text
release/
release2/
out/
dist/
installer-output/
*.exe
*.asar
*.zip
*.dll
*.pak
```

Each developer must build the Windows app locally after cloning the repository.

---

### 1. Setup

From the project root, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup-windows.ps1
```

This installs the required Python and Node dependencies.

---

### 2. Configure `.env`

Create `.env`:

```powershell
copy .env.example .env
```

If `.env.example` does not exist, use the Windows demo file instead:

```powershell
copy .env.windows.demo .env
```

Then edit the file:

```powershell
notepad .env
```

Minimum values:

```env
HOST=127.0.0.1
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

ALLOW_LOCAL_TOOLS=true
SAFE_SEARCH_ROOT=C:\Users
GITHUB_USERNAME=yourgithubusername
```

Each user should use their own Gemini API key.

---

### 3. Build the app

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build-windows.ps1
```

This creates:

```text
dist\sai-backend.exe
out\
release\win-unpacked\S.A.I.exe
```

---

### 4. Run the app

Run:

```powershell
.\release\win-unpacked\S.A.I.exe
```

If the app launches correctly, S.A.I should start its packaged backend and packaged frontend automatically.

---

### 5. Share the app

Do **not** send only:

```text
S.A.I.exe
```

The `.exe` depends on the files beside it inside `win-unpacked`.

Zip the whole `win-unpacked` folder:

```powershell
Compress-Archive -Path .\release\win-unpacked\* -DestinationPath .\SAI-windows-test.zip -Force
```

Send:

```text
SAI-windows-test.zip
```

The user must:

```text
1. Extract the zip fully.
2. Open the extracted folder.
3. Run S.A.I.exe from inside that folder.
```

---

## If Build Fails Because `app.asar` Is Locked

This usually means S.A.I, Electron, Node, or the backend is still running.

Close S.A.I first.

Then run:

```powershell
taskkill /IM "S.A.I.exe" /F
taskkill /IM "electron.exe" /F
taskkill /IM "sai-backend.exe" /F
taskkill /IM "node.exe" /F
```

Then rebuild:

```powershell
.\build-windows.ps1
```

If it still fails, restart the laptop and run `build-windows.ps1` before opening S.A.I.

---

## Environment (Practical)

Minimum useful keys:

```env
HOST=127.0.0.1
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
ALLOW_LOCAL_TOOLS=true
SAFE_SEARCH_ROOT=C:\Users\<you>
```

For model responses:

```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

You can change the model if needed, but stronger models may cost more.

If `GEMINI_API_KEY` is missing, chat still runs but returns a "key not connected" style response when it needs model output.

---

## API Summary

- `GET /health`
  - status, Gemini connection flag, model name, local-tools flag, safe root
- `POST /onboard`
  - returns a Windows demo profile object
- `POST /chat`
  - executes deterministic/AI-routed safe actions or falls back to Gemini text response

---

## Project Structure (Important Files)

- `src/server.py` - active Windows backend
- `electron/main.cjs` - Electron startup + process orchestration
- `src/app/*` - Next.js UI routes
- `src/components/wizard/*` - onboarding flow UI
- `src/components/chat/*` - chat UI
- `backend_launcher.py` - PyInstaller backend entrypoint
- `setup-windows.ps1` - dependency/bootstrap script
- `build-windows.ps1` - builds backend exe, static frontend, and Electron unpacked app
- `start-backend.ps1` - backend runner
- `start-frontend.ps1` - frontend runner
- `src/server_original.py` and `src/server_before_*.py` - legacy/transition snapshots

---

## Commit Source Files Only

After updating the build script and README, commit only source/config files:

```powershell
git add README.md build-windows.ps1 .gitignore
git commit -m "Add Windows build script and build instructions"
git push origin dev
```

Do **not** commit generated app files such as:

```text
release/
out/
dist/
SAI-windows-test.zip
S.A.I.exe
app.asar
```

The GitHub repository should contain source code only. Built apps should be shared through GitHub Releases, Google Drive, OneDrive, or as a zipped `win-unpacked` folder.

---

## Current Status Summary

This fork is best described as:
- a **working Windows assistant shell**
- with **safe local actions + optional Gemini chat**
- while **voice/email deep features are currently out of runtime scope**
- and **legacy deep-memory/original-platform modules kept in repo but not actively wired**

---

## Credits

- Original upstream concept and codebase: `23jomo`
- This branch: Windows-focused adaptation and runtime simplification
