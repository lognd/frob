## Done report

Migrated the 6 land-pipeline ProfileName branches T-1696's re-verification
(`frob explore xref ProfileName`) found -- the 5 T-2360 measured plus a
6th (`_land_cmd.py:4607`'s `_apply_backpressure` soft-warning gate,
T-2290) not enumerated by T-2360's original sweep -- to read the existing
`LandProfileSettings`/`settings_for_profile` resolver
(`frob.verify._backpressure`, already built and tested by T-2360) instead
of comparing `effective_profile`'s result to `ProfileName.RAPID` inline.

Seams migrated (before/after identical per-profile, per
`TestSettingsForProfile` and the touched-set test run below):

1. `frob.tickets._land._land_is_rapid` (evidence-scope-unbound debt) --
   now reads `settings_for_profile(...).evidence_scope_unbound_is_debt`.
2. `frob.tickets._land._mutation_evidence_sync_decision` (TEST016 skip)
   -- now reads `settings_for_profile(...).mutation_evidence_required`.
3. `frob.app.ticket_runner._land_cmd`'s pre-commit-sweep skip -- now
   reads `settings_for_profile(...).pre_commit_sweep_enabled`.
4. `frob.tickets._evidence._is_rapid` -- now reads `settings_for_profile
   (...).evidence_scope_unbound_is_debt`.
5. `frob.app.ticket_runner._close_cmd._own_obligations_rel_bump_dirty`
   (REL001 preflight skip) -- now reads `settings_for_profile(...).
   rel001_preflight_enabled`.
6. `frob.app.ticket_runner._land_cmd._apply_backpressure`'s rapid soft
   warning gate (T-2290) -- a 6th branch this ticket's own
   re-verification found, not in T-2360's original 5. Added a new
   `LandProfileSettings.rapid_soft_warning_enabled` field (True only for
   rapid, matching the prior `is ProfileName.RAPID` behaviour exactly)
   rather than leaving this one branch uncollapsed.

No behaviour changed at any of the 6 sites: each substitution reads the
identical boolean the prior inline comparison computed, verified by the
existing per-seam suites (`test_land_cmd_backpressure.py`,
`test_close_rel001_bump.py`, `test_profile.py`,
`tests/unit/verify/test_backpressure.py`) passing unmodified plus the
updated `TestSettingsForProfile` covering the new field.

Docs: `docs/modules/tickets-verify-sweep.md`'s "Land profile settings
(T-2360)" section updated in the same change -- records the field count
change (4 -> 5), documents the 6th migrated seam, and replaces the prior
"disclosed scope cut: no call site migrated yet" note with the actual
migration.

Re-verification: re-ran `frob explore xref ProfileName` in the worktree
before starting (12 days of drain had passed since the blocking
investigation) -- found the identical 6 sites, nothing new.

Unscoped re-measurement: `frob check --ticket T-1696 --only scope --only
affect_drift --only coverage --only prework` -- gate:SCOPE and
gate:AFFECT both clean (AFFECT001 on `LandProfileSettings` cleared by the
doc update above; SCOPE001 cleared by adding
`tests/unit/verify/test_backpressure.py` to declared scope, the test
file T-2360 already owned and this ticket extended). gate:COV/gate:DRIFT
errors in that same run are pre-existing repo-wide baseline noise
(unrelated files -- `serve/`, `strata/`, `vet/`, etc.) per the
`--ticket` scope-note; none touch this ticket's changed files.

Deliberately NOT done in this leaf (disclosed, not silently dropped):
this migrates all 6 measured ProfileName branches, but does not audit
every OTHER file in the repo for a stray ProfileName comparison outside
the land pipeline (out of this ticket's own acceptance, which is scoped
to "land-pipeline module" branches) -- if one exists, that is separate
follow-up work, not something this re-verification pass claims to have
swept.

Filed separately: none -- no out-of-scope defect found during this pass;
the ticket's own scope (as widened by the prior implementer) was
sufficient once one additional field (`rapid_soft_warning_enabled`) was
added to the existing settings model to close the 6th branch.

### Changed
```
 tickets/T-1696/ticket.md | 28 +++++++++++++++++++++++++---
 1 file changed, 25 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_fortress_matches_current_branch_logic` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_standard_matches_current_branch_logic` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_rapid_matches_current_branch_logic` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_tripped_blocks_then_proceeds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-1696, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
