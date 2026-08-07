---
id: T-0178
title: 'agentic time profiling: non-gated breakdown of where development time goes'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/tickets/**
- src/frob/stats/**
- scripts/**
- docs/modules/stats.md
- tickets.md
- docs/modules/app.md
- tests/test_app.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/guides/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/guides/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/app.md
  reason: T-0178 app work maps to docs/modules/app.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_app.py
  reason: T-0178 app work maps to tests/test_app.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_telemetry.py::test_timed_call_records_event_and_returns_value
- tests/test_telemetry_hook_script.py::test_hook_redacts_secret_looking_input
designated_repro_test: null
threat: null
component: null
---
Diagnostics ONLY -- explicitly NOT a gate family: no rule ids, nothing fails on these numbers, report-only (user directive: for designing tooling around, never for gating). Deliverables: (1) frob CLI entry timing hook -- every frob invocation appends {iso_ts, subcommand, args_head, duration_ms, exit, tree_hash} to .frob/telemetry.jsonl (local-only, already gitignored via .frob/, opt-out env var FROB_NO_TELEMETRY); reuse the per-gate timing frob check already computes by logging it structured instead of display-only. (2) ISO timestamps on ticket state transitions (created/started/done currently date-only) so per-ticket cycle time is computable. (3) EXTERNAL TOOL COVERAGE: ship a Claude Code PostToolUse hook script (scripts/frob-telemetry-hook + docs/guides page with the settings.json snippet) that appends every harness tool invocation -- Bash command head, duration, exit -- to the same telemetry stream; hooks fire for subagents too, so implementer/reviewer runs are covered without per-tool shims; document an optional PATH-shim mode for profiling outside the harness. (4) frob stats --agentic report over the merged stream: per-ticket cycle time and review-round count (parse Done-report addenda), command-time breakdown by category (frob-check / test-suite / native-build / vcs / other), top wall-clock sinks, and RETREAD DETECTION -- identical command+tree_hash re-runs counted as cache-hit candidates, which directly quantifies the T-0177 daemon payoff before it is built. (5) coordinator flow: document attaching the harness usage block (tokens, tool_uses, duration per dispatch role) at ticket close via the existing frob ticket attach, so cost history survives sessions. Privacy: telemetry never committed, never networked, redact anything matching the T-0157 secrets patterns before writing the command head. Tests: hook script emits valid JSONL under fake invocations; stats aggregation over a fixture stream; redaction case.

Addendum (user, 2026-07-18) -- TOKENS as a first-class dimension beside
time: (a) per-tool-call token cost -- the PostToolUse hook also records
an output-size token estimate (len/4 heuristic is fine; note the method)
for every tool result, since tool OUTPUT is what silently consumes agent
context: the report must rank tools by cumulative output tokens (e.g.
'frob check dumps cost N tokens/run x M runs') to identify which tools
need quieter output modes or pagination; (b) per-development-stage
attribution -- bucket both time and tokens by lifecycle stage, using the
telemetry markers already present in the stream (frob ticket start ->
first edit -> first test run -> evidence recording -> done report) and
by dispatch role (implement / review / rework round N / land), so the
report answers 'what does a REJECT round cost in tokens and minutes'
with measured numbers; (c) the coordinator-attached harness usage block
(subagent_tokens, tool_uses, duration per dispatch) is the ground truth
to reconcile the per-call estimates against -- report both and the
discrepancy.

Addendum 2 (user, 2026-07-18) -- PER-TEST TIMING ANNOTATIONS: track
per-test wall-clock as a Gaussian running estimate (Welford mean/sd/n,
persisted in .frob telemetry keyed by pytest node id, fed by the
existing test-run machinery). Write the estimate as a comment annotation
on the test itself (e.g. `# frob:perf mean=12.4s sd=1.1 n=9` above the
test def), updated ONLY when the new mean shifts beyond 2 sigma from
the annotated value -- statistical update to avoid diff churn, never
per-run rewrites. Consumption: frob test / frob check gain a fast mode
that SKIPS tests whose annotated mean exceeds a configured threshold,
and skipping is LOUD (summary names every skipped-slow test and its
annotated cost); the full check always runs everything -- fast mode is
an explicit opt-in, never the default for release/CI gates (vacuous-pass
doctrine: a skipped test must be visible, and the full gate is the
authority).