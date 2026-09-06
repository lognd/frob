---
id: T-3933
title: 'F-171: vitest execution under frob''s evidence-cmd channel fails with import.meta.url
  not a file: URL'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_ts.py
- src/frob/testing/_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer report F-171: "import.meta.url is not a file: URL under the vitest setup frob's evidence-cmd channel uses." This is about EXECUTION (spawning vitest to actually run tests, via a [[test.runner]] command= template or cmd: evidence's shell invocation), not about node-id BINDING -- T-3925 fixed binding (F-134) using a SYNTHETIC LANGUAGE_COLLECTORS['ts'] stand-in in TestTicketEvidenceVitestOracle, which never spawns a real vitest process, so the execution path this report concerns is UNPROVEN by that work. Flagged while addressing F-167/F-134 follow-up so the T-3925/T-3847 support matrix's "verify" column for ts is understood correctly: BINDING is proven end-to-end, real vitest EXECUTION is not.

Investigate: how frob invokes vitest at run time (run_selected's RunnerSpec.command template for a [[test.runner]] language="ts" entry, or the cmd: evidence channel's shell invocation) -- likely a cwd/module-resolution mismatch causes the consumer's own vitest.config's import.meta.url usage to resolve to a non-file:// value (e.g. spawned with a relative cwd, or under an environment/loader frob's spawn helper (run_argv/apply_agent_env) alters in a way plain "npx vitest run" from a shell would not). Needs a real vitest project repro, not a synthetic collector stand-in, to pin down the actual spawn shape at fault.
