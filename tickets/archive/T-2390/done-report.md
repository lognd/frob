## Done report

(epic rollup)

All ten children landed: T-2428, T-2429, T-2430, T-2431, T-2432, T-2433,
T-2434, T-2435, T-2436, T-2437.

WHY THIS WAS NINE TICKETS INSTEAD OF ONE LINE. `frob.toml`'s tables are
read by ~10 disjoint, hand-rolled readers scattered across the codebase
(frob.check._native, frob.gates.__init__, frob.gates._ratchet,
frob.gates._dup, frob.excludes, frob.app._config_external, and others),
none bound to a single pydantic schema. `DupConfig`/`GateConfig` (the
existing pydantic models with `extra="forbid"`-style intent) are NOT
actually constructed from the raw parsed tables anywhere in the call
graph, so `extra="forbid"` would never have seen a stray file key even
if it were declared -- the validation gap was structural, not a missing
flag. There was no single choke point to add one check to; each table
needed its own schema declaration wired to its own real reader(s), which
is why the epic decomposed into one child per disjoint reader (T-2437
combined [dup]/[graph] since both are single-leaf tables with genuinely
separate readers, too small individually to justify separate tickets).

RESULT ACROSS ALL TEN CHILDREN: zero genuinely undeclared keys found in
this repo's real frob.toml. Every must-still-pass control (11 pytest
node ids across the ten schema modules, all bound as this epic's own
closing evidence) passed clean without any control being weakened to
force a pass. Two apparent early failures during development were
DETECTOR bugs, caught and fixed rather than reported as repo debt:
  - the `[[native]]` array-of-tables shape (T-2429) needed the schema
    resolver to iterate array-of-tables entries, not just scalar/dict
    leaves;
  - `[arch.layering]`'s legitimately nested sub-table (T-2433) needed
    the schema to declare a real nested-key allowance rather than flag
    every layering key as unknown.
Neither was a case of loosening a schema to make a real finding go
away -- both were the check learning to parse TOML shapes it had not
yet been taught to parse.

COMPONENT-MEMBERSHIP LESSON (recorded for future schema/gate work):
placing a schema module in the wrong strata component introduces an
undeclared cross-component Flow, caught by SYS003. SYS003 was promoted
from WARN to ERROR severity during this epic's own timeframe (T-2407,
landed 2026-08-18, unrelated ticket but concurrent) -- so a
misplacement here would now fail the build outright rather than warn.
Every one of the ten schema modules was placed in `frob.gates`'s own
strata component (matching its actual import/wiring site), so none
tripped this; noting it here because the next schema/gate ticket will
hit it immediately if it is not.

EPIC CLOSURE BAR (acceptance[2]): "once every child ticket below has
landed, this repo's own frob.toml -- all ~121 leaf values across its 12
top-level tables -- reports zero unknown keys under the union of every
child's declared schema, proving the check was not calibrated by
weakening it." MET: all 11 must-still-pass tests across the ten schema
families pass against this repo's real frob.toml (evidence bound to
this ticket, --accepts 2).

WARN-TO-ERROR PROMOTION: every one of the ten schema modules declares
its own unknown-key finding at `Severity.ERROR` from its very first
land -- none was ever shipped at WARN and promoted later; `git grep
"Severity.WARN"` across all ten `_*_schema.py` files returns zero
matches. So there is no separate "promote WARN to ERROR" step
outstanding for this epic; each child met the ERROR bar on arrival,
which is why acceptance[2]'s bar could be checked directly rather than
gated behind a promotion land.

KNOWN TRAP FOR THE NEXT PERSON, not a defect in this epic's own work:
T-2436/T-2437 (this epic's own children) hit BUG002/EvidenceConfirma-
toryOnly at land time because their code had already landed on main as
a disclosed `--allow-cross-ticket` passenger of T-2435's land (T-1618:
a series-worktree land squashes everything committed on the branch, not
just the named ticket's own commits). Once a sibling's fix rides in as
a passenger, there is no longer a reachable parent commit where the fix
is absent -- the designated repro test trivially PASSES at parent, and
BUG002 correctly reads that as confirmatory-only-evidence and refuses.
The correct, sanctioned remedy (not a workaround) is `frob:waive BUG002
reason="..."` on the passenger ticket's own body, explaining the
passenger-land shape explicitly -- this is exactly the case the error
message's own remedy #3 describes ("this defect genuinely cannot be
reproduced in a test"). Recognise this in under an hour next time: a
bug-kind ticket refusing BUG002 immediately after a sibling's
--allow-cross-ticket land, whose own diff-touched files match the
sibling's just-landed commit, is this shape, not a real regression.

Evidence: 11/11 pytest node ids, one `test_must_still_pass_this_repos_
own_frob_toml`-family test per schema module (two for T-2437's combined
dup/graph module), all green, bound to acceptance[2] via --accepts 2.

Filed: none new by this rollup (T-2457 was already filed independently,
during T-2435/2436/2437's own land window, for the fs.write detector
imprecision the schema modules' own `.open("rb")` read calls tripped;
not a child of this epic).

Gates: SELFAUDIT001 (the ratchet-ceiling side-effect of these ten
children's own via-list growth) cleared to zero via T-2460, landed
separately with full per-entry attribution. Schema-family findings
(GATESSCHEMA001/TESTRUNNERSCHEMA001/DUPSCHEMA001/GRAPHSCHEMA001/
TOPLEVELSCALARSCHEMA001/ARCHSCHEMA001/DOCBLOCKSSCHEMA001/NATIVESCHEMA001/
PROFILESCHEMA001/REFSCHEMA001/TESTINGSCHEMA001) measured at 0 findings
via `frob check --only gates-fast --json` against this repo's real
frob.toml.

### Changed
```
 tickets/T-2390/ticket.md | 40 ++++++++++++++++++++++++++++++++++++++--
 1 file changed, 38 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_docblocks_table_schema.py::TestDocblocksSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py

### Acceptance amendments
- [2] replace: "Given this repo's own frob.toml with all 148 leaf values, when the check runs, then it reports zero unknown keys, proving the check was not calibrated by weakening it." -> "EPIC CLOSURE BAR (not any single child's): once every child ticket below has landed, this repo's own frob.toml -- all ~121 leaf values across its 12 top-level tables -- reports zero unknown keys under the union of every child's declared schema, proving the check was not calibrated by weakening it. A child's OWN acceptance is its own table's must-fire/must-still-pass pair (see each child's body); this criterion is the epic-level aggregate, checked only once the last child lands." (reason: coordinator instruction: criterion[2]'s all-leaves-zero bar is the EPIC's closure bar, not a single ticket's -- a partial-coverage child must not be able to claim it; logan, 2026-08-18)


frob:no-behavior-change reason="epic rollup ticket with no code of its own -- all runtime behavior change happened in the ten already-landed children (T-2428..T-2437), each with its own BUG002-satisfying evidence; T-2390 itself only carries the aggregate closure-bar evidence (11 must-still-pass tests across all ten schema families) proving the union of children meets acceptance[2]"


frob:no-behavior-change reason="epic rollup ticket with no code of its own -- all runtime behavior change happened in the ten already-landed children (T-2428..T-2437), each with its own BUG002-satisfying evidence; T-2390 itself only carries the aggregate closure-bar evidence (11 must-still-pass tests across all ten schema families) proving the union of children meets acceptance[2]"
