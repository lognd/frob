## Done report

Changed:
- src/frob/check/_python.py::_cached_snapshot (new: thread-safe, per-root memoized `build_graph` snapshot so dup/arch's waiver cross-reference reuses gates' single build, T-0122)
- src/frob/check/_python.py::_waive_edges_for_rule (new: WAIVE edges targeting a rule id, from the shared snapshot)
- src/frob/check/_python.py::_dup_group_symrefs, _dup_waived_symrefs, _dup_group_diag, _dup_summary (new: dup-group <-> frob:waive DUP001/DUP002 cross-reference by exact fragment symref)
- src/frob/check/_python.py::_dup_group_covering_waivers (new, review fix: a group counts as waived only when EVERY fragment's symref is covered by a matching waiver -- full-group coverage, not "any fragment matches". Prevents a waiver reasoned about one group, e.g. an exact `{foo,bar}` pair, from silently also excluding a DISTINCT superset group, e.g. renamed `{foo,bar,baz}`, that `frob.dup._legacy` deliberately allows the same symbol to sit in. `_dup_group_diag` now lists every covering waiver symref, not just one.)
- src/frob/check/_python.py::_run_dup (rewritten: waiver-aware via full-group coverage, "N duplicate groups (M waived)" headline; waived groups render as `note` diagnostics, never hidden)
- src/frob/check/_python.py::_arch_summary (rewritten: takes unaccounted/waived/suggestion counts, "N warnings (M waived), K suggestions") -- unchanged by the review fix, reviewer confirmed the ARCH001 path is sound (symref-exact, reuses `frob.gates._apply_waivers`, one violation per finding so no group-coverage ambiguity applies)
- src/frob/check/_python.py::_arch001_violations, _arch_long_function_waived_symrefs (new: ARCH001 Violations built from the already-computed suggestions, run through frob.gates._apply_waivers -- ceiling= honored, no second analyze_project pass) -- unchanged by the review fix
- src/frob/check/_python.py::_run_arch (rewritten: waiver-aware for ARCH001 long-functions only; every other arch category stays on T-0101's unwaivable channel) -- unchanged by the review fix
- docs/modules/dup.md: rewrote the T-0375 section to document the full-group-coverage rule explicitly (with the exact/renamed-superset scenario worked through) and why the check-stage summary deliberately does NOT reuse the real DUP001/DUP002 gate's broader file-scoped waiver matching (`frob.dup._rules` never sets `Violation.symref`, so `frob.gates._match_waiver` falls back to file-scope for those rules -- reusing that here would let one waiver anywhere in a file swallow every group the file participates in)
- docs/modules/arch.md, docs/modules/gates.md: unchanged by the review fix (ARCH001 path was already correct)
- tickets.md: T-0375 scope extended to add src/frob/check/, the three docs files, and tests/unit/test_check.py -- the fix's actual location (per-stage summary rendering) lives in frob.check, not the originally-scoped frob.dup/frob.arch/frob.gates packages themselves

Review fix (round 2): reviewer reproduced a real over-exclusion bug in the DUP001/DUP002 matching -- the original "does ANY fragment in this group share a symref with ANY waived symref" rule let a single waiver reasoned about one pairing (e.g. `foo`+`bar`, an exact-clone group) also silently exclude a DISTINCT, larger renamed-superset group (e.g. `foo`+`bar`+`baz`) containing an un-reasoned-about new symbol (`baz`), because `frob.dup._legacy`'s `_exact_groups`/`_renamed_groups` deliberately let one symbol sit in both group types. Fixed by requiring full-group coverage: `_dup_group_covering_waivers` only marks a group waived when EVERY fragment's symref is named by some waiver. The ARCH001/arch path and `_cached_snapshot` were confirmed sound by the reviewer and left unchanged.

Evidence:
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waived_group_excluded_from_headline_but_listed (updated: now waives BOTH fragments of the 2-fragment group, matching the full-coverage rule)
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_unwaived_group_still_counts
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_partial_group_waiver_does_not_hide_whole_group (new, review fix: waiving only ONE of a 2-fragment group's fragments must not mark the group waived)
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiver_on_shared_symbol_does_not_hide_distinct_superset_group (new, review fix: the reviewer's exact regression -- exact `{foo,bar}` fully waived, renamed `{foo,bar,baz}` superset group must still count since `baz` is unwaived)
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiving_every_fragment_of_superset_group_waives_it_too (new, review fix: the flip side -- once `baz` is also waived, the renamed superset group is fully covered and IS excluded too, proving this is "full coverage", not "never waivable")
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_waived_long_function_excluded_from_headline_but_listed
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_unwaived_long_function_still_counts
- Full `tests/unit/test_check.py` (28 tests) passes: `uv run pytest tests/unit/test_check.py -q -p no:cacheprovider -o addopts=""` -> `28 passed`.
- Real-repo before/after (`uv run frob check --only dup --only arch`): before this ticket, frob-dup reported "127 duplicate groups" and frob-arch "0 warnings, 3 warnings" raw. After the review fix: `pass frob-dup 116 duplicate groups (11 waived)` and `pass frob-arch 0 warnings (3 waived), 74 suggestions` -- UNCHANGED from before the review fix, confirming none of this repo's 11 real DUP001/DUP002 waivers happened to rely on the over-exclusion bug (each already covers its full group); the fix corrects the general-case semantics without altering this repo's real counts.
- `uv run frob check --ticket T-0375` (full run, ruff/ty/cycle/dup/arch/gates) passes clean: `0 errors, 1 warning, 41 waived` on gates, no SCOPE001/PRE001/DOC/COV findings against the extended scope.

Filed: none

Gates: `frob check --ticket T-0375` clean (0 errors across all stages; the sole non-waived gates warning is TEST006 "no coverage stamp found", pre-existing and unrelated to this change per the agent playbook's "no `make coverage`" rule).
