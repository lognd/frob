"""T-2467: unit tests for the periodic frob:waive audit runner."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner._waive_audit import (
    AuditVerdict,
    ScannedWaiver,
    WaiveAuditError,
    complete_pass,
    find_collision_suspects,
    run_scan,
)
from frob.gates._models import Severity, Violation
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
        assert watermark.catchup_remaining == 0
        assert watermark_path(tmp_path).exists()


class TestPartialCatchup:
    """T-2485: a bounded catch-up pass must be able to bank exactly the
    batch it reviewed -- without `partial=True` it still refuses
    (unchanged from before), and the NEXT scan must advance past what
    was already banked rather than re-offering the same window."""

    def test_partial_without_flag_still_refuses(
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
        assert not watermark_path(tmp_path).exists()

    def test_partial_banks_batch_and_advances_watermark(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 1)
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m1.py", "DUP001")
        _write_waiver(tmp_path, "m2.py", "DUP001")
        _commit_all(tmp_path, "add waivers")

        result = complete_pass(
            tmp_path, reviewed_count=1, cop_outs_found=0, partial=True
        )

        assert result.is_ok
        watermark = result.danger_ok
        assert watermark.waivers_audited == 1
        assert watermark.catchup_remaining == 1
        assert len(watermark.catchup_covered) == 1
        assert watermark_path(tmp_path).exists()

    def test_next_scan_skips_already_banked_waivers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 1)
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m1.py", "DUP001")
        _write_waiver(tmp_path, "m2.py", "DUP001")
        _commit_all(tmp_path, "add waivers")

        first = complete_pass(
            tmp_path, reviewed_count=1, cop_outs_found=0, partial=True
        )
        assert first.is_ok
        first_covered = first.danger_ok.catchup_covered

        report = run_scan(tmp_path)

        assert report.mode == "catchup"
        assert report.verdict == AuditVerdict.NEEDS_REVIEW
        assert len(report.scanned) == 1
        assert report.not_covered_count == 0
        scanned_identity = f"{report.scanned[0].file}:{report.scanned[0].line}:{report.scanned[0].rule}"
        assert scanned_identity not in first_covered

    def test_banking_the_final_batch_clears_catchup_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_waive_audit, "_CATCHUP_BOUND", 1)
        _init_git_repo(tmp_path)
        _write_waiver(tmp_path, "m1.py", "DUP001")
        _write_waiver(tmp_path, "m2.py", "DUP001")
        _commit_all(tmp_path, "add waivers")

        first = complete_pass(
            tmp_path, reviewed_count=1, cop_outs_found=0, partial=True
        )
        assert first.is_ok

        second = complete_pass(
            tmp_path, reviewed_count=1, cop_outs_found=0, partial=True
        )

        assert second.is_ok
        watermark = second.danger_ok
        assert watermark.catchup_remaining == 0
        assert watermark.catchup_covered == ()

        # A now-fully-caught-up watermark reverts to plain incremental
        # scanning -- no more waivers to review until something new lands.
        report = run_scan(tmp_path)
        assert report.mode == "incremental"
        assert report.verdict == AuditVerdict.NO_NEW_WAIVERS


class TestCollisionSuspects:
    """T-2493: the sound half of INERT-waiver detection -- a waiver is only
    flagged when a CURRENTLY-KEPT (unsuppressed) violation of the same
    rule sits in the same repo-relative file, never from mere absence
    (the T-1579/55-waiver-deletion failure mode). Both directions of the
    positive/negative control the coordinator required are here:
    positive = a planted mismatch that leaves a real violation
    unsuppressed IS flagged; negative = a genuinely live, correctly-
    matching waiver, and a quiet hardened site with zero violations
    anywhere, are BOTH not flagged."""

    def test_active_unsuppressed_violation_in_same_rule_and_file_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # Positive control: the waiver names DUP001 in mod.py, but (as if
        # its symref/path shape never actually matched, T-2314/T-2438's
        # own root-cause shape) the violation persisted in the KEPT set
        # instead of being suppressed -- a direct, present counter-example
        # that the waiver is not doing its job at that site.
        waiver = ScannedWaiver(
            file="mod.py", line=3, rule="DUP001", reason="should suppress this"
        )
        kept = [
            Violation(
                rule="DUP001",
                severity=Severity.WARN,
                file="mod.py",
                line=10,
                message="DUP001: mod.py:10 duplicate of other.py:5",
            )
        ]

        suspects = find_collision_suspects(
            [waiver], kept, root=tmp_path
        )

        assert len(suspects) == 1
        assert suspects[0].rule == "DUP001"
        assert suspects[0].file == "mod.py"
        assert suspects[0].colliding_violation_line == 10

    def test_a_correctly_matching_live_waiver_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Negative control #1: the waiver's rule/file has NO entry in the
        # kept set at all -- exactly what a correctly-matching waiver
        # produces (its violation was suppressed into `waived`, never
        # reaching `kept`). Some UNRELATED kept violation (different rule)
        # exists in the same file to prove this is not a blanket "any
        # violation in this file" false match.
        waiver = ScannedWaiver(
            file="mod.py", line=3, rule="DUP001", reason="correctly suppresses"
        )
        kept = [
            Violation(
                rule="PERF004",
                severity=Severity.WARN,
                file="mod.py",
                line=20,
                message="PERF004: mod.py:20 unrelated finding",
            )
        ]

        suspects = find_collision_suspects(
            [waiver], kept, root=tmp_path
        )

        assert suspects == ()

    def test_a_quiet_hardened_site_with_zero_violations_anywhere_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Negative control #2, the one that matters most: a load-bearing
        # waiver on a hardened guard, currently producing ZERO violations
        # of its rule ANYWHERE in the tree (not just this file) -- exactly
        # what the falsified T-1579 escape misread as "provably dead".
        # This function must report nothing here, by construction, since
        # it never reasons from absence at all.
        waiver = ScannedWaiver(
            file="hardened_guard.py",
            line=42,
            rule="SEC110",
            reason="FROB_AGENT is a boolean context flag, never a secret",
        )
        kept: list[Violation] = []

        suspects = find_collision_suspects(
            [waiver], kept, root=tmp_path
        )

        assert suspects == ()

    def test_absolute_violation_path_still_matches_repo_relative_waiver(
        self, tmp_path: Path
    ) -> None:
        # T-2314's own root cause: a producer emitting an ABSOLUTE path
        # while everything else compares repo-relative. This function
        # must normalize both sides, not silently miss the collision the
        # way _match_waiver used to.
        waiver = ScannedWaiver(
            file="pkg/mod.py", line=3, rule="DUP001", reason="should suppress this"
        )
        kept = [
            Violation(
                rule="DUP001",
                severity=Severity.WARN,
                file=str(tmp_path / "pkg" / "mod.py"),
                line=10,
                message="DUP001: absolute-path finding",
            )
        ]

        suspects = find_collision_suspects(
            [waiver], kept, root=tmp_path
        )

        assert len(suspects) == 1

