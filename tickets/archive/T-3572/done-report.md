## Done report

Replaced _eval_one_claim's 4-arm isinstance chain with a type-keyed dict
dispatch table (_CLAIM_EVALUATORS), giving every claim-body evaluator a
uniform (FactBase, Claim, ClaimBody, date) signature -- _eval_bound's
extra `current`/`today` argument was the reason a mechanical dict swap
didn't fit before; now every arm takes it (the three time-independent
arms `del current` immediately). Behavior is unchanged: same tests, same
verdicts, evidenced by the pre-existing 16-test test_claims.py suite and
the full 1491-test tests/unit/strata/ suite staying green, plus two new
regression tests guarding dispatch-table completeness and signature
uniformity. Evidence recorded via `frob ticket evidence`. Filed: none.
Gates: `frob check --ticket T-3572 --skip-tests` clean for this ticket's
touched set (gate:SCOPE 0 errors, gate:COV(COV002) 0 errors; two COV006
best-effort callgraph misses on the new dict-dispatch tests waived per
the dsl.py `_VERB_ATTRS_VALIDATORS` precedent; a ty invalid-assignment
diagnostic on the dict-of-heterogeneous-callables literal fixed via
typing.cast per entry).

### Changed
```
 src/frob/strata/_claims.py       | 64 +++++++++++++++++++++++++++++-----------
 tests/unit/strata/test_claims.py | 34 +++++++++++++++++++++
 tickets/T-3572/ticket.md         | 12 +++++++-
 3 files changed, 91 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/unit/strata/test_claims.py::TestClaimDispatchTable::test_dispatch_table_covers_every_claim_body_kind` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_claims.py::TestClaimDispatchTable::test_dispatch_table_evaluators_share_one_call_signature` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 26 error(s), 4118 warning(s), 894 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3572, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
