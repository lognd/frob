## Done report

New REL30x TRANSACTIONAL-BOUNDARY-obligation family (`src/frob/strata/
_txn.py`, mirroring `_ssot.py`'s REL29x store-node-scoped structure but
inverted -- op-node-scoped, grouping by the op writing rather than the
store written). REUSES `_ssot.py`'s store-writer-graph scan verbatim
(`Flow` edges into `store_ids`), flipping the grouping key from
`flow.dst` (REL29x) to `flow.src` (REL30x): REL300 fires when a single op
writes to >=2 distinct stores with no `transaction`/`saga` attr; REL301
is the declared-but-unproven leg (proof-against-code via
`_obligation_proof.py`'s shared owner-index/bound-code/token-scan
plumbing, no re-derivation).

`store_ids` kept as a caller-supplied parameter, not a `KernelModel`
fact -- the same "not reconstructible after elaboration" ceiling
SYS203/REL29x already disclose, reused verbatim rather than re-derived.

Both rules NODE-scoped (op), single-instance-per-op (not registered in
`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same carve-out
REL230/REL231/REL280/REL281/REL290/REL291 use).

Wired into `src/frob/strata/__init__.py`'s public surface
(`check_txn_boundary_obligations`, `TxnBoundaryReport`,
`TxnBoundaryViolation`, `REL_MISSING_TXN_BOUNDARY`,
`REL_UNPROVEN_TXN_BOUNDARY`, `TXN_RULES`). NOT wired into
`frob.app.sys_runner` for the same reason recorded in T-0646/T-0647/
T-0649's Done reports (every sibling landed REL2xx/REL29x family is in
the identical state today; `src/frob/app/**` is outside this ticket's
scope).

Added `docs/strata/reliability.md#rel30x-transactional-boundary-obligation-t-0650`
(surface vocabulary, grammar-data ceiling disclosure, waiver channel,
explicit out-of-scope note pointing at the separate cross-service
distributed-transaction/saga ticket), following the REL29x section
template, plus new see-also entries for `_ssot.py`/`test_ssot.py` that
were missing from the see-also list.

Tests: `tests/unit/strata/test_txn.py`, 9 cases: REL300 (multi-store-write
fires, single-store clean, transaction-attr discharges, saga-attr
discharges, empty store_ids emits nothing, waiver discharges), REL301
(unproven fires, proven discharges, no-bound-code uncheckable).

Pre-implementation check: verified `_ssot.py`/REL29x (T-0649) exists but
no REL30x/transactional-boundary module existed anywhere in the repo
before this ticket (`grep -rn "REL3[0-9][0-9]"` returned nothing) -- this
was NOT pre-implemented, built fresh.

Measured:
- `uv run pytest -q tests/unit/strata/test_txn.py tests/unit/strata/test_ssot.py`
  -> 18 passed.
- `uv run ruff check` / `uv run ruff format --check` on the touched files
  -> clean (one import-sort + one line-length fix applied before this).
- `uv run frob check --ticket T-0650 --only gates-fast` -> PASS 0 errors
  (after `frob ticket sweep T-0650` refreshed PRE001 against the final
  file set).
- `uv run frob check --ticket T-0650 --only gates-native` -> PASS 0
  errors.
- `uv run frob check --ticket T-0650 --only gates-security` -> PASS 0
  errors.
- `uv run frob check --ticket T-0650 --only lint` -> PASS 0 errors.
- `uv run frob check --ticket T-0650 --only static` -> PASS.
- `uv run frob test --base main` -> PASS (touched-set selection, exit=0).

Cuts: none against the stated acceptance criterion. CLI/sys_runner wiring
and the cross-service distributed-transaction/saga obligation are
intentionally out of scope (separate ticket already filed in tickets.md).
Filed: none (no new tickets needed).
