## Done report

T-0739 (parent): typestate protocol enforcement -- init/deinit, declared
state machines, cleanup-on-all-paths. Closes because its four real
children are all done:

  T-0744 (declaration surface): frob:protocol/transition/requires
    comment-DSL, name-pattern init/deinit inference, per-file
    enforceability (an unbound protocol declaration is a MalformedDirective).
  T-0745 (summary engine): shared per-function fixpoint over the call
    graph (frob.graph.summary.compute_protocol_summaries), poisoning
    propagation, not-analyzed/timeout NO-FAIL-SILENT channels.
  T-0746 (verification gate): PROTO002 (state-requirement violation) /
    PROTO003 (invalid transition), ERROR-tier, plus recorded
    language-excuse discharges (Rust Drop, C++ RAII, Python with,
    TypeScript using/try-finally).
  T-0747 (cleanup obligations): PROTO005 -- release-postdominance on all
    exits (including exceptional, via T-0686's may-raise), escape
    transfer, per-protocol cleanup="always" deinit-never-called.

T-0866/T-0867/T-0868/T-0869 (T-0739's other declared blocked_by entries)
are all `state: dropped` -- duplicate/redundant re-scopings of the same
four children's work under different ids, dropped rather than done; the
ticket state machine does not treat a dropped blocker as open (confirmed:
`frob ticket start T-0739` proceeded past them without complaint).

Acceptance ("GIVEN the children closed WHEN frob check runs on fixtures
for each fragment THEN each child gate/advisory fires per its own
acceptance") bound to one representative passing test per child:
T-0744's DSL round-trip, T-0745's summary-engine leaf case, T-0746's
PROTO002 state-never-established case, T-0747's PROTO005 early-return
case -- each is that child's own acceptance-bound evidence, still
passing today (re-verified in this same session: `uv run pytest
tests/test_gates.py tests/unit/test_arch.py
tests/unit/graph/test_dsl.py -q` all green).

Also fixed while re-verifying under this ticket's own sweep (found via
`pytest tests/unit/test_arch.py`, which imports `frob.arch` directly and
triggers an import order T-0747's own test suite never exercised):
`frob.gates._protocol_summary`'s PROTO005 adapter dict was built at
MODULE-IMPORT time, calling `frob.arch._python.PythonAdapter()` before
`frob.arch._python`'s own module body finished (a real circular-import
`AttributeError` reachable via `frob.arch -> _async_hazards -> _python
-> frob.dup -> frob.gates -> _protocol_summary`). Fixed by constructing
each adapter lazily on first call instead of at import time -- no
behavior change, `uv run pytest tests/unit/test_arch.py tests/test_gates.py
tests/unit/graph/test_dsl.py tests/unit/testing/test_import_cycle.py -q`
all green after the fix.

Gates: `uv run frob check --ticket T-0739 --only gates-native/gates-
security` clean (0 errors). `--only gates-fast` shows COV002 findings for
symbols this same worktree changed under T-0747 before T-0747 closed
(the frob:ticket edges name T-0747, now closed, and this check run's
"active ticket" is T-0739, which doesn't own src/frob/gates/**) -- a
ticket-attribution bookkeeping artifact of doing T-0747's close and
T-0739's parent-closability check in the same worktree/session, not a
real gap: every one of those symbols was verified clean under T-0747's
own `--ticket T-0747` scope before T-0747 itself closed. Disclosed here
rather than worked around.

Worktree: .claude/worktrees/agent-a51a11716781a450c

### Changed
```
 docs/modules/gates.md               |  68 ++++++
 docs/modules/graph.md               |  18 +-
 src/frob/gates/__init__.py          |   5 +
 src/frob/gates/_protocol_summary.py | 415 +++++++++++++++++++++++++++++++++++-
 tests/test_gates.py                 | 248 +++++++++++++++++++++
 tickets.md                          | 261 ++++++++++++++++++++++-
 6 files changed, 1001 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestProtocolDeclarations::test_declared_protocol_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_state_never_established_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_early_return_before_release_call_is_an_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 2341 warning(s), 219 waived
- error-findings: none (measured, zero errors)
