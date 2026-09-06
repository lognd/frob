---
id: T-3994
title: 'SEV001: severity overrides require reason/ticket and expire'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a [gates.severity] override with no reason= or ticket=, when frob check
    runs, then SEV001 fires
  evidence: []
- text: given a severity override whose ticket= has since closed, when frob check
    runs, then it is flagged as expired
  evidence: []
- text: given a properly reasoned, ticket-scoped, still-open override, when frob check
    runs, then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-205 (T-3984 item 10). VERIFIED: git grep for SEV001 across src/frob found nothing. src/frob/gates/_waive.py already implements frob:waive's reason/ticket/expiry discipline; [gates.severity] overrides (T-1002 managed zone, used extensively by T-3844) currently take no reason/ticket/expiry -- they are a bare rule-to-severity mapping in frob.toml with no accountability trail.

FINDING THIS WOULD HAVE CAUGHT: a severity override (a rule downgraded from its shipped default, e.g. error to warn) that has no attached reason or owning ticket and never expires -- exactly the kind of permanent, unaccountable exception frob:waive itself is explicitly designed to prevent for individual findings. A severity override is a strictly BIGGER exception (it silences an entire rule repo-wide, not one finding) and today has WEAKER accountability than a single-finding waiver.

Proposed SEV001: require every [gates.severity] override entry to carry reason= and ticket= (mirroring frob:waive's own fields), and expire (become a finding, or auto-revert) when the named ticket closes -- exactly as frob:waive already does. T-3844's own severity-zone edits are a live, current example of what such an override looks like without this discipline; use it as a fixture.
