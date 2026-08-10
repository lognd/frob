"""Direct-call coverage for `frob sys threats [boundary]` (T-1925).

Kept in its own small file, mirroring `test_app_sys_trace.py`'s own
rationale: a dedicated file keeps this ticket's scope closure honest
without dragging in `test_app_runners_batch7.py`'s unrelated test
classes. Reuses `_init_design_repo` by import (reading, never writing, a
file outside declared scope is fine), per the NO DUPLICATION convention.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.sys_runner import run as sys_run
from tests.unit.test_app_runners_batch7 import _init_design_repo

#: Two unclassified `may` capabilities on two nodes, one behind a
#: boundary (`api`) and one not (`other`, unconnected to `f1`) -- lets a
#: scoped `frob sys threats b1` be distinguished from the unscoped run.
_BOUNDARY_MODEL = """\
module m
node evil : foreign
node api : trusted {
    may "mystery_power";
}
node other : trusted {
    may "mystery_power";
}
flow f1 : evil -> api
boundary b1 endorse f1 : foreign -> trusted when "jwt_verified"
"""


# frob:ticket T-1925
class TestSysThreats:
    """`frob sys threats [boundary]`: the THREAT001-005 violation printer,
    optionally scoped to one boundary's protected zone via T-1925's
    node-to-boundary join."""

    def test_no_boundary_prints_every_violation(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _BOUNDARY_MODEL)
        cfg = AppConfig(sys_command="threats", sys_path=repo)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "node=api" in caplog.text
        assert "node=other" in caplog.text

    def test_boundary_scopes_to_its_own_zone_only(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _BOUNDARY_MODEL)
        cfg = AppConfig(sys_command="threats", sys_path=repo, sys_threats_boundary="b1")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "node=api" in caplog.text
        assert "node=other" not in caplog.text

    def test_clean_model_reports_no_violations_and_exits_0(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(
            tmp_path,
            "module m\nnode api : trusted\n",
        )
        cfg = AppConfig(sys_command="threats", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "no violations" in caplog.text

    def test_unknown_boundary_id_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _BOUNDARY_MODEL)
        cfg = AppConfig(
            sys_command="threats", sys_path=repo, sys_threats_boundary="no-such"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "unknown boundary id" in caplog.text
