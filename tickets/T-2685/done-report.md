## Done report

-- batch 3 (DOC008 + DRIFT001 re-verify, plus COV003
## dispositions on 4 closed tickets)

Continuation ticket of T-2674 (which closed on landing its own
batch). Clears the 2 re-verify items flagged in this ticket's own body
plus disposes of the 6-item COV003 group (filed as its own ticket
during triage, T-2686, since COV003 needed per-ticket
judgment rather than a mechanical fix -- see that ticket's own body
and the 4 closed-ticket body notes/evidence rebinds below for the full
record).

### Cleared this batch (against the 35 tracked in this ticket)

- DOC008 docs/modules/gates.md -- a second, previously-missed stale
  anchor slug reference: docs/modules/gates.md's own REFSCHEMA001
  table row cross-linked `#refschema001-t-2390-epic-child-t-draft-2654f0be`
  internally (same stale slug T-2653's batch 1 already fixed in
  _refs_schema.py's frob:doc directives, but this doc-internal
  cross-reference was missed then). Fixed to the current real slug.
- DRIFT001 src/frob/app/ticket_runner/_verify.py::_parse_error_findings_from_json
  -- caused by T-2668's own land (landed mid-session, fixed the
  gate-summary parse regex) moving this function's body digest.
  Re-verified the function's docstring ("THREE independent ways this
  returns None") is still accurate against the live implementation,
  ran `frob ack` naming T-2668 specifically in the reason.

### COV003 dispositions (T-2686, coordinator-approved before
### any evidence write -- see that ticket for the full per-ticket
### investigation)

- T-2344, T-2348: REBOUND via `frob ticket evidence --replace`. Both
  cited the identical node id, `test_every_known_gates_module_module_
  stays_clean`, traced through a real 2-hop rename chain (T-2466
  widened scope + renamed, T-2469 fixed the resulting backlog +
  renamed again) to `test_supplychain_lexcheck001_backlog_is_empty_
  t2469`, confirmed live in the current tree and the underlying
  LEXCHECK001 gate clean repo-wide.
- T-2365, T-1688: recorded OBSOLETE-SUPERSEDED as body notes (no
  evidence-removal verb exists; a rebind was explicitly avoided since
  the successor tests in both cases assert the OPPOSITE of the
  original ticket's claim -- T-2365's disclosed TypeScript
  import_graph gap was closed by T-2408; T-1688's advance-only-on-
  green watermark contract was deliberately replaced by T-2324's
  owned-finding-advances redesign). Both notes name the superseding
  ticket explicitly.
- T-1397, T-1526: NO ACTION -- both already carry their own
  "DELIBERATELY LEFT UNREPOINTED" disclosure from 2026-08-18, predating
  this session, in `tickets/archive/T-1397/ticket.md` and
  `tickets/archive/T-1526/ticket.md`.

### Incidental fix: real ledger corruption found and repaired

`frob ticket body T-1688 --append-file` (used for the OBSOLETE note
above) wrote its update to a fresh `tickets/T-1688/` instead of
updating the existing `tickets/archive/T-1688/ticket.md` in place,
leaving BOTH present with the same id -- `frob ticket show T-1688`
failed outright with `DuplicateId`. Confirmed the archive copy was
stale (missing the just-recorded `body_changes` entry; `done-report.md`
byte-identical between both copies) and removed it, keeping the
updated active-location copy as canonical. `frob ticket show T-1688`
resolves clean afterward; confirmed no other id is duplicated across
`tickets/` and `tickets/archive/` repo-wide (`comm -12` on the sorted
id lists, empty). Filed T-draft-be1e79b5 for the underlying tool bug
(coordinator does not need to take it).

### Verification

Before: `frob check --only docanchor --only drift --json` showed both
DOC008/gates.md and DRIFT001/_verify.py as ERROR (captured in this
session's earlier full unscoped runs).
After: identical scoped check shows ZERO findings for either.

`frob:no-behavior-change` (inherited from this ticket's body) covers
the DOC008/DRIFT001 fixes (doc-anchor + digest-ack only). The COV003
dispositions are ledger/evidence bookkeeping on already-closed
tickets, not this ticket's own behavior claim.

### Evidence

- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001.test_supplychain_lexcheck001_backlog_is_empty_t2469
  (also the rebound evidence for T-2344/T-2348, verified passing
  directly: `pytest tests/unit/gates/test_lexical_selfcheck.py` 8/8)

### Count against the 35

2 of the 35 tracked identities cleared this batch (DOC008, DRIFT001).
33 remain, to be handed to a fresh agent per the coordinator's context-
budget instruction -- COV003 (6) is now fully disposed and drops out
of the remaining count entirely (not "cleared" in the COV001-style
sense, but resolved: 2 rebound + 2 recorded obsolete + 2 already
accepted, none left open). Remaining groups untouched this session:
ARCH103 (2), DOC002/DOC006 (2), PERF002-004 (6), TICK003/004 (2),
SEC004/SEC110x3/PII012/TEST001/RENDER001/WIRE002/WIRE003 (8),
F401/LANG004 re-verify (2), SELFAUDIT001/design (1, excluded pending
T-2666).

### Changed
```
 docs/modules/gates.md                   |   2 +-
 rapid-debt.jsonl                        |   3 +
 tickets/T-2344/ticket.md                |  20 ++++-
 tickets/T-2348/ticket.md                |  20 ++++-
 tickets/T-2686/ticket.md      | 108 +++++++++++++++++++++++++++
 tickets/T-2685/done-report.md | 119 ++++++++++++++++++++++++++++++
 tickets/T-2685/ticket.md      | 125 ++++++++++++++++++++++++++++++++
 tickets/T-2688/ticket.md      |  79 ++++++++++++++++++++
 tickets/T-2689/ticket.md      |  36 +++++++++
 9 files changed, 509 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_supplychain_lexcheck001_backlog_is_empty_t2469` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 35 error(s), 1585 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2684/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
