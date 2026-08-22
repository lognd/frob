## Done report

Changed:
- src/frob/tickets/_land.py::_effective_leakage_scope

Root cause: `_effective_leakage_scope` trusted a live cross-worktree
lease unconditionally whenever one was recorded for a sibling ticket,
even when that sibling's DECLARED scope had since been narrowed to
empty by some means other than a fully lease-syncing `mutate_scope`
call. Confirmed live on this repo's own main: T-2374 was `state:
in-progress` with `scope=[]` on its ticket record, but its lease file
(`.git/frob-leases/T-2374.json`) still listed ~27 stale paths from
earlier in its history, including an unrelated sibling's own ledger
shard (`tickets/T-2524/ticket.md`) -- exactly the misattribution
T-2524's land hit and worked around with `--allow-cross-ticket`.

Fix: `_effective_leakage_scope` now checks the ticket's DECLARED scope
first and short-circuits to `()` when it is empty, before ever
consulting a live lease -- an empty declared scope means "claims
nothing" unconditionally, regardless of what a stale lease still lists.
A ticket with a genuine non-empty declared scope and a live matching
lease is unaffected; the guard only narrows the empty-scope case.

On the second question this ticket's body raised (whether an
in-progress ticket with an empty declared scope holding an unused/stale
lease deserves its own detector): yes, this is a real, currently
undetected gap, distinct from the CrossTicketLeakage misattribution
fixed here (fixing the READ side does not fix the WRITE-time drift that
produced it, and other lease consumers do not share this fix's
empty-scope carve-out). Filed as T-2561 (renumbers on land)
rather than fixed inline -- out of this ticket's declared scope
(src/frob/tickets, this file only) and a distinct design question (what
gate/verb should own detecting lease-vs-declared-scope drift).

Evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_empty_declared_scope_never_attributes_an_unclaimed_file_even_with_a_stale_broad_lease
  (accepts 0) -- FAILED_AT_PARENT confirmed at 48e4b0079 (the repro-test-only
  commit, fix not yet applied) via `frob ticket evidence --designate-repro`.
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_genuine_leak_via_live_lease_still_refused_with_nonempty_declared_scope
  (accepts 1) -- positive control: a genuine leak (non-empty declared
  scope, live lease, real committed work on this branch) is still
  refused with CrossTicketLeakage; the fix does not widen the escape.

Both also verified manually against the pre-fix code (guard temporarily
removed, restored after) to confirm the FIRST test fails without the fix
and the SECOND still refuses either way -- see commit history
(48e4b0079 test-only, 6dfa5d2d0 fix).

Full local suite run: `tests/unit/test_land_cross_ticket_leakage.py`,
`tests/unit/test_land_machinery_owned_leakage.py`,
`tests/unit/test_land_step_ordering.py` -- 27 passed, 0 failed.

Filed: T-2561 (renumbers at land) -- "Stale live lease scope
drifts from an in-progress ticket's declared scope, undetected" -- the
write-time gap noted above.

Gates: `frob check --land-parity` after merging current main shows only
pre-existing, unrelated repo-wide debt (COV003/DOC00x/PERF00x/SEC110/
etc. across files this ticket never touched); profile=rapid on this
land skips the pre-commit sweep and defers to the detached post-land
sweep's own rolling baseline per T-1684 -- consistent with dry-run
reaching the Done-report gate cleanly with no scope/leakage refusal.

### Changed
```
 src/frob/tickets/_land.py                    |  27 +++++-
 tests/unit/test_land_cross_ticket_leakage.py | 123 +++++++++++++++++++++++++++
 tickets/T-2547/ticket.md                     |  20 ++++-
 tickets/T-2561/ticket.md           |  60 +++++++++++++
 4 files changed, 227 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_empty_declared_scope_never_attributes_an_unclaimed_file_even_with_a_stale_broad_lease` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_genuine_leak_via_live_lease_still_refused_with_nonempty_declared_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2547/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2547, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
