## Done report

Root cause and attribution: T-4369 (commit 387caa239) added
`_resolve_kill_argv` and put a `frob:doc` directive
(docs/modules/tickets-landing.md#mutation-evidence-obligation-test016-t-0755)
directly on it -- but that private helper's own caller,
`check_ticket_mutation_evidence`, already carries the identical
anchor. COV007 (error severity) correctly flags a `frob:doc` on a
private symbol when doc anchors are meant to cover the public API
surface; this was a redundant/misplaced duplicate anchor, not a case
needing a waiver. Fix: remove the anchor from `_resolve_kill_argv`,
keeping it only on the public caller, where coverage of that doc
section is unchanged.

Broke ubuntu CI (gh run 34358765772, job 102490073727): "frob check .
[FAIL] 1 error 5260 warnings" -- exact finding:
"src/frob/tickets/_mutation_evidence.py:296  COV007  COV007: frob:doc
on private symbol src/frob/tickets/_mutation_evidence.py::
_resolve_kill_argv -- doc anchors normally cover the public API
surface; move it onto the public caller, or confirm this private
helper genuinely needs its own doc anchor". Confirmed severity via
src/frob/gates/__init__.py: COV007 is Severity.ERROR (COV006, the
other COV rule appearing in that same log, is Severity.WARN).

Evidence: tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
(existing test covering check_ticket_mutation_evidence, still passing
after the anchor removal -- the fix does not touch behavior, only a
doc directive). Full module suite
(tests/test_tickets_mutation_evidence.py, 21 tests) run locally, all
pass.
Filed: none (this ticket, T-4373, IS the filed ticket)
Gates: uv run frob check --only cov clean of COV007 for this symbol
(no _resolve_kill_argv finding in a fresh --only cov run);
uv run frob check --ticket T-4373 run before land.

### Changed
```
 src/frob/tickets/_mutation_evidence.py | 1 -
 tickets/T-4373/ticket.md               | 2 ++
 2 files changed, 2 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4775 warning(s), 955 waived
- error-findings: COV003@tickets/T-4364/ticket.md
