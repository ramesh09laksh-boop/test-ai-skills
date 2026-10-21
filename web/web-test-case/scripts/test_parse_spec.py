#!/usr/bin/env python3
"""Pin parse_spec.py against the two sample test cases.

Run from anywhere:

    python test_parse_spec.py --samples <dir containing the .xlsx and .csv>

Covers both modes:

* single pair -- the step model and the placeholder -> column gap analysis
* batch       -- scanning a spec folder and a data folder, and the pairing
                 statuses that come out of it

The expectations below are the mechanical statuses the parser is allowed to
derive from names and spec wording alone. They are checked against the gap
analysis the two samples are known to need, with one rule: the parser may be
*more* cautious than a human reviewer, never less. A placeholder a human calls
a gap must never come back as a clean `mapped`.

Exit code 0 = all assertions hold.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_spec import analyse, analyse_batch, pair_key  # noqa: E402


BANKZAHLUNG = "ATF_RTP_WEB_BANKING_BankzahlungAuslandischeIBANWahrungUSD"
QRRECHNUNG = "ATF_RTP_WEB_BANKING_QRRechnung_mit_IBAN_ohne_Referenz"

# placeholder -> (parser status, human verdict from the hand-off gap analysis)
#
# "human verdict" is what a reviewer who understands the domain concludes.
# Where it differs from the parser status, the parser is the cautious one and
# the difference is exactly what the gap gate exists to put in front of a human.
EXPECTED = {
    BANKZAHLUNG: {
        "ZAHLUNGSEMPFAENGER_KONTO":     ("missing",   "mapped to IBANAusland (semantic, name gives no clue)"),
        "BANK":                         ("ambiguous", "ambiguous"),
        "BANK_CODE":                    ("ambiguous", "ambiguous"),
        "EMPFAENGER_NAME":              ("candidate", "mapped to EmfaengerName (header typo)"),
        "STRASSE":                      ("ambiguous", "combined variant only, split rule needed"),
        "STRASSE-NR":                   ("ambiguous", "combined variant only, split rule needed"),
        "STRASSE_UND_NR":               ("ambiguous", "mapped to Strasse"),
        "PLZ":                          ("ambiguous", "combined variant only"),
        "STADT":                        ("ambiguous", "combined variant only"),
        "STADT_UND_PLZ":                ("ambiguous", "mapped to PLZStadt, value looks suspect"),
        "LAND":                         ("missing",   "missing"),
        "BETRAG":                       ("mapped",    "mapped"),
        "WAEHRUNG":                     ("missing",   "missing"),
        "MELDUNG":                      ("missing",   "missing"),
        "ZAHLUNGSANWEISUNG":            ("missing",   "missing"),
        "BELASTUNGSKONTO":              ("missing",   "missing"),
        "BANKSPESEN":                   ("missing",   "missing"),
        "ZAHLUNGSBELEG":                ("missing",   "missing"),
        "REFERENZE-NR":                 ("generated", "generated"),
        "TRANSAKTIONSSIGNIERUNG-TOKEN": ("secret",    "secret"),
    },
    QRRECHNUNG: {
        "ZAHLUNGSEMPFAENGER_IBAN":      ("candidate", "mapped to IBAN"),
        "NAME":                         ("candidate", "mapped to CreditName (renamed)"),
        "STRASSE":                      ("missing",   "missing"),
        "STRASSE-NR":                   ("missing",   "missing"),
        "PLZ":                          ("mapped",    "mapped"),
        "STADT":                        ("missing",   "mapped to Ort (semantic, name gives no clue)"),
        "BETRAG":                       ("mapped",    "mapped"),
        "BELASTUNGSKONTO":              ("missing",   "missing"),
        "REFERENZE-NR":                 ("generated", "generated"),
        "TRANSAKTIONSSIGNIERUNG-TOKEN": ("secret",    "secret"),
    },
}

# Everything the human analysis calls a gap must not come back as a clean
# `mapped` with no confirmation flag.
HUMAN_GAPS = {
    BANKZAHLUNG: {"BANK", "BANK_CODE", "STRASSE", "STRASSE-NR", "PLZ", "STADT",
                  "LAND", "WAEHRUNG", "MELDUNG", "ZAHLUNGSANWEISUNG",
                  "BELASTUNGSKONTO", "BANKSPESEN", "ZAHLUNGSBELEG",
                  "STADT_UND_PLZ"},
    QRRECHNUNG: {"STRASSE", "STRASSE-NR", "BELASTUNGSKONTO"},
}

STRUCTURE = {
    BANKZAHLUNG: {
        "steps": 15,
        "conditional_steps": [3, 4, 14, 15],
        "steps_with_expected_result": [1, 15],
        "generated_value_steps": [9],
        "csv_columns": ["IBANAusland", "EmfaengerName", "Strasse",
                        "PLZStadt", "Betrag", "BankCode"],
        "trailing_ignored_min": 1,
    },
    QRRECHNUNG: {
        "steps": 15,
        "conditional_steps": [15],
        "steps_with_expected_result": [1, 11, 15],
        "generated_value_steps": [13],
        "csv_columns": ["IBAN", "CreditName", "PLZ", "Ort", "Betrag"],
        "trailing_ignored_min": 0,
    },
}

PAIRS = {
    BANKZAHLUNG: (BANKZAHLUNG + ".xlsx", "Bankzahlung_auslaendische_IBAN_Waehrung_USD.csv"),
    QRRECHNUNG: (QRRECHNUNG + ".xlsx", "QRRechnung_mit_IBAN_ohne_Referenz.csv"),
}

# Batch mode must not auto-pair either sample: both CSV names differ from
# their spec name, so both are offered as candidates for a human to confirm.
EXPECTED_PAIRING = {
    BANKZAHLUNG: "candidate",
    QRRECHNUNG: "candidate",
}


def check_batch(samples: str, failures: list[str]) -> None:
    """Run batch mode on a folder holding both samples plus the noise."""
    print("\n### batch mode")
    workdir = tempfile.mkdtemp(prefix="parse_spec_batch_")
    spec_dir = os.path.join(workdir, "specs")
    data_dir = os.path.join(workdir, "data")
    testcases_dir = os.path.join(workdir, "Testcases")
    out_dir = os.path.join(workdir, "out")
    for directory in (spec_dir, data_dir, testcases_dir):
        os.makedirs(directory)

    try:
        for xlsx, csvfile in PAIRS.values():
            source = os.path.join(samples, xlsx)
            if not os.path.exists(source):
                failures.append(f"batch: sample not found at {source}")
                return
            shutil.copy2(source, os.path.join(spec_dir, xlsx))
            shutil.copy2(os.path.join(samples, csvfile),
                         os.path.join(data_dir, csvfile))

        # An Excel lock file and an unpaired CSV must be reported, not acted on.
        lock = "~$" + PAIRS[QRRECHNUNG][0]
        with open(os.path.join(spec_dir, lock), "w", encoding="utf-8") as handle:
            handle.write("lock")
        with open(os.path.join(data_dir, "Nicht_zugeordnet.csv"), "w",
                  encoding="utf-8") as handle:
            handle.write("Spalte\nWert\n")

        result = analyse_batch(spec_dir, data_dir, testcases_dir, out_dir)
        by_name = {row["test_case_name"]: row for row in result["table"]}

        checks = [
            ("specs found", result["counts"]["specs"], 2),
            ("data files found", result["counts"]["data_files"], 3),
            ("exact pairings", result["counts"]["exact"], 0),
            ("candidate pairings", result["counts"]["candidate"], 2),
            ("gap gate blocked", result["counts"]["gap_gate_blocked"], 2),
            ("gap gate clear", result["counts"]["gap_gate_clear"], 0),
            ("lock files skipped", [s["file"] for s in result["skipped_files"]], [lock]),
            ("unpaired data files", result["unpaired_data_files"],
             ["Nicht_zugeordnet.csv"]),
        ]
        for label, got, expected in checks:
            status = "ok " if got == expected else "FAIL"
            print(f"  [{status}] {label}: {got}")
            if got != expected:
                failures.append(f"batch.{label}: got {got}, want {expected}")

        print(f"  {'spec':54} {'data':48} {'pairing':10} exists gap")
        for name, want_pairing in EXPECTED_PAIRING.items():
            row = by_name.get(name)
            if row is None:
                failures.append(f"batch: {name} missing from the pairing table")
                continue
            mark = " " if row["pairing"] == want_pairing else " <- FAIL"
            print(f"  {row['spec']:54} {str(row['data']):48} "
                  f"{row['pairing']:10} {str(row['exists_in_testcases']):6} "
                  f"{row['gap_gate']}{mark}")
            if row["pairing"] != want_pairing:
                failures.append(
                    f"batch.{name}: pairing {row['pairing']!r}, want {want_pairing!r}")
            if row["data"] != PAIRS[name][1]:
                failures.append(
                    f"batch.{name}: paired with {row['data']!r}, want {PAIRS[name][1]!r}")
            if row["gap_gate"] != "blocked":
                failures.append(f"batch.{name}: gap gate {row['gap_gate']!r}, want 'blocked'")

        # One JSON result per pair, and it has to be the single-pair shape.
        for name in EXPECTED_PAIRING:
            path = os.path.join(out_dir, name + ".json")
            if not os.path.exists(path):
                failures.append(f"batch: no result file written for {name}")
                continue
            with open(path, encoding="utf-8") as handle:
                single = json.load(handle)
            if single.get("test_case_name") != name or "mapping" not in single:
                failures.append(f"batch: {path} is not a single-pair analysis")
        print(f"  [ok ] one JSON result per pair written to {out_dir}")

        # Already-implemented specs are skipped unless asked for.
        with open(os.path.join(testcases_dir, BANKZAHLUNG + ".xaml"), "w",
                  encoding="utf-8") as handle:
            handle.write("<Activity />")
        skip = analyse_batch(spec_dir, data_dir, testcases_dir)
        skipped_row = {r["test_case_name"]: r for r in skip["table"]}[BANKZAHLUNG]
        if not skipped_row["exists_in_testcases"] or skipped_row["gap_gate"] != "not analysed":
            failures.append("batch: an already-implemented spec was not skipped")
        again = analyse_batch(spec_dir, data_dir, testcases_dir, regenerate=True)
        regen_row = {r["test_case_name"]: r for r in again["table"]}[BANKZAHLUNG]
        if regen_row["gap_gate"] != "blocked":
            failures.append("batch: --regenerate did not re-analyse an existing test case")
        print("  [ok ] existing test case skipped, and re-analysed with --regenerate")

        # The user's inputs are read-only.
        leftovers = sorted(os.listdir(spec_dir)) + sorted(os.listdir(data_dir))
        expected_inputs = sorted([PAIRS[BANKZAHLUNG][0], PAIRS[QRRECHNUNG][0], lock]) + \
            sorted([PAIRS[BANKZAHLUNG][1], PAIRS[QRRECHNUNG][1], "Nicht_zugeordnet.csv"])
        if leftovers != expected_inputs:
            failures.append(f"batch: input folders were modified: {leftovers}")
        print("  [ok ] input folders unchanged")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def check_pair_key(failures: list[str]) -> None:
    """The documented normalisation example has to keep working."""
    print("\n### pairing key")
    cases = [
        (BANKZAHLUNG, "Bankzahlung_auslaendische_IBAN_Waehrung_USD", True),
        (QRRECHNUNG, "QRRechnung_mit_IBAN_ohne_Referenz", True),
        (BANKZAHLUNG, "QRRechnung_mit_IBAN_ohne_Referenz", False),
    ]
    for spec, data, want_equal in cases:
        equal = pair_key(spec) == pair_key(data)
        status = "ok " if equal == want_equal else "FAIL"
        print(f"  [{status}] {pair_key(spec)!r} {'==' if want_equal else '!='} {pair_key(data)!r}")
        if equal != want_equal:
            failures.append(f"pair_key({spec!r}) vs pair_key({data!r}): "
                            f"{'should' if want_equal else 'should not'} match")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True,
                        help="directory holding the sample .xlsx and .csv files")
    args = parser.parse_args()

    failures: list[str] = []
    for name, (xlsx, csvfile) in PAIRS.items():
        xlsx_path = os.path.join(args.samples, xlsx)
        csv_path = os.path.join(args.samples, csvfile)
        if not os.path.exists(xlsx_path):
            failures.append(f"{name}: sample not found at {xlsx_path}")
            continue

        result = analyse(xlsx_path, csv_path)
        print(f"\n### {name}")

        if result["test_case_name"] != name:
            failures.append(f"{name}: test_case_name is {result['test_case_name']!r}")

        want = STRUCTURE[name]
        checks = [
            ("steps", len(result["steps"]), want["steps"]),
            ("conditional_steps", result["conditional_steps"], want["conditional_steps"]),
            ("steps_with_expected_result", result["steps_with_expected_result"],
             want["steps_with_expected_result"]),
            ("generated_value_steps", result["generated_value_steps"],
             want["generated_value_steps"]),
            ("csv_columns", result["csv_columns"], want["csv_columns"]),
        ]
        for label, got, expected in checks:
            status = "ok " if got == expected else "FAIL"
            print(f"  [{status}] {label}: {got}")
            if got != expected:
                failures.append(f"{name}.{label}: got {got}, want {expected}")

        trailing = len(result["trailing_rows_ignored"])
        if trailing < want["trailing_ignored_min"]:
            failures.append(f"{name}: expected trailing Jira rows to be dropped, got {trailing}")
        print(f"  [ok ] trailing Jira rows ignored: {trailing}")

        if result["gap_gate"]["clear"]:
            failures.append(f"{name}: gap gate reported clear; both samples have known gaps")
        print(f"  [ok ] gap gate blocks: {len(result['gap_gate']['blocking_placeholders'])} placeholders")

        by_name = {m["placeholder"]: m for m in result["mapping"] if m["placeholder"]}
        print(f"  {'placeholder':32} {'parser':12} {'confirm':8} human verdict")
        for placeholder, (want_status, human) in EXPECTED[name].items():
            item = by_name.get(placeholder)
            if item is None:
                failures.append(f"{name}: placeholder {placeholder} not extracted")
                print(f"  {placeholder:32} {'MISSING':12}")
                continue
            got = item["status"]
            flag = "yes" if item["needs_confirmation"] else "no"
            mark = " " if got == want_status else "<- FAIL"
            print(f"  {placeholder:32} {got:12} {flag:8} {human}{mark}")
            if got != want_status:
                failures.append(f"{name}.{placeholder}: status {got!r}, want {want_status!r}")

        for placeholder in HUMAN_GAPS[name]:
            item = by_name.get(placeholder)
            if item and item["status"] == "mapped" and not item["needs_confirmation"]:
                failures.append(
                    f"{name}.{placeholder}: silently auto-mapped although it is a known gap")

        for item in result["mapping"]:
            if item["status"] == "secret" and item["column"]:
                failures.append(f"{name}.{item['placeholder']}: secret bound to a CSV column")
        for row in result["rows"]:
            for column, value in row.items():
                if "token" in column.lower() and value != "***masked***":
                    failures.append(f"{name}: secret-looking column {column} not masked")

    check_pair_key(failures)
    check_batch(args.samples, failures)

    print("\n" + "=" * 70)
    if failures:
        print(f"FAILED ({len(failures)})")
        for failure in failures:
            print("  -", failure)
        return 1
    print("PASSED - both samples match the expected step model and gap analysis, "
          "and batch mode pairs them as candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
