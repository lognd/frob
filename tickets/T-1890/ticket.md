---
id: T-1890
title: Dangling registry reference CHK-GATE-SYS104 reds the REG gate on main
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED by the T-1877 implementer agent, 2026-08-09, and confirmed present on main BEFORE that ticket's edits: 'frob check --only registry' reports 1 error, a dangling reference to CHK-GATE-SYS104. This is pre-existing residue unrelated to T-1877, but it means the REG gate is not at zero on main and every agent that runs a scoped registry check sees a red it did not cause -- which trains agents to ignore REG output.

Fix: either restore the CHK-GATE-SYS104 entry the citation points at, or remove/re-home the citation if the check was retired. Determine WHICH by finding the commit that broke it; do not simply delete the citation to make the number go green -- if the check was retired, the retirement was incomplete and that is the real bug.