---
id: T-4044
title: 'F-243: gates-fast prints FAIL prettier with ''0 files need formatting'' in
  the same line -- a verdict over an empty subject set'
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
- src/frob/check/_native.py
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
Consumer logand.app-v2 F-243, 2026-09-06, reported independently by two of their
tickets (T-0217 and T-0210) and REPRODUCING ON AN UNMODIFIED BRANCH:

  "gates-fast prints 'FAIL prettier 0 files need formatting', an inverted label.
   `npx prettier --check` on the touched files is clean. The tool result's exit
   code is being read as failure while its own output says nothing needs
   formatting (same family as F-139 and F-165: prettier's nonzero exit with no
   diagnostic)."

A FAIL OVER ZERO SUBJECTS, PRINTED IN ONE LINE. The message states the count that
disproves it: zero files need formatting, therefore there is nothing to fail
about. This is a self-contradictory diagnostic, and this repo has a standing rule
about those -- when a diagnostic contradicts itself on its face (a count that
cannot produce the verdict, an ordering claim about one object, the same symbol
on both sides), treat it as a finding immediately whatever its severity. I
learned that rule the expensive way earlier today by walking past TDD001 printing
the same symbol on both sides of "was not committed after".

IT REPRODUCES ON AN UNMODIFIED BRANCH. That is the detail that makes this cheap
to fix and embarrassing to keep: no special state is needed, it is not a race,
and anyone running gates-fast sees it.

THE MECHANISM IS ALREADY NAMED BY THEIR OWN CROSS-REFERENCE: prettier exits
nonzero with no diagnostic (their F-139 and F-165). So the wrapper reads the EXIT
CODE as the verdict while the tool's own OUTPUT says clean, and the two disagree.
That is [[wrapper-exit-code-is-not-the-work]] -- an exit code describing the
WRAPPER rather than the work -- and it is the third time this session I have seen
that shape decide something incorrectly.

THIS IS ALSO A SUBJECT-COUNT INSTANCE, and the cleanest one yet: the gate knows
its subject count is zero AND PRINTS IT, and still returns a verdict. T-3985's
primitive would make this structurally impossible -- a gate cannot fail over an
empty subject set. Cross-reference it; if T-3985 lands first, this becomes a
regression test rather than a fix.

WHAT TO DETERMINE FIRST: why does prettier exit nonzero here at all? Do not just
invert the label or ignore the exit code -- an exit code that is nonzero for a
reason we have not identified may be reporting something real (a missing config,
an unparseable file, a version mismatch). Capture and report the actual exit
status and stderr before deciding whether to trust the output over the code. If
it turns out prettier genuinely exits nonzero on a clean run in some
configuration, the fix is to detect that case explicitly, not to stop reading
exit codes.

DO NOT fix this by suppressing the FAIL when the count is zero. That hides the
disagreement instead of resolving it, and would mask a genuine failure that
happened to report zero files.

MUST-FIRE FIXTURE: a file that genuinely needs formatting produces a FAIL.
MUST-STAY-QUIET: a clean tree produces no prettier FAIL, on an unmodified branch.
THIRD FIXTURE: a tool exiting nonzero WITH a real diagnostic is still surfaced --
the fix must not make us blind to prettier's genuine failures.

ACCEPTANCE
- The actual exit status and stderr from the clean-run case captured and
  explained, not assumed.
- Exit code and parsed output reconciled into one verdict with a stated rule for
  which wins and why.
- All three fixtures committed.