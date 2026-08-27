---
id: T-3147
title: Audit closes landed 2026-08-10..2026-08-27 for D-02 self-cover false positives
  (T-1944/T-3141)
state: done
kind: docs
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
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: 'pure audit/measurement ticket, no code change -- matches the established
    convention for this shape (T-2892, T-2909: investigation/audit closing on doc
    output only), which is the ONLY legitimate D-02 route available post-T-3141 fix
    for a no-code-surface ticket'
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_measure_evidence_reach.py::TestMeasureEvidenceReachMain::test_runs_clean_over_a_minimal_ticket_ledger
- cmd:uv run python /tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/audit_d02.py
  exit=0 sha256=13b392782051
kind_history:
- 2026-08-27 bug->docs evidence=1 done_report=no
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2b9985ecdb5a88969a1a73923e3befdf449defd0
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