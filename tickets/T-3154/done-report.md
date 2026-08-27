## Done report

Measured against main directly. SEC110 on
tests/test_worktree_lease_env_ambient.py:70 was GENUINELY LIVE: a fresh
`frob check` run against main reproduced it (error severity, no
existing waiver on this line), unlike the DOC006 identity closed as
stale residue in the sibling T-3158. Confirmed via re-running the full
check and grepping the diagnostic messages directly (not just the
per-diagnostic `path` field, which is `None` for this rule -- the file
is embedded in the message text).

Fix: added a frob:waive SEC110 with a reason on the direct
`os.environ["FROB_WORKTREE"] = ...` write at line 70. This is a
deliberate ambient-env-leak simulation (T-3145's own fixture, whose
already-extensive docstring explains exactly why the write is
necessary and left unrestored on purpose) -- not a secret read/write,
so SEC110's "map it to a declared std.secrets node" framing does not
apply; a waiver with reasoning is the correct disposition, matching the
existing waiver pattern already used elsewhere in this repo for the
same class of deliberate lease-env-var write (e.g.
src/frob/testing/_runners.py's own frob:waive SEC110 lines).

Re-verified: fresh `frob check` after the fix finds zero SEC110
findings on this file; both tests in the module still pass
(2 passed).

Filed: none.

### Changed
```
 tests/test_worktree_lease_env_ambient.py | 1 +
 tickets/T-3154/ticket.md                 | 3 +++
 2 files changed, 4 insertions(+)
```

### Evidence
- `tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_new_ticket_against_unrelated_repo_is_unaffected_by_an_ambient_frob_worktree` (pytest node id, verified passing when recorded)
- `tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_opt_in_worktree_lease_guard_still_fires_when_deliberately_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
