## Done report

frob ticket accept only manages acceptance criterion TEXT; the flags that bind evidence to a criterion index (--evidence-cmd, --accepts) live on frob ticket evidence, and F-305 measured three consumer agents in a row reaching for one of them on accept, getting only argparse's generic unrecognized-arguments error.

Added _CrossVerbFlagHint (src/frob/_cli_parsers/_ticket/_metadata.py): an argparse Action registered as a suppressed, always-refusing trap for the specific confusable flags on each verb:
- accept gets --evidence-cmd/--accepts/--evidence trapped, hinting at frob ticket evidence and its --accepts index flag
- evidence gets the mirror direction: --criterion/--criterion-file/--amend trapped, hinting back at frob ticket accept

This is not an alias: the Action's __call__ never stores a value or succeeds, it always calls parser.error() with the hint appended. The root parser's own leftover-arguments handling (frob/_cli_parsers/_root.py) only ever calls error() on the ROOT ArgumentParser, which is out of this ticket's declared scope (src/frob/_cli_parsers/_ticket/*.py only) -- registering the flag as a recognized no-op on the subcommand's own parser is what makes a per-flag hint reachable without touching that file.

--remove/--reason are deliberately NOT trapped on evidence: both already exist there with a different meaning than on accept (--remove EVIDENCE-ID drops an evidence id vs accept --remove INDEX drops a criterion), so trapping them would be exactly the aliasing this ticket rules out -- documented inline at the trap registration site.

Verified manually via the real CLI (uv run frob ticket accept/evidence with each trapped flag, plus --help and a correct invocation of each) and via tests/unit/test_ticket_accept_evidence_hint_t4106.py covering all three of the ticket's fixtures plus the mirror direction and the non-trapped --remove case.

Filed T-4128 for the ~44 pre-existing SCOPE002 doc-closure findings this ticket's already-declared whole-directory scope surfaces (predates this diff; unrelated to the flag-hint fix; same class of debt as T-4123 filed for T-4105).

### Changed
```
 src/frob/_cli_parsers/_ticket/_closeout.py         |  43 ++++++
 src/frob/_cli_parsers/_ticket/_metadata.py         |  77 +++++++++++
 .../unit/test_ticket_accept_evidence_hint_t4106.py | 148 +++++++++++++++++++++
 tickets/T-4106/done-report.md                      |  33 +++++
 tickets/T-4106/ticket.md                           |  43 +++++-
 tickets/T-4128/ticket.md                           |  33 +++++
 6 files changed, 373 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestAcceptEvidenceFlagHint::test_evidence_flag_on_accept_names_the_evidence_verb` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestAcceptEvidenceFlagHint::test_bare_evidence_flag_on_accept_names_the_evidence_verb` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestAcceptUnrelatedFlagUnchanged::test_unrelated_unrecognized_flag_gets_the_ordinary_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestCorrectInvocationsUnaffected::test_accept_help_does_not_list_the_trap_flags` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestCorrectInvocationsUnaffected::test_evidence_help_does_not_list_the_trap_flags` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestCorrectInvocationsUnaffected::test_accept_plain_criterion_append_still_parses` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestCorrectInvocationsUnaffected::test_evidence_plain_node_id_still_parses` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestEvidenceCriterionFlagHintMirror::test_criterion_flag_on_evidence_names_the_accept_verb` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_accept_evidence_hint_t4106.py::TestEvidenceCriterionFlagHintMirror::test_remove_on_evidence_is_not_trapped_it_is_a_real_flag` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 4 error(s), 4434 warning(s), 932 waived
- error-findings: LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, SCOPE002@tickets.md, WIRE001@src/frob/_cli_parsers/_ticket/_metadata.py, missing-argument@tests/unit/test_check_gates_summary.py
