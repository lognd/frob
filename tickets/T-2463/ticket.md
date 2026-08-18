---
id: T-2463
title: 'SYS101 fallout: checker/fleet/deploy/vet fs.write declarations now unsupported
  post-T-2457'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- src/frob/check/**
- src/frob/fleet/**
- src/frob/deploy/**
- src/frob/vet/_nvd.py
- src/frob/vet/_registry.py
- docs/design/registry/capability-via-ratchet.lock.json
evidence_scope:
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: vet's fs.write capability is fully removed by this ticket (both files it
    covered), not just reduced -- the orphaned vet::fs.write ratchet entry should
    not outlive the capability it was ceiling for
  actor: logan
  at: '2026-08-18'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001
designated_repro_test: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a7b9dcb7abb36670841c96ea6b8023989cd09b94
---
T-2457 fixed the dangerous-ops capability detector's mode-blind `open(`
needle (a bare read-mode `open(path, "rb")` used to satisfy the `fs.write`
rule on its own). Removing that false positive exposed a SECOND, adjacent
problem: with the fix applied, `frob check --only gates-security` reports
SYS101 ("declared but never observed") for FOUR unrelated nodes in
design/frob.strata:

    SELFAUDIT001: self-audit family SYS101 node=checker: capability
      'fs.write' declared but never observed
    SELFAUDIT001: self-audit family SYS101 node=fleet: capability
      'fs.write' declared but never observed
    SELFAUDIT001: self-audit family SYS101 node=deploy: capability
      'fs.write' declared but never observed
    SELFAUDIT001: self-audit family SYS101 node=vet: capability
      'fs.write' declared but never observed via src/frob/vet/_nvd.py,
      src/frob/vet/_registry.py

Measured directly (T-2457 Done report): a full `scan_file_capabilities`
sweep of `src/frob/check/**`, `src/frob/fleet/**`, and `src/frob/deploy/**`
(the `checker`/`fleet`/`deploy` nodes' owned code) finds ZERO files
reporting `fs-write` post-fix. `vet`'s declared via-files (`_nvd.py`,
`_registry.py`) likewise report no `fs-write`. This strongly suggests
these four declarations were ALSO satisfied only by the same mode-blind
`open(` false positive T-2457 fixed -- structurally the same bug, just
not caught by T-2457's own narrower investigation (which was scoped to
the T-2390 config-schema modules named in that ticket).

This needs its own investigation, out of T-2457's declared scope
(src/frob/gates/_pii_structural/**, design/frob.strata) because
confirming whether checker/fleet/deploy/vet genuinely never write to the
filesystem requires reading src/frob/check/**, src/frob/fleet/**, and
src/frob/deploy/** in full -- none of which T-2457 touched or was scoped
to read. Two possible outcomes once investigated:

  - these are ALSO false declarations (bare `may "fs.write";`, coarse,
    with nothing behind them) -- narrow or remove them, same posture as
    T-2457's own fix; or
  - a real write exists that the (now-fixed) scanner still cannot see for
    some OTHER reason (e.g. a write reached only through an aliased/
    binding-indirect call the python resolver does not chase, or a
    subprocess-mediated write) -- in which case the fix is a scanner gap,
    not a declaration fix.

Do not assume either direction without measuring; this ticket exists so
the choice is not silently made inside T-2457.