# Workflow: the spec changed — update an existing test case

> **Derived, not dictated.** The spec for this workflow did not arrive; the Inputs, Steps,
> Done-when and Never below are derived from prompt 8 in `PROMPTS.md` and the skill's critical
> rules. Correct it when the full spec arrives.

Compares a changed spec with the test case already implemented from it, shows the
differences, and updates only what changed — after confirmation.

## Inputs

- The **changed spec file** (`<spec folder>\<TestCaseName>.xlsx`).
- The **existing** `Testcases\<TestCaseName>.xaml`. If there is none, this is not an update:
  run the normal implementation workflow.
- The test data file, if the data changed too.

## Steps

### a. Re-parse the spec

```
python scripts/parse_spec.py --xlsx <changed spec.xlsx> --csv <data.csv>
```

In batch mode an already-implemented spec is skipped, so pass `--regenerate` when you want
the whole folder re-analysed.

### b. Diff the new spec against what is implemented

Read the existing XAML and compare, per step:

| Change | What to look for |
|---|---|
| step added | a new number, or an insertion that renumbered the ones after it |
| step removed | an implemented step with no counterpart in the new spec |
| step reworded | same number, different `action` text — may or may not change behaviour |
| expected result added | a step that now has a "zu prüfendes erwartetes Ergebnis" and no assertion yet |
| expected result removed | an assertion with no counterpart — **ask, do not delete** |
| placeholder added | a new `<PLACEHOLDER>` → it goes through the gap gate |
| placeholder removed | data entry that is now dead |
| conditional changed | a branch added, removed, or its "ansonsten" arm changed |

**Renumbering is the trap.** Match steps by their text and intent first, then by number;
a step that moved from 7 to 8 is not a new step plus a deletion. Say which pairing you used.

### c. Show the difference table and the consequences

| # old | # new | Change | Implemented as | Action needed |
|---|---|---|---|---|

Then state the consequences before touching anything:

- new placeholders → run the **gap gate** on them and stop if it is not clear,
- new UI elements → the **capture list**, and the test case is not runnable until they exist,
- new expected results → the assertions that will be added,
- removed expected results → **ask**; a disappearing assertion is a decision for a human.

**Stop here and wait for confirmation.**

### d. Update only the affected activities

- Change only the activities the diff named. Everything else in the file stays byte-identical.
- Update the Gherkin annotation to match the new steps.
- Keep the step numbering in log messages aligned with the **new** spec.
- `fileName` and the test case name do not change unless the spec file was renamed — if it
  was, that is a new test case name, so say so and ask before creating one and orphaning the
  old entry in `fileInfoCollection`.
- Re-run validation and the analyzer, and report the delta against `main`.

## Done when

- The difference table is shown and was confirmed before any edit.
- Every changed or added expected result has an assertion; every removed one was explicitly
  approved for removal.
- New placeholders cleared the gap gate, or the update stopped there.
- Nothing outside the named activities changed, and the report lists what did.

## Never

- **Never regenerate the test case from scratch.** The implemented file holds confirmed
  bindings, captured references and approved decisions that the spec does not contain.
- **Never drop an assertion** because its step text changed. Reworded wording, same
  assertion — unless the user says otherwise.
- **Never renumber or re-indent unrelated steps**, and never reformat the file.
- Never update the test case before the difference table is confirmed.
