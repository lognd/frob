# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: queued
kind: bug
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0861
- T-0862
- T-0871
- T-0872
- T-0873
- T-0874
- T-0875
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
threat: null
component: null
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

<!-- ticket:T-0254 -->
```yaml
id: T-0254
title: 'frob deploy epic: auditable, isolated, provable OS-layer deployment'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- strata-core/**
- design/**
- docs/**
- tests/**
- Makefile
- tickets.md
threat: null
component: null
```
User mandate 2026-07-19: a frob deploy utility built into strata. The threat model: red teams compromise the one user that owns a service and nothing isolates that user -- lateral and vertical movement must be PROVABLY blocked, not hoped. The deployment sequence (idempotent install, status/health, uninstall with NO artifacts) must be auditable end to end, including an expensive opt-in VM-snapshot audit (VirtualBox) that is NOT part of make check. Scripts must tie into the model so hand edits are DETECTABLE through the strata checker, and the 'weird layer between the OS and the backend' (users, groups, units, ownership, ports) becomes provable architecture. Children: std.host OS-layer modeling -> movement-impossibility proofs + deploy script generation -> script<->model conformance gate -> VM snapshot audit harness -> real-service pilot (malmberg) remediating its awkward setup. Umbrella closes when all children close.

<!-- ticket:T-0260 -->
```yaml
id: T-0260
title: 'deploy pilot: model+generate+audit malmberg''s services, remediate the awkward
  setup'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0257
parent: T-0254
tier: ticket
sprint: null
scope:
- docs/**
- tests/**
- tickets.md
threat: null
component: null
```
T-0254 child 6 (proof on reality). Apply the full chain to malmberg (the real server product from pilot P3: server_api/ingest/cloudsync/faces/backup/display + media_store): extend design/malmberg.strata with std.host (dedicated service users per component, units, ownership of media_store paths, ports), prove HOST001/HOST002 movement-impossibility or record honest waivers, generate the deploy scripts, run the conformance gate, and if a VirtualBox environment is available run the full VM snapshot audit and attach the attestation. Remediate the current awkward setup step in malmberg's docs/scripts with the generated sequence. Work happens IN THE MALMBERG REPO per the break-and-report pilot protocol (frob-side gaps come back as tickets, filed serially by the coordinator); this frob-side ticket tracks the campaign and collects the gap list. Success = malmberg installs/uninstalls via generated scripts with a green conformance gate and a documented (or executed) VM audit path.

<!-- ticket:T-0395 -->
```yaml
id: T-0395
title: 'advisories: large-file residue after calibrated thresholds (T-0373)'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0373
- T-1072
- T-1076
- T-1074
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
After T-0373 re-thresholds frob-arch large-file to 800 lines / 60 (function), address the residue that still exceeds 800 lines among the 34 large-file advisories: real module splits, or accepted-with-reason for files that don't decompose cleanly. Acceptance: frob check arch large-file advisories at the calibrated threshold reduced to zero unresolved.

## Failure log
- 2026-07-28 attempt 1: 31 in-scope large-file findings after T-0373 calibration (43 total minus 12 strata/vet sibling-owned), up to 12047 lines (gates/__init__.py); large-file is unwaivable per docs/modules/gates.md, real splits needed -- too large for one pass, decomposition tickets filed

<!-- ticket:T-0397 -->
```yaml
id: T-0397
title: 'AUDIT REMEDIATION EPIC: North-Star integrity -- every green must be earned'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
Full-repo pessimistic capability audit (2026-07-20, 7 read-only auditors). North-Star: if frob check / a ticket-close / a strata proof passes, the thing it claims must ACTUALLY hold. The audit found the North-Star is violated in concrete ways across subsystems. Each subsystem audit gets an umbrella child holding its full findings table; each HIGH finding gets an actionable child. Findings files live in the audit run; this epic is the durable tracked home so the audit itself does not become an orphaned document (the exact failure mode that motivated it). Consolidation in progress as the 7 auditors land: tickets/testing (evidence integrity), strata (vacuous proofs), graph/edges, gates-accounting, gates-quality/security, vet (lexical resolution), lang/check/docs.

