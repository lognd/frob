---
id: T-2121
title: rapid-debt.jsonl is a shared append-only file every rapid land touches, so
  any ticket declaring it blocks every other land with CrossTicketLeakage (unclaimed)
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_machinery_owned_leakage.py
- src/frob/tickets/_land_release.py
- rapid-debt.jsonl
- tickets/T-2094/ticket.md
- tickets/T-2123/ticket.md
- tickets/T-2124/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_machinery_owned_leakage.py
  reason: self-contained repro test for T-2121; imports the shared land-owned-files
    constant
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/tickets/_land_release.py
  reason: self-contained repro test for T-2121; imports the shared land-owned-files
    constant
  actor: logan
  at: '2026-08-11'
- op: add
  glob: rapid-debt.jsonl
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2094/ticket.md
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2123/ticket.md
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2124/ticket.md
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption::test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it
designated_repro_test: tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption::test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Fix: _machinery_owned_leakage_exempt_paths (src/frob/tickets/_land.py)
recognizes a CATEGORY, not a filename -- any path no ticket's own
committed work can legitimately explain, because a scaffolded
pre-commit hook already refuses ANY worktree commit touching it
(CHANGELOG.md, .frob-release.json, reusing the existing
_LAND_OWNED_RELEASE_FILES constant rather than a second hand-listed
copy) or because only land/sweep machinery ever writes it
(rapid-debt.jsonl, T-1699's deferred-debt append). pyproject.toml is
deliberately excluded (only its version line is land-owned; every
other field is legitimate ticket territory) and uv.lock is
deliberately not added (a stale copy is harmless, unconditionally
re-synced at land time). _check_cross_ticket_leakage drops this set
from its "relevant changed paths" computation before any ticket's
scope is even consulted, alongside the existing tickets.md/archive
exclusion.

Repro: an unrelated, genuinely IN_PROGRESS sibling declares
rapid-debt.jsonl in its own scope; a landing ticket in a DIFFERENT
worktree appends to rapid-debt.jsonl (simulating the detached
post-land sweep) plus its own unrelated fix. Watched FAILED_AT_PARENT
against the test-only commit (4e4ae1675), then fixed; frob ticket
evidence --check-repro confirmed FAILED_AT_PARENT.

Promoted T-draft-66e99c4c (T-2118's real gap: frob ticket new accepts
an unacknowledged broad scope at filing time) to T-2118 -- collided
with a real T-2118 filed independently on main in the interim (the
same duplicate-id shape T-2105 exists to catch, hit live in this
session); recovered by reverting the promote, merging main, and
re-promoting, which landed on T-2123.

### Changed
```
 rapid-debt.jsonl                                |   1 +
 src/frob/tickets/_land.py                       |  56 +++++++-
 tests/unit/test_land_machinery_owned_leakage.py | 183 ++++++++++++++++++++++++
 tickets/T-2094/ticket.md                        |  53 ++++++-
 tickets/T-2121/ticket.md                        |  53 ++++++-
 tickets/T-2123/ticket.md                        |  24 ++++
 tickets/T-2124/ticket.md              |  26 ++++
 7 files changed, 392 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption::test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV005@src/frob/tickets/_land.py, DUP001@tests/unit/test_land_machinery_owned_leakage.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2105/src/frob/gates/_root_asset_dirs.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE001@tests/unit/test_land_machinery_owned_leakage.py
