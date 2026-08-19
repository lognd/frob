## Done report

DOC006's CLI-invocation resolver only ever walked frob.__main__._build_parser()'s
own registration -- a decorative mirror kept for frob --help's grouped
overview, never touched at real argv-parse time for verbs routed through
a _dispatch_* bypass. worktree's whole subtree was incomplete (only sweep
registered, missing remove/release-lease); release's own mirror never
registered publish at all. DOC006 flagged docs naming these real,
working commands as "does not resolve to a known subcommand" -- a false
positive, confirmed by direct comparison against frob worktree remove
--help / frob worktree release-lease --help / frob release publish --help,
all of which resolve cleanly.

Fix: _BYPASS_SUBTREE_PATCHES/_BYPASS_LEAF_PATCHES in
src/frob/gates/_docblocks_refs.py, a small named table (keyed to frob's
own _build_parser path, inert for a downstream project's own
[[docblocks.commands]] entry) that splices each bypassed verb's REAL
subcommand tree -- read live from its own dispatch-time parser factory
(frob.app.worktree_runner._build_worktree_parser,
frob.release._cli.add_release_publish_parser) -- into the walked tree
before DOC006 resolves against it. worktree's whole node is replaced
(fully bypassed); release only gets the one publish leaf added (its
other subcommands genuinely register through _build_parser() already).

Positive controls verified both directions: the 3 previously-false-
positive real commands now resolve; a genuinely nonexistent
`frob worktree nonexistent-subcommand` / `frob release
nonexistent-subcommand` still fires (the patched tree is not a rubber
stamp).

Also removed 8 of the 9 T-2374 frob:waive DOC006 sites this fix makes
dead weight -- the underlying pointers now resolve honestly. Left ONE
waiver (`frob worktree sweep --force`): DOC006's separate FLAG
resolution path (src/frob/gates/_docptr.py, out of this ticket's
declared scope) still walks _build_parser()'s incomplete mirror PARSER
OBJECT directly for --flag lookups and does not see --force -- a
related but distinct gap, filed as T-2559 rather than silently widening
this ticket's own scope.

Also filed T-2558: an unrelated, genuinely pre-existing DOC006 finding
on tickets/T-2556/ticket.md (cites a scaffold subcommand that has never
existed under any name) surfaced while re-running the
zero-on-frob's-own-repo integration test. Confirmed via direct
inspection of _build_parser()'s real tree that this command genuinely
does not exist -- not a gate false positive, not fixable within T-2533's
own scope.

### Evidence
5 new tests, tests/test_docptr_gate.py::TestDoc006Cli -- 3 proving the
previously-flagged real commands now resolve, 2 proving a genuinely
nonexistent subcommand under each patched verb still fires.

### Changed
```
 docs/modules/tickets-landing.md   |  8 ++--
 docs/modules/tickets-lifecycle.md |  8 ++--
 src/frob/gates/_docblocks_refs.py | 90 +++++++++++++++++++++++++++++++++++-
 tests/test_docptr_gate.py         | 96 +++++++++++++++++++++++++++++++++++++++
 tickets/T-2533/ticket.md          | 29 +++++++++++-
 tickets/T-2558/ticket.md          | 61 +++++++++++++++++++++++++
 tickets/T-2559/ticket.md          | 62 +++++++++++++++++++++++++
 7 files changed, 343 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006Cli::test_dispatch_bypassed_worktree_remove_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_dispatch_bypassed_worktree_release_lease_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_dispatch_bypassed_release_publish_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_worktree_subcommand_still_genuinely_nonexistent_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_release_subcommand_still_genuinely_nonexistent_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2556/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DUP001@tests/test_docptr_gate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2533/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
