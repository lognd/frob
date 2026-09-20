"""T-4805: `_scope_closure_warnings` used to resolve "is this site in
scope" via `frob.tickets._models.scope_matches`, which ALSO treats
`DEFAULT_REGISTRY_FILES` (design/frob.strata among them) and
`LEDGER_PATH` as implicitly in scope -- correct for SCOPE001 gating, but
wrong for closure math: an EMPTY declared scope closed over every
`frob:doc` edge hanging off design/frob.strata (587 warnings measured
on `frob ticket new`/`scope --add`, none naming a file the ticket
touches).
Closure must be computed against the ticket's DECLARED scope only.

These tests stub the three gap-producing functions
(`scope_doc_code_gaps`, `scope_test_gaps`, `scope_private_helper_gaps`)
and `_graph_snapshot` so the positive/negative controls below assert the
FILTERING behaviour in `_scope_closure_warnings` itself, independent of
whatever the real repo's graph currently contains."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typani import Ok

import frob.app.ticket_runner._new  # noqa: F401 -- ensures sys.modules entry exists
from frob.graph.affects import ScopeClosureGap
from frob.graph.callgraph import PrivateHelperGap

# T-4805 note: `frob.app.ticket_runner`'s `__init__` re-exports several
# names FROM `_new` directly, and some tooling in this package binds a
# same-named attribute over its own submodule -- go through `sys.modules`
# rather than `from frob.app.ticket_runner import _new as new_mod`, which
# is an ATTRIBUTE lookup and can resolve to the wrong object (see the
# `frob.graph.affects` vs `frob.graph`'s `affects` function collision
# just below).
new_mod = sys.modules["frob.app.ticket_runner._new"]


def _fake_snapshot() -> Any:
    """A minimal stand-in for `GraphSnapshot` -- only `file_hashes` is
    read directly by `_scope_closure_warnings` (the rest flows through
    the stubbed gap functions below, never through real graph code)."""
    return SimpleNamespace(
        file_hashes={"a.py": "hash-a", "design/frob.strata": "hash-b"}
    )


def _patch_gap_sources(
    monkeypatch: pytest.MonkeyPatch,
    *,
    doc_gaps: tuple[ScopeClosureGap, ...] = (),
    test_gaps: tuple[ScopeClosureGap, ...] = (),
    helper_gaps: tuple[PrivateHelperGap, ...] = (),
) -> None:
    """Stub the graph-snapshot loader and the three T-0998 gap functions
    `_scope_closure_warnings` calls, so a test controls exactly which raw
    (unfiltered) gaps reach the declared-scope filter under test."""
    import sys

    import frob.app.ticket_runner as ticket_runner_pkg
    import frob.graph.affects  # noqa: F401 -- ensures sys.modules entry exists
    import frob.graph.callgraph  # noqa: F401 -- ensures sys.modules entry exists

    monkeypatch.setattr(
        ticket_runner_pkg, "_graph_snapshot", lambda root: Ok(_fake_snapshot())
    )
    # T-4805 note: `frob.graph`'s `__init__` re-exports a same-named
    # `affects` FUNCTION that shadows the `affects` submodule as an
    # attribute of the `frob.graph` package, so `import frob.graph.affects
    # as affects_mod` (attribute lookup) would bind the function instead
    # of the submodule -- go through `sys.modules` directly.
    affects_mod = sys.modules["frob.graph.affects"]
    callgraph_mod = sys.modules["frob.graph.callgraph"]

    monkeypatch.setattr(
        affects_mod, "scope_doc_code_gaps", lambda snap, scope: doc_gaps
    )
    monkeypatch.setattr(affects_mod, "scope_test_gaps", lambda snap, scope: test_gaps)
    monkeypatch.setattr(
        callgraph_mod,
        "scope_private_helper_gaps",
        lambda root, scope, files: helper_gaps,
    )


class TestEmptyScopeIsZeroWarnings:
    """Positive control (T-4805): fails today at HEAD c8f56ef10 -- an
    empty declared scope must close over nothing at all."""

    def test_empty_scope_emits_zero_warnings_even_with_hub_file_gaps(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Even if the graph WOULD report hundreds of design/frob.strata
        # gaps, an empty declared scope must never see them.
        hub_gap = ScopeClosureGap(
            direction="code_missing_doc",
            scoped_site="design/frob.strata::frob",
            target="docs/strata/roadmap.md#frob",
            missing_file="docs/strata/roadmap.md",
        )
        _patch_gap_sources(monkeypatch, doc_gaps=(hub_gap,) * 587)
        warnings = new_mod._scope_closure_warnings(tmp_path, ())
        assert warnings == ()

    def test_empty_scope_short_circuits_before_loading_the_graph(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An empty scope has nothing to close over -- the graph cache is
        never even touched, so a slow/broken cache cannot make `frob
        ticket new --declare-no-scope` slow or fail."""

        def _boom(root: Path) -> Any:
            raise AssertionError("graph snapshot must not be loaded for an empty scope")

        import frob.app.ticket_runner as ticket_runner_pkg

        monkeypatch.setattr(ticket_runner_pkg, "_graph_snapshot", _boom)
        assert new_mod._scope_closure_warnings(tmp_path, ()) == ()

    def test_empty_scope_logs_at_debug(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.DEBUG, logger="frob.app.ticket_runner"):
            new_mod._scope_closure_warnings(tmp_path, ())
        assert any("declares no scope" in r.message for r in caplog.records)


