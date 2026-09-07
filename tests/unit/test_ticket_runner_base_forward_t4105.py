"""T-4105: every nested `frob check` spawn under `frob.app.ticket_runner`
forwards the parent's effective base ref as `--base`, instead of always
silently dropping it and letting the child fall back to `main` (or a
repo-wide `check_base`) regardless of what branch the parent actually
resolved as its target.

Covers the T-4105 must-fire/must-stay-quiet/third fixtures at the unit
level, one per nested-spawn site this ticket's scope touches:

  - `_land_cmd._unscoped_check_spawn_args` (the post-land sweep argv
    builder)
  - `_verify._shared_check_spawn_fn` (close/land/verify's shared spawn)
  - `_close_cmd._close_gate_claims_for_ticket` /
    `_close_cmd._own_obligations_diff_findings` (close's two gates spawns)
  - `_rapid_sweep._detached_sweep_env` / `_rapid_sweep._spawn_true_count_
    check` (the rapid-land detached sweep's cross-process base handoff)

None of these fixtures re-derive a live git repo or spawn a real `frob
check` -- each inspects the argv/env this module BUILDS for the spawn,
which is exactly what T-4105's defect (the flag never reaching the
spawned argv at all) lives in.
"""

from __future__ import annotations

from pathlib import Path

import frob.app.ticket_runner._close_cmd as close_cmd_mod
import frob.app.ticket_runner._land_cmd as land_cmd_mod
import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
import frob.app.ticket_runner._verify as verify_mod


class TestUnscopedCheckSpawnArgsForwardsBase:
    """`_land_cmd._unscoped_check_spawn_args`: the post-land/pre-commit
    sweep's argv builder (T-4105 site 1 of 6)."""

    def test_no_base_omits_the_flag(self) -> None:
        """T-4105 MUST-STAY-QUIET: no base given -> argv is byte-identical
        to pre-T-4105 (no `--base` anywhere), so an ordinary main-line
        land forwards nothing and the child's own `main`/frob.toml
        resolution is untouched."""
        argv, _env, _timeout = land_cmd_mod._unscoped_check_spawn_args(
            Path("/repo"), budget=300, env=None, full=False, base=None
        )
        assert "--base" not in argv

    def test_explicit_base_reaches_argv(self) -> None:
        """T-4105 MUST-FIRE: an explicit target branch is forwarded as
        `--base <branch>` verbatim."""
        argv, _env, _timeout = land_cmd_mod._unscoped_check_spawn_args(
            Path("/repo"), budget=300, env=None, full=False, base="release/v1"
        )
        assert "--base" in argv
        assert argv[argv.index("--base") + 1] == "release/v1"

    def test_explicit_base_reaches_argv_in_full_mode_too(self) -> None:
        """The `full=True` branch builds a different argv shape (no
        `--budget`) -- `--base` must still reach it, not just the
        budgeted branch."""
        argv, _env, _timeout = land_cmd_mod._unscoped_check_spawn_args(
            Path("/repo"), budget=None, env=None, full=True, base="release/v1"
        )
        assert "--base" in argv
        assert argv[argv.index("--base") + 1] == "release/v1"


class TestSharedCheckSpawnFnForwardsBase:
    """`_verify._shared_check_spawn_fn`: the shared spawn close/land/
    verify's done-report/reverify/land paths all feed into (T-4105 site
    2 of 6, the same closure `_close_cmd.py`/`_land_cmd.py` both call
    into)."""

    def test_no_base_omits_the_flag(self, monkeypatch) -> None:  # noqa: ANN001
        """MUST-STAY-QUIET: `base=None` (every pre-T-4105 caller) builds
        the exact same argv as before -- no `--base` anywhere."""
        captured: dict = {}

        def _fake_guarded_subprocess_run(argv, **kwargs):  # noqa: ANN001, ANN201
            captured["argv"] = argv
            raise SystemExit("stop before a real spawn")

        monkeypatch.setattr(
            "frob.app.ticket_runner.guarded_subprocess_run",
            _fake_guarded_subprocess_run,
        )
        spawn = verify_mod._shared_check_spawn_fn(Path("/repo"), "T-0001")
        try:
            spawn()
        except SystemExit:
            pass
        assert "--base" not in captured["argv"]

    def test_explicit_base_reaches_argv(self, monkeypatch) -> None:  # noqa: ANN001
        """MUST-FIRE: a caller-resolved base (e.g. `cfg.ticket_base_ref`
        when it differs from the reverify/done-report default, or
        `cfg.ticket_land_branch` for land) reaches the spawned argv."""
        captured: dict = {}

        def _fake_guarded_subprocess_run(argv, **kwargs):  # noqa: ANN001, ANN201
            captured["argv"] = argv
            raise SystemExit("stop before a real spawn")

        monkeypatch.setattr(
            "frob.app.ticket_runner.guarded_subprocess_run",
            _fake_guarded_subprocess_run,
        )
        spawn = verify_mod._shared_check_spawn_fn(
            Path("/repo"), "T-0001", base="integration"
        )
        try:
            spawn()
        except SystemExit:
            pass
        assert "--base" in captured["argv"]
        assert captured["argv"][captured["argv"].index("--base") + 1] == "integration"


