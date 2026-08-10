---
id: T-1911
title: Tier-A handler dispatch signature is stricter than any handler needs, so new
  tests reach for None and re-trip invalid-argument-type
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, from three consecutive post-land sweep regressions in one wave: T-1894, T-1896, T-1906. (Re-filed: the original draft's id was consumed by a ledger renumber during the T-1895 land recovery.)

THE RECURRING SHAPE. Tier-A fix handlers share a uniform dispatch signature, e.g.

  fix_sys_interface_canonical_order(root: Path, snapshot: GraphSnapshot)

but the body immediately does 'del snapshot  # signature uniformity only'. The parameter exists solely so every handler matches the dispatch table's shape; no handler needs the value. GraphSnapshot is declared non-Optional, so every author writing a new test reaches for None as the obvious don't-care value, and ty correctly reports invalid-argument-type.

WHY IT KEEPS HAPPENING -- THE PART THAT MATTERS. T-1896 already fixed exactly this, in exactly this file, by introducing _EMPTY_SNAPSHOT = GraphSnapshot(root='', symbols={}, edges=()). ONE TICKET LATER, T-1900 added three test cases nearby and called the same function with bare None, silently dropping the fixture and reintroducing the identical diagnostic; T-1906 then fixed it a third time. The convention existed only as a usage a few lines up the file, and nothing made departing from it fail. A convention that is not enforced decays at the rate new authors arrive -- and with parallel agents that rate is high.

Related shape: T-1894 was the same category via too-narrow invariant typing (dict[str, Ticket] declared where callers hold Mapping[str, Ticket]).

FIX AT THE SOURCE -- do NOT just fix the call sites a fourth time:
1. Make the parameter honestly Optional (GraphSnapshot | None) since no handler body uses it, OR restructure the dispatch protocol so handlers that do not need a snapshot do not declare one.
2. If it must stay required for uniformity, EXPORT the empty-snapshot sentinel from the module defining GraphSnapshot, so the correct value is discoverable at the point of use rather than by reading neighbouring tests.
3. Audit the other Tier-A handler signatures for the same too-strict-for-purpose declaration -- three instances in one wave means this is a property of the dispatch design, not three unlucky authors.

MAKE IT ENFORCED, NOT DOCUMENTED. Per this repo's standing principle that findings become rules, the deliverable must include something that FAILS when a call site passes bare None for a signature-uniformity parameter. A comment or docs note is exactly what already failed between T-1896 and T-1900.

Related: T-1894, T-1896, T-1906, T-1907.