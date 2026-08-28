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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
