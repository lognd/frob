---
id: T-3988
title: 'TESTRUN001: configured runner produced no tool result'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
blocked_by:
- T-3985
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a configured, non-disabled [[test.runner]] entry with no corresponding
    ToolResult after a completed run, when frob check/test runs, then TESTRUN001 fires
    naming the runner
  evidence: []
- text: given every configured runner producing a ToolResult, when frob check/test
    runs, then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-199 (T-3984 item 4). VERIFIED: git grep for TESTRUN001 found nothing existing. A direct instance of the subject-count primitive (T-3985): a configured [[test.runner]] entry is itself an "enforcing" surface (it is supposed to produce a tool result every run), and today nothing checks that it did.

FINDING THIS WOULD HAVE CAUGHT: a configured test runner (a [[test.runner]] entry in frob's config surface, per src/frob/testing/_runners.py's RunnerSpec) that silently produced NO tool result at all in a given run -- e.g. a broken command template, a runner that errors before producing parseable output, or a runner whose invocation is skipped by some upstream condition -- with nothing distinguishing "ran clean" from "never ran." Proposed: TESTRUN001 fires when a configured, non-disabled test runner has no corresponding ToolResult in a completed frob check/test run.
