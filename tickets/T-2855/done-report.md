## Done report

Changed:
- docs/modules/dup.md (repointed 14 frob:describes edges from frob-core/src/lib.rs to the module each symbol actually moved to in T-2846's split; fixed one stale line/path in prose reference)
- docs/modules/dup-sota-survey.md (fixed stale file/line pointer for apted_similarity, lib.rs -> r4.rs; prose left unchanged, it was already accurate)
- frob-core/src/lib.rs (repointed frob:tests directives for symbols that moved out; added frob:doc for hash_str, which stayed)
- frob-core/src/r3.rs (added frob:doc for is_numeric_literal/is_string_literal)
- frob-core/src/r4.rs (added frob:doc for build_postorder/zhang_shasha_distance)
- frob-core/src/r5.rs (added frob:doc for AntiUnifyErr/Template/anti_unify_core)
- frob-core/src/exact_regions.rs (added frob:doc for build_suffix_array/kasai_lcp)
- frob-core/src/callgraph.rs (added frob:doc for arch_sim_ratio)
- tests/unit/test_dup_core.py (repointed frob:tests directives to moved symbols)
- tests/test_arch_near_duplicate_native.py (repointed frob:tests directive to moved symbol)

Root cause (matches coordinator's characterization): T-2846's split moved ~18 symbols out of frob-core/src/lib.rs into r3.rs/r4.rs/r5.rs/exact_regions.rs/callgraph.rs, but the doc/test frob:describes and frob:tests directive TARGETS were never repointed, and the split forced several previously-private helper fns/types to become pub(crate) (crate-visible across the new file boundary), which is "public" for COV001/TEST001 purposes even though they were never public before the split. Both are the same underlying cause: new files inherit no doc/reference edges automatically.

Measured (unbudgeted, gate-summary present, --ticket T-2855):
- Before this fix (root checkout, matches coordinator's independent measurement): REF001=5, DRIFT002=53 (26 lib.rs, 14 dup.md, 7 test_dup_core.py, 2 test_arch_near_duplicate_native.py, 4 tickets-data-storage.md [out of scope]), COV001=12, DOC006=3, TEST001=8.
- After fix, in T-2855's declared scope: REF001=0, DRIFT002=0, COV001=0, DOC006=0, TEST001=0, DUP001=0 (transient false-positive from one comment placement inside a function body vs above it -- resolved by moving the frob:doc comment above the fn signature, no behavior change).
- REF001's 5 findings resolved WITHOUT any [[refs.entrypoint]] addition: layer-1 auto-scan already counts a frob:describes/frob:tests directive target as a real inbound reference, so repointing the DRIFT002 edges to the correct new files also gave those files their first real inbound reference. No entrypoint glob was needed (unlike T-2820's REF001 fix).
- Remaining errors after fix are ALL outside T-2855's scope (docs/modules/tickets-data-storage.md DRIFT002 x4, docs/audits/test005-zero-classification-t1418.md DOC006 x1, src/frob/graph/callgraph.py COV001 x1, src/frob/strata/_multifile.py TEST001 x1) -- a separate root cause (likely T-2695's _store.py migration split, unrelated to T-2846), filed as T-2858 (renumbers at land) rather than silently expanding scope.

Evidence:
- tests/unit/test_dup_core.py::TestAptedSimilarity::test_identical_trees_similarity_one
- tests/test_arch_near_duplicate_native.py::test_near_duplicate_cluster_dispatches_to_native_and_matches_reference
- Full targeted re-run: tests/unit/test_dup_core.py + tests/test_arch_near_duplicate_native.py, 26/26 passed
- frob natives build: frob_core built cleanly after the .rs comment-only edits

Filed: T-2858 (renumbers at land) -- the 4 out-of-scope error findings above, a separate root cause from T-2846/T-2855.

Gates: frob check --json --ticket T-2855 (unbudgeted, gate-summary present) shows 0 in-scope errors post-fix.

Structural lesson (per coordinator's request): promoting a rule to ERROR and splitting a file are in tension unless the split brief explicitly checks REF001/DRIFT002/COV001/TEST001 for the new files. A split that moves symbols without repointing their doc/test directive targets, or that widens a previously-private helper's visibility to cross a new file boundary, silently creates fresh violations of every promoted-to-ERROR rule that a per-ticket "frob check" scoped to the split's own files would not have caught if measured before rather than after the doc/test directives existed at all.

### Changed
```
 tickets/T-2855/ticket.md           |  5 ++++-
 tickets/T-2858/ticket.md | 33 +++++++++++++++++++++++++++++++++
 2 files changed, 37 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_dup_core.py::TestAptedSimilarity::test_identical_trees_similarity_one` (pytest node id, verified passing when recorded)
- `tests/test_arch_near_duplicate_native.py::test_near_duplicate_cluster_dispatches_to_native_and_matches_reference` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 24 error(s), 581 warning(s), 794 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DSL001@tests/unit/test_coordinator_scripts.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2855, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
