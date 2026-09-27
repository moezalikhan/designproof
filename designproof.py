#!/usr/bin/env python3
"""designproof.py — run an Alloy model and report VERIFIED / VIOLATED per check.

Usage:
    python designproof.py models/permissions.als [--jar PATH] [--output-dir DIR]

Exit codes:
    0  all checks UNSAT (every rule holds)
    1  one or more checks SAT (at least one rule violated)
    2  usage / environment error (Java missing, jar missing, etc.)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_JAR = "org.alloytools.alloy.dist.jar"
DEFAULT_OUTPUT_DIR = "permissions"


# ---------------------------------------------------------------------------
# Parsing helpers (testable, no I/O)
# ---------------------------------------------------------------------------

# Matches lines like:
#   00. check MembersCanEdit           0       UNSAT
#   02. check RemovedUsersCannotEdit   0    1/1     SAT
_LINE_RE = re.compile(
    r"^\s*\d+\.\s+check\s+(\S+)\s+.*?\b(SAT|UNSAT)\s*$",
    re.IGNORECASE,
)


def parse_alloy_output(text: str) -> list[dict]:
    """Parse the stdout of `alloy exec` and return a list of check results.

    Each result dict has keys:
        name   (str)   – assert name
        sat    (bool)  – True if SAT (counterexample found / rule violated)

    Only lines matching the check-result pattern are returned; other output
    is silently ignored so that future Alloy versions with extra logging do
    not break parsing.
    """
    results = []
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if m:
            results.append(
                {
                    "name": m.group(1),
                    "sat": m.group(2).upper() == "SAT",
                }
            )
    return results


def load_skolems(receipt_path: Path) -> dict[str, list]:
    """Read receipt.json and return a mapping of check-name -> list of skolem atoms.

    The skolems section of receipt.json lives at:
        commands.<CheckName>.solution[0].instances[0].skolems

    Each skolem value has an "arity" and "data" list of atom tuples.
    We flatten the data into a list of atom names for display.

    Returns an empty dict if the file is missing or malformed.
    """
    if not receipt_path.exists():
        return {}
    try:
        with receipt_path.open() as f:
            receipt = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    skolems_map: dict[str, list] = {}
    commands = receipt.get("commands", {})
    for check_name, cmd in commands.items():
        solutions = cmd.get("solution", [])
        if not solutions:
            continue
        instances = solutions[0].get("instances", [])
        if not instances:
            continue
        raw_skolems = instances[0].get("skolems", {})
        atoms: list[str] = []
        for skolem_key, skolem_val in raw_skolems.items():
            # Key is like "$CheckName_varname"; value has "data": [[atom], ...]
            data = skolem_val.get("data", [])
            flat = [item for sublist in data for item in sublist]
            # Build a readable "varname = {atom, ...}" string
            var_name = skolem_key.lstrip("$").split("_", 1)[-1]
            atoms.append(f"{var_name} = {{{', '.join(flat)}}}")
        if atoms:
            skolems_map[check_name] = atoms
    return skolems_map


def format_table(results: list[dict], skolems_map: dict[str, list]) -> str:
    """Return a formatted ASCII table of results."""
    col_name = max(len(r["name"]) for r in results) if results else 4
    col_name = max(col_name, len("Check"))
    col_verdict = max(len("VIOLATED (SAT)"), len("VERIFIED (UNSAT)"))

    sep = f"+{'-' * (col_name + 2)}+{'-' * (col_verdict + 2)}+{'-' * 42}+"
    header = (
        f"| {'Check':<{col_name}} | {'Verdict':<{col_verdict}} | {'Counterexample atoms':<40} |"
    )
    lines = [sep, header, sep]
    for r in results:
        verdict = "VIOLATED (SAT)" if r["sat"] else "VERIFIED (UNSAT)"
        atoms_str = "; ".join(skolems_map.get(r["name"], [])) or "-"
        if len(atoms_str) > 40:
            atoms_str = atoms_str[:37] + "..."
        lines.append(
            f"| {r['name']:<{col_name}} | {verdict:<{col_verdict}} | {atoms_str:<40} |"
        )
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def find_java() -> str | None:
    """Return the path to the `java` binary, or None if not found."""
    return shutil.which("java")


def run_alloy(jar: Path, model: Path, output_dir: Path, force: bool = True) -> subprocess.CompletedProcess:
    """Invoke the Alloy jar and return the completed process."""
    cmd = [
        "java",
        "--enable-native-access=ALL-UNNAMED",
        "-jar",
        str(jar),
        "exec",
    ]
    if force:
        cmd.append("-f")
    cmd.extend(["-o", str(output_dir), str(model)])
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run an Alloy model and report VERIFIED/VIOLATED per check.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit 0 = all checks UNSAT (every rule holds)\n"
            "Exit 1 = one or more checks SAT (rule violated)\n"
            "Exit 2 = environment/usage error"
        ),
    )
    parser.add_argument("model", help="Path to the .als Alloy model file")
    parser.add_argument(
        "--jar",
        default=DEFAULT_JAR,
        help=f"Path to the Alloy jar (default: {DEFAULT_JAR})",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        dest="output_dir",
        help=f"Directory for Alloy output (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--results-json",
        default="results.json",
        dest="results_json",
        help="Path to write the JSON results (default: results.json)",
    )
    args = parser.parse_args(argv)

    # --- Environment checks ---
    if find_java() is None:
        print(
            "ERROR: 'java' not found on PATH. Install Java 11+ and ensure it is on your PATH.",
            file=sys.stderr,
        )
        return 2

    jar = Path(args.jar)
    if not jar.exists():
        print(
            f"ERROR: Alloy jar not found: {jar}\n"
            "Download from https://github.com/AlloyTools/org.alloytools.alloy/releases\n"
            "or pass --jar PATH.",
            file=sys.stderr,
        )
        return 2

    model = Path(args.model)
    if not model.exists():
        print(f"ERROR: Model file not found: {model}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)

    # --- Run Alloy ---
    print(f"Running Alloy on {model} ...")
    proc = run_alloy(jar, model, output_dir)

    # The Alloy jar writes check results to stderr; stdout carries other output.
    # Try stderr first; fall back to stdout for forward compatibility.
    alloy_output = proc.stderr if proc.stderr.strip() else proc.stdout

    if proc.returncode not in (0, 1) and not alloy_output.strip():
        print("ERROR: Alloy process failed unexpectedly.", file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        return 2

    # --- Parse results ---
    results = parse_alloy_output(alloy_output)
    if not results:
        print(
            "ERROR: No check results found in Alloy output. "
            "Check that your model contains `check` commands.",
            file=sys.stderr,
        )
        print("Raw Alloy stderr:", file=sys.stderr)
        print(proc.stderr or "(empty)", file=sys.stderr)
        print("Raw Alloy stdout:", file=sys.stderr)
        print(proc.stdout or "(empty)", file=sys.stderr)
        return 2

    receipt_path = output_dir / "receipt.json"
    skolems_map = load_skolems(receipt_path)

    # --- Print table ---
    print()
    print(format_table(results, skolems_map))
    print()

    # --- Write results.json ---
    results_data = []
    for r in results:
        results_data.append(
            {
                "check": r["name"],
                "result": "SAT" if r["sat"] else "UNSAT",
                "violated": r["sat"],
                "counterexample_atoms": skolems_map.get(r["name"], []),
            }
        )
    results_path = Path(args.results_json)
    with results_path.open("w") as f:
        json.dump(results_data, f, indent=2)
    print(f"Results written to {results_path}")

    # --- Exit code ---
    any_violated = any(r["sat"] for r in results)
    if any_violated:
        violated = [r["name"] for r in results if r["sat"]]
        print(f"\nFAILED: {len(violated)} check(s) violated: {', '.join(violated)}")
        return 1
    else:
        print(f"OK: all {len(results)} check(s) UNSAT — every rule holds.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