class TestCloseGuardsBaseResolution:
    """`_close_cmd._close_guards_for_ticket`/`_reverify`: the `!= "main"`
    resolution that decides whether `cfg.ticket_base_ref` is forwarded at
    all (T-4105's documented compromise for the missing unset sentinel).
    Exercised directly against `_close_guards_for_ticket` (rather than
    only through the spawn argv) so a mutant flipping that comparison
    (e.g. `NotEq` -> `Eq`) is actually caught, not just confirmed."""

    def test_default_main_resolves_to_no_base_forwarded(self, monkeypatch) -> None:  # noqa: ANN001
        """`cfg.ticket_base_ref == "main"` (the argparse default, and the
        only value `close` itself can ever produce) must resolve to no
        `--base` reaching either nested spawn."""
        from frob.app.config import AppConfig

        seen_gate_claims: dict = {}
        seen_own_obligations: dict = {}
        import frob.app.ticket_runner as ticket_runner_mod

        monkeypatch.setattr(
            ticket_runner_mod, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        monkeypatch.setattr(
            ticket_runner_mod,
            "_covers_review_for_ticket",
            lambda root, cfg, ticket: None,
        )
        monkeypatch.setattr(
            ticket_runner_mod,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket, base_ref: None,
        )
        monkeypatch.setattr(
            ticket_runner_mod, "_reverify_evidence_for_close", lambda root, ticket: None
        )

        def _fake_gate_claims(root, ticket, base=None):  # noqa: ANN001
            seen_gate_claims["base"] = base
            return None

        def _fake_own_obligations(root, ticket, base=None):  # noqa: ANN001
            seen_own_obligations["base"] = base
            return None

        monkeypatch.setattr(
            ticket_runner_mod, "_close_gate_claims_for_ticket", _fake_gate_claims
        )
        monkeypatch.setattr(
            ticket_runner_mod,
            "_close_own_obligations_for_ticket",
            _fake_own_obligations,
        )
        cfg = AppConfig(ticket_base_ref="main")

        class _FakeTicket:
            id = "T-0001"

        close_cmd_mod._close_guards_for_ticket(Path("/repo"), cfg, _FakeTicket())
        assert seen_gate_claims["base"] is None
        assert seen_own_obligations["base"] is None

    def test_non_main_base_ref_is_forwarded(self, monkeypatch) -> None:  # noqa: ANN001
        """A `reverify --base-ref` explicitly naming a non-`main` branch
        reaches both nested spawns unchanged."""
        import frob.app.ticket_runner as ticket_runner_mod
        from frob.app.config import AppConfig

        monkeypatch.setattr(
            ticket_runner_mod, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        monkeypatch.setattr(
            ticket_runner_mod,
            "_covers_review_for_ticket",
            lambda root, cfg, ticket: None,
        )
        monkeypatch.setattr(
            ticket_runner_mod,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket, base_ref: None,
        )
        monkeypatch.setattr(
            ticket_runner_mod, "_reverify_evidence_for_close", lambda root, ticket: None
        )
        seen_gate_claims: dict = {}
        seen_own_obligations: dict = {}

        def _fake_gate_claims(root, ticket, base=None):  # noqa: ANN001
            seen_gate_claims["base"] = base
            return None

        def _fake_own_obligations(root, ticket, base=None):  # noqa: ANN001
            seen_own_obligations["base"] = base
            return None

        monkeypatch.setattr(
            ticket_runner_mod, "_close_gate_claims_for_ticket", _fake_gate_claims
        )
        monkeypatch.setattr(
            ticket_runner_mod,
            "_close_own_obligations_for_ticket",
            _fake_own_obligations,
        )
        cfg = AppConfig(ticket_base_ref="release/v1")

        class _FakeTicket:
            id = "T-0001"

        close_cmd_mod._close_guards_for_ticket(Path("/repo"), cfg, _FakeTicket())
        assert seen_gate_claims["base"] == "release/v1"
        assert seen_own_obligations["base"] == "release/v1"


class TestDoneReportBaseResolution:
    """`_verify._done_report`: the sibling `!= "main"` resolution feeding
    `_shared_check_spawn_fn` -- exercised through the real CLI function
    (mocking everything else it calls) so a mutant flipping the
    comparison is actually caught, not just confirmed."""

    def _run_done_report(self, monkeypatch, ticket_base_ref: str) -> str | None:  # noqa: ANN001
        from frob.app.config import AppConfig

        captured: dict = {}

        def _fake_shared_check_spawn_fn(root, ticket_id, base=None):  # noqa: ANN001
            captured["base"] = base
            return lambda: None

        monkeypatch.setattr(
            verify_mod, "_shared_check_spawn_fn", _fake_shared_check_spawn_fn
        )
        monkeypatch.setattr(verify_mod, "_resolve_done_report_why", lambda cfg: "why")
        monkeypatch.setattr(
            verify_mod, "_run_tests_count_fn", lambda root: lambda: None
        )
        monkeypatch.setattr(
            verify_mod,
            "_check_gates_summary_fn",
            lambda root, ticket_id, spawn=None: lambda: None,
        )
        monkeypatch.setattr(
            verify_mod,
            "_check_gate_findings_fn",
            lambda root, ticket_id, spawn=None: lambda: None,
        )

        import frob.tickets as tickets_mod

        class _Failing:
            is_err = True
            danger_err = "stop before real work"

        monkeypatch.setattr(tickets_mod, "set_done_report", lambda *a, **k: _Failing())
        cfg = AppConfig(ticket_id="T-0001", ticket_base_ref=ticket_base_ref)
        try:
            verify_mod._done_report(Path("/repo"), cfg)
        except SystemExit:
            pass
        return captured.get("base")

    def test_default_main_resolves_to_no_base_forwarded(self, monkeypatch) -> None:  # noqa: ANN001
        assert self._run_done_report(monkeypatch, "main") is None

    def test_non_main_base_ref_is_forwarded(self, monkeypatch) -> None:  # noqa: ANN001
        assert self._run_done_report(monkeypatch, "release/v1") == "release/v1"


class TestCloseGateSpawnsForwardBase:
    """`_close_cmd._close_gate_claims_for_ticket` /
    `_close_cmd._own_obligations_diff_findings`: close's own two `--only
    gates` spawns (T-4105 sites 3 and 4 of 6)."""

    def test_gate_claims_no_base_omits_the_flag(self, monkeypatch) -> None:  # noqa: ANN001
        captured: dict = {}

        def _fake_guarded_subprocess_run(argv, **kwargs):  # noqa: ANN001, ANN201
            captured["argv"] = argv
            raise SystemExit("stop before a real spawn")

        monkeypatch.setattr(
            "frob.app.ticket_runner.guarded_subprocess_run",
            _fake_guarded_subprocess_run,
        )

        class _FakeTicket:
            id = "T-0001"

        monkeypatch.setattr(
            "frob.tickets._evidence._gate_claim_criteria",
            lambda ticket: (("0 COV002 findings under src/**", "COV002", "src/**"),),
        )
        try:
            close_cmd_mod._close_gate_claims_for_ticket(Path("/repo"), _FakeTicket())
        except SystemExit:
            pass
        assert "--base" not in captured["argv"]

    def test_gate_claims_explicit_base_reaches_argv(self, monkeypatch) -> None:  # noqa: ANN001
        captured: dict = {}

        def _fake_guarded_subprocess_run(argv, **kwargs):  # noqa: ANN001, ANN201
            captured["argv"] = argv
            raise SystemExit("stop before a real spawn")

        monkeypatch.setattr(
            "frob.app.ticket_runner.guarded_subprocess_run",
            _fake_guarded_subprocess_run,
        )

        class _FakeTicket:
            id = "T-0001"

        monkeypatch.setattr(
            "frob.tickets._evidence._gate_claim_criteria",
            lambda ticket: (("0 COV002 findings under src/**", "COV002", "src/**"),),
        )
        try:
            close_cmd_mod._close_gate_claims_for_ticket(
                Path("/repo"), _FakeTicket(), base="release/v1"
            )
        except SystemExit:
            pass
        assert "--base" in captured["argv"]
        assert captured["argv"][captured["argv"].index("--base") + 1] == "release/v1"

    def test_own_obligations_explicit_base_reaches_argv(self, monkeypatch) -> None:  # noqa: ANN001
        captured: dict = {}

        def _fake_guarded_subprocess_run(argv, **kwargs):  # noqa: ANN001, ANN201
            captured["argv"] = argv
            raise SystemExit("stop before a real spawn")

        monkeypatch.setattr(
            "frob.app.ticket_runner.guarded_subprocess_run",
            _fake_guarded_subprocess_run,
        )

        class _FakeTicket:
            id = "T-0001"

        try:
            close_cmd_mod._own_obligations_diff_findings(
                Path("/repo"), _FakeTicket(), {"a.py"}, base="release/v1"
            )
        except SystemExit:
            pass
        assert "--base" in captured["argv"]
        assert captured["argv"][captured["argv"].index("--base") + 1] == "release/v1"


class TestRapidSweepBaseHandoff:
    """`_rapid_sweep._detached_sweep_env`/`_spawn_true_count_check`: the
    rapid-land detached sweep's cross-process base handoff via
    `FROB_LAND_TARGET_BRANCH` (T-4105 site 5 of 6 -- the one site that
    crosses an actual OS-process boundary, documented as the deliberate
    exception to threading base as an explicit argument)."""

    def test_detached_sweep_env_sets_the_var_when_given(self) -> None:
        env = rapid_sweep_mod._detached_sweep_env(
            Path("/repo"), target_branch="release/v1"
        )
        assert env["FROB_LAND_TARGET_BRANCH"] == "release/v1"

    def test_detached_sweep_env_omits_the_var_by_default(self) -> None:
        """MUST-STAY-QUIET: no target branch given -> the var is absent,
        matching pre-T-4105 behavior exactly (and stripping any stale
        value that leaked in from the calling shell's own environment)."""
        env = rapid_sweep_mod._detached_sweep_env(Path("/repo"))
        assert "FROB_LAND_TARGET_BRANCH" not in env

    def test_spawn_true_count_check_forwards_base_from_env(
        self,
        monkeypatch,  # noqa: ANN001
    ) -> None:
        captured: dict = {}

        def _fake_guarded_subprocess_run(argv, **kwargs):  # noqa: ANN001, ANN201
            captured["argv"] = argv
            raise SystemExit("stop before a real spawn")

        monkeypatch.setenv("FROB_LAND_TARGET_BRANCH", "release/v1")
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            _fake_guarded_subprocess_run,
        )
        try:
            rapid_sweep_mod._spawn_true_count_check(Path("/repo"), 300)
        except SystemExit:
            pass
        assert "--base" in captured["argv"]
        assert captured["argv"][captured["argv"].index("--base") + 1] == "release/v1"

    def test_spawn_true_count_check_omits_base_when_env_unset(
        self,
        monkeypatch,  # noqa: ANN001
    ) -> None:
        captured: dict = {}

        def _fake_guarded_subprocess_run(argv, **kwargs):  # noqa: ANN001, ANN201
            captured["argv"] = argv
            raise SystemExit("stop before a real spawn")

        monkeypatch.delenv("FROB_LAND_TARGET_BRANCH", raising=False)
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            _fake_guarded_subprocess_run,
        )
        try:
            rapid_sweep_mod._spawn_true_count_check(Path("/repo"), 300)
        except SystemExit:
            pass
        assert "--base" not in captured["argv"]