<!-- ticket:T-0802 -->
```yaml
id: T-0802
title: 'execute the 2026-10-01 navigation-command sunset: remove map/outline/xref/docs-search
  per T-0580 deprecation'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/docs_runner.py
- src/frob/__main__.py
- docs/modules/cli.md
acceptance:
- text: GIVEN the sunset date 2026-10-01 has passed WHEN this ticket is worked THEN
    the four deprecated navigation commands and their parsers, tests, and doc/test/export
    obligations are removed (or the sunset is explicitly re-adjudicated with the user),
    and no frob:deprecated directive for them remains
  evidence: []
threat: null
component: null
```
Sunset-execution ticket for the user's 2026-07-23 deprecation decision (T-0580, done). Stays OPEN until the sunset so the four frob:deprecated directives have a live ticket binding (DEPR002 requires ticket= to reference an open ticket -- T-0797 registration surfaced that the directives bound to the closed T-0580). Do not work before the sunset date.

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

<!-- ticket:T-1021 -->
```yaml
id: T-1021
title: 'WAIVE004 stale-waiver sweep: remove ~655 waivers matching 0 findings (full-run
  verified)'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/
- tests/
acceptance:
- text: GIVEN a full unscoped frob check THEN WAIVE004 warnings are zero and gate
    errors remain zero
  evidence: []
threat: null
component: null
```
WAIVE004 flags waivers that match 0 findings. Its own message warns the signal is only trustworthy from a FULL unscoped run -- verify against a full run, never --only. For each stale waiver: remove it, unless git history shows it guards a known-flaky/diff-scoped rule (leave those with a comment upgrading them to deliberate). Re-run full check after removal batches to confirm no gate flips to error (a waiver whose removal surfaces a live finding was NOT stale -- restore it and ticket the finding instead).

<!-- ticket:T-1038 -->
```yaml
id: T-1038
title: promote OPAQUE001 to ERROR-tier once frob's own 93-site first-turn-on set is
  fixed-or-waived
state: queued
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_opaque.py
- src/frob/vet/**
- src/frob/app/config.py
- src/frob/deploy/**
- src/frob/dup/**
- src/frob/fuzz/**
- src/frob/graph/**
- tests/**
threat: null
component: null
```
T-0665 landed OPAQUE001 (frob.gates._opaque.opaque_gate) at WARN-tier
per the T-0688/T-0973 first-turn-on promotion precedent: a first
measurement against frob's own tracked codebase found 93 real sites
after string-literal/comment false-positive filtering (147 before),
concentrated in test fixtures using dynamic getattr/setattr for
monkeypatch-style assertions, plus a handful of production sites
(src/frob/app/config.py, src/frob/deploy/_conform.py,
src/frob/dup/_pipeline.py, src/frob/fuzz/_signatures.py,
src/frob/graph/lock.py, src/frob/vet/_capability.py itself). This is
above the >25-site WARN-first threshold, so promoting straight to
ERROR was not safe to do in the same ticket.

Scope: audit each of the ~93 sites and either (a) rewrite to a static
name where the dynamic lookup was incidental, or (b) add an honest
`frob:waive OPAQUE001 reason="..."` naming why the site is a legitimate
runtime-resolved indirection (most test-fixture sites will fall here --
mock/monkeypatch dynamic attribute access is often intentional test
infrastructure, not an evasion risk). Once the WARN count reaches zero
real (unwaived) findings, promote opaque_gate's Severity from WARN to
ERROR in src/frob/gates/_opaque.py.

