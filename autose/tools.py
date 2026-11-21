"""Tools the agents can call, each enforcing its own limits in code (ADR-005).

An agent only receives the tools it is given. A tool that is not in its set
does not exist for it. Paths are resolved and checked on every call.
"""
import difflib
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
                  max_lines: int = READ_MAX_LINES, **kw) -> str:
        # Models call this with many argument names (run 44939124496 used
        # line_start/line_end 13 times); accept them instead of failing.
        start_line = kw.get("line_start", kw.get("start", kw.get(
            "offset", start_line))) or 1
        end = kw.get("line_end", kw.get("end"))
        if end is not None:
            max_lines = int(end) - int(start_line) + 1
        max_lines = kw.get("limit", max_lines)
        p = self.resolve(path)
        if not p.is_file():
            raise ToolError(f"not a file: {path}")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, int(start_line))
        n = max(1, min(int(max_lines), READ_MAX_LINES))
        chunk = lines[start - 1:start - 1 + n]
        body = "\n".join(f"{i:4d}| {l}" for i, l in
                         enumerate(chunk, start=start))
        more = ""
        if start - 1 + n < len(lines):
            more = (f"\n[file has {len(lines)} lines; call read_file with "
                    f"start_line={start + n} for more]")
        return clip(body, limit=5000) + more

    def grep(self, pattern: str, path: str = ".", **_ignored) -> str:
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

    def edit_file(self, path: str, old_string: str, new_string: str,
                  **_ignored) -> str:
        """Exact replace; falls back to an indentation-insensitive match.

        In run 44939124496 the builder failed 9 edits because its
        old_string was indented differently from the file (ADR-014).
        """
        p = self.resolve(path, write=True)
        if not p.is_file():
            raise ToolError(f"not a file: {path} (use write_file to create)")
        old_string = strip_line_numbers(old_string)
        new_string = strip_line_numbers(new_string)
        text = p.read_text(encoding="utf-8")
        n = text.count(old_string)
        if n == 1:
            p.write_text(text.replace(old_string, new_string, 1),
                         encoding="utf-8")
            return f"edited {self.rel(p)}\n" + self._around(p, text.find(
                old_string), new_string)
        if n > 1:
            raise ToolError(f"old_string occurs {n} times; include more "
                            "surrounding lines, or use replace_lines")
        # Fuzzy: compare lines with surrounding whitespace stripped.
        lines = text.splitlines(keepends=True)
        want = [l.strip() for l in old_string.strip("\n").splitlines()]
        want_nb = [w for w in want if w]
        hits = []
        for i in range(len(lines)):
            got, j = [], i
            while j < len(lines) and len(got) < len(want_nb):
                if lines[j].strip():
                    got.append(lines[j].strip())
                j += 1
            if got == want_nb and lines[i].strip() == want_nb[0]:
                hits.append((i, j))
        if len(hits) == 1:
            i, j = hits[0]
            file_indent = _indent(lines[i])
            old_first = next(l for l in old_string.splitlines() if l.strip())
            delta = len(file_indent) - len(_indent(old_first))
            new_lines = [(" " * delta + l if delta >= 0 else
                          l[min(-delta, len(_indent(l))):]) if l.strip()
                         else "" for l in new_string.splitlines()]
            lines[i:j] = [l + "\n" for l in new_lines]
            p.write_text("".join(lines), encoding="utf-8")
            return (f"edited {self.rel(p)} (matched ignoring indentation, "
                    f"lines {i + 1}-{j}; new text re-indented by {delta})\n"
                    + self._show(p, i + 1, i + len(new_lines)))
        hint = self._closest(lines, want_nb[0] if want_nb else "")
        raise ToolError("old_string not found (even ignoring indentation). "
                        "Prefer replace_lines(path, start_line, end_line, "
                        "new_text) using the line numbers from read_file."
                        + hint)

    def replace_lines(self, path: str, start_line: int, end_line: int,
                      new_text: str, **_ignored) -> str:
        """Replace lines start_line..end_line (inclusive, 1-based)."""
        p = self.resolve(path, write=True)
        if not p.is_file():
            raise ToolError(f"not a file: {path}")
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        s, e = int(start_line), int(end_line)
        if not (1 <= s <= e + 1 and e <= len(lines) and s <= len(lines) + 1):
            raise ToolError(f"bad range {s}-{e}; file has {len(lines)} lines "
                            "(use end_line = start_line - 1 to insert)")
        new = strip_line_numbers(new_text).splitlines()
        lines[s - 1:e] = [l + "\n" for l in new]
        p.write_text("".join(lines), encoding="utf-8")
        return (f"replaced lines {s}-{e} of {self.rel(p)} with {len(new)} "
                "lines. Line numbers below this point have shifted:\n"
                + self._show(p, max(1, s - 2), s + len(new) + 1))

    def _show(self, p: Path, a: int, b: int) -> str:
        lines = p.read_text(encoding="utf-8").splitlines()
        return "\n".join(f"{i:4d}| {lines[i - 1]}"
                         for i in range(max(1, a), min(len(lines), b) + 1))

    def _around(self, p: Path, offset: int, new: str) -> str:
        line = p.read_text(encoding="utf-8")[:max(0, offset)].count("\n") + 1
        return self._show(p, line - 1, line + len(new.splitlines()))

    def _closest(self, lines: list, first: str) -> str:
        if not first:
            return ""
        best = difflib.get_close_matches(
            first, [l.strip() for l in lines], n=1, cutoff=0.5)
        if not best:
            return ""
        idx = [l.strip() for l in lines].index(best[0])
        body = "\n".join(f"{i + 1:4d}| {lines[i].rstrip()}" for i in
                         range(max(0, idx - 2), min(len(lines), idx + 8)))
        return f"\nClosest match in the file:\n{body}"

    # ---- test runner (builder and reviewer) -----------------------------
    def run_tests(self, path: str = "", **_ignored) -> str:
        code, out = run_pytest(self.root, path)
        return f"exit code {code}\n" + clip(out, tail=True)


