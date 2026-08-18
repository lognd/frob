"""T-2467: unit tests for the periodic frob:waive audit runner."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner._waive_audit import (
    AuditVerdict,
    WaiveAuditError,
    complete_pass,
    run_scan,
)
from frob.gates._waive_audit_watermark import watermark_path

# The parent package's __init__.py re-exports this submodule's `run` under
# the SAME name (`_waive_audit`) for the CLI dispatch table, which shadows
# the submodule as a package attribute -- `importlib.import_module` reads
# sys.modules directly, bypassing that shadowing, so tests can still
# monkeypatch this submodule's own `_CATCHUP_BOUND`.
_waive_audit = importlib.import_module("frob.app.ticket_runner._waive_audit")


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        # frob:secret-fake reason="fabricated git identity for a test fixture repo"
        ["git", "config", "user.email", "a@b.c"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "a"], cwd=tmp_path, check=True)


def _commit_all(tmp_path: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=tmp_path, check=True)


def _write_waiver(tmp_path: Path, name: str, rule: str) -> None:
    (tmp_path / name).write_text(
        f'# frob:waive {rule} reason="fixture waiver for T-2467 tests"\n'
        "def f() -> None:\n    pass\n"
    )


class TestRunScan:
    def test_no_watermark_bounds_catchup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 2)
        _init_git_repo(tmp_path)
        for i in range(5):
            _write_waiver(tmp_path, f"m{i}.py", "DUP001")
        _commit_all(tmp_path, "add waivers")

        report = run_scan(tmp_path)

        assert report.mode == "catchup"
        assert report.verdict == AuditVerdict.NEEDS_REVIEW
        assert len(report.scanned) == 2
        assert report.not_covered_count == 3

    def test_watermark_malformed_is_unreadable(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m.py", "DUP001")
        _commit_all(tmp_path, "add waiver")
        path = watermark_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json")

        report = run_scan(tmp_path)

        assert report.verdict == AuditVerdict.WATERMARK_UNREADABLE
        assert report.mode == "unreadable"
        assert report.error is not None

    def test_no_new_waivers_when_nothing_changed_since_watermark(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 10)
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m.py", "DUP001")
        _commit_all(tmp_path, "add waiver")
        head = subprocess.run(
            ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        from frob.gates._waive_audit_watermark import WaiveAuditWatermark, save_watermark, utc_now

        save_watermark(
            tmp_path,
            WaiveAuditWatermark(commit_sha=head, audited_at=utc_now(), waivers_audited=1),
        )

        report = run_scan(tmp_path)

        assert report.mode == "incremental"
        assert report.verdict == AuditVerdict.NO_NEW_WAIVERS
        assert report.scanned == ()


class TestCompletePass:
    def test_reviewed_count_mismatch_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 10)
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m.py", "DUP001")
        _commit_all(tmp_path, "add waiver")

        result = complete_pass(tmp_path, reviewed_count=5, cop_outs_found=0)

        assert result.is_err
        assert result.err is WaiveAuditError.ReviewCountMismatch

    def test_catchup_incomplete_refuses_full_completion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 1)
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m1.py", "DUP001")
        _write_waiver(tmp_path, "m2.py", "DUP001")
        _commit_all(tmp_path, "add waivers")

        result = complete_pass(tmp_path, reviewed_count=1, cop_outs_found=0)

        assert result.is_err
        assert result.err is WaiveAuditError.CatchupIncomplete

    def test_matching_reviewed_count_advances_watermark(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 10)
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m.py", "DUP001")
        _commit_all(tmp_path, "add waiver")

        result = complete_pass(tmp_path, reviewed_count=1, cop_outs_found=0)

        assert result.is_ok
        watermark = result.danger_ok
        assert watermark.waivers_audited == 1
        assert watermark_path(tmp_path).exists()
