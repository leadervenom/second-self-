import json
import os
import re
import shutil
import subprocess
import webbrowser
import yt_dlp
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

SKIP_DIRS = {
    "AppData",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "build",
    "dist",
    ".dart_tool",
    ".gradle",
    ".idea",
    ".vscode",
    "android\\.gradle",
}

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


def get_safe_root() -> Path:
    raw = os.getenv("SAFE_SEARCH_ROOT", str(Path.home())).strip()
    return Path(raw).expanduser().resolve()


def max_search_depth() -> int:
    return int(os.getenv("MAX_SEARCH_DEPTH", "7"))


def max_search_items() -> int:
    return int(os.getenv("MAX_SEARCH_ITEMS", "15000"))


def is_safe_path(path: Path) -> bool:
    try:
        root = get_safe_root()
        resolved = path.expanduser().resolve()
        return str(resolved).lower().startswith(str(root).lower())
    except Exception:
        return False


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_connected": bool(os.getenv("GEMINI_API_KEY")),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash").lower(),
        "local_tools_enabled": local_tools_enabled(),
        "safe_search_root": str(get_safe_root()),
        "github_username": os.getenv("GITHUB_USERNAME", ""),
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
                "current_priorities": ["make the assistant useful on Windows"],
            },
        },
        "sources_used": ["windows-demo"],
        "session_id": body.session_id or "demo-local",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def response(text: str, tool: Optional[str] = None, summary: Optional[str] = None) -> ChatResponse:
    actions = []
    if tool and summary:
        actions.append(ActionTaken(tool=tool, summary=summary))
    return ChatResponse(response=text, actions_taken=actions)


def remember_url(session_id: str, url: str):
    LAST_URL_BY_SESSION[session_id] = url


def extract_first_url(text: str) -> Optional[str]:
    match = re.search(r"https?://[^\s\]\)]+", text)
    return match.group(0) if match else None


def open_url(url: str, session_id: str) -> ChatResponse:
    remember_url(session_id, url)
    webbrowser.open(url, new=2)
    return response(f"Opened: {url}", "open_url", url)


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def score_path(path: Path, query: str) -> int:
    q = normalize_text(query)
    if not q:
        return 0

    tokens = q.split()
    name = normalize_text(path.name)
    full = normalize_text(str(path))

    score = 0

    if q == name:
        score += 100

    if q in name:
        score += 60

    if q in full:
        score += 25

    for token in tokens:
        if token in name:
            score += 20
        elif token in full:
            score += 6

    # project folder signals
    if path.is_dir():
        project_markers = [
            "pubspec.yaml",
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            ".git",
        ]
        for marker in project_markers:
            if (path / marker).exists():
                score += 15

    return score


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith("$")


def search_local_paths(
    query: str,
    include_files: bool = True,
    include_dirs: bool = True,
    limit: int = 8,
) -> List[Path]:
    root = get_safe_root()

    if not root.exists():
        return []

    results: List[tuple[int, Path]] = []
    visited = 0
    max_depth = max_search_depth()
    max_items = max_search_items()

    root_parts_count = len(root.parts)

    for current, dirs, files in os.walk(root):
        current_path = Path(current)

        depth = len(current_path.parts) - root_parts_count
        if depth > max_depth:
            dirs[:] = []
            continue

        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        visited += 1
        if visited > max_items:
            break

        if include_dirs:
            for d in dirs:
                p = current_path / d
                score = score_path(p, query)
                if score > 0:
                    results.append((score, p))

        if include_files:
            for f in files:
                p = current_path / f
                score = score_path(p, query)
                if score > 0:
                    results.append((score, p))

    results.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in results[:limit]]


def format_search_results(query: str, results: List[Path]) -> str:
    if not results:
        return f"I could not find anything matching `{query}` under {get_safe_root()}."

    lines = [f"Found these matches for `{query}`:"]
    for index, path in enumerate(results, start=1):
        kind = "folder" if path.is_dir() else "file"
        lines.append(f"{index}. [{kind}] {path}")

    lines.append("")
    lines.append("To open one, say: `open the first result` or be more specific.")
    return "\n".join(lines)


