# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0160 -->
```yaml
id: T-0160
title: burn down TEST005 module-line-coverage backlog (~78 modules below 85% floor)
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
evidence: []
attachments: []
acceptance: []
threat: null
```
TEST005 module-line-coverage floor (frob.toml [testing].module_line_cov=85) reports ~78 src/frob/** modules below threshold, from 0.0% (never-exercised runners like app/ack_runner.py, app/arch_runner.py, and most other app/*_runner.py CLI entry points) up to modules a few points shy of the floor (e.g. tickets/_store.py at 84.8%, strata/_claims.py at 84.7%). This backlog was invisible during T-0148's original scope (a fresh worktree has no .frob/coverage-stamp, and TEST005 silently produces no findings without one) -- it surfaced only after T-0148 regenerated the stamp to clear its own TEST006 finding ("no coverage stamp found"). It is pre-existing, repo-wide coverage debt, not something T-0148's edits introduced, and burning it down to the 85% floor across ~78 modules (many CLI app/*_runner.py entry points at literal 0%, needing new system/integration tests, not just unit tests) is a dedicated, multi-session effort far outside a gates-sweep ticket. Full per-module list captured via: uv run frob check --only test (TEST005 lines), 2026-07-18.

Acceptance: every src/frob/** module at or above module_line_cov=85 (or system_line_cov=80 in aggregate where a narrower per-module floor is not achievable), OR a specific, reasoned frob.toml override for modules that cannot reasonably reach the floor (e.g. thin CLI entry-point shims exercised only via subprocess system tests). Start with the 0.0%-covered app/*_runner.py entry points -- each is a CLI command's runner with no direct unit/integration test at all, the single highest-leverage slice of this backlog.

Scope correction (2026-07-18, same T-0148 sweep): `src/frob/gates/_coverage.py::_parse_classes` had a path-prefix bug -- Cobertura `filename` attrs are relative to the `--cov=src/frob` root (e.g. `app/ack_runner.py`), but every other path in `frob.graph` is repo-relative (`src/frob/app/ack_runner.py`); the two never matched, so BOTH `module_line` (this ticket's original ~78-module estimate) AND `symbol_branch` (per-symbol TEST005 branch-coverage, `unit_branch_cov=90`) silently mapped zero symbols this whole time. T-0148 fixed the prefix join. Re-running with the fix (and after excluding `src/frob/scaffold/data/**` template files, a separate genuine rule misfire fixed in the same sweep) shows the true backlog is far larger than originally scoped here: 197 unwaived TEST005 findings (up from ~78), most now per-symbol branch-coverage misses across `src/frob/**`, not just the module-line floor. This ticket's acceptance criteria and estimate above are superseded by that number -- treat "~78 modules" as the historical (and wrong, pre-fix) figure; the real acceptance criterion is 0 unwaived TEST005 findings from a fresh `uv run frob check --only test` after `make coverage`, both per-module and per-symbol. This is now unambiguously a dedicated, multi-session effort, not a gates-sweep add-on. (Renumbered from T-0157 to T-0160 on 2026-07-18: the original local allocation collided with main's real T-0157 (secrets-scan gate) landing concurrently; every `frob:waive TEST005` directive this ticket's sweep added under `src/frob/**` was updated in lockstep.)

<!-- ticket:T-0170 -->
```yaml
id: T-0170
title: kotlin capability-scanner column for android nodes
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/_capability.py
- tests/**
- docs/modules/vet.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app has an android node; no Kotlin pattern table exists, so its capabilities cannot be verified. Add kotlin as a language column per the T-0158 matrix discipline: pattern tables for the reserved kinds where Kotlin idioms exist (net: OkHttp/HttpURLConnection/Retrofit; exec: Runtime.exec/ProcessBuilder; client_storage: SharedPreferences/Room; fs; eval: unusual -- excuse honestly), per-cell fire fixtures, .kt/.kts extension mapping. Sequence after T-0158 lands the matrix.

<!-- ticket:T-0171 -->
```yaml
id: T-0171
title: THREAT002 fires in quality views lacking the sink taxonomy security views have
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: THREAT002 (capability kind matches no sink taxonomy entry) fires against quality-family audit views because views do not share the capability-to-CWE mapping the security views carry -- the same signal that hit frob's own T-0150 work (DEFAULT_BENIGN_CAPABILITIES was the frob-repo patch, but external repos hit the raw gap). Decide the principled fix: the sink taxonomy and benign-capability excuse table should be single-sourced across view families, not re-declared per view; a capability genuinely irrelevant to a quality view must not demand a per-repo excuse. Regression-test against a fixture reproducing the pilot's shape.

<!-- ticket:T-0173 -->
```yaml
id: T-0173
title: sys audit output repeats identical WARNING blocks across all views
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/sys_runner.py
- src/frob/strata/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: the same WARNING blocks print once per configured view (8x duplication), burying the per-view differences that matter. Deduplicate: print shared findings once with a views-affected annotation, keep per-view sections for view-specific results only. Snapshot-test the output shape.

<!-- ticket:T-0177 -->
```yaml
id: T-0177
title: 'frob serve daemon: incremental gate evaluation over the warm obligation graph'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/serve/**
- src/frob/gates/**
- src/frob/graph/**
- src/frob/app/**
- pyproject.toml
- Makefile
- tests/**
- docs/modules/serve.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
frob serve is already a FastMCP stdio server with 5 read-only tools (doable tickets, stale docs, graph query, doc-for, check-scope) and is now wired into the coordinator's MCP config. Grow it into the structural fix for test-wait latency: the obligation graph knows exactly which obligations a diff can invalidate (frob test --base already proves the touched-set concept for tests) -- exploit it for gates. Deliverables: (1) warm state: the daemon holds the parsed graph snapshot, collected test ids, and the stamped violation baseline, refreshing incrementally on file-change (mtime/content-hash walk, reuse the .frob sqlite cache) instead of cold-parsing per invocation; (2) frob_check_delta MCP tool: given a base ref or dirty set, evaluate ONLY the obligations whose inputs changed and return the violation delta against the stamped baseline, in seconds; (3) frob_run_touched_tests tool wrapping the existing touched-set selection; (4) correctness guarantee: incremental results must provably match a cold frob check -- add a verification mode that runs both and diffs, plus property tests for the invalidation logic (an obligation NOT re-evaluated must have had no changed inputs -- vacuous-pass doctrine applies to the cache); (5) packaging: mcp becomes a proper [serve] extra in pyproject (mirroring [smt]) with _require_mcp's remedy message updated; Makefile install-tool already passes --with mcp -- reconcile with the extra; (6) docs/modules/serve.md updated with the daemon lifecycle and the staleness/correctness contract. Sequence AFTER the T-0148 sweep lands (gates code moves under it).

<!-- ticket:T-0178 -->
```yaml
id: T-0178
title: 'agentic time profiling: non-gated breakdown of where development time goes'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/tickets/**
- src/frob/stats/**
- scripts/**
- docs/modules/stats.md
- docs/guides/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Diagnostics ONLY -- explicitly NOT a gate family: no rule ids, nothing fails on these numbers, report-only (user directive: for designing tooling around, never for gating). Deliverables: (1) frob CLI entry timing hook -- every frob invocation appends {iso_ts, subcommand, args_head, duration_ms, exit, tree_hash} to .frob/telemetry.jsonl (local-only, already gitignored via .frob/, opt-out env var FROB_NO_TELEMETRY); reuse the per-gate timing frob check already computes by logging it structured instead of display-only. (2) ISO timestamps on ticket state transitions (created/started/done currently date-only) so per-ticket cycle time is computable. (3) EXTERNAL TOOL COVERAGE: ship a Claude Code PostToolUse hook script (scripts/frob-telemetry-hook + docs/guides page with the settings.json snippet) that appends every harness tool invocation -- Bash command head, duration, exit -- to the same telemetry stream; hooks fire for subagents too, so implementer/reviewer runs are covered without per-tool shims; document an optional PATH-shim mode for profiling outside the harness. (4) frob stats --agentic report over the merged stream: per-ticket cycle time and review-round count (parse Done-report addenda), command-time breakdown by category (frob-check / test-suite / native-build / vcs / other), top wall-clock sinks, and RETREAD DETECTION -- identical command+tree_hash re-runs counted as cache-hit candidates, which directly quantifies the T-0177 daemon payoff before it is built. (5) coordinator flow: document attaching the harness usage block (tokens, tool_uses, duration per dispatch role) at ticket close via the existing frob ticket attach, so cost history survives sessions. Privacy: telemetry never committed, never networked, redact anything matching the T-0157 secrets patterns before writing the command head. Tests: hook script emits valid JSONL under fake invocations; stats aggregation over a fixture stream; redaction case.

Addendum (user, 2026-07-18) -- TOKENS as a first-class dimension beside
time: (a) per-tool-call token cost -- the PostToolUse hook also records
an output-size token estimate (len/4 heuristic is fine; note the method)
for every tool result, since tool OUTPUT is what silently consumes agent
context: the report must rank tools by cumulative output tokens (e.g.
'frob check dumps cost N tokens/run x M runs') to identify which tools
need quieter output modes or pagination; (b) per-development-stage
attribution -- bucket both time and tokens by lifecycle stage, using the
telemetry markers already present in the stream (frob ticket start ->
first edit -> first test run -> evidence recording -> done report) and
by dispatch role (implement / review / rework round N / land), so the
report answers 'what does a REJECT round cost in tokens and minutes'
with measured numbers; (c) the coordinator-attached harness usage block
(subagent_tokens, tool_uses, duration per dispatch) is the ground truth
to reconcile the per-call estimates against -- report both and the
discrepancy.

Addendum 2 (user, 2026-07-18) -- PER-TEST TIMING ANNOTATIONS: track
per-test wall-clock as a Gaussian running estimate (Welford mean/sd/n,
persisted in .frob telemetry keyed by pytest node id, fed by the
existing test-run machinery). Write the estimate as a comment annotation
on the test itself (e.g. `# frob:perf mean=12.4s sd=1.1 n=9` above the
test def), updated ONLY when the new mean shifts beyond 2 sigma from
the annotated value -- statistical update to avoid diff churn, never
per-run rewrites. Consumption: frob test / frob check gain a fast mode
that SKIPS tests whose annotated mean exceeds a configured threshold,
and skipping is LOUD (summary names every skipped-slow test and its
annotated cost); the full check always runs everything -- fast mode is
an explicit opt-in, never the default for release/CI gates (vacuous-pass
doctrine: a skipped test must be visible, and the full gate is the
authority).

<!-- ticket:T-0179 -->
```yaml
id: T-0179
title: 'TTY-aware pretty output: colors and formatting across all frob commands'
state: in-progress
kind: ux
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/logging/**
- src/frob/app/**
- src/frob/check/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Bake consistent pretty formatting and color into frob's terminal output for TTYs, skipped cleanly when non-TTY. Build on the existing src/frob/logging/color.py should_color machinery -- single source of truth, honoring isatty, NO_COLOR, FORCE_COLOR, and a [tool.frob] override. Apply across the surfaces users actually read: frob check tool/gates summary (pass/fail coloring, aligned columns, per-gate timing dimmed), frob sys audit (PROVED green, GAP red, view sections), frob ticket list/doable (state-colored ids), frob vet reports (severity coloring), frob stats. HARD CONSTRAINT: non-TTY output must remain byte-stable plain text -- agents, CI, and this repo's own snapshot tests parse it; add tests locking both modes (force-color golden and plain golden) so pretty mode can never leak ANSI into piped output. No new heavyweight dependency without written justification (prefer hand-rolled ANSI via the existing color module over adding rich).

<!-- ticket:T-0180 -->
```yaml
id: T-0180
title: 'closed-world unknown-import accounting: vetted-library cache engine (T-0158
  addendum 2 remainder)'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**,tests/**,docs/modules/vet.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0158 shipped the single-source dangerous-operations registry, the (kind x language) coverage matrix with 0 unexcused cells, and the sys-audit matrix-verdict proof line. NOT shipped (too large for one pass, explicitly deferred per T-0158's own escape valve): addendum 2 deliverable (2), full CLOSED WORLD accounting -- resolving every third-party import in a vetted dependency's source to (a) a registry entry, (b) a VETTED library (same scanner engine run over the installed third-party source, cached per package+version, e.g. reusing the frob.vet._cache.py sqlite pattern), or (c) a LOUD 'unknown, unvetted, uninspected' failure -- with the audit accounting line (N registry ops, M vetted libraries, K explicit no-capability entries, 0 unknown) T-0158's addendum 2 describes. T-0158's sys-audit line covers the (kind x language) MATRIX proof only, not this import-resolution closed-world proof. Needs: an import-graph walk per vetted package (python ast.parse imports at minimum), a resolution function classifying each imported name against DANGEROUS_OPERATIONS/registry libraries vs NO_CAPABILITY_MODULES vs unresolved, and a persistent per-package+version cache keyed like _cache.py's verdict cache.

<!-- ticket:T-0187 -->
```yaml
id: T-0187
title: 'frob dup bleeding-edge: algorithm survey, reverse-templating abstraction,
  exhaustiveness meta-test'
state: in-progress
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/dup/**
- frob-core/**
- tests/**
- docs/modules/**
- docs/index.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User mandate 2026-07-18: frob dup does the basics (R1-R6 rungs: winnow, WL-hash, candidate_pairs, tree_edit in frob-core; statement-Levenshtein; co-occurrence CFG/DFG proxy) but must be bleeding-edge. Phase 1 RESEARCH (exhaustive-researcher): map the clone-detection state of the art against our implementation -- APTED exact tree edit distance, SourcererCC bag-of-tokens overlap, Oreo metrics-based type-3/4, NiCad normalization+abstraction, DECKARD characteristic vectors, learning-based (ASTNN, FA-AST GNN, CCLearner) with honest feasibility calls for a no-model-dependency tool, cross-language clone detection, and ANTI-UNIFICATION / reverse templating: report each clone group with its abstracted template plus per-instance bindings (the shared skeleton with holes), so the fix suggestion is the extracted function signature, not just 'these are similar'. Phase 2 DESIGN+TICKETS: planner converts the survey into an implementation ticket tree (rust-kernel work vs python orchestration split explicit). Phase 3 META-TEST: exhaustiveness drift-lock in the T-0158/T-0182 mold -- a registry of detectors/rungs/clone-types, parametrized litmus fixtures proving every (clone type 1-4 x supported language x rung) cell either fires on a minimal fixture pair or carries a written exclusion; adding a detector or claiming a clone type without a firing fixture fails the suite. Acceptance: survey doc committed, ticket tree filed, meta-test green over the CURRENT detector set before any new detector lands.

<!-- ticket:T-0188 -->
```yaml
id: T-0188
title: 'catalog: add CWE-295 (improper cert validation) WeaknessEntry to unblock TLS
  verify=False fingerprint'
state: queued
kind: security
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: spoofing
```
T-0153 review follow-up: the TLS verify=False fingerprint class was correctly cut because no CWE-295 WeaknessEntry exists in CWE_CATALOG/CWE_TOP_25_CATALOG/QUALITY_CATALOG and the CVEFP001 drift-lock (rightly) refuses fingerprints citing absent CWEs. Add the catalog row (with honest views placement), then the fingerprint entry (requests/httpx/aiohttp verify=False, node tls rejectUnauthorized false, rust danger_accept_invalid_certs), litmus positive/negative source tests per T-0153's pattern. Also reconcile CWE-916 (mentioned in _cve_fingerprint.py docstring but in neither catalog nor cut-class list) -- add it or fix the docstring.

<!-- ticket:T-0189 -->
```yaml
id: T-0189
title: 'catalog: add CWE-611 (XXE) WeaknessEntry to unblock XML external-entity fingerprint'
state: queued
kind: security
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
T-0153 review follow-up: XXE fingerprint class cut because no CWE-611 WeaknessEntry exists and CVEFP001 refuses fingerprints citing absent CWEs. Add the catalog row, then the fingerprint entry (python lxml etree.parse with resolve_entities, xml.sax without feature_external_ges disabled, java-style patterns out of scope -- only supported languages), litmus positive/negative tests per T-0153's pattern.

<!-- ticket:T-0190 -->
```yaml
id: T-0190
title: secrets-gate fixtures trip GitHub push protection -- main is unpushable
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tests/test_secrets_gate.py
- src/frob/gates/_secrets.py
- docs/modules/gates.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
GH013 push protection rejects main: the Stripe fixture at tests/test_secrets_gate.py:49 (landed in 48aeed1, T-0157) is realistic enough for GitHub secret scanning despite T-0157's clearly-fake requirement. Every push of main is blocked until resolved. Fix has two parts: (1) make every fixture structurally un-flaggable by GitHub (pattern-invalid tail: wrong length/charset/checksum for the provider) while still firing frob's own gate -- if frob's format constraint is currently so strict that only GitHub-flaggable strings can fire it, LOOSEN the fixture-facing constraint or add a test-only needle path, disclosed; (2) meta-test: fixtures must not match GitHub's published secret-scanning patterns (encode the Stripe/AWS/GitHub-token formats we know) so a future fixture cannot re-trip push protection. REMEDIATION for the already-flagged blob (coordinator step, not this ticket): after all in-flight branches merge, rewrite the unpushed range to replace the flagged fixture in 48aeed1 itself (remote tip predates it, so no force-push needed), or the user may use the GitHub unblock URL instead. This ticket only makes the CURRENT tree safe and drift-locked.

<!-- ticket:T-0194 -->
```yaml
id: T-0194
title: 'anti_unify kernel: Plotkin lgg over (labels,parents) node arrays'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 4: lockstep top-down walk emitting shared nodes and $hole_N at divergence, returning template arrays + binding index pairs; reuses the node-array representation apted_similarity already consumes. Cargo tests incl. hole-ceiling sanity (>50 pct holes = Err back to plain pair).

<!-- ticket:T-0195 -->
```yaml
id: T-0195
title: 'reverse-templating report: CloneTemplate/CloneBinding models, extraction-signature
  synthesis in DUP001 messages'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by:
- T-0194
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 4: frozen pydantic CloneTemplate/CloneBinding, CloneReport.groups[].template optional, signature synthesis one param per distinct hole (reuse identifier when both instances agree), DUP001 violation message gains the suggested extraction. The violation hands you the fix, not a percentage.

<!-- ticket:T-0196 -->
```yaml
id: T-0196
title: 'R5 fidelity: real control-flow edges from frob.lang where available, proxy
  demoted to true fallback'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- src/frob/lang/**
- frob-core/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey items 7/8 ADAPT: verify frob.lang actual CFG-edge coverage FIRST (the survey flags this VERIFY), then follow R4 established two-tier pattern (real primary, proxy fallback for unparseable symbols). Disclose per-language coverage honestly in dup.md.

<!-- ticket:T-0197 -->
```yaml
id: T-0197
title: 'candidate prefilters: DECKARD characteristic vectors + Oreo metric ratios
  + NiCad size ratio'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey items 2/4/6 (non-ML halves): three additive candidate-pruning stages before APTED/WL verification; prefilters only prune pairs, never add false positives -- test that enabling them never changes the verified-clone set on fixtures, only the pair count examined.

<!-- ticket:T-0198 -->
```yaml
id: T-0198
title: 'cross-language clone litmus: same logic in two grammars through the real pipeline'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- tests/**
- src/frob/dup/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey item 13: the cross-language claim rests on shared node vocabulary between frob.lang grammars but no fixture proves it. One fixture pair (python+ts same algorithm) through the REAL pipeline; if vocabulary does not align, that is the finding -- document and file rather than force.

<!-- ticket:T-0199 -->
```yaml
id: T-0199
title: 'dup exhaustiveness meta-test: (clone-type 1-4 x language x rung) matrix registry
  + litmus fixtures'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 5, user mandate: registry of detectors/rungs/claimed clone types; parametrized fixture pairs per claimed cell (fire + negative); unclaimed cells need written exclusions; a detector or clone-type claim added without a fixture fails the suite -- T-0158 capability-matrix mold. Meta-test must be green over the CURRENT detector set before any new detector lands (acceptance from T-0187).

<!-- ticket:T-0200 -->
```yaml
id: T-0200
title: add real kill-switch/feature-flag mechanism for exec/net capabilities (checker/core/stratamod/vet)
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/process/**
- src/frob/check/**
- src/frob/strata/**
- design/frob.strata
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0155's LINT004 rule (design lint family) fires honestly on design/frob.strata's checker/core/stratamod/vet nodes: each holds a risky (exec/net) may capability with no real, checked-in kill switch (env var / feature flag) an operator can flip live to disable it. T-0155 deliberately did not fabricate a flag=<id> attr naming a mechanism that does not exist (declare real facts or waive with reasons, T-0150/T-0151 precedent) -- this ticket is the follow-on product work to build the actual mechanism and then discharge LINT004 for real on design/frob.strata.

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

<!-- ticket:T-0207 -->
```yaml
id: T-0207
title: 'structural PII/secrets detection: waivable checks over data structures, schemas,
  and env access'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- src/frob/vet/**
- src/frob/lang/**
- design/frob.strata
- tests/**
- docs/**
- frob.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
User mandate 2026-07-18 ('if it passes, it's safe'): extend T-0154 (PII flow proofs) and T-0157 (secrets token scan) with STRUCTURAL detection over data surfaces, every rule waivable via frob:waive with a written reason so zero-unwaived means every PII/secret surface is either declared or consciously waived. Detector families: (1) DATA-STRUCTURE FIELDS: pydantic/dataclass/TypedDict/attrs field names and types across supported languages (name keyword table: email, phone, ssn, dob, address, ip, password, token, api_key, secret, salt, card/pan/cvv...; type-based: EmailStr, SecretStr, and TS/rust equivalents) -- a detected PII-shaped field on a node without a matching T-0154 PII category declaration (or waiver) fires; declared-but-never-observed goes stale like SYS101. (2) DATABASE SCHEMA: CREATE TABLE / column DDL in migrations (alembic, raw SQL) and ORM models (sqlalchemy columns) scanned with the same keyword+type tables -- schema headers are the highest-value PII surface. (3) ENV/SECRET SOURCES: os.environ[...]/os.getenv/load_dotenv() call sites (and process.env, std::env::var) are secret-source observations that must map to declared strata secret nodes (T-0082 std.secrets) or be waived -- an unmapped env read fires. (4) EMAIL-SHAPE VALUES: detect email-shaped string literals in code/fixtures WITHOUT naive regex (user explicit: regex is bad for email matching) -- use a structural parse (local@domain.tld via a real address parser, e.g. email.utils/parseaddr semantics or the WHATWG algorithm) with the T-0157 fake-marker escape (frob:secret fake / placeholder shapes stay writable). (5) KEYWORD SWEEP: identifier/comment keyword hits at suggestion severity only (no hard fail on names alone). DISCIPLINE (non-negotiable, per registry precedent): single-source keyword/type registry (no duplication between detectors); litmus fire+discharge fixtures per detector (T-0145 style); per-entry parametrized drift-lock (T-0182 style) so a registry keyword without a firing fixture fails; exhaustiveness matrix (detector x language) with written exclusions for unpatterned cells (T-0158 style); self-match exclusion for the registry file itself designed in from day one (T-0201 lesson -- the keyword table must not detect itself); wire into frob check as a new gate family (PII0xx/SEC1xx) default-on at WARN for adoption, severity dial in frob.toml; sys audit gains the joined view (structural observations vs declared PII/secret model). Split into child tickets per detector family at plan time if needed; this is the umbrella.

<!-- ticket:T-0219 -->
```yaml
id: T-0219
title: secrets scan misses adjacent sk-live key and placeholder-phrase fakes
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/_secrets.py
- tests/**
- tickets.md
evidence:
- tests/test_secrets_gate.py::TestFindsTokens::test_generic_live_key_adjacent_to_other_content_sec001
- tests/test_secrets_gate.py::TestFakeMarking::test_digit_free_mixed_case_your_token_still_fires
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private (gap 15): SEC001 flagged a fake Slack token but MISSED the sk-live-... key on the adjacent line (detection gap -- the miss matters more than any false positive), and the fake-marker heuristics missed obvious placeholder phrasing ('real-slack-token-here' contains no recognized fake word). Fix both directions: audit the provider table against the fixture file that produced the miss (why did sk-live- not match -- prefix table or format constraint?), and extend placeholder recognition ('...-here', 'your-', 'insert-', 'changeme') with fixtures. Coordinate with T-0190 (GitHub-unflaggable fixtures) so new fixtures satisfy both constraints.

## Done report

**Root cause, miss 1 (sk-live- adjacent):** confirmed both misses reproduce
on main (6164712) before any fix -- `_scan_text` returned `[]` for a
`sk-live-<24 hex>` token embedded in `X = "sk-live-...." # trailing note`
and for `xoxb-your-slack-token-here`. Miss 1's root cause is a FORMAT
CONSTRAINT, not a missing prefix-table entry per se: the existing
`openai-legacy` pattern `sk-[A-Za-z0-9]{20,}` requires 20+ contiguous
alnum-ONLY chars right after `sk-`; `sk-live-...` has a hyphen 4 chars in
(`live-`), which breaks that run before it reaches the 20-char floor, so
NO pattern in `_PATTERNS` ever claimed the span (this is also why
"adjacency" mattered in the ticket title -- the token never matched
regardless of what surrounds it). Fix: added a new, more-specific
`generic-live-key` pattern (`sk-live-[A-Za-z0-9-]{16,}`, `SEC001`,
critical) ordered before `openai-legacy` per the file's most-specific-
prefix-first discipline (`src/frob/gates/_secrets.py` `_PATTERNS`).

**Root cause, miss 2 (placeholder phrase):** `_looks_fake` only checked
single WORDS (`fake`/`changeme`/`example`/`placeholder`) and an
XXXX/**** run; a phrase like `xoxb-your-slack-token-here` matches the real
Slack regex and contains none of those words, so it fired a false-
positive SEC001 despite being an obvious template. Fix: added
`_PLACEHOLDER_PHRASE_RE` (`-here`, `your-`, `insert-`, case-insensitive)
checked in `_looks_fake` alongside the existing word list.

**Litmus tests added** (`tests/test_secrets_gate.py`):
- `TestFindsTokens.test_generic_live_key_adjacent_to_other_content_sec001`
  -- miss 1, now caught.
- `TestFakeMarking.test_placeholder_phrase_your_dash_here_is_not_flagged`
  -- miss 2 (`-here`/`your-` phrase), now correctly ignored.
- `TestFakeMarking.test_placeholder_phrase_insert_dash_is_not_flagged` --
  miss 2, `insert-` variant.
- `TestFakeMarking.test_placeholder_phrase_does_not_suppress_real_looking_token`
  -- regression guard: a real-shaped Slack token with none of the new
  phrase fragments still fires (the phrase heuristic must stay scoped, not
  swallow real detections).
- `generic-live-key` added to `_FIXTURES_BY_PROVIDER` (drift-lock
  requirement, `TestDriftLock.test_every_provider_has_a_fixture` and the
  parametrized `test_provider_has_a_registered_fixture`).

**No false positives introduced:** `tests/test_secrets_gate.py` full
suite, 52 passed (`uv run pytest tests/test_secrets_gate.py -q`), including
`TestGateIsGreenOnItself.test_repo_is_clean`,
`test_this_test_file_is_clean`, and `test_secrets_module_source_is_clean`
(the module's own source and this test file, self-scanned by the real
gate, stay clean) and all existing `frob:secret-fake`-marked fixtures
(T-0157/T-0294) still discharge correctly -- unchanged, still passing.

**Evidence:**
- `tests/test_secrets_gate.py::TestFindsTokens::test_generic_live_key_adjacent_to_other_content_sec001`
- `tests/test_secrets_gate.py::TestFakeMarking::test_placeholder_phrase_your_dash_here_is_not_flagged`
- `tests/test_secrets_gate.py::TestFakeMarking::test_placeholder_phrase_insert_dash_is_not_flagged`
- `tests/test_secrets_gate.py::TestFakeMarking::test_placeholder_phrase_does_not_suppress_real_looking_token`
- `tests/test_secrets_gate.py::TestDriftLock::test_every_provider_has_a_fixture`
- `tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean`

**Gates:** `uv run frob check --ticket T-0219` clean: 0 errors, 1 warning
(pre-existing `TEST006` "no coverage stamp found", unrelated to this
change), 24 waived (all pre-existing). `uv run ruff check` and
`uv run ruff format --check` clean on both touched files; `uv run ty
check` clean. `uv run frob test --base main` selected and ran
`tests/test_gates.py::test_gates_run_gates_integration` +
`tests/test_secrets_gate.py`, exit=0. Full-repo `uv run frob check`
(unscoped): `gates 0 errors, 1 warning, 24 waived` -- same pre-existing
`TEST006` warning, no new secrets-gate or other violations. Deletion-
filter (`git diff main --diff-filter=D --stat`) empty.

Filed: none -- both misses were fully addressable within this ticket's
declared scope (`src/frob/gates/_secrets.py`, `tests/**`, `tickets.md`).

Not closing per dispatch instructions -- leaving for reviewer.

## Done report (round 2 -- security bypass fix)

**Reviewer-found bypass:** round 1's `_PLACEHOLDER_PHRASE_RE` was
`.search()`'d as a bare SUBSTRING test against the whole token, and
`_looks_fake` gated the entire SEC001 detection path unconditionally. A
real-shaped, high-entropy `sk-live-` token that merely CONTAINS `your-`,
`insert-`, or `-here` anywhere -- e.g. a live key naming a tenant
"your-company" -- was silently suppressed: zero violations, debug log
"generic-live-key match ... placeholder, skipping". An attacker (or a
tenant genuinely named `your...`) could evade SEC001 entirely by choosing
a credential name that happens to contain one of those three fragments.
Reproduced against the pre-round-2 worktree code before fixing (see
verification below).

**Fix -- anchored-or-entropy-gated phrase suppression**
(`src/frob/gates/_secrets.py`): a phrase match now suppresses ONLY when
one of two guards holds, never on the bare substring alone:
1. `_KNOWN_TEMPLATE_SHAPE_RE` -- a whole-token structural anchor,
   `^[a-z0-9]{2,10}-(your|insert)-[a-z-]+-here$`, matched with
   `fullmatch` against the ENTIRE token (not `.search()`). Catches
   `xoxb-your-slack-token-here`, `sk-insert-api-key-here`, etc.
2. `_looks_low_entropy(token)` AND `_PLACEHOLDER_PHRASE_RE.search(token)`
   -- the phrase must also be sitting inside token text with NO digits
   anywhere (`_looks_low_entropy` returns `not any(c.isdigit() for c in
   token)`). A real secret's non-prefix portion is machine-generated
   noise and virtually always mixes in digits; a human template
   (`insert-your-real-token`) is plain lowercase words and hyphens, no
   digits at all.

Net rule: a token is placeholder-fake via the phrase path only if it is a
known whole-token template shape, OR it is digit-free AND contains the
phrase. A high-entropy, digit-bearing, real-shaped token is NEVER
suppressed by phrase content alone, regardless of what substrings it
happens to contain. `_looks_fake`'s docstring and the `_PLACEHOLDER_PHRASE_RE`
comment block now document this explicitly so the substring trap cannot
be silently reintroduced.

Out of scope, left alone per dispatch instructions: the single-word
`_PLACEHOLDER_WORDS` check (`fake`/`changeme`/`example`/`placeholder`)
still does a bare substring `in` test and has the same theoretical
substring-embedding weakness (e.g. a live key named "...fakecompany...").
The dispatch explicitly named only the phrase-regex bypass for this
round; the word-list's own approved detection behavior (T-0157) was not
touched. Not filing a new ticket for it -- noting here for the reviewer's
awareness since it is the same class of gap.

**Mandatory adversarial regression tests added**
(`tests/test_secrets_gate.py::TestFakeMarking`):
- `test_placeholder_phrase_your_does_not_suppress_high_entropy_token` --
  `sk-live-your-company` + 16 digits fires SEC001.
- `test_placeholder_phrase_insert_does_not_suppress_high_entropy_token` --
  `sk-live-insert` + 20 digits fires SEC001.
- `test_placeholder_phrase_here_does_not_suppress_high_entropy_token` --
  `sk-live-here` + 20 digits + `abcd` fires SEC001.

**Confirmed bypass-then-fix:** stashed only `src/frob/gates/_secrets.py`
(keeping the new tests), reran the three new tests against the
pre-round-2 source -- `test_placeholder_phrase_your_does_not_suppress_high_entropy_token`
FAILED (`assert 0 == 1`, log line `generic-live-key match ...
placeholder, skipping`), confirming the bypass reproduces exactly as the
reviewer described. Restored the round-2 fix and reran: all three pass,
along with the full `tests/test_secrets_gate.py` suite (58 passed,
including `TestGateIsGreenOnItself::test_repo_is_clean` and
`test_secrets_module_source_is_clean`, and the pre-existing round-1
whole-token placeholder tests `test_placeholder_phrase_your_dash_here_is_not_flagged`
/ `test_placeholder_phrase_insert_dash_is_not_flagged`, still suppressed
correctly via the `_KNOWN_TEMPLATE_SHAPE_RE`/low-entropy paths).

**Gates:** `uv run pytest tests/test_secrets_gate.py -q` -- 58 passed.
`uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`
all clean. `uv run frob check` (full repo, unscoped): `gates 0 errors, 1
warning, 24 waived` -- same single pre-existing `TEST006` warning as
round 1, no new secrets-gate violations, no new waivers added.

Evidence stays node-level (see the three new test node ids above, plus
round 1's evidence list, unchanged).

Filed: none -- fix fully addressable within this ticket's declared scope.

Not closing -- reviewer.

## Done report (round 3 -- entropy-proxy bypass fix)

**Reviewer-found bypass (live-reproduced):** round 2's
`_looks_low_entropy(token)` was `return not any(char.isdigit() for char in
token)` -- a binary "has no digits" check, not a real entropy measure. A
digit-free, high-entropy, real-shaped token containing a placeholder-
phrase fragment (`your-`/`insert-`/`-here`) was still silently suppressed
regardless of how random the rest of it looked: 0 violations confirmed for
an `sk-live-your-` prefix glued to a mixed-case run, an `sk-live-insert-`
prefix glued to a near-unique-letter alphabet run, and an `sk-live-`
prefix glued to a mixed-case run ending in `-here` (see the three new
adversarial test cases below for the exact fragments).

**Fix -- real entropy/diversity measure, security-safe by construction**
(`src/frob/gates/_secrets.py`): replaced `_looks_low_entropy` with three
independent, conservative gates, ALL of which must hold before a token is
ever classified low-entropy -- failing any single one keeps it
high/unsuppressed, the security-safe default when uncertain:
1. No digit anywhere (unchanged from round 2, still decisive on its own
   for "not low").
2. Single case only (all-lowercase or all-uppercase letters). Mixed case
   is rejected outright before entropy is even computed -- a real
   generated token frequently mixes case, a hand-typed template phrase
   never does.
3. Real Shannon entropy over the token's alnum characters, bits/char,
   below a calibrated `_LOW_ENTROPY_BITS_PER_CHAR = 3.7` floor.

Calibration against this repo's own fixtures: the existing legit-
suppressed placeholder `xoxb-insert-your-real-token` sits at ~3.64
bits/char (below the floor, still correctly suppressed, no regression);
the reviewer's adversarial `sk-live-insert-` token (a near-unique-letter
run, essentially no character repeats) sits at ~4.32
bits/char (above the floor, correctly now fires); any mixed-case token
never reaches the entropy calculation at all. `_KNOWN_TEMPLATE_SHAPE_RE`
(the whole-token `fullmatch` anchor from round 2, confirmed sound by the
reviewer) is unchanged and remains the primary path for the canonical
`prefix-your/insert-words-here` shape; the entropy gate now only matters
for phrase fragments that don't fullmatch that anchor (no `-here` tail, or
a non-`your`/`insert` middle segment, as in all three of the reviewer's
adversarial tokens).

**Mandatory adversarial regression tests added**
(`tests/test_secrets_gate.py::TestFakeMarking`), all digit-free and
runtime-constructed (concatenated fragments, never a contiguous literal in
this file's own source) so the addition itself stays clean under
`TestGateIsGreenOnItself`:
- `test_digit_free_mixed_case_your_token_still_fires` -- `sk-live-your-` +
  `XKCDplmqrstuvwxyzABCD` (mixed case) fires SEC001.
- `test_digit_free_insert_alphabet_run_still_fires` -- `sk-live-insert-` +
  `abcdefghqrstuvwxyz` (near-unique-letter run, all-lowercase) fires
  SEC001.
- `test_digit_free_mixed_case_here_tail_still_fires` -- `sk-live-` +
  `abcdXYZQRSTUVW` + `-here` (mixed case, structurally close to but does
  NOT fullmatch `_KNOWN_TEMPLATE_SHAPE_RE` since the middle segment is
  `live` not `your`/`insert`) fires SEC001.

**Confirmed bypass-then-fix:** stashed only `src/frob/gates/_secrets.py`
(keeping the new tests), reran the three new tests against the
pre-round-3 source -- all three FAILED (`assert 0 == 1`, log line
`generic-live-key match ... placeholder, skipping`), confirming each of
the reviewer's three tokens reproduces the exact live bypass described.
Restored the round-3 fix and reran: all three pass, along with the full
`tests/test_secrets_gate.py` suite (61 passed), including
`TestGateIsGreenOnItself::test_repo_is_clean` and
`test_secrets_module_source_is_clean`, and every prior round 1/2
adversarial and legit-suppression test unchanged and still green (no
regressions).

Also reworded the module docstring's `_looks_low_entropy`-adjacent example
tokens (previously literal, self-scan-tripping strings) into non-
contiguous doc phrasing, since the new fix's own commentary needed to
reference example token shapes without becoming a false positive against
this module's own self-scan.

**Gates:** `uv run pytest tests/test_secrets_gate.py -q` -- 61 passed.
`uv run ruff check .`, `uv run ruff format --check .` (after `ruff
format`), `uv run ty check src/frob/gates/_secrets.py` all clean. `make
coverage` then `uv run frob check` (full repo, unscoped): `gates 0 errors,
1 warning, 204 waived` -- same single pre-existing warning, no new
violations, no new secrets-gate waivers.

Committed in worktree `.claude/worktrees/agent-aaa45dc8342d35cc0`
(branch `worktree-agent-aaa45dc8342d35cc0`), sha `6cea368`.

Filed: none -- fix fully addressable within this ticket's declared scope.

Not closing -- reviewer.

<!-- ticket:T-0220 -->
```yaml
id: T-0220
title: 'T-0176 scope gap: src/frob/__main__.py missing from declared scope'
state: queued
kind: docs
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0176's scope listed src/frob/tickets/**, src/frob/app/**, tests/**, docs/modules/tickets.md, tickets.md but omitted src/frob/__main__.py -- every prior ticket-subcommand-adding ticket (e.g. T-0162) explicitly included src/frob/__main__.py in scope, since the ticket subcommand argparse wiring lives there, not under src/frob/app/. T-0176 needed exactly that (frob ticket land's --worktree/--dry-run argparse registration) and could not deliver a usable CLI command without it. Waived SCOPE001 at src/frob/__main__.py in T-0176's commit rather than expanding scope unilaterally; this ticket exists to note the gap for future ticket-scope authoring (mechanically: any ticket adding a new frob subcommand should include src/frob/__main__.py in scope up front).

<!-- ticket:T-0222 -->
```yaml
id: T-0222
title: per-node capability excuse channel + missing needles (fs-read, uvicorn bind,
  pyo3 import)
state: in-progress
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/vet/_capability_registry.py
- src/frob/vet/_capability.py
- tests/**
- docs/strata/**
- docs/modules/vet.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 5 (HIGH for adoption; 6 residual gaps across graphite+feldspar trace here): real-but-scanner-invisible capabilities force permanent SYS101 red or dishonest under-declaration -- may ffi on a pyo3-import node, may net for uvicorn.run, may fs for Path.read_text are all 'declared but never observed'. Fix both sides: (a) BenignCapability-style per-node excuse with a written reason (relates to T-0174 waiver channel -- coordinate, do not duplicate); (b) add the missing needles: fs-read (Path.read_text/open-for-read), socket/uvicorn bind, compiled-extension import as ffi observation. Litmus per needle per T-0182 discipline.

## Done report

Investigation first (per dispatch instructions): most of this ticket's
scope had already landed under other tickets between filing (2026-07-18)
and this pass -- confirmed by reading the code, not assumed:

- fs-read (Path.read_text/open-for-read): FULLY landed by T-0304
  (`feat(vet): split fs into fs-read/fs-write capability kinds`, commit
  478a106) -- new `fs-read` kind in `CAPABILITY_KINDS`, patterned python/
  typescript/rust/c-cpp entries, `_selfconform.py` SYS101 backward-compat
  alias (a bare `may "fs"` is satisfied by either fs/fs-read observation;
  a narrow `may "fs-read"` is not satisfied by a write-only observation),
  and `tests/unit/strata/test_selfconform.py` coverage
  (`TestFsReadFsWriteAlias` and neighbors). Nothing left to do here.
- socket/uvicorn bind: `uvicorn.run(` (T-0181) and the c-cpp
  `socket()/connect()/bind()` entry (T-0158) both already pattern as
  `net` -- the tier-2 `may` vocabulary
  (`frob.strata._effects._KIND_MAP`) only delegates `net`/`fs`/`exec`, so
  a distinct `bind` kind would duplicate `net`, not add a new discharge
  shape (exactly the "confusing vocabularies" anti-pattern
  `docs/guides/extending/benign-capabilities.md#common-mistakes` warns
  against). No new kind added; documented the investigation and the one
  real residual gap (Python's `from socket import socket` idiom, no
  `socket.` substring) as a known, undischargeable-without-false-positive-
  risk gap in `docs/modules/vet.md` ("T-0222: socket/uvicorn 'bind'
  observability").
- Part B (per-node capability excuse channel): T-0174's
  `[[strata.benign_capabilities]]` / `load_repo_benign_capabilities`
  channel already exists, already carries `fs-read`, `net`, and `ffi`
  entries in `DEFAULT_BENIGN_CAPABILITIES` (`src/frob/strata/_threat.py`),
  and is already fully tested end-to-end
  (`tests/unit/strata/test_threat.py::test_repo_declared_excuse_resolves_
  threat002` and neighbors). No new mechanism built -- this ticket's Part
  B is pure confirmation that T-0174 already covers the ask; documented
  in the Description discussion above, no separate doc edit needed since
  `docs/guides/extending/benign-capabilities.md` already documents the
  per-repo channel in full (including the worked recipe and the "replace
  a `waive THREAT002:<kind>` with a first-class entry" guidance the
  ticket asked for).

The one genuinely missing needle this pass adds: compiled/native
extension import observed as `ffi` (`src/frob/vet/_capability_registry.py`,
new `DangerousOperation` python/importlib/
`importlib.machinery.ExtensionFileLoader` entry, capability_kind `ffi`).
A bare `import strata_core`-style native-extension import is scanner-
invisible by construction (indistinguishable from any other import by
substring); `ExtensionFileLoader` is the one unambiguous stdlib literal
naming "this is a compiled extension module loader," with no known
false-positive class (verified: zero other occurrences of the literal
anywhere else in `src/`). `docs/modules/vet.md`'s capability taxonomy
table row for `ffi` updated to name it.

Changed:
- src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS (new entry:
  python/importlib/importlib.machinery.ExtensionFileLoader -> ffi)
- docs/modules/vet.md (ffi taxonomy row + new "T-0222: socket/uvicorn
  'bind' observability" investigation subsection)
- tickets.md (scope widened to include src/frob/vet/_capability.py and
  docs/modules/vet.md per dispatch instructions; this Done report)

Evidence (fire/negative fixtures generated automatically per-entry by
T-0182's `TestPerOperationFireFixtures`, confirmed via
`pytest --collect-only`):
- tests/test_capability_registry.py::TestPerOperationFireFixtures::
  test_entry_fires_scan_file_operations[015-python-importlib-importlib.machinery.ExtensionFileLoader]
- tests/test_capability_registry.py::TestPerOperationFireFixtures::
  test_entry_fires_scan_file_capabilities[015-python-importlib-importlib.machinery.ExtensionFileLoader]
- tests/test_capability_registry.py::TestPerOperationFireFixtures::
  test_entry_absent_from_benign_source[015-python-importlib-importlib.machinery.ExtensionFileLoader]
- Regression (pre-existing, still green): tests/test_capability_registry.py
  full module, `tests/unit/strata/test_threat.py`,
  `tests/unit/strata/test_selfconform.py` -- 100% pass, 0 failures,
  `uv run pytest tests/test_capability_registry.py
  tests/unit/strata/test_threat.py tests/unit/strata/test_selfconform.py -q`.

Gates: `uv run ruff check` clean, `uv run ruff format --check` clean
(both PATH and project-pinned ruff, per playbook section 12),
`make typecheck` (`uv run ty check src/`) clean, `uv run frob check
--stamp-baseline` then `uv run frob check --delta`: `gates 0/4 new,
0 errors, 0 warnings, 24 waived` (the 4 baseline violations are all
pre-existing, none in touched files). `git diff main --diff-filter=D
--stat` empty (deletion-filter clean).

Filed: none -- no out-of-scope discoveries required a new ticket; the
"known gap" (low-level `from socket import socket` idiom) is documented
in-line in `docs/modules/vet.md` rather than ticketed, since adding a
discriminating needle for it was investigated and rejected as a false-
positive risk, not deferred work.

Worktree: 172308d base (main tip at start, confirmed via `git log
--oneline -1` before and after -- no drift). NOT closing per dispatch
instructions (review-gated) -- left in-progress for reviewer.

<!-- ticket:T-0223 -->
```yaml
id: T-0223
title: THREAT003 CWE-78 discharge impossible in foreign-less library models
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 8 (medium-high): a library repo with no foreign node (feldspar) declaring may exec cannot discharge CWE-78 -- the demanded claim form is NoFlow(foreign src -> node) and no foreign source exists; frob sys plan --apply then mints permanently unclosable tickets (feldspar T-0009/T-0010 left queued as evidence). Add a library-mode discharge form: an argv-confinement assume against the outermost caller, or an explicit no-foreign-sources model-level fact that discharges the foreign-path obligation family with a written reason.

<!-- ticket:T-0225 -->
```yaml
id: T-0225
title: TEST003 fires on design/ dir; strata ids need e2e-binding obligation not unit/integration
  gates
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/lang/_walk_strata.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 10: T-0168 exempted .strata from TEST001/TEST002 but TEST003 ('interface design has 0 integration tests') still fires on the design dir (graphite +16 findings). Per the refs, system ids bind kind=e2e. Decide + implement consistently with T-0168: exempt design artifacts from TEST003, and (design decision, document it) whether a SYS-family obligation should demand e2e bindings for flows instead.

<!-- ticket:T-0226 -->
```yaml
id: T-0226
title: utility/non-transitive flow marking -- SYS003 hub edges destroy true noflow
  claims
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- strata-core/src/parse.rs
- docs/strata/**
- tests/**
- design/frob.strata
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 11 (expressiveness): graphite had to withdraw a TRUE claim ('TUI never crosses HTTP') because SYS003 forced declaring tui->core (logging import) and core->server (entrypoint hosting), and reachability closure then refutes the noflow through the hub. Add a flow attribute (utility / no-transit) excluded from noflow transitive closure, or claim-level path exclusions; litmus pair: hub edge marked utility keeps the noflow claim provable, unmarked refutes it. Grammar change -> tmLanguage drift-lock will fire.

<!-- ticket:T-0230 -->
```yaml
id: T-0230
title: PERF00x findings anchor to enclosing def line, not the offending statement
state: in-progress
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 15: lithos audit.py:450 PERF002 while the .index() calls sit at 465-466; rust conformance.rs:31 PERF003 points at the fn signature. Report the call-site line. Feeds T-0161 (heuristic fixes) -- coordinate. Regression fixtures asserting the exact reported line.

<!-- ticket:T-0232 -->
```yaml
id: T-0232
title: per-gate timing attribution shared/wrong; concurrent frob runs contend on .frob
  db
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 20: graphite shows secrets=39.71s sys=39.71s tickets=39.69s (identical; 3.6s when quiet) -- shared scan time is attributed to every gate; stages balloon ~56s while a frob vet runs concurrently in the same repo (db contention). Attribute shared scans once (report separately), and check .frob cache.db locking behavior under concurrent invocations (WAL was added once before -- verify it covers this path).

<!-- ticket:T-0233 -->
```yaml
id: T-0233
title: broken frob:doc target suppresses other coverage findings on the same file
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 21 (correctness): feldspar had DOC002 anchor-less targets; fixing them UNMASKED 6 previously-unreported COV001s on the same files -- a broken doc edge was counting as coverage. A frob:doc edge that fails to resolve must not satisfy COV001. Regression: fixture with a broken edge asserts COV001 still fires.

<!-- ticket:T-0234 -->
```yaml
id: T-0234
title: generated-file marker respected by coverage gates (COV001 on generated sources)
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 23: graphite frontend/src/api/api.generated.ts draws COV001 doc-edge demands (its repo ticket T-0006 documents the dead end). The [graph] excludes leaf exists but repos want generated code IN the graph (xref) yet exempt from doc/test obligations. Add a generated marker (glob list in frob.toml, or filename pattern *.generated.*) that COV/TEST gates respect while graph/xref still see the symbols.

<!-- ticket:T-0235 -->
```yaml
id: T-0235
title: exhaustive log/print call-site classification across src/frob (T-0202 follow-up)
state: queued
kind: ux
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0202 fixed the check-path log-level bug (stdout handler defaulted to DEBUG unconditionally) and demoted the per-symbol/per-violation INFO calls found in gates/graph along that path. It did not exhaustively classify every _log./print( call site repo-wide (~1016 sites across src/frob) into keep-INFO/demote-DEBUG/convert-print as the ticket's enumerate-first instruction asked -- only src/frob/{gates,graph,check,app/check_runner.py,logging} got a full pass; the other 26 files under src/frob/app/ (89 INFO, 125 ERROR, 46 print call sites) and all non-scope dirs (strata 27, vet 17, fuzz 6, dup 5, tickets 4, testing 3, perf 3, lang 3, serve 2, arch 2, stats 1, release 1, policy 1, mutate 1, cve 1) were only sampled, not individually classified. Do the full pass and produce the classification table T-0202's Done report deferred.

<!-- ticket:T-0236 -->
```yaml
id: T-0236
title: PRE001 stale-sweep churn in the multi-agent loop -- land should refresh the
  sweep
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Three consecutive reviews (T-0181, T-0203, T-0202) REJECTed solely or partly on a stale PRE001 pre-work sweep, caused not by implementer negligence but by main moving between implementation and review in a multi-agent loop -- any unrelated landing that touches a ticket's scope globs invalidates its recorded sweep. Fix: frob ticket land refreshes the sweep against the post-merge state automatically before close (it already validates evidence/done-report pre-merge; add sweep-refresh as a post-merge, pre-close step), and frob check --ticket's PRE001 message should say when the staleness is due to out-of-scope-agent drift (compare sweep tree hash provenance) vs a genuinely un-swept scope change. Tests: land a ticket whose sweep predates an unrelated main landing; assert land succeeds and the recorded sweep is fresh.

<!-- ticket:T-0237 -->
```yaml
id: T-0237
title: frob:tests edge code endpoints and kind= attr are not gate-verified
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while writing T-0159's extending guides. tests/unit/test_strata_tmlanguage.py:13 declares 'frob:tests strata-core/src/parse.rs::parse_program kind="drift"'. Two problems, neither caught by any gate: (1) the code-side endpoint parse.rs::parse_program does not resolve -- frob.lang's Rust walk qualnames the symbol Parser.parse_program -- yet no DRIFT002 fires; an identical dead endpoint on a frob:describes edge DOES fire DRIFT002 (observed during T-0159: a describes edge to parse.rs::parse_program produced 'DRIFT002 ... gone' until corrected to Parser.parse_program). frob:tests edges appear exempt from endpoint resolution, so a renamed/deleted code symbol silently orphans its test-evidence edge. (2) kind="drift" is not in graph.dsl._TESTS_KINDS (unit/integration/e2e) yet is not reported as a MalformedDirective. Either widen _TESTS_KINDS deliberately or reject unknown kinds loudly; and run frob:tests code-side endpoints through the same DRIFT002 resolution describes edges get. (Refiled: first draft was lost in a tickets.md ledger splice during T-0159's concurrent-agent merge.)

<!-- ticket:T-0238 -->
```yaml
id: T-0238
title: frob outline has no Rust adapter though frob.lang parses Rust
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/outline/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while writing T-0159's extending guides: 'frob outline strata-core/src/parse.rs' errors with 'No outline adapter for this file extension' even though frob.lang extracts 151 symbols from the same file (dispatching path=strata-core/src/parse.rs to grammar=rust). The outline adapter registry does not cover every language frob.lang supports; either add the missing adapters (rust at minimum, check c/cpp/tsx too) or have outline fall back to the frob.lang symbol walk so the two language registries cannot drift apart. (Refiled: first draft was lost in a tickets.md ledger splice during T-0159's concurrent-agent merge.)

<!-- ticket:T-0239 -->
```yaml
id: T-0239
title: graph/gates scan gitignored nested git worktrees -- 73 pct wasted work
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- src/frob/excludes.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH): .claude/worktrees/agent-* checkouts made graph build scan 536 files/3007 symbols vs 144/925 real -- 73 pct of parse/gate work on stale copies; full check 9m47s -> 3m35s after manual exclude. Fix: skip gitignored paths and any directory containing a .git file/dir by DEFAULT (not per-repo config); regression fixture with a nested checkout.

<!-- ticket:T-0240 -->
```yaml
id: T-0240
title: frob ticket sweep unbounded on real scopes -- ignores excludes, walks venvs,
  nonsense xref stems
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/dup/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH): sweep on an 8-glob scope never completed on /mnt/c across 5 attempts (>13 min; /proc fd sampling showed it inside .claude/worktrees/*/.venv site-packages); identical repo on Linux fs: 5.2s. It ignores [graph] exclude; xref_hits derives nonsense symbols from glob stems (**, __init__, README); SIGINT prints bare KeyboardInterrupt. Also fold in: PRE001 catch-22 on slow mounts (scope edit demands re-sweep which is this unbounded op) and scope_digest env-sensitivity (hashes snapshot file-hashes so a sweep record cannot be transplanted between identical-content checkouts -- consider content-digest keying). Fix: honor excludes + gitignore, cap/skip venv trees, derive xref terms from real symbols only, clean interrupt message.

