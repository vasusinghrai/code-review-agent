"""Code Review Agent: an AI agent that explores a project folder with tools
and writes a review report (REVIEW.md)."""
import os
import sys
import anthropic

MODEL = "claude-sonnet-5-5"
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
MAX_CHARS = 8000
MAX_STEPS = 15

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

TOOLS = [
    {
        "name": "list_files",
        "description": "Recursively list files in the project (skips junk folders).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_file",
        "description": "Read a text file by its relative path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_report",
        "description": "Save the final review as REVIEW.md. Call this once at the end.",
        "input_schema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    },
]


def safe_path(root, rel):
    """Block access outside the project folder."""
    full = os.path.abspath(os.path.join(root, rel))
    if not full.startswith(os.path.abspath(root)):
        raise ValueError("Path is outside the project folder")
    return full


def run_tool(root, name, args):
    try:
        if name == "list_files":
            files = []
            for folder, dirs, names in os.walk(root):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for n in names:
                    files.append(os.path.relpath(os.path.join(folder, n), root))
            return "\n".join(files[:200]) or "(empty)"
        if name == "read_file":
            with open(safe_path(root, args["path"]), encoding="utf-8") as f:
                return f.read()[:MAX_CHARS]
        if name == "write_report":
            with open(os.path.join(root, "REVIEW.md"), "w", encoding="utf-8") as f:
                f.write(args["content"])
            return "Report saved to REVIEW.md"
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Error: {e}"


def review(root):
    messages = [{
        "role": "user",
        "content": (
            f"You are a senior code reviewer. Review the project in '{root}'. "
            "First list files, then read the important ones. Find bugs, "
            "security issues, and style problems, and suggest fixes. "
            "Finish by calling write_report with a clear markdown report "
            "(sections: Summary, Bugs, Improvements, Score out of 10)."
        ),
    }]
    for step in range(MAX_STEPS):
        r = client.messages.create(
            model=MODEL, max_tokens=2000, tools=TOOLS, messages=messages
        )
        messages.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            return "".join(b.text for b in r.content if b.type == "text")
        results = []
        for b in r.content:
            if b.type == "tool_use":
                print(f"[step {step + 1}] {b.name} {b.input}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": b.id,
                    "content": run_tool(root, b.name, b.input),
                })
        messages.append({"role": "user", "content": results})
    return "Stopped: reached the step limit."


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else input("Folder to review: ")
    if not os.path.isdir(folder):
        sys.exit("That folder does not exist.")
    print(review(folder))
