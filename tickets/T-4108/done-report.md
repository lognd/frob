## Done report

frob ticket close had an argparse asymmetry: --evidence-cmd had no action= (last-wins) while --accepts is action=append (accumulates), so a caller pairing two evidence commands with two acceptance criteria got one command silently bound to both, and the close SUCCEEDED with a false record (F-306, T-0265).

Enumerated every site defining this flag pair by grepping for --evidence-cmd across src/frob/_cli_parsers/_ticket/_closeout.py: exactly three -- close, reverify (documented as sharing close's flags verbatim), and evidence itself. Confirmed (not assumed) the identical asymmetry exists on all three: each pairs a single-value --evidence-cmd with an accumulating --accepts.

Added _RefuseRepeatedEvidenceCmd, an argparse Action that refuses a SECOND --evidence-cmd in one invocation with a message naming the per-call frob ticket evidence path, rather than accepting action=append's fragile positional-pairing shape (which would also silently change the legitimate one-command-many-criteria case this ticket's must-stay-quiet fixture protects). Applied identically to all three sites.

Verified manually via the real CLI (two-command refusal at all three sites, one-command-many-accepts still parses, --evidence/positional node-ids unaffected) and via tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py covering all three of the ticket's fixtures parametrized across close/reverify/evidence.

Filed T-4129 for a pre-existing SCOPE002 doc-closure gap this ticket's own declared scope surfaces (_closeout.py's frob:doc target cascades into an unrelated file chain when added to scope); unrelated to this ticket's own fix.

### Changed
```
 src/frob/_cli_parsers/_ticket/_closeout.py         |  91 +++++++++++++++--
 .../test_ticket_close_evidence_cmd_repeat_t4108.py | 113 +++++++++++++++++++++
 tickets/T-4108/done-report.md                      |  28 +++++
 tickets/T-4108/ticket.md                           |  52 +++++++++-
 tickets/T-4129/ticket.md                           |  30 ++++++
 5 files changed, 304 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestSecondEvidenceCmdIsRefused::test_second_evidence_cmd_refuses_naming_the_evidence_verb[close]` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestSecondEvidenceCmdIsRefused::test_second_evidence_cmd_refuses_naming_the_evidence_verb[reverify]` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestSecondEvidenceCmdIsRefused::test_second_evidence_cmd_refuses_naming_the_evidence_verb[evidence]` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestOneCommandManyAcceptsUnchanged::test_close_one_command_several_accepts` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestOneCommandManyAcceptsUnchanged::test_reverify_one_command_several_accepts` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestOneCommandManyAcceptsUnchanged::test_evidence_one_command_several_accepts` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestUnaffectedFlagsStillAccumulate::test_close_evidence_node_ids_still_accumulate` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py::TestUnaffectedFlagsStillAccumulate::test_evidence_positional_node_ids_still_accumulate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 6 error(s), 4433 warning(s), 935 waived
- error-findings: DUP001@src/frob/_cli_parsers/_ticket/_closeout.py, DUP002@tests/unit/test_ticket_close_evidence_cmd_repeat_t4108.py, LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, SCOPE002@tickets.md, WIRE001@src/frob/_cli_parsers/_ticket/_closeout.py, missing-argument@tests/unit/test_check_gates_summary.py
