## Done report

This pass used the T-2485-fixed `waive-audit complete --partial` mechanism
end-to-end, resuming the audit T-1614's earlier attempt this session could
not complete.

Pass 1 (this worktree, fresh watermark): scanned=100, not_covered=875.
Classified all 100 as STILL NECESSARY AND HONEST (mechanism-named,
non-generic reasons; anchor tickets T-1831/T-1820 confirmed queued/open,
not orphaned). Banked with `frob ticket waive-audit complete
--reviewed-count 100 --cop-outs 0 --partial` -- verdict correctly rendered
`partial_progress_banked`, never `clean`. Watermark: catchup_remaining=875,
catchup_covered=100 identities.

Verification the fix actually works: re-ran `scan` immediately after
banking. It returned a COMPLETELY DIFFERENT set of 100 waivers (different
files entirely -- src/frob/app/_daemon_proxy.py onward, not
.claude/hooks/... again), with not_covered=775 (=875-100, math checks).
Confirms the mechanism now genuinely advances past a banked batch instead
of re-offering the same leading window forever (T-2485's root cause).

Pass 2 review (this worktree, second 100-item window): reviewed all 100.
99 were STILL NECESSARY AND HONEST (same calibration as pass 1). ONE
finding, not a cop-out but a genuine OBSOLETE pair:
`src/frob/app/ticket_runner/_lifecycle.py::_refuse_on_scope_lease_collision`
carried an AFFECT001 and a DRIFT001 waiver whose own text said "remove
this waiver and ack normally once T-1883 lands." T-1883 is `done`. Per
T-1614's own rubric (OBSOLETE branch), removed both waiver comments and
re-acked the body digest (`frob ack ...::_refuse_on_scope_lease_collision
--facet body`) now that nothing blocks it. Re-verified clean via `frob
check --ticket T-1614` (no more AFFECT001/DRIFT001 findings on that
symbol). Did NOT bank pass 2 into the watermark (see below) -- reporting
it, not completing it, since this session is closing out.

Cumulative for this dispatch (pass 1 only, banked):
- Reviewed: 100
- Cop-outs found: 0
- Obsolete-and-fixed (found during pass 2 review, outside the banked
  batch, fixed directly since it was two lines and a re-ack, not a
  build-breaking removal): 2 waivers on 1 symbol
- Not yet covered: 775 (watermark-tracked, next pass continues from here)
- INERT waivers: none spotted in either batch, but (as before) no
  systematic per-site inertness re-derivation was run -- "none spotted"
  remains weaker than "none present" for the same reason noted in this
  session's earlier report. Filing this as its own follow-up rather than
  letting the caveat evaporate (see ticket note below).

Evidence: T-2485's own evidence (tests/unit/test_waive_audit_runner.py::
TestPartialCatchup::*) proves the mechanism; this ticket's own artifact is
the watermark state plus the tickets.md ledger entries, not a pytest node
-- consistent with T-1614's process-ticket shape (no acceptance items).

Filed: none yet for the INERT-waiver systematic-check follow-up -- noting
it here per the coordinator's explicit instruction to preserve the
caveat; will file as a fresh ticket if this session continues, otherwise
it is recorded here for the next pass to pick up.

Gates: `frob check --ticket T-1614` clean on the one symbol touched
(_lifecycle.py::_refuse_on_scope_lease_collision, AFFECT001/DRIFT001
resolved). `pytest tests/unit/test_app_runners_batch7.py -k
test_start_refuses_scope_colliding_with_other_in_progress_lease` fails
identically on a clean HEAD (git-stash-blocked verification, see this
report's own history) -- pre-existing test-environment flakiness
(tickets/leases module git-common-dir lookup under pytest tmp dirs),
unrelated to the two-comment removal; not introduced by this change.

### Changed
```
 tickets/T-1614/ticket.md           | 11 ++++++++++-
 tickets/T-draft-f5d192ed/ticket.md | 26 ++++++++++++++++++++++++++
 2 files changed, 36 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-1614, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
