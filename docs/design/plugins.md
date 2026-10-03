# Plugins: one mechanism for the standard library and third parties

Status: DRAFT under T-0001, for owner review (proposed decision D76).
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

Directory-scoped packs, the conftest analogue: a repository pack may be
scoped to a subtree (`scope = "services/payments/**"`). Scoped packs may
only provide per-file hooks; a per-run hook in a scoped pack is a load
error (PACK009), which removes pytest's conftest ordering confusion for
repository-wide state.

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

Tier 2 has two source forms, both compiled to the same plan format:

1. **Pattern rules** (single-language): a tree-sitter query or a
   gob-pattern pattern with metavariables and `inside`, `has`, `not`,
   `all`, `any` combinators (rules.md section 3), plus a message and an
   optional fix template.
2. **Relational rules** (universal or single-language): GRL, a small,
   non-Turing-complete predicate language over U relations: select units,
   edges and attributes; join; bounded transitive closure; counts and
   thresholds; Kleene three-valued results. It is stratified Datalog in
   shape (universal-model.md 4.3) with no recursion beyond declared
   closures, so every plan terminates and runs in polynomial time.

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
written in tier 2 whenever they can be, so the std library is mostly
the same thing a third party can write.

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

1. **One plan format, one executor.** Std declarative rules are compiled
   to plan bytes at build time (`cargo dev gen plans`) and embedded; a
   disk pack's rules are compiled to the same bytes on first load and
   cached under `.grimble/cache/plans/<digest>`. The executor cannot tell
   them apart. Parity for tiers 1 and 2 is a property of the
   architecture, and a CI test asserts that the same rule run embedded
   and from disk gives identical findings and timing within noise.
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
   within 1.3x per file); B2 embedded versus disk-loaded plan (target:
   identical within noise after cache); B3 tier-3 per-file call versus
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

Plugins are deny by default for their own effects: a tier-3 component
gets no file system, network, environment, clock or process access unless
its manifest declares the effect and the lock grants it. Grants are
listed in `grimble check --json` and counted. Packs are pinned by content
digest; a signature check (sigstore) is a later option. Tier 1 and 2
content runs no code at all.

## 10. Consequences

- New crates: `gob-packs` (manifest, lock, loader, scoped packs, hook
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

## 11. Open questions for the owner

1. GRL syntax: the sketch above, or a Semgrep-like YAML form for pattern
   rules plus GRL only for relational rules?
2. Should frob's families (COV, DOC, TODO, and so on) become std packs in
   milestone 2, or stay tier 0 until the plan executor has proven B1?
3. Should repository packs be allowed tier 3 (WASM) at all in version 1,
   or only external packs with a signature?
4. Directory-scoped packs: keep them (the conftest idea) or defer to keep
   version 1 smaller?
