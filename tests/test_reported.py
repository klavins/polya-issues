from pathlib import Path

import pytest

from issues import reported
from tests.conftest import TRACKER, by_number


def test_entry_from_a_content_issue(issues):
    e = reported.entry(by_number(issues, 7), "klavins")
    assert list(e) == ["issue", "title", "form", "kind", "location", "url", "filed", "labels", "body", "status", "resolution"]
    assert e["issue"] == 7 and e["form"] == "Content issue" and e["kind"] == "Typo or grammar"
    assert e["labels"] == ["content", "triage"]
    assert e["status"] == "open" and e["resolution"] is None
    assert "comments" not in e


def test_entry_names_comment_authors_by_role(issues):
    issue = dict(by_number(issues, 7))
    issue["comments"] = [
        {"author": {"login": issue["author"]["login"]}, "body": "Also line 30.", "createdAt": "2026-10-20T01:00:00Z"},
        {"author": {"login": "klavins"}, "body": "Thanks.", "createdAt": "2026-10-20T02:00:00Z"},
        {"author": {"login": "someone"}, "body": "Me too.", "createdAt": "2026-10-20T03:00:00Z"},
    ]
    e = reported.entry(issue, "klavins")
    assert [c["by"] for c in e["comments"]] == ["the reporter", "the owner", "another user"]
    assert e["comments"][0] == {"by": "the reporter", "on": "2026-10-20", "text": "Also line 30."}


def test_round_trip_keeps_unicode_and_uses_literal_blocks(tmp_path, issues):
    entries = [reported.entry(i, "klavins") for i in sorted(issues, key=lambda i: i["number"])]
    path = tmp_path / reported.FILE
    reported.dump(entries, path, TRACKER)
    text = path.read_text()
    assert text.startswith("# Written by `issues pull` from klavins/polya-issues")
    assert "body: |" in text and "ℕ" in text
    assert "resolution:\n" in text and "null" not in text
    assert reported.load(path) == entries


def test_empty_file_round_trip(tmp_path):
    path = tmp_path / reported.FILE
    reported.dump([], path, TRACKER)
    assert reported.load(path) == []


def test_merge_keeps_the_four_edited_fields_and_reports_what_vanished(issues):
    new = [reported.entry(by_number(issues, 7), "k"), reported.entry(by_number(issues, 8), "k")]
    old = [
        {"issue": 7, "title": "stale title", "status": "fixed", "commit": "abc1234", "resolution": "Done."},
        {"issue": 8, "status": "open", "resolution": None},
        {"issue": 99, "title": "closed by hand", "status": "wontfix", "resolution": "No."},
        {"issue": 98, "status": "open"},
    ]
    merged, dropped = reported.merge(new, old)
    assert merged[0]["status"] == "fixed" and merged[0]["commit"] == "abc1234" and merged[0]["resolution"] == "Done."
    assert merged[0]["title"] == "Typo"  # regenerated, not kept
    assert list(merged[0])[-3:] == ["status", "commit", "resolution"]
    assert merged[1]["status"] == "open"
    assert [e["issue"] for e in dropped] == [99]


def _entry(**fields):
    base = {"issue": 7, "title": "t", "status": "open", "resolution": None}
    base.update(fields)
    return base


@pytest.mark.parametrize(
    "entry, fragment",
    [
        (_entry(status="Fixed"), "status 'Fixed' is not one of"),
        (_entry(status="fixed", resolution="ok"), "needs commit"),
        (_entry(status="fixed", commit=1234567, resolution="ok"), "needs commit"),
        (_entry(status="fixed", commit="abc1234"), "needs a resolution"),
        (_entry(status="wontfix", resolution="  "), "needs a resolution"),
        (_entry(status="to", resolution="theirs"), "needs repo: one of MUPolya, polya-topology"),
        (_entry(status="to", repo="nowhere", resolution="theirs"), "needs repo"),
        (_entry(comit="abc1234"), "unknown field(s) comit"),
        ({"title": "no number"}, "without an issue number"),
    ],
)
def test_validate_names_each_fault(entry, fragment):
    problems = reported.validate([entry], "polya-basic/reported.yaml", {"MUPolya", "polya-topology"})
    assert any(fragment in p for p in problems), problems


def test_validate_accepts_every_well_formed_status():
    entries = [
        _entry(issue=1),
        _entry(issue=2, status="fixed", commit="3f2a9c1", resolution="Thanks."),
        _entry(issue=3, status="wontfix", resolution="Because."),
        _entry(issue=4, status="to", repo="MUPolya", resolution="Theirs."),
        _entry(issue=5, status="ask", resolution="Which?"),
    ]
    assert reported.validate(entries, "x", {"MUPolya"}) == []


def test_validate_catches_a_duplicate():
    assert any("listed twice" in p for p in reported.validate([_entry(), _entry()], "x", set()))


def test_load_names_the_line_of_a_yaml_fault(tmp_path):
    path = tmp_path / reported.FILE
    path.write_text("- issue: 7\n  status: open\n  resolution: |\n   bad\n  indent: [\n")
    with pytest.raises(reported.ReportedError) as err:
        reported.load(path)
    assert str(err.value).startswith(f"{path}:") and "not YAML" in str(err.value)


def test_load_rejects_a_non_list(tmp_path):
    path = tmp_path / reported.FILE
    path.write_text("issue: 7\n")
    with pytest.raises(reported.ReportedError, match="expected a list"):
        reported.load(path)
