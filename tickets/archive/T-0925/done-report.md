## Done report

Added the "Lock-ordering hazards" section to docs/modules/arch.md (matching
the Fork/pool hazards and Async event-loop hazards sections' structure and
detail level), documenting lock-order-cycle and lock-identity-unresolved
(frob.arch._lock_ordering, T-0694, child 2 of the T-0693 umbrella): the
5-step model, both finding categories, the model-limit disclosure, and
that this channel is unwaivable by design (no frob:waive escape hatch) --
resolution is structural (consistent global lock-acquisition order, or
declaring the lock via a curated ctor). Added a frob:doc directive on
_check_lock_ordering_hazards pointing at the new anchor, and scope-added
tests/unit/test_arch.py (docs-only ticket, existing test file is the
evidence surface) per the playbook's recurring gotcha.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4676 warning(s), 333 waived
- error-findings: none (measured, zero errors)
