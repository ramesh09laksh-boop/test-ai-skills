# Ready prompts: `web-test-case`

Copy-paste prompts for the usual situations. Run them from the **web-test-framework project root**, with the skill installed (see [README](../../README.md)).
Replace the `<…>` parts. The prompts work the same in Claude Code, GitHub Copilot and Codex.

> **Tip:** start each new piece of work in a fresh session. Paste the previous report when you continue work you started earlier.

---

## 1. First look: check readiness without changing anything

Use this before the first real run, or after the framework has changed.

```
Use the web-test-case skill in check-only mode. Don't change any files.
Spec folder: <spec folder>
Data folder: <data folder>
Report:
- the project inspection, including the config path in InitConfig and whether Config/config.json exists
- the pairing table
- the gap gate result per test case
- the capture list
- broken Object Repository references and stubs on the path these tests need
```

## 2. Implement all test cases in a folder

```
Use the web-test-case skill to implement the test cases from <spec folder> with test data from <data folder>.
Follow the existing project structure, templates, InitConfig/Config/config.json and Object Repository exactly.
Stop at the gap gate for anything unclear. Implement only the cases that clear it, and give me the full report.
```

## 3. Implement one test case

```
Use the web-test-case skill to implement only <TestCaseName>.
Spec: <spec folder>\<TestCaseName>.xlsx
Data: <data folder>\<file>.csv
Stop at the gap gate if anything is unclear.
```

## 4. Continue after answering the gap gate

Paste the gap table from the previous report and fill in the last column.

```
Continue with web-test-case for <TestCaseName>. Here are my answers to the gap gate:

| Placeholder | Answer |
|---|---|
| <ZAHLUNGSEMPFAENGER_KONTO> | use CSV column IBANAusland |
| <STADT> | use CSV column Ort |
| <BELASTUNGSKONTO> | <value or "add column X to the CSV"> |
| <TOKEN> | PHI Vault entry <name> |

Confirmed pairings: <spec file> ↔ <csv file>
Implement now, and report anything still open.
```

## 5. Make a test runnable after the elements were captured in Studio

```
I captured the elements from the capture list in Studio: <screen/element names, or "all of them">.
Use web-test-case to bind these Object Repository elements to the open Switch cases for <TestCaseName>.
Re-check every reference against .objects/, run the analyzer, and tell me whether the test is now runnable.
Don't change any other workflows.
```

## 6. Validate only (before a merge request)

```
Use web-test-case to validate <TestCaseName or "all test cases added in this branch"> without changing anything:
XAML well-formed, arguments bound, Object Repository references resolve, project.json registration correct,
no existing file changed, and the analyzer delta compared with main. Give me real CLI output only.
```

## 7. A test failed: classify it

```
<TestCaseName> failed. Here is the log / Orchestrator output:
<paste>
Use web-test-case to find the cause and classify it: product defect, test issue (selector, data, sync) or environment.
Propose a fix and wait for my approval before changing anything. Never weaken an assertion to make the test pass.
```

## 8. The spec changed: update an existing test case

```
The spec for <TestCaseName> changed: <spec folder>\<TestCaseName>.xlsx
Use web-test-case to compare it with Testcases\<TestCaseName>.xaml, show me the step and assertion differences,
and update the test case only after I confirm. Keep everything else unchanged.
```

## 9. Propose a framework fix (Login, templates, stubs)

```
Use web-test-case to propose (not apply) a fix for <e.g. the Login test: swallowed exceptions, empty Then, broken SubmitButton, stub SetText>.
Show the planned file changes and what needs capturing in Studio. Wait for my approval.
```

---

## What to expect every time

- A **pairing table**, then the **gap gate**. The skill asks rather than invents data.
- A **capture list** whenever an element isn't in the Object Repository yet. Capturing happens in Studio and isn't the agent's job.
- A **report** in which every status is backed by real CLI or run output, or marked `Not executed`.
- Your xlsx and CSV files are never modified.

---

## How much of this the skill actually defines

Mapping of each prompt onto the skill, so you know which file governs the run.

| Prompt | Defined where |
|---|---|
| 1. Check-only | `SKILL.md` — "Check-only run": steps 1–5, stops after the gap gate, writes nothing |
| 2. Implement a folder | `SKILL.md` — the main workflow, steps 1–13 |
| 3. Implement one | `SKILL.md` — same workflow with one pair; name the two files directly |
| 4. Continue after the gap gate | `SKILL.md` — step 5 is the stop, this is the resume |
| 5. Bind captured elements | `references/workflows/bind-captured-elements.md` |
| 6. Validate only | `SKILL.md` — step 12 and `references/uipath-cli.md`; the skill's baseline is *the unmodified project*, so ask for the delta against `main` explicitly, as this prompt does |
| 7. Classify a failure | `references/workflows/failure-triage.md` |
| 8. Spec changed → update | `references/workflows/spec-change-update.md` |
| 9. Propose a framework fix | `SKILL.md` — critical rule 3: propose, never apply, wait for approval |

All nine are now backed by a written workflow. Each of the three in
`references/workflows/` states its own Inputs, Steps, **Done when** and **Never**, and each
one stops for confirmation before it changes a file.

> `failure-triage.md` and `spec-change-update.md` were drafted from prompts 7 and 8 plus the
> skill's critical rules, because the detailed spec for them did not arrive. Review them
> against how you actually want those two tasks run.