<!-- ticket:T-0241 -->
```yaml
id: T-0241
title: 'ticket scope parsing: comma-joined strings match nothing, dir/ prefixes dont
  glob, ledger not implicit'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- tests/**
- docs/modules/tickets.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH correctness -- same class as T-0181 round-1 incident): a scope entry 'a/,b/,c/' is treated as ONE fnmatch glob matching nothing -- SCOPE001 fired on every touched file and prior sweeps recorded against ZERO files (digest sha256 of empty; dup/xref vacuous pass). Also 'design/' does not match (needs design/**), and tickets.md itself is flagged out-of-scope though frob edits it on every ticket op. Fix: reject or split comma-joined entries at frob ticket new (loud validation), treat dir/ as dir/**, make tickets.md implicitly in-scope for every ticket. Regression tests for all three.

<!-- ticket:T-0242 -->
```yaml
id: T-0242
title: 'strata runner: frob test should invoke sys audit natively for touched .strata
  files'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/testing/**
- src/frob/strata/**
- tests/**
- docs/modules/testing.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot: touching a .strata file breaks frob test with NoRunner (language strata has selected tests but no [[test.runner]]); workaround registering frob sys audit as runner demands a dummy {ids} placeholder (BadRunnerSpec otherwise). Fix: native strata selection path -- touched .strata invokes sys audit without per-repo runner config; placeholder validation should accept runners that take no ids. Relates T-0149 (closed, per-repo config path) -- this makes it zero-config.

<!-- ticket:T-0243 -->
```yaml
id: T-0243
title: cache.db not invalidated across frob/parser upgrades
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (medium): a stale cache served 2830 symbols where a fresh parse of identical sources gave 3007 -- cache survived a frob upgrade with changed parser behavior. Include the frob version + grammar/parser fingerprint in the cache key so any upgrade invalidates cleanly. Regression: bump a fake version constant in test, assert cold rebuild.

<!-- ticket:T-0244 -->
```yaml
id: T-0244
title: 'embedded-code blind spot: JS/HTML inside python string literals invisible
  to every scanner'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- src/frob/lang/**
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (design-level): the product dashboard is 5400 lines of inline HTML/JS inside a python module -- invisible to capability scanning even post-T-0169. Options to evaluate honestly: (a) detect large embedded html/script string literals and run the TS/JS needle pass over their content; (b) an explicit OutOfScope/managed-style marker declaring embedded-frontend content with a reason, so the blind spot is at least DECLARED not silent. Start with (b) (cheap, honest), spike (a).

<!-- ticket:T-0245 -->
```yaml
id: T-0245
title: 'mount-aware performance: per-file stat storms and sqlite contention on /mnt/c
  (13-60x tax)'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- src/frob/gitio.py
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot dedicated /mnt/c findings: same content, same machine -- graph cold 7.4s vs 1.1s, warm up to 31s vs 0.5s, gates-only 19-47s vs 7.9s; ~0.5ms/stat under load (11.3k stats in 90s of sweep strace); sqlite commit 8.2ms vs 2.3ms; concurrent frob processes drove D-state stalls with no lock feedback. Fixes: batch directory walks (os.scandir reuse), cut redundant per-file stats (trust one snapshot pass), sqlite busy_timeout + a visible waiting-on-lock message, and a docs page on WSL-mount expectations. Acceptance: measured cold graph build on the malmberg /mnt/c checkout under 3s.

<!-- ticket:T-0246 -->
```yaml
id: T-0246
title: 'PERF003 correlation: unwind one level of call parens in _operand_names (f(x)
  == g(y) joins)'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0161 round-2 review follow-up (non-blocking boundary found by the reviewer): a real nested join comparing derived values -- f(x) == g(y) with x,y the loop variables inside call parens -- does not fire because _operand_names only unwinds bare identifiers and one bracket-pair subscript (a[i-1] == b[j-1] works). Extend the unwinding one level of call parens, symmetric with the subscript handling; keep the attribute-access narrowing (its 4 sibling-loop FP sites are documented in T-0161's Done report). Regression: derived-value join fires; the 4 FP classes stay silent.

<!-- ticket:T-0247 -->
```yaml
id: T-0247
title: store grammar still missing on-deploy/observe/errors_total/panics_contained_by
  from node_prop
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- strata-core/src/parse.rs,docs/strata/surface.md,src/frob/strata/**,tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
found while working T-0166: docs/strata/surface.md's std.infra grammar block says store_prop := node_prop | engine | immutable | append_only | rpo, implying store accepts the FULL node_prop set. T-0166 closed the code/may gap (the one this ticket's scope named), but parse_store still has no branch for on deploy/observe/errors_total/panics_contained_by -- store_prop remains a real subset of node_prop, not the full union the grammar block literally claims. Either implement the remaining node_prop items on store (mirroring parse_node) or narrow the surface.md grammar line to enumerate the actual accepted subset instead of the misleading 'node_prop' alias.

<!-- ticket:T-0248 -->
```yaml
id: T-0248
title: grammar-affecting landings leave stale natives on main -- land/check must detect
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/strata/**
- Makefile
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Incident during T-0156 review: T-0166 landed a parse.rs grammar change and design/frob.strata began using it, but main's built strata_core predated the change -- frob check reported SYS004 (design failed to load, suppressing SYS001 project-wide) until the coordinator manually ran make core + tool reinstall. Two fixes: (1) frob ticket land detects when the landed diff touches strata-core/**, frob-core/**, or any native-crate source and prints a LOUD post-land instruction (or optionally runs make core) before the final commit; (2) the SYS004 message should distinguish 'parse failed with unknown construct X' and hint that a grammar/native version mismatch is the likely cause when the construct is recognized by the python-side surface docs. Regression: fixture simulating a grammar-ahead-of-native state asserting the hint appears.

<!-- ticket:T-0251 -->
```yaml
id: T-0251
title: wire frob vet --timeout/--jobs CLI flags to scan_tree
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/vet_runner.py,src/frob/app/config.py,src/frob/__main__.py,docs/modules/vet.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0208 built scan_tree(root, *, timeout=None, jobs=1) and per-package progress logging in src/frob/vet/_scan.py (in scope: src/frob/vet/**), but CLI wiring (--timeout/--jobs flags, AppConfig fields, vet_runner.py dispatch) is out of that ticket's scope (app/** and __main__.py). File this to add the flags: vet_p.add_argument for --timeout (float, seconds) and --jobs (int) in _add_vet_parser (src/frob/__main__.py ~line 784), AppConfig.vet_timeout/vet_jobs fields plus float/int field wiring in from_args (src/frob/app/config.py), and pass them through in _run_scan (src/frob/app/vet_runner.py) as scan_tree(root, timeout=cfg.vet_timeout, jobs=cfg.vet_jobs or 1). Disclosed risk (see _scan.py's _scan_dependencies docstring): jobs>1 is best-effort against the sqlite verdict cache and registry disk cache, which are not lock-hardened for concurrent writes -- document this in docs/modules/vet.md when wiring the flag.

<!-- ticket:T-0254 -->
```yaml
id: T-0254
title: 'frob deploy epic: auditable, isolated, provable OS-layer deployment'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
- strata-core/**
- design/**
- docs/**
- tests/**
- Makefile
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
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
blocked_by:
- T-0257
parent: T-0254
scope:
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0254 child 6 (proof on reality). Apply the full chain to malmberg (the real server product from pilot P3: server_api/ingest/cloudsync/faces/backup/display + media_store): extend design/malmberg.strata with std.host (dedicated service users per component, units, ownership of media_store paths, ports), prove HOST001/HOST002 movement-impossibility or record honest waivers, generate the deploy scripts, run the conformance gate, and if a VirtualBox environment is available run the full VM snapshot audit and attach the attestation. Remediate the current awkward setup step in malmberg's docs/scripts with the generated sequence. Work happens IN THE MALMBERG REPO per the break-and-report pilot protocol (frob-side gaps come back as tickets, filed serially by the coordinator); this frob-side ticket tracks the campaign and collects the gap list. Success = malmberg installs/uninstalls via generated scripts with a green conformance gate and a documented (or executed) VM audit path.

<!-- ticket:T-0261 -->
```yaml
id: T-0261
title: 'std.host windows backend: services, gMSA/service accounts, ACLs, named pipes,
  firewall ports'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by:
- T-0255
parent: T-0254
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- src/frob/deploy/**
- editors/**
- docs/strata/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0254 Windows pillar. Generalize the HostManifest (T-0255, Linux/systemd-first) into a platform-tagged model so a node can target windows. Windows analogs: service account instead of runs_as (dedicated low-priv local account, or a group Managed Service Account gMSA for domain-joined hosts -- NO interactive-logon right, deny-network-logon where possible, SeDenyBatchLogonRight per hardening); Windows Service (SCM) instead of systemd unit, with the hardening equivalents (service SID type restricted, required-privileges allowlist derived from may-capabilities, protected-process where applicable); NTFS ACLs (owner + explicit DACL entries) instead of POSIX owns MODE -- model must express deny-inheritance and per-principal rights, richer than a 3-octal mode; named pipes + Windows firewall rules for the listens surface. The platform tag drives which fields are required (a windows node without an ACL model is a HOST-family gap, mirroring a linux node without owns). Keep ONE HostManifest with a platform discriminator, not two parallel models -- the movement proofs (T-0256) and conformance (T-0258) must consume both uniformly. Grammar in parse.rs, tmLanguage drift-lock, litmus pair (linux + windows), docs/strata/host.md gains a Windows section. Generator/audit are separate tickets -- manifest + model only here.

<!-- ticket:T-0263 -->
```yaml
id: T-0263
title: 'Kerberos/AD movement vectors: delegation abuse, Kerberoasting, S4U, cross-realm
  as HOST/KRB obligations'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by:
- T-0256
- T-0262
- T-0282
parent: T-0254
scope:
- src/frob/strata/**
- docs/strata/**
- design/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: elevation-of-privilege
```
T-0254: the red-team Kerberos playbook as demanded, provable obligations extending T-0256's movement-impossibility family. KRB001 unconstrained delegation: any node declaring delegation unconstrained is a hard finding (it lets a compromised service impersonate ANY user to ANY service -- the worst lateral+vertical vector) -- must be re-declared constrained/rbcd or waived with a written accepted-risk reason and sub-target. KRB002 Kerberoasting exposure: an SPN bound to a principal whose credential class is a human-memorable/user password (not a machine account or gMSA) is roastable -- demand gMSA/machine-account or a waiver. KRB003 constrained-delegation blast radius: for a node with constrained delegation, prove the target SPN set does not transitively reach a higher-trust principal (S4U2Proxy chaining) -- reachability over the SPN graph, counterexample trace on failure. KRB004 cross-realm containment: a one-way/transitive trust must not create an undeclared path from a low-trust realm to a high-trust service. Each rule joins a separate compromised-domain-principal threat view (WeaknessEntry rows: CWE-522/CWE-269/CWE-284 class) per the separate-view precedent, NOT widening defaults. Reuse the T-0073 scenario engine for a compromised-service-account scenario whose closure shows the Kerberos blast radius. Litmus: an unconstrained-delegation + roastable-SPN vuln model fires KRB001/002; a gMSA + constrained + non-chaining hardened model discharges all four.

<!-- ticket:T-0264 -->
```yaml
id: T-0264
title: 'frob deploy generate windows: PowerShell/DSC install/status/uninstall from
  the manifest, drift-locked'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by:
- T-0257
- T-0261
parent: T-0254
scope:
- src/frob/deploy/**
- src/frob/app/**
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0254 Windows generation. The T-0257 generator gains a windows target emitting idempotent PowerShell (check-then-apply, same contract as the bash target): install creates the service account/gMSA, registers the Windows Service with its hardening (service SID type, required-privileges, deny-logon rights), applies the NTFS ACLs exactly from the manifest, opens the declared firewall ports / creates named pipes, and configures the SPN + delegation setting from std.krb (setspn / the delegation flags) when a krb model is present. status queries SCM state + health. uninstall removes exactly the manifest set (service, account, ACL grants, firewall rules, SPN registration) leaving no artifacts. Same DEPLOY001 digest-header drift-lock as bash. Scripts must be PSScriptAnalyzer-clean and depend only on in-box modules (no PSGallery). The conformance gate (T-0258) and VM audit (T-0259) must handle the PowerShell mutation surface too -- coordinate the manifest abstraction so those tickets' parsers are platform-tagged, not bash-only; if T-0258/T-0259 landed bash-only, file follow-ups for their windows extension rather than expanding scope here.

<!-- ticket:T-0265 -->
```yaml
id: T-0265
title: self-referential frob:tests directive on a test function passes --ticket check
  but fails full DRIFT002
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Recurring: implementer agents put a 'frob:tests <self>' directive above their own new test function; the target does not resolve as a graph qualname so full frob check fires DRIFT002, but frob check --delta --ticket (what agents+reviewers run) does NOT surface it -- so it lands and reddens main (happened for T-0213, T-0216; coordinator removed 3). Two fixes: (1) frob check --ticket should include the drift gate for edges the ticket's own diff ADDS (a new frob:tests directive in the diff must be validated even under --ticket scoping); (2) the graph should REJECT or warn on a frob:tests directive whose target is the annotated symbol itself (a test testing itself is meaningless) at directive-parse time, not silently store a dangling edge. Add a check-scoping regression + a self-edge rejection test.

<!-- ticket:T-0266 -->
```yaml
id: T-0266
title: SYS100 core+extended can report the same undeclared-capability site twice
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/_selfconform.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed while working T-0209 (re-filed after a ledger-conflict drop). check_self_conformance's SYS100 join: _core_undeclared_violations (THREAT004 delegate, line=0) and _extended_kind_violations (T-0169 eval/env/ffi slice, real line via _effects.py) can each independently emit a SYS100 for the same (node, capability_kind), so one observed-but-undeclared capability surfaces as two findings. Dedupe by (node, capability_kind) [or (file,line,kind) once core tracks a line] before returning; regression fixture with one capability both paths flag.

<!-- ticket:T-0267 -->
```yaml
id: T-0267
title: 'docs(dup): correct stale DUP001/DUP002 unwired claim in dup-sota-survey.md
  sec 0'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- docs/modules/dup-sota-survey.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0191's Done report: dup-sota-survey.md section 0 says DUP001/DUP002 are 'pure rule functions but NOT wired into frob.gates.__init__' -- stale since a3eef8d8 (2026-07-17), one day before the survey landed. dup_gate already calls the real smart find_clones pipeline and is registered as the opt-in 'clones' gate. Correct section 0's claim to describe the actual state (wired, opt-in via [dup].enforce, connection-pooled as of T-0191) so a future reader does not re-investigate an already-closed gap. (Note: T-draft-2a3adb6d, the T-0253 release-stamp follow-up, was resolved during T-0253's landing -- coordinator stamped 0.3.0 in that motion -- so it is dropped here.)

<!-- ticket:T-0268 -->
```yaml
id: T-0268
title: 'fix(frob-core): candidate_pairs can return a self-pair (i, i)'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- frob-core/src/lib.rs
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while working T-0191: frob_core::candidate_pairs can hand back (i, i) when a symbol's own R4 winnowed-fingerprint set collides with itself past the shared-token floor -- observed for real on this repo's own dup cache module (DUP002 reported get_verdict as its own clone). T-0191 guarded the one Python-side consumer (_r4_groups in src/frob/dup/_pipeline.py) with an i==j/a==b skip, but the kernel itself still emits self-pairs, so any OTHER caller of candidate_pairs inherits the same footgun unless it also guards. Fix at the kernel (skip i==j in the Rust candidate-pair emission) so every caller gets it for free.

<!-- ticket:T-0269 -->
```yaml
id: T-0269
title: invalid frob:tests kind='system' shipped in test_cli_check.py:237 -- malformed
  directive silently dropped
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tests/**
- src/frob/graph/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0231 review found a pre-existing malformed frob:tests directive at tests/system/test_cli_check.py:237 using kind='system' (valid kinds: unit/integration/e2e per _TESTS_KINDS). It parses malformed and is silently dropped -- the bound symbol has no real test edge. Landed via commit 289f2c68 (T-0229). Fix: kind='integration' (or extend _TESTS_KINDS to include 'system' if that taxonomy is intended -- decide, since T-0225 also touches the design-vs-code test-kind question). Also: this class only surfaces on full frob check, not --ticket -- covered by T-0265's scoping fix but this is the concrete instance to clean up. Grep the whole repo for other kind='system'/invalid-kind directives while here.

<!-- ticket:T-0270 -->
```yaml
id: T-0270
title: 'std.host manifest: validate owns MODE and listens PORT (deferred from T-0255)'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0254
scope:
- strata-core/src/parse.rs
- src/frob/strata/_host.py
- src/frob/strata/**
- tests/**
- docs/strata/host.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0255 deliberately left HostOwns.mode (str) and HostManifest.listens (int) UNVALIDATED -- a bogus mode ('999'/'rwx') or out-of-range port is stored raw. T-0255's reviewer confirmed this is a correct deferral (mode-as-opaque-string is intentional so a Windows ACL/SDDL string fits the same field later -- platform-tagged validation belongs here, not in the manifest schema). Implement per-platform validation: LINUX_SYSTEMD validates octal mode (0-7 triples, optional setuid bits) and port in 1-65535; WINDOWS (when T-0261 lands) validates SDDL/ACL shape. Validation fires at elaborate time (MalformedHost error, fail-closed), NOT parse time (keep the grammar platform-agnostic). Litmus: bogus mode/port rejected per platform, valid ones pass. T-0255 added frob:todo T-0270 anchors at the two fields -- this ticket discharges them.

<!-- ticket:T-0272 -->
```yaml
id: T-0272
title: 'std.host: OS-group and sudoers-grant vocabulary'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- docs/strata/**
- tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0256's HOST001 (shared-group sub-target) and HOST002 (sudoers sub-target) cannot structurally prove these two sub-targets because std.host (T-0255) carries no OS-group or sudoers-grant grammar -- both ALWAYS fire (deny-by-default, honest gap) until an explicit waive is written or this ticket adds the grammar. Add: a repeatable 'group "NAME"' owns-adjacent clause (desugars to a group=NAME attr, mirroring runs_as) and a 'sudoers "RULE"' clause (desugars to sudoers=RULE, repeatable) to strata-core/src/parse.rs's parse_node/parse_store, HostManifest gains group: tuple[str,...] and sudoers: tuple[str,...] fields (_host.py), then HOST001's shared-group and HOST002's sudoers sub-targets in _host_isolation.py derive real findings instead of the always-fire placeholder.

<!-- ticket:T-0273 -->
```yaml
id: T-0273
title: 'dup exact_regions: O(k^2) pair emission needs a run-size guard before [dup].region_kernel
  ships enabled'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0193 review finding (non-blocking, feature is off by default): emit_run_pairs is unbounded O(k^2) in run size -- reviewer demonstrated 2000 identical 20-token docs => 1,999,000 pairs in 17.5s, no cap/guard/warning. A real monorepo with thousands of near-identical generated/boilerplate symbols sharing a block >= region_min_tokens would hit multi-second-to-worse pair emission. Add a run-size guard BEFORE anyone flips [dup].region_kernel=true in a real frob.toml: options -- skip/report-truncated beyond some k with a WARN, or downgrade to reporting only the top-N longest matches per run, or cap total pairs with an honest 'truncated at N' signal (never silently drop without a signal, T-0193-recall-bug lesson). Regression: a large-k fixture completes under a time/pair bound and emits the truncation signal.

<!-- ticket:T-0279 -->
```yaml
id: T-0279
title: frob:tests directive src/target direction disagrees between fresh dsl parse
  and stale graph cache
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**,src/frob/gates/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while working T-0259: a fresh frob.graph.dsl.parse_directives call on a frob:tests comment placed above a SOURCE symbol (the _conform.py/_generate.py convention) produces Edge(src=<source symbol>, target=<test id text>). But frob.gates._test_edges groups TESTS edges by edge.target, and _test001_002_one looks up unit_edges.get(record.symref) where record.symref is the SOURCE symbol -- these can never match for a freshly-parsed file. Confirmed empirically: a direct parse_file+parse_directives call on the real, unchanged src/frob/deploy/_generate.py reproduces src=source/target=test (the 'broken' shape), while the live GraphSnapshot's cached edges for that same unchanged file come back reversed (src=test/target=source, the 'working' shape) -- meaning the .frob/cache.db entry for that file predates a src/target semantic change in the current dsl.py/gates code and is silently masking the mismatch by never being invalidated. New frob:tests directives placed above SOURCE symbols (matching every existing precedent in the repo) get spurious TEST001 violations; placing the directive above the TEST method instead with the source symref as target works around it (see T-0259's Done report) but is not documented anywhere as the required convention, and every existing source-side directive in the repo is only 'passing' by cache accident. Fix: either (a) make dsl.py's TESTS-kind edge construction match gates.py's consumption (swap src/target, or attach the comment differently), and force a cache-format bump so all existing cached entries reparse under the corrected semantics, or (b) fix gates.py's lookup to match dsl.py's actual output and same cache-bump concern. Either way this needs a full cache invalidation to reveal how many of the repo's existing frob:tests directives are actually silently non-functional.

<!-- ticket:T-0281 -->
```yaml
id: T-0281
title: 'deploy generate polish: dedup shared runs_as useradd, listens unit hardening,
  multi-host status, CAP_NET_BIND over-grant, DEBUG flood'
state: queued
kind: bug
origin: agent
created: '2026-07-19'
blocked_by: []
parent: T-0254
scope:
- src/frob/deploy/**
- src/frob/strata/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0260 malmberg pilot findings (batched, all in the deploy generator; each needs a fixture+fix): (5) a user shared across a node and a store (media_store+ingest both runs_as malmberg-ingest) emits the useradd guard block TWICE in install.sh -- dedup service-user creation by distinct runs_as identity. (6) listens PORT drives status.sh /dev/tcp health probes but is never materialized into the unit (no .socket, no IPAddressAllow/SocketBindAllow) -- emit network hardening or at least document the port in the unit. (7) status.sh probes 127.0.0.1 for ALL units incl. ones on other hosts (malmberg display is a separate host) -> always reports remote port closed; std.host has no host/placement vocabulary to partition artifacts per host -- design a /placement construct or partition status per declared host (bigger, may split out). (8) may 'net' unconditionally adds CAP_NET_BIND_SERVICE even when all declared listens ports are >=1024 (unprivileged) -- only add it when a listens port is <1024. (4) frob deploy generate floods stdout with per-node 'host manifest runs_as=...' DEBUG lines (repeated per consumer pass) -- route through the logger at DEBUG, mute stdout like check_runner/map_runner (T-0202 class). (10, doc) waive clauses parse but elaborate(...).danger_ok exposes no waivers attribute (read via separate _waive channel) -- add a doc note on reading waivers back from a parsed model. Item 7 (host/placement vocabulary) may warrant its own ticket if it grows.

<!-- ticket:T-0287 -->
```yaml
id: T-0287
title: 'dup: type-generalizing anti-unification (holes bind types, propose generics)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
blocked_by:
- T-0194
- T-0195
parent: null
scope:
- frob-core/**,src/frob/dup/**,tests/**,docs/modules/dup.md,tickets.md
evidence: []
attachments: []
acceptance:
- given two functions identical modulo a type (e.g. sort(list[int]) vs sort(list[str]),
  or a C++ overload set differing only in element type), when dup triage runs anti-unification,
  then the divergence is bound as a TYPE hole (not an opaque value hole) and the group
  is reported as "generalizable over type T" with the concrete instantiations listed
- 'given a type-generalizable group, when the template report renders, then it proposes
  the language-correct generic abstraction: Python def f[T](...), C++ template<typename
  T>, Rust fn f<T>, TS function f<T> -- one suggested signature, not raw $holes'
- given a hole that binds inconsistent types across the two sides (not a single consistent
  T), then it is NOT reported as type-generalizable (no false generic proposal)
threat: null
```
Extends the Plotkin lgg kernel (T-0194) and template report (T-0195). Today anti-unification emits value-holes at any divergence. Many real duplicate pairs differ ONLY in a type: identical algorithm over int vs str, an overload set, a monomorphized-by-hand family. The kernel must classify a hole: if both sides at a divergence are TYPE nodes (annotation, template arg, generic param, cast target) that unify to a single consistent type variable across the whole template, mark it a TYPE hole and record the per-side instantiation. The report then proposes the real fix -- a generic/templated function -- instead of a bare hole template. This is the "reverse templating / abstraction" the user asked for: dup should not just say "these are similar", it should hand back the generic signature that unifies them. Cross-language: each lang backend maps a TYPE hole to its own generics syntax. Consistency guard: a hole whose two sides need DIFFERENT type variables (no single T works) stays a value hole -- do not emit a bogus generic.

<!-- ticket:T-0288 -->
```yaml
id: T-0288
title: 'dup: helper-inlining / call-graph-aware triage (see through arch-forced splits)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/dup/**,tests/**,docs/modules/dup.md,tickets.md
evidence: []
attachments: []
acceptance:
- given two functions whose shared logic was each extracted into differently-named
  PRIVATE helpers (per frob arch small-helper pressure), when dup triage compares
  them, then it resolves the private/module-local helper calls and compares over the
  inlined (or call-graph-closure) body, and still reports the pair as duplicate
- given a private helper called from exactly one site, when triage inlines for comparison,
  then the inlining is bounded (depth + total-node ceiling) and NEVER follows public
  API calls or recurses infinitely (recursion/cycle guard)
- given a cluster of near-identical tiny helpers created by over-splitting, when dup
  runs, then those helpers themselves are reported as a dup group (the inverse failure
  mode -- arch-forced fragmentation producing duplicate helpers)
threat: null
```
Directly motivated by the arch<->dup tension the user raised: frob arch enforces many small private helpers, which (a) HIDES Type-3/4 duplication -- two functions with the same logic split into differently-named helpers now hash/compare as different call skeletons -- and (b) CREATES duplication -- over-splitting spawns families of near-identical one-line helpers. dup currently compares whole bodies (_r1_hash/_r2_hash and the region/anti-unify passes all operate on a single symbol body), so it is blind to logic that lives one call-hop away. Fix: before structural comparison, resolve calls to PRIVATE (leading-underscore / module-local, not re-exported) helpers and splice their bodies into the comparison unit -- a bounded call-graph closure, depth-limited, cycle-guarded, public-API-stopping, node-count-capped (fall back to un-inlined body past the cap). This makes dup measure the ACTUAL logic, not the arch-imposed decomposition. Pair (b): also run a dup pass over the helper population itself so over-splitting is caught. Keep inlining a triage-only view (do not rewrite source); report spans point at the real helper definitions.

<!-- ticket:T-0289 -->
```yaml
id: T-0289
title: 'arch: per-function reasoned override + complexity-aware long-function'
state: in-progress
kind: feature
origin: human
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/arch/**,src/frob/graph/dsl.py,src/frob/gates/**,tests/**,docs/modules/arch.md,tickets.md
evidence: []
attachments: []
acceptance:
- 'given a genuinely atomic long function (big match/case, dispatch table, literal
  data, flat sequential pipeline) with low nesting/cyclomatic complexity, when frob
  arch runs, then it is NOT flagged (complexity-aware: long AND complex fires; long-but-flat
  does not)'
- given a long function the author must keep long, when it carries a reasoned in-code
  directive (frob:waive ARCH001 reason="...", or frob:arch allow-long reason="..."
  ceiling=N), then the finding is WAIVED (counted in the waived tally, auditable),
  and an override without a reason is rejected exactly like a reasoned-less frob:waive
- given a per-function override with a justified ceiling N, when the function later
  grows beyond N, then the waiver stops covering it and it re-fires (bounded, not
  a blank check)
- given the escape hatch, then it lives at the code (in-comment directive travelling
  with the function), NOT as a qualname-keyed table in frob.toml, and raising the
  GLOBAL max_function_lines is not introduced as the sanctioned way to silence findings
threat: null
```
User asked my opinion on per-function arch overrides. Opinion, recorded as the design: YES, worth having, but only if built the frob way. (1) Overrides belong AT THE CODE as reasoned frob:waive-style directives, not in central config -- a qualname table in frob.toml rots silently on rename and hides the exception from the reader; an in-comment waiver travels with the function and justifies the exception at its site, matching every other frob waiver. (2) It must be a WAIVER (counted, auditable, reason-required), never a silent mute -- an un-reasoned override is rejected like a reason-less frob:waive. (3) Prefer a justified CEILING bump over a boolean allow-long: a 45-line match waived to 50 still re-fires if it balloons to 200, keeping the exception honest. (4) Do NOT sanction raising the global threshold -- that is exactly the lazy-developer escape the tool exists to prevent. (5) MOST valuable half: make the heuristic complexity-aware so the bulk of false positives never fire -- a long-but-FLAT function (one match/dict-literal, shallow nesting, low cyclomatic) is not the smell the rule targets; only long-AND-complex is. Auto-exempt flat, require a reasoned waiver for the complex-but-justified residue. This also relieves the arch<->dup tension (T-0288): stop forcing atomic bodies to shatter into helpers that then hide/duplicate.

<!-- ticket:T-0290 -->
```yaml
id: T-0290
title: 'recursion static analysis: prove-terminating-or-error, tail-call + depth-bound
  gate'
state: queued
kind: feature
origin: human
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- frob-core/**,src/frob/perf/**,src/frob/arch/**,src/frob/graph/dsl.py,src/frob/gates/**,tests/**,docs/modules/perf.md,tickets.md
evidence: []
attachments: []
acceptance:
- given any function, when analysis runs, then a static call graph is built and every
  recursive SCC (direct AND mutual recursion) is identified -- purely static, no execution
- 'given a structurally-recursive function (each recursive call is on a provably-smaller
  argument along a well-founded order: list tail, tree child, n-1 on a non-negative
  int, or a strictly-decreasing bounded integer measure toward a guarded base case),
  when the termination checker runs, then it is PROVEN-TERMINATING and passes silently'
- given a recursion the checker CANNOT prove terminating, then it is an ERROR (not
  a warning) -- the author must either refactor into a provable form, or attach a
  reasoned directive (frob:invariant terminates reason="..." with an optional measure),
  which is counted/auditable exactly like every other frob waiver; an UNREASONED unprovable
  recursion can never pass
- given a tail-recursive function in a language without guaranteed TCO (Python especially),
  when detected, then it is flagged with a rewrite-as-loop suggestion AND requires
  a provable depth bound -- unbounded recursion depth that scales with runtime input
  size (stack-overflow / DoS surface) is an error unless a bound is proven or reasoned-waived
- given the arch<->dup<->recursion consistency requirement, then the call graph is
  a SHARED interprocedural substrate reused by T-0288 (dup helper-inlining) and T-0289
  (arch complexity-awareness) -- built once, not three times
threat: null
```
User vision (2026-07-19): frob perf does nothing with recursion today (PERF001-004 are lexical loop smells only). Recursion is a control-flow hazard that must be either statically reasoned about or rejected. NORTH STAR (user, verbatim intent): "you should not be able to write bad code (logically similar or copied); it will be flagged" -- extend that to control flow: no recursion whose termination/depth cannot be statically bounded may pass unreasoned. DESIGN, three layers: (1) DETECT -- build a static call graph, find recursive SCCs incl. mutual recursion (frob-core, reuse for T-0288/T-0289). (2) PROVE-OR-ERROR -- termination is undecidable in general, so be SOUND not complete: prove the decidable fragment (structural descent on a well-founded argument; strictly-decreasing bounded integer measure to a guarded base case), and ERROR on everything unproven. The escape is a REASONED directive (frob:invariant terminates reason=... measure=...), auditable like any waiver -- consistent with the T-0289 arch-override philosophy (prove it, or justify it at the code; never silent). (3) DEPTH/STACK SAFETY -- tail-call detection (user example: Python has no TCO, so tail recursion over runtime-sized input is a stack-overflow/DoS bug): flag tail recursion with a rewrite-as-loop suggestion, and require a proven depth bound; recursion whose depth scales with input and has no bound is an error. CONSISTENCY: this shares the interprocedural call-graph substrate with dup helper-inlining (T-0288) and arch complexity-awareness (T-0289) -- one call-graph facility feeds dup (see through helpers), arch (complexity, mutual-recursion-via-helpers), and this (termination/depth). Unify the escape-hatch philosophy across arch/perf/recursion: the tool proves what it can, and every unprovable residue must carry a reasoned, counted directive -- that is what makes "you cannot write bad code silently" actually hold.

<!-- ticket:T-0292 -->
```yaml
id: T-0292
title: COV003 remediation hint references nonexistent 'frob test --collect' flag
state: queued
kind: bug
origin: agent
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py,src/frob/gates/invariants.py,tests/**,tickets.md
evidence: []
attachments: []
acceptance:
- given a COV003 evidence-resolution failure, when the error message prints its remediation
  hint, then the suggested command is one that actually exists (frob test has no --collect
  flag today); either add the flag or change the hint to the real refresh path
threat: null
```
Hit live 2026-07-19 while closing T-0282: COV003 says "run: frob test --collect to refresh" but `frob test` has no --collect option (argparse rejects it). Root cause of the false COV003 was a stale .frob/pytest-collect.json cache after a merge added new evidence tests; the cache did refresh on the next collection pass, but the user-facing hint points at a nonexistent flag. Fix: either implement `frob test --collect` (force a collection-cache rebuild without running tests) -- the cleaner option, since there is a genuine need to refresh the cache on demand -- or correct the hint to whatever the real refresh path is. Prefer adding the flag.

<!-- ticket:T-0293 -->
```yaml
id: T-0293
title: evidence recording must normalize/reject Class.method vs Class::method separator
state: queued
kind: bug
origin: agent
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**,src/frob/gates/__init__.py,src/frob/testing/**,tests/**,tickets.md
evidence: []
attachments: []
acceptance:
- given evidence recorded as file::Class.method (dot before method), when it is stored,
  then it is either normalized to the canonical pytest file::Class::method form or
  rejected at record time with a clear message -- never silently stored to fail COV003
  downstream
- 'given the canonical :: form, when resolved against collected node ids, then it
  matches (regression: the T-0282/T-0217 dot-form evidence that slipped past)'
threat: null
```
Bit twice (2026-07-19): T-0282 and T-0217 both had evidence stored as tests/...py::Class.method with a DOT between class and method, which never resolves against pytest node ids (Class::method) and surfaces only as a late, confusing COV003 at check time. The recording path (frob ticket evidence / Done-report evidence capture) must canonicalize to :: (or reject) at write time. Cheapest sound fix: normalize a single-dot-before-final-segment in a ::-qualified test id to ::, OR validate against the collected manifest at record time and refuse an unresolvable id. Pairs with T-0292 (COV003 hint bug) -- same gate, both about making COV003 failures self-explanatory and hard to create.

<!-- ticket:T-0297 -->
```yaml
id: T-0297
title: COV001 cannot detect directive rebound to WRONG symbol (only checks attached-to-something)
state: queued
kind: bug
origin: auditor
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py,src/frob/graph/**,tests/**,docs/modules/gates.md,tickets.md
evidence: []
attachments: []
acceptance:
- given a frob:tests/doc/waive/ticket directive that a refactor displaced from its
  intended public function onto a newly-extracted private helper (the exact hazard
  that hit two arch slices), when COV001 runs, then it FLAGS the mis-binding -- today
  it passes because it only verifies a directive resolves to SOME symbol, not the
  correct one
- given a legitimately-moved symbol whose directive correctly moves with it, then
  no false positive fires
threat: null
```
Surfaced by reviewer 2026-07-19 during the core-commands arch burndown: extracting a helper directly above an existing def silently rebinds that defs frob: directives onto the new (private) helper. COV001 does NOT catch this -- it only checks a directive is attached to a resolvable symbol, not the semantically-intended one. So a frob:waive TEST005 or frob:tests evidence binding can silently start describing the wrong function (misrepresenting coverage debt / test evidence) and every gate stays green. This bit TWICE (scan_tree, renumber_one) and was only caught by manual review. Candidate detections: (a) a directive whose target is a PRIVATE (_underscore) symbol when the same directive kind/anchor previously bound a public symbol in that file (git-diff-aware), (b) a frob:tests binding whose named test function bodies do not actually exercise the bound symbol (call-graph reachability -- ties into the shared call-graph substrate of T-0288/T-0290), (c) a frob:doc #public-api anchor on a private helper. This is core to the north star: a displaced obligation is worse than a behavior bug because it is silent. See [[static-quality-vision]].

<!-- ticket:T-0298 -->
```yaml
id: T-0298
title: 'COV003: resolve file-level and directory-level evidence (any collected test
  under the path)'
state: queued
kind: feature
origin: agent
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py,src/frob/testing/**,tests/**,docs/modules/gates.md,tickets.md
evidence: []
attachments: []
acceptance:
- given ticket evidence naming a whole test FILE (tests/test_vet.py) or a DIRECTORY
  (tests/unit/deploy), when COV003 resolves it, then it resolves iff the collected
  manifest contains at least one node under that path -- not an error
- given evidence that resolves to no collected test at any granularity (typo, deleted
  file), then COV003 still errors (the real failure is preserved)
threat: null
```
Root cause of a 25-error main-red incident 2026-07-19: both arch-burndown agents recorded file-level evidence (tests/test_vet.py, tests/unit/deploy) and one embedded a kind="unit" attr into the id, none of which resolve because COV003 only matches node-level file::Class::method against the collected manifest. For a refactor touching ~20 files, "this whole test file passes" is a reasonable and natural evidence granularity; forcing one node-id per file is what led both agents (and me at close) to record unresolvable ids. Make file- and directory-level evidence first-class: resolve iff >=1 collected node lives under the path. Complements T-0293 (reject/normalize a genuinely-unresolvable id at RECORD time) and T-0292 (fix the bogus "frob test --collect" hint) -- together these make COV003 both lenient where it should be and strict where it must be. Until this lands, evidence MUST be node-level file::Class::method.

<!-- ticket:T-0300 -->
```yaml
id: T-0300
title: Rebind frob.fuzz deferred-work TODOs off dropped T-0002
state: queued
kind: bug
origin: human
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/fuzz/**
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0294 fixed the DSL parser's trailing-prose rejection, which un-masked two frob:todo T-0002 directives in src/frob/fuzz/_run.py:30 and src/frob/fuzz/_arbitrary.py:41 (process-global registry scoping; wall-clock budget_s). T-0002 (frob.fuzz generators + FUZZ gates Phase 8) is dropped, so TODO001 now correctly fires: these TODOs are not bound to an open ticket. Either reopen T-0002's scope in a live ticket and rebind, or file focused successor tickets per TODO and rebind. Filed rather than fixed in T-0294 to stay within that ticket's declared DSL-parser scope (this is a ticket-graph bookkeeping fix, not a parser fix).

<!-- ticket:T-0319 -->
```yaml
id: T-0319
title: 'packaging: frob doctor subcommand to verify+remediate missing native extensions'
state: queued
kind: feature
origin: human
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/**,docs/**,tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
Follow-up from T-0316: no install-time guard exists against a plain 'uv tool upgrade frob' (or 'uv tool install --force --reinstall frob' without --with) silently stripping the strata_core/frob_core native extensions that 'make install-tool' added. T-0316 documents a manual 'python3 -c "import strata_core, frob_core"' check plus the loud SYS004/NativeExtensionUnavailable failure gates already provide as the honest fallback. This ticket is to build a real 'frob doctor' (or 'frob --version --verbose') subcommand that runs that same check, reports native-extension presence/version, and prints the exact 'make install-tool' remediation -- so the check is a first-class CLI surface instead of a paragraph in docs/guides/install.md. Also re-evaluate publishing strata-core/frob-core as real PyPI wheels (docs/guides/install.md 'Why not pip install frob[strata]?' section) as the actual long-term fix; that publish step needs PyPI project ownership/CI credentials this environment does not have, so it stays a separate decision, not blocking the doctor subcommand.

<!-- ticket:T-0320 -->
```yaml
id: T-0320
title: 'COV002 grace: require an actual open->done ticket transition, not just marker-in-hunk'
state: queued
kind: bug
origin: auditor
created: '2026-07-19'
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py,tests/**,tickets.md
evidence: []
attachments: []
acceptance:
- given a symbol bound to an ALREADY-DONE (stale) ticket and a diff that edits that
  same ticket entry for a non-close reason (typo fix / evidence append touching its
  marker line), when COV002 runs, then grace is NOT granted (it still fires) -- grace
  requires the ticket to transition open->done in THIS diff
- given a ticket genuinely closing in this diff (open before, done after), then grace
  is granted (catch-22 stays fixed)
threat: null
```
Follow-up from T-0214 (reviewer-recommended, not blocking). T-0214 closed the exploitable COV002 grace bypass by requiring the bound DONE tickets own <!-- ticket:T-#### --> marker line to fall inside the diffs tickets.md hunk. That closes the easy/invisible case (unrelated ticket close elsewhere in the commit). Residual narrow gap: marker-in-hunk is a PROXY for "closing" -- it does not verify a state TRANSITION, so any edit to a stale DONE tickets own entry that touches its marker line (typo fix in its Done report, evidence append, reformat) grants grace to a bound-but-uncovered stale symbol. Narrow + visible in diff review, hence not blocking, but should be tightened: compare the tickets state in the diffs BEFORE vs AFTER tickets.md (open-before / done-after) rather than mere marker-span overlap. Requires diffing ledger state pre/post within the gate.
