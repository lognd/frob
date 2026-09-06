---
id: T-4098
title: SCOPE002 promoted to error by T-3844 but is structurally unwaivable post ledger-v2
  (no tickets.md file exists to attach frob:waive to)
state: queued
kind: bug
origin: agent
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
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'verified the claim in source (gates/__init__.py:3651 emits SCOPE002 with
    file=tickets.md, which ledger v2 removed) and recorded what it explains: every
    ''disclosed as disproportionate'' SCOPE002 report from implementers today was
    forced, not chosen. Also noted that T-3844''s severity ratchet turned a latent
    unwaivable warning into an unwaivable blocking error'
  actor: logan
  at: '2026-09-06'
  old_length: 0
  new_length: 2844
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

## VERIFIED INDEPENDENTLY, AND THIS EXPLAINS A DAY OF FRICTION I HAD MISREAD

Confirmed in source:

    src/frob/gates/__init__.py:3649-3651
        rule="SCOPE002",
        file="tickets.md",

    $ ls tickets.md
    ls: cannot access 'tickets.md': No such file or directory

The finding is emitted against a path that ledger v2 removed. A `frob:waive
SCOPE002` would have to live in a file that does not exist, so the rule is
UNWAIVABLE BY CONSTRUCTION. That is the TWELFTH no-exit instance in this queue and
one of the cleanest: not a hatch that is awkward or misplaced, but one that
addresses a file deleted by a migration.

THIS RETROACTIVELY EXPLAINS A PATTERN I HAD BEEN MISREADING ALL DAY. Multiple
implementers reported SCOPE002 findings as "disclosed and accepted as
disproportionate scope-closure noise", citing the T-3914/T-4019 precedent, and I
read that as agents exercising judgement about closure breadth. THEY WERE NOT
CHOOSING TO DISCLOSE RATHER THAN WAIVE -- THEY COULD NOT WAIVE. Every one of those
disclosures was the only move available. Instances today: T-3947/T-3948 (30-367+
findings for a one-line fix), T-4000 (~110 findings), T-4013 (343 warnings for a
two-function fix), T-4019, T-4085 (9 findings, `--add` also blocked by a lease).

IT COMPOUNDS WITH A DELIBERATE DECISION OF MINE, and that is the part worth
stating plainly. T-3844 promoted SCOPE002 to `error` as part of the blanket
"every error possible rather than a warning" ratchet the owner asked for. That
directive was right, and this rule was a latent no-exit at the time: promoting it
turned an unwaivable warning into an unwaivable BLOCKING ERROR. So a correct
policy decision and a pre-existing defect combined into something neither would
have been alone. NOTE THE ORDER OF OPERATIONS FOR THE FIX: making the waiver
reachable is the prerequisite; re-examining the severity is a separate question
and should not be used as a shortcut around it.

WHAT TO DETERMINE FIRST: how many OTHER rules emit against `file="tickets.md"`.
A quick grep shows the same literal in `_bug_repro.py` (x4), `_debt_deprecated.py`
and `gates/__init__.py`. Each is a candidate for the identical defect -- a finding
anchored to a file the ledger-v2 cutover removed. Classify all of them and report
which are unwaivable; fixing SCOPE002 alone would leave siblings in the same
state.

RELATED: T-4050 (the scope-denominator epic) is about SCOPE002 firing over the
wrong SET. This ticket is about being unable to silence it once it fires. Both are
needed -- narrowing the denominator reduces how often the no-exit is reached, and
does not remove it.

ADDITIONAL ACCEPTANCE
- Every rule emitting against `file="tickets.md"` enumerated and classified.
- The waiver made reachable BEFORE any severity re-examination.
- A fixture proving a SCOPE002 finding can actually be waived.
