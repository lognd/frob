# frob:ticket T-0160
"""Unit tests for `frob.scaffold.project` -- direct calls, no subprocess/uv.

Covers `render_project`'s branches (unknown type, force vs. existing-output
conflict, successful render) and `list_project_types` without paying the
cost of the slow end-to-end scaffold DX test, which exercises the module
only via a spawned subprocess and does not attribute coverage back to it.
"""

from __future__ import annotations

import ast
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
from frob.tickets import TicketSpec, new_ticket
from frob.tickets._models import Origin, TicketKind
from frob.tickets._store import _store_mode
from frob.tickets._store_migrate import migrate_v1_to_v2


# frob:tests \
# tests/unit/test_scaffold_project.py::test_list_project_types_includes_known_types
def test_list_project_types_includes_known_types() -> None:
    """`list_project_types` surfaces every registered manifest key."""
    types = list_project_types()
    assert "python-tool" in types
    assert "python-library" in types
    assert "cpp-library" in types
    assert "web-app" in types


# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_unknown_type_is_err
def test_render_project_unknown_type_is_err() -> None:
    """An unregistered project type returns `UnknownType`, never raises."""
    result = render_project("not-a-real-type", "demo", Path("/tmp/does-not-matter"))
    assert result.is_err
    assert result.danger_err is ScaffoldError.UnknownType


# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_writes_expected_files
def test_render_project_writes_expected_files(tmp_path: Path) -> None:
    """A successful render writes every manifest entry for the given type
    under `output_dir / name` (T-3271: `output_dir` is the PARENT), never
    loose into `output_dir` itself."""
    result = render_project("python-tool", "demo", tmp_path)
    assert result.is_ok
    written = result.danger_ok
    assert len(written) > 0
    for path in written:
        assert path.exists()
    assert (tmp_path / "demo" / "README.md").exists()
    assert (tmp_path / "demo" / "src" / "demo" / "__init__.py").exists()
    assert not (tmp_path / "README.md").exists()


# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_existing_output_without_forc\
# e_is_err
def test_render_project_existing_output_without_force_is_err(tmp_path: Path) -> None:
    """Re-rendering without force=True refuses to clobber existing output."""
    first = render_project("python-tool", "demo", tmp_path)
    assert first.is_ok

    second = render_project("python-tool", "demo", tmp_path)
    assert second.is_err
    assert second.danger_err is ScaffoldError.OutputExists


# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_force_overwrites_existing_ou\
# tput
def test_render_project_force_overwrites_existing_output(tmp_path: Path) -> None:
    """force=True re-renders even when the output files already exist."""
    first = render_project("python-tool", "demo", tmp_path)
    assert first.is_ok

    second = render_project("python-tool", "demo", tmp_path, force=True)
    assert second.is_ok
    assert len(second.danger_ok) == len(first.danger_ok)


# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_all_registered_types_succeed
def test_render_project_all_registered_types_succeed(tmp_path: Path) -> None:
    """Every registered manifest type renders cleanly for a fresh output dir."""
    for project_type in list_project_types():
        out_dir = tmp_path / project_type
        result = render_project(project_type, "demo", out_dir)
        assert result.is_ok, f"{project_type} failed to render: {result.err}"


# frob:ticket T-1576
# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_all_types_default_to_rapid_p\
# rofile
def test_render_project_all_types_default_to_rapid_profile(tmp_path: Path) -> None:
    """T-1576: every registered project type's rendered `frob.toml` opts a
    brand-new scaffolded repo into `[profile] profile = "rapid"` -- the
    one-way auto-ratchet (`frob.tickets._profile`) upgrades it to
    `standard` automatically once the repo outgrows the thresholds."""
    for project_type in list_project_types():
        out_dir = tmp_path / f"{project_type}-profile"
        result = render_project(project_type, "demo", out_dir)
        assert result.is_ok, f"{project_type} failed to render: {result.err}"
        toml_path = out_dir / "demo" / "frob.toml"
        assert toml_path.exists(), f"{project_type} did not write frob.toml"
        contents = toml_path.read_text(encoding="utf-8")
        assert "[profile]" in contents, f"{project_type} missing [profile]"
        assert 'profile = "rapid"' in contents, f"{project_type} not rapid by default"


# frob:tests \
# tests/unit/test_scaffold_project.py::test_resolve_manifest_paths_bad_output_expressio\
# n_is_render_failed
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


# frob:tests \
# tests/unit/test_scaffold_project.py::test_write_manifest_entries_missing_template_is_\
# template_not_found
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


# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_propagates_resolve_failure
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


