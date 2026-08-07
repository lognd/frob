## Done report

_merge_canonical_order used to silently drop a gate's violations whenever
its name was absent from _CANONICAL_GATE_ORDER (T-0788's "compliance" gate
hit this live; main independently added "compliance" to the order tuple
in the interim via T-0788's own land, commit 49e28937 -- merged into this
worktree cleanly, no duplicate entries). This ticket makes that class of
drift structurally loud instead of quiet on both ends:

- _merge_canonical_order now raises GateOrderDriftError, naming every
  unknown gate key found in `raw`, instead of silently skipping it. This
  is an unrecoverable programmer bug (wiring drift between _ALL_GATES/
  _build_jobs and the order tuple), so a plain raised exception is
  correct per the ticket -- not a typani Result, since there is no
  legitimate caller-recoverable path through it.
- A module-level assertion right after _CANONICAL_GATE_ORDER's definition
  (`assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES`, plus a duplicate-
  entry check) fires at import time -- any `frob` invocation that imports
  frob.gates fails immediately on drift, before any gate ever runs, not
  just when frob check happens to be invoked with a stale --only stage
  that never surfaces the merge.
- TestGateOrderSetEquality's single set-equality assertion is split into
  two directional tests (_ALL_GATES subset of the order tuple; the order
  tuple names no nonexistent gate) so a failure names exactly which side
  drifted, plus a new TestMergeCanonicalOrder class exercising
  _merge_canonical_order directly: an unknown-gate-key raise, and a
  clean merge over every current _ALL_GATES member.
- Added a `frob:doc` edge (docs/modules/gates.md#error-types) for the new
  public GateOrderDriftError class to satisfy COV001; extended T-0839's
  scope to include docs/modules/gates.md for that one doc edit (reason
  recorded via `frob ticket scope --reason-file`).

Logging: _merge_canonical_order logs at ERROR (module logger `_log`) with
the missing gate names before raising, per the repo's logging convention
(module logger, no prints) -- the raised exception's message duplicates
that detail for any caller that only sees the traceback.

Deviation from plan: none of substance. The ticket's own text anticipated
"consider deriving the order tuple membership check from _ALL_GATES at
import time" as optional strengthening; this pass takes that up rather
than leaving it as a follow-up, since it was cheap and directly closes
the "impossible to compile" framing requirement #2 in the dispatch.

### Changed
```
 docs/modules/gates.md      | 11 ++++++
 src/frob/gates/__init__.py | 52 +++++++++++++++++++++++++-
 tests/test_gates.py        | 93 ++++++++++++++++++++++++++++++++++++++++++----
 tickets.md                 | 25 +++++++++++--
 4 files changed, 170 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestGateOrderSetEquality::test_canonical_gate_order_matches_all_gates` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestGateOrderSetEquality::test_all_gates_is_subset_of_canonical_order` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestGateOrderSetEquality::test_canonical_order_names_no_nonexistent_gate` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestMergeCanonicalOrder::test_unknown_gate_key_raises_with_name` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestMergeCanonicalOrder::test_all_current_gates_merge_without_raising` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 1202 warning(s), 210 waived
