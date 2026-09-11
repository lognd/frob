---
id: T-4426
title: T-4041 Done report cites dead draft T-draft-858a1bad, never promoted
state: in-progress
kind: docs
origin: human
created: '2026-09-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-4041/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: record draft-loss investigation and repair plan for T-4041's TICK006 finding
  actor: logan
  at: '2026-09-11'
  old_length: 0
  new_length: 1834
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TICK006 (phantom-filing gate) fires on T-4041's Done report: it claims
"Filed: T-draft-858a1bad (out-of-scope T-4172/archive-lease regression found
while working T-4066, ...)" but T-draft-858a1bad resolves to no block in
tickets.md or tickets-archive.md.

INVESTIGATED (read T-4041 and T-4394, git-logged the draft):
- Filing commit cfc17a573 ("chore(tickets): file T-draft-858a1bad T-0843
  archive live-lease guard defeated by T-4172 stale-lease reconciliation for
  just-closed tickets") shows the draft's own intended real id in its title
  as T-0843.
- No tickets/T-0843/ was ever created (checked active ledger and archive).
- The draft file itself (tickets/T-draft-858a1bad/ticket.md) no longer
  exists in the tree; its last touches are ba8b976cb/c2669e42e with no
  subsequent promotion/rename commit -- it was lost, not promoted.
- T-4394 (post-land sweep regression ticket) independently measured this
  same TICK006 finding and already classified it as pre-existing, disclosed
  draft-loss residue, not new damage from its own batch.

CONCLUSION: the draft was NEVER promoted to T-0843 or any other real id --
there is nothing live to repoint the citation to. The repair is to correct
T-4041's Done report to state the draft was lost (disclosed draft-loss,
T-0707/T-0615 incident class) rather than citing a dead id as if it
resolves.

ACTION: use ticket verbs only (frob ticket body --set-file or equivalent) to
edit T-4041's Done report text, replacing the dead
"Filed: T-draft-858a1bad (...)" line with an honest statement that the
draft was lost before promotion (disclosed, matches T-4394's own reading).
Do not hand-edit tickets.md. If the Done-report edit path itself cannot be
reached by a ticket verb (only by hand-editing the ledger), do not force it
-- report that back instead.

SCOPE: tickets/T-4041/** only.
