"""Experiment E2: does the builder need the full hand-off? (ADR-003, ADR-028)

Runs ONLY stages 3+4 (implement <-> test) for one issue, with the spec and
design frozen from that issue's AutoSE branch, and HANDOFF=full|summary
deciding what the builder is told. Nothing else changes: same code shown,
same checks, same 3 attempts, and no redesign (so the design stays fixed).

The result is pushed to its own branch, e2/<handoff>/issue-<n>-r<rep>, so
the approved autose/issue-<n> branches and their PRs are never touched.
No issue or PR comments are made. The hidden tests are run afterwards,
outside the fork.

    HANDOFF=summary python -m autose.experiment --issue 4 --rep 1
"""
import argparse
import json
import sys

from . import checks, gh
from .agent import AgentStopped
from .llm import USAGE, BudgetExceeded, LLMError
from .orchestrator import (HANDOFF, MAX_DESIGN_REENTRIES, Run, Stop,
                           log, now)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--rep", type=int, default=1)
    a = ap.parse_args()
    if HANDOFF not in ("full", "summary"):
        print(f"unknown HANDOFF {HANDOFF!r}", file=sys.stderr)
        return 2

    source = f"autose/issue-{a.issue}"
    branch = f"e2/{HANDOFF}/issue-{a.issue}-r{a.rep}"
    frozen = f".autose/issue-{a.issue}"
    gh.run(["git", "config", "user.name", "autose-bot"])
    gh.run(["git", "config", "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com"])
    gh.run(["git", "fetch", "origin", "master", source])
    gh.run(["git", "checkout", "-B", branch, "origin/master"])
    # The frozen inputs: the spec and design that AutoSE produced earlier.
    gh.run(["git", "checkout", f"origin/{source}", "--",
            f"{frozen}/spec.md", f"{frozen}/design.md"])

    run = Run(a.issue, 1, "implement")
    run.branch = branch
    run.base = gh.run(["git", "merge-base", "origin/master", "HEAD"])
    # design_reentries at the maximum: after 3 failed attempts the run
    # stops instead of redesigning, so both arms share one design.
    run.state = {"attempts": {}, "design_reentries": MAX_DESIGN_REENTRIES,
                 "experiment": {"name": "E2", "handoff": HANDOFF,
                                "rep": a.rep, "source": source}}
    run.acs, _ = checks.check_spec(run.read("spec.md"))
    run.baseline()

    result = {"issue": a.issue, "handoff": HANDOFF, "rep": a.rep,
              "started": now()}
    try:
        run.stage_implement_patch()
        result.update(outcome="pass", reason="all checks pass")
    except Stop as e:
        result.update(outcome="fail", reason=e.reason[:600])
    except (AgentStopped, BudgetExceeded, LLMError) as e:
        result.update(outcome="error", reason=f"{type(e).__name__}: {e}"[:600])
    result.update(attempts=run.state["attempts"].get("r1", 0),
                  tokens=USAGE, finished=now())
    run.write("e2.json", json.dumps(result, indent=2))
    run.save()

    gh.run(["git", "add", "-A", "tinydb", "tests", frozen])
    gh.run(["git", "commit", "-q", "--allow-empty", "-m",
            f"E2 {HANDOFF} issue {a.issue} rep {a.rep}: "
            f"{result['outcome']}"])
    gh.run(["git", "push", "-f", "origin", f"HEAD:refs/heads/{branch}"])
    log(f"E2: {json.dumps({k: result[k] for k in ('outcome', 'attempts')})}")
    gh.summary(f"**E2** issue {a.issue}, `{HANDOFF}`, rep {a.rep}: "
               f"**{result['outcome']}** after {result['attempts']} "
               f"attempt(s); tokens `{json.dumps(USAGE)}`; branch "
               f"`{branch}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
