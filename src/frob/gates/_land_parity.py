"""frob.gates._land_parity -- LANDPARITY001/LANDPARITY002 (T-3456).

T-3302's investigation (F-032/F-051) found three land-only checks with no
`frob.gates` rule behind them at all: the T-2114 new-public-symbol doc/
test-edge check, the diff-scoped ARCH001 (new-or-worsened long function)
check, and CrossTicketLeakage. Each is an ad-hoc CLI-side assertion in
`frob.app.ticket_runner._land_cmd`/`frob.tickets._land` that logs and
calls `sys.exit(1)` -- never a `Violation`-producing gate function
`run_gates` dispatches -- so `frob check --ticket <id>`/`frob ticket
close` structurally cannot see any of the three: there is no rule for
either command's gate loop to run. A ticket could pass `frob check`
clean and still get refused at land time for a finding it had no way to
see coming.

THIS MODULE covers the first two (LANDPARITY001 for T-2114,
LANDPARITY002 for the diff-scoped ARCH001 variant) -- both are pure
functions of `(worktree, merge_base, touched_paths)` with no worktree-
vs-main comparison beyond an ordinary `working_diff`, so wiring them into
`frob check` needs nothing `frob check` cannot already provide.
CrossTicketLeakage is NOT here: `frob.tickets._land._check_cross_ticket_
leakage` needs `worktree`/`base_ref` context specifically about the LAND
being performed (which other ticket's lease overlaps THIS one's touched
files), not a property of `root`'s tree alone the way every other
`frob.gates` rule is -- exposing it needs `frob check` to thread
worktree-vs-main comparison context through generically, which it does
not do today. Filed as a separate follow-up (T-3456's own body already
names this as the (b) case to scope out separately if (a) is infeasible
for it) rather than forced here.

REUSE, NOT REIMPLEMENTATION: every actual finding computation below is a
deferred import of the SAME pure function
`frob.app.ticket_runner._land_cmd`'s own land-time assertions already
call (`_new_public_symbols_missing_doc_or_test_edge`/`_new_or_worsened_
long_functions_in_diff`) -- this module adds zero new detection logic,
only a `frob check`-callable wrapper around logic that already existed
and was already tested. The import is deferred (call-time, not module-
top-level) for two reasons: (1) `_land_cmd.py` was under an exclusive
scope lease held by a concurrent ticket (T-2642) for this entire
session, so genuinely MOVING the pure functions out of it (the ticket
body's own suggested end state: "extracting the pure logic to a place
BOTH `_land_cmd.py`/`_land.py` and the new gate can import from") was
not available this round -- a real, scheduling-only obstacle, the same
shape T-2913's own T-2609 lease conflict was; (2) even once that lease
clears, `_land_cmd.py` importing `frob.gates._models` at its own module
top level means a module-level import in the other direction here would
be circular. FOLLOW-UP FILED: once `_land_cmd.py`'s lease is free, move
`_new_public_symbols_missing_doc_or_test_edge`/`_new_or_worsened_long_
functions_in_diff` (and their own shared helpers `_is_generated_or_test_
path`/`_public_top_level_defs`/`_frob_directive_block`/`_DOC_TEST_EDGE_
FAMILIES`) INTO this module for real, so `_land_cmd.py` imports FROM
here instead of the reverse -- the end state this docstring's own
reasoning already points at.

`[arch.layering]` (frob.toml) is declared but NOT wired into `frob
check` yet (T-0620, that table's own comment) -- this module's `frob.
gates` -> `frob.app.ticket_runner` import direction trips no live
enforcement today, but is still the wrong direction long-term; the
follow-up above is how it gets corrected.
"""

# frob:ticket T-3456

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import working_diff
from frob.logging import get_logger

_log = get_logger(__name__)


def _land_parity_diff(root: Path) -> tuple[str, frozenset[str]] | None:
    """`(merge_base, touched_paths)` from `working_diff(root, "main")` --
    the SAME diff source `frob.app.ticket_runner._land_cmd.
    _land_touched_paths` uses at land time (T-1404), computed ONCE per
    gate call so a `frob check` run in a ticket's own worktree sees the
    identical touched-file set the eventual land will diff against.
    `None` when the diff cannot be computed (no merge-base, detached
    HEAD, a `git` spawn failure) -- both gate functions below degrade to
    `()` (no finding) rather than guess at a touched set they cannot
    verify, matching every diff-scoped land-time check's own fail-open
    posture."""
    diff_result = working_diff(root, "main")
    if diff_result.is_err:
        _log.debug(
            "land_parity: could not compute the working diff (%s) -- "
            "skipping (unmeasured, not zero)",
            diff_result.danger_err,
        )
        return None
    touched = frozenset(hunk.file for hunk in diff_result.danger_ok.hunks)
    if not touched:
        return None
    return diff_result.danger_ok.base, touched


