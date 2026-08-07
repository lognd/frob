## Done report

DEPR005's reference detection was a bare-short-name text match (any
`subprocess.run(` counted as a caller of a `run`-named deprecated
symbol) and its baseline keyed callers by file:line, so a pure
upstream line-shift red-mained the build -- both happened three times
in one session on 2026-07-27.

Fixed both axes without extending frob.graph.callgraph (which is
private-callee-only by design, and stays that way -- extending it to
public callees is out of scope here): a call-shaped xref usage of a
deprecated symbol's bare identifier now only counts as a reference
when its own file is also an exports_consumers import-statement hit
for that exact symbol, so an unrelated same-named call in a
non-importing file (subprocess.run) no longer counts. The committed
baseline is now keyed by (referencing file, symbol) with a per-file
reference count, not (file, line) -- DeprecatedBaselineEntry.references
stores "file#count" strings; a pure line-shift inside an already-
referencing file changes nothing. tighten_deprecated_baseline's
shrink-only contract now operates per-file: a file's baselined count is
capped at min(baselined, currently-observed), never grows past what
was baselined, and a file that disappears drops out entirely.

Regenerated frob-deprecated-baseline.lock.json in the new format:
xref_runner.py::run/outline_runner.py::run/map_runner.py::run went
from 911 file:line junk references each to 49 real importing files
each (911 -> 49, ~95% junk dropped); docs_runner.py::_run_search
stayed at 0 (unchanged, no callers).

Restored DEPR005 to error tier in frob.toml [gates.severity] and
removed the T-1052 demotion comment block, per the ticket's explicit
instruction (frob.toml was not in the ticket's declared scope globs --
added via `frob ticket scope --add frob.toml` with a written reason,
since the ticket body required the change).

`frob check --ticket T-1052 --only gates-fast` is clean: 0 errors,
gate:DEPR 0 errors/4 warnings/0 waived.

First land attempt was refused by TEST016 mutation-evidence: the bound
evidence killed 0/3 mutants of _depr005_violations' own comparison logic
(count > baseline_counts.get(file, 0) at line 5602, and the grown-file
line lookup at line 5608) -- the _deprecated_baseline unit tests never
exercised the gate's own growth comparison directly. Added two
deprecated_gate-level tests (TestDepr005ViolationsGrowth): an unchanged
count must not fire (kills a Gt/Eq-swapped mutant), and a grown file
among a stable sibling must fire naming the right file at the right
line (kills the Eq/And-swapped grown-file lookup).

### Changed
```
 docs/modules/gates.md                        |   70 +-
 frob-deprecated-baseline.lock.json           | 2880 ++------------------------
 frob.toml                                    |    4 -
 src/frob/gates/__init__.py                   |   95 +-
 src/frob/gates/_deprecated_baseline.py       |  156 +-
 tests/unit/gates/test_deprecated_baseline.py |  278 ++-
 tickets.md                                   |    3 +-
 7 files changed, 646 insertions(+), 2840 deletions(-)
```

### Evidence
- `tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_line_shift_leaves_baseline_byte_identical` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_shrinkage_keeps_lower_count_never_grows` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_never_absorbs_growth_inside_an_already_baselined_file` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestFileReferenceCounts::test_buckets_by_file` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedBaselineEntry::test_file_counts_decodes_encoded_references` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_first_seen_symbol_is_seeded_whole` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_shrinkage_drops_stale_references` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_never_absorbs_a_new_reference` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_symbol_no_longer_deprecated_is_dropped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 3 error(s), 2168 warning(s), 380 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t1052-depr005/src/frob/tickets/_leases.py:538, E501@/home/logan/projects/frob/.claude/worktrees/t1052-depr005/src/frob/tickets/_leases.py:547, PERF004@src/frob/gates/_deprecated_baseline.py
