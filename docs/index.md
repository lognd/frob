# frob docs

frob is the enforcement layer for agentic development: an obligation graph,
a statically-checkable ticket queue, and gates that turn unaccounted-for
work into a `frob check` failure. Start with `docs/rework.md` for the
architecture, then `docs/guides/quickstart.md` to see the enforcement loop run for
real.

## Architecture overview

- `docs/rework.md` -- the identity, the module dependency graph, the alpha
  purge (what was deleted and why), the agents/skills redesign, and the
  cross-cutting design decisions. Read this first.

## Getting started

- `docs/guides/install.md` -- the bare, full (native-extension), and dev
  install paths, and why the standalone tool needs --with for the crates.
- `docs/guides/quickstart.md` -- a real end-to-end walkthrough: build the graph,
  file a ticket, annotate code, hit a violation, fix it, ack, test, close.
- `docs/guides/agentic-workflow.md` -- the human/AI split: how planner, implementer,
  reviewer, prover, and the auditors use the ticket queue and gates as the
  shared work surface, including the worktree-per-agent pattern.
- `docs/guides/agent-playbook.md` -- the per-dispatch checklist: worktree
  warm-up, scope/evidence/gate discipline, the deletion-filter land rule,
  and ledger-conflict splice guidance. Every worktree agent should read
  this before starting a ticket.
- `docs/guides/editors.md` -- syntax highlighting for `.strata` in VSCode
  and JetBrains IDEs via one drift-locked TextMate grammar.
- `docs/guides/exhaustive-research.md` -- the frontier-loop for total-coverage
  research (audit every module, read every paper): external pending/done
  store instead of an in-context to-do list, plus the `.mcp.json` wiring for
  `fetch`/`arxiv`.
- `docs/guides/estate-capability-migration.md` -- the per-repo recipe for
  narrowing a `.strata` `may` declaration to the precise `family.mode`
  capability spelling (`fs.read`/`fs.write`, `net.connect`/`net.listen`),
  plus the T-1071 fleet-routed ticket record for the sibling estate.
- `docs/guides/estate-natives-build-rollout.md` -- the per-repo recipe for
  converting a sibling's hand-rolled `maturin develop` Makefile step to
  the one-line `frob natives build` shim, plus the T-1031 fleet-routed
  ticket record for the sibling estate.

## Extending frob

One guide per registry/extension point, on a common template (what/where,
add-an-entry recipe, which drift-locks fire, worked example, common
mistakes). The machine-readable inventory is
`docs/guides/extending/registry_of_registries.json`; the completeness
drift-lock (`tests/unit/test_extending_guides_complete.py`) fails the build
if a registry gains no guide. Start at `docs/guides/extending/README.md`.

- `docs/guides/extending/gate-rule-families.md` -- adding a rule id to a gate family
- `docs/guides/extending/comment-dsl-directives.md` -- adding a `frob:<verb>` directive
- `docs/guides/extending/threat-catalog.md` -- weaknesses, out-of-scope entries, views
- `docs/guides/extending/benign-capabilities.md` -- excusing a capability kind honestly
- `docs/guides/extending/compliance-registry.md` -- regulations and views
- `docs/guides/extending/capability-registry.md` -- dangerous operations, matrix cells, excuses
- `docs/guides/extending/cve-fingerprints.md` -- code-level CVE pattern classes
- `docs/guides/extending/pii-categories.md` -- the personal-data category set
- `docs/guides/extending/design-lint-rules.md` -- operational lints LINT001-005
- `docs/guides/extending/secrets-scan-providers.md` -- credential-shape patterns
- `docs/guides/extending/prover-claim-kinds.md` -- claim kinds the prover evaluates
- `docs/guides/extending/scenario-kinds.md` -- scenario rewrites and results
- `docs/guides/extending/strata-surface-grammar.md` -- surface keywords + tmLanguage lock
- `docs/guides/extending/test-runner-entries.md` -- `[[test.runner]]` entries
- `docs/guides/extending/language-grammar-handlers.md` -- adding a source language
- `docs/guides/extending/sys-export-formats.md` -- `frob sys export` formats
- `docs/guides/extending/litmus-fixtures.md` -- the permanent litmus goldens
- `docs/guides/extending/ticket-kinds-states.md` -- ticket kinds, states, strides
- `docs/guides/extending/dup-detector-registry.md` -- the R1-R7 rung ladder, DUP001/DUP002

