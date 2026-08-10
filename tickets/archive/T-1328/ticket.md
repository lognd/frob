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
scope:
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
- tests/unit/strata/test_mutation_audit.py
- tickets/T-1328/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
---
T-1203's mutation-audit harness (src/frob/strata/_mutation_audit.py, SecondDetectorGap) proves that today only exec/net/fs.read/fs.write have a genuine independent second detector (the seccomp export -- node_allowed_syscalls/_SECCOMP_KIND_MAP): these are real OS-syscall-backed capabilities. The 7 app-level kinds actually declared in design/frob.strata (eval, env, ffi, install-hook, sql, deserialize, fetch_url) have no OS-syscall analog, so faking a seccomp entry for them would be dishonest (no real syscall corresponds to e.g. 'sql'). Acceptance [0] of T-1203 wants EVERY may to be double-detected by two independent mechanisms; this ticket is to design and build a real second detector for these 7 kinds -- e.g. a generated capability-manifest/allowlist artifact (distinct code path from scan_file_capabilities/SYS100) whose diff independently reacts to a may deletion/substitution, mirroring the seccomp-export precedent but for app-level capabilities instead of syscalls.

## Done report

Built node_allowed_app_capabilities (src/frob/strata/_mutation_audit.py),
a THIRD, independent detector for the 7 app-level capability kinds
(eval/env/ffi/install-hook/sql/deserialize/fetch_url) that have no
OS-syscall analog and so could never be honestly added to
_SECCOMP_KIND_MAP. It mirrors _export.py::node_allowed_syscalls's shape
exactly (declared Node.may in, a generated artifact out) but through a
code path that shares nothing with _effects.py::scan_file_capabilities
or _selfconform.py's observed-vs-declared join -- it reads ONLY the
declared may tuple, never re-scans source, so a bug in the first
detector's scanning cannot mask a gap here. This is a genuinely
independent derivation, not a reuse of the first detector's helpers
(the one thing the ticket explicitly called out as defeating the point).

Wired into the existing mutation-audit deletion-mutation loop
(_audit_one_atom) alongside the pre-existing seccomp export diff:
MutationFinding gained app_diff_fired/app_diff_expected fields, and
second_detector_gaps now reports a gap only for a kind neither detector
covers. Real-repo regression confirmed: second_detector_gaps shrank from
9 kinds to exactly {"process-control"} (T-1589's signal-delivery kind,
genuinely outside this ticket's 7-kind scope).

Masking edge case found and fixed during verification: design/frob.strata's
`core` node declares both a coarse `may "env"` and a precise `may
"env.read"` atom. Deleting only the precise atom leaves the coarse
sibling covering the same manifest entries, so the manifest diff
correctly does not fire for that one atom's removal -- `app_expected` is
now computed from the actual diff (masking-aware) rather than a static
kind-membership check, so no MutationFinding claims a per-atom guarantee
a node's own coexisting declarations cannot deliver. The coarser
second_detector_gaps question ("does this KIND have a detector at all")
still uses static APP_DETECTABLE_KINDS membership, unaffected by any one
node's masking.

Added tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities
(4 new tests: each kind maps to a non-empty manifest, the diff actually
fires on deletion, bare `env` is a superset of `env.read`/`env.write`
alone, an unrelated kind like `exec` contributes nothing) and updated the
existing gap-disclosure test's expected set.

Waived AFFECT001 on the 4 new/changed public symbols (APP_DETECTABLE_KINDS,
MutationFinding, MutationFinding.load_bearing, node_allowed_app_capabilities)
with the same reasoning this file's own pre-existing COV001 waiver already
documents: docs/strata/selfconform.md is a large shared doc outside this
ticket's declared scope (src/frob/strata/_mutation_audit.py,
src/frob/strata/_native_staleness.py only).

_native_staleness.py: read, not modified -- no change needed there for
this ticket's scope.

Pre-existing, unrelated failures observed and NOT caused by this change
(confirmed no _export.py touch): tests/unit/strata/test_export_golden.py's
test_k8s/test_seccomp fail against a stale committed golden fixture (a
"strata-vet" -> "strata-verify" node rename drift, unrelated to app
capabilities) -- left alone as out of this ticket's scope.

### Changed
```
 src/frob/strata/_mutation_audit.py       | 132 ++++++++++++++++++++++++++++++-
 tests/unit/strata/test_mutation_audit.py | 121 ++++++++++++++++++++--------
 tickets/T-1328/ticket.md                 |  16 +++-
 3 files changed, 232 insertions(+), 37 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 5 error(s), 627 warning(s), 736 waived
- error-findings: ARCH001@src/frob/tickets/_new_renumber.py, E501@/home/logan/projects/frob/.claude/worktrees/strata-cluster/src/frob/strata/_mutation_audit.py, SELFAUDIT001@design, invalid-assignment@tests/test_ticket_land.py, invalid-return-type@src/frob/tickets/_new_renumber.py
