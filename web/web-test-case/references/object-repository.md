# Object Repository (`.objects\`)

## What exists today

One **Library** `mP2_Cqto3kuFAHZwckVu6g` (`.objects\.metadata`) containing **App** `WebApp`
→ **AppVersion** `1.0.0` → two Screens:

| Screen | Id | Title | Url | Used by |
|---|---|---|---|---|
| HomePage | `MpbgBJcIUESbqIKBNtn1vA` | New Tab | `[in_Config("homepage").ToString]` | `Framework\EnsureSession.xaml` |
| LoginPage | `WmBf68mm7024QOmNDNuPaA` | Anmeldung | `[url]` (screen variable) | `Applications\WebApp\Navigation\OpenBrowser.xaml` |

**Exactly one Element exists:**

| Element | Id | TaxonomyType | Selector | SearchSteps | ActivityType |
|---|---|---|---|---|---|
| LoginPage / VertragsnummerInput | `b9LIEkiNoEqqYcFyGZmP3g` | Input | `<webctrl id='username' tag='INPUT' />` | `Selector` only | CheckState |

Used by `Applications\WebApp\Pages\LoginPage\Validate_LoginPage_Element.xaml`. Its
`BrowserURL` identifies the application under test as the bank's internet-banking test
environment.

**There are no payment screens or elements.** Nothing exists for the Inland/Ausland payment
links, form fields, dropdowns, buttons, the Währungswechsel or Transaktionssignierung
pop-ups, the alert, or the payment list. Every UI element the payment tests need must be
captured in Studio first.

## Layout on disk

```
.objects\
  .metadata .type                                   Library
  qfZ-\                                             App       WebApp
    .metadata .type
    .data\ObjectSelectionName\.content
    9Xgy\                                           AppVersion 1.0.0
      Mpbg\                                         Screen    HomePage
        .metadata .type
        .data\ObjectRepositoryScreenData\.content
      WmBf\                                         Screen    LoginPage
        b9LI\                                       Element   VertragsnummerInput
          .data\ObjectRepositoryTargetData\.content
  -_zc\WG30\VCbY\...                                ORPHANED (see below)
```

- `.metadata` — JSON with `Name`, `Type`, `Id`, `Reference`, `ParentRef`, timestamps.
  `Reference` is always `<libraryId>/<objectId>`.
- `.content` — the selector/target XML. Its declaration says `encoding="utf-16"` but the
  **bytes on disk are UTF-8**. Decode as UTF-8 and ignore the declaration; an XML parser
  that honours it will fail.
- `.hash` / `.attributes\SearchHash` — maintained by Studio.

## Rules

1. **Reuse existing descriptors.** Every new element belongs under the existing
   `WebApp / 1.0.0` app version, in a Screen matching its page (e.g. `PaymentPage`,
   `PaymentListPage`).
2. **Check every `Reference` used in a workflow** against `.objects\` by matching the object
   id against an `Id` in a `.metadata`. A reference to a library id that is not in this
   project is **broken** — report it and never reuse it.
3. **Never edit `.objects\` files by hand.** Studio maintains the hashes; a hand edit
   corrupts the repository.
4. **Never hand-write a `Reference` id and never paste a raw selector** into a workflow.
5. **Name elements in PascalCase after their visible label**, as the existing ones are
   (`VertragsnummerInput`, `SubmitButton`).
6. A missing `imageRef` screenshot is not an error — `.images` is gitignored.

## When an element has no descriptor

An agent cannot capture a UI element. So:

1. Put a clearly named placeholder target in the workflow (a Switch case for the element
   with the activity in place and its target left unbound), commented as awaiting capture.
2. Add the element to the **capture list** in the report, with page, element name, the
   activity type it will be used with, and how to recognise it on screen.
3. Mark the test case **not runnable** until the element is captured.

## Known broken references — report, never reuse

`Applications\WebApp\Pages\LoginPage\Click_LoginPage_Element.xaml` points at library
`5gYTkcWkeUikngI2i_8_9w`, which **does not exist in this project** (the project's library is
`mP2_Cqto3kuFAHZwckVu6g`). Two separate targets are affected:

| Target | Reference | Selector it actually holds |
|---|---|---|
| `NApplicationCard.TargetApp` | `5gYTkcWkeUikngI2i_8_9w/pMl-kapR4E6OVDP3rwUmuw` | `<html app='chrome.exe' title='New Tab' />` |
| `NClick` "SubmitButton" | `5gYTkcWkeUikngI2i_8_9w/vwrTa_gBjkGcA6kKCh5B0w` | `<ctrl name='Enhance your search with tabs, files, or an AI tool' role='push button' />` |

Both were captured on **Chrome's own New Tab page**, outside the repository — not on the
bank's login form. The Workflow Analyzer also flags the SubmitButton selector
(`UI-USG-011`: non-allowed attribute `idx='2'`).

`CancelButton` in the same Switch is `<x:Null x:Key="CancelButton" />` — a case with no
activity in it.

Together with the `SetText` stub called from `LoginSteps.xaml`, this means **the Login test
cannot currently log in**. Since every payment test depends on a logged-in session via
`ExecutionTemplate`, flag this as a blocker before promising a runnable test.

## Orphaned folder

`.objects\-_zc\WG30\VCbY\` and its three child folders (`8Rat`, `aMW7`, `cP_H`) contain only
`.hash` and `.attributes\SearchHash` files — no `.metadata`, `.type` or `.content`. They
look like leftovers of a deleted screen and three deleted elements.

**Report it; do not delete it.** Cleaning it up is a Studio action for the team.
