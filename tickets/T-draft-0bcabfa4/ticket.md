---
id: T-draft-0bcabfa4
title: 'DECISION: how bidirectional cross-module flows are expressed without an import
  cycle'
state: in-progress
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
body_changes:
- mode: append
  reason: owner decision on D-M9 recorded verbatim, 2026-09-19 19:30
  actor: logan
  at: '2026-09-19'
  old_length: 2740
  new_length: 4298
- mode: append
  reason: 'BUG002 front door (T-2393): pure decision record: the owner ruled on D-M9
    (hierarchy, import up only, flows declared by the lower module, accept down) and
    the ruling is recorded verbatim in the body; the behaviour changes land in the
    grammar, linker and migration leaves'
  actor: logan
  at: '2026-09-19'
  old_length: 4298
  new_length: 4575
- mode: append
  reason: 'BUG002 front door (T-2393): pure decision record: the owner ruled on D-M9
    (hierarchy, import up only, flows declared by the lower module, accept down) and
    the ruling is recorded verbatim in the body; the behaviour changes land in the
    grammar, linker and migration leaves'
  actor: logan
  at: '2026-09-19'
  old_length: 4575
  new_length: 4852
- mode: append
  reason: 'BUG002 front door (T-2393): pure decision record: the owner ruled on D-M9
    and the ruling is recorded verbatim in the body; the behaviour lands in the grammar,
    linker and migration leaves'
  actor: logan
  at: '2026-09-19'
  old_length: 4852
  new_length: 5045
- mode: append
  reason: 'BUG002 front door (T-2393): pure decision record: the owner ruled on D-M9
    and the ruling is recorded verbatim in the body; the behaviour lands in the grammar,
    linker and migration leaves'
  actor: logan
  at: '2026-09-19'
  old_length: 5045
  new_length: 5238
- mode: append
  reason: 'BUG002 front door (T-2393): pure decision record: the owner ruling is recorded
    verbatim; the behaviour lands in the grammar, linker and migration leaves'
  actor: logan
  at: '2026-09-19'
  old_length: 5238
  new_length: 5397
- mode: append
  reason: 'BUG002 front door (T-2393): pure decision record: the owner ruling is recorded
    verbatim; the behaviour lands in the grammar, linker and migration leaves'
  actor: logan
  at: '2026-09-19'
  old_length: 5397
  new_length: 5556
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


## DECIDED 2026-09-19 19:30 (owner, verbatim)

HIERARCHY. Modules declare their position in an explicit hierarchy (platform at
the top; app and test at the bottom; the 11-module partition gets an order in
the story body).

IMPORT UP ONLY: a module may import only modules above it; importing a module
below you is a compile error naming both modules, so import cycles are
impossible by construction (the SCC check becomes a redundant assertion).

FLOWS ARE DECLARED BY THE LOWER MODULE in either direction, because only the
lower module can name both ends.

ACCEPT DOWN: the upper module declares `accepts f from <lower-module>` naming
the lower module by reference with no import; an accepts naming a module above
you is an error.

The 16 bidirectional pairs are not waivers: each migration leaf decides which
module is lower and moves the flow declarations there.

## Consequences filed against the leaves

Grammar leaf T-draft-1f0f55cb: `accepts` takes a module REFERENCE, not an
import; the hierarchy declaration form is part of the grammar.
Linker leaf T-draft-27d3ece1: upward-only import check with BOTH module names
in the error; accepts-direction check (an accepts naming a module above is an
error); the SCC check remains as a redundant assertion that must never fire.
Migration order is unchanged and already top-down in STRATA-MODULES-TREE.md:
platform first, then the leaf consumers, then the hubs.
Option (a) of this ticket (accepts-by-reference without an import) is adopted as
part of the hierarchy rule; options (b) and (c) are not taken.


frob:no-behavior-change reason="pure decision record: the owner ruled on D-M9 (hierarchy, import up only, flows declared by the lower module, accept down) and the ruling is recorded verbatim in the body; the behaviour changes land in the grammar, linker and migration leaves"

frob:no-behavior-change reason="pure decision record: the owner ruled on D-M9 (hierarchy, import up only, flows declared by the lower module, accept down) and the ruling is recorded verbatim in the body; the behaviour changes land in the grammar, linker and migration leaves"

frob:no-behavior-change reason="pure decision record: the owner ruled on D-M9 and the ruling is recorded verbatim in the body; the behaviour lands in the grammar, linker and migration leaves"

frob:no-behavior-change reason="pure decision record: the owner ruled on D-M9 and the ruling is recorded verbatim in the body; the behaviour lands in the grammar, linker and migration leaves"

frob:no-behavior-change reason="pure decision record: the owner ruling is recorded verbatim; the behaviour lands in the grammar, linker and migration leaves"

frob:no-behavior-change reason="pure decision record: the owner ruling is recorded verbatim; the behaviour lands in the grammar, linker and migration leaves"