<!-- ticket:T-1062 -->
```yaml
id: T-1062
title: EXHAUST001/002 residual burn-down continuation (post T-1056)
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
Follow-up to T-1056, which closed only the src/frob/gates/__init__.py
slice (16 of 176 sites) of the EXHAUST001/002 turn-on debt burn-down.

Remaining sites (per T-1056's `frob check --only exhaustive_handling
--json` snapshot, minus the closed gates/__init__.py slice and minus the
two sibling-owned trees T-1056 skipped for coordination):

  8 src/frob/gates/_coverage.py
  6 src/frob/dup/_pipeline.py
  6 src/frob/tickets/_leases.py
  5 src/frob/deploy/_conform.py
  5 src/frob/mutate/__init__.py
  5 src/frob/outline/__init__.py
  5 src/frob/strata/_claims.py
  5 src/frob/tickets/__init__.py
  4 src/frob/app/check_runner.py
  4 src/frob/check/_python.py
  4 src/frob/gates/_docptr.py
  4 src/frob/gates/_secrets.py
  4 src/frob/mutate/_journal.py
  4 src/frob/strata/_host_isolation.py
  4 src/frob/strata/_native_staleness.py
  4 src/frob/testing/_collect.py
  3 src/frob/doctor.py
  3 src/frob/gates/_docblocks.py
  3 src/frob/gates/_prework.py
  3 src/frob/stats/_agentic.py
  3 src/frob/xref/__init__.py
  ...remainder spread 1-2 per file across app/gates/check/strata/testing.

Excluded from this list entirely (owned by sibling tickets, do not
recount without checking their status first): src/frob/perf/** (T-1053)
and src/frob/vet/** plus src/frob/gates/_opaque.py (T-1051).

Same disposition rule as T-1056/T-1022: each site gets a truthful
frob:raises/frob:callee-raises annotation (verify against what the
callable can actually raise), a cheap errors-as-values refactor
(tool_crash_result()-style at subprocess/parse boundaries, or a fail-open
try/except matching the function's own documented degrade contract), or a
reasoned frob:waive -- never a blanket suppression. Re-run
`frob check --only exhaustive_handling --json` at the start to get a live
count before starting (T-1056's counts will have drifted).

<!-- ticket:T-1074 -->
```yaml
id: T-1074
title: 'arch: triage 800-2000 line file residue (T-0395 remainder tier 3)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- tests/test_testing.py
- docs/modules/testing.md
- tests/test_gates.py
scope_changes:
- op: add
  glob: tests/test_testing.py
  reason: 'T-1074''s real split of frob.testing._collect into _collect_rust/_collect_ts/_collect_cpp
    moved shutil.which() call sites out of _collect.py; tests/test_testing.py monkeypatches
    collect_mod.shutil by module attribute and must be repointed at the new modules
    to keep passing, per the T-1171 split precedent (repoint tests that monkeypatch
    a moved function via the package attribute).

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/testing.md
  reason: 'T-1074''s real split of frob.testing._collect into _collect_rust/_collect_ts/_collect_cpp
    moved shutil.which() call sites out of _collect.py; tests/test_testing.py monkeypatches
    collect_mod.shutil by module attribute and must be repointed at the new modules
    to keep passing, per the T-1171 split precedent (repoint tests that monkeypatch
    a moved function via the package attribute).

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_gates.py
  reason: 'tests/test_gates.py::TestCppSourceAccurateCollection._mock_ctest monkeypatches
    collect_mod.shutil by module attribute; must be repointed at frob.testing._collect_cpp
    after the T-1074 split moved the cpp collector out of _collect.py.

    '
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_parses_and_caches
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_parses_and_caches
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_parses_and_caches
threat: null
component: null
```
Filed from T-0395 (failed as too large for one pass). Remaining in-scope
large-file residue under 2000 lines (frob-core/src/lib.rs 2277 --
excluded, native crate, separate toolchain/ownership from the python
gates split above; list the rest as of 2026-07-28):
src/frob/tickets/_models.py (1658), src/frob/arch/_patterns.py (1486),
src/frob/app/check_runner.py (1468), src/frob/gates/_docblocks.py (1460),
src/frob/arch/_python.py (1267), src/frob/testing/_collect.py (1267),
src/frob/gates/_protocol_summary.py (1244), src/frob/tickets/_leases.py
(1191), src/frob/app/config.py (1118), src/frob/gates/_secrets.py (1108),
src/frob/graph/dsl.py (1033), src/frob/gates/_docptr.py (1000),
src/frob/gates/_registry_exhaustiveness.py (993), src/frob/check/__init__.py
(958), src/frob/check/_python.py (936), src/frob/graph/__init__.py (869),
strata-core/src/lib.rs (869, native crate -- confirm with the strata
sibling ticket owner before touching), src/frob/app/sys_runner.py (851),
src/frob/perf/_rules.py (845), src/frob/arch/_rust.py (838),
src/frob/graph/callgraph.py (830), src/frob/perf/_effect_summaries.py
(823), src/frob/gates/_refs.py (818). Triage into real splits vs.
files that genuinely do not decompose cleanly (record the specific
reason per file, per this ticket's acceptance framing) -- do not attempt
all ~20 in one diff; group by subsystem and land incrementally, full
suite verification per group.

## Done report

Re-measured LARGE001 (frob check --only archgate, 2026-07-29) over this
ticket's remaining scope, excluding src/frob/gates/** (owned by T-1174)
and src/frob/tickets/** (owned by T-1171) per dispatch instructions. Both
excluded trees' offenders (gates/__init__.py 8128, tickets/_land.py 4866,
tickets/_models.py 1868, tickets/_leases.py 1344, tickets/_evidence.py
1205, tickets/__init__.py 1264) are left untouched, for the sibling
tickets.

REAL SPLIT LANDED this pass: src/frob/testing/_collect.py (1326 lines at
filing, the largest genuinely-mine offender) split by language into four
files:
- src/frob/testing/_collect.py (506 lines) -- python collector only
- src/frob/testing/_collect_rust.py (299 lines, new)
- src/frob/testing/_collect_ts.py (231 lines, new)
- src/frob/testing/_collect_cpp.py (398 lines, new)
- src/frob/testing/_collect_shared.py (65 lines, new) -- cache/walk
  primitives (_prune_dirnames/_load_cache/_store_cache) every language
  collector shares

The four languages (python/rust/ts/cpp) were fully independent code paths
inside the old file -- verified zero cross-language call edges before
splitting (each language's private helpers are only called from that
language's own section and its own public collect_<lang>_tests). Every
name the old module defined is re-imported into _collect.py (module-level,
`frob:ticket T-1074` marked, not exported via __all__) so every existing
`from frob.testing._collect import <name>` call site (frob.testing.__init__,
frob.gates.__init__, and ~40 call sites across tests/test_testing.py,
tests/test_testing_collect.py, tests/test_gates.py, src/frob/strata/
_native_staleness.py) keeps resolving unchanged -- zero caller-visible
behavior change, matching the T-1171 tickets/_evidence.py split precedent
this repo already established.

Repointed:
- docs/modules/testing.md's `frob:describes ...::collect_rust_tests`
  anchor to the new module path (the only tracked describes-anchor that
  moved; collect_ts_tests/collect_cpp_tests were never tracked).
- ~28 `frob:tests src/frob/testing/_collect.py::collect_{rust,ts}_tests`
  directive comments in tests/test_testing.py + tests/test_gates.py to
  the new module paths (DRIFT002-driven, all confirmed via `frob check
  --ticket T-1074`).
- 4 test helpers that monkeypatch a collector's module-level `shutil`/
  `run_argv`/`_cargo_env` by attribute (tests/test_testing.py's rust/ts/
  cpp classes, tests/test_gates.py's TestCppSourceAccurateCollection.
  _mock_ctest) to import the language-specific module instead of
  `frob.testing._collect` -- these are attribute-patch call sites, not
  new tests; each caught immediately as a hard `AttributeError` when run,
  not a silent pass.
- INV006 waivers carried verbatim (T-0585 calibration-batch precedent)
  onto all three new files.
- One genuinely pre-existing DUP001 (src/frob/testing/_collect_ts.py::
  _find_ts_test_files, 95% similar to frob.strata._selfconform.
  _repo_files_excluding_skip_dirs) surfaced only because the file became
  touched -- waived with a reason noting it predates this split and a
  real extraction is separate, deliberate scope.

DISPOSITIONS for the rest of the T-1074 file list still in-scope
(src/frob/, excluding gates/** and tickets/**), re-measured this pass --
recorded here per the ticket's own "accepted-with-reason is a valid
outcome" framing rather than forced into unsafe splits under one dispatch
budget:

- src/frob/graph/callgraph.py (830), src/frob/graph/__init__.py (869),
  src/frob/graph/dsl.py (1033): one graph-resolution pipeline each
  (build_call_graph -> _resolve_edges -> _resolve_edges_python is a single
  mutually-recursive call chain; graph/__init__.py's ingest/prune/finalize
  helpers all share one sqlite connection threaded through every private
  function). Splitting would separate tightly-coupled steps of one
  algorithm across files, adding import indirection with no cohesion gain.
  Accepted with reason; not split this pass.
- src/frob/perf/_rules.py (845), src/frob/perf/_effect_summaries.py (823):
  each is one token-level static-analysis algorithm (PERF001-004 detection,
  effect-graph inference) whose private helpers are single-purpose steps
  of that one algorithm, not independent concerns. Accepted with reason.
- src/frob/arch/_rust.py (838): one tree-sitter node-walker family for a
  single language's AST shape, mirroring the existing arch/_python.py
  split-by-language convention already in place. Accepted with reason.
- src/frob/dup/_pipeline/_fingerprint.py (805, just over threshold): one
  fingerprinting pipeline (r3/r4/r5 rungs feeding one bucket/pair/verify
  chain). Accepted with reason.
- src/frob/testing/_collect.py's own remaining 506 lines: already under
  threshold after this pass's split -- no further action needed.
- src/frob/vet/_capability.py (5938) and src/frob/vet/_capability_registry.py
  (2923): both over 2000 lines, outside this ticket's "under 2000 lines"
  framing at filing -- left for a dedicated follow-up ticket (not filed
  this pass; budget did not allow investigating a safe split boundary for
  either).

NOT investigated this pass (budget): src/frob/app/check_runner.py (1597),
src/frob/app/config.py (1158), src/frob/app/sys_runner.py (1028),
src/frob/arch/_patterns.py (1486), src/frob/arch/_python.py (1539),
src/frob/check/__init__.py (958), src/frob/check/_python.py (970),
src/frob/doctor.py (907), src/frob/strata/*.py (multiple offenders
841-2485 lines), src/frob/_cli_parsers/_ticket.py (1025),
src/frob/app/ticket_runner/_verify.py (949). These remain LARGE001 WARN
findings (advisory, not gating) -- disclosed here rather than silently
dropped; a follow-up ticket covering this residue is warranted but not
filed this pass to avoid re-deriving the same "re-measure first" framing
T-1074 itself used -- the next dispatch of this series should re-run
`frob check --only archgate` fresh rather than trust this list, since
siblings are actively splitting gates/**/tickets/** concurrently and the
overall LARGE001 count moves every wave.

Verification: `frob check --ticket T-1074` clean (0 errors, was 0 errors
after fixing DRIFT002/DUP001/INV006/PRE001 introduced by the split itself)
across gates-native/gates-fast/gates-security (chunked, see command log).
`pytest tests/test_testing.py tests/test_testing_collect.py` (321 tests)
and the cpp-collector slice of tests/test_gates.py (18 tests) all pass.
ruff clean on every touched file (both PATH ruff and `uv run ruff`).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_parses_and_caches` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_parses_and_caches` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_parses_and_caches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 6475 warning(s), 494 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1083 -->
```yaml
id: T-1083
title: 'arch: abstraction-opportunity remaining single-file packages extraction (T-0393/T-1067
  remainder, 23 findings)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/
