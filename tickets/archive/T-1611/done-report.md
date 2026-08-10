## Done report

Classified every doc gap T-1610's audit (docs/audits/docs-completeness-
2026-08-06.md) found, plus the two same-shape incidents from today's
session the coordinator named, per the ticket's own four-way rubric.

## From T-1610's audit

1. FROB_WORKER_STDOUT_LOG_LEVEL (T-0806) undocumented ~2 weeks.
   Classification: NO RULE EXISTS. Checked SEC110 specifically since it
   fires on this exact env-var read and was waived ("worker log-level
   marker, not a secret") -- but that answers a different question
   (secret classification), not doc coverage, and the constant is
   private so COV001/COV007 do not apply either (this repo's own
   convention is that private symbols do NOT carry frob:doc). No
   existing gate asks "does every operational FROB_* env var have
   user-facing documentation". Filed T-1782.

2. docs/modules/gates.md's rule-catalog table missing ~122 real rule
   ids. Classification: RULE EXISTS BUT WAS NEVER WIRED to this
   obligation. DOCENUM001 (T-1227) is built for exactly this shape --
   `frob:enumerates` binds a doc table to a real code collection and
   AST-diffs it every run -- and `_KNOWN_GATE_RULES` (src/frob/gates/
   _waive.py:173) is already the live, authoritative frozenset of every
   registered rule id, the exact collection shape DOCENUM001 supports.
   Nobody ever anchored the rule-catalog table to it. DRIFT001 (digest-
   staleness only) cannot substitute: a table can be byte-identical to
   its last ack and still silently miss a newly-added id. Filed
   T-1781 (the wiring); T-1681 (already filed by T-1610) does
   the one-time content backfill -- independent, either can land first.

3. `frob coverage` has no dedicated doc section (table row only).
   Classification: NO RULE EXISTS. DOC004 (the `[[docblocks.commands]]`
   console/table drift check) verifies a verb table's rows exist and
   are not stale, and `frob coverage` already has a row -- so DOC004
   correctly finds nothing wrong. It was never designed to ask whether
   a verb with a row also has a dedicated section describing its own
   flags. Filed T-1783 (the rule); T-1682 (already filed by
   T-1610) does the content fix for this one verb.

## From today's session, per the coordinator's brief

4. Root `agents/`/`skills/` audited as "live-read by the dispatching
   harness" (T-1767: KEEP) when nothing read them (T-1772: deleted,
   confirmed zero references in src/frob/**, not packaged, not
   scaffolded). Classification: NO RULE EXISTS. Neither DEAD001 (Python
   symbols only) nor REF002 (`.strata` litmus fixtures only) covers "a
   repo-root directory of non-code assets claimed to be read by an
   external process." The verification that settled it (grep the tree,
   check packaging config, check scaffold output) was manual and ad
   hoc -- nothing mechanizes it, so the same name-matching trap (the
   agent/skill names happened to match the dispatching harness's own
   real roster, which read as proof of a link that was not there) can
   recur on the next repo-root directory someone audits. Filed
   T-1784: a rule that flags any non-src/tests/docs/tickets/
   design repo-root directory with zero code references, zero packaging
   references, and no explicit `frob:external-reader` declaration.

5. SYS109 (T-1627) landing as a tested detector wired into no gate.
   Investigated and classification is DIFFERENT from what the pattern
   suggested at a glance: this one is NOT a gap. WIRE001 (a diff-added
   symbol reachable only from its own test file) fired correctly on
   `check_stale_via_symbols` at the time T-1627 landed
   (src/frob/strata/_effects.py:657) and was waived with a specific,
   honest reason ("wiring it into frob sys audit's CLI surface needs
   files outside T-1627's own declared scope") carrying a tracked
   `follow_up="T-1761"` -- and T-1761 is a real, open ticket ("wire
   SYS109 into frob sys audit", confirmed in tickets.md). Per this
   ticket's own rubric ("THE RULE FIRED AND WAS WAIVED -- hand it to
   the waiver audit child; do not resolve it here"), this is exactly
   the mechanism working as intended: a detector shipped ahead of its
   own wiring, correctly caught, correctly deferred with a real
   destination. No new ticket filed for this one -- filing one would be
   noise against a waiver that already does its job.

## Not resolved here

Per the ticket's own instruction, "THE RULE FIRED AND WAS WAIVED" cases
go to the waiver audit child, not this ticket -- item 5 above is the
one instance checked in enough depth to confirm it is exactly that
shape (and, on inspection, not actually a gap). No other waived-finding
gaps were in T-1610's input list to hand off.

### Changed
```
 tickets/T-1611/ticket.md           |  5 +++-
 tickets/T-1781/ticket.md | 50 ++++++++++++++++++++++++++++++++
 tickets/T-1782/ticket.md | 52 ++++++++++++++++++++++++++++++++++
 tickets/T-1783/ticket.md | 51 +++++++++++++++++++++++++++++++++
 tickets/T-1784/ticket.md | 58 ++++++++++++++++++++++++++++++++++++++
 5 files changed, 215 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1579 warning(s), 720 waived
- error-findings: none (measured, zero errors)
