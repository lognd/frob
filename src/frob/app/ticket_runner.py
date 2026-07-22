"""CLI wiring for `frob ticket new|list|show|doable|board|epic|plan|start|
requeue|sweep|reconcile|land|merge-driver|attach|block|close|fail|drop|
evidence|done-report|scope|priority|component|label|archive`
(docs/modules/tickets.md)."""

# frob:waive TEST005 reason="module line coverage 22.7%, debt T-0160"
# frob:waive SCOPE001 reason="T-0323 scope omitted this file, filed T-draft-bc39c17f"
# frob:waive SCOPE001 reason="T-0453 needs doable --show-blocked/--ignore-lease wiring here, T-0176/T-0220 precedent"  # noqa: E501
# frob:waive SCOPE001 reason="T-0411 needs new --priority/priority-subcommand wiring here; T-0453/T-0455 bootstrap precedent, T-0446 tracks the general gap"  # noqa: E501

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from typani.result import Err, Ok

from frob.app._style import style_state, style_ticket_id
from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.process._guard import EXEC_KILL_SWITCH_ENV, exec_enabled

if TYPE_CHECKING:
    from frob.tickets import TicketQueue

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


def _stdout_color() -> bool:
    """Whether ticket-listing lines (routed to stdout via `_log.info`,
    `frob.logging.config.toml`'s below-WARNING handler) should carry ANSI
    color -- T-0179's single should_color(stdout) check, evaluated once per
    call site rather than duplicated per print."""
    from frob.logging.color import should_color

    return should_color(sys.stdout)


def _ticket_dispatch_table() -> dict:
    """Map each `frob ticket` subcommand name to its `(root, cfg)` handler."""
    return {
        "new": _new,
        "list": _list,
        "show": _show,
        "doable": _doable,
        "plan": _plan,
        "start": _start,
        "requeue": _requeue,
        "sweep": _sweep_cmd,
        "reconcile": _reconcile_cmd,
        "migrate": lambda root, _cfg: _migrate(root),
        "renumber": _renumber,
        "land": _land,
        "merge-driver": _merge_driver,
        "attach": _attach,
        "block": _block,
        "close": _close,
        "fail": _fail,
        "drop": _drop,
        "evidence": _evidence,
        "done-report": _done_report,
        "scope": _scope,
        "priority": _priority,
        "component": _component,
        "label": _label,
        "board": _board,
        "epic": _epic,
        "archive": lambda root, _cfg: _archive(root),
    }


# frob:doc docs/modules/app.md#runners
# frob:waive TEST005 reason="run 20.0% branch cover, debt T-0160"
def run(cfg: AppConfig) -> None:
    """Dispatch to the ticket subcommand named by `cfg.ticket_command`."""
    root = (cfg.ticket_path or Path(".")).resolve()

    handler = _ticket_dispatch_table().get(cfg.ticket_command)
    if handler is None:
        _log.error(
            "usage: frob ticket <new|list|show|doable|board|epic|plan|start|"
            "requeue|sweep|reconcile|land|merge-driver|attach|block|close|"
            "fail|drop|evidence|done-report|scope|priority|component|label|"
            "archive> ..."
        )
        sys.exit(1)
    handler(root, cfg)


def _ticket_spec_from_cfg(cfg: AppConfig, *, title: str, kind: str):  # noqa: ANN201
    """Build the `TicketSpec` `frob ticket new`'s flags describe.

    `title`/`kind` are taken as separate required params (not read again from
    `cfg.ticket_title`/`cfg.ticket_kind`) so the caller's None-check narrows
    them to `str` here too -- `cfg`'s fields stay `str | None` on their own.
    """
    from frob.tickets import Origin, Priority, Stride, TicketKind, TicketSpec

    return TicketSpec(
        title=title,
        kind=TicketKind(kind),
        origin=Origin(cfg.ticket_origin) if cfg.ticket_origin else Origin.HUMAN,
        # frob:ticket T-0411
        priority=(
            Priority(cfg.ticket_priority) if cfg.ticket_priority else Priority.MEDIUM
        ),
        scope=tuple(cfg.ticket_scope),
        blocked_by=tuple(cfg.ticket_blocked_by),
        parent=cfg.ticket_parent,
        acceptance=tuple(cfg.ticket_acceptance),
        threat=Stride(cfg.ticket_threat) if cfg.ticket_threat else None,
        # frob:ticket T-0454
        component=cfg.ticket_component,
        labels=tuple(cfg.ticket_labels),
        body=cfg.ticket_body,
    )


def _maybe_attach_clipboard_image(root: Path, ticket_id: str) -> None:
    """Interactively (TTY only) offer to attach a clipboard image to `ticket_id`."""
    if not sys.stdin.isatty():
        return
    from frob.tickets import AttachmentSource, attach
    from frob.tickets.clipboard import clipboard_has_image

    if not clipboard_has_image():
        return
    answer = input(f"Attach clipboard image to {ticket_id}? [y/N] ").strip().lower()
    if answer != "y":
        return
    attach_result = attach(root, ticket_id, AttachmentSource(path=None), caption="")
    if attach_result.is_err:
        _log.error("clipboard attach failed: %s", attach_result.danger_err)
    else:
        _log.info("attached clipboard image to %s", ticket_id)


