---
id: T-1771
title: uv.lock is excluded from the release quartet coherence check and only synced
  inside the bump branch
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_release.py
- tests/unit/test_land_release_coherence.py
- docs/modules/tickets.md
- tickets/T-1771/ticket.md
- tickets/T-1771/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1771/ticket.md
  reason: v2 per-ticket ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1771/done-report.md
  reason: v2 per-ticket ledger files
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped::test_stale_lock_resynced_even_when_pyproject_and_manifest_agree
- tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped::test_lock_already_coherent_is_untouched
designated_repro_test: null
threat: null
component: null
---
Owner directive: all version syncing should be handled automatically.

It is not. Observed on main: `pyproject.toml` and `.frob-release.json`
both declared 0.368.0 while `uv.lock` still recorded frob 0.367.0,
tripping REL002 and requiring a hand `frob release sync`.

Two gaps compose to produce it:

- `_sync_uv_lock_for_land` is only ever called from inside
  `_apply_release_bump`'s "a bump was reported" branch. A land where the
  `bump_version` callback returns `Ok(None)` -- no API change, or the
  version already moved by other means -- never syncs the lock at all.
- `_ensure_release_quartet_coherent` runs unconditionally at the end of
  every land, which is right, but compares ONLY `pyproject.toml` against
  `.frob-release.json`. `uv.lock` is not in the comparison. The
  "quartet" is a trio in practice, and its own docstring's promise --
  "the quartet is coherent when land finishes" -- was not true of the
  fourth member.

The consequence is not cosmetic: `uv run`/`uv lock` re-derives that
version line on every invocation, so a stale lock flaps dirty repo-wide
and trips DirtyMain/SCOPE001 for whichever worktree runs anything next.
Same class of self-inflicted, fleet-wide land blocker as T-1755 (the
sweep's uncommitted writes) and T-1740 (a refused land's staged index).

ALREADY FIXED in the commit that files this ticket:
`_ensure_uv_lock_coherent` now runs as part of the unconditional
coherence step, comparing the lock's recorded frob version against
pyproject's and re-syncing when they differ, regardless of how the
version got where it is. `_read_working_uv_lock_version` returns `None`
for a missing or unparsable lock, meaning "nothing to compare" and never
"they agree". 260 tests across `test_land_release_coherence.py` and
`test_ticket_land.py` green.

REMAINING WORK for whoever takes this ticket:

1. Regression coverage for the real shape: a land whose `bump_version`
   returns `Ok(None)` while `uv.lock` is a version behind must leave the
   lock in step afterwards. Assert the lock's RECORDED VERSION, not that
   a sync helper was called.
2. Audit the rest of the quartet promise. `CHANGELOG.md` is the fourth
   member and is likewise not compared by the coherence check -- decide
   whether a missing changelog entry for the current version belongs
   here or in REL001, and write down which.
3. Rename `_ensure_release_quartet_coherent`, or fix its docstring, so
   the name and the guarantee match. A guard whose name overstates its
   coverage is exactly how this went unnoticed for as long as it did.

## Done report

The core `_ensure_uv_lock_coherent` fix (comparing `uv.lock`'s recorded
frob version against `pyproject.toml` unconditionally) had already
landed by the time this ticket was picked up, but the "unconditionally"
claim was not quite true: `_ensure_uv_lock_coherent` was called ONLY
from inside `_ensure_release_quartet_coherent`'s pyproject-vs-manifest
DIVERGENCE branch. The common, healthy case -- pyproject.toml and
`.frob-release.json` already agree, `bump_version` reported `Ok(None)`
because nothing needed to change -- skipped the lock check entirely,
which is exactly the gap the ticket's own "remaining work item 1" names
("a land whose bump_version returns Ok(None) ... must leave the lock in
step"). Fixed: the lock check now runs whenever `pyproject_version` is
known at all, a sibling of the manifest check rather than nested inside
it (split into `_resync_manifest_if_diverged` to keep the parent under
ARCH001's line threshold).

Item 1 (regression coverage for the real shape): added
`TestUvLockCoherenceWhenAlreadyBumped` with a fake `run_argv` that
actually rewrites `uv.lock`'s on-disk content (not a no-op mock), so the
test asserts the lock's own RECORDED VERSION via
`_read_working_uv_lock_version` after the call, per the ticket's own
instruction -- not merely that a sync helper was invoked. A companion
test asserts an already-coherent lock triggers no `uv lock` spawn at
all.

Item 2 (audit CHANGELOG.md, decide and write down where it belongs):
REL001 (`frob.gates.release_gate`) already refuses with "no CHANGELOG.md
entry for {version}" at GATE time -- it was never actually missing
coverage, just undocumented that this was the deliberate split. Written
down in both `_ensure_release_quartet_coherent`'s own docstring and
`docs/modules/tickets.md`'s T-1358/T-1771 note: the other three quartet
members get a land-time auto-resync because there is one correct
version NUMBER to force-write; CHANGELOG.md gets a gate-time refusal
instead because there is no single correct PROSE entry to auto-write.

Item 3 (rename or fix the docstring): fixed the docstring rather than
renaming `_ensure_release_quartet_coherent` -- a rename would touch
every caller and test referencing the name for no functional gain, and
the docstring now states explicitly which three members this function
checks and where the fourth is checked instead.

### Changed
```
 docs/modules/tickets.md                   | 16 ++++++++
 src/frob/tickets/_land_release.py         | 52 ++++++++++++++++++++++---
 tests/unit/test_land_release_coherence.py | 65 +++++++++++++++++++++++++++++++
 tickets/T-1771/ticket.md                  | 18 ++++++++-
 4 files changed, 144 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped::test_stale_lock_resynced_even_when_pyproject_and_manifest_agree` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped::test_lock_already_coherent_is_untouched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 882 warning(s), 726 waived
- error-findings: none (measured, zero errors)
