## Done report

Done report: T-4607
post-land sweep raises quarantine on its own lease-file/doc noise
(TICK010 on .git/frob-leases, DOC012 docs/commands) and dirties the
root ratchet lock, forcing every land synchronous

Worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-769b07dc
Code commit: dbc91e5a1579290da809e7f1a76409721e488d7b
Evidence commit (HEAD): a050d178780d3c481effaea7410320b73fe5fd87


## WHAT changed, per file, and WHY

### src/frob/app/ticket_runner/_rapid_sweep.py (item 1 + item 2)

- Added `_is_git_metadata_path(file) -> bool`: `True` for `.git` or any
  `.git/`-prefixed path. `.git/frob-leases/T-####.json` (another
  in-progress ticket's own worktree lease) is process state, not
  repository content -- its mtime/content changes on every lease
  renewal, so a naive TICK010 finding against it looks "new" on every
  single sweep, forever.

- `_normalize_identities` (the module's own documented single choke
  point every producer/consumer of an identity set routes through, per
  its pre-existing docstring) now drops any `(rule, file)` pair whose
  normalized file is git-internal, logged at INFO ("T-4607: dropped N
  (rule, file) pair(s) whose file is git-internal"). This is the
  earliest possible point: such a pair now never enters the baseline
  diff, is never filed as a regression ticket, and never reaches
  quarantine -- it simply never existed as a finding. A real `tickets/`
  (or any other repo-content) finding is untouched: the filter checks
  the literal `.git/` path prefix, never a rule id, so it can never
  suppress a genuine regression under any rule.

- `_filter_pairs_for_quarantine_raise` now also drops directory-shaped
  identities (`file.endswith("/")`, e.g. DOC012's own
  `file="docs/commands/"` from `_docblocks.py::_doc012_violation`) from
  the quarantine RAISE only -- not from filing. A directory can never
  match a commit's changed-FILE set, so `_attribute_new_findings` can
  never resolve it to an owning commit; left unfiltered it reads as
  permanently UNATTRIBUTED and re-trips the quarantine circuit breaker
  on every sweep that still has any doc drift anywhere in the repo.
  Still filed as a real regression ticket (doc drift is real, DOC012 is
  ERROR-severity in the ordinary gate) -- only kept off the dispose
  queue that raises quarantine. Logged at INFO naming the count
  dropped. The existing "dropped" accounting for the warm-tree
  native-noise filter was adjusted to not double-count these.

Why here and not in `_verify.py` (the earlier candidate,
`_error_finding_identity`/`_collect_error_findings`): that file is
under another in-progress ticket's (T-3943) exclusive scope lease at
the time of this fix -- `frob ticket scope --add` refused it
(`ScopeLeaseConflict`). `_normalize_identities` is architecturally the
right seam anyway per its own docstring ("the single call every
producer/consumer of an identity set in this module should route
through"), so no functionality was lost by fixing it here instead.

### src/frob/gates/_fix_engine_sync.py (item 3)

`_apply_capability_ratchet_bumps` (the write half of
`fix_sys111_capability_ratchet_sync`, a Tier-A auto-fix handler) wrote
`docs/design/registry/capability-via-ratchet.lock.json`
unconditionally whenever it computed a growth bump. T-4563 already
gated the OTHER writer of this same file (the T-4495 testsuite-glob
auto-accept in `frob.strata._effects`) on
`_land_commit_in_progress(root)` reading `True` -- i.e. only while a
land's own `land.lock` is held, so the write lands inside that land's
own composed commit instead of rewriting the plain root working tree
with no commit absorbing it. This second writer had no such gate.

Fix: `_apply_capability_ratchet_bumps` now imports
`_land_commit_in_progress` from `frob.strata._effects` and skips the
on-disk write (returns `[]`, same shape as "nothing to fix") when it
reads `False`, logging a WARNING naming the count that was computed
but not written. Growth is still a real SYS111 gate violation on the
next (land-owned) check run -- only the auto-bump write is
land-owned now, matching the sibling mechanism exactly.

Both of `fix_sys111_capability_ratchet_sync`'s two current callers
(`_land_cmd._sweep_apply_tier_a_pre_commit` /
`_sweep_apply_tier_a_and_commit`) run while `land()` holds `land.lock`
for the whole land, so ordinary land behavior (both existing tests
`test_sys111_bumps_growth_this_lands_diff_caused` and
`test_sys111_ratchet_bump_still_applies_through_scope_lease_filter`)
is unchanged -- they now create a marker `land.lock` file via a new
`_hold_land_lock` test helper before calling the handler, since they
exercise it directly/through `apply_tier_a_fixes` outside a real
`frob ticket land` process. This closes the gap for any OTHER caller
(a detached sweep, an interactive `frob check --fix`) that does not
hold that lock.

### Test files

- tests/unit/rapid_sweep_suite/test_dispose.py: two new tests on
  `TestNormalizeIdentities` --
  `test_drops_git_metadata_path_such_as_a_lease_file` (positive
  control: a TICK010 against `.git/frob-leases/T-9999.json` is
  filtered) and `test_leaves_a_real_tickets_dir_finding_alone`
  (negative control: a real TICK010 against `tickets/T-9999/ticket.md`
  passes through unchanged).

- tests/unit/rapid_sweep_suite/test_filing.py:
  `TestRaiseQuarantineForRedBatch.test_directory_shaped_finding_is_filed_but_not_quarantined`
  -- end-to-end through the real filer (`_file_regression_ticket`):
  files a ticket for a `("DOC012", "docs/commands/")` +
  `("RULE1", "a.py")` batch and asserts the directory-shaped pair never
  reaches the quarantine record while the batch is still filed.

- tests/gates_suite/test_fix_engine.py: added `_hold_land_lock` helper;
  updated the two existing write-path tests to hold the lock; added
  `test_sys111_without_land_lock_reports_but_does_not_write` (the
  actual T-4607 regression shape: growth computed, `applied == []`,
  lock file byte-identical before/after, WARNING logged).


## Acceptance criteria proof

1. ".git/** never enters the sweep's finding set" --
   `test_drops_git_metadata_path_such_as_a_lease_file` (positive) +
   `test_leaves_a_real_tickets_dir_finding_alone` (negative control,
   same rule id TICK010, real tickets/ path still passes).

2. DOC012 directory-shaped finding excluded from quarantine, with a
   logged reason, while still filed --
   `test_directory_shaped_finding_is_filed_but_not_quarantined`
   (asserts both: ticket filed AND `is_quarantined() is False`); the
   INFO log line in `_filter_pairs_for_quarantine_raise` names the
   count and the reason.

3. The second ratchet-lock writer is gated on land.lock, tested --
   `test_sys111_without_land_lock_reports_but_does_not_write` (no
   lock -> no write, WARNING logged) plus the two pre-existing tests
   re-verified to still pass WITH a held lock (unchanged land
   behavior).

4. Land-time top-3 sinks + tickets filed -- see below.


## Item 4: land-time analysis (/tmp/land-T-3233.log)

T-3233's log covers two attempts. First attempt (06:49:36-06:50:18,
LAND-EXIT=1) was refused at [+2.9s] by a real `ty check` NEW-error
finding in the ticket's own touched file. Second attempt
(08:38:51-08:42:02, LAND-EXIT=0, total ~191s) succeeded and landed as
d164d5df8. The `[+Ns]` phase markers in the successful run:

  [+0.0s]   pre-land Tier-A fixes applied
  [+3.4s]   effective profile=rapid; quarantine IS raised (16
            undisposed findings) -> forces fully-synchronous
            verification (T-1693), pre-land baseline skipped
  [+30.7s]  rapid --files scoped to 9 files
  [+141.6s] auto-synced worktree onto dev
  (LAND-EXIT at ~+191s, i.e. ~49s after the last marker)

Top three time sinks, ranked by measured duration, each with a ticket
filed to cut it:

1. THE DOMINANT COST: +30.7s -> +141.6s = 110.9s, 58% of total land
   wall time, with ZERO phase-transition log lines anywhere in that
   span (commit assembly, claims re-verification, the wip-add
   ignored-path fallback, the REL001 bump, and the rapid-sweep dispatch
   all happen here, completely unattributed). Filed:
   T-draft-f5ac9ec0 -- "instrument the silent ~111s land phase between
   rapid --files scoping and worktree auto-sync with phase-transition
   logging" (extend `_LandPhaseElapsedFilter`'s existing T-4417
   coverage through this span so the dominant cost becomes measurable
   instead of merely noticed after the fact).

2. +3.4s -> +30.7s = 27.3s spent in forced fully-synchronous
   verification specifically BECAUSE quarantine was raised (T-1693) --
   this ticket's own items 1-3 (above) cut the false-positive share of
   that raise (lease-file/doc noise, dirty-root writes), but a real
   quarantine raise still pays this cost blind: the log line only
   names a COUNT ("16 finding(s) undisposed"), never which findings,
   so triaging mid-land needs a separate `frob verify dispose` round
   trip. Filed: T-4611 -- "land's own refusal-avoidance
   quarantine-raised log line does not name the undisposed findings
   forcing synchronous verification" (enumerate/summarize the
   (rule, file) identities inline in that log line).

