---
id: T-3190
title: 'Adopt real milestones: MILE001 cannot fire while all 346 tickets sit in one
  default milestone'
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: the milestone default config and the lifecycle doc that describes milestone
    semantics; queue stamping is a ledger mutation needing no source scope
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: the milestone default config and the lifecycle doc that describes milestone
    semantics; queue stamping is a ledger mutation needing no source scope
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: append
  reason: record the owner's 2026-08-28 decision (publish 0.530.0 to PyPI before 1.0.0),
    which is exactly what this ticket was waiting on; adds the implied two-milestone
    partition and the known blocker set
  actor: logan
  at: '2026-08-28'
  old_length: 3369
  new_length: 6651
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. frob's incremental-release machinery is fully built,
registered, tested -- and cannot fire, because the whole queue sits in ONE
milestone.

WHAT EXISTS AND IS WIRED:
  - `MILE001` -- refuses a ticket `blocked_by` a ticket in a LATER milestone.
    This IS release-train dependency gating: M2 work must not block M1 shipping.
  - `MILE003` -- fires on an open ticket with no resolvable milestone.
  - `MILE004`, plus `Ticket.milestone`, `validate_milestone`, a `milestone` CLI
    verb, milestone inheritance, and a configurable repo default.
  - `frob.gates._milestone.milestone_gate` is registered in the gate table and
    runs in the same stage as "tickets" (src/frob/gates/__init__.py:6769).
  - Six bound tests per rule; 398 lines of gate code.

WHY IT IS INERT:
  - `frob.toml` sets `[tickets] default_milestone = "1.0.0"`.
  - All 346 active tickets resolve to that default; 0 carry an explicit
    milestone.
  - So MILE003 is correctly silent (every ticket resolves), and MILE001 can
    NEVER fire, because a blocker in a "later" milestone cannot exist when there
    is only one milestone.

This is not a defect in the gate. The gate is correct. It has nothing to
discriminate between. But the practical effect is that frob currently has NO
incremental or partial release gating in force, only a single implicit 1.0.0
bucket -- while the docs and the gate suite read as though release trains are
enforced.

THE DECISION THIS TICKET NEEDS (owner input required -- do not invent the
partition unilaterally): what the milestone set is. A defensible starting cut,
given the repo's actual critical path:
  - the natives (frob-core, strata-core) are not on PyPI, so adopting frob in
    another repo requires building Rust from source;
  - there is no verified green CI run on any platform (Windows 278 known
    failures, macOS ~144 uncharacterised, Linux never verified green);
  - `release.yml` already implements manual-dispatch build with a separate
    consent-gated upload job behind a protected environment.
So "M1 = green matrix + wheels published" is a plausible first milestone, with
the language-expansion epics and the WARN-tier burn-downs falling to later ones.
PROPOSE the partition with reasoning; do not stamp 346 tickets before it is
agreed.

SEQUENCING once the set is agreed:
  1. Define the milestones and their order.
  2. Stamp the queue. This is bulk ledger mutation -- the ledger is the most
     contended machinery in this repo, so do it in batches, not one command, and
     never hand-edit tickets.md.
  3. Let MILE001 enforce the ordering, and verify it actually fires by planting
     a deliberate later-milestone blocker (a positive control). A gate that has
     never fired is not known to work.

DO NOT REMOVE THE DEFAULT. `default_milestone` is what keeps MILE003 from
flooding; dropping it before the queue is stamped turns 346 tickets into 346
ERRORs at once.

ACCEPTANCE
- A proposed milestone set with reasoning, agreed before any bulk stamping.
- The queue stamped, with a stated count per milestone.
- MILE001 demonstrated FIRING on a planted later-milestone blocker (positive
  control), then the plant removed.
- A statement of what `REL2xx`/`REL3xx` actually gate -- staged/partial release,
  or only version coherence. This was not verified when this ticket was filed
  and should not be assumed.


OWNER DECISION RECORDED 2026-08-28 -- this ticket was blocked on exactly this
and is now unblocked.

The owner's stated goal: a fully green CI matrix and a WORKING `frob` on PyPI
BEFORE 1.0.0. PyPI currently serves 0.0.9 and is badly stale. The first publish
carries 0.530.0 as-is (the existing `.frob-release.json`/REL001 authority), NOT
a renumber -- see T-3251 for that reasoning.

So the milestone partition is no longer a hypothetical. There are at least two
real milestones, and `default_milestone = "1.0.0"` in frob.toml is now
demonstrably wrong: it asserts that shipping to PyPI and reaching 1.0.0 are the
same event, which the owner has just said they are not.

THE PARTITION THIS DECISION IMPLIES (propose, do not assume -- the owner sees
the final split):
  - 0.530.0 -- "publishable": a green CI matrix on all three platforms, and an
    artifact that installs and works from PyPI. Everything genuinely required
    for a user to `pip install frob` and have it function.
  - 1.0.0 -- everything else currently sitting in the default bucket.

KNOWN 0.530.0-BLOCKING WORK at the time of writing (verify each; states move):
    T-3246  SUITE-RESULT renders an aborted run as a completed one
    T-3247  whole-repo-scan tests blow the 120s cap and abort the suite
    T-3250  macOS CI hangs at 99% with zero diagnostics
    T-3249  unowned 11-failure cluster, load-dependent
    T-3251  release can be dispatched from a red main
Note these are the CURRENTLY KNOWN blockers, not a closed set -- a green matrix
may surface more. Do not treat this list as the definition of the milestone.

WHY THIS IS THE POINT OF THE TICKET. MILE001 (blocked_by a later milestone) and
MILE003 (unresolvable milestone) are registered and wired but STRUCTURALLY
INERT: with every ticket in one bucket, no ticket can ever be blocked by a later
milestone, so MILE001 cannot fire by construction. The machinery has never once
been exercised against real data. A partition makes it live -- and the first
thing it should catch is a 0.530.0 ticket blocked_by a 1.0.0 ticket, which is a
release that cannot ship.

DO NOT DO A BULK BACKFILL. This ticket's original body already warned against
writing `milestone: 1.0.0` into every open ticket file, and that warning stands
with the numbers changed. A mechanical mass-edit produces a partition nobody
believes and that nobody can defend per-ticket. Derive the 0.530.0 set from what
actually blocks a green matrix and a working install, ticket by ticket, and say
what rule you used.

PROVE THE MACHINERY WORKS ON THE WAY THROUGH. A must-fire fixture where a
0.530.0 ticket is blocked_by a 1.0.0 ticket and MILE001 FIRES is worth more than
the partition itself -- it is the only evidence that these gates do anything.
This repo has been bitten repeatedly by catalogued-but-unenforced machinery, and
by "shipped" features whose code path was never reachable. Positive control or
it proves nothing.

ACCEPTANCE
- `default_milestone` no longer conflates shipping with 1.0.0.
- A 0.530.0 set derived per-ticket from a STATED rule, not a bulk write.
- MILE001 demonstrated FIRING on a real (or fixture) later-milestone block, and
  MILE003 likewise -- both were inert before this change.
- The owner sees the proposed split before it is treated as settled.
