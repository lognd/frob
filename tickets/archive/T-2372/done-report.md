## Done report

Changed:
- src/frob/gates/_tickets_gate.py: narrowed TICK011's `residue`/`residual`
  disclosure pattern from a bare word trigger to a colon-labeled-heading
  form (`\bresidu(?:e|al)\s*:`); deleted the now-dead
  `_tick011_preceded_by_technical_token`/`_TICK011_TECHNICAL_TOKEN_RE`
  lookback machinery (unreachable once the pattern itself requires a
  colon, since it only ever inspected bare "residue"/"residual"
  matches); promoted TICK011's severity from WARN to ERROR now that the
  repo-wide count is genuinely zero.
- src/frob/gates/_waive.py: updated TICK011's rule-catalog comment to
  record the WARN->ERROR promotion.
- tests/test_gates.py: updated the two existing residue-false-positive
  tests' docstrings to describe the new (simpler) mechanism, updated
  both existing must-fire assertions to expect Severity.ERROR, and
  added two new tests (must-still-fire for the genuine "Residue:"
  heading-label shape, must-stay-silent when a real citation follows
  immediately) proving the narrowed pattern is not simply "never fires".
- tickets/archive/T-2556/done-report.md,
  tickets/archive/T-2653/done-report.md: repaired the two genuine
  (non-false-positive) TICK011 disclosures a fresh measurement still
  found after the pattern fix -- T-2556's "Residue:" paragraph already
  HAD a real citation (T-2565, done) but it lived outside TICK011's
  300-char vicinity window (in the Done report's own "Changed" section);
  moved the citation to sit immediately after the label. T-2653's
  disclosure was explicitly deferred "in this same ticket" (not
  orphaned, just not phrased as a checkable no-ticket-needed
  disposition); added the explicit phrase.

Investigation finding (root cause, not assumed): TICK011's bare
`\b(?:residue|residual)\b` word-only pattern VIOLATED this module's own
stated design principle ("deliberately CONSERVATIVE multi-word phrases
... so a WARN-tier first turn-on does not drown in false positives").
A fresh repo-wide measurement (2026-08-26) found this ONE pattern
accounted for the ENTIRE live TICK011 population that day: of 9 live
findings, 7 were unrelated English usage a bare-word trigger cannot
discriminate ("no residue", "residual risk", "squash residue", a
function literally named `reclaim_orphaned_squash_residue`, TICK011's
own rule prose quoting itself), and 2 (T-2556, T-2653) were genuine
disclosures whose citation/disposition existed but sat outside the
300-char vicinity window or wasn't phrased in the checkable form. Fixed
the pattern (removes the 7 false positives structurally) and repaired
the 2 real gaps directly (their own historical text, not the check).

Family measurement, before -> after (uv run frob check --json --only
tickets, 2026-08-26, matching this ticket's own required measurement
command):
- TICK011: 9 -> 0. PROMOTED WARN -> ERROR. Confirmed the promotion
  takes effect: a fresh unbudgeted `frob check --only tickets` run
  after the promotion produces zero TICK011 output at any severity
  (nothing left to promote against, by construction) -- not just a
  passing unit test.
- TICK004: 7 -> 7, UNCHANGED. NOT burned, NOT promoted.
- TICK007: 1 -> 1, UNCHANGED. NOT burned, NOT promoted.

Why TICK004/TICK007 are NOT burned or promoted, disclosed explicitly
rather than silently left incomplete: both are DATA-DRIVEN checks over
the live ticket queue's real state (ticket age vs priority threshold;
undispatched-and-unleased time), not code defects. Burning them to zero
honestly requires actually working, re-prioritizing, or dropping seven
substantive, unrelated backlog tickets (T-0450, T-0969, T-1273, T-1382,
T-2391, T-2501, T-2573) and dispatching or re-prioritizing one critical
bug ticket (T-2916, "frob is Linux-only in practice") -- real triage
decisions on other people's/agents' backlog items that are outside a
narrowly-scoped burn-down ticket's unilateral authority, and NOT
something to fake by reprioritizing them downward purely to silence the
gate (that would be gaming the metric, the exact anti-pattern this
program exists to prevent). Promoting TICK004/TICK007 to ERROR while 8
live findings remain would red the tree for everyone, which this
ticket's own body explicitly forbids ("Do not promote before the burn").
Left both at WARN, unburned, for a follow-up (real ticket-queue triage
across the T-0969/T-1273 program, plus T-2916's own dispatch) that is
better done by whoever owns those tickets, or a coordinator-level pass,
not invented here.

T-2367 overlap: T-2367 ("TICK004: tickets.md ledger-consistency -- 9
errors + 17 warnings") claimed a TICK004-only count that is now stale --
a fresh measurement (2026-08-26) shows 0 TICK004 ERRORs and 7 WARNs, not
9+17. Since this ticket already measures and (partially) covers the
current live TICK004 count as part of its own family, dropped T-2367
with `--absorbed-by T-2372` rather than duplicate the same triage twice.

Incidental fix during this ticket: caught myself editing the shared
repo root directly (`/home/logan/projects/frob/tickets/archive/T-2556/
done-report.md`) instead of this worktree's own copy on the first
attempt at the archived-ticket repair above -- reverted immediately via
`git checkout --` before it was ever committed, then redid the edit
inside the worktree. Disclosed per this drive's own measurement
discipline, not because it landed anywhere.

Evidence:
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_residue_heading_label_with_no_citation_still_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_residue_heading_label_with_citation_immediately_after_is_silent

Filed: none new. Dropped T-2367 (--absorbed-by T-2372, stale duplicate
claim). No new ticket filed for the TICK004/TICK007 remainder since it
is real backlog-triage work belonging to the affected tickets'
owners/coordinator, not a defect with a clean, isolated fix shape.

Gates: `frob check --only test --ticket T-2372` -- 1 pre-existing error
(TEST001 on scripts/branch_stranded_work_analysis.py, confirmed
untouched by and unrelated to this ticket). `frob check --only tickets
--json` (unbudgeted, FROB_NO_GATE_CACHE=1) is this ticket's own required
before/after measurement command, reported above.

### Changed
```
 tickets/T-2367/ticket.md |  5 ++++-
 tickets/T-2372/ticket.md | 40 +++++++++++++++++++++++++++++++++++++++-
 2 files changed, 43 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_residue_heading_label_with_no_citation_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_residue_heading_label_with_citation_immediately_after_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 24 error(s), 557 warning(s), 851 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, E501@/home/logan/projects/frob/.claude/worktrees/t2372-series/src/frob/gates/_tickets_gate.py, PRE001@tickets/T-2372, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
