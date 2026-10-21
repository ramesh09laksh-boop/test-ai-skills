# web-test-framework conventions

Every statement below was verified against the `feature/Initial_Work` branch and cites the
file it came from. Re-verify against the branch you are working on before relying on it.

## Project

`project.json`:

| Field | Value |
|---|---|
| `name` | `web-test-framework` |
| `designOptions.outputType` | `Tests` |
| `targetFramework` | `Windows` |
| `expressionLanguage` | `VisualBasic` |
| `designOptions.modernBehavior` | `true` |
| `studioVersion` | `21.4.4.0` |
| `schemaVersion` | `4.0` |

Pinned dependencies — use activities from these and nothing else:

```
UiPath.Testing.Activities      [23.10.1]
UiPath.UIAutomation.Activities [24.10.17]
UiPath.System.Activities       [24.10.8]
UiPath.Excel.Activities        [2.22.3]
GlobaleWorkflow                [26.8.6.21061]   internal; provides Swisscom.PHI / Get_PHI_Vault
```

Known inconsistencies — **report, do not change**:

- `studioVersion` `21.4.4.0` against 24.10 activity packages, while the Object Repository
  metadata was written by `UiPath.Platform 24.11.1.0` (`.objects\**\.metadata`).
- `description` and `README.md` both say "Library-Projekt" although `outputType` is `Tests`.
- `coverageMergeWorkflowPath: "CoverageMerge466635.xaml"` points at a file that is not in
  the repo.
