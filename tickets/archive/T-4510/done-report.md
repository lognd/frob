## Done report

T-4510 -- C# dup/docblock facet fixture (verify _CSHARP_LANGS bucket end to end)

WHAT CHANGED

Added tests/fixtures/csharp_dup_docblock/:
  - Sample/Dup/Duplicate.cs: a documented public class (one /// XML doc
    comment) and an undocumented public class, each with one near-duplicate
    method (renamed identifiers, Type-2 shape).
  - guide.md: two real fenced csharp blocks (anchored project-reference,
    BCL reference) that frob check's own repo-wide DOC004 gate scans for
    real -- both deliberately zero-violation so the fixture itself never
    trips the live gate.
  - python_control/duplicate.py: the same near-duplicate-method shape in
    python, as the positive control for the dup-facet assertion.

Added tests/unit/test_support_csharp.py: 5 test cases (2 parametrized dup
cases + 3 docblock cases) proving both facets fire end to end.

FINDING AND FIX (dup facet)

The docblock facet (frob.gates._docblocks_refs._csharp_using_violations,
T-2906, DOC004's _CSHARP_LANGS bucket) already worked correctly and needed
no source change.

The dup facet did NOT work: frob.dup._legacy._scan_tree dispatched only
_PY_EXTS/_CPP_EXTS -- .cs files were never scanned at all, despite csharp
being a real LANGUAGES entry in frob.dup._exhaustiveness and a real
_CSHARP_LANGS-routed facet in frob.lang._support. This is exactly the
"reports zero on the fixture, that is the finding" case the ticket
predicted. Fixed per the ticket's own instruction (scope-added
src/frob/dup/_legacy.py, new src/frob/dup/_legacy_cs.py,
docs/modules/dup.md):
  - New src/frob/dup/_legacy_cs.py: a C# method/locals/serialization
    walker over tree-sitter-c-sharp (method_declaration/parameter/
    variable_declarator field names verified interactively against a
    parsed sample before writing any walker code), mirroring
    _legacy_py.py's shape.
  - _legacy.py: added _CS_EXTS = {".cs"} and _scan_cs_file, wired into
    _scan_tree's per-extension dispatch alongside _PY_EXTS/_CPP_EXTS.
  - docs/modules/dup.md: documented the new _CS_EXTS dispatch under the
    legacy-scanner anchor.

MEASURED COUNTS ON THE FIXTURE

find_duplicates(tests/fixtures/csharp_dup_docblock, min_lines_overrides=()):
  - 1 group touching a .cs fragment: symbols
    {Documented.AddNumbers, Undocumented.AddValues}
  - 1 group touching a .py fragment (positive control): symbols
    {add_numbers, add_values}

_csharp_using_violations (DOC004's _CSHARP_LANGS bucket):
  - unanchored project-internal `using Sample.Dup;` -> 1 violation (rule
    DOC004)
  - anchored twin (frob:doc marker immediately above the fence) -> 0
    violations
  - BCL `using System.Text;` (never resolves against a tracked .cs path)
    -> 0 violations, unanchored, zero false positives

GATE FINDINGS RESOLVED (from the first --only gates pass)

  - DOC004 on guide.md itself: the checked-in fixture originally included
    an unanchored block, which the REAL repo-wide DOC004 gate flagged
    when scanning this file. Removed that block from guide.md; the
    unanchored case is now built entirely in memory in the test
    (test_unanchored_project_using_fires_unbound), so the checked-in doc
    stays DOC004-clean while the mechanism is still proven directly.
  - SELFAUDIT001 / undeclared fs.read capability effect: the test
    originally read guide.md off disk via Path.read_text. Restructured
    all three docblock test cases to build _FencedBlock/doc_lines in
    memory (mirroring guide.md's real content) instead, so there is no
    fs.read effect to declare at all -- this also avoided needing a
    design/frob.strata via-list edit, which is currently lease-blocked by
    in-progress T-3613 on that exact file (a real ScopeLeaseConflict,
    confirmed via `frob ticket scope --add`; per the hard rule against
    stealing a lease naming another ticket, worked around instead of
    forced).
  - DUP002 on test_support_csharp.py itself: the two dup-facet test
    bodies (csharp assertion, python positive control) were 95% similar
    to each other. Merged into one pytest.mark.parametrize test.
  - WIRE001 x2 on _legacy_cs.py's _collect_locals_cs/_serialize_cs_body:
    both are passed as callback arguments to _index_function in
    _legacy.py._scan_cs_file (an indirect-call shape WIRE001's static
    analysis does not follow) -- same shape as their pre-existing cpp/py
    siblings, which WIRE001 does not flag only because those are not new
    in this diff. Waived with a reason citing the call site and the
    sibling precedent.

VERIFICATION

  - PYTHONPATH=<WT>/src python -m pytest -q -p no:cacheprovider -p no:xdist
    tests/unit/test_support_csharp.py -> 5 passed, 0 failed.
  - ruff check + ruff format --check on every touched file -> clean.
  - frob check --only gates --files <touched files> <WT> (background run,
    repo-wide, ~9 minutes): first pass found the 5 real findings above
    (all in files this ticket touches); all fixed and re-verified by
    running the same test suite + ruff again (the coordinator then took
    over serial gate verification to avoid concurrent-check starvation,
    per its own instruction to stop retrying `frob check`/`done-report`
    myself).

OUT OF SCOPE, NOT FIXED HERE

Acceptance criterion 2's literal wording ("a public C# method missing an
XML doc comment (///) ... flags the missing docblock the same way it
flags a missing Python docstring") is interpreted as DOC004's UNBOUND
check (_csharp_using_violations), since frob.lang._support's own
_docblock_languages() names DOC004's fenced-block buckets as the entire
"docblock" facet in this codebase -- there is no separate per-language
missing-docstring/symbol-doc-coverage gate for python either. This
matches criterion 3's own explicit naming of _csharp_using_violations as
the mechanism under test.

EVIDENCE BOUND (frob ticket evidence, --base-ref dev)

  criterion 1 (dup fires):
    tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::test_find_duplicates_reports_near_duplicate_methods
  criterion 2 (docblock fires / UNBOUND):
    tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_unanchored_project_using_fires_unbound
  criterion 3 (zero false positives):
    tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_bcl_using_is_zero_false_positives
    tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_anchored_project_using_has_zero_violations

All 4 node ids confirmed bound via `frob ticket show T-4510 --path <WT>`
(acceptance section lists all 3 criteria; evidence list has 4 ids).

### Changed
```
 docs/modules/dup.md                                |  12 ++
 src/frob/dup/_legacy.py                            |  60 ++++++-
 src/frob/dup/_legacy_cs.py                         | 196 +++++++++++++++++++++
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 ++++
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 ++++
 .../python_control/duplicate.py                    |  29 +++
 tests/unit/test_support_csharp.py                  | 190 ++++++++++++++++++++
 tickets/T-4510/ticket.md                           |  15 +-
 8 files changed, 569 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::test_find_duplicates_reports_near_duplicate_methods` (pytest node id, verified passing when recorded)
- `tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_unanchored_project_using_fires_unbound` (pytest node id, verified passing when recorded)
- `tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_bcl_using_is_zero_false_positives` (pytest node id, verified passing when recorded)
- `tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_anchored_project_using_has_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
