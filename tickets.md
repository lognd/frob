# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0001 -->
```yaml
id: T-0001
title: frob-core PyO3/maturin crate + smart dup (Phase 7)
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/dup/**,frob-core/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Phase 7 (0.2.0), designed in docs/dup.md: frob-core PyO3/maturin crate (R3 canonicalizer, winnowing, LSH, WL-kernel, APTED; compute-only, no-Python-fallback, lithos as build reference); region-granular matching (function/subsection); content-addressed fingerprint + LRU verdict caches in .frob/dup.db; DUP001/DUP002 gates; R6 observational probing via frob.fuzz generators; pre-work sweep re-platformed onto it.

<!-- ticket:T-0002 -->
```yaml
id: T-0002
title: frob.fuzz generators + FUZZ gates (Phase 8)
state: queued
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
Phase 8 (0.2.0), designed in docs/fuzz.md: Arbitrary protocol (derive from pydantic / __fuzz__ / register), FUZZ001-003 gates, frob test --fuzz with digest-stamped corpus under .frob/corpus (LRU-capped), invariant-anchored default obligation; Rust/TS generator wiring as follow-on. Blocked by T-0001 (frob.fuzz's R6 probing depends on frob-core).

<!-- ticket:T-0003 -->
```yaml
id: T-0003
title: 'REL001 release gate: semver-correct version bump from graph digests'
state: queued
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

<!-- ticket:T-0004 -->
```yaml
id: T-0004
title: 'Decision records (ADR): decisions/AD-###.md + frob:decision edges'
state: queued
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
- src/frob/tickets/**,docs/tickets.md
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
- src/frob/tickets/**,docs/tickets.md
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
- src/frob/tickets/**,docs/tickets.md
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
title: 'frob.vet: dependency capability vetting (docs/vet.md build-out)'
state: queued
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
Full build-out of frob.vet per docs/vet.md: tree-sitter capability scan of the locked dependency tree, declaration-vs-observation conformance ([vet.allow]), version capability-escalation diffs as primary supply-chain signal, obfuscation unconditionally fatal, content-addressed verdict cache; VET001-VET010 gates; typed adapters over osv-scanner/GuardDog/Scorecard/sigstore-SLSA with skipped-never-silent absence; per-ecosystem rule families (VET-PY/VET-RS/VET-C/VET-JS) plus VET011 slopsquat/cooldown quarantine; first-party anomaly detectors (VET008 artifact/source divergence, VET009 stylometric self-similarity via frob-core WL kernels, VET010 sandboxed capability divergence); absorbs license/pinning checks. Not touched by this ticket's author -- owned by the concurrent vet workstream.

<!-- ticket:T-0009 -->
```yaml
id: T-0009
title: 'frob stats: DORA-ish measurement from gitlog + tickets'
state: queued
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

<!-- ticket:T-0010 -->
```yaml
id: T-0010
title: 'frob serve: MCP adapter over stale_docs/doable_tickets/check_scope/pre_work'
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/**
evidence: []
attachments: []
acceptance: []
threat: null
```
MCP adapter exposing stale_docs/doable_tickets/check_scope/pre_work queries as MCP tools, so agent clients can query frob state without shelling out. Deferred post-0.1.0.

<!-- ticket:T-0011 -->
```yaml
id: T-0011
title: Mutation testing as the test-quality oracle
state: queued
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
state: queued
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

<!-- ticket:T-0014 -->
```yaml
id: T-0014
title: Annotate legacy modules (app/, check/, process/, etc) to flip COV001 back to
  error
state: queued
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
docs/gates.md's rule catalog states severity is 'per-rule default overridable in frob.toml', but src/frob/gates/__init__.py's own Phase 4 implementation notes say this was explicitly scoped out: severities are fixed constants in code (ERROR for DRIFT/COV002-004/SCOPE001/PRE001/INV001-002/TEST001/TEST004/WAIVE001; WARN for COV001/TODO001/TEST002/003/005), and frob.toml has no [rules] or per-rule table read anywhere in the gates loading path. This was discovered while trying to set a legacy-adoption severity baseline (TEST001/TEST004/TEST006 -> warn) for the dogfood milestone: writing such config to frob.toml would be silently ignored, so no baseline was written. Implement real per-rule severity override support (e.g. a [rules] table in frob.toml, read in run_gates, applied when constructing each Violation) so this baseline can actually be set.

## Done report

Implemented [gates.severity] frob.toml table; applied as a
post-processing step in run_gates (_apply_severity_overrides) so every
gate stays pure and there is exactly one override site. Garbage values
are logged and ignored. docs/gates.md severity paragraph now true.

<!-- ticket:T-0016 -->
```yaml
id: T-0016
title: Re-platform map/outline/xref/cycle/dup onto frob.lang; delete frob.ast
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0001
parent: null
scope:
- src/frob/map/**,src/frob/outline/**,src/frob/xref/**,src/frob/cycle/**,src/frob/dup/**,src/frob/ast/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Re-platform map/outline/xref/cycle/dup onto frob.lang's uniform ParsedFile contract, then delete src/frob/ast. Deferred post-0.1.0; blocked_by T-0001 since dup's re-platform is entangled with the frob-core work.

<!-- ticket:T-0017 -->
```yaml
id: T-0017
title: Pair-level (consumer x provider) integration test obligations for TEST003
state: queued
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
TEST003 alpha semantics treat every src/<pkg> directory with a public symbol as an interface owing min_integration edges (an honest over-approximation, per docs/gates.md's Phase 4 notes). Deferred: derive real consumer x provider pairs once frob.graph gains cross-file import edges, and require min_integration per pair rather than per provider.

<!-- ticket:T-0018 -->
```yaml
id: T-0018
title: Convention-based unit-test binding inference to reduce frob:tests annotation
  burden
state: queued
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
title: 'frob.perf: profiling, heat-maps, PERF linear-scan rules (docs/perf.md)'
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
- docs/perf.md
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
- docs/perf.md (refreshed for actual coverage/caveats), docs/index.md (link added)
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
state: queued
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/check/**
- src/frob/app/check_runner.py
evidence: []
attachments: []
acceptance: []
threat: null
```

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
state: queued
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
evidence: []
attachments: []
acceptance: []
threat: null
```
found while working T-0021: python -m cProfile exits 0 even when the profiled program exits nonzero (verified: pytest usage error exit 4 -> wrapped exit 0). profile_command therefore records a successful artifact for a workload that never ran. Consider a shim entry that captures SystemExit and records the real returncode in the meta sidecar.

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
path references (terminal-first index style), docs/exports.md linked in
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
- docs/tickets.md
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
- docs/tickets.md
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
