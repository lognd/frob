---
id: T-4043
title: 'F-242: frob format reports directives canonical while gate:FMT rejects the
  same lines, so users hand-wrap what the formatter should emit'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
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
Consumer logand.app-v2 F-242, 2026-09-06:

  "T-0215 hand-wrapped waiver comments with backslash continuations to satisfy
   gate:FMT AFTER `frob fmt` reported nothing to do. One of the two is wrong; the
   formatter should produce what the gate accepts."

THE USER DID THE FORMATTER'S JOB BY HAND. That is the whole finding. They ran the
canonicalizer, it declared the file clean, the gate then refused the same lines,
and the only way through was to hand-wrap directive comments with backslash
continuations -- exactly the mechanical transformation the formatter exists to
perform. A formatter that reports "nothing to do" on text its own gate rejects is
worse than no formatter, because it actively asserts the file is correct.

THIS IS THE PRODUCER/VALIDATOR DESYNC AGAIN, and it is the third instance filed
today: T-4042 (our cargo collector emits deep ids our own binder rejects as
malformed) and T-4020 (a doc anchor written correctly in a doc and truncated in
the runtime message that cites it). One half of frob produces, another half
refuses, and the user is blamed. Worth naming as a class when someone works these.

WHAT I ESTABLISHED, AND WHAT I DID NOT. There IS a shared implementation:

    src/frob/gates/_fmt_directives.py:653
        def canonicalize_text(text: str, *, path: str, limit: int | None) -> str

so this is NOT two hand-written wrappers that drifted. The suspicious part is the
`limit` parameter and how each caller resolves it. The same module documents a
deliberate sentinel (_fmt_directives.py:71-78): _DEFAULT_LIMIT is 88, and there
is an internal stand-in meaning "this language's formatter has no width limit",
which takes "the single-line branch, so a no-width-limit directive is NEVER
WRAPPED". Width is otherwise derived from ruff's line-length in pyproject.toml,
falling back to 88.

SO THE LEADING HYPOTHESIS -- AND IT IS A HYPOTHESIS, NOT A FINDING -- is that the
FORMATTER path resolves a no-limit (or a different limit) for the file in
question while the GATE path resolves 88, so one wraps and the other does not.
CONFIRM OR REFUTE BY MEASURING BOTH CALL SITES' RESOLVED `limit` FOR THE SAME
FILE before changing anything. I did not run that measurement, and this repo's
rule is that a consumer's symptom is reliable while any mechanism -- theirs or
mine -- is a hypothesis until measured.

Also check the simpler possibility first: whether the consumer's repo configures
a line-length that only one of the two paths reads.

THE FIX, whichever way the measurement goes: the formatter and the gate must
resolve the width from ONE place, and `frob format --directives --check` must be
exactly the gate's predicate. If the two can disagree at all, they will again.

DO NOT fix this by relaxing FMT001 to accept over-long directive lines. The
88-column canonical form is the point; the defect is that the formatter does not
produce it.

NOTE `frob fmt` IS A DEPRECATED ALIAS for `frob format --directives` (T-3906), so
verify the behaviour under BOTH spellings -- if the alias resolves its limit
differently from the modern verb, that is the bug and it will disappear when the
alias does.

MUST-FIRE FIXTURE: a directive comment over the limit is flagged by the gate.
MUST-STAY-QUIET: after running the formatter, the gate finds nothing -- for a
directive that needed wrapping, run through both the modern verb and the
deprecated alias.
THIRD FIXTURE: formatter and gate resolve the same width for the same file, in a
repo that configures a non-default line-length.

ACCEPTANCE
- The resolved `limit` at both call sites measured and reported before any fix.
- One shared width resolution; the formatter's --check output equals the gate's
  verdict by construction.
- All three fixtures committed.