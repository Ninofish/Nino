"""
brain.py  –  J.A.R.V.I.S  AI Brain
─────────────────────────────────────────────────────────────────
Model   : GPT-4o  (via OpenAI SDK)
Tools   : read_file · write_file · list_files · run_command
          → allow JARVIS to inspect and repair code autonomously
─────────────────────────────────────────────────────────────────
Required env vars:
    OPENAI_API_KEY   – OpenAI API key
Optional:
    BRAVE_API_KEY    – Brave Search API key (for web search tool)
"""

import json
import os
import subprocess

from openai import OpenAI  # type: ignore

# ── client ────────────────────────────────────────────────────────────────────

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# ── system prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), \
Tony Stark's personal AI assistant — now at the user's service.

Personality & style
• Address the user as "Boss".
• Be concise, professional, and occasionally witty.
• When speaking aloud, avoid markdown symbols (*, #, backticks) — write \
naturally so text-to-speech sounds fluent.
• When writing code in chat, use plain code blocks.

Code-fixing capability
You have tools to read, edit, and run code files on the local filesystem.
When asked to fix code:
1. Use read_file to inspect the relevant files.
2. Identify the bugs, logic errors, or style issues.
3. Use write_file to apply the corrected code.
4. Optionally use run_command to verify the fix (e.g. `python -m py_compile`).
5. Give the user a clear summary of what was wrong and what you changed.

Be safe: never run destructive shell commands (rm -rf, format, etc.).
If asked to run something dangerous, refuse politely.
"""

# ── tool definitions ──────────────────────────────────────────────────────────

_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a file on disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path of the file to read.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (create or overwrite) a file on disk with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete new content for the file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to list. Defaults to current working directory.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a safe, read-only or diagnostic shell command and return "
                "its stdout/stderr. Use for linting, syntax checks, running "
                "tests, etc. Do NOT use for destructive operations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using Brave Search and return top results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]

# ── tool implementations ──────────────────────────────────────────────────────

_DANGEROUS_PATTERNS = (
    "rm -rf", "rm -r", "format", "mkfs", "dd if=", ":(){:|:&};:",
    "chmod 777", "shutdown", "reboot", "halt", "poweroff",
    "DROP TABLE", "DELETE FROM",
)


def _tool_read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        lines = content.splitlines()
        numbered = "\n".join(f"{i+1:4}: {l}" for i, l in enumerate(lines))
        return f"File: {path}  ({len(lines)} lines)\n\n{numbered}"
    except FileNotFoundError:
        return f"ERROR: File not found – {path}"
    except Exception as exc:
        return f"ERROR reading {path}: {exc}"


def _tool_write_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return f"SUCCESS: Wrote {len(content)} chars to {path}"
    except Exception as exc:
        return f"ERROR writing {path}: {exc}"


def _tool_list_files(directory: str = ".") -> str:
    try:
        entries = sorted(os.listdir(directory or "."))
        lines = []
        for e in entries:
            full = os.path.join(directory or ".", e)
            tag = "/" if os.path.isdir(full) else ""
            lines.append(f"  {e}{tag}")
        return f"Directory: {os.path.abspath(directory or '.')}\n" + "\n".join(lines)
    except Exception as exc:
        return f"ERROR listing {directory}: {exc}"


def _tool_run_command(command: str) -> str:
    for pat in _DANGEROUS_PATTERNS:
        if pat.lower() in command.lower():
            return f"REFUSED: Command contains a dangerous pattern ({pat!r})."
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out (30s)."
    except Exception as exc:
        return f"ERROR running command: {exc}"


def _tool_web_search(query: str) -> str:
    api_key = os.getenv("BRAVE_API_KEY", "").strip()
    if not api_key:
        return "ERROR: BRAVE_API_KEY not set."
    try:
        import httpx  # type: ignore

        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            params={"q": query, "count": 5},
            timeout=15,
        )
        data = resp.json()
        results = data.get("web", {}).get("results", [])
        lines = []
        for r in results:
            lines.append(f"• {r.get('title')}\n  {r.get('url')}\n  {r.get('description','')}")
        return "\n\n".join(lines) if lines else "No results found."
    except Exception as exc:
        return f"ERROR searching: {exc}"


_TOOL_HANDLERS: dict = {
    "read_file": lambda args: _tool_read_file(args["path"]),
    "write_file": lambda args: _tool_write_file(args["path"], args["content"]),
    "list_files": lambda args: _tool_list_files(args.get("directory", ".")),
    "run_command": lambda args: _tool_run_command(args["command"]),
    "web_search": lambda args: _tool_web_search(args["query"]),
}

# ── main chat function ────────────────────────────────────────────────────────


def chat(history: list[dict]) -> tuple[str, list[dict]]:
    """
    Send the conversation *history* to GPT-4o (with tools) and return
    (response_text, updated_history).

    Tool calls are executed automatically in an agentic loop until the model
    produces a final text response.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    while True:
        response = _client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.6,
        )

        msg = response.choices[0].message
        finish = response.choices[0].finish_reason

        # Append assistant message (may include tool_calls)
        messages.append(msg.model_dump(exclude_unset=False))

        if finish == "tool_calls" and msg.tool_calls:
            # Execute each requested tool and feed results back
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                handler = _TOOL_HANDLERS.get(fn_name)
                if handler:
                    print(f"  🔧  Tool: {fn_name}({', '.join(str(v)[:60] for v in fn_args.values())})")
                    tool_result = handler(fn_args)
                else:
                    tool_result = f"ERROR: Unknown tool '{fn_name}'"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })
            # Loop back for the next model response
            continue

        # Final text response
        text = (msg.content or "").strip()

        # Rebuild history (drop system prompt; keep everything else)
        new_history = [m for m in messages if m.get("role") != "system"]
        return text, new_history
