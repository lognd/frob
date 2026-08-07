"""CLI wiring for `frob ticket new|list|show|doable|board|epic|brief|plan|
start|requeue|sweep|reconcile|land|merge-driver|attach|block|close|fail|
drop|evidence|done-report|scope|priority|kind|component|label|archive|
review|sprint|tier` (docs/modules/tickets.md).

T-1089 (T-0395 tier-2 split residue): the command families now live in
private sibling modules (`_new`, `_query`, `_land_cmd`, `_lifecycle`,
`_close_cmd`, `_verify`, `_mutate`, `_archive`) and are re-exported here
unchanged -- every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, and tests that `monkeypatch.setattr(ticket_runner, ...)`) keeps
working without edits. `_root_release_manifest` and `_graph_snapshot`
stay defined HERE (not in the submodule that most often calls them) because
tests monkeypatch them via `ticket_runner.<name>` and expect that patch to
be visible to callers in OTHER split-out modules; those callers reach back
through `from frob.app import ticket_runner as _ticket_runner` at their own
call sites instead of a direct import, so the patched attribute on THIS
module is what they actually observe (same reasoning for
`guarded_subprocess_run`, re-exported below unchanged from
`frob.process._guard`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger, logger_levels
from frob.process._guard import guarded_subprocess_run

from ._archive import _archive
from ._close_cmd import (
    _apply_close_time_evidence,
    _close,
    _close_failure_hint,
    _close_gate_claims_for_ticket,
    _close_guards_for_ticket,
    _close_mutation_evidence_for_ticket,
    _close_own_obligations_for_ticket,
    _covers_review_for_ticket,
    _covers_scope_for_ticket,
    _current_commit,
    _drop,
    _fail,
    _reverify,
    _reverify_evidence_for_close,
    _review,
)
from ._land_cmd import (
    _apply_release_bump_for_land,
    _land,
    _land_bump_version_fn,
    _land_collected_fn,
    _land_covers_scope_fn,
    _land_gate_claims_fn,
    _land_passed_fn,
    _land_rebuild_natives_fn,
    _land_sync_gate_rules_fn,
    _merge_driver,
    _push_after_land,
    _report_land_result,
    _require_land_args,
    _require_merge_driver_args,
    _required_release_bump,
    _sync_gate_rules_for_land,
    _write_release_bump,
)
from ._lifecycle import (
    _attach,
    _auto_plan_if_queued,
    _block,
    _find_landing_commit,
    _load_ticket_or_exit,
    _plan,
    _reconcile_cmd,
    _refuse_if_foreign_live_lease,
    _refuse_if_terminal,
    _requeue,
    _run_sweep,
    _spawn_background_sweep,
    _start,
    _sweep_cmd,
    _work,
)
from ._mutate import (
    _accept,
    _board,
    _brief,
    _component,
    _epic,
    _flow,
    _kind,
    _label,
    _priority,
    _resolve_scope_reason,
    _scope,
    _scope_ack,
    _sprint,
    _sprint_assign,
    _sprint_show,
    _tier,
)
from ._new import (
    _maybe_attach_clipboard_image,
    _new,
    _parse_acceptance_file,
    _resolve_new_acceptance,
    _resolve_new_body,
    _scope_closure_warnings,
    _ticket_spec_from_cfg,
)
from ._query import (
    _active_large_glob_warnings,
    _doable,
    _doable_row,
    _filter_by_state,
    _list,
    _migrate,
    _order_dispatchable_with_alarms,
    _promote,
    _render_acceptance,
    _render_active_leases,
    _render_doable_dispatchable,
    _render_doable_in_flight,
    _render_doable_show_blocked,
    _render_scope_breadth_summary,
    _renumber,
    _renumber_one,
    _show,
)
from ._rapid_sweep import _sweep_async
from ._verify import (
    _apply_cmd_evidence,
    _apply_evidence,
    _check_gate_findings_fn,
    _check_gates_summary_fn,
    _collect_python_and_rust_ids,
    _done_report,
    _evidence,
    _exclude_scoped_run_flaky,
    _log_evidence_result,
    _parse_error_findings_from_stdout,
    _python_for_tree,
    _resolve_done_report_why,
    _reverify_direct_pytest_individually,
    _reverify_failing_bucket_individually,
    _run_pytest_directly,
    _run_tests_count_fn,
    _shared_check_spawn_fn,
    _verify_ids_passing,
    _verify_one_bucket_passing,
)

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


# Re-exported for tests/callers that reach into ticket_runner internals
# directly (pre-existing usage this split (T-1089) preserves unchanged --
# zero caller edits, per the T-1072/T-1076/T-1086 precedent).
__all__ = [
    "guarded_subprocess_run",
    "_accept",
    "_active_large_glob_warnings",
    "_apply_close_time_evidence",
    "_apply_cmd_evidence",
    "_apply_evidence",
    "_apply_release_bump_for_land",
    "_attach",
    "_flow",
    "_auto_plan_if_queued",
    "_block",
    "_board",
    "_brief",
    "_check_gate_findings_fn",
    "_check_gates_summary_fn",
    "_close",
    "_close_failure_hint",
    "_close_gate_claims_for_ticket",
    "_close_guards_for_ticket",
    "_close_mutation_evidence_for_ticket",
    "_close_own_obligations_for_ticket",
    "_collect_python_and_rust_ids",
    "_component",
    "_covers_review_for_ticket",
    "_covers_scope_for_ticket",
    "_current_commit",
    "_doable",
    "_doable_row",
    "_done_report",
    "_drop",
    "_epic",
    "_evidence",
    "_exclude_scoped_run_flaky",
    "_fail",
    "_filter_by_state",
    "_find_landing_commit",
    "_kind",
    "_label",
    "_land",
    "_land_bump_version_fn",
    "_land_collected_fn",
    "_land_covers_scope_fn",
    "_land_gate_claims_fn",
    "_land_passed_fn",
    "_land_rebuild_natives_fn",
    "_land_sync_gate_rules_fn",
    "_list",
    "_load_ticket_or_exit",
    "_log_evidence_result",
    "_maybe_attach_clipboard_image",
    "_merge_driver",
    "_migrate",
    "_new",
    "_order_dispatchable_with_alarms",
    "_parse_acceptance_file",
    "_parse_error_findings_from_stdout",
    "_plan",
    "_priority",
    "_promote",
    "_push_after_land",
    "_python_for_tree",
    "_reconcile_cmd",
    "_refuse_if_foreign_live_lease",
    "_refuse_if_terminal",
    "_render_acceptance",
    "_render_active_leases",
    "_render_doable_dispatchable",
    "_render_doable_in_flight",
    "_render_doable_show_blocked",
    "_render_scope_breadth_summary",
    "_renumber",
    "_renumber_one",
    "_report_land_result",
    "_requeue",
    "_require_land_args",
    "_require_merge_driver_args",
    "_required_release_bump",
    "_resolve_done_report_why",
    "_resolve_new_acceptance",
    "_resolve_new_body",
    "_resolve_scope_reason",
    "_reverify",
    "_reverify_direct_pytest_individually",
    "_reverify_evidence_for_close",
    "_reverify_failing_bucket_individually",
    "_review",
    "_run_pytest_directly",
    "_run_sweep",
    "_run_tests_count_fn",
    "_scope",
    "_scope_ack",
    "_scope_closure_warnings",
    "_shared_check_spawn_fn",
    "_show",
    "_spawn_background_sweep",
    "_sprint",
    "_sprint_assign",
    "_sprint_show",
    "_start",
    "_sweep_cmd",
    "_sync_gate_rules_for_land",
    "_ticket_spec_from_cfg",
    "_tier",
    "_verify_ids_passing",
    "_verify_one_bucket_passing",
    "_work",
    "_write_release_bump",
]


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
        "work": _work,
        "requeue": _requeue,
        "sweep": _sweep_cmd,
        # frob:ticket T-1684
        "sweep-async": _sweep_async,
        "reconcile": _reconcile_cmd,
        "migrate": lambda root, cfg: _migrate(root, to=cfg.ticket_migrate_to),
        "renumber": _renumber,
        # frob:ticket T-1637
        "promote": _promote,
        "land": _land,
        "merge-driver": _merge_driver,
        "attach": _attach,
        "block": _block,
        "close": _close,
        # frob:ticket T-1005
        "reverify": _reverify,
        "fail": _fail,
        "drop": _drop,
        "evidence": _evidence,
        "done-report": _done_report,
        "review": _review,
        "scope": _scope,
        # frob:ticket T-1484
        "scope-ack": _scope_ack,
        "priority": _priority,
        "kind": _kind,
        "component": _component,
        "label": _label,
        # frob:ticket T-1029
        "accept": _accept,
        "board": _board,
        "epic": _epic,
        "brief": _brief,
        # frob:ticket T-1100
        "flow": _flow,
        # frob:ticket T-0715
        "sprint": _sprint,
        # frob:ticket T-1069
        "tier": _tier,
        "archive": lambda root, cfg: _archive(
            root,
            force=cfg.ticket_force,
            no_commit=cfg.ticket_no_commit,
            force_reason=cfg.ticket_force_reason,
            force_reason_file=cfg.ticket_force_reason_file,
        ),
    }


# frob:ticket T-1615
# Verbs excluded from `_auto_commit_ledger_after_dispatch`'s uniform
# post-dispatch sweep because they own a commit sequence this generic,
# `tickets.md`/`tickets/<id>`-pathspec-limited sweep would corrupt rather
# than help:
#   - "land"/"merge-driver" own a multi-file transaction end to end
#     (squash-merging a whole worktree branch onto main) -- a stray
#     ledger-only commit spliced in from outside would split what must
#     land as one atomic change into two.
#   - "promote"/"renumber" rewrite a ticket id across MANY tracked files
#     (every `frob:ticket`/`frob:tests`/... directive referencing it, not
#     just the ledger) in one operation -- committing only the ledger
#     half here would leave the rest of that same rename uncommitted,
#     which is a worse state than leaving all of it uncommitted together
#     for the caller to commit as one change.
#   - "sweep-async" is T-1699's territory: a DETACHED child process
#     racing the land lock outside the caller's own commit window --
#     T-1699 owns getting that interaction right, not this sweep.
# Every OTHER verb in `_ticket_dispatch_table()` -- including any verb
# added to it later -- is covered automatically with no per-verb code
# required, because the sweep wraps the single dispatch call site below
# rather than being copied into each handler; the dirtiness check inside
# `commit_ticket_ledger_change` also means this never fires for a verb
# that touched nothing (every read-only verb, or a `--worktree`-scoped
# verb like `work`/`land` that never dirties `root`'s OWN ledger file).
_LEDGER_TRANSACTIONAL_VERBS = frozenset(
    {"land", "merge-driver", "promote", "renumber", "sweep-async"}
)


# frob:ticket T-1615
def _auto_commit_ledger_after_dispatch(
    root: Path, cfg: AppConfig, command: str | None
) -> None:
    """After `run()`'s dispatch call returns (normally or via a verb's own
    `sys.exit`), commit whatever ledger residue that verb's write left
    dirty (T-1615).

    Root cause this closes: `frob ticket new`/`drop`/`fail`/`done-report`/
    `evidence`/`close`/`start`/`requeue` already call
    `commit_ticket_ledger_change` themselves (T-1130/T-1178) -- for those,
    this call is a documented no-op (`_tickets_md_dirty` is already
    `False` by the time it runs here). `block`/`scope`/`scope-ack`/
    `priority`/`kind`/`component`/`label`/`accept`/`tier`/`attach` never
    called it at all, leaving `tickets.md` dirty on every invocation --
    the exact 2026-08-06 incident (two `frob ticket block` calls left a
    two-blank-line, zero-semantic-change residue that DirtyMain-refused
    every concurrent `frob ticket land` in the repo).

    Deliberately a wrapper around the ONE dispatch call site in `run()`,
    not a commit call added to each individual verb handler: a verb
    added to `_ticket_dispatch_table()` in the future is covered the
    instant it is added, with nothing new to remember per verb -- the
    same class of gap this ticket exists to close cannot reopen here.
    `_LEDGER_TRANSACTIONAL_VERBS` (`land`/`merge-driver`) is the only
    exclusion, because both own their own complete multi-file commit
    sequence and must never have a stray single-file `tickets.md` commit
    spliced into it from outside.

    Best-effort against `cfg.ticket_id is None`: every read-only verb
    (`list`/`show`/`doable`/`board`/`epic`/`brief`/`flow`/`sprint show`/
    ...) either never sets it or never dirties the ledger either way, so
    there is nothing to resolve a commit pathspec against."""
    if command in _LEDGER_TRANSACTIONAL_VERBS:
        return
    if cfg.ticket_id is None:
        return
    from frob.tickets._leases import commit_ticket_ledger_change

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): {command} {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        _log.error(
            "ticket %s: ledger auto-commit failed for %s: %s",
            command,
            cfg.ticket_id,
            committed.danger_err,
        )
        sys.exit(1)


# frob:doc docs/modules/app.md#runners
# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#reg010-gate-rule-staleness-t-0560  # noqa: E501
# frob:doc docs/modules/tickets.md#frob-ticket-land
# frob:doc docs/modules/tickets.md#structured-review-channel-t-0571
# frob:doc docs/modules/tickets.md#every-ledger-writing-verb-auto-commits-uniformly-t-1615  # noqa: E501
# frob:ticket T-0588
# frob:ticket T-1029
# frob:ticket T-1100
# frob:ticket T-1615
# frob:waive AFFECT001 reason="T-1029 added a new SUBCOMMAND (accept) to the dispatch \
# table -- REG010-gate-rule-staleness-t-0560 is about a live GATE RULE id drifting out \
# of the registry's own count, an orthogonal concern this change never touches; \
# docs/modules/app.md#runners and #config (the docs this change IS actually about) \
# were updated in the same diff"
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch.test_unknown_command_exits_1  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Dispatch to the ticket subcommand named by `cfg.ticket_command`."""
    root = (cfg.ticket_path or Path(".")).resolve()

    handler = _ticket_dispatch_table().get(cfg.ticket_command)
    if handler is None:
        _log.error(
            "usage: frob ticket <new|list|show|doable|board|epic|brief|plan|"
            "start|requeue|sweep|reconcile|land|merge-driver|attach|block|"
            "close|fail|drop|evidence|done-report|scope|priority|kind|"
            "component|label|accept|flow|archive|review|sprint|tier> ..."
        )
        sys.exit(1)
    with _diagnostic_log_ctx(cfg):
        try:
            handler(root, cfg)
        finally:
            _auto_commit_ledger_after_dispatch(root, cfg, cfg.ticket_command)


