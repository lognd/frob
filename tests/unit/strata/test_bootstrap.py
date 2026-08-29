"""Unit tests for T-2910 (child of the T-2920 shrink-only ratchet epic)
`frob sys init` bootstrap derivation (`frob.strata._bootstrap`): a
one-time skeleton for a repo with NO existing `.strata` model -- nodes +
`code=` globs + real `flow` import edges, and DELIBERATELY never a
derived `may=` capability line."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.strata._bootstrap import (
    BootstrapModel,
    derive_bootstrap_model,
    existing_design_files,
    render_bootstrap_text,
    write_bootstrap_model,
)
from frob.strata._elaborate import elaborate
from frob.strata._errors import StrataError
from frob.strata._parse import parse_module


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _git_init_and_track(root: Path) -> None:
    """`git init` + `git add -A` -- `frob.gates._tracked_files.
    tracked_files` (this module's own file-listing substrate) reads
    `git ls-files`, which needs a real index, not a commit."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


class TestDeriveBootstrapModelRefusesAnExistingModel:
    """The whole bootstrap-not-sync contract: refuse, write nothing, once
    any `.strata` file already exists."""

    def test_refuses_when_a_strata_file_already_exists(self, tmp_path: Path):
        """A pre-existing `design/*.strata` file (any content) makes
        `derive_bootstrap_model` return `Err` without touching anything."""
        _write(tmp_path, "pkg/a.py", "x = 1\n")
        _write(tmp_path, "design/existing.strata", "module existing\n")
        _git_init_and_track(tmp_path)

        result = derive_bootstrap_model(tmp_path)

        assert result.is_err
        assert result.danger_err == StrataError.DuplicateId

    def test_existing_design_files_lists_the_real_files(self, tmp_path: Path):
        """`existing_design_files` is the exact refuse-check `sys_runner`
        uses to print which files caused the refusal."""
        assert existing_design_files(tmp_path) == ()
        _write(tmp_path, "design/one.strata", "module one\n")
        found = existing_design_files(tmp_path)
        assert len(found) == 1
        assert found[0].name == "one.strata"


class TestDeriveBootstrapModelNeverEmitsMay:
    """The T-2920 design constraint: no derived `may=` ceiling, ever --
    not even commented out."""

    def test_rendered_text_never_contains_a_may_line(self, tmp_path: Path):
        """A repo whose code performs an observable capability (a bare
        `eval(...)` call) still gets zero `may` lines in the rendered
        text -- this bootstrap has no code path that reads capability
        sites at all."""
        _write(
            tmp_path,
            "pkg/alpha/handler.py",
            "def handle(expr):\n    return eval(expr)\n",
        )
        _write(tmp_path, "pkg/beta/util.py", "from pkg.alpha import handler\n")
        _git_init_and_track(tmp_path)

        result = derive_bootstrap_model(tmp_path)

        assert result.is_ok
        model = result.danger_ok
        assert "may " not in model.text
        assert 'may "' not in model.text


class TestDeriveBootstrapModelComponentsAndFlows:
    """Node/`code=`/`flow` derivation from a real package layout + real
    import edges."""

    def test_single_top_package_splits_by_subdirectory(self, tmp_path: Path):
        """A `src/pkg/**` single-package layout gets one node per
        SUBdirectory of `pkg`, not one useless whole-package node."""
        _write(tmp_path, "src/pkg/alpha/handler.py", "from pkg.beta import util\n")
        _write(tmp_path, "src/pkg/beta/util.py", "x = 1\n")
        _git_init_and_track(tmp_path)

        result = derive_bootstrap_model(tmp_path)

        assert result.is_ok
        model = result.danger_ok
        ids = {c.id for c in model.components}
        assert "pkg_alpha" in ids
        assert "pkg_beta" in ids
        globs = {c.id: c.code_globs for c in model.components}
        assert globs["pkg_alpha"] == ("src/pkg/alpha/**",)
        assert globs["pkg_beta"] == ("src/pkg/beta/**",)

    def test_real_import_edge_becomes_a_flow_in_the_right_direction(
        self, tmp_path: Path
    ):
        """`alpha` imports `beta` -> exactly one `flow alpha -> beta`, and
        no `beta -> alpha` flow (the import is one-directional)."""
        _write(tmp_path, "src/pkg/alpha/handler.py", "from pkg.beta import util\n")
        _write(tmp_path, "src/pkg/beta/util.py", "x = 1\n")
        _git_init_and_track(tmp_path)

        model = derive_bootstrap_model(tmp_path).danger_ok

        flows = {(f.src, f.dst) for f in model.flows}
        assert ("pkg_alpha", "pkg_beta") in flows
        assert ("pkg_beta", "pkg_alpha") not in flows

    def test_test_files_are_excluded_from_component_derivation(self, tmp_path: Path):
        """`tests/**` and `test_*.py` contribute no node/flow -- only real
        source is modeled."""
        _write(tmp_path, "src/pkg/alpha/handler.py", "x = 1\n")
        _write(tmp_path, "tests/test_handler.py", "from pkg.alpha import handler\n")
        _git_init_and_track(tmp_path)

        model = derive_bootstrap_model(tmp_path).danger_ok

        ids = {c.id for c in model.components}
        assert ids == {"pkg_alpha"}
        assert model.flows == ()

    def test_loose_file_directly_in_single_package_root_is_not_mistaken_for_a_subdir(
        self, tmp_path: Path
    ):
        """Regression (found via a real foreign-repo measurement, T-2910):
        `src/pkg/__init__.py` and `src/pkg/__main__.py` are loose files
        directly in the single package's own root, not subdirectories --
        they must land in one `pkg_root` component with a `*.py` glob,
        never a bogus `pkg___init___py` node globbing a FILE as `/**`."""
        _write(tmp_path, "src/pkg/__init__.py", "x = 1\n")
        _write(tmp_path, "src/pkg/__main__.py", "from pkg.app import run\n")
        _write(tmp_path, "src/pkg/app/run.py", "def run():\n    pass\n")
        _git_init_and_track(tmp_path)

        model = derive_bootstrap_model(tmp_path).danger_ok

        ids = {c.id for c in model.components}
        assert ids == {"pkg_root", "pkg_app"}
        globs = {c.id: c.code_globs for c in model.components}
        assert globs["pkg_root"] == ("src/pkg/__init__.py", "src/pkg/__main__.py")
        assert globs["pkg_app"] == ("src/pkg/app/**",)

    def test_no_python_source_produces_an_empty_but_valid_model(self, tmp_path: Path):
        """A repo with no trackable Python source at all -- zero nodes,
        zero flows, never a crash."""
        _write(tmp_path, "README.md", "hello\n")
        _git_init_and_track(tmp_path)

        result = derive_bootstrap_model(tmp_path)

        assert result.is_ok
        model = result.danger_ok
        assert model.components == ()
        assert model.flows == ()


class TestRenderedTextParsesAndElaborates:
    """The must-produce control: a generated model must round-trip
    through frob's own strata loader, not merely look plausible."""

    def test_derived_model_parses_and_elaborates_cleanly(self, tmp_path: Path):
        _write(tmp_path, "src/pkg/alpha/handler.py", "from pkg.beta import util\n")
        _write(tmp_path, "src/pkg/beta/util.py", "x = 1\n")
        _git_init_and_track(tmp_path)

        model = derive_bootstrap_model(tmp_path).danger_ok

        parsed = parse_module(model.text)
        assert parsed.is_ok, parsed.err
        elaborated = elaborate(parsed.danger_ok)
        assert elaborated.is_ok, elaborated.err

    def test_empty_model_still_parses(self, tmp_path: Path):
        """Even the zero-component/zero-flow model (bare `module <name>`)
        is valid `.strata` text on its own."""
        model = BootstrapModel(
            module_name="empty_repo",
            components=(),
            flows=(),
            text=render_bootstrap_text("empty_repo", (), ()),
            scanned_file_count=0,
        )
        parsed = parse_module(model.text)
        assert parsed.is_ok, parsed.err


class TestWriteBootstrapModel:
    """The one write path, and only ever to a fresh path."""

    def test_writes_module_named_strata_file_under_design_dir(self, tmp_path: Path):
        _write(tmp_path, "src/pkg/alpha/handler.py", "x = 1\n")
        _git_init_and_track(tmp_path)
        model = derive_bootstrap_model(tmp_path).danger_ok

        out_path = write_bootstrap_model(tmp_path, model)

        assert out_path.is_file()
        assert out_path.parent.name == "design"
        assert out_path.read_text(encoding="utf-8") == model.text
