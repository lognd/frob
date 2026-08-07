## Done report

New REL29x SINGLE-SOURCE-OF-TRUTH-obligation family
(`src/frob/strata/_ssot.py`, mirroring `_circuit_breaker.py`'s REL23x
store-node-scoped structure): REL290 (missing owner/reconciliation -- a
multi-writer store, >=2 distinct non-store nodes with a Flow edge into
it, `_contention.py`'s SYS203 exact mode-blind detection re-derived here
for the full-writer-set shape REL290 needs, with no `owner`/
`reconciliation` attr) and REL291 (declared-but-unproven owner, proof-
against-code via `_obligation_proof.py`'s shared owner-index/bound-code/
token-scan plumbing, no re-derivation). Extends SYS203's DETECTION with
an OBLIGATION (ticket body's "extends SYS003 hub" -- the actual landed
codebase analog is SYS203's shared-store-write rule, `_contention.py`,
not a rule literally named SYS003; documented candidly in the module
docstring).

`store_ids` kept as a caller-supplied parameter, not a `KernelModel`
fact -- the exact same "not reconstructible after elaboration" ceiling
SYS203 already discloses (`_contention.py`'s module docstring), reused
verbatim rather than re-derived.

Both rules NODE-scoped (store), single-instance-per-store (not
registered in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same carve-out
REL230/REL231/REL280/REL281 use).

Wired into `src/frob/strata/__init__.py`'s public surface
(`check_ssot_obligations`, `SsotReport`, `SsotViolation`,
`REL_MISSING_OWNER`, `REL_UNPROVEN_OWNER`, `SSOT_RULES`). NOT wired into
`frob.app.sys_runner` for the same reason recorded in T-0646/T-0647's
Done reports (every sibling landed REL2xx family is in the identical
state today; `src/frob/app/**` is outside this ticket's scope).

Added `docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649`
(surface vocabulary, grammar-data ceiling disclosure, waiver channel),
following the REL23x/REL28x section template.

Tests: `tests/unit/strata/test_ssot.py`, 9 cases: REL290 (multi-writer
fires, single-writer clean, owner-attr discharges, reconciliation-attr
discharges, empty store_ids emits nothing, waiver discharges), REL291
(unproven fires, proven discharges, no-bound-code uncheckable).

Measured:
- `uv run pytest tests/unit/strata/test_ssot.py tests/unit/strata/test_slo.py tests/unit/strata/test_observability.py tests/unit/strata/test_backpressure.py -p no:cacheprovider -q`
  -> 31 passed.
- `uv run frob check --only lint --ticket T-0649` -> PASS 0 errors 0
  warnings.
- `uv run frob check --only static --ticket T-0649` -> PASS (frob-exports/
  frob-dup/frob-arch/frob-cycle all pass).
- `uv run frob check --only gates-fast --ticket T-0649` -> PASS 0 errors
  (after `frob ticket sweep T-0649` refreshed PRE001 against the final
  file set).
- `uv run frob check --only gates-native --ticket T-0649` -> PASS 0
  errors (one new unwaived PERF004 warning at `_ssot.py:196`, a small
  per-store `sorted(writer_ids)` call inside the outer store loop --
  same shape as `_contention.py`'s own several pre-existing unwaived
  PERF004 sorted-in-loop warnings; left unwaived to match that
  established repo convention for this exact debt class rather than
  hand-waiving only this file's instance).
- `uv run frob check --only gates-security --ticket T-0649` -> PASS 0
  errors.

Cuts: none against the stated acceptance criterion. CLI/sys_runner
wiring intentionally out of scope (see above). T-0648 (SLO) was written
in the same worktree but is `blocked_by` T-0647 and could not be
`frob ticket start`ed here (`BlockerOpen`) -- its code + tests are
committed and gate-clean, but its own start/evidence/done-report ledger
steps are left for after the coordinator lands T-0647.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_multi_writer_store_without_owner_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_single_writer_store_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_owner_attr_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_reconciliation_attr_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_empty_store_ids_emits_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestMissingOwner::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 2490 warning(s), 219 waived
- error-findings: none (measured, zero errors)
