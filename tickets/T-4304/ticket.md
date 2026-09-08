---
id: T-4304
title: nothing ever sweeps the whole tree for formatting drift, so a file nobody touches
  can stay unformatted indefinitely
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a file that no land has touched since it drifted, when the periodic
    check runs, then the drift is detected without waiting for an integration run
    to fail
  evidence: []
- text: given the periodic check finds drift, when it acts, then what it does with
    the finding is a recorded decision rather than an unread report
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE LAND-TIME FORMATTING GATE IS DIFF-SCOPED BY DESIGN, WHICH IS CORRECT, AND IT LEAVES ONE GAP NOTHING ELSE COVERS.

The gate added today checks only the files a land actually touches. That is the right default: it keeps land latency proportional to the change, and it makes the finding attributable to whoever introduced it, while the drift is still cheap to fix. Nothing here argues for widening it to scan the whole tree on every land.

THE GAP. A file that no land happens to touch can sit unformatted indefinitely, because the only thing that would notice is a whole-tree check, and the only whole-tree check runs in the integration workflow -- where it surfaces as a red run attributed to nobody, long after the fact. That is precisely how the drift cleared today accumulated: two files went unformatted for hours, were invisible to the new gate because no land touched them again, and were found only because someone read a failing run's tool summary.

WHAT THIS SHOULD BE. A periodic whole-tree check, scheduled rather than on the land path. The recommendation came from the agent that cleared the residual drift, and its reasoning is sound: this closes the detection gap without making every land pay for a full scan.

DECIDE WHAT IT DOES WHEN IT FINDS SOMETHING. A scheduled job that merely reports has a way of becoming noise nobody reads. Consider whether it should open a ticket, or simply apply the formatter and land the result itself, given that the operation is deterministic and reviewable. Record the choice.

THIS IS DELIBERATELY LOW PRIORITY. The land-time gate stops NEW drift, which was the bleeding. This only covers the residue, and the residue is currently zero -- the tree is fully formatted as of today. File it so the gap is written down rather than rediscovered.