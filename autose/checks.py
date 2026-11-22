"""Deterministic stage checks (ADR-007). The orchestrator owns pass or fail."""
import re
import subprocess
import sys
from pathlib import Path

from .tools import safe_env

BANNED = ["fast", "efficient", "robust", "user-friendly", "intuitive",
          "properly", "correctly", "gracefully", "appropriate", "etc",
          "and so on", "should work"]

# Files that the builder may not change (ADR-009)
FORBIDDEN_PREFIXES = (".github/", "autose/", "skills/", "ARCHITECTURE.md",
                      "pyproject.toml", "pytest.ini", "uv.lock")


def parse_acs(spec: str) -> dict:
    """Return {'AC-1': block_text, ...} from a spec in the skill's template."""
    parts = re.split(r"^###\s*(AC-\d+)\b.*$", spec, flags=re.M)
    acs = {}
    for i in range(1, len(parts) - 1, 2):
        acs[parts[i]] = parts[i + 1].split("\n## ")[0].strip()
    return acs


def check_spec(spec: str) -> tuple[dict, list]:
    problems = []
    if re.search(r"^\*\*Summary:\*\*\s*STOP:", spec, flags=re.M):
        return {}, ["STOP"]
    for section in ("## Acceptance criteria", "## Assumptions",
                    "## API touched"):
        if section.lower() not in spec.lower():
            problems.append(f"missing section '{section}'")
    acs = parse_acs(spec)
    if not acs:
        problems.append("no acceptance criteria headed '### AC-n: ...'")
    nums = [int(k.split("-")[1]) for k in acs]
    if nums and nums != list(range(1, len(nums) + 1)):
        problems.append(f"AC numbering must be 1..n without gaps, got {nums}")
    if len(acs) > 6:
        problems.append(f"too many ACs ({len(acs)}); keep 2-5")
    for ac, body in acs.items():
        for kw in ("given", "when", "then"):
            if not re.search(rf"\*\*{kw}\*\*|^\s*-?\s*{kw}\b", body,
                             flags=re.I | re.M):
                problems.append(f"{ac}: missing '{kw.title()}' line")
        low = body.lower()
        for w in BANNED:
            if re.search(rf"\b{re.escape(w)}\b", low):
                problems.append(f"{ac}: untestable wording '{w}'")
    return acs, problems


def parse_design_rows(design: str) -> list:
    m = re.search(r"^## Files to change\s*$(.*?)(?=^## |\Z)", design,
                  flags=re.M | re.S)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|")
                 .split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: ") or \
                cells[0].lower() in ("file", "path"):
            continue
        rows.append(cells)
    return rows


def check_design(design: str, root: Path) -> list:
    problems = []
    rows = parse_design_rows(design)
    if not rows:
        return ["missing '## Files to change' table with rows "
                "| file | function/class | change |"]
    if "## test plan" not in design.lower():
        problems.append("missing '## Test plan' section")
    for path, symbol, change, *_ in rows:
        is_new = "NEW" in symbol or "NEW" in change or "NEW" in path
        clean = path.replace("(NEW)", "").strip()
        f = root / clean
        if not f.exists():
            if not is_new:
                problems.append(f"{clean}: file does not exist (mark NEW if "
                                "it is to be created)")
            continue
        if is_new or not symbol or symbol in ("-", "—"):
            continue
        name = re.split(r"[.(\s]", symbol.replace("`", ""))
        name = [n for n in name if n][-1] if any(name) else ""
        if name and not re.search(rf"^\s*(def|class)\s+{re.escape(name)}\b"
                                  rf"|^{re.escape(name)}\s*=",
                                  f.read_text(encoding="utf-8"), flags=re.M):
            problems.append(f"{clean}: '{symbol}' not found (mark NEW if it "
                            "is to be added)")
    return problems


def check_build(root: Path) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, "-m", "compileall", "-q", "tinydb",
                        "tests"], cwd=root, capture_output=True, text=True,
                       env=safe_env())
    if r.returncode != 0:
        return False, r.stdout + r.stderr
    r = subprocess.run([sys.executable, "-c", "import tinydb"], cwd=root,
                       capture_output=True, text=True, env=safe_env())
    return r.returncode == 0, r.stdout + r.stderr


def changed_files(root: Path, base: str) -> list:
    r = subprocess.run(["git", "diff", "--name-only", base, "--", ".",
                        ":(exclude).autose"], cwd=root, capture_output=True,
                       text=True)
    out = set(r.stdout.split())
    r = subprocess.run(["git", "ls-files", "--others", "--exclude-standard",
                        "--", ".", ":(exclude).autose"], cwd=root,
                       capture_output=True, text=True)
    out |= set(r.stdout.split())
    return sorted(out)


def forbidden_changes(files: list) -> list:
    return [f for f in files if f.startswith(FORBIDDEN_PREFIXES)]


