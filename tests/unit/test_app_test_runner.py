"""Direct-call coverage for `frob.app.test_runner`'s path-scoped selection
(T-2319: `frob test PATH` used to resolve PATH only as the repo root to
diff from, never as a SELECTION scope)."""

from __future__ import annotations

from frob.app.config import AppConfig
from frob.app.test_runner import _explicit_path_selection, _selection_report


class TestExplicitPathSelection:
    """`_explicit_path_selection`: repo-relative subtree scoping, pure."""

    def test_none_when_path_unset(self, tmp_path):
        """No `test_path` at all -- no explicit scoping, ordinary --all/
        touched-set behavior stays in effect."""
        cfg = AppConfig(test_path=None)
        assert _explicit_path_selection(cfg, tmp_path) is None

    def test_none_when_path_is_root_itself(self, tmp_path):
        """`test_path == root` (the default `.`) means "whole repo", not a
        subtree -- must not be treated as a scoping request."""
        cfg = AppConfig(test_path=tmp_path)
        assert _explicit_path_selection(cfg, tmp_path) is None

    def test_relative_subdir_scopes_selection(self, tmp_path):
        """A real subdirectory of root resolves to its repo-relative posix
        path -- the exact string `frob test tests/unit` should hand pytest."""
        sub = tmp_path / "tests" / "unit"
        sub.mkdir(parents=True)
        cfg = AppConfig(test_path=sub)
        assert _explicit_path_selection(cfg, tmp_path) == ("tests/unit",)

    def test_path_outside_root_is_ignored(self, tmp_path):
        """A path that does not resolve under root at all (e.g. a sibling
        directory) is not a scopable subtree -- fall through, not crash."""
        outside = tmp_path.parent / "elsewhere-not-under-root"
        cfg = AppConfig(test_path=outside)
        assert _explicit_path_selection(cfg, tmp_path) is None


class TestSelectionReportPathScoping:
    """`_selection_report`: explicit-path selection takes priority over
    both --all and the diff-driven touched set."""

    def test_path_selection_routes_to_python_only(self, tmp_path):
        """A subdirectory `path` selects that subtree for "python" only,
        with `fallback="path"` -- and never touches the diff/graph machinery
        (no snapshot/runners/base needed to produce a result)."""
        sub = tmp_path / "tests" / "unit"
        sub.mkdir(parents=True)
        cfg = AppConfig(test_path=sub)
        report = _selection_report(
            cfg, tmp_path, snapshot=None, runners=(), base="main"
        )
        assert report.fallback == "path"
        assert report.selected == {"python": ("tests/unit",)}

    def test_path_selection_honors_lang_filter(self, tmp_path):
        """`--lang` still filters an explicit-path selection, same as it
        filters the diff-driven/--all paths."""
        sub = tmp_path / "tests" / "unit"
        sub.mkdir(parents=True)
        cfg = AppConfig(test_path=sub, test_lang=["rust"])
        report = _selection_report(
            cfg, tmp_path, snapshot=None, runners=(), base="main"
        )
        assert report.selected == {}

    def test_root_path_falls_back_to_all(self, tmp_path):
        """`path == root` (the ordinary default) is NOT scoped -- --all's
        pre-T-2319 sentinel behavior is unchanged."""
        cfg = AppConfig(test_path=tmp_path, test_all=True)

        class _Spec:
            language = "python"

        report = _selection_report(
            cfg, tmp_path, snapshot=None, runners=(_Spec(),), base="main"
        )
        assert report.fallback == "all"
        assert report.selected == {"python": ("*",)}
