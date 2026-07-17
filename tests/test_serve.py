"""Tests for frob.serve -- the MCP tool layer (docs/serve.md).

Exercises `frob.serve._tools` (the plain-function layer) directly; the
`mcp` SDK transport (`frob.serve.server`) is a thin wrapper that raises on
`Result.is_err` and is not exercised here (no in-process MCP client in this
suite).
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.app.config import AppConfig
from frob.graph import build_graph
from frob.graph._models import LockEntry, LockFile
from frob.graph.lock import write_lock
from frob.serve import (
    ServeError,
    frob_check_scope,
    frob_doable_tickets,
    frob_doc_for,
    frob_graph_query,
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


class TestBuildServer:
    def test_registers_all_five_tools(self, tmp_path: Path) -> None:
        # frob:tests src/frob/serve/server.py::build_server kind="unit"
        from frob.serve.server import build_server

        server = build_server(tmp_path)
        names = {t.name for t in server._tool_manager.list_tools()}
        assert names == {
            "frob_doable_tickets",
            "frob_stale_docs",
            "frob_check_scope",
            "frob_graph_query",
            "frob_doc_for",
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
        write_ticket(tmp_path, _ticket("T-0001"))
        result = frob_doable_tickets(tmp_path)
        assert result.is_ok
        tickets = result.danger_ok
        assert tickets == [
            {"id": "T-0001", "title": "Sample ticket", "kind": "feature"}
        ]

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