# frob:tests \
# tests/unit/test_scaffold_project.py::test_hooks_dir_kill_switch_refuses_without_spawn\
# ing
# frob:ticket T-0803
# frob:ticket T-3271
# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_creates_name_subdir_must_fire
def test_render_project_creates_name_subdir_must_fire(tmp_path: Path) -> None:
    """MUST-FIRE (T-3271): scaffolding `demo` into a temp dir creates
    `<tmp>/demo/README.md`, never `<tmp>/README.md` -- `output_dir` is the
    PARENT, matching docs/commands/scaffold.md's quickstart."""
    result = render_project("python-tool", "demo", tmp_path)
    assert result.is_ok
    assert (tmp_path / "demo" / "README.md").exists()
    assert not (tmp_path / "README.md").exists()


# frob:ticket T-3271
# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_existing_collision_still_ref\
# uses_must_stay_quiet
def test_render_project_existing_collision_still_refuses_must_stay_quiet(
    tmp_path: Path,
) -> None:
    """MUST-STAY-QUIET (T-3271): the pre-existing OutputExists guard must
    not regress -- a colliding file in the (now name-suffixed) project
    directory still refuses without force, and force still overwrites."""
    first = render_project("python-tool", "demo", tmp_path)
    assert first.is_ok

    second = render_project("python-tool", "demo", tmp_path)
    assert second.is_err
    assert second.danger_err is ScaffoldError.OutputExists

    third = render_project("python-tool", "demo", tmp_path, force=True)
    assert third.is_ok


# frob:ticket T-3271
# frob:tests \
# tests/unit/test_scaffold_project.py::test_render_project_bare_form_does_not_scatter_i\
# nto_existing_project_root
def test_render_project_bare_form_does_not_scatter_into_existing_project_root(
    tmp_path: Path,
) -> None:
    """THIRD FIXTURE (T-3271): the bare form (output_dir defaults to ".",
    i.e. the caller's own directory in the CLI) run inside an existing
    project root does not scatter files into it -- everything lands under
    a `name` subdirectory instead, structurally, regardless of what
    `tmp_path` already contains."""
    (tmp_path / "README.md").write_text("pre-existing project readme\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'diax'\n")

    result = render_project("python-tool", "demo", tmp_path)

    assert result.is_ok
    assert (tmp_path / "demo" / "README.md").exists()
    # The pre-existing files at tmp_path's root are untouched.
    assert tmp_path.joinpath("README.md").read_text() == "pre-existing project readme\n"
    assert "diax" in tmp_path.joinpath("pyproject.toml").read_text()


# frob:ticket T-3272
# frob:tests \
# tests/unit/test_scaffold_project.py::test_freshly_scaffolded_project_is_v2_must_fire
def test_freshly_scaffolded_project_is_v2_must_fire(tmp_path: Path) -> None:
    """MUST-FIRE (T-3272): a freshly scaffolded project ships no ledger
    content of any shape, so it is detected as v2, and `frob ticket new`
    in it writes `tickets/T-0001/ticket.md`, not a `tickets.md` monofile
    entry -- the scaffold's fresh-repo default is now ledger v2
    (`_store_mode`'s own T-1553 fresh-repo default, previously defeated
    by the scaffold shipping an empty `tickets.md`)."""
    result = render_project("python-tool", "demo", tmp_path)
    assert result.is_ok
    project_dir = tmp_path / "demo"
    assert not (project_dir / "tickets.md").exists()
    assert not (project_dir / "tickets").exists()
    assert _store_mode(project_dir) == "v2"

    spec = TicketSpec(title="probe", kind=TicketKind.DOCS, origin=Origin.HUMAN)
    created = new_ticket(project_dir, spec)
    assert created.is_ok
    ticket_id = created.danger_ok.id
    assert (project_dir / "tickets" / ticket_id / "ticket.md").exists()


# frob:ticket T-3272
# frob:tests \
# tests/unit/test_scaffold_project.py::test_existing_v1_repo_unaffected_must_stay_quiet
def test_existing_v1_repo_unaffected_must_stay_quiet(tmp_path: Path) -> None:
    """MUST-STAY-QUIET (T-3272): an existing v1 repo (`tickets.md` present,
    no `tickets/T-*/` tree) is unaffected by the scaffold change -- it is
    still detected as v1 ('single') and behaves exactly as today. This
    does not touch `render_project` at all; it directly proves the
    detection this ticket relies on is unchanged for pre-existing repos."""
    (tmp_path / "tickets.md").write_text(
        "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"
    )
    assert _store_mode(tmp_path) == "single"


