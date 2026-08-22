## Done report

Scope declaration gap closed: docs/modules/gates.md added to T-2028's
scope (recorded in ticket frontmatter scope_changes, actor=logan,
2026-08-10, once T-1964's lease on the file landed at 76b249405). The
frob:doc anchor content this ticket exists to cover
(#data-models/#rule-catalog, describing
src/frob/gates/_arch.py::arch_examined_sites/arch_gate and
src/frob/gates/_coverage_sites.py::attach_examined_sites/
is_family_instrumented/site_examined) already existed in
docs/modules/gates.md from T-1921 -- no doc content change was needed,
only the scope declaration itself.

Verified: `frob check --only scope --ticket T-2028` reports
`gate:SCOPE 0 errors, 307 warnings` (pass) -- the SCOPE002 gap this
ticket targeted no longer fires as an error-shaped finding; the
remaining 307 warnings are unrelated symbols under the same doc file's
broad anchor surface, expected per SCOPE002's own design as a nudge,
not a hard block (docs/modules/gates.md#scope002-t-0998).

Filed T-2301 (relocate-vs-widen decision for the two
archgate-specific tests in tests/unit/gates/test_examined_sites.py)
rather than deciding it unilaterally inside this ticket: the cleaner
fix (moving TestAttachExaminedSites.
test_archgate_examined_sites_include_a_real_python_file/
test_archgate_examined_sites_exclude_an_unparseable_file into
tests/test_arch_gate.py) requires updating the frob:tests directives
at src/frob/gates/_arch.py:182-183, which is outside T-2028's own
declared scope (docs/modules/gates.md, tests/unit/gates/
test_examined_sites.py only) -- widening this ticket's scope to include
_arch.py to make that one decision is exactly the disproportionate
widening T-2012's own investigation already flagged and this ticket
was scoped narrowly to avoid.

No pytest surface of this ticket's own (a scope-declaration change to
ticket metadata, no source/doc content edit) -- per playbook section 5's
docs-only precedent, evidence is the existing CLI-dispatch integration
test.

frob:no-behavior-change reason="T-2028's only change is a ticket-metadata scope declaration (docs/modules/gates.md added to scope, recorded in the frontmatter scope_changes list) -- no source or doc content was edited, so there is no code-level defect for a repro test to reach; the designated evidence PASSING at both parent and fix is the expected, correct outcome for a metadata-only ticket, not confirmatory-only evidence of a missed fix."

### Changed
```
 tickets/T-2028/done-report.md      | 53 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2028/ticket.md           |  8 ++++--
 tickets/T-2301/ticket.md | 26 +++++++++++++++++++
 3 files changed, 85 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2028/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2028/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2028/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2028/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2028/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
