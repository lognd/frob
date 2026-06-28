from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.mission import (
    create_mission,
    done_mission,
    list_missions,
    stuck_mission,
)

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    cmd = cfg.mission_command
    root = Path(".")

    if cmd == "new" or cmd is None:
        if cfg.mission_type is None:
            _log.error(
                "frob mission new requires <type>: fix | test | implement | review"
            )
            sys.exit(1)
        result = create_mission(
            cfg.mission_type,
            project_root=root,
            file=cfg.mission_file,
            target=cfg.mission_target,
            error=cfg.mission_error,
            test_name=cfg.mission_test,
            extra_context=cfg.mission_context,
        )
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        path = result.danger_ok
        _log.info("%s", path)

    elif cmd == "done":
        if not cfg.mission_id:
            _log.error("frob mission done requires <id>")
            sys.exit(1)
        result = done_mission(cfg.mission_id, root)
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        _log.info("mission %s completed and removed", cfg.mission_id)

    elif cmd == "stuck":
        if not cfg.mission_id or not cfg.mission_reason:
            _log.error("frob mission stuck requires <id> <reason>")
            sys.exit(1)
        result = stuck_mission(cfg.mission_id, cfg.mission_reason, root)
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        _log.info("mission %s marked stuck: %s", cfg.mission_id, result.danger_ok)

    elif cmd == "list":
        missions = list_missions(root)
        if not missions:
            _log.info("no pending missions")
        for mid, mtype in missions:
            _log.info("%s  %s  .frob/missions/%s.md", mid, mtype, mid)

    else:
        _log.error("unknown mission command %r -- use: new | done | stuck | list", cmd)
        sys.exit(1)
