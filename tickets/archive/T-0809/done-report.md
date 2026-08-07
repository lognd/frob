## Done report

Built (both mechanisms the ticket scoped):

1. Real callee-resolution wiring: `build_call_graph(root, paths, *,
   mark_unresolved=False)` -- opt-in, NOT the default. When
   `mark_unresolved=True`, a call target whose short name starts with `_`
   (looks like this module's own private-symbol convention) but resolves
   to zero candidates anywhere in `paths` gets a `UNRESOLVED_CALLEE` edge
   instead of the previous silent omission. `UNRESOLVED_CALLEE` moved to
   `callgraph.py` (its real producer now) and is re-exported unchanged
   from `summary.py` for backward compatibility.

   Default stayed `False`, not `True`: `frob.gates` (3 call sites,
   including `_cov006_third_file_reachable`) and `frob.dup._pipeline`
   already call `build_call_graph` and iterate its output (including
   `closure()`) assuming every entry is a real `path::qualname` symref
   splittable on `"::"`. Discovered via a real `IndexError` crash in
   `_cov006_third_file_reachable` during this ticket's own gates-fast
   verification pass when I first defaulted to `True`. Those call sites
   are in `src/frob/gates/**` and `src/frob/dup/**`, outside T-0809's
   scope, so widening them is not this ticket's to do -- disclosed here,
   not silently worked around.

2. Resource-tracking DSL: `frob:acquire <resource>` / `frob:release
   <resource>` / `frob:escapes <resource>` (bare-target verbs, same
   grammar as `frob:doc`/`frob:ticket`) -- new `EdgeKind.ACQUIRE`/
   `RELEASE`/`ESCAPES`, parsed by `dsl.parse_directives` exactly like the
   T-0744 protocol verbs. `FunctionSummary` gained `acquired`/`released`/
   `escaped` frozenset fields, folded transitively through
   `compute_protocol_summaries` by the same plain set-union join
   `requires`/`transitions` already use (own declaration union callee
   summaries, propagated bottom-up through the existing SCC/fixpoint
   machinery, no new traversal logic).

Deferred, disclosed (not built, per the ticket's own instruction to
disclose rather than build past scope):
- Real postdominance-based cleanup-obligation VERIFICATION (does every
  acquire actually get released -- or legitimately escape -- on every
  exit path) is T-0747's job (already ticketed, blocked_by T-0745,
  T-0686). This ticket only adds the DSL surface + transitive summary
  exposure T-0747's verifier will need, same posture `requires`/
  `transitions` already have toward T-0746.
- The T-0686 may-raise engine this substrate is meant to eventually share
  with does not exist yet to consume it -- the T-0745 DESIGN CONSTRAINT
  ("one engine, whichever builds first hosts it") still cannot be
  coordinated on this pass, unchanged from T-0745's own disclosure.
- Widening `frob.gates`/`frob.dup._pipeline`'s own `build_call_graph`
  call sites to be `UNRESOLVED_CALLEE`-aware (so a real repo-wide
  protocol-summary run could actually be wired end-to-end) is outside
  `src/frob/graph/**` -- `mark_unresolved` is available for a future
  ticket to opt those call sites in, or to build a genuine production
  entrypoint that calls `build_call_graph(..., mark_unresolved=True)`
  and feeds `compute_protocol_summaries`.

Scope deviations: scope-added tests/test_graph.py, tests/unit/test_arch.py,
and tests/unit/graph/test_dsl.py via the sanctioned `frob ticket scope
--add --reason-file` mechanism (not a hand-edit) -- deterministic fixture
tests for both mechanisms live in each module's existing dedicated test
home rather than a new parallel file.