3. The first attempt's own failure-then-stall shape: a real regression
   (`ty check`) was only caught at [+2.9s] INSIDE a full `frob ticket
   land` dispatch, costing a land-queue slot, with a ~1h42m gap before
   the retry. Filed: T-4609 -- "fast pre-flight
   ty-check-only step before dispatching a full frob ticket land"
   (catch this exact shape in seconds, pre-dispatch, instead of
   spending a full land attempt on it).


## Evidence (pytest node ids, bound via `frob ticket evidence`, base-ref dev)

tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities::test_drops_git_metadata_path_such_as_a_lease_file
tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities::test_leaves_a_real_tickets_dir_finding_alone
tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch::test_directory_shaped_finding_is_filed_but_not_quarantined
tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_without_land_lock_reports_but_does_not_write
tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_ratchet_bump_still_applies_through_scope_lease_filter

Full local runs (all green before evidence binding):
- tests/unit/rapid_sweep_suite/ (whole suite): 211 passed
- tests/gates_suite/test_fix_engine.py (whole file): 74 passed

Note: `frob ticket evidence` warned that the close-time mutation sweep
for this node set projects ~134s against a 90s budget and may report
UNMEASURED rather than confirmatory -- left as-is (not rebound/split)
since the coordinator's close-time gate, not this report, decides how
to handle that; flagged here so it isn't a surprise.


