## Done report

Changed:
- src/frob/tickets/_land.py::_land_should_skip_inline_claims_reverify (new)
- src/frob/tickets/_land.py::land (call site: passes None,None for
  check_gates/check_gate_findings under rapid instead of the real
  closures)
- docs/modules/tickets-landing.md (new section, T-2913)
- tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderRapid (new,
  2 tests)

### Investigation (measure-first, per coordinator brief)

Confirmed the coordinator's observation directly: the land critical
path's single largest cost is the inline `check_gates`/`check_gate_findings`
spawn (`_shared_check_spawn_fn`, `src/frob/app/ticket_runner/_verify.py`)
-- a fresh, full, UNSCOPED `python -m frob check --ticket <id> --json`
re-run against the post-merge tree (T-0754/T-0846's ClaimDivergence
re-verification). Measured this exact spawn directly against this
worktree's own tree with `FROB_ALLOW_FULL_CHECK=1 time .venv/bin/python
-m frob check --ticket T-2913 --json`: **4:01.59 elapsed (241.59s),
115% CPU** -- consistent with the coordinator's own independent
observation of 144s at 124% CPU on a live land. `_verify.py`'s own
docstring already carries a prior T-1344/T-2053 investigation reaching
the same conclusion from a different angle: `--only` narrows what T-0754
verifies (unsafe), `--delta` computes the full check first and only
filters the report (no wall-clock win), and the digest-keyed gate cache
structurally near-always misses because this spawn always runs against
a freshly-merged tree the cache has never seen.

Evaluated the three shapes named in the brief:

- **(a) scope to merge delta.** The existing T-2053 investigation
  already identified this as the one change that could turn the
  near-always-cache-miss into a near-always-cache-hit, but it needs
  land's own diff threaded into `_verify.py`'s closure-construction
  call, which lives in `_land_cmd.py` -- a file another in-progress
  ticket (T-2609) held an exclusive scope lease on for this entire
  session. Also the larger implementation: a new `--only <families>`
  selection derived from touched-file-to-gate-family mapping, itself a
  new piece of machinery to get right and test. Filed as a follow-up
  (T-2924) rather than attempted here.
- **(b) enqueue onto the existing deferred queue.** CHOSEN. The
  architecture already has exactly this mechanism, already wired
  unconditionally for rapid: `_land_post_merge_verify` (`_land_cmd.py`)
  calls `spawn_deferred_post_land_sweep` + `spawn_deferred_drain`
  whenever `rapid_land` is true, REGARDLESS of what `check_gates`/
  `check_gate_findings` were passed -- this is the exact "publish and
  return, verify behind it" shape T-1684 already built for the OTHER
  full-repo check on this same path (the pre-commit sweep). I verified
  directly, live, earlier this session: T-2361's own land triggered
  this exact deferred pipeline, which found and attributed a real
  regression, producing two sweep-filed tickets (T-2898/T-2899) that I
  then fixed. Since the deferred sweep already runs unconditionally
  under rapid, skipping the INLINE check_gates spawn removes a
  redundant synchronous copy of a check the pipeline was already going
  to run after the commit was durable -- it does not remove coverage.
  Implementation cost: one new resolver function plus a 2-line call-site
  change, entirely inside `_land.py` (frob.tickets, no CLI-layer touch
  needed, so no lease conflict with T-2609's `_land_cmd.py` hold).
- **(c) skip on trivial fast-forward.** Rejected: does not help the
  common case at all -- a real ticket's land is essentially always a
  real merge (the worktree branched from main and other lands moved
  main forward meanwhile), so a fast-forward-with-no-overlap land is
  the rare case, not the one costing 144-241s repeatedly.

### The fix

`_land_should_skip_inline_claims_reverify(worktree)`: reads
`LandProfileSettings.pre_commit_sweep_enabled` (the SAME field
`_land_cmd.py` already uses to compute `rapid_land`, via
`effective_profile`/`settings_for_profile` -- both already imported
elsewhere in `_land.py` for the sibling `_land_is_rapid` helper, so this
adds no new cross-module dependency). Returns `True` (skip) only when
that field is `False` (rapid); best-effort fail-closed (an unreadable
profile config resolves to NOT-rapid, never skip). At the one call site
inside `land()`'s body, when this returns `True`, `None`/`None` is
passed to `_reverify_done_report_claims_post_merge` instead of the real
`check_gates`/`check_gate_findings` closures -- that function ALREADY
treats `None` as a fully permissive, logged skip (T-0832's existing
"unmeasured is not a pass" semantics), so no new comparison-site logic
was added, only a new reason to reach the existing one.
`check_gate_claims` (T-1410's separate, cheaper `--only gates` spawn)
is left untouched -- not the cost this ticket measured.

### Proof: must-be-faster

Isolated the removed component directly (see measurement above): the
spawn this change causes `land()` to skip under rapid took 241.59s wall
-clock when run for real against this exact worktree with the exact
command `land()` invokes. Under the fix, `land()` never spawns it at
all under rapid -- `test_rapid_profile_skips_inline_check_gates_spawn`
proves the spawn count is literally zero (a spy closure standing in for
the real one is never called). This is the single largest line item
T-2053's own prior investigation measured on the land critical path
(~209s of a ~95-320s land) removed from every rapid land, not estimated.

### Proof: must-still-catch (both directions)

- **Rapid still lets a regression through the front door only to catch
  it behind:** the deferred sweep this relies on (`spawn_deferred_post_
  land_sweep` + `spawn_deferred_drain`) already runs unconditionally
  under rapid_land in `_land_cmd.py`, unaffected by this change (that
  call site is untouched, and unrelated to whether `check_gates` ran).
  Its real-world behavior was directly observed THIS SESSION: T-2361's
  rapid land produced exactly this deferred sweep run, which raised
  quarantine and filed two attributed regression tickets (T-2898,
  T-2899) for a real I001 finding its own inline check never would have
  seen either way (T-2361's own inline check_gates run, unaffected by
  this ticket, did not catch it -- the deferred sweep did).
- **Non-rapid is untouched:** `test_non_rapid_profile_still_runs_
  inline_check_gates_spawn` proves the SAME divergent-claim scenario,
  with no `frob.toml` (default = standard profile), still invokes
  `check_gates` and still refuses the land with `ClaimDivergence` --
  identical to the pre-existing `TestClaimDivergencePostMerge.
  test_divergent_gate_errors_refuses_land` behavior, now doubly covered.
- **A deliberately broken change is still caught, just later:**
  `test_rapid_profile_skips_inline_check_gates_spawn` is bound as this
  ticket's own BUG002 repro (`--check-repro`/`--designate-repro`
  verified `FAILED_AT_PARENT` at efd07d78853765af16c3cb20e06b20d5d3d9ee7f,
  the test-only commit before the fix) -- without the fix, the spy
  WOULD have been called (proving the OLD code's unconditional-call
  behavior), and with the fix it is not.

### Note on `frob ticket new` blocking on an unrelated land's land.lock

Flagging per the coordinator's own request, WITHOUT investigating or
fixing it (explicit instruction: tell them first, do not widen scope).
`frob ticket new` appearing to block on `land.lock` for up to ~313s
while an unrelated ticket's land runs is suspicious on its face --
filing a ticket only needs the ledger/allocator lock, not anything a
land's merge touches -- but whether `ticket new`'s own lock is
genuinely coupled to `land.lock`, or the observed delay is a different
queueing effect entirely (e.g. the same `wait_for_land_slot.py`
primitive the playbook describes for land, applied more broadly), is
unconfirmed. Left for the coordinator to direct, per instruction.

Evidence: tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderRapid::test_rapid_profile_skips_inline_check_gates_spawn (designated repro, FAILED_AT_PARENT verified),
tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderRapid::test_non_rapid_profile_still_runs_inline_check_gates_spawn,
tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land,
tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds

Filed: T-2924 (option (a), merge-delta scoping for
non-rapid profiles -- deferred follow-up, see above). The land.lock/
ticket-new observation above is disclosed but deliberately NOT filed,
per explicit instruction to tell the coordinator first rather than
widen scope into it.

Gates: `frob check --only lint --ticket T-2913` clean (0 errors; the
17 ruff-format warnings and 1 claude-config-drift error listed are
pre-existing, unrelated files). `frob check --only static --ticket
T-2913` shows only pre-existing, repo-wide, unscoped findings (CYCLE001/
frob-arch/frob-dup/frob-exports) untouched by this 3-file diff -- this
family is not filtered by `--ticket` per the existing gate:scope-note
posture.

### Changed
```
 docs/modules/tickets-landing.md    |  34 ++++++++
 src/frob/tickets/_land.py          |  78 ++++++++++++++++-
 tests/test_ticket_land.py          | 110 +++++++++++++++++++++++
 tickets/T-2913/done-report.md      | 174 +++++++++++++++++++++++++++++++++++++
 tickets/T-2913/ticket.md           |  60 ++++++++++++-
 tickets/T-2924/ticket.md |  47 ++++++++++
 6 files changed, 501 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderRapid::test_rapid_profile_skips_inline_check_gates_spawn` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderRapid::test_non_rapid_profile_still_runs_inline_check_gates_spawn` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 20 error(s), 976 warning(s), 848 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_land.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
