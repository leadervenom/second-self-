from pathlib import Path

path = Path("src/server.py")
s = path.read_text(encoding="utf-8")

workspace_code = r'''

def env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    return value in ["true", "1", "yes", "y", "on"]


def open_url_in_chrome_or_default(url: str, session_id: str) -> ChatResponse:
    """
    Tries Chrome first. If Chrome is not found, uses default browser.
    """
    chrome = find_exe([
        "%PROGRAMFILES%\\Google\\Chrome\\Application\\chrome.exe",
        "%PROGRAMFILES(X86)%\\Google\\Chrome\\Application\\chrome.exe",
    ])

    remember_url(session_id, url)

    if chrome:
        subprocess.Popen([chrome, url])
        return response(f"Opened in Chrome: {url}", "open_chrome", url)

    webbrowser.open(url, new=2)
    return response(f"Opened in default browser: {url}", "open_url", url)


def open_workspace(session_id: str) -> ChatResponse:
    """
    Opens Vajhra's preferred work environment.
    Controlled by .env flags.
    """
    opened = []

    if env_bool("WORKSPACE_OPEN_YOUTUBE", True):
        query = os.getenv("WORKSPACE_YOUTUBE_QUERY", "karuppu song").strip()
        yt_result = open_youtube_search(query, session_id)
        opened.append(f"YouTube: {query}")

    if env_bool("WORKSPACE_OPEN_VSCODE", True):
        project_query = os.getenv("WORKSPACE_PROJECT_QUERY", "").strip()

        if project_query:
            results = search_local_paths(
                project_query,
                include_files=False,
                include_dirs=True,
                limit=1,
            )

            if results:
                open_path(results[0], mode="vscode")
                opened.append(f"VS Code: {results[0]}")
            else:
                default_path = Path(os.getenv("DEFAULT_PROJECT_PATH", str(PROJECT_ROOT)))
                open_path(default_path, mode="vscode")
                opened.append(f"VS Code: {default_path}")
        else:
            default_path = Path(os.getenv("DEFAULT_PROJECT_PATH", str(PROJECT_ROOT)))
            open_path(default_path, mode="vscode")
            opened.append(f"VS Code: {default_path}")

    if env_bool("WORKSPACE_OPEN_CHATGPT", True):
        open_url_in_chrome_or_default("https://chatgpt.com", session_id)
        opened.append("ChatGPT")

    if env_bool("WORKSPACE_OPEN_GITHUB", True):
        username = os.getenv("GITHUB_USERNAME", "leadervenom").strip() or "leadervenom"
        github_url = f"https://github.com/{username}"
        open_url_in_chrome_or_default(github_url, session_id)
        opened.append(f"GitHub: {username}")

    if env_bool("WORKSPACE_OPEN_ELEARNING", True):
        elearning_url = os.getenv("WORKSPACE_ELEARNING_URL", "").strip()

        if elearning_url and elearning_url.startswith(("http://", "https://")):
            open_url_in_chrome_or_default(elearning_url, session_id)
            opened.append(f"E-learning: {elearning_url}")
        else:
            opened.append("E-learning skipped: WORKSPACE_ELEARNING_URL is missing or invalid")

    return response(
        "Workspace opened:\n" + "\n".join(f"- {item}" for item in opened),
        "open_workspace",
        "workspace package"
    )
'''

if "def open_workspace(session_id: str)" not in s:
    s = s.replace("\ndef deterministic_route(message: str, session_id: str)", workspace_code + "\ndef deterministic_route(message: str, session_id: str)")

workspace_route = r'''    # Workspace package launcher
    workspace_phrases = [
        "open my workspace",
        "start my workspace",
        "launch my workspace",
        "open my environment",
        "start my environment",
        "setup my workspace",
        "set up my workspace",
        "open work mode",
        "start work mode",
        "focus mode",
    ]

    if any(phrase in lower for phrase in workspace_phrases):
        return open_workspace(session_id)

'''

marker = r'''    if lower in ["open it", "open that", "open this", "open the link", "open link"]:'''

if workspace_route not in s:
    s = s.replace(marker, workspace_route + marker)

path.write_text(s, encoding="utf-8")
print("Patched workspace launcher.")
