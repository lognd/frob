"""T-1213: auto-rebuild a stale/missing-but-buildable native instead of
merely reminding (T-0248/T-1148's prior reminder-only NATIVE001 posture).

`frob.gates._maybe_autorebuild_natives` is the fix: BEFORE the existing
NATIVE001 reminder check runs, attempt `frob.natives._build.build_natives`
whenever `frob.strata.stale_natives`/`unimportable_natives` reports
anything for the repo root -- disclosed loudly either way, and falling
through to the unchanged fail-closed NATIVE001 path whenever the rebuild
itself could not happen (no toolchain) or failed."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from typani import Err, Ok

import frob.natives._build as native_build_module
import frob.strata as strata_module
from frob.gates import (
    NATIVE_AUTOREBUILD_DISABLE_ENV,
    _maybe_autorebuild_natives,
    _native_autorebuild_disabled,
)
from frob.natives._build import BuildReport, CrateBuildResult, NativesError


def _fake_stale_entry(name: str = "strata_core"):
    """A minimal object shaped enough like `StaleNative` for
    `_maybe_autorebuild_natives`'s own `s.spec.name` access -- the function
    never reads any other attribute off a `stale_natives()` element."""
    return SimpleNamespace(spec=SimpleNamespace(name=name))


def _fake_missing_entry(name: str = "frob_core"):
    """A minimal object shaped enough like `NativeSpec` for
    `_maybe_autorebuild_natives`'s own `s.name` access on an
    `unimportable_natives()` element."""
    return SimpleNamespace(name=name)


class TestNativeAutorebuild:
    def test_stale_native_triggers_autorebuild(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_maybe_autorebuild_natives
        """A `stale_natives` finding triggers `build_natives`, and a clean
        build result logs success with no further action needed from the
        caller (the subsequent NATIVE001 check runs unchanged)."""
        monkeypatch.setattr(
            strata_module, "stale_natives", lambda root: (_fake_stale_entry(),)
        )
        monkeypatch.setattr(strata_module, "unimportable_natives", lambda root: ())
        built = {"called": False}

        def _fake_build(root: Path):
            built["called"] = True
            return Ok(
                BuildReport(
                    cargo_target_dir=tmp_path / "cargo",
                    results=[
                        CrateBuildResult(
                            name="strata_core",
                            crate_dir="strata-core",
                            returncode=0,
                            stdout="",
                            stderr="",
                        )
                    ],
                )
            )

        monkeypatch.setattr(native_build_module, "build_natives", _fake_build)

        _maybe_autorebuild_natives(tmp_path)

        assert built["called"] is True

    def test_missing_but_buildable_native_triggers_autorebuild(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_maybe_autorebuild_natives
        """An entirely unbuilt (but buildable) native reported only via
        `unimportable_natives` -- not `stale_natives` -- also triggers the
        rebuild (T-1213's second acceptance criterion: a fresh worktree
        with no built natives builds automatically on first invocation)."""
        monkeypatch.setattr(strata_module, "stale_natives", lambda root: ())
        monkeypatch.setattr(
            strata_module,
            "unimportable_natives",
            lambda root: (_fake_missing_entry(),),
        )
        built = {"called": False}

        def _fake_build(root: Path):
            built["called"] = True
            return Ok(BuildReport(cargo_target_dir=tmp_path / "cargo", results=[]))

        monkeypatch.setattr(native_build_module, "build_natives", _fake_build)

        _maybe_autorebuild_natives(tmp_path)

        assert built["called"] is True

    def test_disabled_via_env_var_skips_autorebuild(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_maybe_autorebuild_natives
        # frob:tests src/frob/gates/__init__.py::_native_autorebuild_disabled
        """`FROB_NO_NATIVE_AUTOREBUILD` set to any non-empty value skips
        the rebuild entirely -- the opt-out this ticket's guard requires
        for a caller that wants the old reminder-only behavior."""
        monkeypatch.setenv(NATIVE_AUTOREBUILD_DISABLE_ENV, "1")
        assert _native_autorebuild_disabled(tmp_path) is True

        monkeypatch.setattr(
            strata_module, "stale_natives", lambda root: (_fake_stale_entry(),)
        )
        monkeypatch.setattr(strata_module, "unimportable_natives", lambda root: ())
        built = {"called": False}
        monkeypatch.setattr(
            native_build_module,
            "build_natives",
            lambda root: built.update(called=True) or Ok(None),  # pragma: no cover
        )

        _maybe_autorebuild_natives(tmp_path)

        assert built["called"] is False

    def test_disabled_via_frob_toml(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_native_autorebuild_disabled
        """`frob.toml`'s top-level `natives_auto_rebuild = false` is the
        per-repo twin of the env-var opt-out above."""
        (tmp_path / "frob.toml").write_text("natives_auto_rebuild = false\n")
        assert _native_autorebuild_disabled(tmp_path) is True

    def test_enabled_by_default_with_no_frob_toml(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_native_autorebuild_disabled
        """No `frob.toml` at all (or one that does not mention the key)
        leaves auto-rebuild ON -- this ticket's default-on posture."""
        assert _native_autorebuild_disabled(tmp_path) is False

    def test_build_failure_falls_through_to_native001(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_maybe_autorebuild_natives
        """A per-crate build failure (returncode != 0) is disclosed via
        `_log.warning` and the function simply returns -- it never raises,
        letting the caller's own EXISTING NATIVE001 fail-closed check take
        over unchanged, per this ticket's guard against masking a real
        cannot-build case."""
        monkeypatch.setattr(
            strata_module, "stale_natives", lambda root: (_fake_stale_entry(),)
        )
        monkeypatch.setattr(strata_module, "unimportable_natives", lambda root: ())
        monkeypatch.setattr(
            native_build_module,
            "build_natives",
            lambda root: Ok(
                BuildReport(
                    cargo_target_dir=tmp_path / "cargo",
                    results=[
                        CrateBuildResult(
                            name="strata_core",
                            crate_dir="strata-core",
                            returncode=1,
                            stdout="",
                            stderr="boom",
                        )
                    ],
                )
            ),
        )

        # must not raise
        _maybe_autorebuild_natives(tmp_path)

    def test_build_natives_err_falls_through_to_native001(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_maybe_autorebuild_natives
        """An infra-level `Err` from `build_natives` (e.g. the exec kill
        switch, or `NotAGitRepo`) is also disclosed and swallowed, not
        propagated -- the rebuild attempt is best-effort, never load-
        bearing for `run_gates` itself."""
        monkeypatch.setattr(
            strata_module, "stale_natives", lambda root: (_fake_stale_entry(),)
        )
        monkeypatch.setattr(strata_module, "unimportable_natives", lambda root: ())
        monkeypatch.setattr(
            native_build_module,
            "build_natives",
            lambda root: Err(NativesError.ExecDisabled),
        )

        # must not raise
        _maybe_autorebuild_natives(tmp_path)

    def test_nothing_stale_or_missing_skips_build(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_maybe_autorebuild_natives
        """The common, already-healthy case (nothing stale, nothing
        missing) never calls `build_natives` at all."""
        monkeypatch.setattr(strata_module, "stale_natives", lambda root: ())
        monkeypatch.setattr(strata_module, "unimportable_natives", lambda root: ())
        built = {"called": False}
        monkeypatch.setattr(
            native_build_module,
            "build_natives",
            lambda root: built.update(called=True) or Ok(None),  # pragma: no cover
        )

        _maybe_autorebuild_natives(tmp_path)

        assert built["called"] is False
