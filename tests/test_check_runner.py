"""`frob.app.check_runner`'s `--fix` CLI wiring (T-1260/T-1481): `frob
check --fix`'s orchestration of `frob.gates._fix_engine.
apply_tier_a_fixes`, `frob.gates._fix_engine_tier_b.apply_tier_b_fixes`,
and `frob.gates._fix_engine_tier_c.apply_tier_c_fixits` -- fixes applied,
the union of affected gates re-run once in the same invocation, and the
fixed/rolled-back/fix-its summary shape `--fix --json` reports
(docs/design/check-fix-engine.md "Gate re-run semantics" and "Fix-it
emission format")."""

from __future__ import annotations

import json
from pathlib import Path

import frob.gates as gates_module
from frob.app.check_runner import (
    _apply_tier_a_and_reverify,
    _claude_config_drift_result,
    _fix_report_text,
    _result_as_json_with_fix,
)
from frob.app.config import AppConfig
from frob.check import CheckResult
from frob.gates._models import GateReport, GateStats, Severity, Violation
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
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify \
        # kind="unit"
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
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify \
        # kind="unit"
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
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify \
        # kind="unit"
        root = _doc007_repo(tmp_path)
        other = root / "src" / "pkg" / "other.py"
        other_text = "# TODO: something undone\ndef g():\n    pass\n"
        other.write_text(other_text, encoding="utf-8")
        cfg = AppConfig(check_fix=True)
        result = CheckResult(path=str(root), results=[])

        _updated, fix_report = _apply_tier_a_and_reverify(cfg, root, result)

        assert all(f["rule"] != "TODO001" for f in fix_report["fixed"])
        assert other.read_text(encoding="utf-8") == other_text

    # -- T-1481: Tier-B is now a real CLI caller, not test-only -------------

    def test_tierbdemo_marker_is_committed_via_tier_b_and_reported_fixed(
        self, tmp_path: Path
    ) -> None:
        """T-1481's Tier-B wiring: a real `# frob:tierbdemo <replacement>`
        marker (the synthetic reference handler's own trigger shape,
        `frob.gates._fix_engine_tier_b.fix_tierbdemo001_marker_rewrite`)
        gets rewritten and reported in `fix_report["fixed"]` -- proving
        `apply_tier_b_fixes` is reachable from `--fix` for real now, not
        only from that module's own tests. `affected_gates=("tierbdemo",)`
        is a placeholder id no real gate ever reports, so the production
        `_real_gate_runner` re-verification is trivially clean and the fix
        commits rather than rolling back."""
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify \
        # kind="unit"
        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "pkg" / "mod.py").write_text(
            "# frob:tierbdemo # replaced\ndef real():\n    pass\n",
            encoding="utf-8",
        )
        (root / "tickets.md").write_text("", encoding="utf-8")
        cfg = AppConfig(check_fix=True)
        result = CheckResult(path=str(root), results=[])

        _updated, fix_report = _apply_tier_a_and_reverify(cfg, root, result)

        tierbdemo_fixed = [
            f for f in fix_report["fixed"] if f["rule"] == "TIERBDEMO001"
        ]
        assert len(tierbdemo_fixed) == 1
        assert fix_report["rolled_back"] == []
        rewritten = (root / "src" / "pkg" / "mod.py").read_text(encoding="utf-8")
        assert rewritten.splitlines()[0] == "# replaced"

    # -- T-1481: Tier-C is now a real CLI caller, not test-only -------------

    def test_tier_c_fixit_from_a_todo001_violation_is_included(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-1481's Tier-C wiring: a TODO001 `Violation` reported by the
        (here, stubbed) post-fix gates run gets a `FixIt` emitted via
        `emit_todo001_fixit` and included in `fix_report["fixits"]` --
        proving `apply_tier_c_fixits` is reachable from `--fix` for real
        now. `frob.gates.run_gates` is stubbed rather than driving TODO001
        for real (a diff-driven gate needing a git base ref) -- this test
        is about the CLI wiring reaching Tier C's dispatch table, which
        `tests/test_gates.py::TestFixEngineTierC` already covers directly
        for `emit_todo001_fixit`'s own rewrite logic."""
        # frob:tests src/frob/app/check_runner.py::_apply_tier_a_and_reverify \
        # kind="unit"
        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "pkg" / "mod.py").write_text("def real():\n    pass\n")
        (root / "tickets.md").write_text("", encoding="utf-8")
        cfg = AppConfig(check_fix=True)
        result = CheckResult(path=str(root), results=[])

        todo_violation = Violation(
            rule="TODO001",
            severity=Severity.WARN,
            file="src/pkg/mod.py",
            line=1,
            message="TODO001: bare TODO/FIXME at src/pkg/mod.py:1; bind it: ...",
        )
        stub_report = GateReport(
            violations=(todo_violation,), waived=(), stats=GateStats()
        )

        def _fake_run_gates(cfg, use_cache=True):  # noqa: ANN001, ANN202
            from typani import Ok

            return Ok(stub_report)

        monkeypatch.setattr(gates_module, "run_gates", _fake_run_gates)

        _updated, fix_report = _apply_tier_a_and_reverify(cfg, root, result)

        assert len(fix_report["fixits"]) == 1
        assert fix_report["fixits"][0]["rule"] == "TODO001"
        assert fix_report["fixits"][0]["proposed_patch"] is None