- src/frob/dup/
- src/frob/lang/
- src/frob/perf/
- src/frob/process/
- src/frob/render/
- src/frob/serve/
- src/frob/strata/
- src/frob/testing/
- src/frob/tickets/
- src/frob/vet/
threat: null
component: null
```
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). The
remainder of the 84 abstraction-opportunity findings not covered by this
pass's sibling per-package tickets (gates/**, arch/**, app/**) is spread
one-or-two-per-file across ~19 small/standalone modules, ~23 findings
total: `check/_native.py` 1, `check/_python.py` 1,
<!-- frob:waive DOC006 reason="describes the per-file finding count as measured at filing time (T-1067); dup/_pipeline.py has since been split into a package (T-1099-era), rewriting would misrepresent what was actually filed" -->`dup/_pipeline.py` 2,
`lang/__init__.py` 1, `lang/_extract.py` 1, `lang/_walk_kotlin.py` 1,
`perf/_loop_effects.py` 1, `process/parsers/cargo.py` 1,
`render/_renderer.py` 1, `serve/_tools.py` 1, `strata/_compliance.py` 1,
`strata/_export.py` 1, `strata/_selfconform.py` 1, `testing/_collect.py` 1,
`tickets/__init__.py` 3, `tickets/_journal.py` 1, `vet/_capability.py` 1,
`vet/_ecosystem.py` 1, `vet/_lockfile.py` 1.

Two of these are almost certainly detector-precision FP classes, not
genuine dup -- triage these FIRST since they may be quick T-1068-style
detector fixes rather than code changes:

- `testing/_collect.py`: `collect_python_tests`/`collect_rust_tests`/
  `collect_ts_tests`/`collect_cpp_tests` sharing `(Path) -> Result[...]`
  is textbook per-language-parity shape, but T-1068's
  `_is_language_parity_family`/`_LANGUAGE_TAGS` only recognizes the
  segments `py`/`rust`/`kt`/`ts`/`cpp` -- `python` never matches `py` as
  a whole underscore-delimited segment, so this family falls through
  uncaught. Likely fix: extend `_LANGUAGE_TAGS` (or add a synonym map --
  `python`->`py`, `typescript`->`ts`, `kotlin`->`kt`, `cplusplus`->`cpp`)
  in `src/frob/arch/_python.py`, in scope src/frob/arch/ not this
  ticket's scope -- file as its own small detector ticket instead of
  fixing it here.
- `render/_renderer.py`: `RenderWriter.heading`/`.subhead`/`.good`/
  `.warn`/`.muted` are each ALREADY documented (existing `frob:invariant`
  comments at each site) as deliberate same-name thin forwarders to the
  identically-named module-level `frob.render._elements`/`_palette`
  function -- a documented, load-bearing naming convention (the vocabulary
  namespace pattern T-0448/T-0460 established), not an accidental
  duplicate. Extracting a shared `_forward(name, fn, text)` wrapper would
  likely make this WORSE (indirection with no real dedup, since each
  forwards to a different target). Recommend accepting this as a new FP
  class and filing a small T-1068-style detector ticket (recognize a
  same-name call-through to an identically-named imported symbol as
  non-actionable) in scope src/frob/arch/, not extracting here.

The rest (`tickets/__init__.py`'s 3 groups, `vet/_capability.py`'s
4-member `walk`/`walk`/`walk`/`walk` group -- likely local nested-closure
tree-walk helpers with different captured free variables per T-1067's
sibling arch-package ticket note, worth the same "read before extracting"
caution -- and the remaining single-group files) are smaller, more
plausible genuine-duplication candidates; read each before deciding.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity, excluding gates/**, arch/**, app/**) before
starting; other tickets may land in the interim and change the count.

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

<!-- ticket:T-1171 -->
```yaml
id: T-1171
title: 'arch: extract tickets/__init__.py done-report/review/drop/attach family +
  split _land.py -- T-1152 residue'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
