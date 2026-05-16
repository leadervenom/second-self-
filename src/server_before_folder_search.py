import json
import os
import re
import shutil
import subprocess
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(".env")

PROJECT_ROOT = Path.cwd()
LAST_URL_BY_SESSION: Dict[str, str] = {}

app = FastAPI(title="S.A.I Windows Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OnboardRequest(BaseModel):
    name: str = "Vajhra"
    email: str = ""
    context: str = ""
    session_id: str = "demo-local"


class ChatRequest(BaseModel):
    message: str
    session_id: str = "demo-local"


class ActionTaken(BaseModel):
    tool: str
    summary: str


class ChatResponse(BaseModel):
    response: str
    actions_taken: List[ActionTaken] = []


def local_tools_enabled() -> bool:
    return os.getenv("ALLOW_LOCAL_TOOLS", "false").strip().lower() == "true"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_connected": bool(os.getenv("GEMINI_API_KEY")),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash").lower(),
        "local_tools_enabled": local_tools_enabled(),
        "github_username": os.getenv("GITHUB_USERNAME", ""),
        "project_root": str(PROJECT_ROOT),
    }


@app.post("/onboard")
async def onboard(body: OnboardRequest):
    return {
        "profile": {
            "identity": {
                "name": body.name or "Vajhra",
                "role": "Student / Builder",
                "company": "S.A.I Windows Lab",
            },
            "voice": {
                "formality": "casual-direct",
                "avg_email_length": "medium",
                "signature_phrases": ["make it work", "build first", "ship the demo"],
                "opens_with": "hey",
                "closes_with": "done",
                "tone": "direct and practical",
            },
            "behavior": {
                "work_hours": "late night",
                "meeting_load": "medium",
                "response_style": "straight to the point",
                "peak_focus_time": "night",
            },
            "context": {
                "active_projects": ["S.A.I", "AI assistant", "hackathon systems"],
                "top_collaborators": [],
                "current_priorities": ["make the assistant run on Windows"],
            },
        },
        "sources_used": ["windows-demo"],
        "session_id": body.session_id or "demo-local",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def remember_url(session_id: str, url: str):
    LAST_URL_BY_SESSION[session_id] = url


def extract_first_url(text: str) -> Optional[str]:
    match = re.search(r"https?://[^\s\]\)]+", text)
    return match.group(0) if match else None


def response(text: str, tool: Optional[str] = None, summary: Optional[str] = None) -> ChatResponse:
    actions = []
    if tool and summary:
        actions.append(ActionTaken(tool=tool, summary=summary))
    return ChatResponse(response=text, actions_taken=actions)


def open_url(url: str, session_id: str) -> ChatResponse:
    remember_url(session_id, url)
    webbrowser.open(url, new=2)
    return response(f"Opened: {url}", "open_url", url)


def open_github_profile(username: Optional[str], session_id: str) -> ChatResponse:
    username = (username or os.getenv("GITHUB_USERNAME", "") or "leadervenom").strip()
    username = username.replace("@", "").strip("/")

    if not re.fullmatch(r"[A-Za-z0-9-]+", username):
        return response("That GitHub username looks invalid. Use letters, numbers, or hyphens only.")

    url = f"https://github.com/{username}"
    return open_url(url, session_id)


def open_youtube_search(query: str, session_id: str) -> ChatResponse:
    query = query.strip()
    url = "https://www.youtube.com" if not query else f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    return open_url(url, session_id)


def open_google_search(query: str, session_id: str) -> ChatResponse:
    query = query.strip()
    url = "https://www.google.com" if not query else f"https://www.google.com/search?q={quote_plus(query)}"
    return open_url(url, session_id)


def find_exe(candidates: List[str]) -> Optional[str]:
    for item in candidates:
        found = shutil.which(item)
        if found:
            return found

        path = Path(os.path.expandvars(item))
        if path.exists():
            return str(path)

    return None


def open_app(app_name: str) -> ChatResponse:
    app_key = app_name.lower().strip()

    app_map = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "paint": ["mspaint.exe"],
        "cmd": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "terminal": ["wt.exe", "powershell.exe"],
        "vscode": [
            "code",
            "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\Code.exe",
            "%PROGRAMFILES%\\Microsoft VS Code\\Code.exe",
        ],
        "vs code": [
            "code",
            "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\Code.exe",
            "%PROGRAMFILES%\\Microsoft VS Code\\Code.exe",
        ],
        "chrome": [
            "%PROGRAMFILES%\\Google\\Chrome\\Application\\chrome.exe",
            "%PROGRAMFILES(X86)%\\Google\\Chrome\\Application\\chrome.exe",
        ],
        "edge": [
            "msedge.exe",
            "%PROGRAMFILES(X86)%\\Microsoft\\Edge\\Application\\msedge.exe",
            "%PROGRAMFILES%\\Microsoft\\Edge\\Application\\msedge.exe",
        ],
        "android studio": [
            "%PROGRAMFILES%\\Android\\Android Studio\\bin\\studio64.exe",
            "%LOCALAPPDATA%\\Programs\\Android Studio\\bin\\studio64.exe",
        ],
        "discord": [
            "%LOCALAPPDATA%\\Discord\\Update.exe",
        ],
        "spotify": [
            "%APPDATA%\\Spotify\\Spotify.exe",
        ],
    }

    candidates = app_map.get(app_key)
    if not candidates:
        return response(f"I do not have `{app_name}` in my safe app list yet.")

    exe = find_exe(candidates)
    if not exe:
        return response(f"I could not find {app_name} on this Windows machine.")

    if app_key == "discord" and exe.endswith("Update.exe"):
        subprocess.Popen([exe, "--processStart", "Discord.exe"])
    else:
        subprocess.Popen([exe])

    return response(f"Opened {app_name}.", "open_app", app_name)


