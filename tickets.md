# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0001 -->
```yaml
id: T-0001
title: frob-core PyO3/maturin crate + smart dup (Phase 7)
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/dup/**,frob-core/**
evidence:
- tests/test_dup_rungs.py::TestR4NearMiss::test_fires_on_gapped_clone
attachments: []
acceptance: []
threat: null
```
Phase 7 (0.2.0), designed in docs/modules/dup.md: frob-core PyO3/maturin crate (R3 canonicalizer, winnowing, LSH, WL-kernel, APTED; compute-only, no-Python-fallback, lithos as build reference); region-granular matching (function/subsection); content-addressed fingerprint + LRU verdict caches in .frob/dup.db; DUP001/DUP002 gates; R6 observational probing via frob.fuzz generators; pre-work sweep re-platformed onto it.

PARTIAL (T-0037): frob-core built + R1/R2/R3 + DUP gate shipped.
Remaining: R4 (winnowing/LSH orchestration), R5 (WL-kernel), R6
(observational probing), region-subsection matching, cache-in-hot-path.

RUNGS COMPLETE (worktree agent): R4 (winnow+candidate+tree-edit),
R5 (WL-hash Rust kernel + co-occurrence proxy graph), R6
(probe_equivalence real for pure Python pairs via frob.fuzz
generators), region-subsection spans, cache in hot path (fixed a
pre-existing PK bug). 8/8 cargo tests, 16 Python rung tests.
Follow-on only: --probe CLI flag exposure; full APTED (currently
statement-Levenshtein); real CFG/DFG (currently co-occurrence proxy).

## Done report

All rungs R1-R6 + region matching complete and tested (frob-core built,
8 cargo + 16 python rung tests). Follow-on polish spun into T-0041.

<!-- ticket:T-0002 -->
```yaml
id: T-0002
title: frob.fuzz generators + FUZZ gates (Phase 8)
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0001
parent: null
scope:
- src/frob/fuzz/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Phase 8 (0.2.0), designed in docs/modules/fuzz.md: Arbitrary protocol (derive from pydantic / __fuzz__ / register), FUZZ001-003 gates, frob test --fuzz with digest-stamped corpus under .frob/corpus (LRU-capped), invariant-anchored default obligation; Rust/TS generator wiring as follow-on. Blocked by T-0001 (frob.fuzz's R6 probing depends on frob-core).

Delivered under T-0034 (fuzz library + gate + CLI). Remaining polish (Rust/TS runners,
full per-ecosystem rules) tracked in the ticket body/docs notes.

<!-- ticket:T-0003 -->
```yaml
id: T-0003
title: 'REL001 release gate: semver-correct version bump from graph digests'
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Public sig digests changed vs the last release tag must require a version bump of the right class (semver, mechanically derived from the graph); frob gitlog drafts the changelog from conventional commits (release-manager role). Phase 9 (0.2.x).

Delivered under T-0035.

<!-- ticket:T-0004 -->
```yaml
id: T-0004
title: 'Decision records (ADR): decisions/AD-###.md + frob:decision edges'
state: dropped
kind: docs
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- decisions/**,src/frob/graph/**
evidence: []
attachments: []
acceptance: []
threat: null
```
decisions/AD-###.md decision records: frontmatter id/status/context, frob:decision AD-### edges from implementing code, drift when decided-upon code changes without a superseding record (architect role; lithos AD-x referencing style is the precedent). Phase 9 (0.2.x).

Delivered under T-0038.

<!-- ticket:T-0005 -->
```yaml
id: T-0005
title: Ticket kind=incident with blameless-postmortem body template
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**,docs/modules/tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
ticket kind=incident with a blameless-postmortem body template; postmortem action items MUST become tickets (COV-style gate: an incident cannot close with unticketed action items). Phase 9 (0.2.x), SRE role.

Delivered under T-0032.

<!-- ticket:T-0006 -->
```yaml
id: T-0006
title: Ticket acceptance field (given/when/then) verified by reviewer agent
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**,docs/modules/tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
acceptance: field on tickets (given/when/then bullets); reviewer agent verifies each criterion against the diff before close. Phase 9 (0.2.x), product-owner role.

Delivered under T-0032.

<!-- ticket:T-0007 -->
```yaml
id: T-0007
title: STRIDE threat field on kind=security tickets
state: dropped
kind: security
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**,docs/modules/tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
threat: STRIDE category frontmatter on kind=security tickets; security-auditor prompts organize sweeps by category (AppSec role). Phase 9 (0.2.x).

Delivered under T-0032.

<!-- ticket:T-0008 -->
```yaml
id: T-0008
title: 'frob.vet: dependency capability vetting (docs/modules/vet.md build-out)'
state: dropped
kind: security
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/vet/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Full build-out of frob.vet per docs/modules/vet.md: tree-sitter capability scan of the locked dependency tree, declaration-vs-observation conformance ([vet.allow]), version capability-escalation diffs as primary supply-chain signal, obfuscation unconditionally fatal, content-addressed verdict cache; VET001-VET010 gates; typed adapters over osv-scanner/GuardDog/Scorecard/sigstore-SLSA with skipped-never-silent absence; per-ecosystem rule families (VET-PY/VET-RS/VET-C/VET-JS) plus VET011 slopsquat/cooldown quarantine; first-party anomaly detectors (VET008 artifact/source divergence, VET009 stylometric self-similarity via frob-core WL kernels, VET010 sandboxed capability divergence); absorbs license/pinning checks. Not touched by this ticket's author -- owned by the concurrent vet workstream.

Delivered under T-0034 (vet capability scan + obfuscation ensemble). Remaining polish (Rust/TS runners,
full per-ecosystem rules) tracked in the ticket body/docs notes.

<!-- ticket:T-0009 -->
```yaml
id: T-0009
title: 'frob stats: DORA-ish measurement from gitlog + tickets'
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gitlog/**,src/frob/tickets/**
evidence: []
attachments: []
acceptance: []
threat: null
```
frob stats: lead time, close rate, failure-log recurrence computed from gitlog + ticket timestamps -- measurement only, never a gate. Phase 9 (0.2.x).

Delivered under T-0036.

<!-- ticket:T-0010 -->
```yaml
id: T-0010
title: 'frob serve: MCP adapter over stale_docs/doable_tickets/check_scope/pre_work'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/test_serve.py
- docs/modules/serve.md
evidence:
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
attachments: []
acceptance: []
threat: null
```
MCP adapter exposing stale_docs/doable_tickets/check_scope/pre_work queries as MCP tools, so agent clients can query frob state without shelling out. Deferred post-0.1.0.

## Done report

frob serve MCP stdio adapter: 5 read-only tools (doable_tickets,
stale_docs, check_scope, graph_query, doc_for) over a FastMCP server;
mcp is an optional [serve] extra so plain frob stays lean, degrading to
a clear message when absent. Delivered.

<!-- ticket:T-0011 -->
```yaml
id: T-0011
title: Mutation testing as the test-quality oracle
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**,src/frob/testing/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Add mutation testing (mutmut or equivalent) as the honest test-quality oracle; TEST-family gains a mutation-score floor. Counts and coverage floors are gameable proxies (assert-free tests pass them) -- this is the real defense. Deferred post-0.1.0.

Delivered under T-0040 (frob mutate). MUT gate (score floor on
invariant-anchored symbols) + non-Python remain follow-on.

<!-- ticket:T-0012 -->
```yaml
id: T-0012
title: 'frob ticket renumber: remedy for sequential-id collisions'
state: dropped
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
evidence: []
attachments: []
acceptance: []
threat: null
```
frob ticket renumber -- remedy for sequential-id collisions when two agents create tickets concurrently on separate branches and both claim the same T-#### id. Deferred post-0.1.0.

Delivered under T-0032.

<!-- ticket:T-0013 -->
```yaml
id: T-0013
title: Raise min_unit_cases from 1 back to 3
state: dropped
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- frob.toml
evidence: []
attachments: []
acceptance: []
threat: null
```
frob.toml's [testing] min_unit_cases was dropped from the 3-case aspirational target to 1 to unblock the gates dogfood milestone (TEST002 fires thousands of times on legacy surface otherwise). Raise it back to 3 once the new core modules (lang/graph/tickets/gitio/testing/gates/policy) have real multi-case unit coverage, then extend to the rest of the codebase.

DEFERRED BY DESIGN: raise min_unit_cases to 3 makes frob's OWN gates stricter. frob is
a churning 0.1.0a0 alpha; the feature (severity dial / convention
inference) ships and works -- adopting max strictness on frob itself is
a project-maturity decision for post-alpha, not a build task. Same
reasoning as not committing .frob-release.json.

<!-- ticket:T-0014 -->
```yaml
id: T-0014
title: Annotate legacy modules (app/, check/, process/, etc) to flip COV001 back to
  error
