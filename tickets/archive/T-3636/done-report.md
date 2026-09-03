## Done report

Bisect verdict: not a detector regression at all -- reproduced locally
first (test failed at HEAD before any fix, with a WARNING log line
"doc004: could not resolve 'tests.test_gates:_doc012_fake_parser_factory':
No module named 'tests.test_gates'"), which named the true cause directly
without needing to walk the 5bb54dc5f..e1dbe29b9 commit window by hand:
T-3586's split of tests/test_gates.py relocated
_doc012_fake_parser_factory into tests/conftest.py, but
tests/test_doc012_promotion.py's own _DOC012_PROMOTION_FAKE_CONFIG fixture
still pointed its "parser =" dotted-path string at the old
tests.test_gates location. doc004's dotted-path resolver fails silently
on an unresolvable module (logs a WARNING, does not raise), so
doc012_gate had no parser to introspect and returned zero findings
instead of the expected one -- exactly the "zero findings, both legs,
deterministic" symptom.

Fix: repoint the fixture's dotted path at
"tests.conftest:_doc012_fake_parser_factory", matching where T-3586
actually left the helper. No detector code changed; the test was not
weakened, its assertion is unchanged.

Evidence:
tests/test_doc012_promotion.py::TestDoc012PromotedToError::test_undocumented_subcommand_is_now_error
(failed before the fix, reproducing the exact CI symptom; passes after)
tests/test_doc012_promotion.py full file (2/2 green)

Filed: none

Gates: gates-native/gates-security/lint/static chunks show no findings on
tests/test_doc012_promotion.py; ruff-check/ruff-format failures present
are pre-existing repo-wide baseline (50+ unrelated files), confirmed by
grep against this ticket's touched file. gates-fast timed out under this
host's foreground cap (same load as T-3634 hit) and was not re-run
standalone. `frob test --base main` fell back to a suite-wide selection
(tickets/T-3636/ticket.md registers as an unknown-language touched file)
and timed out under the foreground cap; ran the test file directly
instead (pytest, both tests green) as the practical verification.

### Changed
```
 tests/test_doc012_promotion.py | 5 +++--
 tickets/T-3636/ticket.md       | 4 +++-
 2 files changed, 6 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_doc012_promotion.py::TestDoc012PromotedToError::test_undocumented_subcommand_is_now_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 4171 warning(s), 896 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3628/ticket.md, DOC006@tickets/T-3629/ticket.md, DRIFT002@tests/ticket_land_suite/test_archive.py, DRIFT002@tests/ticket_land_suite/test_claim_close.py, DRIFT002@tests/ticket_land_suite/test_dirt_ownership.py, DRIFT002@tests/ticket_land_suite/test_land_core.py, DRIFT002@tests/ticket_land_suite/test_land_lock.py, DRIFT002@tests/ticket_land_suite/test_land_plan.py, DRIFT002@tests/ticket_land_suite/test_ledger_splice.py, DRIFT002@tests/ticket_land_suite/test_push.py, DRIFT002@tests/ticket_land_suite/test_release.py, DRIFT002@tests/ticket_land_suite/test_verify_intent.py, DRIFT002@tests/ticket_land_suite/test_verify_reset.py, DRIFT002@tests/ticket_land_suite/test_waive_deletion.py, DRIFT002@tests/ticket_land_suite/test_wip.py, F401@/home/logan/projects/frob/.claude/worktrees/t-3636/tests/test_ticket_land.py, OPAQUE001@src/frob/app/_config_external.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