def open_vscode_project() -> ChatResponse:
    code = find_exe([
        "code",
        "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\Code.exe",
        "%PROGRAMFILES%\\Microsoft VS Code\\Code.exe",
    ])

    if not code:
        return response("I could not find VS Code. Install it or add `code` to PATH.")

    target = os.getenv("DEFAULT_PROJECT_PATH", str(PROJECT_ROOT))
    subprocess.Popen([code, target])
    return response(f"Opened VS Code at: {target}", "open_app", f"VS Code {target}")


def open_folder(folder_name: str) -> ChatResponse:
    key = folder_name.lower().strip()
    user_home = Path.home()

    folder_map = {
        "desktop": user_home / "Desktop",
        "downloads": user_home / "Downloads",
        "documents": user_home / "Documents",
        "project": Path(os.getenv("DEFAULT_PROJECT_PATH", str(PROJECT_ROOT))),
        "current project": Path(os.getenv("DEFAULT_PROJECT_PATH", str(PROJECT_ROOT))),
        "this project": Path(os.getenv("DEFAULT_PROJECT_PATH", str(PROJECT_ROOT))),
    }

    target = folder_map.get(key)

    if not target:
        return response(f"I do not know that folder yet: {folder_name}")

    if not target.exists():
        return response(f"Folder does not exist: {target}")

    subprocess.Popen(["explorer", str(target)])
    return response(f"Opened folder: {target}", "open_folder", str(target))


def clean_query(text: str, words: List[str]) -> str:
    q = text.lower()
    for word in words:
        q = q.replace(word, " ")
    q = re.sub(r"\s+", " ", q).strip()
    return q


def deterministic_route(message: str, session_id: str) -> Optional[ChatResponse]:
    lower = message.lower().strip()

    if lower in ["open it", "open that", "open this", "open the link", "open link"]:
        last_url = LAST_URL_BY_SESSION.get(session_id)
        if last_url:
            return open_url(last_url, session_id)
        return response("I do not have a previous link stored yet.")

    direct_url = extract_first_url(message)
    if direct_url and any(word in lower for word in ["open", "launch", "go to"]):
        return open_url(direct_url, session_id)

    if "github" in lower and ("profile" in lower or "my github" in lower or "leadervenom" in lower):
        username_match = re.search(r"github(?: profile)?\s+([a-zA-Z0-9-]+)", lower)
        username = username_match.group(1) if username_match else os.getenv("GITHUB_USERNAME", "leadervenom")
        return open_github_profile(username, session_id)

    if "open gpt" in lower or "open chatgpt" in lower or "open chat gpt" in lower or "launch gpt" in lower:
        return open_url("https://chatgpt.com", session_id)

    if "open github" in lower:
        return open_url("https://github.com", session_id)

    if "youtube" in lower or "yt " in lower:
        query = clean_query(lower, ["open", "launch", "youtube", "yt", "search", "for", "play", "on"])
        return open_youtube_search(query, session_id)

    if "google" in lower:
        query = clean_query(lower, ["open", "launch", "google", "search", "for", "on"])
        return open_google_search(query, session_id)

    if "vscode" in lower or "vs code" in lower or "visual studio code" in lower:
        if "project" in lower or "folder" in lower or "here" in lower:
            return open_vscode_project()
        return open_app("vscode")

    folder_aliases = {
        "desktop": ["open desktop", "show desktop folder"],
        "downloads": ["open downloads", "open download folder", "show downloads"],
        "documents": ["open documents", "open document folder"],
        "project": ["open project folder", "open current project", "open this project"],
    }

    for folder, phrases in folder_aliases.items():
        if any(phrase in lower for phrase in phrases):
            return open_folder(folder)

    app_aliases = {
        "notepad": ["open notepad", "launch notepad"],
        "calculator": ["open calculator", "open calc", "launch calculator"],
        "paint": ["open paint", "launch paint"],
        "terminal": ["open terminal", "launch terminal"],
        "powershell": ["open powershell", "launch powershell"],
        "cmd": ["open cmd", "open command prompt"],
        "chrome": ["open chrome", "launch chrome"],
        "edge": ["open edge", "launch edge"],
        "android studio": ["open android studio", "launch android studio"],
        "discord": ["open discord", "launch discord"],
        "spotify": ["open spotify", "launch spotify"],
    }

    for app_name, phrases in app_aliases.items():
        if any(phrase in lower for phrase in phrases):
            return open_app(app_name)

    return None


