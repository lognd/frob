"""T-3943 (F-173): `frob check`/close/done-report must not hardcode
`"main"` as the diff base -- a repo whose default branch is `dev`
(this repo, post-T-4496) sees every symbol touched since main's tip as
"changed with no frob:ticket edge" otherwise, burying real findings
under hundreds of false ones. These prove the canonical resolver
(`frob.tickets._land._resolve_default_ticket_branch`, already used by
`frob ticket work`/evidence/done-report per T-4492) is what a bare,
no-`--base` `frob check` gate run and `_close_own_obligations_for_ticket`
now consult, instead of each independently defaulting to the literal
"main"."""

from __future__ import annotations

from pathlib import Path

from frob.app.check_runner import AppConfig, _check_default_base


# frob:ticket T-3943
class TestCheckDefaultBase:
    """`_check_default_base` (check_runner.py): explicit `cfg.check_base`
    wins outright; otherwise it defers to the same resolver `frob ticket
    work` uses, not a literal "main"."""

    # frob:tests tests/test_check_gate_base.py::TestCheckDefaultBase.test_explicit_check_base_wins kind="unit"  # noqa: E501
    def test_explicit_check_base_wins(self, tmp_path: Path) -> None:
        cfg = AppConfig(check_base="some-branch")
        assert _check_default_base(tmp_path, cfg) == "some-branch"

    # frob:tests tests/test_check_gate_base.py::TestCheckDefaultBase.test_falls_back_to_current_branch_not_literal_main kind="unit"  # noqa: E501
    def test_falls_back_to_current_branch_not_literal_main(
        self, tmp_path: Path
    ) -> None:
        """A real repo checked out on `dev` (never `main`) resolves to
        "dev", not "main" -- the exact F-173 regression: a bare `frob
        check` on this repo's own `dev` branch used to silently diff
        against `main` instead."""
        import subprocess

        subprocess.run(["git", "init", "-q", "-b", "dev", str(tmp_path)], check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-q", "-m", "x"],
            check=True,
        )
        cfg = AppConfig(check_base=None)
        assert _check_default_base(tmp_path, cfg) == "dev"

    # frob:tests tests/test_check_gate_base.py::TestCheckDefaultBase.test_degrades_to_main_on_unresolvable_branch kind="unit"  # noqa: E501
    def test_degrades_to_main_on_unresolvable_branch(self, tmp_path: Path) -> None:
        """Not a git checkout at all: degrades to the historical "main"
        literal (never raises), matching `_resolve_default_ticket_
        branch`'s own documented last-resort fallback."""
        cfg = AppConfig(check_base=None)
        assert _check_default_base(tmp_path, cfg) == "main"
