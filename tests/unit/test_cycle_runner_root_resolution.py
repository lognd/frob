"""T-2588 regression: `frob cycle <path>` used to resolve import edges
RELATIVE TO WHATEVER PATH THE USER GAVE IT, instead of the project's real
import root. Pointing at `src/frob` (the obvious thing to type) made every
absolute `import frob.x` fail to resolve (candidate become
`src/frob/frob/x`, which does not exist), so every edge silently dropped
and the tool printed "no cycles found" on a tree containing a live cycle
`frob check --only cycle` correctly flagged as an error. `frob cycle src`
happened to work by accident (the given path already matched a source
root), which is exactly what made the bug invisible for so long.

This suite is the MANDATORY positive-control set from the ticket: three
path shapes must agree, an acyclic fixture must stay clean from all three,
a planted cycle must be caught from all three, and an unresolvable path
must ERROR rather than report clean.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app import cycle_runner
from frob.app.config import AppConfig


def _write(path: Path, text: str) -> None:
    """Write `text` to `path`, creating parent directories -- fixture helper."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_src_layout_project(root: Path, *, cyclic: bool) -> None:
    """A minimal `src/`-layout project at `root`: `pkg.a` <-> `pkg.b` if
    `cyclic`, otherwise a one-way `pkg.a -> pkg.b` edge."""
    _write(
        root / "pyproject.toml",
        '[project]\nname = "pkg"\n\n'
        '[tool.setuptools]\npackages = { find = { where = ["src"] } }\n',
    )
    _write(root / "src" / "pkg" / "__init__.py", "")
    _write(root / "src" / "pkg" / "a.py", "import pkg.b\n")
    b_body = "import pkg.a\n" if cyclic else "x = 1\n"
    _write(root / "src" / "pkg" / "b.py", b_body)


_PATH_SHAPES = ("src/pkg", "src", ".")


class TestCycleRunnerRootResolution:
    """`_build_graph`'s project-root resolution (T-2588): node identity and
    import-edge resolution must both anchor on the resolved project root,
    not on whichever subdirectory the caller happened to point at."""

    # frob:ticket T-2588
    # frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution.test_all_path_shapes_agree_on_a_real_cycle  # noqa: E501
    @pytest.mark.parametrize("shape", _PATH_SHAPES)
    def test_all_path_shapes_agree_on_a_real_cycle(
        self, tmp_path: Path, shape: str
    ) -> None:
        # frob:tests src/frob/app/cycle_runner.py::_build_graph kind="unit"
        _make_src_layout_project(tmp_path, cyclic=True)
        build_result = cycle_runner._build_graph(tmp_path / shape, None)
        assert build_result is not None, f"{shape}: root did not resolve"
        graph, _errors = build_result
        from frob.cycle.graph import find_cycles

        cycles = find_cycles(graph)
        cycle_sets = [frozenset(c) for c in cycles]
        assert frozenset({"src/pkg/a.py", "src/pkg/b.py"}) in cycle_sets, (
            f"{shape}: planted cycle not detected; got {cycles}"
        )

    # frob:ticket T-2588
    # frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution.test_all_path_shapes_stay_clean_on_an_acyclic_tree  # noqa: E501
    @pytest.mark.parametrize("shape", _PATH_SHAPES)
    def test_all_path_shapes_stay_clean_on_an_acyclic_tree(
        self, tmp_path: Path, shape: str
    ) -> None:
        # frob:tests src/frob/app/cycle_runner.py::_build_graph kind="unit"
        _make_src_layout_project(tmp_path, cyclic=False)
        build_result = cycle_runner._build_graph(tmp_path / shape, None)
        assert build_result is not None, f"{shape}: root did not resolve"
        graph, _errors = build_result
        from frob.cycle.graph import find_cycles

        assert find_cycles(graph) == [], (
            f"{shape}: acyclic fixture reported a cycle that does not exist "
            "-- a fix that 'always reports cycles' is not acceptable"
        )

    # frob:ticket T-2588
    # frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution.test_naive_relative_resolution_would_have_missed_this  # noqa: E501
    def test_naive_relative_resolution_would_have_missed_this(
        self, tmp_path: Path
    ) -> None:
        """The exact shape of the original defect: `src/pkg` as the given
        path used to resolve `import pkg.b` against `src/pkg/pkg/b.py`
        (nonexistent), dropping the edge silently. Confirms the edge now
        resolves correctly even from the innermost path shape."""
        # frob:tests src/frob/app/cycle_runner.py::_build_graph kind="unit"
        _make_src_layout_project(tmp_path, cyclic=True)
        build_result = cycle_runner._build_graph(tmp_path / "src" / "pkg", None)
        assert build_result is not None
        graph, _errors = build_result
        assert "src/pkg/b.py" in graph.neighbors("src/pkg/a.py")

    # frob:ticket T-2588
    # frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution.test_unresolvable_path_refuses_instead_of_reporting_clean  # noqa: E501
    def test_unresolvable_path_refuses_instead_of_reporting_clean(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/cycle_runner.py::_build_graph kind="unit"
        orphan = tmp_path / "no_pyproject_no_git"
        orphan.mkdir()
        (orphan / "mod.py").write_text("x = 1\n")
        assert cycle_runner._build_graph(orphan, None) is None, (
            "a path with no pyproject.toml and no enclosing git repo must "
            "be UNRESOLVED, never silently measured as an empty/clean graph"
        )

    # frob:ticket T-2588
    # frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution.test_run_exits_nonzero_on_a_found_cycle  # noqa: E501
    def test_run_exits_nonzero_on_a_found_cycle(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/cycle_runner.py::run kind="unit"
        _make_src_layout_project(tmp_path, cyclic=True)
        cfg = AppConfig(cycle_path=tmp_path / "src", cycle_lang=None)
        with pytest.raises(SystemExit) as exc_info:
            cycle_runner.run(cfg)
        assert exc_info.value.code != 0, "a run with real findings must exit nonzero"

    # frob:ticket T-2588
    # frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution.test_run_exits_zero_on_a_clean_tree  # noqa: E501
    def test_run_exits_zero_on_a_clean_tree(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/cycle_runner.py::run kind="unit"
        _make_src_layout_project(tmp_path, cyclic=False)
        cfg = AppConfig(cycle_path=tmp_path / "src", cycle_lang=None)
        cycle_runner.run(cfg)  # must return normally, not raise SystemExit

    # frob:ticket T-2588
    # frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution.test_run_exits_nonzero_error_on_unresolvable_path  # noqa: E501
    def test_run_exits_nonzero_error_on_unresolvable_path(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/cycle_runner.py::run kind="unit"
        orphan = tmp_path / "no_pyproject_no_git"
        orphan.mkdir()
        (orphan / "mod.py").write_text("x = 1\n")
        cfg = AppConfig(cycle_path=orphan, cycle_lang=None)
        with pytest.raises(SystemExit) as exc_info:
            cycle_runner.run(cfg)
        assert exc_info.value.code != 0, (
            "an unresolvable path must ERROR, never exit 0 the way a clean "
            "report does -- the two cases must be distinguishable by exit code"
        )
