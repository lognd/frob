"""T-0993: a real (non-mocked) `frob natives build` integration test.

gate:TEST TEST003 flagged `src/frob/natives` as having 0 integration-kind
test edges (min_integration=1) -- `tests/unit/test_natives_build.py`
exercises `build_natives` with `guarded_subprocess_run` monkeypatched,
which is genuine unit coverage of the branching/error-mapping logic but
never actually spawns `maturin` or compiles anything, so a real break in
the `maturin develop --uv --release` invocation itself (a flag rename, an
incompatible pyo3/maturin pairing, a `CARGO_TARGET_DIR` wiring mistake)
would pass every existing test and only surface the next time a human ran
`make core` by hand.

This test closes that gap the way T-0993 scoped it: a MINIMAL synthetic
pyo3 crate (one `#[pyfunction]`, no dependencies beyond pyo3 itself) built
for real via `build_natives`, then imported and called to prove the
resulting extension module actually works end to end. Measured locally
(2026-07-27, warm cargo/crates.io cache shared with this repo's own
strata_core/frob_core crates): ~7s cold-target-dir wall clock -- see this
module's `test_build_natives_compiles_and_imports_real_crate` docstring
for the exact number. That is far below the `make coverage`-class,
minutes-long real build this repo's playbook forbids running inline
(strata_core/frob_core themselves), so it is safe as a `slow`-marked
system test rather than needing a bespoke opt-in env var: `-m "not slow"`
already excludes it from the fast loop, and CI's slow lane has ample
headroom under the generous timeout below.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from frob.natives import build_natives

pytestmark = pytest.mark.slow

# frob:ticket T-0993
_CARGO_TOML = """\
[package]
name = "mincrate"
version = "0.1.0"
edition = "2021"

[lib]
name = "mincrate"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
"""

# frob:ticket T-0993
_LIB_RS = """\
use pyo3::prelude::*;

#[pyfunction]
fn ping() -> PyResult<i64> {
    Ok(1)
}

#[pymodule]
fn mincrate(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ping, m)?)?;
    Ok(())
}
"""


# frob:ticket T-0993
def _toolchain_available() -> bool:
    """True when both `cargo` and `uvx` (maturin's launcher) are on PATH --
    the same best-effort gate `build_natives` itself degrades against for
    a checkout with no rust toolchain (T-0864's docstring)."""
    return shutil.which("cargo") is not None and shutil.which("uvx") is not None


# frob:ticket T-0993
def _init_git_repo(root: Path) -> None:
    """Minimal git init so `build_natives`'s `git_common_dir` lookup
    resolves -- `build_natives` requires `root` to be inside a real git
    checkout regardless of whether anything is actually committed."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)


# frob:ticket T-0993
def _write_mincrate(root: Path) -> None:
    """Write the minimal synthetic pyo3 crate this test builds for real,
    under the `mincrate` name (`_crate_dir_for`'s underscore/hyphen
    convention -- no underscore here, so the crate dir and native name
    match verbatim)."""
    crate_dir = root / "mincrate"
    (crate_dir / "src").mkdir(parents=True)
    (crate_dir / "Cargo.toml").write_text(_CARGO_TOML)
    (crate_dir / "src" / "lib.rs").write_text(_LIB_RS)
    (root / "frob.toml").write_text(
        '[[native]]\nname = "mincrate"\nbuild_cmd = "true"\nlanguage = "rust"\n'
    )


@pytest.mark.skipif(not _toolchain_available(), reason="cargo/uvx not on PATH")
# T-0993: measured ~7s locally with a warm crates.io/pyo3 cache (shared
# with this repo's own strata_core/frob_core crates, which already pull
# the same pyo3 dependency tree) -- 180s gives headroom for a fully cold
# cache (crates.io index clone + pyo3 dependency compile) on a fresh CI
# runner without approaching the minutes-long real-crate build this
# module's docstring explains this test deliberately avoids.
@pytest.mark.timeout(180)
# frob:ticket T-0993
def test_build_natives_compiles_and_imports_real_crate(tmp_path: Path) -> None:
    # frob:tests src/frob/natives/_build.py::build_natives kind="integration"
    _init_git_repo(tmp_path)
    _write_mincrate(tmp_path)

    result = build_natives(tmp_path)

    assert result.is_ok, result
    report = result.danger_ok
    assert report.ok, [r.stderr for r in report.results if not r.ok]
    assert {r.name for r in report.results} == {"mincrate"}

    # The crate is installed editable into THIS test process's own venv
    # (`maturin develop`'s contract) -- import it fresh and call the one
    # exported function to prove the built extension actually works, not
    # just that the subprocess exited zero.
    check = subprocess.run(
        [sys.executable, "-c", "import mincrate; print(mincrate.ping())"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert check.returncode == 0, check.stderr
    assert check.stdout.strip() == "1"