- `projectProfile: "Developement"` (typo, Studio's own).

`.gitignore` excludes `**/.settings`, `**/.local`, `**/.screenshots`,
`**/.ExceptionScreenshots`, `**/.images`. A fresh clone therefore has **no Object Repository
screenshots** — a missing `imageRef` image is not an error.

## Folder structure

```
Testcases\                 ATF_RTP_WEB_<Name>.xaml
.templates\                TestCaseTemplate, ExecutionTemplate, LoginExecutionTemplate
.objects\                  Object Repository (see object-repository.md)
Applications\WebApp\
  Actions\                 ClickElement, SetText, SelectDropdown, SetCheckbox, SetRadioButton
  Navigation\              OpenBrowser, NavigateToPage, RefreshPage, SwitchTab
  Pages\<Page>\            Click_/SetText_/Validate_<Page>_Element.xaml, <Page>Steps.xaml
  Validation\              ValidateElement, ValidateText, ValidateTable, WaitForElement
Framework\                 InitConfig, EnsureSession, HandleException
Utilities\                 GetFrontendCredentials, LogMessage, RetryAction, TakeScreenshot,
                           WaitForLoader
Main.xaml                  comment only; exists to avoid compilation complaints
```

## Page-object dispatch

Two levels of `Switch`. Copy this shape exactly for a new page.

1. `Applications\WebApp\Actions\ClickElement.xaml` — args `in_Page`, `in_Element`,
   `io_Browser`. A `Switch` on `[in_Page]` with one `InvokeWorkflowFile` per page
   (currently only the `LoginPage` case).
2. `Applications\WebApp\Pages\LoginPage\Click_LoginPage_Element.xaml` — arg `in_Element`,
   `io_Browser`. An `NApplicationCard` (`AttachMode="ByInstance"`, `OpenMode="Never"`,
   `InUiElement="[io_Browser]"`) wrapping a `Switch` on `[in_Element]`, one modern activity
   per case with an Object Repository `Reference` on its target.

`Applications\WebApp\Validation\ValidateElement.xaml` is the same pattern plus step
counting: it increments `io_StepCounter`, invokes `Utilities\LogMessage.xaml`, then
switches on `[in_Page]` to `Validate_<Page>_Element.xaml`.

`Validate_LoginPage_Element.xaml` shows the per-element validation shape: `NCheckState`
("Check App State") per element writing a Boolean, then
`If [not isLoginPageElementVisible] → Throw new BusinessRuleException(...)`.

## Arguments and logging

- Prefixes `in_`, `out_`, `io_`. **Exception to be aware of, not copied:**
  `Utilities\GetFrontendCredentials.xaml` declares `in_Username` and `in_Password` as
  `OutArgument`. Call it with that signature; do not imitate the naming.
- `Utilities\LogMessage.xaml` — `in_Message`, `in_LogLevel`, `in_StepNumber`. It formats
  `[timestamp] [Step n] [level] message` and always logs at `Info` regardless of
  `in_LogLevel`; its body still ends in a `Placeholder` comment.
- `io_StepCounter` (`Int32`) is threaded through the test case and incremented by the
  workflow that performs a step (`OpenBrowser.xaml`, `ValidateElement.xaml`).

## Config

`Framework\InitConfig.xaml` — `in_Mandant`, `in_Environment` → `out_Config` (`JObject`).
Reads a `config.json` from a network share (path hard-coded in the Read Text File activity),
deserialises it, and walks `mandant[] → name` then `environments[] → name`, assigning the
matching environment entry to `out_Config`. If neither is found it throws a
`BusinessRuleException`.

A comment in the file states Mandant and Environment are hard-coded as argument defaults
(`VAB` / `TST`) and belong in Orchestrator job arguments.

Config keys used in the project: `homepage` (`Framework\EnsureSession.xaml`), `Kontoname`
(`Utilities\GetFrontendCredentials.xaml`), `url` (`Testcases\ATF_RTP_WEB_Login.xaml`).
Read key names from the code; do not invent new ones without asking.

## Session and credentials

`Framework\EnsureSession.xaml` — `in_Config` → `io_Browser`. An `NApplicationCard` with
`OpenMode="Never"` targeting the `HomePage` repository screen, i.e. it **attaches to an
already-running browser**; it never opens one. On failure it logs "User not logged in" and
throws `new Exception("Unable to ensure session")`.

`Utilities\GetFrontendCredentials.xaml` — a single `Get_PHI_Vault` activity with
`ObjectName="[in_Config("Kontoname").ToString]"`. This is the only sanctioned source of
credentials.

## Templates

`.templates\TestCaseTemplate.xaml` is an **empty Sequence**. The Given/When/Then skeleton
comes from `Testcases\ATF_RTP_WEB_Login.xaml`, not from the template: a root `Sequence` with
three child sequences named `... Given`, `... When`, `... Then`. Use the Login test's
skeleton and propose updating the template.

`.templates\ExecutionTemplate.xaml` — args `in_Config` (`JObject`), `io_Browser`
(`UiElement`). Runs, in order:

1. `Framework\InitConfig.xaml` inside a `TryCatch` catching **only** `BusinessRuleException`
   and only invoking `HandleException`.
2. `Framework\EnsureSession.xaml` — displayed as "CheckSession".
3. the test case `Placeholder`.

`.templates\LoginExecutionTemplate.xaml` — args `in_Config`, `in_Username`, `in_Password`
(`SecureString`). Same `InitConfig` TryCatch, then `GetFrontendCredentials`, then the
placeholder. It does not open a browser; `ATF_RTP_WEB_Login` does that itself.

**Consequence:** a test case on `ExecutionTemplate` needs a browser that is already open and
logged in, normally because `ATF_RTP_WEB_Login` ran earlier in the same robot session. That
is an ordering dependency between test cases — raise it before designing a new test case.

**Consequence:** `InitConfig` is invoked with `in_Mandant` and `in_Environment` unset, so the
defaults apply. If the entry is not found it throws `BusinessRuleException`, the template
logs it and continues with a **null config**, and the real failure surfaces later as an
unrelated `NullReferenceException` (e.g. at `in_Config("Kontoname")`).

## Test case registration

`designOptions.fileInfoCollection` holds one entry per test case and per template:

```json
{
  "editingStatus": "InProgress",
  "testCaseId": "<new GUID>",
  "executionTemplatePath": ".templates\\ExecutionTemplate.xaml",
  "testCaseType": "TestCase",
  "executionTemplateType": "Local",
  "executionTemplateInvokeIsolated": false,
  "fileName": "Testcases\\ATF_RTP_WEB_<Name>.xaml"
}
```

Templates are registered as `{"templateType": "TestCase"|"ExecutionTemplate", "fileName": ...}`.
`Main.xaml` is also registered as a test case (`testCaseId` set, no execution template)
although its body is only a comment.

`ATF_RTP_WEB_Login.xaml` uses `LoginExecutionTemplate`; `ATF_RTP_WEB_Test1.xaml` uses
`ExecutionTemplate` and is an empty Sequence.

## Placeholder stubs

These files contain only a `Comment` with the text `Placeholder` and, except where noted,
**no arguments at all**:

```
Applications\WebApp\Actions\SetText.xaml           SelectDropdown.xaml
Applications\WebApp\Actions\SetCheckbox.xaml       SetRadioButton.xaml
Applications\WebApp\Navigation\NavigateToPage.xaml RefreshPage.xaml  SwitchTab.xaml
Applications\WebApp\Validation\ValidateText.xaml   ValidateTable.xaml  WaitForElement.xaml
Applications\WebApp\Pages\LoginPage\SetText_LoginPage_Element.xaml   Logout.xaml
Utilities\RetryAction.xaml  TakeScreenshot.xaml  WaitForLoader.xaml
```

Partial stubs:

- `Applications\WebApp\Navigation\OpenBrowser.xaml` — real arguments and a real
  `NApplicationCard` (`OpenMode="Always"`, `WindowResize="Maximize"`) on the `LoginPage`
  repository screen, but the card's `Do` body is only a `Placeholder` comment.
- `Framework\HandleException.xaml` — logs the **literal string** `"Some error happened"` at
  `Error`. It never logs `in_Exception` and never rethrows.
- `Utilities\LogMessage.xaml` — works, but ends in a `Placeholder` comment.
- `Testcases\ATF_RTP_WEB_Test1.xaml` — empty Sequence.

Implement a stub only when the test case you are building needs it, keep the change minimal,
and list it in the report.

## Defects you must not copy

1. **Exceptions are swallowed.** In `ATF_RTP_WEB_Login.xaml` the whole `When` body sits in a
   `TryCatch` whose `Catch(System.Exception)` only invokes `HandleException`. A failing step
   therefore produces a **passing** test. Nothing in the project rethrows after
   `HandleException`.
2. **No assertions.** `ATF_RTP_WEB_Login.xaml`'s `... Given` and `... Then` sequences are
   both empty.
3. **Dead invocations.** The last two `InvokeWorkflowFile` calls in that test pass empty
   `in_Page` and `in_Element`.
4. **Display names lie about paths.** e.g. `"OpenBrowser - Invoke Workflow File
   (Framework\Navigation\OpenBrowser.xaml)"` while `WorkflowFileName` is
   `Applications\WebApp\Navigation\OpenBrowser.xaml`; `"CheckSession ...
   (Framework\CheckSession.xaml)"` invokes `Framework\EnsureSession.xaml`;
   `"LoginSteps ... (Pages\LoginPage\LoginFlow.xaml)"` invokes `LoginSteps.xaml`.
5. **`x:Class` does not match the file name** — `ATF_RTP_WEB_Login.xaml` declares
   `x:Class="ATF_RTP_WEB_IB_Login"`.
6. **Login cannot actually log in.** `LoginSteps.xaml` invokes the `SetText` stub with an
   empty argument dictionary, and the SubmitButton target is broken
   (see `object-repository.md`).
7. **Templates continue after a config failure** instead of rethrowing (see above).

In your own test cases: rethrow after `HandleException`, or do not catch in `When`/`Then` at
all; put real Verify activities in `Then`. Propose fixes to the Login test to the user
instead of editing it.
