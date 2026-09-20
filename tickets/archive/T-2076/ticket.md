---
id: T-2076
title: check_gates() land-time spawn reads root's PRE-land tree, not the merged tree
  (T-2064 confirmed)
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_verify.py
evidence_scope:
- tests/unit/test_ticket_runner_gate_findings.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-2076: this spawn carries no --only/--budget selection, so

    frob.app.check_runner._refuse_full_check_for_agent (T-0627) refuses it

    outright -- exit 1, EMPTY stdout -- whenever FROB_AGENT is set in the

    environment. frob ticket land inherits its own caller''s shell env

    unchanged, and every dispatched worktree agent carries FROB_AGENT=1

    (playbook section 1b), so in that (extremely common) case this spawn

    used to refuse silently every time: _parse_check_json cannot parse

    empty stdout, this closure returns None ("unmeasured"), and

    _reverify_done_report_claims_post_merge

    (frob.tickets._land_verify) treats an unmeasured check_gates() as

    "nothing to compare, permissive skip" by design (T-0832) -- so a branch

    that introduced a brand-new error-severity gate finding after

    done-report capture landed completely unblocked. Confirmed directly

    against a real fixture repo (T-2076 investigation) -- this is the

    actual escape mechanism T-1584''s Done report divergence traces to, not

    a stale/pre-merge cwd (a direct probe on this checkout confirmed this

    spawn''s cwd is already the correctly-merged worktree tree).'
  actor: logan
  at: '2026-09-19'
  old_length: 1663
  new_length: 2823
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_spawn_env_survives_caller_frob_agent_flag
- tests/ticket_land_suite/test_claim_close.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
- tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
designated_repro_test: tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_spawn_env_survives_caller_frob_agent_flag
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2064 confirmed by live instrumentation (root-tip probe in `_land_locked`,
see T-2064's own ticket body for the log line) that `check_gates()`'s
land-time spawn (`_shared_check_spawn_fn(root, ...)`, cwd=root) evaluates
root's PRE-land tree, not the merged tree -- because it is triggered from
`_reverify_done_report_claims_post_merge` inside `_land_locked`, which runs
BEFORE `_land_squash_apply` (the module's own documented "ONLY step that
mutates root"). The T-0754 ClaimDivergence check is therefore not checking
what its own docstring in `_verify.py` claims it checks ("always runs
against a FRESHLY MERGED tree").

Independent corroboration: T-1584's Done report claimed a clean
`--land-parity` (0 unscoped errors), yet a throwaway detached worktree at
T-1584's own landed commit (99ecae11dff1) shows 3 DOC005 + 6 SELFAUDIT001
findings deterministically. A pre-land-tree read at land time explains the
gap directly -- this is a silent, general escape hatch for every land whose
Done report captures a gate-state claim, not a one-off bad report.

Needs a real fix, spanning both `src/frob/tickets/_land.py` (the trigger
ordering inside `_land_locked`) and `src/frob/app/ticket_runner/_verify.py`
(`_shared_check_spawn_fn`'s own contract/docstring) -- out of a single-file
`_land.py`-scoped ticket's reach, and needs a decision on how the T-0754
staleness guarantee is preserved across the reorder (moving the spawn to
run after `_land_squash_apply` means it now checks the SQUASHED commit,
which may need its own care around dry-run unwind semantics). Not a
mechanical fix -- read T-2064's full body and `_shared_check_spawn_fn`'s
docstring before starting.

<!-- narrative-moved:src/frob/app/ticket_runner/_verify.py:1130:T-2076 -->
T-2076: this spawn carries no `--only`/`--budget` selection, so
`frob.app.check_runner._refuse_full_check_for_agent` (T-0627)
refuses it outright -- exit 1, EMPTY stdout -- whenever
`FROB_AGENT` is set in the environment. `frob ticket land`
inherits its own caller's shell env unchanged, and every
dispatched worktree agent carries `FROB_AGENT=1` (playbook
section 1b), so in that (extremely common) case this spawn used
to refuse silently every time: `_parse_check_json` cannot parse
empty stdout, this closure returns `None` ("unmeasured"), and
`_reverify_done_report_claims_post_merge`
(`frob.tickets._land_verify`) treats an unmeasured `check_gates()`
as "nothing to compare, permissive skip" by design (T-0832) --
so a branch that introduced a brand-new error-severity gate
finding after done-report capture landed completely unblocked.
Confirmed directly against a real fixture repo (T-2076
investigation) -- this is the actual escape mechanism T-1584's
Done report divergence traces to, not a stale/pre-merge `cwd`
(a direct probe on this checkout confirmed this spawn's `cwd`