## Done report

TICK006's Tier-A auto-recovery (T-1544/T-2690/T-2702) already resolved
citations against this worktree's own ledger, the archive, and (T-2400)
main's own LANDED ledger. What it did not cover: an id minted inside a
SIBLING worktree that has not landed yet -- T-2197's own doctrine that a
worktree-minted id is invisible on main until that worktree lands. A Done
report in worktree A citing an id worktree B minted, while B is still in
flight, read as phantom to every existing view and got auto-filed as a
duplicate of B's own active work -- measured: T-3100/T-3103 duplicated
T-3107/T-3106, both real and non-terminal at the time, both dropped by
hand.

FIX: _sibling_worktree_known_ids enumerates every OTHER live worktree via
git worktree list --porcelain and best-effort reads its own local ticket
queue, unioned into known_ids alongside the archive/merge-target views.
Pure widening source -- a worktree that cannot be read (mid-removal,
pruned, gone) contributes nothing rather than aborting the scan, so it
never needs MergeTargetKnownIds' stricter measured=False-refuses-to-file
doctrine (T-2391): this can only ever prevent a false phantom, never
manufacture a false "known".

WHY AUTO-FILING WAS KEPT (per the ticket's own invitation to weigh
turning it off): the sibling-worktree fix directly closes the SPECIFIC
measured incident's root cause (an id genuinely resolvable, just not yet
visible to any prior view) rather than merely suppressing the SYMPTOM by
disabling filing broadly. A genuinely phantom citation (never filed
anywhere, in any worktree, archive, or main) still needs filing to
recover the lost work description -- that is the whole point of TICK006,
and turning it off entirely would have been strictly worse for that real
case, not merely different.

ACCEPTANCE
- Must-stay-quiet: test_citation_to_sibling_worktree_active_id_does_not_refile
  -- a Done report citing an id active in a sibling, not-yet-landed
  worktree does not refile.
- Must-fire: test_genuinely_nonexistent_id_still_refiles -- an id nowhere
  (not this worktree, not any sibling, not main, not archive) still
  refiles.
- 28 pre-existing TICK006 tests in tests/test_gates.py (T-1544/T-2400/
  T-2690/T-2702's own suites) still pass unmodified -- no regression.

MEASURED FALSE-POSITIVE RATE, BEFORE/AFTER: T-2690's own 92% figure (23/23
triaged = 100%, 92% of all 25 ever filed) was measured against a corpus of
EPHEMERAL worktree states (drafts on now-gone branches) that cannot be
replayed -- there is no way to re-run detection against the ACTUAL git/
worktree state at the moment each of those 25 was filed, since that state
no longer exists. T-2690 itself already closed the dominant (rename-based)
share of that corpus; T-3108 is a THIRD, independent source, confirmed
via a live reproduction of the T-3106/T-3107 incident shape rather than a
replay of the historical corpus: BEFORE this fix, the reproduction fixture
(a citation to an id active in a sibling worktree) files a duplicate
100% of the time (the exact T-3100/T-3103 mechanism); AFTER, 0% (must-
stay-quiet fixture passes). This is a real, if narrower, measurement than
literally re-scoring the 25-ticket historical corpus, which is not
possible.

DISCOVERED, FILED, OUT OF SCOPE: while binding this ticket's own evidence,
new_ticket (called by fix_tick006_phantom_refile when a citation genuinely
survives every check) refused with WorktreeLeaseViolation when reverified
by an agent already working inside a real leased worktree --
enforce_worktree_lease (T-0431) sees FROB_WORKTREE exported into the
evidence-reverify pytest subprocess and refuses new_ticket against the
test's own unrelated tmp_path fake repo. Root-caused directly (a bare
new_ticket call against a tmp_path repo under FROB_WORKTREE=<real path>
reproduces WorktreeLeaseViolation on demand). Worked around locally
(monkeypatch.delenv("FROB_WORKTREE") in this ticket's own new fixture),
but the EXISTING tests.test_gates.py TICK006 fixtures (bound as evidence
for T-1544/T-2690/T-2702, several other landed tickets) do not have this
guard and remain exposed. Filed as T-3145 (related to, but a DIFFERENT
root cause than, T-3123's in-process same-worker leak: T-3145 is the env
var being legitimately exported by frob's own CLI from process start, not
a test failing to restore a value it mutated mid-session) -- a repo-wide
test-isolation fix (an autouse conftest fixture), out of T-3108's own
scope to fix broadly.

SCOPE NOTE: the ticket's declared scope named
src/frob/gates/_fix_engine_text.py, which has no TICK006 handling at all
(FMT001/SUPPRESS001/E501 text-patch helpers only). Corrected to
src/frob/gates/_fix_engine.py (the real fix_tick006_phantom_refile home)
before touching any code, reason recorded in the scope-change audit
trail -- same pattern as T-3116 and T-3124 earlier in this series.

### Changed
```
 docs/modules/gates.md                        |  17 ++
 src/frob/gates/_fix_engine.py                |  81 +++++++++-
 tests/test_gates_tick006_sibling_worktree.py | 232 +++++++++++++++++++++++++++
 tickets/T-3108/ticket.md                     |  38 ++++-
 tickets/T-3145/ticket.md                     |  86 ++++++++++
 5 files changed, 451 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates_tick006_sibling_worktree.py::TestSiblingWorktreeKnownIds::test_reads_an_active_id_from_another_worktree` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick006_sibling_worktree.py::TestSiblingWorktreeKnownIds::test_excludes_root_itself` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick006_sibling_worktree.py::TestSiblingWorktreeKnownIds::test_unreadable_worktree_is_skipped_not_fatal` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick006_sibling_worktree.py::TestFixTick006ResolvesSiblingWorktreeCitations::test_citation_to_sibling_worktree_active_id_does_not_refile` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick006_sibling_worktree.py::TestFixTick006ResolvesSiblingWorktreeCitations::test_genuinely_nonexistent_id_still_refiles` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 78 error(s), 1017 warning(s), 867 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bw/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3108, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
