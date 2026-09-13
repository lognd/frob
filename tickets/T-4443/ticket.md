---
id: T-4443
title: 'LARGE001: _native_staleness.py at 805 lines after T-4434, extract the digest
  helpers'
state: done
kind: bug
origin: agent
created: '2026-09-12'
priority: high
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_native_staleness*.py
- tests/unit/strata/test_native_staleness.py
- docs/modules/testing.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/testing.md
  reason: T-4443's own instructions require updating docs/modules/testing.md's public-api
    section for the LARGE001 split (new sibling module + moved seed_worktree_native_source_mtimes
    internals)
  actor: logan
  at: '2026-09-12'
- op: add
  glob: design/frob.strata
  reason: T-4443's split moved a fs.read call site into the new sibling module _native_staleness_digest.py;
    design/frob.strata's stratamod fs.read capability declaration (SYS100/SELFAUDIT001)
    must list the new file alongside its sibling
  actor: logan
  at: '2026-09-12'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: 'SELFAUDIT SYS111 ratchet ceiling for stratamod::fs.read bumped 10->11:
    the LARGE001 split''s new sibling module adds a second via-list entry for the
    same pre-existing fs.read call site'
  actor: logan
  at: '2026-09-12'
body_changes:
- mode: append
  reason: BUG002 correctly refuses PASSED_AT_PARENT confirmatory-only evidence; this
    ticket is a pure refactor with no behavior change, the documented frob:no-behavior-change
    escape hatch (docs/modules/gates.md) applies
  actor: logan
  at: '2026-09-12'
  old_length: 922
  new_length: 1335
evidence:
- tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes::test_identical_source_is_backdated_and_reads_fresh
- tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes::test_diverged_source_is_left_untouched_and_still_stale
- tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes::test_repo_side_untracked_file_does_not_block_seeding
designated_repro_test: tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes::test_identical_source_is_backdated_and_reads_fresh
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34675057655 (head d0fc8ba1e, 2026-09-12), every leg: LARGE001: src/frob/strata/_native_staleness.py file has 805 lines (threshold: 800). T-4434's land (5ce34a4c8, +66 lines) pushed the file over the threshold; it was 739 lines before. Extract one cohesive helper group (the T-4434 tracked-content digest helpers, or the seeding/backdating block) into a sibling module such as src/frob/strata/_native_staleness_digest.py with its own docstring and frob:tests edges, keeping every public name importable from _native_staleness. ACCEPTANCE: (1) _native_staleness.py under 800 lines with headroom (at most 720); (2) tests/unit/strata/test_native_staleness.py still passes unchanged or with import-path-only edits; (3) frob check --ticket shows no LARGE001 on either file. Sprint v0.531.0 (CI green blocker). Quarantine finding LARGE001:src/frob/strata/_native_staleness.py (batch 5ce34a4c8) is disposed to this ticket.


frob:no-behavior-change reason="T-4443 is a pure LARGE001 line-count split: seed_worktree_native_source_mtimes and its digest/backdating helpers moved verbatim from _native_staleness.py into the new sibling _native_staleness_digest.py, re-exported unchanged. Every bound test genuinely PASSES at the parent commit because there is no behavior to reproduce -- the fix is structural (file location), not logical."