# frob:ticket T-3456
# frob:doc docs/modules/gates.md#land-parity-landparity001landparity002-t-3456
# frob:enforces CHK-GATE-LANDPARITY001
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_new_public_symbol_missing_both_directives_fires  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_new_public_symbol_with_both_directives_is_quiet  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_no_diff_is_quiet  # noqa: E501
def land_parity_doc_test_gate(root: Path) -> tuple[Violation, ...]:
    """LANDPARITY001 (T-3456): `frob check`-callable wrapper around
    `frob.app.ticket_runner._land_cmd._new_public_symbols_missing_doc_or_
    test_edge` (T-2114) -- a new public top-level symbol in this diff
    with no `frob:doc`/`frob:tests` directive (or matching `frob:waive`)
    directly above it. Reuses that function unchanged (this module's own
    docstring explains why the import is deferred and why the module
    reports this rather than owning the detection itself); `()` when the
    touched-file set cannot be computed (`_land_parity_touched_paths`
    returned `None`) or is empty."""
    diff = _land_parity_diff(root)
    if diff is None:
        return ()
    merge_base, touched_paths = diff

    from frob.app.ticket_runner._land_cmd import (
        _new_public_symbols_missing_doc_or_test_edge,
    )

    findings = _new_public_symbols_missing_doc_or_test_edge(
        root, merge_base, touched_paths
    )
    violations: list[Violation] = []
    for rel_path, name, lineno, missing_families in findings:
        missing = ", ".join(missing_families)
        violations.append(
            Violation(
                rule="LANDPARITY001",
                severity=Severity.ERROR,
                file=rel_path,
                line=lineno,
                message=(
                    f"LANDPARITY001: {rel_path}:{lineno} new public symbol "
                    f"{name!r} has no {missing} directive above it (T-2114) "
                    f"-- add the missing directive(s), or a matching "
                    f"`frob:waive` if intentionally undocumented/untested"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-3456
# frob:doc docs/modules/gates.md#land-parity-landparity001landparity002-t-3456
# frob:enforces CHK-GATE-LANDPARITY002
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_new_over_threshold_function_fires  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_pre_existing_over_threshold_function_merely_touched_is_quiet  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_no_diff_is_quiet  # noqa: E501
def land_parity_long_function_gate(root: Path) -> tuple[Violation, ...]:
    """LANDPARITY002 (T-3456): `frob check`-callable wrapper around
    `frob.app.ticket_runner._land_cmd._new_or_worsened_long_functions_in_
    diff` (T-2214) -- a function this diff adds or modifies that crosses
    ARCH001's long-AND-complex threshold in the current worktree content
    but was NOT already over it at `merge_base` (a function already over
    threshold before this diff and merely touched is NOT blamed on this
    ticket, T-2214's own acceptance criterion). A distinct rule id from
    plain `ARCH001` deliberately (not a re-fire of that repo-wide rule):
    `ARCH001` reports EVERY over-threshold function found by an unscoped
    walk, new or pre-existing; `LANDPARITY002` reports only what THIS
    diff newly pushed over the line, the narrower, attributable-only
    claim T-2214 actually makes -- collapsing the two into one rule id
    would either double-report a pre-existing ARCH001 finding under a
    second name, or silently narrow what plain ARCH001 already covers."""
    diff = _land_parity_diff(root)
    if diff is None:
        return ()
    merge_base, touched_paths = diff

    from frob.app.ticket_runner._land_cmd import (
        _new_or_worsened_long_functions_in_diff,
    )

    findings = _new_or_worsened_long_functions_in_diff(root, merge_base, touched_paths)
    violations: list[Violation] = []
    for rel_path, symref, lineno, n_lines in findings:
        violations.append(
            Violation(
                rule="LANDPARITY002",
                severity=Severity.ERROR,
                file=rel_path,
                line=lineno,
                message=(
                    f"LANDPARITY002: {rel_path}:{lineno} {symref} is now "
                    f"{n_lines} line(s), past ARCH001's long-AND-complex "
                    f"threshold, and was NOT already over it before this "
                    f"diff (T-2214) -- split the function, or add "
                    f'`frob:waive ARCH001 reason="..."` above the def if it '
                    f"genuinely does not need to shrink"
                ),
            )
        )
    return tuple(violations)


__all__ = ["land_parity_doc_test_gate", "land_parity_long_function_gate"]
