"""`frob.app.check_runner`'s `--fix` CLI wiring (T-1260): `frob check
--fix`'s orchestration of `frob.gates._fix_engine.apply_tier_a_fixes` --
fixes applied, the union of affected gates re-run once in the same
invocation, and the fixed/rolled-back/fix-its summary shape `--fix
--json` reports (docs/design/check-fix-engine.md "Gate re-run
semantics" and "Fix-it emission format")."""

from __future__ import annotations

import json
from pathlib import Path

from frob.app.check_runner import (
    _apply_tier_a_and_reverify,
    _fix_report_text,
    _result_as_json_with_fix,
)
from frob.app.config import AppConfig
from frob.check import CheckResult
from frob.process.parsers.common import Diagnostic, ToolResult


def _doc007_repo(tmp_path: Path) -> Path:
    """A tiny fixture repo with one live DOC007 finding (a `frob:tests`
    directive using pytest's `Class::method` collect-only separator) --
    the same shape `tests/test_gates.py::TestFixEngineTierA` already
    exercises for `apply_tier_a_fixes` directly; this module exercises the
    CLI-facing wiring around it instead."""
    root = tmp_path / "repo"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "mod.py").write_text(
        "# frob:tests tests/test_mod.py::TestX::test_y\ndef real():\n    pass\n",
        encoding="utf-8",
    )
    (root / "tickets.md").write_text("", encoding="utf-8")
    return root


class TestApplyTierAAndReverify:
    """`_apply_tier_a_and_reverify`: T-1260's CLI wiring of
    `apply_tier_a_fixes` plus the same-invocation gate re-run."""

    # -- acceptance [0]: a live finding is fixed and re-verified clean ------

    def test_doc007_finding_fixed_and_reverified_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify kind="unit"  # noqa: E501
        root = _doc007_repo(tmp_path)
        cfg = AppConfig(check_fix=True)
        stale_gate_result = ToolResult(
            tool="gate:DOC",
            exit_code=1,
            diagnostics=[
                Diagnostic(
                    file="src/pkg/mod.py",
                    line=1,
                    severity="error",
                    code="DOC007",
                    message="stale",
                )
            ],
            summary="1 error, 0 warnings, 0 waived",
        )
        result = CheckResult(path=str(root), results=[stale_gate_result])

        updated, fix_report = _apply_tier_a_and_reverify(cfg, root, result)

        assert len(fix_report["fixed"]) == 1
        assert fix_report["fixed"][0]["rule"] == "DOC007"
        assert fix_report["rolled_back"] == []
        assert fix_report["fixits"] == []
        assert fix_report["residual_by_rule"]["DOC007"] == 0

        rewritten = (root / "src" / "pkg" / "mod.py").read_text(encoding="utf-8")
        assert "TestX::test_y" not in rewritten
        assert "TestX.test_y" in rewritten

        # the stale gate:DOC ToolResult was replaced by a fresh re-run, not
        # left stale in `updated.results` -- no DOC007 diagnostic survives.
        assert stale_gate_result not in updated.results
        assert any(r.tool.startswith("gate") for r in updated.results)
        assert not any(
            d.code == "DOC007" for r in updated.results for d in r.diagnostics
        )

    # -- acceptance [1]-adjacent: nothing to fix is an honest no-op ---------

    def test_no_tier_a_findings_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify kind="unit"  # noqa: E501
        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "pkg" / "mod.py").write_text(
            "# frob:tests tests/test_mod.py::TestX.test_y\ndef real():\n    pass\n",
            encoding="utf-8",
        )
        (root / "tickets.md").write_text("", encoding="utf-8")
        cfg = AppConfig(check_fix=True)
        clean_result = CheckResult(path=str(root), results=[])

        updated, fix_report = _apply_tier_a_and_reverify(cfg, root, clean_result)

        assert fix_report == {"fixed": [], "rolled_back": [], "fixits": []}
        assert updated is clean_result

    # -- acceptance [2]-adjacent: a Tier-C (no-handler) finding is untouched

    def test_finding_with_no_tier_a_handler_is_never_mutated_or_claimed(
        self, tmp_path: Path
    ) -> None:
        """A rule with no Tier-A handler (e.g. a bare `TODO` comment,
        TODO001) is never rewritten or reported as fixed, even in the same
        run that fixes a genuine DOC007 finding alongside it -- `--fix`
        only ever touches what its registered handler table covers."""
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify kind="unit"  # noqa: E501
        root = _doc007_repo(tmp_path)
        other = root / "src" / "pkg" / "other.py"
        other_text = "# TODO: something undone\ndef g():\n    pass\n"
        other.write_text(other_text, encoding="utf-8")
        cfg = AppConfig(check_fix=True)
        result = CheckResult(path=str(root), results=[])

        _updated, fix_report = _apply_tier_a_and_reverify(cfg, root, result)

        assert all(f["rule"] != "TODO001" for f in fix_report["fixed"])
        assert other.read_text(encoding="utf-8") == other_text


class TestResultAsJsonWithFix:
    """`_result_as_json_with_fix`: `--fix`'s JSON shape is strictly
    additive over `CheckResult.as_json()` -- acceptance criteria 1/2."""

    def test_no_fix_report_is_byte_identical_to_plain_as_json(self) -> None:
        # frob:tests src/frob/app/check_runner.py::_result_as_json_with_fix kind="unit"  # noqa: E501
        result = CheckResult(path=".", results=[])
        assert _result_as_json_with_fix(result, None) == result.as_json()

    def test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present(
        self,
    ) -> None:
        # frob:tests src/frob/app/check_runner.py::_result_as_json_with_fix kind="unit"  # noqa: E501
        result = CheckResult(path=".", results=[])
        fix_report = {"fixed": [], "rolled_back": [], "fixits": []}

        payload = json.loads(_result_as_json_with_fix(result, fix_report))

        assert payload["fix"] == fix_report
        assert payload["fix"]["fixits"] == []
        assert payload["fix"]["rolled_back"] == []

    def test_underlying_result_fields_still_present_alongside_fix_key(
        self,
    ) -> None:
        # frob:tests src/frob/app/check_runner.py::_result_as_json_with_fix kind="unit"  # noqa: E501
        result = CheckResult(path="/tmp/x", results=[])
        payload = json.loads(
            _result_as_json_with_fix(
                result, {"fixed": [], "rolled_back": [], "fixits": []}
            )
        )
        assert payload["path"] == "/tmp/x"


class TestFixReportText:
    """`_fix_report_text`: the human-readable `--fix` summary block."""

    def test_summary_line_reports_three_counts(self) -> None:
        # frob:tests src/frob/app/check_runner.py::_fix_report_text kind="unit"
        text = _fix_report_text(
            {
                "fixed": [
                    {"rule": "DOC007", "file": "a.py", "line": 1, "detail": "x -> y"}
                ],
                "rolled_back": [],
                "fixits": [],
            }
        )
        assert "fixed=1" in text
        assert "rolled_back=0" in text
        assert "fix-its=0" in text
        assert "DOC007" in text

    def test_no_fixes_reports_all_zero_counts(self) -> None:
        # frob:tests src/frob/app/check_runner.py::_fix_report_text kind="unit"
        text = _fix_report_text({"fixed": [], "rolled_back": [], "fixits": []})
        assert "fixed=0" in text
        assert "rolled_back=0" in text
        assert "fix-its=0" in text
