# Object Repository (`.objects\`)

**Patterns, not an inventory.** Which Screens and Elements exist is discovered on each run.
The last snapshot is in `known-state-2026-10-21.md` — re-check it, never assume it.

## Inspect it first

```powershell
Get-ChildItem "<project>\.objects" -Recurse -Force -Include .metadata,.type,.content |
  Select-Object FullName
```

Build, for the report, the actual tree: Library → App → AppVersion → Screens → Elements,
with each `Name`, `Id` and the activity type its target was captured for. Then check every
`Reference` used in a workflow against it.

## Layout on disk

A four-character directory per object, nested by ownership:

```
.objects\
  .metadata .type                                   Library
  <app>\                                            App
    .metadata .type
    .data\ObjectSelectionName\.content
    <version>\                                      AppVersion
      <screen>\                                     Screen
        .metadata .type
        .data\ObjectRepositoryScreenData\.content
        <element>\                                  Element
          .data\ObjectRepositoryTargetData\.content
```

- `.metadata` — JSON with `Name`, `Type`, `Id`, `Reference`, `ParentRef`, timestamps.
  `Reference` is always `<libraryId>/<objectId>`.
- `.content` — the selector/target XML. Its declaration says `encoding="utf-16"` but the
  **bytes on disk are UTF-8**. Decode as UTF-8 and ignore the declaration; an XML parser that
  honours it will fail.
- `.hash` / `.attributes\SearchHash` — maintained by Studio.

## Rules

1. **Reuse existing descriptors.** A new element belongs under the App version that is
   already there, in a Screen matching its page.
2. **Check every `Reference`** used in a workflow against `.objects\` by matching the object
   id against an `Id` in a `.metadata`. A reference to a library id that is not in this
   project is **broken** — report it and never reuse it.
3. **Never edit `.objects\` files by hand.** Studio maintains the hashes; a hand edit
   corrupts the repository.
4. **Never hand-write a `Reference` id and never paste a raw selector** into a workflow.
5. **Name elements in PascalCase after their visible label**, as the existing ones are.
6. A missing `imageRef` screenshot is not an error if `.images` is gitignored — check
   `.gitignore`.
7. A folder with `.hash` but no `.metadata`/`.type`/`.content` is an orphan left by a
   deletion. **Report it; do not delete it.** Cleanup is a Studio action for the team.

## When an element has no descriptor

An agent cannot capture a UI element. So:

1. Put a clearly named placeholder target in the workflow — the Switch case for the element
   with the activity in place and its target left unbound, commented as awaiting capture.
2. Add the element to the **capture list** in the report: page, element name, the activity
   type it will be used with, and how to recognise it on screen.
3. Mark the test case **not runnable** until the element is captured.

The capture list is the hand-off to a human in Studio. It is not a defect in the test case —
it is the honest boundary of what an agent can produce.
