"""Code Review Agent (Gemini version): explores a project folder with tools
and writes a review report (REVIEW.md). Works with a free Google AI Studio key."""
import os
import sys
from google import genai
from google.genai import types

MODEL = "gemini-3.8-flash"
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
MAX_CHARS = 8000
ROOT = "."


def safe_path(rel):
    """Block access outside the project folder."""
    full = os.path.abspath(os.path.join(ROOT, rel))
    if not full.startswith(os.path.abspath(ROOT)):
        raise ValueError("Path is outside the project folder")
    return full


def list_files() -> str:
    """List all files in the project folder (skips junk folders)."""
    print("[tool] list_files")
    files = []
    for folder, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            files.append(os.path.relpath(os.path.join(folder, n), ROOT))
    return "\n".join(files[:200]) or "(empty)"


def read_file(path: str) -> str:
    """Read a text file using its relative path."""
    print(f"[tool] read_file {path}")
    try:
        with open(safe_path(path), encoding="utf-8") as f:
            return f.read()[:MAX_CHARS]
    except Exception as e:
        return f"Error: {e}"


def write_report(content: str) -> str:
    """Save the final markdown review as REVIEW.md. Call once at the end."""
    print("[tool] write_report")
    with open(os.path.join(ROOT, "REVIEW.md"), "w", encoding="utf-8") as f:
        f.write(content)
    return "Report saved to REVIEW.md"


def review(root):
    global ROOT
    ROOT = root
    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    prompt = (
        "You are a senior code reviewer. Review this project. First call "
        "list_files, then read_file on the important files. Find bugs, "
        "security issues and style problems, and suggest fixes. Finish by "
        "calling write_report with a clear markdown report (sections: "
        "Summary, Bugs, Improvements, Score out of 10)."
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[list_files, read_file, write_report]
        ),
    )
    return resp.text


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else input("Folder to review: ")
    if not os.path.isdir(folder):
        sys.exit("That folder does not exist.")
    print(review(folder))
