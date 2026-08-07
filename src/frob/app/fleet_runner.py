"""CLI wiring for `frob fleet status` and `frob fleet route` (T-0573,
docs/modules/fleet.md): cross-repo status/gate rollup and ticket routing
over a `fleet.toml` manifest of sibling repos.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.fleet import (
    FleetError,
    RepoStatus,
    load_manifest,
    rollup,
    route_ticket,
)
from frob.logging import get_logger, quiet_stdout_logs
from frob.render import Renderer
from frob.tickets import Origin, Priority, TicketKind, TicketSpec

_log = get_logger(__name__)

_FLEET_ERROR_MESSAGES: dict[FleetError, str] = {
    FleetError.ManifestNotFound: "manifest file does not exist",
    FleetError.ManifestMalformed: "manifest failed to parse",
    FleetError.RepoNotFound: "no manifest entry with that name",
    FleetError.RepoPathMissing: "manifest entry's path does not exist",
    FleetError.RouteFailed: "ticket routing failed",
}


# frob:doc docs/modules/app.md#runners
# frob:ticket T-0815
# frob:tests tests/unit/test_fleet_runner.py::TestFleetRunner.test_run_status_table
# frob:tests tests/unit/test_fleet_runner.py::TestFleetRunner.test_run_status_missing_manifest  # noqa: E501
# frob:tests tests/unit/test_fleet_runner.py::TestFleetRunner.test_run_route_ok
def run(cfg: AppConfig) -> None:
    """Dispatch `frob fleet status` (default) or `frob fleet route`."""
    if cfg.fleet_command == "route":
        _run_route(cfg)
    else:
        _run_status(cfg)


def _manifest_path(cfg: AppConfig) -> Path:
    """`--manifest PATH`, else `fleet_manifest` from `[tool.frob]`, else
    `frob.fleet.DEFAULT_MANIFEST_PATH` (`./fleet.toml`)."""
    from frob.fleet import DEFAULT_MANIFEST_PATH

    return cfg.fleet_manifest or DEFAULT_MANIFEST_PATH


def _run_status(cfg: AppConfig) -> None:
    """Load the manifest, roll up every repo's status, print a reddest-first
    table (or `--json`). Exits 1 on a missing/malformed manifest.

    T-0815: the entire payload path -- `load_manifest`'s own INFO log plus
    `rollup`'s `git`/gate probes spawned through `guarded_subprocess_run`
    (which DEBUG-logs every spawn) -- can leak log lines into stdout ahead
    of the JSON payload, since this repo's stdout log handler is
    DEBUG-level by default. Wrapped in `quiet_stdout_logs()` only when
    `--json` is requested (matching `frob.app.xref_runner`'s conditional
    pattern); human mode keeps the diagnostic lines visible."""
    ctx = quiet_stdout_logs() if cfg.fleet_json else contextlib.nullcontext()
    with ctx:
        manifest_path = _manifest_path(cfg)
        manifest_result = load_manifest(manifest_path)
        if manifest_result.is_err:
            _log.error(
                "fleet status: %s -- %s",
                _FLEET_ERROR_MESSAGES[manifest_result.danger_err],
                manifest_path,
            )
            sys.exit(1)
        report = rollup(manifest_result.danger_ok, probe_gates=not cfg.fleet_skip_gates)

    if cfg.fleet_json:
        payload = json.loads(report.model_dump_json())
        Renderer.for_stream(sys.stdout).line(json.dumps(payload, indent=2))
        return

    _print_table(report.repos)


def _print_table(repos: tuple[RepoStatus, ...]) -> None:
    """Human-readable reddest-first table: repo, branch, dirty, errors,
    warns, doable ticket count, and (if the probe failed) the error note."""
    renderer = Renderer.for_stream(sys.stdout)
    if not repos:
        renderer.line("fleet: no repos in manifest")
        return
    headers = ["repo", "branch", "dirty", "errors", "warns", "doable", "note"]
    rows = [
        [
            s.name,
            s.branch or "-",
            "yes" if s.dirty else "no",
            str(s.gates.error_count),
            str(s.gates.warn_count),
            str(s.doable_count),
            s.error or "",
        ]
        for s in repos
    ]
    renderer.write.table(headers, rows)


def _run_route(cfg: AppConfig) -> None:
    """`frob fleet route --repo NAME --title ... --kind ...`: file one
    ticket into the named sibling's own ledger. Exits 1 on any `FleetError`
    (unknown repo, missing path, or the underlying `new_ticket` failure)."""
    manifest_path = _manifest_path(cfg)
    manifest_result = load_manifest(manifest_path)
    if manifest_result.is_err:
        _log.error(
            "fleet route: %s -- %s",
            _FLEET_ERROR_MESSAGES[manifest_result.danger_err],
            manifest_path,
        )
        sys.exit(1)

    if cfg.fleet_repo is None or cfg.fleet_title is None:
        _log.error("fleet route: --repo and --title are required")
        sys.exit(1)

    spec = TicketSpec(
        title=cfg.fleet_title,
        kind=TicketKind(cfg.fleet_kind or "bug"),
        origin=Origin.AGENT,
        priority=Priority(cfg.fleet_priority or "medium"),
        scope=tuple(cfg.fleet_scope),
        body=cfg.fleet_body,
    )
    result = route_ticket(manifest_result.danger_ok, cfg.fleet_repo, spec)
    if result.is_err:
        _log.error(
            "fleet route: %s -- %s",
            _FLEET_ERROR_MESSAGES[result.danger_err],
            cfg.fleet_repo,
        )
        sys.exit(1)

    Renderer.for_stream(sys.stdout).line(
        f"fleet: routed {result.danger_ok} into {cfg.fleet_repo}"
    )


__all__ = ["run"]
