import json
from pathlib import Path

import yaml

from issues import cli, reported
from tests.conftest import TRACKER, by_number


def run(root, *args, capsys):
    code = cli.main(["--root", str(root), "--tracker", TRACKER, *args])
    return code, capsys.readouterr().out


def load(root, repo):
    return reported.load(root / repo / reported.FILE)


def test_pull_routes_by_the_form_and_writes_each_repository(root, fake_gh, capsys):
    code, out = run(root, "pull", capsys=capsys)
    assert code == 0
    basic = load(root, "polya-basic")
    mupolya = load(root, "MUPolya")
    assert [e["issue"] for e in basic] == [1, 2, 6, 7, 8, 9, 10, 12]  # #2's form names polya-basic
    assert [e["issue"] for e in mupolya] == [11]
    assert not (root / "polya-topology" / reported.FILE).exists()
    assert not (root / "polya-issues" / reported.FILE).exists()
    assert "polya-basic/reported.yaml  8 entries   #1 #2 #6 #7 #8 #9 #10 #12" in out
    assert "unrouted: none" in out
    assert "#7   polya-basic  open" in out  # the status table
    assert fake_gh.calls() == [f"issue list --state open --limit 500 --json number,title,body,labels,createdAt,url,author,comments -R {TRACKER}"]


def test_pull_routes_by_label_first_and_reports_the_unroutable(root, fake_gh, capsys, issues):
    by_number(issues, 7)["labels"].append({"name": "repo:polya-topology"})  # a form saying polya-basic, relabeled
    by_number(issues, 6)["body"] = by_number(issues, 6)["body"].replace("polya-basic", "Other / not sure")
    by_number(issues, 10)["labels"].append({"name": "repo:nowhere"})
    fake_gh.answer(issues)
    code, out = run(root, "pull", capsys=capsys)
    assert code == 0
    assert [e["issue"] for e in load(root, "polya-topology")] == [7]
    assert [e["issue"] for e in load(root, "polya-basic")] == [1, 2, 8, 9, 12]
    assert "unrouted #6 [Content]:: the form names no repository" in out
    assert "unrouted #10 Issue with Definition Pair.swap2: label repo:nowhere names no checkout" in out


def test_pull_keeps_a_sessions_edits_and_drops_the_closed(root, fake_gh, capsys, issues):
    run(root, "pull", capsys=capsys)
    path = root / "polya-basic" / reported.FILE
    entries = reported.load(path)
    by = {e["issue"]: e for e in entries}
    by[7].update(status="fixed", commit="abc1234", resolution="Thank you; fixed.")
    by[8].update(status="ask", resolution="Which line?")
    reported.dump(entries, path, TRACKER)
    fake_gh.answer([i for i in issues if i["number"] != 8])  # #8 closed by hand on GitHub
    code, out = run(root, "pull", capsys=capsys)
    after = {e["issue"]: e for e in reported.load(path)}
    assert list(after) == [1, 2, 6, 7, 9, 10, 12]
    assert after[7]["status"] == "fixed" and after[7]["commit"] == "abc1234"
    assert "dropped #8: gone from GitHub with status ask unposted" in out
    assert "#7   polya-basic  fixed in abc1234" in out


def test_pull_leaves_a_file_it_cannot_parse(root, fake_gh, capsys):
    path = root / "polya-basic" / reported.FILE
    path.write_text("- issue: [\n")
    code, out = run(root, "pull", capsys=capsys)
    assert code == 1
    assert path.read_text() == "- issue: [\n"
    assert "polya-basic/reported.yaml left as it is" in out and "not YAML" in out
    assert (root / "MUPolya" / reported.FILE).exists()  # the other file was still written


def test_check_reports_every_fault_and_passes_a_clean_tree(root, fake_gh, capsys):
    run(root, "pull", capsys=capsys)
    code, out = run(root, "check", capsys=capsys)
    assert code == 0 and "every reported.yaml is well formed" in out
    path = root / "polya-basic" / reported.FILE
    entries = reported.load(path)
    entries[0]["status"] = "done"
    entries[1].update(status="fixed", resolution="ok")
    reported.dump(entries, path, TRACKER)
    code, out = run(root, "check", capsys=capsys)
    assert code == 1
    assert "polya-basic/reported.yaml entry #1: status 'done' is not one of" in out
    assert "polya-basic/reported.yaml entry #2: status fixed needs commit" in out


def _resolve(root):
    """Five resolutions in polya-basic: a pushed fix, an unpushed fix, a wontfix, a handoff, a question."""
    path = root / "polya-basic" / reported.FILE
    entries = reported.load(path)
    by = {e["issue"]: e for e in entries}
    by[7].update(status="fixed", commit=root.pushed, resolution="Thank you. The comment now reads \"A Real Number\".")
    by[6].update(status="fixed", commit=root.unpushed, resolution="Fixed the range.")
    by[8].update(status="wontfix", resolution="Two rotations is what the problem intends; see its statement.")
    by[1].update(status="to", repo="polya-topology", resolution="Set Theory now introduces the notation.")
    by[9].update(status="ask", resolution="Is the right child meant to be a leaf?")
    reported.dump(entries, path, TRACKER)
    return by


