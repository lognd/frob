## Done report

Re-measured the full suite on a fresh worktree (merged to main tip
4310bb76, natives built): a foreground `pytest -p no:cacheprovider -q`
run completed in one shot with 25 failures total (not ~118 -- the prior
number was stale, most of it already fixed by earlier waves before this
ticket started).

Triaged all 25 into fix-in-place (22) or filed-as-separate-ticket (3,
each requiring a real cross-file security/architecture disposition
outside this ticket's tests/**-rooted scope):

Genuine product/source bugs fixed:
- src/frob/tickets/_land.py::_do_wip_commit -- `git add -A` swept up
  frob's own .frob/ scratch artifacts (cache.db, derived.lock,
  prework/*.json, tickets.lock) as real staged changes in a fixture repo
  with no .gitignore, defeating the CRLF-normalization-only no-op
  detection. Excluded `.frob/` from the wip-commit pathspec.
- src/frob/deploy/_generate.py::_node_capabilities -- CAP_NET_BIND_SERVICE
  silently stopped being granted for any node declaring only a T-0717
  mode-qualified `family.mode` may atom (e.g. "net.out"), because
  _CAP_KIND_MAP is keyed by the bare coarse family ("net"). Fixed the
  lookup to key off the family prefix.
- src/frob/app/exports_runner.py::_try_exports_via_daemon -- `frob
  exports <path> --json` corrupted its own JSON payload with a leaked
  `gitio: spawning (...)` DEBUG log line whenever the T-1127 daemon-proxy
  fast path hit, because that helper's repo_root()/query() calls ran
  entirely outside run()'s quiet_stdout_logs() context. Wrapped the
  helper's body in the same context the non-daemon fallback already uses.

Test/fixture fixes (stale expectations, drift from landing waves):
- tests/test_ticket_land.py (3 tests) -- raw `git status --porcelain`
  checks that should have used the file's own `_status_ignoring_frob`
  helper (like every sibling assertion in the same tests), tripped by
  land's own `.frob/land.lock`.
- tests/test_tickets_review.py (4 tests) -- fixture evidence id
  ("tests/fixture.py::test_ok") never resolved against a real test;
  close()'s N-02 evidence-reverification (added after this fixture was
  written) now always fails it. Fixture writes one real, trivial, always-
  green test file instead.
- tests/test_registry_reconciliation_evasion.py /
  _supply_chain.py -- their positive-case "at least one deferred entry"
  self-checks now find zero (every prior deferral has been resolved by
  landing waves); skip with a clear reason instead of asserting a false
  premise, matching the T-1116 precedent already in the sibling
  weaknesses.py test. Waived the resulting DUP001/DUP002 clone findings
  (T-1116-precedented, same shape across all four sibling registry test
  files by convention).
- tests/test_coverage.py::_init_repo -- fixture never gitignored .frob/,
  so frob's own derived.lock write during the test showed up as a real
  untouched-by-user file and fell back to a suite-wide '*' selection.
  Added `.frob/` to the fixture's own .gitignore.
- tests/test_check_coverage_registry.py / test_registry_exhaustiveness.py
  (REG010 half) -- 6 live gate rules (VET-JS004, VET-PY001-3, VET-RS001-2)
  had no CHK-GATE entry in check-coverage.yaml. Ran the existing `frob
  registry audit --sync-gate-rules` to file them.
- tests/unit/strata/test_registry_cross_corpus_totality.py -- two
  one-directional cross_refs (SLH-SYS-EVA-01/02 -> CHK-GATE-SYS103/100)
  missing the reciprocal link on the check-coverage.yaml side. Added the
  two missing cross_refs.
- tests/test_makefile_lock_sync.py -- asserted a literal `uv lock` step
  the Makefile's `upload:` recipe no longer has (T-1009 replaced it with
  `frob release sync`, which relocks uv.lock internally). Updated the
  assertion to check for the superseding step instead.
- tests/unit/deploy/test_generate.py -- same T-0717 mode-qualified-kind
  root cause as the _generate.py fix above; test now passes with the fix.
- tests/system/test_system.py -- hardened two-user model fixture never
  declared `attr health;` on its two `unit` daemon nodes; a real,
  currently-live reliability obligation (check_reliability_health) now
  requires it. Added the attr to both fixture nodes.
- tests/unit/strata/test_export_golden.py::test_seccomp -- design/
  frob.strata legitimately grew new net.* capability declarations since
  this golden was captured (accept/bind/connect/listen/recvfrom/sendto/
  socket now appear as allowed syscalls for the affected node(s)).
  Regenerated the golden from the current model.
- tests/unit/test_app_runners_batch5.py::TestStatsRunner::
  test_json_mode_prints_json -- `stats_run` now proxies through the T-1094
  daemon by default; the background-daemon-subprocess/socket-retry path
  writes asynchronously and is not reliably observable via capsys/capfd at
  the point stats_run returns. Set FROB_NO_DAEMON=1 (the documented
  T-1093 bypass) so this unit test exercises the runner's own synchronous
  rendering deterministically -- the daemon round trip has its own
  dedicated coverage in tests/test_app_daemon_proxy.py.
- tests/unit/test_strata_tmlanguage.py -- strata-core/src/parse.rs was
  split into strata-core/src/parse/ (mod.rs + 6 grammar_*.rs/lexer.rs
  files, mirroring the T-1103 tickets/__init__.py split precedent).
  Updated the drift-lock to concatenate every .rs file under parse/, and
  ran `frob sys sync-interface` to fix the resulting SYS104
  interface=PARSE_RS -> PARSE_DIR drift on design/frob.strata (this was
  the one self-inflicted regression caught by a second full-suite run
  after the rename -- fixed before finalizing).

Filed as separate tickets (each needs a real judgment call/cross-file
work outside tests/**), one already dropped as moot:
- T-1168 (vet: 11 missing frob:enforces CHK-GATE edges,
  REG008 burn-down for VET007-010/SYSWAIVE003/VET-JS004/VET-PY001-3/
  VET-RS001-2) -- filed, then DROPPED after merging main (daada10f):
  concurrent wave work independently resolved every REG008 finding
  before this ticket was ever started on it; a post-merge run of
  TestCheckCoverageReg008BurnDown passes clean (0 findings).
- T-1166 (strata: serve daemon now exercises real net/fs
  effects directly -- capability-boundary disposition needed) --
  test_serve_declares_zero_may_and_exercises_zero_effects is CORRECTLY
  catching a genuine T-1094/T-1096 capability-creep regression per its
  own T-0440 docstring; needs either a declared `may net.connect`/
  `may fs.write` on serve's design node (with justification) or a
  refactor to delegate through an existing may-bearing node -- a
  security-boundary call, not a test fix.
- T-1167 (exports: 15 public symbols across frob/serve/vet
  never wired into __init__.py or demoted private, T-0871 policy
  residue) -- each of 15 symbols needs its own public-vs-private
  judgment call across 3 packages' __init__.py files.

Full-suite verification (9 separate foreground runs across the session,
including 2 re-merges of a fast-moving main mid-ticket -- T-1134 then
07c0026f both landed while this ticket was in flight, each briefly
reintroducing a REG010/REG008 registry-drift pair via newly-synced gate
rules INV006 then NATIVE001; each was re-triaged the same way as the
original 25): `pytest -p no:cacheprovider -q` completes (exit 1, not a
timeout/hang) with exactly 2 failures remaining after the final merge,
both filed as tickets, neither in T-1006's own declared scope. This is
down from the ~118 historically named in the ticket and the 25 actually
re-measured at start. `git log --oneline -1 main` == this worktree's own
merge parent at every merge point; `git diff main --diff-filter=D
--stat` is empty at the final commit.

Final remaining 2 (both filed, security/policy judgment calls, not test
fixes):
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
  -- T-1166
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
  -- T-1167
(T-1168, the original REG008 filing, was dropped as moot once
main's concurrent work resolved it; T-1169 refiles the same
REG008 gap for the ONE new gate rule -- NATIVE001 -- this ticket's own
merge-chase surfaced live via --sync-gate-rules, and is not currently
red in the merged worktree state below.)

`frob sys sync-interface --check`: clean (no drift).
`frob ticket sweep T-1006`: clean, no malformed directives.
`frob check --ticket T-1006` (chunked, every gate group): 0 errors in
every group except the 5 pre-existing ARCH001/ARCH103 findings in files
this ticket never touched (check_runner.py, _close_cmd.py, doctor.py,
_setters.py -- confirmed via `git status --porcelain` these are not in
this ticket's diff) and the pre-existing ruff-check/ruff-format/CRLF
findings, also confirmed present on main and on files outside this
diff.

### Changed
```
 design/frob.strata                                 |    2 +-
 docs/design/registry/check-coverage.yaml           |   10 +-
 src/frob/app/exports_runner.py                     |   39 +-
 src/frob/deploy/_generate.py                       |   14 +-
 src/frob/tickets/_land.py                          |    8 +-
 tests/golden/frob_export_seccomp.json              |   14 +
 tests/system/test_system.py                        |    2 +
 tests/test_coverage.py                             |    9 +
 tests/test_makefile_lock_sync.py                   |   13 +-
 tests/test_registry_reconciliation_evasion.py      |   12 +-
 tests/test_registry_reconciliation_supply_chain.py |   12 +-
 tests/test_ticket_land.py                          |    4 +-
 tests/test_tickets_review.py                       |   17 +-
 tests/unit/test_app_runners_batch5.py              |   17 +-
 tests/unit/test_strata_tmlanguage.py               |   40 +-
 tickets.md                                         | 1162 +++++++++++++++++++-
 16 files changed, 1328 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_strict_flag_alone_does_not_gate_without_config` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_config_gate_alone_does_not_enforce_without_strict_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_matching_approve_review` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_abbreviated_review_commit` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPythonCoverageTargets::test_nothing_touched_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations` (pytest node id, verified passing when recorded)
- `tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump` (pytest node id, verified passing when recorded)
- `tests/system/test_system.py::test_sys_audit_hardened_waived_two_user_model_proved` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate.py::TestSorted::test_privileged_port_grants_cap_net_bind` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_exports.py::TestExportsFlags::test_json_output` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_exports.py::TestExportsFlags::test_json_modules_have_symbols` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 22 passed (from 22 evidence id(s))
- gates: 13 error(s), 735 warning(s), 446 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:155, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:170, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:212, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:271, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:299, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:46, PRE001@tickets/T-1006
