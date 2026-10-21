# Test case report — `<ATF_RTP_WEB_...>`

**Spec:** `<file>.xlsx`  **Test data:** `<file>.csv`  **Branch:** `<branch>`
**Date:** `<YYYY-MM-DD>`  **Status:** Implemented / Blocked at gap gate / Partially implemented

> Never write `Passed` or `Failed` without a run in this session. Otherwise: `Not executed`,
> with the reason and the exact command.

## 1. Summary

Two or three sentences: what was built, what is blocked, what the user has to decide.

## 2. Data mapping

| Placeholder | Status | CSV column | Confirmed by user | Note |
|---|---|---|---|---|
| | `mapped`/`candidate`/`ambiguous`/`missing`/`generated`/`secret` | | yes/no | |

Unused CSV columns: `<...>`
Suspect values: `<column = value — why>`
Open data questions: `<...>`

## 3. Steps

| # | Spec action | Implemented as | Expected result | Assertion | Status |
|---|---|---|---|---|---|
| 1 | | `Actions\...` | | Verify... | done / blocked: `<reason>` |

Conditional steps and how each branch is decided: `<...>`
Generated values and where they are asserted: `<...>`

Every expected result in the spec must appear in the "Assertion" column. List any that
do not and say why.

## 4. Object Repository — elements needing capture in Studio

| Page / Screen | Element | Activity | How to recognise it on screen |
|---|---|---|---|

Existing descriptors reused: `<...>`
Broken references found: `<...>`

**Test case is runnable: yes / no** — if no, because `<...>`.

## 5. Files

| File | Change |
|---|---|
| | new / case added / stub implemented |

Stubs implemented: `<...>`
Existing files modified: `<...>` — approved by `<who>` on `<when>`, or "none".

## 6. CLI results

Real output only. Say which rule set was used.

| Step | Command | Result |
|---|---|---|
| Validate | `uip rpa-legacy validate ...` | `<n>` findings; baseline `<n>`; delta `<n>` |
| Analyzer | `uipcli package analyze ... --governanceFilePath ...` | rule set `<TAU/default>`; `<n>` findings; delta `<n>` |
| Pack | `uip rpa-legacy pack ... --output-type Tests` | `<nupkg>` / failed: `<reason>` |
| Run | `uipcli test run ...` | Passed / Failed / **Not executed** — `<reason>` |

New analyzer findings introduced by this change:

| Code | Severity | File | Description |
|---|---|---|---|

## 7. Proposed changes to existing code — NOT applied

| File | Problem | Proposed fix |
|---|---|---|

## 8. Open questions for the user

1.