def test_post_dry_run_shows_everything_and_touches_nothing(root, fake_gh, capsys):
    run(root, "pull", capsys=capsys)
    _resolve(root)
    code, out = run(root, "post", "--dry-run", capsys=capsys)
    assert code == 0
    assert "#7 Typo  ->  comment and close as completed" in out
    assert f"Fixed in polya-basic commit {root.pushed}; it reaches the site with the next publish of its subject." in out
    assert f"#6 [Content]:: skipped, polya-basic commit {root.unpushed} is not on the remote; push first" in out
    assert "#8 Incorrect Paragraph  ->  comment and close as not planned" in out
    assert "->  comment, label repo:polya-topology and leave open" in out
    assert "#9 Binary Tree Issue  ->" not in out  # the ask entry is not offered
    assert "dry run: 4 action(s) shown, nothing posted" in out
    assert [c for c in fake_gh.calls() if "issue list" not in c] == []


def test_post_refuses_a_malformed_file_before_any_call(root, fake_gh, capsys):
    run(root, "pull", capsys=capsys)
    _resolve(root)
    path = root / "MUPolya" / reported.FILE
    entries = reported.load(path)
    entries[0]["status"] = "fixed"
    reported.dump(entries, path, TRACKER)
    code, out = run(root, "post", "--yes", capsys=capsys)
    assert code == 1
    assert "MUPolya/reported.yaml entry #11: status fixed needs commit" in out
    assert "nothing posted" in out
    assert [c for c in fake_gh.calls() if "issue list" not in c] == []


def test_post_yes_comments_closes_and_relabels_then_pulls(root, fake_gh, capsys):
    run(root, "pull", capsys=capsys)
    _resolve(root)
    code, out = run(root, "post", "--yes", capsys=capsys)
    assert code == 0
    calls = [c for c in fake_gh.calls() if "issue list" not in c]
    assert calls == [
        f"issue comment 1 --body-file - -R {TRACKER}",
        f"label create repo:polya-topology --color 1d76db --description Routed to polya-topology --force -R {TRACKER}",
        f"issue edit 1 --add-label repo:polya-topology -R {TRACKER}",  # #1 carries no triage label
        f"issue comment 7 --body-file - -R {TRACKER}",
        f"issue edit 7 --remove-label triage -R {TRACKER}",
        f"issue close 7 --reason completed -R {TRACKER}",
        f"issue comment 8 --body-file - -R {TRACKER}",
        f"issue edit 8 --remove-label triage -R {TRACKER}",
        f"issue close 8 --reason not planned -R {TRACKER}",
    ]
    assert "posted 3 of 4" in out
    assert fake_gh.calls().count(f"issue list --state open --limit 500 --json number,title,body,labels,createdAt,url,author,comments -R {TRACKER}") == 2
    # the pull after posting rewrote the file; the fake tracker still lists everything open, so the edits stay
    after = {e["issue"]: e for e in load(root, "polya-basic")}
    assert after[7]["status"] == "fixed" and after[9]["status"] == "ask"


def test_post_with_nothing_resolved(root, fake_gh, capsys):
    run(root, "pull", capsys=capsys)
    code, out = run(root, "post", "--yes", capsys=capsys)
    assert code == 0 and "nothing to post" in out


def test_post_asks_per_item_and_stops_on_q(root, fake_gh, capsys, monkeypatch):
    run(root, "pull", capsys=capsys)
    _resolve(root)
    answers = iter(["n", "y", "q"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    code, out = run(root, "post", capsys=capsys)
    calls = [c for c in fake_gh.calls() if "issue list" not in c]
    assert "skipped #1" in out and "posted #7" in out and "stopped" in out
    assert [c for c in calls if c.startswith("issue close")] == [f"issue close 7 --reason completed -R {TRACKER}"]


def test_status_table(root, fake_gh, capsys):
    run(root, "pull", capsys=capsys)
    _resolve(root)
    code, out = run(root, "status", capsys=capsys)
    assert code == 0
    lines = out.splitlines()
    assert lines[0].startswith("#1   polya-basic  to polya-topology")
    assert any(l.startswith(f"#7   polya-basic  fixed in {root.pushed}") for l in lines)
    assert any(l.startswith("#11  MUPolya      open") for l in lines)


def test_status_with_no_files(root, capsys):
    code, out = run(root, "status", capsys=capsys)
    assert code == 0 and out.strip() == "nothing open"


def test_route_prefers_the_label(issues):
    issue = dict(issues[0])
    issue["labels"] = issue["labels"] + [{"name": "repo:MUPolya"}]
    assert cli.route(issue, {"MUPolya", "polya-basic"}) == ("MUPolya", "label repo:MUPolya")
    assert cli.route(issues[0], {"MUPolya", "polya-basic"}) == ("polya-basic", "the form")
    assert cli.route(issues[0], {"MUPolya"}) == (None, "the form names polya-basic, which is no checkout under the root")
