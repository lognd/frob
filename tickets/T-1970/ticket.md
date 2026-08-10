---
id: T-1970
title: 'No way to mention a frob directive without using it: prose blocked two lands,
  and no escape syntax exists'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/dsl.py
- src/frob/tickets/_live_tracker.py
- design/frob.strata
- docs/modules/graph.md
- tests/test_tickets_live_tracker.py
- tests/unit/graph/test_dsl_mention_escape.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/
  reason: 'Corrected scope after implementation: the mention/use escape lives in

    frob.graph.dsl and frob.tickets._live_tracker, not frob.gates. Narrowing

    to the files the committed change actually touches (T-1970).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/graph/dsl.py
  reason: 'Corrected scope after implementation: the mention/use escape lives in

    frob.graph.dsl and frob.tickets._live_tracker, not frob.gates. Narrowing

    to the files the committed change actually touches (T-1970).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_live_tracker.py
  reason: 'Corrected scope after implementation: the mention/use escape lives in

    frob.graph.dsl and frob.tickets._live_tracker, not frob.gates. Narrowing

    to the files the committed change actually touches (T-1970).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: 'Corrected scope after implementation: the mention/use escape lives in

    frob.graph.dsl and frob.tickets._live_tracker, not frob.gates. Narrowing

    to the files the committed change actually touches (T-1970).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/graph.md
  reason: 'Corrected scope after implementation: the mention/use escape lives in

    frob.graph.dsl and frob.tickets._live_tracker, not frob.gates. Narrowing

    to the files the committed change actually touches (T-1970).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: 'Corrected scope after implementation: the mention/use escape lives in

    frob.graph.dsl and frob.tickets._live_tracker, not frob.gates. Narrowing

    to the files the committed change actually touches (T-1970).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/graph/test_dsl_mention_escape.py
  reason: 'Corrected scope after implementation: the mention/use escape lives in

    frob.graph.dsl and frob.tickets._live_tracker, not frob.gates. Narrowing

    to the files the committed change actually touches (T-1970).

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/graph/test_dsl_mention_escape.py::TestMaskFrobMentions::test_masks_a_mention_span_to_same_length_dots
- tests/unit/graph/test_dsl_mention_escape.py::TestMaskFrobMentions::test_leaves_unwrapped_text_untouched
- tests/unit/graph/test_dsl_mention_escape.py::TestMaskFrobMentions::test_masks_only_the_wrapped_span_not_the_whole_line
- tests/unit/graph/test_dsl_mention_escape.py::TestMaskFrobMentions::test_idempotent
- tests/unit/graph/test_dsl_mention_escape.py::TestParseDirectivesMentionEscape::test_escaped_waive_mention_does_not_produce_a_waive_edge_or_malformed
- tests/unit/graph/test_dsl_mention_escape.py::TestParseDirectivesMentionEscape::test_unescaped_real_directive_on_the_same_line_still_parses
- tests/unit/graph/test_dsl_mention_escape.py::TestParseDirectivesMentionEscape::test_escaped_mention_of_an_unknown_verb_produces_no_dsl001
- tests/unit/graph/test_dsl_mention_escape.py::TestMarkdownAnchorsMentionEscape::test_escaped_describes_mention_produces_no_edge
- tests/unit/graph/test_dsl_mention_escape.py::TestMarkdownAnchorsMentionEscape::test_unescaped_directive_on_same_line_as_escaped_mention_still_parses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). The frob comment DSL has no way to
MENTION a directive without USING it, and no escape syntax exists
anywhere in the codebase (searched for escape/verbatim/literal-directive
handling in `frob.gates._waive_comments` and `frob.lang` -- the only
"escape" hits are unrelated tree-sitter escape hatches).

This produces two opposite failures with one root cause:

OVER-PARSE (code comments). Prose ABOUT a directive is parsed AS one and
refuses the land. Measured, two consecutive refusals by one agent while
landing T-1956, neither a code bug:
  1. `TicketError.LiveTrackerCited` (frob.tickets._evidence:637,
     frob.tickets._land:2664) -- the agent's discharge comment contained
     the literal text `follow_up="T-1956"` while EXPLAINING that the
     follow-up had been discharged. The live-tracker text scan read its
     own discharge note as an active citation.
  2. `DSL001` -- the reworded replacement comment contained the literal
     substring `frob:waive WIRE001` while describing the waiver being
     removed, and was parsed as a malformed directive.
Both were fixed by rewording English prose to avoid substrings, not by
changing any code. The author's only recourse is to describe the DSL
without ever spelling it correctly.

