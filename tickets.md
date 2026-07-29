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

<!-- ticket:T-0329 -->
```yaml
id: T-0329
title: 'EPIC arch multi-language: normalized code model + Rust/TypeScript/Kotlin adapters'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: epic
sprint: null
scope:
- src/frob/arch/**
- src/frob/lang/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0329 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
threat: null
component: null
```
frob arch today has per-language walkers (_python.py, _cpp.py) only. To extend cleanly (not N copies of each check), introduce a NORMALIZED CODE MODEL: a language-agnostic view (module, class, function, method, param, branch, loop, call, import, override, field-access, return, raise/throw, catch) that each language adapter maps its tree-sitter grammar onto. Checks are written ONCE against the model; adapters supply per-grammar node-type maps. Then add adapters for TypeScript, Rust, Kotlin (Kotlin needs tree-sitter-kotlin added to frob.lang; ts/rust/cpp/c already parse via tree-sitter-language-pack). Language-specific checks (Rust must_use/ownership, TS any/strict-null) live in per-language extensions on top of the shared model. Acceptance: an arch check written once fires correctly across python+ts+rust+kotlin on equivalent code; Kotlin grammar wired; the existing python/cpp checks refactored onto the model with no regression. Children: normalized-model, ts-adapter, rust-adapter, kotlin-grammar+adapter.

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

<!-- ticket:T-1006 -->
```yaml
id: T-1006
title: widespread pre-existing test failures block make coverage completion (~118
  fails, non-cov-caused)
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
threat: null
component: null
```
Found while working T-0997 (coverage pipeline fix): a real, fresh `make
coverage` run in a clean worktree (merged to main tip) shows ~118 test
failures that are NOT caused by coverage instrumentation -- reproduced
several individually WITHOUT --cov and they still fail (e.g.
tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations,
tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root).
These span registry-reconciliation exhaustiveness self-checks
(patterns/compliance/secrets/supply_chain/weaknesses/system_design all
report real violations against this worktree's live tickets.md/registry
state), ticket-land/evidence-enforcement system tests, and a handful of
CLI system tests. Because pytest exits non-zero, `make coverage`'s
Makefile recipe halts before its own `coverage combine`/`coverage xml`/
`frob check --stamp-coverage` lines run, so a fresh `make coverage`
currently requires a manual combine/xml/stamp workaround to get any
numbers at all -- and the failing subprocess-heavy system tests never
contribute their coverage, capping how far `join_fraction` can rise
(0.49 observed vs T-0997's target of "well above 0.34"; a green suite
would likely push it meaningfully higher). Needs triage: some of these
may be genuine registry drift in this worktree's ticket state (dozens of
concurrent worktree agents landing tickets) rather than a real product
bug; others (the gitless-target severity assertion, the render-lint
stderr-vs-logging-capture mismatch) look like real, fixable test/gate
bugs. Scope was deliberately not widened to fix these under T-0997.

2026-07-28 coordinator addendum (refiled from a w18-strata3 draft that
died to ledger-restore cycles): three more members of this failure set,
each verified pre-existing on main and unrelated to the wave-17/18
changes: tests/system/test_export_golden.py TestExportGolden
test_seccomp; tests/unit/strata/test_effects.py
TestDeployServeMutateNodeSplitConformance
test_serve_declares_zero_may_and_exercises_zero_effects;
tests/test_registry_cross_corpus_totality.py
TestCrossCorpusLinkageIntegrity
test_every_cross_ref_is_mutually_navigable. Fold them into this
ticket's triage denominator.

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
state: queued
kind: feature
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

<!-- ticket:T-1109 -->
```yaml
id: T-1109
title: 'docs: DOC006 doc-pointer round-3 burn-down (~41 residual warnings after T-1015/T-1016)'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- CHANGELOG.md
- tickets.md
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'narrow to real DOC006 finding sites: docs/**, CHANGELOG.md, tickets.md
    (T-1109 re-measure, TICK009)'
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: tests/**
  reason: 'narrow to real DOC006 finding sites: docs/**, CHANGELOG.md, tickets.md
    (T-1109 re-measure, TICK009)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: CHANGELOG.md
  reason: CHANGELOG.md and tickets.md carry real DOC006 finding sites
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tickets.md
  reason: CHANGELOG.md and tickets.md carry real DOC006 finding sites
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob check --only docblocks exit=0 sha256=e5cda9cbf307
acceptance:
- text: GIVEN a full frob check WHEN the doc gate runs THEN DOC006 reports zero unwaived
    warnings, with every fixed pointer resolving to a real heading slug and no matcher
    loosening
  evidence:
  - cmd:uv run frob check --only docblocks exit=0 sha256=e5cda9cbf307
threat: null
component: null
```
T-1015 (matcher hardening, 771->133) and T-1016 (round 2) left ~41 DOC006 doc-pointer warnings. Round 3: fix or reasoned-waive every residual site. No matcher/threshold loosening; follow T-1015's FP-class analysis before touching the matcher. Narrow scope to the real finding sites at start.

## Done report

