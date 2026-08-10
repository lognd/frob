"""Direct-call coverage for `frob sys capacity [--population N]` (T-1927).

Kept in its own small file, mirroring `test_app_sys_threats.py`'s own
rationale: a dedicated file keeps this ticket's scope closure honest
without dragging in `test_app_runners_batch7.py`'s unrelated test
classes. Reuses `_init_design_repo` by import (reading, never writing, a
file outside declared scope is fine), per the NO DUPLICATION convention.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.__main__ import _build_parser
from frob.app.config import AppConfig
from frob.app.sys_runner import run as sys_run
from tests.unit.test_app_runners_batch7 import _init_design_repo

#: `api` declares a small `Capacity` (10 req/s, 1 replica) and `evil`
#: declares `users 50` -- T-0702's `aggregate_demand` propagates that
#: through `f1` to `api`, already over capacity at its CURRENT
#: (unscaled) declared demand.
_CAPACITY_MODEL = """\
module m
node evil : foreign { users 50; }
node api : trusted { capacity 10 req/s replicas 1..1; }
flow f1 : evil -> api
"""

#: `api`'s current demand (10 users) is comfortably under its capacity
#: (10 req/s), but a large enough `--population` scale (against `evil`'s
#: own declared `users 10` baseline) pushes it over.
_SCALABLE_MODEL = """\
module m
node evil : foreign { users 10; }
node api : trusted { capacity 10 req/s replicas 1..1; }
flow f1 : evil -> api
"""

_NO_BASELINE_MODEL = """\
module m
node evil : foreign
node api : trusted { capacity 10 req/s replicas 1..1; }
flow f1 : evil -> api
"""


# frob:ticket T-1927
class TestSysCapacity:
    """`frob sys capacity [--population N]`: the CAP001 demand-vs-capacity
    printer, optionally projected via T-1927's `project_capacity`."""

    def test_no_population_reports_current_violations(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _CAPACITY_MODEL)
        cfg = AppConfig(sys_command="capacity", sys_path=repo)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "node=api" in caplog.text

    def test_population_scales_and_can_fire(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _SCALABLE_MODEL)
        cfg = AppConfig(
            sys_command="capacity", sys_path=repo, sys_capacity_population=1000.0
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "node=api" in caplog.text

    # frob:waive DUP001 reason="shares test_app_sys_threats.py's clean-model shape (build a repo, run the sys verb, assert no-violations at INFO), but exercises a different sys_command (capacity vs threats) against a different evaluator -- the similarity is the shared test-harness convention every sys-verb test file in this package already follows, not duplicated checking logic"  # noqa: E501
    def test_no_violations_exits_0(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(
            tmp_path,
            "module m\nnode api : trusted { capacity 1000 req/s replicas 1..1; }\n",
        )
        cfg = AppConfig(sys_command="capacity", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "no violations" in caplog.text

    def test_population_with_no_baseline_exits_1(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _NO_BASELINE_MODEL)
        cfg = AppConfig(
            sys_command="capacity", sys_path=repo, sys_capacity_population=1000.0
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "no baseline" in caplog.text

    def test_population_flag_survives_real_argv_parsing(self) -> None:
        """Regression guard (T-1927's own live-fire incident): `--population`
        is a `float` CLI flag, and `AppConfig.from_external`'s generic
        argparse-Namespace-to-model copy only forwards fields listed in
        `_config_external._FLOAT_FIELDS` -- a value that parses correctly
        but is missing from that allowlist is silently dropped (`None`)
        rather than raising, which a direct `AppConfig(...)` construction
        (every other test in this file) can never catch. Parse real argv
        through the real parser and real `AppConfig.from_args`, not a
        hand-built `AppConfig`, so this exact class of bug fails loudly."""
        parser = _build_parser()
        ns = parser.parse_args(["sys", "capacity", "--population", "1000000"])
        cfg = AppConfig.from_args(ns)
        assert cfg.sys_capacity_population == 1000000.0
