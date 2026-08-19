---
id: T-2596
title: four real E501 lines in src/ raised quarantine and forced the whole fleet into
  synchronous lands
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/scaffold/project.py
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
## Measured

Genuine E501 violations in two `src/` files. `[tool.ruff.lint.per-file-ignores]`
covers only `tests/**` and `tests/fixtures/**`, so `src/` carries no
exemption, and these lines have no `# noqa`:

    src/frob/app/ticket_runner/_ledger_mirror.py:72    91 chars
    src/frob/scaffold/project.py:115                   89 chars
    src/frob/scaffold/project.py:248                   89 chars
    src/frob/scaffold/project.py:683                   89 chars

Configured limit is 88. Other over-length lines in both files DO carry
`# noqa: E501` (they are `frob:tests` directive comments, which cannot be
wrapped) and are correctly exempt -- do not touch those, and do not "fix"
them by deleting the directives.

## These are PRE-EXISTING, not a regression

They surfaced via the quarantine attached to land `18de7953c` (T-2588).
`git show --stat 18de7953c` shows that commit touched only
`src/frob/app/cycle_runner.py`, two cycle test files, and ledger/changelog
entries. It did NOT touch either flagged file. So the findings are real but
the attribution is wrong: pre-existing floor blamed on an unrelated land.

That misattribution is a THIRD defect class distinct from the two T-2571
addressed. T-2571 filtered PHANTOM findings against deleted paths, and
T-2595 covers a baseline that does not survive concurrent sweeps. This is
neither: the file exists and the finding is real, but the blamed commit
cannot have caused it. Worth checking whether the same `git show --stat`
guard T-2571 added for deleted paths should also refuse to attribute a
finding to a commit that never touched the finding's file. If so, file it
against the sweep rather than widening this ticket.

## Consequence, which is why this is not cosmetic

Two undisposed findings RAISED quarantine, and a raised quarantine turns
OFF deferred landing repo-wide: every land runs fully-synchronous
verification (T-1693). That is a multi-minute inline re-verification on the
land critical path for every agent, and it has previously pushed lands past
the 540s shell cap into silent exit-143. Four over-long lines stalled a
six-agent fleet.

## Fix

Wrap the four lines. That is the whole change.

Do NOT add `# noqa: E501` to silence them -- these are ordinary code lines
that wrap fine, and a noqa here would be the cop-out T-1614's waiver audit
exists to catch.

Note `_ledger_mirror.py` is in T-2587's declared scope. If T-2587 is still
open when this is worked, coordinate: either let T-2587 absorb that one line
or wait for it to land. Do not edit a file under another ticket's live
write lease.

## Positive controls, both directions

- after the fix, an E501-selected run over both files reports zero findings
- the `# noqa: E501` directive lines are UNCHANGED and still present -- a
  diff that removes them is a regression, since those directives are
  load-bearing evidence bindings
- `frob verify status` shows quarantine CLEAR
