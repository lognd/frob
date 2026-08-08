from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-1567
# frob:tests tests/unit/test_app_runners.py::TestQualityRunner.test_subcommand_delegates_to_matching_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestQualityRunner.test_arch_subcommand_delegates_to_arch_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestQualityRunner.test_mutate_subcommand_missing_file_exits_nonzero  # noqa: E501
# frob:tests \
# tests/unit/test_app_runners.py::TestQualityRunner.test_unknown_subcommand_exits_1
def run(cfg: AppConfig) -> None:
    """`frob quality <check|test|dup|arch|cycle|mutate|perf>`: the T-1567
    verb-group front door onto the correctness/hygiene-gate porcelain --
    delegates straight into the existing per-command runner logic (same
    `AppConfig` dests each subcommand's parser populates), so behavior is
    identical to invoking the standalone top-level command directly.
    `bind` is NOT handled here: `frob quality bind` is dispatched directly
    by `frob.__main__._dispatch` before `AppConfig` is even built, mirroring
    top-level `bind`'s own special case (T-0355) -- `bind_runner.run` takes
    raw argv, not a config object."""
    if cfg.quality_command == "check":
        from frob.app.check_runner import run as check_run

        check_run(cfg)
    elif cfg.quality_command == "test":
        from frob.app.test_runner import run as test_run

        test_run(cfg)
    elif cfg.quality_command == "dup":
        from frob.app.dup_runner import run as dup_run

        dup_run(cfg)
    elif cfg.quality_command == "arch":
        from frob.app.arch_runner import run as arch_run

        arch_run(cfg)
    elif cfg.quality_command == "cycle":
        from frob.app.cycle_runner import run as cycle_run

        cycle_run(cfg)
    elif cfg.quality_command == "mutate":
        from frob.app.mutate_runner import run as mutate_run

        mutate_run(cfg)
    elif cfg.quality_command == "perf":
        from frob.app.perf_runner import run as perf_run

        perf_run(cfg)
    else:
        _log.error(
            "frob quality requires a subcommand: check, test, dup, arch, "
            "bind, cycle, mutate, or perf"
        )
        sys.exit(1)
