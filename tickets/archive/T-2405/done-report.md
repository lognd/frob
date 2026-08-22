## Done report

Changed:
src/frob/gates/_port_selfcheck.py::_tracked_gate_files
src/frob/gates/_port_selfcheck.py::port_selfcheck_gate

Evidence:
tests/unit/gates/test_port_selfcheck.py::TestPort001::test_strata_and_vet_are_scanned_since_t2405
tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_detector_package_code_never_scanned
(plus pre-existing 7 tests in the same file, all still passing, 9/9 total)

Filed: none

Gates: frob check --ticket T-2405 clean of new errors introduced by this
change (verified via JSON diagnostics filtered to touched files: 0 errors
against src/frob/gates/_port_selfcheck.py, docs/modules/gates.md,
tests/unit/gates/test_port_selfcheck.py -- the single remaining DOC008 hit
at gates.md:94 is a pre-existing draft-anchor drift unrelated to this
ticket's own new "## PORT001 (T-2388)" anchor, which now resolves).
frob ticket sweep T-2405 re-run clean (PRE001 resolved).

Summary: widened PORT001's scanned scope from src/frob/gates/** only to
frob.gates._detector_scope.DETECTOR_PACKAGE_ROOTS (src/frob/{check,gates,
strata,vet}/), reusing T-2466's shared, measured declaration rather than
inventing a second hardcoded scope (exactly the drift T-2466's own
docstring warned against). No optional pathspec keyword was needed on
tracked_python_files_for_gate -- its existing default (git ls-files --
src/frob) already covers every DETECTOR_PACKAGE_ROOTS prefix, matching
the no-new-keyword pattern LEXCHECK001 (T-2466) already established.

DELTA vs the ticket body's own 8-file grep-derived starting set: ran
PORT001's real AST detector (not grep) against all 8. Only 2 of 8 even
sit inside DETECTOR_PACKAGE_ROOTS (strata/_packs.py, strata/
_selfconform.py) -- the other 6 (tickets/_models.py, tickets/
_land_merge_zones.py, tickets/_new_gate_rule_acceptance.py, app/
ticket_runner/_land_cmd.py, app/ticket_runner/_new.py, refactor/
_repointer.py) sit in packages T-2466 measured as constructing zero
gate-shaped Violation(...) calls, so they are not part of this
detector's population at all -- the same class of exclusion arch/ got
from T-2466's own measurement. Of the 2 in-scope candidates, only
strata/_selfconform.py produced a real finding (PORT001-IDENT, line
1853); strata/_packs.py is clean. Widening the full scan (93 -> 213
tracked files) added exactly one more finding beyond that:
vet/_capability_scan.py (also PORT001-IDENT). Net repo count: 5 -> 7
violations, 0 new PORT001-PATH hits (promotion-bar burn-down target
unchanged), 2 new PORT001-IDENT hits (both real, both advisory,
verified by hand as genuine path-segment-tuple/f-string shapes, not
false positives).

app/_config_meta.py stays out of scope after the widening (app/ is not
a DETECTOR_PACKAGE_ROOTS member); gates/_pii_structural/_self_match.py
stays allowlisted (unchanged, its existing _ALLOWLIST entry). strata/
_compliance.py entered the scanned set but produces no hit, so no new
allowlist entry was needed -- documented in-file rather than silently
carved out for a hypothetical future hit.

Added docs/modules/gates.md "## PORT001 (T-2388)" section (previously
missing entirely -- the frob:doc anchor the code already pointed at did
not resolve to any heading; DOC002 caught this and it's now fixed as
part of this change) documenting both the original T-2388 shape and the
T-2405 widening.

### Changed
```
 tickets/T-2405/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_strata_and_vet_are_scanned_since_t2405` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_detector_package_code_never_scanned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2388, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t2405-t1599/src/frob/app/ticket_runner/_waive_audit.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
