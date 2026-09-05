---
id: T-3889
title: frob fmt ends a wrapped // directive with a backslash, emitting a -Wcomment
  footgun into the consumer's C
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as stpone FROBLEMS F-020. `frob fmt` rewrites an over-length `//`
directive comment as two lines with the first ending in a backslash.

    // frob:waive PARSE002 reason="..."        (over 80 columns)
      becomes
    // frob:waive PARSE002 reason="... \
    // ..."

IT WORKS -- the reporter confirms PARSE is waived on the next run -- and it is
LEGAL C: the compiler splices the continuation into the comment. That is exactly
why it is worth fixing rather than shrugging at. A backslash at the end of a
`//` comment is a known C footgun: it silently swallows the following line into
the comment. Here the following line is another comment so nothing is lost, but
every style guide flags the construct and some compilers warn on it under
`-Wcomment`.

SO THE DEFECT IS: FROB'S OWN FORMATTER EMITS A CONSTRUCT THAT MAKES THE
CONSUMER'S BUILD WARN. A tool whose job is enforcing code quality should not be
the thing introducing a warning into someone else's C.

THE FIX IS ALREADY HALF PRESENT. The continuation line frob writes ALREADY
starts with `//`. So the backslash is both redundant and harmful: with the
prefix repeated, the comment continues perfectly well without it. Dropping the
backslash for `//`-style comments is the whole change.

WHY THE BACKSLASH IS THERE AT ALL, and this must be checked before removing it:
in PYTHON `#` comments the wrapped directive form uses a trailing backslash, and
frob's own source is full of it (`# frob:waive ... \` continuing on the next
`#` line). If the directive PARSER requires the backslash to know a directive
continues, then removing it for C would break parsing, and the fix is
per-language on BOTH sides -- writer and reader -- not just the writer. Measure
which before changing anything: find whether the continuation is recognised by
the trailing backslash, by the repeated comment prefix, or by both.

That measurement also bears on T-3856 (DSL001 rejects `frob:todo` free-text
notes outside Python), which is likewise a per-language divergence in directive
handling. If the continuation rule is also Python-shaped, the two share a cause.
Check and cross-reference; do not assume.

DECIDE AND STATE the alternative the reporter offers: leave directive lines
UNWRAPPED entirely, on the grounds that they are read by machines rather than
humans. That is defensible and simpler, but it loses the column limit frob
itself enforces elsewhere, so it is a real trade rather than an obvious win.
Say which and why.

MUST-FIRE FIXTURE:   an over-length `//` directive is wrapped without a
                     trailing backslash and still parses as one directive.
MUST-STAY-QUIET:     Python `#` directive wrapping is unchanged (frob's own
                     source is full of it and must not be rewritten).
THIRD FIXTURE:       whatever the parser relies on, a wrapped directive in each
                     supported comment style round-trips: written by `frob fmt`,
                     read back by the directive parser, same directive.

ACCEPTANCE
- The continuation-recognition rule measured and stated (backslash, prefix, or
  both) before the writer is changed.
- `//` wrapping emits no backslash, or directive lines are left unwrapped with
  the trade stated.
- Python behaviour unchanged.
- Cross-referenced with T-3856 if the cause is shared.
- All three fixtures committed.
