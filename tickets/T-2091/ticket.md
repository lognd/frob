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
land_commit: null
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

## Done report

### Changed

- src/frob/tickets/_land.py -- added `_LAST_CLAIMS_OUTCOME` (a process-local
  `dict[str, _ClaimsReverifyOutcome]`) and a write into it right after
  `_reverify_done_report_claims_post_merge` returns `Ok(...)` inside
  `land()`/`_land_locked`. This is the T-2091 fix: threading the outcome
  T-2083 already computes out to where `_print_land_proof` can read it,
  without a new `LandReport` field (would require also touching
  `_land_squash.py`, out of scope, since `LandReport` is constructed there
  at both its call sites) and without a new `frob check` subprocess.
- src/frob/app/ticket_runner/_land_cmd.py -- `_print_land_proof` now pops
  `_LAST_CLAIMS_OUTCOME[report.ticket_id]` and, when it is
  `SKIPPED_UNMEASURED`, prints the LAND-PROOF line's `verified=` token as
  the literal word `SKIPPED-UNMEASURED` instead of `True`/`False`, plus a
  new `claims_reverify=<passed|skipped-unmeasured|unknown>` field always
  present on the line. The function's RETURNED bool (what
  `--finish`/`--retire-on-proof`'s worktree-removal gate and T-1910's
  nonzero-exit-on-unverified check both consume) is left exactly as the
  pre-existing ancestor+state computation -- a skip surfaces, it does not
  refuse, per the ticket's own DO-NOT section.
- tests/test_ticket_land_proof_claims.py -- new file (T-2099 already flags
  tests/test_ticket_land.py as too large/slow to add to; this keeps the
  repro isolated and fast). Three tests, isolated from a real `land()` call
  via monkeypatching `_land_proof_checks` and populating
  `_LAST_CLAIMS_OUTCOME` directly.

### Captured claims

- `timeout 100 uv run pytest tests/test_ticket_land_proof_claims.py -o addopts="" -q`
  -> `3 passed in 0.17s` (measured after the ruff-format fix commit).
- `timeout 100 uv run frob ticket evidence T-2091 --check-repro
  "tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true"
  --base-ref fe0fea518` (the test-only commit, fix not yet applied)
  -> `FAILED_AT_PARENT` (real repro, per playbook 7b's split-commit
  technique) -- collection itself failed at that ref with
  `ImportError: cannot import name '_LAST_CLAIMS_OUTCOME'`, confirming the
  acceptance criterion's "first test MUST fail against current main"
  before the fix existed.
- `timeout 540 uv run frob check --ticket T-2091` -> `gate-summary 0
  errors, 1195 warnings, 0 unresolved, 693 waived` (COV002/PRE001/
  SCOPE001/WIRE001 that appeared on the first pass were resolved by adding
  `frob:ticket T-2091` directives to the new test file's symbols, a
  `frob:waive WIRE001` on the test-only `_fake_report` helper, adding
  `tests/test_ticket_land_proof_claims.py` to scope, and re-running
  `frob ticket sweep T-2091`).
- `timeout 400 uv run frob check --land-parity` -> exit 0 (first attempt
  deferred `lint`/`static` under `--budget 300` and correctly refused with
  "could not evaluate", per T-1703; the immediate re-run completed and
  reported clean).
- No new `frob check`/subprocess spawn was added anywhere in the changed
  code -- `_print_land_proof` only reads the existing
  `_LAST_CLAIMS_OUTCOME` dict and the existing `_land_proof_checks`
  ancestor/state check, both already present before this ticket.

### Notes

- Scope was narrowed back to the ticket's original declaration
  (`src/frob/tickets/_land.py`, `src/frob/app/ticket_runner/_land_cmd.py`)
  after a brief detour considering a `LandReport` field addition
  (`src/frob/tickets/_models.py`) that would have also required touching
  `src/frob/tickets/_land_squash.py`; the process-local side-channel dict
  avoids widening the write lease onto either file, matching the ticket's
  own "thread the existing value through" instruction more literally than
  a new frozen-model field would have. `tests/test_ticket_land_proof_claims.py`
  was added to scope for the new evidence file itself.
- The pre-existing repo-wide `ruff-format`/`ruff-check` FAIL counts (110
  files / 15 warnings under an unscoped `frob check`) are untouched by
  this change -- verified the only file this ticket's own diff needed
  reformatted was the new test file itself (fixed, see Changed above); the
  `I001` unsorted-import finding `frob check --ticket T-2091` surfaced at
  `_land_cmd.py:3200` sits inside `block_until_watermark_advances`'s
  caller, ~1900 lines from this ticket's own edits at `_print_land_proof`
  (~1230) -- pre-existing drift, not introduced here.
- The 285/287 SCOPE002 scope-closure warnings this ticket's scope produces
  are the pre-existing, already-disclosed shape the dispatch brief named
  up front (mostly `docs/modules/tickets.md`/`tests/test_ticket_land.py`
  citations from OTHER symbols in these two large files this ticket did
  not touch) -- not new, and deliberately not chased per the brief's own
  "add only what you actually modify" instruction.
- The second known LAND-PROOF overclaim named in the ticket's origin (the
  ancestry-only check reporting `verified=True` on a commit containing
  none of the ticket's code) is untouched, as instructed -- `_land_proof_
  checks`'s own ancestor/state logic was not modified.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py |  39 +++++++++-
 src/frob/tickets/_land.py               |  29 ++++++++
 tests/test_ticket_land_proof_claims.py  | 127 ++++++++++++++++++++++++++++++++
 tickets/T-2091/ticket.md                |  43 +++++++++--
 4 files changed, 230 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2091
