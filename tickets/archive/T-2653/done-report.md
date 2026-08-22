## Done report

-- batch 1 of N (COV001/DOC002)

This ticket tracks 42 identities across many unrelated rules (see
ticket body's TRACKING TICKET section for the full union and live-
reproduction status). This is NOT a full close -- landing the first
coherent, cleanly-fixable batch per the dispatch brief's instruction
not to clear all 34+ in one change.

### Cleared this batch (7 findings across 4 files, 2 identities)

- COV001 src/frob/app/fmt_runner.py -- `run` already had a real
  `frob:describes` reciprocal anchor sitting unused at
  docs/modules/app.md#runners (line 282); added the missing `frob:doc`
  directive to wire it.
- COV001 src/frob/strata/_multifile.py -- `SealedGrantSet.from_root_
  node`/`.grants`/`.widen` (3 symbols) already had a class-level
  `frob:describes` anchor at docs/strata/surface.md#fragments-t-2502;
  added the missing `frob:doc` directive to each of the 3 public
  methods (the class-level anchor does not cover its own methods
  individually).
- COV001 + DOC002 src/frob/gates/_refs_schema.py -- both `refs_schema_
  gate` and `REFS_ENTRYPOINT_KNOWN_KEYS` ALREADY carried a `frob:doc`
  directive, but it pointed at a STALE anchor slug
  (`#refschema001-t-2390-epic-child-t-draft-2654f0be`, a leftover from
  before T-2428 was a draft id) that no longer resolves against the
  heading's current text (`#refschema001-t-2390-epic-child-t-2428`).
  This single stale slug caused BOTH COV001 (unresolvable anchor reads
  as no-edge) AND DOC002 (broken-anchor gate) simultaneously for the
  same file -- fixing the slug clears both. DOC002's own error message
  even suggested the fix directly ("did you mean
  #refschema001-t-2390-epic-child-t-2428?").
- COV001 src/frob/gates/_rule_id_scan.py -- `scan_emitted_rule_ids` had
  no doc edge at all (genuinely missing, unlike its sibling `find_
  unregistered_rule_ids` etc. in the same file, which carry an
  established `T-1010`/`T-1937` waiver for the same doc-anchor scope-
  closure tension). Rather than repeat that waiver, added a real
  `frob:describes`/`frob:doc` pair: `scan_emitted_rule_ids` is the
  scan `find_unregistered_rule_ids` (already documented under
  `## GATERULE001`) directly calls, so that section is its natural
  home -- a real anchor, not another waiver, since the section already
  exists and already describes this exact code path.

### NOT touched this batch (deliberately left for later batches or
### other tickets)

- SELFAUDIT001/design -- excluded from this ticket's scope entirely
  (T-2666's active lease on design/frob.strata; that ticket already
  covers the SYS107 half of this finding).
- COV003 (6 old ticket dirs), COV004 (2), DOC001/005/008 +
  DOCENUM001 (gates.md, cli.md, release.md), DRIFT001 (3 files),
  PERF002-004 (6 files), TICK003/004, SEC004/SEC110/PII012/TEST001/
  RENDER001/WIRE002/WIRE003 -- separate rule families, separate
  investigation each, left for a follow-up batch in this same ticket.
- F401 __init__.py, LANG004 _support.py -- already confirmed NOT LIVE
  at triage time; left as-is pending a fresh re-check before removing
  them from the tracked list.

### Both-direction verification (not a re-break/restore control --
### this batch is purely additive doc-anchor wiring with zero behavior
### change, so there is no meaningful "break it again" step; verified
### instead by re-running the exact gate before/after)

- Before: `frob check --only coverage --only doclink --only docanchor
  --json` (on the pre-fix tree, captured earlier in this triage as
  /tmp/full_check.json) showed COV001 ERROR for all 4 files and DOC002
  ERROR for _refs_schema.py (both lines).
- After: identical scoped check shows ZERO COV001/DOC002 findings for
  any of the 4 files -- only the PRE-EXISTING, unrelated COV007
  warnings on _multifile.py's private helpers (unchanged count, 7
  before and after) and the already-waived note-level COV001 entries
  on _rule_id_scan.py's OTHER symbols (unchanged, not touched this
  batch).
- Existing test suites for all 3 touched modules re-run green:
  tests/unit/test_refs_schema.py + tests/gates/test_rule_id_scan_
  branches.py (26/26), tests/unit/strata/test_fragments.py (19/19,
  covers SealedGrantSet), tests/unit/strata/test_multifile.py (6/6,
  unaffected sibling suite in the same module).

### Evidence

- tests/unit/test_refs_schema.py::TestRefsSchemaGate.test_must_now_fire_reports_the_undeclared_key
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_missing_scanned_base_directory_is_skipped_not_an_error
- tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_widen_on_declared_atom_still_works

### Count against the 42

5 identities of 42 cleared this batch, matching the ticket's own
(rule, file) counting convention: COV001 fmt_runner.py, COV001
_refs_schema.py, COV001 _rule_id_scan.py, COV001 _multifile.py, DOC002
_refs_schema.py. Spans 4 files and 7 individual findings (3 symbols in
_multifile.py collapse to 1 identity). 37 identities remain tracked in
this ticket for follow-up batches.

### Changed
```
 docs/modules/gates.md           | 1 +
 src/frob/app/fmt_runner.py      | 1 +
 src/frob/gates/_refs_schema.py  | 4 ++--
 src/frob/gates/_rule_id_scan.py | 1 +
 src/frob/strata/_multifile.py   | 3 +++
 tickets/T-2591/ticket.md        | 9 +++++++--
 tickets/T-2592/ticket.md        | 9 +++++++--
 tickets/T-2594/ticket.md        | 9 +++++++--
 tickets/T-2597/ticket.md        | 9 +++++++--
 tickets/T-2643/ticket.md        | 7 +++++--
 10 files changed, 41 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_missing_scanned_base_directory_is_skipped_not_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_declared_atom_still_works` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 41 error(s), 1580 warning(s), 697 waived
- error-findings: AFFECT001@src/frob/strata/_multifile.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2653, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
