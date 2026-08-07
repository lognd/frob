## Done report

WAVE20-L session. Warm-up: merged main (c7758ff7 ancestor merge), `make
core` clean, repaired a ledger-splice DuplicateId collision (52 active-side
tickets already archived on main -- `frob ticket archive` self-healed 46
done-state duplicates, 6 stale queued-state duplicates removed by hand
since archive's own DONE/DROPPED filter does not touch a queued active
copy). `frob ticket start T-1420`.

Implemented T-1459 design steps 3-6 (typescript/rust/c/kotlin
per-language binding families) plus a follow-up split of the
aggregation/fingerprint/opaque tail, all out of src/frob/vet/_capability.py
(4670 -> 462 lines across five commits, one seam per commit): new
_capability_typescript.py (1275 lines), _capability_rust.py (794 lines),
_capability_c.py (805 lines), _capability_kotlin.py (507 lines),
_capability_scan.py (972 lines). Full details, per-split line counts, and
the two disclosed cross-family dependencies (rust's _record_rust_binding
reused by the not-yet-split-at-the-time C family; the tail's genuine
two-way dependency on _capability.py's language_for/scan_file_capabilities/
_resolved_candidates_for_language, resolved via local function-body
imports mirroring this ticket's _new_renumber.py/_renumber_v2.py
precedent) are in T-1420 delivered portion 7's own ticket body.

Verification: pytest on tests/test_vet.py, tests/test_vet_capability.py,
tests/test_capability_registry.py, tests/test_pii_structural_gate.py,
tests/unit/strata/test_effects.py, tests/unit/strata/test_selfconform.py,
tests/unit/strata/test_mode_conformance.py, tests/unit/strata/
test_conform_eval_needle.py -- all passing, foreground, after every split.
`frob check --only archgate --only wire --only dead_symbols --only
doclink --only docanchor --only fmt` (plus --only opaque --only
pii_structural for the tail split) 0 errors after each commit; a fresh
`frob check --only drift` catches (and this session fixed) 10 DRIFT002
findings the tail split's doc/test-edge repoint initially missed.
`git diff main --diff-filter=D --stat` empty.

Filed T-1420 delivered portion 7 (T-1500, real id assigned at
land) as the leaf carrier for this session's five commits, parent T-1420.

REQUEUE T-1420: still-open T-1459 design residue (further splitting
_capability_scan.py itself, still 972 lines over the 800 threshold) and
the remaining LARGE001 file list are for the next session.

### Changed
```
 docs/modules/vet.md                    |    8 +-
 src/frob/vet/_capability.py            | 4268 +-------------------------------
 src/frob/vet/_capability_c.py          |  805 ++++++
 src/frob/vet/_capability_kotlin.py     |  507 ++++
 src/frob/vet/_capability_rust.py       |  794 ++++++
 src/frob/vet/_capability_scan.py       |  972 ++++++++
 src/frob/vet/_capability_typescript.py | 1275 ++++++++++
 tests/test_capability_registry.py      |   12 +-
 tests/test_vet.py                      |  518 ++--
 tickets.md                             |  127 +
 10 files changed, 4795 insertions(+), 4491 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestIsSelfPatternPath::test_frob_repo_root_with_matching_suffix_returns_true` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 8 error(s), 562 warning(s), 743 waived
- error-findings: DUP001@src/frob/vet/_capability_c.py, DUP001@src/frob/vet/_capability_kotlin.py, DUP001@src/frob/vet/_capability_rust.py, DUP001@src/frob/vet/_capability_typescript.py, INV006@src/frob/vet/_capability.py, INV006@src/frob/vet/_capability_c.py, INV006@src/frob/vet/_capability_scan.py, PERF002@src/frob/vet/_capability_scan.py
