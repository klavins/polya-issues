"""`reported.yaml`: a repository's working copy of the open issues routed to it.

`issues pull` writes it, a session edits four fields of an entry (status, commit, repo and
resolution), `issues check` validates it and `issues post` reads it. GitHub is the record:
every pull regenerates everything but those four fields.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

from . import forms

FILE = "reported.yaml"
STATUSES = ("open", "fixed", "wontfix", "to", "ask")
EDITABLE = ("status", "commit", "repo", "resolution")
ORDER = (
    "issue", "title", "form", "kind", "location", "url", "filed", "labels", "body",
    "comments", "status", "commit", "repo", "resolution",
)
SHA = re.compile(r"^[0-9a-f]{7,40}$")

HEADER = """\
# Written by `issues pull` from {tracker}: the open issues routed to this repository.
# GitHub is the record. Every pull regenerates this file and keeps only the four fields a
# session edits: status, commit, repo and resolution. Nothing else here is yours to change.
#   status: open | fixed (with commit: its hash) | wontfix | to (with repo: a sibling) | ask
#   resolution: written for the reporter, who reads it as the owner's comment; every status
#   but open needs one.
# `issues check` validates this file; `issues post`, the owner's command, carries it to GitHub.
"""


class ReportedError(Exception):
    pass


def entry(issue: dict, owner: str) -> dict:
    """An entry as pull writes it, before any session edit."""
    form = forms.fields(issue.get("body") or "")
    labels = [label["name"] for label in issue.get("labels", [])]
    kind = forms.first(form, forms.KIND_FIELDS)
    location = forms.first(form, forms.LOCATION_FIELDS)
    reporter = (issue.get("author") or {}).get("login")
    comments = [
        {
            "by": _role(comment.get("author", {}).get("login"), reporter, owner),
            "on": comment.get("createdAt", "")[:10],
            "text": _clean(comment.get("body") or ""),
        }
        for comment in issue.get("comments") or []
    ]
    e = {
        "issue": issue["number"],
        "title": issue["title"].strip(),
        "form": next((forms.FORMS[label] for label in labels if label in forms.FORMS), "Issue"),
        "url": issue["url"],
        "filed": issue.get("createdAt", "")[:10],
        "labels": labels,
        "body": _clean(forms.body(form)),
        "status": "open",
        "resolution": None,
    }
    if kind:
        e["kind"] = kind
    if location:
        e["location"] = location
    if comments:
        e["comments"] = comments
    return _ordered(e)


def _role(login: str | None, reporter: str | None, owner: str) -> str:
    if login == owner:
        return "the owner"
    if login == reporter:
        return "the reporter"
    return "another user"


def _clean(text: str) -> str:
    """Line ends stripped, so the YAML writer can use a literal block for it."""
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def _ordered(e: dict) -> dict:
    return {key: e[key] for key in ORDER if key in e}


def load(path: Path) -> list[dict]:
    """The file's entries; a ReportedError names the line when it is not YAML."""
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as err:
        mark = getattr(err, "problem_mark", None)
        where = f"{path}:{mark.line + 1}" if mark else str(path)
        raise ReportedError(f"{where}: not YAML: {getattr(err, 'problem', err)}") from None
    if data is None:
        return []
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ReportedError(f"{path}: expected a list of entries")
    return data


def validate(entries: list[dict], where: str, repos: set[str]) -> list[str]:
    """Every way an entry can be wrong, one line each; empty when the file is well formed."""
    problems: list[str] = []
    seen: set[int] = set()
    for e in entries:
        number = e.get("issue")
        if not isinstance(number, int):
            problems.append(f"{where}: an entry without an issue number")
            continue
        tag = f"{where} entry #{number}"
        if number in seen:
            problems.append(f"{tag}: listed twice")
        seen.add(number)
        unknown = sorted(set(e) - set(ORDER))
        if unknown:
            problems.append(f"{tag}: unknown field(s) {', '.join(unknown)}")
        status = e.get("status")
        if status not in STATUSES:
            problems.append(f"{tag}: status {status!r} is not one of {', '.join(STATUSES)}")
            continue
        resolution = e.get("resolution")
        if status != "open" and not (isinstance(resolution, str) and resolution.strip()):
            problems.append(f"{tag}: status {status} needs a resolution, written for the reporter")
        if status == "fixed":
            commit = e.get("commit")
            if not (isinstance(commit, str) and SHA.match(commit)):
                problems.append(f"{tag}: status fixed needs commit: a hash of 7 to 40 hex digits, quoted")
        if status == "to":
            repo = e.get("repo")
            if repo not in repos:
                problems.append(f"{tag}: status to needs repo: one of {', '.join(sorted(repos))}")
    return problems


def merge(new: list[dict], old: list[dict]) -> tuple[list[dict], list[dict]]:
    """The regenerated entries with the old file's edits kept by issue number.

    Also returns the old entries that are gone from GitHub while carrying an unposted status.
    """
    kept = {e["issue"]: e for e in old if isinstance(e.get("issue"), int)}
    for e in new:
        previous = kept.pop(e["issue"], None)
        if previous:
            for key in EDITABLE:
                if previous.get(key) not in (None, ""):
                    e[key] = previous[key]
    dropped = [e for e in kept.values() if e.get("status") not in (None, "open")]
    return [_ordered(e) for e in new], dropped


class _Dumper(yaml.SafeDumper):
    pass


def _represent_str(dumper: yaml.SafeDumper, text: str):
    style = "|" if "\n" in text else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", text, style=style)


_Dumper.add_representer(str, _represent_str)
_Dumper.add_representer(type(None), lambda d, _: d.represent_scalar("tag:yaml.org,2002:null", ""))


def dump(entries: list[dict], path: Path, tracker: str) -> None:
    text = yaml.dump(
        entries, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10_000, default_flow_style=False
    )
    path.write_text(HEADER.format(tracker=tracker) + ("\n" + text if entries else "\n[]\n"))


def status_word(e: dict) -> str:
    status = e.get("status")
    if status == "fixed" and e.get("commit"):
        return f"fixed in {e['commit']}"
    if status == "to" and e.get("repo"):
        return f"to {e['repo']}"
    return str(status)


def days_open(e: dict) -> str:
    try:
        days = (date.today() - date.fromisoformat(str(e.get("filed")))).days
    except ValueError:
        return ""
    return f"{days} day" if days == 1 else f"{days} days"
