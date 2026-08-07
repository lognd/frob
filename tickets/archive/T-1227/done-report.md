## Done report

Implemented frob:enumerates as a new comment-DSL verb (src/frob/graph/dsl.py)
that binds a doc span to a named collection literal (dict/set/tuple/
frozenset/Literal/ErrorSet/StrEnum), plus a new DOCENUM001 gate
(src/frob/gates/_docenum.py) that AST-diffs the doc-claimed member list
against the actual collection at check time, independent of frob ack state --
a stale claimed-members list fires even if the doc line was previously acked.
frob:enumerates edges carry the claimed member set on the graph edge
(src/frob/graph/_models.py) so DOCENUM001 can diff without re-parsing the doc
each run.

Bound the initial adoption wave named in the ticket: agent-playbook.md's
_STAGE_GROUPS table, sys-export-formats.md's _EXPORT_FORMATS,
gitlog.md's _TYPE_LABELS, ticket-kinds-states.md's TicketState + TicketKind
(4 of 5 collections named at ticket-open time; see disclosed gap below for
the fifth). Regression corpus (tests/test_docenum_gate.py) exercises the
acceptance criterion directly: a stale claimed-list fires DOCENUM001, the
corrected list passes clean, plus malformed-shape and
unresolvable-shape-is-disclosed-not-silently-passed cases. dsl-level parsing
covered in tests/test_graph.py and tests/unit/graph/test_dsl.py.

Disclosed gaps (both noted in-ledger, not silently dropped):
1. argparse choices lists (cycle.md/xref.md --lang, parse.md tool table)
   are not resolvable by the current AST-based _extract_members -- it walks
   named collection literals only, not an argparse add_argument(choices=...)
   call tree. Needs either the DOC004-style live-argparse-tree approach
   frob.gates._docblocks already uses, or an _extract_members extension for
   the ast.Call shape. Not attempted here; scope stays with the collection-
   literal binder this ticket described.
2. The remaining drift-lock candidates from
   docs/audits/docs-staleness-2026-07-29.md's Drift-lock candidates section
   (test-runner-entries.md, install.md DERIVED_ARTIFACTS,
   compliance-registry.md checkers, litmus-fixtures.md,
   agentic-workflow.md TEST001-006, registry/README.md entry counts,
   sys.md seccomp table, deploy.md allowlist, cycle.md, app.md STATE_STYLE,
   and the clean/decisions/fleet/fuzz/dup/cve/graph/lang/mutate/perf/
   process/render/stats/strata/serve/roadmap/host/krb/surface/threat/
   reliability member tables) still need frob:enumerates bindings added one
   doc at a time -- the mechanism exists and is proven on 4 collections; the
   remaining bulk-adoption pass is follow-up work, not part of this
   mechanism ticket's acceptance criteria (which named the initial-wave
   binding, not the full candidate list).

Round 2 (resuming a killed OOM session, this commit only): merged main
forward (T-1278's TEST005 burn-down landed since), re-ran the ticket-scoped
gate check, and closed every finding attributable to this ticket's own
code: split _docenum001_violation_for_edge into three smaller helpers
(ARCH001, was 73 lines against a 60-line threshold), reworded the DRIFT001-
comparison sentence in the module docstring to drop an unbound "only"
exclusivity claim (INV006), added docenum001_gate + TestDocenum001Gate
interface declarations to design/frob.strata (SELFAUDIT001 -- extended
T-1227's scope to cover design/frob.strata for this, since the
interface= attrs live there), and sorted gates/__init__.py's import block
(ruff I001). `frob check --ticket T-1227` is clean across gates-fast/
gates-native/gates-security modulo two pieces of expected noise: OPAQUE001
on src/frob/app/__init__.py and app.py (pre-existing on main before this
ticket touched anything, unrelated files, confirmed via `git show
55ce2eeb:src/frob/app/__init__.py`), and a SCOPE001 flag on
tests/test_lang_conformance_gate.py (that file is T-1234's own declared
scope, not T-1227's -- an artifact of running a per-ticket check against a
shared multi-ticket worktree branch, not a real gap in either ticket).

Also fixed one blocking finding to unblock T-1234's own close in the same
session: docs/modules/strata.md:230 used the literal string "T-1234" as an
illustrative waiver example (coincidentally the sibling ticket's own id),
which tripped LiveTrackerCited and refused T-1234's close. Retargeted the
example to the repo's existing T-9999 placeholder convention (already used
by tests/test_tickets_brief.py and others). docs/modules/strata.md is
already covered by this ticket's docs/** scope glob.

### Changed
```
 design/frob.strata                              |   4 +
 docs/commands/gitlog.md                         |   1 +
 docs/guides/agent-playbook.md                   |   1 +
 docs/guides/extending/comment-dsl-directives.md |   6 +-
 docs/guides/extending/sys-export-formats.md     |   1 +
 docs/guides/extending/ticket-kinds-states.md    |   2 +
 docs/modules/gates.md                           |  27 +++
 docs/modules/graph.md                           |  12 +-
 docs/modules/strata.md                          |   2 +-
 src/frob/gates/__init__.py                      |   6 +
 src/frob/gates/_docenum.py                      | 301 ++++++++++++++++++++++++
 src/frob/gates/_lang_conformance.py             |  16 +-
 src/frob/gates/_waive.py                        |   3 +
 src/frob/graph/_models.py                       |  12 +
 src/frob/graph/dsl.py                           |  55 +++--
 tests/test_docenum_gate.py                      | 116 +++++++++
 tests/test_graph.py                             |  34 +++
 tests/test_lang_conformance_gate.py             |  28 ++-
 tests/unit/test_check.py                        |   4 +-
 tickets.md                                      | 214 ++++++++++++++++-
 20 files changed, 815 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_stale_claimed_list_fires` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_corrected_claimed_list_passes` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_stale_extra_claimed_member_fires` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_strenum_members_extracted` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_malformed_target_shape_fires` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001Gate::test_unresolvable_shape_is_disclosed_not_silently_passed` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestDsl::test_enumerates_verb_binds_bare_doc_anchor_target` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestMarkdownAnchors::test_enumerates_edge_carries_claimed_members` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 2 error(s), 3121 warning(s), 678 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py
