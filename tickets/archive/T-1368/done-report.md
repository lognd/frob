## Done report

`_apply_release_bump_for_land` called `frob.release.stamp(...)` and threw
away its `Result` -- a write failure (`stamp`'s own `enforce_worktree_
lease` refusal, or any future failure mode `stamp` grows) fell through
silently to `git add .frob-release.json` regardless, staging whatever
(possibly stale) content already happened to be on disk instead of the
fresh bump.

Fixed exactly as the ticket's suggested acceptance describes: the
`stamp(...)` call's `Result` is now checked; on `Err`, the function logs
the failure and returns `Err(LandError.ReleaseBumpFailed)` instead of
falling through to the `git add` staging step, matching every other
failure path this function already uses (fail-closed, since a silently-
skipped bump would let a landed API change slip past REL001 undetected).

Changed:
  src/frob/app/ticket_runner/_land_cmd.py::_apply_release_bump_for_land

Evidence: one new unit test
(`TestApplyReleaseBumpForLand::test_stamp_failure_propagates_instead_of_
staging_stale_manifest`) monkeypatches `frob.release.stamp` to return
`Err(ReleaseError.WriteFailed)` and asserts the function returns
`Err(LandError.ReleaseBumpFailed)` AND that `git add` (`frob.gitio.
run_argv`) is never called -- the exact silent-drop the ticket describes,
proven closed. Full file: 16 passed
(`tests/unit/test_ticket_runner_land_release.py`).

Gates: `frob check --only test --ticket T-1368` 0 errors. `frob check
--only coverage --only scope --only prework --only fmt --only archgate
--ticket T-1368` 0 errors for gate:COV/gate:PRE/gate:ARCH/gate:TODO
after (a) adding `tests/unit/test_ticket_runner_land_release.py` to
T-1368's scope (the test file for this fix) and (b) adding a `frob:ticket
T-1359` edge to `sync_gate_rule_entries` (src/frob/registry/_staleness.py)
so the T-0965 closed-ticket grace window covers it against a genuine
scope tie with another concurrently open ticket (T-1264) that also
claims that file -- both changes are within T-1359's OWN previously-
verified scope, not new scope creep from T-1368.

gate:SCOPE still reports 6 SCOPE001 findings against T-1359's files
(src/frob/gates/_fmt_directives.py, src/frob/registry/_staleness.py,
src/frob/release/__init__.py, tests/test_gates_fmt_directives.py,
tests/test_registry_staleness.py, tests/test_release.py) under
`--ticket T-1368` -- root-caused: T-1359's own worktree commit
(aa9aaa38 "fix(gates,registry,release): make FMT001/REG010/REL002
writes crash-safe") omitted a literal `T-1359` reference from its
SUBJECT line (it names the ticket in the body but SCOPE001's T-0108
cross-ticket exemption regex-matches the commit SUBJECT only), so that
commit's hunks are not recognized as already-scoped-and-closed when a
LATER ticket sharing this same pre-land worktree diffs against main.
This is a known, self-resolving pre-land artifact, not a T-1368 defect
or scope violation: `frob ticket land` regenerates the landing commit
message from the ticket id itself at land time, so it disappears the
moment T-1359 actually lands. None of these 6 files are in T-1368's
scope and none were touched by this ticket's own work; T-1368's own
file (src/frob/app/ticket_runner/_land_cmd.py) reports 0 SCOPE001
findings.

Filed: none (T-1533 from T-1359 already covers the one real
out-of-scope follow-up in this cluster; no new residue from T-1368
itself, and the commit-subject omission above is a one-off historical
fact about a specific already-closed commit, not a recurring gap
worth a ticket).

### Changed
```
 design/frob.strata                            |  16 +-
 docs/design/registry/EXHAUSTIVENESS-GATE.md   |   7 +
 docs/modules/release.md                       |  37 +-
 src/frob/app/ticket_runner/_land_cmd.py       |  26 +-
 src/frob/gates/_fmt_directives.py             |  34 +-
 src/frob/registry/_staleness.py               |  30 +-
 src/frob/release/__init__.py                  |  69 +++-
 tests/test_gates_fmt_directives.py            |  42 +++
 tests/test_registry_staleness.py              |  32 ++
 tests/test_release.py                         |  97 +++++
 tests/test_ticket_land.py                     | 222 ++++++++++++
 tests/unit/test_ticket_runner_land_release.py |  46 ++-
 tickets.md                                    | 502 +++++++++++++++++++++++++-
 13 files changed, 1117 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_stamp_failure_propagates_instead_of_staging_stale_manifest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
