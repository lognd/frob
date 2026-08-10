"""Direct-call coverage for `frob sys trace` (T-1480).

Kept in its own small file, separate from `tests/unit/test_app_runners_
batch7.py` (which already covers `plan`/`doc`/`export`/`audit`): that file
carries several unrelated test classes (`TestTicketStart`,
`TestSpawnBackgroundSweep`, `TestTicketEvidence`, ...) whose own `frob:
tests`/call-graph edges reach well outside T-1480's declared scope --
adding the whole file to scope pulled in real SCOPE002 closure errors for
symbols this ticket never touches. A dedicated file keeps the ticket's
scope closure honest without dragging in that collateral. Reuses that
file's own `_CLEAN_MODEL`/`_init_design_repo` fixtures by import (reading,
never writing, a file outside declared scope is fine) rather than
duplicating them, per the NO DUPLICATION convention -- DUP001 fired on a
first duplicated draft of this file and this import is the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.sys_runner import run as sys_run
from tests.unit.test_app_runners_batch7 import _CLEAN_MODEL, _init_design_repo


# frob:ticket T-1480
class TestSysTrace:
    """`frob sys trace <from> [to]`: the influence-closure witness-path CLI
    wrapper over `FactBase.reachable` (T-1480)."""

    def test_trace_prints_witness_path_to_destination(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(
            sys_command="trace", sys_path=repo, sys_trace_from="evil", sys_trace_to="api"
        )
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "api reachable via evil -> f1 -> api" in caplog.text

    def test_trace_prints_whole_closure_with_no_destination(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(sys_command="trace", sys_path=repo, sys_trace_from="evil")
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "api via evil -> f1 -> api" in caplog.text

    def test_unknown_source_node_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(sys_command="trace", sys_path=repo, sys_trace_from="nope")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "not a known node" in caplog.text

    def test_unreachable_destination_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(
            sys_command="trace", sys_path=repo, sys_trace_from="api", sys_trace_to="evil"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "is not reachable" in caplog.text
