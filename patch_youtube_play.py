from pathlib import Path

path = Path("src/server.py")
s = path.read_text(encoding="utf-8")

# Add yt_dlp import
if "import yt_dlp" not in s:
    s = s.replace("import webbrowser\n", "import webbrowser\nimport yt_dlp\n")

# Replace clean_query with safe whole-word cleaner
start = s.index("def clean_query")
end = s.index("\n\ndef extract_search_query_for_local", start)

new_clean_query = r'''def clean_query(text: str, words: List[str]) -> str:
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
'''

s = s[:start] + new_clean_query + s[end:]

# Replace open_youtube_search function
start = s.index("def open_youtube_search")
end = s.index("\n\ndef open_google_search", start)

new_youtube_func = r'''def find_first_youtube_video(query: str) -> Optional[str]:
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
'''

s = s[:start] + new_youtube_func + s[end:]

path.write_text(s, encoding="utf-8")
print("Patched YouTube first-result playback and fixed song/on bug.")
