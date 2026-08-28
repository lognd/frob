---
id: T-2997
title: 'rapid-debt.jsonl grows unbounded in git with no rotation: 2882 lines / 345KB,
  appended by every land, a merge-conflict hotspot'
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- rapid-debt.jsonl
- .frob/rapid-debt.jsonl
- .gitattributes
- src/frob/tickets/_evidence.py
- tests/unit/test_rapid_debt.py
- CHANGELOG.md
- docs/modules/tickets-verify-sweep.md
- docs/modules/tickets-merge-driver.md
- changelog.d/T-2997.md
- tests/unit/test_rapid_sweep.py
- tests/unit/test_gitattributes_merge.py
- tests/unit/test_gitattributes_crlf_normalization.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: rapid-debt.jsonl
  reason: 'T-2997: move rapid-debt.jsonl from tracked git root to gitignored .frob/,
    per owner decision recorded on this ticket'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: .frob/rapid-debt.jsonl
  reason: 'T-2997: move rapid-debt.jsonl from tracked git root to gitignored .frob/,
    per owner decision recorded on this ticket'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: .gitattributes
  reason: 'T-2997: move rapid-debt.jsonl from tracked git root to gitignored .frob/,
    per owner decision recorded on this ticket'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'T-2997: move rapid-debt.jsonl from tracked git root to gitignored .frob/,
    per owner decision recorded on this ticket'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_rapid_debt.py
  reason: 'T-2997: move rapid-debt.jsonl from tracked git root to gitignored .frob/,
    per owner decision recorded on this ticket'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: CHANGELOG.md
  reason: 'T-2997: move rapid-debt.jsonl from tracked git root to gitignored .frob/,
    per owner decision recorded on this ticket'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: changelog.d/*
  reason: 'T-2997: move rapid-debt.jsonl from tracked git root to gitignored .frob/,
    per owner decision recorded on this ticket'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc targets for record_rapid_debt docstring update
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-merge-driver.md
  reason: doc targets for record_rapid_debt docstring update
  actor: logan
  at: '2026-08-28'
- op: remove
  glob: changelog.d/*
  reason: narrow to the specific changelog entry file
  actor: logan
  at: '2026-08-28'
- op: add
  glob: changelog.d/T-2997.md
  reason: narrow to the specific changelog entry file
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2997: record_rapid_debt now writes under .frob/, which the test fixture
    repo must gitignore like a real repo does, or the commit-clean invariant test
    breaks on an untracked .frob/ dir'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_gitattributes_merge.py
  reason: T-2997 removed rapid-debt.jsonl's merge=union and eol=lf gitattributes pins
    (file no longer tracked); the tests asserting those pins need updating to match
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_gitattributes_crlf_normalization.py
  reason: T-2997 removed rapid-debt.jsonl's merge=union and eol=lf gitattributes pins
    (file no longer tracked); the tests asserting those pins need updating to match
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: set
  reason: 'owner decided the destination: move it under .frob/ rather than rotating
    it in git'
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 2200
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`rapid-debt.jsonl` is append-only operational telemetry (deferred-sweep records,
attribution skips, quarantine events) tracked IN GIT at the repo root. Measured
2026-08-26: 2,882 lines / 345 KB, appended 1-2 lines by every land, and nothing
prunes or rotates it -- grepped, no rotation exists anywhere. It grows without
bound.

It is also a merge-conflict hotspot by construction: every concurrent land
appends to the same file, in a repo that routinely runs six agents landing in
parallel.

OWNER DECISION (2026-08-26): move it OUT of the repo root and into `.frob/`,
which is already gitignored. That resolves both problems at once -- unbounded
growth stops being a git concern, and it stops being a conflict surface on the
hottest path in the system.

REQUIREMENTS
- Every producer and consumer moves with it. `git grep rapid-debt` shows 42
  references in `src/` alone. A partial move that leaves some writers pointing
  at the old root path silently splits the log in two, which is worse than
  either location.
- Decide and STATE what happens to the existing 2,882 lines: migrated into the
  new location, or deliberately dropped with the reason recorded. Do not
  silently discard it -- it is the record of every deferred sweep and
  attribution skip this repo has taken, and T-2929's staleness work reads this
  file's `post-land-sweep-attribution-skipped-stale-baseline` entries.
- `.frob/` is gitignored, so this telemetry stops being shared across clones.
  Confirm nothing depends on reading it from a fresh checkout or another
  machine. Nothing should, but check rather than assume -- this repo has been
  bitten by "referenced but not in the way you think" more than once.
- After the move the repo root must contain no `rapid-debt.jsonl`, and a real
  land must append to the new location. Verify by running one and observing the
  write, not by reading the code.

ACCEPTANCE
- `rapid-debt.jsonl` lives under `.frob/`; the root copy is gone from git
  tracking.
- All 42+ references updated; no writer or reader still targets the root path.
- A real land appends to the new path, verified by observation.
- The disposition of the existing 2,882 lines of history is stated explicitly.
