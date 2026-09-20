---
id: T-2857
title: 'the frob comment DSL drops malformed directives SILENTLY: four distinct failure
  modes measured in one session, each leaving a finding unsuppressed with no diagnostic'
state: done
kind: bug
origin: agent
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- docs/modules/graph.md
- tests/unit/graph/test_dsl_markdown_waive.py
- tickets/T-2869/ticket.md
- tickets/T-2870/ticket.md
evidence_scope:
- tests/unit/graph/test_dsl_markdown_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: docs/tests for the dsl.py fix, plus the two out-of-scope follow-up tickets
    this ticket filed
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tests/unit/graph/test_dsl_markdown_waive.py
  reason: docs/tests for the dsl.py fix, plus the two out-of-scope follow-up tickets
    this ticket filed
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tickets/T-2869/ticket.md
  reason: docs/tests for the dsl.py fix, plus the two out-of-scope follow-up tickets
    this ticket filed
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tickets/T-2870/ticket.md
  reason: docs/tests for the dsl.py fix, plus the two out-of-scope follow-up tickets
    this ticket filed
  actor: logan
  at: '2026-08-22'
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 3897
  new_length: 5341
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 5341
  new_length: 6649
evidence:
- tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_unescaped_internal_quote_is_reported_not_silently_accepted
- tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_escaped_internal_quote_still_parses_cleanly
- tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_well_formed_waiver_of_an_honored_rule_still_suppresses
- tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_reason_continuing_onto_a_later_physical_line_is_not_flagged
- tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_describes_with_a_broken_symref_is_reported_not_silently_dropped
- tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_enumerates_missing_required_members_attr_is_reported
- tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_well_formed_describes_still_parses_cleanly
- tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_well_formed_ticket_and_until_still_parse_cleanly
designated_repro_test: tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_unescaped_internal_quote_is_reported_not_silently_accepted
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3bde41b90c55e4cdc9a566744109f4659fd49990
---
## Four distinct silent failure modes in one session

Every one of these caused a `frob:` directive to be SILENTLY IGNORED -- the
file kept its old severity, no error, no warning, no exit code. Each was
caught only because the agent RE-MEASURED rather than assuming its edit took
effect. An agent that trusted its own edit would have shipped a
non-functioning directive and believed the finding was resolved.

1. UNESCAPED DOUBLE-QUOTE inside `reason="..."`. Two separate agents hit
   this on different tickets. The directive parses as malformed; the file
   stays unwaived. One agent's note: "the file stayed `warning` after
   insertion -- re-measurement caught it, not assumption."

2. UNQUOTED `reason=` VALUE. A third agent wrote `reason=` with a bare
   value; the land-time BUG002 check silently did not recognize it. Fixed by
   re-setting the body with proper quoting.

3. PROSE MATCHING THE DIRECTIVE PATTERN. A docstring in a test contained the
   substring `frob:waive reason ... still binds` -- describing a directive,
   not declaring one. The scanner flagged it as a malformed directive.
   Filed separately as T-2854. The scanner cannot distinguish a directive
   from prose ABOUT a directive.

