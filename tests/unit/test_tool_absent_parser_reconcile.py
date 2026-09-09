"""T-4358: ruff-check's and ty's parsers must agree on the "tool absent
from the target project" shape (T-4354's `tool_absent_from_project`) --
UNMEASURED, never a hard ERROR -- while still keeping the OTHER shape
each already handled distinct: a present-but-broken tool producing
unparsable output is still a genuine hard error.

The real "Failed to spawn" capture (T-4354's doctrine doc,
docs/modules/process.md) looks like::

    error: Failed to spawn: `<tool>`
      Caused by: No such file or directory (os error 2)

exit code 2.
"""

from __future__ import annotations

from frob.process.parsers.ruff import parse_ruff, parse_ruff_json
from frob.process.parsers.ty import parse_ty

_RUFF_SPAWN_FAILURE_STDERR = "error: Failed to spawn: `ruff`\n  Caused by: No such file or directory (os error 2)\n"
_TY_SPAWN_FAILURE_STDERR = "error: Failed to spawn: `ty`\n  Caused by: No such file or directory (os error 2)\n"


# frob:ticket T-4358
class TestRuffAbsentToolIsUnmeasured:
    """T-4358: ruff-check's parser must stop hard-ERRORing on the "tool
    absent from the target project" shape once `stderr` proves that is
    what happened -- matching `parse_ty`'s existing treatment of the
    identical condition."""

    def test_spawn_failure_is_unmeasured_not_error(self) -> None:
        r = parse_ruff_json("", exit_code=2, stderr=_RUFF_SPAWN_FAILURE_STDERR)
        assert r.diagnostics == []
        assert r.error_count == 0
        assert not r.passed

    def test_autodetect_wrapper_forwards_stderr(self) -> None:
        r = parse_ruff("", exit_code=2, stderr=_RUFF_SPAWN_FAILURE_STDERR)
        assert r.diagnostics == []
        assert r.error_count == 0

    def test_whitespace_only_stdout_also_classified(self) -> None:
        r = parse_ruff_json("   \n", exit_code=2, stderr=_RUFF_SPAWN_FAILURE_STDERR)
        assert r.diagnostics == []


# frob:ticket T-4358
class TestRuffEmptyOutputWithoutStderrEvidenceStaysAnError:
    """Without `stderr` proving the absent-tool shape, empty stdout keeps
    T-4308's original hard-ERROR behavior -- the distinction that must
    survive: "not installed" is unmeasured, but "ran and produced
    nothing parseable, for an unknown reason" is still a real failure."""

    def test_no_stderr_argument_is_still_an_error(self) -> None:
        r = parse_ruff_json("", exit_code=2)
        assert r.error_count >= 1
        assert "did not run" in r.diagnostics[0].message

    def test_exit_code_2_with_unrelated_stderr_is_still_an_error(self) -> None:
        r = parse_ruff_json("", exit_code=2, stderr="some unrelated crash text\n")
        assert r.error_count >= 1

    def test_matching_stderr_but_wrong_exit_code_is_still_an_error(self) -> None:
        # `tool_absent_from_project` requires exit code 2 exactly.
        r = parse_ruff_json("", exit_code=1, stderr=_RUFF_SPAWN_FAILURE_STDERR)
        assert r.error_count >= 1


# frob:ticket T-4358
class TestRuffPresentButBrokenStaysAnError:
    """A present tool that ran and produced genuinely unparsable output
    must NOT be swallowed into the new UNMEASURED path -- T-4308's
    malformed-JSON case is unrelated to T-4354's absent-tool case and
    must stay a hard error regardless of `stderr` content."""

    def test_truncated_json_is_still_malformed_even_with_stderr_set(self) -> None:
        r = parse_ruff_json(
            '[{"filename": "a.py", "code": "E501", "mess',
            exit_code=1,
            stderr=_RUFF_SPAWN_FAILURE_STDERR,
        )
        assert r.error_count >= 1
        assert "malformed JSON" in r.diagnostics[0].message

    def test_clean_run_unaffected(self) -> None:
        r = parse_ruff_json("[]", exit_code=0, stderr="")
        assert r.exit_code == 0
        assert r.diagnostics == []


# frob:ticket T-4358
class TestTyAbsentToolIsUnmeasured:
    """T-4358: `parse_ty` now recognizes the absent-tool shape explicitly
    (its real caller already concatenates stdout+stderr into the single
    `stdout` argument, so the spawn-failure text is visible here)."""

    def test_spawn_failure_text_is_unmeasured(self) -> None:
        r = parse_ty(_TY_SPAWN_FAILURE_STDERR, exit_code=2)
        assert r.diagnostics == []
        assert r.error_count == 0
        assert not r.passed

    def test_unrelated_nonzero_exit_with_no_matches_still_empty(self) -> None:
        # Pre-existing T-4309 fallthrough shape must be unchanged.
        r = parse_ty("some unrecognized ty output\n", exit_code=1)
        assert r.diagnostics == []

    def test_real_diagnostic_still_parses_even_with_nonzero_exit(self) -> None:
        text = "error[unresolved-import]: could not resolve\n  --> a.py:1:1\n"
        r = parse_ty(text, exit_code=1)
        assert r.error_count == 1


# frob:ticket T-4358
class TestBothParsersAgree:
    """The reconciliation itself: identical spawn-failure shape, from
    each tool's own parser, must classify the same way."""

    def test_ruff_and_ty_both_report_zero_errors_on_absent_tool(self) -> None:
        ruff_r = parse_ruff_json("", exit_code=2, stderr=_RUFF_SPAWN_FAILURE_STDERR)
        ty_r = parse_ty(_TY_SPAWN_FAILURE_STDERR, exit_code=2)
        assert ruff_r.error_count == 0
        assert ty_r.error_count == 0
        assert ruff_r.diagnostics == []
        assert ty_r.diagnostics == []