threat: null
component: null
```
T-1152 extracted ONE family (evidence/transition) out of
src/frob/tickets/__init__.py into src/frob/tickets/_evidence.py
(__init__.py: 2333 -> ~1250 lines). Remaining work from T-1152's own
original scope, not touched this dispatch:

- done-report/review/drop/attach family (brief_ticket, mutate_labels,
  record_review, attach, drop_ticket helpers, compose_done_report/
  set_done_report, record_failure) -- still in
  src/frob/tickets/__init__.py.
- src/frob/tickets/_land.py (4866 lines, untouched across T-1108/T-1122/
  T-1123/T-1151/T-1152) still needs its own split into cohesive
  preflight/merge-splice/verify/sweep submodules per T-1108's original
  plan, before LARGE001 stops flagging it.

Follow the same pattern each dispatch: one cohesive family per land,
private module re-exported from __init__ via explicit imports, zero
caller-visible behavior change, existing tests as the safety net, carry
frob:ticket/frob:doc/frob:tests directives verbatim, repoint
docs/modules/tickets.md's frob:describes anchors and any tests/*.py
frob:tests directives at the new module path, add frob:ticket edges to
any test class/method a directive-repoint touches (COV002), carry a
file-level INV006 split-module waiver (T-0585 calibration-batch
precedent) if the moved prose trips it, watch for tests that monkeypatch
a moved function via the PACKAGE attribute (tickets_mod.<name>) -- those
need a late `from frob.tickets import <name>` inside the moved function
body instead of a module-top-level binding (two such hazards hit T-1152:
write_ticket and the bare `subprocess` module object itself).

<!-- ticket:T-1173 -->
```yaml
id: T-1173
title: 'bug: cross-worktree lease not renamed when a draft ticket is renumbered at
  land'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_new_renumber.py
