## Done report

Changed:
- src/frob/strata/_selfconform.py (import reorder only)
- src/frob/strata/_selfconform_binding_rules.py (import reorder only)
- src/frob/strata/_selfconform_core_rules.py (import reorder only)
- src/frob/strata/_selfconform_kinds.py (import reorder only)
- src/frob/strata/_selfconform_models.py (import reorder only)
- src/frob/strata/_selfconform_surface_rules.py (import reorder only)

Fixed via `FROB_SUGGEST_ACK=1 uv run ruff check --select I001 --fix
src/frob/strata/_selfconform*.py` -- 7 errors fixed, 0 remaining. Pure import
reordering, zero logic/behavior change (T-2729's split landed these 6 modules
with unsorted import blocks; T-2373's own I001 WARN->ERROR promotion caught
it correctly the moment it appeared).

Verified per the coordinator's caution about via-scoped capability grants in
design/frob.strata: ran `frob check` and confirmed zero new SYS003/SYS100
findings in any of the 6 touched files (import reordering does not change
which modules are imported, only the order of the import statements, so this
was expected but checked rather than assumed).

Also found and filed (out of scope, not fixed here): T-2842 -- a malformed
`frob:waive LARGE001` directive in src/frob/arch/_patterns.py:129 (embedded
escaped double-quote in the reason text breaks the directive parser,
surfacing as a WARNING on every `frob check` run). Landed by T-2359,
unrelated to this ticket's scope.

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(collected + passed fresh this session; this is a pure lint-fix ticket with no
pytest surface of its own -- ruff's own I001 rule has no dedicated gate test
in this repo -- so the CLI-dispatch integration test is bound per the
playbook's docs-only-ticket convention).

Gates: `frob check --json` (unbudgeted, FROB_NO_GATE_CACHE=1, gate-summary
present) -- I001 = 0 findings REPO-WIDE (not just in these 6 files), no other
I001 findings existed anywhere else to report. Ticket-scoped check
(--ticket T-2841) shows only pre-existing PERF004 findings in
_selfconform_binding_rules.py/_selfconform_surface_rules.py (present before
this fix, sort()-in-a-loop findings unrelated to import order) -- zero new
errors introduced by this diff.

### Changed
```
 tickets/T-2841/ticket.md | 25 +++++++++++++++++++++++--
 1 file changed, 23 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 22 error(s), 626 warning(s), 748 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DSL001@src/frob/arch/_patterns.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
