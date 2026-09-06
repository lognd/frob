"""T-3884: `scripts/artifact_smoke.py` is the gate that BLOCKS
`.github/workflows/release.yml`'s `upload` job -- these tests prove it
actually catches the exact regression it was built for (T-3857) and stays
quiet on a healthy build. Real network/subprocess tests (`uv build`, `uv
venv`, `uv pip install` against the real index), so `slow`-marked and
skipped without network -- see `docs/guides/release.md`'s "Artifact smoke
stage" section for why this is the strongest available proof: a synthetic
fixture that mocked dependency resolution would not have caught T-3857
either, since the bug was in what a REAL resolve does against a REAL
index.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SMOKE_SCRIPT = _REPO_ROOT / "scripts" / "artifact_smoke.py"


def _uv_available() -> bool:
    """Whether `uv` is on PATH -- these tests need it to build wheels and
    venvs; skipped (not failed) when it is not, same posture other
    network/toolchain-dependent system tests in this suite take."""
    return shutil.which("uv") is not None


def _build_wheel(src_root: Path, out_dir: Path) -> Path:
    """`uv build --wheel` a copy of `src_root` into `out_dir`; returns the
    built wheel path."""
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=src_root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    (wheel,) = out_dir.glob("frob-*.whl")
    return wheel


def _copy_source_tree(tmp_path: Path, *, serve_pin: str) -> Path:
    """A copy of this repo's own `src/frob`, `pyproject.toml` (with the
    `serve` extra's mcp pin rewritten to `serve_pin`), `README.md`, and
    `LICENSE` -- everything `uv build --wheel` needs, at `tmp_path`. This
    directly exercises the fixed source tree's own packaging metadata,
    not a synthetic stand-in package -- a mocked resolver would not have
    caught T-3857 either, since the bug was in what a REAL resolve
    against a REAL index does with this exact specifier."""
    dest = tmp_path / "src_copy"
    shutil.copytree(_REPO_ROOT / "src", dest / "src")
    shutil.copy2(_REPO_ROOT / "README.md", dest / "README.md")
    shutil.copy2(_REPO_ROOT / "LICENSE", dest / "LICENSE")
    pyproject_text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'serve = ["mcp>=1.28.1,<2"]' in pyproject_text, (
        "this repo's own serve pin shape changed -- update this fixture's "
        "string-replace target"
    )
    pyproject_text = pyproject_text.replace(
        'serve = ["mcp>=1.28.1,<2"]', f'serve = ["{serve_pin}"]'
    )
    (dest / "pyproject.toml").write_text(pyproject_text, encoding="utf-8")
    return dest


class TestArtifactSmokeMustFire:
    """MUST-FIRE fixture (T-3857's exact shape): an unbounded `mcp`
    pin in the `serve` extra must fail `check_serve_extra`, not pass
    silently."""

    @pytest.mark.skipif(not _uv_available(), reason="uv not on PATH")
    def test_unbounded_mcp_pin_fails_serve_extra_check(self, tmp_path: Path) -> None:
        """Rebuild this repo's own wheel with the PRE-T-3857 unbounded
        `mcp>=1.28.1` pin restored, run the smoke script's serve-extra
        check against a real index resolve, and assert it fails with the
        mcp 2.x rename error -- the actual regression, not a stand-in."""
        core_core = _REPO_ROOT / "frob-core" / "target" / "wheels"
        core_strata = _REPO_ROOT / "strata-core" / "target" / "wheels"
        if not list(core_core.glob("frob_core-*.whl")) or not list(
            core_strata.glob("strata_core-*.whl")
        ):
            pytest.skip("frob-core/strata-core not built locally")
        core_wheels_dir = tmp_path / "core-wheels"
        core_wheels_dir.mkdir()
        for whl in list(core_core.glob("frob_core-*.whl"))[:1] + list(
            core_strata.glob("strata_core-*.whl")
        )[:1]:
            shutil.copy2(whl, core_wheels_dir)

        broken_src = _copy_source_tree(tmp_path, serve_pin="mcp>=1.28.1")
        out_dir = tmp_path / "dist"
        out_dir.mkdir()
        wheel = _build_wheel(broken_src, out_dir)

        result = subprocess.run(
            [
                sys.executable,
                str(_SMOKE_SCRIPT),
                "--wheel",
                str(wheel),
                "--core-wheels-dir",
                str(core_wheels_dir),
                "--skip-native",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode != 0, (
            "the unbounded mcp pin must fail the smoke gate -- it did not:\n"
            + result.stdout
            + result.stderr
        )
        assert "serve-extra" in result.stdout + result.stderr
        assert "MCPServer" in result.stdout + result.stderr or "mcp 2.x" in (
            result.stdout + result.stderr
        )


class TestArtifactSmokeAbsentCores:
    """T-3935 MUST-FIRE fixture: `main` run end-to-end against a REAL
    built wheel, with the cores deliberately absent, must report the
    named missing core -- not the raw "was not found in the package
    registry" resolver trace that made CI run 34005559354's failure
    indistinguishable from a wrong version pin."""

    @pytest.mark.skipif(not _uv_available(), reason="uv not on PATH")
    def test_absent_cores_report_named_core_missing(self, tmp_path: Path) -> None:
        """A real wheel, `--core-wheels-dir` pointed at an EMPTY
        directory: the smoke script must fail fast, name both missing
        cores, and never even attempt a pip install."""
        fixed_src = _copy_source_tree(tmp_path, serve_pin="mcp>=1.28.1,<2")
        out_dir = tmp_path / "dist"
        out_dir.mkdir()
        wheel = _build_wheel(fixed_src, out_dir)

        empty_core_dir = tmp_path / "no-cores"
        empty_core_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(_SMOKE_SCRIPT),
                "--wheel",
                str(wheel),
                "--core-wheels-dir",
                str(empty_core_dir),
                "--skip-native",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode != 0, (
            "absent cores must fail the smoke gate -- it did not:\n"
            + result.stdout
            + result.stderr
        )
        combined = result.stdout + result.stderr
        assert "frob-core" in combined
        assert "strata-core" in combined
        assert "not found in the package registry" not in combined, (
            "the raw resolver trace leaked through -- the preflight should "
            "have caught this before any pip install was attempted:\n"
            + combined
        )


class TestArtifactSmokeMustStayQuiet:
    """MUST-STAY-QUIET: the current, fixed wheel must pass every check
    cleanly."""

    @pytest.mark.skipif(not _uv_available(), reason="uv not on PATH")
    def test_current_pin_passes_serve_extra_check(self, tmp_path: Path) -> None:
        """The repo's OWN current `pyproject.toml` (bounded `mcp<2`)
        must pass the smoke script's serve-extra check cleanly."""
        core_core = _REPO_ROOT / "frob-core" / "target" / "wheels"
        core_strata = _REPO_ROOT / "strata-core" / "target" / "wheels"
        if not list(core_core.glob("frob_core-*.whl")) or not list(
            core_strata.glob("strata_core-*.whl")
        ):
            pytest.skip("frob-core/strata-core not built locally")
        core_wheels_dir = tmp_path / "core-wheels"
        core_wheels_dir.mkdir()
        for whl in list(core_core.glob("frob_core-*.whl"))[:1] + list(
            core_strata.glob("strata_core-*.whl")
        )[:1]:
            shutil.copy2(whl, core_wheels_dir)

        fixed_src = _copy_source_tree(tmp_path, serve_pin="mcp>=1.28.1,<2")
        out_dir = tmp_path / "dist"
        out_dir.mkdir()
        wheel = _build_wheel(fixed_src, out_dir)

        result = subprocess.run(
            [
                sys.executable,
                str(_SMOKE_SCRIPT),
                "--wheel",
                str(wheel),
                "--core-wheels-dir",
                str(core_wheels_dir),
                "--skip-native",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "PASS serve-extra" in result.stdout
