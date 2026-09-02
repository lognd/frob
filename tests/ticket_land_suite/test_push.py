import os
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from typani.result import Err, Ok, Result

import frob.tickets._land as _land_mod
import frob.tickets._land_git_ops as _land_git_ops_mod
import frob.tickets._land_ledger_merge as _land_ledger_merge_mod
import frob.tickets._land_release as _land_release_mod
from frob.gitio import ProcResult, run_argv
from frob.tickets import (
    TicketState,
)
from tests.ticket_land_suite.conftest import (
    _STATE_BY_RANK,
    _synthetic_ticket,
)

pytestmark = pytest.mark.heavy_subprocess


class TestLandPushCliWiring:
    """T-0631: `frob ticket land --push` must actually parse and reach
    `AppConfig`, and default to `False` when omitted -- the same untested-
    boolean-default shape `TestSkipMutationEvidenceCliWiring` guards for
    the sibling `--skip-mutation-evidence` flag."""

    def test_flag_parses_to_true(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_push.py::TestLandPushCliWiring.test_flag_parses_\
        # to_true
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--push",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_land_push is True

    def test_flag_omitted_defaults_false(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestLandPushCliWiring.test_flag_omitted_defaults_false  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_land_push is False


# frob:ticket T-1057
class TestLandWorktreeResolvedAtArgParse:
    """T-1057: `frob ticket land <id> --worktree <RELATIVE path>` used to
    fail with `[Errno 2] No such file or directory: '<relative>/.venv/
    bin/python'` -- `ticket_runner._land`'s pre-`land()` spawn joined the
    still-relative `cfg.ticket_worktree` with `.venv/bin/python` and ran
    it with `cwd=` set to that same relative path, which the OS resolves
    against the CALLING process's cwd, not the target `cwd=`.
    `AppConfig.from_external` now resolves `ticket_worktree` to an
    absolute path at argument-parse time (the single place every `Path`-
    typed CLI arg is built), so a relative `--worktree` behaves
    identically to an absolute one from here on -- this test guards that
    `cfg.ticket_worktree` is always absolute regardless of how `--worktree`
    was spelled on the command line."""

    def test_relative_worktree_arg_resolves_to_absolute(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestLandWorktreeResolvedAtArgParse.test_relative_worktree_arg_resolves_to_absolute  # noqa: E501

        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        worktree_dir = tmp_path / "worktree"
        worktree_dir.mkdir()
        old_cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            parser = _build_parser()
            args = parser.parse_args(
                [
                    "ticket",
                    "land",
                    "T-0001",
                    "--worktree",
                    "worktree",
                    "--path",
                    str(tmp_path),
                ]
            )
            cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        finally:
            os.chdir(old_cwd)

        assert cfg.ticket_worktree is not None
        assert cfg.ticket_worktree.is_absolute()
        assert cfg.ticket_worktree == worktree_dir.resolve()

    def test_absolute_worktree_arg_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestLandWorktreeResolvedAtArgParse.test_absolute_worktree_arg_unchanged  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_worktree == tmp_path.resolve()


# frob:ticket T-0631
class TestPushAfterLand:
    """`_push_after_land` -- pushes root's current branch after a real
    land succeeds, never on a dry run, and exits non-zero (without
    unwinding the already-landed commit -- there is nothing left to
    unwind) on a push failure."""

    def _report(self, *, dry_run: bool, commit_sha: str | None = "deadbeef") -> Any:
        from frob.tickets._models import LandReport

        return LandReport(
            ticket_id="T-0001",
            final_id="T-0001",
            dry_run=dry_run,
            wip_committed=False,
            merged_main_into_worktree=False,
            ledger_spliced=not dry_run,
            commit_sha=commit_sha,
        )

    def test_dry_run_never_pushes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_push.py::TestPushAfterLand.test_dry_run_never_pu\
        # shes
        from frob.app import ticket_runner

        def _fail_if_called(*a: Any, **k: Any) -> Any:
            raise AssertionError("git push must not be spawned on a dry run")

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fail_if_called)
        ticket_runner._push_after_land(tmp_path, self._report(dry_run=True))

    def test_real_land_pushes_the_current_branch(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestPushAfterLand.test_real_land_pushes_the_current_branch  # noqa: E501
        from frob.app import ticket_runner

        calls: list[list[str]] = []

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            calls.append(argv)
            return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        ticket_runner._push_after_land(repo, self._report(dry_run=False))

        assert len(calls) == 1
        assert calls[0][:3] == ["git", "-C", str(repo)]
        assert calls[0][3:] == ["push", "origin", "main"]

    def test_push_failure_exits_nonzero(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_push.py::TestPushAfterLand.test_push_failure_exi\
        # ts_nonzero
        from frob.app import ticket_runner

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout="", stderr="no such remote"
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        with pytest.raises(SystemExit) as exc_info:
            ticket_runner._push_after_land(repo, self._report(dry_run=False))
        assert exc_info.value.code == 1

    def test_exec_disabled_exits_nonzero(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_push.py::TestPushAfterLand.test_exec_disabled_ex\
        # its_nonzero
        from frob.app import ticket_runner
        from frob.process._guard import ProcessGuardError

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Err(ProcessGuardError.ExecDisabled)

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        with pytest.raises(SystemExit) as exc_info:
            ticket_runner._push_after_land(repo, self._report(dry_run=False))
        assert exc_info.value.code == 1


# frob:ticket T-1011
class TestSyncGateRulesCallback:
    """T-1011(a): `land()`'s optional `sync_gate_rules` callback (invoked
    right after the REL001 bump, before the completeness assertion) lets a
    landing that changed `_KNOWN_GATE_RULES` auto-file `check-coverage.
    yaml` rows in the same commit, with the same fail-closed-unwind
    posture as `bump_version` on a real failure."""

    def test_sync_gate_rules_none_is_noop(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestSyncGateRulesCallback.test_sync_gate_rules_none_is_noop  # noqa: E501
        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok
        result = _land_release_mod._apply_gate_rule_sync(
            repo, "T-0001", None, pre_land_tip
        )
        assert result.is_ok
        assert result.danger_ok is None

    def test_sync_gate_rules_applies_and_stages(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestSyncGateRulesCallback.test_sync_gate_rules_applies_and_stages  # noqa: E501
        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok

        def _fake_sync(_root: Path, _tip: str) -> Result[tuple[str, ...] | None, Any]:
            return Ok(("SOME001",))

        result = _land_release_mod._apply_gate_rule_sync(
            repo, "T-0001", _fake_sync, pre_land_tip
        )
        assert result.is_ok
        assert result.danger_ok == ("SOME001",)
        # no unwind happened -- HEAD is untouched by a no-op callback.
        assert _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok == pre_land_tip

    def test_sync_gate_rules_failure_unwinds(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestSyncGateRulesCallback.test_sync_gate_rules_failure_unwinds  # noqa: E501
        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok

        def _fake_sync(_root: Path, _tip: str) -> Result[tuple[str, ...] | None, Any]:
            return Err(_land_mod.LandError.GitFailed)

        result = _land_release_mod._apply_gate_rule_sync(
            repo, "T-0001", _fake_sync, pre_land_tip
        )
        assert result.is_err
        assert result.danger_err == _land_mod.LandError.GitFailed
        # the (no-op) unwind reset still leaves HEAD at pre_land_tip.
        assert _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok == pre_land_tip


class TestSyncGateRulesForLandDiffTarget:
    """T-1805 regression: `_sync_gate_rules_for_land`'s trigger diff must
    watch `src/frob/gates/_waive.py`, where `_KNOWN_GATE_RULES` has lived
    since T-1072 moved it out of `src/frob/gates/__init__.py`. Before the
    fix, a commit that only edited `_waive.py` (the ordinary shape of
    "add one rule id") never appeared in the old __init__.py-only diff, so
    the auto-sync silently no-oped on every real change -- confirmed root
    cause of PERF012/SYS108 landing unregistered."""

    def test_edit_to_waive_py_is_detected(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestSyncGateRulesForLandDiffTarget.test_edit_to_waive_py_is_detected  # noqa: E501
        from frob.app.ticket_runner import _sync_gate_rules_for_land

        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok
        waive_path = repo / "src" / "frob" / "gates" / "_waive.py"
        waive_path.parent.mkdir(parents=True, exist_ok=True)
        waive_path.write_text(
            "_KNOWN_GATE_RULES = frozenset({'SOME001'})\n", encoding="utf-8"
        )
        run_argv(["git", "-C", str(repo), "add", "-A"])
        run_argv(["git", "-C", str(repo), "commit", "-m", "add rule id"])

        called: list[str] = []

        def _fake_scan(
            repo_root: Path, retired: frozenset[str] | None = None
        ) -> frozenset[str]:
            called.append("scanned")
            return frozenset({"SOME001"})

        # `_sync_gate_rules_for_land` imports `generated_gate_rule_ids`
        # locally at call time, so patching the source module's attribute
        # (rather than any already-bound name) is what the local import
        # actually re-resolves against.
        import frob.gates._rule_id_scan as _rule_id_scan_mod

        monkeypatch.setattr(_rule_id_scan_mod, "generated_gate_rule_ids", _fake_scan)
        result = _sync_gate_rules_for_land(repo, pre_land_tip)

        assert result.is_ok
        # the scanner must actually have been invoked -- proof the diff
        # against _waive.py was recognized as containing _KNOWN_GATE_RULES,
        # not silently short-circuited to Ok(None) the way the pre-fix
        # __init__.py-only diff target always did for this exact shape.
        assert called == ["scanned"]

    def test_unrelated_waive_py_edit_is_noop(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_push.py::TestSyncGateRulesForLandDiffTarget.test_unrelated_waive_py_edit_is_noop  # noqa: E501
        from frob.app.ticket_runner import _sync_gate_rules_for_land

        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok
        waive_path = repo / "src" / "frob" / "gates" / "_waive.py"
        waive_path.parent.mkdir(parents=True, exist_ok=True)
        waive_path.write_text("# no rule-id literal here\n", encoding="utf-8")
        run_argv(["git", "-C", str(repo), "add", "-A"])
        run_argv(["git", "-C", str(repo), "commit", "-m", "unrelated edit"])

        result = _sync_gate_rules_for_land(repo, pre_land_tip)
        assert result.is_ok
        assert result.danger_ok is None


# frob:ticket T-1194
class TestNewerWinnerQualifiedPreferenceProperty:
    """T-0757: an establish-property obligation (INV008, `frob:invariant
    INV-043 establishes="..."` anchored on `_land._newer`) for T-0682's
    own qualified-preference rule (invariant spec:
    `invariants/INV-043.md`) -- exhaustively over the small state
    space `_newer_winner` actually discriminates on (rank in {0,1,2,3},
    Done-report presence, evidence count), rather than the hand-picked
    field-incident cases `TestSpliceLedgerRicherStatePreference` covers.
    Two properties, both restated from `_newer`'s own docstring tiers:

    1. TERMINAL SUPREMACY: a terminal side (rank 3) always beats a
       non-terminal side, regardless of richness.
    2. QUALIFIED RICHNESS: among two non-terminal sides, the richer side
       (by `_richness`'s tuple order) wins UNLESS the poorer side
       strictly outranks it -- a strictly-higher-rank poorer side always
       wins over a richer-but-lower-or-equal-rank side.
    """

    # frob:ticket T-1194
    # frob:tests tests/ticket_land_suite/test_push.py::TestNewerWinnerQualifiedPreferenceProperty.test_terminal_side_always_wins_over_non_terminal  # noqa: E501
    @given(
        st.sampled_from([0, 1, 2]),
        st.booleans(),
        st.integers(min_value=0, max_value=3),
        st.sampled_from([TicketState.DONE, TicketState.DROPPED]),
        st.booleans(),
        st.integers(min_value=0, max_value=3),
    )
    def test_terminal_side_always_wins_over_non_terminal(
        self,
        non_terminal_rank: int,
        a_report: bool,
        a_evidence: int,
        terminal_state: TicketState,
        b_report: bool,
        b_evidence: int,
    ) -> None:
        a = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[non_terminal_rank][0],
            has_report=a_report,
            evidence_count=a_evidence,
        )
        b = _synthetic_ticket(
            "T-X", terminal_state, has_report=b_report, evidence_count=b_evidence
        )
        assert _land_ledger_merge_mod._newer_winner(a, b) is b
        assert _land_ledger_merge_mod._newer_winner(b, a) is b

    # frob:ticket T-1194
    # frob:tests tests/ticket_land_suite/test_push.py::TestNewerWinnerQualifiedPreferenceProperty.test_strictly_higher_rank_poorer_side_always_wins  # noqa: E501
    @given(
        st.sampled_from([0, 1, 2]),
        st.sampled_from([0, 1, 2]),
        st.integers(min_value=0, max_value=3),
        st.integers(min_value=0, max_value=3),
    )
    def test_strictly_higher_rank_poorer_side_always_wins(
        self,
        richer_rank: int,
        poorer_rank: int,
        richer_evidence: int,
        poorer_evidence: int,
    ) -> None:
        """A reportless-but-strictly-higher-rank side beats a
        reported-but-lower-rank side (the reviewer-caught inverse T-0682
        direction) -- richer here always carries the Done report, poorer
        never does, at a strictly lower rank."""
        if poorer_rank <= richer_rank:
            return
        richer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[richer_rank][0],
            has_report=True,
            evidence_count=richer_evidence,
        )
        poorer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[poorer_rank][0],
            has_report=False,
            evidence_count=poorer_evidence,
        )
        assert _land_ledger_merge_mod._newer_winner(richer, poorer) is poorer
        assert _land_ledger_merge_mod._newer_winner(poorer, richer) is poorer

    # frob:ticket T-1194
    # frob:tests tests/ticket_land_suite/test_push.py::TestNewerWinnerQualifiedPreferenceProperty.test_richer_side_wins_at_equal_or_lower_rank  # noqa: E501
    @given(
        st.sampled_from([0, 1, 2]),
        st.sampled_from([0, 1, 2]),
        st.integers(min_value=0, max_value=3),
        st.integers(min_value=0, max_value=3),
    )
    def test_richer_side_wins_at_equal_or_lower_rank(
        self,
        richer_rank: int,
        poorer_rank: int,
        richer_evidence: int,
        poorer_evidence: int,
    ) -> None:
        """The original T-0682 incident shape: the richer (Done-reported)
        side wins whenever the poorer side does NOT strictly outrank it
        (equal rank, or the richer side is itself the higher-rank one)."""
        if poorer_rank > richer_rank:
            return
        richer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[richer_rank][0],
            has_report=True,
            evidence_count=richer_evidence,
        )
        poorer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[poorer_rank][0],
            has_report=False,
            evidence_count=poorer_evidence,
        )
        assert _land_ledger_merge_mod._newer_winner(richer, poorer) is richer
        assert _land_ledger_merge_mod._newer_winner(poorer, richer) is richer