async def gemini_generate(prompt: str, max_tokens: int = 1024) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return "Gemini key is not connected."

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip().lower()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max_tokens,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if res.status_code >= 400:
        return f"Gemini API error {res.status_code}: {res.text}"

    data = res.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return f"Gemini returned an unexpected response: {data}"


def parse_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


async def ai_tool_route(message: str) -> Optional[Dict[str, Any]]:
    username = os.getenv("GITHUB_USERNAME", "leadervenom")

    prompt = f"""
You are a tool router for a Windows AI assistant.

Convert the user message into exactly one JSON object.

Allowed tools:
1. open_url
   args: url

2. open_app
   args: app
   allowed app values:
   notepad, calculator, paint, cmd, powershell, terminal, vscode, chrome, edge, android studio, discord, spotify

3. open_vscode_project
   args: none

4. open_folder
   args: folder
   allowed folder values:
   desktop, downloads, documents, project

5. open_github_profile
   args: username
   default username: {username}

6. youtube_search
   args: query

7. google_search
   args: query

8. none
   args: none

Rules:
- Return JSON only.
- Do not include markdown.
- If user says "gpt", "chat gpt", or "chat", use open_url with https://chatgpt.com.
- If user says "my github profile" and no username is given, use username "{username}".
- If user says "github profile leadervenom", use username "leadervenom".
- If user says "open this project in code", use open_vscode_project.
- If user asks to search or play something on YouTube, use youtube_search.
- If user asks to search the web, use google_search.
- If the request is normal conversation, use none.

Examples:
User: open gpt
Output: {{"tool":"open_url","url":"https://chatgpt.com"}}

User: open my github profile
Output: {{"tool":"open_github_profile","username":"{username}"}}

User: open my github profile leadervenom
Output: {{"tool":"open_github_profile","username":"leadervenom"}}

User: launch vscode
Output: {{"tool":"open_app","app":"vscode"}}

User: open this project in code
Output: {{"tool":"open_vscode_project"}}

User: open my downloads
Output: {{"tool":"open_folder","folder":"downloads"}}

User message:
{message}
"""

    raw = await gemini_generate(prompt, max_tokens=256)
    data = parse_json_from_text(raw)

    if not data:
        return None

    if data.get("tool") == "none":
        return None

    return data


def execute_tool_route(route: Dict[str, Any], session_id: str) -> Optional[ChatResponse]:
    tool = route.get("tool")

    if tool == "open_url":
        url = route.get("url", "")
        if not url.startswith(("http://", "https://")):
            return response("The URL from the tool router was invalid.")
        return open_url(url, session_id)

    if tool == "open_app":
        return open_app(str(route.get("app", "")))

    if tool == "open_vscode_project":
        return open_vscode_project()

    if tool == "open_folder":
        return open_folder(str(route.get("folder", "")))

    if tool == "open_github_profile":
        return open_github_profile(route.get("username"), session_id)

    if tool == "youtube_search":
        return open_youtube_search(str(route.get("query", "")), session_id)

    if tool == "google_search":
        return open_google_search(str(route.get("query", "")), session_id)

    return None


async def normal_chat(message: str) -> str:
    prompt = f"""
You are S.A.I, Vajhra's Windows web AI assistant.

Style:
- direct
- practical
- useful
- no fake claims

Current capability:
- You can answer questions.
- You can open safe local apps and browser pages only when the backend tool router executes it.
- You cannot yet control arbitrary windows, read the screen, click buttons, or run unrestricted terminal commands.

User message:
{message}
"""
    return await gemini_generate(prompt)


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    if local_tools_enabled():
        direct = deterministic_route(body.message, body.session_id)
        if direct:
            return direct

        route = await ai_tool_route(body.message)
        if route:
            executed = execute_tool_route(route, body.session_id)
            if executed:
                return executed

    reply = await normal_chat(body.message)

    return ChatResponse(
        response=reply,
        actions_taken=[
            ActionTaken(tool="gemini", summary="Generated response through Gemini API")
        ],
    )
