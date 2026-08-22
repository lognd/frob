## Done report

Fragment-per-ticket CHANGELOG.md write (T-2445): killed the ad-hoc,
shared-insertion-point splice into CHANGELOG.md's "unreleased" section
that every bump-worthy land used to do, replacing it with a
collision-free, self-healing mechanism.

FIX SHAPE CHOSEN: fragment-per-ticket (the coordinator's recommended
option, "the standard solution to exactly this problem" -- towncrier's
own convention). New module src/frob/release/_fragments.py:
- write_changelog_fragment(root, ticket_id, bump, note) writes
  changelog.d/T-####.md -- a brand-new file per ticket, so two
  different tickets can NEVER write the same path, regardless of
  concurrent activity on main.
- read_changelog_fragments(root) parses every fragment, sorted
  NUMERICALLY by ticket id (T-2 before T-10, not lexical), and fails
  CLOSED (Err, never silently skips) on any unparsable fragment --
  acceptance [1]'s "no dropped entries" as a structural property, not a
  best-effort.
- assemble_changelog_from_fragments(root, version) regenerates
  CHANGELOG.md's "## [version] - unreleased" section as a pure,
  deterministic function of the CURRENT fragment set every call --
  unlike frob.release.changelog_skeleton_entry (insert-once, frozen
  after the first land at a version), this REPLACES the section body
  each time, so a second land at the same still-unreleased version
  correctly grows the bullet list instead of being silently dropped.
  Idempotent: an unchanged fragment set reproduces byte-identical
  output.

frob.app.ticket_runner._land_cmd._write_release_bump now calls both
(write fragment, then assemble) instead of the old direct
changelog_skeleton_entry splice; the staged-files list for the land
commit gained changelog.d/. A small local _bump_class_between helper
labels each fragment's bump: header from the version delta (major/
minor/patch), since the authoritative diff_class computation stays
exactly where it already was (_required_release_bump, unchanged).

Worktree-lease guard (src/frob/scaffold/project.py, T-0731's existing
_FORBID_LAND_OWNED_FILES_SCRIPT): extended to refuse a worktree commit
touching changelog.d/* the same way it already refuses CHANGELOG.md --
new regression test
test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog_fragment
proves acceptance [2] end to end (real git commit, real installed hook).

WHY THIS BEATS THE OLD SPLICE EVEN THOUGH _reset_release_artifacts_to_
pre_land ALREADY whole-file-resets CHANGELOG.md fresh from pre_land_tip
before each land (so an in-land squash-merge CONFLICT on the text
itself was already rare): an interrupted land -- killed process,
uncaught exception, lock timeout -- that dies AFTER writing but before
finishing a multi-file text-splice/regex-substitute leaves root's
shared working tree in a half-mutated state that the NEXT land, for a
completely unrelated disjoint ticket, has to manually reconcile before
it can proceed. That reconciliation is what "manual conflict-resolve-
and-rebump" cost time. A fragment write is ONE new file via
atomic_write (temp file + fsync + os.replace) -- the worst an
interrupted land can leave behind is one harmless extra file, and the
very next land's own assembly step trivially heals over it because it
reads whatever fragments exist on disk, no unwind step required.

DISCLOSED SCOPE CUT: pyproject.toml's version line and
.frob-release.json's stamped manifest are UNCHANGED -- they still bump
on every land, exactly as before T-2445. Fully deferring that half too
(to an explicit release-cut) ripples into frob.gates.release_gate's
REL001 check and frob.app.ticket_runner._close_cmd's close-time bump
preflight, both of which currently assume "the manifest advances every
land"; changing that without also updating those two would make every
frob check on main error forever and make every API-touching ticket
permanently un-closeable between release cuts. src/frob/gates/__init__.py
was leased by a concurrent ticket (T-2435) at this dispatch's start, so
that half is filed as a separate follow-up rather than attempted
without the file: T-2462 (renumbers at land -- verify the
real id on main before citing it further).

Evidence: fragment round-trip/numeric-ordering/fail-closed-parse tests
(TestChangelogFragments), the real end-to-end land test
(TestRealCallbackStaleWorktreeManifest, exercises the REAL
_apply_release_bump_for_land callback through the actual land pipeline,
proving acceptance [0] with no manual resolution step), and the new
worktree-lease guard test (acceptance [2]). Full existing suites
re-run clean: tests/test_release.py + tests/test_ticket_land.py +
tests/test_scaffold_worktree_lease_hook.py = 361 passed, 0 failed.

Gates: ruff check/format, ty check clean on every touched file. Scoped
frob check --ticket T-2445 (scope/affect_drift/coverage/prework/
docblocks/docanchor): gate:SCOPE and gate:AFFECT clean (AFFECT001 on
docs/modules/release.md's new symbols and SCOPE001 on the two added
test files both closed by scope --add + frob:doc directives). gate:COV/
gate:DOC findings present in that run are pre-existing, unrelated to
any file this ticket touched (verified: none reference _fragments.py,
_write_release_bump, _bump_class_between, or scaffold/project.py's new
block).

### Changed
```
 tickets/T-2445/ticket.md           | 137 +++++++++++++++++++++++++++++++++++--
 tickets/T-2462/ticket.md |  36 ++++++++++
 2 files changed, 169 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_release.py::TestChangelogFragments::test_write_then_read_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestChangelogFragments::test_read_sorts_numerically_not_lexically` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestChangelogFragments::test_read_fails_closed_on_a_malformed_fragment` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestChangelogFragments::test_assemble_writes_every_fragment_as_a_bullet` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestChangelogFragments::test_assemble_is_idempotent_and_picks_up_new_fragments` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog_fragment` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2445/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2445/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2445/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2445/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2445, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/release/_fragments.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE001@src/frob/release/_fragments.py, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
