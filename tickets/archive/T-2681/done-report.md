## Done report

Added `frob ticket unblock <id> --by <blocker>`, mirroring `block`'s own
argument shape and CLI-layer structure exactly (same `--by` validation via
`is_valid_ticket_ref`, same load-then-`write_ticket` shape, same
`--no-commit` flag), except the membership check is inverted: refuses
loudly (SystemExit(1)) if `--by` is NOT currently in `blocked_by`, the
mirror of `block`'s own T-2216 duplicate-append refusal. Removes exactly
the one named edge, leaving any other blocker on the same ticket intact.

Deliberately does NOT let a live/open blocker be routed around: `unblock`
corrects a wrong or obsolete `blocked_by` edge (T-2076/T-1599's actual
incidents -- a blocker survived rescoping, or was deliberately deferred
and made obsolete), never a way to force work to start against a real
blocker. A `blocked_by` pointing at a DONE ticket is already not an open
blocker per `_open_blockers`, unaffected either way.

Found and fixed during end-to-end verification (not caught by the unit
tests alone, which construct/call `_unblock` directly): a new dispatch
verb needs a `LEDGER_VERB_STRATEGY` entry (T-2603) or the real CLI path
crashes with an unhandled KeyError AFTER the ledger write already
succeeded -- `frob ticket unblock` correctly removed the edge, then blew
up on `ledger_write_strategy_for("unblock")`. Registered as
`GENERIC_COMMIT_MIRRORED`, the same strategy `block` already carries
(same field, same fleet-visibility need).

Changed:
src/frob/app/ticket_runner/_lifecycle.py::_unblock (new)
src/frob/app/ticket_runner/__init__.py (import + __all__ + dispatch table)
src/frob/app/ticket_runner/_ledger_mirror.py::LEDGER_VERB_STRATEGY (new "unblock" entry)
src/frob/_cli_parsers/_ticket/_closeout.py::_add_ticket_attach_and_lifecycle_end_parsers (new `unblock` subparser)
docs/modules/tickets-lifecycle.md (documents the new verb + the KeyError-on-real-dispatch lesson)

Evidence:
tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_removes_edge
tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_when_not_present
tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_invalid_ref
tests/test_ticket_lifecycle.py::TestBlockThenUnblockRoundTrip::test_block_then_unblock_round_trips

Manual end-to-end verification (real CLI, scratch git repo, not this
repo's own ledger): `frob ticket new` x2, `frob ticket block T-0001 --by
T-0002` (blocked_by=['T-0002']), `frob ticket unblock T-0001 --by
T-0002` (blocked_by=[]) -- and both refusal paths (not-currently-blocked,
malformed --by) confirmed via the real CLI, each exiting 1 with
blocked_by left byte-for-byte untouched.

Filed: none

Gates: gate:AFFECT clean (0 errors) in `frob check --only affect_drift
--only drift --only docanchor --only fmt`; the DOC002/DRIFT001/CLAUDE001
findings in that same run are pre-existing, in files outside T-2681's
scope, unrelated to this change. FMT001 is a warning only (directive
line wrap), already `frob fmt`-clean on the touched file; `land`
absorbs `frob fmt` automatically regardless.

### Changed
```
 tickets/T-2681/ticket.md | 26 +++++++++++++++++++++++++-
 1 file changed, 25 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_removes_edge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_when_not_present` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_invalid_ref` (pytest node id, verified passing when recorded)
- `tests/test_ticket_lifecycle.py::TestBlockThenUnblockRoundTrip::test_block_then_unblock_round_trips` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 46 error(s), 985 warning(s), 680 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DUP001@tests/test_ticket_lifecycle.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2706/src/frob/_cli_parsers/_ticket/_closeout.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2681, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
