"""AutoSE orchestrator: a deterministic state machine (ADR-002).

    GUARD -> SPEC -> DESIGN -> IMPLEMENT <-> TEST -> RELEASE -> (review job)

Every transition is decided here, by code, from check results and counters.
State lives in .autose/issue-N/ on the branch autose/issue-N (ADR-004).

Usage (from the workflow's build job):
    python -m autose.orchestrator --issue 3 --round 1 --start auto
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import checks, gh, patcher
from .agent import AgentStopped, run_agent
from .llm import (LAST_FINISH, USAGE, BudgetExceeded, LLMError, QuotaExhausted,
                  RequestTooLarge, chat, extract_json, log, strip_think)
from .tools import Workspace, clip, run_pytest, toolset

ROOT = Path.cwd()
PROMPTS = Path(__file__).parent / "prompts"

MODELS = {
    "planner": os.environ.get("PLANNER_MODEL", "gemini-3.8-flash"),
    "builder": os.environ.get("BUILDER_MODEL", "gemini-3.8-flash"),
    "judge": os.environ.get("JUDGE_MODEL", "qwen/qwen3.8-27b"),
    "guard": os.environ.get("GUARD_MODEL",
                            "meta-llama/llama-prompt-guard-2-86m"),
}
BUDGET = {  # tokens per agent per run (ADR-009)
    # ADR-022: spec + design share this. 150k was sized for Groq's 8k TPM;
    # on Gemini run 17 used 126k and run 20 hit 153k in design (~$0.12).
    "planner": int(os.environ.get("PLANNER_BUDGET", "400000")),
    "builder": int(os.environ.get("BUILDER_BUDGET", "200000")),
    "judge": 30000,
}
# ADR-016: "patch" = localize -> one-shot patch -> validate (default);
# "agent" = the earlier free tool loop (ADR-005/014), kept for comparison.
BUILDER_MODE = os.environ.get("BUILDER_MODE", "patch")
# ADR-023: Gemini counts thinking as output. 3000 cut off run 21's answers
# (3 functions + tests); 12k is about $0.045 per call on 3.8 Flash.
BUILDER_MAX_TOKENS = int(os.environ.get("BUILDER_MAX_TOKENS", "12000"))
MAX_IMPLEMENT_ATTEMPTS = 3
MAX_DESIGN_REENTRIES = 1
MAX_SPEC_REDOS = 1
MAX_DESIGN_REDOS = 1

CONTENT_SCHEMA = {"type": "object", "properties": {
    "content": {"type": "string", "description": "the full markdown"}},
    "required": ["content"]}
SUMMARY_SCHEMA = {"type": "object", "properties": {
    "summary": {"type": "string"}}, "required": ["summary"]}


class Stop(Exception):
    """A stage could not pass its check: explain in the artifact and stop."""
    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage, self.reason = stage, reason


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _snapshot(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ADR-017: the agents' instructions are read ONCE, here at import, from the
# master checkout the job starts on, before setup() switches to the issue
# branch. Runs 10-13 read them later from a stale issue branch, so code and
# prompts did not match (run 13 crashed on a missing prompt file).
_PROMPTS = {p.name: _snapshot(p) for p in PROMPTS.glob("*.md")}
SKILL_TEXT = _snapshot(ROOT / "skills/spec-writer/SKILL.md")
ARCHITECTURE_TEXT = _snapshot(ROOT / "ARCHITECTURE.md")


def prompt(name: str, **kw) -> str:
    text = _PROMPTS[name]
    for k, v in kw.items():
        text = text.replace("{" + k + "}", v)
    return text


def untrusted(issue: dict) -> str:
    title = issue["title"].replace("</untrusted_issue>", "")
    body = (issue["body"] or "").replace("</untrusted_issue>", "")
    return (f"<untrusted_issue number=\"{issue['number']}\">\n"
            f"Title: {title}\n\n{body}\n</untrusted_issue>")


class Run:
    def __init__(self, issue_no: int, round_no: int, start: str):
        self.n = issue_no
        self.round = round_no
        self.branch = f"autose/issue-{issue_no}"
        self.dir = ROOT / ".autose" / f"issue-{issue_no}"
        self.start = start
        self.state: dict = {}
        self.issue: dict = {}
        self.acs: dict = {}
        self.base = ""
        self.baseline_passed = 0
        self.builder_msgs: list = []
        self.feedback = ""   # review findings or test failures to carry over

    # ---- state -----------------------------------------------------------
    def save(self) -> None:
        self.state["tokens"] = USAGE
        self.state["updated"] = now()
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "state.json").write_text(
            json.dumps(self.state, indent=2), encoding="utf-8")

    def event(self, stage: str, result: str, detail: str = "") -> None:
        entry = {"t": now(), "round": self.round, "stage": stage,
                 "result": result, "detail": detail[:300]}
        self.state.setdefault("history", []).append(entry)
        log(f"{stage}: {result} {detail[:120]}")
        gh.summary(f"| {entry['t']} | r{self.round} | {stage} | {result} | "
                   f"{detail[:120].replace('|', '/')} |")
        self.save()

    def write(self, name: str, text: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / name).write_text(text, encoding="utf-8")

    def read(self, name: str) -> str:
        p = self.dir / name
        return p.read_text(encoding="utf-8") if p.exists() else ""

    # ---- setup -------------------------------------------------------------
    def setup(self) -> str:
        gh.run(["git", "config", "user.name", "autose-bot"])
        gh.run(["git", "config", "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com"])
        gh.run(["git", "fetch", "origin", "master"])
        exists = gh.run(["git", "ls-remote", "--heads", "origin",
                         self.branch])
        if exists:
            gh.run(["git", "fetch", "origin", self.branch])
            gh.run(["git", "checkout", "-B", self.branch,
                    f"origin/{self.branch}"])
        else:
            gh.run(["git", "checkout", "-B", self.branch, "origin/master"])
        if (self.dir / "state.json").exists():
            self.state = json.loads(self.read("state.json"))
        self.state.update({"issue": self.n, "round": self.round,
                           "branch": self.branch, "run": gh.run_url(),
                           "models": MODELS})
        self.state.setdefault("attempts", {})
        self.state.setdefault("design_reentries", 0)
        self.issue = gh.issue(self.n)

        # Resume: on a restart, continue from the first stage not passed.
        start = self.start
        if start == "auto":
            start = self.state.get("next", "guard")
            if self.state.pop("resume_at", None):
                pass   # stopped only by the Groq quota: continue (ADR-016)
            elif self.state.get("status") in ("released", "stopped"):
                start = "guard"   # a fresh trigger after a finished run
        if exists:
            self.sync_with_master(fresh=(start == "guard"))
        self.base = gh.run(["git", "merge-base", "origin/master", "HEAD"])
        if start in ("guard", "spec", "design") and                 self.state.get("history"):
            # A fresh start must not build on an earlier run's code (run 12
            # left a half-written test file on the branch). A restart at
            # spec or design also gets a clean tree and fresh counters, or
            # an earlier run's used-up attempts stop the builder at once
            # (ADR-023). The spec in .autose/ is kept. --no-overlay
            # also deletes tracked files that master does not have; plain
            # checkout only overwrites (found reproducing run 13).
            for d in ("tinydb", "tests", "docs"):
                gh.run(["git", "checkout", "--no-overlay", "origin/master",
                        "--", d], check=False)
                gh.run(["git", "clean", "-fdq", "--", d], check=False)
            left = gh.run(["git", "diff", "--name-only", "origin/master",
                           "--", "tinydb", "tests", "docs"], check=False)
            if left:
                raise Stop("setup", "could not reset the code to master: "
                           + left[:300])
            self.state["attempts"] = {}
            self.state["design_reentries"] = 0
        self.state["status"] = "running"
        self.event("setup", "ok", f"start={start} base={self.base[:7]}")
        gh.comment_issue(self.n, f"**AutoSE** round {self.round} started "
                         f"at stage `{start}`. Follow it here: "
                         f"{gh.run_url()}")
        return start

    def sync_with_master(self, fresh: bool) -> None:
        """ADR-017: merge master into an existing issue branch, so the agents
        see the current tinydb/, tests/, ARCHITECTURE.md and skill, and the
        review job (which runs from the PR head) runs the current autose/.
        On a fresh start master wins any conflict, since the code is reset
        to master anyway. On a resume a conflict stops the run instead."""
        cmd = ["git", "merge", "--no-edit", "-m",
               f"AutoSE: sync {self.branch} with master"]
        if fresh:
            cmd[2:2] = ["-X", "theirs"]
        try:
            gh.run(cmd + ["origin/master"])
        except RuntimeError as e:
            gh.run(["git", "merge", "--abort"], check=False)
            raise Stop("setup", f"{self.branch} could not be merged with "
                       f"master ({e}). Delete the branch to start over.")
        log(f"setup: {self.branch} synced with master")

    def baseline(self) -> None:
        """Count passing tests on master, so tests cannot silently vanish."""
        tmp = ROOT.parent / "autose-baseline"
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        gh.run(["git", "worktree", "add", "--detach", str(tmp),
                "origin/master"])
        try:
            code, out = run_pytest(tmp)
        finally:
            gh.run(["git", "worktree", "remove", "--force", str(tmp)],
                   check=False)
        self.baseline_passed = checks.pytest_counts(out).get("passed", 0)
        self.state["baseline_passed"] = self.baseline_passed
        log(f"baseline: {self.baseline_passed} passed on master")

    # ---- stage 0: injection screen (ADR-011) ------------------------------
    def stage_guard(self) -> str:
        text = f"{self.issue['title']}\n\n{self.issue['body'] or ''}"
        chunks = [text[i:i + 1500] for i in range(0, len(text), 1500)] or [""]
        scores = []
        try:
            for c in chunks[:8]:
                msg = chat("guard", MODELS["guard"],
                           [{"role": "user", "content": c}], max_tokens=20,
                           temperature=0)
                raw = (msg.content or "").strip()
                try:
                    scores.append(float(raw))
                except ValueError:
                    scores.append(1.0 if re.search(
                        r"MALICIOUS|JAILBREAK|INJECTION", raw, re.I) else 0.0)
        except LLMError as e:
            # Fail open with a record: other defences still apply (ADR-009).
            self.state["guard"] = {"error": str(e)[:200]}
            self.event("guard", "unavailable", str(e))
            return "spec"
        score = max(scores)
        self.state["guard"] = {"max_score": score, "chunks": len(scores)}
        if score > 0.5:
            raise Stop("guard", f"issue text classified as a likely prompt "
                       f"injection (score {score:.2f}); no agent was run")
        self.event("guard", "pass", f"max score {score:.3f}")
        return "spec"

    # ---- stage 1: requirements -----------------------------------------------
    def judge(self, acs: dict) -> list:
        listing = "\n\n".join(f"### {k}\n{v}" for k, v in acs.items())
        msg = chat("judge", MODELS["judge"], [
            {"role": "system", "content": prompt("judge.md")},
            {"role": "user", "content": listing}],
            max_tokens=2000, temperature=0, budget=BUDGET["judge"])
        try:
            verdicts = extract_json(msg.content or "")
        except ValueError as e:
            return [f"judge reply unreadable: {e}"]
        problems = []
        for ac in acs:
            v = verdicts.get(ac, {})
            if not v.get("testable", False):
                problems.append(f"{ac} not testable: "
                                f"{v.get('reason', 'no verdict given')}")
        self.state["judge"] = verdicts
        return problems

    def stage_spec(self) -> str:
        skill = SKILL_TEXT
        ws = Workspace(ROOT, deny_read=(".autose", "autose", ".github"))
        tools, impl = toolset(ws, ["list_dir", "read_file", "grep"])
        msgs = [{"role": "system",
                 "content": prompt("planner_spec.md", skill=skill)},
                {"role": "user", "content": untrusted(self.issue) +
                 "\n\nWrite spec.md for this issue."}]
        for attempt in range(1, MAX_SPEC_REDOS + 2):
            out = run_agent(role="planner", model=MODELS["planner"],
                            messages=msgs, tools=tools, impl=impl,
                            finish_schema=CONTENT_SCHEMA, max_turns=20,
                            budget=BUDGET["planner"])
            spec = strip_think(out.get("content", ""))
            self.write("spec.md", spec)
            acs, problems = checks.check_spec(spec)
            if problems == ["STOP"]:
                raise Stop("spec", "the planner judged the issue not "
                           "implementable as one change (see spec.md)")
            if not problems:
                problems = self.judge(acs)
            if not problems:
                self.acs = acs
                self.event("spec", "pass", f"{len(acs)} ACs, attempt "
                           f"{attempt}")
                return "design"
            self.event("spec", "fail", "; ".join(problems))
            msgs.append({"role": "user", "content":
                         "The spec failed its check:\n- " +
                         "\n- ".join(problems) +
                         "\nFix every problem and call finish again with "
                         "the full corrected spec."})
        raise Stop("spec", "acceptance criteria still not testable after "
                   f"{MAX_SPEC_REDOS + 1} attempts: " + "; ".join(problems))

    # ---- stage 2: design ----------------------------------------------------
    def stage_design(self) -> str:
        # Only §4 (invariants) and §5 (where to change what) fit the 8k TPM
        # budget; the planner can read the rest with read_file (ADR-013).
        full = ARCHITECTURE_TEXT
        m = re.search(r"^## 4\..*?(?=^## 6\.)", full, flags=re.M | re.S)
        arch = (m.group(0) if m else full[:5000]) + \
            "\n(Full document: read_file('ARCHITECTURE.md').)"
        ws = Workspace(ROOT, deny_read=(".autose", "autose", ".github"))
        tools, impl = toolset(ws, ["list_dir", "read_file", "grep"])
        user = "SPEC:\n" + self.read("spec.md")
        if self.feedback:
            user += "\n\nFEEDBACK FROM AN EARLIER ATTEMPT (must address):\n" \
                + self.feedback
        msgs = [{"role": "system",
                 "content": prompt("planner_design.md", architecture=arch)},
                {"role": "user", "content": user + "\n\nWrite design.md."}]
        for attempt in range(1, MAX_DESIGN_REDOS + 2):
            out = run_agent(role="planner", model=MODELS["planner"],
                            messages=msgs, tools=tools, impl=impl,
                            finish_schema=CONTENT_SCHEMA, max_turns=20,
                            budget=BUDGET["planner"])
            design = strip_think(out.get("content", ""))
            self.write("design.md", design)
            problems = checks.check_design(design, ROOT)
            if not problems:
                rows = checks.parse_design_rows(design)
                self.event("design", "pass", f"{len(rows)} rows, attempt "
                           f"{attempt}")
                self.builder_msgs = []     # new design -> fresh builder
                return "implement"
            self.event("design", "fail", "; ".join(problems))
            msgs.append({"role": "user", "content":
                         "The design failed its check:\n- " +
                         "\n- ".join(problems) + "\nFix it and call finish "
                         "again with the full corrected design."})
        raise Stop("design", "design names files or functions that do not "
                   "exist: " + "; ".join(problems))

    # ---- stages 3+4: implement <-> test ----------------------------------------
    def verify(self) -> tuple[bool, str, dict]:
        files = checks.changed_files(ROOT, self.base)
        report = {"files": files}
        bad = checks.forbidden_changes(files)
        if bad:
            return False, f"you changed forbidden files: {bad}. Revert " \
                "them; only tinydb/, tests/ and docs/ may change.", report
        if not any(f.startswith("tinydb/") for f in files):
            return False, "no change under tinydb/ yet; implement the " \
                "design.", report
        ok, out = checks.check_build(ROOT)
        report["build"] = ok
        if not ok:
            return False, "BUILD FAILED (stage 3 check):\n" + clip(out), \
                report
        code, out = run_pytest(ROOT)
        counts = checks.pytest_counts(out)
        report.update(pytest_exit=code, counts=counts,
                      pytest_tail=clip(out, 2500, tail=True))
        if code != 0:
            # ADR-024: name each failing test with its line and first error,
            # not the raw tail of the output (run 22).
            tally = ", ".join(f"{v} {k}" for k, v in counts.items())
            digest = checks.failure_digest(out)
            if digest:
                return False, (f"TESTS FAILED (stage 4 check): {tally}. "
                               "Each failing test, where it failed and its "
                               "first error lines:\n" + digest), report
            return False, f"TESTS FAILED (stage 4 check): {tally}\n" + \
                clip(out, tail=True), report
        if counts.get("passed", 0) < self.baseline_passed:
            return False, (f"only {counts.get('passed', 0)} tests pass but "
                           f"master has {self.baseline_passed}: existing "
                           "tests must not be removed or skipped."), report
        acmap = checks.ac_test_map(self.acs, ROOT, files)
        report["ac_map"] = acmap
        missing = [ac for ac, tests in acmap.items() if not tests]
        if missing:
            return False, (f"no new test mentions {missing}. Add one test "
                           "per AC whose docstring starts with the AC id."
                           ), report
        return True, "all checks pass", report

    def stage_implement(self) -> str:
        if not self.acs:
            self.acs, _ = checks.check_spec(self.read("spec.md"))
        if BUILDER_MODE == "patch":
            return self.stage_implement_patch()
        ws = Workspace(ROOT, deny_read=(".autose", "autose", ".github"))
        tools, impl = toolset(ws, ["list_dir", "read_file", "grep",
                                   "replace_lines", "edit_file", "write_file",
                                   "run_tests"])
        if not self.builder_msgs:
            user = ("SPEC:\n" + self.read("spec.md") + "\n\nDESIGN:\n" +
                    self.read("design.md"))
            if self.feedback:
                user += "\n\nREVIEW FINDINGS / EARLIER FAILURES (fix these):"\
                        "\n" + self.feedback
            self.builder_msgs = [
                {"role": "system", "content": prompt("builder.md")},
                {"role": "user", "content": user}]
        key = f"r{self.round}"
        attempts_log = []
        msg = "no implementation attempt left in this round"
        while self.state["attempts"].get(key, 0) < MAX_IMPLEMENT_ATTEMPTS:
            self.state["attempts"][key] = self.state["attempts"].get(key,
                                                                     0) + 1
            n = self.state["attempts"][key]
            out = run_agent(role="builder", model=MODELS["builder"],
                            messages=self.builder_msgs, tools=tools,
                            impl=impl, finish_schema=SUMMARY_SCHEMA,
                            max_turns=40, budget=BUDGET["builder"],
                            max_chars=16000)
            ok, msg, report = self.verify()
            attempts_log.append((n, ok, msg.splitlines()[0][:150]))
            self.write_test_report(report, attempts_log,
                                   out.get("summary", ""))
            self.write_patch()
            if ok:
                self.event("implement+test", "pass", f"attempt {n}")
                return "release"
            self.event("implement+test", "fail", f"attempt {n}: {msg}")
            self.builder_msgs.append({"role": "user", "content":
                                      f"Orchestrator check after attempt {n}"
                                      f" FAILED:\n{msg}\nFix it, run the "
                                      "full test suite, then call finish."})
        return self.after_failed_attempts(msg)

    def stage_implement_patch(self) -> str:
        """ADR-016: the orchestrator localizes, the model answers once with
        whole definitions and a test file, the checks validate."""
        rows = checks.parse_design_rows(self.read("design.md"))
        test_path = f"tests/test_autose_issue_{self.n}.py"
        spec = self.read("spec.md")
        m = re.search(r"^## Acceptance criteria.*?(?=^## |\Z)", spec,
                      flags=re.M | re.S)
        acs_text = m.group(0).strip() if m else clip(spec, 4000)
        design = self.read("design.md")
        m = re.search(r"^## Approach.*?(?=^## |\Z)", design, flags=re.M | re.S)
        approach = clip(m.group(0).strip() if m else design, 1500)
        system = prompt("builder_patch.md", test_path=test_path)
        # ADR-024: the builder also gets ARCHITECTURE.md §4 (invariants), so
        # facts such as which dicts hold str or int doc IDs reach the agent
        # that writes the code, not only the planner.
        m = re.search(r"^## 4\..*?(?=^## 5\.)", ARCHITECTURE_TEXT,
                      flags=re.M | re.S)
        invariants = m.group(0).strip() if m else ""
        failure = ("REVIEW FINDINGS / EARLIER FAILURES (fix these):\n" +
                   clip(self.feedback, 4000)) if self.feedback else ""
        key = f"r{self.round}"
        attempts_log, msg = [], "no implementation attempt left in this round"
        while self.state["attempts"].get(key, 0) < MAX_IMPLEMENT_ATTEMPTS:
            # Counted only once the model answers, so a quota stop does
            # not use up an attempt.
            n = self.state["attempts"].get(key, 0) + 1
            text = ""
            # ADR-024: sized for Gemini (2M TPM); the second size is the
            # fallback after a 413 (e.g. on a Groq model, ADR-013).
            for code_chars, test_chars, fail_chars in ((20000, 6000, 5000),
                                                       (9000, 3000, 2500)):
                blocks = patcher.localize(ROOT, rows, max_chars=code_chars)
                if not blocks:
                    raise Stop("implement", "the design names no existing "
                               "definition or class under tinydb/ to change")
                user = (acs_text + "\n\n## Design\n" + approach +
                        ("\n\n## ARCHITECTURE.md " + invariants
                         if invariants else "") +
                        "\n\n## Code to change (current)\n\n" +
                        patcher.render_blocks(blocks))
                tp = ROOT / test_path
                if tp.exists():
                    user += (f"\n\n## Current {test_path}\n```python\n" +
                             clip(tp.read_text("utf-8"), test_chars) +
                             "\n```")
                if failure:
                    # The instruction and the first failing tests come first,
                    # so keep the head (ADR-024).
                    user += "\n\n" + clip(failure, fail_chars)
                log(f"builder: attempt {n}, patch request "
                    f"{len(system) + len(user)} chars, blocks "
                    f"{[b['name'] for b in blocks]}")
                try:
                    reply = chat("builder", MODELS["builder"], [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}],
                        max_tokens=BUILDER_MAX_TOKENS,
                        budget=BUDGET["builder"])
                    text = strip_think(reply.content or "")
                    break
                except RequestTooLarge as e:
                    log(f"builder: {e}; shrinking the request")
            self.state["attempts"][key] = n
            summary = ""
            try:
                answer = patcher.parse_answer(text)
                done = patcher.apply_answer(ROOT, answer, test_path)
                summary = answer["summary"]
                log("builder: " + "; ".join(done))
                ok, msg, report = self.verify()
            except patcher.PatchError as e:
                ok, report = False, {"files": checks.changed_files(
                    ROOT, self.base)}
                msg = (f"YOUR ANSWER COULD NOT BE APPLIED: {e}. Answer again "
                       "in exactly the required format.")
                if LAST_FINISH.get("builder") == "length":
                    msg = ("YOUR ANSWER WAS CUT OFF at the output limit "
                           f"({BUILDER_MAX_TOKENS} tokens) before it was "
                           f"complete ({e}). Answer again, shorter: replace "
                           "only the definitions that must change, keep "
                           "comments brief, and one short test per AC.")
            attempts_log.append((n, ok, msg.splitlines()[0][:150]))
            self.write_test_report(report, attempts_log, summary)
            self.write_patch()
            if ok:
                self.event("implement+test", "pass", f"attempt {n}")
                return "release"
            self.event("implement+test", "fail", f"attempt {n}: {msg}")
            failure = (f"## Attempt {n} FAILED the orchestrator's check\n"
                       "Fix the cause in the code (do not weaken the tests) "
                       f"and answer again in the same format.\n\n{msg}")
        return self.after_failed_attempts(msg)

    def after_failed_attempts(self, msg: str) -> str:
        key = f"r{self.round}"
        # Tests keep failing: maybe the design is wrong (ADR-002).
        if self.state["design_reentries"] < MAX_DESIGN_REENTRIES:
            self.state["design_reentries"] += 1
            self.feedback = ("The previous design was implemented "
                             f"{MAX_IMPLEMENT_ATTEMPTS} times and still failed"
                             ":\n" + clip(msg, 3500))
            self.state["attempts"][key] = 0
            gh.run(["git", "checkout", self.base, "--", "tinydb", "tests"],
                   check=False)
            gh.run(["git", "clean", "-fdq", "--", "tinydb", "tests"],
                   check=False)
            self.event("implement+test", "back-to-design",
                       "3 attempts failed")
            return "design"
        raise Stop("test", f"tests still failing after "
                   f"{MAX_IMPLEMENT_ATTEMPTS} attempts and a redesign: "
                   + msg[:500])

    def write_patch(self) -> None:
        diff = gh.run(["git", "diff", self.base, "--", ".",
                       ":(exclude).autose"], check=False)
        untracked = gh.run(["git", "ls-files", "--others",
                            "--exclude-standard", "--", ".",
                            ":(exclude).autose"], check=False)
        for f in untracked.split():
            diff += "\n" + gh.run(["git", "diff", "--no-index", "/dev/null",
                                   f], check=False)
        self.write("diff.patch", diff + "\n")

    def write_test_report(self, report: dict, attempts: list,
                          summary: str) -> None:
        lines = [f"# Test report: issue #{self.n} (round {self.round})", "",
                 f"**Baseline on master:** {self.baseline_passed} passed",
                 f"**Result:** {report.get('counts', {})} "
                 f"(exit {report.get('pytest_exit', 'n/a')})",
                 f"**Build (compileall + import):** "
                 f"{'pass' if report.get('build') else 'fail / not run'}",
                 "", "## Acceptance criteria → tests", "",
                 "| AC | Tests |", "|---|---|"]
        for ac, tests in report.get("ac_map", {}).items():
            lines.append(f"| {ac} | {', '.join(tests) or '**MISSING**'} |")
        lines += ["", "## Attempts", "", "| # | Pass | Check message |",
                  "|---|---|---|"]
        for n, ok, m in attempts:
            lines.append(f"| {n} | {'yes' if ok else 'no'} | "
                         f"{m.replace('|', '/')} |")
        lines += ["", "## Files changed", ""] + \
            [f"- `{f}`" for f in report.get("files", [])]
        lines += ["", "## Builder's summary (unverified claim)", "", summary,
                  "", "## pytest output (tail)", "", "```",
                  report.get("pytest_tail", ""), "```"]
        self.write("test_report.md", "\n".join(lines))

    # ---- stage 5: release (no LLM) -----------------------------------------------
    def commit_and_push(self, message: str) -> None:
        self.save()
        gh.run(["git", "add", "-A", "--", "tinydb", "tests", "docs",
                ".autose"], check=False)
        if gh.run(["git", "status", "--porcelain"]):
            gh.run(["git", "commit", "-m", message])
        gh.run(["git", "push", "origin", f"HEAD:refs/heads/{self.branch}"])

    def stage_release(self) -> str:
        self.write("pr.md", self.pr_body(ci_url="(pending)"))
        self.commit_and_push(f"AutoSE: issue #{self.n} round {self.round}")
        sha = gh.run(["git", "rev-parse", "HEAD"])
        prs = gh.gh_json(["pr", "list", "--repo", gh.repo(), "--head",
                          self.branch, "--state", "open", "--json",
                          "number,url"])
        if prs:
            pr = prs[0]
        else:
            url = gh.run(["gh", "pr", "create", "--repo", gh.repo(),
                          "--base", "master", "--head", self.branch,
                          "--title", f"AutoSE: {self.issue['title'][:80]} "
                          f"(#{self.n})", "--body-file",
                          str(self.dir / "pr.md")])
            pr = {"number": int(url.rstrip("/").split("/")[-1]), "url": url}
        self.state["pr"] = pr
        self.event("release", "pr-open", pr["url"])

        # CI: PR events from GITHUB_TOKEN do not trigger workflows, so start
        # it with workflow_dispatch and watch it (ADR-012).
        ci_ok, ci_url = self.run_ci(sha)
        self.state["ci"] = {"ok": ci_ok, "url": ci_url, "sha": sha}
        self.write("pr.md", self.pr_body(ci_url=ci_url, ci_ok=ci_ok))
        gh.run(["gh", "pr", "edit", str(pr["number"]), "--repo", gh.repo(),
                "--body-file", str(self.dir / "pr.md")], check=False)
        if not ci_ok:
            raise Stop("release", f"CI failed on {sha[:7]}: {ci_url}")
        # No commit after CI: the PR head must stay the commit CI tested.
        # The final state.json is uploaded as an Actions artifact instead.
        self.state["next"] = "review"
        self.state["head_sha"] = sha
        self.event("release", "pass", f"PR #{pr['number']} CI green")
        gh.set_output(status="released", pr=pr["number"], sha=sha,
                      issue=self.n, round=self.round)
        return "done"

    def run_ci(self, sha: str) -> tuple[bool, str]:
        gh.run(["gh", "workflow", "run", "ci-workflow.yml", "--repo",
                gh.repo(), "--ref", self.branch])
        run_id = None
        for _ in range(30):
            time.sleep(6)
            runs = gh.gh_json(["run", "list", "--repo", gh.repo(),
                               "--workflow", "ci-workflow.yml", "--branch",
                               self.branch, "--event", "workflow_dispatch",
                               "--limit", "5", "--json",
                               "databaseId,headSha,url"])
            match = [r for r in runs if r["headSha"] == sha]
            if match:
                run_id, url = match[0]["databaseId"], match[0]["url"]
                break
        if not run_id:
            return False, "CI run did not start within 3 minutes"
        try:
            r = subprocess.run(["gh", "run", "watch", str(run_id), "--repo",
                                gh.repo(), "--exit-status", "--interval",
                                "15"], capture_output=True, text=True,
                               timeout=900)
        except subprocess.TimeoutExpired:
            return False, url + " (timed out after 15 min)"
        return r.returncode == 0, url

    def pr_body(self, ci_url: str, ci_ok: bool | None = None) -> str:
        spec = self.read("spec.md")
        m = re.search(r"\*\*Summary:\*\*\s*(.+)", spec)
        ci = {None: "pending", True: "passed", False: "FAILED"}[ci_ok]
        hist = "\n".join(f"| r{h['round']} | {h['stage']} | {h['result']} |"
                         for h in self.state.get("history", [])
                         if h["stage"] != "setup")
        return f"""## AutoSE pull request for #{self.n}

