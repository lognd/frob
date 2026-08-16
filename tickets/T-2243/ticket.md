---
id: T-2243
title: TICK006's Tier-A auto-fix treats a ticket id mentioned in Done-report PROSE
  as a citation and auto-files a junk ticket -- 5 occurrences, 3 still queued
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_mutation_evidence.py
- tests/test_gates.py
- tests/test_gates_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'Measured: TICK006''s citation EXTRACTION (_tick006_phantom_ids/_tick006_done_report_text)
    lives in _tickets_gate.py, not _fix_engine.py (which only consumes the extracted
    ids). The declared repro (T-2226''s real Done report text, archaeologically confirmed
    via git show 3a688f28b:tickets/T-2226/done-report.md and the resulting T-2238
    body''s exact quoted excerpt) shows the false positive is NOT a code-span/blockquote/fence
    case T-2218''s existing _quoted_char_ranges already covers -- it is an ASCII double-quoted
    clause inside a plain paragraph list item. Extending the SHARED _quoted_char_ranges
    primitive (home: _mutation_evidence.py, T-2218) to also recognize matched double-quote
    spans is the single reuse point for both its existing BUG003 consumer and this
    ticket''s TICK006 consumer, per the ticket''s own ''one home for one rule'' directive.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: 'Measured: TICK006''s citation EXTRACTION (_tick006_phantom_ids/_tick006_done_report_text)
    lives in _tickets_gate.py, not _fix_engine.py (which only consumes the extracted
    ids). The declared repro (T-2226''s real Done report text, archaeologically confirmed
    via git show 3a688f28b:tickets/T-2226/done-report.md and the resulting T-2238
    body''s exact quoted excerpt) shows the false positive is NOT a code-span/blockquote/fence
    case T-2218''s existing _quoted_char_ranges already covers -- it is an ASCII double-quoted
    clause inside a plain paragraph list item. Extending the SHARED _quoted_char_ranges
    primitive (home: _mutation_evidence.py, T-2218) to also recognize matched double-quote
    spans is the single reuse point for both its existing BUG003 consumer and this
    ticket''s TICK006 consumer, per the ticket''s own ''one home for one rule'' directive.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_gates.py
  reason: 'Measured: TICK006''s citation EXTRACTION (_tick006_phantom_ids/_tick006_done_report_text)
    lives in _tickets_gate.py, not _fix_engine.py (which only consumes the extracted
    ids). The declared repro (T-2226''s real Done report text, archaeologically confirmed
    via git show 3a688f28b:tickets/T-2226/done-report.md and the resulting T-2238
    body''s exact quoted excerpt) shows the false positive is NOT a code-span/blockquote/fence
    case T-2218''s existing _quoted_char_ranges already covers -- it is an ASCII double-quoted
    clause inside a plain paragraph list item. Extending the SHARED _quoted_char_ranges
    primitive (home: _mutation_evidence.py, T-2218) to also recognize matched double-quote
    spans is the single reuse point for both its existing BUG003 consumer and this
    ticket''s TICK006 consumer, per the ticket''s own ''one home for one rule'' directive.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: 'Measured: TICK006''s citation EXTRACTION (_tick006_phantom_ids/_tick006_done_report_text)
    lives in _tickets_gate.py, not _fix_engine.py (which only consumes the extracted
    ids). The declared repro (T-2226''s real Done report text, archaeologically confirmed
    via git show 3a688f28b:tickets/T-2226/done-report.md and the resulting T-2238
    body''s exact quoted excerpt) shows the false positive is NOT a code-span/blockquote/fence
    case T-2218''s existing _quoted_char_ranges already covers -- it is an ASCII double-quoted
    clause inside a plain paragraph list item. Extending the SHARED _quoted_char_ranges
    primitive (home: _mutation_evidence.py, T-2218) to also recognize matched double-quote
    spans is the single reuse point for both its existing BUG003 consumer and this
    ticket''s TICK006 consumer, per the ticket''s own ''one home for one rule'' directive.'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_gates.py::TestTick006PhantomFiling::test_prose_quoting_another_tickets_criterion_does_not_fire
- tests/test_gates.py::TestTick006PhantomFiling::test_genuine_dangling_citation_outside_any_quote_still_fires
- tests/test_gates.py::TestTick006PhantomFiling::test_code_spanned_filed_claim_does_not_fire
- tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_double_quoted_span_quoted
designated_repro_test: null
acceptance:
- text: 'A Done report whose PROSE mentions an unresolvable ticket id does not trigger
    a phantom filing (fixture: T-2226''s real Done report text, known to have produced
    T-2238)'
  evidence:
  - tests/test_gates.py::TestTick006PhantomFiling::test_prose_quoting_another_tickets_criterion_does_not_fire
- text: 'MUST-STILL-PASS: a genuine dangling citation still triggers TICK006 and still
    auto-files its recovery ticket'
  evidence:
  - tests/test_gates.py::TestTick006PhantomFiling::test_genuine_dangling_citation_outside_any_quote_still_fires
