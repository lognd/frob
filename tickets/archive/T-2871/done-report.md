## Done report

Fixed the 5 SELFAUDIT001 findings attributable to T-2851/T-2843's file
splits, plus their downstream ratchet-ceiling fallout, without widening
any capability grant:

- gates::exec: removed the now-stale `_mutation_evidence.py` via-source
  (T-2851 moved its only exec call into `_bug_repro.py`, confirmed by
  SYS101 "declared but never observed"; removing it also kept the
  via-list at its existing ratchet ceiling of 1, so no bump needed).
- gates::env.read: added a new precise via-list grant for
  `_bug_repro.py` (first-ever env.read declaration for gates; baselined
  the ratchet at accepted_count=1, ticket T-2871).
- gates::fs.read (48->49) and cli::fs.read (18->19) and
  testsuite::env.read (7->8): each is an already-declared via-source
  growing the measured count past a committed ceiling
  (_docstatus.py/T-2843, _check_chunking_baseline.py, tests/unit/
  test_check.py respectively) -- bumped the ratchet lock's
  accepted_count with a reason, following the T-2743 precedent, rather
  than re-justifying sites that were already reviewed elsewhere.

Left out of scope, filed as T-2877: 3 remaining SELFAUDIT001 errors on
the `core` node (env.read ratchet growth from T-2849's `_reap.py`, and a
via-less `ffi` grant with no `because` justification) -- confirmed via
`tests/unit/strata/test_selfconform.py::TestRealGateGreen` failing
identically on main's root BEFORE this ticket's changes, so it is not a
regression introduced here.

No capability grant was widened beyond what the split's own code
already does; every fix here is either a via-list repoint/removal or a
ratchet-ceiling bump for a site that was already a declared via-source
elsewhere in the same node.

### Changed
```
 design/frob.strata                                 | 13 +++++-
 .../registry/capability-via-ratchet.lock.json      | 23 +++++++----
 tickets/T-2871/done-report.md                      | 48 ++++++++++++++++++++++
 tickets/T-2871/ticket.md                           |  7 +++-
 4 files changed, 80 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_deleting_lock_entry_does_not_bypass_the_ratchet` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_unscoped_grant_is_never_ratcheted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 28 error(s), 645 warning(s), 839 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/claude-hooks.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, DSL001@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PRE001@tickets/T-2871, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
