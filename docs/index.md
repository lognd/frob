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
- `docs/guides/editors.md` -- syntax highlighting for `.strata` in VSCode
  and JetBrains IDEs via one drift-locked TextMate grammar.
- `docs/guides/exhaustive-research.md` -- the frontier-loop for total-coverage
  research (audit every module, read every paper): external pending/done
  store instead of an in-context to-do list, plus the `.mcp.json` wiring for
  `fetch`/`arxiv`.

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
  level heat-maps (`frob perf heat`), and the PERF001..PERF004 linear-scan
  gates.
- `docs/modules/serve.md` -- `frob.serve`: the `frob serve` MCP stdio adapter
  exposing doable tickets, stale docs, scope checks, and graph queries as
  read-only tools.

Two modules that support the above but are not yet fully re-platformed:

- `docs/modules/lang.md` -- `frob.lang`: the tree-sitter parsing core (symbols +
  comments, five languages) that `frob.graph` is built on.
- `docs/modules/dup.md` -- `frob.dup`: duplicate/clone detection, including the
  0.2.0 smart-dup design (region-granular semantic clones, DUP001/DUP002
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
  only (vet integration is T-0147).
- `docs/modules/release.md` -- `frob.release`: mechanical semver from the
  public-API graph, `frob release stamp|check`, and the REL001 gate.
- `docs/modules/stats.md` -- `frob.stats`: DORA-ish delivery measurement (queue
  health + commit cadence); measurement only, never a gate.
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

## Per-command references

Kept commands, each with usage, real output, and a "why it exists" section:

| Doc | Command |
|---|---|
| `docs/commands/scaffold.md` | `frob scaffold` |
| `docs/commands/cycle.md` | `frob cycle` |
| `docs/commands/outline.md` | `frob outline` |
| `docs/commands/map.md` | `frob map` |
| `docs/commands/xref.md` | `frob xref` |
| `docs/commands/exports.md` | `frob exports` |
| `docs/commands/parse.md` | `frob parse` |
| `docs/commands/gitlog.md` | `frob gitlog` |
| `docs/commands/check.md` | `frob check` |
| `docs/commands/sys.md` | `frob sys` (plan T-0084, export T-0086) |

`frob graph`, `frob ack`, `frob ticket`, and `frob test` are documented in
their owning module design docs above (`docs/modules/graph.md`, `docs/modules/tickets.md`,
`docs/modules/testing.md`) rather than as separate per-command pages, since their
usage is inseparable from the data model they operate on.

## Planned / tracked work

- `tickets.md` -- the dispatchable queue (`frob ticket doable`): open work,
  blockers, and anything
  recorded as explicitly cut scope.
