from pathlib import Path

path = Path("src/server.py")
s = path.read_text(encoding="utf-8")

start = s.index("async def call_gemini")
end = s.index('\n\n@app.post("/chat"', start)

new_func = r'''async def call_gemini(message: str) -> str:
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
'''

s = s[:start] + new_func + s[end:]
path.write_text(s, encoding="utf-8")
print("Patched Gemini function.")
