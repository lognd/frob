## Done report

Wired find_collision_suspects (T-2493) into `frob ticket waive-audit
scan --check-collisions`, opt-in and report-only per the coordinator's
explicit brief.

Preserved T-2493's sound-half constraint throughout: the flag only ever
runs a fresh, unscoped `frob check` gate pass to get the current KEPT
(unsuppressed) violation set, hands it plus the current waiver corpus to
the unmodified `find_collision_suspects`, and prints whatever it flags
as a SEPARATE section below scan's own watermark-scoped report --
`_render_collision_suspects` never mutates a waiver, never gates this
command's exit status, and is never folded into scan's own
AuditVerdict (a collision-suspect is not the same question as scan's
"what changed since the last watermark"). No "and clean up"/auto-drop
mode was added -- explicitly out of scope per the brief, would need its
own separate review.

The disclosed blind spot (a waiver whose site has ZERO current
violations anywhere is invisible to this check) is restated, not
hidden, in two places: the flag's own --help text (verified live via
`frob ticket waive-audit scan --help`) and the rendered "check-
collisions:" report line itself.

Removed find_collision_suspects's WIRE001 waiver (T-2493 left it
deliberately unwired; now genuinely wired) and added a frob:tests edge
pointing at this ticket's own new wiring-level test.

Widened scope: implicit_scope already grants config.py/__main__.py/
ticket_runner/__init__.py for FEATURE-kind CLI wiring (T-0446/T-1848);
also touched src/frob/app/_config_external.py (the --check-collisions
bool flag's _BOOL_FLAGS entry, the same argparse-to-AppConfig mapping
every other bool CLI flag in this file needs) and docs/modules/app.md
(the waive-audit doc section's own T-2496 addition).

Verification: added TestCheckCollisionsWiring (2 tests: suspects
rendered from a fake GateReport via monkeypatched frob.gates.run_gates,
and a gate-run failure is reported not fatal) -- 16/16 tests pass in
tests/unit/test_waive_audit_runner.py. Confirmed the flag's --help text
renders the disclosed blind spot live. `frob check --land-parity`:
clean, 0 unscoped errors, after adding two frob:ticket directives COV002
flagged on the changed function/test methods.

### Changed
```
 tickets/T-2496/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2496/src/frob/testing/_collect_kotlin.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2496/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PRE001@tickets/T-2496, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
