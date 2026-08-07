## Done report

parse_directives no longer misreads a frob:-shaped prose token at a continuation-line start as a fresh directive: _is_genuine_directive_start only breaks a fold when the candidate line structurally parses to a real Edge or recognized reserved marker, so unknown-verb or malformed frob: substrings fold through as prose. Genuinely stacked directives and the T-0286 corruption repro are unaffected; both verified repro files parse clean at wrap widths 60/70/88/100 (were 2 and 12 malformed pre-fix), plus a property-style wrap-at-every-width stability test.

### Changed
```
 docs/modules/gates.md        |  37 +++++++-----
 src/frob/graph/dsl.py        |  79 ++++++++++++++++++++------
 tests/unit/graph/test_dsl.py | 130 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                   |  88 ++++++++++++++++++++++++++++-
 4 files changed, 300 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_frob_describes_prose_at_continuation_line_start_folds` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_frob_describes_prose_repro_shape_from_dup_core` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_property_wrap_at_every_width_preserves_reason` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_stacked_directives_still_parse_independently` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestVerbShapedContinuationProse::test_unrelated_directives_corruption_repro_still_rejects_fold` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