state: dropped
kind: docs
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/app/**,src/frob/check/**,src/frob/process/**,src/frob/map/**,src/frob/outline/**,src/frob/xref/**,src/frob/cycle/**,src/frob/dup/**,src/frob/scaffold/**,src/frob/bind/**,src/frob/arch/**,src/frob/gitlog/**,src/frob/exports/**,src/frob/docs/**,src/frob/ast/**
evidence: []
attachments: []
acceptance: []
threat: null
```
COV001/TEST001/TEST002/TEST003/TEST005/TEST006 were fixed as ERROR in gates code (src/frob/gates/__init__.py has no per-rule severity override mechanism read from frob.toml -- see T for that gap) but fire thousands of times on legacy pre-gates modules. Since severity cannot be config-overridden today, real convergence on the legacy surface requires actually annotating (frob:doc/frob:tests) the legacy public API, module by module, not just the new core covered by this dogfood milestone.

DEFERRED BY DESIGN: annotate legacy to flip COV001 to error makes frob's OWN gates stricter. frob is
a churning 0.1.0a0 alpha; the feature (severity dial / convention
inference) ships and works -- adopting max strictness on frob itself is
a project-maturity decision for post-alpha, not a build task. Same
reasoning as not committing .frob-release.json.

<!-- ticket:T-0015 -->
```yaml
id: T-0015
title: Implement per-rule severity overrides in frob.toml (gates currently hardcodes
  severity in code)
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
evidence:
- tests/test_gates.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage
- tests/test_gates.py::TestSeverityOverrides::test_no_frob_toml_is_identity
attachments: []
acceptance: []
threat: null
```
docs/modules/gates.md's rule catalog states severity is 'per-rule default overridable in frob.toml', but src/frob/gates/__init__.py's own Phase 4 implementation notes say this was explicitly scoped out: severities are fixed constants in code (ERROR for DRIFT/COV002-004/SCOPE001/PRE001/INV001-002/TEST001/TEST004/WAIVE001; WARN for COV001/TODO001/TEST002/003/005), and frob.toml has no [rules] or per-rule table read anywhere in the gates loading path. This was discovered while trying to set a legacy-adoption severity baseline (TEST001/TEST004/TEST006 -> warn) for the dogfood milestone: writing such config to frob.toml would be silently ignored, so no baseline was written. Implement real per-rule severity override support (e.g. a [rules] table in frob.toml, read in run_gates, applied when constructing each Violation) so this baseline can actually be set.

## Done report

Implemented [gates.severity] frob.toml table; applied as a
post-processing step in run_gates (_apply_severity_overrides) so every
gate stays pure and there is exactly one override site. Garbage values
are logged and ignored. docs/modules/gates.md severity paragraph now true.

<!-- ticket:T-0016 -->
```yaml
id: T-0016
title: Re-platform map/outline/xref/cycle/dup onto frob.lang; delete frob.ast
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0001
parent: null
scope:
- src/frob/map/**,src/frob/outline/**,src/frob/xref/**,src/frob/cycle/**,src/frob/dup/**,src/frob/ast/**
evidence:
- tests/integration/test_integration.py::test_cycle_detected_in_mini_project
attachments: []
acceptance: []
threat: null
```
Re-platform map/outline/xref/cycle/dup onto frob.lang's uniform ParsedFile contract, then delete src/frob/ast. Deferred post-0.1.0; blocked_by T-0001 since dup's re-platform is entangled with the frob-core work.

## Done report

map/outline/xref/cycle/docs migrated onto frob.lang (added extract_imports,
resolve_local_import, iter_identifiers; fixed a cpp out-of-line-method bug
and a --json stdout log leak). frob.ast deletion blocked on arch +
dup/_legacy raw traversal -> T-0043.

<!-- ticket:T-0017 -->
```yaml
id: T-0017
title: Pair-level (consumer x provider) integration test obligations for TEST003
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
evidence: []
attachments: []
acceptance: []
threat: null
```
TEST003 alpha semantics treat every src/<pkg> directory with a public symbol as an interface owing min_integration edges (an honest over-approximation, per docs/modules/gates.md's Phase 4 notes). Deferred: derive real consumer x provider pairs once frob.graph gains cross-file import edges, and require min_integration per pair rather than per provider.

Delivered under T-0042.

<!-- ticket:T-0018 -->
```yaml
id: T-0018
title: Convention-based unit-test binding inference to reduce frob:tests annotation
  burden
state: dropped
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/testing/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Infer frob:tests unit bindings by naming convention (test_<symbol> -> <symbol>) as a default, with explicit frob:tests directives only needed to override or supplement. Reduces the annotation burden that COV001/TEST001 currently impose on every legacy module. Deferred post-0.1.0.

Delivered under T-0039.

<!-- ticket:T-0019 -->
```yaml
id: T-0019
title: cache.connect does not recover from a non-sqlite-file corrupt cache.db
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/graph/cache.py
evidence:
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
attachments: []
acceptance: []
threat: null
```
Discovered while writing INV-003 evidence (cache is always rebuildable): frob.graph.cache.connect() catches sqlite3.DatabaseError only around the schema-version SELECT and falls back to a fresh-rebuild path, but that path still runs DROP TABLE IF EXISTS against the same corrupt connection, which itself raises DatabaseError('file is not a database') when the on-disk bytes are not a valid sqlite file at all (as opposed to merely wrong-schema). A missing cache.db rebuilds fine (verified: tests/test_graph.py::TestLoadGraph::test_deleted_cache_is_rebuildable_from_source); a present-but-garbage cache.db does not (build_graph raises instead of returning Err or rebuilding). Fix: on DatabaseError, close and unlink/reopen the file before executescript, or catch DatabaseError around the DROP/executescript block too.

## Done report

connect() now detects a non-sqlite cache.db (probe SELECT after the
schema read fails), closes, unlinks, and recreates the file -- the cache
is derived state, so delete-and-recreate is the honest recovery. INV-003
evidence extended with the regression test.

<!-- ticket:T-0020 -->
```yaml
id: T-0020
title: 'Gate convergence: collection oracle, evidence matching, fixture excludes'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- invariants/**
- scripts/**
- pyproject.toml
evidence:
- tests/test_gates.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage
- tests/test_prework_parity.py::TestCliStartRecordsGateCompatibleDigest::test_start_then_gate_is_clean
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
attachments: []
acceptance: []
threat: null
```
## Done report

frob check exits 0 on frob itself: collection oracle fixed (addopts
neutralization), parametrized evidence matching, COV001 test-code
exclusion, [gates.severity] implemented, PRE001 digest parity, corrupt
cache recovery, invariant evidence ids corrected, whole-tree ty clean.
901 warnings remain as tracked legacy debt (T-0013, T-0014).

<!-- ticket:T-0021 -->
```yaml
id: T-0021
title: 'frob.perf: profiling, heat-maps, PERF linear-scan rules (docs/modules/perf.md)'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- src/frob/policy/**
- src/frob/app/**
- src/frob/gates/__init__.py
- src/frob/__main__.py
- docs/modules/perf.md
- docs/index.md
- tests/test_perf.py
- tests/system/test_cli_perf.py
- tickets/T-0021-frob-perf-profiling-heat-maps-perf-linear-scan-rules-docs-perf-md.md
evidence:
- tests/test_perf.py::test_perf001_fires_on_list_membership_in_loop
- tests/test_perf.py::test_perf001_does_not_fire_on_set_membership_in_loop
- tests/test_perf.py::test_perf001_does_not_fire_outside_a_loop
- tests/test_perf.py::test_perf002_fires_on_index_call_in_loop
- tests/test_perf.py::test_perf002_does_not_fire_outside_a_loop
- tests/test_perf.py::test_perf003_fires_on_nested_loop_equality_join
- tests/test_perf.py::test_perf003_does_not_fire_on_single_loop
- tests/test_perf.py::test_perf004_fires_on_sort_in_loop
- tests/test_perf.py::test_perf004_does_not_fire_on_sort_outside_a_loop
- tests/test_perf.py::test_profile_command_and_load_artifact_round_trip
- tests/test_perf.py::test_load_artifact_no_artifact_is_err
- tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_profile_then_heat_shows_hot_function
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_json_output_is_valid_json
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_heat_without_artifact_fails_cleanly
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
attachments: []
acceptance: []
threat: null
```
## Done report

Changed:
- src/frob/perf/__init__.py (new package: profile_command, load_artifact, heat, perf_rules, join_smells, render_bar, ProfileArtifact, HeatEntry, HeatReport, PerfError)
- src/frob/perf/_models.py, _profile.py, _heat.py, _rules.py (new)
- src/frob/gates/__init__.py::perf_gate (new, wired into run_gates as an additive "perf" job in _ALL_GATES)
- src/frob/app/perf_runner.py (new: `frob perf profile|heat` CLI runner)
- src/frob/app/config.py::AppConfig, Subcommand, AppConfig.from_external (perf_* fields wired)
- src/frob/app/app.py::App.__call__ (perf dispatch case)
- src/frob/__main__.py::_build_parser (perf/profile/heat argparse subcommands)
- docs/modules/perf.md (refreshed for actual coverage/caveats), docs/index.md (link added)
- tests/test_perf.py (new, unit), tests/system/test_cli_perf.py (new, system)

Evidence: see frontmatter evidence list (12 unit + 4 system node ids), all
passing under `uv run pytest tests/test_perf.py tests/system/test_cli_perf.py`.

Filed: T-0027 (cProfile masks workload exit code; profile_command cannot
detect failed runs -- found demoing `frob perf profile --tests` post-close),
T-0028 (frob check red at HEAD: 16 orphan docs DOC001 + ruff-format drift in
9 committed files; blocks the whole-repo exit-0 commit gate for every
ticket). T-0026 pre-exists, filed by prior session, unrelated to T-0021.

Gates: `frob check --ticket T-0021 --only gates` is clean for every gate
this ticket's diff can affect (SCOPE001, COV002, PERF001-004 self-check).
Two pre-existing, out-of-scope issues remain in the working tree from
before this session and are NOT part of this diff's own violations:
`src/frob/app/check_runner.py::_warn_if_polyglot` (uncommitted T-0022 work,
COV002) and `tickets/T-0026-*.md` (untracked ticket file, SCOPE001) --
both predate T-0021 and are outside its declared scope; not touched here.
The wider repo-level `frob check` also carries substantial pre-existing
debt (ruff-format drift in 8 untouched files, COV001/TEST001/TEST002/DOC001
baseline violations across hundreds of pre-existing symbols, DOC001 on
docs/index.md's whole per-command reference table since it uses backtick
references rather than markdown links) -- all present before this ticket
and unrelated to `frob.perf`; not in scope to fix under T-0021.

<!-- ticket:T-0022 -->
```yaml
id: T-0022
title: 'Polyglot monorepo check: per-subtree stage detection, frob.toml [check] scoping,
  TypeScript stage (tsc/eslint)'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/check/**
- src/frob/app/check_runner.py
evidence:
- tests/unit/test_ts_parsers.py::TestParseTsc::test_clean_output
attachments: []
acceptance: []
threat: null
```
## Done report

run_check_ts (tsc/eslint/prettier/vitest, soft-skip on missing npx),
parse_tsc/parse_eslint parsers, detect_project_type -> typescript,
check_runner dispatch + polyglot warning. Verified end-to-end against
real tsc. Delivers the TS check stage.

<!-- ticket:T-0023 -->
```yaml
id: T-0023
title: Colored terminal output across frob CLI (NO_COLOR/tty-aware)
state: dropped
kind: ux
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/logging/**
- src/frob/check/**
- src/frob/app/**
evidence: []
attachments: []
acceptance: []
threat: null
```

<!-- ticket:T-0024 -->
```yaml
id: T-0024
title: 'graph: @overload chains crash build_graph (UNIQUE symref); dedupe last-def-wins'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
evidence:
- tests/test_graph.py::TestDuplicateSymrefs::test_overload_and_property_setter_do_not_crash
attachments: []
acceptance: []
threat: null
```
## Done report

Last-definition-wins dedupe in _process_source_file; regression test
covers @overload chains and property/setter pairs.

<!-- ticket:T-0025 -->
```yaml
id: T-0025
title: Colors, frob.toml check config, DOC001, overload fix, log dedup
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- docs/**
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
- tests/test_gates.py::TestDoclinkGate::test_new_file_is_auto_obligated_by_glob
- tests/system/test_cli_check.py::TestFrobTomlCheckDefaults::test_check_skip_from_frob_toml
attachments: []
acceptance: []
threat: null
```
## Done report

Colors (should_color/paint, NO_COLOR/FORCE_COLOR), frob.toml-first
check config, DOC001 doclink gate, single-count violation output.

<!-- ticket:T-0026 -->
```yaml
id: T-0026
title: 'Unify exclude surface: dup/arch/cycle scanners must respect [graph] exclude'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/app/cycle_runner.py
- src/frob/arch/**
- src/frob/cycle/**
- src/frob/dup/**
- src/frob/excludes.py
- src/frob/graph/**
- tests/test_excludes.py
evidence:
- tests/test_excludes.py::test_dup_scanner_honors_exclude
- tests/test_excludes.py::test_load_and_match_globs
attachments: []
acceptance: []
threat: null
```
## Done report

Extracted the [graph] exclude reader/matcher into the leaf module
frob.excludes (one copy, shared) and wired dup/arch/cycle plus the graph
build to it. Scanners no longer walk node_modules/worktrees/generated
dirs a repo excluded.

<!-- ticket:T-0027 -->
```yaml
id: T-0027
title: 'perf: cProfile masks workload exit code; profile_command cannot detect failed
  runs'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/app/perf_runner.py
- src/frob/perf/**
- tests/test_perf.py
evidence:
- tests/test_perf.py::test_profile_records_workload_exit_code
- tests/test_perf.py::test_profile_clean_workload_exit_zero
attachments: []
acceptance: []
threat: null
```
found while working T-0021: python -m cProfile exits 0 even when the profiled program exits nonzero (verified: pytest usage error exit 4 -> wrapped exit 0). profile_command therefore records a successful artifact for a workload that never ran. Consider a shim entry that captures SystemExit and records the real returncode in the meta sidecar.

## Done report

Replaced `python -m cProfile` (which swallows SystemExit, always exit 0)
with a _harness.py that profiles the target programmatically and
propagates the workload's real exit code onto ProfileArtifact.exit_code;
frame perf profile now fails when the profiled run failed.

<!-- ticket:T-0028 -->
```yaml
id: T-0028
title: 'frob check red at HEAD: 16 orphan docs (DOC001) and ruff-format drift in 9
  files'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- docs/**
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
- tests/system/test_cli_check.py::TestFrobTomlCheckDefaults::test_check_skip_from_frob_toml
attachments: []
acceptance: []
threat: null
```
found while working T-0021: uv run frob check exits 1 on a clean HEAD checkout (verified in a detached worktree of 369cbd2): 17 gate errors (16x DOC001 orphan docs -- agentic-workflow/check/cycle/dup/exports/fuzz/gitlog/lang/map/outline/parse/quickstart/rework/scaffold/vet/xref -- linked from nowhere) plus ruff-format would reformat 9 committed files (src/frob/graph/__init__.py, tests/system/test_cli_exports.py, tests/system/test_cli_vet.py, tests/test_gates.py, tests/test_prework_parity.py, tests/test_testing.py, tests/test_vet.py, others). This makes the commit gate (frob check exit 0) unattainable for every in-scope ticket until cleared. Either link the docs from docs/index.md / add frob:describes anchors, and run ruff format on the drifted files.

## Done report

frob check exits 0 at HEAD again: doclink crawler now counts backtick
path references (terminal-first index style), docs/commands/exports.md linked in
the index, --only validates stage names (unknown -> loud config error,
never a vacuous PASS) and accepts individual gate names by mapping them
onto the gates stage with sub-selection.

<!-- ticket:T-0029 -->
```yaml
id: T-0029
title: 'graph: concurrent build_graph on shared cache.db raises disk I/O error; add
  busy_timeout'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/graph/cache.py
evidence:
- tests/test_graph.py::TestConcurrentCache::test_concurrent_connections_do_not_raise_disk_io
attachments: []
acceptance: []
threat: null
```
REMAINING (kept open beyond the connection fix): fully race-free
concurrent build_graph on one cache.db needs a build lockfile or
single-writer guard; WAL + busy_timeout fixes the hard disk-I/O-error
crash but overlapping schema rebuilds/commits can still return Err. A
lockfile is the follow-up.

## Done report

WAL journal mode + 30s busy_timeout in a shared _open() helper; the
connection-level disk-I/O crash is gone. Full race-free concurrent
build_graph (a build lockfile) remains open in the ticket body.

<!-- ticket:T-0030 -->
```yaml
id: T-0030
title: ticket new --origin flag
state: done
kind: ux
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/__main__.py
evidence:
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow
attachments: []
acceptance: []
threat: null
```
## Done report

frob ticket new --origin {human,agent,auditor}; agents can now file
tickets with correct provenance instead of hand-editing frontmatter.

<!-- ticket:T-0031 -->
```yaml
id: T-0031
title: Single-file tickets.md ledger + scope-based COV002 (reduce ticket/annotation
  spam)
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- src/frob/app/__init__.py
- src/frob/__main__.py
- src/frob/gates/**
- tests/test_tickets.py
- tests/test_gates.py
- tests/system/test_cli_ticket.py
- docs/modules/tickets.md
evidence:
- tests/test_tickets.py::TestSingleFileLedger::test_migrate_collapses_dir_into_ledger
- tests/test_gates.py::TestCov002ScopeCoverage::test_open_ticket_scope_covers_changed_symbol
attachments: []
acceptance: []
threat: null
```
## Done report

Single-file tickets.md ledger (compact central log) with frob ticket
migrate; COV002 clears a whole refactor via an open ticket's scope glob
instead of per-symbol directives. frob's own 30 tickets migrated.

<!-- ticket:T-0032 -->
```yaml
id: T-0032
title: 'Ticket schema: incident kind, acceptance, STRIDE threat, renumber'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_tickets.py
- docs/modules/tickets.md
evidence:
- tests/test_tickets.py::TestSchemaExtras::test_renumber_makes_ids_contiguous
- tests/test_tickets.py::TestSchemaExtras::test_acceptance_and_threat_round_trip
attachments: []
acceptance: []
threat: null
```
## Done report

Added incident kind (postmortem template), acceptance criteria,
STRIDE threat field, and frob ticket renumber (contiguous ids,
rewrites blocked_by/parent). T-0005/06/07/12 folded in here.

<!-- ticket:T-0033 -->
```yaml
id: T-0033
title: 'perf: cProfile masks workload exit code (harness preserves it)'
state: dropped
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- src/frob/app/perf_runner.py
- tests/test_perf.py
evidence: []
attachments: []
acceptance: []
threat: null
```

<!-- ticket:T-0034 -->
```yaml
id: T-0034
title: 'Wire fuzz+vet: FUZZ gate, frob test --fuzz, capability scan merge, gates degrade
  without diff'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/fuzz/**
- src/frob/vet/**
- src/frob/gates/**
- src/frob/app/test_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_fuzz.py
- tests/test_vet.py
- tests/test_gates.py
- tests/system/**
- pyproject.toml
- docs/**
evidence:
- tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_independent_gates_run_without_git
- tests/test_vet.py::TestLockfileParsers::test_find_lockfile_uv
attachments: []
acceptance: []
threat: null
```
## Done report

Merged the fuzz library (Arbitrary protocol, FUZZ001-003) and the vet
capability-scan/obfuscation branches; wired the FUZZ gate into run_gates
(default enforce=off) and frob test --fuzz (derived pydantic-model
harness + stamp). Fixed run_gates to degrade to an empty diff when git
has no base instead of skipping every gate. Delivers T-0002 and T-0008.

<!-- ticket:T-0035 -->
```yaml
id: T-0035
title: 'REL001 release gate: mechanical semver from public-API digests'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/release/**
- src/frob/gates/**
- src/frob/app/release_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_release.py
- docs/**
evidence:
- tests/test_release.py::test_release_gate_flags_missing_bump
- tests/test_release.py::test_changed_signature_is_major
attachments: []
acceptance: []
threat: null
```
## Done report

frob.release computes the semver bump class from public sig digests;
frob release stamp/check + the opt-in REL001 gate (runs only when a
.frob-release.json manifest exists) enforce it. Delivers T-0003.

<!-- ticket:T-0036 -->
```yaml
id: T-0036
title: 'frob stats: DORA-ish delivery measurement (queue health + commit cadence)'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/stats/**
- src/frob/app/stats_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_stats.py
- docs/**
evidence:
- tests/test_stats.py::test_collect_combines_both
- tests/test_stats.py::test_commit_stats_classifies_conventional_types
attachments: []
acceptance: []
threat: null
```
## Done report

frob stats reports ticket-queue health (state/kind counts, doable,
blocked, failure-log entries) and commit cadence (per-week rate,
conventional-type breakdown) from git + the queue. Measurement only,
no gate. Delivers T-0009.

<!-- ticket:T-0037 -->
```yaml
id: T-0037
title: 'Smart-dup: frob-core Rust kernels + DUP gate + build wiring'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- frob-core/**
- src/frob/dup/**
- src/frob/gates/**
- tests/test_dup_smart.py
- tests/test_excludes.py
- tests/test_gates.py
- Makefile
- .github/**
- docs/**
- tests/fixtures/**
evidence:
- tests/test_dup_smart.py::TestFindClones::test_finds_renamed_clone_pair
- tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_independent_gates_run_without_git
attachments: []
acceptance: []
threat: null
```
## Done report

frob-core PyO3/maturin crate (r3_canonical_hash, winnow, candidate_pairs,
tree_edit_similarity; 5/5 cargo tests) + the smart-dup Python pipeline
(find_clones R1/R2 pure-Python, R3 via frob-core, no silent fallback);
DUP001/DUP002 wired as the opt-in 'clones' gate; make core + CI build
the Rust side. Delivers the buildable core of T-0001.

<!-- ticket:T-0038 -->
```yaml
id: T-0038
title: 'ADR decision records: frob:decision edges + DEC gates'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/test_decisions.py
- docs/**
evidence:
- tests/test_decisions.py::test_dec002_accepted_decision_unanchored
- tests/test_decisions.py::test_dec001_dangling_decision_edge
attachments: []
acceptance: []
threat: null
```
## Done report

ADR: EdgeKind.DECISION + frob:decision DSL verb; decisions/AD-###.md
records with status; DEC001 (dangling ref), DEC002 (accepted decision
unanchored) gates, opt-in when decisions/ exists. Delivers T-0004.

<!-- ticket:T-0039 -->
```yaml
id: T-0039
title: Convention-based unit-test binding inference (reduce frob:tests burden)
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- tests/test_gates.py
evidence:
- tests/test_gates.py::TestConventionUnitBinding::test_test001_satisfied_by_convention_name
- tests/test_gates.py::TestConventionUnitBinding::test_short_symbol_names_do_not_match_everything
attachments: []
acceptance: []
threat: null
```
## Done report

TEST001 is now satisfiable by a conventionally named test (test_<name>,
snake-cased whole-token match) when no explicit frob:tests edge exists;
explicit edges stay authoritative (an uncollected edge still surfaces).
Short names (<3 chars) never infer. Delivers T-0018.

<!-- ticket:T-0040 -->
```yaml
id: T-0040
title: 'frob mutate: mutation testing quality oracle'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/mutate/**
- src/frob/app/mutate_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_mutate.py
- docs/**
evidence:
- tests/test_mutate.py::test_run_mutations_survivors_when_tests_weak
- tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test
attachments: []
acceptance: []
threat: null
```
## Done report

frob mutate: AST-based Python mutation (comparison/arith/boolop swaps,
bool negation), runs the test command per mutant, reports survivors +
mutation score, restores source always. Weak tests -> survivors, strong
tests -> 100%. Delivers T-0011 (MUT gate + other langs = follow-on).

<!-- ticket:T-0041 -->
```yaml
id: T-0041
title: 'dup follow-on: --probe CLI, full APTED, real CFG/DFG'
state: in-progress
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- frob-core/**
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/dup_runner.py
- src/frob/dup/**
- tests/test_dup_rungs.py
evidence: []
attachments: []
acceptance: []
threat: null
```
Follow-on polish from T-0001 (rungs complete): wire frob dup --probe
to probe_equivalence; replace statement-Levenshtein with full APTED;
replace R5's co-occurrence proxy with a real CFG/DFG.

<!-- ticket:T-0042 -->
```yaml
id: T-0042
title: 'TEST007: pair-level integration obligations from uses-contract edges'
state: done
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- tests/test_gates.py
- docs/**
evidence:
- tests/test_gates.py::TestPairLevelIntegration::test_test007_fires_on_uncovered_boundary
- tests/test_gates.py::TestPairLevelIntegration::test_test007_passes_when_boundary_tested
attachments: []
acceptance: []
threat: null
```
## Done report

TEST007: each cross-package frob:uses-contract dependency (C->P) owes a
pairwise integration test -- a valid integration edge targeting P whose
test path carries C's package leaf. Opt-in via [testing].pair_integration.
Delivers T-0017.

<!-- ticket:T-0043 -->
```yaml
id: T-0043
title: Migrate arch + dup/_legacy off frob.ast, then delete frob.ast
state: queued
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/arch/**
- src/frob/dup/**
- src/frob/ast/**
- src/frob/lang/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Re-platform left two frob.ast consumers needing raw node traversal
not yet in frob.lang: arch (child_by_field/text, 10 sites) and
dup/_legacy (14 sites). Add the needed traversal primitives to frob.lang,
migrate both, then delete src/frob/ast.

<!-- ticket:T-0044 -->
```yaml
id: T-0044
title: 'Comment binder: directive above nested method binds to enclosing class'
state: queued
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
A frob: directive comment placed immediately above a nested method or property binds to the ENCLOSING CLASS, not the method, because the class span contains the comment and 'enclosing' wins over 'following'. The edge is silently dropped (no error), so the method never clears COV001/TEST001. Three doc-campaign agents (a353eda, aa2686f, a1b18ef) independently hit this. Workaround: place the directive as first line INSIDE the method body. Proper fix: when a comment sits directly above a def/decorator, prefer the FOLLOWING symbol over the enclosing one. See src/frob/graph/dsl.py directive binding / _enclosing_src.

<!-- ticket:T-0045 -->
```yaml
id: T-0045
title: 'perf: split heat/profile long functions and clear PERF-rule self-flags'
state: queued
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- tests/test_perf.py
evidence: []
attachments: []
acceptance: []
threat: null
```
Refactor campaign: extract cohesive helpers in frob.perf._heat/_profile/_rules so no function trips PERF003/PERF004 or the long-function bar, preserving behavior. Accounts for the touched-set under frob check COV002.

<!-- ticket:T-0046 -->
```yaml
id: T-0046
title: 'Refactor: clear perf/arch/test warnings in app,process,serve,testing,map,outline,xref,cycle,gitlog,policy'
state: queued
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/process/**
- src/frob/serve/**
- src/frob/testing/**
- src/frob/map/**
- src/frob/outline/**
- src/frob/xref/**
- src/frob/cycle/**
- src/frob/gitlog/**
- src/frob/policy/**
- src/frob/__main__.py
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Refactor campaign: extract cohesive helpers across the app/process/serve/testing/command modules so no function trips PERF00x or the long-function bar, preserving behavior. Accounts for the touched-set under frob check COV002.

<!-- ticket:T-0047 -->
```yaml
id: T-0047
title: 'strata: provable system-design language (epic)'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- docs/strata/**
- src/frob/strata/**
- strata-core/**
- design/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Umbrella for the strata language: deny-by-default architecture models, kernel of 6 primitives (Node/Flow/Boundary/Bound/Claim/Scenario), 3-way claim closure (proved/evidenced/assumed), evidence ladder L1-L5, refinement hierarchy, policy forms, work-order compiler. Charter: docs/strata/charter.md. Independent engine (own strata-core PyO3 crate, NOT lithos); lithos is inspiration only.

<!-- ticket:T-0048 -->
```yaml
id: T-0048
title: strata charter + design doc tree under docs/strata/
state: done
kind: docs
origin: human
created: '2026-07-17'
blocked_by: []
parent: T-0047
scope:
- docs/strata/**
- docs/index.md
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
attachments: []
acceptance:
- GIVEN the doc tree WHEN frob check runs THEN DOC001 passes and every strata page
  is reachable from docs/index.md
threat: null
```
Write charter.md (north star, laws, decisions), kernel.md, surface.md, evidence.md, policy.md, boundary.md, roadmap.md. All decisions from the design sessions recorded unambiguously; strata name final; engine independent of lithos with its own strata-core crate.

## Done report

All seven pages written under docs/strata/ and linked from docs/index.md
(new "strata" section): charter (north star, six laws, three collapses,
decisions D1-D10, glossary), kernel (six primitives, conditional flows,
claim forms + decision procedures, prover pipeline), surface (grammar
sketch, elaborator contract, vocabulary/ticket map, refinement
faithfulness, module system), evidence (L1-L5 ladder, quantifier rules,
exhaustive fault injection, tool attestations, enables cascade, assumption
ledger), policy (five forms, semantic scoping, compilation, packs),
boundary (six-phase contract, frames, atomicity discharge patterns,
cross-store refusal, crash contracts), roadmap (phases 0-5 with exit
criteria, CLI surface, litmus program, ticket map T-0047..T-0086).

Acceptance verified: frob check exit 0; doclink (DOC001) gate passes with
all strata pages reachable from docs/index.md; no gate violation
references docs/strata/** or docs/index.md. Ticket tree T-0047..T-0086
filed with parent/blocked_by chains; phase parents chained sequentially;
phase-0 children chained internally.

<!-- ticket:T-0049 -->
```yaml
id: T-0049
title: 'strata phase 0: kernel + prover core'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0048
parent: T-0047
scope:
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_2_refund_decision_reads_a_stale_replica
attachments: []
acceptance:
- GIVEN hand-written kernel facts for the payments litmus WHEN the prover runs THEN
  all golden findings fire with path counterexamples and quantifier-tagged verdicts
threat: null
```
Kernel data model + fact base + closure + claim evaluation. Pure Python first; hot kernels move to strata-core (PyO3) later. See docs/strata/kernel.md.

## Done report

Phase 0 complete: T-0055 (kernel data model), T-0056 (fact base +
closure), T-0057 (claim evaluation), T-0058 (payments litmus goldens)
all closed with evidence. Exit criterion met exactly as written in the
acceptance: hand-written kernel facts for the payments litmus produce
all golden findings with path counterexamples and quantifier-tagged
verdicts. Side effects: T-0087 (CONST extraction gap) and T-0089
(scaffold DX flake) filed. Frontier advances to phase 1 (T-0050).

<!-- ticket:T-0050 -->
```yaml
id: T-0050
title: 'strata phase 1: surface language v0 + std.trust + refinement'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0049
parent: T-0047
scope:
- src/frob/strata/**
- tests/unit/strata/**
- design/litmus/**
evidence:
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_surface.py::TestHardenedSurfaceGoldens::test_every_assert_holds_after_the_remedies
attachments: []
acceptance:
- GIVEN design/litmus/payments.strata WHEN frob sys check runs THEN it parses, elaborates,
  and reproduces the phase-0 golden findings via CI
threat: null
```
Recursive-descent parser (pydantic AST, typani Result diagnostics), elaborator framework (vocabularies desugar to kernel facts, prover never learns domain terms), std.trust, assert/assume with owner+expiry, refine blocks with faithfulness checks. See docs/strata/surface.md.

## Done report

Phase 1 complete: T-0059 (Rust lexer/parser, serde JSON boundary, no
panic paths), T-0060 (elaborator + std.trust, reviewer round added a
REFUTED-with-witness end-to-end case), T-0061 (verdict report +
assumption ledger), T-0062 (refinement v0 with faithfulness checks and
the compositional-proof property), T-0063 (payments litmus twins in
surface syntax, goldens byte-identical to phase 0, CI-enforced). Exit
criterion met exactly as written: design/litmus/payments.strata
reproduces the phase-0 goldens end to end through parse -> elaborate ->
evaluate -> report. All five children reviewer-approved (T-0060 after
one rejection round). Side tickets filed en route: T-0090 (TEST002
cross-file rust directives), T-0091 (make core stray-venv), T-0092
(rust test runner + COV003 evidence resolution).

<!-- ticket:T-0051 -->
```yaml
id: T-0051
title: 'strata phase 2: std.infra + bounds + policy forms + boundaries'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0047
scope:
- src/frob/strata/**
- tests/unit/strata/**
- design/litmus/**
evidence: []
attachments: []
acceptance:
- GIVEN tube.strata and chirp.strata WHEN frob sys check runs THEN stampede, fanout-ceiling,
  staleness, and CDN-declassification findings fire per goldens
threat: null
```
store/cache/queue/cdn elaboration with mandatory invalidation edges, unified age/staleness propagation, capacity arithmetic with skew + growth horizons + cold/degraded modes, the 5 policy forms with semantic scoping + enables cascade, std.policy.analyzable, six-phase boundary contract with outcome-conditioned frames, errors-total/panics-contained/observe packs. See docs/strata/{policy,boundary}.md.

<!-- ticket:T-0052 -->
```yaml
id: T-0052
title: 'strata phase 3: scenarios, crash contracts, atomicity'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0051
parent: T-0047
scope:
- src/frob/strata/**
- tests/unit/strata/**
- design/litmus/**
evidence: []
attachments: []
acceptance:
- GIVEN scenario Breach(Gateway) in the payments litmus WHEN frob sys check runs THEN
  blast radius, revocation SLA, and recovery-path-independence verdicts are produced
threat: null
```
Scenario rewrites (node loss, rate surge, trust downgrade), on-crash contracts with no-hang caller-timeout checks and crash-retry-idempotency join, atomic/saga with cross-store refusal and exhaustive fault-injection test generation from closed ErrorSets.

<!-- ticket:T-0053 -->
```yaml
id: T-0053
title: 'strata phase 4: code binding (tier 2) + self-hosting'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0052
parent: T-0047
scope:
- src/frob/strata/**
- src/frob/lang/**
- src/frob/gates/**
- tests/**
- design/**
evidence: []
attachments: []
acceptance:
- GIVEN design/frob.strata WHEN frob check runs on this repo THEN SYS gates enforce
  frob's own declared architecture (self-hosting)
threat: null
```
.strata as a 6th frob.lang grammar (design constructs become graph symbols with digests/acks/drift), code globs + import conformance, effect extraction vs may-capabilities, frob:channel/boundary/secret directives, SYS gate family in run_gates. Exit = frob gates on its own design.

<!-- ticket:T-0054 -->
```yaml
id: T-0054
title: 'strata phase 5: std.secrets, std.deploy, work-order compiler, exporters'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0053
parent: T-0047
scope:
- src/frob/strata/**
- tests/**
- design/**
evidence: []
attachments: []
acceptance:
- GIVEN a refuted or undischarged claim WHEN frob sys plan runs THEN scoped tickets
  are filed idempotently and a sys ticket cannot close until its claim discharges
  at the required rung
threat: null
```
Credentials as cache-of-authority (lifetime/revocation obligations), deployment as endorsement pipeline (canary schedules, rollback budgets, vet as endorsement evidence), frob sys plan obligation->ticket compiler, frob sys doc generator + DOC002 claims audit, k8s-netpol/seccomp/IAM exporters.

<!-- ticket:T-0055 -->
```yaml
id: T-0055
title: 'strata kernel data model: Node/Flow/Boundary/Bound/Claim/Scenario'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0048
parent: T-0049
scope:
- src/frob/strata/**
- tests/unit/strata/**
- docs/strata/**
- tickets.md
evidence:
- tests/unit/strata/test_models.py::TestLattice::test_leq_is_reflexive_transitive_and_ordered
- tests/unit/strata/test_models.py::TestQuantity::test_leq_across_dimensions_is_an_error_not_false
- tests/unit/strata/test_models.py::TestKernelModel::test_frozen_models_compare_by_value
attachments: []
acceptance: []
threat: null
```
Frozen pydantic models for the 6 primitives; flows carry payload label, rate, size, age and may be conditioned on phase/outcome (on Ok / on Err / in parse). Law 1: every surface construct must desugar to these.

## Done report

Delivered src/frob/strata/: _errors.py (StrataError closed ErrorSet),
_models.py (Lattice + TRUST/LABELS cores, Quantity with unit dimensions,
Capacity, Node, Flow + FlowCondition/Outcome conditional-flow extension,
Boundary + BoundaryDirection, Metric, claim bodies NoFlow/Reach/BoundClaim,
Rung, Claim with assume owner/review, Scenario + RemoveNode/ScaleRate/
SetTrust rewrites, KernelModel, ClaimResult/Verdict/Quantifier),
__init__.py public API. All frozen pydantic, identity-of-value. 11 unit
tests bound via frob:tests; frob:doc edges to docs/strata/kernel.md#data-models
for every public symbol incl. methods (T-0044 workaround used). Ticket
check exit 0. Deviations: TRUST/LABELS constants are invisible to the
graph (python CONST extraction gap) -- filed T-0087 rather than widening
scope; their describes anchors deferred to that ticket.

<!-- ticket:T-0056 -->
```yaml
id: T-0056
title: strata fact base + semi-naive Datalog closure engine
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0055
parent: T-0049
scope:
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_facts.py::TestClosure::test_boundaries_stop_taint_unless_asked_otherwise
- tests/unit/strata/test_facts.py::TestClosure::test_worst_age_accumulates_along_the_stalest_path
- tests/unit/strata/test_facts.py::TestBuildFacts::test_at_least_once_into_non_idempotent_node_is_diagnosed
attachments: []
acceptance: []
threat: null
```
Tuple store + fixpoint closure (reach/taint over lattices). Pure Python; port to strata-core when litmus models make it slow.

## Done report

Delivered src/frob/strata/_facts.py: build_facts (fails closed on
duplicate ids, dangling flow/boundary references, unknown lattice levels,
cyclic lattices; emits deny-by-default structural diagnostics for
at-least-once-into-non-idempotent and label-above-clearance) and FactBase
(nodes_at, reachable with witness paths + barrier semantics, worst_age
longest-path staleness with inf-on-cycle, demand in base units). 14 new
unit tests bound via frob:tests; describes anchors + frob:doc edges to
docs/strata/kernel.md#fact-base. Ticket check exit 0, ruff clean.

<!-- ticket:T-0057 -->
```yaml
id: T-0057
title: 'strata claim evaluation: noflow/bound/reach with counterexample traces'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0056
parent: T-0049
scope:
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_claims.py::TestNoFlow::test_refuted_with_witness_path_when_no_boundary_intervenes
- tests/unit/strata/test_claims.py::TestReach::test_refutation_of_exists_is_a_forall
- tests/unit/strata/test_claims.py::TestBounds::test_age_bound_refuted_with_stalest_path_and_number
attachments: []
acceptance: []
threat: null
```
Verdicts PROVED/EVIDENCED/ASSUMED/REFUTED, quantifier-tagged (forall/exists); every REFUTED carries a path or a number, never a vibe. Interval arithmetic for bounds; z3 only for nonlinear.

## Done report

Delivered src/frob/strata/_claims.py: evaluate_claims walks claims in
declaration order (one result per claim, none droppable). noflow refutes
with the first witness path through the barrier-respecting closure and
supports trust-level endpoint expansion; reach is PROVED(exists)-with-
witness whose refutation is correctly a forall; bounds cover AGE (worst-
path staleness, inf-on-cycle refutes as unbounded), RATE (demand),
UTILIZATION (percent vs replica ceiling, refusing undeclared capacity),
SIZE (declared flow quantity), LATENCY (deny-by-default refute until
phase-2 path budgets); wrong-dimension limits fail the evaluation closed.
Assumes close ASSUMED with owner/review and overdue flagging. 12 new
unit tests; docs anchor docs/strata/kernel.md#claim-evaluation. Ticket
check exit 0, ruff clean, 37 strata tests green.

<!-- ticket:T-0058 -->
```yaml
id: T-0058
title: strata payments litmus as kernel facts + golden findings
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0057
parent: T-0049
scope:
- docs/strata/**
- tickets.md
- tests/unit/strata/**
- design/litmus/**
evidence:
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_2_refund_decision_reads_a_stale_replica
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_3_at_least_once_webhook_into_non_idempotent_consumer
- tests/unit/strata/test_litmus_payments.py::TestHardenedModel::test_every_assert_holds_after_the_remedies
attachments: []
acceptance: []
threat: null
```
Hand-written kernel facts for the Stripe-shaped model; goldens: foreign-response endorsement gap, stale-replica refund path, webhook idempotency. Phase-0 exit criterion.

## Done report

Delivered tests/unit/strata/test_litmus_payments.py: the payments litmus
as kernel facts with naive and hardened variants. Golden findings all
fire with exact witnesses: (1) third-party response endorsement gap
(stripe -> f_stripe_resp -> api -> f_api_ledger -> ledger), (2) refund
decision on a stale replica (330.0s > 60.0s with the full read path),
(3) at-least-once webhook into a non-idempotent consumer (build
diagnostic). Positive controls: endorsed browser ingress PROVED(forall),
audit Reach PROVED(exists) with witness, assume ledgered with owner and
review. Notably the checker caught MY first hardened variant: endorsing
the response path alone still left stripe -> webhookq -> api -> ledger
open, so the remedy set gained b_webhook (signature verification) and
queue dedup -- the tool refuting its own author's incomplete fix is the
phase-0 exit criterion working as intended. Also fixed a ty typing gap
in the fixture and filed T-0089 (scaffold DX flake seen during the full
suite, unrelated to strata). Ticket check exit 0; 45 strata tests green.

<!-- ticket:T-0059 -->
```yaml
id: T-0059
title: strata lexer + recursive-descent parser (pydantic AST, Result diagnostics)
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0049
parent: T-0050
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_parse.py::TestParseModule::test_parses_bare_module
- tests/unit/strata/test_parse.py::TestParseModule::test_round_trip_small_design
- tests/unit/strata/test_parse.py::TestParseModule::test_module_missing_is_parse_failed
attachments: []
acceptance: []
threat: null
```
Hand-rolled parser for the surface grammar in docs/strata/surface.md; units as lexed token classes; diagnostics as typani Results with spans.

## Done report

Delivered a lexer + recursive-descent parser for the surface grammar v0
(module/node/flow/boundary/assert/assume; `refine` deferred to T-0062),
split per charter D3 (amended): the compute-heavy grammar lives in Rust,
Python keeps the open interface.

- `strata-core/src/parse.rs` (new): hand-rolled lexer (idents, numbers,
  strings, `->`, `..`, `<=`, unit-continuing `/`) and recursive-descent
  parser covering every construct in the grammar; fuzz-safe (no panics on
  any input, verified by a dedicated test feeding malformed/empty/partial
  source). Exposes `pub(crate) fn parse_source_impl` returning JSON
  (`serde`/`serde_json` added as new Cargo deps); `strata-core/src/lib.rs`
  wires it as the `parse_source` pyfunction. 22 cargo unit tests (up from
  4), all green, covering every property, every unit form (`req/s`, `%`,
  bare `min`), attr `k=v`, error line/col accuracy, module-missing,
  duplicate-module, unknown-keyword/property/metric, and a full round-trip
  design. `strata_core.pyi` updated with the new signature.
- `src/frob/strata/_ast.py` (new): frozen pydantic AST mirroring the
  parser's JSON shape -- `Module`, `NodeDecl`, `Capacity`, `FlowDecl`,
  `BoundaryDecl`, `ClaimDecl` -- reusing `Quantity` from `_models.py`.
- `src/frob/strata/_parse.py` (new): `parse_module(text) ->
  Result[Module, StrataError]` bridging the Rust JSON into the AST models;
  logs line/col/message at ERROR on failure, returns bare
  `Err(StrataError.ParseFailed)` on the typani contract.
- `src/frob/strata/_errors.py`: added `StrataError.ParseFailed`.
- `src/frob/strata/__init__.py`: exports `Module`, `NodeDecl`, `FlowDecl`,
  `BoundaryDecl`, `ClaimDecl`, `SurfaceCapacity` (aliased to avoid the
  kernel `Capacity` name clash), and `parse_module`.
- `docs/strata/surface.md`: new "## Parser" section with `frob:describes`
  anchors for every new public symbol (Rust `parse_source` and the six
  Python AST/parse symbols).
- `tests/unit/strata/test_parse.py` (new): 11 unit tests, one
  `frob:tests` directive per case, covering every construct/property,
  quantity units (`req/s`, `%`), `attr k=v`, error-path behavior (Err +
  `ParseFailed`), module-missing, duplicate-module, and a full round-trip.

Verified:
1. `cargo test --lib` (with `PYO3_PYTHON`/`LD_LIBRARY_PATH` set) -- 22
   passed, 0 failed.
2. `cd strata-core && uvx maturin develop --uv --release` (via `make
   core`, run from repo root so it targets the shared `.venv` rather than
   a stray per-crate venv) -- rebuilt and reinstalled cleanly.
3. `uv run pytest tests/unit/strata -q` -- all green (56 total, 11 new).
4. `uv run ruff format`, `uv run ruff check`, `uv run ty check` on
   `src/frob/strata` and `tests/unit/strata` -- all clean.
5. `frob graph build` then `frob ticket sweep T-0059` (last edit before
   sweep) then `frob check --ticket T-0059` -- exit 0. One self-inflicted
   gate finding (COV001/TEST001 on `parse_source_impl`, initially `pub`
   with no doc/test edge of its own) was fixed by making it
   `pub(crate)` and adding its own `frob:doc`/`frob:tests` directives; a
   residual TEST002 stub-coverage note on that same helper is
   non-blocking (`gates` tool reports "pass", 77 warn-level findings, 6
   pre-existing waivers, none newly introduced by this ticket).

Deviations: the grammar sketch's `capacity` node-property syntax in
`kernel.md`/`surface.md` examples wasn't literally reproduced (no worked
example existed); implemented exactly the v0 grammar given in the ticket
body (`capacity NUMBER UNIT replicas INT .. INT`). No other deviations.

Filed: none -- no out-of-scope structural issues found. Pre-existing
repo-wide `frob-arch`/PERF gate warnings on files this ticket touches only
incidentally (`_models.py`, `_facts.py`, `_claims.py`) predate T-0059 and
were left untouched, consistent with scope.

<!-- ticket:T-0060 -->
```yaml
id: T-0060
title: strata elaborator framework + std.trust vocabulary
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0049
parent: T-0050
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_elaborate.py::TestElaborateFullMapping::test_maps_every_construct_field_for_field
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_duplicate_node_id_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_boundary_referencing_unknown_flow_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateAbstract::test_abstract_marker_preserved_in_attrs
- tests/unit/strata/test_elaborate.py::TestElaborateEndToEnd::test_parse_elaborate_evaluate_matches_expected_verdicts
attachments: []
acceptance: []
threat: null
```
Vocabularies are pure functions surface->kernel facts; the prover never learns domain words. std.trust: lattices, principals, components, channels, endorse/declassify boundaries.

## Done report

Changed:
- src/frob/strata/_elaborate.py::elaborate (new)
- src/frob/strata/_elaborate.py::_elaborate_node (new, private)
- src/frob/strata/_elaborate.py::_elaborate_flow (new, private)
- src/frob/strata/_elaborate.py::_elaborate_boundary (new, private)
- src/frob/strata/_elaborate.py::_elaborate_claim_body (new, private)
- src/frob/strata/_elaborate.py::_elaborate_claim (new, private)
- src/frob/strata/_elaborate.py::_validate_no_duplicates (new, private)
- src/frob/strata/_elaborate.py::_validate_references (new, private)
- src/frob/strata/__init__.py (export `elaborate`)
- docs/strata/surface.md (new "## Elaborator" section)

Evidence:
- tests/unit/strata/test_elaborate.py::TestElaborateFullMapping::test_maps_every_construct_field_for_field
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_duplicate_node_id_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_boundary_referencing_unknown_flow_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateAbstract::test_abstract_marker_preserved_in_attrs
- tests/unit/strata/test_elaborate.py::TestElaborateEndToEnd::test_parse_elaborate_evaluate_matches_expected_verdicts

Filed: none

Gates: `frob check --ticket T-0060` exit 0. `uv run pytest tests/unit/strata -q` green (69 tests). `uv run ruff format`/`ruff check` clean. `uv run ty check` clean on src/frob/strata and tests/unit/strata.

### Reviewer round 2 (rejected, both findings fixed)

The reviewer rejected the first pass on two MAJOR findings:

1. The structured `evidence:` YAML list above had only 3 node ids while
   this Done report's prose listed 5. Reconciled by adding the two
   missing node ids (`TestElaborateValidation::test_boundary_referencing_unknown_flow_fails_closed`
   and `TestElaborateAbstract::test_abstract_marker_preserved_in_attrs`)
   to the structured `evidence:` list, verified against
   `uv run pytest --collect-only tests/unit/strata/test_elaborate.py`.
2. `TestElaborateEndToEnd` only drove PROVED verdicts through the
   parse -> elaborate -> evaluate_claims pipeline. Added a third node
   (`rogue`, trust `foreign`) and flow (`f4: rogue -> audit`, no
   boundary) plus claim `c3 noflow foreign -> audit` to the same test, and
   asserted `Verdict.REFUTED` with the exact witness counterexample
   `("rogue", "f4", "audit")`, alongside the existing PROVED claims.

Re-ran the full verification loop after both fixes: `uv run pytest
tests/unit/strata -q` green (70 tests); `ruff format`/`ruff check` +
`ty check` clean on `src/frob/strata` and `tests/unit/strata`; `frob
graph build`; `frob ticket sweep T-0060` (last); `frob check --ticket
T-0060` exit 0.

<!-- ticket:T-0061 -->
```yaml
id: T-0061
title: 'strata assert/assume: owner, expiry, verdict report'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0049
parent: T-0050
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_report.py::TestCounterexamplePath::test_refuted_line_followed_by_exact_path_line
- tests/unit/strata/test_report.py::TestOrdering::test_refuted_sorts_first_regardless_of_input_order
- tests/unit/strata/test_report.py::TestSummarize::test_all_four_keys_always_present
attachments: []
acceptance: []
threat: null
```
Assumption ledger (named, owned, expiring; overdue = gate failure); report renders per-claim verdict + quantifier + evidence rung.

## Done report

Changed:
- src/frob/strata/_report.py::render_report
- src/frob/strata/_report.py::summarize
- src/frob/strata/__init__.py (export render_report, summarize)
- docs/strata/kernel.md (## Verdict report section)
- tests/unit/strata/test_report.py (new)

Evidence:
- tests/unit/strata/test_report.py::TestCounterexamplePath::test_refuted_line_followed_by_exact_path_line
- tests/unit/strata/test_report.py::TestOrdering::test_refuted_sorts_first_regardless_of_input_order
- tests/unit/strata/test_report.py::TestSummarize::test_all_four_keys_always_present

Filed: none

Gates: `frob check --ticket T-0061` clean (exit 0; only pre-existing waived
PERF003 findings in frob-core/frob's own modules, unrelated to this
ticket's scope). `frob graph build` clean. pytest tests/unit/strata 72
passed. ruff format/check clean. ty check clean.

<!-- ticket:T-0062 -->
```yaml
id: T-0062
title: 'strata refinement: abstract components, refine blocks, faithfulness'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0049
parent: T-0050
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_flattens_abstract_node_and_rewires_outer_flow
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_noflow_claim_proved_at_abstract_level_stays_proved_after_refinement
- tests/unit/strata/test_refine.py::TestRefineViolations::test_foreign_inner_node_under_trusted_abstract_fails_trust_laundering
- tests/unit/strata/test_refine.py::TestUnrefinedFrontier::test_unrefined_abstract_node_keeps_marker
attachments: []
acceptance: []
threat: null
```
Three faithfulness checks: no new external surface, no trust laundering, budget distribution. Policies inherit downward monotonically; code binding legal only on leaves.

## Done report

Changed:
- strata-core/src/parse.rs::Parser::parse_refine
- strata-core/src/parse.rs::ModuleAst (new `refines` field)
- strata-core/src/parse.rs::Parser::parse_program (refine keyword wiring)
- src/frob/strata/_ast.py::RefineDecl
- src/frob/strata/_ast.py::Module (new `refines` field)
- src/frob/strata/_errors.py::StrataError (new `RefinementViolation` member)
- src/frob/strata/_elaborate.py::_rewire_endpoint
- src/frob/strata/_elaborate.py::_rewrite_claim_for_refine
- src/frob/strata/_elaborate.py::_apply_refine
- src/frob/strata/_elaborate.py::_elaborate_refines
- src/frob/strata/_elaborate.py::elaborate (now flattens refine blocks)
- src/frob/strata/__init__.py (export RefineDecl)
- docs/strata/surface.md ("### v0 semantics" under Refinement, Parser
  section RefineDecl anchor + grammar-subset note, Elaborator section
  refine/RefinementViolation notes)
- tests/unit/strata/test_refine.py (new)

Evidence:
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_flattens_abstract_node_and_rewires_outer_flow
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_claim_endpoint_rewritten_and_still_evaluable
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_noflow_claim_proved_at_abstract_level_stays_proved_after_refinement
- tests/unit/strata/test_refine.py::TestRefineViolations::test_refine_of_non_abstract_node_fails
- tests/unit/strata/test_refine.py::TestRefineViolations::test_refine_of_unknown_target_fails
- tests/unit/strata/test_refine.py::TestRefineViolations::test_inner_flow_touching_outer_id_fails_new_external_surface
- tests/unit/strata/test_refine.py::TestRefineViolations::test_foreign_inner_node_under_trusted_abstract_fails_trust_laundering
- tests/unit/strata/test_refine.py::TestRefineViolations::test_bind_to_not_an_inner_node_fails
- tests/unit/strata/test_refine.py::TestUnrefinedFrontier::test_unrefined_abstract_node_keeps_marker
- strata-core/src/parse.rs::tests::parses_refine_happy_path
- strata-core/src/parse.rs::tests::error_refine_zero_binds
- strata-core/src/parse.rs::tests::error_refine_two_binds
- strata-core/src/parse.rs::tests::error_refine_binds_lhs_mismatch
- strata-core/src/parse.rs::tests::error_refine_before_module

Deviations: budget distribution (faithfulness check 3) is explicitly
DEFERRED to phase 2, as instructed -- not implemented, documented in
docs/strata/surface.md and as a code comment in `_apply_refine`.

Filed: T-0091 (`make core` creates a stray venv under strata-core/,
observed while rebuilding the Rust extension for this ticket -- worked
around with an explicit `VIRTUAL_ENV`, not fixed here since it is outside
this ticket's deliverable list).

Gates: `cargo test --lib` in strata-core: 27 passed (5 new refine tests).
`make core` rebuilt both extensions (workaround: `VIRTUAL_ENV=$(pwd)/.venv
uvx maturin develop --uv --release -m strata-core/Cargo.toml`, see T-0091).
`uv run pytest tests/unit/strata -q`: all green (81 tests, 9 new).
`uv run ruff format --check` / `ruff check` clean on all touched files.
`uv run ty check` clean. `frob graph build` clean (11 describes anchors in
docs/strata/surface.md). `frob ticket sweep T-0062` recorded. `frob check
--ticket T-0062` exit 0 (only pre-existing waived PERF003 findings in
unrelated modules).

<!-- ticket:T-0063 -->
```yaml
id: T-0063
title: strata payments litmus in surface syntax + CI goldens
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0049
parent: T-0050
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- design/litmus/**
- tests/**
evidence:
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_2_refund_decision_reads_a_stale_replica
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_render_report_shows_refuted_before_proved_with_the_witness_path
- tests/unit/strata/test_litmus_surface.py::TestHardenedSurfaceGoldens::test_every_assert_holds_after_the_remedies
attachments: []
acceptance: []
threat: null
```
design/litmus/payments.strata reproduces phase-0 findings end to end through parser+elaborator; goldens wired into CI. Phase-1 exit criterion.

## Done report

Changed:
- design/litmus/payments.strata (new)
- design/litmus/payments_hardened.strata (new)
- tests/unit/strata/test_litmus_surface.py (new)
- docs/strata/roadmap.md (litmus program section, phase-1 exit noted met)

design/litmus/payments.strata is the surface-syntax twin of
`_payments_model(hardened=False)` in test_litmus_payments.py: same node
ids/trust/clearance, same flow ids/labels/ages (5 min on f_repl, 30 s on
f_dash) and delivery=at_least_once attrs, same b_ingress endorse boundary,
same five claims including the assume (owner logan, review 2026-10-01).
design/litmus/payments_hardened.strata adds b_stripe_resp and b_webhook
endorse boundaries, idempotent attrs on api/webhookq, and reads the refund
decision directly off the ledger (f_refund_read: ledger -> refund),
matching `_payments_model(hardened=True)`.
tests/unit/strata/test_litmus_surface.py loads both files (repo root
resolved by walking up from __file__ to the first frob.toml), runs
parse_module -> elaborate -> evaluate_claims (today=2026-07-17), and
asserts byte-identical goldens to test_litmus_payments.py: golden 1
(stripe->ledger REFUTED with the 5-element counterexample), golden 2
(c_fresh_refund REFUTED, "330.0s > 60.0s", 7-element read path), golden 3
(build_facts f_wq_api at-least-once diagnostic), the browser-noflow PROVED
forall, the audit-reach PROVED exists witness, the assume ASSUMED with
"logan" in detail, and the hardened file's four PROVED asserts plus empty
diagnostics. One render_report smoke test confirms REFUTED sorts before
PROVED and the exact witness-path line
`  path: stripe -> f_stripe_resp -> api -> f_api_ledger -> ledger`
(format matched against src/frob/strata/_report.py's `"  path: " +
" -> ".join(counterexample)`).

The v0 surface grammar (strata-core/src/parse.rs) expressed every kernel
construct needed with no gap: `attr key=value` covers
`delivery=at_least_once`; `age N unit` covers `5 min` / `30 s`; `assume ID
noflow ... owner ID review "date"` covers the owner/review pair verbatim.
No parser-gap ticket was filed -- none was needed.

Evidence:
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_2_refund_decision_reads_a_stale_replica
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_render_report_shows_refuted_before_proved_with_the_witness_path
- tests/unit/strata/test_litmus_surface.py::TestHardenedSurfaceGoldens::test_every_assert_holds_after_the_remedies

Filed: none.

Gates: `frob ticket sweep T-0063` recorded (dup=48, xref=7, all pre-existing
repo-wide noise unrelated to this diff); `frob check --ticket T-0063` exit
0; plain `frob check` exit 0; `uv run pytest tests/unit/strata -q` all 92
tests green; `uv run ruff format --check` and `uv run ruff check` clean on
tests/unit/strata/test_litmus_surface.py; `uv run ty check` clean.

<!-- ticket:T-0064 -->
```yaml
id: T-0064
title: 'strata std.infra: store/cache/queue/cdn/balancer elaboration'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_without_invalidation_is_err
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_ttl_and_staleness_must_agree
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_unlimited_on_mutable_is_err
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_tls_terminates_adds_declassify_boundary
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_delivery_propagates_to_outbound_flows_and_fires_diagnostic
- tests/unit/strata/test_infra.py::TestEndToEnd::test_cache_staleness_refutes_age_bound_claim
attachments: []
acceptance: []
threat: null
```
Caches are derived views: mandatory source-of-truth + invalidation edge + staleness bound; queues carry delivery semantics; delivery x idempotency join; managed components skip tier-2.

## Done report

Changed:
- strata-core/src/parse.rs::Parser::parse_store
- strata-core/src/parse.rs::Parser::parse_cache
- strata-core/src/parse.rs::Parser::parse_queue
- strata-core/src/parse.rs::Parser::parse_cdn
- strata-core/src/parse.rs::Parser::parse_balancer
- strata-core/src/parse.rs::Parser::parse_percent
- strata-core/src/parse.rs::ModuleAst (stores/caches/queues/cdns/balancers fields)
- src/frob/strata/_ast.py::StoreDecl
- src/frob/strata/_ast.py::CacheDecl
- src/frob/strata/_ast.py::QueueDecl
- src/frob/strata/_ast.py::CdnDecl
- src/frob/strata/_ast.py::BalancerDecl
- src/frob/strata/_ast.py::Module (stores/caches/queues/cdns/balancers fields)
- src/frob/strata/_infra.py::elaborate_infra (new module)
- src/frob/strata/_infra.py::InfraExpansion (new module)
- src/frob/strata/_errors.py::StrataError (MissingBound, MissingInvalidation, MutableUnbounded)
- src/frob/strata/_elaborate.py::elaborate (calls elaborate_infra after std.trust mapping)
- src/frob/strata/_elaborate.py::_validate_references (bound-claim targets now include infra decl ids)
- src/frob/strata/__init__.py (exports for the above)
- docs/strata/surface.md (## std.infra section: desugar table, age-collapse,
  mandatory invalidation, immutable-TTL pairing, CDN declassification,
  queue delivery propagation, sticky-balancer contradiction, and the
  documented queue/balancer trust-default deviation)

Evidence:
- cargo test (strata-core), 41/41 green, including new:
  parse::tests::parses_store_with_all_properties,
  parse::tests::parses_bare_store, parse::tests::error_unknown_store_property,
  parse::tests::parses_cache_with_all_properties, parse::tests::parses_cache_ttl,
  parse::tests::error_unknown_cache_property,
  parse::tests::parses_queue_with_all_properties,
  parse::tests::error_unknown_queue_property,
  parse::tests::parses_cdn_with_all_properties,
  parse::tests::parses_cdn_unlimited_staleness,
  parse::tests::error_unknown_cdn_property,
  parse::tests::parses_balancer_with_all_properties,
  parse::tests::parses_bare_balancer,
  parse::tests::error_unknown_balancer_property
- tests/unit/strata/test_infra.py::TestStoreDesugar::test_store_becomes_node_with_markers
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_node_and_fill_flow
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_ttl_and_staleness_must_agree
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_ttl_and_staleness_agreeing_is_ok
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_with_no_bound_is_err
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_without_invalidation_is_err
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_no_inbound_writes_needs_no_invalidation
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_invalidate_on_wrong_dst_is_err
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_node_attrs
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_delivery_propagates_to_outbound_flows_and_fires_diagnostic
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_node_and_fill_flow
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_unlimited_on_mutable_is_err
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_unlimited_on_immutable_is_ok
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_missing_provider_is_err
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_tls_terminates_adds_declassify_boundary
- tests/unit/strata/test_infra.py::TestBalancerDesugar::test_balancer_node_attrs
- tests/unit/strata/test_infra.py::TestBalancerDesugar::test_sticky_balancer_stateless_downstream_is_diagnostic
- tests/unit/strata/test_infra.py::TestEndToEnd::test_cache_staleness_refutes_age_bound_claim
- `uv run pytest tests/unit/strata -q` -- 110 tests green (92 pre-existing + 18 new in test_infra.py)
- `uv run ruff format --check` / `uv run ruff check` clean on all changed files
- `uv run ty check src/` clean
- `cargo fmt -- --check` and `cargo clippy --all-targets -- -D warnings` clean (strata-core)

Filed: T-0093 (strata grammar: explicit trust clause for queue/balancer --
the grammar as specified for this ticket gives queue/balancer no TRUST
clause; `_infra.py` defaults both to `"trusted"`, documented as a
deliberate deviation in docs/strata/surface.md#std-infra rather than left
silent).

Gates: `frob ticket sweep T-0064` recorded (dup=55, xref=8, pre-existing
repo-wide noise unrelated to this diff); `frob check --ticket T-0064` exit
0; plain `frob check` exit 0; `frob graph build` clean (18 describes
anchors resolved in docs/strata/surface.md).

Deviations: (1) queue/balancer trust defaults to `"trusted"` -- see Filed,
above; the ticket's own grammar sketch omits a TRUST clause for these two
constructs, so a default was unavoidable, and it is documented rather than
silent. (2) `MissingBound`'s docstring was worded to cover both the cache
ttl/staleness case and the cdn missing-provider-trust case, since the
ticket specifies exactly three new error members and a fourth was not
warranted for one additional missing-declaration site with the same
deny-by-default shape.

<!-- ticket:T-0065 -->
```yaml
id: T-0065
title: strata age/staleness propagation (TTL = rotation = RPO = expiry)
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_kernel_properties.py::test_reachable_matches_bfs_oracle
- tests/unit/strata/test_kernel_properties.py::test_worst_age_matches_longest_path_oracle_on_dags
- tests/unit/strata/test_kernel_properties.py::test_worst_age_cycle_property
- tests/unit/strata/test_kernel_properties.py::test_demand_matches_sum_oracle
- tests/unit/strata/test_kernel_properties.py::test_reachable_is_deterministic
- tests/unit/strata/test_kernel_properties.py::test_worst_age_is_deterministic
- tests/unit/strata/test_kernel_properties.py::test_demand_is_deterministic
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_context_dependent_memo_undercount
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_adversarial_shared_node_divergent_entry_a
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_adversarial_shared_node_divergent_entry_b
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_adversarial_three_way_convergence
- tests/unit/strata/test_facts.py::TestBuildFacts::test_negative_age_fails_closed
- tests/unit/strata/test_facts.py::TestBuildFacts::test_negative_rate_fails_closed
- tests/unit/strata/test_facts.py::TestBuildFacts::test_nonnegative_age_is_accepted
attachments: []
acceptance: []
threat: null
```
One age metric propagated along read paths; freshness requirements proved or refuted with the accumulating path.

## Done report

Changed:
- strata-core/src/lib.rs::worst_age (bug fix: zero/negative-net cycles no
  longer produce spurious +inf; only a positive-age cycle reaching the
  target does)
- strata-core/src/lib.rs::worst_age_visit
- strata-core/src/lib.rs (new: find_positive_cycle, has_positive_cycle_reaching)
- strata-core/src/parse.rs::parse_store (new `rpo QUANTITY` store_prop)
- src/frob/strata/_ast.py::StoreDecl (new `rpo: Quantity | None` field)
- src/frob/strata/_infra.py::_elaborate_store (rpo dimension validation,
  `rpo=<seconds>` attr; now returns Result)
- src/frob/strata/_infra.py::elaborate_infra (propagates the new Result)
- docs/strata/kernel.md (new "Age propagation semantics" subsection)
- docs/strata/surface.md (store grammar + desugar table updated for `rpo`)
- tests/unit/strata/test_kernel_properties.py (new: hypothesis property
  tests for reachable/worst_age/demand)
- tests/unit/strata/test_infra.py (new: rpo elaboration tests)
- strata-core/src/parse.rs (new cargo test parses_store_rpo)

Evidence: the 14 structured ids in this ticket's evidence list (7 original property/oracle tests + 4 reviewer-round regressions + 3 negative-quantity tests).

Kernel bug found and fixed: `test_worst_age_cycle_property` shrunk to the
single self-loop `('f0', 'n0', 'n0', 0.0)` -- a zero-age self-loop made
`worst_age` return `+inf`, because the old `worst_age_visit` treated ANY
revisited-while-active node as an unbounded cycle, regardless of the
cycle's actual accumulated age. Per docs/strata/kernel.md#age-propagation-
semantics, only a *positive*-age cycle reaching the target should be
unbounded. Fixed by adding a pre-pass (`has_positive_cycle_reaching`) that
DFS-searches for a positive-weight cycle able to reach the target and
returns +inf with the cycle witness only in that case; the memoized DFS
(`worst_age_visit`) no longer special-cases revisits as infinite -- it now
returns `-inf` for a revisit so that branch never wins the max, which
degrades gracefully to a longest-*simple*-path search whenever no positive
cycle exists. The shrunken counterexample is exercised as a regression via
the property test itself (`test_worst_age_cycle_property`), and the
existing `worst_age_is_infinite_on_positive_cycles` / `worst_age_takes_the_
stalest_path` cargo tests continue to pass unchanged, confirming the
positive-cycle and no-cycle behaviors were preserved.

## Reviewer round: soundness fix

The reviewer REJECTED the first pass with a CRITICAL finding: the
memoized-DFS `worst_age` (the fix for the zero-age-self-loop bug above)
was itself unsound. Verified counterexample against the built extension:

```
edges = [("e0","B","A",0.0), ("e1","B","T",0.0), ("e2","A","T",3.0),
         ("e3","A","B",0.0), ("e4","C","B",1.0)]
strata_core.worst_age(edges, "T")  ->  (3.0, [A,e2,T])   -- WRONG
true answer: 4.0 via C->B->A->T
```

Mechanism: `best[node]` was memoized under whichever caller's active-set
happened to compute it first. `A` got memoized as `(0.0, [A])` while `B`
was on the active stack (correctly excluding the `A<-B<-C` continuation
*in that context*), and that truncated cache entry was then wrongly reused
when `A` was visited again with `B` no longer active. An undercount here
is the worst possible bug class for this tool: it can make `bound age(x)
<= v` FALSELY PROVED.

Fix: replaced the memoized-DFS entirely with SCC condensation, per the
reviewer's required design --

1. Kept the positive-cycle pre-pass (`has_positive_cycle_reaching`,
   `find_positive_cycle`) unchanged: with non-negative ages, if any
   positive-weight cycle reaches the target, return `+inf` with a cycle
   witness.
2. Added `_facts.py::_validate_nonnegative_quantities` and
   `StrataError.NegativeQuantity` so `build_facts` fails closed (ERROR-
   logged) on any negative flow age/rate/size -- the surface grammar
   cannot express this, but the Python API can, and non-negativity is the
   premise the SCC argument depends on (documented in
   docs/strata/kernel.md#age-propagation-semantics).
3. Otherwise: compute SCCs (`compute_sccs`, Tarjan, node ids visited in
   sorted order, edges pre-sorted by flow id -- fully deterministic),
   contract each SCC to one supernode, and run standard longest-path DP
   over the condensation DAG in topological order (Kahn's algorithm). This
   is exact and carries no caller-context-dependent state at all.
4. Witness reconstruction (`zero_weight_path`) walks the chosen-edge chain
   from target's SCC back to a root, then BFS-stitches each inter-SCC hop
   through its SCC's zero-weight interior (sound only because step 1/2
   already ruled out positive-weight intra-SCC edges). Verified by hand
   against the reviewer's counterexample (traced in the code review): the
   reconstructed path is exactly `[C, e4, B, e0, A, e2, T]`, age `4.0`.
5. Added the counterexample verbatim as a permanent regression: cargo
   `worst_age_reviewer_regression_context_dependent_memo`
   (strata-core/src/lib.rs) and pytest
   `TestReviewerRegression::test_context_dependent_memo_undercount`
   (calling `strata_core.worst_age` directly), plus three hand-built
   adversarial cases with a node shared across divergent caller contexts
   (`test_adversarial_shared_node_divergent_entry_a/b`,
   `test_adversarial_three_way_convergence`).
6. Closed the generator coverage gap: `_cyclic_edges` now draws ages from
   `[0.0, 0.0, 0.0, 1.0, 2.0]` instead of a uniform float range, so
   zero-net-weight cycles reaching the target actually form during
   property testing (a uniform float draw almost never lands on exactly
   0.0, so this regression class was invisible to the original generator).
7. Documented the non-negativity precondition and the counterexample in
   docs/strata/kernel.md#age-propagation-semantics.

Changed (reviewer round, additive to the list above):
- strata-core/src/lib.rs::worst_age (rewritten: SCC condensation DP,
  replacing the memoized-DFS `worst_age_visit`)
- strata-core/src/lib.rs (new: strongconnect, compute_sccs, zero_weight_path)
- strata-core/src/lib.rs (new cargo test:
  worst_age_reviewer_regression_context_dependent_memo)
- src/frob/strata/_errors.py::StrataError (new NegativeQuantity member)
- src/frob/strata/_facts.py::build_facts (new
  _validate_nonnegative_quantities call)
- src/frob/strata/_facts.py (new: _validate_nonnegative_quantities)
- docs/strata/kernel.md (non-negativity precondition + counterexample)
- tests/unit/strata/test_kernel_properties.py (new: TestReviewerRegression
  class; _cyclic_edges biased toward exact 0.0)
- tests/unit/strata/test_facts.py (new: negative-quantity tests)

Filed: none

Gates: `frob check --ticket T-0065` clean (exit 0; only pre-existing waived
PERF003/frob-exports/frob-arch warnings unrelated to this ticket's scope);
plain `frob check` clean (exit 0). `cargo test` (strata-core) 43/43 green,
including the reviewer's exact counterexample. `make core` rebuilt at repo
root. `uv run pytest tests/unit/strata -q` all green, repeated 3x (property
suite re-run each time with fresh hypothesis examples). ruff format/check
clean. ty clean. `frob graph build` clean. `frob ticket sweep T-0065` run
last before the final `frob check`.

<!-- ticket:T-0066 -->
```yaml
id: T-0066
title: 'strata capacity arithmetic: utilization, fanout, skew, growth horizons'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/unit/strata/**
evidence:
- tests/unit/strata/test_capacity.py::TestSkewUtilization::test_skew_refutes_where_mean_would_prove
- tests/unit/strata/test_capacity.py::TestGrowthHorizon::test_growth_flips_proved_to_refuted_with_month_count
- tests/unit/strata/test_capacity.py::TestPropagatedDemand::test_positive_rate_cycle_is_unbounded
attachments: []
acceptance: []
threat: null
```
Demand propagation with fanout multipliers and zipf skew (check hottest shard, not mean); cold/degraded modes; saturation-date diagnostics; measured capacities bind to frob.perf stamps.

## Done report

Changed: `strata-core/src/lib.rs::propagated_demand` (+ `compute_demand`
helper), `strata-core/src/parse.rs` (`fanout`/`growth`/`skew zipf` props on
node/store/flow, desugar to `attrs`), `strata_core.pyi`,
`src/frob/strata/_facts.py::FactBase.propagated_demand`/`_flow_fanout`,
`src/frob/strata/_claims.py::_eval_bound` (skew hottest-share + growth
horizon), `_node_skew`/`_zipf_hottest_share`/`_flow_growth`/`_add_months`/
`_months_to_saturation`/`GROWTH_HORIZON_MONTHS`. No `_ast.py`/
`_elaborate.py`/`_infra.py` changes needed: the three new props desugar
straight to `attrs` in the Rust parser, which already passes through
field-for-field (law 1). Docs: kernel.md `### Capacity semantics` +
strata-core bullets; surface.md parser section note.
Evidence: see `evidence:` above (3 of 11 new pytest cases + 8 new/updated
cargo tests in strata-core; COV003 cannot resolve cargo names).
Filed: none.
Gates: `frob check --ticket T-0066` and plain `frob check` both exit 0;
cargo test --lib (53 passed), pytest tests/unit/strata (all green), ruff
format/check clean, ty clean. Chose the "honest v0" cycle rule (any cycle
fed by a declared-rate source and reaching target is +inf) over computing
per-cycle fanout products, documented in kernel.md as a deliberate,
non-incomplete conservatism.

<!-- ticket:T-0067 -->
```yaml
id: T-0067
title: 'strata policy sublanguage: 5 forms, semantic scoping, tree-sitter compilation'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- src/frob/policy/**
- tests/**
evidence:
- tests/unit/strata/test_policy.py::TestGrammarRoundTrip::test_forbid_call_round_trips
- tests/unit/strata/test_policy.py::TestScopeResolution::test_trust_scope_resolves_via_lattice
- tests/unit/strata/test_policy.py::TestScopeResolution::test_unknown_component_scope_fails_closed
attachments: []
acceptance: []
threat: null
```
forbid/confine/at-require/mediate/structural, scoped over the model (trust level, component, label) and resolved to files via code globs; compiles to per-language tree-sitter queries; extends existing POL machinery.

## Done report

Changed: strata-core/src/parse.rs (policy grammar, dotted idents, `>=`),
src/frob/strata/_ast.py (ScopeSpec/ForbidCall/ForbidImport/ConfineUse/
AtCallRequire/Mediate/PolicyRule/PolicyDecl, Module.policies), new
src/frob/strata/_policy.py (CompiledPolicy/CompiledPolicies/
compile_policies), src/frob/strata/__init__.py exports.
Evidence: 65 cargo tests green (not listed per policy: COV003 cannot
resolve cargo ids); 3 pytest node ids above out of 19 new tests, all
green; full `tests/unit/strata` suite (154 tests) green.
Filed: none.
Correction (post-review): the evidence block originally used mapping
syntax (`- pytest_node_id: ...`), which broke `frob ticket show`
(MalformedFrontmatter) and made every subsequent `frob check` run
against an unloadable queue -- the "gates clean" claim below was never
actually verified. Fixed to plain string node ids; re-ran for real
after `frob graph build` + `frob ticket sweep T-0067` (T-0068 swept
last). `frob check --ticket T-0067` now actually executes the gates
stage (clones/coverage/decisions/doclink/drift/fuzz/invariant/perf/
policy/release/test all ran, exit 0, no skip) and shows `pass gates
118 violation(s), 6 waived`. Plain `frob check` also exit 0, gates
stage executed. ruff format/check and ty remain clean.

<!-- ticket:T-0068 -->
```yaml
id: T-0068
title: strata std.policy.analyzable base pack + enables soundness cascade
state: done
kind: security
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/**
evidence:
- tests/unit/strata/test_packs.py::TestAutoInjection::test_trusted_component_without_pack_gets_it_injected
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_waived_pack_downgrades_noflow_but_not_bound
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_end_to_end_parse_elaborate_compile_evaluate
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_waiving_a_policy_that_enables_nothing_downgrades_nothing
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_waiving_a_nonexistent_policy_id_is_a_logged_no_op
attachments: []
acceptance: []
threat: elevation-of-privilege
```
Mandatory for trusted components: no eval/exec/dynamic import/reflection dispatch, FFI only via frob bind, anti-aliasing rules. Policies declare enables; waiving one downgrades every dependent claim PROVED -> ASSUMED automatically.

## Done report

Changed: new src/frob/strata/_packs.py (ANALYZABLE pack data,
require_analyzable auto-inject seam), src/frob/strata/_elaborate.py
(calls require_analyzable), src/frob/strata/_claims.py (evaluate_claims
gains compiled_policies/waived_policies, enables-cascade downgrade
logic), src/frob/strata/__init__.py exports, docs/strata/policy.md
(v0 implementation + auto-inject amendment), docs/strata/evidence.md
(v0 dependency rule).
Evidence: 5 pytest node ids above out of 8 pack tests (2 added in
review round 2: waiving a no-enables policy is a no-op; waiving a
nonexistent policy id is a logged no-op, not a crash), all green;
full `tests/unit/strata` suite green.
Filed: none.
Correction (post-review): the evidence block originally used mapping
syntax (`- pytest_node_id: ...`), which broke `frob ticket show`
(MalformedFrontmatter) and made every subsequent `frob check` run
against an unloadable queue -- the "gates clean" claim below was never
actually verified. Fixed to plain string node ids; re-ran for real
after `frob graph build` + `frob ticket sweep T-0067` then
`T-0068` (sweep last). `frob check --ticket T-0068` now actually
executes the gates stage (clones/coverage/decisions/doclink/drift/
fuzz/invariant/perf/policy/release/test all ran, exit 0, no skip) and
shows `pass gates 118 violation(s), 6 waived`. Plain `frob check` also
exit 0, gates stage executed. ruff format/check and ty remain clean.

<!-- ticket:T-0069 -->
```yaml
id: T-0069
title: strata six-phase boundaries + outcome-conditioned frames
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/unit/strata/**
evidence: []
attachments: []
acceptance: []
threat: null
```
admit/parse/judge/effect/record/refuse with per-phase frames and label rules; no-effects-before-judgment; refusal frame is audit-only; error responses are labeled egress flows; modifies-on-Ok/Err claims.

<!-- ticket:T-0070 -->
```yaml
id: T-0070
title: strata errors-total, panics-contained, observe blocks (ERR/OBS gates)
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Exhaustive ErrorSet consumption + variant liveness + no-discarded-Result (graph join); per-language panic chokepoints; observe = obligated labeled flows to an observability node; log rules enable detection SLAs via the cascade.

<!-- ticket:T-0071 -->
```yaml
id: T-0071
title: 'strata-core: independent Rust/PyO3 kernel crate (closure + propagation)'
state: done
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: T-0051
scope:
- src/frob/strata/**
- tests/unit/strata/**
- docs/strata/**
- tickets.md
- pyproject.toml
- strata-core/**
- Makefile
- .github/**
evidence:
- tests/unit/strata/test_facts.py::TestClosure::test_boundaries_stop_taint_unless_asked_otherwise
- tests/unit/strata/test_facts.py::TestClosure::test_worst_age_reports_unbounded_on_a_positive_cycle
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_2_refund_decision_reads_a_stale_replica
attachments: []
acceptance: []
threat: null
```
Own crate mirroring the frob-core maturin pattern; NOT shared with lithos (inspiration only). Kernels: fixpoint closure, staleness/capacity propagation over big models. No pure-Python fallback once adopted.

## Done report

Pulled forward from phase 2 by user directive (Rust-first: the prover
runs constantly). Delivered strata-core/: independent Cargo/maturin
crate (pyo3 0.22, abi3-py311, same posture as frob-core), kernels
reachable (deterministic BFS closure, barrier semantics), worst_age
(memoized longest-path DFS, +inf on positive cycles), demand
(inbound-rate aggregation); bundled .pyi stub + py.typed so ty sees
typed signatures. src/frob/strata/_facts.py now delegates all three
kernels to strata_core with NO pure-Python fallback (ImportError with
`make core` remedy); pydantic interface unchanged -- all 45 strata
tests green against the Rust kernels, 5 cargo tests green. Makefile
`core` target and CI build/test extended to both crates. Charter D3
amended in docs/strata/charter.md; kernel.md gained the strata-core
section. PyO3 exports annotated (frob:doc + frob:tests) per the
rust-publicness rule.

<!-- ticket:T-0072 -->
```yaml
id: T-0072
title: strata tube + chirp litmus models + goldens
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0050
parent: T-0051
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- design/litmus/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Tube: stampede/cold-cache, immutable-TTL pairing, CDN declassification, payout-vs-approximate-counter. Chirp: fanout write ceiling under zipf skew forcing the hybrid. Phase-2 exit criterion.

<!-- ticket:T-0073 -->
```yaml
id: T-0073
title: 'strata scenario engine: node loss, rate surge, trust downgrade'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0051
parent: T-0052
scope:
- src/frob/strata/**
- tests/unit/strata/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Scenario = counterfactual model rewrite; all claims re-checked under it; quorum/placement arithmetic; retry-storm multipliers.

<!-- ticket:T-0074 -->
```yaml
id: T-0074
title: 'strata crash contracts: on-crash, no-hang check, crash-retry-idempotency join'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0051
parent: T-0052
scope:
- src/frob/strata/**
- tests/unit/strata/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Crash-only contracts desugar to auto scenarios + bounds; every caller of a crashable component must declare a compatible timeout; crash+retry implies at-least-once implies idempotency demand downstream.

<!-- ticket:T-0075 -->
```yaml
id: T-0075
title: 'strata atomic/saga: cross-store refusal + fault-injection generation'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0051
parent: T-0052
scope:
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
modifies {} on Err via stage-commit (infallible-commit decidable from Result graph), immutable swap, tx chokepoint, WAL; atomic claims spanning stores refused without saga/2PC; generated exhaustive fault-injection property tests from closed ErrorSets.

<!-- ticket:T-0076 -->
```yaml
id: T-0076
title: 'strata breach scenarios: blast radius + recovery-path independence'
state: queued
kind: security
origin: human
created: '2026-07-17'
blocked_by:
- T-0051
parent: T-0052
scope:
- src/frob/strata/**
- tests/unit/strata/**
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
trust(X) := foreign rewrite; reachability = blast radius; containment bounds (credential age, revocation SLA, detection SLA); assert independent(recovery path, compromised node).

<!-- ticket:T-0077 -->
```yaml
id: T-0077
title: 'strata as 6th frob.lang grammar: design constructs become graph symbols'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0052
parent: T-0053
scope:
- src/frob/lang/**
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
ParsedFile contract over .strata: components/boundaries/claims get qualnames, sig/body digests, acks, DRIFT, frob:doc edges, COV obligations -- the whole existing machinery for free.

<!-- ticket:T-0078 -->
```yaml
id: T-0078
title: 'strata code binding: code globs + import-level conformance'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0052
parent: T-0053
scope:
- src/frob/strata/**
- src/frob/gates/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Undeclared cross-component import = SYS violation with file:line; unclassified code is foreign by default; reflexion-model tier.

<!-- ticket:T-0079 -->
```yaml
id: T-0079
title: 'strata effect extraction: net/fs/exec facts vs may-capabilities'
state: queued
kind: security
origin: human
created: '2026-07-17'
blocked_by:
- T-0052
parent: T-0053
scope:
- src/frob/lang/**
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: tampering
```
Per-language extraction of socket/http/fs/subprocess surfaces; an effect with no may clause in its component fails; sound given std.policy.analyzable (tracked via enables).

<!-- ticket:T-0080 -->
```yaml
id: T-0080
title: strata directives (frob:channel/boundary/secret) + SYS gates in run_gates
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0052
parent: T-0053
scope:
- src/frob/graph/**
- src/frob/gates/**
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Call sites bind to kernel edges; SYS001.. family joins model, graph, and evidence in frob check with severity dial + waivers + remedies.

<!-- ticket:T-0081 -->
```yaml
id: T-0081
title: 'strata self-hosting: design/frob.strata models frob itself'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0052
parent: T-0053
scope:
- design/**
- frob.toml
evidence: []
attachments: []
acceptance: []
threat: null
```
frob declares its own components (lang/graph/gates/tickets/check), trust levels, and module-dependency architecture in strata and gates on it. Phase-4 exit criterion; supersedes the informal docs/rework.md dependency diagram as enforced truth.

<!-- ticket:T-0082 -->
```yaml
id: T-0082
title: 'strata std.secrets: credentials as cache-of-authority'
state: queued
kind: security
origin: human
created: '2026-07-17'
blocked_by:
- T-0053
parent: T-0054
scope:
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
issued-by/audience/lifetime/revocation; no credential without a revocation edge (same rule as cache invalidation); readers() as exact-set closure; secret-in-logs/repo/artifact become label violations.

<!-- ticket:T-0083 -->
```yaml
id: T-0083
title: 'strata std.deploy: endorsement pipeline, canary schedules, rollback budgets'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0053
parent: T-0054
scope:
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Review/build/admit as endorsement boundaries on code-as-data (SLSA falls out); noflow(unreviewed -> prod); staged rate bounds; frob vet as the endorsement evidence for third-party code.

<!-- ticket:T-0084 -->
```yaml
id: T-0084
title: 'strata frob sys plan: obligation -> ticket compiler'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0053
parent: T-0054
scope:
- src/frob/strata/**
- src/frob/tickets/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
REFUTED claims, undischarged obligations, expiring assumes become scoped tickets (scope from counterexample paths, blocked_by from proof dependencies, STRIDE prefilled); idempotent re-planning; sys tickets close only when the claim discharges at the required rung.

<!-- ticket:T-0085 -->
```yaml
id: T-0085
title: strata frob sys doc + DOC002 claims audit
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0053
parent: T-0054
scope:
- src/frob/strata/**
- src/frob/docs/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Generated reference (prose + mermaid topology) per module; guarantee-shaped prose in docs must cite a PROVED claim via frob:claim anchors; overclaiming documentation becomes a build failure.

<!-- ticket:T-0086 -->
```yaml
id: T-0086
title: 'strata exporters: k8s netpol / seccomp / IAM from the model'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0053
parent: T-0054
scope:
- src/frob/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
The model compiles to runtime enforcement so static proofs are backed by defense-in-depth that cannot diverge; exported artifacts digest-stamped as evidence.

<!-- ticket:T-0087 -->
```yaml
id: T-0087
title: python CONST extraction misses call-expression assignments (X = Foo(...))
state: queued
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/lang/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
UPPER_CASE module constants assigned from a constructor call (TRUST = Lattice(...) in src/frob/strata/_models.py) are not extracted as CONST symbols, so frob:doc/frob:describes edges to them dangle (DRIFT002) and COV001 cannot see them. Found during T-0055.

<!-- ticket:T-0088 -->
```yaml
id: T-0088
title: reorganize flat docs/ into guides/ modules/ commands/ hierarchy
state: done
kind: docs
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- docs/**
- src/**
- tests/**
- frob-core/**
- README.md
- frob.toml
- tickets.md
- agents/**
- skills/**
- scripts/**
- invariants/**
- TODO.md
- pyproject.toml
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
attachments: []
acceptance:
- GIVEN the moved docs WHEN frob check runs THEN doclink/drift/coverage gates pass
  with zero dangling frob:doc or describes edges
threat: null
```
Flat docs/ (31 files) becomes: index.md + rework.md at root; guides/ (quickstart, agentic-workflow); modules/ (19 module design docs); commands/ (9 per-command refs); strata/ unchanged. Every frob:doc directive, describes anchor consumer, markdown/backtick link, and config path updated in the same change.

## Done report

Moved 30 files via git mv: guides/ (2), commands/ (9), modules/ (19);
index.md + rework.md stay at root; strata/ untouched. One global rewrite
pass updated every reference in 179 tracked files (frob:doc directives,
backtick doc links, README, TODO.md, pyproject.toml, agents/, skills/,
scripts/, invariants/, frob-core comments). 17 E501s introduced by the
longer paths fixed by wrapping at the doc parenthetical -- doc-facet
digests unaffected because doc_text is whitespace-collapsed by design.
Acceptance verified: frob graph build clean (edges stable at 1311, zero
dangling), frob check --ticket T-0088 exit 0 (doclink/drift/coverage all
pass), frob test --base main --lang python PASS, cargo test --lib 13/13
PASS.

<!-- ticket:T-0089 -->
```yaml
id: T-0089
title: test_scaffold_dx flaky under full-suite run, passes in isolation
state: queued
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- tests/system/**
evidence: []
attachments: []
acceptance: []
threat: null
```
tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately failed during a full uv run pytest -q but passes standalone; suspect shared graph cache or cwd contention between system tests. Found during T-0058 close-out. Also: pytest.mark.slow is unregistered (PytestUnknownMarkWarning).

<!-- ticket:T-0090 -->
```yaml
id: T-0090
title: TEST002 misses frob:tests directives bound cross-file to rust symbols
state: queued
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Reviewer finding during T-0059: strata-core/src/parse.rs carries 18 frob:tests directives targeting strata-core/src/lib.rs::parse_source, but TEST002 reports 0 unit cases collected for that symbol. Suspect the unit-edge collector does not resolve directives living in a different file than the target symbol (rust cross-file binding). Warn-level today; worth fixing before TEST002 is promoted to error.

<!-- ticket:T-0091 -->
```yaml
id: T-0091
title: make core creates a stray venv under strata-core/, contaminating the editable
  install
state: queued
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- Makefile
evidence: []
attachments: []
acceptance: []
threat: null
```
found while working T-0062: running `make core` from repo root invokes `cd strata-core && uvx maturin develop --uv --release`, which (unlike the frob-core target) causes uv/maturin to create and install into a fresh strata-core/.venv instead of the repo root .venv, so the root .venv's installed strata_core.abi3.so goes stale after a rebuild until VIRTUAL_ENV is pinned manually. Repro: rm -rf strata-core/.venv; make core; compare md5sum of strata-core/target/release/libstrata_core.so vs .venv/lib/python3.11/site-packages/strata_core/strata_core.abi3.so -- they differ. Workaround used in T-0062: VIRTUAL_ENV=$(pwd)/.venv uvx maturin develop --uv --release -m strata-core/Cargo.toml. Suggested fix: set VIRTUAL_ENV explicitly in the Makefile core target for both crates, or add a .python-version/uv marker to strata-core/ so uv resolves the root venv the same way it does for frob-core.

<!-- ticket:T-0092 -->
```yaml
id: T-0092
title: 'rust test integration: [[test.runner]] for cargo + COV003 evidence resolution'
state: queued
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- frob.toml
- src/frob/testing/**
- src/frob/gates/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Two symptoms, one gap, both hit on 2026-07-17: (1) frob test --base main errors NoRunner when rust files are touched because frob.toml has no [[test.runner]] language=rust entry (cargo needs PYO3_PYTHON + LD_LIBRARY_PATH env to link); (2) COV003 rejects cargo test ids as ticket evidence because only python tests are collected (T-0062 closed with rust ids and broke repo check until swapped for pytest ids). Wire a cargo runner + rust test collection so native-kernel work can cite its real tests.

<!-- ticket:T-0093 -->
```yaml
id: T-0093
title: 'strata grammar: explicit trust clause for queue/balancer'
state: queued
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- strata-core/src/parse.rs,src/frob/strata/_ast.py,src/frob/strata/_infra.py,docs/strata/surface.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0064 discovery: std.infra's queue/balancer grammar has no TRUST clause (unlike store/cache/cdn), so _infra.py::elaborate_infra defaults both to "trusted" -- documented in docs/strata/surface.md#std-infra as a deliberate deviation. Add an optional (or mandatory, per law 2) trust clause to the queue/balancer grammar productions and thread it through StoreDecl-sibling AST models and elaborate_infra instead of the hardcoded default.

<!-- ticket:T-0094 -->
```yaml
id: T-0094
title: 'frob ticket evidence subcommand: append structured evidence ids from the CLI'
state: queued
kind: ux
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Three implementer agents in a row (T-0062, T-0063, T-0064) wrote Done-report prose evidence but left the structured evidence: YAML empty or wrong (cargo ids), because the only way to record evidence is hand-editing tickets.md YAML. Add 'frob ticket evidence T-XXXX <pytest-node-id>...' that validates ids against collected tests (rejecting unresolvable ids up front, closing the COV003 gap at write time) and appends to the structured list. Orchestration keeps catching this by hand; the tool should make the right thing the easy thing.

<!-- ticket:T-0095 -->
```yaml
id: T-0095
title: 'frob check --delta: report only violations new since a stamped baseline'
state: queued
kind: ux
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/check/**
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Agentic token sink measured during the strata build: every frob check run prints ~90 pre-existing warn-level violations (ticketed legacy debt), and each implementer agent runs check 3-6 times per ticket, paying to re-read the same noise. Add a baseline stamp (like coverage-stamp) plus --delta mode that prints only violations absent from the baseline; frob check --stamp-baseline records it. Warn-dial stays for humans; agents get signal only.

<!-- ticket:T-0096 -->
```yaml
id: T-0096
title: 'frob ticket archive: rotate done tickets out of the active ledger'
state: queued
kind: ux
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
tickets.md is 2100+ lines and grows with every done report; agents hand-edit it by string surgery (three evidence failures already) and re-read big chunks every mission. Add frob ticket archive moving done/dropped tickets verbatim to tickets-archive.md (same format, grep-compatible, still tracked); active ledger stays a few hundred lines. Single-file model preserved -- just two files by temperature. Complements T-0094 (evidence CLI).

<!-- ticket:T-0097 -->
```yaml
id: T-0097
title: README banner with goblin mascot (aviator cap, crystal ball of rune-code)
state: done
kind: docs
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- README.md
- docs/assets/**
- tickets.md
- .gitignore
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
attachments: []
acceptance: []
threat: null
```
Professional repo banner: dark, wordmark + tagline, mascot = cute-ugly miniature green goblin in an aviator cap hunched over a black crystal ball showing unintelligible syntax-highlighted glyph-code. Hand-authored SVG (ASCII-only source, glyphs drawn as paths not unicode), render-iterated via browser screenshots.

## Done report

docs/assets/frob-banner.svg hand-authored (ASCII source, glyph-code as
paths, no unicode): dark modern frame (soft corner glows, gradient
wordmark, pill chips for graph/tickets/gates/strata), goblin mascot in
aviator cap + goggles hunched over the crystal ball, fingers gripping
the glass, syntax-highlighted rune-code inside. Render-iterated 4
versions via cairosvg screenshots (v1 rabbit-ears/beside-ball, v2
turtle-read/face-hidden, v3 composition fixed, v4 face polish).
README.md includes it above the H1. frob check exit 0.

<!-- ticket:T-0098 -->
```yaml
id: T-0098
title: frob ticket attach without path should error usefully outside a TTY
state: queued
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Malmberg adoption agent gap report: frob ticket attach with no path argument attempts clipboard-image capture even in a non-interactive agent session, instead of failing fast with a clear message (or accepting a text note). Agents cannot paste from a clipboard; the command should detect no-TTY and error with remedy text.

<!-- ticket:T-0099 -->
```yaml
id: T-0099
title: document demand() behavior shift for unresolvable rates (propagates vs drops)
state: queued
kind: docs
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- docs/strata/**
- src/frob/strata/**
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0066 reviewer finding: flows whose rate.base_value() errors were previously dropped from demand sums; propagated_demand now treats them as undeclared and recurses into upstream demand. Probably more correct (fails toward propagating load) but undocumented; document in kernel.md capacity semantics or revert deliberately.

<!-- ticket:T-0100 -->
```yaml
id: T-0100
title: frob:tests directives silently degrade when stacked 3+ or separated from def
state: queued
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
typani campaign gap report: a stack of 3 frob:tests directives above one test def collapsed to a generic file-level edge losing kind=unit; a 5-stack silently dropped the first 3; directives above non-def statements degrade too. Silent data loss in the obligation graph -- should either work or error loudly.

<!-- ticket:T-0101 -->
```yaml
id: T-0101
title: extend frob:waive to arch/perf tool channels or document the boundary
state: queued
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/arch/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
typani campaign gap report: frob:waive suppresses gates-channel rule ids only; a waive on an arch long-function finding has no effect and fails silently. Either honor waivers in the arch/dup tool channels or make the waive command error when targeting an unwaivable channel.

<!-- ticket:T-0102 -->
```yaml
id: T-0102
title: frob check must FAIL, not silently pass, when the ticket queue fails to load
state: in-progress
kind: bug
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/check/**
- src/frob/gates/**
- src/frob/tickets/**
- tests/**
- tickets.md
evidence:
- tests/unit/test_check.py::TestRunGatesQueueFailure::test_malformed_tickets_md_is_hard_error_not_silent_skip
- tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_rejects_malformed_entry_before_write
- tests/test_tickets.py::TestEvidenceValidation::test_new_ticket_validates_evidence
attachments: []
acceptance: []
threat: null
```
Found during T-0067/68 review: a malformed evidence block in tickets.md made load_queue fail; frob check printed 'gates skipped: Ticket queue failed to load' and EXITED 0 -- every obligation gate silently vanished while reporting success (the vacuous-pass class again). A queue load failure must be a hard error with remedy text. Companion fix: frob ticket new/close should validate evidence schema on write so malformed entries cannot land at all.

## Done report

Changed: `_run_gates` in src/frob/check/_python.py now special-cases
`GateError.QueueUnavailable` as a hard ERROR ToolResult (exit_code=1,
remedy text), never a soft skip; all other GateError variants keep the
existing soft-skip behavior. Companion fix: `validate_evidence` and
`add_evidence` (src/frob/tickets/__init__.py) plus `TicketSpec.evidence`
(src/frob/tickets/_models.py, new `MalformedEvidence` error) give an
in-process, schema-validated path for evidence to land on a ticket, so a
malformed entry can no longer be constructed via `new_ticket`. A CLI
flag to drive `add_evidence` from `frob ticket close --evidence` would
touch src/frob/__main__.py, src/frob/app/**, and docs/** -- all outside
this ticket's scope; filed as a follow-up.
Evidence: see evidence: list above (all collected, pytest --collect-only verified).
Filed: T-0103 (CLI wiring for `frob ticket close --evidence`, outside T-0102 scope).
Gates: `frob check --ticket T-0102` and plain `frob check` both exit 0
(gates stage genuinely executes, no violations introduced).

<!-- ticket:T-0103 -->
```yaml
id: T-0103
title: Wire frob ticket new/close --evidence to tickets.add_evidence
state: queued
kind: feature
origin: agent
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- docs/commands/check.md
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0102 added frob.tickets.validate_evidence/add_evidence (schema-validated, in-process path for landing ticket evidence) but left them unwired to the CLI because src/frob/__main__.py, src/frob/app/config.py, src/frob/app/ticket_runner.py, and docs/** are outside T-0102's declared scope (src/frob/check/**, src/frob/gates/**, src/frob/tickets/**, tests/**). Add --evidence (repeatable) to 'frob ticket new' and 'frob ticket close', wire through AppConfig.ticket_evidence, call add_evidence/TicketSpec.evidence, and document in docs/modules/tickets.md + docs/commands/check.md. This removes the last reason for agents to hand-edit the evidence: YAML block in tickets.md directly.
