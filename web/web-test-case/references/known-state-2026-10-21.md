# Snapshot — web-test-framework as observed on 2026-10-21

> **This is a snapshot, not a specification.** Every line below was true of one working copy
> on one day. The project keeps changing: pages, elements, actions, stubs, templates and
> config keys are added by Studio and by the team.
>
> **Re-check each item in the run you are doing.** Never assume anything on this page still
> holds, and never present it as the current state. If reality disagrees, reality wins —
> update this file with a new dated snapshot or correct this one, and say what changed.
>
> The patterns (how a page folder is built, how a dispatcher switches, how a test case is
> registered) live in `framework-conventions.md` and `object-repository.md`. Only the
> *inventories* are here.

Source: a working copy of `web-test-framework`, branch `feature/Initial_Work`, at
`...\web-test-framework-feature-Initial_Work`. The copy inspected was an export, not a git
clone, so no commit id could be recorded.

## What to re-check, and how

| # | Item | Check |
|---|---|---|
| 1 | Config path in `InitConfig` | which path the Read Text File activity in `Framework\InitConfig.xaml` holds |
| 2 | `Config\config.json` | does the file exist; which **key names** it contains (never print values) |
| 3 | Object Repository | which Screens and Elements exist under `.objects\`; does every `Reference` in a workflow resolve to an `Id` in this project |
| 4 | Stubs | which files still contain only a `Placeholder` comment |
| 5 | Orphans | folders under `.objects\` with no `.metadata`/`.type`/`.content` |
| 6 | Analyzer baseline | run the analyzer on the **unmodified** project first; that run is the baseline, not the table below |
| 7 | Test data binding | whether the project has acquired a data-variation or CSV-reading mechanism |
| 8 | Pages / dispatcher cases | which `in_Page` cases each dispatcher has |

## 1. Config path — mismatch

`Framework\InitConfig.xaml`, the `ReadTextFile` activity (`DisplayName="Read Config Text
File"`):

```
FileName="\\Sb007047\d$\TestDaten\WebApp\config.json"
```

The convention is `Config\config.json` relative to the project root. The project does have
`Config\config.json` (689 bytes, present on 2026-10-21), so the file and the code disagree:
**InitConfig still reads the UNC share.**

Key names found in `Config\config.json` — names only, values deliberately omitted:

```
mandant[].name
mandant[].environments[].name
mandant[].environments[].url
mandant[].environments[].homepage
mandant[].environments[].Kontoname
```

`homepage` and `Kontoname` were present on the first environment entry only; the other
entries carried `name` and `url`. Do not treat that as a schema — read the file.

**Propose** the switch to `Config\config.json`; do not edit `InitConfig.xaml` without
approval.

## 2. project.json

| Field | Value |
|---|---|
| `name` | `web-test-framework` |
| `designOptions.outputType` | `Tests` |
| `targetFramework` | `Windows` |
| `expressionLanguage` | `VisualBasic` |
| `designOptions.modernBehavior` | `true` |
| `studioVersion` | `21.4.4.0` |
| `schemaVersion` | `4.0` |

Dependencies pinned at the time:

```
UiPath.Testing.Activities      [23.10.1]
UiPath.UIAutomation.Activities [24.10.17]
UiPath.System.Activities       [24.10.8]
UiPath.Excel.Activities        [2.22.3]
GlobaleWorkflow                [26.8.6.21061]   internal; provides Swisscom.PHI / Get_PHI_Vault
```

Read the versions out of `project.json` on your run — these are what the activity set is
pinned to, and they move.

Inconsistencies — **report, do not change**:

- `studioVersion` `21.4.4.0` against 24.10 activity packages, while the Object Repository
  metadata was written by `UiPath.Platform 24.11.1.0` (`.objects\**\.metadata`).