# frob:ticket T-0030
# frob:ticket T-0106
def _new(root: Path, cfg: AppConfig) -> None:
    """Create a ticket from `cfg`'s new-ticket flags; if `--evidence` ids
    were given, apply them (via `_apply_evidence`) after creation succeeds,
    then offer to attach a clipboard image on a TTY."""
    # frob:ticket T-0005
    from frob.tickets import new_ticket

    if cfg.ticket_title is None or cfg.ticket_kind is None:
        _log.error("frob ticket new requires --title and --kind")
        sys.exit(1)

    spec = _ticket_spec_from_cfg(cfg, title=cfg.ticket_title, kind=cfg.ticket_kind)
    result = new_ticket(root, spec)
    if result.is_err:
        _log.error("ticket new failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("created %s: %s", ticket.id, ticket.title)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=ticket.id, event="created")

    if cfg.ticket_evidence_ids:
        added = _apply_evidence(root, ticket.id, cfg.ticket_evidence_ids)
        if added.is_err:
            sys.exit(1)

    _maybe_attach_clipboard_image(root, ticket.id)


def _filter_by_state(tickets, state):
    """Tickets whose state equals `state` (extracted so `_list` stays a flat
    sequence of independent steps, not a nested-loop join)."""
    return [t for t in tickets if t.state == state]


def _list(root: Path, cfg: AppConfig) -> None:
    # Active store only (T-0096) -- archived done/dropped tickets would
    # otherwise pile back up in every `list` the archive command exists to
    # keep them out of.
    from frob.tickets import TicketState, load_active

    result = load_active(root)
    if result.is_err:
        _log.error("ticket list failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    tickets = sorted(queue.tickets.values(), key=lambda t: t.id)
    if cfg.ticket_state:
        tickets = _filter_by_state(tickets, TicketState(cfg.ticket_state))

    if cfg.ticket_json:
        import json

        _log.info(json.dumps([t.model_dump(mode="json") for t in tickets], indent=2))
        return

    if not tickets:
        _log.info("no tickets")
        return
    color = _stdout_color()
    for t in tickets:
        _log.info(
            "%s  [%s]  %s  (%s)",
            style_ticket_id(t.id, color),
            style_state(t.state.value, color),
            t.title,
            t.kind.value,
        )


def _show(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import load_queue

    if cfg.ticket_id is None:
        _log.error("frob ticket show requires <id>")
        sys.exit(1)
    result = load_queue(root)
    if result.is_err:
        _log.error("ticket show failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None:
        _log.error("no ticket %s", cfg.ticket_id)
        sys.exit(1)

    if cfg.ticket_json:
        _log.info(ticket.model_dump_json(indent=2))
        return

    color = _stdout_color()
    _log.info(
        "%s  [%s]  %s  (%s)\nblocked_by=%s scope=%s\n\n%s",
        style_ticket_id(ticket.id, color),
        style_state(ticket.state.value, color),
        ticket.title,
        ticket.kind.value,
        list(ticket.blocked_by),
        list(ticket.scope),
        ticket.body,
    )


# frob:ticket T-0453
def _doable(root: Path, cfg: AppConfig) -> None:
    """Render `frob ticket doable`: the default collision-safe list, or
    `--show-blocked`'s per-exclusion explanation, or `--ignore-lease`'s raw
    blocker-only list (T-0453 scope-lease model) -- also always prints an
    "Active leases" section (what's holding the tree) and large-glob-
    warning nudges, and a clear message when the result is empty."""
    from frob.tickets import doable, load_queue, scope_breadth_context

    result = load_queue(root)
    if result.is_err:
        _log.error("ticket doable failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    # T-0453 perf fix: computed ONCE per invocation and threaded through
    # every lease/warning check below -- never re-walked per candidate.
    breadth = scope_breadth_context(root)

    if cfg.ticket_show_blocked:
        _render_doable_show_blocked(root, queue, cfg, breadth=breadth)
        return

    tickets = doable(queue, root, ignore_lease=cfg.ticket_ignore_lease)

    if cfg.ticket_json:
        import json

        _log.info(json.dumps([t.model_dump(mode="json") for t in tickets], indent=2))
        return

    _render_active_leases(queue)

    for warning in _active_large_glob_warnings(root, queue, breadth=breadth):
        _log.warning("ticket doable: %s", warning)

    if not tickets:
        _log.info(
            "zero doable tickets (no available lease found in repo tree; "
            "starting any ticket would conflict with a ticket in progress)"
        )
        return
    color = _stdout_color()
    for t in tickets:
        _log.info("%s  %s  (%s)", style_ticket_id(t.id, color), t.title, t.kind.value)


# frob:ticket T-0453
def _render_active_leases(queue: "TicketQueue") -> None:
    """Print a compact "Active leases" line per IN-PROGRESS ticket (id,
    title, scope) so the user always sees what's currently holding the
    tree, ahead of the doable list itself (T-0453 UX request)."""
    from frob.tickets import TicketState

    holders = sorted(
        (t for t in queue.tickets.values() if t.state is TicketState.IN_PROGRESS),
        key=lambda t: t.id,
    )
    if not holders:
        _log.info("Active leases: none")
        return
    color = _stdout_color()
    _log.info("Active leases:")
    for t in holders:
        _log.info(
            "  %s  %s  scope=%s", style_ticket_id(t.id, color), t.title, list(t.scope)
        )


# frob:ticket T-0453
def _active_large_glob_warnings(
    root: Path,
    queue: "TicketQueue",
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> list[str]:
    """Large-glob-warning nudges (T-0453) for every ticket currently
    holding a scope-lease (in-progress) or waiting to (queued/planned) --
    surfaced alongside `frob ticket doable` output so an over-broad scope
    that is serializing the queue is visible, not silently hand-diagnosed.
    Pass a precomputed `breadth` (`scope_breadth_context(root)`) so the
    breadth walk runs once for the whole listing, not once per ticket."""
    from frob.tickets import TicketState, large_glob_warnings

    warnings: list[str] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state in (
            TicketState.IN_PROGRESS,
            TicketState.QUEUED,
            TicketState.PLANNED,
        ):
            warnings.extend(large_glob_warnings(t, root, breadth=breadth))
    return warnings


# frob:ticket T-0453
def _render_doable_show_blocked(
    root: Path,
    queue: "TicketQueue",
    cfg: AppConfig,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> None:
    """Render `frob ticket doable --show-blocked`: every doable-candidate
    currently hidden by an in-progress scope-lease, with the holding
    ticket id and the overlapping glob named (T-0453)."""
    from frob.tickets import doable_blocked

    blocked = doable_blocked(queue, root, breadth=breadth)

    if cfg.ticket_json:
        import json

        payload = [
            {
                "ticket": t.model_dump(mode="json"),
                "held_by": [
                    {"ticket_id": holder_id, "glob": glob} for holder_id, glob in hits
                ],
            }
            for t, hits in blocked
        ]
        _log.info(json.dumps(payload, indent=2))
        return

    if not blocked:
        _log.info("nothing held back by a scope-lease")
        return
    color = _stdout_color()
    for t, hits in blocked:
        reasons = "; ".join(
            f"scope {glob!r} leased by in-progress {holder_id}"
            for holder_id, glob in hits
        )
        _log.info("%s  %s  held: %s", style_ticket_id(t.id, color), t.title, reasons)


def _migrate(root: Path) -> None:
    from frob.tickets import migrate

    result = migrate(root)
    if result.is_err:
        _log.error("ticket migrate failed: %s", result.danger_err)
        sys.exit(1)
    n = result.danger_ok
    if n == 0:
        _log.info("no legacy tickets/*.md files to migrate")
    else:
        _log.info("migrated %d ticket(s) into tickets.md; removed tickets/*.md", n)


# frob:ticket T-0162
def _renumber(root: Path, cfg: AppConfig) -> None:
    """`frob ticket renumber <old> <new> [--dry-run]` rewrites one ticket's id
    everywhere (the first-class replacement for the old T-0157-incident sed);
    `frob ticket renumber` with no args keeps the legacy full-contiguous
    renumber (T-0012) for whole-ledger cleanup."""
    if cfg.ticket_old_id is not None or cfg.ticket_new_id is not None:
        _renumber_one(root, cfg)
        return
    if cfg.ticket_dry_run:
        _log.error(
            "frob ticket renumber --dry-run requires <old> <new> "
            "(no dry-run mode for the whole-ledger form)"
        )
        sys.exit(1)

    # frob:ticket T-0012
    from frob.tickets import renumber

    result = renumber(root)
    if result.is_err:
        _log.error("ticket renumber failed: %s", result.danger_err)
        sys.exit(1)
    n = result.danger_ok
    if n:
        _log.info("renumbered %d ticket(s)", n)
    else:
        _log.info("ids already contiguous")


def _renumber_one(root: Path, cfg: AppConfig) -> None:
    """`frob ticket renumber <old> <new>`: rewrite one ticket's id in the
    ledger(s) plus every frob: directive reference across the tracked tree."""
    from frob.tickets import renumber_one

    if cfg.ticket_old_id is None or cfg.ticket_new_id is None:
        _log.error("frob ticket renumber requires both <old> and <new>, or neither")
        sys.exit(1)

    result = renumber_one(
        root, cfg.ticket_old_id, cfg.ticket_new_id, dry_run=cfg.ticket_dry_run
    )
    if result.is_err:
        _log.error("ticket renumber failed: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok
    verb = "would rewrite" if report.dry_run else "rewrote"
    _log.info(
        "%s %s -> %s: ledger_changed=%s, %d code file(s) / %d reference(s)",
        verb,
        report.old_id,
        report.new_id,
        report.ledger_changed,
        len(report.files_changed),
        report.occurrences,
    )
    if report.files_changed:
        for f in report.files_changed:
            _log.info("  %s", f)


# frob:ticket T-0176
def _require_land_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket land`'s required
    `<id>`/`--worktree <path>` args are both present."""
    if cfg.ticket_id is None:
        _log.error("frob ticket land requires <id>")
        sys.exit(1)
    if cfg.ticket_worktree is None:
        _log.error("frob ticket land requires --worktree <path>")
        sys.exit(1)


def _report_land_result(root: Path, report) -> None:  # noqa: ANN001
    """Log every field of a `LandReport`: the dry-run summary line, or the
    landed commit plus each changed file."""
    if report.dry_run:
        _log.info(
            "land %s: DRY RUN clean -- merged=%s wip_committed=%s "
            "(would finalize/close/squash-apply/commit onto %s)",
            report.ticket_id,
            report.merged_main_into_worktree,
            report.wip_committed,
            root,
        )
        return
    _log.info(
        "land %s: landed as %s at %s (%d file(s) changed)",
        report.ticket_id,
        report.final_id,
        report.commit_sha,
        len(report.files_changed),
    )
    for f in report.files_changed:
        _log.info("  %s", f)
    if report.release_bumped_to is not None:
        _log.info(
            "land %s: REL001 bumped to %s",
            report.ticket_id,
            report.release_bumped_to,
        )
    if report.natives_rebuilt:
        _log.info("land %s: native extension(s) rebuilt", report.ticket_id)


# frob:ticket T-0398
def _land_collected_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with no args, AFTER its
    internal merge, to get the post-merge worktree's collected node ids.
    Best-effort -- a collection failure logs and returns an empty set
    (fail-closed: `land`'s post-merge check then treats every non-cmd
    evidence id as unresolved, refusing the landing, rather than silently
    skipping the check)."""

    def fn() -> frozenset[str]:
        collected = _collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as unresolved",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, _runners = collected.danger_ok
        return python_ids | rust_ids

    return fn


# frob:ticket T-0398
def _land_passed_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with the post-merge ticket's
    non-cmd evidence ids, AFTER its internal merge, and expects back the
    subset actually observed passing -- reuses `_verify_ids_passing`
    (D-01's same real-run verification) against the worktree."""

    def fn(node_ids) -> frozenset[str]:  # noqa: ANN001
        collected = _collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as NOT passing",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, runners = collected.danger_ok
        return _verify_ids_passing(worktree, node_ids, python_ids, rust_ids, runners)

    return fn


# frob:ticket T-0398
def _land_covers_scope_fn(worktree: Path):  # noqa: ANN201
    """D-05/D-02 CLI closure: `land()` calls this with the post-merge/
    post-finalize `Ticket`, and expects back the D-02 scope-binding
    answer computed against the WORKTREE's graph (not root's) -- the
    merged, about-to-be-squashed tree is the one whose scope/evidence
    actually matter."""

    def fn(ticket):  # noqa: ANN001, ANN202
        return _covers_scope_for_ticket(worktree, ticket)

    return fn


# frob:ticket T-0338
def _land_bump_version_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this AFTER the squash-apply is staged
    onto `root`, computing whatever `frob.release` says the just-squashed
    public API demands and applying it -- the REL001 half of T-0338's
    coordinator-plumbing consolidation. `frob.release`/`frob.graph` access
    lives here (the CLI layer), not in `frob.tickets` (docs/rework.md
    cycle-avoidance, same reasoning as `_land_covers_scope_fn`)."""

    def fn(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
        return _apply_release_bump_for_land(root, ticket, final_id)

    return fn


# frob:ticket T-0338
def _required_release_bump(root: Path, final_id: str):  # noqa: ANN201
    """The REL001-required version string for `root`'s current public API
    against its tracked release manifest, or `Ok(None)` if no bump is
    needed (no manifest yet, or `BumpClass.NONE`) -- split out of
    `_apply_release_bump_for_land` to keep each half under the ARCH001
    line-count threshold (T-0338)."""
    from frob.release import BumpClass, diff_class, load_manifest, required_version
    from frob.tickets._land import LandError

    manifest_result = load_manifest(root)
    if manifest_result.is_err:
        _log.debug("land: no release manifest at %s, skipping REL001 bump", root)
        return Ok(None)
    manifest = manifest_result.danger_ok

    snapshot = _graph_snapshot(root)
    if snapshot.is_err:
        _log.error(
            "land: %s graph unavailable (%s), cannot compute REL001 bump",
            final_id,
            snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)

    bump = diff_class(manifest, snapshot.danger_ok)
    if bump == BumpClass.NONE:
        return Ok(None)

    needed = required_version(manifest.version, bump)
    if needed.is_err:
        _log.error(
            "land: %s manifest version %r is not parseable, cannot compute REL001 bump",
            final_id,
            manifest.version,
        )
        return Err(LandError.ReleaseBumpFailed)
    return Ok(needed.danger_ok)


# frob:ticket T-0338
def _apply_release_bump_for_land(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN201
    """Compute the REL001 bump class for `root`'s just-squashed public API
    against its release manifest and, if the declared version does not
    already cover it, bump `pyproject.toml`'s `version`, append a minimal
    CHANGELOG.md entry (satisfies `_changelog_mentions`'s "the version
    string appears somewhere" contract), and `frob release stamp` the new
    manifest -- staging all three files in `root`'s index so they land in
    the same commit as the squash-apply (T-0338).

    Returns `Ok(None)` (no write at all) when no manifest exists yet (the
    repo has never opted into `frob release stamp`) or when the diff class
    is `BumpClass.NONE`; `Ok(new_version)` after a successful bump+stamp;
    `Err(LandError.ReleaseBumpFailed)` on any failure along the way (an
    unreadable manifest, an unparsable `pyproject.toml` version, or a
    graph build failure) -- fail-closed, since a silently-skipped bump
    would let a landed API change slip past REL001 undetected."""
    from frob.gitio import run_argv
    from frob.release import stamp
    from frob.tickets._land import LandError

    needed = _required_release_bump(root, final_id)
    if needed.is_err:
        return Err(needed.danger_err)
    if needed.danger_ok is None:
        return Ok(None)
    new_version = needed.danger_ok

    written = _write_release_bump(root, ticket, final_id, new_version)
    if written.is_err:
        return Err(written.danger_err)

    fresh_snapshot = _graph_snapshot(root)
    if fresh_snapshot.is_err:
        _log.error(
            "land: %s graph unavailable post-bump (%s), cannot stamp release manifest",
            final_id,
            fresh_snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)
    stamp(root, fresh_snapshot.danger_ok, new_version)

    staged = run_argv(
        [
            "git",
            "-C",
            str(root),
            "add",
            "pyproject.toml",
            "CHANGELOG.md",
            ".frob-release.json",
        ]
    )
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.error("land: %s failed to stage the REL001 bump files", final_id)
        return Err(LandError.ReleaseBumpFailed)
    return Ok(new_version)


# frob:ticket T-0338
_PYPROJECT_VERSION_RE = re.compile(r'(?m)^version\s*=\s*"[^"]*"')


def _write_release_bump(root: Path, ticket, final_id: str, new_version: str):  # noqa: ANN001, ANN201
    """Rewrite `root/pyproject.toml`'s `version = "..."` line to
    `new_version` and append a minimal `## [new_version] - unreleased`
    CHANGELOG.md entry naming `final_id`/`ticket.title` (T-0338)."""
    from frob.tickets._land import LandError

    pyproject_path = root / "pyproject.toml"
    text = pyproject_path.read_text(encoding="utf-8")
    new_text, count = _PYPROJECT_VERSION_RE.subn(
        f'version = "{new_version}"', text, count=1
    )
    if count != 1:
        _log.error(
            'land: %s could not find a `version = "..."` line in %s',
            final_id,
            pyproject_path,
        )
        return Err(LandError.ReleaseBumpFailed)
    pyproject_path.write_text(new_text, encoding="utf-8")

    changelog_path = root / "CHANGELOG.md"
    changelog_text = changelog_path.read_text(encoding="utf-8")
    entry = f"## [{new_version}] - unreleased\n\n- {final_id}: {ticket.title}\n\n"
    lines = changelog_text.splitlines(keepends=True)
    insert_at = next(
        (i for i, line in enumerate(lines) if line.startswith("## ")), len(lines)
    )
    lines[insert_at:insert_at] = [entry]
    changelog_path.write_text("".join(lines), encoding="utf-8")
    _log.info(
        "land: %s wrote REL001 bump -> %s in %s and %s",
        final_id,
        new_version,
        pyproject_path,
        changelog_path,
    )
    return Ok(None)


# frob:ticket T-0338
def _land_rebuild_natives_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this with `root` only when the landed
    changeset touches a native source tree (frob-core/, strata-core/) --
    runs `make core` in `root` and returns whether it exited 0 (T-0338).
    Best-effort: `land` treats a `False` as a logged warning, never a hard
    failure (a native rebuild is cheap to re-run by hand, and a `make
    core` failure in a from-scratch clone is not necessarily this land's
    fault)."""

    def fn(root: Path) -> bool:
        result = subprocess.run(
            ["make", "core"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode != 0:
            _log.warning(
                "land: `make core` in %s exited %d -- stdout=%r stderr=%r",
                root,
                result.returncode,
                result.stdout[-2000:],
                result.stderr[-2000:],
            )
        return result.returncode == 0

    return fn


def _land(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land <id> --worktree <path> [--dry-run]`: run the whole
    merge-check-splice-close-commit chain via `frob.tickets.land`, reporting
    every field of the resulting `LandReport` (or the exact `Err` + remedy
    already logged by `land` itself) before exiting non-zero on failure.

    T-0398: this is the CLI's STRICT default -- `collected`/`passed`/
    `covers_scope` are ALWAYS supplied (as closures over the worktree,
    since `land`'s internal merge determines the post-merge state they
    must be computed against, see `land`'s own docstring), so a stale/
    red/unrelated evidence id can never silently land onto main through
    the real `frob ticket land` command, even though the library function
    itself still defaults to permissive (`None`) for other callers/tests.

    T-0338: `bump_version`/`rebuild_natives` are ALSO always supplied here
    (`_land_bump_version_fn`/`_land_rebuild_natives_fn`), folding the
    REL001 version-bump/stamp and native-rebuild-trigger coordinator steps
    into this same one command."""
    from frob.tickets import land

    _require_land_args(cfg)
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced above
    assert cfg.ticket_worktree is not None
    worktree = cfg.ticket_worktree

    result = land(
        root,
        cfg.ticket_id,
        worktree,
        dry_run=cfg.ticket_dry_run,
        collected=_land_collected_fn(worktree),
        passed=_land_passed_fn(worktree),
        covers_scope=_land_covers_scope_fn(worktree),
        bump_version=_land_bump_version_fn(),
        rebuild_natives=_land_rebuild_natives_fn(),
    )
    if result.is_err:
        _log.error("ticket land failed: %s", result.danger_err)
        sys.exit(1)

    _report_land_result(root, result.danger_ok)


# frob:ticket T-0323
def _require_merge_driver_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket merge-driver`'s
    three positional temp-file paths (%O/%A/%B, git's merge-driver
    protocol) are all present."""
    if (
        cfg.ticket_merge_base is None
        or cfg.ticket_merge_ours is None
        or cfg.ticket_merge_theirs is None
    ):
        _log.error(
            "frob ticket merge-driver requires %%O %%A %%B (base/ours/theirs "
            "temp file paths -- git supplies these when invoked as the "
            "registered merge driver, see .gitattributes / docs/modules/"
            "tickets.md#git-merge-driver)"
        )
        sys.exit(1)


# frob:ticket T-0323
def _merge_driver(root: Path, cfg: AppConfig) -> None:
    """`frob ticket merge-driver %O %A %B`: git's merge-driver entry point
    for `tickets.md` (docs/modules/tickets.md#git-merge-driver). Reads the
    `ours` (%A) and `theirs` (%B) temp files git hands it, splices them via
    the SAME `splice_ledger` `frob ticket land` uses (never a duplicate
    reimplementation), and overwrites `ours` in place with the result --
    the merge-driver protocol's contract: `ours`'s final content on disk
    IS the merge result git commits, regardless of exit status. `base`
    (%O) is accepted (git always supplies it) but unused: `splice_ledger`
    resolves per-ticket-id divergence via state-rank/Done-report tiebreaks
    over `ours`/`theirs` alone, the same as `land`'s own splice call, not
    a 3-way base diff. Exits 0 (git treats the auto-splice as a clean,
    non-conflicted merge) unless `ours`/`theirs` fail to parse as a
    ticket ledger, in which case it exits 1 and leaves `ours` untouched --
    git then reports the usual conflict for a human to resolve by hand,
    exactly as if no driver were registered."""
    from frob.tickets import splice_ledger
    from frob.tickets._land import _archived_ids

    _require_merge_driver_args(cfg)
    assert cfg.ticket_merge_ours is not None  # narrows for the type checker
    assert cfg.ticket_merge_theirs is not None
    ours_path, theirs_path = cfg.ticket_merge_ours, cfg.ticket_merge_theirs

    ours_text = ours_path.read_text(encoding="utf-8")
    theirs_text = theirs_path.read_text(encoding="utf-8")

    spliced = splice_ledger(ours_text, theirs_text, archived_ids=_archived_ids(root))
    if spliced.is_err:
        _log.error(
            "ticket merge-driver: splice_ledger failed (%s) -- leaving %s "
            "untouched for a manual conflict resolution",
            spliced.danger_err,
            ours_path,
        )
        sys.exit(1)

    ours_path.write_text(spliced.danger_ok, encoding="utf-8")
    _log.info(
        "ticket merge-driver: spliced %s (ours) + %s (theirs) -> %s",
        ours_path,
        theirs_path,
        ours_path,
    )


def _plan(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket plan requires <id>")
        sys.exit(1)
    planned = transition(root, cfg.ticket_id, TicketState.PLANNED)
    if planned.is_err:
        _log.error("ticket plan failed: %s", planned.danger_err)
        sys.exit(1)
    _log.info("planned %s", cfg.ticket_id)


# frob:ticket T-0472
def _requeue(root: Path, cfg: AppConfig) -> None:
    """Transition an in-progress ticket back to queued (the state-machine-
    legal reverse of `start`'s auto-plan+start), for a parked or
    mis-started ticket that must be honestly requeued instead of hand-
    edited (T-0472). Since the T-0453 tree-lease is derived live from
    IN_PROGRESS state + scope, this transition alone releases the lease --
    no separate lease-release step is needed. `--reason` is optional and,
    when given, is only logged (not persisted) -- requeue carries no
    Done-report/evidence surface of its own to attach it to."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket requeue requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="requeue")
    if ticket.state != TicketState.IN_PROGRESS:
        _log.error(
            "ticket requeue failed: %s is %s, not in-progress -- only an "
            "in-progress ticket can be requeued",
            cfg.ticket_id,
            ticket.state.value,
        )
        sys.exit(1)

    requeued = transition(root, cfg.ticket_id, TicketState.QUEUED)
    if requeued.is_err:
        _log.error("ticket requeue failed: %s", requeued.danger_err)
        sys.exit(1)
    if cfg.ticket_reason:
        _log.info(
            "%s requeued (in-progress -> queued): %s",
            cfg.ticket_id,
            cfg.ticket_reason,
        )
    else:
        _log.info("%s requeued (in-progress -> queued)", cfg.ticket_id)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="requeued")


def _load_ticket_or_exit(root: Path, ticket_id: str, *, verb: str):  # noqa: ANN201
    """The ticket `ticket_id`, or exit(1) if the queue or lookup fails."""
    from frob.tickets import load_queue

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("ticket %s failed: %s", verb, queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        _log.error("no ticket %s", ticket_id)
        sys.exit(1)
    return ticket


def _auto_plan_if_queued(root: Path, ticket_id: str, ticket):  # noqa: ANN201
    """Transition a QUEUED ticket to PLANNED first; `start` takes both legal steps."""
    from frob.tickets import TicketState, transition

    if ticket.state != TicketState.QUEUED:
        return ticket
    planned = transition(root, ticket_id, TicketState.PLANNED)
    if planned.is_err:
        _log.error("ticket start failed: %s", planned.danger_err)
        sys.exit(1)
    _log.info("auto-planned %s (queued -> planned)", ticket_id)
    return planned.danger_ok


def _start(root: Path, cfg: AppConfig) -> None:
    """Transition to in-progress (auto-planning a queued ticket first) and
    run the pre-work sweep. Starting a ticket that is ALREADY in-progress is
    a hard error, not a silent no-op or refresh (T-0215): `frob ticket
    sweep <id>` already exists as the idempotent refresh path, so re-running
    `start` on an in-progress ticket is treated as a coordinator mistake and
    named explicitly, pointing at `sweep` instead of quietly duplicating it."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket start requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="start")
    if ticket.state == TicketState.IN_PROGRESS:
        _log.error(
            "ticket start failed: %s is already in-progress -- run "
            "`frob ticket sweep %s` to refresh the pre-work sweep instead",
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    ticket = _auto_plan_if_queued(root, cfg.ticket_id, ticket)

    transitioned = transition(root, cfg.ticket_id, TicketState.IN_PROGRESS)
    if transitioned.is_err:
        _log.error("ticket start failed: %s", transitioned.danger_err)
        sys.exit(1)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="started")

    # frob:ticket T-0474
    # By default `start` is now just the state transition above -- the
    # pre-work sweep (a synchronous whole-repo dup+xref scan, 57s on this
    # repo's /mnt/c checkout) runs in the BACKGROUND instead of blocking the
    # command. `--foreground` opts back into the old synchronous behavior
    # (useful for a script/test that wants the sweep guaranteed recorded the
    # instant `start` returns). Either way, `frob ticket sweep <id>` remains
    # the always-available, always-synchronous way to (re)record it, so
    # PRE001 stays satisfiable regardless of how `start` recorded it.
    if cfg.ticket_foreground:
        _run_sweep(root, transitioned.danger_ok)
    else:
        _spawn_background_sweep(root, cfg.ticket_id)


def _spawn_background_sweep(root: Path, ticket_id: str) -> None:
    """Launch `frob ticket sweep <ticket_id>` as a detached background
    process against `root` (T-0474) -- `start` returns as soon as this is
    spawned, without waiting for the sweep (dup scan + xref + scope digest)
    to finish. `start_new_session=True` detaches it from this process's
    session so it keeps running after the `start` CLI invocation exits;
    stdout/stderr are discarded (the sweep's own `record_prework` call is
    the durable side effect a caller cares about -- `frob check`'s PRE001
    gate, or a later `frob ticket sweep`/`frob ticket show`, is how a
    caller observes whether it has landed yet, not this process's output).

    Best-effort: if spawning itself fails (e.g. `sys.executable` refused by
    a locked-down sandbox), this logs a warning and falls back to running
    the sweep synchronously right here -- `start` must never silently skip
    recording a sweep at all, only ever trade "instant" for "eventually".

    Honors the repo-wide exec kill switch (`FROB_DISABLE_EXEC`, T-0200):
    when set, no process is spawned at all and the sweep runs
    synchronously in-process, keeping `may "exec"` on the `cli` node a
    genuinely switchable capability (design/frob.strata, T-0474)."""
    if not exec_enabled():
        _log.info(
            "ticket start: %s exec kill switch (%s) set -- running the "
            "pre-work sweep synchronously in-process",
            ticket_id,
            EXEC_KILL_SWITCH_ENV,
        )
        ticket = _load_ticket_or_exit(root, ticket_id, verb="start")
        _run_sweep(root, ticket)
        return
    try:
        subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "frob",
                "ticket",
                "sweep",
                ticket_id,
                "--path",
                str(root),
            ],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        _log.warning(
            "ticket start: %s background sweep spawn failed (%s) -- "
            "running it synchronously instead",
            ticket_id,
            exc,
        )
        ticket = _load_ticket_or_exit(root, ticket_id, verb="start")
        _run_sweep(root, ticket)
        return
    _log.info(
        "ticket start: %s pre-work sweep launched in the background -- "
        "`frob ticket sweep %s` re-runs it synchronously if needed sooner",
        ticket_id,
        ticket_id,
    )


def _sweep_cmd(root: Path, cfg: AppConfig) -> None:
    """Re-record the pre-work sweep for an in-progress ticket (scope widened)."""
    from frob.tickets import TicketState

    if cfg.ticket_id is None:
        _log.error("frob ticket sweep requires <id>")
        sys.exit(1)
    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="sweep")
    if ticket.state != TicketState.IN_PROGRESS:
        _log.error("ticket sweep: %s is not in-progress", cfg.ticket_id)
        sys.exit(1)
    _run_sweep(root, ticket)


# frob:ticket T-0476
def _reconcile_cmd(root: Path, cfg: AppConfig) -> None:
    """`frob ticket reconcile [--apply] [--remove-orphans]`: report (and,
    with `--apply`, heal) T-0476's two ticket<->worktree binding anomalies,
    plus T-0456's orphaned-`land`-intent anomaly. Always logs a
    human-readable summary; exits 0 whether or not anomalies were found
    (finding an anomaly is not itself a command failure -- only a real
    error loading the ledger is)."""
    from frob.tickets import reconcile

    result = reconcile(
        root,
        apply=cfg.ticket_reconcile_apply,
        remove_orphans=cfg.ticket_reconcile_remove_orphans,
    )
    if result.is_err:
        _log.error("ticket reconcile failed: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    verb = "requeued" if report.applied else "would requeue"
    if report.requeued_tickets:
        _log.info(
            "reconcile: %s %d stale in-progress hold(s): %s",
            verb,
            len(report.requeued_tickets),
            list(report.requeued_tickets),
        )
    else:
        _log.info("reconcile: no stale in-progress holds found")

    if report.orphan_worktrees:
        removed_verb = "removed" if report.removed_orphans else "flagged (not removed)"
        _log.info(
            "reconcile: %s %d orphan worktree(s) (no lease): %s",
            removed_verb,
            len(report.orphan_worktrees),
            list(report.orphan_worktrees),
        )
    else:
        _log.info("reconcile: no orphan worktrees found")

    if report.orphaned_land_intents:
        intent_verb = "cleared" if report.applied else "would clear"
        _log.info(
            "reconcile: %s %d orphaned land intent(s) (crash/interrupt mid-land): %s",
            intent_verb,
            len(report.orphaned_land_intents),
            list(report.orphaned_land_intents),
        )
    else:
        _log.info("reconcile: no orphaned land intents found")


# frob:ticket T-0354
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_foreground_runs_sweep_synchronously  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_spawns_detached_sweep_subprocess  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_popen_failure_falls_back_to_synchronous_sweep  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_exec_kill_switch_forces_synchronous_sweep  # noqa: E501
def _run_sweep(root: Path, ticket) -> None:  # noqa: ANN001
    """Record the pre-work sweep (dup + xref + scope digest) for `ticket`.

    Delegates to `frob.gates.sweep_ticket` (T-0236's flagged follow-up,
    closed by T-0354): this call site used to carry its own copy of the
    xref loop with the same two bugs `sweep_ticket` fixed for T-0240 -- an
    unbounded `xref(symbol, root)` re-walk of the WHOLE tree per scope
    glob regardless of the per-pattern scan path, and a
    `Path(pattern).stem` guess that fed glob syntax (`"**"`, `"__init__"`)
    into xref as if it were a real symbol name. `src/frob/app/**` was out
    of scope for T-0240, so this copy kept both bugs live until now;
    delegating collapses the duplication instead of porting a second copy
    of the same fix.
    """
    from frob.gates import sweep_ticket

    swept = sweep_ticket(root, ticket)
    if swept.is_err:
        _log.error("pre-work sweep recording failed: %s", swept.danger_err)
        sys.exit(1)

    sweep = swept.danger_ok
    _log.info(
        "swept %s: dup_findings=%d xref_hits=%d",
        ticket.id,
        sweep.dup_findings,
        len(sweep.xref_hits),
    )


def _attach(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import AttachmentSource, attach

    if cfg.ticket_id is None:
        _log.error("frob ticket attach requires <id>")
        sys.exit(1)

    # No path means "read from clipboard" -- but a non-interactive agent
    # session has no clipboard to paste from, and would otherwise hang or
    # spawn a clipboard backend that can never produce an image (T-0098).
    if cfg.ticket_attach_path is None and not sys.stdin.isatty():
        _log.error(
            "frob ticket attach %s: no path given and stdin is not a TTY "
            "(non-interactive session cannot paste from the clipboard); "
            "pass an explicit file path: frob ticket attach %s <path>",
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    source = AttachmentSource(path=cfg.ticket_attach_path)
    result = attach(root, cfg.ticket_id, source, caption=cfg.ticket_caption)
    if result.is_err:
        _log.error("attach failed: %s", result.danger_err)
        sys.exit(1)
    attachment = result.danger_ok
    _log.info("attached %s (sha256=%s)", attachment.path, attachment.sha256)


# frob:ticket T-0081
def _block(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import _load_one
    from frob.tickets._store import write_ticket

    if cfg.ticket_id is None or cfg.ticket_by is None:
        _log.error("frob ticket block requires <id> and --by")
        sys.exit(1)

    loaded = _load_one(root, cfg.ticket_id)
    if loaded.is_err:
        _log.error("block failed: %s", loaded.danger_err)
        sys.exit(1)
    ticket = loaded.danger_ok
    updated = ticket.model_copy(
        update={"blocked_by": ticket.blocked_by + (cfg.ticket_by,)}
    )
    # frob:channel f_cli_tickets
    # design/frob.strata's `flow f_cli_tickets : cli -> tickets_ledger` --
    # this is one of the cli-layer write sites into the ticket ledger.
    written = write_ticket(root, updated)
    if written.is_err:
        _log.error("block failed: %s", written.danger_err)
        sys.exit(1)
    _log.info("%s now blocked by %s", cfg.ticket_id, cfg.ticket_by)


# frob:ticket T-0215
def _close_failure_hint(ticket_id: str, state, err) -> str:  # noqa: ANN001
    """The log message for a failed close: names a concrete remedy instead of
    just echoing the raw error (T-0215 -- both close-on-queued's
    InvalidTransition and MissingEvidence used to log with no next step)."""
    from frob.tickets import TicketError, TicketState

    if err == TicketError.InvalidTransition and state in (
        TicketState.QUEUED,
        TicketState.PLANNED,
    ):
        return (
            f"close failed: {err} -- {ticket_id} is {state.value}, not "
            f"in-progress -- run `frob ticket start {ticket_id}` first"
        )
    if err == TicketError.MissingEvidence:
        return (
            f"close failed: {err} -- {ticket_id} is missing evidence or a "
            f"Done report -- add evidence (`frob ticket evidence {ticket_id} "
            f"<node-id>...`, or for a docs-kind ticket `--evidence-cmd "
            f"'<command>'`) and write a '## Done report' heading under "
            f"{ticket_id}'s section in tickets.md"
        )
    return f"close failed: {err}"


# frob:ticket T-0398
def _graph_snapshot(root: Path):  # noqa: ANN201
    """The current `GraphSnapshot`, loading the cache (or building it fresh
    on a miss) -- same pattern as `_scope_digest_for_ticket`, factored so
    D-02's `covers_scope` computation shares it rather than re-deriving
    its own cache-then-build fallback."""
    from frob.graph import build_graph, load_graph

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        loaded = build_graph(root, cache)
    return loaded


# frob:ticket T-0398
def _covers_scope_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """D-02 CLI wiring: whether `ticket`'s evidence covers a touched/scope
    symbol, via `frob.gates.evidence_covers_scope` over the current graph.

    Returns `None` (skip the check entirely) when `ticket` carries NO
    non-cmd evidence at all -- a docs-kind ticket closed purely via
    `--evidence-cmd` has its own separate exit-code/digest verification
    channel (`add_cmd_evidence`) that already substitutes for "coverage";
    `evidence_covers_scope` would otherwise (correctly, by its own
    contract) return `False` for a ticket with zero non-cmd evidence to
    scan, which would wrongly block the docs cmd-evidence path this ticket
    was explicitly warned not to break. Also returns `None` when
    `ticket.scope` itself is empty -- an undeclared scope gives the
    binding check nothing to bind AGAINST, so "does evidence cover scope"
    is not a meaningful question to ask (this is a false-positive guard,
    not a loophole: a ticket that declares a real scope still gets the
    full check). Returns `False` (fail-closed, blocking the close) if the
    graph itself cannot be loaded/built -- "cannot verify" must never
    silently become "verified"."""
    from frob.gates import evidence_covers_scope
    from frob.tickets._models import is_cmd_evidence

    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    if not non_cmd or not ticket.scope:
        return None

    snapshot = _graph_snapshot(root)
    if snapshot.is_err:
        _log.warning(
            "ticket close: graph unavailable (%s), cannot verify D-02 "
            "scope-binding -- refusing to close on unverifiable evidence",
            snapshot.danger_err,
        )
        return False
    return evidence_covers_scope(ticket, snapshot.danger_ok)


# frob:ticket T-0106
# frob:ticket T-0215
# frob:ticket T-0398
def _close(root: Path, cfg: AppConfig) -> None:
    """Transition a ticket to done; if `--evidence` ids or `--evidence-cmd`
    were given, validate and append them first (`_apply_evidence` /
    `_apply_cmd_evidence`) and refuse to transition at all if either is
    unresolvable/fails, so a bad flag can never close a ticket on
    unvalidated evidence. A failed transition is reported through
    `_close_failure_hint` so the operator gets a concrete next command, not
    just the bare state-machine error (T-0215).

    T-0398: this is the CLI's STRICT default -- `covers_scope` is always
    computed (`_covers_scope_for_ticket`) and always passed to
    `transition`, so evidence that covers none of the ticket's touched/
    scope symbols rejects the close (`EvidenceScopeUnbound`) through the
    real `frob ticket close` command."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket close requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")

    if cfg.ticket_evidence_ids:
        added = _apply_evidence(root, cfg.ticket_id, cfg.ticket_evidence_ids)
        if added.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_added = _apply_cmd_evidence(root, cfg.ticket_id, cfg.ticket_evidence_cmd)
        if cmd_added.is_err:
            sys.exit(1)

    # Re-load: evidence may have just changed above, and covers_scope must
    # be computed against the ticket's CURRENT evidence, not the state
    # loaded before this call's own --evidence/--evidence-cmd applied.
    fresh_ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")
    covers_scope = _covers_scope_for_ticket(root, fresh_ticket)

    result = transition(
        root, cfg.ticket_id, TicketState.DONE, covers_scope=covers_scope
    )
    if result.is_err:
        _log.error(_close_failure_hint(cfg.ticket_id, ticket.state, result.danger_err))
        sys.exit(1)
    _log.info("%s closed (done)", cfg.ticket_id)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="done")


def _fail(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import FailureEntry, load_queue, record_failure

    if cfg.ticket_id is None or cfg.ticket_summary is None:
        _log.error("frob ticket fail requires <id> and --summary")
        sys.exit(1)

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("fail failed: %s", queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None:
        _log.error("no ticket %s", cfg.ticket_id)
        sys.exit(1)

    attempt = ticket.body.count("attempt ") + 1
    entry = FailureEntry(date=date.today(), attempt=attempt, summary=cfg.ticket_summary)
    result = record_failure(root, cfg.ticket_id, entry)
    if result.is_err:
        _log.error("fail failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s: recorded failure attempt %d", cfg.ticket_id, attempt)


# frob:ticket T-0579
def _drop(root: Path, cfg: AppConfig) -> None:
    """CLI wiring for `frob ticket drop <id> --reason TEXT [--absorbed-by
    T-####]` (T-0579): the first-class replacement for hand-editing
    `state: dropped` directly. Delegates entirely to `frob.tickets.
    drop_ticket` for the reason-line + transition + lease-release
    mechanics; this layer only validates required args and reports the
    Result."""
    from frob.tickets import drop_ticket

    if cfg.ticket_id is None or not cfg.ticket_reason:
        _log.error("frob ticket drop requires <id> and --reason")
        sys.exit(1)

    result = drop_ticket(
        root, cfg.ticket_id, cfg.ticket_reason, absorbed_by=cfg.ticket_absorbed_by
    )
    if result.is_err:
        _log.error("drop failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s dropped", cfg.ticket_id)


# frob:ticket T-0094
# frob:ticket T-0106
# frob:ticket T-0215
def _evidence(root: Path, cfg: AppConfig) -> None:
    """Validate `cfg.ticket_evidence_ids` against collected pytest node ids
    and append the resolvable ones to the ticket's structured evidence list;
    or, with `--evidence-cmd`, record the T-0215 non-pytest cmd-evidence
    entry instead (docs-kind tickets only). Requires at least one of the
    two -- neither is silently a no-op."""
    has_evidence = cfg.ticket_evidence_ids or cfg.ticket_evidence_cmd
    if cfg.ticket_id is None or not has_evidence:
        _log.error(
            "frob ticket evidence requires <id> and either <pytest-node-id>... "
            "or --evidence-cmd 'command'"
        )
        sys.exit(1)

    if cfg.ticket_evidence_ids:
        result = _apply_evidence(root, cfg.ticket_id, cfg.ticket_evidence_ids)
        if result.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_result = _apply_cmd_evidence(root, cfg.ticket_id, cfg.ticket_evidence_cmd)
        if cmd_result.is_err:
            sys.exit(1)


# frob:ticket T-0458
def _resolve_done_report_why(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket done-report`'s narrative why text: `--why-file`
    wins if given, else `--why` (a literal `-` or an omitted value both
    mean "read stdin", so `frob ticket done-report T-#### -` and a bare
    `frob ticket done-report T-####` piped a narrative both work). Exits 1
    on an unreadable `--why-file`; returns `None` only if reading stdin
    yields nothing meaningful for the caller to act on (never silently
    writes an empty report)."""
    if cfg.ticket_why_file is not None:
        try:
            return cfg.ticket_why_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "done-report: could not read --why-file %s: %s",
                cfg.ticket_why_file,
                exc,
            )
            sys.exit(1)
    if cfg.ticket_why is not None and cfg.ticket_why != "-":
        return cfg.ticket_why
    text = sys.stdin.read()
    return text or None


# frob:ticket T-0458
# frob:tests tests/test_tickets_evidence_cli.py::TestDoneReportCli.test_cli_composes_and_writes  # noqa: E501
def _done_report(root: Path, cfg: AppConfig) -> None:
    """`frob ticket done-report <id> (--why TEXT | --why-file PATH | -)`:
    resolve the narrative why, then call `frob.tickets.set_done_report` --
    the ONLY thing this command does is supply `why`; the Changed and
    Evidence sections are composed entirely inside `set_done_report` from
    git and the ticket's own recorded evidence, never parsed/typed here
    (T-0458)."""
    from frob.tickets import set_done_report

    if cfg.ticket_id is None:
        _log.error("frob ticket done-report requires <id>")
        sys.exit(1)

    why = _resolve_done_report_why(cfg)
    if why is None:
        _log.error(
            "frob ticket done-report requires --why TEXT, --why-file PATH, "
            "or a narrative piped via stdin"
        )
        sys.exit(1)

    result = set_done_report(root, cfg.ticket_id, why=why, base_ref=cfg.ticket_base_ref)
    if result.is_err:
        _log.error("done-report failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: Done report written (%d evidence id(s) rendered)",
        cfg.ticket_id,
        len(ticket.evidence),
    )


# frob:ticket T-0455
# frob:tests tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_free_path
# frob:tests tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_leased_path_exits_nonzero  # noqa: E501
def _scope(root: Path, cfg: AppConfig) -> None:
    """`frob ticket scope <id> --add GLOB... --remove GLOB... --reason TEXT`:
    the ONLY thing this command does is forward to
    `frob.tickets.mutate_scope` -- all lease-conflict/evidence-orphan
    validation lives there (T-0455), never re-derived here."""
    from frob.tickets import mutate_scope

    if cfg.ticket_id is None:
        _log.error("frob ticket scope requires <id>")
        sys.exit(1)
    if not cfg.ticket_scope_add and not cfg.ticket_scope_remove:
        _log.error("frob ticket scope requires --add and/or --remove GLOB")
        sys.exit(1)
    if not cfg.ticket_scope_reason:
        _log.error("frob ticket scope requires --reason TEXT")
        sys.exit(1)

    result = mutate_scope(
        root,
        cfg.ticket_id,
        add=cfg.ticket_scope_add,
        remove=cfg.ticket_scope_remove,
        reason=cfg.ticket_scope_reason,
    )
    if result.is_err:
        _log.error("scope change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: scope now %s (+%d/-%d this change)",
        cfg.ticket_id,
        list(ticket.scope),
        len(cfg.ticket_scope_add),
        len(cfg.ticket_scope_remove),
    )


# frob:ticket T-0411
def _priority(root: Path, cfg: AppConfig) -> None:
    """`frob ticket priority <id> <level>`: the ONLY thing this command does
    is forward to `frob.tickets.set_priority` -- no validation is re-derived
    here (T-0411, same pattern as `_scope`/T-0455)."""
    from frob.tickets import Priority, set_priority

    if cfg.ticket_id is None or cfg.ticket_priority_level is None:
        _log.error("frob ticket priority requires <id> <level>")
        sys.exit(1)

    result = set_priority(root, cfg.ticket_id, Priority(cfg.ticket_priority_level))
    if result.is_err:
        _log.error("priority change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: priority now %s", cfg.ticket_id, ticket.priority.value)


# frob:ticket T-0454
def _component(root: Path, cfg: AppConfig) -> None:
    """`frob ticket component <id> <name>`: forward to
    `frob.tickets.set_component` -- `name == "none"` clears the field back
    to uncategorized (T-0454, same pattern as `_priority`/`_scope`)."""
    from frob.tickets import set_component

    if cfg.ticket_id is None or cfg.ticket_component is None:
        _log.error("frob ticket component requires <id> <name>")
        sys.exit(1)

    value = None if cfg.ticket_component == "none" else cfg.ticket_component
    result = set_component(root, cfg.ticket_id, value)
    if result.is_err:
        _log.error("component change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: component now %s", cfg.ticket_id, ticket.component)


# frob:ticket T-0454
def _label(root: Path, cfg: AppConfig) -> None:
    """`frob ticket label <id> --add TAG... --remove TAG...`: forward to
    `frob.tickets.mutate_labels` -- all validation lives there (T-0454, same
    "this command does nothing but forward" pattern as `_scope`)."""
    from frob.tickets import mutate_labels

    if cfg.ticket_id is None:
        _log.error("frob ticket label requires <id>")
        sys.exit(1)
    if not cfg.ticket_label_add and not cfg.ticket_label_remove:
        _log.error("frob ticket label requires --add and/or --remove TAG")
        sys.exit(1)

    result = mutate_labels(
        root,
        cfg.ticket_id,
        add=cfg.ticket_label_add,
        remove=cfg.ticket_label_remove,
    )
    if result.is_err:
        _log.error("label change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: labels now %s (+%d/-%d this change)",
        cfg.ticket_id,
        list(ticket.labels),
        len(cfg.ticket_label_add),
        len(cfg.ticket_label_remove),
    )


# frob:ticket T-0454
def _board(root: Path, cfg: AppConfig) -> None:
    """`frob ticket board [--component NAME] [--label TAG] [--json]`:
    render `frob.tickets.board_view`'s fixed state columns, each
    priority-then-age ordered (T-0454)."""
    from frob.tickets import board_view, load_active

    result = load_active(root)
    if result.is_err:
        _log.error("ticket board failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    columns = board_view(
        queue, component=cfg.ticket_board_component, label=cfg.ticket_board_label
    )

    if cfg.ticket_json:
        import json

        payload = [
            {
                "state": col.state.value,
                "tickets": [t.model_dump(mode="json") for t in col.tickets],
            }
            for col in columns
        ]
        _log.info(json.dumps(payload, indent=2))
        return

    color = _stdout_color()
    for col in columns:
        _log.info("%s (%d)", style_state(col.state.value, color), len(col.tickets))
        if not col.tickets:
            continue
        for t in col.tickets:
            _log.info(
                "  %s  %s  (%s, %s)",
                style_ticket_id(t.id, color),
                t.title,
                t.priority.value,
                t.component or "uncategorized",
            )


# frob:ticket T-0454
def _epic(root: Path, cfg: AppConfig) -> None:
    """`frob ticket epic <id> [--json]`: render `frob.tickets.epic_rollup`'s
    subtree summary (T-0454)."""
    from frob.tickets import epic_rollup, load_active

    if cfg.ticket_id is None:
        _log.error("frob ticket epic requires <id>")
        sys.exit(1)
    result = load_active(root)
    if result.is_err:
        _log.error("ticket epic failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    rollup_result = epic_rollup(queue, cfg.ticket_id)
    if rollup_result.is_err:
        _log.error("ticket epic failed: %s", rollup_result.danger_err)
        sys.exit(1)
    rollup = rollup_result.danger_ok

    if cfg.ticket_json:
        import json

        payload = {
            "epic": rollup.epic.model_dump(mode="json"),
            "descendants": [t.model_dump(mode="json") for t in rollup.descendants],
            "done": rollup.done,
            "total": rollup.total,
            "percent_complete": rollup.percent_complete,
            "blocked_leaves": list(rollup.blocked_leaves),
        }
        _log.info(json.dumps(payload, indent=2))
        return

    color = _stdout_color()
    _log.info(
        "%s  %s  -- %d/%d done (%.0f%%)",
        style_ticket_id(rollup.epic.id, color),
        rollup.epic.title,
        rollup.done,
        rollup.total,
        rollup.percent_complete,
    )
    for t in rollup.descendants:
        _log.info(
            "  %s  [%s]  %s",
            style_ticket_id(t.id, color),
            style_state(t.state.value, color),
            t.title,
        )
    if rollup.blocked_leaves:
        _log.info("blocked leaves: %s", list(rollup.blocked_leaves))


# frob:ticket T-0398
def _collect_python_and_rust_ids(root: Path):  # noqa: ANN201
    """`(python_ids, rust_ids, runners)` -- the same union-collection dance
    `_apply_evidence` always did (T-0301), factored out so both evidence
    recording (D-01 pass-check) and `frob ticket land`'s post-merge
    re-verification (D-05) share one implementation. Returns `Err` only on
    a python collection failure (rust degrades to a WARNING + empty set,
    matching the existing resilience posture); `runners` is `()` if
    `load_runners` itself fails."""
    from frob.testing import collect_python_tests, collect_rust_tests, load_runners

    collected = collect_python_tests(root)
    if collected.is_err:
        return collected

    python_ids = frozenset(collected.danger_ok.node_ids)
    rust_ids: frozenset[str] = frozenset()

    runners = load_runners(root)
    runner_specs = runners.danger_ok if runners.is_ok else ()
    if any(spec.language == "rust" for spec in runner_specs):
        rust_collected = collect_rust_tests(root)
        if rust_collected.is_err:
            _log.warning(
                "ticket evidence: rust collection failed (%s); validating "
                "against pytest ids only for this call",
                rust_collected.danger_err,
            )
        else:
            rust_ids = frozenset(rust_collected.danger_ok.node_ids)

    from typani.result import Ok

    return Ok((python_ids, rust_ids, runner_specs))


# frob:ticket T-0398
def _verify_ids_passing(
    root: Path,
    node_ids,  # noqa: ANN001
    python_collected: frozenset[str],
    rust_collected: frozenset[str],
    runners,  # noqa: ANN001
) -> frozenset[str]:
    """D-01 CLI wiring: actually RUN `node_ids` (bucketed by which
    collected set each id resolves against, python vs rust) and return the
    subset that passed -- the piece that makes `frob ticket evidence`/
    `close`/`land` mean "the work was actually tested," not just "a test
    with this name exists."

    Each language bucket is run as its OWN `run_selected` call, not one
    combined invocation, for two reasons: (1) a combined run's single exit
    code cannot tell you WHICH of several ids failed, so a batch mixing a
    red and a green id would have to reject both -- overly strict for no
    reason; per-language buckets are the coarsest split that still lets
    genuinely-independent ids pass independently. (2) an infra failure in
    one language (e.g. no PyO3 env for rust) must not silently swallow a
    python id's real, successful verification -- each bucket's own
    Err/failure is logged and only THAT bucket's ids are withheld from the
    returned passing set, never the whole call. An id that resolves
    against neither collected set is simply absent from the result (it
    already fails resolution elsewhere; this function only concerns
    itself with ids that at least exist)."""
    from frob.tickets._models import matches_collected

    passing: set[str] = set()
    buckets = {
        "python": tuple(n for n in node_ids if matches_collected(n, python_collected)),
        "rust": tuple(n for n in node_ids if matches_collected(n, rust_collected)),
    }
    for language, items in buckets.items():
        if items:
            passing.update(_verify_one_bucket_passing(root, language, items, runners))
    return frozenset(passing)


# frob:ticket T-0398
def _verify_one_bucket_passing(
    root: Path,
    language: str,
    items: tuple[str, ...],
    runners,  # noqa: ANN001
) -> frozenset[str]:
    """One language bucket of `_verify_ids_passing`'s work: run `items`
    via `run_selected` and return the subset (all-or-nothing per bucket,
    see `_verify_ids_passing`'s docstring) that passed. Falls back to a
    direct `pytest <ids>` invocation for python when no `[[test.runner]]`
    is declared at all -- `frob.toml` is optional, so a repo that never
    configured one must not fall straight to "not passing" (a false-
    positive trap this fix was explicitly warned against)."""
    from frob.testing import SelectionReport, TestingError, run_selected

    selection = SelectionReport(
        touched=(),
        selected={language: items},
        ripple=(),
        unbound=(),
        fallback="evidence-verify",
    )
    run = run_selected(selection, runners, root)
    if run.is_ok and run.danger_ok.ok:
        return frozenset(items)
    if run.is_err and language == "python" and run.danger_err == TestingError.NoRunner:
        if _run_pytest_directly(root, items):
            return frozenset(items)
        _log.warning(
            "ticket evidence: direct pytest verification FAILED for %s", list(items)
        )
        return frozenset()
    _log.warning(
        "ticket evidence: %s verification %s for %s",
        language,
        f"run failed to execute ({run.danger_err})" if run.is_err else "run FAILED",
        list(items),
    )
    return frozenset()


# frob:ticket T-0398
def _run_pytest_directly(root: Path, node_ids) -> bool:  # noqa: ANN001
    """`uv run pytest <node_ids> -q -o addopts=` in `root`, exit 0 == pass
    -- the no-`[[test.runner]]`-declared fallback `_verify_ids_passing`
    uses so D-01 verification works even in a repo that never configured
    `frob.toml`'s test-runner registry (the same posture
    `collect_python_tests` already takes for collection)."""
    from frob.gitio import run_argv

    argv = ("uv", "run", "pytest", *node_ids, "-q", "-o", "addopts=")
    spawned = run_argv(argv, cwd=root, timeout_s=300.0)
    if spawned.is_err:
        _log.warning("ticket evidence: direct pytest failed to spawn in %s", root)
        return False
    return spawned.danger_ok.returncode == 0


# frob:ticket T-0106
# frob:ticket T-0398
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_evidence(root: Path, ticket_id: str, node_ids: list[str]):
    """Collect pytest node ids, validate `node_ids` against them AND
    actually run them (D-01: `passed`) via `frob.tickets.add_evidence`
    (resolvable-id + passing + dedupe semantics, wholesale batch rejection
    on any unresolvable OR non-passing id), and append the resolvable
    passing ones to `ticket_id`'s structured evidence list. Shared by
    `frob ticket evidence`, `frob ticket new --evidence`, and `frob ticket
    close --evidence` so all three routes go through identical validation
    -- never through an ad hoc, unvalidated write. Returns the
    `add_evidence` Result unchanged so callers (e.g. `_close`) can refuse
    to transition state on failure.

    T-0301 (feldspar T-0015 escalation): a `--evidence` id must resolve
    against the union of every collected oracle the repo's `[[test.runner]]`
    entries declare, not pytest alone -- a rust node id IS collected (via
    `collect_rust_tests`, into `.frob/cargo-collect.json`) whenever
    `frob.toml` declares a `language = "rust"` runner, so it must be part of
    the same oracle set pytest ids validate against. Rust collection is
    attempted only when a rust runner is actually configured (repos with no
    rust runner never pay a `cargo` invocation here), and a rust-collection
    failure degrades to a WARNING plus python-only validation rather than
    blocking evidence recording outright -- an unrelated cargo/pyo3
    environment problem must not stop a purely-python ticket's evidence
    from being recorded (same resilience posture as T-0144's `make core`
    guidance elsewhere in this module).

    T-0398: this is the CLI's STRICT default -- `passed` is always
    computed and always passed to `add_evidence`, so a red/errored/
    skipped evidence test rejects the whole batch (`EvidenceNotPassing`)
    through the real `frob ticket evidence`/`close` commands, not just the
    library function a caller could otherwise bypass by never supplying
    `passed`.

    T-0492: `node_ids` is normalized (`normalize_evidence_separator`, the
    SAME dot-to-`::` rewrite `add_evidence`'s own `_validate_evidence_list`
    applies, T-0293) BEFORE it is handed to `_verify_ids_passing` here --
    not after. `_verify_ids_passing` buckets ids via `matches_collected`
    against `python_ids`/`rust_ids`, which only ever contain pytest's
    native `::`-form node ids; a raw dot-form id (`path::Class.method`,
    the canonical spelling this module's own docs teach) never matches
    either bucket, so its "did it pass" check silently runs on an empty
    selection and the id ends up absent from `passing` -- rejected
    downstream as `EvidenceNotPassing` even though the test genuinely
    passed. Passing the SAME normalized list into both the passing-check
    and `add_evidence` keeps the two normalization paths from silently
    diverging again."""
    from frob.tickets import add_evidence, normalize_evidence_separator

    collected = _collect_python_and_rust_ids(root)
    if collected.is_err:
        _log.error(
            "ticket evidence: pytest collection failed: %s", collected.danger_err
        )
        return collected
    python_ids, rust_ids, runners = collected.danger_ok
    collected_ids = python_ids | rust_ids

    normalized_ids = [normalize_evidence_separator(n) for n in node_ids]
    passing = _verify_ids_passing(root, normalized_ids, python_ids, rust_ids, runners)

    result = add_evidence(
        root, ticket_id, normalized_ids, collected_ids, passed=passing
    )
    _log_evidence_result(ticket_id, result)
    return result


def _log_evidence_result(ticket_id: str, result) -> None:  # noqa: ANN001
    """Log `add_evidence`'s outcome: the failure reason + remedy, or the
    ticket's resulting evidence id count."""
    if result.is_err:
        _log.error(
            "ticket evidence failed: %s (the collection cache self-refreshes "
            "on the next `frob test` / `frob check` run; if it still does "
            "not resolve, delete .frob/pytest-collect.json (or "
            ".frob/cargo-collect.json for rust) to force a rebuild, or fix "
            "the id)",
            result.danger_err,
        )
        return

    ticket = result.danger_ok
    _log.info(
        "%s: evidence now has %d id(s): %s",
        ticket_id,
        len(ticket.evidence),
        list(ticket.evidence),
    )


# frob:ticket T-0215
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_cmd_evidence(root: Path, ticket_id: str, command: str):
    """Run `command` via `frob.tickets.add_cmd_evidence` and append its
    exit-status/digest entry to `ticket_id`'s evidence list -- the
    docs/design-kind non-pytest evidence channel (T-0215). Returns the
    `add_cmd_evidence` Result unchanged so callers (`_close`, `_evidence`)
    can refuse to transition state on failure, the same contract
    `_apply_evidence` gives pytest-node-id evidence."""
    from frob.tickets import add_cmd_evidence

    result = add_cmd_evidence(root, ticket_id, command)
    if result.is_err:
        _log.error(
            "ticket evidence-cmd failed: %s (docs-kind tickets only; code "
            "kinds require pytest --evidence node ids)",
            result.danger_err,
        )
        return result

    ticket = result.danger_ok
    _log.info(
        "%s: evidence now has %d entries: %s",
        ticket_id,
        len(ticket.evidence),
        list(ticket.evidence),
    )
    return result


# frob:ticket T-0096
def _archive(root: Path) -> None:
    """Move every done/dropped ticket from the active ledger into
    tickets-archive.md, verbatim (idempotent -- a second run finds nothing
    to move)."""
    from frob.tickets import archive

    result = archive(root)
    if result.is_err:
        _log.error("ticket archive failed: %s", result.danger_err)
        sys.exit(1)
    n = result.danger_ok
    if n == 0:
        _log.info("nothing to archive")
    else:
        _log.info("archived %d ticket(s) into tickets-archive.md", n)