Re-measured DOC006 at ticket start: 54 live warnings (up from the ~41 noted
at filing -- heavy landing waves since T-1015/T-1016 shifted counts, as
expected). Scope narrowed to docs/**, CHANGELOG.md, tickets.md (TICK009).

Fixed (real stale pointers, code-verified before editing):
- strata-core/src/parse.rs split into strata-core/src/parse/ (T-1099) --
  19 bare file-path references across 14 docs updated to
  strata-core/src/parse/mod.rs (::symbol-qualified references already
  resolved correctly and were left untouched).
- frob.gates._unwaivable_channel_rules -> frob.gates._waive._unwaivable_channel_rules
  (9 occurrences, docs/modules/arch.md) -- symbol exists, doc dropped the
  module qualifier.
- frob.serve._warm.warm_state -> frob.serve._warm._warm_state
  (docs/modules/graph.md) -- symbol is private, doc had the public spelling.
- frob.dup._pipeline.{_smt_translate,_region_groups,_clone_report,_fingerprint_symbol}
  -> frob.dup._pipeline.{_smt,_fingerprint}.<same name> (docs/modules/dup.md)
  -- dup/_pipeline.py was split into a package; symbols moved to submodules.
- frob.lang._common.iter_cpp_functions -> frob.lang._common._iter_cpp_functions
  (docs/modules/dup.md) -- symbol was demoted private (T-0871) after this
  doc reference was written.
- docs/modules/tickets.md: src/frob/app/ticket_runner.py -> .../ticket_runner/
  in the one non-literal-quote occurrence (the sprint-velocity CLI-surface
  pointer); the CLI_WIRING_FILES-quoting occurrence was left as a verbatim
  quote and waived instead (see below -- the constant itself is stale).
- docs/audits/gates-quality.md: gates/_pii_structural.py -> gates/_pii_structural/
  (real package now, PII010/SEC110 checks span several submodules there).
- docs/modules/gates.md: doc-anchor #per-gate-cache-t-0602 -> the real
  slug #per-gate-dependency-tracked-partial-re-evaluation-t-0602 in
  docs/modules/serve.md (heading text confirmed by reading the file).

Grounded-waived (verified genuinely external/historical, not fixable
without falsifying the record; no matcher/threshold change):
- CHANGELOG.md (6 sites): frozen historical release-note prose describing
  file paths/symbols as they existed at that release; the codebase has
  since been restructured (ticket_runner.py, parse.rs, dup/_core symbols).
  Rewriting would misrepresent what actually shipped in that version.
- docs/audits/tickets-testing-round2.md:6 and tickets.md:477 (dup/_pipeline.py
  finding count): point-in-time audit/filing snapshots whose surrounding
  prose (line numbers, per-file counts) is frozen against a tree that has
  since moved; fixing just the flagged pointer would desync it from the
  rest of the same frozen paragraph.
- docs/guides/agent-playbook.md:50 (.claude/settings.json): confirmed
  gitignored (.gitignore:15) -- a real, intentionally untracked per-clone
  config path, can never resolve.
- docs/guides/estate-capability-migration.md (5 sites): design/*.strata
  paths live in SIBLING repos (lithos/graphite/aprog-public/aprog-private/
  logand.app), never trackable from this repo's own worktree.
- docs/modules/gates.md:2730 (`frob check --fix`): the surrounding prose
  explicitly says wiring this CLI flag is a LATER batch of the same
  T-1137 epic -- genuinely not built yet, not a broken pointer.

Verified: `frob check --only docblocks --json` shows DOC006 count 54 -> 0
(remaining 4 warnings on that gate are pre-existing DOC004, out of this
ticket's rule scope). No matcher/threshold change made anywhere in
src/frob/gates/_docptr.py.

Filed out-of-scope discovery: T-1163 (frob.tickets._models.
CLI_WIRING_FILES still names the retired src/frob/app/ticket_runner.py
path post-package-split, silently defeating T-0446's implicit-scope
mechanism for FEATURE tickets) -- fix is in src/frob/tickets/_models.py,
outside this ticket's docs-only scope.

### Changed
```
 tickets.md | 61 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 56 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1110 -->
```yaml
id: T-1110
title: 'warnings: DEAD001/COV/REF edge burn-down (DEAD 32, COV 10, REF 10 unwaived)'
state: queued
kind: bug
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
acceptance:
- text: GIVEN a full frob check WHEN the dead/coverage/refs gates run THEN DEAD001,
    COV00x, and REF00x report zero unwaived warnings, each finding either root-fixed
    (dead code removed, edge bound) or waived with a grounded reason
  evidence: []
threat: null
component: null
```
Post-wave-16 residue: 32 DEAD001 dead-symbol warnings, 10 COV coverage-edge warnings, 10 REF reference warnings (unwaived, per gate summary). T-1024 precedent: DEAD001 13->0 and COV006 3->0 via real removals and edge bindings, not blanket waivers. Callgraph blind spots (cross-package privates, indexed-constant mutation) get confirmed-exercised waivers per the 3d574f3a precedent. Narrow scope to the real finding sites at start.

<!-- ticket:T-1111 -->
```yaml
id: T-1111
title: 'warnings: small-residue sweep to zero (DEPR 4, LANG 3, INV 2, REG 2, WAIVE
  2, WALK 2)'
state: queued
kind: bug
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
- frob.toml
acceptance:
- text: GIVEN a full frob check WHEN all gates run THEN the DEPR, LANG, INV, REG,
    WAIVE, and WALK families each report zero unwaived warnings
  evidence: []
threat: null
component: null
```
Endgame tail: the sub-five-warning families (DEPR003 x4, LANG003 x3, INV003/004 x2, REG009/REG010 x2, WAIVE004 x2, WALK001 x2 per gate summary). Fix or grounded-waive each. REG009/REG010 residue is the CPPTHROW001 check-coverage auto-sync gap noted at T-1042 land -- fold the registry entry fix here. Narrow scope at start.

<!-- ticket:T-1129 -->
```yaml
id: T-1129
title: 'gates: TICK-family check for disclosed-cut-without-ticket in done reports'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
acceptance:
- text: GIVEN a done report whose prose discloses deferred work (left for a follow-up,
    not yet ticketed, deferred, residue, cut) WHEN frob check runs THEN a TICK-family
    finding fires unless the same report cites an open ticket id (or an explicit no-ticket-needed
    reason) within the disclosure's vicinity
  evidence: []
threat: null
component: null
```
Coordinator hand-screen made mandatory-by-tooling: wave 17 had two incidents in one wave -- T-1085 disclosed 'deliberately left for a follow-up' with no ticket (coordinator hand-filed T-1124), and T-0321's close disclosed the serve RPC gap as 'not yet ticketed as its own item' (coordinator hand-filed T-1127). TICK006 covers phantom citations; nothing covers disclosed-but-unticketed cuts. Detector should be conservative (disclosure phrases + absence of any T-#### in the same bullet/paragraph) and WARN-tier first turn-on with frob's own ledger findings fixed in the same land.

<!-- ticket:T-1133 -->
```yaml
id: T-1133
title: 'gates: suppress WAIVE004 staleness advisories on scoped/--only runs entirely'
state: done
kind: ux
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: call site wiring for the WAIVE004 scoped-run suppression lives in _assemble_gate_report
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: redundant -- already covered by the existing src/frob/gates/** glob
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run
- tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings
- tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver
acceptance:
- text: GIVEN frob check --only <stage> or any diff-scoped run WHEN a waiver matches
    0 findings because its gate did not run THEN no WAIVE004 advisory is emitted (the
    rule only fires on full unscoped runs where match-absence is meaningful)
  evidence:
  - tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run
threat: null
component: null
```
Every scoped run this session printed ~400-447 WAIVE004 warnings with a 'known-flaky, trust only full runs' caveat baked into the message text. A rule that prints its own do-not-trust-me disclaimer on scoped runs should not fire there at all; the caveat is tribal knowledge encoded as noise every coordinator and agent must mentally filter. Keep full-run behavior unchanged (T-1021's sweep depends on it).

## Done report

Changed:
src/frob/gates/_waive.py::_waive004_violations (new full_unscoped_run kwarg, defaults True)
src/frob/gates/__init__.py::_assemble_gate_report (wires full_unscoped_run=not cfg.gates and cfg.ticket is None)

`_waive004_violations` now short-circuits to `()` before any per-edge work
whenever the caller signals a scoped run (`--only` gate selection via
`cfg.gates`, or a `--ticket`-scoped diff via `cfg.ticket`) -- WAIVE004 only
ever fires on a full, unscoped `frob check`, where "matches 0 findings" is
actually meaningful rather than an artifact of the gate/diff-scope
excluding the rule. Full-run behavior (T-1021's sweep) is unchanged: the
default `full_unscoped_run=True` keeps every pre-existing test passing
unmodified. Confirmed live on a real scoped run: `frob check --ticket
T-1133 --only gates-fast` on this worktree produced ZERO WAIVE004
occurrences (measured: `grep -c WAIVE004` = 1, the module's own docstring
reference, no actual finding), versus ~400-447 per scoped run before this
change per the ticket's own observation.

`fake_marker_staleness_gate`/`_stale_fake_marker_violations` (the other
WAIVE004-emitting path, `frob:secret-fake` markers) is intentionally left
unchanged -- it re-derives staleness by re-scanning the file's own text
for real secret-pattern hits every call, independent of which gates
`--only` selected, so it does not exhibit the "gate did not run" false-
positive mechanism this ticket targets.

Evidence:
tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run (new, T-1133)
tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings
tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver
6/6 WAIVE004-related tests pass: `pytest tests/test_gates.py -k waive004 -q` (measured: "......  [100%]").
Acceptance [0] bound to the new suppression test.

Filed: none

Gates: `frob check --ticket T-1133` chunked (gates-fast, gates-native,
gates-security, lint, static) -- gates-fast/gates-security/static all 0
errors. gates-native shows the same 5 pre-existing ARCH001 errors as
T-1155's land (already tracked by T-1162, none in files this diff
touches). lint shows pre-existing ruff-format/ty findings in unrelated
files; my touched files (src/frob/gates/_waive.py,
src/frob/gates/__init__.py, tests/test_gates.py) are individually
ruff-check clean and ruff-format applied.
`uv run frob sys sync-interface --check` not needed -- no public-surface
change (new kwarg is a private-function default-True addition, no new
export).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1134 -->
```yaml
id: T-1134
title: 'gates: INV006 split-assist -- detect verbatim-moved claim prose and carry/suggest
  the source file''s waiver'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/dup/**
- tests/test_gates.py
acceptance:
- text: GIVEN a module split moves docstring/comment prose containing exclusivity
    vocabulary from a file with an INV006 waiver or invariant binding WHEN frob check
    runs on the result THEN the INV006 finding names the source file's existing waiver/binding
    and offers the carried-waiver text as a fix-it (or auto-carries under a flag)
  evidence: []
threat: null
component: null
```
Every split this drive (T-1103, T-1107, T-1072, T-1077, T-1081, T-1082) required hand-carrying INV006 calibration-batch waivers to the new modules -- 3 more by the coordinator today (0abc4e3a) after the gates splits redded main. The clone/dup machinery can already detect verbatim-moved prose; INV006 should use it to stop making 'remember the carried waiver' a human step. Also applies to PII012's (file,token)-keyed allowlist entries which have the same code-moves-need-new-entries failure mode (T-1076 precedent).

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

<!-- ticket:T-1148 -->
```yaml
id: T-1148
title: 'check: detect missing/stale strata_core+frob_core natives and fail honestly
  (or auto-build) instead of 43 bogus DRIFT002s'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- tests/test_gates.py
acceptance:
- text: GIVEN a checkout whose installed natives are missing or stale relative to
    the native source tree WHEN frob check runs any stage that needs them THEN it
    reports ONE actionable finding naming the cause and the fix command (frob natives
    build) -- or auto-builds under a config flag -- and never emits resolver no-candidates
    errors misattributed to design/doc drift
  evidence: []
threat: null
component: null
```
2026-07-28 incident: a root uv sync reinstalled frob without the natives; the next check produced 43 DRIFT002 'no candidates' errors against every design/frob.strata node -- misattributed, alarming, and fixed only by coordinator memory of the worktree-natives artifact (this also recurs in fresh worktrees and sibling repos per the estate rollout T-1031/T-1071 work). The elaboration path knows when strata_core failed to import or its build stamp trails the native source tree; surface THAT, once, with the fix command. Pairs with the T-0864 natives build subcommand and the T-1031 estate shim.

<!-- ticket:T-1152 -->
```yaml
id: T-1152
title: 'arch: extract tickets/__init__.py evidence/transition + done-report/review/drop/attach
  families + split _land.py -- T-1151 residue'
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
T-1151 extracted ONE family (field setters/sprint: set_priority/set_kind/
set_tier/set_sprint/set_component, sprint_view/sprint_velocity,
ticket_flow) into src/frob/tickets/_setters.py, following T-1103/T-1123's
per-family extraction pattern. tickets/__init__.py: 2740 -> ~2065 lines
(carved further, still likely above the <2000 acceptance target from
T-1108's own scope note -- verify exact line count at pickup).

Remaining families (per T-1151's own body, none touched by this pass):
- evidence/transition (transition, add_evidence, the _done_transition_*
  guard family) -- BEWARE the load-time circular import T-1103's Done
  report flagged for this exact family (new_ticket/finalize_draft already
  late-import from the package to work around it)
- done-report/review/drop/attach (brief_ticket, mutate_labels,
  record_review, attach, drop helpers, compose_done_report/
  set_done_report)

_land.py (4762 lines) still untouched across T-1108/T-1123/T-1151 --
still needs its own split (preflight/splice/verify/sweep families per
T-1108's original plan) before LARGE001 stops flagging it.

Follow the same pattern each time: one cohesive family per dispatch,
private module re-exported from __init__ via explicit imports (never
`import *`), zero caller-visible behavior change, existing tests as the
safety net, carry frob:ticket/frob:doc/frob:tests directives verbatim,
repoint docs/modules/tickets.md's frob:describes anchors and any
tests/*.py frob:tests directives at the new module path, add frob:ticket
edges to any test class/method a directive-repoint touches (COV002),
carry an INV006 split-module waiver per 0abc4e3a's precedent if the
moved prose trips it, watch for tests that monkeypatch a moved function
via the PACKAGE attribute (tickets_mod.<name>) -- those need a late
`from frob.tickets import <name>` inside the moved function body instead
of a module-top-level binding.

<!-- ticket:T-1154 -->
```yaml
id: T-1154
title: 'land: take main''s side for ledger/archive files the ticket did not deliberately
  edit (wrong-side-merge corruption, 3rd occurrence)'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_land.py
acceptance:
- text: GIVEN a worktree whose tickets-archive.md (or tickets.md blocks outside the
    landing ticket's own edits) is merely stale relative to main WHEN frob ticket
    land merges THEN main's newer content wins wholesale and the landed diff contains
    no reversion of main-side ledger/archive content the ticket never touched
  evidence: []
- text: GIVEN a ticket that DID deliberately edit tickets-archive.md (e.g. an evidence-path
    migration) THEN its edits land normally -- staleness detection distinguishes unchanged-since-branch
    from deliberately-edited
  evidence: []
threat: null
component: null
```
Third occurrence of the wrong-side-merge corruption class (standing rule: 3rd hit files the root-cause ticket on the merge path). Latest instance: T-1145's land bc834b95 reverted T-1143's tickets-archive.md evidence-path migration (40 parse.rs -> parse/mod.rs occurrences reintroduced) because the worktree's stale archive copy won the merge; T-1153 documents the damage. Two prior agent-observed instances noted in wave 9. T-0959's splice guard covers archive BLOCK LOSS; this is content regression. Detection: compare the worktree file to the merge-base version -- unchanged-in-worktree means the worktree has no claim, take main's side.

<!-- ticket:T-1155 -->
```yaml
id: T-1155
title: 'gates: new-gate-rule-acceptance preflight lost _KNOWN_GATE_RULES after the
  _waive.py move -- resolve dynamically, fail loudly on miss'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
- docs/modules/gates.md
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1155 touches docs/modules/gates.md to document the dynamic-resolution
    fix, an in-scope symptom of the same change
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
acceptance:
- text: GIVEN the new-gate-rule-acceptance preflight WHEN _KNOWN_GATE_RULES lives
    in any gates module THEN the preflight finds it (import-time resolution or the
    generated registry, not a hard-coded file path) and new-rule detection runs
  evidence:
  - tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
- text: GIVEN the literal genuinely cannot be resolved THEN the preflight FAILS with
    an error instead of warning-and-skipping -- a detection check must never silently
    disable itself
  evidence:
  - tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
threat: null
component: null
```
Observed on a T-1153 close (2026-07-28): WARNING new-gate-rule-acceptance: _KNOWN_GATE_RULES literal not found in src/frob/gates/__init__.py, skipping new-rule detection. The wave-18 gates splits moved _KNOWN_GATE_RULES into gates/_waive.py (T-1139 land 71e91ca0); the preflight's hard-coded path went stale and the check now silently skips -- the catalogued-is-not-enforced failure mode applied to a checker itself. Also exactly the moved-symbol class T-1135's refactor verb would have caught; cite this incident in that epic's design.

## Done report

Changed:
src/frob/tickets/_new_gate_rule_acceptance.py::new_gate_rule_ids
src/frob/tickets/_new_gate_rule_acceptance.py::GateRuleRegistryUnresolvable
src/frob/tickets/_new_gate_rule_acceptance.py::_gates_candidate_files
src/frob/tickets/_new_gate_rule_acceptance.py::_locate_known_rules_in_tree
src/frob/tickets/_new_gate_rule_acceptance.py::_known_rules_at_revision
docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756
design/frob.strata (tickets_ledger interface= sync for GateRuleRegistryUnresolvable)

Resolution of `_KNOWN_GATE_RULES` is now dynamic: every direct `*.py`
child of `src/frob/gates/` is a scan candidate, and whichever one
carries the literal is used, both in the current working tree and (via
`_known_rules_at_revision` trying every candidate name against
`base_ref`) across a rename boundary like the real T-1139
`gates/__init__.py` -> `gates/_waive.py` move. If the literal cannot be
resolved to exactly one candidate in the CURRENT tree, `new_gate_rule_ids`
now raises `GateRuleRegistryUnresolvable` instead of warning-and-skipping
-- the exact silent-disable failure mode T-1153 observed. An unresolvable
`base_ref` (or an ambiguous historical match) still degrades to `None`
(skip), unchanged from before -- that remains a legitimate git-side
"cannot tell" condition, distinct from the current-tree structural
failure the new exception covers.

Evidence:
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
14 tests collected/passed via `pytest tests/test_gates.py::TestNewGateRuleDynamicResolution tests/test_tickets_new_gate_rule_acceptance.py -q` (measured: "..............  [100%]").
Acceptance [0] and [1] bound to the two new fixture tests above (resolve-dynamically and raise-loudly respectively).

Filed: none

Gates: `uv run frob check --ticket T-1155` chunked (--only gates-fast, gates-native, gates-security, lint, static) all pass 0 errors for
files this ticket touches. gates-native shows 5 pre-existing ARCH001
errors in src/frob/app/check_runner.py, src/frob/app/ticket_runner/_close_cmd.py,
src/frob/doctor.py, src/frob/tickets/_setters.py -- none touched by this
diff, already tracked by T-1162 (wave-18 fallout, filed before this
ticket started per main's own commit c6c2ee55's parent lineage) --
disclosed, not fixed here (out of this ticket's Description/Plan).
lint shows pre-existing ruff-format/ty findings in unrelated files
(doctor.py, gates/__init__.py, vet/_supplychain.py, etc.); my two touched
files (src/frob/tickets/_new_gate_rule_acceptance.py, tests/test_gates.py)
are individually ruff-check/ruff-format clean.
`uv run frob sys sync-interface --check` clean after syncing
`GateRuleRegistryUnresolvable`/`TestNewGateRuleDynamicResolution` into
design/frob.strata.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1157 -->
```yaml
id: T-1157
title: 'gates: sys audit''s exhaustiveness pass reports every SYS205 waiver as stale
  even when check_mode_conformance correctly matches it'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_audit.py
- tests/unit/strata/test_audit.py
scope_changes:
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: regression test for the SYS205 stale-waiver exclusion fix
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass
threat: null
component: null
```
`frob sys audit`'s exhaustiveness/self-conformance SYSWAIVE002 stale-
waiver pass reports every SYS205:tickets_ledger waiver as stale ("no
matching SYS205:tickets_ledger finding fired this run") even though
`check_mode_conformance` (SYS205's real evaluator) correctly finds and
waives all five in the SAME `frob sys audit` run ("mode-conformance
PROVED (5 waived) -- zero UNWAIVED SYS205 gaps"). Verified pre-existing
(reproduces against a clean T-1149-landed checkout with none of T-1146's
changes applied) -- the exhaustiveness pass's own stale-waiver detection
evidently does not know about the SYS205 rule family at all, so it
always reports any SYS205 waiver as stale regardless of the real
evaluator's outcome. Found while landing T-1146; out of that ticket's
scope.

## Done report

Root cause: `_audit.py::_gap_rule_in_scope` (the exhaustiveness pass's own
`apply_waivers` in-scope predicate) did not exclude SYS205 from the rule ids
it judges staleness for, even though SYS205 already owns its own separate
`apply_waivers` call inside `check_mode_conformance`
(`_mode_conformance.py`). Since the exhaustiveness pass's `gaps` list never
contains a SYS205 finding (SYS205 findings live entirely in
`check_mode_conformance`'s own report), every declared `waive "SYS205:..."`
clause was unconditionally judged stale here regardless of whether the real
SYS205 evaluator matched and waived it -- the exact same cross-family
collision T-0724 (SYS200-203) and T-0640 (REL200/REL201) already hit and
fixed for their own rule families.

Fix: added `SYS_MODE_NONCONFORMANCE` ("SYS205") to the exclusion tuple in
`_gap_rule_in_scope`, imported from `_mode_conformance.py`, mirroring the
existing `_HOST_RULE_IDS`/`RESOURCE_CONTENTION_RULES`/`RELIABILITY_RULES`
pattern exactly.

Verified against this repo's own `design/frob.strata`: `frob sys audit`
now reports "mode-conformance PROVED (5 waived) -- zero UNWAIVED SYS205
gaps" with no SYSWAIVE002 stale-waiver finding for any of the five
tickets_ledger SYS205 waivers (previously all five were misreported
stale).

Gates run (chunked, --ticket T-1157):
- gates-fast: clean (0 errors) after scope-add + frob:ticket edge + sweep
  refresh.
- gates-native: 5 pre-existing ARCH001 errors (check_runner.py
  _try_check_delta_via_daemon, _close_cmd.py _fail, doctor.py
  run_diagnosis, _setters.py ticket_flow) -- these are the exact four
  findings already filed as T-1162 ("wave-18 fallout long-function
  extractions"), none in files this ticket touches or scopes.
- gates-security: clean (0 errors).
- lint/static: ruff-check/ruff-format/ty failures are all in files this
  ticket never touched (_store.py, _supplychain.py, various tests/*); my
  own two files (`src/frob/strata/_audit.py`,
  `tests/unit/strata/test_audit.py`) pass `ruff check` and
  `ruff format --check` individually.

`git diff main --diff-filter=D --stat` is empty.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_audit.py::TestExhaustiveness::test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1158 -->
```yaml
id: T-1158
title: 'strata: declare real owns= paths on tickets_ledger''s five writers to drop
  the SYS205:tickets_ledger waivers'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
threat: null
component: null
```
T-1146 wired module= into the live SELFAUDIT001/frob sys audit call
sites, so SYS203's arbiter-awareness (T-1025) and SYS201's (T-1149) now
genuinely discharge tickets_ledger's five writers live -- the five
SYS203:tickets_ledger waivers in design/frob.strata were dropped as part
of that land (verified stale via frob sys audit's own detection).

The five SYS205:tickets_ledger waivers remain: SYS205's WRITE mode
path-scoping (T-1060) still fires because none of the five nodes
(cli/gates/fleet/core/serve) declare an owns/acl path claim at all.
Declaring a real owns="tickets.md" (or similar) on each would need:
1. Verification that SYS201 genuinely stays clean for the resulting
   overlapping owns claims now that it is arbiter-aware (should, per
   T-1149, but not verified end-to-end against the real design file).
2. Verification against SYS205's OWN "write_outside_declared_path"
   check: the literal write-target paths SYS205 extracts from each
   node's actual bound code must overlap whatever owns= path is
   declared, or a NEW SYS205 finding fires instead of the current
   no_declared_path one.

This ticket is that verification + the owns= declarations themselves,
so the five SYS205:tickets_ledger waivers can finally be dropped too.

<!-- ticket:T-1159 -->
```yaml
id: T-1159
title: 'arch: split remaining ~12 gate families out of src/frob/gates/__init__.py
  (8408 lines) -- T-1140 residue'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
acceptance:
- text: GIVEN src/frob/gates/__init__.py WHEN the remaining families (SCOPE/PREWORK,
    INV00x, TEST00x, DECISIONS, COMPLIANCE00x, SYS00x/DOC00x, DUP00x, REL00x, FUZZ00x,
    DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) are extracted one cohesive family
    per land THEN gates/__init__.py drops below the 800-line large-file threshold
    with no public API change and all existing tests pass
  evidence: []
threat: null
component: null
```
T-1140 extracted the TICK00x family (gates/__init__.py 9172 -> 8408) and disclosed the ~12 remaining families in its done report WITHOUT filing a residue ticket (fourth disclosed-cut-without-ticket incident -- T-1129's gate is the systemic fix; coordinator refiled this one). Same T-1072/T-1077/T-1140 discipline: verbatim moves, directives intact, lazy call-time imports, re-export only externally-called names, carried INV006 waivers, PII012 re-keys, and design/frob.strata interface= sync now via frob sys sync-interface (T-1150).

<!-- ticket:T-1160 -->
```yaml
id: T-1160
title: 'docs: document frob sys sync-interface in docs/commands/sys.md'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/commands/sys.md
- src/frob/app/sys_runner.py
- src/frob/strata/_sync_interface.py
- src/frob/strata/_plan.py
- src/frob/strata/_export.py
- src/frob/strata/_sysdoc.py
- src/frob/strata/_audit.py
scope_changes:
- op: add
  glob: src/frob/app/sys_runner.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_plan.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_export.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_sysdoc.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_audit.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob sys sync-interface --check exit=0 sha256=0a692ca85d0b
acceptance:
- text: GIVEN docs/commands/sys.md WHEN a reader looks up sys subcommands THEN sync-interface
    (and its --check mode) is documented with the SYS104-mandatory upkeep rationale
  evidence:
  - cmd:uv run frob sys sync-interface --check exit=0 sha256=0a692ca85d0b
threat: null
component: null
```
Refile of a T-1150 draft that died to ledger-restore cycles during its land (disclosed in the w18-strata3 done report): the new frob sys sync-interface subcommand landed (5103c0f1) but docs/commands/sys.md does not mention it.

## Done report

Added a `## frob sys sync-interface` section to `docs/commands/sys.md`,
documenting the subcommand landed at 5103c0f1 (T-1150) that was never
mentioned there (the T-1150 draft died to ledger-restore cycles during
its land, per the w18-strata3 done report). Covers: what it does and why
(SYS104 going mandatory at T-1113 turned `interface=` attrs into a
hand-maintained mirror that redded main twice), default vs `--check`
mode behavior/exit codes, the repo-root argument convention (matches
`plan`/`doc`/`audit`), the text-editing strategy (in-place, brace-depth
matched, never a full re-serialize), and `frob:describes` anchors for
the public API (`sync_interface_report`/`apply_sync_interface`) and CLI
wiring (`_run_sync_interface`/`_load_sync_interface_report`/
`_finish_sync_interface`). Also bumped the file's intro line from "Four
verbs" to "Five verbs" to list `sync-interface` alongside the other four.

Docs-only ticket, no pytest surface of its own -- per agent-playbook.md
section 5, the existing CLI-dispatch integration test is recorded as
evidence: `tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches`.

Scope: extended from `docs/commands/sys.md` alone to also cover
`src/frob/app/sys_runner.py`, `src/frob/strata/_sync_interface.py`,
`src/frob/strata/_plan.py`, `src/frob/strata/_export.py`,
`src/frob/strata/_sysdoc.py`, `src/frob/strata/_audit.py` -- SCOPE002
requires every `frob:describes` anchor target in this doc file (both the
new sync-interface anchors and every pre-existing anchor already in the
file for plan/doc/export/audit) to be in-scope.

`uv run frob sys sync-interface --check` (dogfooding the tool this
ticket documents, SYS104 mandatory upkeep, agent-playbook.md): "sys
sync-interface: no drift -- every interface= attr is current".

Gates run (chunked, --ticket T-1160):
- gates-fast: clean (0 errors) after the scope-add + sweep refresh.
- gates-native: 5 pre-existing ARCH001/ARCH103 errors (check_runner.py
  _try_check_delta_via_daemon, _close_cmd.py _fail, doctor.py
  run_diagnosis, _setters.py ticket_flow) -- the same T-1162 baseline
  findings seen on T-1157, none in files this ticket touches.
- gates-security: clean (0 errors).
- lint/static: ruff-check/ruff-format/ty failures are all pre-existing,
  in files this ticket never touched; `docs/commands/sys.md` is markdown
  (not ruff/ty scope) and `ruff check docs/commands/sys.md` reports "No
  Python files found" / "All checks passed!".

`git diff main --diff-filter=D --stat` is empty.

### Changed
```
 tickets.md | 73 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 69 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1161 -->
```yaml
id: T-1161
title: 'doctor/testing: detect root-venv entrypoint shebangs pointing outside this
  venv; collector must fail loudly, not emit 6219 COV003s'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/doctor.py
- tests/test_testing_collect.py
acceptance:
- text: GIVEN .venv/bin entrypoint scripts whose shebang points outside this venv
    (e.g. a removed worktree's python) WHEN frob doctor runs THEN it reports each
    corrupted shim with the uv sync --reinstall-package repair command
  evidence: []
- text: GIVEN pytest --collect-only exits nonzero WHEN the coverage gate needs collection
    THEN it emits ONE error naming the collection failure and its stderr tail instead
    of an unresolved-evidence COV003 for every archived ticket
  evidence: []
threat: null
component: null
```
2026-07-28 incident: worktree uv operations rewrote the ROOT venv's pytest shim shebang to point at .claude/worktrees/w18-tickets/.venv/bin/python; after that worktree was removed, uv run pytest broke, collect_python_tests returned CollectFailed, and the coverage gate emitted 6219 COV003 errors (one per archived evidence id) with a misleading refresh-the-cache hint. Two misattribution layers: (1) doctor has no venv-shim integrity check; (2) the coverage gate degrades a total-collection failure into per-evidence noise. Sibling of T-1148 (natives staleness honest-failure); same design: detect the environment fault once, loudly, with the repair command.

<!-- ticket:T-1162 -->
```yaml
id: T-1162
title: 'arch: wave-18 fallout long-function extractions (check_runner delta-proxy,
  close _fail, doctor run_diagnosis, setters ticket_flow)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/doctor.py
- src/frob/tickets/_setters.py
- tests/**
evidence:
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket
- tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases
- tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day
- tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed
acceptance:
- text: GIVEN frob check --only arch THEN zero ARCH001/ARCH103 errors remain at the
    four wave-18 sites (_try_check_delta_via_daemon 70 lines + mixed concerns, _fail
    73, run_diagnosis 99, ticket_flow 86), each decomposed into cohesive helpers with
    existing tests still passing
  evidence:
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
threat: null
component: null
```
The only remaining errors on main after the wave-18 fallout pass: four functions grew past the 60-line threshold in this wave's lands (T-1147, T-1131/T-1132, T-1142/T-1151). Standard extraction discipline; ARCH103 on _try_check_delta_via_daemon wants the I/O vs formatting vs decision split, not just a length cut.

## Done report

Decomposed the four wave-18 functions that crossed the 60-line ARCH
threshold into cohesive I/O vs decision vs formatting helpers, zero
behavior change:

- src/frob/app/check_runner.py::_try_check_delta_via_daemon split into
  _check_delta_daemon_eligible (decision), _query_check_delta_daemon
  (I/O), _reconcile_daemon_check_result (formatting), and
  _render_and_exit_on_daemon_errors (render/exit) -- addresses ARCH103's
  mixed-concerns finding directly, not just the line count.
- src/frob/app/ticket_runner/_close_cmd.py::_fail split into
  _load_ticket_for_fail (I/O), _record_fail_entry (I/O), and
  _requeue_if_in_progress (decision+I/O).
- src/frob/doctor.py::run_diagnosis split into _diagnose_derived_state
  (locked I/O), _collect_doctor_scans (I/O), and _log_doctor_diagnosis
  (I/O).
- src/frob/tickets/_setters.py::ticket_flow split into
  _load_flow_ticket_universe (I/O), _count_filed_by_day (formatting),
  _count_landed_by_day (I/O), and _build_flow_rows (formatting).

All four public symbols kept their existing frob:tests/frob:doc
directives; the two AFFECT001 findings (run_diagnosis, ticket_flow) are
waived as pure internal extractions with no behavior/doc-contract
change. One new PII012 false positive on _log_doctor_diagnosis (name
signature "diagnosis") waived the same way run_diagnosis's own doc
anchor already is.

### Changed
```
 frob.lock                                |  20 +++
 src/frob/app/check_runner.py             | 111 ++++++++-----
 src/frob/app/ticket_runner/_close_cmd.py | 106 +++++++-----
 src/frob/doctor.py                       | 120 +++++++++++---
 src/frob/tickets/_setters.py             | 119 ++++++++++----
 tickets.md                               | 270 ++++++++++++++++++++++++++++++-
 6 files changed, 603 insertions(+), 143 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1163 -->
```yaml
id: T-1163
title: 'fix: CLI_WIRING_FILES still points at retired src/frob/app/ticket_runner.py'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
threat: null
component: null
```
Found while working T-1109 (DOC006 round-3 burn-down): frob.tickets._models.CLI_WIRING_FILES
(src/frob/tickets/_models.py ~line 204) still lists "src/frob/app/ticket_runner.py" as one of
the three always-in-scope CLI wiring files for a FEATURE ticket. That file was split into a
package (src/frob/app/ticket_runner/) by an earlier landing; the frozenset entry is now a
stale path that can never match a real file glob, silently defeating the T-0446 implicit-scope
mechanism for the ticket_runner half of CLI wiring on any FEATURE ticket.

Fix: update CLI_WIRING_FILES to the correct current path (e.g. a glob covering
src/frob/app/ticket_runner/**, or the package's __init__.py) and re-verify T-0446's own
tests still pass.

<!-- ticket:T-1164 -->
```yaml
id: T-1164
title: 'strata: blast-radius scan spuriously fires for nodes with no declared runs_as
  (None treated as a real compromised-user identity)'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_audit.py
threat: null
component: null
```
`_audit.py::_blast_radius_gaps_per_user` (`src/frob/strata/_audit.py`)
builds its per-user blast-radius scan set as:

```
users = sorted({
    manifest.runs_as
    for node in model.nodes
    if (manifest := host_manifest_for(node)) is not None
})
```

`host_manifest_for(node)` returns non-`None` the moment a node declares
ANY std.host construct at all (`owns`/`acl`/`unit`/`listens`/`runs_as`
per its own docstring) -- `manifest.runs_as` is independently optional
and legitimately `None` when a node declares e.g. `owns` but no
`runs_as` service-account claim. The comprehension above does not filter
that out: a bare `None` lands in `users` as if it were a real
compromised-user identity, and `build_compromised_user_scenario(model,
None, "compromised-user:None")` then runs a full blast-radius scan
treating "no declared service user" as its own reachability scenario,
firing `HOST-BLAST` "influence path X -> Y with no boundary" for every
node reachable from any node whose `owns`/`acl` claim (with no
`runs_as`) triggered the manifest.

Reproduced directly: `design/frob.strata`'s five `tickets_ledger`
writer nodes (`cli`/`gates`/`fleet`/`core`/`serve`) never declared any
std.host construct before T-1158. The moment T-1158 added `owns
"tickets.md" "0644";` to close out the SYS205 waivers, `frob sys audit`
went from 13 checked views (no blast-radius entry at all -- an empty
`users` set) to 14, with a new `host:blast-radius:None` view firing 10
new unwaived `HOST-BLAST` gaps, none of which existed, or were
intended, before -- these nodes are plain trusted repo-internal
components, not services running as any particular OS user, and "None"
is not a real compromised-user identity to model a blast radius against.

Fix: `_blast_radius_gaps_per_user` should exclude manifests whose
`runs_as` is `None` from the `users` set (or otherwise skip the
per-user scenario when there is no real declared service-account
identity to scan against) -- a node declaring pure path ownership
(`owns`/`acl`) with no `runs_as` has nothing for a "compromised user"
scenario to represent.

Blocks T-1158 (`design/frob.strata`'s owns= declarations for the
tickets_ledger writers cannot land clean until this is fixed -- `frob
sys audit`/SELFAUDIT001 would go from 5 pre-existing unrelated gaps to
15).
