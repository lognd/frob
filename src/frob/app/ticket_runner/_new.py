"""frob.app.ticket_runner._new -- the `frob ticket new` command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import difflib
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from frob.app.config import AppConfig
from frob.logging import get_logger

from ._verify import _apply_evidence

if TYPE_CHECKING:
    from frob.tickets import Priority

_log = get_logger("frob.app.ticket_runner")

# frob:ticket T-1995
# difflib's own conventional "close enough to be worth a look" cutoff
# (matching `frob.gates._fix_engine`'s identical use of 0.6 for the same
# "surface a candidate, do not silently assume identity" purpose).
_RELATED_TICKET_SIMILARITY_THRESHOLD = 0.6
_MAX_RELATED_TICKETS_SHOWN = 5

# frob:ticket T-1995
# Phrases a ticket body uses to assert a missing enforcement -- exactly
# the T-1986 shape ("nothing enforces X") this repo's own history shows
# can be wrong when the covering work already shipped and archived.
_MISSING_ENFORCEMENT_CUES = (
    "nothing enforces",
    "nothing refuses",
    "nothing catches",
    "nothing checks",
    "not enforced",
    "not checked",
    "not caught",
    "not refused",
    "no check",
    "only warns",
    "does not refuse",
    "does not check",
    "does not catch",
    "never refuses",
    "never checks",
    "unchecked",
)

_TITLE_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{2,}")
_TITLE_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "not",
        "with",
        "does",
        "this",
        "that",
        "its",
        "are",
        "was",
        "but",
        "all",
        "any",
        "can",
        "has",
        "have",
        "into",
        "when",
        "while",
        "from",
        "over",
        "only",
        "never",
        "nothing",
    }
)

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


# frob:ticket T-1960
def _resolve_new_priority(root: Path, cfg: AppConfig) -> Priority:
    """Resolve `frob ticket new`'s priority: an explicit `--priority`
    always wins; otherwise, if `--parent PARENT_ID` names a real ticket,
    INHERIT that parent's priority instead of defaulting to
    `Priority.MEDIUM` -- T-1960's own defect was that a WIRE001 follow-up
    filed off a HIGH-priority parent's waiver silently dropped to medium
    (three real instances measured: T-1921/T-1937/T-1938, all high,
    each spawning a medium follow-up), so the half of a fix that makes it
    REAL starved behind newer high-priority work. No blanket escalation:
    a medium parent still yields a medium follow-up, same as today, and a
    `--parent` that fails to resolve (unknown id, or none given at all)
    falls back to the pre-existing `Priority.MEDIUM` default unchanged."""
    from frob.tickets import Priority

    if cfg.ticket_priority:
        return Priority(cfg.ticket_priority)
    if cfg.ticket_parent:
        from frob.tickets import _load_one

        parent = _load_one(root, cfg.ticket_parent)
        if parent.is_ok:
            return parent.danger_ok.priority
    return Priority.MEDIUM


def _ticket_spec_from_cfg(root: Path, cfg: AppConfig, *, title: str, kind: str):  # noqa: ANN201
    """Build the `TicketSpec` `frob ticket new`'s flags describe.

    `title`/`kind` are taken as separate required params (not read again from
    `cfg.ticket_title`/`cfg.ticket_kind`) so the caller's None-check narrows
    them to `str` here too -- `cfg`'s fields stay `str | None` on their own.
    `root` is threaded through only for `_resolve_new_priority`'s
    `--parent` priority-inheritance lookup (T-1960)."""
    from frob.tickets import (
        Origin,
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
        # frob:ticket T-1960
        priority=_resolve_new_priority(root, cfg),
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


# frob:ticket T-1995
def _title_words(title: str) -> frozenset[str]:
    """Lowercased, stopword-filtered significant words in `title` (T-1995)
    -- used both to size the related-ticket search's candidate pool
    sanity and to build a targeted `_refuse_*`/`_check_*` symbol grep."""
    return frozenset(
        w for w in _TITLE_WORD_RE.findall(title.lower()) if w not in _TITLE_STOPWORDS
    )


# frob:ticket T-1995
# frob:doc docs/modules/tickets.md#public-api
def related_tickets(root: Path, title: str) -> tuple[tuple[str, str, str, float], ...]:
    """`(ticket_id, title, state, similarity)` for every ticket -- ACTIVE
    or ARCHIVED -- whose own title is a close textual match to `title`
    (T-1995), by descending similarity, capped at
    `_MAX_RELATED_TICKETS_SHOWN`.

    Archived tickets are included deliberately: a search over open
    tickets alone is exactly the gap that let T-1986 through -- it
    asserted a missing enforcement that had shipped and archived as
    T-1866 two days earlier, and the standing pre-filing search (which
    only ever covered open tickets) correctly found nothing. `difflib.
    SequenceMatcher.ratio()` (the same 0.6 cutoff convention `frob.gates.
    _fix_engine` uses for its own close-match nudge) catches near-
    duplicate and reworded titles without requiring an exact match;
    genuinely distinct titles score low and are never surfaced, so a
    successor ticket with a deliberately similar title still needs no
    override beyond the one `--ack-related` gate below."""
    from frob.tickets import load_all
    from frob.tickets._store import load_archive

    pool: dict = {}
    active = load_all(root)
    if active.is_ok:
        pool.update(active.danger_ok)
    archived = load_archive(root)
    if archived.is_ok:
        pool.update(archived.danger_ok)

    scored: list[tuple[str, str, str, float]] = []
    lowered_title = title.lower()
    for tid, ticket in pool.items():
        ratio = difflib.SequenceMatcher(
            None, lowered_title, ticket.title.lower()
        ).ratio()
        if ratio >= _RELATED_TICKET_SIMILARITY_THRESHOLD:
            scored.append((tid, ticket.title, ticket.state.value, ratio))
    scored.sort(key=lambda row: row[3], reverse=True)
    return tuple(scored[:_MAX_RELATED_TICKETS_SHOWN])


# frob:ticket T-1995
def _possible_enforcement_symbols(root: Path, title: str, body: str) -> tuple[str, ...]:
    """`file:symbol` candidates (capped at 5) that MIGHT already implement
    the enforcement `title`/`body` claims is missing (T-1995's second
    class: "nothing enforces X" when X already shipped). Only runs the
    grep at all when the body actually asserts a missing enforcement
    (`_MISSING_ENFORCEMENT_CUES`) -- a ticket with no such claim gets no
    grep and no surfaced symbols, so this never fires on an unrelated
    feature/docs ticket. Best-effort: any git/grep failure returns `()`,
    never blocks ticket creation on its own (this is a hint, not a gate --
    only `related_tickets`'s title-similarity match ever requires `--ack-
    related`)."""
    text = f"{title}\n{body}".lower()
    if not any(cue in text for cue in _MISSING_ENFORCEMENT_CUES):
        return ()
    words = sorted(_title_words(title))[:6]
    if not words:
        return ()
    from frob.gitio import run_argv

    pattern = "|".join(re.escape(w) for w in words)
    grepped = run_argv(
        [
            "git",
            "-C",
            str(root),
            "grep",
            "-niE",
            f"^\\s*def _(refuse|check)_[a-z_0-9]*({pattern})",
            "--",
            "src/frob/**/*.py",
        ]
    )
    if grepped.is_err or grepped.danger_ok.returncode not in (0, 1):
        return ()
    lines = tuple(
        line.split(":", 2)[0] + ":" + line.split(":", 2)[2].strip()
        for line in grepped.danger_ok.stdout.splitlines()
        if line.strip()
    )
    return lines[:5]


# frob:ticket T-1995
def _refuse_unacknowledged_related_tickets(
    root: Path, cfg: AppConfig, title: str, body: str
) -> None:
    """`sys.exit(1)` if `title` closely matches an existing ticket (open,
    done, OR archived) and the caller has not passed `--ack-related`
    (T-1995) -- surfaces every match by id/title/state plus, when the
    body itself claims a missing enforcement, any `_refuse_*`/`_check_*`
    symbol that might already be it. Never auto-drops or silently
    proceeds: the only way past a real match is the explicit flag, and a
    title with no close match needs no flag at all (this never blocks a
    genuinely novel ticket, including a deliberately similar successor
    once acknowledged once)."""
    if cfg.ticket_ack_related:
        return
    related = related_tickets(root, title)
    if not related:
        return
    _log.warning(
        "ticket new: %d existing ticket(s) closely match this title -- "
        "review before filing a duplicate:",
        len(related),
    )
    for tid, related_title, state, ratio in related:
        _log.warning(
            "  %s [%s] (%.0f%% match): %s", tid, state, ratio * 100, related_title
        )
    symbols = _possible_enforcement_symbols(root, title, body)
    if symbols:
        _log.warning(
            "ticket new: this body claims a missing enforcement -- these "
            "existing symbols may already cover it:"
        )
        for sym in symbols:
            _log.warning("  %s", sym)
    _log.error(
        "ticket new: refusing -- pass --ack-related once you have confirmed "
        "this is not a duplicate of the ticket(s) above"
    )
    sys.exit(1)


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

    # frob:ticket T-1995
    _refuse_unacknowledged_related_tickets(
        root, cfg, cfg.ticket_title, _resolve_new_body(cfg)
    )

    spec = _ticket_spec_from_cfg(
        root, cfg, title=cfg.ticket_title, kind=cfg.ticket_kind
    )
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
