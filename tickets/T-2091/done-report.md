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
