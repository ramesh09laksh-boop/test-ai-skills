---
name: web-test-case
description: Turn manual web test descriptions (.xlsx) and their test data (.csv) from a spec folder and a data folder into UiPath test cases inside the web-test-framework project, using the project's own Object Repository, templates and page-object conventions as they are on this run. Use when asked to create, automate, convert, implement or fix a web banking test case in web-test-framework, when given an ATF_RTP_WEB_* spec or a test-data CSV, or when adding a page, element or Object Repository entry for the web banking app. Not for UiPath Test Manager administration (use uipath-test) and not for RPA process development.
---

# Web test case for web-test-framework

Build one UiPath test case per manual spec, in the existing project, without inventing
activities, selectors, Object Repository IDs or test data.

Read `references/framework-conventions.md` before touching any XAML. The other references
load on demand: `spec-to-testcase.md` (inputs, pairing, step model), `object-repository.md`
(targets), `uipath-cli.md` (analyze/pack/run), `examples.md` (two worked samples),
`known-state-2026-10-21.md` (a **dated snapshot** of one past run — re-check it, never assume
it).

## Discover the project; do not hard-code it

The project keeps changing: new pages, actions, utilities, templates and config keys.

1. **Read the current project on every run** and follow whatever structure Studio and the
   team have produced. No reference here lists which pages, elements, stubs or config keys
   exist — that goes in *this run's* inspection output.
2. **Preserve the structure exactly as generated.** Keep the folder layout, file and argument
   naming, the `project.json` layout, `.objects\` and `.templates\`. Add new files where the
   existing pattern puts them. Never reorganise, rename, reformat or regenerate an existing
   file.
3. **Reuse what the framework provides** — config through `Framework\InitConfig.xaml`, the
   session through `EnsureSession`, credentials through `GetFrontendCredentials`, logging
   through `Utilities\LogMessage`, UI interaction through the `Actions\*` dispatchers and the
   `Pages\<Page>\*` element workflows. Add only what the framework does not have yet, built
   the same way as the existing pieces. If the framework already offers a way to do
   something, use it — never write your own version alongside.

## Fixed conventions

| Item | Convention |
|---|---|
| Config | `Config\config.json`, relative to the project root. Read it through `InitConfig`, never directly in a test case. Look up keys **by name in the file**; do not assume them |
| Test cases | `Testcases\<TestCaseName>.xaml`, where `<TestCaseName>` is the spec file name without its extension, verbatim. Register each in `project.json` like the existing entries |
| Structure source | The project as it is in the repo on this run |

## Critical rules

1. **Never fabricate results.** A test is `Passed`/`Failed` only from a run in this session
   with evidence. Otherwise report `Not executed` plus the reason and the exact command.
2. **No swallowed failures.** Never catch-and-log without rethrowing. Every "erwartetes
   Ergebnis" gets a Verify activity. `Then` is never empty. Where an existing test breaks
   this rule, do not copy it — propose the fix.
3. **Preserve existing work.** Add files and Switch cases. Propose fixes to existing
   workflows, project settings, dependency versions, `studioVersion` or `editingStatus` and
   wait for approval.
4. **No invented activities, Object Repository IDs or selectors.** Only activities from the
   packages pinned in the project's own `project.json`. Cite the existing file each pattern
   was copied from.
5. **No invented test data.** Fill gaps by asking. Secrets come from the PHI Vault or config
   through `Utilities\GetFrontendCredentials.xaml` — never from a CSV, config file or XAML.
6. **Synchronise on state,** via Check App State or the activity's own wait options — never a
   fixed `Delay`.
7. **German domain terms stay as written in the spec** (step texts, alert texts). Code
   identifiers follow the existing naming.
8. **The user's input files are read-only.** Never modify, move or rename an xlsx or CSV.

## Workflow

### 1. Get the input folders

Two arguments: the **spec folder** (the `.xlsx` manual steps) and the **data folder** (the
`.csv` test data). They may be the same folder. **If the user does not name them, ask. Do
not search the disk.**

### 2. Inspect the project (read-only)

Read `project.json` (dependencies, `fileInfoCollection`, `outputType`), `Config\`,
`.templates\`, `.objects\`, `Applications\WebApp\{Actions,Navigation,Pages,Validation}`,
`Framework\`, `Utilities\` and `Testcases\`. Record in the report which page/element
workflows exist, which `in_Page`/`in_Element` cases each dispatcher has, which files are
still `Placeholder` stubs, and which Screens/Elements the Object Repository actually holds.

**Config path check — every run.** Find which path the Read Text File activity in
`Framework\InitConfig.xaml` holds:

```powershell
Select-String -Path "<project>\Framework\InitConfig.xaml" -Pattern 'config\.json'
```

- It reads `Config\config.json` or the project-relative equivalent → proceed.
- It reads a UNC share or another absolute path → **report the mismatch and propose the
  change.** Do not edit `InitConfig.xaml` without approval.
- `Config\config.json` does not exist → **stop and report.**

Never print a config value that could be secret. Listing key names is fine.

### 3. Scan and pair the inputs

```
python scripts/parse_spec.py --spec-dir <spec folder> --data-dir <data folder> \
       --testcases-dir <project>/Testcases --out-dir <scratch dir>
