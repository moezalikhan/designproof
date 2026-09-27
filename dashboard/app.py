"""DesignProof Dashboard — Streamlit app.

Presents the DesignProof verification results for the designproof repository:
policy, results table, violation cards, Alloy models, and a live check runner.
"""

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

# Project root is one level up from dashboard/
ROOT = Path(__file__).parent.parent

POLICY_MD      = ROOT / "policy" / "permission_policy.md"
MODEL_BEFORE   = ROOT / "models" / "permissions_before.als"
MODEL_FIX1     = ROOT / "models" / "permissions_fix1.als"
MODEL_AFTER    = ROOT / "models" / "permissions.als"
RESULTS_BEFORE = ROOT / "results_before.json"
RESULTS_FIX1   = ROOT / "results_fix1.json"
RESULTS_AFTER  = ROOT / "results.json"
DESIGNPROOF    = ROOT / "designproof.py"
JAR_PATH       = ROOT / "org.alloytools.alloy.dist.jar"
JAR_URL        = (
    "https://github.com/AlloyTools/org.alloytools.alloy/releases/download/"
    "v6.2.0/org.alloytools.alloy.dist.jar"
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="DesignProof",
    page_icon="🔍",
    layout="wide",
)

# Minimal CSS: tighten vertical rhythm, style verdict badges.
# Uses CSS variables so it works in both light and dark mode.
st.markdown(
    """
    <style>
    .dp-badge-verified {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.82em;
        font-weight: 600;
        background: #d1fae5;
        color: #065f46;
    }
    .dp-badge-violated {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.82em;
        font-weight: 600;
        background: #fee2e2;
        color: #991b1b;
    }
    /* Dark-mode overrides */
    @media (prefers-color-scheme: dark) {
        .dp-badge-verified { background: #064e3b; color: #6ee7b7; }
        .dp-badge-violated { background: #7f1d1d; color: #fca5a5; }
    }
    .dp-rule-table th {
        text-align: left;
        padding: 6px 14px;
        border-bottom: 2px solid var(--primary-color, #3b82d4);
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.7;
    }
    .dp-rule-table td {
        padding: 8px 14px;
        vertical-align: top;
        border-bottom: 1px solid rgba(127,127,127,0.15);
        font-size: 0.92em;
        line-height: 1.4;
    }
    .dp-rule-table tr:last-child td { border-bottom: none; }
    .dp-card {
        border-left: 4px solid #ef4444;
        padding: 12px 18px;
        border-radius: 4px;
        background: rgba(239,68,68,0.06);
        margin-bottom: 8px;
    }
    h1 { margin-bottom: 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _badge(verified: bool) -> str:
    if verified:
        return '<span class="dp-badge-verified">✓ VERIFIED</span>'
    return '<span class="dp-badge-violated">✗ VIOLATED</span>'


def _load_json(path: Path) -> list[dict]:
    """Load a results JSON file; return empty list on failure."""
    try:
        with path.open() as f:
            return json.load(f)
    except Exception:
        return []


def _results_table_html(results: list[dict]) -> str:
    """Render a list of check-result dicts as an HTML table."""
    rows = ""
    for r in results:
        badge = _badge(not r.get("violated", False))
        atoms = r.get("counterexample_atoms", [])
        atom_str = "; ".join(atoms) if atoms else "—"
        rows += (
            f"<tr>"
            f"<td><code>{r['check']}</code></td>"
            f"<td>{badge}</td>"
            f"<td style='font-size:0.82em;opacity:0.75;'>{atom_str}</td>"
            f"</tr>"
        )
    return (
        "<table class='dp-rule-table' style='width:100%;border-collapse:collapse;'>"
        "<thead><tr>"
        "<th>Check</th><th>Verdict</th><th>Counterexample atoms</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )


def _download_jar() -> tuple[bool, str]:
    """Download the Alloy 6.2.0 jar to JAR_PATH if not already present.

    Returns (success, message).
    """
    if JAR_PATH.exists():
        return True, f"Jar already present at `{JAR_PATH.name}`."
    try:
        with st.spinner("Downloading Alloy 6.2.0 jar (≈ 30 MB) …"):
            urllib.request.urlretrieve(JAR_URL, JAR_PATH)
        return True, "Downloaded Alloy 6.2.0 jar successfully."
    except Exception as exc:
        return False, f"Download failed: {exc}"


def _run_designproof(model: Path, output_dir: Path, results_json: Path) -> tuple[int, str, str]:
    """Run designproof.py on *model* and return (returncode, stdout, stderr)."""
    cmd = [
        sys.executable,
        str(DESIGNPROOF),
        str(model),
        "--jar", str(JAR_PATH),
        "--output-dir", str(output_dir),
        "--results-json", str(results_json),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# ── Section 1: Header ──────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

st.title("DesignProof")
st.caption("Checks that your code does what your policy says.")
st.divider()

# ---------------------------------------------------------------------------
# ── Section 2: The Policy ──────────────────────────────────────────────────
# ---------------------------------------------------------------------------

st.header("📋 Permission Policy")
try:
    policy_text = POLICY_MD.read_text()
    # Strip the top-level "# Permission Policy" heading to avoid duplication
    # with the section header rendered by st.header above.
    lines = policy_text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    policy_text = "\n".join(lines).lstrip("\n")
    st.markdown(policy_text)
except FileNotFoundError:
    st.warning(f"Policy file not found at `{POLICY_MD}`.")

st.divider()

# ---------------------------------------------------------------------------
# ── Section 3: Results Table ───────────────────────────────────────────────
# ---------------------------------------------------------------------------

st.header("📊 Verification Results")
st.markdown(
    "Each policy rule checked with the Alloy 6 Analyzer (scope 4) at three "
    "snapshots: original buggy code (`permissions_before.als`), "
    "after fix 1 only (`permissions_fix1.als`), and after both fixes "
    "(`permissions.als`)."
)

# Hard-coded summary table from report.md (these are known, stable results).
RULES = [
    "Current members of a file's owning team may edit that file.",
    "A share link lets its holder edit the file (unless the holder is removed).",
    "A removed user must never edit that team's files by any route, including share links.",
]
CHECKS = ["MembersCanEdit", "ShareLinkHoldersCanEdit", "RemovedUsersCannotEdit"]

# (rule_index, before, after_fix1, after_fix2)
# True = VERIFIED (UNSAT), False = VIOLATED (SAT)
VERDICTS = [
    (0, True,  False, True),   # Rule 1: OK → broken by fix 1 → fixed by fix 2
    (1, True,  True,  True),   # Rule 2: OK throughout
    (2, False, True,  True),   # Rule 3: VIOLATED originally → fixed by fix 1
]

table_rows = ""
for rule_idx, before, after1, after2 in VERDICTS:
    rule_text = RULES[rule_idx]
    check_name = CHECKS[rule_idx]
    table_rows += (
        f"<tr>"
        f"<td><code>{check_name}</code><br>"
        f"<span style='font-size:0.82em;opacity:0.7;'>{rule_text}</span></td>"
        f"<td style='text-align:center;'>{_badge(before)}</td>"
        f"<td style='text-align:center;'>{_badge(after1)}</td>"
        f"<td style='text-align:center;'>{_badge(after2)}</td>"
        f"</tr>"
    )

summary_html = (
    "<table class='dp-rule-table' style='width:100%;border-collapse:collapse;'>"
    "<thead><tr>"
    "<th style='width:45%'>Rule / Check</th>"
    "<th style='text-align:center;'>Before any fix</th>"
    "<th style='text-align:center;'>After fix 1</th>"
    "<th style='text-align:center;'>After fix 2</th>"
    "</tr></thead>"
    f"<tbody>{table_rows}</tbody>"
    "</table>"
)
st.markdown(summary_html, unsafe_allow_html=True)

st.caption(
    "**SAT** = Alloy found a counterexample → rule violated. "
    "**UNSAT** = no counterexample up to scope 4 → rule holds. "
    "All three snapshots were checked by running `designproof.py` on the "
    "corresponding Alloy model; results are from `results_before.json`, "
    "`results_fix1.json`, and `results.json`."
)
st.divider()

# ---------------------------------------------------------------------------
# ── Section 4: Violation Cards ─────────────────────────────────────────────
# ---------------------------------------------------------------------------

st.header("🔴 Violations Found")

# ── Violation 1 ─────────────────────────────────────────────────────────────
st.subheader("Violation 1 — Rule 3: Removed user retains edit access via share link")
st.markdown(
    "<div class='dp-card'>"
    "<strong>Check:</strong> <code>RemovedUsersCannotEdit</code> &nbsp;|&nbsp; "
    "<strong>Model state:</strong> original buggy code"
    "</div>",
    unsafe_allow_html=True,
)

with st.expander("🔍 Counterexample (plain English)", expanded=True):
    st.markdown(
        """
**Witness produced by Alloy (`check RemovedUsersCannotEdit for 4` → SAT):**

- Witness user: `User$0`; witness file: `File$0`.
- `File$0` belongs to a team where `User$0` is in `removed` (and **not** in `members`).
- A `ShareLink` exists with `file = File$0` and `holder = User$0`.

In this state, `can_edit("User$0", "File$0")` returns **True** because the
share-link branch of the `or` succeeds — `team.removed` is never consulted.

**In concrete terms:** Eve is added to a team, receives a share link to one
of the team's files, is then removed from the team, and can still edit that
file via the share link. Rule 3 is violated.
"""
    )

with st.expander("🛠️ How it was detected"):
    st.markdown(
        """
The Alloy Analyzer was run on `models/permissions_before.als`, which faithfully
mirrors the original `can_edit` code (no `removed` guard on the share-link branch).

`check RemovedUsersCannotEdit for 4` returned **SAT** — the Analyzer found and
returned the counterexample above.
"""
    )

with st.expander("🧪 Failing test"):
    st.code(
        """\
def test_removed_member_with_share_link_cannot_edit():
    team_id = _create_team()
    _add_member(team_id, "eve")
    file_id = _create_file(team_id)
    _create_share_link(file_id, "eve")              # share link granted while member
    client.delete(f"/teams/{team_id}/members/eve")  # then removed
    assert _edit(file_id, "eve") == 403             # must be denied
    # Before the fix this returned 200 (edit permitted — bug confirmed)
""",
        language="python",
    )

with st.expander("✅ Fix applied"):
    st.markdown(
        "**File:** `demo_app/permissions.py`\n\n"
        "Added an early-return guard immediately after the team lookup, "
        "before the membership and share-link checks:"
    )
    st.code(
        """\
# Rule 3: removed users are denied via every route, including share links.
if user_id in team.removed:
    return False
""",
        language="python",
    )

st.markdown("---")

# ── Violation 2 ─────────────────────────────────────────────────────────────
st.subheader("Violation 2 — Rule 1: Re-added member is incorrectly blocked")
st.markdown(
    "<div class='dp-card'>"
    "<strong>Check:</strong> <code>MembersCanEdit</code> &nbsp;|&nbsp; "
    "<strong>Model state:</strong> after fix 1, before fix 2"
    "</div>",
    unsafe_allow_html=True,
)

with st.expander("🔍 Counterexample (plain English)", expanded=True):
    st.markdown(
        """
- Frank is added to a team and can edit (`200`).
- Frank is removed: `removed = {frank}`, `members = {}`.
- Frank is re-added: `members = {frank}`, but `removed = {frank}` is **not** cleared  
  because `add_member` only calls `team.members.add(user_id)` — it does not call  
  `team.removed.discard(user_id)`.
- Frank is now in **both** `members` and `removed` simultaneously.
- `can_edit` hits `if user_id in team.removed: return False` and denies Frank,  
  even though he is a current member. Rule 1 is violated.
"""
    )

with st.expander("🛠️ How it was detected"):
    st.markdown(
        """
**First found by code reading and a direct runtime test.**

After applying fix 1, `add_member` in `main.py` was read carefully and it was observed
that `team.removed.discard(user_id)` was missing. A direct Python test confirmed
that a re-added user receives `403` instead of `200`.

**Then confirmed by Alloy:** `models/permissions_fix1.als` models exactly this
intermediate state — `can_edit` has the removed guard but `add_member` does not
clear `removed`. Running `check MembersCanEdit for 4` on that model returns
**SAT**, with counterexample `u = {User$0}, f = {File$0}` — a user in both
`members` and `removed` who is denied despite being a current member.

After fix 2, the model gains `fact MembersRemovedDisjoint` (reflecting the fixed
`add_member` invariant) and `check MembersCanEdit` returns **UNSAT**, confirming
the fix is sound.
"""
    )

with st.expander("🧪 Failing test"):
    st.code(
        """\
def test_readded_member_can_edit():
    team_id = _create_team()
    _add_member(team_id, "frank")
    file_id = _create_file(team_id)
    assert _edit(file_id, "frank") == 200       # member can edit
    client.delete(f"/teams/{team_id}/members/frank")
    _add_member(team_id, "frank")               # re-added
    assert _edit(file_id, "frank") == 200       # must be allowed again
    # Before fix 2 this returned 403 (bug confirmed)
""",
        language="python",
    )

with st.expander("✅ Fix applied"):
    st.markdown(
        "**File:** `demo_app/main.py`, `add_member` endpoint\n\n"
        "Added one line to clear `removed` when a user is (re-)added to a team:"
    )
    st.code(
        """\
team.members.add(body.user_id)
team.removed.discard(body.user_id)   # ← added: clear removed on re-add
""",
        language="python",
    )

st.divider()

# ---------------------------------------------------------------------------
# ── Section 5: Alloy Models Side by Side ───────────────────────────────────
# ---------------------------------------------------------------------------

st.header("⚙️ Alloy Models")
st.markdown(
    "The three Alloy 6 models that were checked — one per snapshot. "
    "Key differences are highlighted in the comments inside each model."
)

tab_b, tab_f, tab_a = st.tabs(
    ["Before any fix", "After fix 1 only", "After both fixes"]
)

with tab_b:
    st.caption("`models/permissions_before.als`")
    try:
        st.code(MODEL_BEFORE.read_text(), language="alloy")
    except FileNotFoundError:
        st.warning("Model file not found.")

with tab_f:
    st.caption("`models/permissions_fix1.als`")
    try:
        st.code(MODEL_FIX1.read_text(), language="alloy")
    except FileNotFoundError:
        st.warning("Model file not found.")

with tab_a:
    st.caption("`models/permissions.als`")
    try:
        st.code(MODEL_AFTER.read_text(), language="alloy")
    except FileNotFoundError:
        st.warning("Model file not found.")

st.divider()

# ---------------------------------------------------------------------------
# ── Section 6: Live Check ──────────────────────────────────────────────────
# ---------------------------------------------------------------------------

st.header("▶️ Live Check")
st.markdown(
    "Click the button to run `designproof.py` on all three models using the "
    "Alloy 6.2.0 jar. If Java is not available, saved results are shown instead."
)

java_available = shutil.which("java") is not None

if not java_available:
    st.info(
        "ℹ️  `java` was not found on PATH. "
        "Showing saved results from the last successful run. "
        "Install Java 11+ and reload to enable the live check."
    )

run_clicked = st.button(
    "🚀 Run Live Check",
    disabled=False,
    help="Downloads the Alloy jar if needed, then runs all three models.",
)

if run_clicked:
    if not java_available:
        # Fallback — show saved results
        st.warning("Java not available — displaying saved results.")
        _show_live = False
    else:
        # Step 1: ensure jar is present
        ok, msg = _download_jar()
        if not ok:
            st.error(f"Could not obtain the Alloy jar: {msg}")
            st.warning("Falling back to saved results.")
            _show_live = False
        else:
            if "Downloaded" in msg:
                st.success(msg)
            _show_live = True

    if _show_live:
        tmp_before_json = ROOT / "_live_results_before.json"
        tmp_fix1_json   = ROOT / "_live_results_fix1.json"
        tmp_after_json  = ROOT / "_live_results_after.json"

        with st.spinner("Running Alloy on `permissions_before.als` …"):
            rc_b, out_b, err_b = _run_designproof(
                MODEL_BEFORE,
                ROOT / "permissions_before",
                tmp_before_json,
            )

        with st.spinner("Running Alloy on `permissions_fix1.als` …"):
            rc_f, out_f, err_f = _run_designproof(
                MODEL_FIX1,
                ROOT / "permissions_fix1",
                tmp_fix1_json,
            )

        with st.spinner("Running Alloy on `permissions.als` …"):
            rc_a, out_a, err_a = _run_designproof(
                MODEL_AFTER,
                ROOT / "permissions",
                tmp_after_json,
            )

        results_b = _load_json(tmp_before_json)
        results_f = _load_json(tmp_fix1_json)
        results_a = _load_json(tmp_after_json)

        if not results_b or not results_f or not results_a:
            st.error(
                "Alloy run did not produce parseable results. "
                "Check that Java 11+ is installed and the jar is valid."
            )
            for label, err in [("before", err_b), ("fix1", err_f), ("after", err_a)]:
                if err:
                    with st.expander(f"Alloy stderr ({label} model)"):
                        st.code(err)
        else:
            lc1, lc2, lc3 = st.columns(3)
            with lc1:
                st.subheader("Before any fix")
                st.markdown(_results_table_html(results_b), unsafe_allow_html=True)
                if rc_b == 1:
                    st.error("⚠ Rules violated.")
                elif rc_b == 0:
                    st.success("All rules verified.")
                with st.expander("Raw output"):
                    st.code(out_b or err_b or "(no output)")
            with lc2:
                st.subheader("After fix 1 only")
                st.markdown(_results_table_html(results_f), unsafe_allow_html=True)
                if rc_f == 1:
                    st.error("⚠ Rules violated.")
                elif rc_f == 0:
                    st.success("All rules verified.")
                with st.expander("Raw output"):
                    st.code(out_f or err_f or "(no output)")
            with lc3:
                st.subheader("After both fixes")
                st.markdown(_results_table_html(results_a), unsafe_allow_html=True)
                if rc_a == 1:
                    st.error("⚠ Rules violated.")
                elif rc_a == 0:
                    st.success("✓ All rules verified.")
                with st.expander("Raw output"):
                    st.code(out_a or err_a or "(no output)")

    else:
        # Show saved results as fallback (three columns)
        results_b_saved = _load_json(RESULTS_BEFORE)
        results_f_saved = _load_json(RESULTS_FIX1)
        results_a_saved = _load_json(RESULTS_AFTER)

        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            st.subheader("Before any fix — saved")
            if results_b_saved:
                st.markdown(_results_table_html(results_b_saved), unsafe_allow_html=True)
            else:
                st.warning(f"`{RESULTS_BEFORE.name}` not found.")
        with lc2:
            st.subheader("After fix 1 only — saved")
            if results_f_saved:
                st.markdown(_results_table_html(results_f_saved), unsafe_allow_html=True)
            else:
                st.warning(f"`{RESULTS_FIX1.name}` not found.")
        with lc3:
            st.subheader("After both fixes — saved")
            if results_a_saved:
                st.markdown(_results_table_html(results_a_saved), unsafe_allow_html=True)
            else:
                st.warning(f"`{RESULTS_AFTER.name}` not found.")
