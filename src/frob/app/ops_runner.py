from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-1569
# frob:tests tests/unit/test_app_runners.py::TestOpsRunner.test_subcommand_delegates_to_matching_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestOpsRunner.test_stats_subcommand_delegates_to_stats_runner  # noqa: E501
# frob:tests \
# tests/unit/test_app_runners.py::TestOpsRunner.test_unknown_subcommand_exits_1
def run(cfg: AppConfig) -> None:
    """`frob ops <release|natives|doctor|clean|fleet|deploy|scaffold|
    gitlog|stats>`: the T-1569 verb-group front door onto the release/
    fleet/infra-plumbing porcelain -- delegates straight into the
    existing per-command runner logic (same `AppConfig` dests each
    subcommand's parser populates), so behavior is identical to invoking
    the standalone top-level command directly."""
    if cfg.ops_command == "release":
        from frob.app.release_runner import run as release_run

        release_run(cfg)
    elif cfg.ops_command == "natives":
        from frob.app.natives_runner import run as natives_run

        natives_run(cfg)
    elif cfg.ops_command == "doctor":
        from frob.app.doctor_runner import run as doctor_run

        doctor_run(cfg)
    elif cfg.ops_command == "clean":
        from frob.app.clean_runner import run as clean_run

        clean_run(cfg)
    elif cfg.ops_command == "fleet":
        from frob.app.fleet_runner import run as fleet_run

        fleet_run(cfg)
    elif cfg.ops_command == "deploy":
        from frob.app.deploy_runner import run as deploy_run

        deploy_run(cfg)
    elif cfg.ops_command == "scaffold":
        from frob.app.scaffold_runner import run as scaffold_run

        scaffold_run(cfg)
    elif cfg.ops_command == "gitlog":
        from frob.app.gitlog_runner import run as gitlog_run

        gitlog_run(cfg)
    elif cfg.ops_command == "stats":
        from frob.app.stats_runner import run as stats_run

        stats_run(cfg)
    else:
        _log.error(
            "frob ops requires a subcommand: release, natives, doctor, "
            "clean, fleet, deploy, scaffold, gitlog, or stats"
        )
        sys.exit(1)
