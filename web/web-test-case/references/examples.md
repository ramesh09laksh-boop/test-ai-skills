# Worked examples

Two real specs, carried through the workflow. Both stop at the gap gate — that is the
expected outcome, not a failure.

Mapping tables below are verbatim `parse_spec.py` output. "Human verdict" is what a reviewer
who knows the domain concludes; where it differs, the parser is the cautious one and the
difference is exactly what has to be asked.

---

## A. `ATF_RTP_WEB_BANKING_BankzahlungAuslandischeIBANWahrungUSD`

Test data: `Bankzahlung_auslaendische_IBAN_Waehrung_USD.csv`
→ `IBANAusland;EmfaengerName;Strasse;PLZStadt;Betrag;BankCode`
→ `NO9386011117947;Tester Test;Teststrasse 1;45000 Norwegen;56;DABANO22XXX`

15 steps. Conditional: **3, 4, 14, 15**. Expected results: **1, 15**. Generated: **9**.
8 trailing Jira rows dropped.

### Mapping

| Placeholder | Parser | Column / candidate | Human verdict |
|---|---|---|---|
| `ZAHLUNGSEMPFAENGER_KONTO` | `missing` | — | **ask** — intended `IBANAusland`, but no name evidence |
| `BANK` | `ambiguous` | `BankCode` | which field does `DABANO22XXX` go in? |
| `BANK_CODE` | `ambiguous` | `BankCode` | same value serves both arms of step 3 |
| `EMPFAENGER_NAME` | `candidate` | `EmfaengerName` | header typo — confirm |
| `STRASSE` | `ambiguous` + split | `Strasse` | `Teststrasse 1` is street **and** number |
| `STRASSE-NR` | `ambiguous` + split | `Strasse` | needs a split rule |
| `STRASSE_UND_NR` | `ambiguous` | `Strasse` | the combined variant this value fits |
| `PLZ` | `ambiguous` + split | `PLZStadt` | needs a split rule |
| `STADT` | `ambiguous` + split | `PLZStadt` | needs a split rule |
| `STADT_UND_PLZ` | `ambiguous` | `PLZStadt` | fits, but see the value warning below |
| `LAND` | `missing` | — | **missing** |
| `BETRAG` | `mapped` | `Betrag` | ok |
| `WAEHRUNG` | `missing` | — | **missing** — USD appears only in the test case name |
| `MELDUNG` | `missing` | — | **missing** |
| `ZAHLUNGSANWEISUNG` | `missing` | — | **missing** |
| `BELASTUNGSKONTO` | `missing` | — | **missing** |
| `BANKSPESEN` | `missing` | — | **missing** |
| `ZAHLUNGSBELEG` | `missing` | — | **missing** |
| `REFERENZE-NR` | `generated` | — | runtime, stored, asserted at step 15 |
| `TRANSAKTIONSSIGNIERUNG-TOKEN` | `secret` | — | PHI Vault |

Unused columns: `IBANAusland`, `EmfaengerName` (they only become used once the two
`candidate`/`missing` rows above are confirmed).

**Suspect value:** `PLZStadt = "45000 Norwegen"` — Norwegen is a country, not a city, and
the IBAN is Norwegian while the test name says USD. Raise it.

### Scenario

```gherkin
Given die Konfiguration für Mandant/Umgebung geladen ist
  And eine angemeldete Browser-Session auf der Startseite besteht
 When ich den Ausland Payment Link klicke
 Then wird die Zahlungsmaske angezeigt                       # Schritt 1
 When ich <ZAHLUNGSEMPFAENGER_KONTO> eingebe
  And — wenn das Feld BIC/Swift-Code erscheint — <BANK> eingebe,
      ansonsten <BANK_CODE> zwischenspeichere                # Schritt 3, bedingt
  And — wenn Feld-Stadt ein Eingabefeld ist — Name/Strasse/Nr/PLZ/Stadt/Land eingebe,
      ansonsten Name/Strasse_und_Nr/Stadt_und_PLZ eingebe    # Schritt 4, bedingt
  And <BETRAG>, <WAEHRUNG>, <MELDUNG>, <ZAHLUNGSANWEISUNG> erfasse
  And ein zufälliges Stichwort als <REFERENZE-NR> erfasse und zwischenspeichere
  And <BELASTUNGSKONTO>, <BANKSPESEN>, <ZAHLUNGSBELEG> auswähle
  And den Button "Überweisen" klicke
  And — wenn das Währungswechsel-Pop-Up erscheint — "Nein, Zahlung speichern" klicke
  And — wenn das Transaktionssignierung-Pop-Up erscheint — den Token eingebe
      und "Jetzt überweisen" klicke
 Then wurde die Zahlung korrekt erfasst und erscheint auf der Website
      inkl. der gespeicherten <REFERENZE-NR>                 # Schritt 15
```

---

## B. `ATF_RTP_WEB_BANKING_QRRechnung_mit_IBAN_ohne_Referenz`

Test data: `QRRechnung_mit_IBAN_ohne_Referenz.csv`
→ `IBAN;CreditName;PLZ;Ort;Betrag`
→ `CH3708393042020857309;Tester Test;9000;Testcity;52`

