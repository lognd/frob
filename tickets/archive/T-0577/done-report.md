## Done report

Scope was empty at dispatch; set to src/frob/tickets/**, src/frob/app/ticket_runner.py,
src/frob/scaffold/project.py, docs/modules/tickets.md, docs/guides/agent-playbook.md,
and the tickets/land/scaffold-hook test files.

Implemented, against the two field-evidence scenarios named in the dispatch:

1. Draft finalize now rewrites registry-yaml ticket-id references, not just
   `frob:` directive lines. `frob.tickets.__init__._rewrite_registry_references`
   (new) matches `deferred:<id>`/`duplicate_of:<id>` disposition targets
   (the grammar `frob.registry._models.parse_disposition` reads) anywhere in a
   tracked file and rewrites the whole-word ticket id, independent of the
   existing `frob:` directive-line matcher. Wired into `_scan_code_references`
   so `renumber_one` (and therefore `finalize_draft`, and therefore
   `frob ticket land`) applies both classes of rewrite in the same pass.
   Regression test: a registry yaml's `disposition: "deferred:<draft-id>"`
   survives a real `land()` finalize with the draft id rewritten to the
   final T-#### everywhere, ledger and yaml alike.

2. Sibling Done-report preservation on ledger splice. `_splice_only_ticket`
   (T-0479) still takes every ticket id OTHER than the one landing from
   main untouched (the T-0475 resurrection guard stays intact), but a new
   `_preserve_sibling_done_reports` pass additionally keeps the WORKTREE's
   copy of a sibling id when main's copy has no substantive Done report and
   the worktree's does -- exactly the T-0386/T-0387/T-0388 incident
   (landing one ticket in a multi-ticket worktree erased a still-open
   sibling's already-written Done report and regressed its state to
   queued). A stale advanced-but-Done-report-less sibling (the genuine
   T-0479/T-0475 requeue case) is untouched by this rule -- main still wins
   there, proven by a dedicated non-regression test alongside the new
   preservation test.

3. Land-call serialization. The whole `land()` body (precheck through the
   squash commit) now runs under a dedicated `_land_lock` (`<root>/.frob/
   land.lock`, a fresh cross-process flock, deliberately NOT reusing
   `frob.tickets._store.ledger_lock`'s `.frob/tickets.lock` path -- that
   collided with the SAME relative path a landed worktree branch commits
   via its own `git add -A`, and git's squash-merge refused outright). A
   second concurrent `land()` against the same root now blocks instead of
   racing -- closes the REL001 version-bump-collision class (two lands
   reading the same pre-bump manifest version and each computing the same
   "next" version). `_porcelain_dirty` now ignores anything under `.frob/`
   (the lock file itself, plus every other `.frob/` scratch artifact) when
   deciding dirtiness, matching the repo convention that `.frob/` is always
   gitignored.

4. Raw ticket-branch merges forbidden. `frob.scaffold.
   install_worktree_lease_hook`'s `pre-merge-commit` hook now also refuses
   a real merge commit whose incoming side is a `worktree-agent-*` branch,
   from ANY shell (including a coordinator's -- the existing FROB_AGENT
   guard deliberately exempts the coordinator, this new guard does not).
   Detects the incoming branch via `$GIT_REFLOG_ACTION` (git sets this in
   every hook's environment); `.git/MERGE_HEAD` was tried first and
   observed empirically to be absent by the time `pre-merge-commit` fires
   on a plain, conflict-free merge under this git version -- documented in
   the hook script itself. `land()`'s own internal git calls never trip
   this hook (both suppress the automatic merge commit the hook fires
   for); `FROB_LAND_INTERNAL=1` is a documented manual override, proven by
   a dedicated end-to-end test with real `git merge`.

Gates: `uv run frob check --ticket T-0577` clean (0 errors, 378 warnings,
188 waived) after a fresh `frob ticket sweep T-0577` and after merging
main a second time to pull in fast-moving code (`git diff main
--diff-filter=D --stat` empty both before and after that merge -- no
stale-base deletions).

Not done / left as-is: the ticket body also named "TICK005-backed
regression sweep" and a "push option" for `land`; neither was touched --
scope was set to the four items with concrete field evidence in the
dispatch brief, and those two are unticketed/underspecified enough
(no TICK005 rule exists yet, no push-option design was named) that
building them here would have been scope creep without a plan. Filing
a follow-up ticket for TICK005 + push-option is the honest next step,
not silently claiming they're covered.

### Changed
```
 docs/modules/tickets.md                    |  62 +++++++++++
 src/frob/scaffold/project.py               |  61 +++++++++-
 src/frob/tickets/__init__.py               |  46 +++++++-
 src/frob/tickets/_land.py                  | 173 ++++++++++++++++++++++++++++-
 tests/system/test_cli_ticket_land.py       |  10 +-
 tests/test_scaffold_worktree_lease_hook.py |  71 ++++++++++++
 tests/test_ticket_land.py                  | 141 ++++++++++++++++++++++-
 7 files changed, 550 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSiblingDoneReportPreserved::test_sibling_done_report_survives_landing_another_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSiblingDoneReportPreserved::test_sibling_requeue_on_main_still_wins_when_neither_side_has_a_done_report` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDraftFinalizeRewritesRegistryYamlRefs::test_registry_yaml_deferred_ref_rewritten_to_final_id` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_raw_merge_of_worktree_agent_branch_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_raw_merge_override_env_var_allows_it` (pytest node id, verified passing when recorded)
