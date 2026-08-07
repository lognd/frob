---
id: T-1700
title: TICK006 fires on a Done report DISCUSSING a code-spanned ticket id; reuse DOC011's
  code-span stripping
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_doclink_docanchor.py
- tests/unit/gates/test_doc011.py
- docs/modules/gates.md
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_markdown_scan.py
- tests/test_gates.py
- tests/unit/gates/test_markdown_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: the shared code-span-stripping helper needs a new home both _doclink_docanchor.py
    and _tickets_gate.py can import from without one owning the other's private namespace;
    TICK006's own regression test lives in tests/test_gates.py per its existing frob:tests
    convention
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/gates/_markdown_scan.py
  reason: the shared code-span-stripping helper needs a new home both _doclink_docanchor.py
    and _tickets_gate.py can import from without one owning the other's private namespace;
    TICK006's own regression test lives in tests/test_gates.py per its existing frob:tests
    convention
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_gates.py
  reason: the shared code-span-stripping helper needs a new home both _doclink_docanchor.py
    and _tickets_gate.py can import from without one owning the other's private namespace;
    TICK006's own regression test lives in tests/test_gates.py per its existing frob:tests
    convention
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/gates/test_markdown_scan.py
  reason: direct unit tests for the new shared strip_code_spans helper, including
    the double-backtick regression this ticket's own investigation found as the actual
    root cause
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_double_backtick_span_is_blanked
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_single_backtick_span_is_blanked
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_triple_backtick_span_is_blanked
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_fenced_code_block_is_blanked
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_line_wrapped_inline_span_is_blanked_as_one_token
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_blank_line_is_not_treated_as_inside_a_span
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_id_inside_double_backtick_span_is_not_flagged
- tests/test_gates.py::TestTick006PhantomFiling::test_code_spanned_filed_claim_does_not_fire
- tests/test_gates.py::TestTick006PhantomFiling::test_backtick_styled_id_in_a_real_claim_still_fires
- tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_run_length_must_match_to_close
designated_repro_test: null
threat: null
component: null
---
Main went red on T-1542's land with two TICK006 errors:

    T-1542's Done report claims T-0104 was filed, but T-0104 resolves ...
    T-1542's Done report claims T-9999 was filed, but T-9999 resolves ...

Neither is a claim. The Done report is EXPLAINING that those ids are
inline-code-span examples in docs -- `` `Filed: T-0104` `` and
`` `waive ... ticket "T-9999";` `` -- which illustrate the id SYNTAX
rather than naming a real ticket. The report says so in as many words,
and TICK006 fired on the explanation.

Root cause: TICK006 scans Done-report prose for anything matching the
ticket-id shape and asserts it must resolve, with no notion of context.
It cannot tell "I filed T-1234" from "`T-9999` is what a placeholder
looks like". That is a lexical rule pretending to be a semantic one.

The fix already exists in a sibling gate. DOC011 -- in this same
`_doclink_docanchor.py` -- strips inline code spans before scanning
precisely because an id inside backticks is being MENTIONED, not
referenced. T-1542's own Done report documents that exemption, which is
what makes this doubly sharp: the gate fired on prose explaining the
exemption the neighbouring gate correctly applies.

Do this:

1. Extract DOC011's code-span stripping into ONE shared helper and have
   both rules use it. Do not copy the logic -- two copies of a scanning
   rule is a desync waiting to happen, and this repo has paid for that
   before.
2. Apply it to TICK006's Done-report scan.
3. Consider whether TICK006 can go further than code spans and become
   genuinely semantic: a "claims X was filed" assertion has a recognisable
   shape (a filing verb near the id) that a bare id-in-prose does not. If
   that is cheap and reliable, do it; if it needs guesswork, stop at the
   code-span fix rather than shipping a heuristic that fails differently.
   State which you chose and why in the Done report.

Regression coverage must include the EXACT shape that broke main: a Done
report whose prose discusses a code-spanned id that does not resolve, and
which must not fire.

Note for whoever takes this: T-1544 is already queued for a Tier-A
auto-fix of TICK006 phantom citations (refile+renumber). That ticket
assumes the finding is real and repairs the citation. This ticket is
upstream of it -- if the finding is a false positive, auto-fixing it
would rewrite correct prose. Land this first, and leave a note on T-1544
saying so.