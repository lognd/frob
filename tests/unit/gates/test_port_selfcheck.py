"""PORT001: a gate rule that hardcodes THIS project's own package identity
(a "src/<pkg>/" path prefix, or a bare package-name literal used to build
one) instead of resolving it from the project's declared config is itself
a finding (T-2388, child of T-2384)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._port_selfcheck import port_selfcheck_gate

_PYPROJECT_NAMED_FROB = '[project]\nname = "frob"\n'
_PYPROJECT_NAMED_LOGRADER = '[project]\nname = "lograder"\n'


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)


def _commit(tmp_path: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "c"], cwd=tmp_path, check=True)


def _write_gate_module(
    tmp_path: Path, pkg_name: str, filename: str, source: str
) -> None:
    gates_dir = tmp_path / "src" / pkg_name / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / pkg_name / "__init__.py").write_text("")
    (gates_dir / "__init__.py").write_text("")
    (gates_dir / filename).write_text(source)


class TestPort001:
    """`port_selfcheck_gate`: flags a hardcoded package-identity literal,
    stays silent on allowlisted/self-excluded files, and treats an
    unresolvable project name as UNRESOLVED rather than a clean pass."""

    def test_hardcoded_path_prefix_is_flagged(self, tmp_path: Path) -> None:
        """PORT001-PATH: a `.startswith("src/frob/")`-shaped literal is
        caught -- the exact `_env_var_docs.py`/`_root_asset_dirs.py` bug
        shape T-2384 measured. Proves this is not a check that always
        finds nothing."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NAMED_FROB)
        _write_gate_module(
            tmp_path,
            "frob",
            "_offender.py",
            "def _tracked(rel_path):\n    return rel_path.startswith('src/frob/')\n",
        )
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        hits = [v for v in violations if v.rule == "PORT001-PATH"]
        assert len(hits) == 1
        assert hits[0].file == "src/frob/gates/_offender.py"
        assert hits[0].severity.value == "warn"

    def test_hardcoded_identity_literal_in_tuple_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """PORT001-IDENT: the bare package-name literal used inside a
        tuple-of-path-segments (the `_self_match.py`-style shape) is
        caught even with no `.startswith` call present at all."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NAMED_FROB)
        _write_gate_module(
            tmp_path,
            "frob",
            "_offender.py",
            "_SUFFIXES = (\n    ('frob', 'gates', 'thing.py'),\n)\n",
        )
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        hits = [v for v in violations if v.rule == "PORT001-IDENT"]
        assert len(hits) == 1
        assert hits[0].file == "src/frob/gates/_offender.py"
        assert hits[0].severity.value == "warn"

    def test_allowlisted_self_match_file_is_silent(self, tmp_path: Path) -> None:
        """The identical PORT001-PATH shape, at
        `_pii_structural/_self_match.py`'s own allowlisted relpath, is not
        flagged -- an allowlist entry actually suppresses, matching
        LEXCHECK001's own contract."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NAMED_FROB)
        gates_dir = tmp_path / "src" / "frob" / "gates" / "_pii_structural"
        gates_dir.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (tmp_path / "src" / "frob" / "gates" / "__init__.py").write_text("")
        (gates_dir / "__init__.py").write_text("")
        (gates_dir / "_self_match.py").write_text(
            "_SELF = {\n    f'src/frob/gates/_pii_structural/{n}'\n"
            "    for n in ('a.py',)\n}\n"
        )
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        assert [
            v for v in violations if v.rule in ("PORT001-PATH", "PORT001-IDENT")
        ] == []

    def test_non_detector_package_code_never_scanned(self, tmp_path: Path) -> None:
        """A file outside `DETECTOR_PACKAGE_ROOTS`
        (`src/frob/{check,gates,strata,vet}/`, T-2405's widened scope,
        T-2466's shared, MEASURED declaration) carrying the identical
        offending literal is never scanned -- `app/_config_meta.py` is
        the disclosed example: T-2466 measured `app/` as containing zero
        gate-shaped `Violation(` constructors, so it stays out of
        PORT001's scanned set even after the T-2405 widening, not
        allowlisted for a scope it cannot enter."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NAMED_FROB)
        app_dir = tmp_path / "src" / "frob" / "app"
        app_dir.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (app_dir / "__init__.py").write_text("")
        (app_dir / "_config_meta.py").write_text(
            "def f(rel_path):\n    return rel_path.startswith('src/frob/')\n"
        )
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "__init__.py").write_text("")
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        assert [
            v for v in violations if v.rule in ("PORT001-PATH", "PORT001-IDENT")
        ] == []

    def test_strata_and_vet_are_scanned_since_t2405(self, tmp_path: Path) -> None:
        """T-2405: PORT001 widened past `src/frob/gates/**` to the full
        `DETECTOR_PACKAGE_ROOTS` set -- a hardcoded-identity literal in
        `src/frob/strata/` or `src/frob/vet/` is now caught, mirroring
        LEXCHECK001's own reuse of the same shared declaration (T-2466)."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NAMED_FROB)
        (tmp_path / "src" / "frob").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        strata_dir = tmp_path / "src" / "frob" / "strata"
        strata_dir.mkdir()
        (strata_dir / "__init__.py").write_text("")
        (strata_dir / "_offender.py").write_text(
            "def f(rel_path):\n    return rel_path.startswith('src/frob/')\n"
        )
        vet_dir = tmp_path / "src" / "frob" / "vet"
        vet_dir.mkdir()
        (vet_dir / "__init__.py").write_text("")
        (vet_dir / "_offender.py").write_text(
            "_SUFFIXES = (\n    ('frob', 'vet', 'thing.py'),\n)\n"
        )
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir()
        (gates_dir / "__init__.py").write_text("")
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        path_hits = {
            v.file for v in violations if v.rule == "PORT001-PATH"
        }
        ident_hits = {
            v.file for v in violations if v.rule == "PORT001-IDENT"
        }
        assert "src/frob/strata/_offender.py" in path_hits
        assert "src/frob/vet/_offender.py" in ident_hits

    def test_clean_gate_module_is_silent(self, tmp_path: Path) -> None:
        """A gate module with no hardcoded identity literal at all is
        clean -- proves this is not a check that always fires."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NAMED_FROB)
        _write_gate_module(
            tmp_path,
            "frob",
            "_clean.py",
            "def f(rel_path, roots):\n"
            "    return any(rel_path.startswith(r) for r in roots)\n",
        )
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        assert [
            v for v in violations if v.rule in ("PORT001-PATH", "PORT001-IDENT")
        ] == []

    def test_search_literal_is_resolved_not_hardcoded(self, tmp_path: Path) -> None:
        """The LITERAL PORT001 searches source text for comes from THIS
        repo's own `pyproject.toml` `[project].name`, never a hardcoded
        `'frob'` string -- proven by pointing a `pyproject.toml` naming a
        DIFFERENT package at the (still fixed, `src/frob/gates/`-scanned,
        disclosed limitation noted in `_tracked_gate_files`) gates
        directory: a `'src/renamed-pkg/'`-hardcoding literal there is
        still caught, and the message names the RESOLVED package, not a
        literal 'frob' baked into the detector."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "renamed-pkg"\n')
        _write_gate_module(
            tmp_path,
            "frob",
            "_offender.py",
            "def f(rel_path):\n    return rel_path.startswith('src/renamed-pkg/')\n",
        )
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        hits = [v for v in violations if v.rule == "PORT001-PATH"]
        assert len(hits) == 1
        assert "renamed-pkg" in hits[0].message

    def test_unresolved_project_name_is_not_a_clean_pass(self, tmp_path: Path) -> None:
        """T-2391 fail-loudly doctrine: a repo with no readable
        pyproject.toml `[project].name` produces an UNRESOLVED finding,
        never an empty (clean-looking) violation list -- "cannot
        determine an answer" is a different claim than "found nothing"."""
        _init_repo(tmp_path)
        _write_gate_module(
            tmp_path,
            "frob",
            "_offender.py",
            "def f(rel_path):\n    return rel_path.startswith('src/frob/')\n",
        )
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        hits = [v for v in violations if v.rule == "PORT001"]
        assert len(hits) == 1
        assert hits[0].severity.value == "unresolved"

    def test_unparseable_file_is_parse001_not_silent(self, tmp_path: Path) -> None:
        """A file this gate cannot `ast.parse` fires PARSE001 instead of
        silently dropping out of the scan -- matching LEXCHECK001/
        RENDER001's own convention."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NAMED_FROB)
        _write_gate_module(tmp_path, "frob", "_broken.py", "def f(:\n    pass\n")
        _commit(tmp_path)

        violations = port_selfcheck_gate(tmp_path)

        parse_hits = [v for v in violations if v.rule == "PARSE001"]
        assert len(parse_hits) == 1
        assert parse_hits[0].file == "src/frob/gates/_broken.py"
