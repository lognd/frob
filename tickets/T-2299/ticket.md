---
id: T-2299
title: 'DOC012 debt: 24 CLI subcommands have no dedicated doc section, disclosed in
  T-1783''s Done report but never tracked; burn to zero then promote WARN->ERROR'
state: queued
kind: docs
origin: agent
created: '2026-08-17'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given the DOC012 backlog, when it is re-measured, then a child ticket exists
    for every remaining undocumented subcommand grouped by owning doc file
  evidence: []
- text: given all children are landed, when frob check --only docblocks runs, then
    DOC012 reports zero findings
  evidence: []
- text: given DOC012 measures zero, when the rule severity is promoted from WARN to
    ERROR, then a subsequent undocumented subcommand fails the gate
  evidence: []
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
T-1783 (landed 2026-08-17, commit 153f84bb) shipped a new gate **DOC012**:
every top-level CLI subcommand the live `[[docblocks.commands]]` registry
exposes needs a dedicated `## `-level heading under `docs/commands/` or
`docs/modules/`, not merely a DOC005 table row.

It shipped at WARN rather than ERROR, which was the RIGHT call: the
implementer measured **24 pre-existing undocumented subcommands**, and
shipping at ERROR would have reddened every unrelated land fleet-wide (the
T-0688 new-gate-at-WARN precedent).

THE GAP: that 24-item backlog exists only as prose in T-1783's Done report,
now at `tickets/archive/T-1783/`. Nothing tracks it, nothing schedules it,
and DOC012 cannot be promoted to ERROR until it is zero. This is exactly
the "we only pop the top half of the stack" failure mode -- a deliberate
scope cut that was disclosed but never converted into work. Per this repo's
own standing rule, cut scope is recorded as a TICKET with a reason, not as
a paragraph in a closed ticket.

REQUIRED:
 1. Read the disclosed 24-subcommand list out of T-1783's archived Done
    report, and RE-MEASURE it (`uv run frob check --only docblocks`) rather
    than trusting the number -- several subcommands may have gained doc
    sections since, and the list is a point-in-time claim.
 2. File one child ticket per coherent group of subcommands (group by
    owning doc file so scopes stay disjoint and the work parallelizes),
    parented to this ticket.
 3. This ticket is the epic-level tracker; it closes when DOC012 measures
    zero AND the rule has been promoted from WARN to ERROR, so the debt
    cannot silently reaccumulate.

NOTE ON SEQUENCING: promotion to ERROR is the whole point. A burn-down that
drives the count to zero without promoting the severity leaves the gate
advisory forever, and the next unlanded subcommand re-opens the hole
silently.
