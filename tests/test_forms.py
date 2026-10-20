from issues import forms
from tests.conftest import by_number


def test_content_issue_fields(issues):
    f = forms.fields(by_number(issues, 7)["body"])
    assert f["Subject repository"] == "polya-basic"
    assert f["Kind of problem"] == "Typo or grammar"
    assert f["Location"].startswith("Getting Started / Types")
    assert '"-- A Real Numer"' in f["What it currently says"]
    assert forms.project(f) == "polya-basic"


def test_bug_report_fields(issues):
    f = forms.fields(by_number(issues, 11)["body"])
    assert f["Project"] == "MUPolya"
    assert f["Page URL"].startswith("https://")
    assert f["Error messages or Lean output"].startswith("```shell")
    assert f["Screenshots"] == ""  # _No response_
    assert forms.project(f) == "MUPolya"


def test_every_recorded_issue_names_a_repository(issues):
    assert {forms.project(forms.fields(i["body"])) for i in issues} == {"polya-basic", "MUPolya"}


def test_not_sure_is_no_route():
    assert forms.project({"Project": "Not sure"}) is None
    assert forms.project({"Subject repository": "Other / not sure"}) is None
    assert forms.project({}) is None


def test_body_leaves_out_the_route_the_kind_and_the_location(issues):
    f = forms.fields(by_number(issues, 7)["body"])
    body = forms.body(f)
    assert "polya-basic" not in body and "Typo or grammar" not in body and "Getting Started" not in body
    assert body.startswith("**What it currently says**\nOn Line 25")
    assert "**What you think it should say**" in body


def test_a_body_without_headings_is_one_field():
    f = forms.fields("Just some text.\nTwo lines.")
    assert f == {"": "Just some text.\nTwo lines."}
    assert forms.body(f) == "Just some text.\nTwo lines."
    assert forms.project(f) is None
