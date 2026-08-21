## Done report

Changed: docs/investigations/T-2796-backlog-reproduction.md (new)

Evidence: docs-only investigation ticket, no pytest surface of its own.
Per playbook section 5, recording the existing CLI-dispatch integration
test as evidence:
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

Filed: T-draft-b1ac02d7 (docs, kind=docs) -- document and enforce the
drop --absorbed-by vs fail distinction in docs/guides/agent-playbook.md
(out of this ticket's own scope, which is docs/investigations/ only).

Gates: one full unbudgeted `frob check --json` was run and reused across
every ticket's measurement (gate-summary present, 300s+ wall, per-stage
timings recorded -- the positive-control shape from the brief). No
mechanism was built in this ticket: the measurement did not support
building one directly (most claims required either bulk gate-identity
counts, which reused the single check above, or a targeted source-level
repro this pass's budget did not reach -- reported CANNOT MEASURE rather
than guessed). The durable-mechanism recommendation (reuse T-2760's
findings/--finding land-time identity match, do not build a parallel
doable-based query) is recorded in the investigation doc's own section
rather than implemented as code in this ticket, since T-2796's own scope
is docs/investigations/ only and no ticket authorized landing that
land-time wiring here.

### Changed
```
 tickets/T-2796/ticket.md           |  2 +-
 tickets/T-draft-b1ac02d7/ticket.md | 48 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 49 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 19 error(s), 852 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
