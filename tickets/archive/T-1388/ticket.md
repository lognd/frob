---
id: T-1388
title: land's Tier-A pre-fix pass touches out-of-scope _daemon_proxy.py, then self-blocks
  on OutOfScopeWaiveDeletion
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land*.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-1388: regression test for the real FMT001 fixer''s output not tripping
    the waive-deletion guard'
  actor: logan
  at: '2026-08-04'
evidence:
- tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_real_fmt001_fixer_rewrap_does_not_trip_the_guard
designated_repro_test: null
threat: null
component: null
---
Found while landing T-1237 (and earlier T-1235) in the coverage-integrity
series worktree: every `frob ticket land <id> --worktree ...` invocation's
own pre-land Tier-A auto-fix pass ("ticket land: T-1235/T-1237 pre-land
Tier-A fixes applied 2 fix(es)") rewrites src/frob/app/_daemon_proxy.py
(re-wrapping two frob:waive reason= comment blocks, ARCH103 at line ~135
and SEC110 at line ~342) and stubs a CHANGELOG.md "## [0.295.0] -
unreleased" entry, even though neither file is in the landing ticket's
declared scope and neither ticket touched src/frob/app/**.

That collateral edit then trips land's OWN OutOfScopeWaiveDeletion guard
on the very same invocation:

  ERROR: land: T-1237 refused -- worktree has uncommitted frob:waive
  deletion(s) outside scope [...] and undeclared by the Done report:
  ['src/frob/app/_daemon_proxy.py:ARCH103', 'src/frob/app/_daemon_proxy.py:SEC110']

i.e. land's own Tier-A fixer creates the exact violation land's own
scope guard then refuses on -- deterministic, reproduced twice in one
session (T-1235's land attempt, then T-1237's, both against the same
_daemon_proxy.py lines). Working around it by `git checkout --
src/frob/app/_daemon_proxy.py CHANGELOG.md` before every land retry is
a manual step every future ticket in this repo will hit the same way,
since the Tier-A fixer re-triggers it every time land runs.

Root cause not fully isolated (would require reading
src/frob/tickets/_land*.py's Tier-A fixer dispatch, which is out of this
series' declared scope -- Makefile, src/frob/clean/**, docs/**, tests/**
only), but the shape strongly suggests either: (a) the Tier-A fmt fixer
runs unscoped (whole repo) instead of restricted to the landing ticket's
own touched-file set, or (b) _daemon_proxy.py's frob:waive reason=
comments sit right at whatever line-length threshold `frob fmt` rewraps,
so any repo-wide fmt pass touches it regardless of which ticket is
landing.

Suggested fix direction: scope the Tier-A pre-land auto-fix pass to the
landing ticket's own scope globs (same set the OutOfScopeWaiveDeletion
guard itself already checks against), so it structurally cannot produce
a collateral out-of-scope edit for a DIFFERENT ticket to trip over.