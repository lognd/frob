## Done report

Added the paired regression-gate test for T-0906/H1 (docs/audits/gates-vacuous.md):
`test_scope001_empty_scope_never_returns_bare_empty_tuple_for_a_real_diff` binds
that an in-progress ticket carrying scope=() must never again let scope_gate
silently return the bare `()` no-violation sentinel for a non-empty,
multi-file, out-of-scope diff -- each touched file must produce its own
SCOPE001 violation, not a single silently-cleared pass.

T-0906 itself (the fix direction: removing scope_gate's empty-scope early
return) landed on main separately (fa2d2ea6); this ticket is the standalone
regression-test binding called for in its own body, tagged
`frob:ticket T-0899` in tests/test_gates.py.

Verification: merged current main (T-0906's land, fa2d2ea6) into this
worktree; ledger conflict auto-spliced via the registered frob-ledger merge
driver, `git diff main --diff-filter=D --stat` empty (no reverted work).
Targeted pytest (tests/test_gates.py -k TestScopePrework, 19 tests) all
pass in the foreground post-merge. Chunked `frob check --ticket T-0899
--only <group>` loop over all five stage groups (lint, static, gates-fast,
gates-native, gates-security) all pass clean; no PRE001 (pre-work sweep
was already fresh, no re-sweep needed).

Note: the tickets.md merge driver spliced this ticket's `state` field back
to `queued` (main's pre-work-session snapshot) despite the on-disk lease
still showing in-progress@this worktree -- a real instance of the ledger-
splice hazard (docs/guides/agent-playbook.md section 10: "a naive
resolution can silently drop a state transition"). Caught it via
`frob ticket show T-0899` (lease-derived, correctly showed in-progress)
disagreeing with the raw YAML `state:` line; fixed with
`frob ticket start T-0899 --foreground`, which restored state=in-progress
and refreshed the pre-work sweep, before writing this Done report.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestScopePrework::test_scope001_empty_scope_never_returns_bare_empty_tuple_for_a_real_diff` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
