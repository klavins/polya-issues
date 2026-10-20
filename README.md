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

## For the maintainer

This repository also holds `issues`, the tool that carries open issues to the checkouts beside
this one and their resolutions back. From this directory:

| command | what it does | who runs it |
|---|---|---|
| `uv run issues pull` | writes each repository's `reported.yaml` with the open issues routed to it (read-only on GitHub) | anyone |
| `uv run issues check` | validates every `reported.yaml` | anyone |
| `uv run issues status` | one table of every entry across the repositories | anyone |
| `uv run issues post` | comments, relabels and closes on GitHub from the resolutions, one item at a time | the maintainer |

An issue is routed by a `repo:<name>` label when it has one, else by the project its form names.
`uv run pytest tests/` runs the tool's tests against recorded issues and a fake `gh`.
