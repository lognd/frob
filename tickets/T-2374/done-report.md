## Done report

Two-part closure per T-0969, both parts now met and measured together.

Part 1 -- burn to zero. Roughly 36 content fixes across docs/commands,
docs/guides, docs/modules and eight ticket bodies: stale symbol/anchor/config-ref
pointers corrected where the target had moved, two unbound skip-flag/fix-ruff
code blocks anchored (DOC004), and honest per-finding `frob:waive DOC006` entries
where the pointer is deliberately illustrative, historical, or self-referential
prose rather than a live reference.

Part 2 -- promote. `_docptr._doc006_violation` and
`_docblocks_shared._doc004_violation`'s unbound tier both move WARNING -> ERROR
for the v1.0.0 severity freeze, with the gate modules' own docstrings and the two
gate test files updated to match.

The promotion was split out of an earlier attempt because three load-bearing
gates.md fixes sat under T-2523's live lease; T-2523 landed at c44342c5, the lease
released, and both halves are reunited here.

Re-measured AFTER merging current main (T-2523's own gates.md edits landed under
this branch): `frob check --only doclink --only docanchor --only docblocks --json`
reports DOC004 = 0 and DOC006 = 0 with both codes now at ERROR severity. The merge
surfaced one genuinely new DOC006 that main had accrued in the meantime --
T-2524's body cited a `done-report` file-input flag that does not exist -- fixed
here, since promoting DOC006 to ERROR is what turns that pre-existing WARN into a
land blocker.

The five errors that remain in the DOC family (DOC001 on docs/commands/release.md,
DOC008/DOC002 on a gates.md anchor naming an unpromoted draft id, DOC005 on
cli.md's stale generated command table) are pre-existing on main, belong to other
codes, and are outside this ticket's scope -- verified by confirming none of them
fall in this branch's diff.

Residue: two follow-ups AZ filed as drafts are promoted to real ids so they
survive independently of this branch. T-2533 -- DOC006's CLI-invocation walker
resolves verbs only from `_build_parser()`'s registration and misses verbs reached
through `_dispatch_*` bypasses, so it reports nonexistent-subcommand findings for
commands that genuinely exist; release-relevant now that DOC006 is ERROR, because
it is a known false-positive class in a newly-blocking gate. T-2534 -- T-2505's
historical-record exemption does not reach ticket evidence/attachment
subdirectories.

### Changed
```
 docs/commands/check.md                             |   2 +
 docs/commands/deploy.md                            |   2 +-
 docs/guides/coordinator-scripts.md                 |   4 +-
 docs/modules/app.md                                |   2 +-
 docs/modules/cli.md                                |   2 +-
 docs/modules/gates.md                              |   6 +-
 docs/modules/process.md                            |   3 +-
 docs/modules/tickets-data-storage.md               |   4 +-
 docs/modules/tickets-landing.md                    |  15 +-
 docs/modules/tickets-lifecycle.md                  |   8 +-
 docs/modules/tickets-verify-sweep.md               |   8 +-
 src/frob/gates/_docblocks.py                       |   3 +-
 src/frob/gates/_docblocks_shared.py                |  11 +-
 src/frob/gates/_docptr.py                          |  45 ++--
 tests/test_docblocks_gate.py                       |   6 +-
 tests/test_docptr_gate.py                          |   2 +-
 tickets/T-1656/ticket.md                           |   6 +-
 tickets/T-1661/ticket.md                           |  19 +-
 tickets/T-1881/evidence/fix-measurement.md         |   2 +-
 tickets/T-2080/ticket.md                           |   4 +-
 ...and-fix-guidance-no-src-lexical-special-case.md |   2 +-
 tickets/T-2251/ticket.md                           |   8 +-
 ...ction-t-2329-s-own-land-root-cause-narrowing.md |   2 +-
 tickets/T-2374/done-report.md                      | 107 ++++++++++
 tickets/T-2374/ticket.md                           | 234 ++++++++++++++++++++-
 tickets/T-2384/ticket.md                           |   4 +-
 tickets/T-2524/ticket.md                           |   2 +-
 tickets/T-2533/ticket.md                           |  62 ++++++
 tickets/T-2534/ticket.md                           |  46 ++++
 29 files changed, 541 insertions(+), 80 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCCppNamespace::test_include_of_tracked_header_unanchored_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2374/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2374/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2374/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2374/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2374/tests/unit/test_ticket_runner_repro_merge_base.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2374, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
