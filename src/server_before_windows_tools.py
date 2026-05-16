import os
from datetime import datetime, timezone
from typing import List

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
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
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


async def call_gemini(message: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return (
            "Gemini key is not connected yet. Add GEMINI_API_KEY to .env, "
            "restart the backend, then test again."
        )

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip().lower()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    prompt = (
        "You are S.A.I, Vajhra's Windows web AI assistant. "
        "Be direct, practical, and useful. "
        "Do not claim you can control the computer yet.\n\n"
        f"User message: {message}"
    )

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
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return f"Gemini returned an unexpected response: {data}"


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    reply = await call_gemini(body.message)
    return ChatResponse(
        response=reply,
        actions_taken=[
            ActionTaken(tool="gemini", summary="Generated response through Gemini API")
        ],
    )