- text: An id inside a fenced block, inline code span, or blockquote is treated as
    prose, consistent with T-2218's landed semantics
  evidence:
  - tests/test_gates.py::TestTick006PhantomFiling::test_code_spanned_filed_claim_does_not_fire
- text: Classification derives from parsed markdown structure, never indentation or
    surrounding-word heuristics
  evidence:
  - tests/test_gates.py::TestTick006PhantomFiling::test_prose_quoting_another_tickets_criterion_does_not_fire
  - tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_double_quoted_span_quoted
threat: null
component: null
anchor: false
anchor_reason: null
---
# TICK006's Tier-A auto-fix reads a ticket id MENTIONED IN PROSE as a citation, and auto-files a junk ticket every time

## Measured evidence: five occurrences, three still polluting the queue

Every one of these was created automatically by the land path, not by a human:

    T-1976  dropped   Recovered from T-1944's phantom TICK006 citation of T-draft-4a627425
    T-2035  dropped   Recovered from T-2036's phantom TICK006 citation of T-2030
    T-2113  queued    Recovered from T-2105's phantom TICK006 citation of T-2111
    T-2228  queued    Recovered from T-2215's phantom TICK006 citation of T-2218
    T-2238  queued    Recovered from T-2226's phantom TICK006 citation of T-draft-0bd874ac

Two were manually dropped as junk. **Three are still sitting queued**, occupying the
backlog and the rot report, describing work nobody ever intended.

The two most recent are directly traceable. T-2226's Done report DISCUSSED
`T-draft-0bd874ac` as the subject of its investigation -- the whole ticket was about
repairing records that name that dead draft id -- and the land auto-filed T-2238 from
that prose. T-2215's Done report mentioned `T-2218` while explaining an escalation, and
the land auto-filed T-2228.

So writing an accurate Done report about ticket ids CREATES junk tickets. The better the
prose, the more phantoms.

## This is the same defect class that was just fixed one layer over

T-2218 (landed today, `64511427fb3e`) fixed exactly this shape in
`src/frob/gates/_mutation_evidence.py`: directive regexes scanned a whole ticket body, so
prose DISCUSSING a directive was indistinguishable from prose DECLARING one. The fix
parses the body with tree_sitter `markdown`/`markdown_inline` and skips matches falling
inside fenced blocks, blockquotes, and inline code spans -- a real grammatical
distinction. That primitive now exists and is landed. This ticket is the same fix for the
TICK006 citation path.

T-1662 ("EPIC: every check must decide from semantics, never a lexical match") is the
standing epic for this family and is in-progress, but no leaf reaches this code path --
which is why it has recurred five times.

## Do NOT fix it this way

- **Do NOT filter out only `T-draft-*` ids.** Three of the five phantoms cite REAL ticket
  ids (T-2030, T-2111, T-2218). The defect is prose-vs-citation, not draft-vs-real.
- **Do NOT disable the Tier-A auto-fix.** A genuine dangling citation IS worth catching;
  `_fix_engine.py:293`'s handler exists for a real reason. Removing it trades a noisy
  guard for a silent one.
- **Do NOT filter by "is this id in a Done report".** Done reports legitimately carry real
  citations too. The distinction is grammatical position (prose vs directive/citation),
  not which file it lives in.
- **Do NOT hand-write a new markdown scanner.** T-2218's `_quoted_char_ranges` already
  parses ticket-body markdown with the same grammar-loading primitive `frob.lang` uses.
  Reuse it. Two homes for one rule is the defect shape T-1966 covers.
- **Do NOT retroactively "fix" the five existing phantoms as part of this.** Cleaning them
  up is a separate, trivial act; the point here is that no sixth one is ever created.

## Acceptance criteria

1. (MUST FAIL FIRST) A Done report whose PROSE mentions a ticket id that resolves to
   nothing does not trigger a phantom filing. Use T-2226's real Done report text
   (mentioning `T-draft-0bd874ac`) as the fixture -- it is on main and is known to have
   produced T-2238. Confirm `--check-repro` reads FAILED_AT_PARENT before the fix.
2. MUST-STILL-PASS CONTROL, the critical half: a GENUINE dangling citation still triggers
   TICK006 and still auto-files its recovery ticket. A fix that stops detecting real
   dangling citations would satisfy criterion 1 and silently disable a working guard --
   this repo has shipped exactly that failure before.
3. An id inside a fenced code block, inline code span, or blockquote is treated as prose,
   consistent with T-2218's landed semantics.
4. Classification derives from the parsed markdown structure, never from position
   heuristics, indentation, or surrounding-word matching. Standing user directive:
   token/grammar, never lexical.

## Scope note

The phantom-citation handling lives at `src/frob/gates/_fix_engine.py:293-310` (its own
comments describe the phantom-draft-citation case and the claim window). The citation
EXTRACTION that feeds it may live elsewhere -- trace it and widen scope with
`frob ticket scope --add <path> --reason "<measured>"` rather than guessing a file from a
module name. Do not edit outside scope.