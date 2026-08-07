## Done report

WIRE001 and SCOPE001 enrolled in `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES`
(`src/frob/gates/_waive.py`), each with a justification comment citing the
gate's own diff-scoping (verified directly, not assumed from the ticket
text):

- WIRE001 (`frob.gates._wire`): every finding is constructed from `diff.
  hunks`' added lines -- "a newly-added symbol nothing outside its own
  tests can reach" is structurally diff-relative, so a full unscoped run's
  diff essentially never matches the diff that introduced the waived
  symbol.
- SCOPE001: already documented in this same module (T-0753 comment,
  "a diff-scoped rule like SCOPE001") and already carries the mirror
  exemption for WAIVE004's own scoped-run flakiness via
  `SCOPED_RUN_FLAKY_RULE_IDS` (`_waive.py`). Enrolling it here closes the
  matching full-run-side gap.

Audited DEPR005, DEAD001, REF002 for the same shape per the ticket's
instruction -- none qualify, and none were enrolled:

- DEPR005 (`_depr005_edge_violations`) compares the FULL current
  reference-count index against a committed baseline every run -- no diff
  input.
- DEAD001 (`frob.gates._dead_symbols`) walks the full repo-wide call graph
  for reachability -- no diff input.
- REF002 (`frob.gates._refs`) counts inbound references over every
  git-tracked file -- no diff input.

A "0 findings" read from any of these three is a genuine, trustworthy
signal on a full run; exempting them would hide real staleness rather
than diff-scoping noise.

`docs/modules/gates.md`'s "Structurally-unverifiable rules (T-1064)"
section gained a matching bullet for WIRE001/SCOPE001 plus the negative
DEPR005/DEAD001/REF002 audit result, so the doc and the code enumerate
the same set.

Residual, disclosed rather than forced: this worktree also holds T-1581's
already-committed work (same worktree, series dispatch). A `--ticket
T-1577`-scoped `frob check` sees SCOPE001/SCOPE002 noise against files
T-1581 touched (`src/frob/gates/_fix_engine.py`,
`src/frob/gates/_fmt_directives.py`, `tests/test_gates_fix_engine.py`,
<!-- frob:waive DOC006 reason="historical Done report: docs/modules/gates_e501_autofix.md was real when this landed; T-1580's own follow-up (also in this ledger) later folded it into gates.md and deleted it" -->
`docs/modules/gates_e501_autofix.md`) because T-1581's landing commit
subject did not literally include "T-1581" (T-0108's cross-ticket SCOPE001
exemption keys off a `T-\d{4}` reference in the attributing commit's own
subject line) -- a pre-existing gap in this worktree's own commit history,
not something narrowing T-1577's scope further can fix, and not something
this ticket's own scope should absorb (removed `src/frob/gates/_fix_engine.
py` from T-1577's scope instead, since this ticket never touches it).
`frob check --land-parity` -- the actual land-sweep-equivalent check --
reports CLEAN (0 unscoped errors) against the current combined worktree
tree, confirming this is per-ticket-scoped-check noise from the
multi-ticket-worktree sequencing, not a real land blocker.

### Changed
```
 docs/modules/gates.md              |  17 ++++++
 docs/modules/gates_e501_autofix.md |  31 ++++++++---
 src/frob/gates/_fix_engine.py      |  56 ++++++++++++-------
 src/frob/gates/_fmt_directives.py  |  10 +++-
 src/frob/gates/_waive.py           |  36 ++++++++++++-
 tests/test_gates.py                |  44 +++++++++++++++
 tests/test_gates_fix_engine.py     |  78 +++++++++++++++++++++++++++
 tickets.md                         | 108 +++++++++++++++++++++++++++++++++++--
 8 files changed, 350 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_waive004_exempts_wire001_as_diff_scoped` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_exempts_scope001_as_diff_scoped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1116 warning(s), 784 waived
- error-findings: none (measured, zero errors)