LINE_NO = re.compile(r"^\s*\d+\| ?")


def strip_line_numbers(text: str) -> str:
    """Remove '  123| ' prefixes copied from read_file output."""
    lines = text.splitlines()
    nonblank = [l for l in lines if l.strip()]
    if nonblank and all(LINE_NO.match(l) for l in nonblank):
        return "\n".join(LINE_NO.sub("", l, count=1) for l in lines) + \
            ("\n" if text.endswith("\n") else "")
    return text


def _indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


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
                     "numbers ('  123| code'). Use start_line + max_lines, or "
                     "line_start + line_end.",
                     {"path": S, "start_line": I, "max_lines": I,
                      "line_start": I, "line_end": I}, ["path"]),
    "grep": _fn("grep", "Search .py/.md/.rst files with a Python regex. "
                "Returns file:line: text.", {"pattern": S, "path": S},
                ["pattern"]),
    "write_file": _fn("write_file", "Create or overwrite a file under "
                      "tinydb/, tests/ or docs/.", {"path": S, "content": S},
                      ["path", "content"]),
    "edit_file": _fn("edit_file", "Replace one unique occurrence of "
                     "old_string with new_string (indentation differences "
                     "are tolerated). Do not include the '123| ' prefixes.",
                     {"path": S, "old_string": S, "new_string": S},
                     ["path", "old_string", "new_string"]),
    "replace_lines": _fn("replace_lines", "MOST RELIABLE EDIT: replace lines "
                         "start_line..end_line (inclusive, numbers from "
                         "read_file) with new_text. Write new_text with its "
                         "final indentation and no '123| ' prefixes. To "
                         "insert without deleting, use end_line = "
                         "start_line - 1.",
                         {"path": S, "start_line": I, "end_line": I,
                          "new_text": S},
                         ["path", "start_line", "end_line", "new_text"]),
    "run_tests": _fn("run_tests", "Run pytest. Optional path under tests/ "
                     "to run a subset. Returns exit code and output tail.",
                     {"path": S}, []),
}


def toolset(ws: Workspace, names: list) -> tuple[list, dict]:
    impl = {n: getattr(ws, n) for n in names}
    return [SCHEMAS[n] for n in names], impl
