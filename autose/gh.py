"""Thin wrappers around git and the gh CLI. Only orchestrator code calls
these; no LLM tool can reach GitHub (ADR-005)."""
import json
import os
import subprocess
import sys


def log(msg: str) -> None:
    # Kept local so gate/post jobs need no `openai` install.
    print(f"[autose] {msg}", file=sys.stderr, flush=True)


def run(cmd: list, cwd=None, check: bool = True, env=None) -> str:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])}... failed "
                           f"({r.returncode}): {r.stderr.strip()[:800]}")
    return r.stdout.strip()


def gh_json(args: list):
    return json.loads(run(["gh"] + args))


def repo() -> str:
    return os.environ["GITHUB_REPOSITORY"]


def run_url() -> str:
    return (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{repo()}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '0')}")


def issue(number: int) -> dict:
    return gh_json(["issue", "view", str(number), "--repo", repo(),
                    "--json", "number,title,body,url"])


def comment_issue(number: int, body: str) -> None:
    try:
        run(["gh", "issue", "comment", str(number), "--repo", repo(),
             "--body", body])
    except RuntimeError as e:
        log(f"could not comment on #{number}: {e}")


def set_output(**kw) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{k}={v}\n" for k, v in kw.items())
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(lines)
    log("outputs: " + lines.replace("\n", " "))


def summary(md: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(md + "\n")