threat: null
component: null
```
Observed while landing T-1165/T-1172 in the same worktree: frob ticket start T-draft-XXXXXXXX records a lease at .git/frob-leases/T-draft-XXXXXXXX.json. When the draft is renumbered to a real id (T-1172) at land time, the lease file is never renamed/migrated -- a subsequent frob check --ticket T-1172 in the SAME worktree that started it fails with 'no recorded lease', even though the worktree genuinely holds the ticket. Worked around by hand-copying the lease json with the new id; the renumber path should do this automatically.

<!-- ticket:T-1174 -->
```yaml
id: T-1174
title: 'arch: split remaining ~10 gate families out of src/frob/gates/__init__.py
  (8128 lines) -- T-1170 residue'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
threat: null
component: null
```
T-1170 extracted ONE cohesive family (DOC001/DOC002 -- `doclink_gate`/
`docanchor_gate` plus their private helpers) into
`src/frob/gates/_doclink_docanchor.py` (gates/__init__.py 8401 -> 8128
lines), one-family-per-land per the T-1072/T-1140/T-1159 discipline.
Budget did not allow the other ~10 remaining families this drive's own
ticket named. gates/__init__.py is still 8128 lines, well above the
large-file threshold.

Still remaining, in the same one-family-per-land shape:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines)
- DUP00x (dup_gate + helpers, ~500 lines)
- FUZZ00x (fuzz_gate)
- INV00x (inv006_gate + helpers)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1170 close
with silent residue, per TICK011.

<!-- ticket:T-1175 -->
```yaml
id: T-1175
title: 'tickets: one-verb lifecycle -- frob ticket work (setup) and land absorbing
  fmt + sync-interface + Tier-A fixes + on-main proof + finish'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- docs/guides/agent-playbook.md
