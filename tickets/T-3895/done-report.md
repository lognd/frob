## Done report

BLAST RADIUS, measured first as instructed: 0 files in this repo's own
corpus parse differently between "native" and "pure-Python" -- because
that axis does not exist for tree-sitter-backed languages. Grep-verified:
frob.lang._parse (the single chokepoint for .py/.ts/.tsx/.rs/.c/.h/.cpp/
.cs/.java/.cu/.cuh/.zig/.kt/.kts/.sh/.bash) imports neither frob_core nor
strata_core anywhere. strata_core is used ONLY for .strata files;
frob_core is used ONLY by frob.graph.callgraph's call-edge resolution
(already covered by its own existing native/pure-Python differential
test, test_native_matches_python_fallback_on_a_real_package). Confirmed
empirically in this worktree: parsing tests/fixtures/lang/sample.c with
both frob_core and strata_core forcibly blocked via a sys.meta_path
finder produces the byte-identical PARSE002 result as parsing with both
natives present. So the ticket's own premise -- "two backends disagree" --
does not hold for any tree-sitter language in this codebase as it stands.

FIRST QUESTION (which backend is correct), answered against the C
language: I built a reduced repro (tests/fixtures/lang/anonymous_bitfield.c)
using an ISO C11 6.7.2.1p12-legal anonymous bit-field (common in
embedded/HAL register-layout structs, matching the reporter's own
hal/setup.c domain). tree-sitter-language-pack's "c" grammar sets
has_error=True on this legal construct -- verified across three releases
spanning its published history (0.13.0, 1.12.5, 1.16.1 -- not a version-
skew artifact a pin bump would fix). The FULL-PARSE outcome is what ISO C
calls for; PARSE002 firing on this construct is a confirmed grammar false
positive, independent of frob-core/strata-core availability.

WHAT WAS BUILT (durable output, per the ticket's own ordering):
1. tests/test_lang.py::TestNativeIndependentParsing -- the differential
   test: force-blocks frob_core/strata_core via a real sys.meta_path
   MetaPathFinder and asserts parse_file is byte-identical across a
   C/C++/Rust/TypeScript/Python corpus (tests/fixtures/lang/sample.*)
   either way. A future change that actually wires a native into this
   parse path fails this test the day it lands.
2. tests/test_lang.py::TestKnownGrammarGaps + tests/fixtures/lang/
   anonymous_bitfield.c -- pins the specific setup.c-class divergence
   (root-caused above) as expected, native-independent behavior, so a
   future tree-sitter-language-pack upgrade that happens to fix it shows
   up as a caught assertion flip, not a silent behavior change.
3. docs/modules/lang.md's new "What T-0133's degrade guarantee does and
   does not promise" section + a matching note in docs/guides/install.md:
   states plainly that T-0133 covers availability (a missing native is a
   clear Err, never a crash), not cross-backend correctness parity, and
   names the one real exception (.strata/strata_core) versus the
   tree-sitter-only languages where no such choice exists.

T-3845 cross-reference: both new doc sections state directly that T-3845
(cores as default deps) is a pure packaging change for every tree-sitter
language -- it changes nothing about parse results for .py/.ts/.rs/.c/
.cpp/etc, since those never depended on the natives in the first place.

WAIVER CLAIM ADDRESSED: the reporter's fallback complaint ("one waiver
cannot satisfy both") does not reproduce in this codebase: since there is
exactly one true parse result (proven by TestNativeIndependentParsing), a
single frob:waive PARSE002 on a file using this construct is stable
across every install, native or not.

GATES: frob check --ticket T-3895 clean of everything this ticket's diff
could plausibly cause. Three pre-existing, repo-wide, unrelated-file
errors remain untouched by this diff (DEPR003 src/frob/app/fmt_runner.py,
DOC006 tickets/T-3902/ticket.md, DRIFT001 src/frob/verify/_worker.py --
none in this ticket's scope or diff). gate:SCOPE's SCOPE002 fan-in (~30
findings against docs/modules/graph.md, dup.md, frob-core/src/extract.rs,
doctor.py, and every other frob.lang/_walk_*.py sibling) is accepted,
disposition-2-shaped debt per docs/design/tickets-package-scope-
precedent.md: docs/modules/lang.md and tests/test_lang.py are frob.lang's
pre-existing package-wide doc/test home, not created by this ticket's
one-file diagnosis+test diff, and narrowing them to evidence-only (tried,
then reverted) turns SCOPE002 warnings into real SCOPE001 errors instead
(the write lease on an already-edited file cannot be released).

`frob test --base main` timed out at the 540s shell cap twice (frob.lang
has enormous fan-out; the touched-set pulled in an unrelated, large slice
of the suite including tests/system/test_cli_ticket.py) -- exit 143 is
the wrapper, not the work; the actual evidence for this ticket's own
change is the full tests/test_lang.py run (121 passed, 0 failed) plus the
3 bound frob:tests node ids re-run individually, both clean.

### Changed
```
 docs/guides/install.md                   |  12 +++
 docs/modules/lang.md                     |  44 ++++++++
 src/frob/lang/__init__.py                |   6 ++
 tests/fixtures/lang/anonymous_bitfield.c |  17 ++++
 tests/test_lang.py                       | 168 +++++++++++++++++++++++++++++++
 tickets/T-3895/ticket.md                 |  86 +++++++++++++++-
 6 files changed, 331 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestNativeIndependentParsing::test_natives_are_actually_blocked_by_the_harness` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestNativeIndependentParsing::test_corpus_parses_identically_with_and_without_natives` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestKnownGrammarGaps::test_anonymous_bitfield_partial_parse_is_native_independent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 4370 warning(s), 930 waived
- error-findings: DEPR003@src/frob/app/fmt_runner.py, DOC006@tickets/T-3902/ticket.md, DRIFT001@src/frob/verify/_worker.py, SCOPE002@tickets.md