```

Lists every `.xlsx` and every `.csv`, skipping and reporting lock files (`~$*.xlsx`) and
specs already implemented in `Testcases\` (`--regenerate` to include them). Pairing has three
outcomes and no fallback: `exact` base-name match → paired automatically; normalised match →
**`candidate`, confirm with the user**; anything else → `unpaired` and reported. **Never pair
by similarity scoring alone.**

Present the **batch table**: spec file, data file, pairing status, test case name, whether it
already exists in `Testcases\`, gap-gate status. Then take each test case through steps 4–12.
**One blocked test case does not stop the others.**

Self-test: `python scripts/test_parse_spec.py --samples <dir with the two samples>` — covers
single-pair and batch mode.

### 4. Parse

```
python scripts/parse_spec.py --xlsx <spec.xlsx> --csv <data.csv>
```

Emits steps, placeholders, CSV columns, rows (secrets masked), conditional steps, steps with
expected results, and a `mapping[]` with one status per placeholder: `mapped` / `candidate` /
`ambiguous` / `missing` / `generated` / `secret` / `unused_column`, plus `split_required` and
`needs_confirmation`.

### 5. Gap gate — STOP

If `gap_gate.clear` is false, present the mapping as a table and ask. Do not implement data
entry for an unconfirmed placeholder. The parser only auto-maps on an exact normalised name
match; everything else is a `candidate` a human must confirm. Also raise sample values that
look wrong for their field (e.g. a country where a city is expected).

### 6. Scenario

Write the Gherkin Given/When/Then as the test case annotation so the business reads the same
steps the robot runs.

- **Given** — config, session/login (supplied by the execution template) and the start page.
- **When** — the action steps, in spec order, each logged with its step number.
- **Then** — every expected result as an assertion.

Intermediate expected results are asserted where they occur, not only at the end.

### 7. Map steps to framework calls

Reuse the `Actions\*` dispatchers and the `Pages\<Page>\*` element workflows that exist.

- New page → create `Pages\<Page>\` with the element workflows the test needs, following an
  existing page's files exactly, and add the `in_Page` case to every dispatcher that needs it.
- New element → a Switch case plus an Object Repository target.
- Implement a `Placeholder` stub **only when a test needs it**, following the conventions, and
  list each one you implemented in the report.

### 8. Conditional steps

For "Wenn … erscheint, dann …": Check App State with a short timeout from config, a distinct
path per branch, and a log line saying which branch ran. Where the spec gives an expected
result for a conditional path, assert it there.

### 9. Generated values

For `<REFERENZE-NR>`: generate a unique random keyword, log it, hold it in a variable, and
assert on it in the final check. Never hard-code it.

### 10. Test data binding

Check what the project does today. If it has a mechanism, use it. If it has none, propose one
(a data-driven test case with the CSV as a data variation, or reading the CSV in `Given`) and
**wait for approval**. Keep the original CSV column names and do the mapping in exactly one
place.

### 11. Register the test case

Add an entry to `designOptions.fileInfoCollection` in `project.json`, copying the shape of the
existing entries in that file exactly, with `fileName: "Testcases\\<TestCaseName>.xaml"` and a
new `testCaseId` GUID. Change nothing else and keep the file's formatting.

### 12. Validate

Check the XAML is well-formed, arguments are bound, and every `Reference` resolves to an `Id`
in `.objects\`. Then run the CLI — see `references/uipath-cli.md`. Take your own baseline from
the unmodified project and report the delta; say which rule set you used.

### 13. Run and report

Use `assets/report-template.md`. Report what actually happened, nothing more.

## Definition of done

- Test case named exactly as the xlsx, in `Testcases\`, registered in `fileInfoCollection`.
- The batch table reported, with every spec and every CSV accounted for — paired, candidate,
  unpaired or skipped with the reason.
- Config-path status reported, and `Config\config.json` confirmed to exist.
- Every step implemented, or listed as blocked with the reason.
- Every expected result has an assertion, including intermediate ones.
- Data mapping complete, or its gaps confirmed by the user. No secrets in any file.
- New elements reuse Object Repository descriptors or are listed as "needs capture".
- Stubs implemented are listed. Existing files unchanged unless the user approved it.
- Input xlsx and CSV files unchanged.
- Analyzer and pack results are real CLI output. Run status is evidenced, or recorded as
  `Not executed` with the reason and the command.
