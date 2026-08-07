---
id: T-1649
title: 'PERF remainder: 9 real PERF011 site fixes, PERF014 rule-level audit, 2 out-of-scope
  PERF005 Rust findings'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/_native.py
- src/frob/gates/_inv.py
- src/frob/gates/_inv006_split_assist.py
- src/frob/gates/_lang_conformance.py
- src/frob/vet/_capability_scan.py
- src/frob/gates/_docptr.py
- src/frob/gates/_refs.py
- src/frob/arch/_cpp_mayraise.py
- src/frob/arch/_ffi.py
- src/frob/arch/_protocol_excuse.py
- src/frob/gates/_rule_id_scan.py
- src/frob/perf/_hotpath_smells.py
- frob-core/src/extract.rs
- tests/**
- docs/modules/gates.md
- docs/modules/perf.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 doc-drift edits recording the T-1649 rule-level fixes
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/perf.md
  reason: AFFECT001 doc-drift edits recording the T-1649 rule-level fixes
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_does_not_fire_on_whole_text_single_pass
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_kotlin_file_no_longer_flagged_by_lang002
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_aggregates_across_files
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_aggregates_across_files
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
  reason: T-1763 deleted find_carried_waiver/_inv006_split_assist.py entirely along
    with INV006 -- no functional equivalent exists; rebinding to the nearest still-live
    sibling test in INV003
  actor: logan
  at: '2026-08-07'
threat: null
component: null
---
T-1647 fixed the majority of the 47-warning gate:PERF pool (rule-level PERF011 false-positive fix cleared 20 findings on its own; PERF013's genuine duplicate ast.walk got merged; 3 PERF008 findings and 2 residual PERF011 sibling-loop false positives got specific waivers; one PERF005 recursion got its frob:invariant terminates). Unscoped gate:PERF went 47 -> 20 unwaived warnings (99 -> 104 waived).

This ticket is the disclosed remainder T-1647 did not attempt, split by rule:

## PERF011 -- 9 genuine findings (real debt, not rule misfires)

A repo-scan API (iter_files/xref/exports_consumers) called once per outer-loop iteration, genuinely re-walking the same (sub)tree N times where N is a small collection (file extensions, spec dirs) the caller already has in hand. Per this repo's own PERF011 remedy text: hoist and index once per distinct key, don't rescan.

- src/frob/check/_native.py:29 (_collect_sources) -- per-extension rglob via iter_files inside `for ext in exts:`
- src/frob/gates/_inv.py:370 (inv003_gate) -- per spec_dir (2 dirs)
- src/frob/gates/_inv.py:495 (inv004_gate) -- same shape as inv003_gate
- src/frob/gates/_inv.py:661 (inv006_gate) -- nested per src_dir x suffix
- src/frob/gates/_inv006_split_assist.py:89 (find_carried_waiver) -- nested per candidate_dir x candidate_suffix (own docstring notes this runs rarely -- low real-world cost, still worth an honest fix or a reasoned waiver citing that same rarity)
- src/frob/gates/_lang_conformance.py:159 (_lang002_unregistered_files) -- per candidate-language extension
- src/frob/gates/_lang_conformance.py:190 (_lang003_unsound_gaps) -- per supported_extensions() extension, called just to check truthiness (existence) -- cheapest fix of the nine: hoist one `iter_files(repo_root)` call and index by suffix once, or track "extension present" via a single pass
- src/frob/vet/_capability_scan.py:602 (_aggregate_capabilities) -- per _EXT_LANGUAGE extension
- src/frob/vet/_capability_scan.py:663 (_aggregate_fingerprints) -- identical shape, sibling of the above (candidate for a genuinely shared helper -- same walk/exclusion shape already noted in that file's own docstring)

## PERF014 -- 9 findings, rule needs the SAME kind of audit T-1647 gave PERF011 first

_perf014_finditer_in_nested_loop fires on "3+ for/while tokens anywhere earlier in the function", the same flat/no-nesting-info design PERF011 had before T-1647's fix. A spot check of 2 of the 9 live findings found the identical failure class: SEQUENTIAL (sibling), not truly nested, loops earlier in the function inflate the count past the threshold.

- src/frob/gates/_docptr.py:122 (_prose_tokens) -- CONFIRMED false positive: a listcomp's own `for` (building newline_offsets) plus the first (single-loop) finditer call's own `for match in ... finditer(text):` both precede the SECOND, genuinely-2-level-nested finditer call (`for line_no, line in enumerate(...): for match in ..finditer(line):`), pushing the count to 3 and misfiring on a shape the rule's own docstring says must stay silent.
- src/frob/gates/_refs.py:387 (_python_import_targets) -- CONFIRMED false positive: two SEQUENTIAL top-level for-loops (one per import style: `from X import Y` then `import X`), each with its own single level of real nesting; the second loop's count inherits the first loop's tokens, again crossing the >=3 threshold on 2 real levels.

The other 7 (src/frob/arch/_cpp_mayraise.py:238,354; src/frob/arch/_ffi.py:273,366; src/frob/arch/_protocol_excuse.py:91; src/frob/gates/_refs.py:412; src/frob/gates/_rule_id_scan.py:128) were NOT individually re-verified against real code by T-1647 -- do that first, the same way T-1647 audited every live PERF011 finding, before assuming they're all false positives or all real.

A real fix needs the same "is this call inside a loop that is ITSELF nested under an earlier, still-open loop, vs. one that just lexically follows an earlier CLOSED loop" distinction PERF011's T-1647 fix used bracket-depth-plus-first-loop tracking for -- PERF014's threshold-counting design will need a comparable (not necessarily identical) rewrite, since sum-of-preceding-loops can't currently tell "3 truly nested" from "2 nested + 1 sequential sibling" apart. Follow T-1647's own audit-before-fixing method: read the rule, sample every live finding against real code, classify per-site, THEN decide site-fix vs rule-fix vs waive.

## PERF005 -- 2 findings, both out of scope for T-1647 (scope was src/frob/**, tests/**)

- frob-core/src/extract.rs:52 (walk_leaves)
- frob-core/src/extract.rs:254 (collect_comment_nodes)

Both are Rust recursion in the frob-core crate; this repo's `frob:invariant terminates` annotation convention is Python-only as far as T-1647 could tell in-scope -- confirm whether an equivalent Rust-side annotation mechanism exists before fixing/waiving these, or extend scope to frob-core/**.

## Done report

Natives verified healthy before measuring: `make core`/`uv run frob natives
build` (both strata_core and frob_core built cleanly) at the start of this
session, and unscoped `uv run frob check --only perf` read exactly ~20
unwaived warnings (20 -- matches T-1647's disclosed baseline, not 0/near-0),
confirming the analysis layer was live, not silently dead.

PERF014 audit (the ticket's main ask): read `_perf014_finditer_in_nested_loop`
and found the identical flaw T-1647 fixed in PERF011 -- a flat "count every
for/while token anywhere earlier in the function" heuristic that cannot tell
a genuinely nested loop from an earlier, already-closed SIBLING loop.
Rewrote it as a per-file AST pass (`_perf014_ast_violations`, reusing
`frob.lang.raw_tree`, the same substrate `frob.perf._loop_effects` already
uses for PERF008 in this package) computing real ancestor for/while
loop-nesting depth for each `.finditer(...)` call site, via body-only
containment so a loop's own iterable expression never counts as nesting.

Verdict per finding (all 9 sampled against real code):
- src/frob/gates/_docptr.py:122 -- FALSE POSITIVE (confirmed). A listcomp's
  own for-clause plus a first, single-level finditer loop are SEQUENTIAL;
  a genuinely-2-level-nested second finditer call is the only real site.
  Depth-based check: both finditer calls measure depth 0/1, correctly silent.
- src/frob/gates/_refs.py:387 (_python_import_targets) -- FALSE POSITIVE
  (confirmed). Two SEQUENTIAL top-level for-loops, each with one real
  level, never nested in each other. Both finditer calls measure depth 0,
  correctly silent.
- src/frob/gates/_refs.py:412 (_candidate_tokens) -- FALSE POSITIVE. The
  `for pattern in (...): for match in pattern.finditer(text):` shape is
  the FIXED, desired one-loop-per-pattern form (T-1211's own remedy target)
  -- depth 1, correctly silent.
- src/frob/arch/_cpp_mayraise.py:238 (_scan_body_raises) -- FALSE POSITIVE.
  A single compiled pattern's finditer called once per line inside ONE
  loop (`for line in body_lines:`), not a pattern-list-inside-per-line
  shape at all -- depth 1, correctly silent (the rule's own remedy text
  is about pattern-list x per-line; this has no pattern list).
- src/frob/arch/_protocol_excuse.py:91 -- FALSE POSITIVE, same shape as
  _refs.py:412 (single loop-per-pattern, the fixed form). Depth 1, silent.
- src/frob/gates/_rule_id_scan.py:128 -- REAL. `for base in SCANNED_BASES:
  for path in sorted(base_dir.rglob(...)): for lineno, line in enumerate(...):
  for m in _LITERAL_PATTERN.finditer(line):` is 3 real nested levels
  (dir x file x line) around a single-pattern per-line finditer call --
  depth 3, correctly stays live (line shifted to :163 after this diff's
  own unrelated edits elsewhere in the file).
- src/frob/arch/_cpp_mayraise.py:354 (_scan_each_function) -- REAL. Per-
  function x per-line nested loop around `_CALL_RE.finditer(line)` --
  depth 2 (line shifted to :371).
- src/frob/arch/_ffi.py:273,367 -- one FALSE POSITIVE (same single-loop
  shape as _cpp_mayraise.py:238's sibling), one REAL (same per-function x
  per-line shape as _cpp_mayraise.py:354, now at :399).

Net: rewrote the rule (one fix, not nine site edits) rather than hand-
classifying each site with a bespoke waiver. Unscoped gate:PERF PERF014
count: 9 -> 3 unwaived (6 confirmed false positives eliminated; the 3
real, confirmed-nested sites are correctly still live, not silenced).
Filed a successor, T-1660, for those 3 real fixes -- restructuring
each to a whole-text finditer + line-offset recovery (the _docptr.py::
_prose_tokens precedent) is real work outside this ticket's own stated
scope (rule-level audit, not the site fixes).

PERF011: all 9 genuine sites fixed by hoisting the per-extension/per-
directory repo-scan call to ONE `iter_files()` scan, filtered/indexed in
memory against the caller's own already-known small extension/directory
set, instead of one call per extension/directory:
- src/frob/check/_native.py::_collect_sources
- src/frob/gates/_inv.py::inv003_gate/inv004_gate (new `_spec_dir_md_files`
  shared helper) and ::inv006_gate (new `_inv006_src_files` helper)
- src/frob/gates/_inv006_split_assist.py::find_carried_waiver
- src/frob/gates/_lang_conformance.py::_lang002_unregistered_files/
  _lang003_unsound_gaps
- src/frob/vet/_capability_scan.py::_aggregate_capabilities/
  _aggregate_fingerprints (new shared `_files_by_ext` helper, matching
  that file's own docstring note calling these two "candidate for a
  genuinely shared helper")

PERF005 (frob-core/src/extract.rs, Rust): confirmed the `frob:invariant
terminates` comment-DSL convention already applies to Rust (precedent:
frob-core/src/lib.rs:522, strata-core/src/lib.rs:93/167/520) -- not
Python-only as T-1647 left disclosed-uncertain. Added the annotation to
both `walk_leaves` and `collect_comment_nodes`: both recurse strictly into
tree-sitter's own finite parse-tree children, terminating at a leaf (zero
children) or, for `collect_comment_nodes`, also at the first
`RUST_COMMENT_KINDS` match. Rebuilt natives after the Rust edit and
re-verified.

No mass waiving: every disposition above is either a structural rule fix
(PERF014), a real site hoist (PERF011), a real Rust invariant annotation
(PERF005), or an explicit successor ticket for confirmed-real remaining
debt (PERF014 x3) -- zero blanket/reasonless waivers added.

Measured before/after unscoped `uv run frob check --only perf`:
- Before: 0 errors, 20 warnings, 104 waived.
- After: 0 errors, 3 warnings, 105 waived (2 PERF005 fixed via
  annotation not waiver, so waived count only moved by the ledger's own
  bookkeeping, not a new suppression -- see gate:PERF tool output).

Verification: touched-file pytest suites (hotpath_smells, test_gates.py,
test_lang_conformance_gate.py, test_vet.py, test_check.py,
test_app_runners_batch6.py) all green (1285 collected, 0 failed, run in
two passes). `frob check --only gates-fast --ticket T-1649`: 0 errors
(AFFECT001/PRE001/SCOPE001 fixed via doc touches + scope --add + a
sweep re-run). `frob check --land-parity`: clean, 0 unscoped errors.
`git diff main --diff-filter=D --stat`: empty.

### Changed
```
 docs/modules/gates.md                  |  19 ++++
 docs/modules/perf.md                   |   8 ++
 frob-core/src/extract.rs               |  14 +++
 src/frob/check/_native.py              |  21 +++-
 src/frob/gates/_inv.py                 |  78 ++++++++------
 src/frob/gates/_inv006_split_assist.py |  93 +++++++++--------
 src/frob/gates/_lang_conformance.py    |  21 +++-
 src/frob/perf/_hotpath_smells.py       | 180 ++++++++++++++++++++++++++-------
 src/frob/vet/_capability_scan.py       |  28 ++++-
 tickets.md                             |  76 +++++++++++++-
 10 files changed, 415 insertions(+), 123 deletions(-)
```

### Evidence
- `tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_does_not_fire_on_whole_text_single_pass` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_kotlin_file_no_longer_flagged_by_lang002` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_aggregates_across_files` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_aggregates_across_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 6369 warning(s), 849 waived
- error-findings: none (measured, zero errors)
