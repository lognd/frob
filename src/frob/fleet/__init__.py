"""frob.fleet -- cross-repo status, gate rollup, and ticket routing for a
named estate of sibling repos (T-0573, docs/modules/fleet.md).

The 9-repo compliance campaign (frob plus 8 sibling repos wired to run
`frob check`/`frob ticket` of their own) was coordinated by hand from
coordinator memory files -- there was no single command that answered "how
red is the estate right now, and where should this new finding go".
`frob fleet` reads a small manifest (`fleet.toml`, `[[repo]] name/path`),
probes each repo (git branch/dirty state, a `frob check --json` gate
summary, and its own doable-ticket count via `frob.tickets`), and rolls the
result into one reddest-first table or JSON payload. `route_ticket` files a
ticket directly into a named sibling's own ledger via `frob.tickets.
new_ticket`, no shelling out to a second `frob` process required.
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.tickets import TicketSpec, doable, load_queue, new_ticket
from frob.tickets._store import ledger_path, tickets_dir

_log = get_logger(__name__)

# frob:doc docs/modules/fleet.md#manifest-fleettoml
#: Default manifest path (repo-root-relative), matching the CLI default
#: (`--manifest fleet.toml`, `[tool.frob] fleet_manifest` in pyproject.toml).
DEFAULT_MANIFEST_PATH = Path("fleet.toml")

#: `frob check --json` subprocess timeout (seconds) for one repo's probe.
#: Generous enough for a cold ruff/ty pass on a mid-size repo, but bounded
#: so one hung sibling can never stall the whole fleet rollup indefinitely.
_CHECK_PROBE_TIMEOUT_S = 120.0


# frob:doc docs/modules/fleet.md#routing
class FleetError(ErrorSet):
    """Fallible outcomes of frob.fleet manifest loading and ticket routing."""

    ManifestNotFound = "fleet manifest file does not exist"
    ManifestMalformed = "fleet manifest failed to parse as [[repo]] TOML"
    RepoNotFound = "no manifest entry with that name"
    RepoPathMissing = "manifest entry's path does not exist on disk"
    RouteFailed = "ticket routing into the target repo's ledger failed"


# frob:doc docs/modules/fleet.md#manifest-fleettoml
class RepoEntry(BaseModel):
    """One `[[repo]]` manifest row: a short `name` and its filesystem `path`."""

    model_config = {}

    name: str
    path: Path


# frob:doc docs/modules/fleet.md#manifest-fleettoml
class FleetManifest(BaseModel):
    """The full parsed `fleet.toml`: an ordered tuple of `RepoEntry` rows."""

    model_config = {}

    repos: tuple[RepoEntry, ...] = ()


# frob:doc docs/modules/fleet.md#gate-summary
class GateSummary(BaseModel):
    """Severity-bucketed violation counts from one repo's `frob check --json`
    probe (or a zeroed summary when the probe could not run at all)."""

    model_config = {}

    error_count: int = 0
    warn_count: int = 0
    exit_code: int | None = None


# frob:doc docs/modules/fleet.md#repo-status
class RepoStatus(BaseModel):
    """One repo's collected status row: git state, gate summary, doable-ticket
    count, and (when the probe failed) a human-readable `error` instead."""

    model_config = {}

    name: str
    path: Path
    branch: str | None = None
    dirty: bool = False
    gates: GateSummary = GateSummary()
    doable_count: int = 0
    error: str | None = None


# frob:doc docs/modules/fleet.md#fleet-report
class FleetReport(BaseModel):
    """`rollup`'s output: every probed repo's `RepoStatus`, reddest-first."""

    model_config = {}

    repos: tuple[RepoStatus, ...] = ()


# frob:doc docs/modules/fleet.md#manifest-fleettoml
# frob:tests tests/unit/fleet/test_manifest.py::TestLoadManifest.test_load_manifest_ok
# frob:tests tests/unit/fleet/test_manifest.py::TestLoadManifest.test_load_manifest_missing  # noqa: E501
# frob:tests tests/unit/fleet/test_manifest.py::TestLoadManifest.test_load_manifest_malformed  # noqa: E501
def load_manifest(path: Path) -> Result[FleetManifest, FleetError]:
    """Parse `[[repo]] name/path` rows out of `path` (a `fleet.toml`-shaped
    file); `Err(ManifestNotFound)` when `path` is missing, `Err
    (ManifestMalformed)` on any TOML/schema failure -- never a bare
    exception, callers (the CLI runner, tests) get a typed outcome either
    way."""
    if not path.exists():
        _log.error("fleet: manifest not found: %s", path)
        return Err(FleetError.ManifestNotFound)
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        _log.error("fleet: manifest %s failed to parse: %s", path, exc)
        return Err(FleetError.ManifestMalformed)
    try:
        manifest = FleetManifest(repos=tuple(data.get("repo", [])))
    except Exception as exc:  # noqa: BLE001 -- pydantic ValidationError, re-typed
        _log.error("fleet: manifest %s failed schema validation: %s", path, exc)
        return Err(FleetError.ManifestMalformed)
    manifest = _rebase_relative_paths(manifest, path.resolve().parent)
    _log.info("fleet: loaded %d repo(s) from %s", len(manifest.repos), path)
    return Ok(manifest)


def _rebase_relative_paths(
    manifest: FleetManifest, manifest_dir: Path
) -> FleetManifest:
    """Resolve each relative `RepoEntry.path` against `manifest_dir` (the
    manifest FILE's own directory), not the process cwd -- a `fleet.toml`
    committed at a repo root with `path = "../typani"` must mean "next to
    this repo", regardless of where `frob fleet` happens to be invoked
    from. An already-absolute entry path is left untouched."""
    rebased = tuple(
        entry
        if entry.path.is_absolute()
        else entry.model_copy(update={"path": (manifest_dir / entry.path)})
        for entry in manifest.repos
    )
    return manifest.model_copy(update={"repos": rebased})


# frob:ticket T-0573
def _git_branch_and_dirty(repo_path: Path) -> tuple[str | None, bool]:
    """`(current branch name or None, has-uncommitted-changes)` for
    `repo_path`, via a bare `git status --porcelain=v1 -b`; a `None` branch
    (detached HEAD, or `git` unavailable/failed) still reports `dirty` best
    -effort from whatever output was produced."""
    # T-0803: routed through `guarded_subprocess_run` (T-0778's guard) so
    # `FROB_DISABLE_EXEC=1` refuses this git spawn -- kept as a direct
    # `guarded_subprocess_run` call (not `frob.gitio.run_argv`) to preserve
    # this function's existing best-effort `(None, False)` fallback
    # contract and its `cwd=`-based invocation shape.
    try:
        guarded = guarded_subprocess_run(
            ["git", "status", "--porcelain=v2", "--branch"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("fleet: git status failed for %s: %s", repo_path, exc)
        return None, False
    if guarded.is_err:
        _log.warning("fleet: git status refused (exec disabled) for %s", repo_path)
        return None, False
    result = guarded.danger_ok
    branch = None
    dirty = False
    for line in result.stdout.splitlines():
        if line.startswith("# branch.head "):
            branch = line.removeprefix("# branch.head ").strip()
        elif not line.startswith("#"):
            dirty = True
    return branch, dirty


# frob:ticket T-0573
def _gate_summary_probe(repo_path: Path) -> GateSummary:
    """Fast `frob check --json` subprocess probe: severity-bucketed
    violation counts for `repo_path`. Any failure (missing `frob` on PATH,
    timeout, non-JSON output) degrades to a zeroed `GateSummary` -- one
    unreachable sibling never aborts the whole fleet rollup, it just shows
    as all-zero with the caller's own `RepoStatus.error` set."""
    argv = _check_probe_argv(repo_path)
    # T-0803: routed through `guarded_subprocess_run` (T-0778's guard) so
    # `FROB_DISABLE_EXEC=1` refuses this `frob check` probe spawn too;
    # degrades to the same all-zero `GateSummary()` fallback this function
    # already uses for any other probe failure.
    try:
        guarded = guarded_subprocess_run(
            argv,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=_CHECK_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("fleet: check probe failed for %s: %s", repo_path, exc)
        return GateSummary()
    if guarded.is_err:
        _log.warning("fleet: check probe refused (exec disabled) for %s", repo_path)
        return GateSummary()
    result = guarded.danger_ok
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        _log.warning(
            "fleet: check probe for %s produced non-JSON output (exit %d)",
            repo_path,
            result.returncode,
        )
        return GateSummary(exit_code=result.returncode)
    error_count, warn_count = _count_diagnostics(payload)
    return GateSummary(
        error_count=error_count, warn_count=warn_count, exit_code=result.returncode
    )


# frob:ticket T-0573
def _check_probe_argv(repo_path: Path) -> list[str]:
    """The `_gate_summary_probe` argv for `repo_path`: `uv run --project
    <repo_path> frob check --json`, NEVER a bare `frob` on `PATH`. This
    machine's PATH `frob` is a documented stale global (docs/guides/
    agent-playbook.md section 2) -- shelling a bare `frob` here would
    silently probe every sibling with the WRONG gate logic while looking
    trustworthy (same-looking table, wrong numbers). `--project` pins `uv`
    to that repo's own environment/pinned `frob`, matching the `uv run
    frob ...` convention this repo's own playbook mandates everywhere
    else; `cwd=repo_path` (set by the caller) is what actually makes the
    probe analyze THAT repo's tree rather than the caller's cwd."""
    return ["uv", "run", "--project", str(repo_path), "frob", "check", "--json"]


# frob:ticket T-0573
def _count_diagnostics(payload: dict) -> tuple[int, int]:
    """`(error_count, warn_count)` from a real `frob check --json` payload
    (`frob.check.CheckResult.as_json`'s schema: `{"path", "results": [
    {"diagnostics": [{"severity": "error"|"warning"|...}, ...]}, ...]}`) --
    NOT the flat `{"violations": [...]}` shape another `frob` subcommand
    (`frob vet --json`) happens to use; the two are different schemas and
    must not be confused."""
    results = payload.get("results", [])
    errors = 0
    warns = 0
    for tool_result in results:
        for diag in tool_result.get("diagnostics", []):
            severity = diag.get("severity")
            if severity == "error":
                errors += 1
            elif severity == "warning":
                warns += 1
    return errors, warns


# frob:ticket T-0573
def _doable_count(repo_path: Path) -> int:
    """Repo's own `frob ticket doable` count via `frob.tickets`' public API
    directly (no subprocess) -- 0 (logged, not raised) when the repo has no
    ledger or a malformed one, since a missing ledger is not the fleet
    rollup's problem to fail on."""
    queue_result = load_queue(repo_path)
    if queue_result.is_err:
        _log.warning(
            "fleet: %s: ticket queue unavailable (%s)",
            repo_path,
            queue_result.danger_err,
        )
        return 0
    return len(doable(queue_result.danger_ok, repo_path))


# frob:doc docs/modules/fleet.md#collect
# frob:tests tests/unit/fleet/test_status.py::TestCollectStatus.test_collect_status_ok
# frob:tests tests/unit/fleet/test_status.py::TestCollectStatus.test_collect_status_missing_path  # noqa: E501
# frob:tests tests/unit/fleet/test_status.py::TestCollectStatus.test_collect_status_probes_sibling_pinned_frob_not_bare_path_frob  # noqa: E501
def collect_status(entry: RepoEntry, *, probe_gates: bool = True) -> RepoStatus:
    """One repo's full status row: git branch/dirty, doable-ticket count,
    and (when `probe_gates`) a `frob check --json` gate summary. A
    nonexistent `entry.path` short-circuits to a zeroed `RepoStatus` with
    `error` set, rather than letting `git`/`frob` subprocess calls fail
    confusingly against a missing cwd."""
    resolved = entry.path.resolve()
    if not resolved.is_dir():
        _log.error("fleet: %s: path does not exist: %s", entry.name, resolved)
        return RepoStatus(
            name=entry.name,
            path=entry.path,
            error=f"path does not exist: {resolved}",
        )
    branch, dirty = _git_branch_and_dirty(resolved)
    gates = _gate_summary_probe(resolved) if probe_gates else GateSummary()
    doable_count = _doable_count(resolved)
    return RepoStatus(
        name=entry.name,
        path=entry.path,
        branch=branch,
        dirty=dirty,
        gates=gates,
        doable_count=doable_count,
    )


# frob:doc docs/modules/fleet.md#rollup
# frob:tests tests/unit/fleet/test_status.py::TestRollup.test_rollup_orders_reddest_first  # noqa: E501
def rollup(manifest: FleetManifest, *, probe_gates: bool = True) -> FleetReport:
    """`collect_status` over every manifest entry, sorted reddest-first
    (most gate errors, then most warnings, then most doable tickets) so the
    worst-off repo is always row one -- the whole point of a fleet view is
    never having to eyeball nine rows to find the one that is on fire."""
    statuses = tuple(
        collect_status(entry, probe_gates=probe_gates) for entry in manifest.repos
    )
    ordered = tuple(
        sorted(
            statuses,
            key=lambda s: (-s.gates.error_count, -s.gates.warn_count, -s.doable_count),
        )
    )
    return FleetReport(repos=ordered)


# frob:doc docs/modules/fleet.md#routing
# frob:tests tests/unit/fleet/test_route.py::TestRouteTicket.test_route_ticket_ok
# frob:tests tests/unit/fleet/test_route.py::TestRouteTicket.test_route_ticket_unknown_repo  # noqa: E501
# frob:tests tests/unit/fleet/test_route.py::TestRouteTicket.test_route_ticket_not_frob_enabled  # noqa: E501
def route_ticket(
    manifest: FleetManifest, repo_name: str, spec: TicketSpec
) -> Result[str, FleetError]:
    """File `spec` into the named sibling's own ledger via `frob.tickets.
    new_ticket(root=<that repo's path>, spec)` -- no second `frob` process,
    no copy-paste into a coordinator memory file. `Err(RepoNotFound)` when
    `repo_name` is not in the manifest, `Err(RepoPathMissing)` when the
    entry's path does not exist, `Err(RouteFailed)` when the target has no
    ticket ledger at all (neither `tickets.md` nor a legacy `tickets/`
    dir) -- routing into a directory that has never been wired for frob
    would otherwise silently BOOTSTRAP a brand-new ledger there via
    `new_ticket`'s own create-on-first-write behavior, which is exactly
    right for a human deliberately initializing a repo but wrong for a
    fleet-routed finding landing in some unrelated directory by typo --
    or wrapping any other `frob.tickets.new_ticket` failure (a locked/
    malformed ledger, an unleased worktree, ...). Returns the new
    ticket's id on success."""
    entry = next((r for r in manifest.repos if r.name == repo_name), None)
    if entry is None:
        _log.error("fleet: route: no manifest entry named %r", repo_name)
        return Err(FleetError.RepoNotFound)
    resolved = entry.path.resolve()
    if not resolved.is_dir():
        _log.error("fleet: route: %s: path does not exist: %s", repo_name, resolved)
        return Err(FleetError.RepoPathMissing)
    if not ledger_path(resolved).exists() and not tickets_dir(resolved).is_dir():
        _log.error(
            "fleet: route: %s: no tickets.md or tickets/ ledger at %s -- "
            "not a frob-enabled repo",
            repo_name,
            resolved,
        )
        return Err(FleetError.RouteFailed)
    result = new_ticket(resolved, spec)
    if result.is_err:
        _log.error(
            "fleet: route: %s: new_ticket failed: %s", repo_name, result.danger_err
        )
        return Err(FleetError.RouteFailed)
    ticket = result.danger_ok
    _log.info("fleet: routed %s into %s", ticket.id, repo_name)
    return Ok(ticket.id)


__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "FleetError",
    "FleetManifest",
    "FleetReport",
    "GateSummary",
    "RepoEntry",
    "RepoStatus",
    "collect_status",
    "load_manifest",
    "rollup",
    "route_ticket",
]
