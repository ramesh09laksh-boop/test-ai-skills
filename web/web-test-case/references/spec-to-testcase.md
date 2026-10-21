# From spec to test case

## The inputs

`ATF_RTP_WEB_<Name>.xlsx` — one manual test case exported from Jira, in German. First sheet,
three columns: `Schritt` | `Aktion/Eingabe` | `zu prüfendes erwartetes Ergebnis`.
**The file name without the extension is the test case name**, used verbatim for the XAML
file, the `DisplayName` and the `fileInfoCollection` entry.

The export appends UI chrome below the step table — "Drop files to attach, or browse.",
"Activity", "All", "Comments", "Work Log", "History", "Transitions". The table ends at the
first row whose `Schritt` is not an integer. `parse_spec.py` stops there and returns the
dropped rows in `trailing_rows_ignored` so you can see what was discarded.

`<Name>.csv` — `;`-separated, CRLF, a header row and one row per data variation. UTF-8 with
a cp1252 fallback. The CSV name does not follow mechanically from the xlsx name
(`BankzahlungAuslandischeIBANWahrungUSD.xlsx` ↔
`Bankzahlung_auslaendische_IBAN_Waehrung_USD.csv`). Pair them explicitly.

## Step model

`parse_spec.py` emits per step: `number`, `action`, `expected_result`,
`has_expected_result`, `conditional`, `has_else_branch`, `generates_value`, `stores_value`
and the `placeholders` it mentions with the branch each one sits in.

Placeholders are `<UPPERCASE_TOKENS>` in either column.

## Placeholder → column mapping

The matcher is deliberately conservative. Names are folded (lowercase, `ä→ae`, `ö→oe`,
`ü→ue`, `ß→ss`), split on `_ - .` space, CamelCase and letter/digit boundaries, and the
connector words `und oder der die das mit ohne als im in` are dropped.

| Status | Meaning |
|---|---|
| `mapped` | the token sets are **identical**. The only status that may be used without asking. |
| `candidate` | tokens overlap, or differ by a single character in a token of 5+ characters. **Confirm with the author.** |
| `ambiguous` | one column is the only match for two mutually exclusive variants of a conditional step. |
| `missing` | no column resembles the placeholder. |
| `generated` | produced at runtime by a "zufällig … zwischenspeichern" step. |
| `secret` | name matches `token`, `passwor`, `kennwort`, `pin`, `secret`, `credential`, `geheim`, `vault`. Never from a CSV. |
| `unused_column` | a CSV column no placeholder refers to. |

Two further flags: `split_required` (one column feeds several fields of the same variant, so
a split rule has to be agreed) and `needs_confirmation` (roll-up used by the gap gate).

A semantic mapping that the names do not support — `<ZAHLUNGSEMPFAENGER_KONTO>` ↔
`IBANAusland`, `<STADT>` ↔ `Ort` — comes back as `missing`. That is correct behaviour, not
a parser bug: guessing it is exactly what the gap gate exists to prevent.

## Gap gate

If `gap_gate.clear` is false, present the mapping table and stop. Do not implement data
entry for an unconfirmed placeholder, do not substitute a plausible value, and do not drop
a step because its data is missing.

Also surface values that are implausible for their field even when the status is `mapped` —
the parser checks names, not meanings.

## Scenario structure

Mirror `Testcases\ATF_RTP_WEB_Login.xaml`: a root `Sequence` named after the test case
containing `... Given`, `... When`, `... Then`. Put the Gherkin text in the test case
annotation so the business reads the same steps the robot runs.

- **Given** — config and session come from the execution template; state the start page.
- **When** — the action steps in spec order. Each logged with its step number via
  `io_StepCounter` and `Utilities\LogMessage.xaml`.
- **Then** — every expected result as a Verify activity from `UiPath.Testing.Activities`.

**Intermediate expected results are asserted where they occur.** Both samples have one at
step 1 ("Zahlungsmaske wird angezeigt"), and the QR case has one at step 11 (the alert). An
expected result asserted only at the end is a defect.

Keep the German wording of step texts and alert texts verbatim in display names, log
messages and assertion messages. Code identifiers follow the existing naming.

## Conditional steps

"Wenn … erscheint, dann … , ansonsten …" is a runtime branch, not a choice you make while
writing the test:

- `Check App State` (`NCheckState`) on the deciding element, with a short timeout taken from
  config — never a fixed `Delay`.
- A distinct path per branch. If the spec gives an "ansonsten" arm, implement it too.
- Log which branch ran.
- If the spec attaches an expected result to a conditional path, assert it inside that path.

A placeholder that only appears in one arm belongs to a field variant that may not exist on
screen in a given run; `parse_spec.py` marks it `alternative_variant`.

## Generated values

`<REFERENZE-NR>`: "Zufällige Stichwort als <REFERENZE-NR> erfassen und zwischenspeichern".
Generate a unique random keyword, log it, hold it in a variable scoped to the test case, and
assert on that same variable in the final check. Never hard-code it and never read it from
the CSV.

Note the different verb in the Bankzahlung step 3: "<BANK_CODE> zwischenspeichern" stores a
value that came from the test data — it is not generated. The parser only treats a step as
generating when it contains both "zufällig" and a store verb.

## Secrets

`<TRANSAKTIONSSIGNIERUNG-TOKEN>` and anything else matching the secret pattern must come
from the PHI Vault or config through `Utilities\GetFrontendCredentials.xaml`. Never in a
CSV, config file, XAML literal or log line. `parse_spec.py` masks values of
secret-looking CSV columns in its `rows[]` output.

## Test data binding

The project has **no** data-binding mechanism today: no data variations in
`fileInfoCollection`, no CSV reader anywhere. Propose one approach —

- a data-driven test case with the CSV attached as a data variation, or
- reading the CSV in `Given` and iterating rows —

and **wait for approval**. Keep the original CSV column names, and put the
placeholder→column mapping in exactly one place so it can be reviewed as a unit.
