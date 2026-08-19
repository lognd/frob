## Done report

Added real documentation table rows for six of the seven ids T-2613's
member-list sync left undocumented: CYCLE001, MILE001, MILE002, MILE003,
MILE004, TICK012. WAIVE009 already got its own row from T-2639 (landed
mid-way through this ticket, merged into this worktree before writing
these rows) -- verified no duplicate needed by grepping for an existing
`| WAIVE009 |` row before adding anything.

Each row was written from the real gate implementation (src/frob/check/
_python.py for CYCLE001, src/frob/gates/_milestone.py for MILE001-004,
src/frob/gates/_tickets_gate.py for TICK012), not guessed from the id --
severity, stage name, and the actual trigger condition/exemptions all
read from the docstrings and code, matching the surrounding table's
existing one-line-with-parenthetical-severity-and-ticket-ref shape (see
e.g. GATESSCHEMA001/WIRE001 rows, which this follows).

Judgment on DOCENUM001 itself (per the brief): the gate only diffs the
`frob:enumerates` members= list against the real `_KNOWN_GATE_RULES` set
-- it never checks that a listed member has an actual documentation row
or section anywhere in the file. That is a real, demonstrated gap: three
of the seven ids (MILE001, MILE002, and WAIVE009 before T-2639 landed)
sat with zero documentation while DOCENUM001 read clean throughout,
exactly the same "gate proves nothing about the thing it exists to
protect" shape as WAIVE009 being defined-but-unwired this same session.
Filed T-2664 (scope docs/modules/gates.md +
src/frob/gates/_docenum.py) proposing DOCENUM001 also require a
resolvable row/section per member, rather than fixing it here -- it is a
gate-CONTRACT change (widens what passing requires), out of this docs-
only ticket's scope, and deserves its own scoped review per the brief's
own instruction not to implement it inline.

Evidence is confirmatory-only, expected for a docs-only ticket with no
own pytest surface: `tests/integration/test_interfaces.py::
TestInterfaces::test_main_cli_dispatches` already PASSES at the parent
commit (--check-repro confirmed PASSED_AT_PARENT). T-2662's own `kind` is
`docs`, not `bug`, so BUG002 does not even apply here -- no waiver
needed, recorded per the T-0167 doc-ticket evidence precedent (playbook
section 5) instead of inventing a test.

Positive control: `frob check --only docanchor --only decisions --ticket
T-2662 --delta` produces zero findings whose file is docs/modules/
gates.md; the 3 pre-existing DOC002 errors it reports (2 unresolvable
draft-id refschema001 anchors, 1 stale mile004 anchor in
tickets-data-storage.md) are all pointer-side breakage in files this
ticket's scope does not cover, predating this change (confirmed via
`git log -1` on their owning source files, both last touched by
unrelated tickets T-2390/T-2580).

### Changed
```
 tickets/T-2662/ticket.md           |  6 +++-
 tickets/T-2664/ticket.md | 69 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 74 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2662, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
