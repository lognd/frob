## Done report

T-2934: burned the 5 real PLATFORM001 findings from T-2919's first run.

Fixed (genuine msvcrt Windows backend + loud refusal when neither
fcntl nor msvcrt exists, matching T-2918's own precedent):

  src/frob/process/_lock.py::derived_state_lock (line 265) --
    DerivedStateLockUnavailable. Windows backend always takes an
    EXCLUSIVE msvcrt.locking lock regardless of the requested shared/
    exclusive mode (msvcrt has no shared/read-lock primitive at all) --
    a documented, deliberate conservative-concurrency tradeoff: correct,
    just less parallel than POSIX's real reader-writer semantics.

  src/frob/tickets/_land.py::_land_lock (line 649) -- reuses the
    EXISTING LandLockTimeout(root, holder) exception (holder=None for
    the neither-primitive case) rather than inventing a second typed
    error, since land() already catches it and surfaces
    Err(LandError.LandLockTimeout). Windows backend mirrors the
    existing poll-with-timeout retry loop, swapping fcntl.flock for
    msvcrt.locking.

  src/frob/tickets/_store.py::ledger_lock and ::_flock_path (lines 257,
    357) -- new TicketLockUnavailable. Both are simple blocking
    exclusive locks (ledger + fine-grained ticket/allocator locks); the
    msvcrt backend/loud-refusal helper is duplicated locally rather
    than imported from frob.process._lock (deliberate: frob.tickets and
    frob.process already never share a lock FILE by design, per
    ledger_lock/_land_lock's own distinctness precedent, and a ~10-line
    primitive did not seem worth a new cross-component import edge).

NOT fixed, found to be a FALSE POSITIVE instead (per the coordinator's
explicit instruction: narrow the gate, don't waive the first real
finding on a brand-new rule):

  src/frob/tickets/_land_git_ops.py::reclaim_orphaned_squash_residue
    (line 410) -- `if _fcntl is None: _log.warning(...); return
    Ok(False)`. This function's whole job is deciding whether a
    mutation is SAFE; `Ok(False)` here is a genuine, visible, controlled
    abort of the risky operation (typani convention), not "proceeded as
    if the missing primitive did not matter" the way `_baseline_lock`'s
    pre-T-2918 bug did. Narrowed `frob.gates._walk_lint._guard_is_loud`
    to also treat `return Ok(...)`/`return Err(...)` as a loud, typed
    exit -- added `test_typed_result_refusal_is_quiet` /
    `test_typed_err_refusal_is_quiet` (the real false-positive shape)
    plus `test_plain_return_with_no_typed_constructor_still_fires` (a
    negative control proving the narrowing does not weaken the original
    must-fire fixture). Updated docs/modules/gates.md's PLATFORM001
    section to record this as a narrowing, not a disclosed gap anymore.

Every fix + the gate narrowing has its own must-fire/must-stay-quiet
test pair (Windows backend exercised on Linux CI via a fake msvcrt
module backed by real fcntl.flock, same technique T-2918 used).

### Changed
```
 docs/modules/gates.md                |  38 ++++++----
 docs/modules/process.md              |  20 +++--
 docs/modules/tickets-data-storage.md |   8 +-
 docs/modules/tickets.md              |   1 +
 src/frob/gates/_walk_lint.py         |  59 ++++++++++++---
 src/frob/process/_lock.py            | 105 +++++++++++++++++++++-----
 src/frob/tickets/_land.py            |  66 ++++++++++++-----
 src/frob/tickets/_store.py           | 140 +++++++++++++++++++++++++++--------
 tests/test_ticket_land.py            |  71 ++++++++++++++++++
 tests/test_walk_lint_gate.py         |  61 +++++++++++++++
 tests/unit/test_process_lock.py      |  61 +++++++++++++++
 tests/unit/test_ticket_store.py      |  57 ++++++++++++++
 tickets/T-2934/done-report.md        |  67 +++++++++++++++++
 tickets/T-2934/ticket.md             |  88 +++++++++++++++++++++-
 14 files changed, 738 insertions(+), 104 deletions(-)
```

### Evidence
- `tests/unit/test_process_lock.py::TestDerivedStateLockPlatformBackends::test_no_lock_primitive_refuses_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockPlatformBackends::test_no_lock_primitive_raises_land_lock_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLedgerLockPlatformBackends::test_no_lock_primitive_refuses_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLedgerLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001::test_typed_result_refusal_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001::test_typed_err_refusal_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001::test_plain_return_with_no_typed_constructor_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 22 error(s), 1456 warning(s), 853 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
