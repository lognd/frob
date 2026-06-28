from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.dispatch import (
    abort_dispatch,
    collect_dispatch,
    create_dispatch,
    list_dispatches,
)


def run(cfg: AppConfig) -> None:
    root = Path(".").resolve()

    match cfg.dispatch_command:
        case "create":
            if not cfg.dispatch_label:
                print("dispatch create: label required", file=sys.stderr)
                sys.exit(1)
            result = create_dispatch(cfg.dispatch_label, project_root=root)
            if result.is_err:
                print(f"error: {result.danger_err.value}", file=sys.stderr)
                sys.exit(1)
            info = result.danger_ok
            print(f"dispatch {info.dispatch_id}")
            print(f"  branch:   {info.branch}")
            print(f"  worktree: {info.worktree}")

        case "collect":
            if not cfg.dispatch_id:
                print("dispatch collect: id required", file=sys.stderr)
                sys.exit(1)
            result = collect_dispatch(
                cfg.dispatch_id,
                project_root=root,
                strategy=cfg.dispatch_strategy,
            )
            if result.is_err:
                print(f"error: {result.danger_err.value}", file=sys.stderr)
                sys.exit(1)
            print(f"collected dispatch {cfg.dispatch_id}")

        case "abort":
            if not cfg.dispatch_id:
                print("dispatch abort: id required", file=sys.stderr)
                sys.exit(1)
            result = abort_dispatch(cfg.dispatch_id, project_root=root)
            if result.is_err:
                print(f"error: {result.danger_err.value}", file=sys.stderr)
                sys.exit(1)
            print(f"aborted dispatch {cfg.dispatch_id}")

        case "list":
            dispatches = list_dispatches(root)
            if not dispatches:
                print("no active dispatches")
                return
            for d in dispatches:
                print(f"  {d.dispatch_id}  [{d.label}]  branch: {d.branch}")

        case _:
            print(
                "usage: frob dispatch <create|collect|abort|list> ...", file=sys.stderr
            )
            sys.exit(1)
