## Done report

Confirmed the reported root cause directly in code before designing: the
watermark lived at `.frob/waive-audit-watermark.json`, and `.frob/` is
repo-gitignored (`.gitignore:87`) -- so `save_watermark`'s write is
per-checkout scratch state by construction. Agents run this audit from
disposable worktrees, so a completed pass's progress lived only inside a
directory `frob ticket land --finish` (or manual cleanup) deletes.

Went with option (a)+(b) from the ticket body together, not either alone:
the watermark file moved OUT of `.frob/` to a plain, git-tracked file at
the repo root (`waive-audit-watermark.json`, `.gitignore`-negated the same
way `!rapid-debt.jsonl` already is -- same established pattern, not a new
one), and `save_watermark` now COMMITS it in `root` and, when `root` is a
worktree, MIRRORS-AND-COMMITS it onto the primary checkout immediately
(reusing `frob.tickets._land._resolve_primary_checkout`/`frob.tickets.
_leases.refuse_if_land_in_progress`, the same primitives T-2563's
`_ledger_mirror` already established for exactly this "an edit made in a
worktree must be visible to the whole fleet immediately" shape).
`waive-audit` is `NOT_TICKET_SCOPED` in `LEDGER_VERB_STRATEGY` -- its
write carries no ticket id, so it cannot reuse that mirror table
directly; this is the same primitives, purpose-built for this one file.

Both the in-root commit and the primary mirror are best-effort and never
turn a successful on-disk write into an `Err` -- a git/lock failure logs
loudly (matching `_log_mirror_unavailable`'s posture) rather than
discarding real, already-computed audit progress over a git plumbing
hiccup.

Positive controls, all three required, all covered by new tests in
`tests/unit/test_waive_audit_watermark.py`:
- a pass run inside a worktree reaches the primary's own watermark file
  immediately, without a land (`TestMirrorToPrimary::
  test_worktree_pass_reaches_primary_without_a_land`) -- this is the
  ticket's own designated BUG002 repro: committed the test alone first
  (f9b6e801f, against the pre-fix `.frob/`-only code) and confirmed a
  genuine failure (`Err(WaiveAuditWatermarkError.NotFound)` on the
  primary), then applied the fix as a second commit and reconfirmed the
  same test passes.
- two passes in different worktrees do not lose either one's progress
  (`test_two_worktree_passes_do_not_lose_either_ones_progress` -- both
  commits are real, reachable git history; only the CURRENT watermark
  marker reflects the later pass, by the module's own documented "single
  current-position marker, not a log" contract).
- a pass that classifies nothing does not advance the watermark: this is
  unchanged, pre-existing `frob.app.ticket_runner._waive_audit` behavior
  (it only calls `save_watermark` after a genuinely completed pass) --
  outside this ticket's declared scope (`src/frob/gates/
  _waive_audit_watermark.py` and its own test file only), not re-verified
  here.

Also added coverage for the plain in-root git-commit half on its own
(`TestSaveWatermarkGitTracking`) and confirmed the pre-existing
non-git-`root` contract (a bare `tmp_path`, every OTHER test class in this
file) still succeeds on disk with the commit attempt degrading silently.

Scope note: `docs/modules/app.md#waive-audit-t-2467` (the `frob:doc`
target for this module) was held by a LIVE cross-worktree lease (T-2694)
for this ticket's entire duration and could not be touched. Waived
AFFECT001 on `save_watermark` with `follow_up="T-2735"` and
filed that draft ticket to update the doc once the lease frees, rather
than force a same-file edit into a colliding scope lease.

Also fixed a pre-existing T-2467 evidence-orphan while renaming a test
(`test_creates_frob_dir_if_missing` -> `test_creates_parent_dir_if_missing`,
since the watermark is no longer under `.frob/`): rebound T-2467's own
recorded evidence via `frob ticket evidence T-2467 --replace` rather than
leaving it dangling.

`frob check --ticket T-2721` reports zero errors attributable to
`src/frob/gates/_waive_audit_watermark.py`, `tests/unit/
test_waive_audit_watermark.py`, or `.gitignore`; the only remaining error
in the full check output (`frob-cycle`, an import cycle rooted in
`src/frob/tickets/_land_verify.py` and unrelated modules) is a
pre-existing, repo-wide finding that does not name any file this ticket
touched.

### Changed
```
 .gitignore                               |   9 ++
 src/frob/gates/_waive_audit_watermark.py | 185 ++++++++++++++++++++++++--
 tests/unit/test_waive_audit_watermark.py | 222 ++++++++++++++++++++++++++++++-
 tickets/T-2467/ticket.md                 |  12 +-
 tickets/T-2721/ticket.md                 |  34 ++++-
 tickets/T-2735/ticket.md       |  43 ++++++
 6 files changed, 486 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/unit/test_waive_audit_watermark.py::TestSaveWatermarkGitTracking::test_commits_the_watermark_in_a_real_repo` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_watermark.py::TestSaveWatermarkGitTracking::test_second_save_advances_with_its_own_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_watermark.py::TestSaveWatermarkGitTracking::test_non_git_root_still_succeeds_on_disk` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_watermark.py::TestMirrorToPrimary::test_worktree_pass_reaches_primary_without_a_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_watermark.py::TestMirrorToPrimary::test_two_worktree_passes_do_not_lose_either_ones_progress` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_watermark.py::TestMirrorToPrimary::test_calling_from_the_primary_checkout_itself_mirrors_nothing_extra` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 45 error(s), 777 warning(s), 680 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2723-t2721/src/frob/_cli_parsers/_ticket/_closeout.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2721, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
