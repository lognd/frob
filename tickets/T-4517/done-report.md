## Done report

T-4517 Done report narrative

WHAT CHANGED

- src/frob/testing/_collect_csharp.py (new): collect_csharp_tests(root),
  a static tree-sitter-based collector for NUnit [Test]/[TestCase(...)]/
  [TestCaseSource(...)] and Unity Test Framework [UnityTest] methods.
  Parses every .cs file under root with tree-sitter-language-pack's
  bundled "csharp" grammar (get_parser("csharp"), same grammar name
  frob.lang._walk_csharp.py already uses), walks namespace/class/struct/
  interface containers to build a dotted qualname stack, and matches
  method_declaration nodes carrying a leading attribute_list whose bare
  attribute name is in {Test, TestCase, TestCaseSource, UnityTest}.
  [SetUp]/[TearDown]/[OneTimeSetUp]/[OneTimeTearDown] carry none of
  those names so they are excluded with no special-casing needed.

  Node id shape: "<path>::<Namespace.Class>::<Method>" (three-part,
  doubly "::"-separated). A [TestCase(...)]-parameterized method emits
  exactly ONE node id -- multiple attribute_list children on the same
  method_declaration collapse to one qualname tuple, since the union
  is over a set of qualname tuples per method, not per attribute.

  Deliberately does NOT invoke dotnet/NUnit console runner -- there is
  no npm-equivalent "list tests without building" command assumed to be
  on PATH for a C#/.NET project; a full build-then-run is exactly the
  heavier cost collect_kotlin_tests's own module docstring declines to
  pay for gradle, so this collector applies the same restraint one step
  earlier: static source parsing only, matching collect_kotlin_tests's
  "no build/run just to collect" posture. Cached under
  .frob/csharp-nunit-collect.json, keyed on a sha256 over every
  discovered .cs file's (relpath, content) pair, kept as a LOCAL cache
  helper (not imported from _collect_shared.py) since this ticket's
  declared scope is this file alone -- adding a new shared cache key
  would have meant touching _collect_shared.py, which was never granted.

  Did NOT modify src/frob/lang/_walk_csharp.py or import its private
  _cs_visit/_cs_dispatch recursion -- that walker builds RawSymbol
  values for a completely different purpose (doc/dup/coverage graph
  extraction) and exposes no attribute-list information on its
  RawSymbol at all (verified interactively: attribute_list nodes are
  never inspected by that walker). This collector's own namespace/
  class-stack recursion (_cs_test_methods/_cs_dispatch_test_methods) is
  a small, self-contained copy of the same traversal shape, kept
  separate rather than coupling a RawSymbol-shaped walker to a
  node-id-only collector.

- src/frob/testing/_collect.py: re-imports collect_csharp_tests (T-1074
  call-site-stability convention every other collector split follows),
  adds "csharp": collect_csharp_tests to LANGUAGE_COLLECTORS (the T-3847
  registry frob.app.ticket_runner._verify iterates for evidence
  verification), adds it to __all__.

- src/frob/testing/__init__.py: re-exports collect_csharp_tests,
  __all__ entry.

- src/frob/lang/_support.py: adds "csharp":
  "frob.testing.collect_csharp_tests" to _TEST_DISCOVERY_COLLECTORS (the
  T-2499 registry _capability_test_discovery_status derives from) so
  the csharp capability now reads IMPLEMENTED instead of KNOWN_GAP for
  test discovery.

- docs/modules/testing.md: new "T-4517" paragraph under "## Public API"
  describing the collector and its wiring points, plus a
  <!-- frob:describes src/frob/testing/_collect_csharp.py::collect_csharp_tests -->
  anchor alongside the existing collect_python_tests/collect_rust_tests
  anchors.

- tests/fixtures/lang/csharp/tests/SampleNunitTests.cs,
  tests/fixtures/lang/csharp/tests/SampleUnityTests.cs (new, static,
  checked in per the brief): fixture C# source exercising [SetUp]/
  [TearDown] (must be excluded), [Test], a two-attribute-list
  [TestCase(1,2)]/[TestCase(3,4)] parameterized method (must collapse
  to one id), and [UnityTest] on an IEnumerator coroutine method.

- tests/test_testing.py: new TestCollectCsharpTests class (5 tests),
  copying the static fixtures into each test's own tmp_path root via
  shutil.copyfile rather than generating source inline, mirroring
  TestCollectKotlinTests/TestCollectTsTests/TestCollectCppTests's
  existing per-collector test-class shape in the same file.

