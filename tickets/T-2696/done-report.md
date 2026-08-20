## Done report

Populated `Violation.symref` for PII010/011/012, closing the dormant
over-forgiveness hole T-1666 identified (93 raw violations, 21
(rule,file) pairs carrying 2+ findings under file-scope match).

## Confirmed the gap was real, not by-design

Read `Violation.symref`'s own docstring (src/frob/gates/_models.py)
first, per this ticket's own instruction: it explicitly names PERF,
TEST005, and TEST006 as intentionally file/module-scoped rules where
"a file-level waiver is the correct and intentional precision, not a
shortcut." PII010/011/012 are never named there -- the docstring gives
no design basis for their file-scoping, confirming this is the same
structural gap CACHE001/OPAQUE001 had (T-1659's precedent), not a
legitimate close-as-designed.

## Fix

`enclosing_qualname` (new, `src/frob/gates/_pii_structural/_node_index.py`)
resolves the tightest-enclosing class/function's dotted qualname for a
given line, reusing the SAME `_NodeIndex` bucketing pass (`_build_node_
index`, T-1209) every PII sub-scan already builds -- no second `ast.walk`,
no file re-parse, no new dependency. This is a BETTER precedent than
either this ticket's own suggested approach (a GraphSnapshot-based
lookup) or the closest existing analog I found (`frob.gates._opaque.
_enclosing_qualname`, T-1659 -- which re-parses the file via `frob.lang.
parse_file`): the PII scanners already hold a fully-parsed `ast.Module`
plus a pre-built `_NodeIndex` in every call, so the enclosing symbol is
resolvable from data already in hand, at zero extra parse cost. Said so
explicitly rather than silently building the ticket's own suggested
GraphSnapshot-threading version, per this series' standing instruction
to flag a filer's suggested approach when a better one is found, with
the measurement.

Threaded through the 3 constructors that actually have live findings
(measured first: `pii_structural_gate` currently reports 30 PII010/011/
012 violations repo-wide, ALL in `.py` files -- the TS/Rust PII010 path
in `_crosslang.py` has zero live findings, so it was NOT touched; this is
a disclosed, measured scope decision, not an oversight):
- `_python_fields.py::_pii010_violation` (+ its 4 call sites across
  `_scan_class_fields`, `_scan_orm_columns`, `_scan_ddl_strings`)
- `_emails.py::_pii011_violation`
- `_keywords.py::_pii012_violation` (+ its 2 call sites, identifier sweep
  and comment-keyword sweep)

Live-verified against this repo's own tree: 28 of 30 PII010/011/012
violations now carry a real symref (e.g. `StateCapture`, `_DaemonServer`);
the remaining 2 are genuinely module-level sites (a module docstring
comment, a top-level list-literal field) where `symref=None` is the
CORRECT answer, not a miss -- confirmed by reading both sites directly.

## Consequence measured and disclosed, not silently absorbed

Re-ran `pii_structural_gate` through the real `run_gates` waiver-matching
path per this ticket's own final instruction. Symref population made
waiver matching symbol-exact wherever it resolves (`_match_waiver`'s
T-2438 `_canonical_symref` path) -- unwaived PII010/011/012 findings went
from 1 (T-1666's baseline) to 20, since most existing `frob:waive`
comments were matching only via the old file-wide fallback. Did NOT
re-triage these 20 myself: this ticket's own body explicitly keeps the
fix separate from any classification/re-waive pass, mirroring the T-1659
(fix) / T-1666 (classify) precedent it names for OPAQUE001. Filed the
follow-up (draft id below; real id after land) with the measured count
and per-site discipline instructions rather than rushing 20 individual
waiver decisions under this ticket's own scope.

Changed:
src/frob/gates/_pii_structural/_node_index.py::enclosing_qualname
src/frob/gates/_pii_structural/_python_fields.py::_pii010_violation
src/frob/gates/_pii_structural/_python_fields.py::_scan_class_fields
src/frob/gates/_pii_structural/_python_fields.py::_scan_python_fields
src/frob/gates/_pii_structural/_python_fields.py::_scan_orm_columns
src/frob/gates/_pii_structural/_python_fields.py::_scan_ddl_strings
src/frob/gates/_pii_structural/_emails.py::_pii011_violation
src/frob/gates/_pii_structural/_emails.py::_scan_python_email_values
src/frob/gates/_pii_structural/_keywords.py::_pii012_violation
Filed: T-2712 (real id after land)

### Changed
```
 rapid-debt.jsonl                                 |   2 +
 src/frob/gates/_pii_structural/_emails.py        |  25 ++++-
 src/frob/gates/_pii_structural/_keywords.py      |  32 ++++++-
 src/frob/gates/_pii_structural/_node_index.py    |  40 ++++++++
 src/frob/gates/_pii_structural/_python_fields.py |  56 +++++++++--
 tests/test_pii_structural_gate.py                | 117 +++++++++++++++++++++++
 tickets/T-2696/done-report.md                    |  93 ++++++++++++++++++
 tickets/T-2712/ticket.md               |  76 +++++++++++++++
 8 files changed, 423 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestSymrefPopulation::test_class_field_symref_is_class_dot_none_shape` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPopulation::test_orm_column_inside_method_symref_is_nested_dotted` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPopulation::test_email_literal_inside_function_symref_is_function_name` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPopulation::test_keyword_sweep_identifier_symref_is_function_name` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPopulation::test_module_level_field_symref_is_none` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPopulation::test_enclosing_qualname_nested_method_is_dotted` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPopulation::test_enclosing_qualname_module_level_is_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 45 error(s), 758 warning(s), 682 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2696/src/frob/gates/_fix_engine.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2696/src/frob/gates/_pii_structural/_node_index.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2696, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
