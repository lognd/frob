from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-1568
# frob:tests tests/unit/test_app_runners.py::TestDesignRunner.test_subcommand_delegates_to_matching_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestDesignRunner.test_exports_subcommand_delegates_to_exports_runner  # noqa: E501
# frob:tests \
# tests/unit/test_app_runners.py::TestDesignRunner.test_unknown_subcommand_exits_1
def run(cfg: AppConfig) -> None:
    """`frob design <sys|registry|docs|graph|exports>`: the T-1568
    verb-group front door onto the design-knowledge porcelain -- delegates
    straight into the existing per-command runner logic (same `AppConfig`
    dests each subcommand's parser populates), so behavior is identical to
    invoking the standalone top-level command directly."""
    if cfg.design_command == "sys":
        from frob.app.sys_runner import run as sys_run

        sys_run(cfg)
    elif cfg.design_command == "registry":
        from frob.app.registry_runner import run as registry_run

        registry_run(cfg)
    elif cfg.design_command == "docs":
        from frob.app.docs_runner import run as docs_run

        docs_run(cfg)
    elif cfg.design_command == "graph":
        from frob.app.graph_runner import run as graph_run

        graph_run(cfg)
    elif cfg.design_command == "exports":
        from frob.app.exports_runner import run as exports_run

        exports_run(cfg)
    else:
        _log.error(
            "frob design requires a subcommand: sys, registry, docs, graph, "
            "or exports"
        )
        sys.exit(1)