15 steps. Conditional: **15**. Expected results: **1, 11, 15**. Generated: **13**.
No trailing rows.

### Mapping

| Placeholder | Parser | Column / candidate | Human verdict |
|---|---|---|---|
| `ZAHLUNGSEMPFAENGER_IBAN` | `candidate` | `IBAN` | confirm |
| `NAME` | `candidate` | `CreditName` | renamed — confirm |
| `STRASSE` | `missing` | — | **missing** |
| `STRASSE-NR` | `missing` | — | **missing** |
| `PLZ` | `mapped` | `PLZ` | ok |
| `STADT` | `missing` | — | **ask** — intended `Ort`, but no name evidence |
| `BETRAG` | `mapped` | `Betrag` | ok |
| `BELASTUNGSKONTO` | `missing` | — | **missing** |
| `REFERENZE-NR` | `generated` | — | runtime, stored, asserted at step 15 |
| `TRANSAKTIONSSIGNIERUNG-TOKEN` | `secret` | — | PHI Vault |

Unused columns: `IBAN`, `CreditName`, `Ort`.

**Also undefined:** which characters count as "unerlaubt" for step 10, and what the
"korrekte Nachricht" of step 12 is. Neither is in the CSV.

### Scenario

A negative check lives inside a positive test. Both are real assertions.

```gherkin
Given die Konfiguration für Mandant/Umgebung geladen ist
  And eine angemeldete Browser-Session auf der Startseite besteht
 When ich den Inland Payment Link klicke
 Then wird die Zahlungsmaske angezeigt                       # Schritt 1
 When ich <ZAHLUNGSEMPFAENGER_IBAN>, <NAME>, <STRASSE>, <STRASSE-NR>,
      <PLZ>, <STADT>, <BETRAG> eingebe
  And <BELASTUNGSKONTO> auswähle
  And eine Nachricht mit unerlaubten Zeichen eingebe         # Schritt 10
  And den Button "Überweisen" klicke
 Then erscheint die Alert-Meldung
      'Nachricht mit unerlaubten Zeichen'                    # Schritt 11
 When ich eine korrekte Nachricht eingebe
  And ein zufälliges Stichwort als <REFERENZE-NR> erfasse und zwischenspeichere
  And den Button "Überweisen" klicke
  And — wenn das Transaktionssignierung-Pop-Up erscheint — den Token eingebe
      und "Jetzt überweisen" klicke
 Then wurde die Zahlung korrekt erfasst und erscheint auf der Website
      inkl. der gespeicherten <REFERENZE-NR>                 # Schritt 15
```

---

## Files both samples would touch

**Derived from the 2026-10-21 snapshot** (`known-state-2026-10-21.md`), so the "new" vs
"implement stub" column may already be wrong. Re-derive this list from the project you are
in: whichever of these already exist are reused, not created. Nothing below is written before
the gap gate clears and the element captures exist.

| File | Action |
|---|---|
| `Testcases\<TestCaseName>.xaml` | new |
| `project.json` → `fileInfoCollection` | one new entry |
| `Applications\WebApp\Pages\PaymentPage\Click_PaymentPage_Element.xaml` | new |
| `Applications\WebApp\Pages\PaymentPage\SetText_PaymentPage_Element.xaml` | new |
| `Applications\WebApp\Pages\PaymentPage\Validate_PaymentPage_Element.xaml` | new |
| `Applications\WebApp\Pages\PaymentPage\SelectDropdown_PaymentPage_Element.xaml` | new |
| `Applications\WebApp\Pages\PaymentListPage\Validate_PaymentListPage_Element.xaml` | new |
| `Applications\WebApp\Actions\ClickElement.xaml` | add `in_Page` cases |
| `Applications\WebApp\Actions\SetText.xaml` | implement stub + dispatcher |
| `Applications\WebApp\Actions\SelectDropdown.xaml` | implement stub + dispatcher |
| `Applications\WebApp\Validation\ValidateElement.xaml` | add `in_Page` cases |
| `Applications\WebApp\Validation\ValidateText.xaml` | implement stub (alert text, list entry) |
| `Utilities\WaitForLoader.xaml` | implement stub (used instead of `Delay`) |

The Bankzahlung case additionally needs `SetCheckbox`/`SetRadioButton` if Bankspesen or
Zahlungsbeleg turn out to be radio groups rather than dropdowns — unknown until the page is
seen.

## Open questions these two raise

1. `ExecutionTemplate` (ordering dependency on the login test) or self-login in `Given`?
   And should the templates rethrow config errors instead of continuing with a null config?
2. Fix the Login test first? As of the last snapshot it could not log in — re-check.
3. Who captures the payment-page elements in Studio, and when?
4. The missing data in both tables above; and is `45000 Norwegen` correct?
5. Should the `ATF_RTP_WEB_BANKING_` prefix stay in the test case name, given the CSVs drop
   it? (It does: the test case name is the xlsx name verbatim.)
6. Data variations or reading the CSV in `Given`?
7. Where does the transaction-signing token come from — which PHI Vault entry?
8. `InitConfig` reads a UNC share, not `Config\config.json` — switch it?
