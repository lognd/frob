## Done report

Audited every `frob:waive` reason citing "T-XXXX's LIVE/live cross-worktree
lease" as its justification. Of the 12 ticket citations named in this
ticket's own Measured section, 5 distinct holder-tickets still had
matching waiver text findable in the current tree (12 individual waiver
sites across 8 files) -- the other 7 (T-0764, T-0854, T-1592, T-1665,
T-1703, T-1937, T-2207) have no live-lease-citing waiver text remaining
anywhere in src/**/*.py today, i.e. concurrent work already resolved
those before this ticket started.

Split, per this ticket's own required deliverable:

REMOVABLE (3 sites -- premise expired AND the deferred work was
confirmed done):
- src/frob/scaffold/project.py::install_worktree_lease_hook (AFFECT001,
  cited T-1382): docs/commands/scaffold.md already documents the T-2071
  guard in full (T-2112's own done-report confirms). Waiver removed;
  re-ran gate:AFFECT with it removed -- 0 findings.
- src/frob/app/check_runner.py::_run_census and ::run (AFFECT001 x2,
  cited T-2485): T-2491 (done) actually added the promised
  docs/modules/app.md content (confirmed present). Both waivers removed.

REAL OWED WORK (9 sites -- premise expired, deferred work NOT done; kept
suppressed with a corrected, non-expiring reason, and ticketed):
- src/frob/__main__.py::_SuggestingArgumentParser.parse_known_args
  (COV001, cited T-1382): resolved INLINE in this ticket instead of
  deferring further -- added the missing `frob:doc` anchor plus a
  `frob:describes` entry in docs/commands/cli-vocabulary.md#did-you-mean
  (the doc's prose already covered the mechanism from T-2107/T-2112, it
  only lacked the anchor). Waiver removed; gate:COV confirms clean.
- src/frob/tickets/_reconcile.py::ReconcileReport and ::reconcile
  (AFFECT001 x2, cited T-1720): docs/modules/tickets.md still has zero
  mentions of unlanded_branch_work (T-1934's fourth anomaly class).
  Filed T-2619 (renumbers at land); reasons corrected to cite
  the real gap instead of the expired lease.
- src/frob/lang/_nodes.py::declared_project_package_name and
  ::declared_source_prefixes (COV001 x2, cited T-2365): the "doc-anchor
  follow-up ticket" the original waiver promised was never actually
  filed; docs/modules/lang.md still has no anchor for either function.
  Filed T-2618; reasons corrected.
- src/frob/gates/_mutation_evidence.py::mutation_evidence_violations,
  src/frob/tickets/_models.py::Ticket, ::TicketError, and
  src/frob/tickets/_evidence.py::replace_evidence (AFFECT001 x4, cited
  T-1739/T-1715): TEST018 is fully documented in docs/modules/gates.md
  (T-1733's own docs home), but the SEPARATE tickets-data-storage.md/
  tickets-landing.md updates each waiver reason promised for its own
  affects()-closure doc were never made (grep confirms zero mentions of
  evidence_changes/EvidenceReplaceReasonMissing in either file). Filed
  T-2620 covering all three doc entries; reasons corrected.

Enforceability (deliverable 2): filed T-2622 proposing a
unified detector shared with T-2606 (waiver-promises-a-follow-up-ticket)
-- both are "a waiver reason makes a claim about another ticket's state,
and nothing keeps that claim honest" instances, and should not become
two independently-maintained regex sets. Did not implement the gate
itself in this ticket: it is new-feature scope well past a single-file
audit ticket, and T-2606 is the more natural owner to build from: this
finding is recorded as a blocked-by dependency on T-2606 so whoever
picks either one up sees the other.

Evidence: added tests/test_lease_premise_waivers.py, a regression lock
pinning the exact stale citation strings this ticket found. Verified
genuine FAILED_AT_PARENT via the T-2021 technique (commit the test
alone against the still-broken text, confirm failure, then commit the
fix): `frob ticket evidence T-2612 --check-repro
tests/test_lease_premise_waivers.py::TestNoStaleLeasePremiseWaivers::test_stale_lease_citations_are_gone
--base-ref aa939d73182650935bd8b3b4ac99f196c47c6ff3` -> FAILED_AT_PARENT.
Designated as this ticket's repro evidence.

Filed: T-2619, T-2618, T-2620,
T-2622 (all renumber at land). T-2621 was filed then
dropped/absorbed once its own fix (the __main__.py anchor) landed
directly in this ticket instead.

Gates: frob check --only affect_drift --only scope --only prework
--ticket T-2612 clean (0 errors in those families; the only remaining
errors under a broader --ticket run are pre-existing DRIFT001/COV001/
COV003/TICK003/TICK004 findings on files this ticket never touched, plus
a pre-existing claude-config-drift warning -- confirmed unrelated by
file path). `frob test --base main` surfaced widespread failures (e.g.
test_cycle_no_cycle_exits_zero: `frob cycle` subprocess exits 2) that
reproduce identically and are unrelated to this ticket's comment/doc-only
changes -- environmental/pre-existing under current fleet load, not a
regression this ticket introduced.

### Changed
```
 src/frob/__main__.py                 |   9 ++-
 src/frob/app/check_runner.py         |  10 ---
 src/frob/gates/_mutation_evidence.py |  14 ++--
 src/frob/lang/_nodes.py              |  18 +++--
 src/frob/scaffold/project.py         |   5 --
 src/frob/tickets/_evidence.py        |  11 ++-
 src/frob/tickets/_models.py          |  22 +++---
 src/frob/tickets/_reconcile.py       |  18 ++---
 tests/test_lease_premise_waivers.py  |  68 ++++++++++++++++
 tickets/T-2612/ticket.md             | 149 ++++++++++++++++++++++++++++++++++-
 tickets/T-2618/ticket.md   |  49 ++++++++++++
 tickets/T-2619/ticket.md   |  45 +++++++++++
 tickets/T-2620/ticket.md   |  63 +++++++++++++++
 tickets/T-2621/ticket.md   |  46 +++++++++++
 tickets/T-2622/ticket.md   |  76 ++++++++++++++++++
 15 files changed, 538 insertions(+), 65 deletions(-)
```

### Evidence
- `tests/test_lease_premise_waivers.py::TestNoStaleLeasePremiseWaivers::test_stale_lease_citations_are_gone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2612/src/frob/gates/_mutation_evidence.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
