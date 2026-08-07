## Done report

Changed:
- src/frob/gates/_refs.py (new) -- ref_gate, REF001/REF002/REF003, `[[refs.entrypoint]]` allowlist loader, `frob:used-by` declaration parser+verifier, syntactic-position reference detector (`_candidate_tokens`/`_tokens_reach`)
- src/frob/gates/__init__.py -- wired `refs` into `_ALL_GATES`/`_build_jobs` (always against `repo_root`, same posture as `docanchor`), added REF001/002/003 to `_KNOWN_GATE_RULES`
- src/frob/graph/dsl.py -- registered `used-by` as a reserved marker verb (`_RESERVED_MARKER_VERBS`) so the generic directive parser doesn't misreport it as an unknown-verb `MalformedDirective`; `frob._refs` owns and verifies it directly
- frob.toml -- added `[[refs.entrypoint]]` allowlist (README.md, LICENSE, CHANGELOG.md, pyproject.toml, frob.toml, frob.lock, src/frob/__main__.py), each with a reason
- docs/modules/gates.md -- REF001/002/003 rows in the rule catalog table, new "Anti-orphan file-reference gate T-0396" subsection
- tests/test_refs_gate.py (new) -- 12 tests across tiers, declare-where-used (valid + two dangling shapes), entrypoint allowlist, severity/degrade, and the syntactic-position reference-detection discipline (bare prose vs. real markdown link)

Real REF001 finding lines for the registry yamls (frob check --only refs on this repo, post-merge with main tip decce26, all 9 registry files flagged as required by acceptance criterion 1):

```
[gates] docs/design/registry/RECONCILIATION.md:0  REF001  REF001: docs/design/registry/RECONCILIATION.md has no inbound references from any other tracked file ...
[gates] docs/design/registry/arch-checks.yaml:0    REF001  REF001: docs/design/registry/arch-checks.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/compliance.yaml:0     REF001  REF001: docs/design/registry/compliance.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/evasion.yaml:0        REF001  REF001: docs/design/registry/evasion.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/patterns.yaml:0       REF001  REF001: docs/design/registry/patterns.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/pii.yaml:0            REF001  REF001: docs/design/registry/pii.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/secrets.yaml:0        REF001  REF001: docs/design/registry/secrets.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/supply-chain.yaml:0   REF001  REF001: docs/design/registry/supply-chain.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/system-design.yaml:0  REF001  REF001: docs/design/registry/system-design.yaml has no inbound references from any other tracked file ...
[gates] docs/design/registry/weaknesses.yaml:0     REF001  REF001: docs/design/registry/weaknesses.yaml has no inbound references from any other tracked file ...
```
Full run: `pass  gates  0 errors, 484 warnings, 0 waived  [refs=5.04s]` -- exit 0 (WARN-only, never blocks the build), 484 REF001/REF002 warnings total across the whole repo.