## Module design docs

The four components that make up the enforcement layer:

- `docs/modules/graph.md` -- `frob.graph`: the obligation graph engine, the comment
  DSL (`frob:ticket`, `frob:tests`, `frob:doc`, `frob:invariant`,
  `frob:waive`, ...), digests, the lock file, and drift.
- `docs/modules/tickets.md` -- `frob.tickets`: the ticket/feature queue, its state
  machine, attachments, and clipboard capture.
- `docs/modules/gates.md` -- `frob.gates`: the drift, coverage, scope, pre-work,
  invariant, test, and policy gates; the rule catalog; invariants; and
  `frob check` integration.
- `docs/modules/testing.md` -- `frob.testing`: touched-set selection across the diff,
  the per-language runner registry, and worktree-correct git semantics via
  `frob.gitio`.
- `docs/modules/perf.md` -- `frob.perf`: profiling (`frob perf profile`), symbol-
  level heat-maps (`frob perf heat`), and the PERF001-008,PERF012 detection
  gates.
- `docs/modules/serve.md` -- `frob.serve`: the `frob serve` MCP stdio adapter
  exposing doable tickets, stale docs, scope checks, and graph queries as
  read-only tools.

Two modules that support the above but are not yet fully re-platformed:

- `docs/modules/lang.md` -- `frob.lang`: the tree-sitter parsing core (symbols +
  comments, seven languages) that `frob.graph` is built on.
- `docs/modules/dup.md` -- `frob.dup`: duplicate/clone detection, including the
  0.2.0 smart-dup design (region-granular semantic clones, DUP001/DUP002/DUP003
  gates).
- `docs/modules/dup-sota-survey.md` -- T-0187 phase-1 survey: clone-detection
  state of the art dispositioned against `frob.dup` (26 techniques), the
  reverse-templating design sketch, the exhaustiveness-matrix meta-test
  design, and the source of the T-0191..T-0199 ticket tree.
- `docs/modules/fuzz.md` -- `frob.fuzz`: the 0.2.0 enforced property fuzzing design
  (Arbitrary protocol, FUZZ gates).
- `docs/modules/vet.md` -- policy/vetting notes referenced by `frob.gates`.
- `docs/modules/cve.md` -- `frob.cve`: pydantic v2 models and a local-mirror
  parser for CVE Record Format v5 (cvelistV5); no network, parser+models
  only (vet integration shipped as `src/frob/vet/_cve.py`, T-0147).
- `docs/modules/release.md` -- `frob.release`: mechanical semver from the
  public-API graph, `frob release stamp|check`, and the REL001 gate.
- `docs/modules/stats.md` -- `frob.stats`: DORA-ish delivery measurement (queue
  health + commit cadence); measurement only, never a gate.
- `docs/modules/clean.md` -- `frob.clean`: tiered, artifact-only workspace
  cleanup (`frob clean [--all|--deep] [-y]`); allowlist-only, never touches
  source or git-tracked files.
- `docs/modules/decisions.md` -- ADR decision records (`decisions/AD-###.md`),
  `frob:decision` anchors, and the DEC gates.
- `docs/modules/mutate.md` -- `frob.mutate`: mutation testing, the honest
  test-quality oracle.
- `docs/modules/arch.md` -- `frob.arch`: architectural smell detection (long
  functions, god classes) over the shared `frob.lang` parse.
- `docs/modules/process.md` -- `frob.process`: the tool-output parsers (ruff, ty,
  clang-tidy, valgrind, tsc, eslint, junit) and the shared `Diagnostic`/
  `TestCase`/`ToolResult` types `frob check` consumes.

Support modules underneath the above:

- `docs/modules/app.md` -- `frob.app`: the App/AppConfig runtime wiring and CLI
  entry (`__main__`).
- `docs/modules/cli.md` -- CLI command tier ledger: which subcommands are
  plumbing kept as-is, versus regrouped under `frob explore` (T-1238,
  supersedes the T-0580 navigation-porcelain deprecation).