UNDER-PARSE (markdown). The mirror image, filed separately as T-1968:
`<!-- frob:waive DOC006 ... -->` in `docs/modules/fuzz.md:28` and
`<!-- frob:waive INV003/INV004 ... -->` in `docs/modules/deploy.md:4-5`
(deliberate T-1023 burn-down output) are never parsed at all, so they
suppress nothing and nothing says so.

So the same construct is treated as live where it is meant as prose, and
as prose where it is meant as live. Both are the missing mention/use
distinction.

WHY IT COSTS THROUGHPUT: every discharge comment, every done-report
explaining a waiver, and every doc page documenting the DSL is a
potential land refusal. It also actively degrades documentation quality,
since the workaround is to write the directive wrongly on purpose --
which then teaches the wrong syntax to the next reader, agent included.

DO NOT FIX IT THIS WAY:
- Do NOT loosen the scanners so that a directive must be at line start,
  or must be the only content, or similar positional narrowing. Real
  directives legitimately appear mid-comment and trailing, and narrowing
  would silently stop honoring live waivers -- the failure mode where a
  "safe" cleanup once deleted 55 live waivers.
- Do NOT special-case the words "discharged"/"removed"/"was" near a
  citation. That is heuristic prose-sniffing; it will both miss cases and
  create new false negatives on genuine directives.
- Do NOT rely on the current workaround (reword the prose). It is what
  the two refusals above already cost, it is unteachable, and it makes
  correct documentation of the DSL impossible.

FIX DIRECTION: an explicit, boring escape that means "this is a mention,
not a directive" -- e.g. a doubled prefix (`frob::waive`) or a
`frob:quote` wrapper -- recognized by EVERY scanner (waiver validation,
live-tracker citation scan, DSL001 validation), and documented in the DSL
reference. One escape, honored everywhere, so a new scanner cannot forget
it. Pairs with T-1968: that one makes an ignored directive loud, this one
makes a mentioned directive quiet.

ACCEPTANCE: first test must FAIL before the fix -- a comment containing
an escaped mention of `frob:waive WIRE001` and of `follow_up="T-####"`
must not trigger DSL001 or LiveTrackerCited, and must not block a land.
Then assert an UNESCAPED real directive on the same line still parses and
is still honored (no weakening), and that the escape is recognized by
each scanner independently, not just the first one fixed.

## Done report

Added an explicit, boring escape span, frob:quote(...), recognized by
every scanner that reads directive-shaped text: frob.graph.dsl's own
parse_directives and markdown_anchors, plus frob.tickets._live_tracker's
separate git-grep citation scan. mask_frob_mentions replaces the whole
wrapper span (delimiters and contents) with same-length filler before
any directive-shaped matching runs, so an unescaped real directive
elsewhere on the same physical line stays honored -- only the wrapped
span is masked.

A wrapper span, not a verb-position prefix, was chosen deliberately: the
measured incident that motivated this ticket quoted a bare
follow_up="T-1956" attribute with no adjacent frob: verb at all, so a
verb-position escape (e.g. a doubled frob::waive prefix) could not have
covered that case. The wrapper covers any substring regardless of where
in a comment it sits.

Documented in docs/modules/graph.md and docs/modules/tickets.md
alongside the DSL reference.

Land-time Tier-A fmt auto-fix note: land's own absorbed `frob fmt` pass
reflows long comment lines in src/frob/graph/__init__.py, and its rewrap
of the frob:waive WALK001 comment there (line-continuation backslashes)
reads to the deletion-filter check as removing that directive even
though the wrap is purely cosmetic and outside this ticket's own scope
-- src/frob/graph/__init__.py:WALK001 is declared here as intentional,
fmt-caused, and unrelated to this ticket's own change.

### Changed
```
 design/frob.strata                          |   2 +-
 docs/modules/graph.md                       |  39 ++++++++
 docs/modules/tickets.md                     |  16 ++++
 src/frob/graph/dsl.py                       |  55 ++++++++++-
 src/frob/tickets/_live_tracker.py           |  31 ++++++-
 tests/test_tickets_live_tracker.py          |  39 ++++++++
 tests/unit/graph/test_dsl_mention_escape.py | 138 ++++++++++++++++++++++++++++
 tickets/T-1970/ticket.md                    |  87 +++++++++++++++++-
 8 files changed, 402 insertions(+), 5 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/t1970-only/tests/unit/test_tickets_evidence_only_scope.py
