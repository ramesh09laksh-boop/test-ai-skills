# Workflow: bind elements captured in Studio

Runs after a human has captured, in Studio, the elements the last run listed as "needs
capture". Turns those captures into bound Switch cases and says whether the test case is now
runnable.

## Inputs

- The **test case name**.
- The **capture list** from that test case's last report (page/screen, element name, activity
  type, how to recognise it on screen).

If either is missing, ask. Do not reconstruct a capture list by guessing which elements a
test case "probably" needed.

## Steps

### a. Re-read `.objects/` and match

Re-read the Object Repository from disk — not from the last report, not from
`known-state-<date>.md`. For each capture-list item, look for a newly captured element and
match **by screen and element name**:

| Match | Meaning |
|---|---|
| exact | same screen, same element name → bindable |
| renamed | same screen, no name match, but one new element of the right activity type | → ask |
| wrong screen | the name exists under a different screen → ask |
| none | nothing new for this item → stays on the capture list |

Record each element's `Id`, its `Reference` (`<libraryId>/<objectId>`), and its
`TaxonomyType` / captured activity type, so the binding can be checked against the activity
it will sit on.

### b. Show the match table and ask

Present the table before changing anything:

| Capture-list item | Screen | Element found | `Id` | Activity type agrees | Match |
|---|---|---|---|---|---|

**Ask before binding anything ambiguous or unmatched.** A renamed element, an element under
an unexpected screen, a type that disagrees with the activity it is destined for, or two
candidates for one item — all of these are questions, not decisions. Only `exact` matches
whose activity type agrees may be bound without asking.

### c. Bind only this capture list's open Switch cases

For each confirmed match, set the target `Reference` on the activity in the Switch case that
was left unbound and commented as awaiting capture, and remove that comment.

- Bind **only** the cases belonging to this test case's capture list.
- Leave every other case, workflow and file alone — including unbound cases from a *different*
  test case's capture list.
- An unmatched item keeps its placeholder case and stays on the capture list with its reason.

### d. Re-audit and re-measure

1. **Reference audit across all XAML:** every `Reference` in every workflow must resolve to an
   `Id` present in `.objects/`. Report any that does not — including pre-existing ones you did
   not create.
2. **Analyzer delta against `main`:** run the analyzer on `main` for the baseline and on the
   working tree, and report the delta. Say which rule set you used
   (`references/uipath-cli.md`).

## Done when

- Every capture-list item is either **bound** or **still listed with its reason**.
- There are **no broken references** anywhere in the project.
- The **runnable status is stated with evidence** — a reference audit that resolves and an
  analyzer run, or `Not executed` plus the reason and the exact command. Never assert
  "runnable" from inspection alone if a run was possible and not done.

## Never

- **Never edit `.objects/` files by hand.** Studio maintains the hashes; a hand edit corrupts
  the repository. If a capture is wrong, it goes back to Studio.
- **Never touch Switch cases outside this capture list**, and never hand-write a `Reference`
  id or paste a raw selector.
