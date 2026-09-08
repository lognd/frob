---
id: T-4334
title: New verify-rapid-debt doc carries the tree's only three gate errors
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/verify-rapid-debt-visibility.md
- invariants/INV-052.md
- docs/index.md
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: REF002 needs a real inbound link from a comparable verification doc, and
    INV003/INV004 need a new declared invariant file to anchor the doc's append-only/never-null
    claims
  actor: logan
  at: '2026-09-08'
- op: add
  glob: invariants/INV-052.md
  reason: REF002 needs a real inbound link from a comparable verification doc, and
    INV003/INV004 need a new declared invariant file to anchor the doc's append-only/never-null
    claims
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: swap the heavy tickets-verify-sweep.md link target (137 scope-closure warnings)
    for docs/index.md's module list, the same lightweight anti-orphan link surface
    T-4324 already relies on for its own module docs
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/index.md
  reason: swap the heavy tickets-verify-sweep.md link target (137 scope-closure warnings)
    for docs/index.md's module list, the same lightweight anti-orphan link surface
    T-4324 already relies on for its own module docs
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: INV002 requires a real frob:invariant code anchor at the enforcing site
    (record_rapid_debt) for the new INV-052 this doc's genuine append-only claim needs;
    the T-4324 doc's existing describes-anchor to verify_runner.py stays out of scope
    since that file needs no edit
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A DOCUMENTATION FILE ADDED WITH THE LAST LAND CARRIES THE ONLY THREE GATE ERRORS
IN THE TREE, AND THEY WILL FAIL THE INTEGRATION RUN'S GATE STEP.

MEASURED ON MAIN JUST NOW. An unscoped gate run reports exactly three errors, all
against the same newly-added module doc, and nothing else in the repository is in
error:
  - an exclusivity/normative claim ("only") with no invariant anchor
  - a behaviour description ("never", "only") with no invariant anchor, first
    flagged at its opening section
  - exactly one inbound reference, from the single source module it documents

The rest of the tree is clean, so these three are the whole gap between the gate
step and green.

WHY THIS SLIPPED IN. The doc was created as part of a land whose post-land sweep
reported clean, because the rolling baseline it compared against predated the new
file. That is worth noticing but is not this ticket's job to fix.

THE FIRST TWO ARE THE SAME REQUEST, AND IT IS A REASONABLE ONE. The doc states
what the mechanism always or never does. This project requires such claims to be
anchored to a declared invariant so that the assertion is checkable rather than
merely written down -- prose asserting behaviour is not enforcement, a lesson this
repository has paid for repeatedly. Read the surrounding module docs to see how
existing anchors are written and follow that form exactly rather than inventing
one. If a sentence turns out to be a loose "only" that does not actually claim an
invariant, rewording it to stop over-claiming is an equally valid fix -- decide per
sentence rather than blanket-anchoring.

THE THIRD IS A DIFFERENT QUESTION. A doc reachable from exactly one place is
flagged as likely-orphaned. Judge honestly whether this doc genuinely belongs in
the documentation graph -- linked from the module index or the guide that covers
verification status, wherever comparable docs are referenced from -- or whether
its content should have lived inside an existing verification document instead of
a new standalone file. Both are acceptable answers; a new top-level doc that
nothing links to is not.

DO NOT CLEAR ANY OF THE THREE WITH A WAIVER. All three are asking for something
cheap and genuinely useful, and the file is one land old -- there is no legacy
cost being paid down here.

VERIFY with an unscoped run and quote the exact error count. Measure it with
`uv run frob check --json | python3 scripts/check_summary.py` rather than
grepping text output: reading that JSON at the wrong nesting level has produced
false "0 errors" reports in this repo before, and an absent section looks
identical to a clean one. The count must reach zero.
