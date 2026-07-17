from __future__ import annotations

import sys
from collections.abc import Callable

from frob.app.config import AppConfig, Subcommand
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-0021
def _dispatch_table() -> dict[Subcommand, Callable[[AppConfig], None]]:
    """Map each subcommand to the runner entry point that handles it."""
    from frob.app import (
        ack_runner,
        arch_runner,
        bind_runner,
        check_runner,
        cycle_runner,
        docs_runner,
        dup_runner,
        exports_runner,
        gitlog_runner,
        graph_runner,
        map_runner,
        mutate_runner,
        outline_runner,
        parse_runner,
        perf_runner,
        release_runner,
        scaffold_runner,
        serve_runner,
        stats_runner,
        test_runner,
        ticket_runner,
        vet_runner,
        xref_runner,
    )

    return {
        Subcommand.scaffold: scaffold_runner.run,
        Subcommand.cycle: cycle_runner.run,
        Subcommand.outline: outline_runner.run,
        Subcommand.map: map_runner.run,
        Subcommand.xref: xref_runner.run,
        Subcommand.parse: parse_runner.run,
        Subcommand.dup: dup_runner.run,
        Subcommand.arch: arch_runner.run,
        Subcommand.docs: docs_runner.run,
        Subcommand.bind: lambda _cfg: bind_runner.run([]),
        Subcommand.exports: exports_runner.run,
        Subcommand.check: check_runner.run,
        Subcommand.gitlog: gitlog_runner.run,
        Subcommand.graph: graph_runner.run,
        Subcommand.ack: ack_runner.run,
        Subcommand.ticket: ticket_runner.run,
        Subcommand.test: test_runner.run,
        Subcommand.vet: vet_runner.run,
        Subcommand.perf: perf_runner.run,
        Subcommand.release: release_runner.run,
        Subcommand.stats: stats_runner.run,
        Subcommand.serve: serve_runner.run,
        Subcommand.mutate: mutate_runner.run,
    }


# frob:doc docs/modules/app.md#entry-point
class App:
    # frob:ticket T-0021
    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    def __call__(self) -> None:
        # frob:ticket T-0021
        subcommand = self._cfg.subcommand
        handler = _dispatch_table().get(subcommand) if subcommand else None
        if handler is None:
            _log.error(
                "usage: frob "
                "<scaffold|cycle|outline|map|xref|parse|dup|arch|docs|bind|"
                "exports|check|gitlog|graph|ack|ticket|test|vet|perf|"
                "release|stats|serve|mutate>"
                " ..."
            )
            sys.exit(1)
        handler(self._cfg)
