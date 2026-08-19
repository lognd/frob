## Done report

Changed:
- docs/modules/lang.md (new "Declared project identity (T-2195/T-2389)"
  section, frob:describes-anchored, after "Primitives")
- src/frob/lang/_nodes.py (declared_project_package_name,
  declared_source_prefixes: removed 2 frob:waive COV001 directives,
  added 2 frob:doc directives pointing at the new anchor)

Verified before starting: both COV001 waivers cited T-2618 by name as
the promised doc-anchor follow-up (grep confirmed on both sites); no
follow-up ticket for this had ever been filed (searched tickets/ for
declared-source-prefixes-t-2389/declared_source_prefixes/
declared_project_package_name -- only T-2389's own ticket/done-report
referenced them, matching the ticket body's own claim).

Positive control: `frob check --ticket T-2618 --only gates-fast` before
this change reported 39 errors including 2 COV001 findings at
src/frob/lang/_nodes.py:96/123 (the two undocumented functions). After
adding the doc section and the two frob:doc directives, the same run
reports 39 errors again -- both COV001 findings gone, and DOC002
resolves the new anchor cleanly (no "anchor does not resolve" finding).
Reverting the new lang.md section locally reproduces both COV001
findings, confirming the section closes the edge rather than the
finding having moved.

Evidence: `tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches` (pytest node id, PASSES both before and after
this change). Confirmatory-only -- `--check-repro` reports
PASSED_AT_PARENT, expected for a docs-only ticket with no own pytest
surface (T-0167 doc-ticket evidence precedent, playbook section 5, most
recently applied by T-2620/T-2662). T-2618's `kind` is `docs`, not
`bug`/`security`, so BUG002 does not apply -- no waiver needed or added.

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-2618 --only gates-fast` clean of
COV001/DOC002 on the two touched symbols; the 39 pre-existing repo-wide
errors are unrelated ledger/anchor/config-drift findings, identical
count before and after this change.

### Changed
```
 tickets/T-2618/ticket.md | 15 ++++++++++++++-
 1 file changed, 14 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, LANG004@src/frob/lang/_support.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2618, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
