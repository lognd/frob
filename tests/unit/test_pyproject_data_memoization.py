"""T-4646: `_pyproject_data` memoization -- regression tests for the
per-candidate x per-lease-holder `pyproject.toml` re-parse defect
(`declared_project_package_name` did a fresh `tomllib.load()` on EVERY
call with no caching at all; `doable()`'s `_leased_by_one_holder` called
`over_broad_literal_globs(root)` -> `declared_source_prefixes(root)` ->
`declared_project_package_name(root)` once per (queued/planned candidate
ticket, in-progress lease holder) pair, O(tickets x leases), the same cost
shape T-4649 fixed for `_store_mode`).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from frob.lang._nodes import (
    _pyproject_data,
    declared_project_package_name,
    declared_source_prefixes,
)
from frob.tickets._models import over_broad_literal_globs


def _seed_pyproject(root: Path, name: str) -> None:
    """Write a minimal `pyproject.toml` declaring `[project].name = name`
    at `root`, the fixture every test in this module shares."""
    (root / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n')


class TestPyprojectDataMemo:
    """Positive-control tests: each plants a mutation the cache MUST
    detect (a changed `pyproject.toml`), not just a "second call returns
    the same answer" timing assertion a broken cache would also pass."""

    def test_memoized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/lang/_nodes.py::_pyproject_data kind="unit"
        _seed_pyproject(tmp_path, "widget")
        assert declared_project_package_name(tmp_path) == "widget"

        calls = {"n": 0}
        real_open = Path.open

        def _counting_open(self: Path, mode: str = "r") -> object:
            if self.name == "pyproject.toml":
                calls["n"] += 1
            return real_open(self, mode)

        monkeypatch.setattr(Path, "open", _counting_open)
        for _ in range(5):
            assert declared_project_package_name(tmp_path) == "widget"
            assert declared_source_prefixes(tmp_path) == ("widget/",)
            assert over_broad_literal_globs(tmp_path) >= {"widget/**", "widget/"}
        # a cache hit does not re-open pyproject.toml at all: no mtime
        # change happened between calls, so all 15 calls above (5 loops x
        # 3 functions) above are served from `_pyproject_data_cache` alone.
        assert calls["n"] == 0

    def test_invalidates_on_mtime_change(self, tmp_path: Path) -> None:
        # frob:tests src/frob/lang/_nodes.py::_pyproject_data kind="unit"
        # positive control: rewrite pyproject.toml with a DIFFERENT
        # package name after the first (cached) call and confirm the
        # answer flips -- proves the mtime-keyed cache actually
        # invalidates on a real config change, not just that it returns a
        # stale answer fast.
        _seed_pyproject(tmp_path, "widget")
        assert declared_project_package_name(tmp_path) == "widget"

        # ensure a distinct mtime tick on filesystems with coarse
        # resolution (some CI/container filesystems round to 1s).
        time.sleep(1.01)
        _seed_pyproject(tmp_path, "gadget")
        assert declared_project_package_name(tmp_path) == "gadget"
        assert declared_source_prefixes(tmp_path) == ("gadget/",)

    def test_missing_pyproject_returns_none_and_stays_cached(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/lang/_nodes.py::_pyproject_data kind="unit"
        assert declared_project_package_name(tmp_path) is None

        # a missing pyproject.toml is CHEAP to re-detect (one `stat()`
        # that raises `OSError`, no `tomllib.load()`), so the cache-miss
        # invalidation signal is still probed every call by design (the
        # same shape `_store_mode_cache_signal` uses) -- only the (absent)
        # `open()`/parse is what memoization must avoid.
        calls = {"n": 0}
        real_open = Path.open

        def _counting_open(self: Path, mode: str = "r") -> object:
            if self.name == "pyproject.toml":
                calls["n"] += 1
            return real_open(self, mode)

        monkeypatch.setattr(Path, "open", _counting_open)
        for _ in range(5):
            assert declared_project_package_name(tmp_path) is None
        assert calls["n"] == 0

    def test_scales_across_many_candidates_and_leases(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/lang/_nodes.py::_pyproject_data kind="unit"
        # T-4646's actual defect shape: doable()'s per-candidate x
        # per-lease-holder loop calls over_broad_literal_globs(root) once
        # per pair -- 200 candidates x 50 leases = 10000 calls. Assert the
        # underlying pyproject.toml open() count stays O(1), not O(pairs).
        _seed_pyproject(tmp_path, "widget")
        _pyproject_data.__globals__["_pyproject_data_cache"].clear()

        opens = {"n": 0}
        real_open = Path.open

        def _counting_open(self: Path, mode: str = "r") -> object:
            if self.name == "pyproject.toml":
                opens["n"] += 1
            return real_open(self, mode)

        monkeypatch.setattr(Path, "open", _counting_open)
        for _ in range(200):
            for _lease in range(50):
                over_broad_literal_globs(tmp_path)
        assert opens["n"] == 1

    # frob:ticket T-5117
    def test_declared_source_prefixes_resolve_calls_stay_o1_across_pairs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/lang/_nodes.py::declared_source_prefixes kind="unit"
        """T-5117's own repro: T-4646 only memoized the two calls
        `declared_source_prefixes` makes INTERNALLY (`declared_project_
        package_name`'s underlying `_pyproject_data` read, and
        `_declared_python_source_roots`'s own `lru_cache`) -- the
        function's OWN body (a `Path.resolve()` pair per declared source
        root) still ran fresh on every call before this ticket's fix, the
        literal `over_broad_literal_globs(root) -> declared_source_
        prefixes(root) -> Path.resolve()` bottleneck this ticket's audit
        traced. Assert `Path.resolve()` call count stays O(1) across
        `doable()`'s real (candidate, lease-holder) pair shape (200 x 50
        = 10000 calls), not O(pairs) -- fails at the pre-fix parent
        commit (resolve count scales with the loop), passes after
        (pinned at a small constant)."""
        _seed_pyproject(tmp_path, "widget")
        _pyproject_data.__globals__["_pyproject_data_cache"].clear()
        declared_source_prefixes.__globals__["_declared_source_prefixes_cache"].clear()
        over_broad_literal_globs.__globals__["_over_broad_literal_globs_cache"].clear()

        resolves = {"n": 0}
        real_resolve = Path.resolve

        def _counting_resolve(self: Path, strict: bool = False) -> Path:
            resolves["n"] += 1
            return real_resolve(self, strict=strict)

        monkeypatch.setattr(Path, "resolve", _counting_resolve)
        for _ in range(200):
            for _lease in range(50):
                over_broad_literal_globs(tmp_path)
        assert resolves["n"] <= 4, (
            f"expected a constant (small) number of Path.resolve() calls "
            f"across 10000 (candidate, lease-holder) pairs, got "
            f"{resolves['n']} -- the per-pair over_broad_literal_globs/"
            "declared_source_prefixes cost T-5117 fixed has regressed"
        )
