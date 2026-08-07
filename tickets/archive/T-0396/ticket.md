---
id: T-0396
title: 'anti-orphan gate: every tracked file must be referenced+declared by another
  file (0 refs = warn, 1 = weak-warn, 2+ ok)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/graph/
- frob.toml
- docs/modules/gates.md
- tests/test_refs_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_refs_gate.py::TestTiers::test_zero_refs_warns_ref001
- tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002
- tests/test_refs_gate.py::TestTiers::test_two_refs_passes
- tests/test_refs_gate.py::TestUsedByDeclaration::test_valid_declaration_counts_not_dangling
- tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_nonexistent_consumer_fails
- tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_non_reaching_consumer_fails
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_allowlisted_file_is_exempt
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_non_allowlisted_orphan_still_fires
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_no_tracked_files_returns_empty
- tests/test_refs_gate.py::TestReferenceDetection::test_bare_prose_mention_does_not_count_as_a_reference
- tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_multi_name_from_import_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_parenthesized_from_import_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_pytest_collected_test_file_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_registry_style_yaml_with_only_prose_mentions_still_fires
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_genuinely_unreferenced_module_still_fires
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dead_non_test_file_under_tests_dir_still_fires
designated_repro_test: null
threat: null
component: null
---
GENERAL prevention for the orphaned-artifact class (the docs/design/registry/*.yaml manifests were read by ZERO files -- exactly this). Add a gate over EVERY git-tracked file, regardless of language/type (.py/.rs/.ts AND .yaml/.md/.toml/.json/.cfg/.txt/data/assets), that verifies each file is REFERENCED (hooked) by at least one OTHER tracked file. Tiers: 0 inbound references = REF001 warn (an orphan -- probably dead or silently unenforced, like the registry yamls); exactly 1 inbound reference = REF002 weaker warn (single point of anchor, fragile); 2+ = pass. The user wants 2+ as the norm, 1 waivable, 0 loud.

REFERENCE DETECTION must be cross-type, not just import graphs: a file X is referenced by file Y if Y names X by repo-relative path or basename in ANY of -- python/js/ts/rust/c import|require|include|use, a config/string path literal, a markdown/doc link, a frob:doc / frob:describes anchor, a build-system or CI path, a loader/glob base dir, etc. Reuse frob.graph/frob.lang where possible; for non-source files fall back to a whole-repo path/basename scan (tracked files only, honoring frob.excludes).

DECLARE-WHERE-USED: auto-detected references are not always visible (a data file loaded via a path built at runtime, a yaml read by a glob). So support an EXPLICIT declaration a file (or its consumer) carries -- a frob:used-by / frob:consumes directive (DSL) naming the consumer(s)/consumed path -- and VERIFY the declared reference is real (the named consumer exists and actually reaches this file), fail-closed if a declaration is dangling. A file with no auto-detected refs AND no valid declaration is the orphan case. The point: for every file we DECLARE exactly where it is used, and the gate proves the declaration true.

ENTRY-POINT ALLOWLIST: genuinely-referenced-from-outside files (README.md, LICENSE, pyproject.toml, .github/**, __main__.py, top-level entry scripts, the root config) are legitimately low-inbound -- a small explicit allowlist in frob.toml (documented, not a blanket mute), each with a reason, satisfies the gate for those.

Acceptance: (1) frob check gains a REF001/REF002 family; running it on THIS repo TODAY flags docs/design/registry/*.yaml as orphans (0 refs) -- proving it catches the real case; (2) a frob:used-by declaration pointing at a nonexistent/non-reaching consumer fails; (3) the entry-point allowlist is honored with per-file reasons; (4) tests: an orphan file warns, a 1-ref file weak-warns, a 2-ref file passes, a valid declaration passes, a dangling declaration fails. This is a WAIVABLE-warning gate (not error) per the user, so it does not block builds, but every orphan must be waived-with-reason or fixed -- honest accounting, same posture as the other advisory-but-tracked families.