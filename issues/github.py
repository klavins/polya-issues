"""The tracker through `gh`: five calls and nothing else.

`gh` is signed in as the owner, so everything but `open_issues` writes under their name;
that is why `issues post` is the owner's command.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable

FIELDS = "number,title,body,labels,createdAt,url,author,comments"


class GitHubError(Exception):
    pass


class GitHub:
    def __init__(self, tracker: str, gh: str = "gh"):
        self.tracker = tracker
        self.gh = gh

    def _run(self, *args: str, stdin: str | None = None) -> str:
        proc = subprocess.run(
            [self.gh, *args, "-R", self.tracker], input=stdin, capture_output=True, text=True
        )
        if proc.returncode:
            detail = proc.stderr.strip() or proc.stdout.strip()
            raise GitHubError(f"gh {' '.join(args[:2])}: {detail}")
        return proc.stdout

    def open_issues(self) -> list[dict]:
        out = self._run("issue", "list", "--state", "open", "--limit", "500", "--json", FIELDS)
        return json.loads(out or "[]")

    def comment(self, number: int, text: str) -> None:
        self._run("issue", "comment", str(number), "--body-file", "-", stdin=text)

    def close(self, number: int, reason: str) -> None:
        self._run("issue", "close", str(number), "--reason", reason)

    def relabel(self, number: int, add: Iterable[str] = (), remove: Iterable[str] = ()) -> None:
        args = ["issue", "edit", str(number)]
        for label in add:
            args += ["--add-label", label]
        for label in remove:
            args += ["--remove-label", label]
        if len(args) > 3:
            self._run(*args)

    def ensure_label(self, name: str, description: str) -> None:
        self._run("label", "create", name, "--color", "1d76db", "--description", description, "--force")
