"""Patch-mode builder (ADR-016): localize -> patch -> validate.

The orchestrator, not the model, finds the code to change: it reads the
design's "Files to change" rows and extracts those definitions (plus the
helpers they call) with ``ast``. The model gets that code in ONE request and
answers with whole replacement definitions in a fixed text format. We apply
them by name, so there are no line numbers or exact-match snippets to get
wrong, and no tool loop that can wander (runs 10 and 12).
"""
import ast
import re
import textwrap
from pathlib import Path

from .checks import FORBIDDEN_PREFIXES

CODE_PREFIX = "tinydb/"
MAX_CALLEES = 3
MAX_CALLEE_LINES = 80


class PatchError(Exception):
    pass


# ---- localize ---------------------------------------------------------------
def _clean_symbol(symbol: str) -> tuple[str, bool]:
    is_new = "NEW" in symbol
    s = symbol.replace("`", "").replace("(NEW)", "").replace("NEW", "")
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = s.split()[0] if s.split() else ""
    return s.strip(".:"), is_new


def _defs(tree: ast.Module) -> dict:
    """qualname -> node, for module-level defs and methods of classes."""
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            out[node.name] = node
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{node.name}.{sub.name}"] = sub
    return out


def resolve(defs: dict, name: str) -> str | None:
    """Find a qualname for 'Table.update', 'update' or '_update_table'."""
    if name in defs:
        return name
    tail = name.split(".")[-1]
    hits = [q for q in defs if q.split(".")[-1] == tail]
    return hits[0] if len(hits) == 1 else None


def _start(node) -> int:
    return min([node.lineno] + [d.lineno for d in
                                getattr(node, "decorator_list", [])])


def _source(lines: list, node) -> str:
    return "\n".join(lines[_start(node) - 1:node.end_lineno])


def _outline(lines: list, cls: ast.ClassDef) -> str:
    """Class header plus one line per method: enough to add a method."""
    out = [lines[cls.lineno - 1]]
    for sub in cls.body:
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(lines[sub.lineno - 1].rstrip() + "  ...")
    return "\n".join(out)


def _callees(node, cls_name: str | None, defs: dict) -> list:
    names = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id == "self" and cls_name:
            names.append(f"{cls_name}.{f.attr}")
        elif isinstance(f, ast.Name):
            names.append(f.id)
    seen, out = set(), []
    for q in names:
        if q in defs and q not in seen and \
                not isinstance(defs[q], ast.ClassDef):
            seen.add(q)
            out.append(q)
    return out


