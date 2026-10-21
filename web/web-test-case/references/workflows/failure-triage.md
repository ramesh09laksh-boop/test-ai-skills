# Workflow: classify a failed test case

> **Derived, not dictated.** The spec for this workflow was cut off in transit; the Inputs,
> Steps, Done-when and Never below are derived from prompt 7 in `PROMPTS.md` and the skill's
> critical rules. Correct it when the full spec arrives.

Finds the cause of a failure and classifies it. Produces a diagnosis and a proposed fix —
never a fix applied on the spot.

## Inputs

- The **test case name**.
- The **log or Orchestrator output** of the failing run (pasted, or a `testresults.xml` /
  robot log path). Without it, ask — do not re-run the test and triage your own run unless the
  user asks for that, and never triage from the spec alone.
- Optionally, the report from the run that implemented the test case, for the confirmed data
  mapping and the capture list.

## Steps

### a. Read the failure before theorising

From the log, establish and quote:

- the **step number** and the display name of the activity that failed (`Utilities\LogMessage`
  output gives `[Step n]`),
- the **exception type** and message,
- whether the failure was an **assertion** (a Verify activity) or an **action**,
- how far the test got — which steps logged successfully before it.

If the log does not say, say so. Do not infer a step number that was never logged.

### b. Gather the evidence for each category

Check these against the project, not from memory:

| Evidence | How to check |
|---|---|
| Reference resolves | the activity's `Reference` matches an `Id` in `.objects/` |
| Selector quality | is the target one of the known-bad kinds (captured off the application, non-allowed attributes such as `idx`) |
| Data | was the value's placeholder `mapped`, or a `candidate`/`missing` the user confirmed; does the CSV value suit the field |
| Sync | is the failure a timeout or a "not found" on an element that exists, and is there a fixed `Delay` or a missing state check nearby |
| Session / config | was `out_Config` null, or did the session attach fail (`Unable to ensure session`) |
| Product | the application reached the right page and rejected a valid input, or the asserted business outcome genuinely did not happen |

### c. Classify into exactly one category

| Class | Means |
|---|---|
| **Product defect** | the application misbehaved; the test is correct and the assertion is right to fail |
| **Test issue — selector** | the target is wrong, broken or unresolvable |
| **Test issue — data** | the value was wrong, missing, or an unconfirmed gap-gate guess |
| **Test issue — sync** | the step raced the page; fixed waits or a missing state check |
| **Environment** | config, session, credentials, feed, Orchestrator or the machine |

State the class, then the **evidence line** that chose it, then what would have to be true for
it to be one of the others. If the evidence does not separate two classes, say **inconclusive**
and name the one observation that would settle it. An inconclusive answer is a valid outcome;
a confident wrong one is not.

### d. Propose a fix and wait

List the proposed change per file, and what it would prove. Then **stop and wait for
approval.** Nothing is edited in this workflow.

## Done when

- The failing step, exception and activity are quoted from the log.
- One class is stated with its evidence, or `inconclusive` with the missing observation.
- A fix is proposed per file, with nothing applied.
- No file in the project changed.

## Never

- **Never weaken an assertion to make the test pass** — do not delete it, loosen it, make it
  conditional, or move it out of `Then`.
- **Never add a `Delay`** to fix a race; synchronise on state.
- **Never catch-and-log** the failing step so the test reports green.
- **Never report `Passed`/`Failed` from reasoning.** Only a run in this session with evidence
  produces those; everything else is `Not executed` plus the reason and the command.
- Never classify as "product defect" without having ruled out the selector, the data and the
  session — a false product defect costs someone else a bug investigation.
