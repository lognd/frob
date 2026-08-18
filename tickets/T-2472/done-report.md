## Done report

Added the `## GATERULE001 (T-2448)` catalog entry to
`docs/modules/gates.md`, right before `## Public API`, matching the
style of neighboring rule-catalog sections (e.g. `## LEXCHECK001`): a
`frob:describes` anchor on `gate_rule_registry_violations`, and prose
covering what `GATERULE001` checks, why it exists as a STANDING gate
(vs. the T-1956 ticket-scoped close/land preflight it complements), and
its `UNRESOLVED`-not-silent-zero posture (T-2391 fail-loudly) when
`src/` is missing or the scan crashes.

Could not complete the second half in the same pass (adding the
`frob:doc` edge on `gate_rule_registry_violations` and dropping the
`frob:waive COV001` above it): `src/frob/gates/_rule_id_scan.py` was
under T-2454's live in-progress lease for this ticket's entire working
window (checked repeatedly, still held). This ticket's own scope is
`docs/modules/gates.md` only; widening it to include
`src/frob/gates/_rule_id_scan.py` was refused by the lease conflict.
Filed T-2476 (scope `src/frob/gates/_rule_id_scan.py`) to finish the
edge + waiver-drop once the lease clears, with the exact two edits
spelled out.

Changed:
- `docs/modules/gates.md` (new `## GATERULE001 (T-2448)` section only)

Evidence: none required (docs-kind ticket, no code path changed;
`frob check --ticket T-2472` clean on `docs/modules/gates.md` -- the one
pre-existing DOC002 finding at line 94 is unrelated, a stale
`T-draft-...` anchor citation from a different ticket, not touched by
this diff)

Filed: T-2476 (finish the frob:doc edge + COV001 waiver drop once
T-2454's lease on src/frob/gates/_rule_id_scan.py clears)

Gates: `frob check --ticket T-2472` clean on `docs/modules/gates.md` (0
new errors attributable to this diff).

### Changed
```
 docs/modules/gates.md    | 30 ++++++++++++++++++++++++++++++
 tickets/T-2472/ticket.md |  2 +-
 2 files changed, 31 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/gaterule001-doc/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/gaterule001-doc/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/gaterule001-doc/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/gaterule001-doc/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/gaterule001-doc/src/frob/vet/_capability.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2472, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
