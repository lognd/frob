---
id: T-draft-6fd4eae5
title: Audit closes landed 2026-08-10..2026-08-27 for D-02 self-cover false positives
  (T-1944/T-3141)
state: queued
kind: bug
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
- tickets/
scope_breadth_ack: true
scope_breadth_ack_reason: audit ticket over ticket history/evidence bindings, not
  a code-scope change; no narrower glob applies
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
T-3141 fixed a D-02 (evidence_covers_scope) regression: from T-1944
(commit 49abc109e, landed 2026-08-10) until T-3141's fix, ANY evidence
cited via add_evidence auto-satisfied D-02's scope-binding check by
definition (evidence_scope was auto-widened to include the evidence's
own file, which the same check then self-matched against). D-02 has
therefore been a no-op for any close/land whose evidence was not
already covered by declared scope or a genuine TESTS graph edge, for
roughly 17 days.

## Plan
Audit tickets closed/landed in the window 2026-08-10..2026-08-27 whose
evidence relied ONLY on the now-removed self-cover route (i.e. would
have failed D-02 under the corrected check) to determine whether any
should not have closed -- cross-reference against T-3046's evidence-reach
classifier (733 bindings, 95.5% reaching / 1.2% not reaching / 3.3%
unknown) as an independent signal on the same population.