acceptance:
- text: GIVEN frob ticket work T-#### WHEN run from root THEN it creates/reuses the
    named worktree, verifies base freshness against main tip, builds natives, and
    starts the ticket -- one command replacing playbook contract steps 1-2 plus start
  evidence: []
- text: GIVEN frob ticket land WHEN run THEN it first runs frob fmt on touched files,
    sys sync-interface (applying the interface diff in-land), and the T-1137 Tier-A
    fix handlers; after landing it prints a machine-checkable proof line (land hash
    + is-ancestor-of-main + ticket state on main) and offers --finish to remove the
    worktree only when every series land verifies
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: agents should only run frob commands and write content requiring actual thinking. The remaining per-ticket ritual (playbook section 0) is ~10 mechanical steps; steps 1-2, 5, and 9 are pure command sequences frob can own. This collapses them into two verbs. The playbook contract section then shrinks to: work, think, land. Absorb-not-add: reuse the existing fmt/sync-interface/fix-engine/land machinery, no new subsystems.

<!-- ticket:T-1176 -->
```yaml
id: T-1176
title: 'gates: named waiver presets -- frob:waive RULE preset=<name> resolving to
  one documented reason text'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
acceptance:
- text: GIVEN a frob:waive directive using preset=<name> WHEN gates evaluate it THEN
    the reason resolves from a single documented preset table (docs/modules/gates.md
    section, machine-read), behaves identically to the inline reason, and an unknown
    preset name is an error
  evidence: []
- text: GIVEN the existing calibration-batch INV006 text THEN it becomes preset=split-carried-prose
    and the repo's 10+ verbatim copies are migrated to it in the same land
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: remove boilerplate agents hand-write. The 8-line INV006 calibration-batch waiver text has been copy-pasted 10+ times this drive (0abc4e3a lineage), and the T-1099 REF002 split-fragment text 7+ times. A preset is NOT a blanket waiver: each site still carries an explicit per-site directive naming rule + preset; the preset only deduplicates the REASON prose, which the NO DUPLICATION principle applies to as much as code. Reason-required stays intact -- a preset name must resolve to a real documented reason.

<!-- ticket:T-1177 -->
```yaml
id: T-1177
title: 'fix-engine: Tier-A auto-carry of split-carried waivers (T-1137 child; coordinator
  decision recorded)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
