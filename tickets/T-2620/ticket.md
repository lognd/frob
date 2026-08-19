---
id: T-2620
title: evidence_changes/EvidenceReplaceReasonMissing never got their promised tickets-data-storage.md
  entries (T-2612 audit)
state: in-progress
kind: docs
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-data-storage.md
- docs/modules/tickets-landing.md
- src/frob/gates/_mutation_evidence.py::mutation_evidence_violations
- src/frob/tickets/_evidence.py::replace_evidence
- src/frob/tickets/_models.py::Ticket
- src/frob/tickets/_models.py::TicketError
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: removing the four AFFECT001 waivers this ticket's doc work discharges
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: removing the four AFFECT001 waivers this ticket's doc work discharges
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_models.py
  reason: removing the four AFFECT001 waivers this ticket's doc work discharges
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: src/frob/gates/_mutation_evidence.py
  reason: narrowing to symrefs instead of whole files
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: src/frob/tickets/_evidence.py
  reason: narrowing to symrefs instead of whole files
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: src/frob/tickets/_models.py
  reason: narrowing to symrefs instead of whole files
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/_mutation_evidence.py::mutation_evidence_violations
  reason: removing the four AFFECT001 waivers this ticket's doc work discharges
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_evidence.py::replace_evidence
  reason: removing the four AFFECT001 waivers this ticket's doc work discharges
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_models.py::Ticket
  reason: removing the four AFFECT001 waivers this ticket's doc work discharges
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_models.py::TicketError
  reason: removing the four AFFECT001 waivers this ticket's doc work discharges
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Three T-1733 waivers cite T-1739's (and T-1715's) "live lease" on
docs/modules/tickets.md as the reason evidence_changes/
EvidenceReplaceReasonMissing/replace_evidence's own contract updates
never landed there:

  - src/frob/gates/_mutation_evidence.py::mutation_evidence_violations
  - src/frob/tickets/_models.py::Ticket (evidence_changes field)
  - src/frob/tickets/_models.py::TicketError (EvidenceReplaceReasonMissing)
  - src/frob/tickets/_evidence.py::replace_evidence

T-1739 is done. T-1733 documented the TEST018 mechanism in full in
docs/modules/gates.md (confirmed: "TEST018 (T-1733)" section exists,
docs/modules/gates.md:1009), which is why none of these waivers block a
real gate finding today -- but the waiver reasons explicitly promised
separate updates to docs/modules/tickets-data-storage.md (#data-models,
#error-types) and docs/modules/tickets-landing.md
(#frob-ticket-evidence---replace-t-1537) once the tickets.md lease
cleared, and grep confirms zero mentions of evidence_changes or
EvidenceReplaceReasonMissing in either file. That promised follow-up
never happened.

Add:
  - a data-models entry for Ticket.evidence_changes in
    docs/modules/tickets-data-storage.md#data-models
  - an error-types entry for TicketError.EvidenceReplaceReasonMissing in
    docs/modules/tickets-data-storage.md#error-types
  - the required-reason/evidence_changes behavior update to
    docs/modules/tickets-landing.md#frob-ticket-evidence---replace-t-1537

then remove all three COV001/AFFECT001 waivers listed above (they may
already collapse to fewer once accurate, since TEST018's own doc arguably
already covers the mutation_evidence_violations case -- verify against
COV001/AFFECT001 directly, do not assume).

Filed by T-2612's lease-premise audit (waiver-removal-vs-owed-work split).
