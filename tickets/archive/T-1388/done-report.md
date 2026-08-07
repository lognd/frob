## Done report

Investigated before implementing anything, per the ticket's own "root
cause not fully isolated" disclosure: the incident this ticket reports
(land's pre-land Tier-A FMT001 pass rewrapping an out-of-scope file's
`frob:waive` comment, then self-refusing on `OutOfScopeWaiveDeletion`
for the very edit it just made) is ALREADY FIXED by prior work, on both
of the ticket's two suggested fix directions:

- (a) "scope the pre-fix pass to the ticket's touched set": T-1404
  (already landed, `src/frob/app/ticket_runner/_land_cmd.py::
  _land_touched_paths`/`_fmt_pre_land_step`/`_tier_a_pre_land_step`, out
  of this ticket's own declared scope `src/frob/tickets/_land*.py`) now
  scopes the pre-land `frob fmt` pass to the landing ticket's own diff
  hunks and excludes FMT001 from the generic Tier-A batch whenever that
  scoped pass ran, so FMT001 specifically can no longer rewrite a file
  outside the landing ticket's own touched set in the normal (touched-
  set-computable) path.

- (b) "exempt its own mechanical reflows from the waive-deletion check":
  T-1468 (already landed, IN this ticket's own scope --
  `src/frob/tickets/_land_git_ops.py::_uncommitted_waive_deletions` and
  its `_waive_deletions_in_diff`/`_scan_diff_for_waive_deletions`/
  `_real_waive_deletions`/`_fold_waive_blocks`/`_normalize_waive_
  fragments` support) makes the deletion-detector itself rewrap-
  insensitive: a `frob:waive` comment block that is REWRAPPED (a
  different number of physical lines, byte-identical normalized content)
  on both sides of a hunk is silently NOT counted as a deletion at all,
  regardless of which file it lives in or which ticket's scope covers
  it. `TestWaiveRewrapNotDeletion` (tests/test_ticket_land.py) already
  covers this directly against a hand-written rewrap.

Both mechanisms independently close the exact symptom described (a
`frob:waive` reason= comment rewrap in an out-of-scope file self-
blocking land) -- (b) alone is sufficient even if (a)'s touched-set
computation somehow fails and the whole-tree FMT001 fallback runs, since
the deletion-detector T-1468 fixed sits downstream of EITHER path.

Verified this is not merely catalogued-but-unenforced (this repo's own
"catalogued is not enforced" lesson): reproduced the original incident
shape as closely as this ticket's own scope allows -- ran the REAL
`frob.gates._fmt_directives.format_paths` fixer (not a hand-written
rewrap) against an out-of-scope file with an over-long single-line
`frob:waive` comment, confirmed it rewrapped the line (the same
mechanical reflow the incident describes), then ran a real `land(...,
dry_run=True)` against that dirty worktree and confirmed it does NOT
refuse.

Changed: none (no code change -- see above; only a new regression test)

Added:
  tests/test_ticket_land.py::TestWaiveRewrapNotDeletion.test_real_fmt001_fixer_rewrap_does_not_trip_the_guard

Evidence: 1 new test exercising the real FMT001 fixer's own output
through the real `land()` dry-run path (not a synthetic rewrap) -- see
evidence list below. Full class: 3 passed
(`tests/test_ticket_land.py::TestWaiveRewrapNotDeletion`).

Gates: `frob check --only test --ticket T-1388` 0 errors. `frob check
--only coverage --only scope --only prework --only fmt --only archgate
--ticket T-1388`: gate:ARCH/gate:LARGE/gate:TODO/gate:PRE/gate:FMT 0
errors. gate:COV shows 1 error (`_land_cmd.py::_apply_release_bump_for_
land`, T-1368's own symbol) and gate:SCOPE shows 6 errors (T-1359's six
files) -- both are the SAME pre-land, same-worktree artifact already
disclosed in T-1368's Done report: T-1368/T-1359 are closed tickets
whose own commits are still unlanded in this shared worktree, and their
symbol/scope coverage now ties against OTHER, unrelated, currently open
tickets (T-1523's scope also claims `_land_cmd.py`; T-1264's scope also
claims `_staleness.py`) once THIS ticket's own `--ticket` selection no
longer prefers them. None of these 7 findings are against any file
T-1388 itself touched (`tests/test_ticket_land.py` reports 0 SCOPE001/
COV002); this self-resolves once T-1368/T-1359 land as their own
commits (a coordinator step), same disclosure as T-1368's report.

Filed: none -- this ticket's own suggested acceptance is already met by
existing code; nothing new to track. The commit-subject-omission
observation from T-1368's Done report (T-1359's crash-safety commit
lacking a literal T-1359 in its subject) is a one-off historical fact
about a specific already-closed commit, not a recurring gap.

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
 tests/test_ticket_land.py                     | 222 +++++++++++
 tests/unit/test_ticket_runner_land_release.py |  46 ++-
 tickets.md                                    | 506 +++++++++++++++++++++++++-
 13 files changed, 1121 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_real_fmt001_fixer_rewrap_does_not_trip_the_guard` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