class TestResultAsJsonWithFix:
    """`_result_as_json_with_fix`: `--fix`'s JSON shape is strictly
    additive over `CheckResult.as_json()` -- acceptance criteria 1/2."""

    def test_no_fix_report_is_byte_identical_to_plain_as_json(self) -> None:
        # frob:tests src/frob/app/check_runner.py::_result_as_json_with_fix kind="unit"
        result = CheckResult(path=".", results=[])
        assert _result_as_json_with_fix(result, None) == result.as_json()

    def test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present(
        self,
    ) -> None:
        # frob:tests src/frob/app/check_runner.py::_result_as_json_with_fix kind="unit"
        result = CheckResult(path=".", results=[])
        fix_report = {"fixed": [], "rolled_back": [], "fixits": []}

        payload = json.loads(_result_as_json_with_fix(result, fix_report))

        assert payload["fix"] == fix_report
        assert payload["fix"]["fixits"] == []
        assert payload["fix"]["rolled_back"] == []

    def test_underlying_result_fields_still_present_alongside_fix_key(
        self,
    ) -> None:
        # frob:tests src/frob/app/check_runner.py::_result_as_json_with_fix kind="unit"
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


_MINIMAL_SYNC_HOOK = '''"""Sync git-tracked Claude config from this repo out to `~/.claude/`."""

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_HOME_CLAUDE = Path.home() / ".claude"

MANAGED: list[tuple[str, str]] = [
    (".claude/hooks/widget.py", "hooks/widget.py"),
]

_BANNER = "# GENERATED COPY -- DO NOT EDIT.\\n"


def plan():
    actions = []
    missing = []
    for source_rel, dest_rel in MANAGED:
        source = _REPO / source_rel
        if not source.exists():
            missing.append(source_rel)
            continue
        want = _BANNER + source.read_text(encoding="utf-8")
        dest = _HOME_CLAUDE / dest_rel
        have = dest.read_text(encoding="utf-8") if dest.exists() else None
        if have == want:
            continue
        state = "absent" if have is None else "differs"
        actions.append((f"{dest_rel} ({state} vs {source_rel})", dest, want))
    return actions, missing


def main(argv=None):
    return 0
'''


def _claude_config_repo(tmp_path: Path, monkeypatch) -> Path:  # noqa: ANN001
    """A fixture repo carrying a minimal `.claude/hooks/sync-claude-
    config.py`, plus a throwaway `$HOME` so this stage's own `Path.home()
    / ".claude"` read never touches the real operator home directory."""
    root = tmp_path / "repo"
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "sync-claude-config.py").write_text(_MINIMAL_SYNC_HOOK, encoding="utf-8")
    (hooks / "widget.py").write_text("print('widget')\n", encoding="utf-8")

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)
    return root


class TestClaudeConfigDriftStage:
    """`_claude_config_drift_result` (T-1809): the `frob check` extra
    stage gating T-1808's Claude-config sync drift. Acceptance shape: a
    divergence MUST fail before any sync (`test_reports_drift_when_
    managed_copy_absent`), and an in-sync tree MUST report clean, no
    false positive (`test_clean_when_in_sync`)."""

    # frob:tests \
    # tests/test_check_runner.py::TestClaudeConfigDriftStage.test_reports_drift_when_ma\
    # naged_copy_absent
    def test_reports_drift_when_managed_copy_absent(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        root = _claude_config_repo(tmp_path, monkeypatch)
        result = _claude_config_drift_result(root)
        assert result is not None
        assert result.exit_code == 1
        assert result.tool == "claude-config-drift"
        assert any(d.code == "CLAUDE001" for d in result.diagnostics)

    # frob:tests \
    # tests/test_check_runner.py::TestClaudeConfigDriftStage.test_clean_when_in_sync
    def test_clean_when_in_sync(self, tmp_path: Path, monkeypatch) -> None:
        root = _claude_config_repo(tmp_path, monkeypatch)
        dest = Path.home() / ".claude" / "hooks" / "widget.py"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            "# GENERATED COPY -- DO NOT EDIT.\n" + (root / ".claude" / "hooks" / "widget.py").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        result = _claude_config_drift_result(root)
        assert result is not None
        assert result.exit_code == 0
        assert result.diagnostics == []

    # frob:tests \
    # tests/test_check_runner.py::TestClaudeConfigDriftStage.test_no_stage_when_repo_ha\
    # s_no_managed_config
    def test_no_stage_when_repo_has_no_managed_config(self, tmp_path: Path) -> None:
        root = tmp_path / "bare"
        root.mkdir()
        assert _claude_config_drift_result(root) is None
