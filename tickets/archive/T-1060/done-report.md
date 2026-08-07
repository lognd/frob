## Done report

SYS205 v0 (T-0701) disclosed three cuts; T-1060 closes all three, each
as a narrow TEXTUAL approximation in the module's own established idiom
(cheap indentation/string-based scanning -- deliberately NOT tree-sitter
based like frob.arch._lock_ordering's own T-0694 lock-identity mechanism,
a heavier tool this ticket does not adopt):

1. ALPHA/EXCLUSIVE upgrade-deadlock anti-pattern: a write-capable op
   nested inside TWO `with <lock>:` blocks naming the SAME lock now
   fires a NEW `alpha_reacquire_deadlock` category, alongside (not
   instead of) the existing unguarded-write check. Telling two DIFFERENT
   lock objects with the same name apart (T-0694's harder problem) is
   still out of scope -- this only catches literal name reuse.
2. `arbitrated_by NODE` code-checkable identity: `_arbiter_identity_for`
   now resolves both `lock` (unchanged) and `arbitrated_by` (new) -- for
   a NODE arbiter, a write-capable line textually calling through the
   arbiter node's id (`"{node_id}."` dotted-call prefix) discharges. Not
   real cross-node call-graph resolution (still disclosed out of scope)
   -- an indirection (alias, returned callable, injected dependency) is
   invisible to this join and fails closed as unguarded, same as
   before. A resource declaring neither `lock` nor `arbitrated_by` still
   fails closed exactly as before.
3. WRITE mode path-scoping: `_declared_write_paths` reads a node's own
   `owns`/`acl` claims off `_host.py::host_manifest_for` -- the SAME
   "declared path" fact SYS201 (`_contention.py`) already uses. A node
   declaring NO `owns`/`acl` at all now fails closed
   (`no_declared_path`) -- WRITE is no longer silently unrestricted just
   because nothing was declared to scope it. When paths ARE declared, a
   write-capable line whose call shape carries a literal string path
   argument is checked for directory-segment-prefix overlap against the
   declared paths (`_path_within_declared`, a small local port of
   `_contention.py::_paths_overlap`'s identical logic -- that module is
   out of scope, and the join is small enough that duplicating it here
   is more honest than reaching across a module boundary for a private
   helper); no overlap fires `write_outside_declared_path`. A write with
   no extractable literal path stays silent -- disclosed, not a false
   pass (real path-literal resolution needs real static analysis).

`check_mode_conformance` was refactored into three per-mode helpers
(`_read_append_violations`/`_alpha_exclusive_violations`/
`_write_violations`) to stay under ARCH001's 60-line threshold after the
new logic landed.

Test changes (tests/unit/strata/test_mode_conformance.py, 17 total -- 9
pre-existing + 8 new):
- `test_write_mode_is_unrestricted_in_v0` KEPT its original name
  (T-0701's archived Done report cites this exact node id as evidence)
  but the assertion now reflects v1: a node with no owns/acl fails
  closed instead of staying silent.
- New: test_write_mode_discharges_inside_a_declared_path,
  test_write_mode_fails_outside_the_declared_path,
  test_write_mode_with_no_extractable_literal_stays_silent,
  test_exclusive_mode_discharges_through_an_arbitrated_by_node,
  test_exclusive_mode_fails_when_arbitrated_by_node_never_called,
  test_alpha_mode_fires_reacquire_deadlock_alongside_the_guarded_pass,
  test_alpha_mode_single_lock_context_does_not_fire_reacquire_deadlock.

docs/strata/host.md: new "SYS205 mode conformance (T-0701, v1 T-1060)"
subsection under "Resource access modes (T-0700)" documents all three
v1 closures and their residual disclosed limits (scope widened via
`frob ticket scope --add docs/strata/host.md`, AFFECT001 precedent).

Gate verification (all foreground, chunked):
- uv run pytest tests/unit/strata/test_mode_conformance.py -q: 17
  passed.
- uv run frob check --ticket T-1060 --only gates-native: 0 errors
  (initially caught a real ARCH001 -- check_mode_conformance grew past
  the 60-line threshold -- fixed via the three-helper split above; also
  a real DRIFT002 from renaming a test the old archived T-0701 Done
  report cited as evidence -- fixed by reverting to the original name).
- uv run frob check --ticket T-1060 --only static: 0 errors.
- uv run frob check --ticket T-1060 --only lint: 0 errors in this
  ticket's own files (ruff-format applied to _mode_conformance.py); the
  6 remaining ruff-check errors are pre-existing in
  src/frob/vet/_capability.py and src/frob/vet/_supplychain.py.
- uv run frob check --ticket T-1060 --only gates-security: 2
  SELFAUDIT001 (SYS104) errors, CONFIRMED pre-existing/unrelated --
  TestCheckRegistryExclusion (tests/unit/test_arch.py) and
  TestRenumberRewritesLedgerProse (tests/test_tickets_collision.py) are
  new public test classes added by unrelated, already-landed tickets
  (T-1125 and a sibling) after T-1113's SYS104-mandatory flip;
  design/frob.strata is out of T-1060's declared scope, so the
  interface= sync for these two symbols was generated, verified, then
  DELIBERATELY REVERTED (git checkout -- design/frob.strata) rather than
  committed here -- this is a recurring maintenance task any agent
  touching design/frob.strata should pick up, not this ticket's own
  regression.
- uv run frob check --ticket T-1060 --only gates-fast: 26 remaining
  errors, all pre-existing (confirmed via diff against T-1025's and
  T-1091's identical baseline set: 24 stale strata-core/src/parse.rs
  COV003 citations from the unrelated T-1099 rust split, 1 COV001 on
  src/frob/gates/_tracked_files.py, 1 TICK006 on T-1114's own phantom
  draft citation).
- git diff main --diff-filter=D --stat: empty (AFTER a required second
  `git merge main` -- main had advanced with T-1031's estate-natives-
  build-rollout doc cleanup mid-ticket; merged and rebuilt natives
  before this check).

Filed: none new by this ticket.

### Changed
```
 docs/strata/host.md                        |  56 ++++
 src/frob/strata/_mode_conformance.py       | 478 +++++++++++++++++++++++++----
 tests/unit/strata/test_mode_conformance.py | 209 ++++++++++++-
 tickets.md                                 |  11 +-
 4 files changed, 684 insertions(+), 70 deletions(-)
```

### Evidence
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_alpha_mode_fires_reacquire_deadlock_alongside_the_guarded_pass` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_alpha_mode_single_lock_context_does_not_fire_reacquire_deadlock` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_discharges_through_an_arbitrated_by_node` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_fails_when_arbitrated_by_node_never_called` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_discharges_inside_a_declared_path` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_is_unrestricted_in_v0` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_fails_outside_the_declared_path` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_with_no_extractable_literal_stays_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
