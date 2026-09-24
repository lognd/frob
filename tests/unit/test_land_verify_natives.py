"""T-5518: `_rebuild_stale_worktree_natives` -- the T-1213
stale-natives detector's second call site, run right before
`_reverify_evidence_post_merge` spawns the post-merge evidence run.

Real incident this reproduces: T-3010's land failed the FIRST attempt
because the worktree's evidence subprocess (`uv run pytest`, cwd=
worktree) imported a `strata_core` extension built before the ticket's
own new PyO3 export landed in worktree source -- every evidence test
importing that export failed "individually", though the identical tests
passed with no source change after a manual `frob natives build`
(`/tmp/land-T-5464.log` ~line 24069). This module never called T-1213's
detector between `_land_merge_stage`'s merge and the evidence spawn;
these tests are the positive/MUST-STAY-QUIET pair for the fix, driving
the SAME `frob.gates._maybe_autorebuild_natives` detector two different
Rust-source-changed-or-not ways, exactly as `frob.gates.run_gates`'s own
pre-squash call to it is already covered.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typani.result import Ok

from frob.strata._native_staleness import StaleNative
from frob.testing._models import NativeSpec
from frob.tickets._land_verify import _rebuild_stale_worktree_natives


def _fake_spec() -> NativeSpec:
    """One fake `[[native]]` entry -- shape only, never a real crate --
    used by both controls below to drive `_maybe_autorebuild_natives`'s
    own stale/missing branches without needing an actual Rust build."""
    return NativeSpec(name="fake_native", build_cmd="true", language="rust")


class TestRebuildStaleWorktreeNatives:
    # frob:tests tests/unit/test_land_verify_natives.py::TestRebuildStaleWorktreeNatives.test_stale_fake_native_triggers_rebuild  # noqa: E501
    # frob:tests src/frob/tickets/_land_verify.py::_rebuild_stale_worktree_natives kind="unit"  # noqa: E501
    # frob:ticket T-5518
    def test_stale_fake_native_triggers_rebuild(self, tmp_path: Path) -> None:
        """Positive control: a fake native T-1213's own `stale_natives`
        reports STALE must reach `build_natives(worktree)` -- the actual
        rebuild call this ticket's fix exists to trigger post-merge,
        before evidence, that a Rust change riding `_land_merge_stage`'s
        merge into `worktree` was previously never caught until the
        evidence subprocess itself failed."""
        spec = _fake_spec()
        stale = (
            StaleNative(
                spec=spec,
                source_dir="fake-native",
                artifact_mtime=1.0,
                source_mtime=2.0,
                reason="mtime",
            ),
        )
        with (
            patch("frob.strata.stale_natives", return_value=stale),
            patch("frob.strata.unimportable_natives", return_value=()),
            patch("frob.gates._native_autorebuild_disabled", return_value=False),
            patch("frob.natives._build.build_natives") as mock_build,
            patch("frob.testing._runners.load_natives", return_value=Ok(())),
        ):
            from frob.natives._build import BuildReport

            mock_build.return_value = Ok(BuildReport(cargo_target_dir=tmp_path))
            _rebuild_stale_worktree_natives(tmp_path)
        mock_build.assert_called_once_with(tmp_path)

    # frob:tests tests/unit/test_land_verify_natives.py::TestRebuildStaleWorktreeNatives.test_fresh_natives_stay_quiet  # noqa: E501
    # frob:tests src/frob/tickets/_land_verify.py::_rebuild_stale_worktree_natives kind="unit"  # noqa: E501
    # frob:ticket T-5518
    def test_fresh_natives_stay_quiet(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET control: no Rust change in the merge (T-1213's
        own `stale_natives`/`unimportable_natives` report nothing) must
        NEVER call `build_natives` -- the common, already-healthy case
        every evidence run takes, unaffected by this fix's new call
        site."""
        with (
            patch("frob.strata.stale_natives", return_value=()),
            patch("frob.strata.unimportable_natives", return_value=()),
            patch("frob.gates._native_autorebuild_disabled", return_value=False),
            patch("frob.natives._build.build_natives") as mock_build,
            patch("frob.testing._runners.load_natives", return_value=Ok(())),
        ):
            _rebuild_stale_worktree_natives(tmp_path)
        mock_build.assert_not_called()
