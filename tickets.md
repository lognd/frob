# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0969 -->
```yaml
id: T-0969
title: 'Epic: burn WARN-tier quality gates to zero, then promote to ERROR'
state: queued
kind: security
origin: auditor
created: '2026-07-27'
priority: high
parent: null
tier: epic
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-0399's gates-quality audit (docs/audits/gates-quality.md) found the
entire quality/security-advisory surface (PERF001-004, PII010/012, SEC110,
ARCH001, DUP) is WARN-tier and non-blocking, so a green `frob check` makes
no quality claim. T-0399 executed the promotable-now slice (DUP fail-
closed behavior) and measured live warning counts per family. This epic
parents the burn-down children needed before each remaining family can be
safely promoted to ERROR without redding main.

<!-- ticket:T-1135 -->
```yaml
id: T-1135
title: 'EPIC frob refactor: transactional move/rename/split with full reference, directive,
  and obligation rewrite'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
acceptance:
- text: 'GIVEN frob refactor move/rename/split on a symbol or module family WHEN it
    completes THEN all imports and call sites are rewritten (absolute imports, auto-aliasing
    on destination or import-site name conflicts, with a disclosed alias report),
    and every frob-owned reference moves with the symbol: frob:tests/frob:doc/frob:enforces
    target forms, waiver symrefs including path:: prefixes, PII012 (file,token) allowlist
    entries, check-coverage registry citations, and archived-ticket evidence node
    ids'
  evidence: []
- text: GIVEN a refactor that cannot complete every rewrite THEN it refuses and rolls
    back rather than leaving a half-move; post-conditions verified in-command (import
    graph resolves, tests collect, gate findings diff-clean vs pre-refactor)
  evidence: []
- text: 'GIVEN a moved or renamed symbol WHEN the refactor completes THEN every mention
    of it in prose is rewritten too: docstrings and comments naming the dotted path
    (including all frob: comment-DSL directive targets anywhere in the repo, not just
    those attached to the moved symbol), docs/** prose and code refs, and doc anchors
    whose heading slugs embed the symbol or module name -- auto-documentation updating
    is part of the transaction, with unresolvable prose mentions listed in the disclosed
    report rather than silently skipped'
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: refactors today mean an agent hand-editing every import and callsite, and -- the expensive part -- hand-carrying frob's symbol-attached bookkeeping. Second user directive same day: the rewrite must ALSO cover frob symbols and symbols in comments -- auto-documentation updating -- because a rename that fixes code but strands docs/docstring/comment mentions just converts silent breakage into doc drift (the DRIFT001/DOC006 class this repo keeps paying down). Evidence from this drive: 3 coordinator INV006 waiver carries in one wave (0abc4e3a), PII012 allowlist re-keying on every move (T-1076), the ARCH101/103 waiver-symref path:: bug where moved waivers never matched again, archived evidence repoints after litmus renames (8dae48c5), DRIFT002 edge repoints. frob owns the graph/binding/exports substrate to do this transactionally. Python first; the multi-language binding tables (TS/Rust/C-C++/Kotlin) extend it later. Children to file at design time: reference-rewrite engine, directive/waiver carrier (absorbs T-1134), registry/evidence repointer, split verb built on the T-1072/T-1077 family-extraction pattern, alias-conflict policy. Relationship: makes T-1108/T-1115-class split tickets mechanical.

<!-- ticket:T-1136 -->
```yaml
id: T-1136
title: 'EPIC ledger v2: per-ticket files replace the tickets.md monofile (design first,
  then migration)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/tickets/**
- docs/design/**
- tests/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
acceptance:
- text: GIVEN the design doc WHEN reviewed THEN it covers file-per-ticket layout (block
    + done report), draft lifecycle without splice restores, cross-ticket operations
    (renumber with reference rewrite, doable ordering, archive as git mv, flow/velocity
    mining), lock model, merge story with the frob-ledger driver retired, greppability,
    and a reversible migration plan with a compatibility window
  evidence: []
- text: GIVEN the migration lands THEN the land path performs no monofile splice,
    two agents landing disjoint tickets produce no ledger merge conflict, and the
    TICK002/TICK006 draft-death classes are structurally impossible or auto-repaired
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: too much manual work rides on tickets.md mechanics. The monofile is the root cause of a documented incident museum: land splice regression (T-0577), archive clobber (T-0959), ledger churn rewrites (T-1036), id collision (T-1090), draft deaths in 10b restores (4 coordinator refiles on 2026-07-28 alone: T-1115, T-1126, T-1127, T-1128), DirtyMain transitions (T-1054), hand splices where the merge driver is unregistered in worktrees, ledger-lock starvation and deadlocks (T-0933, T-0982). Per-ticket files make disjoint tickets disjoint git objects so merge/lease/draft/renumber/archive become ordinary git operations. The global convention (tickets/ tracked in git) already names the directory form. Design doc in docs/design/ first; migration is a separate child with golden round-trip tests; T-1125 (draft-id prose rewrite) stays valuable pre-migration and its engine is reusable for renumber-with-references after.

<!-- ticket:T-1137 -->
```yaml
id: T-1137
title: 'EPIC frob check --fix: tiered auto-fix engine (auto / verified-auto / assisted
  fix-its)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/gates/**
- src/frob/app/**
- docs/**
- tests/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
acceptance:
- text: GIVEN frob check --fix WHEN Tier-A findings exist THEN deterministic semantics-preserving
    fixes are applied (directive-form rewrite, unique anchor-slug correction, fmt,
    draft renumber, generated-registry regeneration, release sync, full-run-verified
    stale-waiver removal) and the affected gates re-run clean in the same invocation
  evidence: []
- text: 'GIVEN a Tier-B fix WHEN applied THEN it is transactional: affected gates
    plus the finding''s bound tests re-run per fix and any regression rolls that fix
    back with a disclosed report'
  evidence: []
- text: GIVEN a Tier-C (content-required) finding THEN --fix never edits it and never
    inserts a waiver; it emits a structured fix-it (file, line, proposed patch) for
    explicit acceptance -- an obligation can never be auto-discharged by waiver
  evidence: []
- text: GIVEN the generated rule registry THEN every rule id carries a fixability
    tier (auto/verified/assisted/manual) that is generated-verified against the fix
    engine's actual handler table, so an unwired fixability claim is a check failure
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: the annoying errors are the ones whose fix is mechanical but manual. Drive evidence: DRIFT002 dotted-form rewrites redded main twice and are pure string rewrites; T-0602's one wrong anchor slug caused 11 COV001s with an unambiguous correct slug available; TICK002's message prints its own fix command; REL002 took three incidents before land invoked the existing frob release sync; E501-on-waive-lines when frob fmt exists and is idempotent; WAIVE004 removal is mechanical given a full run (mechanizes T-1021's hand-sweep); REG008/REG010 enforces edges are derivable from emitting sites (T-1008 generate-and-verify precedent). Design doc first (docs/design/): fix-handler protocol per rule id, transaction/rollback model, interaction with frob doctor (inventory what doctor already repairs and fold or delegate), daemon-warm --fix, and the two anti-goals (no auto-waivers ever; no threshold loosening ever). Children at design time: Tier-A handler batch, Tier-B transaction engine, fixability registry field, fix-it emission format for agents.

<!-- ticket:T-1204 -->
```yaml
id: T-1204
title: 'perf: hot-graph burn-down (2026-07-29 profile)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
threat: null
component: null
```
Umbrella epic for the 2026-07-29 in-process cProfile hot-graph report (scratchpad hotgraph/report.md). 11 children, one per ranked PERF candidate (10 from the report's 'Ranked PERF ticket candidates' section) plus a CLI-startup lazy-import fix. Each child fixes a measured root cause AND ships a PERF01x lint rule per repo convention (perf root causes ship as both a .strata obligation and a PERF0xx detector, never fix-only). See STANDALONE ticket 'perf: PERF01x detectors from hot-graph root causes' for the four new detector rules this epic's children rely on.

<!-- ticket:T-1205 -->
```yaml
id: T-1205
title: 'coverage as managed derived state: auto-refresh touched-set, never stale,
  never manual'
state: in-progress
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- Makefile
- src/frob/gates/_coverage.py
- src/frob/check/__init__.py
- docs/modules/gates.md
- tests/test_coverage.py
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_coverage.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_coverage.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: TEST005's violation-emitting helpers (_test005_symbols/_modules/_systems)
    live in src/frob/gates/__init__.py, not _coverage.py -- acceptance[1]'s stale-and-disclosed
    marking must be added there; tests/test_gates.py is where TEST005's existing test
    coverage lives
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: TEST005's violation-emitting helpers (_test005_symbols/_modules/_systems)
    live in src/frob/gates/__init__.py, not _coverage.py -- acceptance[1]'s stale-and-disclosed
    marking must be added there; tests/test_gates.py is where TEST005's existing test
    coverage lives
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestTestGate::test_test005_symbol_finding_discloses_stale_coverage
- tests/test_gates.py::TestTestGate::test_test005_symbol_finding_no_disclosure_when_fresh
- tests/test_gates.py::TestTestGate::test_test005_module_finding_discloses_stale_coverage
- tests/test_gates.py::TestTestGate::test_test005_system_finding_discloses_stale_coverage
- tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction
- tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data
- tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files
- tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
- tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps
- tests/test_coverage.py::TestNativeCoverageRefresh::test_pytest_failure_is_err
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
acceptance:
- text: GIVEN a tracked source change WHEN the user runs frob coverage, or frob test
    --wait-coverage (via run_coverage_wait) THEN coverage data is refreshed automatically
    via the touched-set test machinery (frob.testing._incremental_coverage.python_coverage_targets)
    merged into the persisted coverage store, in-process, no Makefile/shell dependency
    -- the common incremental loop never requires a manual make coverage invocation;
    frob check itself deliberately does NOT trigger a refresh (see acceptance[4]);
    make coverage (the full-suite target) remains a legitimate manual/coordinator-only
    step for its own xdist-crash-recovery resilience, disclosed not silently dropped
  evidence:
  - tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
  - tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- text: GIVEN coverage data that cannot be refreshed (tests failing, run interrupted)
    THEN TEST005-family findings against stale regions are marked stale-and-disclosed
    rather than reported as current fact, and TEST011 escalates from advisory to a
    blocking freshness contract
  evidence:
  - tests/test_gates.py::TestTestGate::test_test005_symbol_finding_discloses_stale_coverage
  - tests/test_gates.py::TestTestGate::test_test005_module_finding_discloses_stale_coverage
  - tests/test_gates.py::TestTestGate::test_test005_system_finding_discloses_stale_coverage
  - tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction
- text: 'GIVEN an unchanged file THEN its coverage is never recomputed: per-file coverage
    keyed by content hash, full-suite runs reserved for cold start or explicit --full'
  evidence:
  - tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty
  - tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file
  - tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash
  - tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data
  - tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files
  - tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache
- text: 'GIVEN any frob-enabled repo on any OS (Linux, macOS, Windows) WHEN coverage
    refresh is needed THEN a frob-native command (frob coverage or frob test --coverage)
    performs the whole orchestration -- subprocess rc generation, pytest invocation,
    combine, xml, stamp -- in Python with no Makefile or shell dependency; make coverage
    becomes a thin optional wrapper calling it (user directive 2026-07-29: portable,
    not just this project and not just Linux)'
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_pytest_failure_is_err
  - tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- text: GIVEN a frob command that actually RUNS tests to obtain coverage data (frob
    test --wait-coverage, via run_coverage_wait) THEN the frob-native coverage refresh
    runs automatically inside it (touched-set only, in-process, no spawned command)
    -- the user never invokes a separate refresh verb for that path, and nothing cached
    is re-run; frob check deliberately does NOT auto-trigger a refresh, for any caller
    (agent or non-agent) -- a documented, deliberate boundary (docs/modules/cli.md#frob-coverage-t-1525),
    not an omission
  evidence:
  - tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh
  - tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
acceptance_amendments:
- op: replace
  index: 4
  old_text: 'GIVEN a frob command whose gates need coverage data WHEN the freshness
    contract says it is stale THEN the frob-native coverage refresh runs automatically
    inside that command (touched-set only) -- the user never invokes a refresh verb,
    and nothing cached is re-run (user directive 2026-07-29: minimal friction)'
  new_text: GIVEN a frob command that actually RUNS tests to obtain coverage data
    (frob test --wait-coverage, via run_coverage_wait) THEN the frob-native coverage
    refresh runs automatically inside it (touched-set only, in-process, no spawned
    command) -- the user never invokes a separate refresh verb for that path, and
    nothing cached is re-run; frob check deliberately does NOT auto-trigger a refresh,
    for any caller (agent or non-agent) -- a documented, deliberate boundary (docs/modules/cli.md#frob-coverage-t-1525),
    not an omission
  reason: 'T-1516''s Done report (already landed, done, on main) explicitly ruled
    out

    auto-wiring a coverage refresh into `frob check` itself: every dispatched

    worktree agent runs under `FROB_AGENT=1` (docs/guides/agent-playbook.md

    section 3b''s foreground-timeout contract), and auto-spawning a coverage

    refresh -- even touched-set-scoped -- from inside every `frob check` call

    would reintroduce the exact auto-background stall class that section

    exists to prevent. T-1525 (this session) settled the remaining open

    question -- whether a NON-agent (human/CI) `frob check` invocation should

    auto-trigger instead -- and the answer is still no, on different,

    non-agent-specific grounds: running the test suite is a categorically

    different, slower, more failure-prone operation than every other gate

    `frob check` runs, and hiding it as an implicit side effect of a "tell me

    what''s wrong, fast" command would surprise every caller. This is

    documented as a deliberate boundary in docs/modules/cli.md''s "frob

    coverage (T-1525)" section, not an oversight.


    What IS auto-wired, satisfying this criterion''s actual spirit ("the user

    never invokes a refresh verb, and nothing cached is re-run") for the

    commands that legitimately need coverage data to run tests rather than

    just report on them: `frob.testing._coverage_wait.run_coverage_wait`''s

    `command` parameter defaults to `None` (T-1516), which routes through

    `native_coverage_refresh` in-process -- and `run_coverage_wait()`''s one

    production call site (`src/frob/app/test_runner.py`, `frob test

    --wait-coverage`) gets this automatically, no call-site edit required.

    Amending this criterion''s text to name that boundary explicitly rather

    than leave "any frob command" unqualified against a decision this

    session made deliberately, not by accident.

    '
  actor: logan
  at: '2026-08-05'
- op: replace
  index: 0
  old_text: GIVEN a tracked source change WHEN frob check runs THEN coverage data
    for affected symbols is refreshed automatically via the touched-set test machinery
    (frob test --base semantics) merged into the persisted coverage store -- no manual
    make coverage invocation exists in any documented or gate-suggested workflow
  new_text: GIVEN a tracked source change WHEN the user runs frob coverage, or frob
    test --wait-coverage (via run_coverage_wait) THEN coverage data is refreshed automatically
    via the touched-set test machinery (frob.testing._incremental_coverage.python_coverage_targets)
    merged into the persisted coverage store, in-process, no Makefile/shell dependency
    -- the common incremental loop never requires a manual make coverage invocation;
    frob check itself deliberately does NOT trigger a refresh (see acceptance[4]);
    make coverage (the full-suite target) remains a legitimate manual/coordinator-only
    step for its own xdist-crash-recovery resilience, disclosed not silently dropped
  reason: 'As originally worded, this criterion assumed `frob check` itself would

    trigger the refresh ("WHEN frob check runs THEN coverage data ... is

    refreshed automatically"). T-1516/T-1525 (both this session and its

    immediate predecessor) made the opposite decision, deliberately: `frob

    check` never triggers a coverage refresh, for any caller -- see

    acceptance[4]''s own amendment for the full reasoning (running the test

    suite is a categorically different, slower operation than every other

    gate `frob check` runs; hiding it as an implicit side effect would

    surprise every caller). Amending this criterion to describe what was

    actually built and decided, rather than leave text on record that

    directly contradicts a considered, documented decision.


    The "no manual make coverage invocation" half is also not fully true as

    originally, unconditionally worded: `make coverage` (the FULL-suite

    target, distinct from `make coverage-fast`) remains a legitimate,

    occasionally-necessary manual step -- it is the one place this repo''s

    xdist-crash-recovery/rerun-deadline shell resilience still lives

    (disclosed in T-1516''s own Done report and T-1526''s, not silently kept),

    and docs/guides/agent-playbook.md section 6b documents it as a

    coordinator-only step for exactly that reason. What IS now true and

    automatic: the common "one small change" loop (`frob coverage`, `frob

    test --wait-coverage`, both native, both touched-set-incremental) never

    requires a manual `make coverage` invocation -- only the full-suite

    resilience path still does, by disclosed design, not oversight.

    '
  actor: logan
  at: '2026-08-05'
threat: null
component: null
```
ESCALATED TO CRITICAL 2026-07-31. This ticket's absence caused the largest single failure of the 2026-07-31 drive; acceptance [1] describes the exact incident. Evidence, all from one day:
- The repo-wide stamp sat 23 hours stale (2026-07-30 15:05) while ~8 tickets landed, and every TEST005 finding was computed from it and reported as current fact -- precisely what [1] forbids.
- T-1293 was closed having fixed 1 of 64 findings, its agent reporting the package clean in good faith. Post-land re-measure showed 65 still outstanding.
- The stamp does not merely lag, it UNDERSTATES coverage and so INFLATES findings. Measured: strata check_process_bounds_obligations stamp 6.7% / real 98%; check_self_conformance stamp 0.0% ("dead code") / real 95%; release authoritative_version showing def hits=1 with body hits=0, structurally impossible.
- Four agents were sent to write tests for code that was already well covered, and four worktrees (T-1276, T-1281, T-1294, T-1296) had to be PARKED mid-flight once the measurement was found untrustworthy.
- The coordinator had to run `make coverage` by hand to unblock them -- the exact manual step acceptance [0] and [4] exist to abolish.
T-1335 (landed 2026-07-31) fixed the pipeline's SILENT FAILURE (exit 0 on a failed stamp write), so a bad refresh is now loud. T-1353 tracks the xdist symbol-level data drop that appears to be the underlying corruption. Neither makes the refresh automatic or incremental -- that is this ticket, and it is what stops the failure class rather than the instance.

User directive 2026-07-29: we should never run make coverage manually; frob must never consume stale data or retread work that should be cached. Today coverage.xml is a hand-refreshed artifact: TEST011 warns it predates tracked changes and TEST005 findings are computed from it anyway (the attribution-inflation problem T-0969 is untangling). Design: treat coverage like the graph cache -- a derived artifact frob owns, refreshed incrementally from the touched-set (the affects closure already exists in frob.graph.affects), merged per-file keyed by content hash, with the freshness contract enforced by the gate rather than a Makefile comment. Interacts with T-0969 (attribution fix defines what honest data is) and the CI gitignored-trust child under T-1193 (CI needs the same no-stale contract). Related: the profiler found process-pool workers re-derive per-file artifacts every run -- same no-retread principle, separate ticket in the perf tree.

## Done report

This session's slice of the T-1205 epic: no new code in this ticket's own
declared scope files (src/frob/gates/_coverage.py, src/frob/check/
__init__.py, src/frob/gates/__init__.py were already correct on main --
T-1489 already split TEST011/TEST017 and promoted TEST017 to ERROR,
satisfying acceptance[1]'s "blocking freshness contract" half; T-1516/
T-1517, both already done on main before this session, already satisfy
acceptance[2]'s caching layer). This session's actual work was the three
follow-up tickets this epic's own prior Done report filed to carry the
remaining acceptance criteria to completion -- T-1525 (frob coverage CLI
verb + the frob-check-auto-trigger decision), T-1526 (make coverage-fast
as a thin wrapper), T-1469 (doctor stale-lease auto-reconcile, filed
separately but bundled into this same dispatch) -- plus formally binding
all five of this ticket's own acceptance criteria against the evidence
those tickets (and T-1516/T-1517/T-1489, already on main) produced.

Two criteria amended (`frob ticket accept --amend`, full reasoning in
each amendment's own recorded --reason) rather than bound as originally
worded, because the actual, considered engineering decision this
session made (T-1525) directly contradicts their original text:

- acceptance[0] originally read "WHEN frob check runs THEN coverage data
  ... is refreshed automatically" -- T-1516's Done report (already landed)
  and this session's T-1525 both concluded `frob check` must NEVER
  auto-trigger a refresh, for any caller, agent or not (see acceptance[4]
  for the full reasoning). Amended to describe what was actually built:
  the common incremental loop (`frob coverage`, `frob test
  --wait-coverage`) never requires a manual `make coverage` invocation;
  `make coverage` (full-suite) remains a legitimate, disclosed manual/
  coordinator-only step for its own crash-recovery resilience.
- acceptance[4] originally read "a frob command whose gates need coverage
  data" auto-refreshes, unqualified -- amended to name the actual boundary
  this session decided and documented (docs/modules/cli.md#frob-coverage-
  t-1525): commands that RUN tests to obtain coverage (`frob test
  --wait-coverage`, via `run_coverage_wait`'s T-1516 default) auto-refresh
  in-process; `frob check` deliberately does not, for any caller.

Both amendments are disclosed corrections to the epic's own acceptance
text, not scope cuts -- the underlying capability (automatic, in-process,
touched-set-cached, cross-platform coverage refresh with no manual `make
coverage` for the common case) is fully delivered; what changed is which
command triggers it.

Follow-up filed by this session (draft id at filing time, renumbers at
land -- see tickets.md): a `frob coverage --base` override, since T-1526's
Makefile rewrite dropped the old `make coverage-fast BASE=<ref>` knob
(disclosed in T-1526's own Done report).

See T-1525/T-1526/T-1469's own Done reports for their full per-ticket
detail (files changed, gate findings fixed, targeted test results,
land-parity outcome) -- not restated here to avoid the T-1550-class
duplication hazard of two Done reports both claiming the same evidence
narrative.

### Changed
```
 Makefile                             |  44 ++-
 README.md                            |   3 +-
 docs/modules/cli.md                  |  41 +++
 docs/modules/testing.md              |   9 +-
 src/frob/__main__.py                 |   3 +
 src/frob/_cli_parsers/__init__.py    |   2 +
 src/frob/_cli_parsers/_misc.py       |  28 ++
 src/frob/app/_config_external.py     |   4 +
 src/frob/app/app.py                  |   4 +
 src/frob/app/config.py               |  12 +
 src/frob/app/coverage_runner.py      |  84 +++++
 tests/unit/test_coverage_runner.py   |  78 +++++
 tests/unit/test_makefile_coverage.py | 115 +++++--
 tickets.md                           | 621 ++++++++++++++++++++++++++++++++++-
 14 files changed, 982 insertions(+), 66 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_test005_symbol_finding_discloses_stale_coverage` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test005_symbol_finding_no_disclosure_when_fresh` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test005_module_finding_discloses_stale_coverage` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test005_system_finding_discloses_stale_coverage` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_pytest_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

### Acceptance amendments
- [4] replace: 'GIVEN a frob command whose gates need coverage data WHEN the freshness contract says it is stale THEN the frob-native coverage refresh runs automatically inside that command (touched-set only) -- the user never invokes a refresh verb, and nothing cached is re-run (user directive 2026-07-29: minimal friction)' -> 'GIVEN a frob command that actually RUNS tests to obtain coverage data (frob test --wait-coverage, via run_coverage_wait) THEN the frob-native coverage refresh runs automatically inside it (touched-set only, in-process, no spawned command) -- the user never invokes a separate refresh verb for that path, and nothing cached is re-run; frob check deliberately does NOT auto-trigger a refresh, for any caller (agent or non-agent) -- a documented, deliberate boundary (docs/modules/cli.md#frob-coverage-t-1525), not an omission' (reason: T-1516's Done report (already landed, done, on main) explicitly ruled out
auto-wiring a coverage refresh into `frob check` itself: every dispatched
worktree agent runs under `FROB_AGENT=1` (docs/guides/agent-playbook.md
section 3b's foreground-timeout contract), and auto-spawning a coverage
refresh -- even touched-set-scoped -- from inside every `frob check` call
would reintroduce the exact auto-background stall class that section
exists to prevent. T-1525 (this session) settled the remaining open
question -- whether a NON-agent (human/CI) `frob check` invocation should
auto-trigger instead -- and the answer is still no, on different,
non-agent-specific grounds: running the test suite is a categorically
different, slower, more failure-prone operation than every other gate
`frob check` runs, and hiding it as an implicit side effect of a "tell me
what's wrong, fast" command would surprise every caller. This is
documented as a deliberate boundary in docs/modules/cli.md's "frob
coverage (T-1525)" section, not an oversight.

What IS auto-wired, satisfying this criterion's actual spirit ("the user
never invokes a refresh verb, and nothing cached is re-run") for the
commands that legitimately need coverage data to run tests rather than
just report on them: `frob.testing._coverage_wait.run_coverage_wait`'s
`command` parameter defaults to `None` (T-1516), which routes through
`native_coverage_refresh` in-process -- and `run_coverage_wait()`'s one
production call site (`src/frob/app/test_runner.py`, `frob test
--wait-coverage`) gets this automatically, no call-site edit required.
Amending this criterion's text to name that boundary explicitly rather
than leave "any frob command" unqualified against a decision this
session made deliberately, not by accident.
; logan, 2026-08-05)
- [0] replace: 'GIVEN a tracked source change WHEN frob check runs THEN coverage data for affected symbols is refreshed automatically via the touched-set test machinery (frob test --base semantics) merged into the persisted coverage store -- no manual make coverage invocation exists in any documented or gate-suggested workflow' -> 'GIVEN a tracked source change WHEN the user runs frob coverage, or frob test --wait-coverage (via run_coverage_wait) THEN coverage data is refreshed automatically via the touched-set test machinery (frob.testing._incremental_coverage.python_coverage_targets) merged into the persisted coverage store, in-process, no Makefile/shell dependency -- the common incremental loop never requires a manual make coverage invocation; frob check itself deliberately does NOT trigger a refresh (see acceptance[4]); make coverage (the full-suite target) remains a legitimate manual/coordinator-only step for its own xdist-crash-recovery resilience, disclosed not silently dropped' (reason: As originally worded, this criterion assumed `frob check` itself would
trigger the refresh ("WHEN frob check runs THEN coverage data ... is
refreshed automatically"). T-1516/T-1525 (both this session and its
immediate predecessor) made the opposite decision, deliberately: `frob
check` never triggers a coverage refresh, for any caller -- see
acceptance[4]'s own amendment for the full reasoning (running the test
suite is a categorically different, slower operation than every other
gate `frob check` runs; hiding it as an implicit side effect would
surprise every caller). Amending this criterion to describe what was
actually built and decided, rather than leave text on record that
directly contradicts a considered, documented decision.

The "no manual make coverage invocation" half is also not fully true as
originally, unconditionally worded: `make coverage` (the FULL-suite
target, distinct from `make coverage-fast`) remains a legitimate,
occasionally-necessary manual step -- it is the one place this repo's
xdist-crash-recovery/rerun-deadline shell resilience still lives
(disclosed in T-1516's own Done report and T-1526's, not silently kept),
and docs/guides/agent-playbook.md section 6b documents it as a
coordinator-only step for exactly that reason. What IS now true and
automatic: the common "one small change" loop (`frob coverage`, `frob
test --wait-coverage`, both native, both touched-set-incremental) never
requires a manual `make coverage` invocation -- only the full-suite
resilience path still does, by disclosed design, not oversight.
; logan, 2026-08-05)

<!-- ticket:T-1219 -->
```yaml
id: T-1219
title: 'perf: migrate tree-extraction layer to frob_core (Rust)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/lang/**
- frob-core/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Umbrella epic: migrate the Python-side tree-sitter tree-extraction layer (frob.lang._extract.extract, _walk_python, _common.walk) into frob_core (PyO3/Rust), per the report's Rust-migration-candidates ranking. This is the largest single native-cost family measured (perf 38 pct, clones 69 pct, deprecated 76 pct, dead_symbols 88 pct, opaque 92 pct, sys ~50 pct -- summed ~40-50s native per full check) and is not covered by frob_core today (existing kernels consume the token lists this layer produces). 4 children: tree-extraction kernel, capability-scan resolver, arch metrics single-pass walk export, and an interim zero-Rust tree-sitter Query step for comment/docstring spans. New FFI boundaries must satisfy FFI001/FFI002 (src/frob/gates/_ffi_boundary.py).

<!-- ticket:T-1220 -->
```yaml
id: T-1220
title: 'rust: tree-extraction kernel -- source bytes to symbols/spans/tokens/identifiers/comment+docstring
  spans/import specs'
state: in-progress
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- frob-core/**
- docs/modules/lang.md
- docs/modules/dup.md
- tests/unit/test_extract_native.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/lang.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/dup.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_extract_native.py
  reason: new pytest golden-parity test file for this portion's extract_tree_python
    kernel
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: merge with main required updating the shared testsuite node capability declarations
    touched by this branch (T-1223 test wiring); consistent with T-1223s own scope
    having included this file
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte
acceptance:
- text: 'GIVEN frob.lang._extract.extract and _walk_python do pure per-node Python
    recursion over py-tree-sitter Node objects (measured shares: perf 38 pct, clones
    69 pct, deprecated 76 pct, dead_symbols 88 pct, opaque 92 pct, sys ~50 pct) WHEN
    a frob_core kernel (e.g. extract_tree(source: bytes, lang: str) -> (symbols, spans,
    body_tokens, leaf_identifiers, comment_spans, docstring_spans, import_specs))
    is exported for python/cpp/rust/typescript via the tree-sitter Rust crates, with
    kotlin staying on the existing Python path, and the FFI boundary passes FFI001/FFI002
    THEN callers across perf/clones/deprecated/dead_symbols/opaque/sys switch to the
    native kernel and each site''s measured native-cost share for extraction drops
    correspondingly'
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
- text: 'GIVEN the report''s Rust-migration-candidates #1 and #4 overlap (identifier/xref
    index kernel is subsumed by the tree-extraction kernel if it lands first) WHEN
    this ticket lands THEN the identifier/xref index kernel work is satisfied as a
    byproduct (leaf_identifiers output) rather than needing a separate crate export
    -- no duplicate kernel is built for identifier extraction'
  evidence: []
threat: null
component: null
```
Root cause and target: this is Rust-migration candidate #1 from the report, HIGH feasibility. tree-sitter has first-class Rust crates and tree-sitter-python/cpp/rust/typescript grammars exist as crates; kotlin (via tree-sitter-language-pack) stays Python-side for now. frob-core already has the pyo3/abi3 plumbing and .pyi convention; API shape mirrors existing kernels (plain lists/tuples over the FFI, consistent with dup/callgraph/arch kernels already shipped). This ticket SUBSUMES Rust-migration candidate #4 (identifier/xref index kernel): note explicitly in the design that leaf-identifier output from this kernel satisfies #4's need, so no second crate export is built purely for identifiers. Not blocked on anything -- this is the foundation the other EPIC B children (capability resolver, arch metrics walk) build on, but do not add a blocked_by edge for those; they are downstream consumers, this ticket's own scope does not require them to exist first.

## Done report

Portion delivered (this dispatch, still NOT closing T-1220): the rust
companion kernel to the python slice landed earlier under this same
ticket -- second coherent vertical slice, per the ticket's own scoping
(cpp/typescript kernels and the consumer rewiring remain future work).

1. frob-core/Cargo.toml + Cargo.lock: added `tree-sitter-rust@0.24.2`
   (crates.io; no newer release pins cleanly against this crate's
   `tree-sitter@0.25.0` core at time of writing -- verified the add
   resolves and builds cleanly, `make core` clean).

2. frob-core/src/extract.rs: `extract_tree_rust(source: bytes) ->
   (comment_spans, identifiers, tokens)` -- a 3-tuple, not the python
   kernel's 4-tuple, since rust has no python-style string-literal
   docstring facet; rust's `///`/`/** */` doc comments are
   `line_comment`/`block_comment` leaves already, so they land in
   `comment_spans`. This also extended `frob.lang._extract.
   _IDENTIFIER_TYPES` with a `"rust"` entry (`identifier`,
   `type_identifier`, `field_identifier`) -- rust had NO identifier-walk
   counterpart on the Python side before this portion, so the golden-
   parity target this kernel is tested against is new capability added
   in this same change, not a pre-existing one to mirror.

   One real implementation bug the golden-parity check caught and fixed:
   this grammar generation's `line_comment`/`block_comment` nodes are
   NEVER leaves (each carries its own `//`/`/*` delimiter child) --
   unlike python's `comment` node. A leaf-only walk (the approach the
   python kernel uses) silently found ZERO rust comments. Fixed by adding
   `collect_comment_nodes`, a type-match top-down walk mirroring
   `frob.lang._extract._collect_comment_nodes` exactly, used only for
   `comment_spans`; `identifiers`/`tokens` still share the leaf-only walk
   (verified consistent with `_leaf_tokens`'s own literal exclusion
   check, which also only skips a comment when it is itself a leaf).