## Filed (out-of-scope / follow-up tickets)

T-draft-f5ac9ec0 -- instrument the silent ~111s land phase
T-4611 -- name undisposed findings in the quarantine-raised log line
T-4609 -- fast pre-flight ty-check-only step before a full land dispatch


## Gates

- `frob check --only gates --files <5 touched files> --base dev`: ran
  clean -- 0 ERROR-severity lines in the output, no COV002 against the
  new `_is_git_metadata_path` symbol or the `_land_commit_in_progress`
  gate added to `_apply_capability_ratchet_bumps` (both carry
  docstrings; the latter is private, no new frob:tests/frob:doc
  obligation).
- `frob check --only coverage --files <2 touched src files> --base
  dev`: ran clean -- no COV002 lines against the touched files.
- `ruff check` on all 5 touched files: All checks passed (2
  pre-existing unrelated `# noqa` warnings elsewhere in
  test_fix_engine.py at lines 1822/1830, not touched by this change).
- `ruff format --check`: clean after auto-formatting
  test_filing.py (whitespace only, re-verified: still 31/31 green).
- `ty check` on both touched src files: All checks passed.

Waivers added: none.
Tests skipped: none.
Scope refusals: `src/frob/app/ticket_runner/_verify.py` (the original
candidate seam) was refused by `frob ticket scope --add`
(ScopeLeaseConflict, held by in-progress T-3943) -- worked around
architecturally via `_normalize_identities` in `_rapid_sweep.py`
instead, as documented above; no functionality lost.
Cross-ticket file overlap: none known -- all 5 touched files were
free to lease at scope-add time.

Repair follow-up (land refused twice):