# frob:ticket T-3272
# frob:tests \
# tests/unit/test_scaffold_project.py::test_migrator_still_works_on_v1_repo_third_fixtu\
# re
def test_migrator_still_works_on_v1_repo_third_fixture(tmp_path: Path) -> None:
    """THIRD FIXTURE (T-3272): the one-shot `migrate_v1_to_v2` migrator
    still works on a genuine v1 repo (a monofile ledger with real ticket
    content) after this change -- the scaffold no longer writing
    `tickets.md` did not touch the migrator itself."""
    (tmp_path / "tickets.md").write_text(
        "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"
    )
    spec = TicketSpec(title="probe", kind=TicketKind.DOCS, origin=Origin.HUMAN)
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    ticket_id = created.danger_ok.id
    assert _store_mode(tmp_path) == "single"

    migrated = migrate_v1_to_v2(tmp_path)
    assert migrated.is_ok
    assert migrated.danger_ok == 1
    assert (tmp_path / "tickets" / ticket_id / "ticket.md").exists()
    assert _store_mode(tmp_path) == "v2"
    # T-3272 (not T-3282): migrate is non-destructive, the monofile stays.
    assert (tmp_path / "tickets.md").exists()


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


# frob:ticket T-3314
# frob:tests \
# tests/unit/test_scaffold_project.py::test_ci_template_frob_check_gate_fails_loudly_no\
# t_silently
def test_ci_template_frob_check_gate_fails_loudly_not_silently(
    tmp_path: Path,
) -> None:
    """T-3314: every scaffolded CI template's `frob check` step must fail
    the job (non-green CI status, `::error::`) when frob is missing/not
    working, never emit a quiet `::notice::` and continue with exit 0 --
    a skipped gate that only prints a notice is indistinguishable from a
    passing one in an otherwise-green build (T-3276's governing rule:
    optional-but-needed-for-a-gate means the gate reports UNMEASURED
    loudly, never CLEAN)."""
    for project_type in ("python-tool", "pyo3-library", "web-app"):
        result = render_project(project_type, "probe", tmp_path, force=True)
        assert result.is_ok, f"{project_type}: {result.err}"
        ci_paths = [p for p in result.danger_ok if p.name == "ci.yml"]
        assert ci_paths, f"{project_type}: no rendered ci.yml"
        text = ci_paths[0].read_text()
        assert "::notice::" not in text, (
            f"{project_type}: frob-missing case must not silently skip via ::notice::"
        )
        assert "::error::" in text, (
            f"{project_type}: frob-missing case must emit a loud ::error::"
        )
        assert "exit 1" in text, (
            f"{project_type}: frob-missing case must fail the job "
            "(non-green CI status), not continue past the gate"
        )
        assert "uv tool install frob" in text, (
            f"{project_type}: the error must name the install command"
        )


# frob:ticket T-3605
# frob:tests \
# tests/unit/test_scaffold_project.py::test_scaffolded_docs_make_targets_exist_in_makef\
# ile
def test_scaffolded_docs_make_targets_exist_in_makefile(tmp_path: Path) -> None:
    """T-3410 regression: `docs/index.md.j2`'s ``make <target>`` references
    must resolve against the same template set's rendered Makefile, and
    must not name any target the shared python Makefile.j2 dropped in
    T-3400 (test/lint/typecheck/check/coverage) -- catches a scaffold doc
    documenting a deleted make target before it ships to a new user."""
    result = render_project("python-library", "probe", tmp_path, force=True)
    assert result.is_ok, result.err
    rendered = result.danger_ok

    makefile_paths = [p for p in rendered if p.name == "Makefile"]
    assert makefile_paths, "python-library: no rendered Makefile"
    makefile_targets = {
        line.split(":", 1)[0].strip()
        for line in makefile_paths[0].read_text().splitlines()
        if line
        and not line.startswith((" ", "\t", "#", "."))
        and ":" in line
        and line.split(":", 1)[0].strip().isidentifier()
    }
    assert "install" in makefile_targets
    assert "test" not in makefile_targets, "T-3400 dropped `make test`"

    for doc_name in ("index.md", "README.md"):
        doc_paths = [p for p in rendered if p.name == doc_name]
        assert doc_paths, f"python-library: no rendered {doc_name}"
        text = doc_paths[0].read_text()
        referenced = {
            token.split()[0]
            for line in text.splitlines()
            if line.strip().startswith("make ")
            for token in [line.strip()[len("make ") :]]
        }
        stale = referenced - makefile_targets
        assert not stale, (
            f"{doc_name} references make target(s) {stale} absent from "
            "the rendered Makefile (T-3410 regression)"
        )
        assert "frob check" in text, (
            f"{doc_name} must steer to `frob check` per T-3400/T-3410"
        )


