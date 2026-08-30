---
id: T-2371
title: Burn TEST003/TEST006/TEST014 WARN gates to zero, then promote to error
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence: []
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (test-hygiene checks): 31 across codes TEST003, TEST006, TEST014.

Do NOT hand-count with grep -- this repo has measured false zeros that way, including
one tonight. Re-measure with the same command above before starting and before
claiming done; treat any disagreement with the number in this body as the tree
having moved, not as your measurement being wrong.

Closure is two-part per the epic (T-0969):
1. Zero findings for every code above, verified via the same
   `frob check --json --budget 500 | python3 scripts/check_summary.py` command.
2. Each code above promoted from warning to error severity in its gate module
   (grep the gate module for its severity constant/mapping) -- a burn-down that
   stops at zero and leaves the gate advisory lets the debt silently reaccumulate.
   DOC012 and the T-1662 arc both closed correctly today by doing both; follow
   that shape, not a zero-only burn-down.

Narrow `scope` to the actual files this family's findings live in once you've
run the gate and can see them -- do not take a broad blanket scope; this keeps
you disjoint from sibling children of T-0969.

## Failure log
- 2026-08-30 attempt 1: Re-measured via 'uv run frob check --only test --json' in a fresh worktree, 2026-08-30: 72 findings across TEST003(30)/TEST006(1)/TEST014(41), not the ticket body's stale 31 (2026-08-18) -- the tree has moved, per the ticket's own instruction to treat that as the correct explanation. This burn-down needs real new integration-test authorship across Rust (frob-core/strata-core) and Python interfaces (TEST003, 30 sites), a policy call on whether TEST006's per-worktree coverage-stamp freshness should even gate a fresh checkout (1 site), and call-graph-informed disambiguation of 41 name-collision pairs concentrated in .claude/hooks/*.py (TEST014) -- each real work, not a mechanical directive-add, and far beyond a single normal-effort session without risking gamed/incorrect frob:tests bindings. Filed T-draft-8729dba3 with the full re-measured breakdown by file/rule for whoever picks this up next, split-scoped per T-2371's own instruction.
