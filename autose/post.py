"""Publish the review and route the verdict. No LLM runs here (ADR-002,
ADR-008).

    approve                       -> comment, hand to human
    changes and round < MAX       -> comment with the command for round 2
    changes and round == MAX      -> comment, hand to human

ADR-026: round 2 is no longer dispatched by the bot. The gate rejects
bot events (ADR-010), so run 28 never ran; and every run is started by a
person. The comment gives the exact `/autose round 2 <stage>` to type.
"""
import argparse
import json
import sys
from pathlib import Path

from . import gh

MAX_REVIEW_ROUNDS = 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--dir", default="review-out")
    a = ap.parse_args()
    d = Path(a.dir)

    if not (d / "verdict.json").exists():
        err = (d / "error.txt").read_text("utf-8") if (d / "error.txt") \
            .exists() else "no verdict produced"
        gh.run(["gh", "pr", "comment", str(a.pr), "--repo", gh.repo(),
                "--body", f"**AutoSE review round {a.round} failed:** "
                f"{err[:1500]}\n\nHanding over to a human. Run: "
                f"{gh.run_url()}"])
        return 1

    v = json.loads((d / "verdict.json").read_text("utf-8"))
    gh.run(["gh", "pr", "comment", str(a.pr), "--repo", gh.repo(),
            "--body-file", str(d / "review.md")])

    if v["verdict"] == "changes" and a.round < MAX_REVIEW_ROUNDS:
        nxt = a.round + 1
        gh.run(["gh", "pr", "comment", str(a.pr), "--repo", gh.repo(),
                "--body", f"**AutoSE:** the reviewer requested changes "
                f"(route back to `{v['target']}`). A maintainer decides "
                f"whether to continue. To start review round {nxt} of "
                f"{MAX_REVIEW_ROUNDS}, comment:\n\n"
                f"```\n/autose round {nxt} {v['target']}\n```\n\n"
                "Otherwise close this PR. AutoSE never merges."])
        gh.set_output(next="await-round-" + str(nxt))
        return 0

    why = "the reviewer approved" if v["verdict"] == "approve" else \
        f"{MAX_REVIEW_ROUNDS} review rounds are used up"
    gh.run(["gh", "pr", "comment", str(a.pr), "--repo", gh.repo(),
            "--body", f"**AutoSE finished:** {why}. **Ready for a human "
            "decision**: merge or close. AutoSE never merges."])
    gh.set_output(next="human")
    return 0


if __name__ == "__main__":
    sys.exit(main())
