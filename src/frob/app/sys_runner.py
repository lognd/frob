"""CLI wiring for `frob sys plan` -- obligation -> ticket compiler (T-0084,
docs/strata/roadmap.md phase 5, docs/commands/sys.md).

Loads every `.strata` design file under the repo's design dir, computes
the obligation frontier (`frob.strata.plan_obligations`), diffs it against
markers already present in the ticket ledger, and either prints the
would-be tree (default, dry-run) or writes it (`--apply`). The dry-run/
apply split plus the marker-diff idempotency check both live here rather
than in `frob.strata._plan` -- that module stays a pure model -> tickets
compiler with no I/O of its own (T-0084 scope note: `frob.tickets` is
read-only reuse from this runner's point of view, never mutated by
`_plan.py` itself).
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from frob.app.config import AppConfig
from frob.graph import GraphSnapshot, build_graph, load_graph
from frob.logging import get_logger
from frob.strata import (
    DEFAULT_DESIGN_DIR,
    MARKER_PREFIX,
    KernelModel,
    PlannedTicket,
    load_design_ids,
    plan_obligations,
)
from frob.tickets import load_all, new_ticket
from frob.tickets._models import Origin, TicketSpec

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from frob.toml, defaulting to `DEFAULT_DESIGN_DIR`
    (duplicated from `frob.gates`'s identical helper -- T-0084 scope excludes
    `src/frob/gates`, and this is a two-line frob.toml read, not shared logic
    worth a cross-module import)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("sys plan: frob.toml unreadable: %s", exc)
        return DEFAULT_DESIGN_DIR
    return data.get("strata", {}).get("design_dir", DEFAULT_DESIGN_DIR)


def _merge_models(models: tuple[KernelModel, ...]) -> KernelModel:
    """Concatenate every loaded design file's facts into one `KernelModel` so
    a multi-file design is planned as a single obligation surface."""
    return KernelModel(
        nodes=tuple(n for m in models for n in m.nodes),
        flows=tuple(f for m in models for f in m.flows),
        boundaries=tuple(b for m in models for b in m.boundaries),
        claims=tuple(c for m in models for c in m.claims),
        scenarios=tuple(s for m in models for s in m.scenarios),
    )


def _load_snapshot(root: Path) -> GraphSnapshot | None:
    """Load (building if stale) the graph snapshot the unbound boundary/secret
    check needs; `None` (with a logged warning) if it cannot be produced --
    the rest of the plan still runs without that one obligation kind."""
    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info("sys plan: cache stale/missing, building: %s", loaded.danger_err)
        loaded = build_graph(root, cache)
    if loaded.is_err:
        _log.warning(
            "sys plan: graph unavailable, skipping unbound check: %s",
            loaded.danger_err,
        )
        return None
    return loaded.danger_ok


def _existing_markers(root: Path) -> frozenset[str]:
    """Every `sys-plan:...` marker line already present in some ticket body --
    the idempotency join key (`frob.strata._plan` module docstring)."""
    loaded = load_all(root)
    if loaded.is_err:
        _log.error("sys plan: could not load ticket store: %s", loaded.danger_err)
        sys.exit(1)
    markers: set[str] = set()
    for ticket in loaded.danger_ok.values():
        for line in ticket.body.splitlines():
            stripped = line.strip()
            if stripped.startswith(MARKER_PREFIX):
                markers.add(stripped)
    return frozenset(markers)


def _print_dry_run(new: list[PlannedTicket]) -> None:
    """Print the would-be ticket tree without writing anything (dry-run default)."""
    if not new:
        _log.info("sys plan: model unchanged, nothing to plan")
        return
    for ticket in new:
        indent = "  " if ticket.parent_marker else ""
        _log.info(
            "%s[%s] %s (%s)", indent, ticket.marker, ticket.title, ticket.kind.value
        )


def _spec_for(ticket: PlannedTicket, marker_to_id: dict[str, str]) -> TicketSpec:
    """Build a `TicketSpec` for `ticket`, resolving its marker-keyed
    blocked_by/parent references against ids already created this run."""
    blocked_by = tuple(
        marker_to_id[m] for m in ticket.blocked_by_markers if m in marker_to_id
    )
    parent = marker_to_id.get(ticket.parent_marker) if ticket.parent_marker else None
    return TicketSpec(
        title=ticket.title,
        kind=ticket.kind,
        origin=Origin.AGENT,
        scope=ticket.scope,
        blocked_by=blocked_by,
        parent=parent,
        threat=ticket.threat,
        body=ticket.body,
    )


def _apply(root: Path, new: list[PlannedTicket]) -> None:
    """Write `new` tickets to the store, parents before children, so a
    child's `parent`/`blocked_by` can resolve to the parent's freshly
    allocated id (marker -> ticket id built up as each ticket is created)."""
    marker_to_id: dict[str, str] = {}
    ordered = sorted(new, key=lambda t: t.parent_marker is not None)
    for ticket in ordered:
        spec = _spec_for(ticket, marker_to_id)
        created = new_ticket(root, spec)
        if created.is_err:
            _log.error(
                "sys plan: failed to create ticket for %s: %s",
                ticket.marker,
                created.danger_err,
            )
            sys.exit(1)
        marker_to_id[ticket.marker] = created.danger_ok.id
        _log.info("sys plan: created %s for %s", created.danger_ok.id, ticket.marker)


def _run_plan(cfg: AppConfig) -> None:
    """`frob sys plan`: compile the frontier, diff against the ledger, and
    print (default) or write (`--apply`) exactly the delta."""
    root = (cfg.sys_path or Path(".")).resolve()
    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error("sys plan: %s failed to load: %s", error.path, error.error)
        sys.exit(1)
    if not ids.models:
        _log.info("sys plan: no design models under %s/%s", root, design_dir)
        return

    model = _merge_models(ids.models)
    snapshot = _load_snapshot(root)
    planned = plan_obligations(model, design_ids=ids, snapshot=snapshot)
    if planned.is_err:
        _log.error("sys plan: %s", planned.danger_err)
        sys.exit(1)

    existing = _existing_markers(root)
    new = [t for t in planned.danger_ok.tickets if t.marker not in existing]

    if not new:
        _log.info("sys plan: model unchanged, nothing to plan")
        return
    if not cfg.sys_apply:
        _print_dry_run(new)
        return
    _apply(root, new)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-0084
def run(cfg: AppConfig) -> None:
    """Dispatch `frob sys <command>`; only `plan` exists today (roadmap
    phase 5's `check`/`trace`/`capacity`/`threats`/`doc`/`export` are
    later tickets)."""
    if cfg.sys_command == "plan":
        _run_plan(cfg)
        return
    _log.error("usage: frob sys <plan> ...")
    sys.exit(1)