class TestDeclaredScopeOnlyFiltering:
    """Negative control (T-4805): a three-file scope must see warnings
    ONLY for gaps whose scoped site is reachable from those three files --
    never every doc/test/helper edge in the repo."""

    def test_three_file_scope_keeps_only_matching_gaps(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        scope = ("a.py", "b.py", "docs/c.md")
        in_scope_gap = ScopeClosureGap(
            direction="code_missing_doc",
            scoped_site="a.py::foo",
            target="docs/x.md#foo",
            missing_file="docs/x.md",
        )
        out_of_scope_gap = ScopeClosureGap(
            direction="code_missing_doc",
            scoped_site="design/frob.strata::frob",
            target="docs/strata/roadmap.md#frob",
            missing_file="docs/strata/roadmap.md",
        )
        test_gap_in_scope = ScopeClosureGap(
            direction="code_missing_test",
            scoped_site="b.py::bar",
            target="tests/test_bar.py::test_bar",
            missing_file="tests/test_bar.py",
        )
        helper_gap_out_of_scope = PrivateHelperGap(
            caller="design/frob.strata::frob",
            callee="_helper",
            definition_file="src/frob/other.py",
            only_used_by_scope=False,
        )
        _patch_gap_sources(
            monkeypatch,
            doc_gaps=(in_scope_gap, out_of_scope_gap),
            test_gaps=(test_gap_in_scope,),
            helper_gaps=(helper_gap_out_of_scope,),
        )
        warnings = new_mod._scope_closure_warnings(tmp_path, scope)
        assert any("a.py::foo" in w for w in warnings)
        assert any("b.py::bar" in w for w in warnings)
        assert not any("design/frob.strata" in w for w in warnings)

    def test_scope_actually_covering_the_hub_file_still_gets_its_warnings(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Regression guard: this must not become "disable the check" --
        a ticket that DOES declare design/frob.strata in scope still gets
        told about its unscoped doc target."""
        hub_gap = ScopeClosureGap(
            direction="code_missing_doc",
            scoped_site="design/frob.strata::frob",
            target="docs/strata/roadmap.md#frob",
            missing_file="docs/strata/roadmap.md",
        )
        _patch_gap_sources(monkeypatch, doc_gaps=(hub_gap,))
        warnings = new_mod._scope_closure_warnings(tmp_path, ("design/frob.strata",))
        assert any("design/frob.strata::frob" in w for w in warnings)
        assert any("docs/strata/roadmap.md" in w for w in warnings)