- `docs/modules/bind.md` -- `frob.bind`: verifies `// BIND:` declarations in
  pybind11/PyO3 glue match a real native-side function, so a Python-facing
  binding never drifts from the C++/Rust signature it wraps.
- `docs/modules/logging.md` -- `frob.logging`: the module-logger/dictConfig setup
  and the `quiet_stdout_logs` helper that keeps `--json` output clean.

## strata -- the system-design language (in design; epic T-0047)

strata is frob's provable system-design language: deny-by-default
architecture models (trust lattices, flows, boundaries, capacity, crash
and breach scenarios) checked like code and bound two-way to the
obligation graph. Charter and component designs:

- `docs/strata/charter.md` -- north star, the six laws, the three
  collapses, decisions, glossary. Read this first.
- `docs/strata/kernel.md` -- the six primitives, conditional flows, claim
  forms and decision procedures, verdicts.
- `docs/strata/surface.md` -- grammar, vocabularies, construct semantics,
  refinement hierarchy, module system.
- `docs/strata/evidence.md` -- the L1-L5 evidence ladder, quantifiers,
  tool attestations, the enables soundness cascade, the assumption ledger.
- `docs/strata/policy.md` -- the five universal policy forms, semantic
  scoping, policy packs.
- `docs/strata/boundary.md` -- the six-phase boundary contract,
  outcome-conditioned frames, failure atomicity, crash contracts.
- `docs/strata/roadmap.md` -- phases 0-5 with exit criteria, the litmus
  program, the ticket map (T-0047..T-0086).
- `docs/strata/threat.md` -- the obligation catalog: CWE/CVE security
  weaknesses plus performance, reliability, compatibility, and compliance
  (COPPA/GDPR/HIPAA + privacy-policy-as-claims) anti-patterns as
  conditional obligations with a three-part exhaustiveness proof
  (epic T-0109).
- `docs/strata/selfconform.md` -- self-conformance: SYS100-106, the check
  that our own `src/frob/` capability surface actually matches what
  `design/frob.strata` declares (T-0150).

## Per-command references

Each with usage, real output, and a "why it exists" section (`map`,
`outline`, `xref` were DEPRECATED under T-0580/T-0802; T-1238 rescinded
that sunset and regrouped all three, plus `frob docs --search`, under
`frob explore` -- see `docs/design/cli-regrouping.md` and
`docs/modules/cli.md`):

| Doc | Command |
|---|---|
| `docs/commands/scaffold.md` | `frob scaffold` |
| `docs/commands/cycle.md` | `frob cycle` |
| `docs/commands/outline.md` | `frob outline` / `frob explore outline` |
| `docs/commands/map.md` | `frob map` / `frob explore map` |
| `docs/commands/xref.md` | `frob xref` / `frob explore xref` |
| `docs/commands/exports.md` | `frob exports` |
| `docs/commands/parse.md` | `frob parse` |
| `docs/commands/gitlog.md` | `frob gitlog` |
| `docs/commands/check.md` | `frob check` |
| `docs/commands/sys.md` | `frob sys` (plan T-0084, export T-0086) |
| `docs/commands/deploy.md` | `frob deploy` (generate T-0257) |

`frob graph`, `frob ack`, `frob ticket`, and `frob test` are documented in
their owning module design docs above (`docs/modules/graph.md`, `docs/modules/tickets.md`,
`docs/modules/testing.md`) rather than as separate per-command pages, since their
usage is inseparable from the data model they operate on.

## Design docs (active epics)

Design-first epics landed 2026-07-29; each doc is the canonical design its
epic's children implement:

- `docs/design/refactor-verb.md` -- T-1135: transactional frob refactor
  move/rename/split with full reference, directive, and prose rewrite.
- `docs/design/ledger-v2.md` -- T-1136: per-ticket files replacing the
  tickets.md monofile, with locks, merge story, and reversible migration.
- `docs/design/check-fix-engine.md` -- T-1137: tiered frob check --fix
  auto-fix engine (Tier A/B/C, fixability registry, no auto-waivers).
- [`docs/design/land-checkpoint-durability.md`](design/land-checkpoint-durability.md)
  -- T-1554: the post-commit checkpoint gap in `frob ticket land` beyond
  T-1523's sweep-window marker (audit of what remains unmarked, Option A
  vs B, recommendation).
