"""frob.app.ticket_runner._new -- the `frob ticket new` command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

from ._verify import _apply_evidence

_log = get_logger("frob.app.ticket_runner")

# frob:ticket T-1556
# Above this many scope-closure warnings, `_emit_scope_closure_warnings`
# collapses the rest into one counted summary line instead of one WARNING
# per gap -- a mega-glob scope can produce thousands of lines (T-1556's own
# "signal is never drowned" acceptance criterion), which buries the FIRST
# few (usually the most actionable) hints under a wall of repetition.
_SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD = 8


def _resolve_new_body(cfg: AppConfig) -> str:
    """Resolve `frob ticket new`'s body: `--body-file` wins if given (read
    verbatim, byte-for-byte -- T-0737, so backticked/quoted/`$`-laden prose
    never rides the shell), else the inline `--body` string. Exits 1 if
    both are given (ambiguous which the caller meant) or the file cannot be
    read."""
    if cfg.ticket_body_file is not None and cfg.ticket_body:
        _log.error("frob ticket new: --body and --body-file are mutually exclusive")
        sys.exit(1)
    if cfg.ticket_body_file is not None:
        try:
            return cfg.ticket_body_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket new: could not read --body-file %s: %s",
                cfg.ticket_body_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_body


# frob:ticket T-0737
def _parse_acceptance_file(text: str) -> list[str]:
    """Split `--acceptance-file` contents into criteria: one criterion per
    blank-line-separated block (T-0737) -- chosen over strict one-per-line
    so a multi-sentence GIVEN/WHEN/THEN criterion may still wrap across
    lines within its own block. A file with no blank lines degrades
    gracefully to one criterion per non-empty line. Blocks are stripped of
    leading/trailing whitespace; empty blocks are dropped."""
    if re.search(r"\n\s*\n", text):
        blocks = [b.strip() for b in re.split(r"\n\s*\n+", text)]
        return [b for b in blocks if b]
    return [line.strip() for line in text.splitlines() if line.strip()]


# frob:ticket T-0737
def _resolve_new_acceptance(cfg: AppConfig) -> list[str]:
    """Resolve `frob ticket new`'s acceptance criteria: `--acceptance-file`
    wins if given (parsed via `_parse_acceptance_file`, T-0737), else the
    repeated `--acceptance TEXT` flags. Exits 1 if both are given (ambiguous
    which the caller meant) or the file cannot be read."""
    if cfg.ticket_acceptance_file is not None and cfg.ticket_acceptance:
        _log.error(
            "frob ticket new: --acceptance and --acceptance-file are mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_acceptance_file is not None:
        try:
            text = cfg.ticket_acceptance_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket new: could not read --acceptance-file %s: %s",
                cfg.ticket_acceptance_file,
                exc,
            )
            sys.exit(1)
        return _parse_acceptance_file(text)
    return list(cfg.ticket_acceptance)


def _ticket_spec_from_cfg(cfg: AppConfig, *, title: str, kind: str):  # noqa: ANN201
    """Build the `TicketSpec` `frob ticket new`'s flags describe.

    `title`/`kind` are taken as separate required params (not read again from
    `cfg.ticket_title`/`cfg.ticket_kind`) so the caller's None-check narrows
    them to `str` here too -- `cfg`'s fields stay `str | None` on their own.
    """
    from frob.tickets import (
        Origin,
        Priority,
        Stride,
        TicketKind,
        TicketSpec,
        TicketTier,
    )

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
        # frob:ticket T-0715
        tier=TicketTier(cfg.ticket_tier) if cfg.ticket_tier else TicketTier.TICKET,
        # frob:ticket T-0715
        sprint=cfg.ticket_sprint,
        # T-0572: `--acceptance TEXT` (repeatable) gives plain strings;
        # TicketSpec's `_coerce_acceptance_field` validator wraps each into
        # a fresh, unbound {text, evidence: ()} AcceptanceCriterion --
        # `type: ignore` names the mismatch this validator exists to close
        # (the annotated field type is the POST-validation shape).
        # frob:ticket T-0737
        # `_resolve_new_acceptance` picks --acceptance or --acceptance-file.
        acceptance=tuple(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
            _resolve_new_acceptance(cfg)
        ),
        threat=Stride(cfg.ticket_threat) if cfg.ticket_threat else None,
        # frob:ticket T-0454
        component=cfg.ticket_component,
        labels=tuple(cfg.ticket_labels),
        # frob:ticket T-0737
        # `_resolve_new_body` picks --body or --body-file.
        body=_resolve_new_body(cfg),
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
# frob:ticket T-1130
def _new(root: Path, cfg: AppConfig) -> None:
    """Create a ticket from `cfg`'s new-ticket flags; if `--evidence` ids
    were given, apply them (via `_apply_evidence`) after creation succeeds,
    then offer to attach a clipboard image on a TTY.

    T-1130: auto-commits the ledger change LAST, after every other write
    this command makes (`new_ticket`'s own frontmatter block, plus any
    `--evidence` ids applied right after) -- so the one commit captures
    the WHOLE filed block, evidence included, rather than a partial commit
    of just the bare ticket followed by a second, separately-dirty write.
    `--no-commit` (`cfg.ticket_no_commit`) opts out entirely, matching
    `start`'s T-1054 auto-commit precedent (parity, T-1130's own acceptance
    criterion)."""
    # frob:ticket T-0005
    from frob.tickets import new_ticket
    from frob.tickets._leases import commit_ticket_ledger_change

    if cfg.ticket_title is None or cfg.ticket_kind is None:
        _log.error("frob ticket new requires --title and --kind")
        sys.exit(1)

    spec = _ticket_spec_from_cfg(cfg, title=cfg.ticket_title, kind=cfg.ticket_kind)
    # T-1758: new_ticket now auto-commits internally by default -- opt out
    # here (no_commit=True) so THIS verb's own commit below still captures
    # the whole filed block (title/scope/body plus any --evidence ids
    # applied right after), not just the bare ticket in a separate commit.
    # T-1891: warn_if_dirty=False too -- this call is always followed,
    # unconditionally, by this same function's own commit_ticket_ledger_
    # change call below, so the ledger being dirty HERE is never the
    # final outcome; warning about it as if --no-commit left it that way
    # is actively misleading (confirmed live: a plain `frob ticket new`,
    # no --no-commit anywhere, still printed that warning).
    result = new_ticket(root, spec, no_commit=True, warn_if_dirty=False)
    if result.is_err:
        _log.error("ticket new failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("created %s: %s", ticket.id, ticket.title)
    # frob:ticket T-0998
    _emit_scope_closure_warnings(
        "ticket new", ticket.id, _scope_closure_warnings(root, ticket.scope)
    )
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=ticket.id, event="created")

    if cfg.ticket_evidence_ids:
        added = _apply_evidence(root, ticket.id, cfg.ticket_evidence_ids)
        if added.is_err:
            sys.exit(1)

    _maybe_attach_clipboard_image(root, ticket.id)

    committed = commit_ticket_ledger_change(
        root,
        ticket.id,
        f"chore(tickets): file {ticket.id} {ticket.title}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


# frob:ticket T-1556
# frob:tests \
# tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings\
# .test_few_warnings_logged_individually
# frob:tests \
# tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings\
# .test_many_warnings_collapse_to_counted_summary
# frob:tests \
# tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings\
# .test_verbose_env_var_disables_collapse
# frob:tests \
# tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings\
# .test_no_warnings_logs_nothing
# frob:doc \
# docs/design/cli-hygiene.md#principle-4-scope-closure-warning-volume-must-not-bury-its\
# -own-most
def _emit_scope_closure_warnings(
    prefix: str, ticket_id: str, warnings: tuple[str, ...]
) -> None:
    """Log `warnings` (from `_scope_closure_warnings`) as `prefix
    <ticket_id>: scope closure: <warning>` lines -- one per warning below
    `_SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD`, or the first N plus a
    single counted-summary line above it (T-1556: a mega-glob scope's
    scope-closure feedback used to flood output with one WARNING per gap,
    up to thousands of lines, burying the first few -- usually the most
    actionable -- hints; a genuinely narrow scope, the common case, is
    completely unaffected since it never crosses the threshold).

    `FROB_SCOPE_CLOSURE_VERBOSE=1` disables collapsing entirely (the
    escape hatch this ticket's acceptance criterion calls for) -- shared
    by both `frob ticket new` and `frob ticket scope`'s own call sites
    (`_mutate.py`), matching this repo's existing `FROB_AGENT`/`FROB_NO_
    GATE_CACHE`-style env-toggle precedent rather than a new CLI flag,
    since `--verbose` itself would need `src/frob/_cli_parsers/**` wiring
    outside this ticket's own declared scope (see the Done report for the
    CLI-flag follow-up this leaves open, mirroring T-1824's log-only-
    wiring precedent for the identical cross-file-scope shape)."""
    if not warnings:
        return
    # frob:waive SEC110 reason="FROB_SCOPE_CLOSURE_VERBOSE is a boolean \
    # output-verbosity toggle (T-1556), not a credential or secret -- its value never \
    # holds anything sensitive"
    if os.environ.get("FROB_SCOPE_CLOSURE_VERBOSE") or (
        len(warnings) <= _SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD
    ):
        for warning in warnings:
            _log.warning("%s %s: scope closure: %s", prefix, ticket_id, warning)
        return
    shown = warnings[:_SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD]
    for warning in shown:
        _log.warning("%s %s: scope closure: %s", prefix, ticket_id, warning)
    _log.warning(
        "%s %s: scope closure: %d more warning(s) collapsed -- set "
        "FROB_SCOPE_CLOSURE_VERBOSE=1 and retry to see all %d",
        prefix,
        ticket_id,
        len(warnings) - len(shown),
        len(warnings),
    )


# frob:ticket T-0998
def _scope_closure_warnings(root: Path, scope) -> tuple[str, ...]:  # noqa: ANN001
    """Suggest-or-warn scope-closure hints for `scope` (T-0998), rendered
    as plain human warning lines for `frob ticket new`/`frob ticket scope`'s
    own CLI surface -- the closure TRIPLE `frob.gates._scope002_violations`
    consults: `frob.graph.affects.scope_doc_code_gaps` (code<->docs),
    `frob.graph.affects.scope_test_gaps` (code<->tests, symmetric with the
    doc direction), and `frob.graph.callgraph.scope_private_helper_gaps`
    (private-helper capture) -- so a declaring agent sees this feedback at
    `new`/`scope` time -- before ever running `frob check` -- instead of
    discovering AFFECT001/COV002 reactively mid-ticket. Returns `()`
    silently (never blocks the CLI command) when the graph cache cannot be
    loaded/built at all -- this is a nudge, not a gate."""
    from frob.app import ticket_runner as _ticket_runner
    from frob.graph.affects import scope_doc_code_gaps, scope_test_gaps
    from frob.graph.callgraph import scope_private_helper_gaps

    snapshot = _ticket_runner._graph_snapshot(root)
    if snapshot.is_err:
        return ()
    snap = snapshot.danger_ok
    scope_tuple = tuple(scope)
    warnings: list[str] = []
    for gap in scope_doc_code_gaps(snap, scope_tuple):
        if gap.direction == "code_missing_doc":
            warnings.append(
                f"{gap.scoped_site}'s frob:doc target lives in "
                f"{gap.missing_file!r}, not in scope -- consider --add "
                f"{gap.missing_file!r}"
            )
        else:
            warnings.append(
                f"doc anchor {gap.scoped_site} describes {gap.target} in "
                f"{gap.missing_file!r}, not in scope -- consider --add "
                f"{gap.missing_file!r}"
            )
    for gap in scope_test_gaps(snap, scope_tuple):
        if gap.direction == "code_missing_test":
            warnings.append(
                f"{gap.scoped_site}'s frob:tests target lives in "
                f"{gap.missing_file!r}, not in scope -- consider --add "
                f"{gap.missing_file!r}"
            )
        else:
            warnings.append(
                f"test {gap.scoped_site} covers {gap.target} in "
                f"{gap.missing_file!r}, not in scope -- consider --add "
                f"{gap.missing_file!r}"
            )
    for helper_gap in scope_private_helper_gaps(
        root, scope_tuple, tuple(snap.file_hashes)
    ):
        suggestion = "add" if helper_gap.only_used_by_scope else "review"
        warnings.append(
            f"{helper_gap.caller} calls private helper {helper_gap.callee} "
            f"defined in {helper_gap.definition_file!r}, not in scope "
            f"(probable under-capture) -- {suggestion} "
            f"{helper_gap.definition_file!r}"
        )
    return tuple(warnings)
