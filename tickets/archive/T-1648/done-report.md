## Done report

Fix shape: reuse WIRE002's own precedent (an escape hatch must bind to a
real, open follow-up ticket, not free-text prose) instead of inventing a
second obligation-tracking mechanism.

frob.tickets._reporting.disclosure_shaped_language(text) is a
deliberately generous phrase-match heuristic over a Done report's own
narrative (not attempted, still outstanding, out of scope for this pass,
etc) -- not an English parser. False positives are the acceptable
failure mode (one extra Filed: line); false negatives are the incident
this exists to prevent.

frob.tickets._reporting.filed_followup_tickets(body) parses every T-####
id named on a Filed: line, the existing playbook Done-report convention,
now made checkable.

frob.app.ticket_runner._close_cmd._undisclosed_remainder_reason(root,
ticket) combines the two and is wired into both _close and _reverify
before the transition/guard chain runs: if disclosure-shaped language is
present and no Filed: id resolves to a real, still-open ticket (reusing
frob.gates._OPEN_STATES, the same "open" WIRE002 uses), the close/
reverify refuses with the matched phrase and a concrete remedy.

Docs added to docs/modules/tickets.md under a new "Disclosed-remainder-
requires-follow-up guard at close (T-1648)" section, cited via frob:doc
on both new public functions.

While narrowing scope, frob sys sync-interface auto-rewrote
design/frob.strata (2 new tickets_ledger interface symbols, 2 new
testsuite capability declarations for the new test file's git-subprocess
and tmp_path writes) -- this reproduced, live, the exact sync-interface
-> COV/SELFAUDIT -> scope-widening-pressure mechanism the coordinator's
T-1868 brief suspected; noted here as direct evidence for that ticket
rather than acted on further (out of T-1648's own scope).

Filed: none -- no unfinished remainder disclosed by this ticket itself.

### Changed
```
 tickets/T-1648/ticket.md | 33 +++++++++++++++++++++++++++++++--
 1 file changed, 31 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 2 error(s), 1207 warning(s), 745 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/land-integrity/src/frob/tickets/_reporting.py, PRE001@tickets/T-1648
