# web-test-framework conventions

**Patterns, not an inventory.** This file describes how the project is built and cites the
file each pattern was read from. It does **not** list which pages, elements, stubs or config
keys exist — that changes every time Studio or the team touches the project, so it belongs in
the run's own inspection output. A dated snapshot of one past run is in
`known-state-2026-10-21.md`, clearly marked as a snapshot; re-check every item in it.

Read the project on **every** run. Follow whatever structure you find.

## Fixed conventions

These three do not change with the project and may be relied on:

| Item | Convention |
|---|---|
| Config | `Config\config.json`, relative to the project root. Read it through `Framework\InitConfig.xaml`, never directly in a test case. Look up keys **by name in the file**; do not assume a key exists |
| Test cases | `Testcases\<TestCaseName>.xaml`, where `<TestCaseName>` is the spec file name without its extension, verbatim. Register each one in `project.json` the same way the existing entries are registered |
| Structure source | The project as it is in the repo on this run |

## Preserve the structure exactly as generated

Studio generated this layout; the team extended it. Keep both.

- Keep the folder layout, the file names, the argument names, the `project.json` layout,
  `.objects\` and `.templates\`.
- Add new files **where the existing pattern puts them** — a new page goes in
  `Applications\WebApp\Pages\<Page>\`, a new test case in `Testcases\`.
- **Never** reorganise, rename, reformat or regenerate an existing file. Not to tidy it up,
  not to make your own work easier. Propose, and wait.
- Do not touch project settings, dependency versions, `studioVersion` or `editingStatus`.

## Reuse what the framework provides

| Need | Use |
|---|---|
| Configuration | `Framework\InitConfig.xaml` |
| Browser session | `Framework\EnsureSession.xaml` |
| Credentials / secrets | `Utilities\GetFrontendCredentials.xaml` |
| Logging | `Utilities\LogMessage.xaml` |
| UI interaction | the `Applications\WebApp\Actions\*` dispatchers and the `Applications\WebApp\Pages\<Page>\*` element workflows |
| Validation | `Applications\WebApp\Validation\*` |

If the framework already offers a way to do something, **use it**. Do not write a second
version alongside it — no inline config read, no inline selector, no local credential
lookup, no `Delay` instead of a state check. Add only the pieces the framework does not have
yet (a page folder, an element case, a dispatcher case, a stub a test actually needs), and
build them the same way the existing ones are built.

Activities come only from the packages pinned in the project's own `project.json`. If you
are unsure an activity exists, look it up (`uip rpa-legacy find-activities`).

## Inspecting the project (do this first, every run)

Read, in this order, and write what you found into the report:

1. `project.json` — `designOptions.outputType`, `targetFramework`, `expressionLanguage`,
   the pinned `dependencies`, and `designOptions.fileInfoCollection` (the registration
   pattern and the existing entries).
2. `Config\config.json` — does it exist, and which **key names** does it hold.
3. `Framework\InitConfig.xaml` — which path does it actually read (see below).
4. `.templates\` — which templates exist and what each one runs, in order.
5. `.objects\` — Library / App / AppVersion / Screens / Elements actually present.
6. `Applications\WebApp\{Actions,Navigation,Pages,Validation}` — which workflows exist,
   which `in_Page` / `in_Element` cases each dispatcher has, and which files are still
   `Placeholder` stubs.
7. `Framework\`, `Utilities\`, `Testcases\`.

### Config path check — run it every time

`Framework\InitConfig.xaml` reads the config file with a Read Text File activity whose path
is a literal in the XAML. Check which path that is:

```powershell
Select-String -Path "<project>\Framework\InitConfig.xaml" -Pattern 'config\.json'
```

- It reads `Config\config.json`, or the project-relative equivalent → **proceed**.
- It reads a UNC share or any other absolute path → **report the mismatch and propose the
  change.** Do not edit `InitConfig.xaml` without approval.
- `Config\config.json` does not exist → **stop and report.**

Never print a config value that could be secret. Listing key names is fine.

## Page-object dispatch pattern

Two levels of `Switch`. Copy the shape from whichever page already exists in the project you
are in — read it, do not copy it from here.

1. **Dispatcher**, e.g. `Applications\WebApp\Actions\ClickElement.xaml` — arguments
   `in_Page`, `in_Element`, `io_Browser`; a `Switch` on `[in_Page]` with one
   `InvokeWorkflowFile` per page.
2. **Element workflow**, e.g. `Applications\WebApp\Pages\<Page>\Click_<Page>_Element.xaml` —
   arguments `in_Element`, `io_Browser`; an `NApplicationCard` (`AttachMode="ByInstance"`,
   `OpenMode="Never"`, `InUiElement="[io_Browser]"`) wrapping a `Switch` on `[in_Element]`,
   one modern activity per case, each with an Object Repository `Reference` on its target.

A validation dispatcher follows the same pattern plus step counting: it increments
`io_StepCounter`, invokes `Utilities\LogMessage.xaml`, then switches on `[in_Page]`
(pattern read from `Applications\WebApp\Validation\ValidateElement.xaml`).

Per-element validation shape (read from
`Applications\WebApp\Pages\LoginPage\Validate_LoginPage_Element.xaml`): one `NCheckState`
("Check App State") per element writing a Boolean, then
`If [not <...>IsVisible] → Throw new BusinessRuleException(...)`.

**Adding a page:** create `Applications\WebApp\Pages\<Page>\` with the
`Click_`/`SetText_`/`Validate_<Page>_Element.xaml` files the test needs, following the
existing page's files exactly, and add the `in_Page` case to every dispatcher that needs it.
**Adding an element:** a Switch case in the element workflow plus an Object Repository
target — see `object-repository.md`.

## Arguments and logging

- Prefixes `in_`, `out_`, `io_`. Where an existing file breaks that (an `OutArgument` named
  `in_*`), call it with the signature it has and do not imitate the naming — note it in the
  report.
- `Utilities\LogMessage.xaml` takes `in_Message`, `in_LogLevel`, `in_StepNumber` and formats
  `[timestamp] [Step n] [level] message`. Check its current behaviour before relying on the
  level being honoured.
- `io_StepCounter` (`Int32`) is threaded through the test case and incremented by the
  workflow that performs a step.

## Config, session and credentials

`Framework\InitConfig.xaml` — `in_Mandant`, `in_Environment` → `out_Config` (`JObject`).
It reads the config file, deserialises it, and walks `mandant[] → name` then
`environments[] → name`, assigning the matching environment entry to `out_Config`; if neither
is found it throws a `BusinessRuleException`. Mandant and Environment are hard-coded as
argument defaults and, per a comment in the file, belong in Orchestrator job arguments.

`Framework\EnsureSession.xaml` — `in_Config` → `io_Browser`. An `NApplicationCard` with
`OpenMode="Never"`, i.e. it **attaches to an already-running browser**; it never opens one.

`Utilities\GetFrontendCredentials.xaml` — a `Get_PHI_Vault` activity keyed on a config value.
This is the only sanctioned source of credentials.

Config keys: read the names out of the code and out of `Config\config.json`. Do not invent a
key, and do not assume a key seen in an earlier run still exists.

## Templates

Read `.templates\` on your run: which templates exist, what each runs and in what order, and
which arguments each declares. Then pick the one the test case needs and register it in
`fileInfoCollection`.

Two consequences that have held so far and are worth re-checking:

- A template whose session step only **attaches** to a browser needs one that is already open
  and logged in — normally because a login test ran earlier in the same robot session. That
  is an ordering dependency between test cases; raise it before designing a new test case.
- A template that catches the config failure without rethrowing continues with a null config,
  and the real failure surfaces later as an unrelated `NullReferenceException`.

If `.templates\TestCaseTemplate.xaml` is empty, take the Given/When/Then skeleton from an
existing test case instead and **propose** updating the template.

## Test case registration

`designOptions.fileInfoCollection` in `project.json` holds one entry per test case and per
template. Copy the shape of the **existing entries in the file you are editing**; at the time
of the last snapshot a test case entry looked like:

```json
{
  "editingStatus": "InProgress",
  "testCaseId": "<new GUID>",
  "executionTemplatePath": ".templates\\ExecutionTemplate.xaml",
  "testCaseType": "TestCase",
  "executionTemplateType": "Local",
  "executionTemplateInvokeIsolated": false,
  "fileName": "Testcases\\<TestCaseName>.xaml"
}
```

Templates are registered as `{"templateType": "TestCase"|"ExecutionTemplate", "fileName": ...}`.
Add your entry; change nothing else in the file, and keep its existing formatting.

## Rules for your own test cases

1. **Rethrow after the exception handler, or do not catch in `When`/`Then` at all.** A
   catch-and-log turns a failing step into a passing test.
2. **Every "erwartetes Ergebnis" gets a Verify activity.** `Then` is never empty, and
   intermediate expected results are asserted where they occur.
3. **Synchronise on state** — Check App State or an activity's own wait options. Never a
   fixed `Delay`.
4. **German domain terms stay as written in the spec** in display names, log messages and
   assertion messages. Code identifiers follow the existing naming.
5. **No secrets** in a CSV, a config file, a XAML literal, a log line or a report.

Where an existing file breaks one of these, **propose** the fix to the user and leave the
file alone. See `known-state-2026-10-21.md` for the defects found in the last snapshot, and
check whether they are still there.