Honest disclosure of a real dogfooding failure this ticket caught in itself: the first working version of the auto-scan (bare substring match anywhere in a file's text) produced a FALSE 2+-refs PASS for the registry yamls, because `docs/design/registry/README.md` and `RECONCILIATION.md` both name every yaml's basename in prose/table cells (e.g. `` `patterns.yaml` ``), and `tickets.md`'s own ticket body text does too. A bare substring match cannot tell "prose mentioning a filename" from "a real reference", so it silently defeated the gate's own purpose. Fixed by restricting auto-detection to real reference SYNTACTIC positions (markdown link `](path)`, quoted string literal, import/require/include/use statement target, frob:doc/describes/used-by directive target) -- `_candidate_tokens`/`_tokens_reach` in `_refs.py`, documented in both the module docstring and `docs/modules/gates.md`'s new subsection. A second false-positive round (this module's OWN docstring text and this ticket's body both containing the literal string "frob:used-by" in prose) required restricting `frob:used-by` directive recognition to line-start-after-comment-leader form (`_strip_comment_prefix`/`_directive_target`), same posture as `frob.graph.dsl`'s own `_LINE_RE`. Also tried and deliberately dropped: a bare containing-directory substring fallback (the "loader glob base dir" shape) -- it reintroduced the exact same false-pass on the registry yamls, so declared `frob:used-by` is the only mechanism for that shape, not an auto-heuristic.

Acceptance criterion (2) verified directly by `TestUsedByDeclaration::test_dangling_declaration_nonexistent_consumer_fails` (consumer path never a tracked file -> REF003) and `test_dangling_declaration_non_reaching_consumer_fails` (consumer exists but never references the declaring file back -> REF003) -- both also assert REF001 still fires alongside REF003 (a dangling declaration is not evidence of use, so it must not suppress the orphan tier).

Evidence: tests/test_refs_gate.py::TestTiers::test_zero_refs_warns_ref001, tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002, tests/test_refs_gate.py::TestTiers::test_two_refs_passes, tests/test_refs_gate.py::TestUsedByDeclaration::test_valid_declaration_counts_not_dangling, tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_nonexistent_consumer_fails, tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_non_reaching_consumer_fails, tests/test_refs_gate.py::TestEntrypointAllowlist::test_allowlisted_file_is_exempt, tests/test_refs_gate.py::TestEntrypointAllowlist::test_non_allowlisted_orphan_still_fires, tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity, tests/test_refs_gate.py::TestSeverityAndDegrade::test_no_tracked_files_returns_empty, tests/test_refs_gate.py::TestReferenceDetection::test_bare_prose_mention_does_not_count_as_a_reference, tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference (all 12 collected and passing, `uv run pytest tests/test_refs_gate.py -q` -> `............` 12 passed)

Filed: none (no out-of-scope discoveries needing a separate ticket this pass)

Gates: `uv run frob check --delta --ticket T-0396 --json` clean post-merge-with-main -> `gates 0 0/501 new  0 errors, 0 warnings, 41 waived`; `ruff-check`/`ruff-format` (both `uv run ruff` and PATH `ruff`) clean; `ty` clean; `frob-cycle` clean. `uv run frob test --base main` -> `[PASS] python exit=0 1.81s` (tests/test_gates.py::test_gates_run_gates_integration, tests/test_graph.py::test_graph_build_lock_drift_integration, tests/test_refs_gate.py). Scope was widened from the original `src/frob/gates/`, `src/frob/graph/`, `frob.toml` to also include `docs/modules/gates.md` and `tests/test_refs_gate.py` (via `frob ticket sweep T-0396` after the edit) since the ticket's own acceptance criteria explicitly require both a doc section and a test fixture. `git diff main --diff-filter=D --stat` is empty (deletion-filter land rule, section 9 of the playbook) after re-merging main (which had moved to decce26, well past this worktree's stale creation base, per the T-0167-style lesson section 1 warns about).

NOT closed -- review-gated per the dispatch instructions; leaving in `in-progress` for reviewer close.

## Done report (round 2 -- reviewer-rejected, false-positive fix)

**The round-1 "484 warnings, all real" framing above was WRONG and is retracted.** Reviewer measured an 86% false-positive rate on this repo's own tree (326 of 379 REF001 findings were detector gaps, not real orphans) -- exactly the "high-FP noise that gets blanket-waived" failure this gate exists to prevent. Two systemic detector bugs, both reviewer-cited, both fixed:

