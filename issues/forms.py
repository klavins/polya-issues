"""The four issue forms, read from the body GitHub renders for them.

A form's body is a run of `### Label` headings, each followed by its value; a field left
empty renders as `_No response_`. Every form has a dropdown naming the project, and its
options are the directory names of the checkouts, which is what routing relies on.
"""

from __future__ import annotations

import re

FORMS = {
    "bug": "Bug report",
    "content": "Content issue",
    "enhancement": "Feature request",
    "content-suggestion": "New content suggestion",
}
PROJECT_FIELDS = ("Subject repository", "Project")
KIND_FIELDS = ("Kind of problem", "What are you suggesting?")
LOCATION_FIELDS = ("Location", "Page URL", "Where should it go?")
UNROUTED = {"Not sure", "Other / not sure", "A new subject"}

_HEADING = re.compile(r"^### (.+?)\s*$", re.M)


def fields(body: str) -> dict[str, str]:
    """The form's fields, label to value, in the body's order.

    Text before the first heading, or a body with no headings at all, is the field "".
    """
    parts = _HEADING.split(body.replace("\r\n", "\n"))
    out: dict[str, str] = {}
    lead = parts[0].strip()
    if lead:
        out[""] = lead
    for label, value in zip(parts[1::2], parts[2::2]):
        value = value.strip()
        out[label.strip()] = "" if value == "_No response_" else value
    return out


def project(form: dict[str, str]) -> str | None:
    """The repository the form names, or None when it names none or says it is not sure."""
    for label in PROJECT_FIELDS:
        value = form.get(label, "").strip()
        if value and value not in UNROUTED:
            return value
    return None


def first(form: dict[str, str], labels: tuple[str, ...]) -> str:
    for label in labels:
        if form.get(label):
            return form[label]
    return ""


def body(form: dict[str, str]) -> str:
    """The fields that are not the route, the kind or the location, as Markdown paragraphs."""
    skip = set(PROJECT_FIELDS) | set(KIND_FIELDS) | set(LOCATION_FIELDS)
    paragraphs = []
    for label, value in form.items():
        if label in skip or not value:
            continue
        paragraphs.append(value if label == "" else f"**{label}**\n{value}")
    return "\n\n".join(paragraphs)
