---
id: T-2091
title: LAND-PROOF prints verified=True for lands whose claims re-verification was
  skipped as unmeasured
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land_proof_claims.py
evidence_scope:
- tests/test_ticket_land_proof_claims.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: the claims-reverify outcome must cross the land()->LandReport->_print_land_proof
    boundary; LandReport (extra=forbid, frozen) is the only channel, so adding one
    field there is required to thread the existing T-2083 outcome through per this
    ticket's own instruction
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/tickets/_models.py
  reason: 'reconsidered: LandReport is constructed in _land_squash.py (also out of
    scope) at both call sites, so extending it would require touching a third file;
    a module-level side-channel confined to the two declared scope files (_land.py
    writes, _land_cmd.py reads) avoids widening the write lease'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_ticket_land_proof_claims.py
  reason: new repro/evidence test file added for this ticket's own bug fix
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected
designated_repro_test: tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true
acceptance:
- text: given a land whose claims re-verification returns SKIPPED_UNMEASURED, when
    LAND-PROOF is printed, then it does NOT read verified=True and instead names the
    skip as its own distinct state -- this test MUST fail against current main
  evidence:
  - tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true
- text: given a land whose claims re-verification returns PASSED, when LAND-PROOF
    is printed, then it reads verified=True exactly as before -- no behaviour change
    on the healthy path
  evidence:
  - tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged
  - tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected
- text: given the change, when land wall-clock is measured, then no additional frob
    check subprocess has been introduced
  evidence:
  - tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged
threat: null
component: tickets
anchor: false
anchor_reason: null
---
## Origin

This is the half of T-2083 that was cut and disclosed rather than done.
T-2083 (landed `213eef2f3009`) closed the return-value ambiguity in
`_reverify_done_report_claims_post_merge`, which now returns a
`_ClaimsReverifyOutcome` (`PASSED` / `SKIPPED_UNMEASURED`) instead of a bare
`Ok(None)` at both unmeasured-skip sites. What it could NOT do is surface
that outcome, because the surfacing lives in files that were under another
ticket's live write lease (T-2082) for T-2083's entire duration.

NOTE: this ticket is a RE-FILE. T-2083's agent filed it once, it was
renumbered mid-land after an id collision, and the ticket file was then
overwritten by a merge of main and lost entirely -- it never reached main.
Its content is reconstructed here from the agent's report. The loss
mechanism is worth its own investigation and is NOT part of this ticket.

## The defect

`_print_land_proof` (`src/frob/app/ticket_runner/_land_cmd.py`) computes its
`verified=` field from ancestry plus ticket state, and NEVER consults the
claims re-verification at all. The caller in `src/frob/tickets/_land.py`
(around line 1658) discards the outcome entirely:

    if claims_check.is_err:
        ...

so nothing about "this land's claims were verified" versus "this land's
claims could not be measured and were skipped" reaches the operator-facing
LAND-PROOF line.

The consequence: `LAND-PROOF: verified=True` is printed for lands whose
claims were never checked. That word is the single line an operator or agent
reads to decide a land is sound, and it is currently asserting something it
does not measure.

This repo already knows this exact shape from another angle: LAND-PROOF has
reported `verified=True` on a commit containing NONE of the ticket's code,
because it checks ancestry, not content. Same field, same overclaim, second
mechanism.

## Why it matters now

The measured mechanism behind T-1584 landing 8 error-severity findings under
a Done report reading "land-parity: clean" was a guard that treated "could
not measure" as "found nothing" (fixed in T-2076). T-2083 made the skip
distinguishable INSIDE the verification layer. Until it is surfaced, the
operator still cannot tell a verified land from a skipped one -- which is
where the original incident actually went unnoticed.

## Measurement already done (from T-2083, do not redo)

Done reports missing a `### Captured claims` section:
  all history: 675 / 1492 (45.2%, dominated by pre-T-0754 tickets)
  last 300:    4 (1.3%)  -- T-1392, T-1476, T-1541, T-1573
  last 100:    2 (2.0%)
  last  50:    0 (0%)
So the skip path is rare on recent lands; surfacing it will be quiet in
practice, and a hard refusal later would be viable. This ticket is
surfacing, not refusal.

## DO NOT FIX IT THIS WAY

- **Do not report `verified=False` for a skip.** False asserts a negative
  verification result; a skip is a third state. Print it as its own word
  (e.g. `verified=SKIPPED-UNMEASURED`) or as a separate explicit field. The
  entire defect class is two different things sharing one indistinguishable
  representation -- do not fix it by picking the other of the two.
- **Do not add a new full `frob check` spawn to obtain a verdict.** Land cost
  is already the fleet's throughput ceiling (~210s inside the land lock).
  T-2083 already computes the outcome; thread the existing value through.
- **Do not silence the skip.** It must become MORE visible, not less.
- **Do not change what LAND-PROOF's ancestry check does.** That is a
  separate, known overclaim; conflating the two makes both harder to reason
  about.

## Lease note

T-2082 landed at `93de62f646e2`, so its lease on `_land.py` /
`_land_cmd.py` is released and this is now unblocked.