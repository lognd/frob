"""T-2484 acceptance [3]: per-caller audit of `_parse_check_json`'s `None`.

`_parse_check_json` returns `None` on a decode failure -- e.g. a T-2473-
style advisory prefix corrupting `--json` stdout ahead of the payload.
Each of `_parse_check_json`'s callers must treat that `None` as
"unmeasured", never as "measured, no findings" -- the exact silent-
degradation shape T-1703 already exists to guard against elsewhere. This
module locks in the audited behavior of every current caller so a future
change that flips one of them to a false-clean read fails a test, not
just a Done report claim.

Scope note: this ticket's declared scope is `src/frob/__main__.py` only
-- these tests exercise, but never modify, the callers living in
`frob.app.ticket_runner._verify` and `frob.app.ticket_runner._rapid_
sweep`; the audit's conclusion (all four callers already correct) is
documented in T-2484's Done report.
"""

from __future__ import annotations

from pathlib import Path

# T-2473-shaped corruption: an advisory line prepended to otherwise-valid
# `frob check --json` stdout. Deliberately contains neither "## Errors"
# (only the plain-text renderer ever emits that heading) nor the literal
# "gate-summary N errors, ..." phrase the legacy-text fallback's own
# cross-check regex requires -- exercising exactly the shape T-2484's
# repro produced.
_CORRUPTED_JSON_STDOUT = (
    "frob check: 1 other check(s) already running on this host -- see "
    "`scripts/fleet_status.py` for swap/load before dispatching more "
    "(T-2473, advisory only -- this check is not deferred)\n"
    '{"path": ".", "results": [{"tool": "gate-summary", "exit_code": 0, '
    '"summary": "0 errors, 0 warnings, 0 waived"}]}'
)


# frob:ticket T-2484
class TestParseCheckJsonReturnsNoneOnCorruption:
    """`_parse_check_json` itself: the shared gate every caller below
    depends on."""

    def test_corrupted_json_stdout_is_unparsable(self) -> None:
        # frob:tests tests/unit/test_check_json_none_handling_t2484.py::TestParseCheckJsonReturnsNoneOnCorruption.test_corrupted_json_stdout_is_unparsable  # noqa: E501
        from frob.app.ticket_runner._verify import _parse_check_json

        assert _parse_check_json(_CORRUPTED_JSON_STDOUT) is None


# frob:ticket T-2484
class TestBudgetDeferredGroupsFromStdoutOnNone:
    """`_budget_deferred_groups_from_stdout`: an ADDITIVE detail, never
    the primary measured/unmeasured verdict -- an empty tuple here means
    only "no BUDGET001 deferral names recoverable", not "measured zero
    findings"."""

    def test_corrupted_stdout_yields_empty_tuple_not_a_false_claim(
        self,
    ) -> None:
        # frob:tests tests/unit/test_check_json_none_handling_t2484.py::TestBudgetDeferredGroupsFromStdoutOnNone.test_corrupted_stdout_yields_empty_tuple_not_a_false_claim  # noqa: E501
        from frob.app.ticket_runner._verify import (
            _budget_deferred_groups_from_stdout,
        )

        assert _budget_deferred_groups_from_stdout(_CORRUPTED_JSON_STDOUT) == ()


# frob:ticket T-2484
class TestParseErrorFindingsFromStdoutOnCorruption:
    """`_parse_error_findings_from_stdout`: the caller with a legacy
    plain-text fallback when `_parse_check_json` fails. Must still return
    `None` (unmeasured) on T-2473-corrupted `--json` stdout, never a
    frozenset standing in for "measured, zero errors"."""

    def test_corrupted_json_stdout_is_unmeasured_not_empty(self) -> None:
        # frob:tests tests/unit/test_check_json_none_handling_t2484.py::TestParseErrorFindingsFromStdoutOnCorruption.test_corrupted_json_stdout_is_unmeasured_not_empty  # noqa: E501
        from frob.app.ticket_runner._verify import (
            _parse_error_findings_from_stdout,
        )

        result = _parse_error_findings_from_stdout(
            "T-9999", _CORRUPTED_JSON_STDOUT, returncode=0
        )
        assert result is None


# frob:ticket T-2484
class TestMatchingErrorDiagnosticsOnNone:
    """`_rapid_sweep._matching_error_diagnostics`: must return `None`
    (never `[]`) when `_parse_check_json` cannot decode the spawn's
    stdout."""

    def test_none_data_returns_none_not_empty_list(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_json_none_handling_t2484.py::TestMatchingErrorDiagnosticsOnNone.test_none_data_returns_none_not_empty_list  # noqa: E501
        from frob.app.ticket_runner import _rapid_sweep

        class _FakeProc:
            stdout = _CORRUPTED_JSON_STDOUT

        monkeypatch.setattr(
            _rapid_sweep, "_spawn_true_count_check", lambda root, budget: _FakeProc()
        )
        result = _rapid_sweep._matching_error_diagnostics(
            root=Path("."), pairs=frozenset(), budget=100
        )
        assert result is None
