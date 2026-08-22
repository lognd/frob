## Done report

Changed:
  src/frob/gates/__init__.py (frob:waive LARGE001 only)
  src/frob/gates/_coverage.py (frob:waive LARGE001 only)
  src/frob/gates/_dead_symbols.py (frob:waive LARGE001 only)
  src/frob/gates/_debt_deprecated.py (frob:waive LARGE001 only)
  src/frob/gates/_docblocks.py (frob:waive LARGE001 only)
  src/frob/gates/_docblocks_refs.py (frob:waive LARGE001 only)
  src/frob/gates/_docptr.py (frob:waive LARGE001 only)
  src/frob/gates/_fix_engine.py (frob:waive LARGE001 only)
  src/frob/gates/_fix_engine_sync.py (frob:waive LARGE001 only)

Per-file disposition, T-1651-grade review (comment-only, no behavior change
in any of the 9):

  __init__.py       WAIVE -- module's own docstring: public gate functions
                    MUST stay here to keep frob:doc/frob:tests symrefs
                    stable; this is also the live source T-1072/T-1077/
                    T-1115/T-1140/T-1159/T-1170/T-1195 already
                    incrementally extract cohesive families FROM.
  _coverage.py      WAIVE -- one pipeline (parse -> stamp -> lock) for
                    TEST005/006/012; existing ARCH102 waiver already
                    establishes this precedent for the same file.
  _dead_symbols.py  WAIVE -- one gate (DEAD001), one algorithm, all 22
                    defs feed the single dead_symbol_gate entrypoint.
  _debt_deprecated.py  WAIVE -- module's own docstring: DEBT/DEPR
                    deliberately paired (DEPR001-004 mirror DEBT001-003
                    one-for-one, both feed the same REL001 check).
  _docblocks.py     WAIVE -- DOC005 explicitly reuses DOC004's
                    _console_trees/_project_namespaces infra (own
                    docstring); T-1195 already extracted the separable
                    per-language backend to _docblocks_refs.py.
  _docblocks_refs.py  WAIVE -- module's own docstring: this IS the T-1195
                    LARGE001 residue split already (per-language DOC004
                    checkers).
  _docptr.py        WAIVE -- one gate (DOC006/DOC007), six claim-kinds,
                    same shape as _dead_symbols.py, one gate function.
  _fix_engine.py    WAIVE -- module's own docstring documents the T-1646
                    three-way seam (graph-driven / line-scoped-text /
                    derived-artifact-sync); no further natural boundary.
  _fix_engine_sync.py  WAIVE -- sibling of the same T-1646 split, module's
                    own docstring documents its half of the seam.

NOT waived this batch: src/frob/gates/_doclink_docanchor.py. Real seam
found but not the one its own (stale) docstring describes: DOC001/DOC002
(doclink_gate/docanchor_gate) genuinely are one cohesive family per that
docstring, but docstatus_gate/docmake_gate/docseverity_gate were bolted
on later without updating it, and one of them (docstatus_gate) carries a
live frob:waive AFFECT001 flagging docs/modules/gates.md as under another
ticket's lease at write time -- needs a fresh doc-anchor/re-export check
before moving anything, not assumed from the stale docstring's claimed
import surface. Filed as T-2843 (renumbers at land), same shape
as T-2833/T-2834's "real seam blocked on out-of-scope verification, gets
its own ticket" precedent. Removed from THIS ticket's scope accordingly.

Re-measured (unbudgeted `frob check --only gates --json`, fresh worktree):
all 9 remaining files read severity=note (waived), 0 remain warning.
`_doclink_docanchor.py` still warning (unresolved, tracked in the new
ticket).

One waiver draft initially had an embedded double-quote inside its
reason= string (_docblocks.py) which the frob:waive DSL parser cannot
handle (breaks the reason at the first unescaped quote) -- caught via
re-measurement showing it still read as warning after insertion, fixed
by removing the inner quotes.

Test suite: full `tests/test_gates.py` re-run (unset FROB_WORKTREE/
FROB_AGENT first -- those env vars from `frob agent env` pollute several
tmp_path-isolated ticket tests with the real worktree's lease state,
producing WorktreeLeaseViolation failures that vanish once unset and are
unrelated to this diff). Result: 803/809 pass. The 6 failures
(TestWireGate::test_new_cli_dest_present_in_config_external_is_not_
flagged, TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_
passes_after, TestAutofixManifest::test_killed_mid_handler_leaves_
manifest_naming_completed_fixes, TestDoc004ConsoleCommandDrift::test_
real_subcommand_unanchored_warns_unbound, TestKnownGateRuleIds::test_
every_emitted_rule_literal_is_known, TestOptInGates::test_perf_gate_
still_reports_genuine_parse_failure) were independently reproduced on
unmodified main HEAD from the primary checkout before touching anything
-- pre-existing debt, not caused by this batch.

Evidence: 4 representative passing tests, one per waived gate family
(DEAD001, DEBT002, DOC007/TICK002 fix-engine, COV002) -- confirmatory
since this is a comment-only diff with no logic change; the full-suite
803/809 result above is the actual regression check.

Filed: T-2843 (Split frob.gates._doclink_docanchor's
later-bolted docstatus/docmake/docseverity gates out; real seam, needs
docs/modules/gates.md + tests/test_gates.py citation verification before
extraction, out of scope for this batch).

Gates: `frob check --only gates` unbudgeted, fresh worktree, confirms
0/9 files in this batch's final scope remain LARGE001 warning.

### Changed
```
 tickets/T-2828/ticket.md | 20 ++++++++++++++++++--
 1 file changed, 18 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_debt002_closed_ticket_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCov002ScopeCoverage::test_open_ticket_scope_covers_changed_symbol` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 30 error(s), 1082 warning(s), 758 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform_core_rules.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform_kinds.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform_binding_rules.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform_core_rules.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform_kinds.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform_models.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2828/src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2828, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
