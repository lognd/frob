# Plugins: one mechanism for the standard library and third parties

Status: draft
Owner: gob
Decisions: D76
Audience: contributor

Provenance: ACCEPTED with changes (D76, owner review 2026-10-04, ticket
~J8PJHKX). The changes: GRL is the one rule language (no second source
form), so it must be intuitive (grl-spec.md, ticket ~4QBTKCK); built-in
rules are compiled into the binary for speed and treated logically the
same as plugin rules (section 6.1).
Evidence: notes/research/plugins.md (wasmtime, dprint, swc, Zed, Typst,
Extism, oxlint, ruff, dylint, Semgrep, CodeQL, stack-graphs, tree-sitter
WASM grammars, pluggy and pytest measured locally). Depends on
universal-model.md (U, queries, evaluator, polarity), packs.md (pack
format, lock), grmb-spec.md (selectors, templates), binding.md (matrix),
rules.md (rule metadata).

## 1. What the owner asked for, and the design's answer

First-class plugins: universal rules (over U, every language) and
single-language rules (over one language's tree), capability atoms,
detectors and matrix-build excuse templates, loadable from a standard
library or from a third-party plugin, with performance close to code
compiled into the binary.

The answer, taken from pytest's best idea and fixed where pytest is slow:

1. **The standard library is built as plugins.** Every built-in rule,
   atom, detector, vocabulary, template and language adapter is
   registered through the same public pack API a third party uses.
   pytest's core is thirty plugins on pluggy; ours is a set of std packs
   on gob-packs. There is no private back door, and CI enforces it.
2. **Performance parity comes from running everything in one engine,
   not from making foreign code fast.** Most rules are declarative and
   are compiled into the same plan format whether they ship inside the
   binary or on disk. One executor runs both. A plugin rule written in
   the declarative tiers therefore runs at exactly the speed of a
   built-in one; only loading differs, and loading is cached by digest.
3. **Arbitrary code is the last resort, sandboxed and batched.** Rules
   that cannot be declarative run as WebAssembly components, called once
   per file over a flat arena, never once per node. That is the
   difference between oxlint's 48 ms and its 236 ms.
4. **Honesty holds for plugins too.** A plugin that runs out of its time
   budget, traps, or asks for an effect it was not granted produces an
   Unresolved finding for the subjects it did not finish. It never
   produces silence.

## 2. Packs: the unit of extension

A pack is a directory or archive with a manifest (`pack.toml`) and
content. The manifest declares what the pack provides and what it
needs:

```toml
[pack]
name = "py-safety"
version = "1.2.0"
families = ["PYS"]          # rule id prefixes this pack owns
needs = { grimble = ">=2.0", u = "1" }

[provides]
atoms = "atoms.toml"         # tier 1
templates = "templates.toml" # tier 1 (matrix-build excuses)
rules = ["rules/*.grl"]      # tier 2
wasm = []                    # tier 3, empty: pure declarative pack
adapters = []                # tier 4

[effects]                    # what a tier-3 component may do (deny by default)
```

Sources, in resolution order (packs.md section 3 is kept):

| Source | Where | Trust |
|---|---|---|
| std | compiled into the binary as precompiled plan bytes (`include_bytes!`) and inventory entries | the binary's own |
| repository | `packs/<name>/` in the repository | reviewed with the code |
| external | URL plus content digest, fetched by `grimble packs update` | pinned in the lock, optional signature |

Nothing activates by being installed. A pack is active only when listed
in `[packs] enabled` and pinned in `grimble.packs.lock` (packs.md 4). This
replaces pytest's entry-point auto-discovery, whose import-time cost and
surprise activation the survey measured.

There are no directory-scoped packs (owner decision 2026-10-04): no
pack file in a subdirectory changes what applies there. Rules that apply
to part of a repository are activated per path from the one root
configuration:

```toml
[[packs.enable]]
name  = "react"
paths = ["frontend/**"]
```

One file says what applies where, so a reviewer and a newcomer read one
place. `grimble config --for <file>` prints the packs and rules in
effect for that file and the config line each came from. Rejected
because of locality-of-definition confusion: ESLint removed cascading
config in its flat-config redesign for that reason, ruff never merges
nested configs, and pytest's conftest lookup is a recurring source of
"where does this come from" questions. A nested `grimble.toml` is a
separate project (its own root, no merging), as in ruff.

Rule ids stay FAMILYNNN. A pack owns the families it declares; two packs
declaring one family is PACK004. The std packs own the existing families.

## 3. The tiers

| Tier | Content | Runs as | Speed relative to built-in |
|---|---|---|---|
| 0 | kernel and engine (walk, U, scope graph, evaluator, matrix, lock) | compiled Rust | itself |
| 1 | data: atoms, detectors, vocabularies, matrix-build excuse templates, claim templates | parsed TOML, interned into the registry | identical: data |
| 2 | declarative rules: universal relational rules and single-language pattern rules | compiled plans run by the host executor | identical by construction (same executor and plan format as std) |
| 3 | code rules | wasmtime components, AOT-compiled and cached | bounded by a benchmark gate (section 6) |
| 4 | language adapters | grammar (native or WASM tree-sitter) plus declarative mapping and scope files | parse cost measured per adapter; mapping identical |

Rejected, with the survey's reasons: Rust dylib/cdylib plugins (no stable
ABI, undefined behaviour on mismatch, unsandboxed; abi_stable and stabby
included); an embedded scripting language as the rule host (per-node
interpreter calls); IPC for in-loop rules; passing the AST through the
plugin ABI (swc's serialization cost); per-node callbacks of any kind;
wasmer and wasm3; a registry service in version 1.

## 4. Universal versus single-language rules

Every rule declares its language reach:

- `lang = "*"` (universal). The rule may use only the universal operators
  of U, the scope graph, the 47 queries of universal-model.md 5 and
  declared capabilities. The plan compiler rejects a universal plan that
  references an adapter operator or a concrete-tree pattern, so
  universality is checked, not promised. On a language whose adapter
  lacks a needed capability the rule reports Unresolved or NotApplicable
  per universal-model.md 4.
- `lang = "rust"` (single-language), or a list. The rule may additionally
  use that language's adapter operators and concrete-tree patterns
  (tree-sitter queries or gob-pattern patterns). On other languages it is
  NotApplicable and appears once in the fidelity report.

Tier 2 has exactly one source language, GRL (owner decision: one way to
do a thing). GRL has two sublanguages that mix freely in one rule:

1. **Patterns** (single-language): a language-tagged code snippet with
   metavariables and ellipsis, refined by `inside`, `has`, `not`, `all`,
   `any` (the gob-pattern combinators of rules.md section 3), so the
   easiest rule starts by pasting the code it should match.
2. **Relations** (universal or single-language): a small,
   non-Turing-complete predicate language over U relations: select units,
   edges and attributes; join; bounded transitive closure; counts and
   thresholds; Kleene three-valued results. It is stratified Datalog in
   shape (universal-model.md 4.3) with no recursion beyond declared
   closures, so every plan terminates and runs in polynomial time.

Because there is no escape into a second form, GRL carries the burden of
being intuitive for someone who has never written a lint rule: it reads
like the code it matches, every construct has an example, embedded
fire/clean tests, and its own errors teach like rustc (diagnostics.md).
The full language, grammar, static checks, ten existing rules rewritten
as proof of expressiveness, and a five-minute newcomer walkthrough are
specified in grl-spec.md (ticket ~4QBTKCK, decision D80); the sketch
below predates it, and grl-spec.md section 12 has NEAT013 in the final
syntax.

```text
rule NEAT013 "ambient-source-call"
  lang * polarity P+ severity warn
  for u: unit(kind=function) where not attr(u, "frob:shell")
  find c: apply(head=resolves_to(v)) inside u
       where vocab(v, "clock" | "rng" | "env" | "fs" | "net" | "stdio" | "exit")
  report c "{u} calls {v}, an ambient source; inject it or mark the unit frob:shell"
```

Rules written in Rust today (`#[derive(Rule)]`) stay valid as tier-0 std
rules registered through the same Registry API. New std rules are
written in GRL whenever they can be, so the std library is mostly the
same source a third party can write, then compiled into the binary
(section 6.1).

## 5. Hooks: the plugin contract

Taken from pluggy: a small, typed, versioned set of hook specifications
is the entire ABI. Hooks are named-argument and grow only additively; a
breaking change is a new hook version, and a pack declares which
versions it implements. Implementations are validated at load time
(unknown hook, wrong signature, missing capability: PACK005 with the
exact reason).

| Hook | Called | Provided by |
|---|---|---|
| `atoms` | once per run | tier 1 |
| `detect(lang, unit) -> uses` | once per file, batched over its units | tier 1 (vocabulary detectors), tier 2, tier 3 |
| `templates` | once per run | tier 1 |
| `check_file(file) -> findings` | once per file | tier 2, tier 3 |
| `check_repo(graph) -> findings` | once per run (root packs only) | tier 2, tier 3 |
| `fix(finding) -> edits` | on request | tier 2 (fix templates), tier 3 |
| `adapter.fold(source) -> term` | once per file | tier 4 |
| `config_tables` | once at load | any (materialized knobs, no invisible variables) |

Ordering is explicit priority with a deterministic tie-break by pack name,
replacing pytest's tryfirst/trylast surprises. There is no wrapper hook
in version 1: findings are data, merged by the engine, so nothing needs
to wrap another pack's execution.

## 6. Performance: how parity is guaranteed and measured

1. **Built-ins are compiled in, and treated logically the same.** (Owner
   decision.) A std GRL rule is compiled ahead of time at build time
   (`cargo dev gen rules`): GRL to Rust code against the executor's
   operator library, so the hot path has no plan interpretation. A disk
   pack's GRL is compiled to plans on first load, cached outside the
   work tree under `$XDG_CACHE_HOME/grimble/plans/` keyed by the pack
   tree digest and the engine fingerprint, MAC'd (security.md 2.2), and
   run by the plan executor built
   from the same operator library. Speed differs; nothing else may.
   "Logically the same" is a list of obligations, each enforced:

   | Same | How it is enforced |
   |---|---|
   | source | every std rule has its GRL source in a std pack directory; the Rust is generated from it (GEN001 keeps it current), never hand-written |
   | registry entry | one Registry view; built-in and plugin rules both carry pack provenance (`std` or the pack name) and appear identically in `rules list` |
   | metadata | the same Rule metadata (id, slug, family, severity, polarity, must_measure, fixes, explain) from the same GRL declaration |
   | configuration | the same `[rules]` knobs, severities, exceptions and waivers; a built-in can be disabled exactly like a plugin |
   | lock and manifest | the std pack is listed in the pack lock with its digest like any other pack (frozen to the binary's version) |
   | diagnostics and explain | the same renderer, the same `explain` page generator |
   | semantics | the conformance test: every std GRL rule also runs as a plan on the std corpus and on the rule's embedded examples, and findings must be identical (byte-identical JSON) |
   | override | a plugin may replace a std rule only by declaring `replaces = "ID"`, which is recorded in the lock and reported; no silent shadowing |

   Hand-written tier-0 Rust rules (the current frob families) satisfy
   every row except "source"; each is recorded as a known exception in
   the std pack manifest, and moving one to GRL is a normal ticket.
   Plugin authors who need built-in-class speed compile their pack ahead
   of time to a WASM component (`grimble pack build`), which runs in the
   tier-3 host with the tier-2 semantics; the conformance test applies
   to it too.
2. **Prefilter by node kind.** Every plan carries the set of operator and
   node kinds it can match; the executor skips files and subtrees
   without them. This is the main reason host-executed declarative rules
   stay close to handwritten Rust.
3. **Batch the boundary for tier 3.** The host builds one flat arena per
   file (U term, scope graph, attributes, location table) and calls the
   component once per file. Measured wasmtime crossing cost is tens of
   nanoseconds; per-file batching makes it negligible, per-node would
   make it dominant.
4. **Compile once.** WASM components are compiled ahead of time with
   Cranelift on first use and cached by (component digest, engine
   version, target); instantiation uses wasmtime's pooling allocator.
5. **Budgets, loudly.** Every tier-3 call runs under epoch interruption
   (about 10 percent guest overhead, cheaper than fuel). A call that
   exceeds `[packs] file_budget_ms` is cancelled and its rules report
   Unresolved for that file with reason `budget`. A trap reports
   Unresolved with reason `trap`. Never silence.
6. **Benchmark gates in CI** (survey benchmarks B1-B4, filed as tickets):
   B1 plan executor versus handwritten Rust on three std rules (target:
   within 1.3x per file); B2 compiled-in GRL rule versus the same rule as
   a disk-loaded plan (target: plan within 1.3x after cache, findings
   identical); B3 tier-3 per-file call versus
   the same rule in tier 0 (target: within 1.5x); B4 WASM tree-sitter
   grammar versus native (target: measured and published per adapter,
   with native grammars compiled in for the std languages). `--timing`
   reports time per pack, so a slow plugin is visible by name.

## 7. Excuses and the capability matrix as pack content

The deny-by-default decision (D75) is unchanged and becomes pack data:

- Atoms, their detectors per language (with detector kind or impossible),
  and their vocabularies are tier-1 content of the pack that owns the
  atom family. The std pack `core-effects` owns `fs`, `net`, `env`,
  `clock`, `rng`, `stdio`, `exit`, `process`, `unsafe`.
- Matrix-build excuse templates (`excuse ATOM for SELECTOR because=`) are
  tier-1 content too, either in a pack (only for atoms that pack owns) or
  in the model's `template` entities. Their selectors run over U, so one
  template covers every language with an adapter.
- Detectors may be declarative (vocabulary lookups, tier 2 plans) or code
  (tier 3); the matrix computation in binding.md 7.2 consumes their
  answers identically and evaluates observed uses before any excuse, so
  CAP004 holds for plugin atoms exactly as for std atoms.
- Adding a language adds an adapter pack and detector rows; no template
  has to change.

## 8. Language adapters as packs

A tier-4 adapter pack contains: a grammar (native tree-sitter compiled
into the binary for the std languages; a WASM tree-sitter grammar for
third-party languages), `mapping.toml` (node kind to U operator, checked
against the grammar's `node-types.json` so an unmapped kind is a load
finding), `scopes.scm` (a locals-style description of the binding
discipline that builds the scope graph, with each reference kind marked
Must, May or Unknown), capability declarations with precisions, and a
fidelity corpus the loader runs once per version. Whatever the files
cannot express becomes `opaque` and reports Unresolved. The `.grmb`
adapter, Rust and markdown become std adapter packs.

## 9. Trust and effects of plugins themselves

Owner decision 2026-10-04: repository packs may run tier 3 (WASM) and
may be granted any effect; nothing is banned. The pessimistic audit
(notes/review/plugin-security-audit.md) tightened the first sketch; the
full model is security.md (D82). In short:

1. **Pure by default**, in a separate sandbox worker with no secrets;
   granted effects are performed by a host broker, never by the guest.
   Tier 1 and 2 content runs no code at all.
2. **Declared, exact and classed**: ordinary, secret-shaped, control
   plane and privilege effects (`replaces`, `fix.machine`, `subprocess`)
   are separate classes; read implies publish.
3. **Pinned to the pack tree digest**, which covers every byte of the
   pack (code, data, text, includes); any change drops trust and grants.
4. **Trusted from a protected branch, not from a prompt**: CI uses
   `--trust-from <protected ref>` only; developers run
   `trust --follow origin/main` once; the TTY-only prompt remains for
   code not yet on the protected branch. A repository can never raise
   its own privileges.
5. **An honest gate**: required packs make untrusted, budget and trap
   results fail; CI fails on new unknowns in changed files; GATE001
   reports any policy weakening between base and head.

## 10. Consequences

- Crate homes (consistency pass D85): the GRL lexer, parser, catalog
  checks, plan format, executor and codegen are all `gob-plan`; std
  rule sources live in `packs/std/<family>/*.grl` and the generated Rust
  in its own crate `gob-std` (a grimble node with no grants, so any
  ambient effect in generated code is CAP001, security.md 2.8); the
  `rule` verbs are a module of `gob-plan` that each product registers
  through gob-cli's verb registry; the sandbox worker is
  `gob-wasm::worker`; fix applicability lives in `gob-fix`
  (boundaries.md). The ten GRL rewrites of grl-spec.md 12 are acceptance
  fixtures registered in no registry while the Rust rules of those ids
  exist; moving a family to GRL replaces its Rust rules in the same
  ticket (PACK004 forbids two owners of one id).
- New crates: `gob-packs` (manifest, lock, loader, path-scoped activation, trust store, hook
  registry; product-neutral so frob and crunk use it), `gob-plan` (plan
  format, GRL compiler, pattern compiler, executor; the gob-ir evaluator
  becomes its backend), `gob-wasm` (wasmtime host, feature-gated, per-file
  arena, budgets, effects).
- gob-pattern (G17) becomes the pattern-rule compiler of tier 2 and is
  needed before most std rules move.
- The registry in gob-rules gains pack provenance per rule and merges
  inventory (std tier 0) and loaded packs into one view.
- Milestone 2 order changes (build-test-ci.md): gob-packs and gob-plan
  with the B1/B2 benchmarks come before architecture rules (G10), the
  capability matrix (G14) and NEAT; G10 and the first NEAT rules are
  written as tier-2 std rules; G14 consumes atoms and templates from
  packs; gob-wasm and tier 4 follow once tier 2 is proven.
- frob's own rules stay tier 0 for milestone 2 and may move to std packs
  later; the mechanism is product-neutral from the start.

## 11. Owner decisions and open questions

Decided 2026-10-04 (all four questions are now decided):

1. One rule language, GRL, for pattern and relational rules; no YAML
   form. GRL must be intuitive (grl-spec.md).
2. Built-in rules are compiled in for performance and treated logically
   the same as plugin rules (section 6.1). frob's families stay tier-0
   Rust in milestone 2, registered as recorded exceptions in the std pack.
3. Repository packs may run tier 3 with any granted effect under the
   trust model of section 9 (owner decision 2026-10-04), subject to the
   pessimistic security audit.
4. No directory-scoped packs; path-scoped activation from the root
   configuration instead (section 2, owner decision 2026-10-04).