- [`docs/design/cli-hygiene.md`](design/cli-hygiene.md) -- T-1556: CLI
  hygiene principles backed by real papercuts (destructive-verb-by-
  dropped-argument, scope-closure warning volume, and related output
  discipline rules `frob ticket new`/`scope` apply).
- `docs/audits/docs-staleness-2026-07-29.md` -- the 121-doc staleness
  sweep whose findings drive the T-1226 docs-integrity epic and the
  T-1233 fix campaign.

## Design research corpora (arch + strata check foundations)

Cited, exhaustive design foundations that feed the arch epic (T-0330), the
strata-systems epic (T-0331), the pattern recommender (T-0332), the sound
capability may-analysis (T-0339), and conformance totality (T-0341):

- `docs/design/architecture-check-catalog.md` -- the exhaustive
  architecture/systems check catalog (GoF, Fowler smells, Release It!,
  cloud patterns, 12-factor), tagged by checkability tier.
- `docs/design/design-pattern-catalog.md` -- exhaustive cited enumeration of
  the design-pattern universe (341 patterns across GoF/POSA/PoEAA/EIP/DDD/
  cloud/...), primary-source citations per pattern, cross-linked to traps.
- `docs/design/design-pattern-traps-corpus.md` -- cited practitioner
  corpus of pattern/principle TRAPS (the "El Dorado" failure modes) with a
  static hallmark per trap.
- `docs/design/system-design-corpus.md` -- cited system-design canon at all
  scales (distributed fundamentals, consensus, DDIA, resilience/SRE,
  performance, observability, HW->FW->SW->service boundaries, and verified
  primary-contributor lessons), each tagged by strata-checkability.
- `docs/design/gate-semantics-classification.md` -- T-1663: every gate rule
  classified semantic/legitimately-lexical/lexical-and-wrong, the T-1662
  epic's precursor evidence map.
- `docs/design/coding-performance-corpus.md` -- cited code-level performance
  corpus: conceptual/algorithmic (complexity traps, data-structure choice)
  and low-level/mechanical-sympathy (cache/branch/alloc/SIMD; Drepper, Fog,
  H&P), mapped to frob.perf PERF rules (implemented/gap/advisory).
- `docs/design/system-performance-corpus.md` -- cited system-performance
  corpus (USE/RED methods, resource analysis, profiling/flame graphs,
  queueing/USL, latency/coordinated-omission, capacity; Gregg/Gunther/Tene),
  each tagged by strata-checkability.
- `docs/design/security-corpus.md` -- cited security/weakness corpus (CWE
  Top 25, OWASP Top 10, CVE fingerprint classes, threat-modeling frameworks,
  Saltzer & Schroeder), each tagged by strata-checkability.
- `docs/design/cwe-1000-registry.md` -- the COMPLETE MITRE CWE-1000 view
  (all 944 weaknesses, CWE 4.20) with a per-entry disposition each
  (checkable / duplicate-of / out-of-scope naming the missing kernel
  concept), grouped into 18 named out-of-scope buckets.
- `docs/design/compliance-corpus.md` -- cited compliance-framework corpus (16
  frameworks: SOC2/PCI-DSS/HIPAA/GDPR/NIST/ISO27001/CIS/ASVS/SLSA...), 599
  controls tagged code-checkable vs process.
- `docs/design/secrets-pii-corpus.md` -- cited secrets-detection (gitleaks/
  trufflehog/detect-secrets rule universe + provider token formats) and PII/
  sensitive-data taxonomy (GDPR/CCPA/HIPAA/PCI), with detection signatures.
- `docs/design/supply-chain-corpus.md` -- cited supply-chain threat/defense
  corpus (typosquat/dependency-confusion/xz-backdoor; SLSA/Scorecard/Sigstore/
  SBOM/OSV), each mapped to frob.vet implemented-vs-gap + detection signature.
- `docs/design/capability-evasion-taxonomy.md` -- per-language-spec
  enumeration of every capability-scan evasion construct (static-resolvable
  vs runtime-opaque).
- `docs/design/structural-linter-adversarial-hardening.md` -- the
  anti-evasion structure (ground-truth grounding, model<->code conformance,
  fail-closed, bounded escape hatches, gated config).