# frob:ticket T-0768
def _diagnostic_log_ctx(cfg: AppConfig):  # noqa: ANN202
    """The logger context `run` dispatches every subcommand under (T-0768).

    At default verbosity the `frob` logger tree is clamped to WARNING so
    library diagnostic chatter (`frob.gitio` spawn/returncode lines, the
    `frob.tickets` loader's per-run INFO) stays out of the terminal, while
    this module's own logger -- the ticket CLI's user-facing output channel
    -- is pinned to INFO so listings still print. `-v` skips the clamp and
    restores the full firehose. WARNING+ lines (stale leases, over-broad
    scopes) always show either way.
    """
    import contextlib
    import logging

    if cfg.ticket_verbose > 0:
        return contextlib.nullcontext()
    return logger_levels({"frob": logging.WARNING, __name__: logging.INFO})


# frob:ticket T-0737


# frob:ticket T-0338
# frob:ticket T-1007
def _root_release_manifest(root: Path):  # noqa: ANN201
    """Read `.frob-release.json` as it stood at `root`'s CURRENT git HEAD
    (T-1007/T-1009) -- never the worktree-carried on-disk copy, which can
    ride a `git merge --squash` straight into `root`'s working tree before
    this callback ever runs (the exact corruption class T-0992's
    `_read_root_pyproject_version` fixed for `pyproject.toml`; same git-show
    technique, applied here to the manifest that is now the version
    authority). `land()` invokes the bump callback AFTER the squash-apply
    is staged but BEFORE any commit, so `root`'s `HEAD` here still names
    main's true pre-land tip -- reading through git makes the monotonicity
    guard in `frob.tickets._land._apply_release_bump` a never-fires
    invariant instead of a per-land speed bump, since this callback can no
    longer compute a bump baseline from anything but root's own state.
    Returns `None` when no manifest exists at `HEAD` (repo never adopted
    `frob release stamp`) or it fails to parse."""
    from frob.gitio import run_argv
    from frob.release import ReleaseManifest

    shown = run_argv(["git", "-C", str(root), "show", "HEAD:.frob-release.json"])
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    try:
        data = json.loads(shown.danger_ok.stdout)
        return ReleaseManifest.model_validate(data)
    except (ValueError, TypeError) as exc:
        _log.error("land: HEAD:.frob-release.json at %s unparsable: %s", root, exc)
        return None


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
