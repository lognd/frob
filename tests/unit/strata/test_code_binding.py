"""Unit tests for strata tier-2 code binding
(docs/strata/surface.md#code-binding-tier-2-v0-implementation, T-0078).
"""

from __future__ import annotations

import ast
from pathlib import Path

from frob.strata import (
    FOREIGN,
    Flow,
    KernelModel,
    Node,
    StrataError,
    bind_code,
    check_import_conformance,
)
from frob.strata import _code_binding as _cb_mod
from frob.strata._code_binding import (
    _call_names,
    _call_target_name,
    _observed_call_names,
    _python_imports_with_lines,
    _relative_base_dir,
    _relative_imports,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestBindCode:
    # frob:tests src/frob/strata/_code_binding.py::bind_code kind="unit"
    def test_partitions_files_by_glob_and_defaults_unmatched_to_foreign(
        self, tmp_path: Path
    ):
        _write(tmp_path, "api/handler.py", "x = 1\n")
        _write(tmp_path, "db/store.py", "x = 1\n")
        _write(tmp_path, "scripts/one_off.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            )
        )
        result = bind_code(model, tmp_path)
        assert result.is_ok
        owner = result.danger_ok.owner
        assert owner["api/handler.py"] == "Api"
        assert owner["db/store.py"] == "Db"
        assert owner["scripts/one_off.py"] == FOREIGN

    # frob:tests src/frob/strata/_code_binding.py::bind_code kind="unit"
    def test_graph_exclude_dir_is_never_bound_even_when_glob_matches(
        self, tmp_path: Path
    ):
        # T-0274: a file under a [graph].exclude dir must never be
        # attributed to a node, even if its code= glob would otherwise
        # match it (graphite FROBLEMS.md 2026-07-18 #1: bundled frontend
        # build output misattributed to the `server` node).
        _write(tmp_path, "server/routes.py", "x = 1\n")
        _write(tmp_path, "server/static/bundle.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["server/static/**"]\n', encoding="utf-8"
        )
        model = KernelModel(
            nodes=(Node(id="Server", trust="trusted", attrs=("code=server/**",)),)
        )
        result = bind_code(model, tmp_path)
        assert result.is_ok
        owner = result.danger_ok.owner
        assert owner["server/routes.py"] == "Server"
        assert "server/static/bundle.py" not in owner

    # frob:tests src/frob/strata/_code_binding.py::bind_code kind="unit"
    # frob:ticket T-0416
    def test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs(
        self, tmp_path: Path
    ):
        """T-0416: `_sorted_py_files`'s pruned walk drops a nested git
        checkout's `.py` files unconditionally (`_is_nested_worktree`), even
        when NO `[graph] exclude` glob covers it -- an intentional
        tightening vs. the pre-T-0414 `rglob` walk, which had no such
        check and would have bound `vendor/dep/lib.py` to `Vendor`."""
        _write(tmp_path, "vendor/dep/lib.py", "x = 1\n")
        (tmp_path / "vendor" / "dep" / ".git").mkdir(parents=True, exist_ok=True)
        model = KernelModel(
            nodes=(Node(id="Vendor", trust="trusted", attrs=("code=vendor/**",)),)
        )
        result = bind_code(model, tmp_path)
        assert result.is_ok
        assert "vendor/dep/lib.py" not in result.danger_ok.owner

    # frob:tests src/frob/strata/_code_binding.py::bind_code kind="unit"
    def test_no_code_glob_declared_yields_empty_binding(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "x = 1\n")
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        result = bind_code(model, tmp_path)
        assert result.is_ok
        assert result.danger_ok.owner == {}

    # frob:tests src/frob/strata/_code_binding.py::bind_code kind="unit"
    def test_file_matched_by_two_globs_is_ambiguous(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="ApiToo", trust="trusted", attrs=("code=api/*.py",)),
            )
        )
        result = bind_code(model, tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.AmbiguousCodeBinding

    # frob:tests src/frob/strata/_code_binding.py::bind_code kind="unit"
    def test_skipped_dir_name_in_a_file_path_part_is_never_bound(
        self, tmp_path: Path, monkeypatch
    ):
        """`_bind_all_files`'s own per-file `is_skipped_dir` continue branch
        (T-1415 remainder): a defensive check that fires even when the
        upstream directory-level pruning in `walk_pruned` did not already
        filter the file out."""
        _write(tmp_path, "api/handler.py", "x = 1\n")
        # A file under a built-in skip-dir name that the walk itself did
        # not prune (e.g. surfaced by a different discovery path than
        # os.walk) must still be filtered by the per-file is_skipped_dir
        # check inside _bind_all_files.
        stray = tmp_path / "node_modules" / "vendor.py"
        monkeypatch.setattr(
            _cb_mod,
            "_sorted_py_files",
            lambda root, exclude_globs=(): [tmp_path / "api" / "handler.py", stray],
        )
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        result = bind_code(model, tmp_path)
        assert result.is_ok
        owner = result.danger_ok.owner
        assert "api/handler.py" in owner
        assert "node_modules/vendor.py" not in owner

    # frob:tests src/frob/strata/_code_binding.py::bind_code kind="unit"
    def test_file_level_exclude_glob_not_caught_by_directory_pruning(
        self, tmp_path: Path
    ):
        """`_bind_all_files`'s own per-file `is_excluded` continue branch
        (T-1415 remainder): a single-FILE exclude glob (not a directory
        prefix) cannot be pruned by `walk_pruned`'s directory-level check."""
        _write(tmp_path, "api/handler.py", "x = 1\n")
        _write(tmp_path, "api/secret.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["api/secret.py"]\n', encoding="utf-8"
        )
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        result = bind_code(model, tmp_path)
        assert result.is_ok
        owner = result.danger_ok.owner
        assert "api/handler.py" in owner
        assert "api/secret.py" not in owner


class TestCheckImportConformance:
    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_same_component_import_is_fine(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "import api.util\n")
        _write(tmp_path, "api/util.py", "x = 1\n")
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_cross_component_import_with_declared_flow_is_fine(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "import db.store\n")
        _write(tmp_path, "db/store.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            ),
            flows=(Flow(id="f1", src="Api", dst="Db"),),
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_cross_component_import_without_declared_flow_is_a_violation(
        self, tmp_path: Path
    ):
        _write(tmp_path, "api/handler.py", "x = 1\nimport db.store\n")
        _write(tmp_path, "db/store.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.file == "api/handler.py"
        assert v.line == 2
        assert v.spec == "db.store"
        assert v.src_component == "Api"
        assert v.dst_component == "Db"

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_declared_flow_in_reverse_direction_only_still_refuses_the_import(
        self, tmp_path: Path
    ):
        """`Flow` is directed (kernel.md): a Db -> Api flow authorizes only
        code Db imports from Api, never the reverse. An Api -> Db import
        must still be flagged (T-0078 review round -- the earlier draft
        wrongly let either declared direction satisfy both)."""
        _write(tmp_path, "api/handler.py", "import db.store\n")
        _write(tmp_path, "db/store.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            ),
            flows=(Flow(id="f1", src="Db", dst="Api"),),
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.src_component == "Api"
        assert v.dst_component == "Db"

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_declared_flow_in_exact_direction_satisfies_conformance(
        self, tmp_path: Path
    ):
        _write(tmp_path, "api/handler.py", "import db.store\n")
        _write(tmp_path, "db/store.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            ),
            flows=(Flow(id="f1", src="Api", dst="Db"),),
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_import_into_foreign_code_is_flagged(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "import scripts.one_off\n")
        _write(tmp_path, "scripts/one_off.py", "x = 1\n")
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].dst_component == FOREIGN

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_third_party_import_is_not_tracked(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "import os\nimport somepkg.util\n")
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_from_import_is_resolved_and_checked(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "from db import store\n")
        _write(tmp_path, "db/__init__.py", "")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].dst_component == "Db"

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_level1_relative_import_same_package_is_fine(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "from . import util\n")
        _write(tmp_path, "api/util.py", "x = 1\n")
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_level1_relative_import_crossing_component_is_flagged(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "x = 1\nfrom .sub import store\n")
        _write(tmp_path, "api/sub/__init__.py", "")
        _write(tmp_path, "api/sub/store.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/handler.py",)),
                Node(id="Sub", trust="trusted", attrs=("code=api/sub/**",)),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.line == 2
        assert v.src_component == "Api"
        assert v.dst_component == "Sub"

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_level2_relative_import_crossing_component_is_flagged(self, tmp_path: Path):
        # level 2 from pkg/handler.py walks up to the scan root, then into
        # sibling top-level package db/ -- python relative-import semantics
        # (docs/strata/surface.md#code-binding-tier-2-v0-implementation).
        _write(tmp_path, "pkg/handler.py", "from ..db import store\n")
        _write(tmp_path, "pkg/__init__.py", "")
        _write(tmp_path, "db/__init__.py", "")
        _write(tmp_path, "db/store.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Pkg", trust="trusted", attrs=("code=pkg/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.src_component == "Pkg"
        assert v.dst_component == "Db"

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_level2_relative_import_with_declared_flow_is_fine(self, tmp_path: Path):
        _write(tmp_path, "pkg/handler.py", "from ..db import store\n")
        _write(tmp_path, "pkg/__init__.py", "")
        _write(tmp_path, "db/__init__.py", "")
        _write(tmp_path, "db/store.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="Pkg", trust="trusted", attrs=("code=pkg/**",)),
                Node(id="Db", trust="trusted", attrs=("code=db/**",)),
            ),
            flows=(Flow(id="f1", src="Pkg", dst="Db"),),
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    # frob:ticket T-0172
    def test_managed_node_owned_files_are_never_checked_for_conformance(
        self, tmp_path: Path
    ):
        _write(tmp_path, "infra/config.py", "import api.handler\n")
        _write(tmp_path, "api/handler.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Infra",
                    trust="trusted",
                    attrs=("code=infra/**", "managed"),
                ),
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::_relative_imports kind="unit"
    def test_relative_base_dir_level_walks_exactly_to_root_returns_none(
        self, tmp_path: Path
    ):
        """`_relative_base_dir`'s own None-returning mid-loop branch
        (T-1415 remainder): file_dir = tmp_path/a/b, level=4 walks up 3
        times: b -> a -> root, hitting the base==root check mid-loop."""
        file_dir = tmp_path / "a" / "b"
        assert _relative_base_dir(file_dir, tmp_path, 4) is None

    # frob:tests src/frob/strata/_code_binding.py::_relative_imports kind="unit"
    def test_relative_base_dir_outside_root_returns_none_via_value_error(
        self, tmp_path: Path
    ):
        """A file_dir sharing no ancestry with root at all: `relative_to`
        raises ValueError, hit only once the loop itself is skipped
        (level=1, range(0) iterations) (T-1415 remainder)."""
        unrelated = tmp_path.parent / "elsewhere" / "pkg"
        assert _relative_base_dir(unrelated, tmp_path, 1) is None

    # frob:tests src/frob/strata/_code_binding.py::_relative_imports kind="unit"
    def test_relative_base_dir_within_root_resolves(self, tmp_path: Path):
        file_dir = tmp_path / "a" / "b"
        assert _relative_base_dir(file_dir, tmp_path, 1) == file_dir

    # frob:tests src/frob/strata/_code_binding.py::_relative_imports kind="unit"
    def test_relative_import_level_too_deep_for_file_position_yields_no_imports(
        self, tmp_path: Path
    ):
        """`_relative_imports`'s own `base_dir is None` branch (T-1415
        remainder)."""
        file_dir = tmp_path / "a" / "b"
        tree = ast.parse("from ....unreachable import x\n")
        import_from = next(n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom))
        assert _relative_imports(import_from, file_dir, tmp_path) == []

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_python_imports_missing_file_contributes_no_imports(self, tmp_path: Path):
        """`_python_imports_with_lines`'s own read-failure branch (T-1415
        remainder)."""
        missing = tmp_path / "ghost.py"
        assert _python_imports_with_lines(missing, tmp_path) == []

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_python_imports_syntax_error_contributes_no_imports_and_is_memoized(
        self, tmp_path: Path
    ):
        """`_python_imports_with_lines`'s own parse-failure branch, plus the
        content-keyed memo cached-hit branch on the second call (T-1415
        remainder)."""
        bad = tmp_path / "bad.py"
        bad.write_text("def f(\n    not valid python\n", encoding="utf-8")
        first = _python_imports_with_lines(bad, tmp_path)
        assert first == []
        second = _python_imports_with_lines(bad, tmp_path)
        assert second == []

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    def test_python_imports_repeated_call_with_same_content_hits_memo(
        self, tmp_path: Path
    ):
        good = tmp_path / "good.py"
        good.write_text("import os\n", encoding="utf-8")
        first = _python_imports_with_lines(good, tmp_path)
        second = _python_imports_with_lines(good, tmp_path)
        assert first == second == [("os", 1)]


# frob:ticket T-0595
class TestObservedCallNames:
    """docs/audits/strata.md G1 stronger half (T-0595): the code-side half
    of the ENDORSE-boundary predicate join `_threat.py::
    _predicate_is_code_bound` needs -- every distinct call-target name
    observed in one node's own `code=`-bound files."""

    # frob:tests src/frob/strata/_code_binding.py::_observed_call_names kind="unit"
    # frob:ticket T-0595
    def test_bare_call_name_is_observed(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "def f(x):\n    return sanitize(x)\n")
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        assert "sanitize" in _observed_call_names(binding, tmp_path, "Api")

    # frob:tests src/frob/strata/_code_binding.py::_observed_call_names kind="unit"
    # frob:ticket T-0595
    def test_attribute_call_name_is_observed(self, tmp_path: Path):
        _write(
            tmp_path,
            "api/handler.py",
            "import html\ndef f(x):\n    return html.sanitize(x)\n",
        )
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        assert "sanitize" in _observed_call_names(binding, tmp_path, "Api")

    # frob:tests src/frob/strata/_code_binding.py::_observed_call_names kind="unit"
    # frob:ticket T-0595
    def test_mention_with_no_call_is_not_observed(self, tmp_path: Path):
        _write(
            tmp_path,
            "api/handler.py",
            '"""mentions sanitize but never calls it"""\ndef f(x):\n    return x\n',
        )
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        assert "sanitize" not in _observed_call_names(binding, tmp_path, "Api")

    # frob:tests src/frob/strata/_code_binding.py::_observed_call_names kind="unit"
    # frob:ticket T-0595
    def test_call_in_a_different_nodes_files_is_not_observed(self, tmp_path: Path):
        _write(tmp_path, "other/attacker.py", "def f(x):\n    return sanitize(x)\n")
        _write(tmp_path, "api/handler.py", "def f(x):\n    return x\n")
        model = KernelModel(
            nodes=(
                Node(id="Api", trust="trusted", attrs=("code=api/**",)),
                Node(id="Other", trust="trusted", attrs=("code=other/**",)),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        assert "sanitize" not in _observed_call_names(binding, tmp_path, "Api")

    # frob:tests src/frob/strata/_code_binding.py::_observed_call_names kind="unit"
    # frob:ticket T-0595
    def test_unparseable_file_contributes_no_call_names(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "def f(x)\n    this is not valid python\n")
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        assert _observed_call_names(binding, tmp_path, "Api") == frozenset()

    # frob:tests src/frob/strata/_code_binding.py::_observed_call_names kind="unit"
    def test_subscript_call_target_is_not_resolved(self):
        """`_call_target_name`'s conservative None case (T-1415 remainder):
        a call whose target is neither a bare name nor an attribute access
        (e.g. a subscript result) is not resolved."""
        tree = ast.parse("funcs[0](x)\n")
        func = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)).func
        assert _call_target_name(func) is None

    # frob:tests src/frob/strata/_code_binding.py::_observed_call_names kind="unit"
    def test_call_names_skips_unresolvable_subscript_call(self):
        tree = ast.parse("funcs[0](x)\nsanitize(x)\n")
        assert _call_names(tree) == frozenset({"sanitize"})
