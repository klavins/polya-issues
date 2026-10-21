# polya-issues

The issue tracker for **MUPolya**, **polya-topology**, and **polya-basic**.

To file an issue, go to [Issues → New issue](https://github.com/klavins/polya-issues/issues/new/choose) and choose one of the forms below. Each form asks which project the issue is about.

## Which form should I use?

| Form | Use it for |
|---|---|
| **Bug report** | Something in the MUPolya site or app is broken: a page won't load, a button doesn't work, the Lean checker misbehaves. |
| **Content issue** | A mistake in existing material in polya-topology or polya-basic: a typo, a wrong statement or proof, Lean code that doesn't compile, an ambiguous problem, a confusing explanation, or a broken link. |
| **Feature request** | An idea for a new feature or an improvement to MUPolya. |
| **New content suggestion** | A new problem, concept, section, example, or whole subject you'd like to see added. |

If you're not sure, pick the closest form. We'll relabel it if needed.

## Writing a good bug report

A bug we can reproduce is a bug we can fix. Please:

1. **Search first.** Check [open issues](https://github.com/klavins/polya-issues/issues) to see whether someone has already reported the problem. If so, add a comment there instead of opening a new issue.
2. **Use a specific title.** Write "Submit button does nothing on Problem 3 of Open Sets", not "Site broken".
3. **Report one problem per issue.** Unrelated bugs should go in separate reports.
4. **Give the page URL.** Paste the link from your browser's address bar.
5. **Separate what happened from what you expected.** Describe each one plainly in its own field.
6. **List exact steps to reproduce.** Number them, starting from a fresh page load, so someone else can follow them and see the same thing:
   ```
   1. Go to https://...
   2. Click "Check proof"
   3. The spinner never stops
   ```
7. **Paste error messages as text, not screenshots.** Copy the full Lean output or error message into the *Error messages or Lean output* field, where it will be formatted as code. If you need to include code anywhere else, wrap it in a fenced block:
   ````
   ```lean
   theorem foo : 1 + 1 = 2 := by rfl
   ```
   ````
8. **Include your browser and operating system,** for example "Firefox 131 on macOS 15".
9. **Add screenshots** for visual problems, such as layout or rendering glitches. Drag the images into the form.

If the problem is with the mathematics or wording of a subject rather than the software, use the **Content issue** form instead.

## For a repository's maintainer

The open issues routed to your repository are in `reported.yaml` at its root, written by
`issues pull` (from a checkout of this repository beside yours, `uv run issues pull`; it is
read-only on GitHub, so run it whenever you like). An entry holds the issue as it was filed, its
comments, and four fields that are yours to edit: `status`, `commit`, `repo` and `resolution`.
Everything else is regenerated on every pull, so change nothing else.

When you have addressed an issue:

1. **Set `status`** to one of five words.

   | status | when | also needs |
   |---|---|---|
   | `fixed` | the fix is committed | `commit`: the hash of that commit, quoted if it is all digits |
   | `wontfix` | the content is right as it stands | a `resolution` saying why |
   | `to` | the issue belongs to another repository | `repo`: that repository's name, such as `polya-topology` |
   | `ask` | you need the tracker's maintainer to decide something | a `resolution` holding the question |
   | `open` | nothing done yet | |

2. **Write `resolution` for the reporter.** It is posted word for word as a comment on the
   issue, so say what changed in their terms, not yours. A multi-line text goes under `|`. For a
   `fixed` entry the tool appends the repository, the commit and when the change reaches the
   site; you need not.

3. **Run `uv run issues check`.** It validates every `reported.yaml` and names any entry that is
   wrong: a status outside the five, a `fixed` without a `commit`, a missing resolution, an
   unknown field. A file that fails the check is never posted.

4. **Push the commit.** The tracker's maintainer runs `issues post`, which refuses a `fixed`
   entry whose commit is not on your repository's remote, comments and closes the issue, and
   pulls again, so the entry leaves your file.

An entry as `pull` writes it, and after a fix:

```yaml
- issue: 7
  title: Typo
  form: Content issue
  kind: Typo or grammar
  location: Getting Started / Types / The Type of a Term / Checking a Type
  url: https://github.com/klavins/polya-issues/issues/7
  filed: '2026-10-19'
  labels:
  - content
  - triage
  body: |-
    **What it currently says**
    On Line 25:
    "-- A Real Numer"

    **What you think it should say**
    It should say:
    "-- A Real Number"
  status: open
  resolution:
```

```yaml
  status: fixed
  commit: 3f2a9c1
  resolution: |
    Thank you. The comment on Checking a Type now reads "A Real Number".
```

An issue that is not yours:

```yaml
  status: to
  repo: polya-topology
  resolution: |
    Set Theory now introduces the image and preimage notation. The first use in General
    Topology could point back to it.
```

## For the tracker's maintainer

This repository also holds `issues`, the tool that carries open issues to the checkouts beside
this one and their resolutions back. From this directory:

| command | what it does | who runs it |
|---|---|---|
| `uv run issues pull` | writes each repository's `reported.yaml` with the open issues routed to it (read-only on GitHub) | anyone |
| `uv run issues check` | validates every `reported.yaml` | anyone |
| `uv run issues status` | one table of every entry across the repositories | anyone |
| `uv run issues post` | comments, relabels and closes on GitHub from the resolutions, one item at a time after showing each | the tracker's maintainer |

An issue is routed by a `repo:<name>` label when it has one, else by the project its form names;
one the tool cannot route is printed by `pull` for you to label. `post` validates every file
before its first GitHub call, refuses a `fixed` whose commit is not on the remote, and removes
`triage` from every issue it acts on. `uv run pytest tests/` runs the tool's tests against
recorded issues and a fake `gh`.
