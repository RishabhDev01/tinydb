"""Decide whether this event may start AutoSE (ADR-010).

Reads the event payload from GITHUB_EVENT_PATH. Untrusted text such as
comment bodies is only inspected here, in Python. It is never interpolated
into a shell command.
"""
import json
import os
import re
import sys

from . import gh

TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}


def decide(event_name: str, ev: dict) -> dict:
    no = lambda why: {"run": "false", "reason": why}  # noqa: E731
    sender = ev.get("sender", {})
    if sender.get("type") == "Bot":
        return no("event sent by a bot")

    if event_name == "workflow_dispatch":
        inp = ev.get("inputs", {})
        return {"run": "true", "issue": int(inp["issue"]),
                "round": int(inp.get("round") or 1),
                "start": inp.get("start") or "auto",
                "reason": "workflow_dispatch (requires write access)"}

    issue = ev.get("issue", {})
    if event_name == "issues":
        if ev.get("label", {}).get("name") != "autose":
            return no("label is not 'autose'")
        if issue.get("pull_request"):
            return no("labels on PRs are ignored")
        # Adding a label already requires triage access to the repo.
        return {"run": "true", "issue": issue["number"], "round": 1,
                "start": "auto", "reason": f"labeled by {sender.get('login')}"}

    if event_name == "issue_comment":
        c = ev.get("comment", {})
        body = (c.get("body") or "").strip()
        if not body.startswith("/autose"):
            return no("comment is not an /autose command")
        # ADR-026: review round 2 is started by a person with
        # `/autose round 2 <design|implement>`, which the post job suggests.
        # The bot no longer dispatches it (run 28 was rejected as a bot
        # event), so every run stays human-triggered.
        cmd = re.fullmatch(r"/autose(?:\s+round\s+([12])"
                           r"(?:\s+(design|implement))?)?",
                           body.splitlines()[0].strip())
        if not cmd:
            return no("unrecognised /autose command; use `/autose` or "
                      "`/autose round 2 <design|implement>`")
        round_no = int(cmd.group(1) or 1)
        start = cmd.group(2) or ("implement" if round_no > 1 else "auto")
        if c.get("author_association") not in TRUSTED:
            return no(f"commenter association "
                      f"{c.get('author_association')} is not trusted")
        number = issue["number"]
        if issue.get("pull_request"):
            head = gh.gh_json(["pr", "view", str(number), "--repo",
                               gh.repo(), "--json", "headRefName"])
            m = re.fullmatch(r"autose/issue-(\d+)", head["headRefName"])
            if not m:
                return no("/autose on a PR that AutoSE did not open")
            number = int(m.group(1))
        return {"run": "true", "issue": number, "round": round_no,
                "start": start,
                "reason": f"/autose by {c.get('user', {}).get('login')}"
                + (f" (round {round_no}, {start})" if round_no > 1 else "")}

    return no(f"unsupported event {event_name}")


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        ev = json.load(f)
    d = decide(os.environ["GITHUB_EVENT_NAME"], ev)
    gh.set_output(**d)
    gh.summary(f"**Gate:** run={d['run']} ({d['reason']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
