## Done report

Chose option 1 (mirror to the primary checkout), the preferred one: it removes
the failure rather than reporting it. Option 3 alone leaves an agent who reads
the warning with no mechanism short of the hand cherry-pick that already
happened once.

MECHANISM, reusing what already exists rather than inventing one. The T-1615
choke point (`_auto_commit_ledger_after_dispatch`) already funnels every
ledger-mutating verb through one call site, so the mirror is wired there and
nowhere else -- a verb added to the dispatch table in future is covered the
instant it is added. `_resolve_primary_checkout` (T-1003, how `land` finds the
real root from a worktree via the shared git common dir) answers "which root",
`refuse_if_land_in_progress` answers "is it safe right now", `ledger_lock`
serialises against other ledger writers, and `_without_agent_commit_guard`
handles the T-0431 hook. No new locking primitive was introduced.

CONTENTION, which the ticket called out as the hard constraint. The mirror
returns BEFORE any lock or land probe when the verb already ran in the primary
checkout, so a coordinator's own invocation costs literally nothing. From a
worktree it uses the same `refuse_if_land_in_progress` primitive the local
auto-commit already called, so no new class of wait is introduced on the common
path -- the added work is one pathspec-limited add+commit.

SAFETY. Only the ticket's own `_ledger_pathspecs` are read, so unlanded source
edits cannot ride along however dirty the worktree is -- that positive control
holds by construction, not by care. Both `git add` and `git commit` are
pathspec-limited, so a concurrent land staging content in the shared root
cannot be swept in as a passenger (the T-1403 incident shape).

The state-machine verbs are deliberately NOT mirrored. Their ledger write
describes work that is still worktree-local and `land` carries them atomically
with the code; mirroring one would advance main's state machine ahead of the
work it claims to have finished, which is a worse failure than the one being
fixed. That exclusion is itself tested rather than left as a comment.

MEASURED, and this one verified itself live: the `frob ticket scope --add` that
put this ticket's own test file in scope ran from the worktree, waited out an
in-flight land for T-2532, mirrored, and left main carrying the change at
commit e1000949c with the shared root clean. The fix demonstrated itself on its
own ticket while being built.

10 tests pass. Controls proven against the pre-fix behaviour at checkpoint
56cd4ffe5: the four must-fire controls fail there (the edit is invisible on the
primary checkout), the must-not-fire controls pass there unchanged, and
`--designate-repro` returned FAILED_AT_PARENT.

KNOWN INTERACTION, disclosed rather than discovered later. Main is now a second
writer of the same ticket file, so a later `git merge main` in a worktree can
conflict on it -- this branch hit exactly that and resolved it by keeping the
newer superset. The `frob ticket merge-driver` exists to splice this
automatically and is documented as a once-per-clone registration, but I measured
it as NOT registered in this clone (`git config --get merge.frob-tickets.driver`
is empty), which is why the conflict surfaced raw. Registering it is a
coordinator action, not a code change, and is noted in the new docs section.

CUT, disclosed: the third positive control ("concurrent lands must not be
DirtyMain-blocked") is covered in halves rather than as one test -- the
cleanliness half is `test_primary_worktree_is_left_clean`, and the
land-in-flight half is the `refuse_if_land_in_progress` guard, exercised live
during the scope call above but not as an automated test, because
deterministically staging a real concurrent land inside a unit test needs a
fixture this ticket's scope does not reach.

### Changed
```
 docs/modules/tickets-lifecycle.md              |  49 ++++++
 src/frob/app/ticket_runner/__init__.py         |  13 ++
 src/frob/app/ticket_runner/_ledger_mirror.py   | 225 +++++++++++++++++++++++++
 tests/unit/test_ticket_runner_ledger_mirror.py | 186 ++++++++++++++++++++
 tickets/T-2563/ticket.md                       |  15 +-
 5 files changed, 487 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_scope_edit_from_worktree_is_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_block_edit_from_worktree_is_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_attachment_file_reaches_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorCarriesNothingElse::test_worktree_source_changes_do_not_leak_to_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorCarriesNothingElse::test_primary_worktree_is_left_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope::test_running_in_the_primary_checkout_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2565/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2563/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2563/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2563/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2563, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/app/ticket_runner/_ledger_mirror.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE001@tests/unit/test_ticket_runner_ledger_mirror.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