- `docs/design/language-adapter-tier-decision.md` -- T-0691's decision on
  the next language-adapter tier (Go/Java/C#): none for now, demand-driven
  per the 9-repo estate's actual language mix, with a reopen criterion.
- `docs/design/tickets-package-scope-precedent.md` -- T-1145's decision on
  when a ticket may legitimately declare the broad `src/frob/tickets/**`
  scope glob (package-wide redesign/residue work) vs. when SCOPE002's
  nudge means narrow it to the specific module(s) touched.
- `docs/design/registry/` -- the UNIFIED design-knowledge registry: the
  single machine-readable source of truth (per-domain YAML, canonical
  namespaced ids, cross-refs, per-entry disposition) that all the corpus
  docs above feed into.
- `docs/design/registry/README.md` -- the registry schema and index.
- `docs/design/registry/RECONCILIATION.md` -- the prose-only / split /
  undispositioned findings the T-0343 drift-lock (bound to this registry)
  must drive to zero (epic T-0346).

## Capability audits (North-Star hardening, epic T-0397)

Full-repo pessimistic capability audit (2026-07-20): every way a green
`frob check` could be a lie, per subsystem. Remediation tracked under T-0397.

- [docs/audits/README.md](audits/README.md) -- the audit index + honest
  per-subsystem "is this good enough?" verdicts + cross-cutting themes.
- [docs/audits/tickets-testing.md](audits/tickets-testing.md) -- evidence integrity.
- [docs/audits/tickets-testing-round2.md](audits/tickets-testing-round2.md) -- evidence integrity convergence re-audit (round 2).
- [docs/audits/frob-blindspots-2026-07-23.md](audits/frob-blindspots-2026-07-23.md) -- structural-inefficiency/security blind spots frob's own gates bless (kill-switch wiring, lease-layer respawns, daemon argv trust boundary); fix+gate tickets T-0778..T-0786.
- [docs/audits/strata.md](audits/strata.md) -- proof-engine vacuous-proof gaps.
- [docs/audits/vet.md](audits/vet.md) -- capability/supply-chain resolution + fail-open.
- [docs/audits/gates-accounting.md](audits/gates-accounting.md) -- accounting gates.
- [docs/audits/gates-quality.md](audits/gates-quality.md) -- quality/security detectors.
- [docs/audits/graph.md](audits/graph.md) -- graph foundation.
- [docs/audits/lang-check-docs.md](audits/lang-check-docs.md) -- polyglot enforcement.
- [docs/audits/perf.md](audits/perf.md) -- frob check hotpaths + caching.
- [docs/audits/gates-vacuous.md](audits/gates-vacuous.md) -- gate-by-gate vacuous-satisfaction sweep, full catalog (125 rule ids, zero unswept): SCOPE001 empty-scope, partial-parse symbol drop, _KNOWN_GATE_RULES omissions, registry/design-dir-deletion, dup native-fallback, private-parse silent-skips, lang parser DoS boundary; 7 fix+gate ticket pairs filed.
- [docs/audits/docs-completeness-2026-08-06.md](audits/docs-completeness-2026-08-06.md) -- T-1610's mechanical CLI/env-var/rule-catalog sweep against docs/: FROB_WORKER_STDOUT_LOG_LEVEL undocumented (fixed here), docs/modules/gates.md's rule-catalog table missing ~122 real rule ids, frob coverage lacking its own doc section; two follow-up tickets filed. Input to T-1611's detector-gap audit.
- [docs/audits/check-performance.md](audits/check-performance.md) -- T-0928 end-to-end `frob check` profile: `frob.perf`'s own collectors are blind to thread-pool/process-pool gate dispatch; ranked wall-clock hot-path table anchored on `gate-summary` brackets instead; four follow-up tickets filed.
- [docs/audits/test005-zero-classification-t1418.md](audits/test005-zero-classification-t1418.md) -- T-1418: all 306 symbol-level TEST005 findings at exactly 0.0% branch coverage classified as coverage-combine attribution artifacts, not genuine gaps.

## Planned / tracked work

- `tickets.md` -- the dispatchable queue (`frob ticket doable`): open work,
  blockers, and anything
  recorded as explicitly cut scope.