Closes #{self.n}

**Summary:** {m.group(1).strip() if m else '(see spec)'}

| Artifact | |
|---|---|
| Spec (stage 1) | `.autose/issue-{self.n}/spec.md` |
| Design (stage 2) | `.autose/issue-{self.n}/design.md` |
| Patch (stage 3) | `.autose/issue-{self.n}/diff.patch` |
| Test report (stage 4) | `.autose/issue-{self.n}/test_report.md` |
| CI (stage 5) | {ci}: {ci_url} |
| Run | {gh.run_url()} |

### Stage history
| Round | Stage | Result |
|---|---|---|
{hist}

An independent reviewer agent (different model, read-only, no access to the spec or design) will post its review below. **This PR is never merged automatically. A maintainer decides.**

The `.autose/` folder holds the audit trail and can be deleted before merging.
"""

    def load_review_feedback(self) -> None:
        """Round > 1: the previous review is a PR comment (see post.py)."""
        prs = gh.gh_json(["pr", "list", "--repo", gh.repo(), "--head",
                          self.branch, "--state", "open", "--json",
                          "number"])
        if not prs:
            raise Stop("setup", "round > 1 but no open PR for "
                       f"{self.branch}")
        marker = f"<!-- autose-review round={self.round - 1} -->"
        comments = gh.gh_json(["api", f"repos/{gh.repo()}/issues/"
                               f"{prs[0]['number']}/comments",
                               "--paginate"])
        bodies = [c["body"] for c in comments if marker in c["body"]]
        if not bodies:
            raise Stop("setup", f"review for round {self.round - 1} not "
                       "found on the PR")
        self.write(f"review-r{self.round - 1}.md", bodies[-1])
        self.feedback = bodies[-1][:6000]
        self.event("setup", "loaded-review", f"round {self.round - 1}")

    # ---- driver ------------------------------------------------------------
    def main(self) -> int:
        stages = {"guard": self.stage_guard, "spec": self.stage_spec,
                  "design": self.stage_design,
                  "implement": self.stage_implement,
                  "release": self.stage_release}
        try:
            stage = self.setup()
            if self.round > 1:
                self.load_review_feedback()
            if stage not in ("guard", "spec"):
                self.acs, _ = checks.check_spec(self.read("spec.md"))
            self.baseline()
            while stage != "done":
                self.state["next"] = stage
                self.save()
                stage = stages[stage]()
            self.state["status"] = "released"
            self.save()
            return 0
        except (Stop, AgentStopped, BudgetExceeded, LLMError) as e:
            st = e.stage if isinstance(e, Stop) else self.state.get("next")
            reason = e.reason if isinstance(e, Stop) else \
                f"{type(e).__name__}: {e}"
            if isinstance(e, QuotaExhausted):
                # Nothing failed a check: the next trigger resumes here
                # instead of paying for spec and design again (ADR-016).
                self.state["resume_at"] = st
                reason += ("\n\nThe free-tier quota refills at about 8k "
                           "tokens per hour per model. Comment `/autose` "
                           "later to resume at this stage.")
            return self.stop(st, reason)

    def stop(self, stage: str, reason: str) -> int:
        artifact = {"guard": "state.json", "spec": "spec.md",
                    "design": "design.md", "implement": "test_report.md",
                    "test": "test_report.md",
                    "release": "pr.md"}.get(stage, "test_report.md")
        if artifact.endswith(".md"):
            self.write(artifact, self.read(artifact) +
                       f"\n\n## STOPPED at stage `{stage}`\n\n{reason}\n")
        self.state.update(status="stopped", stopped_at=stage,
                          stop_reason=reason[:1000])
        self.event(stage, "STOPPED", reason)
        try:
            if stage != "guard":
                self.commit_and_push(f"AutoSE: stopped at {stage} for "
                                     f"#{self.n}")
        except RuntimeError as e:
            log(f"push after stop failed: {e}")
        gh.comment_issue(self.n, f"**AutoSE stopped** at stage `{stage}` "
                         f"(round {self.round}).\n\n> {reason[:1500]}\n\n"
                         f"Artifacts: branch `{self.branch}`, run "
                         f"{gh.run_url()}")
        gh.set_output(status="stopped", issue=self.n, round=self.round)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--start", default="auto",
                    choices=["auto", "guard", "spec", "design", "implement",
                             "release"])
    a = ap.parse_args()
    gh.summary("| time | round | stage | result | detail |\n|---|---|---|---|"
               "---|")
    run = Run(a.issue, a.round, a.start)
    code = run.main()
    gh.summary("\n**Tokens:** `" + json.dumps(USAGE) + "`")
    return code


if __name__ == "__main__":
    sys.exit(main())
