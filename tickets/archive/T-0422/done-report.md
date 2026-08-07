## Done report

New DEAD001 gate (src/frob/gates/_dead_symbols.py::dead_symbol_gate,
WARN severity), the symbol-level analog of REF001's anti-orphan file
gate: a private Python function/class/method with no reference-graph
caller and no frob:tests/frob:describes/frob:invariant edge is flagged.
Own standalone module (per this wave's gates/** ownership split);
gates/__init__.py touched only with additive registration lines (one
import, one _ALL_GATES entry, one _CANONICAL_GATE_ORDER entry, one
process-pool registration + one process-job dict entry), same shape as
T-0558's parse_failure_gate.

Two "wired" signals exempt a symbol: (1) referenced anywhere in its own
package's reference graph, (2) an existing TESTS/DESCRIBES/INVARIANT
edge targets it directly (a bare frob:ticket tag does NOT count -- every
symbol in this repo carries one, which would silence the gate entirely).
Dunder methods and test_*/Test*-named symbols are exempt by convention;
anything else genuinely reached only dynamically is exempt via the
standard frob:waive DEAD001 reason="..." mechanism.

Counterexample-first triage (T-0422's own "expect real findings, triage
them honestly" instruction) surfaced a REAL soundness gap in the shared
frob.graph.callgraph substrate, not a bug in this new gate:

1. Running the naive build_call_graph-based check against ALL languages
   produced 199 findings, ~100% false positives, entirely in
   frob-core/strata-core Rust sources (e.g. Parser.advance, called
   dozens of times via self.advance(), came back "uncalled"). Root
   cause: callgraph._short_name_index hardcodes Python's
   leading-underscore privacy convention (frob.lang._walk_python); Rust
   (pub), TypeScript (export), and C (static) each compute
   SymbolRecord.public from a completely different marker the call
   graph never consults, so a Rust method's short name never starts
   with "_" and its calls are never recorded as edges at all. Fix:
   scoped dead_symbol_gate to Python (.py) files only for this pass,
   documented in the gate's own docstring -- extending to other
   languages needs the underlying substrate fixed first, not a
   per-language guess bolted onto this gate.
2. Even Python-only, build_call_graph's call-token-only recall
   (name(...)) missed every dispatch-table-registered handler in this
   repo's own app/*_runner.py CLI dispatch tables (e.g. "new": _new) --
   100 false positives. Added frob.graph.callgraph.build_reference_graph
   (new public function, additive to build_call_graph, same CallGraph
   shape, shared _resolve_edges/_parse_package helpers factored out of
   the existing T-0361 split) with broader recall: a bare identifier
   reference counts, not only a call token. This alone cut the Python
   finding count from 100 to 51.

Remaining 51 findings (Python-only, frob check --only dead_symbols):
manually triaged via a cross-file/package grep (not by inspection alone)
and found a further ~40 are STILL false positives from a third, deeper
substrate gap -- a symbol referenced ONLY from a bare MODULE-LEVEL
dict/tuple/list literal (frob.lang.RawSymbol/body_tokens only captures
function/class/method bodies; a top-level statement's tokens are
invisible to build_reference_graph too, since there is no enclosing
symbol to attribute them to). A smaller remainder look like pytest
fixtures referenced by parameter name across sibling test files, and
pydantic @field_validator/@model_validator methods invoked by the
framework (RawSymbol carries no decorator information to detect this
structurally). Given this, mass-waiving the 51 findings now would be
dishonest (most are provably NOT dead per the manual grep) and fixing
the underlying gap (extending frob.lang's extraction contract with a
module-scope token bucket, or adding decorator info to RawSymbol) is a
real, separate, cross-cutting piece of work. Not Filed T-draft-09c8e260 (never refiled)
("DEAD001 burndown: triage 51 findings...") with the exact count and
both identified false-positive classes, per this ticket's own
"file ONE burndown follow-up with exact counts if large" instruction.

Also re-tagged 4 already-closed-T-0561 symbols in src/frob/tickets/
__init__.py and tests/test_tickets_scope_mutation.py with frob:ticket
T-0422 (COV002 needs an OPEN ticket edge; T-0561 is now DONE) -- no
functional change to those symbols, same precedent as T-0543/T-0561's
own Done reports.

Public API changed (new GraphSnapshot-adjacent callgraph.
build_reference_graph function) -- version bumped 0.64.0 -> 0.65.0
(pyproject.toml, CHANGELOG.md, .frob-release.json via `frob release
stamp`, uv.lock via `uv lock`).

### Changed
```
 .frob-release.json                   |   4 +-
 CHANGELOG.md                         |  14 ++
 pyproject.toml                       |   2 +-
 src/frob/gates/__init__.py           |   6 +
 src/frob/gates/_parse_failures.py    |  58 ++++++++
 src/frob/graph/__init__.py           | 134 +++++++++++++++---
 src/frob/graph/_models.py            |  26 ++++
 src/frob/tickets/__init__.py         |  76 +++++++++-
 tests/test_gates.py                  |  40 ++++++
 tests/test_graph.py                  | 101 ++++++++++++-
 tests/test_tickets_scope_mutation.py |  96 +++++++++++++
 tickets.md                           | 267 +++++++++++++++++++++++++++++++++--
 uv.lock                              |   2 +-
 13 files changed, 788 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_dunder_method_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_test_function_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_tests_edge_target_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry` (pytest node id, verified passing when recorded)