- `description` and `README.md` both say "Library-Projekt" although `outputType` is `Tests`.
- `coverageMergeWorkflowPath: "CoverageMerge466635.xaml"` points at a file not in the repo.
- `projectProfile: "Developement"` (typo, Studio's own).

## 3. Folders present

```
Config\                    config.json
Testcases\                 ATF_RTP_WEB_Login.xaml, ATF_RTP_WEB_Test1.xaml
.templates\                TestCaseTemplate, ExecutionTemplate, LoginExecutionTemplate
.objects\                  Object Repository
Applications\WebApp\
  Actions\                 ClickElement, SetText, SelectDropdown, SetCheckbox, SetRadioButton
  Navigation\              OpenBrowser, NavigateToPage, RefreshPage, SwitchTab
  Pages\LoginPage\         Click_/SetText_/Validate_LoginPage_Element.xaml, LoginSteps.xaml,
                           Logout.xaml
  Validation\              ValidateElement, ValidateText, ValidateTable, WaitForElement
Framework\                 InitConfig, EnsureSession, HandleException
Utilities\                 GetFrontendCredentials, LogMessage, RetryAction, TakeScreenshot,
                           WaitForLoader
Main.xaml                  comment only; exists to avoid compilation complaints
```

`LoginPage` was the **only** page folder. `ClickElement.xaml` and `ValidateElement.xaml` had
a `LoginPage` case and no other.

`.gitignore` excludes `**/.settings`, `**/.local`, `**/.screenshots`,
`**/.ExceptionScreenshots`, `**/.images`. A fresh clone therefore has **no Object Repository
screenshots** — a missing `imageRef` image is not an error.

## 4. Object Repository inventory

One Library `mP2_Cqto3kuFAHZwckVu6g` (`.objects\.metadata`) → App `WebApp` → AppVersion
`1.0.0` → two Screens:

| Screen | Id | Title | Url | Used by |
|---|---|---|---|---|
| HomePage | `MpbgBJcIUESbqIKBNtn1vA` | New Tab | `[in_Config("homepage").ToString]` | `Framework\EnsureSession.xaml` |
| LoginPage | `WmBf68mm7024QOmNDNuPaA` | Anmeldung | `[url]` (screen variable) | `Applications\WebApp\Navigation\OpenBrowser.xaml` |

**Exactly one Element existed:**

| Element | Id | TaxonomyType | Selector | SearchSteps | ActivityType |
|---|---|---|---|---|---|
| LoginPage / VertragsnummerInput | `b9LIEkiNoEqqYcFyGZmP3g` | Input | `<webctrl id='username' tag='INPUT' />` | `Selector` only | CheckState |

Used by `Applications\WebApp\Pages\LoginPage\Validate_LoginPage_Element.xaml`. Its
`BrowserURL` identifies the application under test as the bank's internet-banking test
environment.

**There were no payment screens or elements** — nothing for the Inland/Ausland payment
links, form fields, dropdowns, buttons, the Währungswechsel or Transaktionssignierung
pop-ups, the alert, or the payment list. Re-check: elements may have been captured since.

### Broken references

`Applications\WebApp\Pages\LoginPage\Click_LoginPage_Element.xaml` points at library
`5gYTkcWkeUikngI2i_8_9w`, which does **not** exist in this project (the project's library is
`mP2_Cqto3kuFAHZwckVu6g`). Two targets affected:

| Target | Reference | Selector it actually holds |
|---|---|---|
| `NApplicationCard.TargetApp` | `5gYTkcWkeUikngI2i_8_9w/pMl-kapR4E6OVDP3rwUmuw` | `<html app='chrome.exe' title='New Tab' />` |
| `NClick` "SubmitButton" | `5gYTkcWkeUikngI2i_8_9w/vwrTa_gBjkGcA6kKCh5B0w` | `<ctrl name='Enhance your search with tabs, files, or an AI tool' role='push button' />` |

Both were captured on Chrome's own New Tab page, not on the bank's login form. The analyzer
also flags the SubmitButton selector (`UI-USG-011`, non-allowed attribute `idx='2'`).

`CancelButton` in the same Switch was `<x:Null x:Key="CancelButton" />` — a case with no
activity in it.

Together with the `SetText` stub called from `LoginSteps.xaml`, **the Login test could not
log in**. Since a test case on `ExecutionTemplate` needs an already-logged-in session, this
was a blocker for every payment test. Re-check it before promising a runnable test.

### Orphaned folder

`.objects\-_zc\WG30\VCbY\` and its three child folders (`8Rat`, `aMW7`, `cP_H`) contained
only `.hash` and `.attributes\SearchHash` — no `.metadata`, `.type` or `.content`. They look
like leftovers of a deleted screen and three deleted elements.

**Report it; do not delete it.** Cleaning it up is a Studio action for the team.

## 5. Placeholder stubs

Files containing only a `Comment` with the text `Placeholder` and, except where noted, no
arguments at all:

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

## 6. Defects not to copy

1. **Exceptions swallowed.** In `ATF_RTP_WEB_Login.xaml` the whole `When` body sits in a
   `TryCatch` whose `Catch(System.Exception)` only invokes `HandleException`. A failing step
   therefore produces a **passing** test. Nothing in the project rethrew after
   `HandleException`.
2. **No assertions.** `ATF_RTP_WEB_Login.xaml`'s `... Given` and `... Then` sequences were
   both empty.
3. **Dead invocations.** The last two `InvokeWorkflowFile` calls in that test passed empty
   `in_Page` and `in_Element`.
4. **Display names lie about paths.** e.g. `"OpenBrowser - Invoke Workflow File
   (Framework\Navigation\OpenBrowser.xaml)"` while `WorkflowFileName` was
   `Applications\WebApp\Navigation\OpenBrowser.xaml`; `"CheckSession ...
   (Framework\CheckSession.xaml)"` invoked `Framework\EnsureSession.xaml`;
   `"LoginSteps ... (Pages\LoginPage\LoginFlow.xaml)"` invoked `LoginSteps.xaml`.
5. **`x:Class` does not match the file name** — `ATF_RTP_WEB_Login.xaml` declared
   `x:Class="ATF_RTP_WEB_IB_Login"`.
6. **Login could not log in** — see the broken references above.
7. **Templates continue after a config failure.** `InitConfig` is invoked inside a `TryCatch`
   catching only `BusinessRuleException` and only invoking `HandleException`, so a missing
   config entry leaves a **null config** and surfaces later as an unrelated
   `NullReferenceException` (e.g. at `in_Config("Kontoname")`).

## 7. Test data binding — none

No data variations in `designOptions.fileInfoCollection`, and no CSV reader anywhere in the
project. Re-check: if a mechanism has appeared since, use it. If not, propose one and wait
for approval.

## 8. CLI baselines

Both baselines are **from this snapshot, on this machine**. Produce your own baseline by
running the same command on the unmodified project before you change anything, and report
the delta against *that*.

Workflow Analyzer, **default** rule set (not TAU) — 91 findings:

| Severity | Code | Count | Rule |
|---|---|---:|---|
| Error | `ST-ANA-009` | 24 | File Activities Stats (a metrics rule, one per file — not a defect) |
| Warning | `ST-MRD-002` | 35 | Activity Name Defaults |
| Warning | `ST-USG-020` | 21 | Minimum Log Messages |
| Warning | `ST-NMG-004` | 4 | Display Name Duplication |
| Warning | `ST-NMG-002` | 2 | Arguments Naming Convention (`io_Browser` vs an `out_*` pattern) |
| Warning | `UI-USG-011` | 1 | Non-allowed attribute `idx='2'` — the broken SubmitButton selector |
| Warning | `ST-SEC-007` | 1 | SecureString argument in `LoginSteps.xaml` |

CI sets `RULECONFIG_TYPE: TAU`. The TAU policy file was not available in this environment,
so the numbers above are not CI-equivalent.

`uip rpa-legacy validate` — exits `1` with **81 findings, all `CLI-TR-0001` TypeResolution
false positives** across all 32 XAML files (32 × `Collection`, 32 × `Dictionary`,
11 × `SecureString`/`System.Exception`, 1 × `Get PHI Vault`). Not usable as a pass/fail gate.

`uip rpa-legacy pack` — **failed** in this environment:

```
Unable to create activity builder for Utilities\GetFrontendCredentials.xaml.
Reason was 'Cannot create unknown type
'{clr-namespace:Swisscom_PHI;assembly=Swisscom.PHI}Get_PHI_Vault'.'
```

The internal `GlobaleWorkflow` dependency could not be restored — the configured feeds were
only `nuget.org` and `C:\ProgramData\UiPath\Packages`. An environment limitation, not a
project defect; do not "fix" it by removing the dependency.
