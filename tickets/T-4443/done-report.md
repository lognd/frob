## Done report

Extracted seed_worktree_native_source_mtimes's digest/backdating internals (_tracked_source_digest, _seed_one_native_source_mtime) from _native_staleness.py into a new sibling module _native_staleness_digest.py, keeping every public name importable from _native_staleness unchanged (thin wrapper). File is now 696 lines (was 805, threshold 800, target <=720). Updated docs/modules/testing.md#public-api (AFFECT001/DOC006), design/frob.strata's stratamod fs.read via-list and docs/design/registry/capability-via-ratchet.lock.json's ceiling 10->11 (SELFAUDIT SYS100/SYS111, the moved fs.read call site), waived ARCH102 on the now-thinner _native_staleness.py (edges severed by extraction, not new fragmentation), extended ticket scope to docs/modules/testing.md, design/frob.strata, docs/design/registry/capability-via-ratchet.lock.json (scope closure required by the doc/capability edges the split touches), and recorded frob:no-behavior-change on the ticket body (this is a pure structural move -- every bound test genuinely PASSES at the parent commit, so BUG002's confirmatory-only refusal on --check-repro is expected and the no-behavior-change escape hatch documented in docs/modules/gates.md applies; frob check --ticket T-4443 shows no BUG002 finding). All 26 tests in tests/unit/strata/test_native_staleness.py pass unchanged. frob check --ticket T-4443 is clean of every in-scope finding; remaining FAILs (ruff-format on tests/test_tickets_triage_dates.py, gate:TICK006/TICK010) are pre-existing and out of scope, confirmed by inspection.

### Changed
```
 tickets/T-4443/ticket.md | 43 ++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 42 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes::test_identical_source_is_backdated_and_reads_fresh` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes::test_diverged_source_is_left_untouched_and_still_stale` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes::test_repo_side_untracked_file_does_not_block_seeding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 4828 warning(s), 963 waived
- error-findings: TICK006@tickets.md, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4412.json
