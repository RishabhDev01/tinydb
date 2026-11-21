"""Tools the agents can call, each enforcing its own limits in code (ADR-005).

An agent only receives the tools it is given. A tool that is not in its set
does not exist for it. Paths are resolved and checked on every call.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

OUTPUT_LIMIT = int(os.environ.get("AUTOSE_TOOL_OUTPUT_CHARS", "3000"))
READ_MAX_LINES = 80
SECRET_RE = re.compile(r"(gsk_|ghp_|ghs_|gho_|github_pat_)[A-Za-z0-9_]{8,}")

# Paths agents may never write (ADR-009: they cannot rewrite their guardrails)
WRITE_DENY = (".github", "autose", "skills", ".git", ".autose",
              "ARCHITECTURE.md", "pyproject.toml", "pytest.ini", "uv.lock")
WRITE_ALLOW = ("tinydb/", "tests/", "docs/")


def redact(text: str) -> str:
    return SECRET_RE.sub("[REDACTED]", text)


def clip(text: str, limit: int = OUTPUT_LIMIT, tail: bool = False) -> str:
    text = redact(text)
    if len(text) <= limit:
        return text
    cut = len(text) - limit
    if tail:
        return f"[... {cut} chars truncated ...]\n" + text[-limit:]
    return text[:limit] + f"\n[... {cut} chars truncated ...]"


class ToolError(Exception):
    pass


class Workspace:
    def __init__(self, root: str, deny_read: tuple = ()):
        self.root = Path(root).resolve()
        self.deny_read = deny_read

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def resolve(self, path: str, write: bool = False) -> Path:
        p = (self.root / (path or ".")).resolve()
        if p != self.root and self.root not in p.parents:
            raise ToolError(f"path outside repository: {path}")
        rel = "" if p == self.root else self.rel(p)
        for d in self.deny_read:
            if rel == d or rel.startswith(d + "/"):
                raise ToolError(f"access to {d} is not allowed")
        if write:
            if any(rel == d or rel.startswith(d + "/") for d in WRITE_DENY):
                raise ToolError(f"writing {rel} is not allowed")
            if not rel.startswith(WRITE_ALLOW):
                raise ToolError(f"you may only write under {WRITE_ALLOW}")
        return p

    # ---- read tools ----------------------------------------------------
    def list_dir(self, path: str = ".") -> str:
        p = self.resolve(path)
        if not p.is_dir():
            raise ToolError(f"not a directory: {path}")
        items = []
        for c in sorted(p.iterdir()):
            if c.name.startswith(".") or c.name == "__pycache__":
                continue
            items.append(c.name + ("/" if c.is_dir() else ""))
        return "\n".join(items) or "(empty)"

    def read_file(self, path: str, start_line: int = 1,
                  max_lines: int = READ_MAX_LINES) -> str:
        p = self.resolve(path)
        if not p.is_file():
            raise ToolError(f"not a file: {path}")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, int(start_line))
        n = min(int(max_lines), READ_MAX_LINES)
        chunk = lines[start - 1:start - 1 + n]
        body = "\n".join(f"{i:4d}| {l}" for i, l in
                         enumerate(chunk, start=start))
        more = ""
        if start - 1 + n < len(lines):
            more = (f"\n[file has {len(lines)} lines; call read_file with "
                    f"start_line={start + n} for more]")
        return clip(body, limit=5000) + more

    def grep(self, pattern: str, path: str = ".") -> str:
        try:
            rx = re.compile(pattern)
        except re.error as e:
            raise ToolError(f"bad regex: {e}")
        base = self.resolve(path)
        files = [base] if base.is_file() else sorted(base.rglob("*.py")) + \
            sorted(base.rglob("*.md")) + sorted(base.rglob("*.rst"))
        hits = []
        for f in files:
            rel = self.rel(f)
            if any(rel.startswith(d) for d in self.deny_read) or \
                    "/." in "/" + rel:
                continue
            try:
                for i, line in enumerate(
                        f.read_text(encoding="utf-8",
                                    errors="replace").splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{rel}:{i}: {line.strip()[:160]}")
                        if len(hits) >= 60:
                            return "\n".join(hits) + "\n[60 hits shown]"
            except OSError:
                continue
        return "\n".join(hits) or "(no matches)"

    # ---- write tools (builder only) -------------------------------------
    def write_file(self, path: str, content: str) -> str:
        p = self.resolve(path, write=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote {self.rel(p)} ({len(content.splitlines())} lines)"

    def edit_file(self, path: str, old_string: str, new_string: str) -> str:
        p = self.resolve(path, write=True)
        if not p.is_file():
            raise ToolError(f"not a file: {path} (use write_file to create)")
        text = p.read_text(encoding="utf-8")
        n = text.count(old_string)
        if n == 0:
            raise ToolError("old_string not found; read the file again and "
                            "copy the exact text including indentation")
        if n > 1:
            raise ToolError(f"old_string occurs {n} times; include more "
                            "surrounding lines to make it unique")
        p.write_text(text.replace(old_string, new_string, 1),
                     encoding="utf-8")
        return f"edited {self.rel(p)}"

    # ---- test runner (builder and reviewer) -----------------------------
    def run_tests(self, path: str = "") -> str:
        code, out = run_pytest(self.root, path)
        return f"exit code {code}\n" + clip(out, tail=True)


def safe_env() -> dict:
    """Environment for subprocesses: no API keys or GitHub tokens."""
    return {k: v for k, v in os.environ.items()
            if not re.search(r"KEY|TOKEN|SECRET|PASSWORD", k, re.I)}


def run_pytest(root: Path, path: str = "", timeout: int = 300):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "-o", "addopts=", "--tb=short"]
    if path:
        rel = Path(path).as_posix()
        if not rel.startswith("tests") or ".." in rel:
            raise ToolError("run_tests path must be under tests/")
        cmd.append(rel)
    try:
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                           timeout=timeout, env=safe_env())
    except subprocess.TimeoutExpired:
        return 124, f"pytest timed out after {timeout}s"
    return r.returncode, r.stdout + r.stderr


# ---- tool schemas -------------------------------------------------------
def _fn(name, desc, props, required):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props,
                       "required": required}}}


S = {"type": "string"}
I = {"type": "integer"}
SCHEMAS = {
    "list_dir": _fn("list_dir", "List a directory of the repository.",
                    {"path": S}, []),
    "read_file": _fn("read_file", "Read up to 80 lines of a file, with line "
                     "numbers.", {"path": S, "start_line": I,
                                  "max_lines": I}, ["path"]),
    "grep": _fn("grep", "Search .py/.md/.rst files with a Python regex. "
                "Returns file:line: text.", {"pattern": S, "path": S},
                ["pattern"]),
    "write_file": _fn("write_file", "Create or overwrite a file under "
                      "tinydb/, tests/ or docs/.", {"path": S, "content": S},
                      ["path", "content"]),
    "edit_file": _fn("edit_file", "Replace one exact, unique occurrence of "
                     "old_string with new_string in a file.",
                     {"path": S, "old_string": S, "new_string": S},
                     ["path", "old_string", "new_string"]),
    "run_tests": _fn("run_tests", "Run pytest. Optional path under tests/ "
                     "to run a subset. Returns exit code and output tail.",
                     {"path": S}, []),
}


def toolset(ws: Workspace, names: list) -> tuple[list, dict]:
    impl = {n: getattr(ws, n) for n in names}
    return [SCHEMAS[n] for n in names], impl
