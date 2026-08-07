## Done report

Added frob.process._lock.derived_state_lock, a cross-process shared/
exclusive flock over <root>/.frob/derived.lock, mirroring frob.tickets.
_store.ledger_lock's T-0458 precedent (same fcntl-posix-only primitive,
same documented no-op fallback on a platform without fcntl, same
per-thread re-entrancy bookkeeping, but refuses a same-thread mode
upgrade/downgrade rather than silently allowing one).

Wired the SHARED (reader) form into every frob.check entry point --
run_check, run_check_cpp, run_check_rust, run_check_ts -- so each holds
one shared lock for its entire run, from _derived_state_integrity_
result's precheck through the last stage's read. This closes the
disclosed cross-process TOCTOU window: two frob check runs (or, once a
follow-on wires the exclusive side, a check run and a concurrent
mutate/doctor rebuild) can no longer interleave a precheck-verified
read with a mid-run rewrite of the same .frob derived artifacts,
because both now hold flock-serialized access for their whole run
rather than just at the single precheck instant T-0603 covered.

Cut disclosed honestly: only the reader side is wired in this ticket's
scope (src/frob/check/** + src/frob/process/**). No current writer of
.frob's derived artifacts (frob mutate, frob doctor's rebuild path,
frob.dup/frob.graph's cache rebuilders) takes the exclusive form yet --
they are outside this ticket's scope and still race a genuine writer
the same way T-0603 disclosed, just with the check side's window now
closed instead of open. Filed T-0879 to wire the exclusive
side into those writers.

Docs: docs/modules/process.md gained a "Derived-state lock (T-0859)"
section plus frob:describes entries for _derived_lock_path and
derived_state_lock; check/__init__.py's four run_check* docstrings note
the T-0859 lock coverage inline.

Scope was extended (frob ticket scope --add) to cover docs/modules/
process.md and the new tests/unit/test_process_lock.py, needed for the
new public symbol's frob:doc/frob:tests coverage (COV001/TEST001).

Measured:
- uv run pytest tests/unit/test_process_lock.py tests/unit/test_check.py
  -p no:cacheprovider -q -> 47 passed (5 new + 42 existing, no
  regressions from the lock wiring).
- uv run pytest tests/unit/test_process_lock.py --collect-only -q
  -o addopts="" -> confirmed the 5 node ids bound as evidence actually
  collect.
- FROB_AGENT=1 ... frob check --ticket T-0859 --only lint -> PASS, 0/0.
- FROB_AGENT=1 ... frob check --ticket T-0859 --only static (via --json,
  diagnostics filtered to severity=error) -> 0 errors.
- FROB_AGENT=1 ... frob check --ticket T-0859 --only gates-fast -> 0
  errors, 927 warnings, 162 waived (COV002/INV006/PRE001/SCOPE001 errors
  from an earlier pass were fixed: frob:ticket edges added to every new
  test method, an INV006 waiver added mirroring frob.check's own T-0585
  calibration-batch waiver for the same design-rationale "only"
  vocabulary, ticket scope extended for docs/tests, and the sweep
  refreshed).
- FROB_AGENT=1 ... frob check --ticket T-0859 --only gates-native -> 0
  errors, 932 warnings, 44 waived.
- FROB_AGENT=1 ... frob check --ticket T-0859 --only gates-security -> 0
  errors, 935 warnings, 18 waived.
- git diff main --diff-filter=D --stat -> empty (no out-of-scope
  deletions).

Drafts filed: T-0879 (wire derived_state_lock's EXCLUSIVE side
into .frob writers: mutate/doctor/dup/graph). A second draft was
originally filed for a stale src/frob/exports/__init__.py frob:doc
anchor found while gate-checking on a merged main, but main fixed that
anchor upstream (commit aca32397, unrelated to T-0859's own diff)
before this Done report was finalized, so it is not re-filed -- the
finding is resolved, not dropped.

Ledger note: an earlier round of this ticket's evidence/scope/Done-
report recording was lost when a section-10b `git checkout main --
tickets.md` ledger restore ran against a `main` that had not yet
received this ticket's (refused) land -- that restore correctly kept
T-0859 in its actual queued-then-restarted state, but it also silently
dropped a draft ticket (originally T-draft-e763c4f3) that had only ever
existed in this worktree's own history, never landed. Re-filed as
T-0879 with identical scope/body; no content was lost, only
the id changed.

Land-preflight follow-up (TEST016 EvidenceConfirmatoryOnly): the first
land attempt was refused because the 5 tests bound above killed 0/8
mutants in the WIRING region of run_check/run_check_cpp/run_check_rust/
run_check_ts (the `with derived_state_lock(...)` lines and their
immediately surrounding precheck/dispatch statements) -- the lock
primitive was proven correct in isolation, but nothing proved the check
entry points actually acquire and hold it. Added tests/unit/test_check.
py::TestDerivedStateLockWiring (6 tests, extending scope to tests/unit/
test_check.py, the existing home for run_check*'s own wiring tests):
a `_LockSpy` test double that records every `(root, exclusive)`
acquisition and exposes whether the lock is held at the instant a
planted probe fires, wired into the precheck and stage-dispatch call
sites of all four entry points, plus a short-circuit test (precheck
failure must not let any stage run) and a cpp build-failure test
(covers the skip_tests=True-on-build-failure branch specifically).
Manually verified the new tests catch the flagged mutant class: flipping
run_check_cpp's `exclusive=False` to `exclusive=True` turned 2 of the 6
new tests red (`test_run_check_cpp_holds_shared_lock_across_precheck_
and_stages`, `test_run_check_cpp_build_failure_skips_tests_under_held_
lock`), then reverted cleanly (git checkout) before committing. All 6
new node ids added to the evidence list above (11 total).

### Changed
```
 docs/modules/process.md         |  32 ++++-
 src/frob/check/__init__.py      | 251 +++++++++++++++++++---------------
 src/frob/process/_lock.py       | 182 +++++++++++++++++++++++++
 tests/unit/test_check.py        | 295 ++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_process_lock.py | 105 ++++++++++++++
 tickets.md                      | 187 ++++++++++++++++++++++++-
 6 files changed, 937 insertions(+), 115 deletions(-)
```

### Evidence
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_same_mode_in_same_thread` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_opposite_mode_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_two_threads_serialize_exclusive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_shared_locks_do_not_block_each_other` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_precheck_failure_short_circuits_under_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_build_failure_skips_tests_under_held_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_rust_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_ts_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
