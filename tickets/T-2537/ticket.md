---
id: T-2537
title: 'tool parsers report a crashed run as zero findings: attach an error diagnostic
  on unparsable output'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/process/parsers/
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
T-2521 (landed 80aa49964) root-caused the terminal destruction of 7
sweep tickets / ~66 live finding identities to this:

    frob.process.parsers.ruff.parse_ruff_json's malformed-JSON fallback
    returns ToolResult(exit_code=1, diagnostics=[])

-- a FAILED run carrying an EMPTY diagnostic list and NO error
diagnostic, unlike its own siblings `tool_crash_result` and
`tool_disabled_result` which do attach one. A ruff-check crash under
fleet contention is therefore byte-identical to a clean run at the
ToolResult level.

T-2521 fixed the CONSUMERS: `_incomplete_tool_results` in
`src/frob/app/ticket_runner/_verify.py` now treats "failed exit code with
zero diagnostics of any severity" as unmeasured, wired into both the
deferred-sweep and doable-time revalidation paths. That closes the
specific hazard that destroyed the tickets.

THE PRODUCER STILL LIES. This ticket fixes that.

Why it matters even though the known consumers are now guarded: a
producer that reports failure as silence is wrong for EVERY consumer,
including ones not written yet. This repo has repeatedly been bitten by
exactly this shape -- a shared component that is correct for its original
consumer and silently wrong for the next one (the call graph resolving
callees by bare short name: fine for the dead-symbol gate, fatal for
attribution; then the same graph following only private names: fine for
internal-helper analysis, fatal for confinement). Guarding two call sites
leaves the third to rediscover the bug the expensive way.

DELIVERABLE: make the malformed-JSON / unparsable-output fallback attach
a real error diagnostic describing what failed, matching the
`tool_crash_result` / `tool_disabled_result` posture that already exists
in the same module. A caller reading only `diagnostics` must be able to
see that something went wrong.

SCOPE NOTE: `src/frob/process/parsers/eslint.py` has the same shape and
should get the same treatment. Check the other parsers in that package
too -- report which ones already attach a diagnostic on failure and which
do not, so the answer is a measured set rather than the two we happen to
have noticed.

POSITIVE CONTROLS, BOTH DIRECTIONS:
- a parser fed malformed/truncated JSON must produce a ToolResult whose
  diagnostics are NON-EMPTY and describe the failure;
- a genuinely clean run must still produce zero diagnostics and a zero
  exit code, unchanged (otherwise this converts every clean run into a
  false alarm);
- and: a warning-only nonzero exit (ruff-format's legitimate case, which
  T-2521 had to special-case downstream) must NOT be misreported as a
  crash.

Do NOT weaken T-2521's consumer-side guard as part of this. Defence in
depth is correct here: the producer should not lie AND the consumer
should not trust an empty set from a failed run. Both layers stay.
