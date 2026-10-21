#!/usr/bin/env python3
"""Parse manual web test descriptions (.xlsx) and their test data (.csv) into JSON.

Input  : <TestCaseName>.xlsx  (Jira export, German, columns
         Schritt / Aktion/Eingabe / zu pruefendes erwartetes Ergebnis)
         <Name>.csv           (';'-separated, header row + 1..n data rows)
Output : JSON on stdout -- step model, placeholders, CSV columns, rows and a
         placeholder -> column mapping with a status per placeholder.

Two modes:

  single pair  --xlsx <spec.xlsx> [--csv <data.csv>]
  batch        --spec-dir <dir> [--data-dir <dir>]

Batch mode scans the folders the user named, pairs spec and data files, and
emits a pairing table plus one analysis per pair. It never searches the disk
on its own: the folders are arguments.

Everything here is deliberately conservative. Only an exact match produces an
automatic result -- an exact normalised token set for a placeholder -> column
mapping, an exact base name for a spec <-> data pairing. Anything that merely
looks similar comes back as `candidate` and has to be confirmed by a human.
The script never guesses a value, never emits a value for a secret, and never
writes to the files it reads.

No network access. Requires openpyxl.

Usage:
    python parse_spec.py --xlsx <spec.xlsx> --csv <data.csv> [--indent 2]
    python parse_spec.py --xlsx <spec.xlsx>             # no test data yet
    python parse_spec.py --spec-dir <dir> --data-dir <dir> \
                         [--testcases-dir <project>/Testcases] \
                         [--out-dir <dir>] [--regenerate]
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import glob
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
# file-name pairing (batch mode)
# --------------------------------------------------------------------------

# A leading run of two or more ALL-CAPS underscore segments, as in
# ``ATF_RTP_WEB_BANKING_``. The run stops at the first segment that is not
# all-caps, so ``ATF_RTP_WEB_BANKING_QRRechnung_mit_IBAN_ohne_Referenz``
# keeps ``QRRechnung_mit_IBAN_ohne_Referenz``.
NAME_PREFIX_RE = re.compile(r"^(?:[A-Z][A-Z0-9]*_){2,}")

LOCK_FILE_GLOBS = ("~$*",)


def strip_name_prefix(stem: str) -> str:
    return NAME_PREFIX_RE.sub("", stem) or stem


def pair_key(stem: str) -> str:
    """Normalised key used to offer a spec <-> data file pairing.

    On top of :func:`norm` (case, umlaut -> ae/oe/ue, separators, CamelCase,
    connector words) the digraphs are collapsed to the bare vowel, because the
    spec names drop the umlaut entirely where the CSV names transliterate it:
    ``AuslandischeIBANWahrungUSD`` vs ``auslaendische_IBAN_Waehrung_USD``.

    This is looser than :func:`norm` on purpose. A match on this key is only
    ever reported as a `candidate` for a human to confirm, never auto-paired.
    """
    key = norm(strip_name_prefix(stem))
    for digraph, vowel in (("ae", "a"), ("oe", "o"), ("ue", "u")):
        key = key.replace(digraph, vowel)
    return key


def is_lock_file(filename: str) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in LOCK_FILE_GLOBS)


def list_inputs(directory: str, extension: str) -> tuple[list[str], list[dict]]:
    """Every ``*<extension>`` in *directory*, with lock files reported, not hidden."""
    if not os.path.isdir(directory):
        raise ValueError(f"{directory}: not a directory")

    kept: list[str] = []
    skipped: list[dict] = []
    for path in sorted(glob.glob(os.path.join(directory, "*" + extension))):
        filename = os.path.basename(path)
        if is_lock_file(filename):
            skipped.append({"file": filename, "reason": "temporary/lock file"})
            continue
        kept.append(path)
    return kept, skipped


def implemented_test_cases(testcases_dir: str | None) -> set[str]:
    """Test case names that already have a ``<name>.xaml`` in *testcases_dir*."""
    if not testcases_dir or not os.path.isdir(testcases_dir):
        return set()
    return {os.path.splitext(f)[0]
            for f in os.listdir(testcases_dir) if f.lower().endswith(".xaml")}


def pair_inputs(spec_paths: list[str], data_paths: list[str]) -> list[dict]:
    """Pair spec files with data files by name. Three outcomes only.

    ``exact``     identical base names -- paired automatically.
    ``candidate`` the normalised keys match -- shown for confirmation.
    ``unpaired``  no name evidence, or several data files compete for one spec.

    There is no similarity score and no fallback. A spec with no usable
    pairing stays unpaired and is reported.
    """
    data_by_stem = {os.path.splitext(os.path.basename(p))[0]: p for p in data_paths}
    data_by_key: dict[str, list[str]] = {}
    for stem, path in data_by_stem.items():
        data_by_key.setdefault(pair_key(stem), []).append(path)

    pairs = []
    for spec_path in spec_paths:
        stem = os.path.splitext(os.path.basename(spec_path))[0]
        item = {
            "test_case_name": stem,
            "spec": os.path.basename(spec_path),
            "spec_path": spec_path,
            "data": None,
            "data_path": None,
            "pairing": "unpaired",
            "pair_key": pair_key(stem),
            "data_candidates": [],
            "note": "",
        }

        if stem in data_by_stem:
            item["data_path"] = data_by_stem[stem]
            item["data"] = os.path.basename(item["data_path"])
            item["pairing"] = "exact"
            item["note"] = "Base names are identical."
        else:
            matches = data_by_key.get(item["pair_key"], [])
            item["data_candidates"] = [os.path.basename(p) for p in matches]
            if len(matches) == 1:
                item["data_path"] = matches[0]
                item["data"] = os.path.basename(matches[0])
                item["pairing"] = "candidate"
                item["note"] = ("Normalised names match (case, umlauts, separators, "
                                "name prefix). Confirm before using it.")
            elif len(matches) > 1:
                item["pairing"] = "unpaired"
                item["note"] = ("Several data files normalise to the same name "
                                f"({', '.join(item['data_candidates'])}). Ask which one.")
            else:
                item["note"] = "No data file in the data folder matches this spec by name."
        pairs.append(item)
    return pairs


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
        "mode": "single",
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


def analyse_batch(spec_dir: str, data_dir: str | None = None,
                  testcases_dir: str | None = None,
                  out_dir: str | None = None,
                  regenerate: bool = False,
                  indent: int = 2) -> dict:
    """Scan a spec folder and a data folder, pair them, analyse each pair.

    The two folders may be the same folder. One unusable pair never stops the
    others: a pair that cannot be parsed carries its ``error`` and the rest
    are still analysed.
    """
    data_dir = data_dir or spec_dir

    spec_paths, skipped = list_inputs(spec_dir, ".xlsx")
    data_paths, skipped_data = list_inputs(data_dir, ".csv")
    skipped += skipped_data

    already = implemented_test_cases(testcases_dir)
    pairs = pair_inputs(spec_paths, data_paths)

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    paired_data = {p["data"] for p in pairs if p["data"]}

    for item in pairs:
        item["already_implemented"] = item["test_case_name"] in already
        item["analysed"] = False
        item["error"] = None
        item["gap_gate"] = None
        item["result_file"] = None
        item["analysis"] = None

        if item["already_implemented"] and not regenerate:
            item["note"] = ((item["note"] + " ") if item["note"] else "") + (
                f"Testcases\\{item['test_case_name']}.xaml already exists; "
                "skipped. Pass --regenerate to analyse it anyway.")
            continue

        try:
            result = analyse(item["spec_path"], item["data_path"])
        except Exception as exc:  # a broken spec must not stop the batch
            item["error"] = f"{type(exc).__name__}: {exc}"
            continue

        item["analysed"] = True
        item["gap_gate"] = result["gap_gate"]
        if out_dir:
            path = os.path.join(out_dir, item["test_case_name"] + ".json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=indent, ensure_ascii=False)
            item["result_file"] = path
        else:
            item["analysis"] = result

    table = [{
        "spec": item["spec"],
        "data": item["data"],
        "pairing": item["pairing"],
        "test_case_name": item["test_case_name"],
        "exists_in_testcases": item["already_implemented"],
        "gap_gate": ("clear" if item["gap_gate"] and item["gap_gate"]["clear"]
                     else "blocked" if item["gap_gate"]
                     else "error" if item["error"]
                     else "not analysed"),
        "blocking_placeholders": (len(item["gap_gate"]["blocking_placeholders"])
                                  if item["gap_gate"] else None),
    } for item in pairs]

    return {
        "mode": "batch",
        "spec_dir": os.path.abspath(spec_dir),
        "data_dir": os.path.abspath(data_dir),
        "testcases_dir": os.path.abspath(testcases_dir) if testcases_dir else None,
        "spec_files": [os.path.basename(p) for p in spec_paths],
        "data_files": [os.path.basename(p) for p in data_paths],
        "skipped_files": skipped,
        "table": table,
        "pairs": pairs,
        "unpaired_specs": [i["spec"] for i in pairs if i["pairing"] == "unpaired"],
        "unpaired_data_files": [os.path.basename(p) for p in data_paths
                                if os.path.basename(p) not in paired_data],
        "counts": {
            "specs": len(spec_paths),
            "data_files": len(data_paths),
            "exact": sum(1 for i in pairs if i["pairing"] == "exact"),
            "candidate": sum(1 for i in pairs if i["pairing"] == "candidate"),
            "unpaired": sum(1 for i in pairs if i["pairing"] == "unpaired"),
            "already_implemented": sum(1 for i in pairs if i["already_implemented"]),
            "gap_gate_clear": sum(1 for i in pairs
                                  if i["gap_gate"] and i["gap_gate"]["clear"]),
            "gap_gate_blocked": sum(1 for i in pairs
                                    if i["gap_gate"] and not i["gap_gate"]["clear"]),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--xlsx", help="single-pair mode: path to <TestCaseName>.xlsx")
    parser.add_argument("--csv", help="single-pair mode: the paired test-data .csv")
    parser.add_argument("--spec-dir", help="batch mode: folder holding the .xlsx specs")
    parser.add_argument("--data-dir",
                        help="batch mode: folder holding the .csv test data "
                             "(defaults to --spec-dir)")
    parser.add_argument("--testcases-dir",
                        help="batch mode: the project's Testcases folder, to flag "
                             "test cases that already exist")
    parser.add_argument("--out-dir",
                        help="batch mode: write one <TestCaseName>.json per pair here "
                             "instead of inlining the analyses")
    parser.add_argument("--regenerate", action="store_true",
                        help="batch mode: analyse specs that already exist in Testcases")
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args(argv)

    if bool(args.xlsx) == bool(args.spec_dir):
        parser.error("give either --xlsx (single pair) or --spec-dir (batch), not both")
    if args.xlsx:
        for name in ("spec_dir", "data_dir", "testcases_dir", "out_dir"):
            if getattr(args, name):
                parser.error(f"--{name.replace('_', '-')} belongs to batch mode")
        result = analyse(args.xlsx, args.csv)
    else:
        if args.csv:
            parser.error("--csv belongs to single-pair mode; use --data-dir")
        result = analyse_batch(args.spec_dir, args.data_dir, args.testcases_dir,
                               args.out_dir, args.regenerate, args.indent)

    sys.stdout.write(json.dumps(result, indent=args.indent, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
