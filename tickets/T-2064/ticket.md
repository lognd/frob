---
id: T-2064
title: Confirm whether check_gates()'s land-time spawn (cwd=root) actually sees the
  merged tree, or root's stale pre-land state
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Surfaced while measuring T-2055 (_land_gate_claims_fn's spawn cost), NOT
confirmed by live instrumentation -- needs dedicated verification before
being treated as a real defect.

In src/frob/tickets/_land.py's `_land_locked`, the ordering is:

1. merge/finalize happen in `worktree` only
2. `claims_check = _reverify_done_report_claims_post_merge(worktree,
   ticket_id, passing_ids, check_gates, check_gate_findings)` runs --
   `check_gates`/`check_gate_findings` are zero-arg closures built earlier
   by the CLI (`_check_gates_summary_fn(root, ticket_id, ...)`,
   `_land_cmd.py:3355`) that spawn `frob check` with `cwd=root`, NOT
   `cwd=worktree`.
3. `check_gate_claims(reloaded)` runs next, spawning `frob check --only
   gates` with `cwd=worktree` (T-2055's own measured second spawn).
4. `_land_finalize_and_close` runs.
5. `_land_squash_apply(root, worktree, ...)` runs -- an inline comment a
   few lines above this call in `_land.py` names it explicitly as "the
   ONLY step that mutates root".

If that comment is literally true, step 2's `check_gates()` spawn (cwd=
root) runs BEFORE anything in this land has touched `root`'s own working
tree/branch at all -- meaning it evaluates `root`'s PRE-land state, not
the "just-merged tree" its own docstring in `_verify.py`'s
`_shared_check_spawn_fn` describes. If true, the T-0754 ClaimDivergence
check may not actually be checking what it claims to check, which would
be a significant, independently-discovered defect (or the comment/my
reading is wrong and something else keeps `root` in sync -- also worth
confirming).

This needs live instrumentation (a temporary log line recording `git rev-
parse HEAD` in `root` immediately before the `check_gates()` spawn during
a real land, or an equivalent test) to confirm or refute, not more
static reading -- filed rather than asserted as fact.

CONFIRMED by live instrumentation (T-2075's land, and a follow-up
`--dry-run` land of this ticket itself, both with the probe log line
this ticket's own instrumentation added at the `_reverify_done_report_
claims_post_merge` call site in `_land_locked`):

    land: T-2064 T-2064 probe: root HEAD immediately before the
    check_gates() spawn is 176a24f5aa7e206944f2f16e6192b765b162edfa;
    this run's captured pre-mutation tip (root_pre_land_tip) is
    176a24f5aa7e206944f2f16e6192b765b162edfa -- equal means the spawn
    (cwd=root) observes root's PRE-land state, not a merged tree

Root's live HEAD immediately before the call that (when the Done
report's captured claim is measured) triggers `check_gates()` is
IDENTICAL to `root_pre_land_tip`, the tip this land captured before any
mutation. Combined with the static fact already in this ticket's own
body -- `_land_squash_apply` runs strictly AFTER this point and is the
module's own documented "ONLY step that mutates root" -- this is
conclusive: whenever `check_gates()` actually fires, it evaluates
`root`'s PRE-land tree, not the merged tree its own docstring
(`_shared_check_spawn_fn`, src/frob/app/ticket_runner/_verify.py) claims
("always runs against a FRESHLY MERGED tree"). The T-0754
ClaimDivergence check is not checking what it claims to check.

Independent corroboration, not previously recorded on this ticket:
T-1584's own Done report claimed "frob check --land-parity: clean -- 0
unscoped error(s)", yet checking out T-1584's exact landed commit
(99ecae11dff1) into a throwaway detached worktree and running `frob
check --only docblocks --json` / `--only sys --json` unscoped there
fires 3 DOC005 findings (2.84s) and SELFAUDIT001 six times,
deterministically, at that commit. Neither rule is exempted by
`_drop_checkpoint_exempt_findings`, both stages are ordinary `_STAGE_
GROUPS` members inside land-parity's `--budget 300`, and `land_parity_
findings` forces `FROB_NO_GATE_CACHE=1` -- no blind spot in land-
parity's own coverage explains the gap. A pre-land-tree read explains it
directly: T-1584's own land-time `check_gates()` spawn was clean because
it evaluated `root` BEFORE the merge that introduced the DOC005/
SELFAUDIT001 findings, not after. This generalizes beyond T-1584 -- it is
a silent, general escape hatch for every land whose Done report captures
a gate-state claim, not a one-off bad report.

This ticket did NOT implement a fix -- `_land.py`-only scope cannot
safely move `check_gates()`'s trigger point without also touching
`_verify.py` (`_shared_check_spawn_fn`'s docstring/contract) and
re-deriving the T-0754 staleness guarantee this reordering could affect
(see `docs/guides/agent-playbook.md` section 13's own ranked-proposal
precedent for how carefully that kind of change needs to be sequenced).
The instrumentation log line this ticket added stays in `_land.py`
(informational, gated behind `-v`) as a standing diagnostic for whoever
picks up the fix.

frob:no-behavior-change reason="investigation ticket -- confirms a defect but implements no fix; the real fix is filed separately as T-2076 since it needs to touch _verify.py as well as _land.py, out of this single-file ticket's scope"

## Done report

Investigated by live instrumentation, not by re-deriving the code
statically a second time. Added a log line in `_land_locked` (already
landed as part of T-2075) right before the call site that -- when the
Done report's captured claim is measured -- triggers `check_gates()`'s
land-time spawn (`cwd=root`), recording both root's live HEAD at that
point and `root_pre_land_tip` (this run's own pre-mutation tip, captured
at the very start of `_land_locked`).

Observed with `-v` on a real `--dry-run` land of this ticket:

    land: T-2064 T-2064 probe: root HEAD immediately before the
    check_gates() spawn is 176a24f5aa7e206944f2f16e6192b765b162edfa;
    this run's captured pre-mutation tip (root_pre_land_tip) is
    176a24f5aa7e206944f2f16e6192b765b162edfa

The two values are IDENTICAL. CONFIRMED: `check_gates()`'s land-time
spawn evaluates root's PRE-land tree, not the merged tree -- because it
fires (when it fires) strictly before `_land_squash_apply`, the module's
own documented "ONLY step that mutates root". This falsifies
`_shared_check_spawn_fn`'s own docstring claim in `_verify.py` that the
spawn "always runs against a FRESHLY MERGED tree".

Also recorded (not previously on this ticket): the T-1584 corroboration
the coordinator supplied -- a throwaway detached worktree at T-1584's own
landed commit shows 3 DOC005 + 6 SELFAUDIT001 findings deterministically,
despite T-1584's own Done report claiming a clean `--land-parity`. A
pre-land-tree read at land time explains that gap directly, and
generalizes it from "one bad report" to a standing, silent escape hatch
for every land whose Done report captures a gate-state claim.

Separately observed, not chased further (out of this investigation's
scope, may be its own defect): in this repo's CURRENT state,
`check_gates()`'s own spawn consistently fails to produce a parsable
gate-summary at all (`WARNING: ... produced no gate-summary tool result
(exit=1)`), even though a direct, equivalent `frob check --ticket
T-2064 --json` run DOES contain a `gate-summary` tool result at that same
exit code. This meant the actual `check_gates()` subprocess never fired
during either of the two lands this investigation observed -- the
CONFIRMED finding above rests on the log line firing unconditionally
before that call, not on the subprocess spawn itself succeeding. Filed no
separate ticket for this since it was not chased to a root cause; noting
it here so a future reader does not assume the subprocess spawn was
exercised.

No code fix is included -- see T-2076, filed for the real fix,
which needs to touch `_verify.py` as well as `_land.py` and is out of
this ticket's single-file scope. The instrumentation log line itself
stays in `_land.py` (informational, `-v`-gated) as a standing diagnostic.

frob:no-behavior-change reason="investigation ticket -- no code change accompanies this Done report; the instrumentation log line it relies on was already landed as part of T-2075 (the ARCH001 split), not this ticket's own diff"

### Changed
```
 tickets/T-2064/done-report.md      | 24 ++++++++++++++++++
 tickets/T-2064/ticket.md           |  6 ++++-
 tickets/T-2076/ticket.md | 50 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 79 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, COV001@src/frob/strata/_claims.py, DOC002@src/frob/strata/_claims.py
