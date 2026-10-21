# Rules for agents working in this repository

These apply to editing the skills here, and the skills themselves repeat the ones that
matter at runtime.

## Source-grounding

- **Every factual claim cites the file it came from.** "Test cases are registered in
  `designOptions.fileInfoCollection` in `project.json`" is fine. "Test cases are usually
  registered in the project file" is not.
- **Verify before you write.** A convention remembered from a previous session, a zip, or a
  summary is a hypothesis. Open the file.
- **Record what you could not verify**, in the skill, where a reader will hit it. A
  reference that silently omits the limits of its own evidence is worse than no reference.
- When reality disagrees with a hand-off, a ticket or an older version of a reference,
  **reality wins** — fix the document and say what changed.

## No invention

- **No invented activities.** Only activities from the versions pinned in the target
  project's `project.json`. If you are unsure an activity exists, look it up
  (`uip rpa-legacy find-activities`).
- **No invented selectors or Object Repository IDs.** An agent cannot capture a UI element.
  Emit a named placeholder and a capture list; never hand-write a `Reference` or paste a
  raw selector.
- **No invented test data.** A missing value is a question for a human, not a gap to fill
  with something plausible.
- **No invented results.** `Passed` and `Failed` require a run in the session that reports
  them, with evidence. Everything else is `Not executed` plus the reason and the command.
- No invented file paths, GUIDs, config keys or package versions.

## Secrets

Tokens, passwords and vault entries come from the credential store the target project
already uses. Never put a secret in a CSV, a config file, a XAML literal, a log line, a
report or this repository. Scripts that print test data mask columns that look secret.

## Changing someone else's project

A skill that edits an existing automation project is a guest in it:

- Add files and add cases. Do not rewrite existing workflows.
- Never touch project settings, dependency versions, `studioVersion` or `editingStatus`.
- Known defects in the target project get **proposed** fixes, not silent ones — including
  defects that make your own work harder.
- Dry runs happen on a scratch branch that is discarded.

## Writing a skill

- `SKILL.md` is always in context: keep it short and imperative. Long material goes to
  `references/`, loaded on demand.
- The `description` is the trigger. Say what fires it *and* what should not — especially
  neighbouring skills it could be confused with.
- Anything deterministic belongs in `scripts/`, with a test that runs against real sample
  inputs and is checked in next to it.
- A script that guesses is worse than one that refuses. Prefer "candidate, confirm this"
  over a silent best match.
- Stop gates are features. If a skill must pause for a human, say so in the step itself,
  not only in a rules section.
