## Done report

Fixed the 3 SELFAUDIT001 findings on the `core` node, left out of T-2871
as a separate root cause (T-2849's forkserver-leak fix):

- `may "ffi"` was a via-less, unjustified grant T-2849 added alongside
  its `_reap.py` prctl(2) work (confirmed by git blame: the exact line
  was introduced in that land's diff, with no `because` comment and no
  via-list). Measured every file under the `core` node's code globs for
  an actual ffi/ctypes call site: `src/frob/process/_reap.py` is the
  ONLY one (`ctypes.CDLL(None)` loading libc to call `prctl(2)` and arm
  PR_SET_PDEATHSIG so a forkserver child dies with its parent). Per the
  ordering the coordinator asked for -- via-scope first, `because`
  second, leave-and-explain third -- the call site is precise and
  nameable, so this is via-scoped to `_reap.py` rather than given a
  `because` justification (which would have been a cop-out restating
  "this node needs ffi" without saying where or why, the exact T-1614
  pattern to avoid).
- `core::env.read` SYS111 ratchet ceiling (3->4): confirmed this is a
  genuinely NEW read, not moved -- `_reap.py` did not appear in this
  via-list before T-2849's land (git show of that commit's diff), and
  the code itself is a real, new `os.environ.get(...)` feature-flag
  check the forkserver-leak fix added. A ceiling bump is correct here
  (unlike T-2871's gates::exec case, where the site had MOVED and the
  right fix was removing the stale via-source instead).
- Added a new `core::ffi` ratchet entry (accepted_count=1): converting
  the via-less grant to a via-list makes it ratchet-eligible for the
  first time; baselined at the one genuine site.

No grant was widened: the ffi grant went from "anywhere in a 126-file
node" to "one named file" (strictly narrower), and both ratchet bumps
cover already-declared, already-real capability uses, not new surface.

### Changed
```
 design/frob.strata                                    | 11 ++++++++++-
 docs/design/registry/capability-via-ratchet.lock.json | 11 ++++++++---
 tickets/T-2877/ticket.md                              | 19 +++++++++++++++++--
 3 files changed, 35 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_deleting_lock_entry_does_not_bypass_the_ratchet` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_unscoped_grant_is_never_ratcheted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 8 error(s), 646 warning(s), 846 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DOC006@tickets/T-2880/ticket.md, OPAQUE001@src/frob/gates/_refs.py, PRE001@tickets/T-2877, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