# frob:ticket T-3930
def test_hyphenated_name_produces_importable_source_all_types(tmp_path: Path) -> None:
    """T-3930: a hyphenated scaffold name (`my-test-tool`) must still yield
    parseable Python everywhere it is generated -- a bare
    `from my-test-tool.app import ...` is a SyntaxError that aborts pytest
    COLLECTION, not a failing test, so this parses every generated `.py`
    file with `ast.parse` (the same check the acceptance fixture demands)
    across all seven registered scaffold types."""
    for project_type in list_project_types():
        out = tmp_path / project_type
        out.mkdir()
        result = render_project(project_type, "my-test-tool", out, force=True)
        assert result.is_ok, f"{project_type}: {result.err}"

        py_files = [p for p in result.danger_ok if p.suffix == ".py"]
        for py_file in py_files:
            try:
                ast.parse(py_file.read_bytes())
            except SyntaxError as exc:
                raise AssertionError(
                    f"{project_type}: {py_file} is not valid Python: {exc}"
                ) from exc


# frob:ticket T-3930
def test_hyphenated_name_import_paths_are_underscored(tmp_path: Path) -> None:
    """T-3930: the package DIRECTORY under `src/` (or `python/` for the
    binding library types) must be the underscored import name, never the
    hyphenated distribution name verbatim -- a hyphen there is not a
    legal Python package/module identifier."""
    checks = {
        "python-library": "src/my_test_tool",
        "python-tool": "src/my_test_tool",
        "pybind11-library": "my_test_tool",
        "pyo3-library": "python/my_test_tool",
    }
    for project_type, rel in checks.items():
        out = tmp_path / project_type
        out.mkdir()
        result = render_project(project_type, "my-test-tool", out, force=True)
        assert result.is_ok, f"{project_type}: {result.err}"
        assert (out / "my-test-tool" / rel).is_dir(), (
            f"{project_type}: expected import package at {rel!r} under the "
            "hyphenated project dir"
        )
        assert not (out / "my-test-tool" / rel.replace("_", "-")).exists(), (
            f"{project_type}: a hyphenated package path must not exist"
        )


# frob:ticket T-3930
def test_single_word_name_unaffected_by_import_name_split(tmp_path: Path) -> None:
    """T-3930 MUST-STAY-QUIET: a single-word project name has no hyphen to
    normalize, so `dist_name`/`import_name` collapse to the same value and
    the generated `__main__.py` import line reads exactly as it always
    has -- no regression for the case that works today."""
    out = tmp_path / "python-tool"
    out.mkdir()
    result = render_project("python-tool", "mytool", out, force=True)
    assert result.is_ok, result.err
    main_py = out / "mytool" / "src" / "mytool" / "__main__.py"
    assert main_py.is_file()
    assert "from mytool.app import App, AppConfig" in main_py.read_text()


# frob:ticket T-3931
def test_every_scaffold_type_declares_default_milestone(tmp_path: Path) -> None:
    """T-3931: MILE003 fires on a freshly scaffolded project's first
    ticket because frob.toml has no [tickets].default_milestone -- "a
    fresh repo has no way to know it must set one until the first frob
    check". Every registered scaffold type's rendered frob.toml must
    declare one (0.1.0, matching the generated pyproject.toml version)."""
    import tomllib

    for project_type in list_project_types():
        out = tmp_path / project_type
        out.mkdir()
        result = render_project(project_type, "demo", out, force=True)
        assert result.is_ok, f"{project_type}: {result.err}"
        frob_toml = next((p for p in result.danger_ok if p.name == "frob.toml"), None)
        assert frob_toml is not None, f"{project_type}: no rendered frob.toml"
        with frob_toml.open("rb") as f:
            doc = tomllib.load(f)
        assert doc.get("tickets", {}).get("default_milestone") == "0.1.0", (
            f"{project_type}: frob.toml missing [tickets].default_milestone"
        )


# frob:ticket T-3931
def test_bump_version_script_constant_is_private(tmp_path: Path) -> None:
    """T-3931: COV001 fired on the generated scripts/bump_version.py's
    module-level PYPROJECT constant on a freshly scaffolded, untouched
    project -- a day-one finding the user did not cause. A standalone
    release script has no public API to document; the fix is a leading
    underscore (frob's own private-symbol convention, which COV001
    already skips), not a scaffold-shipped waiver."""
    out = tmp_path / "python-library"
    out.mkdir()
    result = render_project("python-library", "demo", out, force=True)
    assert result.is_ok, result.err
    script = next(p for p in result.danger_ok if p.name == "bump_version.py")
    tree = ast.parse(script.read_bytes())
    top_level_constant_names = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.isupper()
    }
    assert top_level_constant_names, "fixture drifted: no top-level constant found"
    for name in top_level_constant_names:
        assert name.startswith("_"), (
            f"bump_version.py's top-level constant {name!r} is not private "
            "-- COV001 will fire on it as a day-one scaffold finding"
        )
