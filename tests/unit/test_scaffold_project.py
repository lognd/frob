# frob:ticket T-0160
"""Unit tests for `frob.scaffold.project` -- direct calls, no subprocess/uv.

Covers `render_project`'s branches (unknown type, force vs. existing-output
conflict, successful render) and `list_project_types` without paying the
cost of the slow end-to-end scaffold DX test, which exercises the module
only via a spawned subprocess and does not attribute coverage back to it.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import DictLoader, Environment

from frob.scaffold.project import (
    ScaffoldError,
    _ManifestEntry,
    _resolve_manifest_paths,
    _write_manifest_entries,
    list_project_types,
    render_project,
)


# frob:tests tests/unit/test_scaffold_project.py::test_list_project_types_includes_known_types
def test_list_project_types_includes_known_types() -> None:
    """`list_project_types` surfaces every registered manifest key."""
    types = list_project_types()
    assert "python-tool" in types
    assert "python-library" in types
    assert "cpp-library" in types
    assert "web-app" in types


# frob:tests tests/unit/test_scaffold_project.py::test_render_project_unknown_type_is_err
def test_render_project_unknown_type_is_err() -> None:
    """An unregistered project type returns `UnknownType`, never raises."""
    result = render_project("not-a-real-type", "demo", Path("/tmp/does-not-matter"))
    assert result.is_err
    assert result.danger_err is ScaffoldError.UnknownType


# frob:tests tests/unit/test_scaffold_project.py::test_render_project_writes_expected_files
def test_render_project_writes_expected_files(tmp_path: Path) -> None:
    """A successful render writes every manifest entry for the given type."""
    result = render_project("python-tool", "demo", tmp_path)
    assert result.is_ok
    written = result.danger_ok
    assert len(written) > 0
    for path in written:
        assert path.exists()
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "src" / "demo" / "__init__.py").exists()


# frob:tests tests/unit/test_scaffold_project.py::test_render_project_existing_output_without_force_is_err
def test_render_project_existing_output_without_force_is_err(tmp_path: Path) -> None:
    """Re-rendering without force=True refuses to clobber existing output."""
    first = render_project("python-tool", "demo", tmp_path)
    assert first.is_ok

    second = render_project("python-tool", "demo", tmp_path)
    assert second.is_err
    assert second.danger_err is ScaffoldError.OutputExists


# frob:tests tests/unit/test_scaffold_project.py::test_render_project_force_overwrites_existing_output
def test_render_project_force_overwrites_existing_output(tmp_path: Path) -> None:
    """force=True re-renders even when the output files already exist."""
    first = render_project("python-tool", "demo", tmp_path)
    assert first.is_ok

    second = render_project("python-tool", "demo", tmp_path, force=True)
    assert second.is_ok
    assert len(second.danger_ok) == len(first.danger_ok)


# frob:tests tests/unit/test_scaffold_project.py::test_render_project_all_registered_types_succeed
def test_render_project_all_registered_types_succeed(tmp_path: Path) -> None:
    """Every registered manifest type renders cleanly for a fresh output dir."""
    for project_type in list_project_types():
        out_dir = tmp_path / project_type
        result = render_project(project_type, "demo", out_dir)
        assert result.is_ok, f"{project_type} failed to render: {result.err}"


# frob:tests tests/unit/test_scaffold_project.py::test_resolve_manifest_paths_bad_output_expression_is_render_failed
def test_resolve_manifest_paths_bad_output_expression_is_render_failed(
    tmp_path: Path,
) -> None:
    """A malformed Jinja expression in an entry's `output` path is caught
    and reported as `RenderFailed` rather than propagating the raw
    Jinja2 exception."""
    env = Environment(loader=DictLoader({}))
    entries = [_ManifestEntry(template="whatever.j2", output="{{ unterminated")]

    result = _resolve_manifest_paths(entries, env, {}, tmp_path)

    assert result.is_err
    assert result.danger_err is ScaffoldError.RenderFailed


# frob:tests tests/unit/test_scaffold_project.py::test_write_manifest_entries_missing_template_is_template_not_found
def test_write_manifest_entries_missing_template_is_template_not_found(
    tmp_path: Path,
) -> None:
    """A manifest entry pointing at a template absent from the loader
    reports `TemplateNotFound`, not an unhandled Jinja2 exception."""
    env = Environment(loader=DictLoader({}))
    entries = [
        (_ManifestEntry(template="missing.j2", output="out.txt"), tmp_path / "out.txt")
    ]

    result = _write_manifest_entries(entries, env, {})

    assert result.is_err
    assert result.danger_err is ScaffoldError.TemplateNotFound


# frob:tests tests/unit/test_scaffold_project.py::test_render_project_propagates_resolve_failure
def test_render_project_propagates_resolve_failure(tmp_path: Path, monkeypatch) -> None:
    """When output-path resolution fails, `render_project` returns that
    error directly rather than proceeding to write anything."""
    import frob.scaffold.project as project_mod

    bad_manifest = {
        "bad-type": [_ManifestEntry(template="whatever.j2", output="{{ unterminated")]
    }
    monkeypatch.setitem(project_mod._MANIFESTS, "bad-type", bad_manifest["bad-type"])

    result = render_project("bad-type", "demo", tmp_path)

    assert result.is_err
    assert result.danger_err is ScaffoldError.RenderFailed


# frob:tests tests/unit/test_scaffold_project.py::test_hooks_dir_kill_switch_refuses_without_spawning
# frob:ticket T-0803
def test_hooks_dir_kill_switch_refuses_without_spawning(
    tmp_path: Path, monkeypatch
) -> None:
    """T-0803: FROB_DISABLE_EXEC=1 must make `_hooks_dir`'s `git rev-parse
    --git-path hooks` spawn refuse (via `frob.gitio.run_argv` ->
    `guarded_subprocess_run`) instead of bypassing the T-0200/T-0778 exec
    guard -- proven with a spy on the real `subprocess.run` so a spawn
    attempt would be observed, not assumed. This is the module's one
    subprocess-touching function; the rest of this file stays pure/
    subprocess-free per its own docstring."""
    import subprocess

    from frob.scaffold.project import _hooks_dir

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

    monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
    spawned = False
    real_run = subprocess.run

    def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
        nonlocal spawned
        spawned = True
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)
    result = _hooks_dir(tmp_path)
    assert not spawned
    assert result.is_err
    assert result.danger_err == ScaffoldError.NotAGitRepo
