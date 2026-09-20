## Done report

T-5122 fixes the silent-zero incident where `frob ticket land` printed
`LAND-PROOF ... verified=SKIPPED-UNMEASURED` next to `LAND-EXIT=0`: a
post-merge Done-report-claims re-verification that a caller genuinely
attempted (real `passed`/`check_gates` callables supplied) but that an
infrastructure failure (graph-cache lock contention, a crash, an
unparsable run -- `_ClaimsReverifyOutcome.INFRA_UNMEASURED`, T-4281)
prevented from ever running is UNKNOWN, not clean, and now refuses the
land by default (`LandError.ClaimsReverifyUnmeasured`,
`_enforce_claims_reverify_verdict` in `_land_finalize.py`, called from
`land()`'s own body in `_land.py` immediately after the outcome is
computed -- before the dry-run early return, so `--dry-run` proves the
refusal too). `frob ticket land --force --reason ...` overrides it,
recording the bypass via the existing T-1762 `record_force_override`
audit trail (`force-overrides.jsonl`) -- the same mechanism `frob ticket
archive --force` already uses; a blank reason still refuses even with
`--force`.

Deliberately left non-gating: `_ClaimsReverifyOutcome.SKIPPED_UNMEASURED`
-- a claims re-verification NEVER ATTEMPTED at all, by design (no
capture callables supplied at all, `--rapid`'s T-2913 inline-skip, or a
Done report with no `### Captured claims` section to compare against).
T-2083/T-4281's own docstrings are explicit this is a legitimate, common,
non-error shape; gating on it broke ~10 unrelated existing tests
(`tests/ticket_land_suite/test_claim_close.py`,
`tests/test_ticket_work_and_land_finish.py`) that exercise other `land()`
behavior and never supply those callables at all -- confirming this is
the correct, narrower boundary for the fix, not scope creep.

Scope was widened from the ticket's original three files
(`_land_finalize.py`/`_land_verify.py`/the new test) to also include
`_land.py` (the call site that must run the gate before the dry-run
early return), `_land_cmd.py` and `_progress.py` (thread the EXISTING
`--force`/`--reason`/`--reason-file` CLI flags -- previously only
covering the --finish/--retire-on-proof worktree-in-use refusal -- into
this new guard too), and `_models.py` (one new `LandError` variant). Each
was recorded via `frob ticket scope --add ... --reason ...` before the
edit.

`frob check --files <touched>` hung twice (fleet contention: several
sibling land/check invocations were running concurrently in other
worktrees at the time) and was BLOCKED per the coordinator brief's hard
rule after the second 590s timeout; `ruff check`/`ruff format` and the
full touched-file + adjacent claims-reverify test suites
(`tests/ticket_land_suite/test_land_proof_unmeasured.py`,
`tests/ticket_land_suite/test_claim_close.py`,
`tests/test_ticket_work_and_land_finish.py`,
`tests/test_land_verify_claims_outcome.py`,
`tests/test_ticket_land_proof_claims.py`,
`tests/unit/test_land_verify_claim_divergence_sentinel.py`) all pass
clean (191 node ids, 0 failed).

### Changed
```
 src/frob/_cli_parsers/_ticket/_progress.py         |   9 +-
 src/frob/app/ticket_runner/_land_cmd.py            |   8 ++
 src/frob/tickets/_land.py                          |  51 +++++++++-
 src/frob/tickets/_land_finalize.py                 | 101 +++++++++++++++++++
 src/frob/tickets/_models.py                        |  12 +++
 .../test_land_proof_unmeasured.py                  | 111 +++++++++++++++++++++
 tickets/T-5122/ticket.md                           |  39 +++++++-
 7 files changed, 327 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/ticket_land_suite/test_land_proof_unmeasured.py::TestEnforceClaimsReverifyVerdict::test_passed_is_ok` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_proof_unmeasured.py::TestEnforceClaimsReverifyVerdict::test_deliberate_skip_is_ok_not_gated` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_proof_unmeasured.py::TestEnforceClaimsReverifyVerdict::test_infra_unmeasured_refuses_without_force` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_proof_unmeasured.py::TestEnforceClaimsReverifyVerdict::test_unmeasured_with_force_and_reason_records_override_and_proceeds` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_proof_unmeasured.py::TestEnforceClaimsReverifyVerdict::test_unmeasured_with_force_but_no_reason_still_refuses` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_proof_unmeasured.py::TestEnforceClaimsReverifyVerdict::test_unmeasured_with_force_reason_file` (pytest node id, verified passing when recorded)
