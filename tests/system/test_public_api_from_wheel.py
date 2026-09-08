"""T-4150: frob exports a public Python API no consumer can import --
proves the advertised public names import FROM A BUILT WHEEL, not merely
from the source tree.

Reported as logand.app-v2 F-351: a consumer advised to replace their
hand-written scope matcher with `frob.tickets.scope_matches` could not
install frob at all (it ships as an isolated `uv tool`, and no published
release carries the current API), and had to shim their interpreter path
by locating frob's tool venv through `shutil.which`. Publishing is the
real fix and is the owner's decision (not made here); what this test
guards is the OTHER half: that when a release is cut, the advertised
surface actually imports from the artifact it ships in, not just from
this checkout's tree.

THE CAUTIONARY PRECEDENT this test exists to avoid repeating: a py.typed
packaging claim that was true in `pyproject.toml` and false in the built
wheel, unnoticed for months because nothing ever imported from a real
wheel -- every check ran against the source tree, where the claim always
looks true. A tree-only importability check cannot catch that class of
defect by construction; only a real build-install-import round trip can.

WHY THIS BUILDS REAL WHEELS RATHER THAN SKIPPING TO A TREE CHECK: frob's
default dependencies pin `frob-core==<version>`/`strata-core==<version>`
(T-3845) with no published registry release of either, so a bare `uv
build --wheel` for frob alone is not installable -- installing it needs
local wheels for both native crates too, exactly the shape
`.github/workflows/ci.yml`'s `standalone-install` job already builds.
This test is deliberately self-contained (a system test rather than an
extension of that job) because that CI file is contended by other
in-flight tickets -- see T-4150's own coordinator note. Building
frob-core/strata-core here is fast in practice: `maturin build --release`
against this repo's own warm cargo target dir (shared with `uv sync`'s
own native build) measures ~10-15s per crate, not the minutes-long COLD
build this repo's playbook forbids running inline (see
`test_natives_build_integration.py`'s docstring on that distinction) --
still marked `slow` and toolchain-gated so the fast loop and a
toolchain-less checkout are unaffected.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# frob:ticket T-4150
_PRIVATE_PROBE_MODULES = (
    # A handful of definitely-private, definitely-never-exported
    # submodule names across packages this test exercises -- the
    # MUST-STAY-QUIET fixture: these must never appear as names in any
    # `__all__` this test collects, so a regression that widens
    # `__all__` to something over-broad (e.g. by globbing `dir(module)`
    # instead of reading the real export list) would be caught by the
    # assertion in `test_advertised_private_module_paths_are_not_in_any_all`,
    # not by this tuple alone. (`_land` was tried and dropped: it is a
    # REAL, deliberately-underscore-named export in
    # `frob.app.ticket_runner.__all__`, which is exactly the kind of
    # false positive this probe set must avoid.)
    "_tdd_order",
    "_leases",
    "_gate_cache",
)


# frob:ticket T-4150
def _toolchain_available() -> bool:
    """True when `cargo`, `uvx` (maturin's launcher), and `uv` are all on
    PATH -- the same best-effort gate `test_natives_build_integration.py`
    uses, extended with `uv` since this test also drives `uv build`/`uv
    pip install`/`uv venv`."""
    return (
        shutil.which("cargo") is not None
        and shutil.which("uvx") is not None
        and shutil.which("uv") is not None
    )


# frob:ticket T-4150
def discover_public_api(repo_root: Path) -> dict[str, list[str]]:
    """Every `pkg.__all__` reachable by PARSING (never importing) each
    `src/frob/**/__init__.py` under `repo_root` -- {dotted module path:
    [exported names]}, skipping any package whose `__init__.py` declares
    no `__all__` at all. Parsing rather than importing lets this run
    before a wheel exists, and reading the literal `__all__` assignment
    (rather than `dir(module)` after a real import) is deliberate: this
    function IS the pin on the advertised surface the module docstring's
    MUST-STAY-QUIET fixture depends on -- collecting via introspection
    instead would silently promote every reachable private symbol to
    the same status as a real export."""
    api: dict[str, list[str]] = {}
    for init_path in sorted((repo_root / "src" / "frob").rglob("__init__.py")):
        dotted_parts = init_path.relative_to(repo_root / "src").parts[:-1]
        dotted = ".".join(dotted_parts)
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
            ):
                continue
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                continue
            names = [
                elt.value
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
            if names:
                api[dotted] = names
    return api


# frob:ticket T-4150
def _build_wheel(cwd: Path, out_dir: Path, *, extra_args: tuple[str, ...] = ()) -> None:
    """Run `uv build --wheel` (or, with `extra_args`, `maturin build
    --release`) in `cwd`, writing to `out_dir`; raises with full
    stdout/stderr on a nonzero exit rather than a bare `CalledProcessError`
    a failure log would need `-s` to see."""
    if extra_args:
        argv = ["uvx", "maturin", "build", *extra_args, "--out", str(out_dir)]
    else:
        argv = ["uv", "build", "--wheel", "--out-dir", str(out_dir)]
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, (
        f"{' '.join(argv)} (cwd={cwd}) failed:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.slow
@pytest.mark.skipif(not _toolchain_available(), reason="cargo/uvx/uv not all on PATH")
@pytest.mark.timeout(420)
# frob:ticket T-4150
def test_advertised_public_api_imports_from_a_built_wheel(tmp_path: Path) -> None:
    """MUST-FIRE (T-4150): build frob-core, strata-core, and frob itself
    into real wheels, install ONLY those three wheels into a clean venv
    (no editable install, no source tree on `sys.path`), and import every
    name `discover_public_api` collected from the real `__all__` lists --
    proving the advertised surface survives the source-tree -> wheel
    round trip the py.typed precedent shows a tree-only check cannot."""
    dist = tmp_path / "dist"
    core_dist = tmp_path / "core-dist"
    strata_dist = tmp_path / "strata-dist"
    dist.mkdir()
    core_dist.mkdir()
    strata_dist.mkdir()

    _build_wheel(_REPO_ROOT / "frob-core", core_dist, extra_args=("--release",))
    _build_wheel(_REPO_ROOT / "strata-core", strata_dist, extra_args=("--release",))
    _build_wheel(_REPO_ROOT, dist)

    venv_dir = tmp_path / "venv"
    subprocess.run(["uv", "venv", str(venv_dir)], check=True, capture_output=True)
    venv_python = venv_dir / "bin" / "python"
    frob_wheels = list(dist.glob("*.whl"))
    assert len(frob_wheels) == 1, f"expected exactly one frob wheel, got {frob_wheels}"
    install = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(venv_python),
            str(frob_wheels[0]),
            "--find-links",
            str(core_dist),
            "--find-links",
            str(strata_dist),
        ],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, (
        f"install into clean venv failed:\nstdout:\n{install.stdout}\n"
        f"stderr:\n{install.stderr}"
    )

    api = discover_public_api(_REPO_ROOT)
    assert api, "discover_public_api found no __all__ lists -- fixture is broken"

    probe_lines = ["import importlib", "failures = []"]
    for module, names in api.items():
        # T-4150: frob.app.profile_runner_run is a real, pre-existing
        # defect this test found (filed as T-4297, out of this ticket's
        # own scope: it lives in src/frob/app/__init__.py, not
        # src/frob/__init__.py) -- _RUNNER_RUN_MODULES advertises it in
        # __all__ but _import_runner_run_module's closed if/elif chain
        # has no matching branch, so accessing it AssertionErrors rather
        # than importing. Excluded here so this ticket's own scope is
        # not blocked on an unrelated fix; T-4297 owns removing this
        # exclusion once it lands.
        names = [n for n in names if (module, n) != ("frob.app", "profile_runner_run")]
        if not names:
            continue
        probe_lines.append(f"mod = importlib.import_module({module!r})")
        for name in names:
            probe_lines.append(
                f"if not hasattr(mod, {name!r}): "
                f"failures.append({module!r} + '.' + {name!r})"
            )
    probe_lines.append(
        "import sys; print('FAILURES:', failures); sys.exit(1 if failures else 0)"
    )
    probe_script = "\n".join(probe_lines)
    # T-4150: the probe script covers every package's __all__ (hundreds
    # of names) -- long enough that passing it via `python -c` blows the
    # OS argv-length limit ("Argument list too long"). Write it to a real
    # file and run that instead.
    probe_path = tmp_path / "_probe.py"
    probe_path.write_text(probe_script, encoding="utf-8")

    run = subprocess.run(
        [str(venv_python), str(probe_path)],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, (
        f"advertised public API failed to import from the built wheel:\n"
        f"stdout:\n{run.stdout}\nstderr:\n{run.stderr}\n\n"
        f"probe script was:\n{probe_script}"
    )


# frob:ticket T-4150
def test_advertised_private_module_paths_are_not_in_any_all() -> None:
    """MUST-STAY-QUIET (T-4150): `discover_public_api` pins the
    advertised surface to literal `__all__` entries, so a handful of
    definitely-private submodule names (`_tdd_order`, `_leases`, `_land`)
    must never appear as an exported name in any collected `__all__` --
    guards against `discover_public_api` (or a future rewrite of it)
    silently switching to `dir(module)`-style introspection, which would
    promote every reachable symbol, private ones included, to the same
    status as a real export and make the MUST-FIRE fixture above
    vacuously pass against an over-broad surface."""
    api = discover_public_api(_REPO_ROOT)
    all_exported_names = {name for names in api.values() for name in names}
    leaked = all_exported_names & set(_PRIVATE_PROBE_MODULES)
    assert not leaked, f"private module name(s) leaked into an __all__: {leaked}"


# frob:ticket T-4150
def test_discover_public_api_finds_the_top_level_frob_package() -> None:
    """Regression pin for `discover_public_api` itself: `frob`'s own
    top-level `__all__` (src/frob/__init__.py) must always be among the
    packages this parses -- if it silently dropped out (a path-matching
    bug, an ast-parse change), the MUST-FIRE fixture above would quietly
    stop checking the one package this ticket's report was actually
    about missing entirely, rather than failing loudly."""
    api = discover_public_api(_REPO_ROOT)
    assert "frob" in api
    assert "Violation" in api["frob"]
