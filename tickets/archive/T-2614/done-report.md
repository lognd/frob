## Done report

T-2450's declared scope contained a single ticket-frontmatter entry --
`'src/frob/verify/**;src/frob/app/ticket_runner/**'` -- a semicolon
joining two globs into one malformed pattern instead of two separate
scope entries. `PurePath.match` raises `ValueError` on `'**' can only be
an entire path component'` for the joined string, so it was not
evaluable as "either glob" and matched nothing, voiding T-2450's
declared write lease and evidence coverage.

Fixed via `frob ticket scope T-2450 --remove '<joined-string>' --add
'src/frob/verify/**' --add 'src/frob/app/ticket_runner/**'` -- the
single-writer CLI, not a hand-edit.

Also checked whether anything validates scope entries at write time, per
the ticket's own second question. Answer: partially. `_split_scope_
entries` (T-0241) already splits on COMMAS, but nothing splits or
rejects a SEMICOLON-joined (or any other malformed) entry -- confirmed
by reading `_validate_scope_request`/`_validate_scope_mutation` in
`src/frob/tickets/_scope.py`, neither of which runs any glob-syntax
check. Filed as a follow-up draft (renumbers at land) rather than
bulk-fixing from outside T-2450's own scope, per the ticket's own
explicit instruction not to.

## Done report

Changed:
- tickets/T-2450/ticket.md (scope split via `frob ticket scope`, single-writer CLI)

Evidence:
- tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_no_scope_entry_contains_a_semicolon (designated repro, FAILED_AT_PARENT verified against a synthetic pre-fix revert commit 5bf3f0f66 -- see below)
- tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_every_scope_entry_is_independently_matchable

Repro methodology: T-2450's scope fix was already committed in this
worktree before the repro test was written (both are the same one-line
data change), so a genuine pre-fix state was constructed explicitly: the
repro test was committed alone, then a follow-up commit reverted
tickets/T-2450/ticket.md's scope field back to its pre-fix (semicolon-
joined) content -- confirmed both new tests genuinely FAIL against that
commit (`AssertionError: T-2450 scope still carries a semicolon-joined
entry`) -- then a final commit re-applied the real fix, restoring the
same content `frob ticket scope`'s CLI write produced. `--check-repro`/
`--designate-repro --base-ref 5bf3f0f66` both verified FAILED_AT_PARENT
against that synthetic revert commit.

Filed: a follow-up draft ticket (kind=bug, scope src/frob/tickets/
_scope.py + _models.py) for the write-time validation gap -- nothing in
`frob ticket scope`/`new --scope`'s write path rejects a syntactically
invalid glob entry (only comma-splitting exists, T-0241; no semicolon
handling or general glob-validity check). Renumbers to its real id at
land; cite via the ledger block once landed.

Gates: full tests/unit/test_t2450_scope_repair.py run: 2 passed, 0
failed (measured). This ticket's own scope is data-only (a YAML ticket
frontmatter field plus one new small test file) with no other code
touched, so no broader gate sweep is load-bearing here.

### Changed
```
 tests/unit/test_t2450_scope_repair.py | 62 +++++++++++++++++++++++++++++++++
 tickets/T-2450/ticket.md              | 25 +++++++++++++-
 tickets/T-2614/ticket.md              | 20 +++++++++--
 tickets/T-2626/ticket.md    | 64 +++++++++++++++++++++++++++++++++++
 4 files changed, 168 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_no_scope_entry_contains_a_semicolon` (pytest node id, verified passing when recorded)
- `tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_every_scope_entry_is_independently_matchable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2614/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2614, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
