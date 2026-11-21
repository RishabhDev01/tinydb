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
        if not (c.get("body") or "").strip().startswith("/autose"):
            return no("comment is not an /autose command")
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
        return {"run": "true", "issue": number, "round": 1, "start": "auto",
                "reason": f"/autose by {c.get('user', {}).get('login')}"}

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