WHY (acceptance criteria, registered via `frob ticket accept` since they
were free text on the ticket body, not yet indexed acceptance items)

  [1] GIVEN a C# test class with a [Test] method ... THEN it emits a
      stable node id an frob:tests directive can bind to.
      -> test_collect_csharp_tests_collects_test_and_unitytest asserts
         the exact node id for SampleNunitTests.AddsTwoNumbers.

  [2] GIVEN a [TestCase(1, 2)] parameterized NUnit test ... THEN each
      case is represented (or the parameterized method is represented
      once with a documented id scheme) without erroring.
      -> test_collect_csharp_tests_collapses_parameterized_test_case
         asserts AddsPair (two [TestCase(...)] attribute lists in the
         fixture) yields exactly ONE node id. The "one id per method"
         scheme is documented in the module docstring's "NODE ID SHAPE"
         section.

  [3] GIVEN a MonoBehaviour test class using [UnityTest] ... THEN it is
      collected distinctly from a plain [Test] method.
      -> test_collect_csharp_tests_collects_test_and_unitytest also
         asserts SampleUnityTests.SpawnsPlayerNextFrame's own distinct
         node id is present alongside the [Test] one.

  Two additional tests beyond the three criteria: excludes_setup_teardown
  (regression guard against the ticket's own named exclusion) and
  cache_hit_skips_reparse (monkeypatches parse_csharp to raise, proving
  a cache hit never re-parses -- mirrors the cache-key contract every
  sibling collector documents).

MEASURED NUMBERS

  - New file: src/frob/testing/_collect_csharp.py, 5 tests, all pass:
    "PYTHONPATH=<WT>/src .venv/bin/python -m pytest -q -p no:cacheprovider
    -p no:xdist tests/test_testing.py::TestCollectCsharpTests"
    -> SUITE-RESULT: exitstatus=0 collected=5 failed=0
  - Full tests/test_testing.py (120 tests, serial, -p no:xdist):
    -> SUITE-RESULT: exitstatus=0 collected=120 failed=0
  - tests/test_lang_support.py (29 tests, covers the
    _TEST_DISCOVERY_COLLECTORS/capability-status machinery touched):
    -> SUITE-RESULT: exitstatus=0 collected=29 failed=0
  - ruff check on every touched/new file: All checks passed (0 errors;
    the two pre-existing "Invalid # noqa directive" warnings and the one
    "Would reformat: tests/test_tickets_triage_dates.py" ruff-format
    finding are in files this ticket never touched)
  - ruff format --check: clean on every file this ticket touched (ran
    ruff format once to apply, then re-checked clean)

OUT OF SCOPE / NOT FIXED (found but not touched)

  - src/frob/lang/_walk_csharp.py exposes no attribute-list information
    on its RawSymbol model at all -- verified interactively, not a bug
    in that walker (attributes are simply out of its documented scope,
    doc/dup/coverage extraction never needed them before). Not filed as
    a new ticket: this collector's own small local traversal is a
    complete, working substitute for THIS ticket's purpose, and nothing
    else in the repo currently needs attribute-aware RawSymbols, so
    there is no concrete consumer motivating a ticket yet.
  - _collect_shared.py's cache-path constant table (_KOTLIN_CACHE_REL
    etc.) was deliberately NOT extended with a csharp entry -- kept the
    new cache path fully local to _collect_csharp.py instead, since this
    ticket's declared scope never included _collect_shared.py and the
    duplication (two dozen lines of local _load_cache/_store_cache
    copies) is small and self-contained enough not to justify a scope
    request purely to save that duplication. If a SIXTH collector is
    ever added, moving all per-language cache-path constants into
    _collect_shared.py (including this one) would be worth a ticket then.

GATES

  Per the coordinator's amendment (b): did NOT run the ticket-scoped
  `frob check --ticket T-4517` and did NOT run `frob ticket done-report`
  (spawns a full check) -- verified instead with ruff check/format and
  serial pytest only, per instruction (b) above. `frob ticket show T-4517
  --path <WT>` confirms 3/3 acceptance criteria bound to evidence ids.

STATUS: READY (not landed -- ticket says do not land).

### Changed
```
 docs/modules/testing.md                            |  16 +
 src/frob/lang/_support.py                          |   2 +
 src/frob/testing/__init__.py                       |   2 +
 src/frob/testing/_collect.py                       |  12 +
 src/frob/testing/_collect_csharp.py                | 324 +++++++++++++++++++++
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 ++
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
 tests/test_testing.py                              | 103 +++++++
 tickets/T-4517/ticket.md                           |  12 +-
 9 files changed, 513 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collects_test_and_unitytest` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collapses_parameterized_test_case` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