Changed:
  src/frob/graph/callgraph.py -- UNRESOLVED_CALLEE (moved here),
    build_call_graph gains mark_unresolved kwarg (default False),
    _resolve_edges gains the unresolved-marking logic
  src/frob/graph/summary.py -- UNRESOLVED_CALLEE re-exported from
    callgraph; FunctionSummary gains acquired/released/escaped;
    _own_contribution/_join_from_callees/compute_protocol_summaries
    fold the three new sets transitively
  src/frob/graph/_models.py -- EdgeKind.ACQUIRE/RELEASE/ESCAPES
  src/frob/graph/dsl.py -- "acquire"/"release"/"escapes" verbs in
    _VERB_TABLE
  docs/modules/graph.md -- Call graph section updated for
    mark_unresolved + the default-False rationale; Protocol summary
    engine section updated for the moved UNRESOLVED_CALLEE and a new
    "Resource-tracking DSL (T-0809)" subsection; Comment DSL directive
    table gains the three new verb rows
  tests/test_graph.py -- 4 new TestCallGraph tests (unresolved marking,
    no-mark on public-looking calls, default-False preserved, resolved
    callee never also unresolved)
  tests/unit/test_arch.py -- 3 new TestProtocolSummaryEngine tests
    (resource leaf declarations, one-hop join, recursive-cluster join)
    plus _acquire/_release/_escapes test helpers
  tests/unit/graph/test_dsl.py -- new TestResourceDirectives class (2
    tests: round-trip, missing-target malformed)
  tickets.md -- T-0809 scope changes, evidence, this Done report

Evidence (9 ids, bound via `frob ticket evidence`, all pass):
  tests/test_graph.py::TestCallGraph::test_build_call_graph_marks_unresolved_private_looking_callee
  tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_mark_unresolved_public_looking_call
  tests/test_graph.py::TestCallGraph::test_build_call_graph_default_preserves_old_silent_omission_behavior
  tests/test_graph.py::TestCallGraph::test_build_call_graph_resolved_private_callee_is_not_also_unresolved
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_resource_declarations_populate_acquired_released_escaped
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_transitively_through_a_caller
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_across_a_recursive_cluster
  tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_release_escapes_round_trip
  tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_missing_target_is_malformed

`uv run pytest tests/unit/graph/ tests/unit/test_arch.py tests/test_graph.py`:
274 passed (21 new + full pre-existing graph/dsl/arch suites, all green).
`uv run frob test --base main`: touched=35 ripple=0, exit=0, 3.06s.

Filed: none -- both out-of-scope discoveries (gates/dup call sites not
UNRESOLVED_CALLEE-aware; T-0686/T-0747 dependency chain) are already
covered by existing tickets (T-0747, T-0686) or are a future-opt-in this
ticket's own kwarg default already protects against, not a new bug
needing its own ticket.

Gates: chunked `frob check --ticket T-0809 --only <stage>` for
lint/static/gates-fast/gates-native/gates-security all PASS (0 errors).
gates-fast initially FAILed with a real `IndexError` crash in
`frob.gates._cov006_third_file_reachable` when `mark_unresolved` first
defaulted to `True` -- fixed by flipping the default to `False` (see
"Built" section above), not by waiving or working around the gate.
gates-fast also initially flagged DRIFT002 (a `frob:describes` anchor in
docs/modules/graph.md still pointing at
`src/frob/graph/summary.py::UNRESOLVED_CALLEE` after the symbol moved to
`callgraph.py`) and PRE001 (stale pre-work sweep after the scope-add) --
both fixed (anchor retargeted, `frob ticket sweep T-0809` re-run), not
waived. No new waivers added by this ticket's own code.

Worktree: .claude/worktrees/agent-ad87b621f69d37500
Not closed, not landed (per dispatch instructions) -- ready for review/land.

### Changed
```
 docs/modules/graph.md        |  89 ++++++++++++++++++-----
 src/frob/graph/_models.py    |  15 ++++
 src/frob/graph/callgraph.py  |  95 +++++++++++++++++++++++--
 src/frob/graph/dsl.py        |   7 ++
 src/frob/graph/summary.py    | 164 ++++++++++++++++++++++++++++++++++++-------
 tests/test_graph.py          |  77 ++++++++++++++++++++
 tests/unit/graph/test_dsl.py |  34 +++++++++
 tests/unit/test_arch.py      |  64 +++++++++++++++++
 tickets.md                   |  85 +++++++++++++++++++++-
 9 files changed, 579 insertions(+), 51 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_marks_unresolved_private_looking_callee` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_mark_unresolved_public_looking_call` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_default_preserves_old_silent_omission_behavior` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestCallGraph::test_build_call_graph_resolved_private_callee_is_not_also_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_resource_declarations_populate_acquired_released_escaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_transitively_through_a_caller` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_across_a_recursive_cluster` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_release_escapes_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_missing_target_is_malformed` (pytest node id, verified passing when recorded)
