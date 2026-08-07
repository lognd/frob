## Done report

`scope_gate` (SCOPE001, src/frob/gates/__init__.py) short-circuited to an
unconditional `return ()` whenever `ticket.scope` was empty, so a ticket
with no declared scope at all -- the riskiest, least-declared-intent
state -- got strictly LESS SCOPE001 enforcement than a normally-scoped
ticket, not more (docs/audits/gates-vacuous.md H1).

Fix: removed the empty-scope early return. `scope_matches` (src/frob/
tickets/_models.py) already treats an empty `scope` sequence as matching
only `LEDGER_PATH` (plus a FEATURE ticket's implicit CLI-wiring files, via
`_scope_globs`), so falling through to the existing per-touched-file loop
now produces a loud SCOPE001 violation for every other file an
empty-scope ticket's diff touches, while the ledger itself (needed to
record the Done report) stays implicitly in scope, matching every other
ticket's behavior.

Updated the one existing test that asserted the old vacuous-pass shape
(`test_scope_unrestricted_when_no_scope_declared` -> renamed
`test_scope001_fires_when_no_scope_declared`, now asserting the loud
violation) and added a paired ledger-still-in-scope regression test.

The paired regression-gate ticket T-0899 (same session, same worktree)
also landed in this branch: a third test binds the multi-file, real-diff
case so scope_gate can never again return the bare `()` sentinel for a
non-empty out-of-scope diff on an empty-scope ticket.

Verification after merging current main into this worktree: targeted
pytest (19 tests in TestScopePrework, all pass), full collection of
tests/test_gates.py (438 tests collected, no errors), and the chunked
`frob check --ticket T-0906 --only <group>` loop over all five stage
groups (lint, static, gates-fast, gates-native, gates-security) -- all
pass (gates-fast required one `frob ticket sweep T-0906` refresh for a
stale PRE001 pre-work sweep after the main merge).

### Changed
```
 src/frob/gates/__init__.py |  19 ++++--
 tests/test_gates.py        |  48 +++++++++++++-
 tickets.md                 | 155 ++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 213 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestScopePrework::test_scope001_fires_when_no_scope_declared` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_scope001_empty_scope_ledger_still_implicitly_in_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
