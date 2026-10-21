#!/usr/bin/env python3
"""Parse a manual web test description (.xlsx) and its test data (.csv) into JSON.

Input  : ATF_RTP_WEB_<Name>.xlsx  (Jira export, German, columns
         Schritt / Aktion/Eingabe / zu pruefendes erwartetes Ergebnis)
         <Name>.csv               (';'-separated, header row + 1..n data rows)
Output : JSON on stdout -- step model, placeholders, CSV columns, rows and a
         placeholder -> column mapping with a status per placeholder.

The mapping is deliberately conservative. Only an exact match of the
normalised name tokens produces `mapped`. Everything else that merely looks
similar is reported as `candidate` and must be confirmed by a human. The
script never guesses a value and never emits a value for a secret.

No network access. Requires openpyxl.

Usage:
    python parse_spec.py --xlsx <spec.xlsx> --csv <data.csv> [--indent 2]
    python parse_spec.py --xlsx <spec.xlsx>            # no test data yet
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

try:
    import openpyxl
except ImportError:  # pragma: no cover - environment problem, not a parse problem
    sys.exit("openpyxl is required: python -m pip install openpyxl")


# --------------------------------------------------------------------------
# normalisation
# --------------------------------------------------------------------------

UMLAUTS = {
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "ae", "Ö": "oe", "Ü": "ue",
    "à": "a", "á": "a", "â": "a", "è": "e", "é": "e", "ê": "e",
}

# German connector words carry no identifying information in a field name.
STOPWORDS = {"und", "oder", "der", "die", "das", "mit", "ohne", "als", "im", "in"}

SECRET_RE = re.compile(
    r"token|passwor|kennwort|\bpin\b|secret|credential|geheim|vault",
    re.IGNORECASE,
)

PLACEHOLDER_RE = re.compile(r"<([A-Z0-9ÄÖÜ][A-Z0-9ÄÖÜ_\-\.]*)>")

# "Wenn ... erscheint, dann ..." / "Wenn ... angezeigt wird, dann ..."
CONDITIONAL_RE = re.compile(r"\bwenn\b.*?\bdann\b", re.IGNORECASE | re.DOTALL)
ELSE_RE = re.compile(r"\bansonstens?\b|\bandernfalls\b|\bsonst\b", re.IGNORECASE)

RANDOM_RE = re.compile(r"zuf(ä|ae)llig", re.IGNORECASE)
STORE_RE = re.compile(r"zwischenspeichern|zwischen speichern|merken", re.IGNORECASE)


def fold(text: str) -> str:
    """Lowercase and transliterate German umlauts."""
    for src, dst in UMLAUTS.items():
        text = text.replace(src, dst)
    return text.lower()


def tokenize(name: str) -> list[str]:
    """Split a field name into comparable tokens.

    Handles snake_case, kebab-case, dotted names, CamelCase and
    letter/digit boundaries: ``STRASSE-NR`` -> ``['strasse', 'nr']``,
    ``PLZStadt`` -> ``['plz', 'stadt']``.
    """
    spaced = re.sub(r"[_\-. ]+", " ", name)
    # CamelCase / acronym boundaries: PLZStadt -> PLZ Stadt, iBANAusland -> IBAN Ausland
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-ZÄÖÜ])", " ", spaced)
    spaced = re.sub(r"(?<=[A-ZÄÖÜ])(?=[A-ZÄÖÜ][a-zäöü])", " ", spaced)
    spaced = re.sub(r"(?<=[A-Za-zÄÖÜäöü])(?=\d)|(?<=\d)(?=[A-Za-zÄÖÜäöü])", " ", spaced)
    tokens = [fold(t) for t in spaced.split() if t]
    return [t for t in tokens if t and t not in STOPWORDS]


def norm(name: str) -> str:
    return "".join(tokenize(name))


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 1:
        return 2  # we only ever care about "<= 1"
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def tokens_similar(a: str, b: str) -> bool:
    """Exact, or a single-character typo in a reasonably long token."""
    return a == b or (min(len(a), len(b)) >= 5 and edit_distance(a, b) <= 1)


# --------------------------------------------------------------------------
# xlsx
# --------------------------------------------------------------------------

def parse_xlsx(path: str) -> tuple[str, list[dict], list[str]]:
    """Read the first sheet and stop at the first non-integer step number.

    The Jira export appends UI chrome below the step table ("Drop files to
    attach...", "Activity", "Comments", ...). Those rows have no step number,
    so the integer check is what ends the table.
    """
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = workbook[workbook.sheetnames[0]]

    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        raise ValueError(f"{path}: first sheet is empty")

    header = [("" if c is None else str(c).strip()) for c in rows[0]]
    header += [""] * (3 - len(header))

    steps: list[dict] = []
    trailing: list[str] = []
    table_ended = False

    for raw in rows[1:]:
        cells = [("" if c is None else str(c).strip()) for c in raw]
        cells += [""] * (3 - len(cells))
        number, action, expected = cells[0], cells[1], cells[2]

        if table_ended:
            if any(cells):
                trailing.append(" | ".join(c for c in cells if c))
            continue

        if not re.fullmatch(r"\d+", number.strip().rstrip(".")):
            if not any(cells):
                continue  # blank spacer row inside the table
            table_ended = True
            trailing.append(" | ".join(c for c in cells if c))
            continue

        steps.append(build_step(int(number.strip().rstrip(".")), action, expected))

    return header, steps, trailing


def build_step(number: int, action: str, expected: str) -> dict:
    text = f"{action}\n{expected}"
    conditional = bool(CONDITIONAL_RE.search(action))
    else_match = ELSE_RE.search(action)

    found: list[dict] = []
    for match in PLACEHOLDER_RE.finditer(text):
        name = match.group(1)
        if else_match and match.start() < len(action):
            branch = "else" if match.start() > else_match.start() else "then"
        else:
            branch = "then" if conditional else None
        found.append({"name": name, "branch": branch})

    return {
        "number": number,
        "action": action,
        "expected_result": expected,
        "has_expected_result": bool(expected),
        "conditional": conditional,
        "has_else_branch": bool(else_match),
        "generates_value": bool(RANDOM_RE.search(action)) and bool(STORE_RE.search(action)),
        "stores_value": bool(STORE_RE.search(action)),
        "placeholders": found,
    }


def collect_placeholders(steps: list[dict]) -> list[dict]:
    """One entry per distinct placeholder, with where and how it is used."""
    seen: dict[str, dict] = {}
    for step in steps:
        for item in step["placeholders"]:
            entry = seen.setdefault(item["name"], {
                "name": item["name"],
                "steps": [],
                "branches": [],
                "in_conditional_step": False,
                "generated": False,
                "stored": False,
                "secret": False,
            })
            if step["number"] not in entry["steps"]:
                entry["steps"].append(step["number"])
            if item["branch"]:
                entry["branches"].append(item["branch"])
            entry["in_conditional_step"] |= step["conditional"]
            entry["generated"] |= step["generates_value"]
            entry["stored"] |= step["stores_value"]
            entry["secret"] |= bool(SECRET_RE.search(item["name"]))

    result = []
    for entry in seen.values():
        branches = set(entry.pop("branches"))
        # A placeholder that only ever appears in one arm of a
        # "Wenn ... dann ... ansonsten ..." step belongs to a field variant
        # that may not exist on screen in a given run.
        entry["branch"] = (
            "both" if branches == {"then", "else"}
            else (branches.pop() if len(branches) == 1 else None)
        )
        entry["alternative_variant"] = entry["in_conditional_step"] and entry["branch"] in ("then", "else")
        result.append(entry)
    return sorted(result, key=lambda e: (e["steps"][0], e["name"]))


# --------------------------------------------------------------------------
# csv
# --------------------------------------------------------------------------

def parse_csv(path: str) -> tuple[list[str], list[dict], str]:
    """Read a ';'-separated test-data file; UTF-8 first, cp1252 as fallback."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with open(path, "r", encoding=encoding, newline="") as handle:
                rows = list(csv.reader(handle, delimiter=";"))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"{path}: not readable as UTF-8 or cp1252")

    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError(f"{path}: no rows")

    columns = [c.strip() for c in rows[0]]
    records = []
    for row in rows[1:]:
        row += [""] * (len(columns) - len(row))
        record = {}
        for column, value in zip(columns, row):
            record[column] = "***masked***" if SECRET_RE.search(column) else value.strip()
        records.append(record)
    return columns, records, encoding


