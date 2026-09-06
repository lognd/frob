---
id: T-3995
title: --only with a known stage name does not actually filter
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: high
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given frob check --only ruff run against this repo, when it completes, then
    no ToolResult with tool=claude-config-drift (or other unconditional-tail checks)
    is present unless explicitly not gated by design
  evidence: []
- text: given any check that is deliberately left unconditional regardless of --only,
    when this ticket lands, then that is documented explicitly in --only's own help
    text
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-206 (T-3984 item 11). MEASURED SPECIFICALLY for this ticket, per the coordinator's instruction not to treat an earlier unknown-stage-name strike as covering this claim. The earlier measurement (elsewhere in this drive) found an UNKNOWN --only stage name is refused; this audit claims something different, that a KNOWN stage name does not actually filter.

MEASUREMENT: ran `frob check --only ruff --json` (ruff is a real, known entry in src/frob/check/__init__.py's _TOOL_STAGES) against this repo. Result: 3 ToolResult entries came back with tool values ruff-check, ruff-format, AND claude-config-drift. claude-config-drift is unrelated to the ruff stage -- reading src/frob/app/check_runner.py confirms _claude_config_drift_result(root) (and, in the same unconditional tail of run_check, _deploy_drift_result/_deploy_conformance_result) is called unconditionally at the end of run_check with no check against cfg.check_only at all. So --only ruff, a KNOWN stage name, does NOT actually restrict output to only that stage: at minimum the claude-config-drift (and likely deploy-drift/deploy-conformance) checks always run regardless of --only.

FINDING THIS WOULD HAVE CAUGHT (and this repo just reproduced independently): a user running `frob check --only <stage>` believing they scoped the run gets extra, unrelated findings anyway -- and by the same silent-zero logic this epic is about, might also get FEWER findings than expected from stages that DO respect --only, with no signal distinguishing "this stage was filtered out on purpose" from "this stage silently didn't run." Fix: either every unconditional tail check (claude-config-drift, deploy-drift, deploy-conformance, and any others added the same way) is gated by cfg.check_only when --only is given, or --only's own documentation/behavior is corrected to state plainly which checks it does NOT filter and why (some may be legitimately unconditional, e.g. cheap sanity checks) -- but today neither is true: it is undocumented and inconsistent.
