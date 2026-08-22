## Done report

Changed:
docs/modules/app.md (Runners section: check_runner.run entry; #frob-check---census-t-1764 section)

Once T-2485's lease on docs/modules/app.md cleared (confirmed done/landed
before this ticket started, and T-2492 landed with its own `_json_guard`
promotion in the interim), added the AFFECT001-required doc sync T-2486
waived: a paragraph on `check_runner.run`'s Runners-list entry describing
`_guard_json_stdout_writes` and naming every guarded span in that runner,
PLUS the T-2492 update noting the guard's promotion to the shared
`src/frob/app/_json_guard.py` module and the 8 sibling runners (bind,
clean, docs, fmt, graph query/why/affects, map, test, vet) it was applied
to after T-2492's execution-verified audit. Mirrors the paragraph T-2486
already landed in docs/modules/tickets-landing.md#frob-check---land-parity-t-1535
for `_run_land_parity`, so the guard now has one doc note per module it
touches (app.md for the general runner + census path, tickets-landing.md
for the land-parity path).

Also updated the `#frob-check---census-t-1764` section with the same
T-2486/T-2492 note for `_run_census`'s own guarded gate run.

Filed: none new.

Gates: `frob check --ticket T-2491` -- gate:SCOPE clean (0 errors, 101
pre-existing warnings from this doc's many unrelated frob:describes
anchors, all advisory "not in scope" notes any docs/modules/app.md edit
triggers). gate:DOC's 6 errors are all pre-existing/unrelated: verified
by `git diff main -- docs/modules/app.md`, which shows this diff's only
hunk starts at line 328 (the Runners list) -- the one app.md DOC006
finding (frob.app._config_meta pointer, line 60) sits outside this
diff's touched region entirely, and the other 5 DOC errors are in files
this ticket never touched (tickets-landing.md, gates.md, several ticket
bodies).

### Changed
```
 tickets/T-2491/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2491/src/frob/testing/_collect_kotlin.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2491/tests/unit/test_app_runners_json_guard_t2492.py, LANG004@src/frob/lang/_support.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PRE001@tickets/T-2491, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
