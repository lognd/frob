# T-2851: the BUG002/must-still-pass repro-classification family (
# _BugReproOutcome onward) that used to live below this point moved to
# frob.gates._bug_repro -- this file's own former LARGE001 waiver
# documented exactly this plan. Dropped below the 500-line threshold on
# its own (1281 -> 488 lines), so no fresh waiver is needed here.
"""TEST016 (T-0755): the diff-scoped adversarial evidence obligation as a
`Violation`-producing gate.

Deliberately NOT part of `test_gate`'s snapshot-driven pipeline (docs/
modules/gates.md's `_STAGE_GROUPS`): every other TEST rule is a pure
function of the graph snapshot, cheap and safe to run on every `frob
check`. This rule spawns a bounded but real subprocess mutation pass
(`frob.tickets._mutation_evidence.check_ticket_mutation_evidence`, which
itself reuses `frob.mutate` -- no parallel mutation engine) per ticket. Not
something the default snapshot-driven gate pass may do without violating
the T-0755 PERF guard (must not slow `frob check` for tickets that never
opt in) -- `frob.check` is out of this ticket's declared scope entirely, so
`mutation_evidence_violations` has two callers today:
`frob.tickets._land._check_mutation_evidence`, invoked from
`_land_precheck` at `frob ticket land` time, and (T-0844)
`frob.app.ticket_runner`'s direct `frob ticket close` CLI path, so a
security/bug-kind ticket closed without landing is not exempt from this
obligation either.

Severity: WARN by default, promoted to ERROR for `security`/`bug`-kind
tickets (T-0755's own text: "ratchet to error ... for security/bug-kind
tickets") -- those are exactly the kinds the root-cause incident (T-0611,
T-0571, T-0682, T-0574, T-0710) came from. This is a plain per-ticket
`kind` check, not the `frob.gates._ratchet` baseline-pool mechanism: no
retroactive-mutation-of-past-findings concern applies here, because the
check runs ONLY at THIS ticket's own close/land time -- an already-closed
ticket's evidence is never re-scanned, so landing this rule cannot
retroactively turn a past close red (T-0755's own landing-safety
requirement, satisfied structurally rather than via a ratchet pool)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.tickets._models import Ticket, TicketKind
from frob.tickets._mutation_evidence import (
    ConfirmatoryFinding,
    MutationEvidenceError,
    check_ticket_mutation_evidence,
)

_log = get_logger(__name__)

_ERROR_KINDS = frozenset({TicketKind.SECURITY, TicketKind.BUG})


# frob:doc docs/modules/tickets-landing.md#mutation-evidence-obligation-test016-t-0755
# frob:enforces CHK-GATE-TEST016
# frob:enforces CHK-THEME-EXISTENCE-NOT-PROOF
# frob:enforces CHK-SUBSYS-TICKETS-TESTING
# frob:enforces CHK-GATE-TEST018
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_warn_for_feature_kind  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_error_for_security_kind  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_no_findings_no_violations  # noqa: E501
# frob:tests tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches.test_exec_disabled_degrades_to_no_violations  # noqa: E501
# frob:ticket T-1733
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_evidence_weakened_and_confirmatory_refuses_outright  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_no_evidence_changes_never_produces_test018  # noqa: E501
def mutation_evidence_violations(
    root: Path, ticket: Ticket, base_ref: str = "main"
) -> tuple[Violation, ...]:
    """TEST016: `ticket`'s own bound evidence tests never killed a single
    mutant of a diff-touched, in-scope file -- confirmatory-only evidence.

    Severity is ERROR for `security`/`bug`-kind tickets, WARN otherwise
    (see module docstring). `Err(ExecDisabled)` (the exec kill switch was
    active) degrades to NO violations rather than a false-clean pass being
    silently indistinguishable from a real one -- the caller sees the
    `Err` via `frob.tickets._mutation_evidence` directly if it needs to
    react to that case specially; this wrapper's job is only to turn
    genuine `ConfirmatoryFinding`s into `Violation`s.

    T-1733/TEST018: when `ticket.evidence_changes` is non-empty (evidence
    was rebound/weakened at LEAST once during this ticket's life, via
    `frob ticket evidence --replace`) AND at least one `ConfirmatoryFinding`
    survives against the CURRENT evidence set (confirmatory-only OR
    T-1727's `unmeasured`), an ADDITIONAL, always-ERROR `TEST018`
    violation is appended -- refusing the close OUTRIGHT (severity ERROR
    regardless of ticket kind, never downgraded to WARN the way an
    ordinary TEST016 finding is for a non-bug/security ticket), never
    merely flagging it. This is the mechanical fingerprint T-1733 exists
    to catch: evidence was weakened AND what remains cannot prove the
    change -- exactly the shape of "the tests that proved it were removed
    so it would close." A ticket whose evidence was rebound but whose
    SURVIVING evidence still kills mutants is unaffected (rebinding to an
    equally-strong or stronger test is not the incident this closes)."""
    result = check_ticket_mutation_evidence(root, ticket, base_ref)
    if result.is_err:
        if result.danger_err is MutationEvidenceError.ExecDisabled:
            return ()
        return ()
    findings = result.danger_ok
    severity = Severity.ERROR if ticket.kind in _ERROR_KINDS else Severity.WARN
    violations: list[Violation] = []
    for finding in findings:
        violations.append(
            Violation(
                rule="TEST016",
                severity=severity,
                file=finding.file,
                line=0,
                message=_test016_message(ticket.id, finding),
            )
        )
    if ticket.evidence_changes and findings:
        violations.append(
            Violation(
                rule="TEST018",
                severity=Severity.ERROR,
                file=findings[0].file,
                line=0,
                message=_test018_message(ticket.id, findings),
            )
        )
    return tuple(violations)


# frob:ticket T-1733
def _test018_message(ticket_id: str, findings: tuple[ConfirmatoryFinding, ...]) -> str:
    """T-1733: the TEST018 refusal message -- names every rebound
    evidence id (from `ticket.evidence_changes`, via the caller) is NOT
    done here since the caller already has the ticket; this only names
    the confirmatory-only/unmeasured files the surviving evidence could
    not prove, and the two remedies (strengthen evidence, or the
    disclosed `--skip-mutation-evidence` escape hatch)."""
    files = ", ".join(f.file for f in findings)
    return (
        f"TEST018: {ticket_id}'s evidence was rebound/replaced during "
        f"this ticket's life (frob ticket evidence --replace, recorded "
        f"in evidence_changes) AND the surviving evidence proves nothing "
        f"against {files} -- confirmatory-only or unmeasured, per "
        f"TEST016. This is refused OUTRIGHT, not merely flagged: it is "
        f"the exact fingerprint of evidence weakened so a slow close "
        f"could complete. Remedy: (1) rebind evidence that genuinely "
        f"kills a mutant of the changed lines, or (2) if the rebind is "
        f"honest and the surviving evidence really is the best "
        f"available, `frob ticket land --skip-mutation-evidence` (logs "
        f"a loud, justification-required override)."
    )


# frob:ticket T-1727
def _test016_message(ticket_id: str, finding: ConfirmatoryFinding) -> str:
    """The TEST016 finding message (T-0755 reviewer round 2, finding 4):
    names every surviving mutant's file:line + description, then BOTH
    documented remedies (strengthen the tests, or the `--skip-mutation-
    evidence` escape hatch) -- never just a bare "confirmatory-only"
    count with no actionable next step.

    T-1727: `finding.unmeasured` gets a DIFFERENT message, never the
    "confirmatory-only" wording -- an unmeasured file was never actually
    run to completion, so nothing was proven weak, only unknown. Reusing
    the confirmatory wording here would misreport "could not measure" as
    "measured and failing" (T-1703's exact lesson, same shape as a
    budget-truncated `frob check` parsed as a clean run)."""
    if finding.unmeasured:
        return _test016_unmeasured_message(ticket_id, finding)
    named = "; ".join(f"{m.file}:{m.line} ({m.description})" for m in finding.survivors)
    return (
        f"TEST016: {ticket_id}'s bound evidence {list(finding.tests)} killed "
        f"0/{finding.mutants_total} mutant(s) of {finding.file}'s changed "
        f"lines -- confirmatory-only, does not prove the evidence detects "
        f"this change. Surviving mutant(s): {named or '(none named)'}. "
        f"Remedy: (1) strengthen the named test(s) so at least one fails "
        f"on a mutant above, or (2) if this is a genuine false positive, "
        f"`frob ticket land --skip-mutation-evidence` (logs a loud, "
        f"justification-required override)."
    )


# frob:ticket T-1727
def _test016_unmeasured_message(ticket_id: str, finding: ConfirmatoryFinding) -> str:
    """T-1727: the TEST016 message for a file the sweep's shared wall-
    clock budget cut off before it could be (fully) measured -- distinct
    wording from `_test016_message`'s confirmatory-only case so
    UNMEASURED never reads as "measured and found weak"."""
    return (
        f"TEST016: {ticket_id}'s bound evidence {list(finding.tests)} could "
        f"NOT be measured against {finding.file} -- the mutation sweep's "
        f"wall-clock budget ran out before this file's mutants could be "
        f"(fully) run. This is UNMEASURED, not confirmatory-only: nothing "
        f"was proven weak, nothing was proven adversarial either. Remedy: "
        f"(1) split the bound evidence across faster tests so the sweep "
        f"fits its budget, or (2) if the evidence is known-good and the "
        f"budget is the real constraint, `frob ticket land "
        f"--skip-mutation-evidence` (logs a loud, justification-required "
        f"override) -- the same escape hatch a genuine confirmatory-only "
        f"finding uses."
    )


# frob:ticket T-2243
def _quoted_span_ranges(
    inline_text: bytes, exclude: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Byte-offset ranges of `inline_text` (already-parsed markdown_inline
    source, one `inline` block's worth) delimited by a MATCHED pair of
    ASCII double-quote (`"`) bytes -- an inline echo of another
    document's/criterion's own words, the sentence-level counterpart to a
    block-level `> ` blockquote (T-2243). `_quoted_char_ranges` already
    treats a blockquote as QUOTED rather than DECLARED; a Done report
    routinely quotes another ticket's acceptance-criterion prose inline
    (`` acceptance [3] there is "T-2226's two still-unresolved
    T-draft-... records are re-attempted..." ``) without promoting it to
    a full blockquote -- the measured T-2226/T-2238 incident this ticket
    fixes. `exclude` is `_quoted_char_ranges`' own already-found
    `code_span` byte ranges (relative to `inline_text`) -- a `"` inside a
    code span is literal text of that span, already quoted for a
    different reason, and must never seed or close a pairing here (a
    stray quote inside `` `a "quoted" example` `` must not leak a
    pairing out past the span's own end).

    A straightforward LEFT-TO-RIGHT SEQUENTIAL PAIRING (1st with 2nd, 3rd
    with 4th, ...), scanning `"` byte OFFSETS only -- never the
    directive/id text itself, so this is a delimiter-structure parse, not
    a lexical match on the citation. An ODD total count of non-excluded
    `"` bytes leaves the trailing one unmatched and produces no range
    from it (conservative: an unclosed quote never quotes everything
    after it to the end of the paragraph)."""
    positions = [
        i
        for i, byte in enumerate(inline_text)
        if byte == 0x22  # b'"'
        and not any(start <= i < end for start, end in exclude)
    ]
    ranges: list[tuple[int, int]] = []
    for open_pos, close_pos in zip(positions[0::2], positions[1::2], strict=False):
        ranges.append((open_pos, close_pos + 1))
    return ranges


# frob:ticket T-2218
# frob:ticket T-2243
# frob:tests tests/test_gates_mutation_evidence.py::TestQuotedRanges.test_fenced_quoted
# frob:tests \
# tests/test_gates_mutation_evidence.py::TestQuotedRanges.test_inline_span_quoted
# frob:tests \
# tests/test_gates_mutation_evidence.py::TestQuotedRanges.test_blockquote_quoted
# frob:tests \
# tests/test_gates_mutation_evidence.py::TestQuotedRanges.test_indented_quoted
# frob:tests \
# tests/test_gates_mutation_evidence.py::TestQuotedRanges.test_plain_text_not_quoted
# frob:tests \
# tests/test_gates_mutation_evidence.py::TestQuotedRanges.test_double_quoted_span_quoted
def _quoted_char_ranges(body: str) -> tuple[tuple[int, int], ...]:
    """Character-offset ranges of `body` (a ticket's markdown body text)
    that markdown QUOTES rather than DECLARES: a fenced code block, an
    indented code block, a blockquote, an inline code span (T-2218), or a
    matched pair of ASCII double-quote characters within a paragraph
    (`_quoted_span_ranges`, T-2243). A directive-looking string inside
    any of these ranges is being shown as an EXAMPLE, not asserted as the
    ticket's own live directive -- the exact ambiguity `tickets/T-2215/
    ticket.md:56`'s own prose ('a `frob:waive BUG003 reason="..."`
    body-text directive') measured against `_BUG002_WAIVER_RE` and
    self-waived, and the T-2243 incident where a Done report's own prose
    inline-quoted ANOTHER ticket's acceptance-criterion text (containing
    an unrelated id) without wrapping it in a full blockquote.

    Deliberately grammar-based (`tree_sitter_language_pack`'s `markdown`
    + `markdown_inline` grammars, the same loading mechanism `frob.lang`
    uses -- see that module's own `_EXTENSION_TABLE`), not an
    indentation/substring heuristic: a fenced/indented code block and a
    blockquote are a REAL markdown-grammar distinction from a plain
    paragraph, and only the markdown_inline grammar (parsed separately,
    per markdown's own two-stage design -- the block grammar leaves
    inline content as opaque `inline` leaf nodes) can tell an inline code
    span (`` `...` ``) apart from a bare word. Deliberately NOT
    `frob.lang.raw_tree`/`COMMENT_TYPES` -- those answer 'is line N of a
    SOURCE file (a real filesystem path with a registered grammar) inside
    a comment', a different question, and `raw_tree` requires a `Path`
    with `frob.lang`'s own suffix-to-language table matching; a ticket's
    `body` is an in-memory string with no such path, and `tickets.md`
    is deliberately excluded from `frob.graph`'s own file walk (see
    `_BUG002_WAIVER_RE`'s comment) -- routing through `frob.lang` here
    would return an empty set for every ticket body, exactly the same
    silent-disable failure mode already caught and rejected once this
    session for a different suggestion (`_genuine_comment_lines`).

    A code-block/blockquote node's WHOLE byte range is excluded in one
    step (no need to descend further -- everything inside a fenced code
    block is definitionally quoted, including a directive that happens
    to look like it starts a new blockquote/fence). Byte ranges are
    converted to CHARACTER offsets (`str.find`/regex `Match.span()`
    operate in characters, tree-sitter in UTF-8 bytes) via a `bytes.
    decode` slice -- this repo's own ASCII-only convention (CLAUDE.md)
    means the two coincide in practice, but this stays correct even if
    a ticket body ever contains non-ASCII text."""
    all_ranges, _double_quote_only = _quoted_and_double_quote_char_ranges(body)
    return all_ranges


# frob:ticket T-2243
def _double_quote_char_ranges(body: str) -> tuple[tuple[int, int], ...]:
    """The STRICT SUBSET of `_quoted_char_ranges(body)` produced by a
    matched ASCII double-quote pair alone (T-2243) -- excludes fenced/
    indented code, blockquote, and inline-code-span ranges. TICK006's own
    id-side check (`frob.gates._tickets_gate._tick006_phantom_ids`) needs
    exactly this narrower set, not the full union `_quoted_char_ranges`
    returns: T-1700 already established that an id styled in `` `backtick
    code` `` right after plain-prose "Filed:" is a real, checkable claim
    (`tests/test_gates.py::TestTick006PhantomFiling::
    test_backtick_styled_id_in_a_real_claim_still_fires`) -- applying the
    FULL `_quoted_char_ranges` set (which also excludes code spans) to
    the id's own offset would silently regress that exact precedent.
    Only a double-quoted id is new T-2243 prose-not-citation territory;
    a code-spanned id was already a settled, tested, opposite case."""
    _all, double_quote_only = _quoted_and_double_quote_char_ranges(body)
    return double_quote_only


def _quoted_and_double_quote_char_ranges(
    body: str,
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    """The shared walk `_quoted_char_ranges` and `_double_quote_char_
    ranges` both need, run once: `(every_quoted_range, double_quote_only_
    ranges)`, both character-offset, both from the SAME parse (T-2243;
    avoids parsing `body` twice for two callers wanting overlapping but
    distinct subsets)."""
    from tree_sitter_language_pack import get_parser

    body_bytes = body.encode("utf-8")
    block_tree = get_parser("markdown").parse(body_bytes)
    inline_parser = get_parser("markdown_inline")
    byte_ranges: list[tuple[int, int]] = []
    double_quote_byte_ranges: list[tuple[int, int]] = []

    def walk_block(node) -> None:  # noqa: ANN001
        if node.type in ("fenced_code_block", "indented_code_block", "block_quote"):
            byte_ranges.append((node.start_byte, node.end_byte))
            return
        if node.type == "inline":
            inline_text = body_bytes[node.start_byte : node.end_byte]
            inline_tree = inline_parser.parse(inline_text)
            local_code_spans: list[tuple[int, int]] = []

            def walk_inline(inline_node, base: int) -> None:  # noqa: ANN001
                if inline_node.type == "code_span":
                    span = (
                        base + inline_node.start_byte,
                        base + inline_node.end_byte,
                    )
                    byte_ranges.append(span)
                    local_code_spans.append(
                        (inline_node.start_byte, inline_node.end_byte)
                    )
                    return
                for child in inline_node.children:
                    walk_inline(child, base)

            walk_inline(inline_tree.root_node, node.start_byte)
            for s, e in _quoted_span_ranges(inline_text, local_code_spans):
                span = (node.start_byte + s, node.start_byte + e)
                byte_ranges.append(span)
                double_quote_byte_ranges.append(span)
            return
        for child in node.children:
            walk_block(child)

    walk_block(block_tree.root_node)

    def byte_to_char(offset: int) -> int:
        return len(body_bytes[:offset].decode("utf-8"))

    return (
        tuple((byte_to_char(s), byte_to_char(e)) for s, e in byte_ranges),
        tuple((byte_to_char(s), byte_to_char(e)) for s, e in double_quote_byte_ranges),
    )


def _is_quoted(pos: int, quoted_ranges: tuple[tuple[int, int], ...]) -> bool:
    """`True` when character offset `pos` (a regex match's own `start()`)
    falls inside one of `_quoted_char_ranges`'s ranges -- the shared
    predicate every directive-extraction function below applies before
    accepting a match as a live DECLARATION rather than a quoted
    DISCUSSION (T-2218)."""
    return any(start <= pos < end for start, end in quoted_ranges)



# T-2851: BUG002/must-still-pass repro-classification family moved to
# frob.gates._bug_repro (see its own module doc); re-exported here so
# frob.gates.__init__'s existing import line needs no change.
from frob.gates._bug_repro import (  # noqa: E402, F401 -- re-exported for frob.gates.__init__'s existing import line
    BugReproOutcome,
    bug_repro_outcome_at_ref,
    bug_repro_violations,
    designated_repro_test,
    must_still_pass_violations,
)

