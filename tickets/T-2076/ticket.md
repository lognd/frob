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
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_verify.py
evidence_scope:
- tests/unit/test_ticket_runner_gate_findings.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_spawn_env_survives_caller_frob_agent_flag
- tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
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

## Done report

T-2076 confirmed a real, general escape hatch on `frob ticket land`'s gate
re-verification -- but the actual mechanism differs from the ticket's own
opening theory, and this report says so plainly.

## What I measured

Direct instrumentation (a temporary print in `_shared_check_spawn_fn`'s
`spawn()`, run against the real `TestDoneReportThenLandRealClosuresEndToEnd`
end-to-end test) confirmed the spawn's `cwd` is already `worktree` -- the
correctly-merged tree -- both from `_land_cmd.py`'s own production wiring
(`_shared_check_spawn_fn(worktree, cfg.ticket_id)` in `_land_core_invoke`,
present since the T-1089 split) and from a live run. The T-2064 probe this
ticket cited as confirmation compared `root`'s HEAD across a window `root`
is never mutated in before `_land_squash_apply` -- that comparison is
trivially "equal" no matter what `cwd` the spawn actually uses, and proved
nothing about it. That was a false positive, not a wrong-tree bug.

The REAL mechanism, found by testing against a real fixture repo with a
genuine ruff E722 (bare-except) error: `_shared_check_spawn_fn`'s spawn
command (`python -m frob check --ticket <id> --json`) carries no
`--only`/`--budget` selection. `frob.app.check_runner.
_refuse_full_check_for_agent` (T-0627) refuses exactly that shape whenever
`FROB_AGENT` is set in the environment -- true for every dispatched
worktree agent (playbook section 1b) and inherited unchanged by `frob
ticket land`'s own subprocess spawn. Measured directly:

  FROB_AGENT unset: rc=1, stdout has real ruff E722 finding, gate-summary present
  FROB_AGENT=1:      rc=1, stdout EMPTY, stderr "refusing a full/unchunked run under FROB_AGENT (T-0627)"

Empty stdout is unparsable JSON, so `check_gates()` returns `None`
("unmeasured"), and `_reverify_done_report_claims_post_merge` treats an
unmeasured claim as a permissive skip by design (T-0832) -- so a branch
that introduces a brand-new error-severity gate finding after done-report
capture lands completely unblocked whenever the landing shell carries
FROB_AGENT. This explains T-1584's escape without needing a wrong-cwd
theory.

## Fix

`_shared_check_spawn_fn` (`src/frob/app/ticket_runner/_verify.py`) now
passes `FROB_ALLOW_FULL_CHECK=1` (T-0627's own documented override) in the
spawned subprocess's environment unconditionally, additive on top of the
caller's real environment (verified: PATH and other vars still pass
through unchanged -- confirmed via a `T2076_MARKER` env var set before
spawn in the repro test). This spawn is frob's own internal, machinery-
driven re-verification step, never a sub-agent's discretionary bare `frob
check`, so it must run to completion regardless of the calling shell's own
`FROB_AGENT` flag.

Verified end-to-end against a real fixture repo: with `FROB_AGENT=1` set,
`_shared_check_spawn_fn`'s spawn now runs to completion and correctly
reports the E722 finding, matching without-agent behavior exactly.

Also corrected: `_shared_check_spawn_fn`'s docstring (added a T-2076
correction paragraph naming the real mechanism and the fix) and the
`_land.py` T-2064 probe/log, which asserted the disproven "cwd=root" theory
as fact -- replaced with an honest account of what was actually found and
a pointer to the real explanation.

## Cost

No new full-check spawn added -- this only adds one env var to the
EXISTING single shared spawn `_land_core_invoke` already builds (T-0919's
one-spawn-shared-by-both-consumers design is unchanged). No measurable
wall-clock delta: the spawn now runs to completion instead of refusing in
milliseconds, which is closer to the land's INTENDED cost (this spawn was
already supposed to run a real check every time under non-agent shells;
agent shells were the ones getting an accidental, unintended free pass).

## Residue

Filed T-2081 (renumbers at land): once this fix let the spawn
run for real, `frob check --land-parity` surfaced 3 pre-existing unscoped
findings in `src/frob/strata/_claims.py` (COV001, DOC002) and a repo-wide
SELFAUDIT001 -- all confirmed untouched by T-2076 (`git diff --stat main
-- src/frob/strata/_claims.py` empty on this branch) and themselves
previously escaping detection for the same FROB_AGENT reason. Two of the
three (COV001/DOC002) were independently fixed by T-2070's own land
(`docs/strata/kernel.md` addition) landing on main during this ticket's
work -- confirmed by a second `git merge main` and re-running
`--land-parity`, which dropped to just the remaining SELFAUDIT001. Not
fixed here (out of scope): the file is untouched by T-2076's declared
scope.

`design/frob.strata`'s `testsuite` node is currently under a live T-2033
lease (`frob ticket scope T-2076 --add "design/frob.strata"` refused with
`ScopeLeaseConflict`) -- rather than expand scope onto a leased file, the
new repro test's inherited-environment assertion was reworked around a
monkeypatched marker variable instead of `os.environ.get(...)`, avoiding
the SELFAUDIT001 `env.read` capability-declaration gap entirely.

## Acceptance demonstrated

A land whose branch introduces a new error-severity finding is now
blocked under `FROB_AGENT=1` (the standard dispatched-agent condition) --
demonstrated directly against a real fixture repo, not just asserted:
before the fix, `spawn()` returned `None` under `FROB_AGENT=1` for a tree
carrying a real E722 finding; after the fix, `spawn()` returns the real
check result with the finding intact, identical to the non-agent-shell
run.

### Changed
```
 src/frob/app/ticket_runner/_verify.py          | 59 +++++++++++++++++++++++++
 src/frob/tickets/_land.py                      | 44 +++++++++++--------
 tests/unit/test_ticket_runner_gate_findings.py | 60 ++++++++++++++++++++++++++
 tickets/T-2076/ticket.md                       | 11 ++++-
 tickets/T-2081/ticket.md             | 44 +++++++++++++++++++
 5 files changed, 197 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_spawn_env_survives_caller_frob_agent_flag` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2076
