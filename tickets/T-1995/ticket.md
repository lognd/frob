---
id: T-1995
title: 'frob ticket new does not surface existing or archived coverage: 7 tickets
  filed and dropped this session, several costing a dispatch'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/config.py
- tests/unit/test_ticket_new_related.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_new.py
  reason: src/frob/tickets/_new.py does not exist -- the interactive frob ticket new
    CLI dispatch lives at src/frob/app/ticket_runner/_new.py; the library new_ticket()
    in src/frob/tickets/_new_renumber.py is shared by non-interactive auto-filing
    callers (rapid-sweep regression filing, mutation-sweep, testing stability, sys_runner,
    fleet) that must never block on an acknowledgement flag, so the surface-and-require-ack
    fix belongs at the interactive CLI layer only
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: src/frob/tickets/_new.py does not exist -- the interactive frob ticket new
    CLI dispatch lives at src/frob/app/ticket_runner/_new.py; the library new_ticket()
    in src/frob/tickets/_new_renumber.py is shared by non-interactive auto-filing
    callers (rapid-sweep regression filing, mutation-sweep, testing stability, sys_runner,
    fleet) that must never block on an acknowledgement flag, so the surface-and-require-ack
    fix belongs at the interactive CLI layer only
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: surfacing related tickets needs a new --ack-related CLI flag; wiring it
    requires the ticket-new argparse subparser and its AppConfig field declaration
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/config.py
  reason: surfacing related tickets needs a new --ack-related CLI flag; wiring it
    requires the ticket-new argparse subparser and its AppConfig field declaration
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_ticket_new_related.py
  reason: regression test for the related-ticket surfacing check, CLI-dispatch style
    matching test_ticket_runner_designate_repro.py
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_no_match_for_a_genuinely_distinct_title
- tests/unit/test_ticket_new_related.py::TestRefusesUnacknowledgedRelatedTicket::test_close_match_against_an_archived_ticket_refuses
- tests/unit/test_ticket_new_related.py::TestRefusesUnacknowledgedRelatedTicket::test_ack_related_proceeds_despite_the_match
- tests/unit/test_ticket_new_related.py::TestNovelTicketFilesWithoutFriction::test_novel_title_needs_no_ack
- tests/unit/test_ticket_new_related.py::TestSuccessorTicketAfterAcknowledgement::test_successor_of_an_open_ticket_files_after_ack
- tests/unit/test_ticket_new_related.py::TestPossibleEnforcementSymbolsCue::test_missing_enforcement_cue_surfaces_a_real_symbol
- tests/unit/test_ticket_new_related.py::TestPossibleEnforcementSymbolsCue::test_no_cue_means_no_grep
designated_repro_test: tests/unit/test_ticket_new_related.py::TestRefusesUnacknowledgedRelatedTicket::test_close_match_against_an_archived_ticket_refuses
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob ticket new` accepts any ticket without checking whether the work is
already tracked or already done. Seven tickets filed this session had to
be dropped, and several cost a dispatched agent a full cycle to discover
there was nothing to do.

MEASURED -- all seven dropped, with the reason each was unnecessary:
  T-1915  duplicate of open T-1867
  T-1991  duplicate of open T-1989 (same 105 findings)
  T-1986  duplicate of ALREADY-LANDED T-1866 -- the feature it asked for
          (`_refuse_over_broad_scope_on_start`, app/ticket_runner/
          _lifecycle.py:912) already existed and its tests passed
  T-1972  already resolved by REG010's existing Tier-A auto-fix, which
          had run during another ticket's land
  T-1947  already fixed by T-1954 + T-1951 before anyone read it
  T-1976  its only outstanding item already existed on main
  T-1949  already split by T-1933; function measured 41 lines, under the
          60-line threshold it claimed to exceed

COST: T-1972 and the T-1976/T-1949 pair each consumed a dispatch. T-1986
was filed at HIGH and competed for a dispatch slot against genuinely
starved work. A stale or duplicate ticket does not merely waste its own
slot -- it displaces real work at the top of the queue.

TWO DISTINCT MISSES, and the second is the one nothing covers:
1. Duplicate of an existing TICKET. The standing pre-filing search covers
   open tickets, which catches T-1915/T-1991 if actually run.
2. Duplicate of an already-SHIPPED capability. T-1986 asserted "nothing
   enforces X" when X had shipped two days earlier. Searching open
   tickets cannot catch this -- the covering ticket was DONE and
   archived. This class needs a code check, not a queue check.

THE RULE EXISTS AND IS ALREADY FOLLOWED. The standing dispatch duty says
to search for an existing ticket including in-progress and queued before
filing. That search WAS run before T-1986 and returned nothing, correctly,
because the covering work was archived. So a louder instruction cannot
fix class 2 -- the search was performed and was looking in the wrong
place.

DO NOT FIX IT THIS WAY:
- Do NOT block `ticket new` on a similarity heuristic alone. False
  positives on genuinely-new tickets would be worse than the current
  cost, and near-duplicate titles are common and often legitimate
  (successor tickets, per-node burn-downs, sweep-filed regressions).
- Do NOT auto-close/auto-drop a suspected duplicate. Disposition needs a
  human or agent judgement; the harm here was wasted dispatch, not a
  corrupted ledger.
- Do NOT limit the check to open tickets. That is exactly the gap that
  let T-1986 through.

FIX DIRECTION, preferred order:
(a) At `ticket new`, surface likely-related tickets -- INCLUDING done and
    archived -- and require an explicit acknowledgement to proceed. The
    ledger is local and already indexed; this is a read, not a new
    subsystem.
(b) For a ticket whose body asserts a missing enforcement ("nothing
    refuses / only warns / is not checked"), additionally surface any
    matching rule id, `_refuse_*`/`_check_*` symbol, or test name found
    in the tree, so the author sees the existing implementation before
    filing.

ACCEPTANCE: first test must FAIL before the fix -- file a ticket whose
title closely matches an ARCHIVED done ticket and assert the related
ticket is surfaced by id. Then assert a genuinely novel ticket files
without friction, and that a successor ticket deliberately similar to its
predecessor can still be filed after acknowledgement.

## Done report

Scope correction: the ticket's declared scope named src/frob/tickets/_new.py,
which does not exist. The library new_ticket() function lives in
src/frob/tickets/_new_renumber.py, but that library function is shared by
several NON-interactive auto-filing callers (rapid-sweep regression
filing, mutation-sweep, testing stability, sys_runner, fleet) that must
never block on an acknowledgement flag -- surfacing + requiring ack is an
interactive-CLI-only concern. Retargeted scope to
src/frob/app/ticket_runner/_new.py (the frob ticket new CLI dispatch,
_new()), plus the two files a new CLI flag structurally requires:
src/frob/_cli_parsers/_ticket/_new.py (the argparse wiring) and
src/frob/app/config.py (the AppConfig field), both additive, single-field
changes only.

Fix direction (a) implemented: at frob ticket new, a new related_tickets()
helper searches BOTH active (load_all) and ARCHIVED (load_archive)
tickets by title similarity (difflib.SequenceMatcher.ratio(), 0.6 cutoff
-- the same convention frob.gates._fix_engine already uses for an
identical "surface a candidate, do not assume identity" purpose). Any
match >= threshold refuses ticket creation (sys.exit(1)) UNLESS the
caller passes the new --ack-related flag (cfg.ticket_ack_related) --
surfaced by id/title/state/match percentage, never auto-dropped, never a
permanent block: the flag is the escape hatch. Verified live against
this repo's own real archive (1824 archived tickets): searching for
T-1949's exact archived title returns it at 100% match; a genuinely
distinct search string returns nothing.

Fix direction (b) implemented, additively: when the new ticket's title+
body contains one of a fixed set of "missing enforcement" phrases
(_MISSING_ENFORCEMENT_CUES -- "nothing enforces", "nothing refuses",
"only warns", etc., covering the exact T-1986 wording), a `git grep` for
`_refuse_*`/`_check_*` symbols whose name shares a significant word with
the title is run and surfaced alongside the related-ticket list. This
never fires on an unrelated ticket (no cue, no grep) and never blocks on
its own -- only related_tickets' title match ever requires --ack-related;
the symbol hint is informational.

DID NOT do: block on similarity alone with no escape (the flag is the
escape -- a genuinely novel title needs no flag and files with zero
friction, verified by test); auto-close/auto-drop a suspected duplicate
(the check only ever refuses THIS new filing, never touches any existing
ticket's state); limit the search to open tickets (load_archive is
included unconditionally, which is the entire point -- this is exactly
what would have caught T-1986 against archived T-1866).

Acceptance criteria, all met:
1. First test must FAIL before the fix: verified by reverting the three
   changed files to their pre-fix content (saved as a patch first, no
   cross-branch checkout involved) -- the ENTIRE test module fails to
   even collect (ImportError: cannot import name 'related_tickets'),
   since neither the function nor the --ack-related flag existed.
   Restored the fix, all 8 new tests pass.
2. A genuinely novel ticket files without friction:
   TestNovelTicketFilesWithoutFriction -- passes with an archived
   near-title present but this title distinct.
3. A successor ticket deliberately similar to its predecessor can still
   be filed after acknowledgement: TestSuccessorTicketAfterAcknowledgement
   -- "Burn down TEST005 in src/frob/gates" then "... in src/frob/tickets"
   with --ack-related.

BUG002 note: the designated repro test is a brand-new node in a brand-new
file; --check-repro correctly reports NO_VERDICT/exit 5 (the whole module
fails to collect at the parent commit, since related_tickets doesn't
exist there) -- documented per T-1929's structural shape, designated via
--designate-repro-force with the fail-before-fix verification recorded
as the substitute evidence.

Full regression sweep: tests/unit/test_ticket_new_related.py (8, new),
tests/unit/test_ticket_runner_designate_repro.py + tests/test_app_config.py
(22) + tests/unit/test_scope_closure_warning_collapse_t1556.py +
tests/test_tickets_new_gate_rule_acceptance.py (20) all pass unmodified.

### Changed
```
 tickets/T-1995/ticket.md | 57 +++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 54 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_no_match_for_a_genuinely_distinct_title` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestRefusesUnacknowledgedRelatedTicket::test_close_match_against_an_archived_ticket_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestRefusesUnacknowledgedRelatedTicket::test_ack_related_proceeds_despite_the_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestNovelTicketFilesWithoutFriction::test_novel_title_needs_no_ack` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestSuccessorTicketAfterAcknowledgement::test_successor_of_an_open_ticket_files_after_ack` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestPossibleEnforcementSymbolsCue::test_missing_enforcement_cue_surfaces_a_real_symbol` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestPossibleEnforcementSymbolsCue::test_no_cue_means_no_grep` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/_cli_parsers/_ticket/_new.py, AFFECT001@src/frob/app/ticket_runner/_new.py, DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/ticket-bookkeeping/tests/unit/test_tickets_evidence_only_scope.py, TEST001@src/frob/app/ticket_runner/_new.py, WIRE001@src/frob/_cli_parsers/_ticket/_new.py
