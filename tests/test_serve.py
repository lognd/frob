"""Tests for frob.serve -- the MCP tool layer (docs/modules/serve.md).

Exercises `frob.serve._tools` (the plain-function layer) directly; the
`mcp` SDK transport (`frob.serve.server`) is a thin wrapper that raises on
`Result.is_err` and is not exercised here (no in-process MCP client in this
suite).
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from frob.app.config import AppConfig
from frob.gates import stamp_baseline
from frob.graph import build_graph
from frob.graph._models import LockEntry, LockFile
from frob.graph.lock import write_lock
from frob.serve import (
    ServeError,
    _warm,
    frob_affects,
    frob_check_delta,
    frob_check_scope,
    frob_doable_tickets,
    frob_doc_for,
    frob_graph_query,
    frob_perf_hot,
    frob_run_touched_tests,
    frob_stale_docs,
)
from frob.tickets import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import write_ticket


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


def _ticket(ticket_id: str = "T-0001", scope: tuple[str, ...] = ()) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="Sample ticket",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
    )


_SAMPLE_PY = (
    '"""Module docstring."""\n\n\n'
    "def helper(x):\n"
    "    # frob:doc docs/x.md#helper\n"
    "    return x\n"
)


class TestServeGetattr:
    """T-0160 batch 8: `frob.serve.__getattr__`'s lazy re-export (T-0362) --
    `frob.serve` must import cheaply and still resolve `McpUnavailable`/
    `build_server`/`run_stdio` on demand, and raise normal `AttributeError`
    for anything else."""

    def test_getattr_resolves_lazy_server_names(self) -> None:
        # frob:tests src/frob/serve/__init__.py::__getattr__ kind="unit"
        import frob.serve as serve_pkg
        from frob.serve import server as server_mod

        assert serve_pkg.McpUnavailable is server_mod.McpUnavailable
        assert serve_pkg.build_server is server_mod.build_server
        assert serve_pkg.run_stdio is server_mod.run_stdio

    def test_getattr_unknown_name_raises_attribute_error(self) -> None:
        # frob:tests src/frob/serve/__init__.py::__getattr__ kind="unit"
        import frob.serve as serve_pkg

        with pytest.raises(AttributeError, match="not_a_real_export"):
            serve_pkg.not_a_real_export


class TestBuildServer:
    # invariant spec: [INV-021](invariants/INV-021.md)
    def test_registers_all_five_tools(self, tmp_path: Path) -> None:
        # Name kept as-is despite now covering 10 tools (T-0177 added 2 more,
        # T-0325 added frob_affects, T-0733 added frob_daemon_status,
        # T-0917 added frob_perf_hot): T-0010/T-0046/T-0520 already cite
        # this node id as `frob:tests` evidence, and COV003 resolves
        # evidence by exact node id -- a rename here would silently break
        # their recorded evidence.
        # frob:tests src/frob/serve/server.py::build_server kind="unit"
        from frob.serve.server import build_server

        server = build_server(tmp_path)
        names = {t.name for t in server._tool_manager.list_tools()}
        assert names == {
            "frob_doable_tickets",
            "frob_stale_docs",
            "frob_check_scope",
            "frob_daemon_status",
            "frob_graph_query",
            "frob_doc_for",
            "frob_affects",
            "frob_check_delta",
            "frob_run_touched_tests",
            "frob_perf_hot",
        }

    def test_require_mcp_raises_when_unavailable(self, monkeypatch) -> None:
        # frob:tests src/frob/serve/server.py::run_stdio kind="unit"
        import builtins

        from frob.serve.server import McpUnavailable, _require_mcp

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "mcp.server.fastmcp" or name.startswith("mcp"):
                raise ImportError("simulated missing mcp")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        try:
            _require_mcp()
            raised = False
        except McpUnavailable:
            raised = True
        assert raised


class TestServeRunner:
    def test_run_delegates_to_run_stdio_with_resolved_root(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/serve_runner.py::run kind="unit"
        import frob.serve.server as server_module
        from frob.app.serve_runner import run

        calls = []
        monkeypatch.setattr(server_module, "run_stdio", calls.append)

        cfg = AppConfig(serve_path=tmp_path)
        run(cfg)
        assert calls == [tmp_path.resolve()]


class TestDoableTickets:
    def test_lists_queued_ticket(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_doable_tickets kind="unit"
        ticket = _ticket("T-0001")
        write_ticket(tmp_path, ticket)
        result = frob_doable_tickets(tmp_path)
        assert result.is_ok
        tickets = result.danger_ok
        # T-1128: the RPC now returns each ticket's FULL model_dump(mode=
        # "json"), field-for-field identical to `frob ticket doable
        # --json`'s own per-row shape, not an id/title/kind-only subset.
        assert tickets == [ticket.model_dump(mode="json")]

    def test_empty_queue_is_empty_list(self, tmp_path: Path) -> None:
        result = frob_doable_tickets(tmp_path)
        assert result.is_ok
        assert result.danger_ok == []


class TestStaleDocs:
    def test_clean_snapshot_has_no_drift(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_stale_docs kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        result = frob_stale_docs(tmp_path)
        assert result.is_ok
        assert result.danger_ok == {"stale": [], "dangling": []}

    def test_dangling_edge_reported(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _write(
            tmp_path,
            "docs/x.md",
            "# Doc\n\n<!-- frob:describes src/pkg/a.py::gone -->\n",
        )
        _git_init(tmp_path)
        result = frob_stale_docs(tmp_path)
        assert result.is_ok
        dangling = result.danger_ok["dangling"]
        assert any(d["target"].endswith("::gone") for d in dangling)

    def test_stale_ack_reported(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        cache = tmp_path / ".frob" / "cache.db"
        snapshot = build_graph(tmp_path, cache).danger_ok
        record = next(iter(snapshot.symbols.values()))
        lock = LockFile(
            entries=(LockEntry(ref=record.symref, facet="sig", digest="deadbeef" * 8),)
        )
        write_lock(lock, tmp_path / "frob.lock")

        result = frob_stale_docs(tmp_path)
        assert result.is_ok
        stale = result.danger_ok["stale"]
        assert any(s["ref"] == record.symref for s in stale)


class TestCheckScope:
    def test_in_scope_diff_passes(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_check_scope kind="unit"
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        write_ticket(
            tmp_path, _ticket("T-0001", scope=("src/pkg/**", ".frob/**", "tickets.md"))
        )
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x + 1\n")

        result = frob_check_scope(tmp_path, "T-0001")
        assert result.is_ok
        assert result.danger_ok["in_scope"] is True
        assert result.danger_ok["violations"] == []

    def test_out_of_scope_diff_flagged(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        write_ticket(tmp_path, _ticket("T-0001", scope=("src/other/**",)))
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x + 1\n")

        result = frob_check_scope(tmp_path, "T-0001")
        assert result.is_ok
        assert result.danger_ok["in_scope"] is False
        assert result.danger_ok["violations"][0]["rule"] == "SCOPE001"


class TestPerfHot:
    def test_empty_store_is_empty_list(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_perf_hot kind="unit"
        result = frob_perf_hot(tmp_path)
        assert result.is_ok
        assert result.danger_ok == []

    def test_ranks_by_default_p50xcount(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_perf_hot kind="unit"
        from frob.perf._sketch_store import SketchStoreConfig, _close_all, put_sketch
        from frob.stats._sketch import DEFAULT_ALPHA, add_value, new_sketch

        config = SketchStoreConfig()
        slow_rare = add_value(new_sketch(alpha=DEFAULT_ALPHA), 100.0)
        fast_frequent = new_sketch(alpha=DEFAULT_ALPHA)
        for _ in range(100):
            fast_frequent = add_value(fast_frequent, 5.0)
        put_sketch(tmp_path, "k_slow", "loop", slow_rare, config, label="pkg.mod.slow")
        put_sketch(
            tmp_path, "k_fast", "loop", fast_frequent, config, label="pkg.mod.fast"
        )
        try:
            result = frob_perf_hot(tmp_path)
            assert result.is_ok
            rows = result.danger_ok
            assert [r["section_key"] for r in rows] == ["k_fast", "k_slow"]
        finally:
            _close_all()

    def test_by_p90_ranks_by_p90_instead(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_perf_hot kind="unit"
        from frob.perf._sketch_store import SketchStoreConfig, _close_all, put_sketch
        from frob.stats._sketch import DEFAULT_ALPHA, add_value, new_sketch

        config = SketchStoreConfig()
        slow_rare = add_value(new_sketch(alpha=DEFAULT_ALPHA), 100.0)
        fast_frequent = new_sketch(alpha=DEFAULT_ALPHA)
        for _ in range(10):
            fast_frequent = add_value(fast_frequent, 5.0)
        put_sketch(tmp_path, "k_slow", "loop", slow_rare, config, label="pkg.mod.slow")
        put_sketch(
            tmp_path, "k_fast", "loop", fast_frequent, config, label="pkg.mod.fast"
        )
        try:
            result = frob_perf_hot(tmp_path, by="p90")
            assert result.is_ok
            rows = result.danger_ok
            assert rows[0]["section_key"] == "k_slow"
        finally:
            _close_all()

    def test_top_truncates_results(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_perf_hot kind="unit"
        from frob.perf._sketch_store import SketchStoreConfig, _close_all, put_sketch
        from frob.stats._sketch import DEFAULT_ALPHA, add_value, new_sketch

        config = SketchStoreConfig()
        put_sketch(
            tmp_path,
            "k1",
            "loop",
            add_value(new_sketch(alpha=DEFAULT_ALPHA), 1.0),
            config,
            label="a",
        )
        put_sketch(
            tmp_path,
            "k2",
            "loop",
            add_value(new_sketch(alpha=DEFAULT_ALPHA), 2.0),
            config,
            label="b",
        )
        try:
            result = frob_perf_hot(tmp_path, top=1)
            assert result.is_ok
            assert len(result.danger_ok) == 1
        finally:
            _close_all()


class TestGraphQuery:
    def test_resolves_symbol_and_edges(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_graph_query kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)

        result = frob_graph_query(tmp_path, "helper")
        assert result.is_ok
        payload = result.danger_ok
        assert payload["ref"].endswith("::helper")
        assert any(e["kind"] == "doc" for e in payload["edges_from"])

    def test_unknown_symbol_is_err(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)

        result = frob_graph_query(tmp_path, "does_not_exist")
        assert result.is_err
        assert result.danger_err == ServeError.UnknownSymbol


class TestDocFor:
    def test_reports_doc_edge(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_doc_for kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)

        result = frob_doc_for(tmp_path, "helper")
        assert result.is_ok
        payload = result.danger_ok
        assert payload["doc"] == [{"target": "docs/x.md#helper"}]
        assert payload["described_by"] == []

    def test_unknown_symbol_is_err(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)

        result = frob_doc_for(tmp_path, "does_not_exist")
        assert result.is_err
        assert result.danger_err == ServeError.UnknownSymbol


_SAMPLE_CALLER_PY = (
    '"""Caller module."""\n\n\n'
    "def caller(x):\n"
    "    # frob:uses-contract src/pkg/a.py::helper\n"
    "    return x\n"
)


class TestAffects:
    """`frob_affects` -- T-0325's north-star doc-drift digest-graph query."""

    def test_direct_symbol_no_dependents(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_affects kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)

        result = frob_affects(tmp_path, "helper")
        assert result.is_ok
        payload = result.danger_ok
        assert payload["ref"].endswith("::helper")
        assert payload["dependents"] == []
        assert payload["docs"] == ["docs/x.md#helper"]
        assert payload["tests"] == []
        assert payload["truncated"] is False

    def test_transitive_dependent_docs_included(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_affects kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _write(tmp_path, "src/pkg/b.py", _SAMPLE_CALLER_PY)
        _git_init(tmp_path)

        result = frob_affects(tmp_path, "helper")
        assert result.is_ok
        payload = result.danger_ok
        assert payload["dependents"] == ["src/pkg/b.py::caller"]
        assert "docs/x.md#helper" in payload["docs"]

    def test_unknown_symbol_is_err(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_affects kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)

        result = frob_affects(tmp_path, "does_not_exist")
        assert result.is_err
        assert result.danger_err == ServeError.UnknownSymbol


class TestRepoDirtyKey:
    def test_non_git_root_is_always_dirty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_warm.py::_repo_dirty_key kind="unit"
        assert _warm._repo_dirty_key(tmp_path) == _warm._ALWAYS_DIRTY

    def test_clean_repo_key_is_stable_across_calls(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_warm.py::_repo_dirty_key kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        first = _warm._repo_dirty_key(tmp_path)
        second = _warm._repo_dirty_key(tmp_path)
        assert first == second
        assert first != _warm._ALWAYS_DIRTY

    def test_tracked_edit_changes_the_key(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_warm.py::_repo_dirty_key kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        before = _warm._repo_dirty_key(tmp_path)
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY + "\n# edited\n")
        after = _warm._repo_dirty_key(tmp_path)
        assert before != after

    def test_untracked_file_content_edit_changes_the_key(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_warm.py::_repo_dirty_key kind="unit"
        # Regression guard: `git status --porcelain` alone reports an
        # untracked path as just "?? path" regardless of its content, so a
        # naive key over the porcelain listing would miss a content-only
        # edit to a file that was never staged -- `_stat_tag` closes that.
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _write(tmp_path, "src/pkg/new_untracked.py", "x = 1\n")
        before = _warm._repo_dirty_key(tmp_path)
        _write(tmp_path, "src/pkg/new_untracked.py", "x = 2\n")
        after = _warm._repo_dirty_key(tmp_path)
        assert before != after


class TestWarmState:
    def test_second_call_is_cache_hit(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests src/frob/serve/_warm.py::_warm_state kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        calls = []
        real_build_cold = _warm._build_cold

        def spy(root, dirty_key):
            calls.append(dirty_key)
            return real_build_cold(root, dirty_key)

        monkeypatch.setattr(_warm, "_build_cold", spy)

        first = _warm._warm_state(tmp_path)
        second = _warm._warm_state(tmp_path)
        assert first.is_ok
        assert second.is_ok
        assert second.danger_ok is first.danger_ok
        assert len(calls) == 1

    def test_file_change_forces_rebuild(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests src/frob/serve/_warm.py::_warm_state kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        calls = []
        real_build_cold = _warm._build_cold

        def spy(root, dirty_key):
            calls.append(dirty_key)
            return real_build_cold(root, dirty_key)

        monkeypatch.setattr(_warm, "_build_cold", spy)

        first = _warm._warm_state(tmp_path)
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY + "\n# edited\n")
        second = _warm._warm_state(tmp_path)
        assert first.is_ok
        assert second.is_ok
        assert second.danger_ok is not first.danger_ok
        assert len(calls) == 2

    def test_invalidate_is_a_noop_when_nothing_cached(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_warm.py::_invalidate kind="unit"
        _warm._invalidate(tmp_path)  # must not raise


@settings(deadline=None, max_examples=15)
@given(edits=st.lists(st.booleans(), min_size=0, max_size=5))
def test_warm_state_rebuilds_iff_tree_changed(
    edits: list[bool], tmp_path_factory
) -> None:
    # frob:tests tests/test_serve.py::test_warm_state_rebuilds_iff_tree_changed kind="unit"  # noqa: E501
    # Property (T-0177's invalidation-logic guarantee, vacuous-pass
    # doctrine): for ANY sequence of "edit the tracked file, then call
    # warm_state" vs "call warm_state with nothing touched", a rebuild
    # happens EXACTLY on the initial call and every call following a real
    # edit -- an obligation (here, the cached graph snapshot) not
    # rebuilt must correspond 1:1 to a call where nothing changed on
    # disk, never the reverse.
    root = tmp_path_factory.mktemp("warm-prop")
    _write(root, "src/pkg/a.py", _SAMPLE_PY)
    _git_init(root)
    _warm._invalidate(root)

    build_count = 0
    real_build_cold = _warm._build_cold

    def counting_build(r: Path, dirty_key: str):
        nonlocal build_count
        build_count += 1
        return real_build_cold(r, dirty_key)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(_warm, "_build_cold", counting_build)

        expected_builds = 1
        result = _warm._warm_state(root)
        assert result.is_ok
        assert build_count == expected_builds

        for edited in edits:
            if edited:
                _write(root, "src/pkg/a.py", _SAMPLE_PY + f"\n# {build_count}\n")
                expected_builds += 1
            # frob:waive PERF008 reason="this test's entire point is calling \
            # warm_state(root) repeatedly across a sequence of edits to verify its \
            # incremental cache/invalidation behavior (asserting build_count only \
            # increments on an actual edit) -- hoisting the call out of the loop \
            # would defeat the test"  # noqa: E501
            result = _warm._warm_state(root)
            assert result.is_ok
            assert build_count == expected_builds
    _warm._invalidate(root)


class TestCheckDelta:
    def test_delta_against_fresh_baseline_is_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_check_delta kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        first = frob_check_delta(tmp_path)
        assert first.is_ok
        stamp_baseline(tmp_path, ())
        second = frob_check_delta(tmp_path)
        assert second.is_ok
        payload = second.danger_ok
        assert payload["baseline_stale"] is False

    def test_missing_baseline_is_full_set(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_check_delta kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        result = frob_check_delta(tmp_path)
        assert result.is_ok
        payload = result.danger_ok
        assert payload["baseline_stale"] is True
        assert payload["delta_count"] == payload["violation_count"]

    def test_delta_reports_new_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_check_delta kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        baseline_run = frob_check_delta(tmp_path)
        assert baseline_run.is_ok
        stamp_baseline(tmp_path, ())

        _write(
            tmp_path, "docs/dangling.md", "<!-- frob:describes src/pkg/a.py::gone -->\n"
        )
        _warm._invalidate(tmp_path)
        after = frob_check_delta(tmp_path)
        assert after.is_ok
        payload = after.danger_ok
        assert payload["baseline_stale"] is False
        assert payload["delta_count"] >= 1

    def test_verify_true_matches_when_no_drift(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_check_delta kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        result = frob_check_delta(tmp_path, verify=True)
        assert result.is_ok
        payload = result.danger_ok
        assert payload["verified"] is True
        assert payload["verify_mismatch_count"] == 0

    def test_check_result_matches_only_gates_delta_cli_shape(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_check_delta kind="unit"
        # T-1147: `check_result` reuses `frob.check._python.
        # _gates_success_result` directly, so its per-family `ToolResult`
        # list is field-for-field what `frob check --only gates --delta
        # --json` renders -- this unit test asserts the SHAPE (keys,
        # violation-to-diagnostic mapping) without spawning the real
        # subprocess-vs-subprocess daemon comparison
        # `tests/test_app_daemon_proxy.py::TestDifferentialParity::
        # test_check_delta_gates_only_json_daemon_matches_in_process`
        # covers end to end.
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        result = frob_check_delta(tmp_path)
        assert result.is_ok
        payload = result.danger_ok
        check_result = payload["check_result"]
        assert check_result["path"] == str(tmp_path)
        tools = [r["tool"] for r in check_result["results"]]
        assert "gate-summary" in tools
        assert all(t.startswith("gate:") or t == "gate-summary" for t in tools)


class TestRunTouchedTests:
    def test_no_diff_selects_nothing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_run_touched_tests kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _write(tmp_path, ".gitignore", ".frob/\n")
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)
        # Materialize `.frob/` (build_graph/collect_python_tests's cache dir)
        # BEFORE the diff-under-test so it never itself shows up as a hunk.
        _warm._warm_state(tmp_path)

        result = frob_run_touched_tests(tmp_path)
        assert result.is_ok
        payload = result.danger_ok
        # T-1128: the RPC now returns `test_run.model_dump(mode="json")`
        # verbatim (a `TestRunReport`: `selection`/`outcomes`/`ok`), field-
        # for-field identical to `frob test --json`'s own output, not the
        # earlier flat `base`/`touched`/`ok`/`outcomes` subset.
        assert payload["selection"]["touched"] == []
        assert payload["ok"] is True
        assert payload["outcomes"] == []

    def test_bad_base_is_git_failed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/_tools.py::frob_run_touched_tests kind="unit"
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        result = frob_run_touched_tests(tmp_path, base="not-a-real-ref")
        assert result.is_err
        assert result.danger_err == ServeError.GitFailed
