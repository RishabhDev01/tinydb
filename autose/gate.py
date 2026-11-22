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

    if event_name == "schedule":
        return pick_paused()

    return no(f"unsupported event {event_name}")


MIN_PAUSE_MIN = 60   # let the quota refill before trying again


def paused_issues() -> list:
    """[(paused_at, issue, round)] for autose/issue-N branches whose state
    says they paused on the Groq quota (ADR-018). Only issues a maintainer
    already started have such a branch, so no new work is ever begun."""
    names = gh.run(["gh", "api", f"repos/{gh.repo()}/branches",
                    "--paginate", "-q", ".[].name"]).split()
    out = []
    for name in names:
        m = re.fullmatch(r"autose/issue-(\d+)", name)
        if not m:
            continue
        n = int(m.group(1))
        try:
            st = json.loads(gh.run([
                "gh", "api", "-H", "Accept: application/vnd.github.raw",
                f"repos/{gh.repo()}/contents/.autose/issue-{n}/state.json"
                f"?ref={name}"]))
        except (RuntimeError, ValueError):
            continue
        if st.get("status") == "paused" or (
                st.get("status") == "stopped" and st.get("resume_at")):
            out.append((st.get("paused_at") or st.get("updated", ""), n,
                        int(st.get("round") or 1)))
    return sorted(out)


def pick_paused(cutoff: str | None = None) -> dict:
    from datetime import datetime, timedelta, timezone
    no = lambda why: {"run": "false", "reason": why}  # noqa: E731
    running = gh.run(["gh", "run", "list", "--repo", gh.repo(), "--workflow",
                      "autose.yml", "--status", "in_progress", "--json",
                      "databaseId", "-q", "length"], check=False)
    if running.strip() not in ("", "0", "1"):   # 1 = this run itself
        return no("another AutoSE run is in progress; it uses the quota")
    cutoff = cutoff or (datetime.now(timezone.utc) -
              timedelta(minutes=MIN_PAUSE_MIN)
              ).strftime("%Y-%m-%dT%H:%M:%SZ")
    for paused_at, n, rnd in paused_issues():
        if paused_at <= cutoff:
            return {"run": "true", "issue": n, "round": rnd, "start": "auto",
                    "reason": f"scheduled resume of issue #{n} (paused "
                              f"{paused_at})"}
    return no("no issue paused long enough to resume")


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        ev = json.load(f)
    d = decide(os.environ["GITHUB_EVENT_NAME"], ev)
    gh.set_output(**d)
    gh.summary(f"**Gate:** run={d['run']} ({d['reason']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
