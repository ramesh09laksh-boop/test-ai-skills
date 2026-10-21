# UiPath CLI

Only commands actually executed and observed are written below. **Re-run the discovery step
in your own environment** — versions and the bundled `uipcli` path change.

## Discovery

```powershell
uip --version                       # 1.202.1
uip rpa-legacy --help               # debug | find-activities | find-package | pack
                                    # type-definition | validate      (NO analyze)
```

`uip rpa-legacy` is a wrapper. Workflow Analyzer is **not** exposed through it; use the
bundled legacy binary:

```powershell
$cli = "$env:USERPROFILE\.uipath\.cache\rpa-legacy-tool\26.4.0.3\legacy-cli\tools\uipcli.exe"
& $cli --version                    # uipcli 26.4.0+7e11f79...
& $cli                              # lists: asset | job | package | run | test
```

Find it rather than hard-coding the version directory:

```powershell
$cli = (Get-ChildItem "$env:USERPROFILE\.uipath\.cache\rpa-legacy-tool" -Recurse `
        -Filter uipcli.exe | Sort-Object FullName -Descending | Select-Object -First 1).FullName
```

## Workflow Analyzer

```powershell
& $cli package analyze "<project>\project.json" `
      --analyzerTraceLevel Warning `
      --resultPath "<project>\analyzer.json" `
      --traceLevel Information
```

Verified on the unmodified project: **exit code 0**, `analyzer.json` written as a JSON
array. `ErrorSeverity` is numeric: `1` Info, `2` Warning, `3` Error.

Baseline on `feature/Initial_Work` with the **default** rule set — 91 findings:

| Severity | Code | Count | Rule |
|---|---|---:|---|
| Error | `ST-ANA-009` | 24 | File Activities Stats (a metrics rule, one per file — not a defect) |
| Warning | `ST-MRD-002` | 35 | Activity Name Defaults |
| Warning | `ST-USG-020` | 21 | Minimum Log Messages |
| Warning | `ST-NMG-004` | 4 | Display Name Duplication |
| Warning | `ST-NMG-002` | 2 | Arguments Naming Convention (`io_Browser` vs an `out_*` pattern) |
| Warning | `UI-USG-011` | 1 | Non-allowed attribute `idx='2'` — the broken SubmitButton selector |
| Warning | `ST-SEC-007` | 1 | SecureString argument in `LoginSteps.xaml` |

Compare your run against this baseline and report the **delta** your change introduces.

Useful flags: `--stopOnRuleViolation`, `--treatWarningsAsErrors`, `--ignoredRules a,b`.

### The TAU rule set

CI sets `RULECONFIG_TYPE: TAU` (`.gitlab-ci.yml`). The CLI takes a rule set through
`--governanceFilePath <policy.json>` (an Automation Ops policy or one exported from Studio).

**The TAU policy file was not available in this environment**, so every analyzer number
above is from the *default* rule set. Before quoting analyzer results as CI-equivalent, get
the TAU policy from Automation Ops or from the `swisscom/uipath-b2b/pipeline/includes`
repository and pass it with `--governanceFilePath`. Say which rule set you used.

## Validate

```powershell
uip rpa-legacy validate "<project>\project.json" --result-path "<project>\validate.json"
```

**Not usable as a pass/fail gate in this environment.** On the unmodified project it exits
`1` with **81 findings, all `CLI-TR-0001` TypeResolution false positives** across all 32
XAML files:

- 32 × `Collection ... 'System.Collections.ObjectModel' (System.Private.CoreLib)`
- 32 × `Dictionary ... 'System.Collections.Generic' (System.Private.CoreLib)`
- 11 × `SecureString` / `System.Exception` namespace resolution
- 1 × `Get PHI Vault` — from the unresolvable internal dependency

Treat the 81-finding baseline as the zero point and report only new entries that name a file
you touched.

## Pack

```powershell
uip rpa-legacy pack "<project>\project.json" --output "<project>\out" `
      --version "<x.y.z>" --output-type Tests
```

`--output-type` accepts `Process|Library|Tests|Objects`; this project is `Tests`. Other
flags: `--auto-version`, `--repository-url/-commit/-branch`, `--release-notes`.

**Pack could not be completed in this environment.** It fails during compilation:

```
Unable to create activity builder for Utilities\GetFrontendCredentials.xaml.
Reason was 'Cannot create unknown type
'{clr-namespace:Swisscom_PHI;assembly=Swisscom.PHI}Get_PHI_Vault'.'
```

Cause: the internal `GlobaleWorkflow [26.8.6.21061]` dependency cannot be restored — the
configured feeds are only `nuget.org` and `C:\ProgramData\UiPath\Packages`. Add the internal
Swisscom feed to `%APPDATA%\NuGet\NuGet.Config`, or pack in CI. This is an environment
limitation, not a project defect — do not "fix" it by removing the dependency.

## Run a test set

```powershell
& $cli test run "<orchestrator_url>" "SCS-TEST-AUT" `
      -P "<project>\project.json" `
      -s "<test set name>" `
      -o "<folder name>" `
      --out junit --result_path "<project>\testresults.xml" `
      --attachRobotLogs true --traceLevel Information
```

Authentication is mandatory; pick one scheme:

- `-u <user> -p <password>`
- `-t <refresh token> -a <account name>`
- `-A <org> -I <appId> -S <appSecret> --applicationScope "<scopes>"`

Scopes used in UiPath's own examples: `OR.Folders OR.BackgroundTasks OR.TestSets
OR.TestSetExecutions OR.TestSetSchedules OR.Settings.Read OR.Robots.Read OR.Machines.Read
OR.Execution OR.Assets OR.Users.Read OR.Jobs OR.Monitoring`.

Other flags: `--timeout <seconds>` (default 7200), `--retryCount`, `-i <input json>`.

**Not executed here** — no Orchestrator credentials in this environment.

## Credentials

Take CLI credentials and tokens from environment variables or CI variables. Never write them
into a file in either repository, never echo them, and never put them in a report.

## Relationship to CI

`.gitlab-ci.yml` includes `swisscom/uipath-b2b/pipeline/includes` → `/Deploy2Orch.yml` with
`PROJECT_FILE=$CI_PROJECT_DIR\project.json`, `RULECONFIG_TYPE=TAU`, `UNIT_TESTS=NONE`,
`ORCHESTRATOR_TENANT=SCS-TEST-AUT`, `PACKAGE_VERSION=~~REPLACE~~`.

**That pipeline is the official deploy path.** Local CLI runs are for fast feedback only;
never publish a package by hand. The include itself was not readable from this environment,
so the exact analyzer and pack invocations it uses are unconfirmed — read it and align
before claiming CI equivalence.
