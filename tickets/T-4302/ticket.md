---
id: T-4302
title: clear the two residual unformatted files that predate the land-time formatting
  gate
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land_proof_claims.py
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the integration run's formatter check, when it runs after this lands,
    then no file in the repository would be reformatted
  evidence: []
- text: given the set of drifting files, when it is measured before acting, then the
    report names the set actually found rather than the two quoted in this ticket
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TWO FILES REMAIN UNFORMATTED ON THE INTEGRATION BRANCH, AND THEY ARE THE LAST KNOWN BLOCKER ON THAT RUN'S POSIX LEGS. Everything else from that run's eleven gate errors has been cleared.

WHAT THEY ARE. The land-proof claims test and the ticket-runner gate-findings unit test. Both were landed BEFORE the new land-time formatting gate went in, which is why that gate did not catch them: it is diff-scoped to the files a land actually touches, and neither has been touched by a land since the gate existed. That is the gate working as designed rather than a gap in it, but it does mean pre-existing drift is never swept by it.

WHAT TO DO. Run the project's format verb over these two files and land the result. Nothing else. Do not widen this into a repo-wide sweep, do not adjust the gate, and do not fix anything else you notice in those files.

CONFIRM THE PREMISE FIRST, BECAUSE IT MAY HAVE MOVED. Measure which files the formatter actually wants to rewrite before formatting anything, and report the set YOU find rather than the two named here. Several tickets today rested on counts that had changed by the time someone acted on them, including two I filed myself. If the set is empty, say so and drop this ticket with that measurement.

WORTH ANSWERING WHILE YOU ARE HERE. Since the new gate only sees files a land touches, pre-existing drift can sit indefinitely in files nobody happens to modify. Say in your report whether that is acceptable or whether something should periodically sweep the whole tree -- do not build that here, just record the judgement so the next person is not guessing.