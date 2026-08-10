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
