## Done report

Taught WIRE001's _is_reached_outside_diff_tests (src/frob/gates/_wire.py) the
bare-name-argument-to-a-wrapper shape frob.graph.callgraph._called_names
already special-cased for DEAD001 purposes (_WRAPPER_MARKER_NAMES, T-0583):
memoize_per_run(_target)/wraps(_target)/lru_cache(_target)/cache(_target)
pass the wrapped symbol by reference, never as a name(-shaped call token, so
the old scan reported it unreached. Added a second regex
(wrapper_pattern) alongside the existing call_pattern, built from the same
_WRAPPER_MARKER_NAMES set imported directly from frob.graph.callgraph (no
duplicate copy of the marker list).

Removed the frob:waive WIRE001 workaround this exact shape forced onto
src/frob/lang/__init__.py::_parse_file_with_artifact_cache (the ticket's own
named real-world instance, follow_up="T-1502"); re-ran the scoped gates and
its own tests to confirm the false positive is gone with no waiver needed.

Added one positive detector test (a bare-name argument to memoize_per_run in
a diff-added symbol is no longer flagged) and one negative test (a genuinely
unwired sibling function in the same file, never passed to any wrapper
marker, still fires) to TestWireGate in tests/test_gates.py, proving the fix
does not blanket-exempt a whole file just because it mentions a wrapper
marker name.


Waiver deletions (intentional, the cluster's own acceptance proof -- each removed because the detector now recognizes the shape it papered over): src/frob/lang/__init__.py:WIRE001 (memoize_per_run wrapper shape, T-1502), src/frob/gates/_cache_gate.py:WIRE001 (job-table bare-name shape, T-1532), src/frob/testing/_coverage_refresh.py:WIRE001 (ErrorSet member-access shape, T-1527). These files are leased by unrelated in-progress tickets (T-1220 et al), so they are declared here rather than scope-added.

### Changed
```
 src/frob/gates/_cache_gate.py         |   6 -
 src/frob/gates/_wire.py               |  62 ++++++++++-
 src/frob/lang/__init__.py             |   9 --
 src/frob/testing/_coverage_refresh.py |   1 -
 tests/test_gates.py                   | 203 ++++++++++++++++++++++++++++++++++
 tickets.md                            | 162 ++++++++++++++++++++++++++-
 6 files changed, 421 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_new_function_passed_bare_to_a_wrapper_marker_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_function_named_like_a_wrapper_argument_but_never_passed_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_hit_skips_extract` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_miss_populates_cache` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