# ADR-026: run 27's builder made Table.search() walk the call stack and
# run the old code when called from one existing test. Production code
# must never detect that it is under test.
GAMING = [
    (re.compile(r"\b_getframe\b|\binspect\.(stack|currentframe|"
                r"getouterframes|getframeinfo)\b|\btraceback\."
                r"(extract_stack|format_stack|walk_stack)\b"),
     "inspects the call stack"),
    (re.compile(r"PYTEST_CURRENT_TEST|['\"]pytest['\"]\s+in\s+sys\.modules"
                r"|\bimport\s+pytest\b|\bfrom\s+_?pytest\b"),
     "detects pytest"),
    (re.compile(r"['\"][^'\"\n]*\btest_\w+[^'\"\n]*['\"]"),
     "names a test in a string"),
    (re.compile(r"\bco_name\b|\bf_code\b|\bf_back\b"),
     "reads frame objects"),
]


def test_gaming(diff: str) -> list:
    """Added lines under tinydb/ that detect or special-case tests."""
    hits, path = [], ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[4:].removeprefix("b/")
            continue
        if not path.startswith("tinydb/") or not line.startswith("+") \
                or line.startswith("+++"):
            continue
        for pattern, why in GAMING:
            if pattern.search(line):
                hits.append(f"{path}: {line[1:].strip()[:120]}  ({why})")
                break
    return hits


_FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+?\.py)::([^\s\[]+)", re.M)


def failing_tests(output: str) -> list:
    """['tests/x.py::test_y', ...] from pytest's short summary; the
    [memory]/[json] parameters are dropped."""
    return sorted({f"{p.replace(chr(92), '/')}::{n}"
                   for p, n in _FAILED.findall(output)})


_SECTION = re.compile(r"^_{3,} (.+?) _{3,}$", re.M)
_FRAME = re.compile(r"^(\S+\.py):(\d+): in (\S+)$")


def failure_digest(output: str, max_tests: int = 8,
                   limit: int = 3500) -> str:
    """Each failing test once: where it failed and its first error lines.

    ADR-024: in run 22 the builder got the tail of pytest's output, which
    was 19 one-line summaries cut at the terminal width, with no location
    and no traceback. It could see that tests failed but not why.
    Parametrized cases with the same error are merged ([memory, json]).
    Expects ``--tb=short`` output; returns "" if there is no FAILURES or
    ERRORS section (the caller then falls back to the raw tail).
    """
    m = re.search(r"^=+ (?:FAILURES|ERRORS) =+$", output, re.M)
    if not m:
        return ""
    body = output[m.end():]
    end = re.search(r"^=+ (?:short test summary info|warnings summary|"
                    r"\d+ (?:failed|passed|error)).*$", body, re.M)
    if end:
        body = body[:end.start()]
    parts = _SECTION.split(body)
    entries, index = [], {}
    for name, text in zip(parts[1::2], parts[2::2]):
        lines = [ln.rstrip().replace("\\", "/") for ln in text.splitlines()
                 if ln.strip()]
        frames = [i for i, ln in enumerate(lines) if _FRAME.match(ln)]
        errors = [ln[:220] for ln in lines if ln.startswith("E ")][:2]
        base, _, param = name.partition("[")
        key = (base, errors[0] if errors else "")
        if key in index:
            if param:
                entries[index[key]]["params"].append(param.rstrip("]"))
            continue
        shown = []
        # The test's own line, and the deepest frame if the error was
        # raised inside tinydb/.
        for i in sorted({frames[0], frames[-1]}) if frames else []:
            shown.append(lines[i])
            if i + 1 < len(lines) and lines[i + 1].startswith("    "):
                shown.append(lines[i + 1])
        path = _FRAME.match(lines[frames[0]]).group(1) if frames else ""
        index[key] = len(entries)
        entries.append({"name": f"{path}::{base}" if path else base,
                        "params": [param.rstrip("]")] if param else [],
                        "lines": shown + errors})
    out = []
    for k, e in enumerate(entries[:max_tests]):
        head = f"- {e['name']}"
        if e["params"]:
            head += f" [{', '.join(e['params'])}]"
        block = "\n".join([head] + ["    " + ln for ln in e["lines"]])
        if out and len("\n".join(out)) + len(block) > limit:
            out.append(f"... and {len(entries) - k} more failing test(s)")
            return "\n".join(out)
        out.append(block)
    if len(entries) > max_tests:
        out.append(f"... and {len(entries) - max_tests} more failing "
                   "test(s)")
    return "\n".join(out)


def pytest_counts(output: str) -> dict:
    counts = {}
    for n, kind in re.findall(r"(\d+) (passed|failed|error|errors|skipped)",
                              output):
        counts[kind.rstrip("s") if kind == "errors" else kind] = int(n)
    return counts


def ac_test_map(acs: dict, root: Path, files: list) -> dict:
    """Map each AC to the new or changed tests that mention it."""
    result = {ac: [] for acs_ in [acs] for ac in acs_}
    for f in files:
        if not f.startswith("tests/") or not f.endswith(".py"):
            continue
        p = root / f
        if not p.exists():
            continue
        current = None
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*def (test_\w+)", line)
            if m:
                current = m.group(1)
            for ac in acs:
                if re.search(rf"\b{ac}\b", line) and current:
                    if f"{f}::{current}" not in result[ac]:
                        result[ac].append(f"{f}::{current}")
    return result
