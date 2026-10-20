"""`issues`: pull, check, status and post.

The checkouts are the siblings of the tracker's, under one root. `pull` and `check` and
`status` write nothing to GitHub and are anyone's; `post` comments and closes under the
owner's account and is the owner's.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from . import forms, reported
from .github import GitHub, GitHubError
from .reported import FILE, ReportedError

TRACKER = "klavins/polya-issues"


def default_root() -> Path:
    env = os.environ.get("ISSUES_ROOT")
    return Path(env) if env else Path(__file__).resolve().parents[2]


def repositories(root: Path, tracker: str) -> list[Path]:
    """Every git checkout under the root but the tracker's own."""
    own = tracker.split("/")[-1]
    return sorted(
        d for d in root.iterdir() if d.is_dir() and (d / ".git").exists() and d.name != own
    )


def route(issue: dict, names: set[str]) -> tuple[str | None, str]:
    """The repository an issue goes to and why, or None and why not."""
    for label in (label["name"] for label in issue.get("labels", [])):
        if label.startswith("repo:"):
            name = label[len("repo:"):]
            if name in names:
                return name, f"label {label}"
            return None, f"label {label} names no checkout under the root"
    named = forms.project(forms.fields(issue.get("body") or ""))
    if named is None:
        return None, "the form names no repository"
    if named in names:
        return named, "the form"
    return None, f"the form names {named}, which is no checkout under the root"


def pull(args: argparse.Namespace) -> int:
    repos = repositories(args.root, args.tracker)
    names = {r.name for r in repos}
    owner = args.tracker.split("/")[0]
    routed: dict[str, list[dict]] = {}
    unrouted: list[tuple[dict, str]] = []
    for issue in GitHub(args.tracker).open_issues():
        name, why = route(issue, names)
        if name:
            routed.setdefault(name, []).append(issue)
        else:
            unrouted.append((issue, why))
    failed = False
    for repo in repos:
        path = repo / FILE
        new = [reported.entry(i, owner) for i in sorted(routed.get(repo.name, []), key=lambda i: i["number"])]
        if not new and not path.exists():
            continue
        try:
            old = reported.load(path) if path.exists() else []
        except ReportedError as err:
            print(f"{repo.name}/{FILE} left as it is: {err}")
            failed = True
            continue
        entries, dropped = reported.merge(new, old)
        reported.dump(entries, path, args.tracker)
        numbers = " ".join(f"#{e['issue']}" for e in entries)
        print(f"{repo.name}/{FILE}  {len(entries)} entries   {numbers}".rstrip())
        for e in dropped:
            print(f"  dropped #{e['issue']}: gone from GitHub with status {reported.status_word(e)} unposted")
    for issue, why in unrouted:
        print(f"unrouted #{issue['number']} {issue['title']}: {why}; label it repo:<name> on GitHub")
    if not unrouted:
        print("unrouted: none")
    print()
    print_status(repos)
    return 1 if failed else 0


def _load_all(repos: list[Path]) -> tuple[list[tuple[Path, list[dict]]], list[str]]:
    names = {r.name for r in repos}
    loaded: list[tuple[Path, list[dict]]] = []
    problems: list[str] = []
    for repo in repos:
        path = repo / FILE
        if not path.exists():
            continue
        try:
            entries = reported.load(path)
        except ReportedError as err:
            problems.append(str(err))
            continue
        problems += reported.validate(entries, f"{repo.name}/{FILE}", names)
        loaded.append((repo, entries))
    return loaded, problems


def check(args: argparse.Namespace) -> int:
    _, problems = _load_all(repositories(args.root, args.tracker))
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"every {FILE} is well formed")
    return 0


def print_status(repos: list[Path]) -> None:
    rows: list[tuple[int, str, str, str, str]] = []
    for repo in repos:
        path = repo / FILE
        if not path.exists():
            continue
        try:
            entries = reported.load(path)
        except ReportedError as err:
            print(err)
            continue
        for e in entries:
            number = e.get("issue")
            rows.append((
                number if isinstance(number, int) else 0,
                repo.name,
                reported.status_word(e),
                str(e.get("title", ""))[:60],
                reported.days_open(e),
            ))
    if not rows:
        print("nothing open")
        return
    rows.sort()
    widths = [max(len(str(row[i])) for row in rows) for i in range(5)]
    for number, repo, status, title, age in rows:
        print(f"#{number:<{widths[0]}}  {repo:<{widths[1]}}  {status:<{widths[2]}}  {title:<{widths[3]}}  {age}".rstrip())


