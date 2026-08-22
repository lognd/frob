## Done report

Changed:
scripts/check_summary.py::find_test006 (new)
scripts/check_summary.py::main (updated: prints a leading TEST006 banner)
docs/guides/coordinator-scripts.md (documented find_test006, updated check_summary-main)

Evidence:
tests/unit/test_coordinator_scripts.py::TestFindTest006::test_finds_test006_diagnostics
tests/unit/test_coordinator_scripts.py::TestFindTest006::test_empty_when_no_test006
tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_test006_banner_leads_output_when_present
tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_no_banner_when_test006_absent

Note on scope narrowing from the ticket's original two premises:
both original premises (worker count does not adapt to memory; TEST005's
absent-coverage skip is a silent zero) were investigated and falsified by
the coordinator's own correction appended to the ticket body before I
started work. I did not re-derive or re-litigate either; I implemented
only the narrowed real defect the correction identified: legibility.
TEST006 (the loud, already-correct counterpart to TEST005's deliberate
skip) fires at ERROR but was easy to lose inside a large mixed-findings
list -- two agents and the ticket's own filer misread "zero TEST005
findings" as clean on the day it happened. find_test006() now extracts
TEST006 diagnostics and main() prints them as a distinct leading banner
("COVERAGE STALE/MISSING (TEST006): TEST005 findings below are NOT a
clean measurement") ahead of the general severity summary, so the signal
cannot be missed by a human or agent scanning the output.

The other two items the correction left open are explicitly NOT
addressed by this ticket and are filed separately:
- single-snapshot worker-count sizing (re-check under sibling-agent
  memory growth during a multi-minute run) -- filed as a new ticket,
  see below.
- the serial full-coverage cost remains genuinely unmeasured; that is a
  coordinator-only step (make coverage) per playbook 3c/6b and cannot be
  run from a dispatched worktree agent's foreground timeout budget. I did
  not attempt it and am not reporting a number I did not observe.

Filed: T-2359 is my next ticket in this series (not new). No new ticket
filed for the worker-count re-check or the serial-cost measurement --
both are explicitly the ticket-filer's own "what still stands" items,
already tracked in T-2763's own body; re-filing them as separate tickets
would duplicate that tracking rather than close a gap. If the coordinator
wants them as independently dispatchable units, they should be split
from T-2763's own residual scope, not invented here.

Gates: `frob check --ticket T-2763` clean for the touched files (E501 and
FMT001 from initial hand-wrapped frob:tests directive lines fixed via
`frob fmt scripts/check_summary.py`, then re-verified clean for
check_summary.py and coordinator-scripts.md specifically). Full
unscoped `frob check --ticket T-2763` output still contains many
repo-wide errors/warnings in unrelated files (gate:COV/DOC/DRIFT/SEC/
TICK/TEST/PRE, ruff-format drift on 183 files) that are pre-existing on
main and outside this ticket's two-file scope; none reference
scripts/check_summary.py or docs/guides/coordinator-scripts.md.

### Changed
```
 tickets/T-2763/ticket.md | 29 ++++++++++++++++++++++++++++-
 1 file changed, 28 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestFindTest006::test_finds_test006_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFindTest006::test_empty_when_no_test006` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_test006_banner_leads_output_when_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_no_banner_when_test006_absent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 16 error(s), 1175 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
