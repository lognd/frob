"""T-0248: detect a native extension whose built artifact predates its own
source tree (the T-0166 review incident class -- a landed grammar change
left main's built `strata_core` behind, and `frob check` silently ran the
OLD parser until a human noticed a confusing SYS004)."""

from __future__ import annotations

import importlib
import importlib.util
import os
import time
from pathlib import Path

import pytest

from frob.strata._native_staleness import (
    NATIVE_SOURCE_DIRS,
    check_native_staleness_or_exit,
    stale_native_warning,
    stale_natives,
)


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test file(s) (2 \
# sites) sharing an arrange-act scaffold typical of exhaustive per-case/per-scenario \
# coverage; extracting would obscure per-case intent"
def _fake_native_package(root: Path, name: str, so_bytes: bytes) -> Path:
    """A maturin-style extension PACKAGE on `root`: `name/__init__.py` plus a
    compiled `name.abi3.so` alongside it -- mirrors
    `tests/test_testing.py`'s helper of the same name (the strata_core/
    frob_core on-disk layout)."""
    pkg = root / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("# fake native package\n")
    (pkg / f"{name}.abi3.so").write_bytes(so_bytes)
    return root


def _write_frob_toml(root: Path, name: str) -> None:
    (root / "frob.toml").write_text(
        f'[[native]]\nname = "{name}"\nbuild_cmd = "make core"\nlanguage = "rust"\n'
    )


def _write_source_dir(root: Path, source_dir: str, *, mtime: float) -> None:
    """One source file under `root/source_dir`, with mtime forced to `mtime`
    so tests can deterministically place it before/after the built artifact
    without depending on filesystem write ordering/resolution."""
    src = root / source_dir / "src"
    src.mkdir(parents=True, exist_ok=True)
    lib = src / "lib.rs"
    lib.write_text("// fake crate source\n")
    os.utime(lib, (mtime, mtime))


class TestStaleNatives:
    """`stale_natives`/`stale_native_warning`: source-tree-vs-built-artifact
    mtime comparison, T-0248."""

    def test_reports_native_grammar_ahead_of_native(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_reports_nat\
        # ive_grammar_ahead_of_native kind="unit"
        # Fixture simulating T-0166's real incident: strata-core/** source
        # newer than the built strata_core.abi3.so.
        name = "fake_native_src"
        source_dir = "fake-native-src"
        monkeypatch.setattr(
            "frob.strata._native_staleness.NATIVE_SOURCE_DIRS", (source_dir,)
        )
        _write_frob_toml(tmp_path, name)
        _fake_native_package(tmp_path, name, b"\x00compiled-old")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        found = importlib.util.find_spec(name)
        assert found is not None
        artifact = tmp_path / name / f"{name}.abi3.so"
        artifact_mtime = artifact.stat().st_mtime
        # source written strictly AFTER the built artifact
        _write_source_dir(tmp_path, source_dir, mtime=artifact_mtime + 100.0)

        stale = stale_natives(tmp_path)
        assert len(stale) == 1
        assert stale[0].spec.name == name
        assert stale[0].source_dir == source_dir
        assert stale[0].source_mtime > stale[0].artifact_mtime

        warning = stale_native_warning(tmp_path)
        assert warning is not None
        assert name in warning
        assert "make core" in warning

    def test_fresh_native_reports_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_fresh_nativ\
        # e_reports_nothing kind="unit"
        name = "fake_native_src_fresh"
        source_dir = "fake-native-src-fresh"
        monkeypatch.setattr(
            "frob.strata._native_staleness.NATIVE_SOURCE_DIRS", (source_dir,)
        )
        _write_frob_toml(tmp_path, name)
        _write_source_dir(tmp_path, source_dir, mtime=time.time() - 1000.0)
        # built AFTER the source (the normal, healthy post-`make core` state)
        _fake_native_package(tmp_path, name, b"\x00compiled-fresh")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        assert stale_natives(tmp_path) == ()
        assert stale_native_warning(tmp_path) is None

    # frob:ticket T-0513
    def test_touch_without_rebuild_is_caught_by_content_digest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """strata audit G9 counterexample: a bare `touch` on the built
        artifact (no rebuild) advances its mtime past a genuine source
        edit with NO content change to the compiled bytes -- proving (1)
        the mtime SIGNAL ALONE is fooled (`source_mtime <= artifact_mtime`
        after the touch, exactly what a pre-fix mtime-only check would
        see as "clean"), then (2) `stale_natives` still reports it via
        `reason="content-digest"` because the fix compares content, not
        just timestamps."""
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_touch_witho\
        # ut_rebuild_is_caught_by_content_digest kind="unit"
        name = "fake_native_src_touch_attack"
        source_dir = "fake-native-src-touch-attack"
        monkeypatch.setattr(
            "frob.strata._native_staleness.NATIVE_SOURCE_DIRS", (source_dir,)
        )
        monkeypatch.setattr(
            "frob.strata._native_staleness._STAMP_REL",
            Path(".frob") / "native-content-stamps-test.json",
        )
        _write_frob_toml(tmp_path, name)
        base_time = time.time() - 1000.0
        _write_source_dir(tmp_path, source_dir, mtime=base_time)
        _fake_native_package(tmp_path, name, b"\x00compiled-v1")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        # First observation: genuinely fresh, no prior stamp -- establishes
        # the baseline (source digest + artifact digest) this attack must
        # get past.
        assert stale_natives(tmp_path) == ()

        # Attacker (or an editor auto-save, or a careless rebase) edits the
        # source WITHOUT rebuilding the native at all -- the compiled
        # artifact's bytes on disk are untouched.
        lib = tmp_path / source_dir / "src" / "lib.rs"
        lib.write_text("// EDITED -- a real, un-rebuilt change\n")
        artifact = tmp_path / name / f"{name}.abi3.so"
        # ... then advances BOTH mtimes so the artifact still looks newer
        # than the edited source -- the exact touch-without-rebuild shape.
        now = time.time()
        os.utime(lib, (now, now))
        os.utime(artifact, (now + 50.0, now + 50.0))

        # Counterexample part 1: the mtime SIGNAL ALONE says "clean" --
        # this is the vulnerability G9 names.
        assert lib.stat().st_mtime <= artifact.stat().st_mtime

        # Counterexample part 2: the fix catches it anyway.
        stale = stale_natives(tmp_path)
        assert len(stale) == 1
        assert stale[0].spec.name == name
        assert stale[0].reason == "content-digest"

        warning = stale_native_warning(tmp_path)
        assert warning is not None
        assert "content digest" in warning
        assert name in warning

    # frob:ticket T-0513
    def test_real_rebuild_after_edit_is_not_a_false_positive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression guard: a GENUINE rebuild (the compiled artifact's
        bytes actually change) after a source edit must NOT be
        misreported as stale via content-digest -- only an unrebuilt edit
        (artifact bytes unchanged) is the touch-attack signature."""
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_real_rebuil\
        # d_after_edit_is_not_a_false_positive kind="unit"
        name = "fake_native_src_real_rebuild"
        source_dir = "fake-native-src-real-rebuild"
        monkeypatch.setattr(
            "frob.strata._native_staleness.NATIVE_SOURCE_DIRS", (source_dir,)
        )
        monkeypatch.setattr(
            "frob.strata._native_staleness._STAMP_REL",
            Path(".frob") / "native-content-stamps-test-2.json",
        )
        _write_frob_toml(tmp_path, name)
        base_time = time.time() - 1000.0
        _write_source_dir(tmp_path, source_dir, mtime=base_time)
        _fake_native_package(tmp_path, name, b"\x00compiled-v1")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        assert stale_natives(tmp_path) == ()  # establishes the baseline

        lib = tmp_path / source_dir / "src" / "lib.rs"
        lib.write_text("// a real, then genuinely rebuilt, change\n")
        artifact = tmp_path / name / f"{name}.abi3.so"
        # a REAL rebuild: the compiled artifact's BYTES actually change,
        # not just its mtime.
        artifact.write_bytes(b"\x00compiled-v2-really-rebuilt")
        now = time.time()
        os.utime(lib, (now, now))
        os.utime(artifact, (now + 50.0, now + 50.0))

        assert stale_natives(tmp_path) == ()
        assert stale_native_warning(tmp_path) is None

    def test_unbuilt_native_is_not_reported_as_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_unbuilt_nat\
        # ive_is_not_reported_as_stale kind="unit"
        # An unbuilt native is T-0333's `missing_natives` diagnostic -- a
        # different remedy ("build it") from "stale" ("rebuild it").
        name = "fake_native_src_unbuilt"
        source_dir = "fake-native-src-unbuilt"
        monkeypatch.setattr(
            "frob.strata._native_staleness.NATIVE_SOURCE_DIRS", (source_dir,)
        )
        _write_frob_toml(tmp_path, name)
        _write_source_dir(tmp_path, source_dir, mtime=time.time())

        assert stale_natives(tmp_path) == ()
        assert stale_native_warning(tmp_path) is None

    def test_no_matching_source_dir_is_not_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_no_matching\
        # _source_dir_is_not_reported kind="unit"
        name = "fakenat_no_source_dir"
        _write_frob_toml(tmp_path, name)
        _fake_native_package(tmp_path, name, b"\x00compiled")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        # no source dir under NATIVE_SOURCE_DIRS exists in tmp_path at all
        assert stale_natives(tmp_path) == ()

    def test_default_native_source_dirs_match_repo_convention(self) -> None:
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_default_nat\
        # ive_source_dirs_match_repo_convention kind="unit"
        assert NATIVE_SOURCE_DIRS == ("strata-core", "frob-core")


class TestCheckNativeStalenessOrExit:
    """`check_native_staleness_or_exit`: the `make check` entry point."""

    def test_exits_nonzero_and_prints_when_stale(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestCheckNativeStalenessOrExit.te\
        # st_exits_nonzero_and_prints_when_stale kind="unit"
        monkeypatch.setattr(
            "frob.strata._native_staleness.stale_native_warning",
            lambda root: "STALE NATIVE: fake",
        )
        with pytest.raises(SystemExit) as exc_info:
            check_native_staleness_or_exit(tmp_path)
        assert exc_info.value.code == 1
        assert "STALE NATIVE" in capsys.readouterr().err

    def test_returns_none_when_not_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/strata/test_native_staleness.py::TestCheckNativeStalenessOrExit.te\
        # st_returns_none_when_not_stale kind="unit"
        monkeypatch.setattr(
            "frob.strata._native_staleness.stale_native_warning", lambda root: None
        )
        assert check_native_staleness_or_exit(tmp_path) is None


class TestNativeStalenessBranchGaps:
    """T-0160 batch 8: TEST005 branch-coverage gaps in
    src/frob/strata/_native_staleness.py -- error/degraded paths
    _newest_mtime, _artifact_mtime, and stale_natives never exercised
    above."""

    def test_newest_mtime_absent_directory_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/strata/_native_staleness.py::stale_natives kind="unit"
        from frob.strata._native_staleness import _newest_mtime

        assert _newest_mtime(tmp_path / "does-not-exist") is None

    def test_newest_mtime_skips_unstatable_file_and_keeps_max(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/strata/_native_staleness.py::stale_natives kind="unit"
        # an OSError statting one file must be skipped, not raised, and the
        # true newest mtime among the remaining files must still win (the
        # "keep old newest" branch when a later file is NOT newer).
        from frob.strata._native_staleness import _newest_mtime

        older = tmp_path / "older.rs"
        older.write_text("old")
        newer = tmp_path / "newer.rs"
        newer.write_text("new")
        import time

        now = time.time()
        os.utime(older, (now - 100.0, now - 100.0))
        os.utime(newer, (now, now))

        real_stat = Path.stat

        def fake_stat(self, *a, **kw):
            if self.name == "broken.rs":
                raise OSError("boom")
            return real_stat(self, *a, **kw)

        broken = tmp_path / "broken.rs"
        broken.write_text("broken")
        monkeypatch.setattr(Path, "stat", fake_stat)

        result = _newest_mtime(tmp_path)
        assert result == real_stat(newer).st_mtime

    def test_artifact_mtime_find_spec_error_is_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/strata/_native_staleness.py::stale_natives kind="unit"
        from frob.strata._native_staleness import _artifact_mtime
        from frob.testing import NativeSpec

        def _boom(name: str):
            raise ImportError("shadowed name")

        monkeypatch.setattr(importlib.util, "find_spec", _boom)
        spec = NativeSpec(name="whatever", build_cmd="make core")
        assert _artifact_mtime(spec) is None

    def test_artifact_mtime_no_compiled_artifact_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/strata/_native_staleness.py::stale_natives kind="unit"
        # resolvable name, but no compiled artifact (pure-python stub) --
        # must report None, not crash on an empty artifact list.
        from frob.strata._native_staleness import _artifact_mtime
        from frob.testing import NativeSpec

        name = "fakenat_purepy_stub_staleness"
        pkg = tmp_path / name
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# pure-python stub, no .so\n")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        spec = NativeSpec(name=name, build_cmd="make core")
        assert _artifact_mtime(spec) is None

    def test_artifact_mtime_unstatable_artifact_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/strata/_native_staleness.py::stale_natives kind="unit"
        # an OSError statting the compiled artifact must degrade to None
        # (via an empty mtimes list), not raise.
        from frob.strata._native_staleness import _artifact_mtime
        from frob.testing import NativeSpec

        name = "fakenat_unstatable"
        _fake_native_package(tmp_path, name, b"\x00v1")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        real_stat = Path.stat

        def fake_stat(self, *a, **kw):
            if self.suffix == ".so":
                raise OSError("boom")
            return real_stat(self, *a, **kw)

        monkeypatch.setattr(Path, "stat", fake_stat)
        spec = NativeSpec(name=name, build_cmd="make core")
        assert _artifact_mtime(spec) is None

    def test_stale_natives_degrades_on_malformed_config(self, tmp_path: Path) -> None:
        # frob:tests src/frob/strata/_native_staleness.py::stale_natives kind="unit"
        # a malformed [[native]] table must not crash stale_natives -- it
        # degrades to reporting nothing, with a warning logged.
        (tmp_path / "frob.toml").write_text("this is [not valid toml")
        assert stale_natives(tmp_path) == ()

    def test_stale_natives_skips_empty_source_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/strata/_native_staleness.py::stale_natives kind="unit"
        # a matching source dir that exists but contains no files at all
        # has _newest_mtime -> None, which must be skipped (not compared
        # against the artifact) rather than raising a TypeError.
        name = "fakenat_empty_src"
        source_dir = "fakenat-empty-src"
        monkeypatch.setattr(
            "frob.strata._native_staleness.NATIVE_SOURCE_DIRS", (source_dir,)
        )
        _write_frob_toml(tmp_path, name)
        _fake_native_package(tmp_path, name, b"\x00compiled")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        (tmp_path / source_dir).mkdir()  # exists, but empty -> _newest_mtime is None

        assert stale_natives(tmp_path) == ()