def status(args: argparse.Namespace) -> int:
    print_status(repositories(args.root, args.tracker))
    return 0


def commit_not_on_remote(repo: Path, sha: str) -> str | None:
    """Why a fixed entry cannot be posted yet, or None when its commit is on the remote."""

    def git(*cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repo), *cmd], capture_output=True, text=True)

    if git("cat-file", "-e", f"{sha}^{{commit}}").returncode:
        return f"{repo.name} has no commit {sha}"
    if not git("branch", "-r", "--contains", sha).stdout.strip():
        return f"{repo.name} commit {sha} is not on the remote; push first"
    return None


def comment_text(repo: Path, e: dict) -> str:
    text = str(e["resolution"]).strip()
    if e["status"] == "fixed":
        site = "the next publish of its subject" if (repo / "about.yaml").exists() else "the next deployment"
        text += f"\n\nFixed in {repo.name} commit {e['commit']}; it reaches the site with {site}."
    return text


def apply(gh: GitHub, e: dict, text: str) -> None:
    """One entry's actions on GitHub: the comment, then the labels, then the close or the route."""
    number = e["issue"]
    labels = list(e.get("labels") or [])
    gh.comment(number, text)
    if e["status"] == "to":
        label = f"repo:{e['repo']}"
        gh.ensure_label(label, f"Routed to {e['repo']}")
        remove = [l for l in labels if (l == "triage" or l.startswith("repo:")) and l != label]
        gh.relabel(number, add=[label] if label not in labels else [], remove=remove)
    else:
        gh.relabel(number, remove=[l for l in labels if l == "triage"])
        gh.close(number, "completed" if e["status"] == "fixed" else "not planned")


DESCRIBE = {
    "fixed": "comment and close as completed",
    "wontfix": "comment and close as not planned",
    "to": "comment, label repo:{repo} and leave open",
}


def post(args: argparse.Namespace) -> int:
    repos = repositories(args.root, args.tracker)
    loaded, problems = _load_all(repos)
    if problems:
        for problem in problems:
            print(problem)
        print("nothing posted: fix the file and run again")
        return 1
    actions = [(repo, e) for repo, entries in loaded for e in entries if e["status"] in DESCRIBE]
    if not actions:
        print("nothing to post")
        return 0
    gh = GitHub(args.tracker)
    posted = 0
    for repo, e in actions:
        number, title = e["issue"], e.get("title", "")
        if e["status"] == "fixed":
            problem = commit_not_on_remote(repo, e["commit"])
            if problem:
                print(f"\n#{number} {title}: skipped, {problem}")
                continue
        text = comment_text(repo, e)
        print(f"\n#{number} {title}  ->  {DESCRIBE[e['status']].format(repo=e.get('repo'))}")
        print("---")
        print(text)
        print("---")
        if args.dry_run:
            continue
        if not args.yes:
            answer = input("post? [y/n/q] ").strip().lower()
            if answer == "q":
                print("stopped")
                break
            if answer != "y":
                print(f"skipped #{number}")
                continue
        apply(gh, e, text)
        posted += 1
        print(f"posted #{number}")
    if args.dry_run:
        print(f"\ndry run: {len(actions)} action(s) shown, nothing posted")
        return 0
    print(f"\nposted {posted} of {len(actions)}")
    if posted:
        print()
        return pull(args)
    return 0


COMMANDS = {"pull": pull, "check": check, "status": status, "post": post}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="issues",
        description="Carries the tracker's open issues to each repository's reported.yaml and their resolutions back.",
    )
    parser.add_argument("--root", type=Path, default=default_root(), help="the directory holding the checkouts (default: the tracker checkout's parent, or $ISSUES_ROOT)")
    parser.add_argument("--tracker", default=os.environ.get("ISSUES_TRACKER", TRACKER), help=f"the tracker repository (default {TRACKER})")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pull", help="write every repository's reported.yaml from the open issues (read-only on GitHub)")
    sub.add_parser("check", help="validate every reported.yaml")
    sub.add_parser("status", help="one table of every entry across the repositories")
    p = sub.add_parser("post", help="the owner's: comment, close and relabel on GitHub from the resolutions, one item at a time")
    p.add_argument("--dry-run", action="store_true", help="show every action and take none")
    p.add_argument("--yes", action="store_true", help="take every action without asking")
    args = parser.parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except (ReportedError, GitHubError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
