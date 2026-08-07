---
id: T-1409
title: 'T-1276 successor: burn down the real TEST005 count under src/frob/app/** (false-closed
  criterion remainder)'
state: dropped
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1276 closed done on main (LAND-PROOF verified=True) against its own criterion [0] ("0 TEST005 findings under src/frob/app/**") while main actually reported 116 live TEST005 findings under that glob (T-1399's finding, measured 2026-08-01). T-1276 cannot be requeued (only in-progress tickets can be) so its honest remainder must not be lost to the false close.

The implementing agent's own account (T-1276's Done report, prior to this successor): roughly 50 unsampled app runner entrypoints under src/frob/app/** still need real coverage to actually reach the 0-TEST005 floor its criterion claimed. This ticket picks that remainder back up as real, trackable work: run a fresh, unscoped `make coverage` + `frob check --only test` to get the CURRENT app-package TEST005 count (do not trust the 116 figure without re-measuring -- T-1398's per-symbol join defect may have inflated or deflated some of it, per T-1399's own related-ticket note), then burn it down to 0 with real per-symbol test coverage, the same way every other TEST005 burn-down ticket in this queue works.

## Drop reason
- 2026-08-01: duplicate of T-1400, which already exists as the T-1276 successor (blocked on T-1398/T-1399/T-1401) -- discovered after filing, dropping in favor of the existing ticket