def open_path(path: Path, mode: str = "default") -> ChatResponse:
    if not is_safe_path(path):
        return response("Blocked. That path is outside the safe search root.")

    if not path.exists():
        return response(f"Path does not exist: {path}")

    if mode == "vscode":
        code = find_exe([
            "code",
            "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\Code.exe",
            "%PROGRAMFILES%\\Microsoft VS Code\\Code.exe",
        ])

        if code:
            subprocess.Popen([code, str(path)])
            return response(f"Opened in VS Code: {path}", "open_vscode", str(path))

        subprocess.Popen(["explorer", str(path if path.is_dir() else path.parent)])
        return response(f"VS Code was not found. Opened folder instead: {path}", "open_folder", str(path))

    if path.is_dir():
        subprocess.Popen(["explorer", str(path)])
        return response(f"Opened folder: {path}", "open_folder", str(path))

    os.startfile(str(path))
    return response(f"Opened file: {path}", "open_file", str(path))


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


def open_github_profile(username: Optional[str], session_id: str) -> ChatResponse:
    username = (username or os.getenv("GITHUB_USERNAME", "") or "leadervenom").strip()
    username = username.replace("@", "").strip("/")

    if username in ["profile", "github", "my", ""]:
        username = os.getenv("GITHUB_USERNAME", "leadervenom").strip()

    if not re.fullmatch(r"[A-Za-z0-9-]+", username):
        return response("That GitHub username looks invalid.")

    return open_url(f"https://github.com/{username}", session_id)


def find_first_youtube_video(query: str) -> Optional[str]:
    """
    Uses yt-dlp to get the first YouTube search result.
    No YouTube API key required.
    """
    query = query.strip()

    if not query:
        return None

    try:
        opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)

        entries = info.get("entries", []) if info else []

        if not entries:
            return None

        video_id = entries[0].get("id")

        if not video_id:
            return None

        return f"https://www.youtube.com/watch?v={video_id}&autoplay=1"

    except Exception:
        return None


def open_youtube_search(query: str, session_id: str) -> ChatResponse:
    query = query.strip()

    if not query:
        return open_url("https://www.youtube.com", session_id)

    video_url = find_first_youtube_video(query)

    if video_url:
        return open_url(video_url, session_id)

    # Fallback if yt-dlp fails
    fallback_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    return open_url(fallback_url, session_id)


def open_google_search(query: str, session_id: str) -> ChatResponse:
    query = query.strip()
    url = "https://www.google.com" if not query else f"https://www.google.com/search?q={quote_plus(query)}"
    return open_url(url, session_id)


def clean_query(text: str, words: List[str]) -> str:
    """
    Removes command words safely.
    Important: only removes whole words.
    Example:
    - removes 'on' from 'play music on youtube'
    - does NOT destroy 'song' into 's g'
    """
    q = text.lower()

    for word in words:
        pattern = r"\b" + re.escape(word.lower()) + r"\b"
        q = re.sub(pattern, " ", q)

    q = re.sub(r"\s+", " ", q).strip()
    return q