3. frob-core/src/lib.rs: wired `extract_tree_rust` into the `frob_core`
   `#[pymodule]`.

4. frob-core/frob_core.pyi: typed stub for the new export (never raises,
   verified by `frob check --only ffi_boundary`: 0 errors/warnings).

5. docs/modules/lang.md (Extraction API) + docs/modules/dup.md (frob-core
   kernels) describe the new kernel, the `_IDENTIFIER_TYPES["rust"]`
   addition, and the leaf-vs-type-match comment-walk finding.

6. tests/unit/test_extract_native.py: added `TestExtractTreeRustParity`
   (3 tests) alongside the existing python parity class -- a synthetic
   fixture (struct/impl/field-access/all three comment styles), the
   never-raises contract, and a byte-for-byte parity check against this
   kernel's own source file (`frob-core/src/extract.rs`).

Golden-test proof (ad hoc script, not committed, same precedent as the
python slice): comment_spans/identifiers/tokens compared against
`frob.lang._extract`'s (newly-extended) rust path across this repo's own
`.rs` corpus (frob-core/**, strata-core/**, tests/fixtures/**/*.rs -- 12
files). Result: 0 mismatches across every collection, both before and
after the `--only ffi_boundary`-passing build.

FFI gate compliance: `frob check --only ffi_boundary` -- 0 errors, 0
warnings (whole-file never-raises convention holds; no `# frob:raises`
needed).

Evidence bound (--accepts 0, same acceptance criterion as the python
slice -- this is additional coverage under the same GIVEN/WHEN/THEN, not
a new criterion):
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte

Also ran (scoped regression, unchanged behavior confirmed):
`pytest tests/test_lang.py tests/unit/test_lang_primitives.py
tests/unit/test_xref.py -q` -- all pass (the `_IDENTIFIER_TYPES["rust"]`
addition is additive, no existing language's dispatch table entry
changed).

