---
id: T-1025
title: 'strata SYS203: make shared-store-write contention consult a resource''s declared
  arbiter, drop tickets_ledger waivers'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_contention.py
- tests/unit/strata/test_contention.py
- docs/strata/host.md
- design/frob.strata
- tickets.md
- tests/unit/strata/litmus/contention_store_arbitered.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/litmus/contention_store_arbitered.strata
  reason: new litmus fixture proving SYS203's arbiter-discharge (T-1025's own code
    capability), mirroring the sibling contention_store_vuln.strata litmus precedent
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_arbitered_store_discharges
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_arbitered_store_still_fires_without_module
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_unarbitered_store_still_fires_with_module
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind
designated_repro_test: null
threat: null
component: null
---
T-0956 modeled the tickets_ledger's real single-writer-lock arbitration
using T-0700's grammar (resource tickets_ledger { lock "tickets.lock"; }
plus access "tickets_ledger" mode write; on cli/gates/fleet/core/serve),
verified clean via frob.strata._access.resource_contention_violations
(SYS204). SYS203 itself (src/frob/strata/_contention.py::
check_resource_contention) remains permanently mode-blind by design: it
has no code path that reads Module.resources or a node's access= attrs at
all, so it keeps firing on tickets_ledger's five writers regardless of the
now-modeled arbiter, and the five SYS203:tickets_ledger waivers (cli/
gates/fleet/core/serve in design/frob.strata) stay in place, permanently
justified rather than pending re-evaluation.

This ticket is the actual code-level follow-up: teach SYS203 (or a new,
narrower successor rule) to consult a resource's declared arbiter
(arbitrated_by/lock) the same way SYS204 already does, so a store with a
provably-safe declared arbiter stops being flagged by SYS203 at all,
letting the five tickets_ledger waivers above finally be dropped. Scope:
src/frob/strata/_contention.py, tests/unit/strata/test_contention.py,
docs/strata/host.md#resource-contention-sys2xx-t-0699, design/frob.strata
(dropping the five waivers once SYS203 itself discharges them),
tickets.md.