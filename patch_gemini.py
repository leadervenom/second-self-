from pathlib import Path

path = Path("src/server.py")
s = path.read_text(encoding="utf-8")

if "import httpx" not in s:
    s = s.replace("import uuid\n", "import uuid\nimport httpx\n")

if "async def _gemini_chat" not in s:
    helper = r'''
async def _gemini_chat(message: str) -> str:
    """Call Gemini directly through the REST API."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "Gemini is not connected. Add GEMINI_API_KEY to .env and restart the backend."

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    system_prompt = (
        "You are S.A.I, Vajhra's Windows web AI assistant. "
        "Be direct, practical, and help with coding, planning, studying, and daily work. "
        "Do not claim you can control the computer yet. "
        "If the user asks for computer control, explain that desktop automation will be added later."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "system_instruction": {
            "parts": [
                {"text": system_prompt}
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": message}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024
        }
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            },
            json=payload
        )

    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:500]}")

    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
'''
    s = s.replace("\ndef _fallback_profile", helper + "\n\ndef _fallback_profile")

start = s.index('@app.post("/chat", response_model=ChatResponse, deprecated=True)')
end = s.index('\ndef _fallback_profile', start)

new_endpoint = '''@app.post("/chat", response_model=ChatResponse, deprecated=True)
async def chat(body: ChatRequest):
    """Windows demo chat. Uses Gemini if GEMINI_API_KEY is set."""
    if os.getenv("GEMINI_API_KEY", "").strip():
        response_text = await _gemini_chat(body.message)
        return ChatResponse(response=response_text, actions_taken=[])

    return ChatResponse(
        response=f"Demo mode is running, but Gemini is not connected yet. You said: {body.message}",
        actions_taken=[],
    )
'''

s = s[:start] + new_endpoint + s[end:]
path.write_text(s, encoding="utf-8")

print("Patched src/server.py for Gemini chat.")