def localize(root: Path, rows: list, max_chars: int = 9000) -> list:
    """Code blocks for the design's rows: [{path, name, kind, code}]."""
    blocks, have = [], set()
    extra = []
    for row in rows:
        path = row[0].replace("(NEW)", "").strip().strip("`")
        if not path.startswith(CODE_PREFIX) or not path.endswith(".py"):
            continue
        f = root / path
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        lines = text.splitlines()
        defs = _defs(ast.parse(text))
        name, is_new = _clean_symbol(row[1] if len(row) > 1 else "")
        q = resolve(defs, name) if name else None
        if q and (path, q) in have:
            continue
        if q and isinstance(defs[q], ast.ClassDef):
            blocks.append({"path": path, "name": q, "kind": "class outline",
                           "code": _outline(lines, defs[q])})
            have.add((path, q))
            continue
        if q:   # existing, or NEW but already added by an earlier attempt
            node = defs[q]
            blocks.append({"path": path, "name": q, "kind": "definition",
                           "code": _source(lines, node)})
            have.add((path, q))
            cls = q.split(".")[0] if "." in q else None
            for c in _callees(node, cls, defs):
                extra.append((path, c, lines, defs))
            continue
        # A new method: show the class it goes into.
        owner = name.split(".")[0] if "." in name else None
        if owner and owner in defs and isinstance(defs[owner], ast.ClassDef) \
                and (path, owner) not in have:
            blocks.append({"path": path, "name": owner,
                           "kind": "class outline",
                           "code": _outline(lines, defs[owner])})
            have.add((path, owner))
    # ADR-024: helpers get their own share of the budget. In run 22 the
    # three large definitions used it all, so `_read_table` (whose
    # docstring says its doc IDs are still `str`) was never shown.
    used, budget = 0, max(2500, max_chars // 3)
    seen, unique = set(), []
    for item in extra:
        if (item[0], item[1]) not in seen:
            seen.add((item[0], item[1]))
            unique.append(item)
    for path, q, lines, defs in unique:
        node = defs[q]
        if (path, q) in have or node.end_lineno - _start(node) > \
                MAX_CALLEE_LINES:
            continue
        code = _source(lines, node)
        if used + len(code) > budget:
            continue
        blocks.append({"path": path, "name": q, "kind": "helper it calls",
                       "code": code})
        have.add((path, q))
        used += len(code)
        if sum(b["kind"] == "helper it calls" for b in blocks) >= MAX_CALLEES:
            break
    return blocks


def render_blocks(blocks: list) -> str:
    return "\n\n".join(f"#### {b['path']} :: {b['name']} ({b['kind']})\n"
                       f"```python\n{b['code']}\n```" for b in blocks)


# ---- parse the model's answer ---------------------------------------------
HEAD = re.compile(r"^###\s+(REPLACE|ADD|TESTS|SUMMARY)\b[ \t]*(.*)$", re.M)
FENCE = re.compile(r"```[a-zA-Z]*\n(.*?)\n```", re.S)


def parse_answer(text: str) -> dict:
    """-> {"edits": [(op, path, target, code)], "tests": str, "summary": str}"""
    out = {"edits": [], "tests": "", "summary": ""}
    heads = list(HEAD.finditer(text))
    for i, h in enumerate(heads):
        body = text[h.end():heads[i + 1].start() if i + 1 < len(heads)
                    else len(text)]
        op, arg = h.group(1), h.group(2).strip().strip("`")
        if op == "SUMMARY":
            out["summary"] = body.strip()[:1500]
            continue
        m = FENCE.search(body)
        if not m:
            raise PatchError(f"'### {op} {arg}' has no ```python code block")
        code = m.group(1)
        if op == "TESTS":
            out["tests"] = code.strip("\n") + "\n"
            continue
        parts = arg.split()
        if len(parts) != 2:
            raise PatchError(f"'### {op} {arg}': expected "
                             f"'### {op} <path> <name>'")
        out["edits"].append((op, parts[0], parts[1], code))
    if not out["edits"]:
        raise PatchError("no '### REPLACE <path> <name>' or "
                         "'### ADD <path> <Class|MODULE>' block found")
    if not out["tests"]:
        raise PatchError("no '### TESTS' block found")
    return out


# ---- apply -------------------------------------------------------------------
def _check_path(path: str) -> None:
    if not path.startswith(CODE_PREFIX) or path.startswith(FORBIDDEN_PREFIXES) \
            or ".." in path or not path.endswith(".py"):
        raise PatchError(f"{path}: code edits may only touch tinydb/*.py")


def _reindent(code: str, indent: int) -> list:
    code = textwrap.dedent(code.strip("\n"))
    return [(" " * indent + ln) if ln.strip() else ""
            for ln in code.splitlines()]


def apply_edit(root: Path, op: str, path: str, target: str,
               code: str) -> str:
    _check_path(path)
    f = root / path
    if not f.exists():
        raise PatchError(f"{path}: file does not exist")
    text = f.read_text(encoding="utf-8")
    lines = text.splitlines()
    defs = _defs(ast.parse(text))
    if op == "REPLACE":
        q = resolve(defs, target)
        if not q:
            raise PatchError(f"{path}: no definition named {target!r} "
                             "(use ### ADD for a new one)")
        node = defs[q]
        new = _reindent(code, node.col_offset)
        lines[_start(node) - 1:node.end_lineno] = new
        done = f"replaced {path}::{q}"
    elif op == "ADD":
        # Adding a name that already exists (e.g. on a retry) replaces it.
        try:
            first = next(n for n in ast.parse(textwrap.dedent(
                code.strip("\n"))).body if isinstance(
                    n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
        except (SyntaxError, StopIteration) as e:
            raise PatchError(f"### ADD {path} {target}: the code block is "
                             f"not a valid definition ({e})") from e
        existing = first.name if target.upper() == "MODULE" else \
            f"{target}.{first.name}"
        if existing in defs:
            return apply_edit(root, "REPLACE", path, existing, code)
        if target.upper() == "MODULE":
            new = [""] + _reindent(code, 0)
            lines += [""] + new
        else:
            cls = defs.get(target)
            if not isinstance(cls, ast.ClassDef):
                raise PatchError(f"{path}: no class named {target!r}")
            new = [""] + _reindent(code, cls.col_offset + 4)
            lines[cls.end_lineno:cls.end_lineno] = new
        done = f"added to {path}::{target}"
    else:
        raise PatchError(f"unknown operation {op}")
    result = "\n".join(lines) + "\n"
    try:
        ast.parse(result)
    except SyntaxError as e:
        raise PatchError(f"{done} gives a syntax error at line {e.lineno}: "
                         f"{e.msg}") from e
    f.write_text(result, encoding="utf-8")
    return done


def apply_answer(root: Path, answer: dict, test_path: str) -> list:
    done = [apply_edit(root, *e) for e in answer["edits"]]
    (root / test_path).write_text(answer["tests"], encoding="utf-8")
    return done + [f"wrote {test_path}"]
