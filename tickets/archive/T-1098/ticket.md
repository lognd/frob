---
id: T-1098
title: T-1087 land left REG003 x13 + TICK006 phantom-draft debt on main
state: dropped
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/supply-chain.yaml
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`frob check --only registry --only tickets` on current main (post T-1087
land, 52212cdb) reports:

- REG003 x13: docs/design/registry/supply-chain.yaml's SC-* entries
  disposition `deferred:T-1087`, but T-1087 is itself DONE -- a deferral
  to a closed ticket is not a real deferral (needs re-dispositioning to
  an open ticket or `implemented`).
- TICK006 x1: T-1087's own Done report claims T-1101 was
  filed, but that draft resolves to no block in tickets.md or
  tickets-archive.md -- a phantom filing trail (T-0707/T-0615 incident
  class).

Found incidentally while verifying T-1090's own scoped gate state stayed
clean; unrelated to T-1090's finalize_draft fix (files are outside
T-1090's scope). Filed rather than fixed to keep T-1090 scoped.

## Drop reason
- 2026-07-28: both halves resolved: the REG003 x13 deferred-to-closed claims were already flipped to handled_by by T-1087's own land (verified 0 'deferred:T-1087' in supply-chain.yaml), and the TICK006 phantom draft was refiled as T-1101 with prose repointed in d9d1a6e3 -- gate:TICK and gate:REG both green