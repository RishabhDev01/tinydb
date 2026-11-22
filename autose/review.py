"""Stage 6: the independent reviewer (ADR-008).

Runs in its own job, on a fresh checkout of the PR head, with a read-only
token. It sees ONLY the issue, the diff and the repository. The .autose/
folder (spec, design, test report) is deleted before it starts and is also
blocked by the tools. Its output goes to files; the separate post job
publishes them.

    python -m autose.review --pr 6 --issue 3 --round 1 --out review-out
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from . import gh
from .agent import AgentStopped, run_agent
from .llm import USAGE, BudgetExceeded, LLMError
from .tools import Workspace, clip, toolset

ROOT = Path.cwd()
# ADR-021: a different Gemini series from the builder (gemini-3.8-flash).
MODEL = os.environ.get("REVIEWER_MODEL", "gemini-4-hydrogen")
BUDGET = int(os.environ.get("REVIEWER_BUDGET", "250000"))

ITEM = {"type": "object"}
VERDICT_SCHEMA = {"type": "object", "properties": {
    "verdict": {"type": "string", "enum": ["approve", "changes"]},
    "target": {"type": "string", "enum": ["design", "implement", "none"],
               "description": "where changes must go; 'none' if approve"},
    "requirements": {"type": "array", "items": {
        "type": "object", "properties": {
            "requirement": {"type": "string"}, "evidence": {"type": "string"},
            "met": {"type": "boolean"}}}},
    "risks_checked": {"type": "array", "items": {
        "type": "object", "properties": {
            "risk": {"type": "string"}, "result": {"type": "string"},
            "is_defect": {"type": "boolean"}}}},
    "findings": {"type": "array", "items": {
        "type": "object", "properties": {
            "location": {"type": "string"}, "problem": {"type": "string"},
            "fix": {"type": "string"}}}},
    "summary": {"type": "string"}},
    "required": ["verdict", "target", "requirements", "risks_checked",
                 "findings", "summary"]}


def validate(v: dict, tests_ran: bool) -> list:
    """Code-side checks that stop a rubber-stamp approval (ADR-008)."""
    problems = []
    if not tests_ran:
        problems.append("you did not call run_tests; run the full suite")
    if len(v.get("risks_checked", [])) < 2:
        problems.append("check at least two concrete risks or edge cases")
    if not v.get("requirements"):
        problems.append("list the issue's requirements with evidence")
    if v.get("verdict") == "approve":
        unmet = [r.get("requirement") for r in v.get("requirements", [])
                 if not r.get("met")]
        defects = [r.get("risk") for r in v.get("risks_checked", [])
                   if r.get("is_defect")]
        if unmet or defects or v.get("findings"):
            problems.append("you approved but listed unmet requirements, "
                            "defects or findings; either request changes or "
                            "remove items that are not real problems")
    if v.get("verdict") == "changes" and v.get("target") not in (
            "design", "implement"):
        problems.append("with verdict 'changes', target must be design or "
                        "implement")
    if v.get("verdict") == "changes" and not v.get("findings"):
        problems.append("requesting changes needs at least one finding")
    return problems


def render(v: dict, round_no: int, pr: int) -> str:
    icon = "APPROVE" if v["verdict"] == "approve" else "CHANGES REQUESTED"
    lines = [f"<!-- autose-review round={round_no} -->",
             f"## AutoSE independent review, round {round_no}: **{icon}**",
             "", f"Reviewer model: `{MODEL}` (read-only; did not see the "
             "spec, design, test report or the implementer's reasoning).",
             "", f"**Summary:** {v.get('summary', '')}", ""]
    if v["verdict"] == "changes":
        lines.append(f"**Route back to:** `{v['target']}`\n")
    lines += ["### Issue requirements → evidence", "",
              "| Requirement | Met | Evidence |", "|---|---|---|"]
    for r in v.get("requirements", []):
        lines.append(f"| {r.get('requirement', '')} | "
                     f"{'yes' if r.get('met') else '**no**'} | "
                     f"{r.get('evidence', '')} |".replace("\n", " "))
    lines += ["", "### Risks and edge cases checked", "",
              "| Risk | Defect? | Result |", "|---|---|---|"]
    for r in v.get("risks_checked", []):
        lines.append(f"| {r.get('risk', '')} | "
                     f"{'**yes**' if r.get('is_defect') else 'no'} | "
                     f"{r.get('result', '')} |".replace("\n", " "))
    if v.get("findings"):
        lines += ["", "### Findings", ""]
        for i, f in enumerate(v["findings"], 1):
            lines.append(f"{i}. `{f.get('location', '')}`: "
                         f"{f.get('problem', '')}. **Fix:** "
                         f"{f.get('fix', '')}")
    if v.get("forced"):
        lines += ["", f"> Note: {v['forced']}"]
    lines += ["", f"_Run: {gh.run_url()}_"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--out", default="review-out")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # Independence: remove the implementer's artifacts from this checkout.
    shutil.rmtree(ROOT / ".autose", ignore_errors=True)
    issue = gh.issue(a.issue)
    diff = gh.run(["git", "diff", "origin/master...HEAD", "--", ".",
                   ":(exclude).autose"])

    ws = Workspace(ROOT, deny_read=(".autose", "autose", ".github"))
    tools, impl = toolset(ws, ["list_dir", "read_file", "grep", "run_tests"])
    ran = {"tests": False}
    real_run = impl["run_tests"]

    def tracked_run_tests(path: str = ""):
        ran["tests"] = ran["tests"] or not path
        return real_run(path)
    impl["run_tests"] = tracked_run_tests

    sysmsg = (Path(__file__).parent / "prompts/reviewer.md").read_text(
        "utf-8")
    title = issue["title"].replace("</untrusted_issue>", "")
    body = (issue["body"] or "").replace("</untrusted_issue>", "")
    msgs = [{"role": "system", "content": sysmsg},
            {"role": "user", "content":
             f"<untrusted_issue number=\"{a.issue}\">\nTitle: {title}\n\n"
             f"{body}\n</untrusted_issue>\n\nPULL REQUEST #{a.pr} DIFF:\n"
             f"```diff\n{clip(diff, 6000)}\n```\n\nReview it. If the diff "
             "is truncated, read the changed files with read_file."}]
    verdict = None
    try:
        for attempt in range(3):
            v = run_agent(role="reviewer", model=MODEL, messages=msgs,
                          tools=tools, impl=impl,
                          finish_schema=VERDICT_SCHEMA, max_turns=25,
                          budget=BUDGET, max_chars=15000,
                          # Gemini counts thinking as output (ADR-021).
                          max_tokens=3000)
            problems = validate(v, ran["tests"])
            if not problems:
                verdict = v
                break
            msgs.append({"role": "user", "content":
                         "Your verdict was rejected by the checker:\n- " +
                         "\n- ".join(problems) + "\nFix this and call "
                         "finish again."})
        if verdict is None:
            # Never let an invalid verdict count as an approval.
            v["verdict"], v["target"] = "changes", v.get("target") \
                if v.get("target") in ("design", "implement") else "implement"
            v["forced"] = ("the verdict failed validation 3 times (" +
                           "; ".join(problems) + "), so it is recorded as "
                           "'changes' rather than an approval.")
            verdict = v
    except (AgentStopped, BudgetExceeded, LLMError) as e:
        (out / "error.txt").write_text(f"{type(e).__name__}: {e}",
                                       encoding="utf-8")
        gh.set_output(status="error")
        print(f"reviewer failed: {e}", file=sys.stderr)
        return 1

    verdict["tests_ran"] = ran["tests"]
    verdict["tokens"] = USAGE
    verdict["model"] = MODEL
    (out / "verdict.json").write_text(json.dumps(verdict, indent=2),
                                      encoding="utf-8")
    (out / "review.md").write_text(render(verdict, a.round, a.pr),
                                   encoding="utf-8")
    gh.set_output(status="ok", verdict=verdict["verdict"],
                  target=verdict["target"])
    gh.summary(f"**Review r{a.round}:** {verdict['verdict']} → "
               f"{verdict['target']}; tokens `{json.dumps(USAGE)}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