def extract_search_query_for_local(message: str) -> str:
    lower = message.lower()

    remove_phrases = [
        "search my folders for",
        "search folders for",
        "search for",
        "find my",
        "find the",
        "find",
        "open my",
        "open the",
        "open",
        "launch",
        "in vscode",
        "in vs code",
        "in code",
        "using vscode",
        "using vs code",
        "project",
        "folder",
        "file",
        "called",
        "named",
    ]

    q = lower
    for phrase in remove_phrases:
        q = q.replace(phrase, " ")

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

    # GitHub shortcuts
    if "github" in lower and "profile" in lower:
        configured = os.getenv("GITHUB_USERNAME", "leadervenom").strip() or "leadervenom"

        if "my github" in lower and "leadervenom" not in lower:
            return open_github_profile(configured, session_id)

        username_match = re.search(r"profile\s+([a-zA-Z0-9-]+)$|github\s+profile\s+([a-zA-Z0-9-]+)", lower)
        username = configured

        if username_match:
            username = next((g for g in username_match.groups() if g), configured)

        return open_github_profile(username, session_id)

    if lower in ["open my github", "launch my github", "open github profile"]:
        return open_github_profile(os.getenv("GITHUB_USERNAME", "leadervenom"), session_id)

    if "open gpt" in lower or "open chatgpt" in lower or "open chat gpt" in lower or "launch gpt" in lower:
        return open_url("https://chatgpt.com", session_id)

    if lower == "open github":
        return open_url("https://github.com", session_id)

    if "youtube" in lower or "yt " in lower:
        query = clean_query(lower, ["open", "launch", "youtube", "yt", "search", "for", "play", "on"])
        return open_youtube_search(query, session_id)

    if "google" in lower:
        query = clean_query(lower, ["open", "launch", "google", "search", "for", "on"])
        return open_google_search(query, session_id)

    # App shortcuts
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

    if "open vscode" in lower or "open vs code" in lower or "launch vscode" in lower:
        return open_app("vscode")

    # Local folder/file search
    wants_local_search = any(
        phrase in lower
        for phrase in [
            "find ",
            "search my folders",
            "search folders",
            "open project",
            "open the project",
            "open my project",
            "open folder",
            "open the folder",
            "open file",
            "open the file",
            "in vscode",
            "in vs code",
            "in code",
        ]
    )

    if wants_local_search:
        query = extract_search_query_for_local(message)

        if not query:
            return response("Tell me what folder or file name to search for.")

        include_files = "file" in lower or "find" in lower or "search" in lower
        include_dirs = "folder" in lower or "project" in lower or "vscode" in lower or "code" in lower or "open" in lower

        results = search_local_paths(
            query,
            include_files=include_files,
            include_dirs=include_dirs,
            limit=8,
        )

        if lower.startswith("find") or "search" in lower:
            return response(format_search_results(query, results), "search_local", query)

        if not results:
            return response(f"I could not find `{query}` under {get_safe_root()}.")

        best = results[0]
        mode = "vscode" if any(x in lower for x in ["vscode", "vs code", "in code", "project"]) else "default"
        return open_path(best, mode=mode)

    return None


async def gemini_generate(prompt: str, max_tokens: int = 1024) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return "Gemini key is not connected."

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip().lower()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
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
You are a safe tool router for a Windows AI assistant.

Return exactly one JSON object. No markdown.

Allowed tools:
1. open_url
   args: url

2. open_app
   args: app
   allowed app values:
   notepad, calculator, paint, cmd, powershell, terminal, vscode, chrome, edge, android studio, discord, spotify

3. open_github_profile
   args: username
   default username: {username}

4. youtube_search
   args: query

5. google_search
   args: query

6. search_local
   args: query
   Use this when the user asks to find a local file/folder/project.

7. open_local
   args: query, mode
   mode values: default, vscode
   Use this when the user asks to open a local file/folder/project.

8. none
   args: none

Rules:
- If user says "gpt", "chat gpt", or "chatgpt", use open_url with https://chatgpt.com.
- If user says "my github profile", use username "{username}".
- If user asks to search or play something on YouTube, use youtube_search.
- If user asks to search the web, use google_search.
- If user asks to open a local project/folder/file, use open_local.
- If user asks to find a local project/folder/file, use search_local.
- If normal conversation, use none.

User message:
{message}
"""

    raw = await gemini_generate(prompt, max_tokens=256)
    data = parse_json_from_text(raw)

    if not data or data.get("tool") == "none":
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

    if tool == "open_github_profile":
        return open_github_profile(route.get("username"), session_id)

    if tool == "youtube_search":
        return open_youtube_search(str(route.get("query", "")), session_id)

    if tool == "google_search":
        return open_google_search(str(route.get("query", "")), session_id)

    if tool == "search_local":
        query = str(route.get("query", "")).strip()
        results = search_local_paths(query, include_files=True, include_dirs=True, limit=8)
        return response(format_search_results(query, results), "search_local", query)

    if tool == "open_local":
        query = str(route.get("query", "")).strip()
        mode = str(route.get("mode", "default")).strip()
        results = search_local_paths(query, include_files=True, include_dirs=True, limit=8)

        if not results:
            return response(f"I could not find `{query}` under {get_safe_root()}.")

        return open_path(results[0], mode=mode)

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
- You can open safe local apps and browser pages.
- You can search file/folder names under {get_safe_root()}.
- You cannot delete files, modify files, read private file contents, control arbitrary windows, or run unrestricted terminal commands.

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
