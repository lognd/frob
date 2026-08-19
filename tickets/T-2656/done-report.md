## Done report

T-2622's extended WAIVE006 binding-phrase extraction (recognizing "T-####
holds/holding/under a live lease" phrasing, not just "pending T-####")
surfaced 13 genuinely stale waiver sites on this repo's own real tree.
For each: checked whether the deferred work the waiver named was
actually done, then fixed or reworded per T-2612's posture (expired
premise != dead finding).

Split: 8 sites where the deferred work was verifiably done -- waiver
removed outright:

- 6 SCOPE001/T-1279 sites (src/frob/gates/{__init__,
  _decisions_compliance,_doclink_docanchor,_sys,_tickets_gate,
  _todo_fmt}.py): the waiver's own substance was a ONE-TIME historical
  scope-registration blocker for a long-since-landed commit (T-1402).
  Verified with a real `frob check --only gates` pass (FROB_NO_GATE_CACHE=1)
  after stripping each waiver: SCOPE001 does not fire on any of these
  files today -- there is no live diff needing scope validation, so the
  waiver was protecting nothing.
- 2 AFFECT001/T-1235 sites (src/frob/gates/_coverage.py::load_coverage,
  ::write_coverage_lock): both cited T-1405 as the tracking ticket for
  the deferred docs/modules/gates.md update. T-1405 is DONE, and its
  documented behavior (unjoined-module enumeration log, zero-hit ratchet
  carve-out) is present in docs/modules/gates.md#public-api today
  (verified by reading the doc, not just trusting the closed ticket).
  Verified AFFECT001 does not fire on either symbol after removal.

5 sites where the work is genuinely still owed -- waiver reworded, not
removed, per the _waive.py top-of-file SCOPE001 precedent (past-tense
historical narration, current justification stated explicitly):

- 4 AFFECT001/T-1739 sites (src/frob/gates/_mutation_evidence.py::
  mutation_evidence_violations, src/frob/tickets/_evidence.py::
  replace_evidence, src/frob/tickets/_models.py::Ticket/TicketError):
  all four already cited T-2620 as the real follow-up ticket for the
  deferred docs/modules/tickets-landing.md/tickets-data-storage.md
  paragraph. Checked T-2620: still QUEUED, work genuinely not done.
  Reworded only the stale "T-1739's lease cleared" framing (the phrase
  WAIVE006's T-2622 extension was matching) to past tense, keeping T-2620
  as the live, open justification -- did NOT touch T-2620 itself or its
  scope.
- 1 AFFECT001/T-2076 site (src/frob/tickets/_draft_finalize.py::
  finalize_draft): the waiver's actual substance (T-1669's allocator_lock
  is an internal-only change, no public-contract doc update needed) was
  already sound and remains sound -- only the "T-2076 holds a live lease"
  framing was stale (T-2076 is DONE). Reworded to drop the live-lease
  claim while keeping the real justification (no observable contract
  change) explicit and current.

Confirmed via `FROB_NO_GATE_CACHE=1 frob check --only gates`: gate:WAIVE
went from FAIL (13 errors) to PASS (0 errors); no new SCOPE001/AFFECT001
finding appeared at any of the 8 removed-waiver sites.

Shrank tests/test_waive_gate.py::TestWaive006RealRepo's
`_WAIVE006_KNOWN_DEBT_T2622` allowlist to nothing and removed it entirely
(along with its helper `_waive006_unexpected` and the now-unused `re`
import), restoring the original bare-zero assertion -- per acceptance
[1]. TestWaive007RealRepo was already a bare zero and untouched.

Repro evidence: split the allowlist-removal test change into its own
commit (bff46d4e8) BEFORE re-applying the 11 waiver fixes, confirmed it
genuinely fails there (all 13 WAIVE006 findings present), then designated
it via `frob ticket evidence --check-repro --base-ref bff46d4e8
--repro-timeout-s 150` (the default 60s budget was too tight for this
real-repo-scanning test) -- FAILED_AT_PARENT.

### Changed
```
 src/frob/gates/__init__.py              | 11 ------
 src/frob/gates/_coverage.py             | 11 ------
 src/frob/gates/_decisions_compliance.py | 11 ------
 src/frob/gates/_doclink_docanchor.py    | 11 ------
 src/frob/gates/_mutation_evidence.py    |  6 ++--
 src/frob/gates/_sys.py                  | 11 ------
 src/frob/gates/_tickets_gate.py         | 11 ------
 src/frob/gates/_todo_fmt.py             | 11 ------
 src/frob/tickets/_draft_finalize.py     |  9 ++---
 src/frob/tickets/_evidence.py           |  7 ++--
 src/frob/tickets/_models.py             | 14 ++++----
 tests/test_waive_gate.py                | 63 +++++++--------------------------
 tickets/T-2656/ticket.md                |  9 +++--
 13 files changed, 39 insertions(+), 146 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive007RealRepo::test_zero_findings_on_real_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
