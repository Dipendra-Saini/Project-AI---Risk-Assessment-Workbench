"""Commit helper used while native git is unavailable on the build machine.

Uses dulwich (pure-Python git) and produces a standard .git repository, so the
history is identical to one made with the git CLI.

    .venv/bin/python scripts/commit.py "message"
"""

import subprocess
import sys
from pathlib import Path

from dulwich import porcelain
from dulwich.repo import Repo

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = b"Risk Workbench Team <team@example.com>"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: commit.py <message>")
    if subprocess.run(["which", "git"], capture_output=True).returncode == 0:
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
            subprocess.run(["git", "commit", "-m", sys.argv[1]], cwd=ROOT, check=True)
            return
        except subprocess.CalledProcessError:
            pass
    if not (ROOT / ".git").exists():
        porcelain.init(str(ROOT))
    repo = Repo(str(ROOT))
    porcelain.add(repo)
    for path in porcelain.status(repo).unstaged:
        if not (ROOT / path.decode()).exists():
            porcelain.rm(repo, paths=[str(ROOT / path.decode())])
    sha = porcelain.commit(repo, message=sys.argv[1].encode(), author=AUTHOR, committer=AUTHOR)
    print(sha.decode()[:10], sys.argv[1])


if __name__ == "__main__":
    main()
