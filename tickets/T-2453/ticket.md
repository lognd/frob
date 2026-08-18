---
id: T-2453
title: Fix out-of-scope doc/ack drift left by this drive's refactors (DRIFT001/DRIFT002/SELFAUDIT001)
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata;docs/design/registry/capability-via-ratchet.lock.json;docs/modules/arch.md;docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Coordinator-directed error-floor sweep (T-2407 series follow-up):
frob check --json | scripts/check_summary.py reported 30-87 errors on
main (count moved as other agents landed concurrently), none of them
SYS003 -- collateral drift this drive's own refactors left in files the
refactoring diffs never touched:

- DRIFT002 docs/modules/vet.md#public-api -> src/frob/vet/_capability.py
  ::language_for / ::scan_file_capabilities no longer resolve: T-2358
  relocated these into _capability_core.py/_capability_scan.py. Doc fix
  (not ack): rewrite the two frob:describes anchors to the real def
  sites.
- DRIFT002 docs/modules/arch.md#configuration-frobtoml-arch-table-t-0373
  -> src/frob/app/_config_meta.py::* (11 distinct symbols, one per
  frob:describes anchor, all under the same doc section): T-2403/T-2407
  relocated _config_meta.py -> repo_meta.py. Doc fix: rewrite all 11
  anchor prefixes to repo_meta.py.
- DRIFT001 src/frob/gates/_fix_engine.py::apply_tier_a_fixes (sig+body):
  T-2400 added an additive merge_target_ids parameter, documented in the
  function's own docstring; docs/modules/gates.md's Tier-A section
  describes handler CLASSES at a level of abstraction the new param
  doesn't affect. frob ack (genuinely still true).
- DRIFT001 src/frob/app/ticket_runner/_rapid_sweep.py::
  _file_regression_ticket (body+sig): digest moved from unrelated nearby
  edits (T-2165) in the same file; re-verified against
  docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690 --
  T-2009/T-1791/T-2208 content all still present. frob ack.
- SELFAUDIT001 SYS101 gates node: 'eval' declared but never observed via
  _docblocks_refs.py: T-2231 moved the importlib.import_module call to
  _docblocks_shared.py. Doc/declaration fix (not ratchet, not deletion):
  retarget the via-file.
- SELFAUDIT001 SYS100 (undeclared, new): src/frob/process/_reap.py (core
  fs.read) and tests/unit/test_process_reap.py (testsuite exec/fs.write)
  are T-2443's own new forkserver-reaping primitive + its test, neither
  yet added to any via-list. Real declaration fix: add both files to
  their node's via-lists.
- SELFAUDIT001 SYS111 ratchet growth across cli/core/gates/testsuite/
  tickets_ledger/verify (13 node::capability pairs): measured as
  cumulative site-count growth from many already-declared via-files
  across this drive's many small lands (T-2390 series schema-gate
  children, T-2358's split, T-2443's reap work) -- every contributing
  file is already an authorized via-source for its capability, so this
  is legitimate accumulated growth, not a new unauthorized site (that
  is the SYS100 case above, handled separately). Ratchet bump with a
  measured reason, not re-justifying each site.

Fix already drafted (uncommitted diff preserved at
/tmp/t2407-drift-preserve/drift-fix.diff after being pulled out of the
shared root per coordinator direction -- was mistakenly worked directly
in the root with no ticket holding it, DirtyMain-blocking T-2441's land
and its downstream T-2388/T-2435/T-2436/T-2437 queue). This ticket's
worktree re-applies that diff, verifies, and lands normally.