---
id: T-1328
title: 'strata: build an independent second detector for app-level capability kinds
  (eval/env/ffi/install-hook/sql/deserialize/fetch_url)'
state: done
kind: invariant
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
- tests/unit/strata/test_mutation_audit.py
- tickets/T-1328/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/strata/test_mutation_audit.py
  reason: regression tests for the T-1328 app-capability detector, plus the CLI-owned
    per-ticket state file
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1328/ticket.md
  reason: regression tests for the T-1328 app-capability detector, plus the CLI-owned
    per-ticket state file
  actor: logan
  at: '2026-08-08'
body_changes:
- mode: append
  reason: condense second-detector masking narrative into T-1328 body
  actor: logan
  at: '2026-09-19'
  old_length: 979
  new_length: 1916
- mode: append
  reason: condense second-detector app-capability narrative into T-1328 body
  actor: logan
  at: '2026-09-19'
  old_length: 1916
  new_length: 3102
evidence:
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
- tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities::test_maps_each_app_kind
- tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities::test_differs_when_atom_removed
- tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities::test_bare_env_covers_both_modes
- tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities::test_unknown_kind_allows_nothing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1203's mutation-audit harness (src/frob/strata/_mutation_audit.py, SecondDetectorGap) proves that today only exec/net/fs.read/fs.write have a genuine independent second detector (the seccomp export -- node_allowed_syscalls/_SECCOMP_KIND_MAP): these are real OS-syscall-backed capabilities. The 7 app-level kinds actually declared in design/frob.strata (eval, env, ffi, install-hook, sql, deserialize, fetch_url) have no OS-syscall analog, so faking a seccomp entry for them would be dishonest (no real syscall corresponds to e.g. 'sql'). Acceptance [0] of T-1203 wants EVERY may to be double-detected by two independent mechanisms; this ticket is to design and build a real second detector for these 7 kinds -- e.g. a generated capability-manifest/allowlist artifact (distinct code path from scan_file_capabilities/SYS100) whose diff independently reacts to a may deletion/substitution, mirroring the seccomp-export precedent but for app-level capabilities instead of syscalls.

<!-- narrative-moved:src/frob/strata/_mutation_audit.py:428:T-1328 -->
T-1328: unlike EXPORT_DETECTABLE_KINDS (in practice no node in this
repo declares both a precise and a coarse seccomp-covered kind
together), a node CAN legitimately declare both a coarse `env` and a
precise `env.read`/`env.write` atom (design/frob.strata's `core`
node does exactly this) -- deleting the precise atom alone then
leaves the coarse sibling still covering the same manifest entries,
so the diff correctly does NOT fire for THIS atom's removal. Compute
`app_expected` from the actual diff (masking-aware) rather than a
static kind-membership check, so `app_diff_expected` never claims a
per-atom guarantee this specific node's coexisting declarations
cannot deliver -- `APP_DETECTABLE_KINDS` membership alone still
governs the coarser `second_detector_gaps` "does this KIND have a
detector at all" question below, unaffected by any one node's
masking.

<!-- narrative-moved:src/frob/strata/_mutation_audit.py:128:T-1328 -->
T-1328's independent SECOND detector for the app-level capability kinds
`_SECCOMP_KIND_MAP` deliberately excludes (module docstring: no real
OS-syscall analog exists for these -- faking a seccomp entry for `sql`
would be dishonest). Mirrors `_SECCOMP_KIND_MAP`'s own shape exactly
(raw declared kind -> tuple of allowed manifest entries) but generates
a DIFFERENT artifact -- an app-capability manifest, not a syscall list
-- through a code path that shares nothing with `_effects.py::
scan_file_capabilities`/`_selfconform.py`'s observed-vs-declared join
(the FIRST detector): like the seccomp map, this reads ONLY the
declared `Node.may` tuple, never re-scans source. `env`/`env.read`/
`env.write` are all listed because a node may declare either the bare
family or a precise mode (`_may_kind` returns whichever was written).
`html_render`/`client_storage` (the module docstring's other two
disclosed-gap kinds) are deliberately NOT here -- this ticket's
declared scope is exactly the 7 kinds named in its title; those two
remain open `SecondDetectorGap` findings, same as before this ticket.
frob:ticket T-1328