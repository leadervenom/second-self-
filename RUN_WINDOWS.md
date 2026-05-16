# Second Self — Windows Run Pack

This pack is for running the uploaded project on Windows as a web app + Python backend.

The macOS Swift notch app, Quartz screen capture, LaunchAgent files, and Vine/VNC setup are macOS-specific. Do not try to run those on Windows.

## 1. Copy these files

Copy all files in this pack into the root of the extracted project folder, the same folder that contains `package.json`.

## 2. Run setup

Open PowerShell in the project root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup-windows.ps1
```

## 3. Start backend

Open PowerShell window 1:

```powershell
.\start-backend.ps1
```

## 4. Start frontend

Open PowerShell window 2:

```powershell
.\start-frontend.ps1
```

Open:

```text
http://localhost:3000
```

## 5. Test backend directly

With the backend running:

```powershell
.\test-backend.ps1
```

## API modes

### Demo mode, no API payment

Use this first:

```env
DEMO_MODE=true
```

This checks whether the app runs.

### Real AI mode

Change `.env`:

```env
DEMO_MODE=false
ANTHROPIC_API_KEY=your_key_here
CLAUDE_MODEL=claude-sonnet-4-6
TAVILY_API_KEY=your_key_here
```

Tavily is only needed for web search/profile lookup. Anthropic is needed because the current code calls the Anthropic SDK directly.

### Local model mode

This project does not support local models cleanly yet. The fastest local workaround is to add a model adapter or use LM Studio's Anthropic-compatible server, then patch the code to pass `base_url` into the Anthropic client.

Do not spend hackathon time converting the entire app before first proving the web/backend app runs in demo mode.