1. **Multi-name `from X import a, b, c` only captured the module prefix.** `_candidate_tokens("from frob.arch import _cpp, _python")` returned `('frob.arch',)` only -- `src/frob/arch/_cpp.py` (reached only via that import) was a false orphan even though `frob/arch/__init__.py` imports and calls it. Fixed: `_python_import_targets` (new) parses every name in a `from`-import (single-line, comma-list, AND parenthesized/multi-line continuation) and a plain `import a, b.c as d`, producing per-name candidate tokens. `_tokens_reach` (rewritten) resolves a bare imported name against a `.py` target's extensionless STEM (`frob.arch._cpp` -> stem `_cpp`) -- this is also what makes a dispatch table's bare quoted module-name string (`"ack_runner"` reaching `ack_runner.py`) resolve, since neither shape spells the target's full `.py`-suffixed basename literally. **Deliberately restricted the stem shortcut to `.py` targets**: a stem match against a non-Python target reintroduced the exact same false-PASS bug on the registry yamls (a quoted English word colliding with a data file's stem, e.g. a test asserting `g.family == "compliance"` was unrelated to `compliance.yaml` but "compliance" as a bare quoted token matched its stem) -- caught during fix-verification, not by the reviewer, and is why the restriction exists.
2. **Pytest-discovered test files were permanent false orphans (52% of the false REF001s).** A test file is referenced by the test RUNNER via filesystem/naming convention, which no textual auto-scan can see. Fixed: `ref_gate` now skips REF001/REF002 entirely for any file `frob.excludes.is_test_file` recognizes (same predicate `frob.arch`/coverage/the touched-set selector already use) -- still subject to REF003 (a test file's own dangling `frob:used-by` is still a lie).

**Three more false-positive causes found and fixed during fix-verification (self-caught while manually sampling remaining findings for genuineness, not reviewer-cited but required to make the "genuine signal" claim honest):**

3. `_QUOTED_RE`'s original `["\']([^"\']{2,300})["\']` opened on EITHER quote character and closed on EITHER quote character -- an apostrophe in prose ("argv's") paired with a distant, mismatched `"` and swallowed a huge span into one bogus token, hiding a real short quoted path (`"_harness.py"`) inside it instead of extracting it. Fixed with a backreference requiring the SAME quote character to close, and excluding newlines from the match.
4. `frob:tests <path>::<qualname>` and `frob:doc <path>#anchor` directive tokens kept their `::qualname`/`#anchor` suffix attached, so they never equaled the bare target path/basename and a real directive-backed reference was invisible. Fixed: strip at both `::` and `#` when building the directive token. Also added `tests` to the recognized directive verb set (`frob:tests` names the exact file its test binds to, same footing as `frob:doc`).
5. This module's OWN docstring used two of the actual registry yaml basenames, double-quoted, as illustrative code examples inside backtick spans -- the quote characters inside those spans were real matches for `_QUOTED_RE` regardless of the surrounding backticks, so `_refs.py` itself became a false inbound reference for two of the nine registry yamls it exists to catch. Fixed by renaming the illustrative examples to a generic placeholder filename instead of a real registry basename. (NOTE: this Done report paragraph itself had to be reworded a second time for the same reason -- an earlier draft of this very paragraph, quoting the two real basenames as an example, reintroduced the identical self-reference against tickets.md; this final wording deliberately names neither basename in quotes.)

**Re-measured on this repo (`uv run frob check --only refs`, same HEAD, post-fix):**

```
pass  gates  0 errors, 82 warnings, 0 waived  [refs=4.6s]
```
82 total (28 REF001 + 54 REF002), down from 484 (a discarded, wrong measurement) -- registry yamls still 9/9 REF001 as required:
```
[gates] docs/design/registry/RECONCILIATION.md:0   REF001 ...
[gates] docs/design/registry/arch-checks.yaml:0    REF001 ...
[gates] docs/design/registry/compliance.yaml:0     REF001 ...
[gates] docs/design/registry/evasion.yaml:0        REF001 ...
[gates] docs/design/registry/patterns.yaml:0       REF001 ...
[gates] docs/design/registry/pii.yaml:0            REF001 ...
[gates] docs/design/registry/secrets.yaml:0        REF001 ...
[gates] docs/design/registry/supply-chain.yaml:0   REF001 ...
[gates] docs/design/registry/system-design.yaml:0  REF001 ...
[gates] docs/design/registry/weaknesses.yaml:0     REF001 ...
```

**FP measurement on the remaining findings**: exhaustively reviewed ALL 28 REF001 findings by hand (small enough to do exhaustively rather than sample), not just the 9 registry files -- `.claude/agents/exhaustive-researcher.md`, `CLAUDE.md`, `docs/commands/parse.md`, `docs/design/cwe-1000-registry.md`, `docs/design/security-corpus.md`, `docs/design/system-performance-corpus.md`, `docs/guides/agentic-workflow.md`, `docs/guides/editors.md`, `docs/guides/install.md`, `docs/modules/dup-sota-survey.md`, `docs/rework.md`, `docs/strata/charter.md`, `invariants/INV-002/003/004.md`, `strata-core/strata_core.pyi`, plus the 9 registry files and RECONCILIATION.md. For every one, manually grepped the whole tracked-file corpus for its basename and confirmed every hit outside the file itself was a bare prose/parenthetical citation ("see CLAUDE.md", "(docs/rework.md's cycle-...)", "(docs/modules/dup-sota-survey.md section 4)") -- never a markdown link, quoted-path literal, import, or directive target. Under this gate's own stated detection contract (real syntactic reference position, not prose), **0 of 28 REF001 findings are detector false positives** in this sample -- the same standard that correctly excludes the registry yamls' own prose mentions is what these findings are consistent with. Did not exhaustively re-verify all 54 REF002 findings (out of scope of "REF001 findings" the reviewer asked for), but spot-checked ~10 (`src/frob/fuzz/_obligations.py`, `src/frob/lang/_walk_python.py`, `Makefile`, `scripts/bump_version.py`, `src/frob/logging/formatter.py`, `src/frob/dup/_legacy_cpp.py`, `src/frob/dup/_legacy_common.py`, `docs/design/architecture-check-catalog.md`, `docs/design/compliance-corpus.md`, `docs/design/supply-chain-corpus.md`) and all showed exactly one genuine syntactic-position reference, consistent with REF002's definition.

**New regression tests** (`tests/test_refs_gate.py::TestReviewerRegressionRound2`, 6 tests): `test_multi_name_from_import_target_not_flagged`, `test_parenthesized_from_import_target_not_flagged`, `test_dispatch_table_bare_string_target_not_flagged`, `test_pytest_collected_test_file_not_flagged`, `test_registry_style_yaml_with_only_prose_mentions_still_fires` (the fix must not regress the motivating case), `test_genuinely_unreferenced_module_still_fires` (the fix must not blanket-pass everything). All 18 tests in the file pass: `uv run pytest tests/test_refs_gate.py -q` -> `..................` (18 passed).

Evidence (6 new ids recorded on top of round 1's 12, 18 total): tests/test_refs_gate.py::TestReviewerRegressionRound2::test_multi_name_from_import_target_not_flagged, tests/test_refs_gate.py::TestReviewerRegressionRound2::test_parenthesized_from_import_target_not_flagged, tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged, tests/test_refs_gate.py::TestReviewerRegressionRound2::test_pytest_collected_test_file_not_flagged, tests/test_refs_gate.py::TestReviewerRegressionRound2::test_registry_style_yaml_with_only_prose_mentions_still_fires, tests/test_refs_gate.py::TestReviewerRegressionRound2::test_genuinely_unreferenced_module_still_fires

Changed (round 2, on top of round 1's files): src/frob/gates/_refs.py (`_python_import_targets`, `_split_import_names`, `_FROM_IMPORT_RE`, `_PLAIN_IMPORT_RE`, `_SINGLE_IMPORT_RE`, rewritten `_tokens_reach`/`_candidate_tokens`/`_QUOTED_RE`, `is_test_file` skip in `ref_gate`, `tests` added to `_DIRECTIVE_RE`, `::`/`#` suffix stripping for directive tokens, docstring self-reference fix); docs/modules/gates.md (round-2 correction paragraph in the subsection); tests/test_refs_gate.py (`TestReviewerRegressionRound2`, 6 new tests).

Gates: `uv run frob check --delta --ticket T-0396 --json` clean -> `gates 0 0/105 new  0 errors, 0 warnings, 41 waived`; `ruff-check`/`ruff-format` (both `uv run ruff` and PATH `ruff`) clean; `ty` clean; `frob-cycle` clean. `uv run frob test --base main` -> `[PASS] python exit=0 1.93s`.

Filed: none.

STILL NOT closed -- review-gated; leaving in `in-progress` for reviewer re-review.

## Done report (round 3 -- reviewer-rejected, false-negative fix)

**Round 2 was rejected for one precise false negative** (import resolution, dispatch-table stem match, registry-yaml acceptance, and the dangling-declaration mechanism were all verified sound and kept as-is). The round-2 pytest-discovery fix used `frob.excludes.is_test_file`, which exempts ANY path with a `tests/` directory COMPONENT, not just files that are themselves tests -- so a genuinely-orphaned non-test file that merely lives under `tests/` (reviewer repro: `tests/fixtures/orphan_helper.py`, no `test_*` functions, imported nowhere) was silently exempted from REF001 alongside real test files.

**Fix**: stopped importing/using `is_test_file` in this gate entirely. Added a gate-local, narrower predicate `_is_collectible_test_filename` (`src/frob/gates/_refs.py`) that checks ONLY the file's own basename against the test-collection naming convention (`test_*.py`, `*_test.py`, `.test.`/`_test.` for TS/Rust analogs) -- never true merely because the path sits under a `tests/` directory. Per the reviewer's explicit instruction, `is_test_file` itself was NOT changed (it stays correct and shared for its other callers, e.g. the arch gate T-0359, where "skip everything under tests/" is the right rule).

**Re-measured on this repo** (`uv run frob check --only refs`, same HEAD):

```
pass  gates  0 errors, 133 warnings, 0 waived  [refs=5.4s]
```
30 REF001 + 103 REF002 = 133, up from round 2's 82 (28+54) -- the increase is EXPECTED and correct: every non-test-named file previously blanket-exempted under `tests/` (CVE fixture JSON, golden export files, `.strata` litmus fixtures, `conftest.py`-adjacent helpers, etc.) is now actually evaluated instead of skipped. Registry yamls still 10/10 REF001 (9 yamls + RECONCILIATION.md) -- unchanged, verified again:
```
[gates] docs/design/registry/RECONCILIATION.md:0   REF001 ...
[gates] docs/design/registry/arch-checks.yaml:0    REF001 ...
[gates] docs/design/registry/compliance.yaml:0     REF001 ...
[gates] docs/design/registry/evasion.yaml:0        REF001 ...
[gates] docs/design/registry/patterns.yaml:0       REF001 ...
[gates] docs/design/registry/pii.yaml:0            REF001 ...
[gates] docs/design/registry/secrets.yaml:0        REF001 ...
[gates] docs/design/registry/supply-chain.yaml:0   REF001 ...
[gates] docs/design/registry/system-design.yaml:0  REF001 ...
[gates] docs/design/registry/weaknesses.yaml:0     REF001 ...
```

**Newly-surfaced findings, hand-verified**: the full 30-item REF001 list is round 2's already-exhaustively-verified 28 files PLUS exactly 2 new ones, both under `tests/`: `tests/unit/cve/fixtures/vet_mirror/cves/2024/1xxx/CVE-2024-1000.json` and `CVE-2024-1001.json` -- confirmed via repo-wide grep that their only mention anywhere is a bare prose list in `tickets-archive.md` ("- tests/unit/cve/fixtures/vet_mirror/cves/2024/1xxx/CVE-2024-1000.json, CVE-2024-1001.json (new synthetic fixtures; ...)"), never a real syntactic reference -- genuine orphans, likely loaded via a directory glob at runtime rather than a literal filename, exactly the shape `frob:used-by` exists to let an owner declare explicitly. Spot-checked ~15 of the newly-surfaced REF002 findings (`tests/golden/frob_export_iam.json`, `tests/golden/frob_export_k8s.yaml`, `tests/unit/cve/fixtures/CVE-2021-44228.json`, `tests/unit/cve/fixtures/mirror/cves/.../CVE-2024-3094.json`, `tests/unit/strata/litmus/cwe_22_unfired.strata`, `cwe_352_unfired.strata`, `cwe_502_hardened.strata`, `cwe_502_vuln.strata`, `cwe_611_unfired.strata`) -- every one is a real fixture/golden/litmus data file with exactly one genuine consumer (the test module that loads it), consistent with REF002's definition, not a detector artifact.

**New regression test** (`tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dead_non_test_file_under_tests_dir_still_fires`): writes `tests/fixtures/orphan_helper.py` (no test-shaped name, no consumer) alongside a real `tests/test_something.py`; asserts the fixture STILL fires REF001 while the real test file stays exempt. All 19 tests in the file pass: `uv run pytest tests/test_refs_gate.py -q` -> `...................` (19 passed).

Evidence (1 new id on top of round 2's 18, 19 total): tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dead_non_test_file_under_tests_dir_still_fires

Changed (round 3, on top of rounds 1-2): src/frob/gates/_refs.py (removed the `frob.excludes.is_test_file` import/usage, added `_is_collectible_test_filename`, updated both docstrings that described the old broad exemption); tests/test_refs_gate.py (`test_dead_non_test_file_under_tests_dir_still_fires`).

Gates: `uv run frob check --delta --ticket T-0396 --json` clean -> `gates 0 0/157 new  0 errors, 0 warnings, 41 waived`; `ruff-check`/`ruff-format` (both `uv run ruff` and PATH `ruff`) clean; `ty` clean; `frob-cycle` clean. `uv run frob test --base main` -> `[PASS] python exit=0 2.31s`.

**Minor, not fixed this round (reviewer flagged as non-blocking)**: backtick-code-span doc mentions (`` `path` `` in markdown prose, not a real `](path)` link) still don't count as references, so some docs listed only in `docs/index.md`'s prose/table (not real hyperlinks) still fire REF001 -- a calibration choice consistent with what makes the registry-yaml motivating case work at all (see round 2's Done report and `_refs.py`'s module docstring). Left as-is per the reviewer's own note; a follow-up ticket for markdown-table-cell-as-reference detection was not filed since the reviewer characterized it as optional, not required.

Filed: none.

STILL NOT closed -- review-gated; leaving in `in-progress` for reviewer re-review.
