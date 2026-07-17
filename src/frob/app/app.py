from __future__ import annotations

import sys

from frob.app.config import AppConfig, Subcommand
from frob.logging import get_logger

_log = get_logger(__name__)


class App:
    # frob:ticket T-0021
    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    def __call__(self) -> None:
        # frob:ticket T-0021
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
            outline_runner,
            parse_runner,
            perf_runner,
            release_runner,
            scaffold_runner,
            test_runner,
            ticket_runner,
            vet_runner,
            xref_runner,
        )

        match self._cfg.subcommand:
            case Subcommand.scaffold:
                scaffold_runner.run(self._cfg)
            case Subcommand.cycle:
                cycle_runner.run(self._cfg)
            case Subcommand.outline:
                outline_runner.run(self._cfg)
            case Subcommand.map:
                map_runner.run(self._cfg)
            case Subcommand.xref:
                xref_runner.run(self._cfg)
            case Subcommand.parse:
                parse_runner.run(self._cfg)
            case Subcommand.dup:
                dup_runner.run(self._cfg)
            case Subcommand.arch:
                arch_runner.run(self._cfg)
            case Subcommand.docs:
                docs_runner.run(self._cfg)
            case Subcommand.bind:
                bind_runner.run([])
            case Subcommand.exports:
                exports_runner.run(self._cfg)
            case Subcommand.check:
                check_runner.run(self._cfg)
            case Subcommand.gitlog:
                gitlog_runner.run(self._cfg)
            case Subcommand.graph:
                graph_runner.run(self._cfg)
            case Subcommand.ack:
                ack_runner.run(self._cfg)
            case Subcommand.ticket:
                ticket_runner.run(self._cfg)
            case Subcommand.test:
                test_runner.run(self._cfg)
            case Subcommand.vet:
                vet_runner.run(self._cfg)
            case Subcommand.perf:
                perf_runner.run(self._cfg)
            case Subcommand.release:
                release_runner.run(self._cfg)
            case _:
                _log.error(
                    "usage: frob "
                    "<scaffold|cycle|outline|map|xref|parse|dup|arch|docs|bind|"
                    "exports|check|gitlog|graph|ack|ticket|test|vet|perf|release>"
                    " ..."
                )
                sys.exit(1)
