---
id: T-2218
title: 'A ticket body that DISCUSSES a waiver is indistinguishable from one that DECLARES
  it: T-2215''s own prose describing the escape-hatch shape would satisfy the BUG003
  waiver regex and self-waive'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_mutation_evidence.py
- tests/test_gates_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: repro + must-still-pass controls for markdown-aware directive quoting
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_inline_code_span_does_not_suppress
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_fenced_code_block_does_not_suppress
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_blockquote_does_not_suppress
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_genuine_declared_waiver_still_suppresses
- tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_directive_inside_inline_code_span_does_not_recognize
- tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_genuine_declared_directive_still_recognized
- tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_directive_inside_fenced_code_block_is_not_extracted
- tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_genuine_directive_alongside_quoted_example_still_extracted
- tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_fenced_quoted
- tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_inline_span_quoted
- tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_blockquote_quoted
- tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_indented_quoted
- tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_plain_text_not_quoted
designated_repro_test: tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_inline_code_span_does_not_suppress
acceptance:
- text: 'Measured instance, and it is self-referential: tickets/T-2215/ticket.md:56
    reads ''escape-hatch shape (a `frob:waive BUG003 reason="..."` body-text ...)''
    -- prose DESCRIBING the mechanism, with the directive inside backticks as an example.
    _BUG002_WAIVER_RE (src/frob/gates/_mutation_evidence.py:238, pattern frob:waive\s+BUG00N\s+reason="([^"]*)")
    matches it and extracts ''...'' as the reason. So the ticket that documents the
    waiver mechanism would waive itself. 13 ticket files currently contain a matching
    string; most are genuine declarations, which is exactly why the two cannot be
    told apart today. This test MUST fail against current main.'
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_inline_code_span_does_not_suppress
  - tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_fenced_code_block_does_not_suppress
  - tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_blockquote_does_not_suppress
- text: 'Distinguish DECLARATION from DISCUSSION structurally, not by pattern tightening.
    A ticket body is markdown, so the grammar available is markdown''s: a directive
    inside a fenced code block, an inline code span, or a blockquote is being QUOTED,
    not declared. Parse the body as markdown and ignore code spans/blocks -- do not
    reach for frob.lang raw_tree/COMMENT_TYPES here, which answers a different question
    (is line N of a SOURCE file inside a grammar comment) and returns an empty set
    for any path without a registered grammar, including tickets.md. An implementer
    already checked that and was right to refuse it.'
  evidence:
  - tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_fenced_quoted
  - tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_inline_span_quoted
  - tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_blockquote_quoted
  - tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_indented_quoted
- text: Do NOT fix this by requiring the directive at column 0 or on its own line
    -- a documenting author will naturally write it on its own line too, and a declaring
    author may indent it under a heading. Do NOT narrow the reason= capture to exclude
    '...' specifically; that fixes one literal and leaves every other quoted example.
    Fix BUG002, BUG003, no-behavior-change and must-still-pass together -- they share
    the same raw regex-over-ticket.body mechanism (_BUG002_WAIVER_RE's precedent is
    cited in-file at line 244), so fixing one leaves the identical hole in the others.
  evidence:
  - tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_genuine_declared_waiver_still_suppresses
  - tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_genuine_declared_directive_still_recognized
  - tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_genuine_directive_alongside_quoted_example_still_extracted
- text: 'SWEEP RESULT, so the next implementer does not re-derive it: 21 sites in
    src/ compile a frob: directive regex, and most are already safe because they ANCHOR
    to a comment marker -- _WAIVE_SINGLE_LINE_RE uses ^\s*(#|//)\s*frob:waive, _DOC_INVARIANT_MARKER_RE
    requires <!-- ... -->, _CALLEE_RAISES_PRESENT_RE requires a leading #. The unanchored,
    prose-exposed ones are _mutation_evidence.py''s four (BUG002, BUG003, no-behavior-change,
    must-still-pass), which all scan a whole ticket.body and are this ticket''s scope.
    Two others share the shape but with far smaller exposure and live in other files:
    _WAIVE_DOC004_RE and _WAIVE_DOC006_RE scan only a bounded lookbehind WINDOW of
    doc lines near the finding (src/frob/gates/_docptr.py:164), not a whole body.
    Do not widen this ticket''s scope to them; note in the Done report whether the
    markdown-structural approach you land here would transfer, so a follow-up can
    be sized honestly.'
  evidence:
  - tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_plain_text_not_quoted
threat: null
component: null
anchor: false
anchor_reason: null
---
