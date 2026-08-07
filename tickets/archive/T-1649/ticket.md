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
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns
- tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_kotlin_file_no_longer_flagged_by_lang002
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_aggregates_across_files
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_aggregates_across_files
designated_repro_test: null
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