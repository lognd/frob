from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.stub import stub_file, stub_file_multi

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.stub_file is None or not cfg.stub_targets:
        _log.error("frob stub requires <file> and at least one <target>")
        sys.exit(1)

    if len(cfg.stub_targets) == 1:
        result = stub_file(cfg.stub_file, cfg.stub_targets[0])
    else:
        result = stub_file_multi(cfg.stub_file, cfg.stub_targets)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    out = result.danger_ok
    if cfg.stub_output:
        cfg.stub_output.write_text(out)
        _log.info("wrote %s", cfg.stub_output)
    else:
        _log.info(out)