# --------------------------------------------------------------------------
# mapping
# --------------------------------------------------------------------------

def build_mapping(placeholders: list[dict], columns: list[str]) -> list[dict]:
    column_tokens = {c: tokenize(c) for c in columns}
    branch_of = {e["name"]: e["branch"] for e in placeholders}

    mapping = []
    for entry in placeholders:
        name = entry["name"]
        item = {
            "placeholder": name,
            "steps": entry["steps"],
            "column": None,
            "candidates": [],
            "status": None,
            "split_required": False,
            "needs_confirmation": False,
            "note": "",
        }

        # Precedence: a secret is never test data, and a generated value is
        # produced at runtime. Neither may come from the CSV.
        if entry["secret"]:
            item["status"] = "secret"
            item["note"] = ("Must be read from the PHI Vault or config via "
                            "Utilities\\GetFrontendCredentials.xaml. Never store it in the CSV.")
            mapping.append(item)
            continue
        if entry["generated"]:
            item["status"] = "generated"
            item["note"] = ("Generated at runtime (step "
                            f"{entry['steps'][0]}), stored in a variable and asserted later.")
            mapping.append(item)
            continue

        tokens = tokenize(name)
        exact = [c for c in columns if set(tokens) == set(column_tokens[c])]
        if len(exact) == 1:
            item["column"] = exact[0]
            item["status"] = "mapped"
        elif len(exact) > 1:
            item["candidates"] = exact
            item["status"] = "ambiguous"
            item["note"] = "Several columns normalise to the same name."
        else:
            candidates = []
            for column in columns:
                overlap = [t for t in tokens
                           if any(tokens_similar(t, ct) for ct in column_tokens[column])]
                if overlap:
                    candidates.append({
                        "column": column,
                        "shared_tokens": overlap,
                        "exact_token_set": False,
                        "unmatched_placeholder_tokens":
                            [t for t in tokens if t not in overlap],
                        "unmatched_column_tokens":
                            [ct for ct in column_tokens[column]
                             if not any(tokens_similar(t, ct) for t in tokens)],
                    })
            if candidates:
                item["candidates"] = candidates
                item["status"] = "candidate"
                item["note"] = ("Name is similar but not identical. Confirm with the "
                                "author before using it; do not auto-map.")
            else:
                item["status"] = "missing"
                item["note"] = "No column in the test data resembles this placeholder."

        if entry["alternative_variant"]:
            item["note"] = (item["note"] + " " if item["note"] else "") + (
                "Belongs to the '" + entry["branch"] + "' arm of a conditional step; "
                "the opposite arm uses a different set of fields.")
        mapping.append(item)

    # One CSV column feeding several placeholders is never self-explanatory.
    # Same branch  -> the single value has to be split across the fields.
    # Opposite arms -> the spec is ambiguous about which field the value is for.
    targets: dict[str, list[dict]] = {}
    for item in mapping:
        column = item["column"] or (
            item["candidates"][0]["column"]
            if len(item["candidates"]) == 1 and isinstance(item["candidates"][0], dict)
            else None)
        if column:
            targets.setdefault(column, []).append(item)

    for column, items in targets.items():
        if len(items) < 2:
            continue
        per_branch: dict[str | None, list[dict]] = {}
        for item in items:
            per_branch.setdefault(branch_of.get(item["placeholder"]), []).append(item)

        # Several fields of the *same* variant share one value -> split rule.
        for siblings in per_branch.values():
            if len(siblings) > 1:
                for item in siblings:
                    item["split_required"] = True
                    item["note"] = (item["note"] + " " if item["note"] else "") + (
                        f"Column '{column}' feeds several fields of the same variant "
                        f"({', '.join(i['placeholder'] for i in siblings)}); "
                        "a split rule must be agreed before the value can be used.")

        # Mutually exclusive variants share one value -> the spec is ambiguous.
        if "then" in per_branch and "else" in per_branch:
            for item in items:
                item["status"] = "ambiguous"
                item["note"] = (f"Column '{column}' is the only match for mutually "
                                "exclusive variants "
                                f"({', '.join(i['placeholder'] for i in items)}). "
                                "The spec does not say which field the value belongs to. "
                                ) + item["note"]

    for item in mapping:
        item["needs_confirmation"] = bool(
            item["status"] in ("candidate", "ambiguous", "missing")
            or item["split_required"]
            or (item["placeholder"] and
                next(e["alternative_variant"] for e in placeholders
                     if e["name"] == item["placeholder"])
                and item["status"] not in ("secret", "generated")))

    unused = [c for c in columns
              if c not in {m["column"] for m in mapping if m["column"]}]
    for column in unused:
        mapping.append({
            "placeholder": None,
            "steps": [],
            "column": column,
            "candidates": [],
            "status": "unused_column",
            "split_required": False,
            "needs_confirmation": True,
            "note": "Column present in the test data but not referenced by any placeholder.",
        })
    return mapping


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def analyse(xlsx_path: str, csv_path: str | None) -> dict:
    header, steps, trailing = parse_xlsx(xlsx_path)
    placeholders = collect_placeholders(steps)

    columns: list[str] = []
    rows: list[dict] = []
    encoding = None
    if csv_path:
        columns, rows, encoding = parse_csv(csv_path)

    mapping = build_mapping(placeholders, columns)
    blocking = [m for m in mapping if m["needs_confirmation"]]

    return {
        "test_case_name": os.path.splitext(os.path.basename(xlsx_path))[0],
        "source": {
            "xlsx": os.path.basename(xlsx_path),
            "csv": os.path.basename(csv_path) if csv_path else None,
            "csv_encoding": encoding,
            "columns_header": header[:3],
        },
        "steps": steps,
        "conditional_steps": [s["number"] for s in steps if s["conditional"]],
        "steps_with_expected_result": [s["number"] for s in steps if s["has_expected_result"]],
        "generated_value_steps": [s["number"] for s in steps if s["generates_value"]],
        "placeholders": placeholders,
        "csv_columns": columns,
        "rows": rows,
        "mapping": mapping,
        "gap_gate": {
            "clear": not blocking,
            "blocking_placeholders": [m["placeholder"] for m in blocking if m["placeholder"]],
        },
        "trailing_rows_ignored": trailing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--xlsx", required=True, help="path to ATF_RTP_WEB_<Name>.xlsx")
    parser.add_argument("--csv", help="path to the paired test-data .csv")
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args(argv)

    result = analyse(args.xlsx, args.csv)
    sys.stdout.write(json.dumps(result, indent=args.indent, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