4. TRAILING SPACE BEFORE A `\` CONTINUATION. The continuation fold is plain
   concatenation, so a trailing space before the backslash breaks a dotted
   `Class.method` reference into invalid syntax. Found while splitting
   `_host_isolation.py`.

## Why this is a coherent bug, not four papercuts

The comment DSL is load-bearing: `frob:waive`, `frob:doc`, `frob:tests`,
`frob:enforces`, `frob:no-behavior-change` and friends are how every gate
finding gets dispositioned. Tonight the fleet promoted four rules to ERROR
severity (I001, REF001, REF002, REG008, and LARGE001), which means a
silently-dropped waiver now REDS MAIN rather than merely leaving a warning.

The failure mode is uniform: malformed input produces silence rather than a
diagnostic. That is this repo's dominant bug class (silent zero, epic
T-2391) sitting inside the mechanism used to suppress findings -- the worst
possible place for it, because the user's intent was explicitly "suppress
this", and the observed behavior is "suppressed nothing" with no signal.

## Required shape

A directive that LOOKS like a directive but does not parse must produce a
LOUD, LOCATED diagnostic naming the file, line, and what specifically failed
to parse -- never silence. Prefer failing the check over silently ignoring.

Note there is already a `malformed directive` WARNING emitted in some paths
(mode 3 above produced one). So part of the machinery exists. Determine why
modes 1, 2 and 4 do not reach it -- whether they fail earlier, are filtered,
or are simply not recognized as directive-shaped at all. Instrument rather
than infer.

For mode 3 specifically (prose false positive), the fix is the inverse:
tighten recognition so prose describing a directive is not treated as one.
Modes 1/2/4 want LOUDER failure; mode 3 wants NARROWER recognition. Do not
let a fix for one make the other worse -- that tension is the real design
problem here.

## Positive controls, both directions

- Each of the four malformed shapes above produces a located diagnostic
  naming file and line. Plant all four as fixtures; they are cheap.
- A correctly-formed directive of each kind still parses and still
  suppresses its finding. Without this, a stricter parser silently breaks
  every existing waiver in the repo -- and there are hundreds.
- Prose in a docstring or comment that merely mentions a directive does NOT
  warn (T-2854's case).
- A directive using a legitimate `\` continuation, WITHOUT a trailing space,
  still folds correctly.

## Related

T-2854 covers mode 3 alone. This ticket is the class. If they are worked
separately, whoever takes T-2854 must not tighten recognition in a way that
makes modes 1/2/4 quieter.

<!-- narrative-moved:src/frob/graph/dsl.py:573:T-2857 -->
frob:ticket T-2857
T-2857 mode 4: these five verbs used to sit in `_MD_HANDLED_VERBS` below,
on the assumption that reaching this function with one of them meant
"already turned into a real edge, nothing to report". That assumption is
false: `markdown_anchors`'s loop only calls `_unhandled_markdown_
directive` on a line AFTER `_directive_edge` has already tried and
FAILED to match it (see that loop's `if directive_edge is not None:
continue` immediately above the call) -- so a line whose verb is one of
these five reaching this function is proof the line shape-matched loosely
(`_ANY_MD_DIRECTIVE_RE`) but failed the strict per-verb regex
(`_DESCRIBES_RE`/`_ENUMERATES_RE`/`_UNTIL_RE`/`_TICKET_MD_RE`/
`_DOC_MD_RE`) -- e.g. a `frob:describes` symref broken by an embedded
space from a bad line-wrap (T-2857's own measured repro: `frob:describes
path::Class.metho d_further_here` -- the wrapped continuation's trailing
space landed mid-identifier). Treating them as unconditionally "handled"
made that failure completely silent: verb membership alone said "fine",
with no check that THIS line actually produced the edge. A well-formed
directive of any of these five verbs can never reach this function in
the first place (it `continue`s out of the loop above), so moving them
out of the blanket-accept set below cannot produce a new false positive
on anything that already parses.

<!-- narrative-moved:src/frob/graph/dsl.py:539:T-2857 -->
frob:ticket T-2857
T-2857 mode 1: `_MD_WAIVE_RE` above only checks for the OPENING
`reason="` -- it never verified the value actually closes, so a bare
unescaped `"` inside the reason text (a genuine incident: two agents
wrote `reason="the "old" foo"` in a markdown doc) silently matched as if
well-formed, extracting the wrong (truncated) `rule`/never checking the
rest of the line at all -- `_unhandled_markdown_directive` then saw a
recognized rule and returned `None`, no diagnostic, ever. This
escape-aware value grammar (`\"` does NOT terminate the value, mirroring
the informal backslash-escape convention this repo's own docs already
use, e.g. `docs/modules/tickets-verify-sweep.md`'s `reason="... ==
\"select-batch-tests\" ..."`) finds the REAL closing quote so
`_md_waive_reason_tail_error` below can tell a genuinely early close
(leftover text before `-->`, the incident's shape) from a value that
legitimately continues onto a later physical line (this per-line scanner
cannot see across lines at all, so that case is left exactly as
tolerant as before rather than guessed at -- see that function's
docstring for the measured false-positive check against all 219
tracked `<!-- frob:waive` sites in this repo, T-2857's positive
control).