---
id: T-draft-0bcabfa4
title: 'DECISION: how bidirectional cross-module flows are expressed without an import
  cycle'
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: critical
parent: T-draft-0a0c7b43
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'pure decision record (D-M9): no file scope until the owner
  rules'
designated_repro_test: null
acceptance:
- text: Given this decision ticket, when the owner rules, then the body records the
    chosen option (a/b/c), the exact rule for which side declares `accepts` relative
    to the import direction, and which edge set cycle detection runs over.
  evidence: []
- text: Given the 16 bidirectional pairs listed in the body, when the decision is
    applied on paper to each pair, then each pair is shown to be expressible without
    an import cycle, or is named as needing option (b) or (c) with a reason.
  evidence: []
- text: Given the decision, when the grammar and linker leaves start, then their acceptance
    criteria are reconciled with it (accepts naming an unimported module; SCC over
    imports only).
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DECISION REQUIRED (raised in coordinator review of the module-system tree).

THE HOLE. A flow A -> B is declared in module A, which must import B to name
B's node. A flow B -> A then makes B import A. That is exactly the import cycle
D-M2 forbids -- yet 16 of the module pairs in STRATA-MODULES.md section 2 are
mutually bidirectional, and most are legitimate request/response shapes between
services, not design defects.

EVIDENCE. The 16 bidirectional pairs (section 2 of the proposal, computed from
the 117 flow declarations): app<->gates, app<->platform, app<->serve,
app<->tickets, gates<->graph, gates<->platform, gates<->strata, gates<->tickets,
gates<->vet, graph<->platform, graph<->tickets, graph<->vet,
platform<->strata, platform<->tickets, strata<->tickets, strata<->vet.
109 of 117 flows (93.2%) cross a module boundary; 59 distinct ordered
module->module edges, 54% density. An import-cycle rule that also counts
inbound flows fails on day one against 16 pairs.

OPTIONS.
(a) `accepts f from <module>` names the peer module BY REFERENCE, without
    importing it. The sink side never needs an import to receive an inbound
    flow, and the cycle rule applies to IMPORTS ONLY. Bidirectional traffic
    between two modules is then expressible with at most one import.
(b) An interface node owned by `platform` mediates the reverse direction: the
    reverse flow targets a platform-owned interface instead of the peer.
(c) Allow a declared, owned exception per pair (an assume with owner+expiry per
    bidirectional pair).

RECOMMENDATION: (a).
Precise rule: `accepts` applies when the SINK is the imported node -- the source
module imports the sink module, declares the flow, and the sink module declares
`accepts f from <source module>` naming the source by reference only. When the
SOURCE is the imported node, the flow is declared in the SINK's module (which
already imports the source to name it) and is ONE-SIDED by construction, since
the two-sided contract exists to make an inbound obligation consented to, and
the importer is already the consenting party. Cycle detection therefore runs
over the import edge set, never over the flow edge set.
(b) stays available as the remedy for a pair that genuinely should not see each
other at all; (c) is the last resort and is what D-M2 means by "decided
individually, never bulk-waived".

CONSEQUENCES IF (a) IS ADOPTED: the grammar leaf must allow a module name in
`accepts` that is NOT bound by an import (a bare dotted module path, not an
alias), and the linker leaf must build its SCC over imports only, with the
two-sided check keyed on flow direction relative to the import direction. The
cycle-rule enforcement in migration depends on this decision being made first.
