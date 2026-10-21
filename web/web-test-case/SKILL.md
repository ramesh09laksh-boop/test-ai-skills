---
name: web-test-case
description: Turn a manual web test description (ATF_RTP_WEB_*.xlsx) and its test data (.csv) into a UiPath test case inside the web-test-framework project, using its Object Repository, templates and page-object conventions. Use when asked to create, automate, convert, implement or fix a web banking test case in web-test-framework, when given an ATF_RTP_WEB_* spec or a test-data CSV, or when adding a page, element or Object Repository entry for the web banking app. Not for UiPath Test Manager administration (use uipath-test) and not for RPA process development.
---

# Web test case for web-test-framework

Build one UiPath test case per manual spec, in the existing project, without inventing
activities, selectors, Object Repository IDs or test data.

Read `references/framework-conventions.md` before touching any XAML. The other references
are loaded on demand: `spec-to-testcase.md` (step model), `object-repository.md` (targets),
`uipath-cli.md` (analyze/pack/run), `examples.md` (the two worked samples).

## Critical rules

1. **Never fabricate results.** A test is `Passed`/`Failed` only from a run in this session
   with evidence. Otherwise report `Not executed` plus the reason and the exact command.
2. **No swallowed failures.** Never catch-and-log without rethrowing. Every "erwartetes
   Ergebnis" gets a Verify activity. `Then` is never empty. The project's own Login test
   breaks this rule — do not copy it (`Testcases\ATF_RTP_WEB_Login.xaml`).
3. **Preserve existing work.** Add files and Switch cases. Never rewrite existing workflows,
   project settings, dependency versions, `studioVersion` or `editingStatus`. Propose fixes
   and wait for approval.
4. **No invented activities, Object Repository IDs or selectors.** Only activities from the
   pinned packages. Cite the existing file each pattern was copied from.
5. **No invented test data.** Fill gaps by asking. Secrets (token, password) come from the
   PHI Vault or config through `Utilities\GetFrontendCredentials.xaml` — never from a CSV,
   config file or XAML.
6. **Synchronise on state,** via Check App State or the activity's own wait options — never
   a fixed `Delay`.
7. **German domain terms stay as written in the spec** (step texts, alert texts). Code
   identifiers follow the existing naming.

## Workflow

### 1. Inspect the project (read-only)

Read `project.json` (dependencies, `fileInfoCollection`, `outputType`), `.templates\`,
`.objects\`, `Applications\WebApp\{Actions,Navigation,Pages,Validation}`, `Framework\`,
`Utilities\` and `Testcases\`. List which page/element workflows exist and which are
`Placeholder` stubs. Most of them are stubs — see `references/framework-conventions.md`.

### 2. Pair the inputs

Test case name = the xlsx file name without extension, used verbatim. The CSV name does
**not** follow from it (`...AuslandischeIBANWahrung...` pairs with
`...auslaendische_IBAN_Waehrung...`). Take the pairing from the user or a documented
mapping file. If it is ambiguous, ask. Never guess.

### 3. Parse

```
python scripts/parse_spec.py --xlsx <spec.xlsx> --csv <data.csv>
```

Emits steps, placeholders, CSV columns, rows (secrets masked), conditional steps, steps
with expected results, and a `mapping[]` with one status per placeholder:
`mapped` / `candidate` / `ambiguous` / `missing` / `generated` / `secret` / `unused_column`,
plus `split_required` and `needs_confirmation`.

Self-test: `python scripts/test_parse_spec.py --samples <dir with the two samples>`.

### 4. Gap gate — STOP

If `gap_gate.clear` is false, present the mapping as a table and ask. Do not implement data
entry for an unconfirmed placeholder. The parser only auto-maps on an exact normalised name
match; everything else is a `candidate` a human must confirm. Also raise sample values that
look wrong for their field (e.g. a country where a city is expected).

### 5. Scenario

Write the Gherkin Given/When/Then as the test case annotation so the business reads the same
steps the robot runs.

- **Given** — config, session/login (supplied by the execution template) and the start page.
- **When** — the action steps, in spec order, each logged with its step number.
- **Then** — every expected result as an assertion.

Intermediate expected results are asserted where they occur, not only at the end.

### 6. Map steps to framework calls

Reuse `Actions\*` dispatchers and `Pages\<Page>\*` element workflows.

- New page → create `Pages\<Page>\` with `Click_<Page>_Element.xaml`,
  `SetText_<Page>_Element.xaml`, `Validate_<Page>_Element.xaml` following the LoginPage
  pattern exactly, and add the `in_Page` case to every dispatcher that needs it.
- New element → a Switch case plus an Object Repository target.
- Implement a `Placeholder` stub **only when a test needs it**, following the conventions,
  and list each one you implemented in the report.

### 7. Conditional steps

For "Wenn … erscheint, dann …": Check App State with a short timeout from config, a distinct
path per branch, and a log line saying which branch ran. Where the spec gives an expected
result for a conditional path, assert it there.

### 8. Generated values

For `<REFERENZE-NR>`: generate a unique random keyword, log it, hold it in a variable, and
assert on it in the final check. Never hard-code it.

### 9. Test data binding

Follow the project's existing mechanism. At the time of writing the project has **none** —
no data variations and no CSV reader. Propose one approach (data-driven test case with the
CSV as a data variation, or reading the CSV in `Given`) and **wait for approval**. Keep the
original CSV column names and do the mapping in exactly one place.

### 10. Register the test case

Add an entry to `designOptions.fileInfoCollection` in `project.json` copying the existing
shape exactly: `editingStatus: "InProgress"`, a new `testCaseId` GUID, `testCaseType:
"TestCase"`, `executionTemplatePath`, `executionTemplateType: "Local"`,
`executionTemplateInvokeIsolated: false`, `fileName: "Testcases\\<Name>.xaml"`.

### 11. Validate

Check the XAML is well-formed, arguments are bound, and every `Reference` resolves to an
`Id` in `.objects\`. Then run the CLI — see `references/uipath-cli.md` for verified
commands, the known-noisy baseline and what the TAU rule set needs.

### 12. Run and report

Use `assets/report-template.md`. Report what actually happened, nothing more.

## Definition of done

- Test case named exactly as the xlsx, in `Testcases\`, registered in `fileInfoCollection`.
- Every step implemented, or listed as blocked with the reason.
- Every expected result has an assertion, including intermediate ones.
- Data mapping complete, or its gaps confirmed by the user. No secrets in any file.
- New elements reuse Object Repository descriptors or are listed as "needs capture".
- Stubs implemented are listed. Existing files unchanged unless the user approved it.
- Analyzer and pack results are real CLI output. Run status is evidenced, or recorded as
  `Not executed` with the reason and the command.
