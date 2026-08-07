## Done report

Delivered the safest, most clearly-scoped of the ticket's 3 named
consolidations: `arch/_patterns.py`'s `_check_type_switch`/
`_check_state_field_chain`/`_check_stringly_typed`, all called
sequentially over the SAME tree by `arch/__init__.py`'s per-file check
driver, each independently ran a full recursive `_find_if_statements`
walk. Added `if_stmts: list[Node] | None = None` to
`iter_type_switch_chains` and all three `_check_*` functions
(defaulting to `None` -> compute locally, so `frob.arch._ocp`'s own
existing `iter_type_switch_chains` reuse and any other pre-T-1485
caller is byte-for-byte unaffected -- verified by
`tests/unit/test_arch_ocp.py`, 10 passed unchanged); `arch/__init__.py`
now computes `_patterns._find_if_statements(...)` once and threads the
result through all three, cutting 3 full-tree walks per Python file
down to 1 for this check family.

Needed `frob ticket scope T-1485 --add src/frob/arch/__init__.py` (real
call site the ticket's original 3-file scope did not name -- the
duplication can only be eliminated at the caller, since all 3 walks
live inside independently-callable public/private functions whose own
bodies each need to stay correct when called alone) -- recorded via the
CLI with a reason, per playbook section 4.

The other two named consolidations were investigated and NOT
attempted, disclosed rather than silently dropped:

- `arch/_python.py`'s nesting/cyclomatic/events fold: this ticket's own
  body AND `_py_build_function`'s existing docstring both explicitly
  flag this as deliberately NOT safe to fold without a from-scratch
  byte-identical-output proof across a real corpus first (T-1215's own
  precedent) -- max_nesting_depth/cyclomatic are kept as separate walks
  specifically so they match the original per-language walk exactly,
  and _py_collect_body_events does not necessarily visit every node
  type the same way. Forcing this fold inside a multi-ticket sweep
  without that proof risks silently changing either metric's value for
  an edge case neither this session's time budget nor its test corpus
  could rule out.
- `_concurrency_model.py`'s `_walk_all`: read its only caller
  (`_executor_bindings`) and found it is NOT residue -- `_walk_all` is
  a genuinely different walk from this package's `_iter_own_scope`
  family (module-wide, not scope-limited, by design: an executor is
  commonly bound at module level and consumed elsewhere, per its own
  docstring) and has exactly ONE caller. There is no second full-tree
  walk of the same shape anywhere in scope to consolidate it with --
  it is already minimal, not duplicated.

Measurement: unscoped `frob check --only archgate --only perf`: gate:
ARCH 0 errors/0 warnings/61 waived (unchanged), gate:PERF 0 errors/47
warnings/99 waived (unchanged -- this consolidation's redundant-walk
shape is not one any existing PERF01x rule's lexical pattern
(PERF011/013/014) matches, since all three calls are direct symbol
calls, not a loop-nested repo-scan/ast.walk/finditer; no new rule
proposed here since the pattern this fixes -- N independent public
functions each re-walking a caller-supplied tree, only detectable by
knowing they are always invoked together over the same tree -- needs
cross-call-site correlation a single-symbol lexical rule cannot see).
`pytest tests/unit/test_arch.py -k PatternRecommender`: 33 passed.
`pytest tests/unit/test_arch.py`: 292 passed. `pytest tests/unit/
test_arch_ocp.py`: 10 passed (proves the shared `iter_type_switch_chains`
entry point's other caller is unaffected). `pytest tests/test_gates.py
-k "ArchGate or Pattern"`: 3 passed.

### Changed
```
 docs/modules/tickets.md                          |  58 ++-
 src/frob/arch/__init__.py                        |  14 +-
 src/frob/arch/_patterns.py                       |  64 ++-
 src/frob/gates/decisions.py                      |   3 +-
 src/frob/gates/invariants.py                     |   3 +-
 src/frob/perf/_hotpath_smells.py                 |  44 +-
 src/frob/registry/_models.py                     |   3 +-
 src/frob/tickets/_store.py                       |  64 +--
 src/frob/vet/_capability_typescript.py           | 597 +----------------------
 src/frob/vet/_capability_typescript_bindtable.py | 593 ++++++++++++++++++++++
 src/frob/vet/_lockfile.py                        |   3 +-
 src/frob/yaml_io.py                              |  73 +++
 tests/unit/perf/test_hotpath_smells.py           |  24 +
 tickets.md                                       | 281 ++++++++---
 14 files changed, 1080 insertions(+), 744 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestPatternRecommender::test_isinstance_chain_recommends_strategy` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_state_field_chain_recommends_state_machine` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_stringly_typed_recommends_newtype` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_ocp.py::TestTypeDispatchSmell::test_isinstance_chain_flags_ocp_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 454 warning(s), 797 waived
- error-findings: none (measured, zero errors)
