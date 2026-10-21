# UiPath CLI

Only commands actually executed and observed are written below. **Re-run the discovery step
in your own environment** — versions and the bundled `uipcli` path change.

Baseline numbers are **not** here. Produce your own baseline by running the command on the
unmodified project before you change anything, and report the delta against that. The
numbers observed in one past run are in `known-state-2026-10-21.md`, as a snapshot.

## Discovery

```powershell
uip --version                       # 1.202.1 when this was written
uip rpa-legacy --help               # debug | find-activities | find-package | pack
                                    # type-definition | validate      (NO analyze)
```

`uip rpa-legacy` is a wrapper. Workflow Analyzer is **not** exposed through it; use the
bundled legacy binary. Find it rather than hard-coding the version directory:

```powershell
$cli = (Get-ChildItem "$env:USERPROFILE\.uipath\.cache\rpa-legacy-tool" -Recurse `
        -Filter uipcli.exe | Sort-Object FullName -Descending | Select-Object -First 1).FullName
& $cli --version
& $cli                              # lists: asset | job | package | run | test
```

## Workflow Analyzer

```powershell
& $cli package analyze "<project>\project.json" `
      --analyzerTraceLevel Warning `
      --resultPath "<project>\analyzer.json" `
      --traceLevel Information
```

Verified: **exit code 0**, `analyzer.json` written as a JSON array. `ErrorSeverity` is
numeric: `1` Info, `2` Warning, `3` Error.

Run it **twice**: once on the unmodified project for your baseline, once after your change,
and report the delta. Note that `ST-ANA-009` (File Activities Stats) is a metrics rule that
fires once per file — adding a file adds findings without adding defects. Say so rather than
hiding it.

Useful flags: `--stopOnRuleViolation`, `--treatWarningsAsErrors`, `--ignoredRules a,b`.

### Rule set

The CLI takes a rule set through `--governanceFilePath <policy.json>` (an Automation Ops
policy or one exported from Studio). CI sets `RULECONFIG_TYPE: TAU` in `.gitlab-ci.yml`.

The TAU policy file was not available in the environment this was written in, so any number
produced without `--governanceFilePath` is from the **default** rule set and is not
CI-equivalent. Get the TAU policy from Automation Ops or from the pipeline-includes
repository before quoting analyzer results as CI-equivalent. **Always say which rule set you
used.**

## Validate

```powershell
uip rpa-legacy validate "<project>\project.json" --result-path "<project>\validate.json"
```

**Not usable as a pass/fail gate** in the environment this was written in: on the unmodified
project it exits `1` with findings that are all `CLI-TR-0001` TypeResolution false positives,
across every XAML file. Take your own unmodified-project run as the zero point and report
only new entries that name a file you touched.

## Pack

```powershell
uip rpa-legacy pack "<project>\project.json" --output "<project>\out" `
      --version "<x.y.z>" --output-type Tests
```

`--output-type` accepts `Process|Library|Tests|Objects`; match the project's
`designOptions.outputType`. Other flags: `--auto-version`, `--repository-url/-commit/-branch`,
`--release-notes`.

Pack needs every dependency restorable. An internal dependency that is not on a configured
feed fails compilation with `Cannot create unknown type '...'` — that is an environment
limitation, not a project defect. Add the internal feed to `%APPDATA%\NuGet\NuGet.Config`, or
pack in CI. **Never "fix" it by removing the dependency.**

## Run a test set

```powershell
& $cli test run "<orchestrator_url>" "<tenant>" `
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

Without credentials in the environment this cannot run: report `Not executed`, the reason,
and the exact command. Never report `Passed` or `Failed` without a run in this session.

## Credentials

Take CLI credentials and tokens from environment variables or CI variables. Never write them
into a file in either repository, never echo them, and never put them in a report.

## Relationship to CI

`.gitlab-ci.yml` in the target project includes a shared pipeline (observed:
`swisscom/uipath-b2b/pipeline/includes` → `/Deploy2Orch.yml`) with `PROJECT_FILE`,
`RULECONFIG_TYPE`, `UNIT_TESTS`, `ORCHESTRATOR_TENANT` and `PACKAGE_VERSION` variables. Read
the file on your run — those values move.

**That pipeline is the official deploy path.** Local CLI runs are for fast feedback only;
never publish a package by hand. The include itself was not readable from the environment
this was written in, so the exact analyzer and pack invocations it uses are unconfirmed —
read it and align before claiming CI equivalence.
