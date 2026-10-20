"""Fixtures: the eight recorded issues, a fake `gh` on the PATH, and a root of fake checkouts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
TRACKER = "klavins/polya-issues"


@pytest.fixture
def issues() -> list[dict]:
    return json.loads((FIXTURES / "issues.json").read_text())


def by_number(issues: list[dict], number: int) -> dict:
    return next(i for i in issues if i["number"] == number)


@pytest.fixture
def fake_gh(tmp_path, monkeypatch):
    """A `gh` that logs every call and answers `issue list` from a JSON file tests may rewrite."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    answers = tmp_path / "issues.json"
    answers.write_text((FIXTURES / "issues.json").read_text())
    script = bin_dir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        'case "$*" in\n'
        f'  *"issue list"*) cat "{answers}" ;;\n'
        '  *"issue comment"*) cat > /dev/null ;;\n'
        "esac\n"
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")

    class Fake:
        def calls(self) -> list[str]:
            return log.read_text().splitlines() if log.exists() else []

        def answer(self, issues: list[dict]) -> None:
            answers.write_text(json.dumps(issues))

    return Fake()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


class Root(type(Path())):
    """A root path that also remembers polya-basic's pushed and unpushed commits."""


@pytest.fixture
def root(tmp_path):
    """Checkouts beside a tracker: polya-basic (a content project with a pushed and an unpushed
    commit), MUPolya and polya-topology (bare directories with a .git), and the tracker itself."""
    root = Root(tmp_path / "polya")
    root.mkdir()
    for name in ("MUPolya", "polya-topology", "polya-issues"):
        (root / name / ".git").mkdir(parents=True)
    basic = root / "polya-basic"
    basic.mkdir()
    git(basic, "init", "-q", "-b", "main")
    (basic / "about.yaml").write_text("subjects: []\n")
    git(basic, "add", "about.yaml")
    git(basic, "commit", "-q", "-m", "first")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    git(basic, "remote", "add", "origin", str(remote))
    git(basic, "push", "-q", "origin", "main")
    pushed = git(basic, "rev-parse", "--short", "HEAD")
    (basic / "STYLE.md").write_text("style\n")
    git(basic, "add", "STYLE.md")
    git(basic, "commit", "-q", "-m", "second")
    unpushed = git(basic, "rev-parse", "--short", "HEAD")
    root.pushed, root.unpushed = pushed, unpushed
    return root