(1) Duplicate id T-draft-f5ac9ec0: dev had promoted this unrelated draft to T-4599
(confirmed dev's tickets/T-4599/ticket.md exists and dev has no tickets/T-draft-f5ac9ec0/
dir at all -- fully promoted, in-progress, with real scope). Deleted this worktree's stale
tickets/T-draft-f5ac9ec0/ dir (git rm -rf), kept dev's T-4599 untouched. Note: dev's own
T-4599/ticket.md still has `id: T-draft-f5ac9ec0` on its id line (a pre-existing bug in
dev's own promotion, not introduced by this merge) -- left as-is, not ours to rewrite.
Checked whether dev had also promoted T-4607 itself: it has not (dev's
tickets/T-4607/ still exists under its draft id), so no id-adoption was needed
for this ticket. Verified every tickets/<dir>/ticket.md id line matches its directory
afterward (the one mismatch found, T-4599 vs its own id line, is dev's pre-existing issue,
noted above, not fixed here). Committed with FROB_LAND_INTERNAL=1 (commit 8afd5e934).

(2) ARCH001: _filter_pairs_for_quarantine_raise (src/frob/app/ticket_runner/
_rapid_sweep.py) was 93 lines, over the long-and-complex threshold. Extracted the T-4607
directory-shaped-identity exclusion's logging into a small private helper,
_log_directory_shaped_pairs_dropped(final_id, directory_shaped_pairs) -- a no-op on an
empty list, otherwise the same _log.info call the parent used to run inline. Verified with
`frob check --only arch --files src/frob/app/ticket_runner/_rapid_sweep.py --base dev`:
`pass frob-arch: 19 warnings (36 waived), 542 suggestions` -- no ARCH001 anywhere in the
output; every warning is unrelated repo-wide pattern-recommendation noise (same class as
seen on T-draft-76fef001's identical check). ruff check/format clean.
tests/unit/rapid_sweep_suite/test_dispose.py + test_filing.py (the quarantine-raise/
directory-shaped-pair test coverage) re-run green: SUITE-RESULT exitstatus=0 collected=57
failed=0. Commit c55cdfb5b.

HEAD after both fixes: (see READY line in the final report).

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 +++-
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 ++-
 CHANGELOG.md                                       |  53 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3020.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3233.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
 changelog.d/T-4214.md                              |   2 +
 changelog.d/T-4413.md                              |   2 +
 changelog.d/T-4414.md                              |   2 +
 changelog.d/T-4415.md                              |   2 +
 changelog.d/T-4491.md                              |   2 +
 changelog.d/T-4492.md                              |   2 +
 changelog.d/T-4493.md                              |   2 +
 changelog.d/T-4494.md                              |   2 +
 changelog.d/T-4495.md                              |   2 +
 changelog.d/T-4496.md                              |   2 +
 changelog.d/T-4498.md                              |   2 +
 changelog.d/T-4501.md                              |   2 +
 changelog.d/T-4502.md                              |   2 +
 changelog.d/T-4503.md                              |   2 +
 changelog.d/T-4510.md                              |   2 +
 changelog.d/T-4511.md                              |   2 +
 changelog.d/T-4512.md                              |   2 +
 changelog.d/T-4514.md                              |   2 +
 changelog.d/T-4517.md                              |   2 +
 changelog.d/T-4520.md                              |   2 +
 changelog.d/T-4521.md                              |   2 +
 changelog.d/T-4522.md                              |   2 +
 changelog.d/T-4523.md                              |   2 +
 changelog.d/T-4531.md                              |   2 +
 changelog.d/T-4532.md                              |   2 +
 changelog.d/T-4535.md                              |   2 +
 changelog.d/T-4536.md                              |   2 +
 changelog.d/T-4540.md                              |   2 +
 changelog.d/T-4543.md                              |   2 +
 changelog.d/T-4547.md                              |   2 +
 changelog.d/T-4548.md                              |   2 +
 changelog.d/T-4550.md                              |   2 +
 changelog.d/T-4552.md                              |   2 +
 changelog.d/T-4553.md                              |   2 +
 changelog.d/T-4554.md                              |   2 +
 changelog.d/T-4555.md                              |   2 +
 changelog.d/T-4556.md                              |   2 +
 changelog.d/T-4563.md                              |   2 +
 changelog.d/T-4579.md                              |   2 +
 changelog.d/T-4582.md                              |   2 +
 changelog.d/T-4583.md                              |   2 +
 changelog.d/T-4596.md                              |   2 +
 design/frob.strata                                 | 133 ++--
 docs/commands/check.md                             |  15 +
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  50 +-
 docs/commands/ticket.md                            |  72 ++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 ++
 .../registry/capability-via-ratchet.lock.json      |  69 +-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/install.md                             |  40 +
 docs/guides/release.md                             |  37 +
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gates.md                              |   3 +-
 docs/modules/graph.md                              |  39 +
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  16 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 188 ++++-
 docs/modules/tickets.md                            |   9 +-
 docs/strata/surface.md                             |  40 +
 frob.lock                                          |  42 +-
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/_check.py                    |  16 +
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++-
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 +++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       |  23 +-
 src/frob/app/config.py                             |  92 ++-
 src/frob/app/ticket_runner/__init__.py             | 125 ++--
 src/frob/app/ticket_runner/_land_cmd.py            | 532 +++++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 664 ++++++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 235 +++++-
 src/frob/check/__init__.py                         | 244 ++++---
 src/frob/check/_python.py                          | 136 ++--
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 +++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 ++++++
 src/frob/excludes.py                               |  83 ++-
 src/frob/gates/__init__.py                         | 263 ++++---
 src/frob/gates/_fix_engine_sync.py                 |  69 +-
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 ++++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 101 ++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 +++++
 .../scaffold/data/types/unity-project/frob.toml.j2 |  64 ++
 src/frob/scaffold/project.py                       |   6 +-
 src/frob/strata/_effects.py                        | 494 +++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 +++++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 +++++++++
 src/frob/testing/_stackdump.py                     |  68 +-
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 122 +++-
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   |  48 +-
 src/frob/tickets/_leases.py                        | 552 ++++++++++----
 src/frob/tickets/_models.py                        |  42 +-
 src/frob/tickets/_setters.py                       | 113 ++-
 src/frob/tickets/_store.py                         |  42 +-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 ++++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 ++++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 ++++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  54 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 +
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 +
 .../python_control/duplicate.py                    |  29 +
 tests/fixtures/dsl_todo_notes/sample.c             |   3 +
 tests/fixtures/dsl_todo_notes/sample.cpp           |   3 +
 tests/fixtures/dsl_todo_notes/sample.cs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.cu            |   3 +
 tests/fixtures/dsl_todo_notes/sample.java          |   3 +
 tests/fixtures/dsl_todo_notes/sample.kt            |   3 +
 tests/fixtures/dsl_todo_notes/sample.py            |   9 +
 tests/fixtures/dsl_todo_notes/sample.rs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.sh            |   3 +
 tests/fixtures/dsl_todo_notes/sample.ts            |   3 +
 tests/fixtures/dsl_todo_notes/sample.zig           |   3 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |  14 +
 .../lang/csharp/combined_static_and_namespace.cs   |  16 +
 .../dotnet_bcl_activator_createinstance_eval.cs    |  12 +
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |  12 +
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |  12 +
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |  12 +
 .../dotnet_bcl_jsonserializer_deserialize.cs       |  12 +
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |  12 +
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |  13 +
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |  13 +
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |  13 +
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |  12 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |  17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |  12 +
 tests/fixtures/lang/csharp/static_using_console.cs |  12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |  20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |  21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |  18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |  12 +
 .../Assets/Editor/Editor.asmdef                    |   6 +
 .../Assets/Editor/Editor.asmdef.meta               |   2 +
 tests/fixtures/unity_sample_asmdef/Assets/Loose.cs |   2 +
 .../Assets/Runtime/Runtime.asmdef                  |   6 +
 .../Assets/Runtime/Runtime.asmdef.meta             |   2 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef        |   6 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef.meta   |   2 +
 .../unity_sample_asmdef/Assets/Tests/Tests.asmdef  |   6 +
 .../Assets/Tests/Tests.asmdef.meta                 |   2 +
 .../unity_sample_asmdef/Packages/manifest.json     |   3 +
 .../ProjectSettings/ProjectVersion.txt             |   2 +
 tests/gates_suite/test_fix_engine.py               |  63 ++
 tests/test_excludes.py                             |  75 ++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 ++
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 +++
 tests/test_lang.py                                 |  90 +++
 tests/test_lang_conformance_gate.py                |  81 ++-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 ++-
 tests/test_ticket_leases.py                        | 313 +++++---
 tests/test_ticket_work_and_land_finish.py          | 206 +++---
 tests/test_tickets_migration.py                    | 121 ++--
 tests/test_tickets_parent.py                       | 208 ++++++
 tests/test_waive_gate.py                           | 145 ++++
 tests/unit/graph/test_dsl.py                       | 164 ++++-
 tests/unit/rapid_sweep_suite/test_dispose.py       |  39 +
 tests/unit/rapid_sweep_suite/test_filing.py        |  33 +
 tests/unit/rapid_sweep_suite/test_window.py        | 457 ++++++++++++
 tests/unit/strata/test_effects.py                  |  44 ++
 tests/unit/strata/test_selfconform.py              | 263 ++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 ++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 ++--
 tests/unit/test_check_scoped_files.py              | 566 +++++++++++++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 +++++
 tests/unit/test_cli_group_parity.py                | 220 ++++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 +++
 tests/unit/test_cli_single_child_groups.py         | 106 +++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  35 +-
 tests/unit/test_doctor.py                          | 115 +++
 tests/unit/test_done_report_check_scope.py         | 177 +++++
 tests/unit/test_land_default_queue.py              | 128 ++++
 tests/unit/test_land_in_progress_window.py         | 351 +++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 +++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 ++++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_leases_staleness_perf.py           | 310 ++++++++
 tests/unit/test_lifecycle_work_base.py             | 217 ++++++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 ++++
 tests/unit/test_support_csharp.py                  | 190 +++++
 tests/unit/test_suppress_worktree_path.py          |  87 +++
 tests/unit/test_ticket_cli_surface.py              | 182 +++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_xref.py                            |  40 +
 tests/vet_suite/test_capability_registry_unity.py  | 130 ++++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 +++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 +++
 tickets/T-1661/ticket.md                           |  23 +-
 tickets/T-1778/ticket.md                           |  17 +-
 tickets/T-1820/ticket.md                           |  17 +-
 tickets/T-1831/ticket.md                           |  17 +-
 tickets/T-2451/ticket.md                           |  17 +-
 tickets/T-2752/ticket.md                           |  17 +-
 tickets/T-2803/ticket.md                           |  17 +-
 tickets/T-2835/ticket.md                           |  17 +-
 tickets/T-2837/ticket.md                           |  17 +-
 tickets/T-2856/ticket.md                           |  17 +-
 tickets/T-2886/ticket.md                           |  17 +-
 tickets/T-2889/ticket.md                           |  23 +-
 tickets/T-2939/ticket.md                           |  17 +-
 tickets/T-2962/ticket.md                           |  17 +-
 tickets/T-2965/done-report.md                      | 149 ++++
 tickets/T-2965/ticket.md                           |  41 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-3020/done-report.md                      | 578 +++++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  17 +-
 tickets/T-3053/ticket.md                           |  16 +-
 tickets/T-3063/ticket.md                           |  17 +-
 tickets/T-3067/ticket.md                           |  17 +-
 tickets/T-3082/ticket.md                           |  63 +-
 tickets/T-3083/ticket.md                           |  17 +-
 tickets/T-3102/ticket.md                           |  17 +-
 tickets/T-3127/ticket.md                           |  17 +-
 tickets/T-3193/ticket.md                           |  17 +-
 tickets/T-3213/ticket.md                           |  17 +-
 tickets/T-3221/ticket.md                           |  17 +-
 tickets/T-3229/ticket.md                           |  17 +-
 tickets/T-3232/done-report.md                      | 179 +++++
 tickets/T-3232/ticket.md                           |  88 ++-
 tickets/T-3233/done-report.md                      | 606 ++++++++++++++++
 tickets/T-3233/ticket.md                           |  62 +-
 tickets/T-3241/ticket.md                           |  17 +-
 tickets/T-3259/ticket.md                           |  17 +-
 tickets/T-3262/ticket.md                           |  17 +-
 tickets/T-3270/ticket.md                           |  17 +-
 tickets/T-3274/ticket.md                           |  16 +-
 tickets/T-3327/ticket.md                           |  17 +-
 tickets/T-3330/ticket.md                           |  17 +-
 tickets/T-3335/ticket.md                           |  17 +-
 tickets/T-3351/ticket.md                           |  17 +-
 tickets/T-3357/ticket.md                           |  17 +-
 tickets/T-3359/ticket.md                           |  17 +-
 tickets/T-3377/ticket.md                           |  17 +-
 tickets/T-3412/ticket.md                           |  17 +-
 tickets/T-3415/ticket.md                           |  17 +-
 tickets/T-3459/ticket.md                           |  17 +-
 tickets/T-3504/ticket.md                           |  17 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  17 +-
 tickets/T-3564/ticket.md                           |  17 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3612/done-report.md                      | 221 ++++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 +++++-
 tickets/T-3614/ticket.md                           | 111 ++-
 tickets/T-3615/done-report.md                      |  33 +
 tickets/T-3615/ticket.md                           |  30 +-
 tickets/T-3620/ticket.md                           |  16 +-
 tickets/T-3646/ticket.md                           |  17 +-
 tickets/T-3659/ticket.md                           |  16 +-
 tickets/T-3660/ticket.md                           |  17 +-
 tickets/T-3677/ticket.md                           |  17 +-
 tickets/T-3714/ticket.md                           |  17 +-
 tickets/T-3716/ticket.md                           |  17 +-
 tickets/T-3728/ticket.md                           |  17 +-
 tickets/T-3729/ticket.md                           |  17 +-
 tickets/T-3739/ticket.md                           |  17 +-
 tickets/T-3758/ticket.md                           |  17 +-
 tickets/T-3783/ticket.md                           |  16 +-
 tickets/T-3789/ticket.md                           |  17 +-
 tickets/T-3802/ticket.md                           |  17 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3856/done-report.md                      | 247 +++++++
 tickets/T-3856/ticket.md                           |  60 +-
 tickets/T-3859/ticket.md                           |  17 +-
 tickets/T-3867/ticket.md                           |  17 +-
 tickets/T-3882/ticket.md                           |  17 +-
 tickets/T-3883/ticket.md                           |  17 +-
 tickets/T-3896/ticket.md                           |  17 +-
 tickets/T-3899/ticket.md                           |  26 +
 tickets/T-3904/ticket.md                           |  17 +-
 tickets/T-3917/ticket.md                           |  17 +-
 tickets/T-3918/ticket.md                           |  16 +-
 tickets/T-3919/ticket.md                           |  17 +-
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3943/ticket.md                           |  40 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3986/ticket.md                           |   2 +-
 tickets/T-3995/ticket.md                           |   2 +
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4035/ticket.md                           |   2 +
 tickets/T-4073/ticket.md                           |  12 +-
 tickets/T-4111/ticket.md                           |  20 +-
 tickets/T-4112/ticket.md                           |  33 +-
 tickets/T-4113/ticket.md                           |  33 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/ticket.md                           |   2 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 +++++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/ticket.md                           |  80 +-
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4240/ticket.md                           |   2 +-
 tickets/T-4254/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4413/done-report.md                      |  71 ++
 tickets/T-4413/ticket.md                           |  75 +-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  56 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           |  17 +-
 tickets/T-4420/ticket.md                           |  17 +-
 tickets/T-4421/ticket.md                           |  17 +-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  17 +-
 tickets/T-4491/done-report.md                      |  23 +
 tickets/T-4491/ticket.md                           |  69 ++
 tickets/T-4492/done-report.md                      |  34 +
 tickets/T-4492/ticket.md                           |  67 ++
 tickets/T-4493/done-report.md                      |  19 +
 tickets/T-4493/ticket.md                           |  61 ++
 tickets/T-4494/done-report.md                      | 138 ++++
 tickets/T-4494/ticket.md                           |  73 ++
 tickets/T-4495/done-report.md                      | 197 +++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 ++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 ++
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 +++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 ++
 tickets/T-4503/done-report.md                      | 592 +++++++++++++++
 tickets/T-4503/ticket.md                           |  94 +++
 tickets/T-4504/ticket.md                           |  69 ++
 tickets/T-4505/ticket.md                           |  38 +
 tickets/T-4506/ticket.md                           |  40 +
 tickets/T-4507/ticket.md                           |  37 +
 tickets/T-4508/ticket.md                           | 114 +++
 tickets/T-4509/ticket.md                           |  47 ++
 tickets/T-4510/done-report.md                      | 149 ++++
 tickets/T-4510/ticket.md                           |  81 +++
 tickets/T-4511/done-report.md                      |  97 +++
 tickets/T-4511/ticket.md                           | 103 +++
 tickets/T-4512/done-report.md                      | 524 ++++++++++++++
 tickets/T-4512/ticket.md                           | 102 +++
 tickets/T-4513/ticket.md                           |  36 +
 tickets/T-4514/done-report.md                      | 179 +++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 +++++
 tickets/T-4517/ticket.md                           |  94 +++
 tickets/T-4518/ticket.md                           |  34 +
 tickets/T-4519/ticket.md                           |  67 ++
 tickets/T-4520/done-report.md                      | 163 +++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 ++++++
 tickets/T-4521/ticket.md                           | 125 ++++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 +++
 tickets/T-4523/ticket.md                           |  40 +
 tickets/T-4524/ticket.md                           |  45 ++
 tickets/T-4526/ticket.md                           |  45 ++
 tickets/T-4529/ticket.md                           |  76 ++
 tickets/T-4530/ticket.md                           |  64 ++
 tickets/T-4531/done-report.md                      |  21 +
 tickets/T-4531/ticket.md                           | 110 +++
 tickets/T-4532/done-report.md                      |  24 +
 tickets/T-4532/ticket.md                           |  66 ++
 tickets/T-4533/ticket.md                           |  35 +
 tickets/T-4534/ticket.md                           |  69 ++
 tickets/T-4535/done-report.md                      |  64 ++
 tickets/T-4535/ticket.md                           |  61 ++
 tickets/T-4536/done-report.md                      |  78 ++
 tickets/T-4536/ticket.md                           | 128 ++++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  60 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 ++++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  84 +++
 tickets/T-4547/done-report.md                      | 137 ++++
 tickets/T-4547/ticket.md                           |  45 ++
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 ++++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 ++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 +++++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 ++++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 ++++++++++++++
 tickets/T-4555/ticket.md                           |  78 ++
 tickets/T-4556/done-report.md                      | 602 +++++++++++++++
 tickets/T-4556/ticket.md                           |  46 ++
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 ++
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/ticket.md                           |  35 +
 tickets/T-4563/done-report.md                      | 556 ++++++++++++++
 tickets/T-4563/ticket.md                           |  47 ++
 tickets/T-4566/ticket.md                           | 154 ++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 ++
 tickets/T-4572/ticket.md                           |  43 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 +
 tickets/T-4578/ticket.md                           |  32 +
 tickets/T-4579/done-report.md                      | 522 ++++++++++++++
 tickets/T-4579/ticket.md                           |  68 ++
 tickets/T-4580/ticket.md                           |  47 ++
 tickets/T-4581/ticket.md                           |  47 ++
 tickets/T-4582/done-report.md                      | 551 ++++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 ++++++++++++++++
 tickets/T-4583/ticket.md                           |  87 +++
 tickets/T-4588/ticket.md                           |  41 ++
 tickets/T-4589/ticket.md                           |  53 ++
 tickets/T-4596/done-report.md                      | 640 ++++++++++++++++
 tickets/T-4596/ticket.md                           |  43 ++
 tickets/T-4597/ticket.md                           |  31 +
 tickets/T-4598/ticket.md                           |  29 +
 tickets/T-4599/ticket.md                           |  69 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  41 ++
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  54 ++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4608/ticket.md                 |  41 ++
 tickets/T-4609/ticket.md                 |  27 +
 tickets/T-4607/done-report.md            | 803 +++++++++++++++++++++
 tickets/T-4607/ticket.md                 |  81 +++
 tickets/T-4611/ticket.md                 |  28 +
 uv.lock                                            |   2 +-
 518 files changed, 37934 insertions(+), 1816 deletions(-)
```

### Evidence
- `tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities::test_drops_git_metadata_path_such_as_a_lease_file` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities::test_leaves_a_real_tickets_dir_finding_alone` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch::test_directory_shaped_finding_is_filed_but_not_quarantined` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_without_land_lock_reports_but_does_not_write` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_ratchet_bump_still_applies_through_scope_lease_filter` (pytest node id, verified passing when recorded)
