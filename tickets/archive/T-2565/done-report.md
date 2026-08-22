## Done report

Executed the migration shape this ticket was filed with, rather than the string
edit it looks like.

The hook header comment and `_managed._OURS_MARKER` both named `frob scaffold
install-worktree-lease-hook`, which has never been a real subcommand -- `frob
scaffold` exposes list/apply/new/pool, and `install_worktree_lease_hook` is a
function, not a CLI verb. The real installer is `frob scaffold apply`.

WHY IT IS A MIGRATION. The marker is how frob recognises a hook it OWNS
(`is_ours`, the one consumer, decides whether a hook may be updated or must be
left alone as the repo's own custom file). Renaming it outright would make
every ALREADY-INSTALLED hook stop matching -- silently never updated again and
never reported stale. So `_OURS_MARKER` becomes the corrected text and
`_LEGACY_OURS_MARKERS` keeps the old one recognised, with a documented rule for
when an entry may be retired (once installed hooks have had a release to turn
over). The single `is_ours` site becomes `_is_ours(body)`, which accepts either.

This is not hypothetical: the coordinator reinstalled the hooks fleet-wide
earlier today via `install_worktree_lease_hook(root, force=True)`, so hooks
carrying the old marker are live in this clone right now.

POSITIVE CONTROLS, BOTH DIRECTIONS:
- the current marker names a real command (must-fire: this is the defect);
- a freshly installed hook carries the current marker;
- a hook carrying the LEGACY marker is still recognised as ours (the migration
  control -- without it the rename silently orphans every installed hook);
- a genuinely foreign hook is still NOT claimed (the must-NOT-fire direction:
  widening recognition must not start overwriting somebody else's file);
- end to end, a legacy-marker hook is reported present AND stale -- updatable
  rather than abandoned.

Measured: 28 passed in tests/test_scaffold_worktree_lease_hook.py (23
pre-existing plus 5 new). Repro proven at checkpoint ae4fb1105 (the
pre-migration marker with the tests present): `--designate-repro` returned
FAILED_AT_PARENT.

ALSO CLEARED, and this is why the ticket mattered beyond tidiness: this
ticket's own body quoted the stale string twice, and with DOC006 promoted to
ERROR by T-2374 those were two hard errors sitting on the repo's floor,
blocking the whole fleet's lands rather than just mine. They are now waived
with an honest reason -- the body is quoting the exact text the ticket
retires, a historical record of the defect, not a live invocation. Measured
before/after: the DOC family drops from 8 errors to 6, and the two remaining
DOC006 findings belong to T-2561, another agent's ticket, not this one.

NOTED, not fixed (outside scope): BUG002's repro check spawns a scratch
worktree and checks out the whole tree (6331 files) to run one test at the
parent commit. Under fleet load that git call failed once here with a bare
`GitFailed`, reported NO_VERDICT, and refused -- a transient contention
failure presenting as an evidence problem. The identical command succeeded on
retry minutes later against the same commit, and a direct `git worktree add`
probe of that same commit succeeded immediately, which is what identified it as
contention rather than a bad base ref.

### Changed
```
 src/frob/scaffold/_managed.py              | 32 ++++++++++++-
 src/frob/scaffold/project.py               |  2 +-
 tests/test_scaffold_worktree_lease_hook.py | 73 ++++++++++++++++++++++++++++++
 tickets/T-2565/ticket.md                   | 13 +++++-
 4 files changed, 115 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_current_marker_names_a_real_command` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_a_foreign_hook_is_not_claimed` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_installed_hook_carries_the_current_marker` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_a_legacy_installed_hook_is_reported_stale_not_foreign` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/scaffold/_managed.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV005@src/frob/scaffold/_managed.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2565/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2565/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2565/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2565, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
