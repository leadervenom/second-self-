import os
import re
import shutil
import subprocess
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(".env")

app = FastAPI(title="S.A.I Windows Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LAST_URL_BY_SESSION = {}


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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_connected": bool(os.getenv("GEMINI_API_KEY")),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash").lower(),
        "local_tools_enabled": local_tools_enabled(),
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
                "meeting_load": "light",
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


def local_tools_enabled() -> bool:
    return os.getenv("ALLOW_LOCAL_TOOLS", "false").strip().lower() == "true"


def remember_url(session_id: str, url: str):
    LAST_URL_BY_SESSION[session_id] = url


def extract_first_url(text: str) -> Optional[str]:
    match = re.search(r"https?://[^\s\]\)]+", text)
    return match.group(0) if match else None


def open_url(url: str, session_id: str) -> ChatResponse:
    remember_url(session_id, url)
    webbrowser.open(url, new=2)
    return ChatResponse(
        response=f"Opened this in your browser: {url}",
        actions_taken=[
            ActionTaken(tool="open_url", summary=url)
        ],
    )


def open_vscode() -> ChatResponse:
    code_cmd = shutil.which("code")

    if code_cmd:
        subprocess.Popen([code_cmd])
        return ChatResponse(
            response="Opened VS Code.",
            actions_taken=[ActionTaken(tool="open_app", summary="VS Code")]
        )

    local_appdata = os.getenv("LOCALAPPDATA", "")
    candidate = Path(local_appdata) / "Programs" / "Microsoft VS Code" / "Code.exe"

    if candidate.exists():
        subprocess.Popen([str(candidate)])
        return ChatResponse(
            response="Opened VS Code.",
            actions_taken=[ActionTaken(tool="open_app", summary="VS Code")]
        )

    return ChatResponse(
        response="I could not find VS Code. Add VS Code to PATH or install it in the default Windows location.",
        actions_taken=[]
    )


def open_simple_windows_app(app_name: str) -> ChatResponse:
    allowed_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
    }

    exe = allowed_apps.get(app_name)

    if not exe:
        return ChatResponse(
            response=f"{app_name} is not in my allowed app list yet.",
            actions_taken=[]
        )

    subprocess.Popen([exe])
    return ChatResponse(
        response=f"Opened {app_name}.",
        actions_taken=[ActionTaken(tool="open_app", summary=app_name)]
    )


def clean_query(text: str, remove_words: List[str]) -> str:
    q = text.lower()

    for word in remove_words:
        q = q.replace(word, " ")

    q = re.sub(r"\s+", " ", q).strip()
    return q


def try_local_action(message: str, session_id: str) -> Optional[ChatResponse]:
    if not local_tools_enabled():
        return None

    text = message.strip()
    lower = text.lower()

    if lower in ["open it", "open that", "open this", "open the link", "open link"]:
        last_url = LAST_URL_BY_SESSION.get(session_id)
        if last_url:
            return open_url(last_url, session_id)

        return ChatResponse(
            response="I do not have a previous link stored yet. Tell me exactly what to open, for example: open youtube karuppu songs.",
            actions_taken=[]
        )

    direct_url = extract_first_url(text)
    if "open" in lower and direct_url:
        return open_url(direct_url, session_id)

    if lower.startswith("open youtube") or "open youtube" in lower:
        query = clean_query(
            lower,
            ["open", "youtube", "on", "with", "for", "search", "search for", "play"]
        )

        if query:
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        else:
            url = "https://www.youtube.com"

        return open_url(url, session_id)

    if lower.startswith("open google") or "open google" in lower:
        query = clean_query(lower, ["open", "google", "search", "for", "on"])

        if query:
            url = f"https://www.google.com/search?q={quote_plus(query)}"
        else:
            url = "https://www.google.com"

        return open_url(url, session_id)

    if "open chatgpt" in lower or "open chat gpt" in lower:
        return open_url("https://chatgpt.com", session_id)

    if "open github" in lower:
        return open_url("https://github.com", session_id)

    if "open vscode" in lower or "open vs code" in lower or "open visual studio code" in lower:
        return open_vscode()

    if "open notepad" in lower:
        return open_simple_windows_app("notepad")

    if "open calculator" in lower or "open calc" in lower:
        return open_simple_windows_app("calculator")

    return None


async def call_gemini(message: str, session_id: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return (
            "Gemini key is not connected yet. Add GEMINI_API_KEY to .env, "
            "restart the backend, then test again."
        )

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip().lower()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    system_prompt = (
        "You are S.A.I, Vajhra's Windows web AI assistant. "
        "Be direct, practical, and useful. "
        "You can only open local apps or browser pages through the backend tool router. "
        "If the user wants something opened, tell them the exact command format, such as: "
        "'open youtube karuppu songs', 'open vscode', or 'open chatgpt'. "
        "Do not pretend you opened something unless a tool actually did it."
    )

    prompt = f"{system_prompt}\n\nUser message: {message}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
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
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return f"Gemini returned an unexpected response: {data}"

    possible_url = extract_first_url(reply)
    if possible_url:
        remember_url(session_id, possible_url)

    return reply


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    local_result = try_local_action(body.message, body.session_id)

    if local_result:
        return local_result

    reply = await call_gemini(body.message, body.session_id)

    return ChatResponse(
        response=reply,
        actions_taken=[
            ActionTaken(tool="gemini", summary="Generated response through Gemini API")
        ],
    )
