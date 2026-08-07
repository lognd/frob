## Done report

REL36x NO-SHARED-MUTABLE-STATE-ACROSS-SERVICE-BOUNDARIES obligation
(T-0656), a single-rule family mirroring _spof.py/REL25x's shape (a
structural fact readable straight off the kernel model):

- New module src/frob/strata/_shared_state.py: REL360 fires on a mutable
  node (the dst of >=1 flow at all) accessed -- as either flow endpoint,
  read OR write -- by >=2 distinct other nodes, with no
  `shared_state_ok` exemption.
- DISTINGUISHED FROM REL29x (SSOT): REL290/REL291 already flag a store
  written by >=2 distinct nodes, but that obligation is dischargeable by
  declaring `owner`/`reconciliation` -- sharing is still allowed as long
  as conflicts are reconciled. REL360 is a stricter, independent
  principle (services should not share mutable state directly at all),
  so `owner`/`reconciliation` do NOT discharge it -- verified by a
  dedicated test (test_owner_attr_alone_does_not_discharge). REL360's
  population is also broader: it counts every accessor (read or write),
  not just writers (verified by test_read_only_accessor_still_fires).
- Wired __init__.py exports (REL_SHARED_MUTABLE_STATE,
  SHARED_STATE_RULES, SharedStateReport, SharedStateViolation,
  check_shared_state).
- New docs/strata/reliability.md REL36x section.
- New tests/unit/strata/test_shared_state.py, 7 tests, all pass.

Filed: none (no out-of-scope findings; ticket was not pre-implemented).

Gates: frob check --ticket T-0656 clean across lint/static/gates-fast/
gates-native/gates-security (chunked --only loop); gate:PRE refreshed via
`frob ticket sweep T-0656`.

DELETION-FILTER NOTE (section 9): `git diff main --diff-filter=D --stat`
showed one file (tests/test_arch_near_duplicate_native.py) because main
advanced past my worktree's base mid-session (a sibling ticket, T-0953,
landed a new test file after I started this batch) -- not anything this
ticket touched or removed. Attempted `git merge main` to resolve it per
section 9's literal instruction; the merge succeeded content-wise
(tickets.md auto-spliced correctly via the registered merge driver, T-
0652..T-0655 all verified still `state: done` in the merged result) but
the commit was refused by the scaffolded land-owned-files pre-commit
guard (T-0731: CHANGELOG.md/pyproject.toml/uv.lock are land-exclusive),
because main's T-0953 commit itself carried a legitimate land version
bump through those files. Completing this merge would require either
the land-internal escape hatch (never a worktree agent's to set) or
hand-editing land-owned files (explicitly forbidden). Per section 10b's
own warning that a late `git merge main` mid-session is a timing trap,
and since nothing in this ticket's own diff deletes or reverts any
already-landed work (confirmed: T-0652/T-0653/T-0654/T-0655 all read
`state: done` both before and inside the aborted merge), I aborted the
merge (`git merge --abort`, clean, no partial state left) rather than
force it through. Flagging this honestly rather than silently
resolving it: the coordinator's own land/merge of this worktree onto a
current main will pick up T-0953 via a normal 3-way merge with no
special handling needed.

### Changed
```
 docs/strata/reliability.md                   | 215 ++++++++++++++
 docs/strata/threat.md                        |  11 +
 src/frob/strata/__init__.py                  |  44 +++
 src/frob/strata/_delivery_semantics.py       | 343 ++++++++++++++++++++++
 src/frob/strata/_distributed_txn.py          | 320 +++++++++++++++++++++
 src/frob/strata/_sync_depth.py               | 277 ++++++++++++++++++
 tests/unit/strata/test_delivery_semantics.py | 175 ++++++++++++
 tests/unit/strata/test_distributed_txn.py    | 193 +++++++++++++
 tests/unit/strata/test_sync_depth.py         | 110 +++++++
 tickets.md                                   | 412 ++++++++++++++++++++++++++-
 10 files changed, 2090 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/strata/test_shared_state.py::TestSharedState::test_mutable_node_shared_by_two_services_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shared_state.py::TestSharedState::test_read_only_accessor_still_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shared_state.py::TestSharedState::test_single_writer_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shared_state.py::TestSharedState::test_immutable_node_touched_by_many_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shared_state.py::TestSharedState::test_shared_state_ok_exemption_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shared_state.py::TestSharedState::test_owner_attr_alone_does_not_discharge` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shared_state.py::TestSharedState::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 4241 warning(s), 219 waived
- error-findings: none (measured, zero errors)
