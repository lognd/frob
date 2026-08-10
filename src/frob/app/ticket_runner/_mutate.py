"""frob.app.ticket_runner._mutate -- the `scope`/`scope-ack`/`priority`/
`kind`/`component`/`label`/`accept`/`board`/`epic`/`tier`/`sprint`/`brief`/
`flow` mutation command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app._style import style_state, style_ticket_id
from frob.app.config import AppConfig
from frob.logging import get_logger

from ._new import _scope_closure_warnings

_log = get_logger("frob.app.ticket_runner")


# frob:ticket T-1317
# frob:doc docs/modules/gates.md#ack-accountability-t-1317
# frob:tests tests/test_gates_drift_ack.py::TestAckAccountability.test_ack_cli_reason_file_reads_verbatim  # noqa: E501
def read_reason_file_verbatim(path: Path, *, cli_label: str) -> str:
    """Read a `--reason-file PATH` argument's contents verbatim (T-0737's
    shell-injection-avoidance precedent), or `sys.exit(1)` with `cli_label`
    named in the error. Shared here (this module already declares the
    `cli` node's `fs.read` capability, T-0455) rather than duplicated as a
    second capability-declaration site per caller -- `frob.app.ack_runner`
    (T-1317's `frob ack --reason-file`) is the first cross-module reuse."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error("%s: could not read --reason-file %s: %s", cli_label, path, exc)
        sys.exit(1)


def _resolve_scope_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket scope`'s `--reason`: `--reason-file` wins if
    given (read verbatim -- T-0737, same rationale as `_resolve_new_body`),
    else the inline `--reason` string. Exits 1 if both are given; returns
    `None` if neither is given (the caller reports the "one is required"
    error, matching `_resolve_done_report_why`'s shape)."""
    if cfg.ticket_scope_reason_file is not None and cfg.ticket_scope_reason:
        _log.error(
            "frob ticket scope: --reason and --reason-file are mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_scope_reason_file is not None:
        try:
            return cfg.ticket_scope_reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket scope: could not read --reason-file %s: %s",
                cfg.ticket_scope_reason_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_scope_reason


# frob:ticket T-0455
# frob:ticket T-0737
# frob:tests tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_free_path
# frob:tests tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_leased_path_exits_nonzero  # noqa: E501
def _scope(root: Path, cfg: AppConfig) -> None:
    """`frob ticket scope <id> --add GLOB... --remove GLOB... (--reason
    TEXT | --reason-file PATH)`: the ONLY thing this command does is
    resolve the reason (`_resolve_scope_reason`, T-0737) and forward to
    `frob.tickets.mutate_scope` -- all lease-conflict/evidence-orphan
    validation lives there (T-0455), never re-derived here."""
    from frob.tickets import mutate_scope

    if cfg.ticket_id is None:
        _log.error("frob ticket scope requires <id>")
        sys.exit(1)
    if not cfg.ticket_scope_add and not cfg.ticket_scope_remove:
        _log.error("frob ticket scope requires --add and/or --remove GLOB")
        sys.exit(1)

    reason = _resolve_scope_reason(cfg)
    if not reason:
        _log.error("frob ticket scope requires --reason TEXT or --reason-file PATH")
        sys.exit(1)

    result = mutate_scope(
        root,
        cfg.ticket_id,
        add=cfg.ticket_scope_add,
        remove=cfg.ticket_scope_remove,
        reason=reason,
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
    # frob:ticket T-1855
    for glob in cfg.ticket_scope_remove:
        still_covered = _still_implicitly_covered(glob, ticket)
        if still_covered is not None:
            _log.warning(
                "ticket scope %s: --remove %r reported success, but the "
                "effective scope did NOT change -- %r is still covered "
                "implicitly (%s); only an explicit scope change is "
                "observable here, this removal was not",
                ticket.id,
                glob,
                glob,
                still_covered,
            )
    # frob:ticket T-0998
    for warning in _scope_closure_warnings(root, ticket.scope):
        _log.warning("ticket scope %s: scope closure: %s", ticket.id, warning)


# frob:ticket T-1855
def _still_implicitly_covered(glob: str, ticket) -> str | None:  # noqa: ANN001
    """Whether a just-`--remove`d `glob` is STILL covered by one of
    `ticket`'s implicit (kind-based or always-on) scope grants -- the
    reason string naming which rule, or `None` if the removal genuinely
    freed the path (T-1855 item 4). This is the concrete incident this
    ticket exists to fix: a coordinator ran `scope --remove` on a path
    still covered by the FEATURE-kind CLI-wiring grant
    (`CLI_WIRING_FILES`, T-0446/T-1848), the command reported SUCCESS,
    and the effective scope had not actually changed -- an agent was then
    told the path was free when it was not. `_globs_intersect` (T-0453)
    is the existing sound glob-vs-glob overlap test; reused here rather
    than re-derived, since a removed entry can itself be a glob, not just
    a literal path."""
    from frob.tickets._models import (
        CLI_WIRING_FILES,
        LEDGER_PATH,
        TicketKind,
        _globs_intersect,
    )

    if _globs_intersect(glob, LEDGER_PATH):
        return "the ledger is always in scope, T-0241"
    if _globs_intersect(glob, f"tickets/{ticket.id}/**"):
        return "a ticket's own tickets/<id>/ shard is always in scope, T-1819"
    if ticket.kind is TicketKind.FEATURE:
        for wiring_path in CLI_WIRING_FILES:
            if _globs_intersect(glob, wiring_path):
                return (
                    f"the FEATURE-kind CLI-wiring grant still covers "
                    f"{wiring_path!r}, T-0446/T-1848"
                )
    return None


# frob:ticket T-1484
# frob:tests \
# tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck.test_ack_sets_both_fields
def _scope_ack(root: Path, cfg: AppConfig) -> None:
    """`frob ticket scope-ack <id> (--reason TEXT | --reason-file PATH)`:
    the honest TICK009 acknowledged-broad channel (WAVE14-B) -- forwards to
    `frob.tickets.set_scope_breadth_ack`, reusing `_resolve_scope_reason`'s
    `--reason`/`--reason-file` resolution (same mutual-exclusivity/required
    -ness rules `scope` already enforces, T-0737)."""
    from frob.tickets import set_scope_breadth_ack

    if cfg.ticket_id is None:
        _log.error("frob ticket scope-ack requires <id>")
        sys.exit(1)

    reason = _resolve_scope_reason(cfg)
    if not reason:
        _log.error("frob ticket scope-ack requires --reason TEXT or --reason-file PATH")
        sys.exit(1)

    result = set_scope_breadth_ack(root, cfg.ticket_id, reason)
    if result.is_err:
        _log.error("scope-ack failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: scope_breadth_ack now True (TICK009 exempt) -- %s",
        cfg.ticket_id,
        ticket.scope_breadth_ack_reason,
    )


# frob:ticket T-1867
def _resolve_anchor_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket anchor`'s `--reason`: `--reason-file` wins if
    given (read verbatim, T-0737 pattern), else the inline `--reason`
    string. Exits 1 if both are given; returns `None` if neither is given
    (the caller reports the "one is required" error)."""
    if cfg.ticket_anchor_reason_file is not None and cfg.ticket_anchor_reason:
        _log.error(
            "frob ticket anchor: --reason and --reason-file are mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_anchor_reason_file is not None:
        try:
            return cfg.ticket_anchor_reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket anchor: could not read --reason-file %s: %s",
                cfg.ticket_anchor_reason_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_anchor_reason


# frob:ticket T-1867
# frob:tests \
# tests/unit/test_ticket_anchor_cli.py::TestAnchorCli::test_set_anchor_via_cli
# frob:tests \
# tests/unit/test_ticket_anchor_cli.py::TestAnchorCli::test_clear_anchor_via_cli
# frob:tests tests/unit/test_ticket_anchor_cli.py::TestAnchorCli.test_requires_reason
def _anchor(root: Path, cfg: AppConfig) -> None:
    """`frob ticket anchor <id> --set|--clear (--reason TEXT | --reason-file
    PATH)`: the ONLY thing this command does is forward to
    `frob.tickets.set_anchor` (T-1856's library-level primitive, CLI
    wiring deferred to this ticket, T-1867) -- no validation is re-derived
    here, same forwarding shape as `_priority`/`_kind`/T-0411."""
    from frob.tickets._land import set_anchor

    if cfg.ticket_id is None:
        _log.error("frob ticket anchor requires <id>")
        sys.exit(1)

    reason = _resolve_anchor_reason(cfg)
    if not reason:
        _log.error("frob ticket anchor requires --reason TEXT or --reason-file PATH")
        sys.exit(1)

    anchor_value = cfg.ticket_anchor_set
    result = set_anchor(root, cfg.ticket_id, anchor=anchor_value, reason=reason)
    if result.is_err:
        _log.error("anchor change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: anchor now %s -- %s",
        cfg.ticket_id,
        ticket.anchor,
        ticket.anchor_reason,
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


# frob:ticket T-0834
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to the deferred import of \
# set_kind, a typani Result-returning call the resolver cannot follow through the \
# function-local import boundary; the only locally-visible fallible step (TicketKind \
# construction) is already caught below"
def _kind(root: Path, cfg: AppConfig) -> None:
    """`frob ticket kind <id> <kind>`: the ONLY thing this command does is
    forward to `frob.tickets.set_kind` -- no validation is re-derived here
    (T-0834, same pattern as `_priority`/T-0411). `kind` is validated
    strictly against the real `TicketKind` enum inside `TicketKind(...)`;
    an unknown value raises `ValueError`, reported and exited the same way
    an unresolvable ticket id is."""
    from frob.tickets import TicketKind, set_kind

    if cfg.ticket_id is None or cfg.ticket_kind_value is None:
        _log.error("frob ticket kind requires <id> <kind>")
        sys.exit(1)

    try:
        kind = TicketKind(cfg.ticket_kind_value)
    except ValueError:
        _log.error(
            "frob ticket kind: %r is not a valid kind (choose from %s)",
            cfg.ticket_kind_value,
            sorted(k.value for k in TicketKind),
        )
        sys.exit(1)

    result = set_kind(root, cfg.ticket_id, kind)
    if result.is_err:
        _log.error("kind change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: kind now %s", cfg.ticket_id, ticket.kind.value)


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


# frob:ticket T-1029
def _resolve_accept_criteria(cfg: AppConfig) -> list[str]:
    """Resolve `frob ticket accept`'s criteria: `--criterion-file` wins if
    given (parsed via `_new._parse_acceptance_file`, T-0737's blank-line-
    separated-block convention, reused verbatim rather than duplicated),
    else the repeated `--criterion TEXT` flags. Exits 1 if both are given
    (ambiguous which the caller meant) or the file cannot be read -- same
    shape as `_new._resolve_new_acceptance`."""
    from ._new import _parse_acceptance_file

    if cfg.ticket_accept_criterion_file is not None and cfg.ticket_accept_criterion:
        _log.error(
            "frob ticket accept: --criterion and --criterion-file are "
            "mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_accept_criterion_file is not None:
        try:
            text = cfg.ticket_accept_criterion_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket accept: could not read --criterion-file %s: %s",
                cfg.ticket_accept_criterion_file,
                exc,
            )
            sys.exit(1)
        return _parse_acceptance_file(text)
    return list(cfg.ticket_accept_criterion)


# frob:ticket T-1422
def _resolve_accept_amend_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket accept`'s `--amend`/`--remove` reason:
    `--reason-file` wins if given (read verbatim -- T-0737 precedent,
    same shape as `_resolve_scope_reason`), else the inline `--reason`
    string. Exits 1 if both are given; returns `None` if neither is given
    (the caller reports the "one is required" error)."""
    if (
        cfg.ticket_accept_amend_reason_file is not None
        and cfg.ticket_accept_amend_reason
    ):
        _log.error(
            "frob ticket accept: --reason and --reason-file are mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_accept_amend_reason_file is not None:
        try:
            return cfg.ticket_accept_amend_reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket accept: could not read --reason-file %s: %s",
                cfg.ticket_accept_amend_reason_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_accept_amend_reason


# frob:ticket T-1422
def _accept_amend(root: Path, cfg: AppConfig) -> None:
    """`frob ticket accept <id> --amend INDEX --text TEXT (--reason TEXT |
    --reason-file PATH)`: the ONLY thing this command does is resolve the
    reason (`_resolve_accept_amend_reason`) and forward to `frob.tickets.
    amend_acceptance` -- all validation (terminal-state refusal, index
    range, reason requirement) lives there (T-1422, same "this command
    does nothing but forward" pattern as `_scope`/`_accept`)."""
    from frob.tickets import amend_acceptance

    if cfg.ticket_accept_amend_text is None:
        _log.error("frob ticket accept --amend requires --text TEXT")
        sys.exit(1)
    reason = _resolve_accept_amend_reason(cfg)
    if not reason:
        _log.error(
            "frob ticket accept --amend requires --reason TEXT or --reason-file PATH"
        )
        sys.exit(1)

    assert cfg.ticket_id is not None
    assert cfg.ticket_accept_amend_index is not None
    result = amend_acceptance(
        root,
        cfg.ticket_id,
        cfg.ticket_accept_amend_index,
        cfg.ticket_accept_amend_text,
        reason=reason,
    )
    if result.is_err:
        _log.error("accept --amend failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: acceptance[%d] amended: %s",
        cfg.ticket_id,
        cfg.ticket_accept_amend_index,
        ticket.acceptance[cfg.ticket_accept_amend_index].text,
    )


# frob:ticket T-1422
def _accept_remove(root: Path, cfg: AppConfig) -> None:
    """`frob ticket accept <id> --remove INDEX (--reason TEXT |
    --reason-file PATH)`: the ONLY thing this command does is resolve the
    reason and forward to `frob.tickets.remove_acceptance` -- all
    validation lives there (T-1422, mirrors `_accept_amend`)."""
    from frob.tickets import remove_acceptance

    reason = _resolve_accept_amend_reason(cfg)
    if not reason:
        _log.error(
            "frob ticket accept --remove requires --reason TEXT or --reason-file PATH"
        )
        sys.exit(1)

    assert cfg.ticket_id is not None
    assert cfg.ticket_accept_remove_index is not None
    result = remove_acceptance(
        root, cfg.ticket_id, cfg.ticket_accept_remove_index, reason=reason
    )
    if result.is_err:
        _log.error("accept --remove failed: %s", result.danger_err)
        sys.exit(1)
    _log.info(
        "%s: acceptance[%d] removed",
        cfg.ticket_id,
        cfg.ticket_accept_remove_index,
    )


# frob:ticket T-1029
# frob:ticket T-1422
def _accept(root: Path, cfg: AppConfig) -> None:
    """`frob ticket accept <id>`: dispatches to exactly one of three modes
    on `cfg` -- `--amend INDEX` (`_accept_amend`, T-1422), `--remove
    INDEX` (`_accept_remove`, T-1422), or the default append mode
    (`_resolve_accept_criteria` + `frob.tickets.add_acceptance`, T-1029).
    `--amend` and `--remove` are mutually exclusive with each other and
    with plain `--criterion`/`--criterion-file` -- naming more than one
    mode in a single invocation is ambiguous, not a "do all of them"
    request."""
    from frob.tickets import add_acceptance

    if cfg.ticket_id is None:
        _log.error("frob ticket accept requires <id>")
        sys.exit(1)

    modes_given = sum(
        [
            cfg.ticket_accept_amend_index is not None,
            cfg.ticket_accept_remove_index is not None,
        ]
    )
    if modes_given > 1:
        _log.error("frob ticket accept: --amend and --remove are mutually exclusive")
        sys.exit(1)
    if cfg.ticket_accept_amend_index is not None:
        _accept_amend(root, cfg)
        return
    if cfg.ticket_accept_remove_index is not None:
        _accept_remove(root, cfg)
        return

    criteria = _resolve_accept_criteria(cfg)
    if not criteria:
        _log.error(
            "frob ticket accept requires --criterion TEXT or --criterion-file PATH "
            "(or --amend INDEX / --remove INDEX)"
        )
        sys.exit(1)

    result = add_acceptance(root, cfg.ticket_id, criteria)
    if result.is_err:
        _log.error("accept failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: acceptance now %d criterion/criteria (+%d this change)",
        cfg.ticket_id,
        len(ticket.acceptance),
        len(criteria),
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

    from frob.app.ticket_runner import _stdout_color

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

    from frob.app.ticket_runner import _stdout_color

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


# frob:ticket T-1069
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to the deferred import of \
# set_tier, a typani Result-returning call the resolver cannot follow through the \
# function-local import boundary; the only locally-visible fallible step (TicketTier \
# construction) is already caught below"
def _tier(root: Path, cfg: AppConfig) -> None:
    """`frob ticket tier <id> <epic|story|ticket>`: the ONLY thing this
    command does is forward to `frob.tickets.set_tier` -- no validation is
    re-derived here (T-1069, same pattern as `_priority`/T-0411). `tier` is
    validated strictly against the real `TicketTier` enum inside
    `TicketTier(...)`; an unknown value raises `ValueError`, reported and
    exited the same way an unresolvable ticket id is."""
    from frob.tickets import TicketTier, set_tier

    if cfg.ticket_id is None or cfg.ticket_tier_value is None:
        _log.error("frob ticket tier requires <id> <tier>")
        sys.exit(1)

    try:
        tier = TicketTier(cfg.ticket_tier_value)
    except ValueError:
        _log.error(
            "frob ticket tier: %r is not a valid tier (choose from %s)",
            cfg.ticket_tier_value,
            sorted(t.value for t in TicketTier),
        )
        sys.exit(1)

    result = set_tier(root, cfg.ticket_id, tier)
    if result.is_err:
        _log.error("tier change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: tier now %s", cfg.ticket_id, ticket.tier.value)


# frob:ticket T-1613
def _runs_last(root: Path, cfg: AppConfig) -> None:
    """`frob ticket runs-last <id> <on|off>`: the ONLY thing this command
    does is forward to `frob.tickets.set_runs_last` -- no validation is
    re-derived here (same pattern as `_tier`/T-1069). `on|off` is already
    restricted by argparse `choices` (`_add_ticket_runs_last_parser`), so
    the only local step is the literal `on` -> `True` mapping."""
    from frob.tickets import set_runs_last

    if cfg.ticket_id is None or cfg.ticket_runs_last_value is None:
        _log.error("frob ticket runs-last requires <id> <on|off>")
        sys.exit(1)

    runs_last = cfg.ticket_runs_last_value == "on"
    result = set_runs_last(root, cfg.ticket_id, runs_last)
    if result.is_err:
        _log.error("runs-last change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: runs-last now %s", cfg.ticket_id, ticket.runs_last)


# frob:ticket T-0715
def _sprint(root: Path, cfg: AppConfig) -> None:
    """Dispatch `frob ticket sprint assign|show` (T-0715) to its handler."""
    if cfg.ticket_sprint_command == "assign":
        _sprint_assign(root, cfg)
    elif cfg.ticket_sprint_command == "show":
        _sprint_show(root, cfg)
    else:
        _log.error("usage: frob ticket sprint <assign|show> ...")
        sys.exit(1)


# frob:ticket T-0715
def _sprint_assign(root: Path, cfg: AppConfig) -> None:
    """`frob ticket sprint assign <id> <label>` (T-0715): set a ticket's
    sprint commitment via `frob.tickets.set_sprint`."""
    from frob.tickets import set_sprint

    if cfg.ticket_id is None or cfg.ticket_sprint is None:
        _log.error("frob ticket sprint assign requires <id> <label>")
        sys.exit(1)
    result = set_sprint(root, cfg.ticket_id, cfg.ticket_sprint)
    if result.is_err:
        _log.error("ticket sprint assign failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s sprint set to %s", cfg.ticket_id, cfg.ticket_sprint)


# frob:ticket T-0715
def _sprint_show(root: Path, cfg: AppConfig) -> None:
    """`frob ticket sprint show <label>` (T-0715): render
    `frob.tickets.sprint_view`'s commitment summary -- every ticket
    carrying this sprint label, a state rollup, and closed-count
    velocity."""
    from frob.tickets import load_active, sprint_view

    if cfg.ticket_sprint is None:
        _log.error("frob ticket sprint show requires <label>")
        sys.exit(1)
    result = load_active(root)
    if result.is_err:
        _log.error("ticket sprint show failed: %s", result.danger_err)
        sys.exit(1)
    report = sprint_view(result.danger_ok, cfg.ticket_sprint)

    if cfg.ticket_json:
        import json

        payload = {
            "sprint": report.sprint,
            "tickets": [t.model_dump(mode="json") for t in report.tickets],
            "rollup": {state.value: count for state, count in report.rollup.items()},
            "closed": report.closed,
        }
        _log.info(json.dumps(payload, indent=2))
        return

    from frob.app.ticket_runner import _stdout_color

    color = _stdout_color()
    _log.info(
        "sprint %s -- %d ticket(s), %d closed",
        report.sprint,
        len(report.tickets),
        report.closed,
    )
    for state, count in sorted(report.rollup.items(), key=lambda kv: kv[0].value):
        _log.info("  %s: %d", state.value, count)
    for t in report.tickets:
        _log.info(
            "  %s  [%s]  %s",
            style_ticket_id(t.id, color),
            style_state(t.state.value, color),
            t.title,
        )


# frob:ticket T-0568
# frob:ticket T-1243
def _brief(root: Path, cfg: AppConfig) -> None:
    """`frob ticket brief <id>` (T-0568): print `frob.tickets.brief_ticket`'s
    full mission briefing text -- the entire point is a single command a
    coordinator can paste into a dispatch prompt instead of hand-typing
    the same ~400 words of playbook/scope/verify boilerplate every time.
    `--cluster <epic-or-story-id>` (T-1243) instead prints `frob.tickets.
    brief_cluster`'s one briefing covering every dispatchable descendant of
    that epic/story, dependency-ordered."""
    from frob.tickets import brief_cluster, brief_ticket

    if cfg.ticket_cluster is not None:
        cluster_result = brief_cluster(root, cfg.ticket_cluster)
        if cluster_result.is_err:
            _log.error("ticket brief --cluster failed: %s", cluster_result.danger_err)
            sys.exit(1)
        _log.info("%s", cluster_result.danger_ok)
        return

    if cfg.ticket_id is None:
        _log.error("frob ticket brief requires <id> or --cluster <epic-or-story-id>")
        sys.exit(1)
    result = brief_ticket(root, cfg.ticket_id)
    if result.is_err:
        _log.error("ticket brief failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s", result.danger_ok)


# frob:ticket T-1100
def _flow(root: Path, cfg: AppConfig) -> None:
    """`frob ticket flow [--json]` (T-1100): render `frob.tickets.
    ticket_flow`'s filed/day vs landed/day vs net table, the current open
    count, and a naive burn-down ETA -- one table, one ETA line, nothing
    re-derived here that `ticket_flow` itself does not already compute."""
    from frob.tickets import load_active, ticket_flow

    result = load_active(root)
    if result.is_err:
        _log.error("ticket flow failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    report = ticket_flow(root, queue)

    if cfg.ticket_json:
        import json

        payload = {
            "rows": [
                {
                    "day": r.day.isoformat(),
                    "filed": r.filed,
                    "landed": r.landed,
                    "net": r.net,
                }
                for r in report.rows
            ],
            "open_count": report.open_count,
            "trailing_net_rate": report.trailing_net_rate,
            "eta_days": report.eta_days,
        }
        _log.info(json.dumps(payload, indent=2))
        return

    _log.info("%-12s  %6s  %6s  %6s", "day", "filed", "landed", "net")
    for row in report.rows:
        _log.info(
            "%-12s  %6d  %6d  %+6d", row.day.isoformat(), row.filed, row.landed, row.net
        )
    # 3 matches frob.tickets._FLOW_TRAILING_DAYS (T-1100) -- a display-only
    # literal, not re-derived: the actual window width is `ticket_flow`'s
    # own concern, this only labels the number it already returned.
    _log.info(
        "open: %d  trailing-3-day net rate: %+.2f/day",
        report.open_count,
        report.trailing_net_rate,
    )
    if report.eta_days is None:
        _log.info(
            "ETA: cannot estimate (naive extrapolation) -- queue is not "
            "net-shrinking over the trailing window"
        )
    else:
        _log.info(
            "ETA: ~%.1f days to zero-open (naive extrapolation, NOT a forecast)",
            report.eta_days,
        )


# frob:ticket T-0398
