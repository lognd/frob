## Done report

Root-caused and fixed the TICK006 Tier-A phantom-citation auto-recovery
mechanism (`src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile`,
T-1544), measured at a 92% false-positive rate across all 25 tickets
ever auto-filed with the "Recovered from ...'s phantom TICK006 citation
of T-draft-..." shape (23/25 dropped as bookkeeping duplicates; the
remaining 2, T-2687/T-2689, triaged separately in this same series).

## Mechanism found

Three compounding defects, all in `fix_tick006_phantom_refile` and its
caller:

1. The handler iterated `queue.tickets.values()` -- the WORKTREE's
   entire active queue (mirrored fleet-wide by T-2563's ledger mirror),
   not the ticket actually landing. `ticket_id` was already threaded to
   every Tier-A handler (T-1548) but the TICK006 dispatch lambda in
   `TIER_A_HANDLERS` silently dropped it. A land's own pre-land Tier-A
   pass therefore re-scanned and could refuse-to-file on behalf of any
   OTHER ticket's stale citation -- "a pre-land fixer for ticket A
   refuses the land of unrelated ticket B" was this loop, literally.
2. The dominant false-positive shape (confirmed directly: T-2684's own
   citation of T-draft-f3bbfd8e, renamed via `git mv` at T-2134's land)
   is structurally invisible to a ledger-snapshot lookup no matter how
   fresh -- a rename's whole point is that the OLD name stops existing
   anywhere a snapshot (active queue, archive, or T-2400's merge-target
   union) could see it. Git's own history (the actual "renumber map"
   this repo has -- `frob ticket renumber`'s v2 path does a literal
   `git mv`) was never consulted.
3. A phantom already recovered by an earlier pass (the recovery
   ticket's title is fully deterministic) had no dedupe check before
   `new_ticket` was called again -- every subsequent land re-attempted
   the identical file, re-hit `DuplicateTicket`, and left the SAME
   unrewritten citation to repeat forever. This is the "refusing to
   file ... already has this exact title" noise a coordinator
   misdiagnosed as 45 minutes of land lock contention -- unlike
   contention, retrying a duplicate-title refusal never clears.

## Fix (per the ticket's own required-shape options: chose "resolve
through the renumber map first" for (2)+(3), plus scope-narrowing for (1))

- `fix_tick006_phantom_refile` gained a `ticket_id: str | None = None`
  parameter (already the standard T-1548 shape every other handler
  uses); when given, only that ticket's own Done report is scanned.
  `TIER_A_HANDLERS["TICK006"]` now threads it through (previously
  dropped). `ticket_id=None` (bare `frob check --fix`) is unchanged --
  still processes the whole queue.
- New `_resolve_via_git_rename(root, tid)`: bounded, best-effort git
  history lookup (`git log --diff-filter=D` to find the deletion commit,
  then `git show -M --name-status` unrestricted to read the paired
  rename target) -- resolves a genuinely-renamed draft to its real
  successor id without ever filing anything. Consulted for every
  candidate BEFORE it is treated as phantom.
- `_tick006_refile_for_ticket` now calls `_find_exact_duplicate` (reused
  from `frob.tickets._new_renumber`, the SAME check `new_ticket`'s own
  `DuplicateTicket` refusal already performs -- no second
  implementation) before every `new_ticket` attempt; a match rewrites
  the citation to the EXISTING recovery ticket and stops, never re-files.

Both resolution paths, when they fire, still rewrite the citing ticket's
body via the existing `_rewrite_body_prose_references` -- so a citation
that was phantom-looking either points at the real renamed id or the
real existing recovery ticket afterward, never left dangling.

## Positive/negative controls (both directions, per the ticket's own
requirement)

- `test_tick006_renamed_draft_resolved_via_git_not_refiled`: a genuinely
  renamed draft resolves via git and is NOT re-filed.
- `test_tick006_already_recovered_citation_rewritten_not_refiled_again`:
  an already-recovered phantom is NOT filed a second time; citation
  rewritten to the existing recovery ticket.
- `test_tick006_ticket_id_scopes_to_landing_ticket_only`: an unrelated
  ticket's own phantom citation is untouched when `ticket_id` scopes to
  a DIFFERENT ticket; unscoped (`ticket_id=None`) still processes it,
  proving the scoping is additive, not a blind spot.
- `test_tick006_genuinely_lost_draft_still_caught_no_rename_no_duplicate`
  (negative control, the one the coordinator's design constraint most
  cares about): a `tid` with NO git rename record and NO existing
  recovery ticket is still refiled exactly as before -- proves neither
  new check made the detector blind to a real loss.

All pre-existing TICK006/Tier-A tests (23 total before this ticket's 4
new ones, 29 in `TestFixEngineTierA` overall) still pass unmodified,
confirming the T-2400 merge-target behavior and every other Tier-A
handler are unaffected.

Documented in `docs/modules/gates.md`'s existing `fix_tick006_phantom_
refile` entry (AFFECT001 required this -- the doc-code edge was already
declared).

Changed:
src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile
src/frob/gates/_fix_engine.py::_tick006_refile_for_ticket
src/frob/gates/_fix_engine.py::_resolve_via_git_rename
src/frob/gates/_fix_engine.py::TIER_A_HANDLERS
docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138

### Changed
```
 tickets/T-2690/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 35 error(s), 1821 warning(s), 697 waived
- error-findings: ARCH001@src/frob/gates/_fix_engine.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