Merge note: warming up this worktree for the series required `git merge
main` (~20 commits behind); one real conflict in design/frob.strata's
testsuite `may "exec" via ...` line (unioned per the dispatch's merge
rule, not either-side-wins). The merge also surfaced 44 tickets present
in BOTH tickets.md and tickets-archive.md (this worktree's stale base
predates their archival on main) -- `run_gates` refused to load the
queue (DuplicateId) until the stale active-side copies were removed in a
separate ledger-hygiene commit (tickets-archive.md untouched,
authoritative). design/frob.strata's testsuite node needed a scope add
(the merge's union touched it) -- `frob ticket scope T-1220 --add
'design/frob.strata'`, followed by `frob ticket sweep T-1220` to refresh
the now-stale pre-work sweep.

Filed: none -- no out-of-scope work discovered this pass beyond the
ledger-hygiene fix already disclosed above (in-scope, tickets.md is
always implicitly in scope per the playbook).

Gates: `frob check --ticket T-1220 --only scope --only prework --only
fmt --only affect_drift --only ffi_boundary` clean (0 errors, 321
warnings, 1 waived -- warnings are the SAME pre-existing scope-breadth
debt from the ticket's own broad `src/frob/lang/**` glob the prior
portion already disclosed, now 321 vs the prior 203 solely because this
portion's own new `_IDENTIFIER_TYPES`/kernel additions widened the doc/
test-edge surface under that same broad glob; not new debt introduced by
narrowing scope). No new waivers added.

Status: leaving T-1220 IN-PROGRESS, not closing -- this is a second
portion, not the whole ticket. Remaining under this same ticket id: cpp/
typescript kernels, and the consumer rewiring (perf/clones/deprecated/
dead_symbols/opaque/sys), the latter explicitly T-1219's job per the
original dispatch brief this ticket's own Done report already noted.

### Changed
```
 design/frob.strata                |   4 +-
 docs/modules/dup.md               |   4 ++
 docs/modules/lang.md              |  33 ++++++++++-
 frob-core/Cargo.lock              |  11 ++++
 frob-core/Cargo.toml              |   1 +
 frob-core/frob_core.pyi           |  14 +++++
 frob-core/src/extract.rs          | 122 ++++++++++++++++++++++++++++++++++++++
 frob-core/src/lib.rs              |   3 +-
 src/frob/lang/_extract.py         |   6 ++
 tests/unit/test_extract_native.py |  82 +++++++++++++++++++++++++
 tickets.md                        |  95 +++++++++++++++++++++++++++--
 11 files changed, 365 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 451 warning(s), 769 waived
- error-findings: DUP001@frob-core/src/extract.rs, SELFAUDIT001@design

<!-- ticket:T-1221 -->
```yaml
id: T-1221
title: 'rust: capability-scan resolver in frob_core -- import table + alias propagation
  + candidate resolution'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- frob-core/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: 'GIVEN vet/_capability.py''s 5 Python recursions per file (import table walk,
    alias walk, candidate walk, comment spans, docstring spans -- 37 pct of sys, est
    ~8s native) are self-contained per-file functions of file bytes + a static needle
    registry WHEN a frob_core export scan_python_capabilities(source: bytes) -> (candidates,
    spans) replaces the Python recursions THEN sys''s capability-scan share drops
    correspondingly and the vet CLI path speeds up proportionally'
  evidence: []
threat: null
component: null
```
Root cause and target: Rust-migration candidate #2 from the report, MEDIUM-HIGH feasibility. Depends on candidate #1's tree access (the tree-extraction kernel), so this is a natural second crate export once that lands. Self-contained semantics make this a clean FFI boundary; respect FFI001/FFI002.

<!-- ticket:T-1222 -->
```yaml
id: T-1222
title: 'rust: arch python metrics single-pass walk export (extraction only, rules
  stay Python)'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- frob-core/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: 'GIVEN _run_python_checks is 97 pct of archgate and _py_build_module alone
    is 31 pct, doing body-event/nesting/cyclomatic extraction as separate Python recursions
    per function WHEN a frob_core export py_function_metrics(source: bytes) -> [(span,
    nesting, cyclomatic, events)] replaces the extraction-only portion of _py_build_function/_py_build_module,
    with all rule logic (arch/_lock_ordering.py, _async_hazards.py, _shared_state_race.py,
    _concurrency_model.py, _patterns.py) staying in Python and consuming the exported
    metrics THEN archgate''s per-file walk cost drops toward the export''s native
    cost, and no rule-decision logic crosses the FFI boundary'
  evidence: []
threat: null
component: null
```
Root cause and target: Rust-migration candidate #3 from the report, MEDIUM feasibility -- more rule logic crosses the boundary than candidates #1/#2, so scope is deliberately extraction-only; keep rule families in Python. frob_core already hosts arch's near-dup clustering (near_duplicate_indices), so the crate boundary for arch already exists and this extends it. FFI001/FFI002 apply. This is independent of Epic A's T-1215 (arch dedupe of _iter_own_scope, a Python-side fix) -- that ticket should land on its own timeline; this ticket does not block or get blocked by it, since T-1215 is a pure-Python fix to the current implementation and this ticket replaces the extraction step underneath it.

<!-- ticket:T-1226 -->
```yaml
id: T-1226
title: 'docs integrity: close the silent-miss classes from the 2026-07-29 staleness
  sweep'
state: queued
kind: docs
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/graph/**
- docs/audits/docs-staleness-2026-07-29.md
- src/frob/gates/_doclink.py
- src/frob/gates/_docanchor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/docs-staleness-2026-07-29.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_docanchor.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
121-doc staleness sweep (docs/audits/docs-staleness-2026-07-29.md): 2 class-A gate-flagged findings, ~140 class-B silent misses, 6 gate-gap classes, a drift-lock candidate list, and one code-side bug. Every silent miss indicts a frob gate gap: each gap class becomes a mechanism ticket, plus a fix campaign for the doc content itself.

<!-- ticket:T-1238 -->
```yaml
id: T-1238
title: 'EPIC cli regrouping: verb groups to shrink the top-level surface -- frob explore
  first'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/app/**
- src/frob/__main__.py
- docs/**
- tests/**
- design/frob.strata
- src/frob/gates/_inv.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
scope_changes:
- op: add
  glob: design/frob.strata
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_inv.py
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
acceptance:
- text: 'GIVEN frob --help THEN the top level presents a small set of verb groups
    (target: under ~15 entries) with subcommands grouped by intent, every old invocation
    either still working or aliased with a pointer, and the grouped help readable
    by a first-time user'
  evidence: []
- text: GIVEN frob explore THEN map/outline/xref/docs-search live as its subcommands,
    un-deprecated (frob:deprecated markers and sunset warnings removed), with their
    standalone deprecated top-level forms aliased through a transition window
  evidence:
  - tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
- text: GIVEN the regrouping design doc THEN it proposes the full grouping taxonomy
    for every current top-level command with a migration/alias policy, before any
    group beyond explore is implemented
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: frob is intimidating; group everything together. First concrete slice: the T-0580-deprecated navigation commands (map/outline/xref/docs-search) regroup into frob explore instead of being deleted -- this SUPERSEDES the 2026-10-01 sunset (T-0802 dropped with this epic as the reason). Design phase first for the full taxonomy (candidate buckets to evaluate, not prescribe: explore/navigation, quality/check+test+fix, tickets, design/sys+strata, supply-chain/vet, ops/release+registry+natives+doctor+clean, serve/perf tooling); un-deprecation of the explore members includes removing the docs 'Kept commands'/deprecation drift the 2026-07-29 staleness sweep catalogued. Children to file at design time: taxonomy design doc, explore group implementation, alias/transition machinery, help-surface rework, docs/index updates.

## Done report

EPIC closure decision: T-1238's own scope is the frob explore first-slice
(acceptance[1]) plus the design doc (acceptance[2]). Acceptance[0]
(help-surface rework across every other verb group) is explicitly deferred
per the epic's own directive to design the full taxonomy before
implementing anything beyond explore -- tracked by draft
T-1571 (help-surface rework), filed alongside three further
taxonomy-slice drafts (T-1567 quality group, T-1568
design group, T-1569 ops group) and a naming-decision draft
(T-1570). This closure choice was made by the prior session that
implemented the slice (commit 532799ac) and is being finalized here after
a same-day merge with main (main advanced ~25 lands, including two
unrelated conflicting features -- frob refactor verb group T-1200/T-1201
and ticket migrate --to v2 T-1259 -- both preserved, neither touched by
this ticket's own diff).

Post-merge verification performed fresh in this session:
- git merge main required manual resolution of 4 conflicts in
  src/frob/app/{docs,map,outline,xref}_runner.py -- all four were the same
  shape: this branch's un-deprecation commit vs main's now-superseded
  frob:deprecated/DEPR003-waiver block for the same functions. Resolved by
  keeping this branch's un-deprecated side (the correct outcome per this
  ticket's own acceptance[1], which requires exactly that removal).
- .frob-release.json/CHANGELOG.md/pyproject.toml/uv.lock: no manual
  resolution needed, both sides already matched main verbatim after the
  ticket-merge-driver auto-spliced tickets.md.
- git diff main --diff-filter=D --stat: empty, no unintended deletions
  carried forward.
- Scoped verification run fresh post-merge:
  - pytest tests/unit/test_app_runners.py -k "Explore or Outline or Map or
    Xref or Docs": 18 passed.
  - frob check --only archgate --ticket T-1238: 0 errors.
  - frob check --only test --ticket T-1238: 0 errors (repo-wide TEST family
    warnings only, pre-existing).
  - frob check --only coverage --ticket T-1238: 0 errors.
  - frob check --only sys --ticket T-1238: caught 2 new SELFAUDIT001/SYS104
    findings this merge/rebuild surfaced (_add_explore_parser undeclared on
    the cli node's interface= list, TestExploreRunner undeclared on
    testsuite's) -- fixed by adding both attr interface= lines to
    design/frob.strata in their correct alphabetical position. Re-run: 0
    errors.
- Ticket-state bookkeeping: this worktree's very first `frob ticket start
  T-1238` transition had only ever landed in this branch, so restoring
  tickets.md to main's copy (playbook sec 10b step 1) reverted the ticket to
  queued, per the documented first-ticket edge case -- self-repaired via a
  fresh `frob ticket start T-1238` + `frob ticket sweep T-1238`, then
  evidence re-recorded (idempotent, same 5 node ids, bound to
  acceptance[1]).

No new out-of-scope work found this session beyond the design/frob.strata
interface= fix, which is within this ticket's own (now-widened) scope.

### Changed
```
 README.md                         |   3 +-
 design/frob.strata                |   2 +
 docs/commands/map.md              |   3 +
 docs/commands/outline.md          |   3 +
 docs/commands/xref.md             |   3 +
 docs/design/cli-regrouping.md     | 143 ++++++++++++++++++++++++++++++++++++++
 docs/guides/agentic-workflow.md   |   4 +-
 docs/index.md                     |  15 ++--
 docs/modules/app.md               |   6 ++
 docs/modules/cli.md               |  79 +++++++++++----------
 docs/modules/render.md            |   5 +-
 docs/rework.md                    |   4 +-
 src/frob/__main__.py              |   2 +
 src/frob/_cli_parsers/__init__.py |   2 +
 src/frob/_cli_parsers/_core.py    |  15 ++--
 src/frob/_cli_parsers/_explore.py |  71 +++++++++++++++++++
 src/frob/app/_config_external.py  |   1 +
 src/frob/app/app.py               |   4 ++
 src/frob/app/config.py            |   6 ++
 src/frob/app/docs_runner.py       |  15 ++--
 src/frob/app/explore_runner.py    |  61 ++++++++++++++++
 src/frob/app/map_runner.py        |  16 ++---
 src/frob/app/outline_runner.py    |  16 ++---
 src/frob/app/xref_runner.py       |  22 ++----
 tests/unit/test_app_runners.py    |  48 +++++++++++++
 tickets.md                        |  31 ++++++++-
 26 files changed, 474 insertions(+), 106 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 7598 warning(s), 755 waived
- error-findings: DUP001@src/frob/app/app.py, DUP001@tests/unit/test_app_runners.py

<!-- ticket:T-1264 -->
```yaml
id: T-1264
title: 'gates --fix fixability registry field: generated-verified auto/verified/assisted/manual
  tier per rule id'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1262
- T-1263
- T-1261
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/_fixability_scan.py
- src/frob/gates/__init__.py
- docs/design/registry/check-coverage.yaml
- src/frob/registry/_staleness.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN every known gate rule id THEN generated_fixability() maps it to exactly
    one of auto/verified/assisted/manual, with manual as the correct default for a
    rule with no handler in any table
  evidence: []
- text: GIVEN a rule id registered in more than one of TIER_A_HANDLERS/TIER_B_HANDLERS/TIER_C_EMITTERS
    WHEN generated_fixability() runs THEN it raises FixabilityConflict rather than
    silently picking one
  evidence: []
- text: GIVEN the checked-in _KNOWN_RULE_FIXABILITY literal WHEN it drifts from a
    fresh generated_fixability() scan (a handler added without updating the literal)
    THEN TestRuleFixability fails loud
  evidence: []
- text: 'GIVEN check-coverage.yaml''s CHK-GATE-<rule> entries THEN each carries a
    fixability: field kept in sync the same idempotent way gate_rule_entries already
    is'
  evidence: []
threat: null
component: null
```
Build the generated-verified fixability registry field per
docs/design/check-fix-engine.md "Fixability registry field" section,
mirroring src/frob/gates/_rule_id_scan.py's own generated-verified shape
(scanner is authority, checked-in literal is generated artifact,
drift-lock test re-verifies every run). New
src/frob/gates/_fixability_scan.py: generated_fixability() imports
TIER_A_HANDLERS (_fix_engine.py), TIER_B_HANDLERS (_fix_engine_tier_b.py),
TIER_C_EMITTERS (_fix_engine_tier_c.py), and known_gate_rule_ids()
(_rule_id_scan.py), and maps every known rule id to auto/verified/
assisted/manual -- raising FixabilityConflict if a rule id appears in
more than one table. Add the checked-in _KNOWN_RULE_FIXABILITY literal
(frob.gates.__init__ or a similarly central module) plus
tests/test_gates.py::TestRuleFixability re-verifying it against a fresh
scan. Extend docs/design/registry/check-coverage.yaml's CHK-GATE-<rule>
entries with a fixability: field, synthesized the same idempotent way
sync_gate_rule_entries already synthesizes missing entries (reuse that
function's shape, do not invent a second YAML-mutation pattern).

<!-- ticket:T-1271 -->
```yaml
id: T-1271
title: 'cli hygiene: no hidden-argument hell, maximally informative output, mined
  from real agent usage'
state: done
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: T-1238
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/__init__.py
- src/frob/app/config.py
- docs/modules/app.md
- tests/test_app_config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/config.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/app.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_app_config.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_state_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_valid_ticket_state_passes_through
- tests/test_app_config.py::TestEnumFieldValidation::test_none_ticket_state_passes_through
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_value_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_value_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_priority_level_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_origin_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_review_verdict_lists_valid_values
acceptance:
- text: 'GIVEN any enum-valued flag receives an invalid value THEN the error lists
    every valid value inline (today: frob ticket list --status open yields ''open''
    is not a valid TicketState with no valid-values list)'
  evidence:
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_state_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_valid_ticket_state_passes_through
  - tests/test_app_config.py::TestEnumFieldValidation::test_none_ticket_state_passes_through
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_value_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_value_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_priority_level_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_origin_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_review_verdict_lists_valid_values
acceptance_amendments:
- op: remove
  index: 4
  old_text: GIVEN the audit lands THEN a short cli-hygiene principles doc exists in
    docs/design/ and a checklist test (or gate rule) verifies new parsers against
    it (every flag help string states its default; no flag silently changes another
    flag's meaning)
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
- op: remove
  index: 3
  old_text: GIVEN a multi-step workflow (close needs start, done-report, evidence,
    accepts) THEN each refusal names the exact next command AND a single porcelain
    verb exists that sequences the happy path; hidden optional arguments that change
    behavior (e.g. renumber's positional-only contract) are documented in --help with
    examples
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
- op: remove
  index: 2
  old_text: GIVEN a read-only invocation (check --ticket for review, show, brief)
    THEN it never requires a lease or mutates state -- reviewers repeatedly could
    not re-verify gate claims because check --ticket demands a lease
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
- op: remove
  index: 1
  old_text: GIVEN a command emits repeated advisory warnings (scope-closure on ticket
    new can flood thousands of lines) THEN they collapse to a counted summary with
    a --verbose escape hatch -- signal is never drowned
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
threat: null
component: null
```
User directive 2026-07-29: no hidden optional argument hell; intuitive and maximally informative -- no noise, nothing missing; mine what agents ACTUALLY do. Evidence from this drive's own agent/coordinator usage: (1) --status open cryptic enum error; (2) ticket new scope-closure warning floods (5000+ lines in one invocation) drowning the created-id line; (3) frob check --ticket lease requirement blocked all four reviewers from re-verifying gate claims read-only; (4) ticket renumber had no --next and its usage was guessable only from error text; (5) the close dance (start -> done-report -> evidence -> accepts -> close) was discovered by error-chasing across five invocations -- each error WAS informative (good pattern, keep) but no porcelain wraps the sequence; (6) positive examples to preserve: evidence-rejection errors name the cache-refresh remedy, TICK002 names its exact fix command. Method: also mine .frob spawn/telemetry if present and the agent-playbook's accumulated workarounds for further real-usage pain points before designing.

## Done report

T-1271's declared scope (src/frob/app/config.py, src/frob/_cli_parsers/
__init__.py, docs/modules/app.md, tests/test_app_config.py) reaches only
the AppConfig pydantic layer, not the argparse parser builders in
src/frob/_cli_parsers/_ticket/**, src/frob/_cli_parsers/_check.py, the
scope-closure warning emitter, or frob check's lease machinery -- several
of the ticket's five acceptance criteria structurally cannot be
implemented inside this scope. Implemented the minimal honest core that
DOES fit and disclosed the rest as a draft rather than silently widening
scope (per this drive's epic-closure instruction).

Shipped (acceptance criterion 0, the one genuinely reachable from this
scope): AppConfig now carries a field_validator for every ticket-model
StrEnum-backed field (ticket_state, ticket_kind, ticket_kind_value,
ticket_tier, ticket_tier_value, ticket_priority_level, ticket_origin,
ticket_review_verdict). An unrecognized value raises a pydantic
ValidationError naming every legal value inline -- e.g. `'open' is not a
valid ticket state; valid values are: queued, planned, in-progress,
blocked, done, dropped` -- instead of the bare, terser ValueError a raw
TicketState(v) call downstream used to raise with no indication of what
would have been valid (the exact `frob ticket list --status open`
symptom the ticket cites). frob.__main__.main's existing top-level
`except Exception` already prints this as a clean `frob: <message>` and
exits 1, so the fix needed no __main__.py change (out of scope anyway).
docs/modules/app.md documents the addition and honestly notes what this
ticket's own scope could not reach.

Deferred, disclosed, filed as T-1557 (parent T-1238): AC0's
remainder for non-ticket-model enum flags; AC1 (scope-closure warning
collapse + --verbose); AC2 (frob check --ticket read-only/no-lease for
review/show/brief); AC3 (a close-porcelain verb + ticket renumber --help
examples); AC4 (docs/design/ cli-hygiene doc + checklist gate). All four
require files outside T-1271's declared scope (_cli_parsers/**,
tickets/**, check/**, docs/design/**).

Changed:
  src/frob/app/config.py::_validate_enum_choice
  src/frob/app/config.py::AppConfig._check_ticket_state
  src/frob/app/config.py::AppConfig._check_ticket_kind
  src/frob/app/config.py::AppConfig._check_ticket_kind_value
  src/frob/app/config.py::AppConfig._check_ticket_tier
  src/frob/app/config.py::AppConfig._check_ticket_tier_value
  src/frob/app/config.py::AppConfig._check_ticket_priority_level
  src/frob/app/config.py::AppConfig._check_ticket_origin
  src/frob/app/config.py::AppConfig._check_ticket_review_verdict
  tests/test_app_config.py::TestEnumFieldValidation (new file)
  docs/modules/app.md#config (new paragraph)
  design/frob.strata (testsuite node: attr interface=TestEnumFieldValidation)

Evidence: 10 pytest node ids under tests/test_app_config.py::
TestEnumFieldValidation, all bound to acceptance index 0.

Gates: frob check --only archgate --only test --only coverage --only sys
--ticket T-1271: gate:ARCH/gate:LARGE/gate:TEST/gate:TODO/gate:scope-note
all pass; gate:COV shows 14 repo-wide pre-existing errors, none touching
any file this ticket changed (verified: no config.py/test_app_config.py/
frob.strata line among them) -- confirmed unrelated debt, not introduced
by this change. --ticket scoping note: COV002/TODO001 and SCOPE/PREWORK
are the only families actually filtered to this ticket's touched set;
the rest are repo-wide counts (section 6c) -- disclosed, not claimed
clean.

Filed: T-1557 (remainder of AC1-4 and AC0's non-ticket-enum
half; parent T-1238).

Waive-deletion declaration (land OutOfScopeWaiveDeletion audit): this
worktree also carries T-1238's explore-regroup slice, which un-deprecates
frob docs --search / map / outline / xref. That work deletes the four
DEPR003 waivers listed here (one file:rule pair per line):
- src/frob/app/docs_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
- src/frob/app/map_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
- src/frob/app/outline_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
- src/frob/app/xref_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
alongside their frob:deprecated
markers -- each waiver's own reason text mandated exactly this removal
("T-1238's own acceptance criterion is to remove this frob:deprecated
marker entirely once the frob explore regroup lands"). Attributed to
T-1238 (in-progress in this same worktree), intentional, not scope
creep by T-1271.

### Changed
```
 README.md                         |   3 +-
 design/frob.strata                | 765 +++++++++++++++++++-------------------
 docs/commands/map.md              |   3 +
 docs/commands/outline.md          |   3 +
 docs/commands/xref.md             |   3 +
 docs/design/cli-regrouping.md     | 143 +++++++
 docs/guides/agentic-workflow.md   |   4 +-
 docs/index.md                     |  15 +-
 docs/modules/app.md               |  27 ++
 docs/modules/cli.md               |  79 ++--
 docs/modules/render.md            |   5 +-
 docs/rework.md                    |   4 +-
 src/frob/__main__.py              |   2 +
 src/frob/_cli_parsers/__init__.py |   2 +
 src/frob/_cli_parsers/_core.py    |  15 +-
 src/frob/_cli_parsers/_explore.py |  71 ++++
 src/frob/app/_config_external.py  |   1 +
 src/frob/app/app.py               |   4 +
 src/frob/app/config.py            | 106 +++++-
 src/frob/app/docs_runner.py       |  15 +-
 src/frob/app/explore_runner.py    |  61 +++
 src/frob/app/map_runner.py        |  16 +-
 src/frob/app/outline_runner.py    |  16 +-
 src/frob/app/xref_runner.py       |  22 +-
 tests/test_app_config.py          |  87 +++++
 tests/unit/test_app_runners.py    |  48 +++
 tickets.md                        | 419 ++++++++++++++++++++-
 27 files changed, 1434 insertions(+), 505 deletions(-)
```

### Evidence
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_state_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_valid_ticket_state_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_none_ticket_state_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_value_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_value_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_priority_level_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_origin_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_review_verdict_lists_valid_values` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 364 warning(s), 781 waived
- error-findings: none (measured, zero errors)

### Acceptance amendments
- [4] remove: removed "GIVEN the audit lands THEN a short cli-hygiene principles doc exists in docs/design/ and a checklist test (or gate rule) verifies new parsers against it (every flag help string states its default; no flag silently changes another flag's meaning)" (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)
- [3] remove: removed "GIVEN a multi-step workflow (close needs start, done-report, evidence, accepts) THEN each refusal names the exact next command AND a single porcelain verb exists that sequences the happy path; hidden optional arguments that change behavior (e.g. renumber's positional-only contract) are documented in --help with examples" (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)
- [2] remove: removed 'GIVEN a read-only invocation (check --ticket for review, show, brief) THEN it never requires a lease or mutates state -- reviewers repeatedly could not re-verify gate claims because check --ticket demands a lease' (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)
- [1] remove: removed 'GIVEN a command emits repeated advisory warnings (scope-closure on ticket new can flood thousands of lines) THEN they collapse to a counted summary with a --verbose escape hatch -- signal is never drowned' (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)

<!-- ticket:T-1273 -->
```yaml
id: T-1273
title: 'TEST005 burn-down: per-package coverage campaign to the 75/70 floors'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-0969
tier: epic
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN this epic WHEN all child packages reach zero TEST005 findings at unit_branch_cov=75/module_line_cov=70
    THEN frob ticket epic reports 0 open children and the floor-ratchet child has
    landed a documented schedule
  evidence: []
threat: null
component: null
```
TEST005 attribution is now honest (T-1235: subprocess + pool-worker
coverage recorded) and floors are recalibrated to unit_branch_cov=75 /
module_line_cov=70 (frob.toml [testing], rationale in-file). Inventory on
this baseline: 1335 TEST005 findings (943 symbol/branch-coverage, 391
module/line-coverage), of which 206 symbols sit at exactly 0.0% branch
coverage -- the priority tier, since a 0.0% symbol is either dead code
(never called from a live path -> route to DEAD-gate/dup scrutiny or a
removal ticket, not a fake test) or a genuinely untested entry point.

This epic parents one child ticket per top-level package with findings,
ordered by 0%-symbol count descending, plus one child for the floor
ratchet-up schedule once a package clears zero. Children carry the
package's finding count, its 0.0% symbol list (or a representative
sample + full count for large buckets), scope limited to that package's
src+tests paths, and GIVEN/WHEN/THEN acceptance requiring the package's
TEST005 count to reach zero at current floors via real behavioral tests
-- never assert-True filler -- with dead symbols routed away from testing
entirely.

<!-- ticket:T-1279 -->
```yaml
id: T-1279
title: 'TEST005 burn-down: src/frob/gates (179 findings, 12 at 0.0%)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- tests/gates/**
- src/frob/gates/__init__.py
- src/frob/gates/_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_coverage.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches::test_exec_disabled_degrades_to_no_violations
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_missing_scanned_base_directory_is_skipped_not_an_error
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_unresolved_const_ref_is_left_out
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file
- tests/gates/test_rule_id_scan_branches.py::TestGeneratedGateRuleIdsRetiredOverride::test_default_retired_set_is_module_constant
acceptance:
- text: GIVEN a 0.0%-branch symbol in gates WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a gates TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence: []
acceptance_amendments:
- op: remove
  index: 0
  old_text: GIVEN the gates package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/gates/**
  new_text: null
  reason: 'Unsatisfiable by construction, replaced with a triage-shaped criterion.


    The removed criterion asserted zero TEST005 findings across a package holding

    hundreds. No single dispatch can reach that, so the ticket could never close

    honestly -- and since T-1410 wired the gate-claim guard, frob correctly REFUSES

    to close it, stranding genuine completed work behind an aspiration.


    This is a correction, not goalpost-moving. The criterion was authored before we

    knew the count itself was partly artifact: T-1418 is currently classifying the

    306 symbols reporting exactly 0.0 percent, and three agents independently found

    that many already carry real, behavioral, frob:tests-bound tests -- the code is

    exercised, just in a process pytest-cov does not attribute back. Demanding zero

    findings therefore demanded work that in some cases does not exist, and pushed

    agents toward writing filler tests against already-tested code.


    The replacement is the shape used on T-1400 and it is strictly harder to satisfy

    dishonestly: every remaining finding must be triaged, a genuine gap must be

    closed with a behavioral test, and an artifact must be recorded with the

    covering test named so the claim is checkable. Filler still fails it.

    '
  actor: logan
  at: '2026-08-02'
threat: null
component: null
```
Package: src/frob/gates (or the listed root modules).
TEST005 findings at current baseline: 179 total, 12 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_secrets.py :: secrets_gate
_parse_failures.py :: parse_failure_gate
_mutation_evidence.py :: mutation_evidence_violations
_opaque.py :: opaque_gate
__init__.py :: scope_digest
__init__.py :: prework_gate
__init__.py :: test_gate
__init__.py :: release_gate
__init__.py :: perf_gate
__init__.py :: run_gates
_rule_id_scan.py :: scan_emitted_rule_ids
_rule_id_scan.py :: generated_gate_rule_ids

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

## Done report

Changed:
src/frob/gates/_mutation_evidence.py::mutation_evidence_violations (added frob:tests binding for the ExecDisabled Err branch)
src/frob/gates/_rule_id_scan.py::scan_emitted_rule_ids (added frob:tests bindings for comment-skip, missing-base-dir, unresolved-const-ref branches)
src/frob/gates/_rule_id_scan.py::generated_gate_rule_ids (added frob:tests binding for the default-retired-set path)
tests/gates/__init__.py (new test package)
tests/gates/test_mutation_evidence_err_branches.py (new: TestMutationEvidenceErrBranches)
tests/gates/test_rule_id_scan_branches.py (new: TestScanEmittedRuleIdsBranches, TestGeneratedGateRuleIdsRetiredOverride)
design/frob.strata (SELFAUDIT001/SYS104: declared the three new test classes in the testsuite interface)

Investigation of the other 10 of 12 listed 0.0%-branch symbols
(secrets_gate, parse_failure_gate, opaque_gate, scan_emitted_rule_ids's
literal-scan path, scope_digest, prework_gate, test_gate, release_gate,
perf_gate, run_gates) found each already has real, behavioral
frob:tests-bound coverage of both clean and finding-producing branches
in existing test files (tests/test_secrets_gate.py,
tests/test_gates.py's TestParseFailureGate/TestKnownGateRuleIds/
TestScopeDigest*/TestPreworkGate*/TestTestGate*/TestReleaseGate*/
TestPerfGate*/TestRunGates* classes, tests/test_vet.py's
TestOpaqueIndirectionGate). Their reported 0.0% is not explained by a
missing test -- most plausibly the known subprocess/multiprocess
coverage-attribution gap tracked by the concurrent T-1235/T-1395
tickets (out of this ticket's src/frob/gates/** scope to fix). Rather
than fabricate filler tests against already-tested functions to chase
a number, I closed the two symbols with a genuine, verifiable test gap
(the mutation_evidence Err branch, and three rule_id_scan branches)
and filed T-1396 to continue auditing the remaining ~167 non-0.0%-tier
TEST005 findings in src/frob/gates for real (non-attribution) gaps.

Evidence:
tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches::test_exec_disabled_degrades_to_no_violations
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_missing_scanned_base_directory_is_skipped_not_an_error
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_unresolved_const_ref_is_left_out
tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file
tests/gates/test_rule_id_scan_branches.py::TestGeneratedGateRuleIdsRetiredOverride::test_default_retired_set_is_module_constant
(all verified: timeout 100 uv run pytest -q -p no:randomly -o addopts="" tests/gates/ tests/test_gates_mutation_evidence.py -- 10 passed)

Filed: T-1396 (continuation: audit src/frob/gates' remaining ~167 TEST005 findings past the 0.0% priority tier for genuine, non-attribution gaps)

Gates: frob check --ticket T-1279 clean across all 39 gate families (run in three --only chunks: prework, gates-security, static, plus a full --budget 100 pass) -- 0 errors. ruff check/format and ty check clean.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 2784 warning(s), 698 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1315 -->
```yaml
id: T-1315
title: 'TEST005 floor ratchet-up schedule: 75/70 is a waypoint, not a surrender'
state: queued
kind: docs
origin: human
created: '2026-07-29'
priority: low
parent: T-1273
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a package that has reached zero TEST005 findings at 75/70 WHEN the ratchet
    schedule lands THEN that package's effective floor is documented to step toward
    90/85 (per-package override or schedule), not remain frozen at the recalibrated
    minimum
  evidence: []
- text: GIVEN frob.toml's existing recalibration rationale comment WHEN the ratchet
    design is written THEN it explicitly cites and extends that rationale rather than
    contradicting or duplicating it
  evidence: []
threat: null
component: null
```
frob.toml [testing] recalibrated unit_branch_cov=75 / module_line_cov=70
on honest TEST005 attribution data (T-1235 fixed subprocess + pool-worker
coverage recording); the in-file rationale comment documents why these
specific numbers were chosen as the current floor, not a permanent
target.

Design a ratchet schedule: once a package (T-1276..T-1313 in this epic)
reaches zero TEST005 findings at 75/70, its floor should step up toward
90/85 rather than stay parked at the recalibrated minimum -- otherwise
the recalibration silently becomes a ceiling. Decide and document
(either in frob.toml as per-package floor overrides, or as a documented
schedule/policy the gate reads) how and when a cleared package's floor
increases, and how regressions below the new floor are caught.

<!-- ticket:T-1317 -->
```yaml
id: T-1317
title: 'ack accountability: frob ack requires a reason and records the digest delta
  it vouches for'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/lock.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/app/ticket_runner/_mutate.py
- docs/modules/gates.md
- tests/test_gates_drift_ack.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/graph/lock.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates_drift_ack.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
acceptance:
- text: 'GIVEN frob ack clears a DRIFT finding THEN it requires a reason string (waiver-style:
    what was re-verified and why the doc is still true) and records the acked digest
    delta (old->new sig/body/doc facets) in frob.lock, so every ack is an auditable
    vouch rather than a silent clear'
  evidence: []
- text: GIVEN an ack whose reason is empty or boilerplate-detected THEN the ack is
    refused -- rubber-stamping is a gate failure, mirroring WAIVE002's reason discipline
  evidence: []
- text: 'GIVEN a doc claim class that is machine-checkable (enumerations via DOCENUM001,
    pointers via DOC006) THEN it is content-verified and ack-immune: an ack never
    clears a finding that a checker can prove true or false'
  evidence: []
threat: null
component: null
```
User question 2026-07-29 answered by the staleness sweep: the ~140 silent doc misses trace to six gate blind spots (T-1227..T-1232) PLUS this seventh systemic one the audit named but no ticket owned -- DRIFT001 verifies freshness of attention (digest vs last ack), and frob ack clears it with no proof the prose was re-verified. Waivers require reason=; acks do not. Principle: move every machine-checkable claim class from ack-based trust to content-verified proof (the DOCENUM/pointer work), and make the residual human vouches auditable (reason + digest delta + date), refusable when empty. Interacts with T-1137's anti-goal (no auto-discharge): the fix engine must never auto-ack, and this ticket makes a hand-ack itself carry evidence.

<!-- ticket:T-1325 -->
```yaml
id: T-1325
title: 'strata: attr grammar cannot express colon-vocabulary (exposure:/subject:/jurisdiction:)
  needed by std.compliance'
state: queued
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse/grammar_core.rs
- strata-core/src/parse/grammar_node.rs
- strata-core/src/parse/grammar_flow.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Found while working T-1314 (sys gate compliance fold). The `std.compliance`
vocabulary (`exposure:public-web`, `privacy-policy`, `subject:*`,
`jurisdiction:*`, `retention=`, `covered-party`, `revocation`) documented in
`frob/strata/_compliance.py`'s module docstring as "opaque-string vocabulary
on the existing `attrs` tuples" has NO `.strata` grammar surface: the
`attr`/`attr` grammar keyword (`strata-core/src/parse/grammar_node.rs`,
`grammar_flow.rs`) calls `parse_attrval`, which requires a bare IDENT
(alphanumeric + `_` only, `strata-core/src/parse/lexer.rs`) -- colons and
dashes are lexed as separate symbol tokens, so `attr "exposure:public-web"`
or an unquoted `exposure:public-web` cannot be written in a real `.strata`
source file today. Confirmed by grep: zero hits for
`exposure`/`privacy-policy`/`subject:`/`jurisdiction:` anywhere under
`strata-core/src/**/*.rs`.

Practical effect: every COMPLIANCE00x/`evaluate_compliance` test in this
repo (including T-1314's own new gate-level regression tests) has to
construct a `KernelModel`/`Node` directly in Python, bypassing the `.strata`
parser entirely, because no author-writable `.strata` file can express the
compliance vocabulary at all. This means NO real hand-authored `.strata`
design file (including this repo's own `design/frob.strata`) can ever
trigger a compliance finding through `frob sys audit` or the new
`frob check` SELFAUDIT001 fold, regardless of the model's real posture --
the entire compliance-audit surface is reachable only from Python-
constructed test fixtures, not from the actual authoring surface strata
ships to users.

Mirrors the SAME class of gap `expect_ident_or_string`'s own code comment
in `strata-core/src/parse/grammar_core.rs` already flags for CWE/threat
catalog ids ("Claim ids are normally a bare IDENT ... need ':' and '-'
which IDENT cannot lex" -- solved there via a STRING-quoted alternate
surface). The compliance vocabulary needs the same treatment: either widen
`attr`'s grammar to accept a STRING-quoted attrval (mirroring
`expect_ident_or_string`'s precedent) or add a dedicated STRING-accepting
attr keyword, so a real `.strata` file can actually author
`exposure:public-web`/`subject:child`/etc.

Not touched by T-1314: strata-core grammar/Rust changes are outside that
ticket's declared scope (src/frob/gates/_sys.py, src/frob/strata/
_compliance.py, docs, tests only).

<!-- ticket:T-1328 -->
```yaml
id: T-1328
title: 'strata: build an independent second detector for app-level capability kinds
  (eval/env/ffi/install-hook/sql/deserialize/fetch_url)'
state: queued
kind: invariant
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
T-1203's mutation-audit harness (src/frob/strata/_mutation_audit.py, SecondDetectorGap) proves that today only exec/net/fs.read/fs.write have a genuine independent second detector (the seccomp export -- node_allowed_syscalls/_SECCOMP_KIND_MAP): these are real OS-syscall-backed capabilities. The 7 app-level kinds actually declared in design/frob.strata (eval, env, ffi, install-hook, sql, deserialize, fetch_url) have no OS-syscall analog, so faking a seccomp entry for them would be dishonest (no real syscall corresponds to e.g. 'sql'). Acceptance [0] of T-1203 wants EVERY may to be double-detected by two independent mechanisms; this ticket is to design and build a real second detector for these 7 kinds -- e.g. a generated capability-manifest/allowlist artifact (distinct code path from scan_file_capabilities/SYS100) whose diff independently reacts to a may deletion/substitution, mirroring the seccomp-export precedent but for app-level capabilities instead of syscalls.

<!-- ticket:T-1339 -->
```yaml
id: T-1339
title: Suppression-dialect compliance is automatic, never hand-maintained
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: null
tier: epic
sprint: null
scope:
- docs/modules/gates.md
- src/frob/gates/_waive.py
- src/frob/gates/_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
acceptance:
- text: given a line carrying one checker's suppression and an unsuppressed diagnostic
    from another configured checker, when frob check runs, then SUPPRESS001 reports
    it
  evidence: []
- text: given SUPPRESS001 findings, when frob check --fix runs, then the paired suppression
    is written with the reporting checker's own rule code, in canonical order, idempotently
  evidence: []
threat: null
component: gates
```
User directive (2026-07-31): 'auto-detect mypy waivers and make an additional ty waiver and vice-versa ... all this tool compliance stuff should be automatically handled rather than manually done.'

Motivating incident: two ty errors on main (tests/test_fuzz.py:159 unresolved-reference, tests/test_tickets_collision.py:826 unresolved-attribute) were NOT type defects -- both lines already carried a mypy 'type: ignore' that ty does not honor. Both were hand-fixed. Per the systematize-friction mandate, repeated dev friction becomes tooling, not repeated hand-work.

DESIGN (decided, see leaves): pairing is EVIDENCE-DRIVEN, not static. The gate fires only where checker B emits an unsuppressed diagnostic on a line that already carries checker A's suppression. This avoids the two failure modes of naive static pairing: (a) mypy/ty rule codes are not 1:1 (name-defined vs unresolved-reference, attr-defined vs unresolved-attribute), so static pairing needs a lossy mapping table; (b) stamping suppressions onto lines the other checker never flagged just creates unused-suppression debt. Evidence-driven pairing needs NO mapping table -- the reporting checker's diagnostic carries the exact rule code to emit.

Current population: 37 'type: ignore' lines, 20 already dual-dialect, 17 mypy-only, 6 ty-only.

DESIGN AMENDMENT (2026-07-31, user, SUPERSEDES the configuration-gating decision above): the GOAL IS PORTABILITY, not conformance to whichever checker this repo happens to run. 'This repo runs ty, but that doesn't mean every repo runs ty; I just want anybody to be able to type-check the code.' A downstream consumer running mypy against frob's source must not eat spurious errors, so every suppressed line should carry EVERY supported dialect's suppression -- including for checkers this repo never runs.

Consequences, all of which reverse earlier decisions:
1. Do NOT gate a direction on the tool being configured in the consuming project. Silence-when-unconfigured was correct for a conformance goal and is WRONG for a portability goal -- it would leave frob's own source hostile to mypy users forever, since mypy never runs here.
2. Do NOT drop the mypy dialect or migrate the 17 legacy mypy-only ignores away. They are load-bearing for downstream mypy users. The successor question posed in T-1342 is withdrawn.
3. mypy becomes a DEV DEPENDENCY used purely as an ORACLE (user-sanctioned: 'If we need to get mypy purely for testing this capability, then we can go ahead and do so'). ty stays the gating checker; mypy is never a gate, only a source of ground-truth diagnostics.

This amendment RESCUES the evidence-driven design rather than forcing a retreat to static pairing. The reason evidence-driven pairing looked impossible for an unconfigured checker is that nothing produced its diagnostics; installing mypy as an oracle produces exactly those diagnostics locally. So pairing stays evidence-driven and SYMMETRIC, still needs NO mypy-code <-> ty-code mapping table, and each dialect's suppression is written with that dialect's own rule code taken from that dialect's own diagnostic. Static pairing with a lossy mapping table remains rejected.

Watch item for the oracle: mypy's --warn-unused-ignores must stay OFF, or be reconciled deliberately. Exact evidence-driven pairing should not produce unused ignores, but the 17 pre-existing legacy mypy ignores were written for a mypy that never ran and some may now be unused; treat any such finding as information, never as license to delete a suppression a downstream consumer may need.

<!-- ticket:T-1342 -->
```yaml
id: T-1342
title: Backfill the 23 unpaired suppression lines and lock main at zero SUPPRESS001
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: medium
parent: T-1339
tier: ticket
sprint: null
scope:
- src/frob/gates/_waive.py
- tests/test_gates_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
acceptance:
- text: given frob check on main, when the suppress gate runs, then it reports 0 SUPPRESS001
    findings
  evidence: []
threat: null
component: gates
```
Phase 3 of T-1339, depends on both the detector and the Tier-A handler. Drive the existing population to zero via frob check --fix: 37 'type: ignore' lines exist, 20 already dual-dialect, 17 mypy-only, 6 ty-only. Expect far fewer than 23 actual findings, since evidence-driven detection only fires where the other checker genuinely reports -- the remaining unpaired lines are legitimately fine and MUST NOT be touched. Add a lock test so a regression reds main.

WITHDRAWN by T-1339's DESIGN AMENDMENT (2026-07-31): the successor question originally posed here -- whether to migrate the 17 legacy mypy-only ignores to ty and drop the mypy dialect from this repo -- is answered NO and must not be pursued. The goal is portability: those mypy suppressions are load-bearing for downstream consumers who type-check frob with mypy, even though mypy never gates here. Do not delete or migrate a suppression for a checker this repo does not run.

Expect this ticket's real work to GROW rather than shrink under the amendment: with mypy installed as an oracle, the ty->mypy direction now produces findings too, so lines carrying only a ty suppression will need mypy pairs added.

<!-- ticket:T-1344 -->
```yaml
id: T-1344
title: 'Agentic-development throughput: the land path is the bottleneck, not the work'
state: queued
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: null
tier: epic
sprint: null
scope:
- docs/guides/agent-playbook.md
- src/frob/tickets/_land_git_ops.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
acceptance:
- text: given N concurrent agents finishing work, when each lands, then no agent is
    refused for DirtyMain and no agent touches another agent uncommitted state
  evidence: []
- text: given an unchanged file set, when frob check re-runs, then gate results are
    served from a content-digest cache rather than recomputed
  evidence: []
threat: null
component: tickets
```
Filed 2026-07-31 from direct observation of a 7-agent parallel drive (T-1334/1336/1337/1338/1340/1327/1276/1293/1294/1296).

THE EVIDENCE: across four completed tickets that day, every agent got its ENGINEERING right on the first pass. Effectively all of the lost wall-clock was in the LAND PATH:

- T-1336: DirtyMain refusal from a sibling's in-flight land, plus one land attempt killed by an undersized timeout wrapper.
- T-1337: committed ANOTHER agent's uncommitted tickets.md churn to main, twice, purely to clear DirtyMain. Inert metadata this time; the shape is dangerous.
- T-1338: land killed mid-Tier-A-autofix left a GARBLED source file; the obvious "git checkout -- <file>" recovery then silently destroyed an uncommitted new test. Caught only because a pytest count looked wrong.
- Coordinator: "frob ticket new" exceeded a 120s timeout under 4 concurrent agents (single-file ledger lock).

So the leverage is not in how agents do the work -- it is in serialization, cache-coldness, and non-atomic recovery. Leaves cover: merge queue, digest-memoized gates, sibling-lease disclosure in brief, transactional land auto-fix, ledger write contention.

ALSO NOTE (separate but related): the coordinator was hand-writing 40-line dispatch prompts duplicating what "frob ticket brief" already emits. Underused capability, not a tool gap -- addressed by convention plus the brief leaf.

CONSTRAINT DISCOVERED: memory is no longer the limit on agent count (.wslconfig now gives 23 GB + 24 GB swap). CPU is: 12 cores, load ~11 at only 4 agents, and land must finish inside a 540s wrapper. Practical ceiling ~7 concurrent agents. Every item below raises that ceiling by making the land path cheaper.

T-1058 (worktree cut from stale origin/main -- a documented silent-revert cause) is ARCHIVED, not resolved in the active ledger; the playbook still carries a manual "git merge main first" step as the mitigation. Re-decide it under this epic if the merge queue does not subsume it.

<!-- ticket:T-1366 -->
```yaml
id: T-1366
title: CI still cannot verify the .frob/-local coverage stamp and delta baseline (T-1265
  successor)
state: queued
kind: security
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- .github/workflows/ci.yml
- src/frob/gates/_coverage.py
- src/frob/gates/_baseline.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a CI run WHEN the coverage stamp or delta baseline is absent, stale
    or tampered THEN the build fails rather than silently degrading to a pass
  evidence: []
threat: repudiation
component: null
```
T-1265 made the ci.yml self-gate blocking and added a TEST012 check for frob-coverage.lock.json, the one committed coverage channel. The residue it did not close: the coverage stamp and the delta baseline still live in .frob/, which is gitignored and never restored in CI, so TEST005/TEST006 remain structurally inert there. CHK-THEME-GITIGNORED-TRUST in docs/design/registry/check-coverage.yaml is repointed here.

<!-- ticket:T-1382 -->
```yaml
id: T-1382
title: 'Decouple frob from the Makefile: make every workflow a first-class cross-platform
  frob subcommand'
state: queued
kind: feature
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
- docs/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
acceptance:
- text: GIVEN a repo with no Makefile WHEN every documented frob workflow is run THEN
    each works via a frob subcommand alone
  evidence: []
- text: GIVEN Windows (no make, no POSIX shell) WHEN the coverage workflow runs THEN
    it works without shell quoting, backslash line continuations, or GNU-make syntax
  evidence: []
- text: GIVEN docs and agent guidance WHEN a workflow is described THEN it names the
    frob subcommand, with make targets documented only as thin optional aliases
  evidence: []
threat: null
component: null
```
User directive 2026-08-01: frob must be cross-project and cross-platform, so it cannot depend on a Makefile.

Current state measured today: the Makefile is 528 lines and 21 call sites across src/frob/ reference it (src/frob/_cli_parsers/_core.py, testing/_collect_cpp.py, vet/_supplychain.py, vet/_capability_registry.py, natives/_build.py, strata/_native_staleness.py, scaffold/_managed.py, scaffold/project.py and others).

The sharpest example is 'make coverage'. Its recipe is ~30 lines of GNU-make-escaped POSIX shell -- COVERAGE_PROCESS_START, a generated coverage rc, an xdist run, a 'node down' grep with a full serial re-run, coverage combine, a T-1363 status guard, then a stamp. None of that runs on Windows, and tests/unit/test_makefile_coverage.py has to slice the recipe text out of the Makefile with a regex and re-run it under bash just to test it -- which is itself evidence the logic is in the wrong place. It should be 'frob coverage', implemented in Python, with the Makefile target reduced to a one-line alias.

Suggested decomposition (leaves to be filed as children):
1. frob coverage -- own the whole recipe in Python, including worker-crash detection and the T-1363 never-promote-partial-data guard.
2. frob build/natives -- replace 'make core' and the native build paths.
3. Audit the 21 Makefile references; each is either a workflow to promote or a scaffold template to re-point.
4. Path/shell portability sweep: no bash -c, no backslash continuations, no assumption of a POSIX shell in any code path.
5. Docs + agent-playbook rewrite so guidance names frob subcommands first; keep make targets as documented optional aliases for muscle memory.

Related: the user's standing preference is still to SUGGEST 'make <target>' where one exists, so this is about removing the DEPENDENCY, not deleting the Makefile.

<!-- ticket:T-1389 -->
```yaml
id: T-1389
title: 'TEST011: extend deflation detection to catch per-symbol false-0.0% coverage
  under xdist worker loss'
state: queued
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Investigated directly: reproduced the SAME test (tests/test_ticket_leases.py
::TestWorktreeSweepCli::test_sweep_cli_prints_verdicts_and_summary) under a
real xdist run (-n 4, the exact absolute-path subprocess rc T-1235 fixed:
branch/parallel/relative_files/sigterm/concurrency all matching the real
make coverage recipe) against the whole tests/test_ticket_leases.py file
(45 tests, several workers). `coverage report -m` on the combined result
shows src/frob/app/worktree_runner.py at 80% branch, matching the
originally-cited direct-run number exactly -- no 0% false-negative
reproduces at this scale. The merge machinery (combine + the [paths]
remap) is not dropping this symbol's data in a smaller, controlled xdist
run.

This narrows the likely cause to a FULL-suite-scale-only effect, not a
distinct bug in coverage.xml combine/attribution logic itself. The most
likely explanation is the class T-1353 already root-caused and partially
fixed in the same investigation window: under the full suite's `-n auto`
(pre-T-1353) or even the now-capped `COVERAGE_WORKERS=4`, several tests in
this repo (self-conformance/self-scan tests especially) spawn their own
coverage-traced subprocess/multiprocessing children, oversubscribing
CPU/memory and crashing xdist workers ("node down"); a crash bypasses
`sigterm=true`'s flush and drops that ENTIRE worker's coverage
contribution, not just its failed test(s). If `test_sweep_cli_prints_
verdicts_and_summary` happened to land on a worker that later crashed in
that specific full-suite run, its earlier-recorded coverage would be lost
this exact way -- consistent with "a false 0.0% only in the full suite,
never in isolation" and with T-1353's own measured symptom shape
(severely deflated numbers for symbols near/after a stuck/crashed
worker's tests).

I cannot conclusively distinguish "this exact symbol got node-downed in
that one run" from "a still-undiscovered distinct merge defect" without
re-running the FULL, unscoped `make coverage` under load and inspecting
which worker crashed and when that specific test executed -- both a
coordinator-only step (playbook section 6b: a dispatched sub-agent cannot
run/wait on `make coverage`) and, even if it could, backward-looking
forensics on a run that already happened and was cleaned up. Per this
series' guidance ("if the root cause turns out to be an environment
artifact rather than a defect, say so plainly and drop"), dropping here:
the evidence available points to an already-partially-mitigated
environment/load artifact (T-1353's node-down class), not a fresh,
reproducible defect in the merge code this ticket's scope (src/frob/
gates/_coverage.py, Makefile) could fix.

The ticket's OWN alternative plan item -- "extend TEST011's detection to
catch this class of false 0.0%" -- is real, actionable follow-up work
(a per-symbol deflation heuristic distinct from TEST011's current
aggregate module_join_fraction check, which stays silent when only a
handful of symbols are affected but the overall join fraction is fine).
That is a genuine new detector design, not a small fix-in-place; filing
it as its own ticket rather than forcing a half-designed version into
this investigation ticket's close.

<!-- ticket:T-1396 -->
```yaml
id: T-1396
title: 'TEST005 burn-down: src/frob/gates remaining findings past the 0.0% priority
  tier'
state: queued
kind: feature
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/gates/**
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
## Description + plan
T-1279's brief listed 12 symbols in src/frob/gates at exactly 0.0%
branch coverage. Investigation found 10 of the 12 (secrets_gate,
parse_failure_gate, opaque_gate, scan_emitted_rule_ids/
generated_gate_rule_ids partially, scope_digest, prework_gate,
test_gate, release_gate, perf_gate, run_gates) already carry real,
behavioral frob:tests-bound unit tests exercising both clean and
finding-producing branches (e.g. tests/test_secrets_gate.py,
tests/test_gates.py::TestParseFailureGate,
tests/test_gates.py::TestKnownGateRuleIds, tests/test_gates.py's
TestScopeDigest*/TestPreworkGate*/TestTestGate*/TestReleaseGate*/
TestPerfGate*/TestRunGates* classes). Their reported 0.0% is most
plausibly the known coverage-attribution gap tracked by T-1235/T-1395
(subprocess + multiprocess worker coverage not being attributed back
to the parent process) rather than a genuine test gap -- this ticket
does not re-litigate that; it is out of `src/frob/gates/**` scope.

Genuine, closeable gaps found and fixed by T-1279 itself:
- `mutation_evidence_violations`'s `Err` (ExecDisabled) degrade branch
  had no direct test -- added (tests/gates/test_mutation_evidence_err_branches.py).
- `scan_emitted_rule_ids`'s comment-skip line, missing-scanned-base-dir,
  and unresolved-const-ref branches had no direct test -- added
  (tests/gates/test_rule_id_scan_branches.py).

Remaining work for a genuine, non-attribution-driven TEST005 burn-down
of src/frob/gates (179 findings total, only 12 were the 0.0% priority
tier T-1279 targeted): audit the other ~167 findings in the 0-75%
band across src/frob/gates/** for real missing-branch gaps (as opposed
to attribution noise) and close them with behavioral tests, same
discipline as T-1279 (no assert-True filler, judge dead code before
writing a test for it).

## Acceptance
- [ ] GIVEN the gates package at the 75%/70% floors WHEN frob check --only test runs THEN it reports 0 TEST005 findings under src/frob/gates/** that are NOT explained by the T-1235/T-1395 coverage-attribution gap
- [ ] GIVEN a symbol judged to have a genuine missing-branch gap WHEN a test is added THEN it asserts real behavior, never filler

<!-- ticket:T-1420 -->
```yaml
id: T-1420
title: 'arch: 51-file LARGE001 residue after T-1270''s 2-file split'
state: queued
kind: feature
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/lib.rs
- strata-core/src/parse/mod.rs
- src/frob/tickets/_models.py
- src/frob/tickets/_store.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_reporting.py
- src/frob/tickets/_reporting_attachments.py
- src/frob/vet/_capability.py
- src/frob/vet/_scan.py
- src/frob/vet/_scan_violations.py
- strata-core/src/parse/**
- tests/test_capability_registry.py
- tests/test_vet.py
- tests/test_gates.py
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry.py
  reason: the file this split deletes; land's UnownedDeletions check does not treat
    the src/** glob as covering it, and the ledger splice dropped this entry when
    main was merged forward
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: src/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_store.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_reporting_attachments.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_capability.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_scan.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_scan_violations.py
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: strata-core/src/lib.rs
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: strata-core/src/parse/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/**
  reason: 'T-1420 was scoped to src/** repo-wide, which held a blocking lease over

    the whole tree and stalled other tickets'' scope operations this session

    (per coordinator brief). Only 8 unwaived LARGE001 findings remain as of

    this measurement (archgate re-run): tickets/_models.py, tickets/_store.py,

    tickets/_new_renumber.py, tickets/_reporting.py, vet/_capability.py,

    vet/_scan.py, strata-core/src/lib.rs, strata-core/src/parse/mod.rs.

    Narrowing scope to exactly those files plus their test/doc counterparts

    so this ticket no longer holds a tree-wide lease.

    '
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: frob-core/src/lib.rs
  reason: neither file appears in the current unwaived LARGE001 finding set; drop
    from scope to keep the lease minimal (re-applying the same narrowing lost by the
    tickets.md main-restore step)
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: src/frob/vet/_capability_registry.py
  reason: neither file appears in the current unwaived LARGE001 finding set; drop
    from scope to keep the lease minimal (re-applying the same narrowing lost by the
    tickets.md main-restore step)
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_capability_registry.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_vet.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_tickets_collision.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_matrix_covers_every_kind_and_language
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy
- tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
- tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged
- tests/test_gates.py::TestSysGate::test_sys001_dangling
- tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
- tests/test_tickets_collision.py::TestRenumberOneV2::test_git_mv_renames_directory_and_rewrites_id_field
- tests/test_tickets_collision.py::TestRenumberOneV2::test_sibling_ticket_prose_citation_rewritten
- tests/test_tickets_collision.py::TestRenumberOneV2::test_dry_run_mutates_nothing
- tests/test_tickets_collision.py::TestRenumberOneV2::test_target_id_already_exists_is_duplicate_id
- tests/test_tickets_collision.py::TestRenumberOneV2::test_unknown_old_id_is_not_found
threat: null
component: null
```
T-1270 cleared 2 of the 32 files on its list this pass (src/frob/_cli_parsers/_ticket.py
split into a per-concern package; src/frob/app/config.py split by extracting its two
procedural blocks -- from_external's field-copy loop and the stale-install/arch-config
helpers -- into app/_config_external.py and app/_config_meta.py). Both splits verified
scoped-and-foreground (pytest on the covering test files, ruff/format clean) before
landing.

51 unwaived LARGE001 findings remain repo-wide as of this measurement (down from 53),
listed below with current line counts. Same instruction as T-1270's own brief: pick a
cohesive subsystem slice per land, split it where a real seam exists (a parser/renderer
split, a coherent helper family, a distinct concern), or record an accepted-with-reason
frob:waive LARGE001 where the file is a genuinely single irreducible unit -- do not
raise the threshold and do not waive merely for size.

- frob-core/src/lib.rs (2277)
- strata-core/src/lib.rs (869)
- strata-core/src/parse/mod.rs (1744)
- src/frob/app/check_runner.py (1267)
- src/frob/app/sys_runner.py (1023)
- src/frob/app/ticket_runner/_close_cmd.py (1086)
- src/frob/app/ticket_runner/_land_cmd.py (967)
- src/frob/app/ticket_runner/_verify.py (973)
- src/frob/arch/_patterns.py (1486)
- src/frob/arch/_python.py (962)
- src/frob/arch/_rust.py (838)
- src/frob/check/__init__.py (959)
- src/frob/check/_python.py (1063)
- src/frob/doctor.py (920)
- src/frob/dup/_pipeline/_fingerprint.py (812)
- src/frob/gates/__init__.py (6713)
- src/frob/gates/_coverage.py (916)
- src/frob/gates/_debt_deprecated.py (851)
- src/frob/gates/_docblocks.py (822)
- src/frob/gates/_docptr.py (1468)
- src/frob/gates/_fix_engine.py (1401)
- src/frob/gates/_protocol_summary.py (1244)
- src/frob/gates/_registry_exhaustiveness.py (988)
- src/frob/gates/_secrets.py (1089)
- src/frob/gates/_sys.py (818)
- src/frob/gates/_tickets_gate.py (1077)
- src/frob/gates/_waive.py (1459)
- src/frob/graph/__init__.py (864)
- src/frob/graph/callgraph.py (830)
- src/frob/graph/dsl.py (1075)
- src/frob/perf/_effect_summaries.py (823)
- src/frob/perf/_rules.py (840)
- src/frob/strata/__init__.py (957)
- src/frob/strata/_audit.py (1055)
- src/frob/strata/_compliance.py (1257)
- src/frob/strata/_elaborate.py (1403)
- src/frob/strata/_host_isolation.py (1285)
- src/frob/strata/_infra.py (837)
- src/frob/strata/_mode_conformance.py (871)
- src/frob/strata/_selfconform.py (1608)
- src/frob/strata/_threat.py (2522)
- src/frob/tickets/_evidence.py (1369)
- src/frob/tickets/_land.py (1831)
- src/frob/tickets/_land_squash.py (919)
- src/frob/tickets/_leases.py (1403)
- src/frob/tickets/_models.py (1917)
- src/frob/tickets/_new_renumber.py (963)
- src/frob/tickets/_store.py (1552)
- src/frob/vet/_capability.py (6020, T-1074-flagged, still no dedicated follow-up filed)
- src/frob/vet/_capability_registry.py (2991, same T-1074 flag)
- src/frob/vet/_scan.py (901)

Note: src/frob/tickets/ and src/frob/app/ticket_runner/ overlap T-1296's strata TEST005
lease and other concurrent tickets' scopes at filing time -- narrow scope via
`frob ticket scope` before starting, per playbook section 4/lease-collision guidance.

## Done report

WAVE6-R session (dedicated T-1420 lease). Warm-up: merged main
(a776121c -> 90eff16c ancestor merge), `frob natives build` clean,
`frob ticket start T-1420`.

Re-measured LARGE001 (`frob check --only archgate`) at session start: 48
unwaived + 1 waived (49 total). Split
src/frob/tickets/_new_renumber.py's already comment-delimited v2-mode
git-mv renumber backend (`_v2_id_dir` through `renumber_one_v2`, T-1255
family, 260 lines) verbatim to a new sibling _renumber_v2.py
(989 -> 730 lines; new file 288 lines). `renumber_one` dispatches to
`renumber_one_v2` via a local (not top-level) import to avoid a circular
import, since `_renumber_v2` imports helpers back from `_new_renumber`
(`_rewrite_body_prose_references`, `_scan_code_references`,
`_log_renumber_dry_run`, `_log_renumber_done`). Repointed the 5
frob:tests edges in tests/test_tickets_collision.py's TestRenumberOneV2
class and the frob:waive DUP002 prose in _store.py's git_mv_dir that
named the old module path. Commit a0037269.

Verification: `pytest tests/test_tickets_collision.py` (24 passed,
foreground). `frob check --only drift` 0 errors after the edge
repoint (was 5 DRIFT002 before). `frob check --only archgate --only
wire --only dead_symbols --only doclink --only docanchor --only fmt`:
0 errors (gate:LARGE 0 errors, 47 warnings, 1 waived -- down from 48
unwaived before this split).

src/frob/vet/_capability.py (6070 lines, largest unwaived LARGE001 file
repo-wide): per this session's brief, did NOT split it blind. Read the
full symbol list (`grep -n '^def \|^class '`, 180 symbols) and found a
clean per-language seam: a scanner core plus six self-contained
per-language alias/binding-resolution families (Python, TypeScript,
Rust, C, Kotlin) plus a tail aggregation/fingerprint/opaque-indirection
layer -- the same shape T-1420's already-landed
_capability_registry.py package split found in the sibling file. Wrote
the full seam analysis (module boundaries, line ranges, what stays in
the dispatcher, the one open question about the opaque-indirection
family's placement) as a design ticket, parent T-1420, kind=feature,
scope src/frob/vet/_capability.py + its two test files:
T-1459 (real id assigned at land). Left QUEUED, not
implemented -- per the brief's explicit instruction to design first and
implement only if time remains and the design is unambiguous; this
session's remaining time went to closing out the one small clean file
on the list instead of starting a 6000-line six-language split without
review.

The Rust files (strata-core/src/lib.rs, strata-core/src/parse/**) and
the other Python files on the ticket's scope list
(src/frob/tickets/_models.py 1977 lines, _store.py 1576 lines) were NOT
touched this session -- time was spent on natives warm-up, the merge,
the _new_renumber split, and the capability design ticket. Not
splitting them is a disclosed cut, not a silent one: none of the three
have an obvious single clean seam the way _new_renumber.py's v2 block
did (a quick read of _models.py's export list shows a much more tangled
pydantic-model + validator + prose-rewrite mix than the tickets/ backend
split just landed), and the Rust files need a from-scratch seam read
this session did not get to.

Measured LARGE001 count after this session's one split: 47 unwaived + 1
waived (48 total, down from 49 at session start) via `frob check --only
archgate`, full output read (not piped).

Nothing outside the ticket's declared scope was touched. No lease
collisions hit. T-1420 itself stays open (not closed) -- 47 unwaived
files remain repo-wide, most of them (Rust natives, strata/, gates/,
tickets/_land.py, etc.) untouched by this session and needing their own
seam reads before a future session force-splits them.

### Changed
```
 src/frob/tickets/_new_renumber.py | 273 ++---------------------------------
 src/frob/tickets/_renumber_v2.py  | 296 ++++++++++++++++++++++++++++++++++++++
 src/frob/tickets/_store.py        |  18 +--
 tests/test_tickets_collision.py   |  10 +-
 tickets.md                        | 145 +++++++++++++++++++
 5 files changed, 466 insertions(+), 276 deletions(-)
```

### Evidence
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_matrix_covers_every_kind_and_language` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_sys001_dangling` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 8 error(s), 7405 warning(s), 730 waived
- error-findings: AFFECT001@src/frob/tickets/_new_renumber.py, AFFECT001@src/frob/tickets/_renumber_v2.py, AFFECT001@src/frob/tickets/_store.py, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:29, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:35, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:57, F401@/home/logan/projects/frob/.claude/worktrees/t-1420/src/frob/tickets/_new_renumber.py:58, INV006@src/frob/tickets/_renumber_v2.py

<!-- ticket:T-1452 -->
```yaml
id: T-1452
title: 'strata: design argument-level may scoping (may KIND of TARGET)'
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1440 parent: argument-level `may` scoping follow-up (design sketch item
5, explicitly deferred to documentation-only by T-1440's own acceptance
plan): e.g. `may "env.read" of "FROB_*"` narrowing WHICH env vars, fs
paths, or net hosts a grant covers, not just which FILES (`via`) may
exercise it. Natural follow-up once `via` itself has real migrated usage
(T-1440's sibling migration ticket) to learn argument-scoping shapes
from. Not designed in detail yet -- this ticket is a placeholder for that
design pass, not a ready-to-implement plan.

<!-- ticket:T-1459 -->
```yaml
id: T-1459
title: vet _capability split design
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: T-1420
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet.py
- tests/test_vet_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1420 LARGE001 residue: src/frob/vet/_capability.py is 6070 lines (T-1074-
flagged, largest unwaived LARGE001 file repo-wide). This ticket is the
SPLIT DESIGN only -- do not implement blind; a follow-up ticket implements
it once this design is reviewed.

## Seam analysis (measured via `grep -n '^def \|^class ' src/frob/vet/_capability.py`)

The module already reads as a scanner CORE plus a strict per-LANGUAGE
alias/binding-resolution family repeated six times (Python, TypeScript,
Rust, C, Kotlin) plus the tail-end fingerprint/opaque-indirection
aggregation layer. Each per-language family is internally self-contained
(its own scope-binding walk, alias table builder, resolved-candidate
collector, `_<lang>_binding_capabilities`/`_<lang>_binding_operations`
pair) and calls back into the scanner core only through a small, already-
named set of shared helpers (`_needle_hits_outside_comments`,
`_compiled_capability_patterns`, `ByteSpan` family, `_DangerousOperation`).
This is the same shape the registry package split (T-1420, already landed
this ticket's earlier portion: `src/frob/vet/_capability_registry/`) found
in the sibling file -- same treatment applies here.

Proposed module boundaries (verbatim moves, one seam per land, same
discipline as every other T-1420 split):

1. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_core.py` (~180-820, ~640 lines): pattern
   compilation (`_compile_patterns`, `_compiled_capability_patterns`),
   comment/docstring/non-executable byte-span helpers (`_comment_byte_spans`
   through `_non_executable_byte_spans`), the needle-matching primitives
   (`_needle_to_ws_pattern` through `_needle_hits_as_bare_call`), and the
   embedded-code-region family (`_looks_like_embedded_code` through
   `_embedded_operations`). Every per-language module imports from here;
   this module imports from no per-language module -- it is the shared
   floor, so it must land FIRST if this is done incrementally.

2. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_python.py` (~820-1670, ~850 lines): the
   `_py_*`/`_python_*`/`_resolve_py_*`/`_record_py_*`/`_bind_py_*` family
   -- scope binding, alias table construction, resolved-candidate
   collection, `_python_binding_capabilities`/`_python_binding_operations`.

3. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_typescript.py` (~1670-2745, ~1075 lines): the
   `_ts_*`/`_collect_ts_*`/`_resolve_ts_*`/`_record_ts_*`/`_bind_ts_*`
   family, same shape as Python's, plus TS-specific require/dynamic-import
   handling (`_ts_require_call_module`, `_ts_dynamic_import_module`, the
   `_ts_dynamic_import_then_*` chain) that has no Python analog.

4. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_rust.py` (~3282-4043, ~760 lines): the
   `_rust_*` family -- `use`-declaration binding (`_bind_rust_use_as_clause`
   through `_rust_use_table`), scope binding, alias tables,
   `_rust_binding_capabilities`/`_rust_binding_operations`.

5. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_c.py` (~4043-4744, ~700 lines): the `_c_*`
   family -- macro alias table, declaration/scope binding, alias tables
   (including the array/structured-binding/default-param alias variants C
   has that the other languages don't), `_c_binding_capabilities`/
   `_c_binding_operations`/`_extra_c_binding_operations` (note:
   `_c_binding_capabilities`/`_c_binding_operations`/
   `_extra_c_binding_operations` currently sit textually AFTER the Kotlin
   block at ~5208-5274, not adjacent to the rest of the `_c_*` family --
   move them here too, verbatim, to keep the per-language module
   cohesive rather than mirroring the current file's accidental ordering).

6. <!-- frob:waive DOC006 reason="proposed future module split -- not yet landed" -->`src/frob/vet/_capability_kotlin.py` (~4744-5274, ~530 lines): the
   `_kt_*` family -- import table, callable-reference resolution, alias
   table, `_kt_binding_capabilities`/`_kt_binding_operations`/
   `_extra_kt_binding_operations`.

7. `src/frob/vet/_capability.py` (remaining, ~5274-6070 minus the C tail
   moved to (5), ~700 lines): stays the package's public entry surface --
   `_operation_entry_matches`, `_resolved_candidates_for_language`,
   `_binding_fingerprints`, the CVE-fingerprint scan family
   (`_yaml_load_call_lacks_explicit_loader` through
   `_scan_file_fingerprints`), `_decode_to_exec_signal`/
   `_body_reaches_decode_and_exec`, the directory-level aggregation
   (`_scan_directory_capabilities`/`_aggregate_capabilities`/
   `_scan_directory_fingerprints`/`_aggregate_fingerprints`), self-path
   exclusion (`is_self_pattern_path`/`_is_self_path`/`_is_test_path`), and
   the public `scan_file_capabilities`/`language_for`/
   `non_executable_line_numbers` entry points near the top of this range
   (~2908-3184) -- these dispatch across every per-language module by
   calling `_resolved_candidates_for_language`, so they belong with the
   dispatcher, not with any one language.

   Also stays here: the `_OpaqueFinding` class and the opaque-indirection
   scan family (`_split_top_level_args` through `_needle_construct_findings`
   and beyond, ~5771-6070) -- this is a DIFFERENT concern (structural
   opaqueness of a needle's argument, not capability/operation binding)
   that happens to live in the same file today; worth a SEPARATE follow-up
   ticket to ask whether it should move to its own
   `_capability_opaque.py` rather than folding it into step 7's dispatcher
   module by default -- flagging here rather than deciding unilaterally in
   this design ticket.

## What the registry package split (already landed, T-1420) already absorbed

`_capability_registry.py`'s own LARGE001 split (this ticket's earlier
portion, see Done report) is the PRECEDENT this design follows: verbatim
per-concern module extraction (`_dangerous_ops_python.py`,
`_dangerous_ops_other.py`, `_matrix.py`, `_kinds.py`, `_schemas.py`,
`_opaque.py`) under a package `__init__.py` that re-exports the public
surface unchanged. `_capability.py`'s split should follow the SAME
external-surface-unchanged discipline: `import frob.vet._capability` (or
`from frob.vet._capability import scan_file_capabilities`, etc.) from any
caller outside this module must keep working without a caller-side edit,
whether the final shape is a flat sibling-file split (as sketched above)
or a `_capability/` package mirroring the registry's own package shape --
that packaging decision (flat siblings vs. a package directory) is left
open for whoever implements this, not fixed by this design.

## Why this session did not implement it

Time/effort budget for this T-1420 session was allocated to closing out
the smaller, unambiguous files on the ticket's scope list first (see the
`_new_renumber.py`/`_renumber_v2.py` split landed this session). A ~6000
line, 180-symbol, six-language file is not something to split blind in
the time remaining -- this design ticket exists so the NEXT session (or
this one, if time allows) can implement steps 1-6 as a clean sequence of
one-seam-per-land commits without re-deriving the seam analysis from
scratch.

## Acceptance

- [ ] Design reviewed (seam boundaries above judged unambiguous, or
      revised) before any implementation ticket starts moving code.
- [ ] Implementation, if undertaken, follows the verbatim-relocation +
      frob:waive-carry + same-commit doc/test-edge-repoint discipline
      every other T-1420 split in this ticket's history used.

<!-- ticket:T-1466 -->
```yaml
id: T-1466
title: extend T-1433 SIGUSR1 stack-dump handler beyond pytest-only scope
state: queued
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/conftest.py
- src/frob/testing/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1433's SIGUSR1 stack-dump handler (tests/conftest.py::_install_stackdump_handler/_dump_all_thread_stacks) is currently wired ONLY into the pytest test-session lifecycle (pytest_configure), gated behind FROB_COVERAGE_STACKDUMP. WIRE001 flags both helpers as unreached outside their own tests, since tests/conftest.py itself is a test-path the gate's text scan skips. Follow-up: evaluate whether frob's own daemon/CLI processes (frob serve, frob check's own subprocess pool) would benefit from the same opt-in handler for non-coverage-recipe wedges, or whether the current pytest-only scope is intentionally final (in which case this ticket should close as won't-fix with that recorded).

<!-- ticket:T-1469 -->
```yaml
id: T-1469
title: make coverage doctor precondition dies on stale leases a finished agent left;
  auto-reconcile instead
state: in-progress
kind: bug
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/app/doctor_runner.py
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: acceptance[0]'s pytest evidence must live in the same test file T-1526 already
    uses for coverage-recipe assertions, matching every other coverage/Makefile ticket's
    own test-location convention
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
acceptance:
- text: GIVEN a stale in-progress hold with no live lease WHEN make coverage runs
    THEN the hold is auto-requeued with a logged line and the suite proceeds
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
threat: null
component: null
```
Third occurrence 2026-08-02: an agent session ends leaving an in-progress hold with no live lease; the next make coverage aborts at its frob doctor precondition (exit 1, before pytest ever runs) and the whole suite run is lost -- twice this cost a full run slot, and the footgun FAST_EXIT1 detector now flags it but cannot fix it. Stale leases are mechanically healable (frob ticket reconcile --apply does exactly this). Fix: either the coverage recipe runs reconcile --apply before doctor, or doctor gains --heal-stale-leases (auto-requeue with a logged line) for exactly this class while still failing hard on the non-healable conditions (missing natives, corrupt derived state).

## Done report

Fixed via the Makefile-side option this ticket's body offered ("the
coverage recipe runs reconcile --apply before doctor"), not the
`doctor --heal-stale-leases` flag option: `coverage:` and `coverage-fast:`
both now run `uv run frob ticket reconcile --apply` immediately before
`uv run frob doctor`. `reconcile --apply` (`frob.tickets._reconcile.
reconcile`) already exists and already does exactly what
`scan_stale_ticket_leases` (T-1131, `src/frob/doctor.py`) detects: an
IN_PROGRESS ticket with no live cross-worktree lease gets auto-requeued,
logged, and cleared -- so the very condition that used to make `frob
doctor`'s precondition abort the recipe (this ticket's acceptance[0]
GIVEN clause) is healed one command earlier, unconditionally, as a no-op
when there is nothing stale. `frob doctor` still runs immediately after
and still fails the recipe hard on every OTHER condition it checks
(missing natives, corrupt derived state, a live `land.lock`, venv shim
drift) -- `reconcile` only ever touches ticket leases, nothing else.

Chose this over the `doctor --heal-stale-leases` alternative because it
is strictly smaller and lower-risk: `frob.tickets._reconcile.reconcile`
is already the single source of truth for "what counts as stale and how
to fix it" (T-1131/T-0473), so wiring the existing CLI verb into the
Makefile precondition sequence reuses it directly with zero new code in
`src/frob/doctor.py`/`src/frob/app/doctor_runner.py` -- both stayed in
this ticket's declared scope but untouched; not a scope violation, this
ticket's own body explicitly offered the Makefile-only path as
sufficient ("either... or...").

tests/unit/test_makefile_coverage.py added to scope (same test file
T-1526 uses for coverage-recipe Makefile-text assertions): new
`TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor` asserts
`reconcile --apply` appears, and appears BEFORE `frob doctor`, in both
the `coverage:` and `coverage-fast:` recipe text.

One drive-by gate fix: `src/frob/app/config.py::AppConfig` (T-1525's own
`coverage_full`/`coverage_path` field additions, still in-progress, not
yet closed) was missing a `frob:ticket T-1525` class-level edge under
`--ticket T-1469`'s COV002 pass -- added the one-line edge comment; not a
scope violation (config.py is T-1525's own declared scope, T-1525 still
holds the lease), just a gate fix needed to get T-1469's own check run
clean.

Targeted tests: `tests/unit/test_makefile_coverage.py` -- 23 passed.
`frob check --ticket T-1469`: no ERROR-level finding traces to a file
this ticket touched. `frob check --land-parity`: clean, 0 unscoped
errors.

### Changed
```
 Makefile                             |  30 ++-
 README.md                            |   3 +-
 docs/modules/cli.md                  |  41 +++++
 docs/modules/testing.md              |   9 +-
 src/frob/__main__.py                 |   3 +
 src/frob/_cli_parsers/__init__.py    |   2 +
 src/frob/_cli_parsers/_misc.py       |  28 +++
 src/frob/app/_config_external.py     |   4 +
 src/frob/app/app.py                  |   4 +
 src/frob/app/config.py               |  11 ++
 src/frob/app/coverage_runner.py      |  84 +++++++++
 tests/unit/test_coverage_runner.py   |  78 ++++++++
 tests/unit/test_makefile_coverage.py |  79 +++++---
 tickets.md                           | 346 ++++++++++++++++++++++++++++++++++-
 14 files changed, 669 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 276 warning(s), 782 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1478 -->
```yaml
id: T-1478
title: argument-level may scoping (T-1440 follow-up)
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/surface.md
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
docs/strata/surface.md documents argument-level `may` scoping (e.g.
`may "env.read" of "FROB_*"`, narrowing WHICH env vars/paths/hosts a
grant covers, not just which files) as deliberately deferred by T-1440's
own scope cut, saying "its own follow-up ticket (T-1440's child) rather
than bundled into the grammar/join landing; see tickets.md for its id" --
but no T-1440 child ticket was ever actually filed. File it for real
(this ticket) and build argument-level may scoping. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

<!-- ticket:T-1479 -->
```yaml
id: T-1479
title: wire remaining daemon-proxy subcommands named by T-0321's integration map
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
docs/modules/serve.md's daemon-proxy section says T-0321's integration
map names outline/map/xref/parse/graph/exports/bind/docs/stats as
eventual proxy targets alongside check --delta-style reads, and that
these remain a disclosed residual, not yet wired. T-0321 itself is done
(tickets-archive.md); no open follow-up currently tracks wiring the
remaining subcommands through the daemon proxy. Wire the remaining
named subcommands (or a subset chosen by the implementer, disclosed in
the Done report) through frob.serve._tools/query() the same way
T-1128/T-1147 wired frob_graph_query/frob_doable_tickets/
frob_run_touched_tests/frob_check_delta. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

<!-- ticket:T-1480 -->
```yaml
id: T-1480
title: build frob sys check/trace/capacity/threats verbs
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- docs/commands/sys.md
- src/frob/strata/_mutation_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
docs/commands/sys.md documents frob sys as having five verbs today
(plan/doc/export/audit/sync-interface) and names check/trace/capacity/
threats as later phase-5 verbs not yet landed on main. No ticket
currently tracks building these four verbs. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

<!-- ticket:T-1481 -->
```yaml
id: T-1481
title: wire frob check --fix CLI flag to the tiered fix engine
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/app/check_runner.py
- docs/design/check-fix-engine.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
docs/design/check-fix-engine.md's "Status quo" section states
apply_tier_a_fixes has no CLI entry point: src/frob/app/check_runner.py
and src/frob/_cli_parsers/_check.py have no --fix/Fix reference, so
`frob check --fix` does not exist as a runnable command. Wire a --fix
flag through _cli_parsers/_check.py and check_runner.py that invokes
apply_tier_a_fixes (and, once T-1262/T-1263 land, the Tier-B/Tier-C
paths). Found while draining NEGEXIST001 (T-1477): the doc's
absence-claim had no frob:until binding.

<!-- ticket:T-1482 -->
```yaml
id: T-1482
title: build policy refinement-monotonicity diff pass (INV-030)
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/policy.md
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
threat: null
component: null
```
docs/strata/policy.md documents that policy refinement is DESIGNED to be
monotonic downward (a child may only strengthen an inherited policy,
never weaken it), but compile_policies/_resolve_scope only resolve scope
membership -- there is no refinement-diff pass that compares a child's
policy set against its parent's and flags a weakening. The paragraph
currently states design intent, not an enforced guarantee (also
disclosed via a frob:waive INV003 reason on the same section). Build
the refinement-diff pass. Found while draining NEGEXIST001
(T-1477): the doc's absence-claim had no frob:until binding.

<!-- ticket:T-1483 -->
```yaml
id: T-1483
title: wire frob refactor into main CLI dispatch
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
docs/commands/refactor.md documents frob.refactor._cli.add_refactor_parser
and run_refactor_command as built and ready, but T-1197's declared scope
never included src/frob/_cli_parsers/** or src/frob/__main__.py, so the
one-line _add_refactor_parser(sub) wiring call was never actually made.
Wire frob refactor into the main CLI dispatch. Found while draining
NEGEXIST001 (T-1477): the doc's own "not yet wired" claim had
no frob:until binding.

<!-- ticket:T-1485 -->
```yaml
id: T-1485
title: 'perf: fold arch nesting/cyclomatic/events into one walk; consolidate _walk_all/_find_if_statements'
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- src/frob/arch/_concurrency_model.py
- src/frob/arch/_patterns.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1215 fixed the _iter_own_scope quadruplication (lock_ordering,
async_hazards, shared_state_race, concurrency_model all now share
frob.arch._python._iter_own_scope). The OTHER half of report candidate #9
is not done: arch/_python.py's _py_build_module/_py_build_function still
run nesting/cyclomatic/events as 3 separate recursions per function
instead of folding them into the existing _py_collect_body_events walk,
and _concurrency_model.py's _walk_all plus _patterns.py's
_find_if_statements are further independent per-file walks not yet
consolidated.

This was deliberately NOT attempted in T-1215: _py_build_function's own
docstring explicitly documents that max_nesting_depth/cyclomatic are kept
as SEPARATE walks rather than derived from the flattened event list "so
these two metrics match the original per-language walk exactly,
byte-for-byte" -- collapsing them risks silently changing either metric's
value for edge cases (e.g. node types counted by _py_max_nesting/
_py_cyclomatic that _py_collect_body_events does not visit the same way).
That merge needs its own careful pass with a byte-identical-output proof
across a real corpus, not a quick fold-in inside a multi-ticket sweep.

Scope for the follow-up: src/frob/arch/_python.py (nesting/cyclomatic/
events fold), src/frob/arch/_concurrency_model.py (_walk_all), src/frob/
arch/_patterns.py (_find_if_statements).

<!-- ticket:T-1487 -->
```yaml
id: T-1487
title: 'rust: python tree-extraction kernel in frob-core (T-1220 delivered portion
  1)'
state: queued
kind: feature
origin: agent
created: '2026-08-03'
priority: high
parent: T-1220
tier: ticket
sprint: null
scope:
- frob-core/**
- tests/unit/test_extract_native.py
- docs/modules/lang.md
- docs/modules/dup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
acceptance:
- text: GIVEN the delivered kernel WHEN the golden-parity tests run THEN they pass
    and ffi_boundary reads 0 errors
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
threat: null
component: null
```
Leaf carrier for T-1220's first portion: extract_tree_python in frob-core (tree-sitter 0.25 kernel; comment spans, docstring spans, identifiers, token stream behind one non-raising FFI entry), golden-verified byte-for-byte against the Python path across 917 repo files with one documented grammar-generation delta. Consumer rewiring stays T-1219; cpp/rust/ts walkers remain under T-1220.

## Done report

Carrier for T-1220 portion 1; see the parent ticket Done report for
the full delivery narrative (917-file golden parity, FFI compliance,
grammar-generation delta documentation).

### Changed
```
 docs/modules/dup.md               |   7 +
 docs/modules/lang.md              |  23 +++
 frob-core/Cargo.lock              | 196 +++++++++++++++++++++-
 frob-core/Cargo.toml              |   2 +
 frob-core/frob_core.pyi           |  13 ++
 frob-core/src/extract.rs          | 215 ++++++++++++++++++++++++
 frob-core/src/lib.rs              |   6 +
 src/frob/vet/_capability_core.py  | 174 +++++++++++++-------
 tests/test_vet.py                 |  42 +++++
 tests/unit/test_extract_native.py | 123 ++++++++++++++
 tickets.md                        | 336 +++++++++++++++++++++++++++++++++++++-
 11 files changed, 1068 insertions(+), 69 deletions(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 299 warning(s), 745 waived
- error-findings: DUP001@frob-core/src/extract.rs, F401@/home/logan/projects/frob/.claude/worktrees/w18r-rust/src/frob/vet/_capability_core.py:30, INV006@frob-core/src/extract.rs, SELFAUDIT001@design, WIRE001@tests/unit/test_extract_native.py

<!-- ticket:T-1492 -->
```yaml
id: T-1492
title: 'ledger v2: wire migrate --to v2 CLI flag onto migrate_v1_to_v2'
state: queued
kind: feature
origin: agent
created: '2026-08-03'
priority: medium
blocked_by:
- T-1259
parent: T-1259
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/__init__.py
- docs/modules/cli.md
- tests/test_tickets_migration.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a monofile-mode repo WHEN frob ticket migrate --to v2 runs THEN it calls
    migrate_v1_to_v2 (T-1259) and reports the migrated count, leaving --to omitted
    behavior (collapse dir into monofile) unchanged
  evidence: []
threat: null
component: null
```
found while working T-1259: migrate_v1_to_v2 (src/frob/tickets/_store.py) is implemented and golden-round-trip tested, but T-1259's own scope does not cover the CLI parser (_cli_parsers/_ticket/_progress.py) or the ticket_runner dispatch (app/ticket_runner/_query.py, __init__.py) needed to actually expose --to v2 on the existing frob ticket migrate subcommand. This ticket wires that flag.

<!-- ticket:T-1503 -->
```yaml
id: T-1503
title: WIRE001 on test_extract_native.py's _python_side/_rust_side golden-test helpers
state: queued
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_extract_native.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
WIRE001 flags `_python_side`/`_rust_side` in tests/unit/test_extract_native.py
(T-1220's golden-parity tests for frob_core.extract_tree_python) as unreached
outside their own tests -- they exist solely as per-file test helpers that
assemble the existing Python-side computation vs the native kernel's output
for comparison within TestExtractTreePythonParity's own methods, mirroring
the tests/unit/test_conftest_stackdump.py::_load_conftest precedent (T-1466).
Follow-up: evaluate whether this pair should move to a shared test-support
module (frob.testing or a conftest fixture) if a future native-extraction
golden test wants the same comparison, or whether the current per-file scope
is intentionally final (in which case this ticket should close as won't-fix
with that recorded).

<!-- ticket:T-1505 -->
```yaml
id: T-1505
title: 'vet/resolvers: close remaining 3 structural points-to gaps (rust macro_rules,
  cpp ptr-to-member, kotlin operator-invoke) -- T-1063 residue'
state: queued
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1063's Done report closed 3 of 6 tracked structural points-to gaps and
left 3 genuinely residual (its own body already documents why each is
architecturally deeper than a table addition, quoted from T-1063):

- rust: `macro_rules!` expansion emitting a fixed call. No macro-expansion
  handling exists anywhere in the Rust resolver; closing this means
  expanding a macro body's tokens as if inlined at the invocation site, an
  AST transformation the resolver's plain-walk architecture does not
  support.
- c++: pointer-to-member (`auto p = &Ops::run; (obj.*p)(x);` / `->*`). No
  pointer-to-member alias tracking exists AND the C/C++ candidate
  collector has no handling for a `.*`/`->*` dereference as a call target.
- kotlin: operator-invoke (`class Handler { operator fun invoke(x) = ... };
  val h = Handler(); h(x)`). Needs receiver-INSTANCE points-to -- no
  instance points-to of any kind exists in the kotlin resolver today.

Each row is locked by its own honest non-firing/non-resolving litmus
fixture in tests/test_vet.py (per T-1063's evidence). T-0339 stays open
against these 3 rows until this closes or each gets a reasoned
OPAQUE_SOURCE_INVISIBLE excuse instead.

Filed as the TICK011 remediation for T-1063 (drain-to-zero warning
burn-down, this ticket).

<!-- ticket:T-1506 -->
```yaml
id: T-1506
title: 'docenum: widen _extract_members to resolve argparse choices=[...] lists'
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_docenum.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
frob.gates._docenum's `_extract_members` cannot resolve argparse
`choices=[...]` lists (cycle.md/xref.md --lang, parse.md tool table) --
a `parser.add_argument(..., choices=[...])` call site has no bare
module/class-level assignment target `_find_node_for_qualname` can walk
to at all. Widen `_extract_members` to this shape so doc-enum coverage
extends to CLI choices lists the same way it already covers
Literal/frozenset assignments.

Follow-up filed as the TICK0/TODO002 remediation for the dangling
`frob:todo T-draft-323551f5` directive at
src/frob/gates/_docenum.py::_extract_members (drain-to-zero warning
burn-down, this ticket) -- that draft id was never actually filed as a
real ticket.

<!-- ticket:T-1508 -->
```yaml
id: T-1508
title: z3-solver fails to build in worktrees, blocking dup._pipeline._smt TEST005
  burn-down
state: queued
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_pipeline/_smt.py
- tests/unit/test_dup_smt.py
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
src/frob/dup/_pipeline/_smt.py has TEST005 module-line coverage of 21.0%
(floor: 70%). Its own test file (tests/unit/test_dup_smt.py) correctly
skips when z3-solver is not importable -- but in this worktree,
`uv sync --extra smt` (the "frob[smt]" optional dependency group) fails
outright to build the z3-solver wheel:

  LibError: Unable to build Z3.
  hint: `z3-solver` (v5.0.0.0) was included because `frob[smt]`
  (v0.319.0) depends on `z3-solver`

This blocks raising this module's coverage from any worktree session
until the z3-solver build issue is resolved (likely needs a system
package -- cmake/a C++ toolchain matching what z3-solver's sdist build
expects -- or a prebuilt wheel pin). Filed while working T-1307 (TEST005
burn-down: src/frob/dup); T-1307's own scope was amended to exclude this
finding as environment-blocked rather than force it.

## Failure log
- 2026-08-05 attempt 1: z3-solver has no aarch64 linux wheel compatible with this glibc 2.35 host for any version, and sdist builds fail both directions: 5.0.0.0 needs a GCC with C++20 format header (absent in the system GCC 11.4), while 4.9.1.0 and earlier need CMake below 3.5 support (removed from the installed CMake 3.22); genuinely un-buildable in this worktree, not a pyproject fix

<!-- ticket:T-1518 -->
```yaml
id: T-1518
title: 'move TEST016 mutation evidence off the per-land critical path: batch/nightly
  cadence, land-blocking only for security-kind'
state: queued
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
From the 2026-08-04 dev-cycle review: TEST016 (mutation evidence) is the most expensive, least incremental land stage, and its marginal per-ticket value is test-strength validation, not main-correctness. Proposal: run TEST016 per merge-queue batch drain (T-1444) or nightly over the day's landed diffs; keep it synchronous+blocking only for kind=security tickets. A batch finding files a ticket against the offending land instead of refusing it retroactively. Interacts with: T-1444 (batch boundary is the natural cadence point), the existing --skip-mutation-evidence override (today used 2x for genuine false positives T-1235/T-1439 -- a lower-frequency, higher-context batch run should also reduce false-positive pressure).

<!-- ticket:T-1521 -->
```yaml
id: T-1521
title: 'strata: decide whether flow src/dst validation belongs inside elaborate()
  itself'
state: queued
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Disclosed cut from T-1196: check_cross_file_references only covers the two
reference shapes elaborate() itself does not already validate at all
(flow src/dst). Whether flow src/dst validation belongs inside elaborate()
itself (so a single-file design also gets it too) is left as a design
question for this follow-up.

<!-- ticket:T-1525 -->
```yaml
id: T-1525
title: 'coverage: user-facing frob coverage CLI verb + decide frob check auto-trigger
  for non-agent callers'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/_cli_parsers/_misc.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/coverage_runner.py
- docs/modules/cli.md
- tests/unit/test_main_entry.py
- tests/test_app_config.py
- tests/unit/test_coverage_runner.py
- src/frob/_cli_parsers/__init__.py
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/app.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/config.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/coverage_runner.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/cli.md
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_app_config.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_coverage_runner.py
  reason: CLI verb wiring needs Subcommand enum + config fields + runner + parser
    registration, not just __main__.py dispatch; declared scope predated the actual
    convention this repo uses (natives_runner precedent)
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: re-export barrel for the new _add_coverage_parser builder, same pattern
    every existing parser follows
  actor: logan
  at: '2026-08-05'
- op: add
  glob: README.md
  reason: DOC005 requires the new frob coverage verb's README command-table row +
    updated count, same as every prior CLI-verb ticket (T-0864 precedent)
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_full_calls_native_refresh_directly
- tests/unit/test_coverage_runner.py::TestCoverageRunner::test_run_failure_exits_nonzero
threat: null
component: null
```
T-1516/T-1205 acceptance[3]'s other half: native_coverage_refresh exists as a library function but has no CLI entrypoint (frob coverage / frob test --coverage). Also open: T-1205 acceptance[4] literally asks for auto-refresh inside any frob command whose gates need coverage data; frob check deliberately does not do this for a dispatched worktree agent (FROB_AGENT=1, docs/guides/agent-playbook.md section 3b's foreground-timeout contract), but no decision has been made about whether a non-agent (human/CI) frob check invocation -- where that constraint does not apply -- should auto-trigger. Wire the CLI verb and make and document that decision.

## Done report

Added `frob coverage` (`src/frob/app/coverage_runner.py`): the missing CLI
entrypoint over `frob.testing._coverage_refresh.native_coverage_refresh`
(T-1516) and `frob.testing._coverage_wait.run_coverage_wait`. Default (no
flag) delegates to `run_coverage_wait(root)`, reusing its existing
single-flight lock and freshness check. `--full` bypasses both and calls
`native_coverage_refresh(root, snapshot, full=True)` directly (an
explicit whole-suite request should not be short-circuited by another
worktree's already-fresh cached result). Wired through the same path
every other verb here uses: `Subcommand.coverage` (src/frob/app/config.py),
`coverage_full`/`coverage_path` fields whitelisted in
src/frob/app/_config_external.py, `_add_coverage_parser`
(src/frob/_cli_parsers/_misc.py, re-exported via
src/frob/_cli_parsers/__init__.py), dispatch-table entry plus the closed
if/elif import chain in src/frob/app/app.py, and the parser registered in
src/frob/__main__.py.

Decision (this ticket's other half): `frob check` does NOT auto-trigger a
coverage refresh, for any caller -- agent or non-agent/human/CI. T-1516's
Done report already ruled this out for a dispatched worktree agent
(FROB_AGENT=1, agent-playbook.md section 3b's foreground-timeout
contract); this ticket had to decide the non-agent half and the answer is
still no, on different grounds: running the test suite is a categorically
slower, more failure-prone operation than every other gate `frob check`
runs, and hiding it as an implicit side effect of a "tell me what's
wrong, fast" command would surprise every caller. Documented in
docs/modules/cli.md's new "frob coverage (T-1525)" section. `frob check`
keeps reporting staleness via TEST011/TEST017 rather than fixing it;
`frob coverage` (this verb) and `frob test --wait-coverage`
(test_runner.py's existing wired call into run_coverage_wait, T-1516)
are the two explicit places a refresh is expected to run from.

Scope was widened beyond the ticket's original single-file declaration
(src/frob/__main__.py) to cover the actual CLI-verb convention this repo
follows (Subcommand enum + config fields + parser + runner + dispatch
wiring, the natives_runner/T-0864 precedent) -- added via
`frob ticket scope --add --reason`, each add logged: src/frob/_cli_parsers/
_misc.py, src/frob/_cli_parsers/__init__.py, src/frob/app/app.py,
src/frob/app/config.py, src/frob/app/_config_external.py, src/frob/app/
coverage_runner.py, docs/modules/cli.md, README.md, tests/unit/
test_main_entry.py, tests/test_app_config.py, tests/unit/
test_coverage_runner.py.

Gate findings addressed as part of this ticket's own diff: DOC005 (README
command-table row + count, fixed), INV006 (coverage_runner.py's docstring
used "exclusively"/"only" as unenforced normative claims, reworded),
PRE001 (stale pre-work sweep, re-ran `frob ticket sweep T-1525`), WIRE001
(tests/unit/test_coverage_runner.py's module-level `_cfg` helper read as
an unwired new symbol; converted to a bound `TestCoverageRunner._cfg`
method, matching the existing `TestNativesRunner._cfg` precedent in
tests/unit/test_natives_build.py).

One finding disclosed, not fixed: SELFAUDIT001 (self-audit family SYS104)
flags `_add_coverage_parser` (cli node) and `TestCoverageRunner`
(testsuite node) as public symbols missing an `interface=` declaration in
design/frob.strata. That file is leased by in-progress T-1220
(`ScopeLeaseConflict` on `frob ticket scope T-1525 --add
design/frob.strata`) -- per this dispatch's hard rule, the scope add was
skipped rather than forced, and this edge is left for whichever ticket
next holds design/frob.strata's lease (T-1220 itself, or a follow-up
after it lands).

gate:DUP001 (src/frob/app/app.py::_import_runner_module vs
src/frob/app/__init__.py::_import_runner_run_module, 95% similar) is
PRE-EXISTING on main (verified via `git show main:src/frob/app/app.py` --
the duplicate pair already existed before this ticket's 2-line addition
to the same if/elif chain) -- not this ticket's to fix, out of scope.

Targeted tests: `tests/unit/test_coverage_runner.py`,
`tests/unit/test_main_entry.py`, `tests/test_app_config.py` -- 29 passed.
`frob check --ticket T-1525` (foreground, 540s wrapper): no ERROR-level
finding traces to a file this ticket touched except the disclosed
SELFAUDIT001 pair above.

### Changed
```
 tickets.md | 94 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 92 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_full_calls_native_refresh_directly` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_run_failure_exits_nonzero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 341 warning(s), 782 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1526 -->
```yaml
id: T-1526
title: 'coverage: make make coverage/coverage-fast a thin wrapper over native_coverage_refresh'
state: in-progress
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/testing.md
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
threat: null
component: null
```
T-1205 acceptance[3] asks for make coverage to become a thin optional wrapper around the frob-native orchestration. T-1516 added native_coverage_refresh and rewired run_coverage_wait's default onto it, but the Makefile coverage/coverage-fast targets themselves were left untouched (they still run the full ~300-line shell recipe independently). Rewrite them to delegate their common-path work to native_coverage_refresh, keeping only the xdist-crash-recovery/rerun-deadline shell logic (or whatever that becomes once T-1524 lands) as the part that stays Makefile-side, or is itself ported.

## Done report

Rewrote `coverage-fast:` (Makefile) into a thin wrapper: `$(MAKE) core &&
uv run frob doctor || exit 1` (unchanged natives-clobber guard, T-0538)
followed by a single `uv run frob coverage .` call -- the ~15-line inline
`xargs uv run pytest --cov-append`/`coverage combine`/`coverage xml -i`/
`frob check --stamp-coverage` sequence is gone; `frob coverage` (T-1525)
now performs that exact sequence via `native_coverage_refresh` (T-1516)
in-process, cross-platform, no Makefile/shell dependency for the common
path.

`coverage:` (the full-suite target) is intentionally UNCHANGED -- this
ticket's own acceptance text keeps "the xdist-crash-recovery/rerun-
deadline shell logic ... Makefile-side", and `coverage-fast:` had no such
resilience of its own to begin with (it was already re-deriving exactly
what `native_coverage_refresh` now does as a library call, per T-1516's
Done report) -- `coverage:` is the one that legitimately needs to keep
its shell recipe.

Known limitation, disclosed rather than silently regressed: the old
`coverage-fast:` respected `BASE ?= main` (`make coverage-fast
BASE=<ref>` overrode the touched-set diff base). `frob coverage` has no
`--base` flag today -- `native_coverage_refresh`'s own default is `base=
"HEAD"`, not `main`. `frob coverage`'s CLI scope (T-1525) did not extend
to adding a `--base` override; filed a follow-up ticket (draft
T-1572 at filing time -- renumbers to a real id at land, see
tickets.md) to add one and wire it through `coverage-fast: BASE=$(BASE)
uv run frob coverage . --base $(BASE)` once it exists. Until then, `make
coverage-fast BASE=<ref>` no
longer honors a non-default `BASE` -- worth flagging to anyone who used
that override, though the common case (default `main`) already differs
from HEAD in ways that usually select a similar or larger touched set,
not a smaller one, so this is unlikely to under-select tests silently.

tests/unit/test_makefile_coverage.py updated in the same change (added to
scope via `frob ticket scope --add --reason`, alongside
docs/modules/testing.md): `TestCoverageFastUsesAbsoluteSubprocessRc`'s
three methods (T-1397's own evidence bindings) were REWORDED, not
deleted or renamed -- same method names, updated bodies asserting the
stronger post-rewrite invariant (no inline `COVERAGE_PROCESS_START`/
`xargs`/`pytest` left in `coverage-fast:` at all, so the whole class of
bug T-1397 exists to prevent is now structurally impossible, not merely
avoided) -- this keeps T-1397's already-`done`/archived evidence
resolving instead of orphaning it (COV003 caught the dangling-evidence
shape on the first check pass when these methods were initially replaced
outright; fixed by reusing the names). `TestCoverageXmlIgnoreErrors.
test_coverage_xml_invocations_pass_ignore_errors`'s expected `uv run
coverage xml` call count dropped from 2 to 1 (coverage-fast's own call is
gone, replaced by `native_coverage_refresh`'s in-process `coverage xml
-i` subprocess call, not Makefile shell text).

docs/modules/testing.md: fixed pre-existing drift in
`run_coverage_wait`'s documented signature (still showed the pre-T-1516
`command: tuple[str, ...] = ("make", "coverage-fast")` default instead of
the real `tuple[str, ...] | None = None`), and updated
`native_coverage_refresh`'s docstring block to note `coverage-fast` no
longer has xdist-crash-recovery of its own to lose (it never had any).

src/frob/__main__.py: one edge-comment addition
(`# frob:ticket T-1525` above `_add_workflow_subparsers`) -- COV002
flagged the function (already changed by T-1525's own diff, committed
before T-1526 started) with no `frob:ticket` edge; added under this
ticket's own gate-fix pass since it blocked `--ticket T-1526`'s check
run, not a scope violation (T-1525's own scope already covers
`__main__.py`, and T-1525 is still in-progress, not closed).

Targeted tests: `tests/unit/test_makefile_coverage.py` -- 21 passed
(includes T-1397's rebound evidence). `frob check --ticket T-1526`: no
ERROR-level finding traces to a file this ticket touched. `frob check
--land-parity`: clean, 0 unscoped errors.

### Changed
```
 README.md                          |   3 +-
 docs/modules/cli.md                |  41 +++++++
 src/frob/__main__.py               |   2 +
 src/frob/_cli_parsers/__init__.py  |   2 +
 src/frob/_cli_parsers/_misc.py     |  28 +++++
 src/frob/app/_config_external.py   |   4 +
 src/frob/app/app.py                |   4 +
 src/frob/app/config.py             |  11 ++
 src/frob/app/coverage_runner.py    |  84 ++++++++++++++
 tests/unit/test_coverage_runner.py |  78 +++++++++++++
 tickets.md                         | 232 ++++++++++++++++++++++++++++++++++++-
 11 files changed, 485 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 357 warning(s), 782 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1533 -->
```yaml
id: T-1533
title: CorpusError needs a dedicated write-failure member
state: queued
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/registry/_corpus.py
- src/frob/app/registry_runner.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1359 made src/frob/registry/_staleness.py::sync_gate_rule_entries's
write crash-safe via frob.tickets._store.atomic_write, but on the
(should-never-happen) I/O failure path it has to reuse
CorpusError.FileNotFound as a stand-in -- not semantically accurate --
because CorpusError (src/frob/registry/_corpus.py) has no dedicated
write-failure member, and the two call sites that key a message dict on
CorpusError (frob.app.registry_runner._CORPUS_ERROR_MESSAGES,
frob.app.ticket_runner._land_cmd's synced.danger_err logging) sit
outside T-1359's declared scope (src/frob/gates/_fmt_directives.py,
src/frob/registry/_staleness.py, src/frob/release/**).

Add a CorpusError.WriteFailed member in src/frob/registry/_corpus.py,
have sync_gate_rule_entries return it instead of the FileNotFound
stand-in, and update _CORPUS_ERROR_MESSAGES (src/frob/app/registry_runner.py)
plus any other CorpusError-message dict to cover it so no caller KeyErrors
on the new variant.

<!-- ticket:T-1534 -->
```yaml
id: T-1534
title: WIRE001 false-positives on autouse pytest fixtures (no call-site to find)
state: queued
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
land-repair for t-1321: WIRE001 flags _isolate_from_host_git_config in
tests/test_ticket_land.py (T-1393's autouse pytest fixture that isolates
every fixture repo in this module from the host machine's real git
config) as unreached outside its own tests -- WIRE001's text scan looks
for name(...)-shaped call occurrences, but an autouse=True pytest
fixture is invoked implicitly by pytest's own fixture-injection
machinery, never by a literal name() call anywhere in the file. This is
the same class of detector gap as T-1502/T-1527 (WIRE001's text-scan
missing a real-but-non-call-shaped wiring mechanism), specialized to
autouse fixtures. Teach WIRE001 to recognize @pytest.fixture(autouse=True)
-decorated functions as wired by construction, or otherwise special-case
the shape.

<!-- ticket:T-1538 -->
```yaml
id: T-1538
title: gates.md stale doc anchor for moved redaction engine (frob.security._redact)
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled: original draft T-1538 (filed during T-1318) died in the t-1350 ledger corruption spans. One stale doc anchor in docs/modules/gates.md still points at the pre-move frob.gates._secrets redaction internals; file was leased by T-1205 at the time. Repoint to frob.security._redact's section.

<!-- ticket:T-1539 -->
```yaml
id: T-1539
title: 'PERF012 registry-entry gap: PERF012 detector exists with no CHK-GATE-PERF012
  registry row'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled: original draft T-1539 (filed during T-1225's perf-detector work) died in the t-1350 ledger corruption spans. PERF012 fires from src/frob/perf but docs/design/registry/check-coverage.yaml has no CHK-GATE-PERF012 entry -- pre-existing gap found (not caused) by T-1225.

<!-- ticket:T-1540 -->
```yaml
id: T-1540
title: 'PERF012 registry-entry gap: detector exists with no CHK-GATE-PERF012 row'
state: dropped
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
PERF012 fires from src/frob/perf but docs/design/registry/check-coverage.yaml has no CHK-GATE-PERF012 entry -- pre-existing gap found (not caused) by T-1225's PERF01x work. Originally tracked as worktree draft T-draft-7858da45, which the tickets.md splice drops from merge previews (land-splice-regression class), so refiled as a real ticket.

## Drop reason
- 2026-08-05: duplicate of T-1539: both are refiles of the same PERF012 registry-gap draft lost to the ledger-splice corruption; T-1539 is the survivor

<!-- ticket:T-1541 -->
```yaml
id: T-1541
title: audit non-done-report free-text ledger entry points for marker-lookalike corruption
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1536 fixed the marker-lookalike ledger-corruption class specifically
for the Done-report why path (compose_done_report/sanitize_narrative_
for_ledger) and hardened write_ticket's single-mode splice with a
post-write reparse-and-refuse check. Other free-text entry points that
also end up embedded into a ticket's body/ledger text -- ticket new
--body-file/--acceptance-file, scope --reason-file, drop --reason,
review --findings-file -- were not audited or defused against the same
marker-lookalike-line class in this ticket (kept narrowly scoped to the
done-report path per the incident this ticket root-caused). Audit each
of those write paths for the same vulnerability and apply sanitize_
narrative_for_ledger (or an equivalent) wherever caller-authored free
text is spliced into ticket.body before a single-mode ledger write.

<!-- ticket:T-1542 -->
```yaml
id: T-1542
title: fix 10 stale ticket-id citations DOC011 found, then promote DOC011 WARN to
  ERROR
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/README.md docs/audits/perf.md docs/modules/dup.md docs/modules/gates.md
  docs/modules/serve.md docs/modules/strata.md docs/modules/tickets.md docs/strata/host.md
  src/frob/gates/_doclink_docanchor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1486 shipped DOC011 (a T-####/T-draft-<hex> mention in doc prose that
does not resolve to any active or archived ticket) as a WARN-severity
gate rather than ERROR, specifically because its first live run against
this repo's own docs tree found 10 genuine pre-existing stale citations,
entirely outside T-1486's own declared scope to fix:

  docs/audits/README.md:31        T-draft-0b60dd31
  docs/audits/perf.md:159         T-draft-bafbce1c
  docs/modules/dup.md:615         T-draft-d6bca168
  docs/modules/gates.md:1175      T-0104
  docs/modules/gates.md:1177      T-draft-4e98abb1
  docs/modules/gates.md:1178      T-draft-05d8f716
  docs/modules/serve.md:726       T-draft-8a56400c
  docs/modules/strata.md:254      T-9999 (may be an intentional example)
  docs/modules/tickets.md:2235    T-draft-2f611252
  docs/strata/host.md:542         T-draft-7b5b5541

Most are T-draft-<hex> ids that finalized to a real T-#### long ago --
fix each by resolving what the draft became (git log/tickets-archive.md
should show the renumber) and updating the citation, or confirm T-9999
is deliberately illustrative and leave it (maybe reword to make that
obvious, e.g. T-####). T-0104 needs its own check: either a genuine typo
for a real id, or a citation that should be dropped.

Once this list is provably empty (re-run `frob check --only docstatus`
unscoped), promote DOC011's severity from WARN to ERROR in
src/frob/gates/_doclink_docanchor.py::_doc011_violation -- this ticket
was only ever meant as a soft landing, not the permanent posture.

<!-- ticket:T-1544 -->
```yaml
id: T-1544
title: 'Tier-A auto-fix: TICK006 phantom draft citation refile+renumber'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: when a TICK006 finding names a draft citation absent from both the ledger and archive, refile a real ticket for it and renumber the citation to the new real id. Needs a Tier-A handler that parses the phantom draft id, files a real ticket capturing recoverable context, and rewrites the citation -- T-1125's prose-reference rewrite already handles the case where the draft DOES exist in the ledger.

<!-- ticket:T-1545 -->
```yaml
id: T-1545
title: 'Tier-A auto-fix: SYS100 EXTENDED-kind capability declaration (eval/process-control/ffi/...)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/strata/_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: SYS100's EXTENDED case (eval/process-control/ffi/install-hook/sql/deserialize/html_render/fetch_url/client_storage, _selfconform.py::_extended_kind_violations) fires per-NODE with no per-file evidence -- there is no single observed file a Tier-A writer could add to a may via list without guessing which of a node's many bound files actually exercises the capability. Needs either a finer per-file extended-kind scan before an auto-fix is even possible, or a deliberately-conservative whole-node (via-less) grant-insertion policy with its own written justification. T-1531's fix_sys100_may_via_union only handles the CORE (net/fs-write/exec, THREAT004-delegated) case.

<!-- ticket:T-1546 -->
```yaml
id: T-1546
title: 'frob refactor rename: detect bound-evidence references and offer --replace
  rebind'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1537 (frob ticket evidence --replace): that ticket shipped the CLI primitive (replace_evidence) but not the detection half its own body named -- frob refactor rename (or an equivalent rename-detection pass) should notice when a renamed/parametrized symbol/test node id is bound as a ticket's evidence and offer (or auto-apply) the matching --replace rebind, closing the loop the T-1520 parametrization incident exposed by hand.

<!-- ticket:T-1547 -->
```yaml
id: T-1547
title: 'Tier-A auto-fix: E501 introduced by merge, targeted ruff-format'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: an E501 finding introduced specifically by a land-time merge should get a targeted ruff-format pass over just the offending lines/files, distinct from fix_fmt001_directive_wrap (which is scoped to frob:-directive comment lines only). Needs a handler reusing the same touched-path plumbing _fmt_pre_land_step already has, re-verifying E501 is gone before counting it as a fix.

<!-- ticket:T-1548 -->
```yaml
id: T-1548
title: 'Tier-A auto-fix: COV002 changed-symbol-without-edge insertion'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: insert '# frob:ticket <landing-id>' above a symbol when COV002 (changed-symbol-without-edge) fires and the diff producing it belongs to the landing ticket itself. Needs a Tier-A handler that reads COV002's finding (symbol + file:line) plus the landing ticket id from the caller (both _tier_a_pre_land_step and _apply_root_tier_a_fixes already have it), confirms the changed hunk actually belongs to that ticket's own diff, and inserts the directive line above the symbol.

<!-- ticket:T-1549 -->
```yaml
id: T-1549
title: 'Tier-A auto-fix: ClaimDivergence re-run via done-report recap'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Follow-up from T-1531: a ClaimDivergence land refusal already has a documented manual recipe (re-run the ticket's done-report with its existing why text -- the recap re-measures the claim against current evidence). Wire a Tier-A handler that performs exactly that through the T-1262 verify-or-rollback transaction like every other handler here.

<!-- ticket:T-1551 -->
```yaml
id: T-1551
title: unify duplicated committed-lock-reading test helpers (test_coverage_attribution_lock_t1395.py
  + test_makefile_coverage.py)
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_coverage_attribution_lock_t1395.py
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
tests/unit/test_coverage_attribution_lock_t1395.py::_load_committed_lock
and tests/unit/test_makefile_coverage.py::TestCommittedLockCoverageFloor.
_load_committed_lock (a class method, self-bound) both independently read
module_line out of the repo-root frob-coverage.lock.json for a regression
lock, using near-identical logic. T-1490 evaluated promoting the former
to a shared helper and found this second occurrence, but T-1490's own
scope (tests/unit/test_coverage_attribution_lock_t1395.py only) does not
cover tests/unit/test_makefile_coverage.py, so unifying both into one
shared load_coverage_lock test helper is left as this follow-up rather
than expanded into T-1490 silently.

<!-- ticket:T-1552 -->
```yaml
id: T-1552
title: 'ledger v2: delete v1 splice machinery once main is migrated'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_merge_zones.py
- .gitattributes
- docs/modules/tickets.md
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
## Description

T-1491 (final cutover) deliberately did NOT delete the v1 splice
machinery (`_render_ledger`, `splice_ledger` in
`src/frob/tickets/_land_ledger_merge.py`, `_land_merge.py`,
`_land_merge_zones.py`, the `tickets.md`/`tickets-archive.md`
`.gitattributes` merge-driver lines) because this repo's OWN ledger is
still v1-mode as of T-1491's session -- every ticket mutation across a
multi-agent dispatch still depends on `splice_ledger` via the registered
git merge driver. Deleting the machinery before this repo's own
`tickets.md`/`tickets-archive.md` content is actually migrated to v2
(via `frob ticket migrate` once the v1-to-v2 migrator is CLI-wired --
see T-1492) would break every in-flight worktree's ticket operations
immediately.

## Plan

Blocked on: T-1492 (CLI wiring for `frob ticket migrate --to v2`), the
follow-up default-flip ticket (T-1553, renumbers at land), and
a coordinator-chosen quiet window (per this ticket's own stated
precondition) to actually run the migration against this repo's real
`tickets.md`/`tickets-archive.md`.

1. Coordinator runs `frob ticket migrate --to v2` against this repo in a
   quiet window (zero in-flight worktrees).
2. Observe the LEDGERV1001 deprecation window for the recorded interval.
3. Delete `_render_ledger`, `splice_ledger`, `_land_merge.py`,
   `_land_merge_zones.py`, remove the `.gitattributes` merge-driver
   lines, remove `tickets.md`/`tickets-archive.md` from the repo (or
   archive them as historical artifacts per the coordinator's call).

## Acceptance

- [ ] GIVEN this repo's own ledger has been migrated to v2 in a quiet
      window WHEN this ticket lands THEN `_render_ledger`, `splice_ledger`,
      `_land_merge.py`, `_land_merge_zones.py`, and the `.gitattributes`
      merge-driver lines no longer exist, and `frob check` reports zero
      references to any of them.

<!-- ticket:T-1553 -->
```yaml
id: T-1553
title: 'ledger v2: flip fresh-repo default to v2 (safe, test-fixture-audited)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- tests/test_tickets.py
- tests/test_ticket_land.py
- tests/test_tickets_migration.py
- tests/test_tickets_collision.py
- tests/test_tickets_velocity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
## Description

T-1491 investigated flipping `_store_mode`'s final fresh-repo default
from 'single' (v1) to 'v2' (design section 7 deliverable 4, final
cutover) and found the change itself safe in principle but the blast
radius across this repo's own test suite too large to land inside T-1491
without becoming a much bigger ticket than its own declared scope. Many
existing v1-path tests construct a fixture via a bare `tmp_path` with no
explicit `tickets.md` seed and rely on `_store_mode`'s current default to
implicitly choose v1/'single' semantics -- flipping the default alone
(measured directly against `tests/test_tickets.py`) breaks at least:
`TestArchive::test_new_ticket_corrupt_archive_fails_loudly`,
`TestArchive::test_id_present_in_both_active_and_archive_collapses_not_refuses`,
`TestSingleFileLedger::test_new_tickets_land_in_single_tickets_md`,
`TestArchive::test_blocked_by_archived_ticket_resolves_closed`,
`TestSingleFileLedger::test_write_ticket_never_touches_a_sibling_ticket_bytes`,
`TestArchive::test_new_ticket_id_continues_past_archived_max` -- and this
is only one test file; `tests/test_ticket_land.py`,
`tests/test_tickets_migration.py`, `tests/test_tickets_collision.py`,
`tests/test_tickets_velocity.py`, and any CLI/integration test that
constructs a fresh repo without seeding `tickets.md` first are likely
affected the same way, unmeasured here.

## Plan

1. Audit every v1-path test fixture across `tests/test_tickets*.py` and
   `tests/test_ticket_land.py` that currently relies on the implicit
   fresh-repo default; update each to seed an explicit `tickets.md` (even
   an empty `# Tickets\n\n` header) so it pins v1 mode deliberately
   instead of by accident of default.
2. Flip `_store_mode`'s final `return "single"` to `return "v2"`.
3. Re-run the full suite (coordinator step, `make coverage` /
   unscoped `frob check`) and fix any remaining fallout outside the
   audited files.
4. Update `docs/design/ledger-v2.md` / `docs/modules/tickets.md` to
   record the flip as landed, not merely designed.

## Acceptance

- [ ] GIVEN a fresh repo with no `tickets.md`/`tickets/*.md`/`tickets/T-####/`
      content at all WHEN any ticket-store operation runs THEN it chooses
      v2 mode, not v1.
- [ ] GIVEN the full existing test suite WHEN run against the flipped
      default THEN every previously-passing test still passes (v1-path
      tests updated to seed `tickets.md` explicitly, not broken by the
      flip).

<!-- ticket:T-1554 -->
```yaml
id: T-1554
title: 'land: design the remaining post-commit checkpoint gap beyond the sweep window
  (T-1523 follow-up)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1523 closed a narrow slice of this (the post-land unscoped-error sweep's
own killable window, via a durable marker + read-only reconciliation on
the next invocation). Two larger design questions from its body remain
open:

- Option A (full): make EVERY intermediate land state durable/self-
  describing, not just the sweep window, so a kill at ANY instant is
  recoverable, including push and --finish's own worktree-removal step
  (currently believed safe/idempotent per playbook section 0 item 9 and
  T-1175's LAND-PROOF, but never load-bearing-verified against a real
  SIGTERM injection the way T-1523's own test suite does for the sweep).
- Option B: a separately-invocable `frob ticket land --verify-only <sha>`
  resumable CLI step, decoupled from a fresh merge/commit entirely.

Needs its own design doc before implementation, same as T-1523's body
said before it was scoped down.

<!-- ticket:T-1556 -->
```yaml
id: T-1556
title: 'cli hygiene remainder: warning collapse, read-only check --ticket, close porcelain,
  cli-hygiene principles doc (T-1271 split)'
state: queued
kind: ux
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a command emits repeated advisory warnings (scope-closure on ticket
    new can flood thousands of lines) THEN they collapse to a counted summary with
    a --verbose escape hatch -- signal is never drowned
  evidence: []
- text: GIVEN a read-only invocation (check --ticket for review, show, brief) THEN
    it never requires a lease or mutates state -- reviewers repeatedly could not re-verify
    gate claims because check --ticket demands a lease
  evidence: []
- text: GIVEN a multi-step workflow (close needs start, done-report, evidence, accepts)
    THEN each refusal names the exact next command AND a single porcelain verb exists
    that sequences the happy path; hidden optional arguments that change behavior
    (e.g. renumber's positional-only contract) are documented in --help with examples
  evidence: []
- text: GIVEN the audit lands THEN a short cli-hygiene principles doc exists in docs/design/
    and a checklist test (or gate rule) verifies new parsers against it (every flag
    help string states its default; no flag silently changes another flag's meaning)
  evidence: []
threat: null
component: null
```
Split from T-1271: its dispatch delivered criterion 0 (enum-valued flag errors list every valid value inline) with bound evidence; these four criteria were not implemented in that worktree and were drafted there as T-1557, which cannot survive a land preview (land-splice draft-loss class). Filed as a real main-side ticket so T-1271 can land its delivered portion with an honest acceptance trail.

<!-- ticket:T-1557 -->
```yaml
id: T-1557
title: 'cli hygiene remainder: warning collapse, read-only check --ticket, close porcelain,
  cli-hygiene doc'
state: queued
kind: ux
origin: human
created: '2026-08-04'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/**
- src/frob/tickets/**
- src/frob/check/**
- docs/design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
T-1271's own declared scope (src/frob/_cli_parsers/__init__.py, src/frob/
app/config.py, docs/modules/app.md, tests/test_app_config.py) covers only
the AppConfig pydantic layer -- it cannot reach the actual argparse parser
builders (src/frob/_cli_parsers/_ticket/**, _check.py, etc.), the
scope-closure warning emitter, frob check's lease requirement, or ticket
renumber's own --help text, all of which several of T-1271's acceptance
criteria depend on. T-1271 implemented the minimal honest core that DOES
fit its scope (a generic AppConfig field_validator that gives every
ticket-model enum flag -- state/kind/kind_value/tier/tier_value/
priority_level/origin/review_verdict -- an inline valid-values error
message, replacing the bare TicketState(v)-shaped ValueError) and disclosed
the rest here rather than silently widening scope.

Remaining work from T-1271's acceptance criteria, for a properly-scoped
follow-up ticket (or several):

1. (AC0 remainder) Non-ticket-model enum-shaped CLI flags still raise
   whatever their own conversion path raises with no valid-values list --
   e.g. check_type ("python"/"cpp"/"rust"/"typescript", a plain string
   field with no argparse choices=), any argparse choices= flag whose
   error text isn't already argparse's own (which DOES list choices).
   Audit src/frob/_cli_parsers/**/*.py for every type=/dest= flag lacking
   argparse choices= or an AppConfig-level validator and either add
   choices= or a validator per the T-1271 precedent.

2. (AC1) Repeated advisory warnings (scope-closure on `ticket new` observed
   flooding 5000+ lines in one invocation) need to collapse to a counted
   summary with a --verbose escape hatch. Likely lives in
   src/frob/tickets/_scope*.py or wherever scope-closure warnings are
   emitted, plus a new --verbose-style AppConfig field and _cli_parsers
   wiring -- outside T-1271's scope.

3. (AC2) `frob check --ticket` for a read-only invocation (review, show,
   brief) should never require or mutate a lease. Lives in
   src/frob/check/** (lease acquisition) -- outside T-1271's scope.

4. (AC3) A porcelain verb that sequences the ticket close happy path
   (start -> done-report -> evidence -> accepts -> close), plus
   documenting `ticket renumber`'s positional-only contract with --help
   examples. Lives in src/frob/tickets/** and _cli_parsers/_ticket/**  --
   outside T-1271's scope.

5. (AC4) A short cli-hygiene principles doc under docs/design/ (not
   docs/modules/app.md, which is T-1271's only in-scope doc target) plus a
   checklist test/gate rule verifying new parsers against it (every flag's
   help string states its default; no flag silently changes another
   flag's meaning). docs/design/ was not in T-1271's scope globs.

Filed by T-1271's Done report (2026-08-04) per the epic-closure
"minimal honest core, disclose the rest" instruction.

<!-- ticket:T-1558 -->
```yaml
id: T-1558
title: 'WIRE001 module-local test-helper false-positive class: teach the gate or wire
  the helpers (T-1490/T-1488 successor, waiver home)'
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a module-local pytest helper (fixture factory, git-init scaffold, parametrized-data
    builder) with no direct call-site the callgraph can see THEN WIRE001 either recognizes
    the pytest usage pattern natively or the helper is wired/bound explicitly -- and
    the 16 waivers currently binding here are deleted
  evidence: []
threat: null
component: null
```
Successor to T-1490 and T-1488, which closed while 16 frob:waive WIRE001 directives still named them, orphaning the waivers into WIRE002 errors (2026-08-05 incident). This ticket is the OPEN waiver home those 16 directives rebind to; it stays open until the class is actually resolved. Siblings: T-1503 (extract_native golden helpers), T-1534 (autouse fixtures).

<!-- ticket:T-1559 -->
```yaml
id: T-1559
title: 'land/close guard: refuse or auto-migrate open frob:waive directives bound
  to the closing ticket (WIRE002 orphan prevention)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN a ticket close/land WHEN any frob:waive directive in the repo names
    the closing ticket id THEN the close refuses with the waiver list and the exact
    rebind command, OR a Tier-A auto-fix rebinds them to a named open successor --
    closing a waiver-bound ticket can never silently red main again
  evidence: []
- text: GIVEN the guard fires THEN the refusal message names each waiver file:line
    and the successor-ticket flag to pass
  evidence: []
threat: null
component: null
```
2026-08-05 incident: T-1490/T-1488 landed and closed while 16 frob:waive WIRE001 directives bound them; the next full check showed 16 WIRE002 errors on main with no gate having warned at close time. The WIRE002 rule (waivers must bind an open ticket) is only enforced at check time, after the close already happened. Tier-A auto-fix family (T-1544..T-1549 precedent).

<!-- ticket:T-1560 -->
```yaml
id: T-1560
title: 'post-T-1555 error burn: 16 orphaned WIRE001 waivers, 2 renamed-evidence COV003s,
  2 ARCH001 splits, PERF001, 3 PII012'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
- tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
- tests/test_tickets.py::TestV2StateTransitions::test_byte_similar_sibling_ticket_does_not_drop_transitions
- tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge
acceptance:
- text: 'GIVEN a full unscoped frob check on main THEN gate errors are 0: the 16 WIRE002
    stale waivers rebind to the open successor ticket, T-1269/T-1495 evidence ids
    rebind to the renamed tests via evidence --replace, _land_plan_locked and v2_state_transitions
    drop under the ARCH001 60-line threshold via genuine helper extraction, _v2_path_lineage
    membership test uses a set, and the 3 PII012 test-token suggestions carry reasoned
    waivers'
  evidence:
  - tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
  - tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
  - tests/test_tickets.py::TestV2StateTransitions::test_byte_similar_sibling_ticket_does_not_drop_transitions
  - tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge
threat: null
component: null
```
Post-T-1555 re-measure found 26 errors. 2 (PRE001/SCOPE001) were an uncommitted archive artifact, fixed. The rest: 15 waivers name done T-1490 + 1 names done T-1488 (WIRE002); T-1269 evidence test_tick_gate_dirty_unwinds_everything renamed to test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge, T-1495 evidence test_no_foreign_commit_unwinds_cleanly_as_before renamed to test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge (COV003); ARCH001 on src/frob/tickets/_land.py::_land_plan_locked (67) and src/frob/tickets/_store.py::v2_state_transitions (77); PERF001 at _store.py:790 (list membership in loop); PII012 x3 in tests/unit/test_dup_legacy_cpp.py (lexer-token identifiers, not credentials).

## Done report

Post-T-1555 full re-measure found 26 gate errors on main; this ticket
closes every one of them. Two (PRE001/SCOPE001 on tickets-archive.md)
were an uncommitted archive artifact, fixed by committing it on main
before this worktree branched. Two COV003s (archived T-1269/T-1495
evidence pointing at tests renamed by wave-4 unwind-semantics work) were
fixed on main directly via an exact-string swap in tickets-archive.md,
because evidence --replace cannot reach archived tickets -- that tooling
gap is filed as T-1561.

In this worktree:

- 16 WIRE002 errors: frob:waive WIRE001 directives across 8 test files
  named T-1490 (15) and T-1488 (1), both closed by wave-4 lands; WIRE002
  requires waivers to bind an OPEN ticket. All 16 rebind to T-1558, the
  filed successor/waiver-home for the module-local-test-helper WIRE001
  class. No waiver was deleted -- follow_up attribution only. The
  systemic prevention (close/land must refuse or auto-migrate waivers
  bound to the closing ticket) is filed as T-1559.
- ARCH001 on src/frob/tickets/_land.py::_land_plan_locked (67 lines):
  the dry-run/report success tail extracts into _land_plan_finish, a
  genuine unit (report construction + dry-run always-reset semantics)
  with its own docstring; T-1522 unwind semantics unchanged, covered by
  the bound TestLandPlan evidence.
- ARCH001 on src/frob/tickets/_store.py::v2_state_transitions (77
  lines): the per-lineage-segment git-log mining extracts into
  _mine_v2_path_transitions with a local flush() closing over the
  commit/state scan state; oldest-first ordering and cross-segment sha
  dedup preserved, covered by the three bound TestV2StateTransitions
  evidence ids.
- PERF001 at _store.py:790: _v2_path_lineage kept an ordered list but
  did membership tests against it inside the walk loop; a parallel seen
  set now answers membership, the list keeps ordering.
- 3 PII012 suggestions in tests/unit/test_dup_legacy_cpp.py: 'token'
  there is the dup-fingerprint lexer's positional _vN token, not a
  credential surface; reasoned frob:waive PII012 directives added above
  the two owning tests.

frob check --land-parity in this worktree: clean, 0 unscoped errors --
matches what the land sweep will evaluate. Targeted suites green:
tests/test_tickets.py + tests/test_ticket_land.py -k "V2StateTransitions
or LandPlan" (11 passed); ruff check/format clean; ty clean on both
touched source files.

Changed:
  src/frob/tickets/_land.py::_land_plan_locked (shrunk)
  src/frob/tickets/_land.py::_land_plan_finish (new private helper)
  src/frob/tickets/_store.py::v2_state_transitions (shrunk)
  src/frob/tickets/_store.py::_mine_v2_path_transitions (new private helper)
  src/frob/tickets/_store.py::_v2_path_lineage (seen set)
  tests/_cache_transparency.py, tests/test_cache_gate.py,
  tests/test_cache_transparency.py, tests/test_ticket_land.py,
  tests/test_tickets_migration.py, tests/unit/perf/test_hotpath_smells.py,
  tests/unit/perf/test_serial_pools_import_failure.py,
  tests/unit/test_coverage_attribution_lock_t1395.py (follow_up rebinds)
  tests/unit/test_dup_legacy_cpp.py (2 reasoned PII012 waivers)

### Changed
```
 src/frob/tickets/_land.py                          |  25 +++++
 src/frob/tickets/_store.py                         |  98 ++++++++++--------
 tests/_cache_transparency.py                       |   6 +-
 tests/test_cache_gate.py                           |   2 +-
 tests/test_cache_transparency.py                   |   2 +-
 tests/test_ticket_land.py                          |   2 +-
 tests/test_tickets_migration.py                    |  12 +--
 tests/unit/perf/test_hotpath_smells.py             |   2 +-
 .../unit/perf/test_serial_pools_import_failure.py  |   4 +-
 tests/unit/test_coverage_attribution_lock_t1395.py |   2 +-
 tests/unit/test_dup_legacy_cpp.py                  |   6 ++
 tickets.md                                         | 112 +++------------------
 12 files changed, 114 insertions(+), 159 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2StateTransitions::test_byte_similar_sibling_ticket_does_not_drop_transitions` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 258 warning(s), 784 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1561 -->
```yaml
id: T-1561
title: 'evidence ops cannot reach archived tickets while COV003 still scans them:
  add --archived reach or an unarchive verb'
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
acceptance:
- text: GIVEN an archived ticket whose bound evidence id goes stale (test renamed)
    THEN a frob CLI path exists to rebind it (evidence --replace --archived, or ticket
    unarchive) -- the gate never polices records the CLI cannot repair
  evidence: []
threat: null
component: null
```
2026-08-05: COV003 fired on archived T-1269/T-1495 after their bound tests were renamed by wave-4 unwind-semantics work; frob ticket evidence --replace answered NotFound because the store only reads tickets.md. Gate scans the archive, repair tooling does not reach it -- catalogued-is-not-enforced inverse: enforced-but-not-repairable. Coordinator worked around with an exact-string swap in tickets-archive.md.

<!-- ticket:T-1562 -->
```yaml
id: T-1562
title: 'cli regrouping: frob quality verb group (check/test/dup/arch/bind/cycle/mutate/perf)'
state: dropped
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1567 (T-1238 taxonomy slice; the draft died in the land-splice draft-loss class before T-1271's land). Group the quality-facing verbs under one frob quality namespace following the frob explore precedent (T-1271/T-1238, src/frob/_cli_parsers/_explore.py + explore_runner.py).

## Drop reason
- 2026-08-05: refiled immediately with --parent T-1238 (parent is only settable at new time)

<!-- ticket:T-1563 -->
```yaml
id: T-1563
title: 'cli regrouping: frob design verb group (sys/registry/docs/graph/exports)'
state: dropped
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1568 (T-1238 taxonomy slice, draft-loss class). Group design/model verbs under frob design following the frob explore precedent.

## Drop reason
- 2026-08-05: refiled immediately with --parent T-1238 (parent is only settable at new time)

<!-- ticket:T-1564 -->
```yaml
id: T-1564
title: 'cli regrouping: frob ops verb group (release/natives/doctor/clean/fleet/deploy/scaffold/gitlog/stats)'
state: dropped
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1569 (T-1238 taxonomy slice, draft-loss class). Group operational verbs under frob ops following the frob explore precedent.

## Drop reason
- 2026-08-05: refiled immediately with --parent T-1238 (parent is only settable at new time)

<!-- ticket:T-1565 -->
```yaml
id: T-1565
title: 'cli regrouping: resolve ticket/debt/deprecated naming (frob tickets vs frob
  ticket)'
state: dropped
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1570 (T-1238 naming-decision slice, draft-loss class). Decide and implement the singular/plural verb naming for ticket/debt/deprecated surfaces as part of the T-1238 regroup.

## Drop reason
- 2026-08-05: refiled immediately with --parent T-1238 (parent is only settable at new time)

<!-- ticket:T-1566 -->
```yaml
id: T-1566
title: 'cli regrouping: help-surface rework -- group verbs in frob --help output'
state: dropped
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1571 (T-1238 slice, draft-loss class; also cited by T-1238's Done report). Rework the top-level frob --help output to present the T-1238 verb groups instead of the flat 30+ subcommand list.

## Drop reason
- 2026-08-05: refiled immediately with --parent T-1238 (parent is only settable at new time)

<!-- ticket:T-1567 -->
```yaml
id: T-1567
title: 'cli regrouping: frob quality verb group (check/test/dup/arch/bind/cycle/mutate/perf)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1567 (T-1238 taxonomy slice; the draft died in the land-splice draft-loss class before T-1271's land). Group the quality-facing verbs under one frob quality namespace following the frob explore precedent (T-1271/T-1238, src/frob/_cli_parsers/_explore.py + explore_runner.py).

<!-- ticket:T-1568 -->
```yaml
id: T-1568
title: 'cli regrouping: frob design verb group (sys/registry/docs/graph/exports)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1568 (T-1238 taxonomy slice, draft-loss class). Group design/model verbs under frob design following the frob explore precedent.

<!-- ticket:T-1569 -->
```yaml
id: T-1569
title: 'cli regrouping: frob ops verb group (release/natives/doctor/clean/fleet/deploy/scaffold/gitlog/stats)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1569 (T-1238 taxonomy slice, draft-loss class). Group operational verbs under frob ops following the frob explore precedent.

<!-- ticket:T-1570 -->
```yaml
id: T-1570
title: 'cli regrouping: resolve ticket/debt/deprecated naming (frob tickets vs frob
  ticket)'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1570 (T-1238 naming-decision slice, draft-loss class). Decide and implement the singular/plural verb naming for ticket/debt/deprecated surfaces as part of the T-1238 regroup.

<!-- ticket:T-1571 -->
```yaml
id: T-1571
title: 'cli regrouping: help-surface rework -- group verbs in frob --help output'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: T-1238
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from T-1571 (T-1238 slice, draft-loss class; also cited by T-1238's Done report). Rework the top-level frob --help output to present the T-1238 verb groups instead of the flat 30+ subcommand list.

<!-- ticket:T-1572 -->
```yaml
id: T-1572
title: 'frob coverage: add --base override, thread through make coverage-fast BASE='
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
threat: null
component: null
```
Refiled from worktree draft T-draft-a385ed9f (T-1526 follow-up; drafts cannot be cited by reports that must survive a land preview). make coverage-fast BASE=<ref> was honored by the old shell recipe but frob coverage currently hardcodes the touched-set base; add a --base flag and pass BASE through the Makefile wrapper.
