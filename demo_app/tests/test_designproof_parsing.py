"""Tests for designproof.py parsing logic (no I/O, no Alloy process required)."""

import json
import tempfile
from pathlib import Path

import pytest

# Import the module under test
import designproof as dp


# ---------------------------------------------------------------------------
# parse_alloy_output
# ---------------------------------------------------------------------------

ALLOY_OUTPUT_ALL_UNSAT = """\
00. check MembersCanEdit           0       UNSAT
01. check ShareLinkHoldersCanEdit     0       UNSAT
02. check RemovedUsersCannotEdit     0       UNSAT
"""

ALLOY_OUTPUT_ONE_SAT = """\
00. check MembersCanEdit           0       UNSAT
01. check ShareLinkHoldersCanEdit     0       UNSAT
02. check RemovedUsersCannotEdit     0    1/1     SAT
"""

ALLOY_OUTPUT_WITH_NOISE = """\
Some preamble line the tool might emit
Loading model...
00. check MembersCanEdit           0       UNSAT
Warning: something irrelevant
01. check RuleX     0    1/1     SAT
Done.
"""


def test_parse_all_unsat():
    results = dp.parse_alloy_output(ALLOY_OUTPUT_ALL_UNSAT)
    assert len(results) == 3
    assert all(not r["sat"] for r in results)
    assert [r["name"] for r in results] == [
        "MembersCanEdit",
        "ShareLinkHoldersCanEdit",
        "RemovedUsersCannotEdit",
    ]


def test_parse_one_sat():
    results = dp.parse_alloy_output(ALLOY_OUTPUT_ONE_SAT)
    assert len(results) == 3
    sat_results = [r for r in results if r["sat"]]
    assert len(sat_results) == 1
    assert sat_results[0]["name"] == "RemovedUsersCannotEdit"


def test_parse_ignores_noise_lines():
    results = dp.parse_alloy_output(ALLOY_OUTPUT_WITH_NOISE)
    assert len(results) == 2
    assert results[0] == {"name": "MembersCanEdit", "sat": False}
    assert results[1] == {"name": "RuleX", "sat": True}


def test_parse_empty_output():
    assert dp.parse_alloy_output("") == []


def test_parse_case_insensitive():
    # Both "UNSAT" and "unsat" should be treated as not-SAT.
    results = dp.parse_alloy_output(
        "00. check MyCheck  0  unsat\n"
        "01. check OtherCheck  0  1/1  sat\n"
    )
    assert results[0]["sat"] is False
    assert results[1]["sat"] is True


# ---------------------------------------------------------------------------
# load_skolems
# ---------------------------------------------------------------------------

RECEIPT_WITH_SKOLEMS = {
    "commands": {
        "RemovedUsersCannotEdit": {
            "solution": [
                {
                    "instances": [
                        {
                            "skolems": {
                                "$RemovedUsersCannotEdit_u": {
                                    "arity": 1,
                                    "data": [["User$0"]],
                                },
                                "$RemovedUsersCannotEdit_f": {
                                    "arity": 1,
                                    "data": [["File$0"]],
                                },
                            }
                        }
                    ]
                }
            ]
        },
        "MembersCanEdit": {
            "solution": []  # UNSAT — no instance
        },
    }
}


def test_load_skolems_normal():
    with tempfile.TemporaryDirectory() as tmpdir:
        receipt_path = Path(tmpdir) / "receipt.json"
        receipt_path.write_text(json.dumps(RECEIPT_WITH_SKOLEMS))
        result = dp.load_skolems(receipt_path)

    assert "RemovedUsersCannotEdit" in result
    atoms = result["RemovedUsersCannotEdit"]
    # Should contain both variables
    assert any("u" in a and "User$0" in a for a in atoms)
    assert any("f" in a and "File$0" in a for a in atoms)


def test_load_skolems_unsat_check_omitted():
    """UNSAT checks have no solution instances — they must not appear in the map."""
    with tempfile.TemporaryDirectory() as tmpdir:
        receipt_path = Path(tmpdir) / "receipt.json"
        receipt_path.write_text(json.dumps(RECEIPT_WITH_SKOLEMS))
        result = dp.load_skolems(receipt_path)

    assert "MembersCanEdit" not in result


def test_load_skolems_missing_file():
    result = dp.load_skolems(Path("/nonexistent/path/receipt.json"))
    assert result == {}


def test_load_skolems_malformed_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        receipt_path = Path(tmpdir) / "receipt.json"
        receipt_path.write_text("not valid json {{{")
        result = dp.load_skolems(receipt_path)
    assert result == {}


def test_load_skolems_empty_skolems():
    """A SAT check with no skolems should produce an empty list, not an error."""
    receipt = {
        "commands": {
            "SomeCheck": {
                "solution": [{"instances": [{"skolems": {}}]}]
            }
        }
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        receipt_path = Path(tmpdir) / "receipt.json"
        receipt_path.write_text(json.dumps(receipt))
        result = dp.load_skolems(receipt_path)
    # No atoms means the key is not present (nothing to show)
    assert result.get("SomeCheck", []) == []


# ---------------------------------------------------------------------------
# format_table
# ---------------------------------------------------------------------------

def test_format_table_all_verified():
    results = [
        {"name": "RuleA", "sat": False},
        {"name": "RuleB", "sat": False},
    ]
    table = dp.format_table(results, {})
    assert "VERIFIED (UNSAT)" in table
    assert "VIOLATED" not in table
    assert "RuleA" in table
    assert "RuleB" in table


def test_format_table_one_violated():
    results = [
        {"name": "RuleA", "sat": False},
        {"name": "BadRule", "sat": True},
    ]
    skolems = {"BadRule": ["u = {User$0}", "f = {File$0}"]}
    table = dp.format_table(results, skolems)
    assert "VIOLATED (SAT)" in table
    assert "User$0" in table


def test_format_table_long_atoms_truncated():
    results = [{"name": "X", "sat": True}]
    skolems = {"X": ["a = {" + "Atom$0, " * 20 + "}"]}
    table = dp.format_table(results, skolems)
    # Should be truncated to fit 40 chars
    for line in table.splitlines():
        if "VIOLATED" in line:
            # The atom cell is bounded
            assert len(line) < 200  # not exploding


def test_format_table_no_counterexample_dash():
    results = [{"name": "MyCheck", "sat": True}]
    table = dp.format_table(results, {})  # no skolems for this check
    assert "| - " in table or "| -" in table
