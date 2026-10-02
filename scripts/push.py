"""Push the local history to GitHub while native git is unavailable (see F-002).

    .venv/bin/python scripts/push.py https://github.com/<owner>/<repo>.git [branch]

Reads GITHUB_TOKEN from the environment or the git-ignored .env. The token is
passed per request only: it is never printed and never written to .git/config.
"""

import os
import sys
from pathlib import Path

from dulwich import porcelain
from dulwich.repo import Repo

ROOT = Path(__file__).resolve().parents[1]


def token() -> str:
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    env = ROOT / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith("GITHUB_TOKEN=") and line.split("=", 1)[1].strip():
            return line.split("=", 1)[1].strip()
    sys.exit("GITHUB_TOKEN not set (add it to .env)")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: push.py <https url> [branch]")
    url, branch = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "main")
    repo = Repo(str(ROOT))
    local = repo.refs.read_ref(b"HEAD")
    if local.startswith(b"ref: "):
        local = local[5:]
    result = porcelain.push(repo, url, refspecs=[local + b":refs/heads/" + branch.encode()],
                            username="x-access-token", password=token(), errstream=sys.stderr.buffer)
    failed = {ref.decode(): err for ref, err in (getattr(result, "ref_status", None) or {}).items() if err}
    if failed:
        sys.exit(f"push rejected: {failed}")
    print(f"pushed {repo.head().decode()[:10]} to {url} ({branch})")


if __name__ == "__main__":
    main()
