## Done report

Changed:
- docs/design/registry/capability-via-ratchet.lock.json (3 ceiling bumps)

Every delta attributed to a specific, already-landed ticket (measured via
diffing design/frob.strata's via-list file sets directly, not assumed):

- gates::fs.write 37->40: _gates_schema.py (T-2435), _test_runner_schema.py
  (T-2436), _dup_graph_schema.py (T-2437), _port_selfcheck.py (T-2388).
  3 of 4 are false declarations forced by T-2457's open()-mode-blind
  detector bug -- noted explicitly in the ratchet entry's own reason field
  so this is findable and NOT treated as a permanent floor; ceiling is
  expected to fall again by up to 3 (plus the 4 pre-existing false
  T-2390-sibling declarations already in this via-list, 7 total) once
  T-2457 lands.
- testsuite::exec 185->186: test_process_reap.py (T-2443),
  test_port_selfcheck.py (T-2388), test_tickets_no_scope.py (T-2394).
- testsuite::fs.write 345->348: test_port_selfcheck.py (T-2388),
  test_process_reap.py (T-2443), test_gates_table_schema.py (T-2435),
  test_test_table_schema.py (T-2436), test_dup_graph_table_schema.py
  (T-2437).

No unexplained remainder in any of the three deltas -- every added site
traces to a real ticket already on main. Set each ceiling to exactly the
current measured count, not padded, per the coordinator's explicit
instruction not to let this become a rubber stamp.

Evidence: docs-kind evidence-cmd (bash /tmp/t2460_verify.sh) re-runs
`frob check --only gates-fast --json` and asserts SELFAUDIT001 count == 0;
exit=0, sha256=054d8bbd1270.

Filed: none

Gates: SELFAUDIT001 confirmed 0 findings against this repo's real state
post-edit (was 3 pre-edit, all three of exactly the shape this ticket
addresses).

### Changed
```
 tickets/T-2460/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `cmd:bash /tmp/t2460_verify.sh exit=0 sha256=054d8bbd1270` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2460/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2460/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2460/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2460/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2460/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