acceptance:
- text: GIVEN a module split moves prose verbatim from a file whose waiver covered
    it (T-1134's find_carried_waiver detects the source) WHEN frob check --fix runs
    THEN the carried waiver is applied automatically at the new site, citing the source
    file and preset, and the fix report discloses every carry
  evidence: []
- text: GIVEN prose that is NOT a verbatim move from an already-waived source THEN
    --fix never inserts any waiver (the no-auto-waive anti-goal stands for everything
    else)
  evidence: []
threat: null
component: null
```
Coordinator decision 2026-07-29 under user-delegated authority: carrying an EXISTING waiver whose prose moved verbatim preserves a prior explicit human disposition -- it is not a new waiver, so it does not violate T-1137's never-auto-waive anti-goal, which continues to bind for every other case. Evidence: 6+ hand-carries this drive (3 by the coordinator in one day, 0abc4e3a; 2 rust files missed and redded main). Builds directly on T-1134's detector; pairs with the preset ticket so the carried text is one reference, not a copy.

<!-- ticket:T-1178 -->
```yaml
id: T-1178
title: 'tickets: complete the auto-commit family -- close/done-report/evidence/requeue
  transitions commit like start/new/drop/fail'
state: queued
kind: bug
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_leases.py
acceptance:
- text: GIVEN any ledger-writing ticket verb run on main WHEN it completes THEN its
    transition is committed automatically (T-1130's commit_ticket_ledger_change, --no-commit
    opt-out), so no concurrent land preflight reset can ever discard a completed verb's
    write
  evidence: []
threat: null
component: null
```
REFILE: the original filing (commit 46a115c4, first allocated id clobbered by a concurrent land's renumber -- see the sibling id-allocation bug ticket) recorded the 2026-07-29 incident: the coordinator's T-0329 epic close wrote the ledger uncommitted (close is not in T-1130's new/drop/fail set), a concurrent agent land preflight ran git reset --hard in root, and the close silently vanished -- caught only by T-1131's doctor stale-lease scan. Extend commit_ticket_ledger_change to every remaining ledger-writing verb: close, done-report, evidence add, requeue, and any mutation verbs still uncommitted. Closes the reset-eats-uncommitted-coordinator-work class (T-0948 lineage) at the verb layer.

<!-- ticket:T-1179 -->
```yaml
id: T-1179
title: 'land: draft renumbering allocated an id already taken on main, clobbering
  a main-side block (T-1090 gap on the land path)'
state: queued
kind: bug
origin: human
created: '2026-07-29'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets_collision.py
acceptance:
- text: GIVEN a worktree land whose draft renumbering runs WHEN main has allocated
    new ids since the worktree's last merge THEN renumbering reads the id ceiling
    from CURRENT main (not the worktree's stale view) under the ledger lock, and a
    would-be collision with any existing main-side id is impossible by construction,
    proven by a regression test reproducing the 2026-07-29 shape
  evidence: []
- text: GIVEN the splice THEN a landing block may never overwrite a different-titled
    existing block under the same id -- a detected id/title mismatch refuses the land
    loudly instead of silently replacing content
  evidence: []
threat: null
component: null
```
2026-07-29 incident (5th id-collision, first SINCE T-1090): coordinator filed a ticket on main (46a115c4, auto-committed); minutes later T-1170's land (17c6ca89) renumbered its residue draft to the SAME id, and the splice replaced the coordinator's block wholesale -- content lost from the live ledger (recovered from git history and refiled). T-1090's atomic allocation apparently guards concurrent new_ticket calls against a shared counter but the LAND-path renumber derived its next-id from the worktree's stale ledger view. Two independent guards per acceptance: allocation-from-current-main under lock, and a splice-level id/title-mismatch refusal (defense in depth, T-0959 style).

<!-- ticket:T-1180 -->
```yaml
id: T-1180
title: 'coverage pipeline: flake-tolerant end-to-end -- serial rerun of failures,
  stale-data cleanup, deflation guard before stamp'
state: queued
kind: bug
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/testing/**
- src/frob/gates/**
- tests/test_coverage.py
acceptance:
- text: GIVEN make coverage WHEN the parallel suite has failures THEN the failed tests
    are re-run once serially without coverage-halting, and only still-failing tests
    fail the target -- load-sensitive flakes (the four known self-model/serve-watch
    specimens) no longer block combine/xml/stamp
  evidence: []
- text: GIVEN combine runs THEN stale .coverage* files from prior aborted runs are
    removed first and the combine reports consuming every fresh worker file; a coverage.xml
    whose module-coverage fraction is below a sanity floor refuses to stamp (extending
    TEST011's deflation heuristic into a hard pre-stamp guard)
  evidence: []
threat: null
component: null
```
Three consecutive coverage runs failed to produce a trustworthy coverage.xml on 2026-07-28/29: (1) corrupted coverage shim broke combine silently; (2+3) four load-sensitive tests (three strata self-model + serve-watch tick, all pass in isolation, verified twice) fail only under xdist+coverage parallelism and halt the recipe before combine; a manual combine then consumed 2 of 7 data files (stale-file skip). The TEST005 bucket (~600 warnings) cannot be honestly recounted until this pipeline is deterministic. Also route the notification-exit-code mismatch to the record: background make reported exit 0 twice while make actually failed -- do not trust bg exit codes for make pipelines, read the output tail.
