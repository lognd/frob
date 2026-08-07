## Done report

`frob ticket evidence <id> --replace OLD-NODE-ID NEW-NODE-ID` (T-1537):
rebinds one evidence id everywhere it appears -- the flat evidence list
AND every acceptance criterion's own binding -- in a single atomic
`write_ticket` call (`frob.tickets.replace_evidence`), routed through the
exact same single-writer path every other evidence mutation already
uses. `NEW-NODE-ID` is held to the same bar a fresh `--evidence` id is
(schema-validated, resolved against collected pytest/rust node ids,
required to have actually passed on the CLI's own verification run);
`OLD-NODE-ID` must be present somewhere on the ticket
(`Err(EvidenceReplaceNotFound)` otherwise, never a silent no-op for a
typo'd source id); `OLD-NODE-ID == NEW-NODE-ID` (post-normalization) is a
no-op SUCCESS. Composes with the positional node-id list and
`--evidence-cmd` in one invocation.

Verified two ways: the direct library API (`TestReplaceEvidence`, 4
cases -- successful atomic rebind including an acceptance binding,
old-node-absent refusal, unresolvable-new-node refusal, same-old-new
no-op) and the real CLI end to end against a throwaway fixture repo
(`uv run frob ticket evidence T-0001 --replace <old> <new>`, both the
success and the not-found-refusal paths), before writing the hermetic
CLI-level pytest coverage (`TestReplaceEvidenceCli`, 3 cases).

Follow-up disclosed by this ticket's own body (frob refactor rename
detecting a bound-evidence reference and offering the --replace rebind
automatically) filed as a new ticket this session (draft id, will
renumber at land -- not cited here by draft id per the never-cite rule).

Scoped verification: `frob check --only test --only archgate --only
coverage --only sys --ticket T-1537` -- 0 errors (one round of real
self-inflicted findings fixed along the way: ARCH001 on `replace_evidence`
itself, split into `_prepare_replace_evidence`/`_rebind_evidence`;
SELFAUDIT001 SYS104 interface= drift on `design/frob.strata` for the new
`replace_evidence`/test classes, fixed via T-1531's own
sync_interface_report/apply_sync_interface writer -- same dogfood
pattern used across all three tickets in this series). `frob check
--land-parity` -- 0 errors, matches the scoped result (the ONLY findings
the raw sweep saw were the two T-1524 checkpoint-artifact exemptions on
`design/frob.strata`, correctly dropped before the final report). `ruff
check`/`ruff format` clean on every touched file. `git diff main
--diff-filter=D --stat` is empty.

### Changed
```
 design/frob.strata                         | 1038 ++++++++++++++--------------
 docs/guides/agent-playbook.md              |   32 +
 docs/modules/gates.md                      |   68 ++
 docs/modules/tickets.md                    |   71 ++
 src/frob/_cli_parsers/_check.py            |   12 +
 src/frob/_cli_parsers/_ticket/_closeout.py |   13 +
 src/frob/app/_config_external.py           |    4 +
 src/frob/app/check_runner.py               |   54 +-
 src/frob/app/config.py                     |   13 +
 src/frob/app/ticket_runner/_land_cmd.py    |   88 ++-
 src/frob/app/ticket_runner/_verify.py      |   69 +-
 src/frob/gates/_fix_engine.py              |  125 ++++
 src/frob/strata/_sync_may.py               |  412 +++++++++++
 src/frob/tickets/__init__.py               |    2 +
 src/frob/tickets/_evidence.py              |  158 +++++
 src/frob/tickets/_models.py                |    9 +
 tests/test_gates.py                        |   93 +++
 tests/test_ticket_work_and_land_finish.py  |   73 ++
 tests/test_tickets_evidence_cli.py         |  183 +++++
 tests/unit/strata/test_sync_may.py         |  167 +++++
 tickets.md                                 |  569 ++++++++++++++-
 21 files changed, 2717 insertions(+), 536 deletions(-)
```

### Evidence
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_replaces_flat_evidence_and_acceptance_binding_atomically` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_old_node_absent_is_a_hard_refusal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_unresolvable_new_node_is_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_same_old_and_new_is_a_no_op_success` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replaces_and_commits` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_requires_at_least_one_of_the_three_modes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_not_found_exits_nonzero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 1 error(s), 479 warning(s), 799 waived
- error-findings: PRE001@tickets/T-1537
