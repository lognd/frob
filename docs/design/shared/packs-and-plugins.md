# Packs and plugins: one extension mechanism, data packs and the drift-lock

Status: draft
Owner: gob
Decisions: D76, D68
Audience: contributor

Provenance: ACCEPTED with changes (D76, owner review 2026-10-04, ticket
~J8PJHKX). The changes: GRL is the one rule language (no second source
form), so it must be intuitive (grl-spec.md, ticket ~4QBTKCK); built-in
rules are compiled into the binary for speed and treated logically the
same as plugin rules (section 6.1).
Evidence: notes/research/plugins.md (wasmtime, dprint, swc, Zed, Typst,
Extism, oxlint, ruff, dylint, Semgrep, CodeQL, stack-graphs, tree-sitter
WASM grammars, pluggy and pytest measured locally). Depends on
universal-model.md (U, queries, evaluator, polarity), packs-and-plugins.md (pack
format, lock), grimble/grmb-spec.md (selectors, templates), grimble/binding.md (matrix),
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

Sources, in resolution order (docs/design/shared/packs-and-plugins.md section 12.3 is kept):

| Source | Where | Trust |
|---|---|---|
| std | compiled into the binary as precompiled plan bytes (`include_bytes!`) and inventory entries | the binary's own |
| repository | `packs/<name>/` in the repository | reviewed with the code |
| external | URL plus content digest, fetched by `grimble packs update` | pinned in the lock, optional signature |

Nothing activates by being installed. A pack is active only when listed
in `[packs] enabled` and pinned in `grimble.packs.lock` (packs-and-plugins.md 4). This
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

Implementation (repository packs, tiers 1 and 2): `gob_packs::loader::load_pack`
loads `packs/<name>/`. It reads the manifest and each content file once into memory,
interns the tier-1 atoms (provenance `repo:packs/<name>`), compiles the tier-2 GRL rules
(through the plan cache when given), computes the tree digest and verifies the pack against
the lock (PACK001 findings, `lock_verified`). The directory name must equal `pack.name`.
Tier 3 is refused until the trust store and sandbox land: the pack's wasm components come
back as `Unavailable` (PACK006, Unresolved `pack-unavailable`, with the reason), never
dropped silently. `inspect_pack` does the same without registering atoms, to build a lock
entry; nothing is registered unless every step succeeds.

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
   `any` (the gob-pattern combinators of docs/design/shared/rules.md section 3), so the
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
fire/clean tests, and its own errors teach like rustc (cli-contract.md).
The full language, grammar, static checks, ten existing rules rewritten
as proof of expressiveness, and a five-minute newcomer walkthrough are
specified in grl-spec.md (ticket ~4QBTKCK, decision D80); the sketch
below predates it, and docs/design/shared/grl-spec.md section 12 has NEAT013 in the final
syntax.

```text
rule NEAT013 "ambient-source-call"
  lang * polarity P+ severity warn
  for u: unit(kind=function) where not attr(u, "grimble:shell")
  find c: apply(head=resolves_to(v)) inside u
       where vocab(v, "clock" | "rng" | "env" | "fs" | "net" | "stdio" | "exit")
  report c "{u} calls {v}, an ambient source; inject it or mark the unit grimble:shell"
```

Rules written in Rust today (`#[derive(Rule)]`) stay valid as tier-0 std
rules registered through the same Registry API. New std rules are
written in GRL whenever they can be, so the std library is mostly the
same source a third party can write, then compiled into the binary
(section 6.1).

Tool id maps and default configurations are pack content: a vocabulary
pack carries the map from a linter's rule ids to frob ids and the default
`[[check.tool]]` configuration, so a third party can bind a new linter
without a frob release (docs/design/shared/rules.md section 1, bind before own).

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

Implemented in `gob_packs::hooks`: `Hook` is the closed list above, a pack
declares each implementation as hook name, version, signature and
priority (`Implementation`), and `Registry::register` refuses an unknown
hook, an unimplemented version, a signature that differs from the
specification (whitespace ignored) or a missing capability (`check_repo`
needs `graph`, `adapter.fold` needs `adapter`) as PACK005 stating the
reason. `Registry::ordered` sorts by priority then pack name;
`Registry::config_tables` lists materialized tables sorted.

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
   within 1.3x per file; the executor caches kind domains, reachability
   closures, operand values and unit lookups per run, indexes equality
   joins in quantifier bodies and matches comment text in place, which
   brought the per-file medians from 4.6x/25.8x/68.1x to about
   3.0x/4.2x/6.6x for TODO001/COV001/DOC002; the remaining gap is open
   work); B2 compiled-in GRL rule versus the same rule as
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
  (tier 3); the matrix computation in grimble/binding.md 7.2 consumes their
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
  (charter.md). The ten GRL rewrites of grl-spec.md 12 are acceptance
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
- Tool id maps and default tool configurations are pack content, not
  compiled in (section 4); the parsers stay in gob-check.
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

## 12. Data packs and the registry drift-lock

Merged from the former packs-and-plugins.md.
Status of this chapter: draft.

Provenance: DRAFT under T-0001 (a v1-format id that migrates with an alias);
written under ticket 01M3Z712SX9DEEAF4K8ER867TX (G04). It makes
docs/design/grimble/grmb-spec.md#20-the-model-and-the-substrate and section 12.9.6 precise: what a data pack is,
its file format, where packs live, how a repository pins them, how a
changed pack surfaces, how pack detectors become the cells of the
capability matrix, and what the three built-in packs of milestone 2
contain. Milestone 2 or later (D36): this whole file.

Inputs: docs/design/grimble/grmb-spec.md#20-the-model-and-the-substrate, 9.6, 9.7; grimble/grmb-spec.md (the `pack`
entity 4.6, MDL004, MDL016, open questions 1 and 11); grimble/binding.md
(source (c) in 2.3, the matrix view in section 12.7, the not-applicable
declaration 7.3); sibling-contract.md (compute digest 3.3, fidelity 3.4,
open question 1); universal-model.md 4.4 and 4.6 (capabilities, annotate
or be opaque, `callee_vocab` Q47); docs/design/grimble/rule-families.md section 3 (the
`[neat.effects]` vocabulary); docs/design/grimble/rule-families.md section 5 (the `[ci] registries`
vocabulary); the landed `crates/gob-ir/src/registry.rs` (`AtomEntry`,
`DetectorEntry`, `VocabEntry`); notes/v1/strata.md section 8 (the v1
registry drift-lock); docs/design/shared/architecture.md section 1.6 (config inventory, "no
invisible variables").

### 12.1 Purpose

#### 12.1.1 What a pack is

A data pack is a versioned, digest-pinned TOML document that teaches
grimble words, not grammar. (Consistency pass D85: in packs-and-plugins.md terms
this document is the tier-1 data file of a pack. A pack is a directory
with `pack.toml` (packs-and-plugins.md 2) that may hold data files like this one,
GRL rules and WASM components; the semantic item and pack digests of 2.5
are computed over its data items for drift reporting, and the tree
digest of security.md 2.1 over the whole directory for trust.) It may contribute:

- capability ATOMS (names, docs, default severities of the CAP rules);
- DETECTORS: how each atom is recognized in each language, or an
  explicit statement that it cannot be (`impossible`) or is not yet
  (`none`);
- CALLEE VOCABULARIES: named sets of callee names per language and
  class, the one mechanism shared with NEAT's `[neat.effects]` and the
  CI `[ci] registries` tables;
- INFERENCE RULES for binding source (c) (grimble/binding.md 2.3);
- CLAIM TEMPLATES (obligation shapes a claim can discharge);
- NODE KINDS and, if section 12.11 decides in favour, LATTICE EXTENSIONS.

#### 12.1.2 Packs versus the kernel

| Belongs in the kernel (crates, versioned with the binary) | Belongs in a pack (data) |
|---|---|
| the .grmb grammar, the keyword table, the eight entity kinds | an atom, a detector, a vocabulary name |
| the two builtin lattices, the answer lattice, the verdicts | extra trust elements or labels (11, Q1) |
| the CAP, SYS, MDL, PACK rule predicates and their polarity | the default severity a CAP rule has for one atom |
| the U operators, the 47 queries, the detector KINDS | which query, vocabulary or attribute a detector uses |
| the matrix cell algebra (docs/design/grimble/binding.md section 7) | which (language, atom) pairs are measured or impossible |
| the pack format, loader, lock and digest | everything inside one pack file |

Test for a feature: if adding it would change the lexer, the parser, the
keyword table, a rule's predicate or a U operator, it is kernel and goes
through a ticket and a release; if it adds rows to a table that an
existing predicate reads, it is pack data. Consequence stated once
(grmb-spec section 1): the editor grammar generated from the keyword
table and the parser never change when a pack is added.

#### 12.1.3 Packs are data, never code

A pack contains no executable content: no scripts, no regex callbacks, no
plugin entry points, no build steps. Two things look like code and are
not: the `pattern` detector's pattern text is interpreted by the
gob-pattern engine (a declarative ast-grep-shaped language, never a
general program), and the `query` detector names a query of the fixed
47-query interface (docs/design/shared/universal-model.md section 5) with literal
arguments. A pack that needs a new U query or a new detector kind is a
kernel change. This is what makes external packs safe to fetch by URL
(section 12.3.4): loading one cannot run anything.

### 12.2 Pack format

#### 12.2.1 The document

A pack is one UTF-8 TOML 1.0 file, ASCII only, with the grammar of 2.2
and the checks of 2.6. Unknown keys are PACK005 (the same
`deny_unknown_fields` stance as every grimble config table,
docs/design/shared/architecture.md section 1.6). Example (abridged; the built-in packs are
section 12.8):

```toml
format = 1                      # pack format major; this file defines 1

[pack]
name        = "core-effects"    # kebab-case; the registry prefix
version     = "1.0.0"           # exact semver, no ranges
description = "Process-level effects every language has: files, network, environment, time, randomness, stdio, exit, processes, unsafe."
licence     = "MIT"             # SPDX expression
[pack.provenance]
source  = "https://github.com/lognd/frob"   # where the maintainers publish it
authors = ["frob maintainers"]
basis   = ["CWE-73", "CWE-78", "CWE-367", "CWE-676"]   # catalogues the atoms answer

[[atom]]
name     = "fs.write"
doc      = "Creates, modifies, renames or removes files and directories."
args     = "path"               # what `may fs.write("...")` constrains
cwe      = ["CWE-73"]
severity = { CAP001 = "error", CAP002 = "warn" }

[[vocab]]
lang  = "rust"
class = "fs.write"
names = ["std::fs::write", "std::fs::remove_file", "tokio::fs::write"]

[[detector]]
atom      = "fs.write"
lang      = "rust"
kind      = "callee"            # callee vocabulary; the class defaults to the atom name
precision = "typed"
rationale = "A direct call to a filesystem mutator in the standard library."
```

#### 12.2.2 Grammar

EBNF over TOML tables. `[x]` optional, `{x}` repeated, `|` alternative.
Every table is closed (no keys beyond those listed).

```
pack_file   = "format" "=" INT
              pack_table { atom } { vocab } { detector } { template }
              { infer } { claim } { node_kind } [ lattice ] ;

pack_table  = "[pack]" name version description licence [ provenance ] ;
name        = "name" "=" KEBAB ;                 (* [a-z][a-z0-9-]*, max 40 *)
version     = "version" "=" SEMVER ;             (* X.Y.Z, optional -pre, no ranges *)
licence     = "licence" "=" SPDX ;
provenance  = "[pack.provenance]" [ "source" "=" URL ] [ "authors" "=" LIST ]
              [ "reviewed" "=" DATE ] [ "basis" "=" LIST ] ;

atom        = "[[atom]]" "name" "=" ATOMNAME "doc" "=" STRING
              [ "aliases" "=" LIST_OF_ATOMNAME ]
              [ "args" "=" ( "none" | "path" | "host" | "name" | "string" ) ]
              [ "cwe" "=" LIST ] [ "severity" "=" SEVTABLE ] ;
ATOMNAME    = IDENT { "." IDENT } ;              (* snake_case segments *)
SEVTABLE    = "{" [ "CAP001" "=" SEV ] [ "," "CAP002" "=" SEV ] "}" ;
                                                 (* CAP003 retired (D75); CAP004 is a fixed Error *)
SEV         = "error" | "warn" | "advisory" | "off" ;

vocab       = "[[vocab]]" "lang" "=" LANG "class" "=" ATOMNAME
              "names" "=" LIST_OF_VOCABNAME [ "precision" "=" PREC ] ;
VOCABNAME   = [ "uses:" | "run:" ] PATHLIKE [ "[" FILTER { "," FILTER } "]" ] ;
FILTER      = ARG ( "=" | "~=" ) LITERAL ;       (* literal argument or `with:` input; ~= is a regex on a literal *)
PREC        = "typed" | "lexical" ;

detector    = "[[detector]]" ( "atom" "=" ATOMNAME | "atoms" "=" ( LIST_OF_ATOMNAME | "*" ) )
              ( "lang" "=" LANG | "langs" "=" LIST_OF_LANG )
              "kind" "=" KIND  kind_fields
              [ "precision" "=" PREC ] [ "cwe" "=" LIST ] [ "rationale" "=" STRING ]
              [ "safer_alternative" "=" STRING ] [ "severity" "=" SEV ]
              [ "min_fidelity" "=" ( "F1" | "F2" | "F3" | "F4" ) ]
              [ "needs" "=" LIST_OF_NEED ] ;     (* NEED = "manifest" | "types" | "scope" *)
KIND        = "query" | "callee" | "attribute" | "pattern" | "none" | "impossible" ;
kind_fields = (* query *)     "q" "=" QID [ "args" "=" TABLE ]
            | (* callee *)    [ "vocab" "=" ATOMNAME ]        (* default: the atom's own class *)
            | (* attribute *) "names" "=" LIST
            | (* pattern *)   "engine" "=" ( "gpol" | "ast-grep" ) "pattern" "=" STRING
                              [ "in" "=" ( "source" | "macro" ) ]
            | (* none *)      "reason" "=" STRING
            | (* impossible *) "reason" "=" STRING ;      (* reason is mandatory *)
QID         = "Q" DIGIT DIGIT ;                  (* a query of universal-model.md section 5 *)

template    = "[[template]]" "name" "=" IDENT "atom" "=" ATOMNAME
              "for" "=" SELECTOR_TEXT "reason" "=" STRING ;
                                                 (* a matrix-build excuse, 6.7; the selector is grmb-spec 6.1 text *)

infer       = "[[infer]]" "id" "=" IDENT "applies" "=" TABLE "role" "=" ROLE
              "from" "=" TABLE "status" "=" "may" "reason" "=" STRING ;

claim       = "[[claim]]" "id" "=" IDENT "when" "=" TABLE "obligation" "=" STRING
              "rung" "=" RUNG [ "severity" "=" SEV ] ;

node_kind   = "[[node_kind]]" "name" "=" IDENT "doc" "=" STRING [ "attrs" "=" TABLE ] ;

lattice     = "[lattice.trust]" insert_list | "[lattice.label]" insert_list ;   (* 11, Q1 *)
insert_list = "insert" "=" "[" { "{" "name" "=" IDENT "," "above" "=" IDENT
                                  "," "below" "=" IDENT "}" } "]" ;
```

Notes on the grammar:

- Names. Atom names, aliases, infer ids, claim ids and node kinds are
  `ident` segments of grmb-spec 2.7 (snake_case, no hyphen) so they can
  be written in a .grmb file; the PACK name is kebab-case and a model
  addresses it through the `pack` entity's local NAME (hyphen becomes
  underscore by default: `core-effects` is `core_effects`). An atom is
  registered as `core-effects::fs.write`; in a model it is written
  `fs.write` or `core_effects::fs.write`. Because duplicate atom names
  are an error (3.5), the unqualified form is never ambiguous.
- Hierarchy. `fs.write` has parent `fs`; a parent must exist in the same
  pack or an enabled pack (PACK005 otherwise). A parent atom normally
  has no detector of its own: its cell is the join of its children's
  (6.3). `aliases` are extra spellings in the same namespace; `exec` is
  an alias of `process.spawn` in `core-effects` so that grmb-spec's
  `may exec` keeps working.
- `args` types the parenthesized constraint of `may ATOM(ARGS)`
  (grmb-spec 4.1). A grant with arguments of the wrong type is MDL008.
  The loader keeps each atom's kind in the pin (`PackPin::arg_kinds`): `path`
  and `host` validate and judge like the built-in `fs` and `net` atoms, `name`
  is one token without whitespace and `string` any string, both compared
  exactly. An atom with no `args` (or `none`) takes no arguments, so a grant
  argument on it is MDL008; any other `args` value makes the pack file
  malformed (MDL004). CAP001 judges a call site's folded argument against the
  grant arguments with the same kind (ticket 01M61Y35AKW4QDRE70W6HFQAJ5).
- Detector rows are the registry row of grimble/binding.md 7.5:
  `{atom, language, detector_kind, pattern_or_vocab_ref, precision, cwe,
  rationale, safer_alternative, severity}`; `kind` is `detector_kind`,
  the kind-specific key is `pattern_or_vocab_ref`, `lang` is `language`.
  `atoms = "*"` expands to every LEAF atom of this pack; `langs` expands
  to one row per language. Row counts in section 12.8 are DECLARATIONS
  (before expansion) with the expanded cell count beside them.
- Vocabulary names. A name is a resolved callee path (`std::fs::write`);
  a trailing `*` globs one path segment tail; a trailing `!` names a
  macro call (`println!`). A name may also denote a global member read
  (`process.env`). A `[arg=literal]` filter narrows by a literal argument
  (Python `open[mode~=[wax+]]`) or, in the Actions language, by a
  `with:` input (`docker/build-push-action[push=true]`). If the argument
  is not a literal the filter answers May, never No. Prefix `uses:` names
  an action reference and prefix `run:` a command-line prefix inside an
  opaque `run:` payload (a Lexical match, universal-model.md 2.2).
  Precision defaults to `typed` when the callee resolves through the
  scope graph (Q20), else the match is `lexical` and is reported with
  that precision in the matrix.
- Detector kinds, their meaning and their landed counterpart in
  `gob_ir::registry::DetectorKind`:

| Pack `kind` | What runs | Needs | `DetectorKind` |
|---|---|---|---|
| `query` | the named query Q-id over U with literal args (Q08 attributes, Q12 imports, Q19 keys, Q13 name uses and call sites) | the adapter's fidelity for that query | new variant `Query` (an additive change; today `Import` and `Lexical` are folded into it and `precision`) |
| `callee` | Q13 call sites resolved by Q20, matched against the vocabulary class (Q47 `callee_vocab(lang, class)`) | F2 for typed, F1 for lexical | `Callee` |
| `attribute` | Q08 attributes or decorators of a unit named in `names` | F2 | `Attribute` |
| `pattern` | gob-pattern (ticket G17, blocked by the `Doc`-over-U spike): `gpol` is the declarative pattern language of the GPOL family, `ast-grep` the grammar-level shape; `in = "macro"` selects the macro phase | the engine being built | `Pattern` (and `Macro` for `in = "macro"`) |
| `none` | nothing; the pack records that the gap is known | nothing | no row (the answer is Unknown) |
| `impossible` | nothing; the capability cannot exist in this language | nothing | `NotApplicable` |

  A `none` row exists so that a missing detector is a visible line of
  the pack and not an omission; it has exactly the effect of no row and
  PACK003 does not fire for it (nothing is unavailable, nothing was
  declared available).
- Matrix-build templates (`[[template]]`, D75) are excuses: "atom A does
  not apply to the units this selector picks, because REASON" (6.7).
  They are the pack-side twin of the `template` entity of grmb-spec 4.7;
  both feed one effective template set. A template can never hide an
  observed use (CAP004, grimble/binding.md 7.2).
- Claim templates (`[[claim]]`) generate the obligation shape of v1's
  threat packs: "when a node holds atom A at scope S, a claim of rung R
  discharging OBLIGATION must exist". They carry no grammar. The three
  built-in packs of milestone 2 ship none; the `threat` and
  `reliability` packs of docs/design/grimble/grmb-spec.md#20-the-model-and-the-substrate are later packs.
- `[[node_kind]]` adds kinds a node may declare with `kind IDENT;`
  (grmb-spec 4.1). A kind that collides with a core kind or another
  pack's kind is PACK004.

#### 12.2.3 Inference rules

An `[[infer]]` row is the grimble/binding.md 2.3 rule, with the id grammar fixed
to `ident` so it can be requested as `attr infer = pack::rule_id;`
(grimble/binding.md writes `cargo.crate-owns-dir` there as an illustration; this
file's `crate_owns_dir` is the rule). `applies` names the entity kind and
the attribute an entity must carry; `role` is the binding role; `from`
names the adapter and the fact; `status` is always `"may"` (a pack can
never write a Must row, and PACK005 refuses any other value). A rule is
inert until an entity asks for it; there is no ambient inference
(grimble/binding.md 2.3 item 1). Provenance of every inferred row names the
pack, its LOCKED version and the rule id, so a pack update is visible in
`grimble explain` exactly where inferred rows change.

#### 12.2.4 JSON Schema outline

`docs/schemas/pack.json` is generated from the `PackFile` serde type
(`cargo dev gen schemas`, D50) and `grimble packs lint` validates a file
against it before the semantic checks of 2.6. The outline fixes the
shape (Draft 2020-12, every object `additionalProperties: false`, the
document `$id` `https://frob.dev/schemas/pack/1`):

```json
{
  "type": "object",
  "required": ["format", "pack"],
  "properties": {
    "format":  { "const": 1 },
    "pack":    { "$ref": "#/$defs/pack" },
    "atom":    { "type": "array", "items": { "$ref": "#/$defs/atom" } },
    "vocab":   { "type": "array", "items": { "$ref": "#/$defs/vocab" } },
    "detector":{ "type": "array", "items": { "$ref": "#/$defs/detector" } },
    "infer":   { "type": "array", "items": { "$ref": "#/$defs/infer" } },
    "claim":   { "type": "array", "items": { "$ref": "#/$defs/claim" } },
    "node_kind":{ "type": "array", "items": { "$ref": "#/$defs/node_kind" } },
    "lattice": { "$ref": "#/$defs/lattice" }
  },
  "$defs": {
    "pack":   { "required": ["name", "version", "description", "licence"],
                "properties": { "name": { "pattern": "^[a-z][a-z0-9-]{0,39}$" },
                                "version": { "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9A-Za-z.-]+)?$" } } },
    "atom":   { "required": ["name", "doc"],
                "properties": { "name": { "pattern": "^[a-z_][a-z0-9_]*(\\.[a-z_][a-z0-9_]*)*$" },
                                "severity": { "$ref": "#/$defs/severities" } } },
    "detector": { "required": ["kind"],
                  "oneOf": [ { "properties": { "kind": { "const": "query" } },      "required": ["q"] },
                             { "properties": { "kind": { "const": "callee" } } },
                             { "properties": { "kind": { "const": "attribute" } },  "required": ["names"] },
                             { "properties": { "kind": { "const": "pattern" } },    "required": ["engine", "pattern"] },
                             { "properties": { "kind": { "const": "none" } },       "required": ["reason"] },
                             { "properties": { "kind": { "const": "impossible" } }, "required": ["reason"] } ] },
    "severities": { "properties": { "CAP001": { "$ref": "#/$defs/sev" },
                                    "CAP002": { "$ref": "#/$defs/sev" } } },
    "sev":    { "enum": ["error", "warn", "advisory", "off"] }
  }
}
```

The schema checks shape only; the relational checks (parents exist, a
vocabulary class referenced by a `callee` detector exists, a Q-id exists
in docs/design/shared/universal-model.md section 5, no `impossible` beside a real detector
for one `(atom, lang)`) are semantic and produce PACK005 (2.6).

#### 12.2.5 The canonical form and the digest

Two digests are defined over a parsed pack, never over the file bytes, so
reformatting, reordering tables and editing comments never re-lock:

- The ITEM digest of an item is `blake3` of the canonical JSON (keys
  sorted bytewise, no insignificant whitespace, integers decimal, no
  floats, the same canonicalization as `compute_digest` in
  sibling-contract.md 3.3) of the item with its documentary text removed
  (`doc`, `description`, `rationale`, `safer_alternative`, `reason` of
  `none` rows; the `reason` of an `impossible` row is KEPT because it
  justifies a matrix cell). An item is identified by a KEY: `atom:NAME`,
  `detector:ATOM/LANG/KIND` (with a `#n` suffix to separate two rows of
  the same triple), `vocab:LANG/CLASS`, `infer:ID`, `claim:ID`,
  `kind:NAME`, `lattice:trust/NAME`, `lattice:label/NAME`.
  Vocabulary `names` are a set (sorted, duplicates removed).
- The PACK digest is `blake3:` plus the hex blake3 of the canonical JSON
  of `{format, name, version, licence, items}` where `items` is the
  object of all item keys to item digests. `provenance` and
  `description` are excluded (they cannot change a finding).

Documentary text is excluded because it only changes messages, not
findings; a documentation-only edit therefore needs a version bump by
convention but not a re-lock. These two digests feed PACK001 drift
reporting only. Trust, grants and cache keys bind to a third digest,
the TREE digest over every byte of the pack including its text
(security.md 2.1, D82), so a text-only change needs trust again even
though it does not re-lock. `grimble packs show NAME --digest` prints
both digest levels.

#### 12.2.6 Semantic checks (PACK005)

At load, in this order; each failure is one PACK005 finding naming the
file, the table and the key: the schema; `format` is a major this
binary reads; every atom's parent exists; every `callee` detector's
class exists as a vocabulary for that language (or in another enabled
pack); every `query` Q-id exists and its `args` match the query's
parameter names; every `attribute` detector lists at least one name;
`impossible` and `none` carry a `reason`; a `(atom, lang)` has either
`impossible` or real detectors, never both; every `[[infer]]`
has `status = "may"`; every `severity` is in the enum (a `CAP003` key is retired and is a schema failure); every `[[template]]` has a non-empty `reason`, a `for` selector that parses (grmb-spec 6.1) and an `atom` of THIS pack (a template excusing another pack's atom is PACK005, as for `impossible`); `atoms = "*"`
matches at least one leaf atom; no two items in the file share a key.

### 12.3 Where packs live

#### 12.3.1 The three sources

| Source | Pack id | Where | Loaded as | Pinned by |
|---|---|---|---|---|
| built-in | `grimble/NAME` | `crates/gob-ir/packs/NAME.toml`, compiled into the binary | link-time inventory entries (3.2) | the binary version, and the lock |
| repository | `local/NAME` | `packs/NAME.toml` under the repository root | read at run time | the lock |
| external | `ext/NAME` | an `https` URL | fetched once by `grimble packs fetch`, stored at `packs/vendor/NAME-VERSION.toml`, then read as a repository pack | URL plus digest in `grimble.toml`, and the lock |

The pack's `name` must equal the NAME of its id; the `grimble/`
namespace is reserved for built-ins. The `pack` entity of a model
(grmb-spec 4.6) refers to a pack by id: `pack core_effects { ref
"grimble/core-effects"; version "1.0.0"; digest "blake3:..."; }`.

#### 12.3.2 Built-in packs are inventory entries in gob-ir

The shared crate of grimble/binding.md 7.5 is `gob-ir` (the landed
`registry.rs`). A built-in pack is the same TOML file as any other,
embedded at build time by a declarative macro, `gob_ir::builtin_pack!
("packs/core-effects.toml")`, whose expansion is a set of
`inventory::submit!` items: one `PackEntry { id, name, version, digest,
source: &str }` (the verbatim file, for `grimble packs show` and for
digests) plus the `AtomEntry`, `DetectorEntry` and `VocabEntry` rows
parsed at macro-expansion time, so there is no run-time parse of
built-ins and a malformed built-in pack fails the build (PACK005 at
compile time). Link-time inventory is why a built-in pack can extend the
registry without a closed Rust enum; a repository or external pack
cannot be linked, so it is loaded at run time into an `EffectiveRegistry`
value that merges the inventory entries of ENABLED built-in packs with
the loaded packs and answers the same questions (`atoms()`, `atom(n)`,
`detectors(atom, lang)`, `callee_vocab(lang, class)`) as the landed free
functions, which keep answering for built-ins alone (no behaviour
change for milestone 1 code).

Required additive changes to the landed types, for the implementation
ticket (G14) and not made here: `AtomEntry` gains `pack`, `doc`,
`severity` and `aliases`; `DetectorEntry` gains `precision`, `reason`,
`rationale`, `cwe`, `safer_alternative`, `severity`, `min_fidelity` and
a reference to a vocabulary class or query; `VocabEntry` gains `pack`
and `precision`; `DetectorKind` gains `Query`. The two seed atoms in
`registry.rs` (`net.connect` and `fs.write` and the `net` vocabularies)
are removed when `core-effects` lands because that pack supersedes them;
the seed vocabulary class `net` is split into `net.connect` and
`net.listen` (8.1).

#### 12.3.3 Repository packs

A repository pack is a file of the format of section 12.2 under `packs/`
(never in a subdirectory except `packs/vendor/`). It is enabled the same
way as a built-in, by an entry in `[packs] enabled` of `grimble.toml`
(3.6). A file under `packs/` that is not enabled is ignored and `grimble
doctor` lists it (it is not a finding: a staged pack is legitimate).

#### 12.3.4 External packs

An external pack is declared in `grimble.toml`:

```toml
[[packs.external]]
id     = "ext/acme-db"
url    = "https://packs.example.org/acme-db/1.2.0/acme-db.toml"
digest = "blake3:..."          # the PACK digest of 2.5, mandatory
```

`grimble packs fetch` (the only verb that touches the network for packs;
it goes through gob-exec's bounded fetch, architecture.md) downloads the file,
refuses it unless its pack digest equals the declared one, and vendors
it under `packs/vendor/`. `grimble check` never fetches: it reads the
vendored file, so a check is reproducible offline and a changed remote
file cannot alter a run. A declared external pack that is not vendored
is PACK006 (Unresolved, required) and the rest of the registry still
loads. The digest in `grimble.toml` is the author's expectation; the
digest in the lock is what was accepted; they must agree (PACK001
otherwise). Because a pack is data (1.3), fetching is the whole trust
decision: the digest is the supply-chain pin, not a signature, and a pack
author's identity is the URL and `provenance.source` only.

#### 12.3.5 Resolution and conflicts

Enabled packs are loaded in the order of `[packs] enabled`, then
`[[packs.external]]`; order never decides a conflict (there is no
shadowing) because every conflict is an error:

| Conflict | Result |
|---|---|
| two enabled packs with the same `name` | PACK004 naming both ids |
| the same atom name or alias in two packs, or an alias equal to another atom | PACK004 naming both packs and both atoms |
| the same node kind, infer id or claim id in two packs | PACK004 naming both |
| the same lattice gap (`above`, `below` pair) extended by two packs | PACK004 naming both |
| `impossible` in one pack and a real detector in another for one `(atom, lang)` | PACK004 naming both packs and the cell |
| vocabulary classes for one `(lang, class)` in two packs | NOT a conflict: the name sets are unioned (the point of one vocabulary mechanism); PACK001 and `grimble packs show --vocab` show provenance per name |

Two packs that supply different DETECTOR KINDS for one `(atom, lang)`
are not a conflict either: the cell is the join of the answers (6.2).
Layering above packs is the repository's own decision and always wins
(3.6, 5).

#### 12.3.6 What grimble.toml holds

`grimble.toml` is the repository's side (docs/design/shared/architecture.md section 1.6); the
lock (4) is the pack's side. The tables, all with
`deny_unknown_fields`, materialized by `grimble init` (the knob
inventory rows to add to docs/design/shared/architecture.md section 1.6 are in section 12.12):

```toml
[packs]
enabled = ["grimble/core-effects", "grimble/ci-github", "grimble/rust-ecosystem"]
lock    = "grimble.packs.lock"          # default; one lock per repository

[[packs.external]]                      # as in 3.4

[packs.severity]                        # repository override, wins over the pack
"unsafe"     = { CAP001 = "error" }
"stdio.write" = { CAP001 = "warn" }

[neat.effects.rust]                     # repository vocabulary layer (grimble/rule-families.md 3)
"fs.write" = ["tempfile::NamedTempFile::persist"]
[neat.effects.exclude.rust]             # a false positive removed, with a reason
"fs.read"  = { names = ["std::fs::metadata"], because = "stat only, no content read" }

[ci]
registries = ["uses:my-org/internal-publish"]   # repository layer of vocab class ci.publish
```

Severity precedence, strongest first: `[packs.severity]` for the atom,
then `[rules.CAP001] severity` for the rule (rules.md), then the pack's
per-atom default, then the rule's own default. Implemented for CAP001
(ticket K4EMP90): `gob_ir::registry::atom_row` returns an atom's row
(precision, cwe, rationale, safer alternative, per-rule severity), the
`[packs.severity]` table reaches the binder through
`ModelFiles.pack_severity`, a `warn` level reports a denied use as an
Unresolved finding (Severity has no Warn, rules.md 6.1.1), and the CAP001
message ends with the row's `[why: ..; safer: ..]` when it has them; the
`[rules.CAP001]` layer is not yet consulted. The repository layer of a
vocabulary (`[neat.effects.<lang>]`, `[ci] registries`) is the
`local/repo` layer, unioned with the pack names and minus the `exclude`
entries; `[neat.effects]` and `[ci] registries` are therefore views over
the registry exactly as grimble/binding.md 7.5 and docs/design/grimble/rule-families.md section 3
say: one mechanism, three spellings. A repository override that equals
the effective pack value is PACK008.

Per-atom severity `warn` is emitted as Unresolved, not as a warning: the
finding model has only Error and Unresolved (rules.md 6.1.1), so a `warn`
level, from `[packs.severity]` or from the atom row, reports the denied use
as an Unresolved finding (reason `may-only-owner`). Any other level string
is logged and treated as Error. The full CAP001 resolution order is in
docs/design/grimble/binding.md (paragraph "CAP001 severity resolution").

### 12.4 The drift-lock

#### 12.4.1 What it replaces

v1's registry drift-lock (notes/v1/strata.md section 8) kept a
denominator and a disposition per enumerated concept and cross-checked
the dispositions against live rules, so that "we surveyed it" could not
diverge from "we enforce it". Its descendant for rules is the generated
rule registry (docs/design/grimble/grmb-spec.md#20-the-model-and-the-substrate). This section is a different
lock with a similar job for DATA: `grimble.packs.lock` pins every pack a
repository uses so that "the registry says X about `fs.write` in Rust"
cannot change under a repository without a reviewable diff. v1's lesson
kept: never auto-widen; the tool reports drift, a human accepts it.

#### 12.4.2 The file

`grimble.packs.lock` is a TOML file at the repository root, written only
by `grimble packs lock` and `grimble packs update`, and read by every
verb. It is never edited by hand (PACK001 catches a hand edit that
disagrees with the packs).

```toml
# grimble.packs.lock -- written by `grimble packs lock`; do not edit
lock_version  = 1
digest_scheme = 1                       # the item and pack digest scheme of 2.5

[[pack]]
name    = "core-effects"
id      = "grimble/core-effects"
version = "1.0.0"
source  = "builtin"                     # builtin | local | external
digest  = "blake3:6f1c...e90a"          # the PACK digest
[pack.items]                            # key -> ITEM digest, sorted by key
"atom:fs.read"                = "blake3:11aa..."
"atom:fs.write"               = "blake3:5be2..."
"detector:fs.write/rust/callee" = "blake3:9d40..."
"vocab:rust/fs.write"         = "blake3:c3f7..."
# ...
[pack.vocab_count]                      # names per vocabulary, for human diffs
"rust/fs.write" = 11
[pack.severity]                         # the pack-derived defaults, MATERIALIZED (5)
"fs.write" = { CAP001 = "error", CAP002 = "warn" }
```

There is one `[[pack]]` per enabled pack, sorted by name. The lock is
small: the three built-in packs of section 12.8 have 146, 102 and 43 items
(8.4), one line each.

Implementation: `gob_packs::lock` (crate `gob-packs`) reads, writes and
verifies the lock. `verify` returns typed PACK001 findings (`LockMissing`,
`LockStale`, `Scheme`, `Version`, `Effects`, per-item `Item`) and, when only
the tree digest differs (a documentation-only edit), exactly one `TreeOnly`.
The file name is a parameter of `read` and `write`.

#### 12.4.3 What changes require re-locking

| Change | Re-lock? | Surfaces as |
|---|---|---|
| a pack is enabled or disabled in `[packs] enabled` | yes | PACK001 `lock-missing` (enabled, not locked) or `lock-stale` (locked, no longer enabled) |
| a pack's version changes (a new binary carries a newer built-in, a repository file edited, an external URL changed) | yes | PACK001 per changed item, plus one pack-level finding for version and metadata |
| a pack's content changes at the same version | yes | PACK001 per changed item with detail `content changed without a version bump` |
| an item is added, removed or its item digest changes | yes | one PACK001 per item: `added`, `removed`, `changed` |
| an external pack's declared `digest` or `url` changes | yes | PACK001 on the pack |
| `digest_scheme` or `lock_version` of this binary differs from the lock's | yes, all packs | one PACK001 `scheme` with the reason, never a silent rewrite (grimble/binding.md 14.1 does the same for `grimble.lock`) |
| documentation text, comments, order of tables, whitespace | no | nothing |
| `provenance`, `description` | no | nothing |
| a repository override (`[packs.severity]`, `[neat.effects]`, `[ci] registries`) | no: it is the repository's own, already in git | nothing (PACK008 if redundant) |
| a pack is added to the model's `pack` entities without being locked | yes | MDL004 (grmb-spec) and PACK001 `lock-missing` |

#### 12.4.4 How a changed pack surfaces

`grimble check` loads every enabled pack, computes item and pack digests
and compares them to the lock. The comparison is item-wise, so the
result is one finding per changed thing and never one per pack and never
silent:

- PACK001 `changed|added|removed` is emitted ONCE PER ITEM, anchored to
  the pack file (or, for a built-in, to `grimble.packs.lock` at the
  pack's table), with the key, the old and new item digest and, for a
  vocabulary, the old and new name count. A whole-pack version bump with
  40 changed atoms and detectors is 40 findings plus one pack-level
  finding; that is deliberate: a review of an update is a review of the
  list.
- Name-level detail for a vocabulary is not in the lock (it would
  multiply the lock by the vocabulary size). `grimble packs diff NAME
  [--from-git REV]` prints it for repository and external packs by
  reading the old file from git; for a built-in the changelog fragment
  of the release lists the changed names (notes/research/documentation.md section 5).
- A finding is evaluated by equality of recorded and computed digests,
  so its polarity is P0 (universal-model.md 4.2). Where the pack's
  bytes cannot be read at all the comparison cannot run: PACK006
  Unresolved `pack-unavailable`, required, and no PACK001 item findings
  for that pack (an unreadable pack is not "unchanged").
- Findings produced by new content downstream of an update are ordinary
  findings (a new detector can create CAP001 at a use it never saw
  before). They are not special-cased; the repository absorbs them with
  the normal ratchet pool (rules.md) or a model change. The
  grace period that the pre-D75 design gave CAP003 after a new atom
  shipped is gone with CAP003 (capabilities are denied by default, so a
  new atom's first observed use is CAP001 at its pack severity). A pack
  author who wants a softer landing ships the new atom with a lower
  `CAP001` in its `severity` and a later pack version raises it, so the
  window is itself a visible, locked pack change (and its
  `[pack.severity]` line in the lock).

The whole point is that a finding set never changes without a
diff: either the repository's inputs changed (grimble.toml, the model,
the code, the lock) or PACK001 says a pack did.

#### 12.4.5 The verbs

| Verb | Writes | Meaning |
|---|---|---|
| `grimble packs list` | no | enabled packs, source, locked version, current version, state (`ok`, `drift`, `unlocked`, `unavailable`) |
| `grimble packs show NAME [--digest] [--vocab]` | no | the parsed pack, its digests, vocabulary provenance per name |
| `grimble packs lint FILE` | no | schema and PACK005 checks of one file (for authors) |
| `grimble packs fetch` | `packs/vendor/` | fetch and vendor declared external packs (3.4); needs the network |
| `grimble packs lock` | the lock | create the lock for a repository that has none; refuses when a lock exists (use `update`) |
| `grimble packs verify` | no | exactly the PACK001 evaluation of `check`, as a verb; exit 1 on any drift (cli-contract.md exit table) |
| `grimble packs diff NAME [--from-git REV]` | no | item-wise and name-wise difference between the locked and the current pack |
| `grimble packs update [NAME...] [--dry-run] [--write-model]` | the lock, with `--write-model` also the model pins | accept the current pack content as the new lock for the named packs (default: every drifted pack) |
| `grimble packs outdated` | no | for built-ins, packs whose compiled version is newer than the lock; for external, the declared URL against the vendored version |

`grimble check`, `status`, `fmt`, `doctor` and every other verb are
read-only for the lock and the packs.

#### 12.4.6 Why updates are explicit (grmb-spec open question 11)

`grimble packs update` is the only writer of the lock and it is never
implied by another verb, and it never runs by itself. Reasons, in order
of weight:

1. A pack change changes findings. A new detector can turn a clean
   repository red, a removed vocabulary name can turn a red one green
   (a P+ rule losing coverage is a silent improvement of a score; a
   P- one is the opposite). Anything that moves findings without a
   repository diff is an invisible variable (D22).
2. "Never auto-widen" is the v1 lesson that shaped the whole design
   (docs/design/grimble/grmb-spec.md#20-the-model-and-the-substrate): neither the model nor its grants are
   regenerated to match the code, and neither is the pin regenerated to
   match the pack.
3. A security fix in a pack (a new detector for a newly discovered
   dangerous API) is exactly when a repository wants the update and the
   resulting findings in ONE reviewable commit; explicit update makes
   that commit the unit of review, with the PACK001 list as its
   description.
4. Reproducibility: two checkouts of one commit must agree on findings
   (sibling contract determinism); the lock plus the vendored packs plus
   the binary version are all of the pack inputs, and the binary's
   built-in pack set is itself recorded by the lock, so upgrading the
   binary alone cannot change findings silently either.

The decision for the open question: a `pack` entity's pin stays exact
and `grimble packs update` MAY rewrite it, but only under the explicit
flag `--write-model`, which edits exactly the `version` and `digest`
clauses of the named `pack` entities through the `grimble fmt` printer
(a span-precise edit of two clauses, never any other text) and prints
the resulting diff. Without the flag the verb rewrites only the lock and
prints the model edit it would make (`MDL004` stays open until a human
applies it). The edit is shrink-neutral (grants and template excuses are
never touched), it is a visible commit, and it is never run by a hook or by
`check`. This resolves the question in favour of a bounded, opt-in
rewrite rather than refusing to edit the model: an update that required
hand-editing digests in a .grmb file would be error-prone, and the flag
keeps the "grimble never edits a model on its own" rule literally true.

### 12.5 Materialization

The rule (D22, docs/design/shared/architecture.md section 1.6): nothing that changes findings
is invisible. For packs this is made concrete as a table of every
pack-derived default that can change a finding and the file in which a
reader finds its effective value in git:

| Pack-derived default | Written to | By | Changing it is |
|---|---|---|---|
| which packs are on | `grimble.toml` `[packs] enabled` | `grimble init` | a repository edit |
| which pack content is in force | `grimble.packs.lock` `[[pack]]` digests and items | `packs lock` and `update` | a lock edit, PACK001 until done |
| per-atom default severity of CAP001, CAP002 | the lock, `[pack.severity]` (the resolved pair per atom, after the pack's own defaults and before the repository override) | `packs lock` and `update` | a lock edit, PACK001 for the atom item |
| repository severity overrides | `grimble.toml` `[packs.severity]` | by hand or `grimble init --materialize` | a repository edit |
| vocabulary names and their classes | the pack (digest in the lock) plus the repository layer `[neat.effects]`, `[ci] registries` | pack author, repository | PACK001, or a repository edit |
| which detectors run per `(atom, lang)` | the lock (detector item keys) | `packs lock` and `update` | PACK001 |
| inference | the entity's `attr infer = pack::rule;` in the model (grimble/binding.md 2.3), never ambient | the model author | a model edit |
| landing severity of a new atom (a lower CAP001 for one release) | the pack's per-atom `severity`, resolved into the lock `[pack.severity]` | pack author | a lock edit, PACK001 for the atom item |
| external pack identity | `grimble.toml` `[[packs.external]]` url and digest | by hand or `packs fetch --add` | a repository edit |

`grimble config show --effective` prints, per atom, the effective
severity with the layer that decided it (`repository`, `pack`, `rule`).
There is no pack default that is read at run time and appears in no
file: the lock carries the resolved severity pair precisely so that a
change to a pack's atom `severity` shows up as a one-line diff in
`grimble.packs.lock` as well as a PACK001 finding.

### 12.6 Detectors, the matrix and not-applicable

#### 12.6.1 One registry, one answer per (language, atom)

The effective registry of 3.2 answers `detectors(lang, atom)` of
grimble/binding.md 7.5 and grimble/binding.md 7.2 item 3: `NotApplicable | None |
Some(precision)`. The matrix cell algebra is docs/design/grimble/binding.md section 7 and is
not repeated; this section says where each of its inputs comes from.

#### 12.6.2 Combining detector rows

For one `(atom, lang)` over all enabled packs:

1. If any row is `impossible` and no real detector exists (a row with
   kind `query`, `callee`, `attribute` or `pattern`): the answer is
   NotApplicable. A mix is PACK004 (3.5) and the answer is Unknown until
   it is fixed (a conflicted cell never reads as measured).
2. Else if there is no real detector (no row, or only `none` rows): the
   answer is None (the cell is `unknown`).
3. Else the real detectors that are AVAILABLE (PACK003 below) are the
   answer; the precision is the weakest among them for a hit, and the
   cell can claim ABSENCE (the basis of `declared-unused`, CAP002) only
   if every declared real detector is available. A cell with an
   unavailable detector still reports `uses` for hits found by the
   available ones and is `unknown` where it would otherwise be
   `declared-unused` or blank: partial coverage is Some for P+ rules
   and None for P- rules, the standing polarity discipline.

A detector is AVAILABLE for a language when the adapter registered for
that language provides the facts it needs at the repository's fidelity:
the kind's engine exists (`pattern` needs gob-pattern), the adapter's
level is at least `min_fidelity` (default F2 for `callee` typed, F1 for
lexical, F2 for `attribute` and `query`), and every `needs` is met
(`manifest` needs the F2 manifest adapter of grimble/grmb-spec.md 20.2, `types`
needs the type capability of Q25, `scope` needs Q20). Otherwise the
row is unavailable and PACK003 reports it once per `(pack, atom, lang)`.

#### 12.6.3 Parents and hierarchy

Detectors are declared on leaf atoms. The cell of a parent atom `fs` is
the join of its children: `uses` if any child cell is `uses`;
`not-applicable` only if every child is; `unknown` if any child is
unknown and none is `uses`. A grant `may fs` covers `fs.read` and
`fs.write` (hierarchy, grimble/binding.md 7.5) and a template excuse for `fs`
excludes both. If a pack puts a detector on a parent atom, it answers
for each child that has no detector of its own at May precision (a hit
is a use of the parent but cannot tell which child), which is why
built-in packs do not.

#### 12.6.4 Where each cell kind comes from

| Cell | Source of the answer |
|---|---|
| `uses`, `undeclared` | a detector fired (Exact for typed, lexical flagged); grants decide which |
| `declared-unused` | a grant, every real detector available and complete, Exact absence (CAP002) |
| `denied` (blank) | no grant covers the atom for the node (deny by default, grimble/binding.md 7.2); no finding unless a use is observed (CAP001) |
| `excused` | a matrix-build template excuse (6.7): a `[[template]]` of an enabled pack or a `template` entity of the model (grmb-spec 4.7); a detected use in the covered code is CAP004, never a pass |
| `not-applicable` | ONLY a pack's explicit `impossible` detector for that `(lang, atom)` (below), or grimble/binding.md 7.2 item 1 (a node that owns no code) |
| `unknown` | no detector row, a `none` row, an unavailable detector, or a detector answer of Unknown; one summary Unresolved per node, never per cell |

#### 12.6.5 Not-applicable is declared only by `impossible`

NotApplicable is data in a pack, never an inference and never a model
claim (grimble/binding.md 7.3). A pack author writes a row:

```toml
[[detector]]
atoms  = "*"
langs  = ["css", "markdown", "toml", "json"]
kind   = "impossible"
reason = "static data languages: nothing here can perform an effect"
```

The `reason` is mandatory, is part of the item digest (so changing it is
PACK001), and is printed by `grimble status --explain ATOM LANG`. A pack
can declare impossible only for its OWN atoms (an `impossible` row whose
atom belongs to another pack is PACK005): one pack cannot suppress
another pack's measurement. A language that no pack mentions for an atom
is `unknown`, not not-applicable; there is deliberately no way to say
"everything else is impossible".

#### 12.6.6 Acceptance scenario

The ticket's acceptance criterion as a fixture (mdtest, G14): a
repository enables `core-effects` and a repository pack
`packs/acme-db.toml` that adds ONE atom with ONE detector:

```toml
format = 1
[pack]
name = "acme-db"
version = "0.1.0"
description = "Database access"
licence = "MIT"
[[atom]]
name = "db.query"
doc  = "Issues a query against the application database."
[[vocab]]
lang = "rust"
class = "db.query"
names = ["sqlx::query", "sqlx::query_as", "rusqlite::Connection::execute"]
[[detector]]
atom = "db.query"
lang = "rust"
kind = "callee"
[[detector]]
atom = "db.query"
lang = "css"
kind = "impossible"
reason = "stylesheets cannot query a database"
```

A node that owns Rust, Python and CSS files then has, for `db.query`:
the Rust column is `uses`, `undeclared`, `declared-unused` or blank per
the code and grants; the Python column is `unknown` (no row); the CSS
column is `not-applicable` (the pack's explicit `impossible`). The node
carries ONE summary Unresolved (`no-detector`) for the Python cell. If
the pack author had omitted the `css` row the CSS cell would also be
`unknown`; adding a TypeScript nowhere declared never yields
`not-applicable`. The fixture asserts the three cells.

#### 12.6.7 Template excuses in packs

An excuse is a matrix-build declaration, not a statement about a node
(D75; grmb-spec 4.7 gives the model-file twin). A pack author writes it
beside the atoms and detectors it qualifies:

```toml
[[template]]
name   = "generated-protobuf"
atom   = "net.listen"
for    = "lang(rust) & attr(generated_by = \"protoc\")"
reason = "generated stubs declare a server trait but never bind a socket"
```

- `for` is a selector over UNITS (grmb-spec 6.1), so languages, unit
  kinds and attributes decide what the excuse covers; `reason` is
  mandatory and is part of the item digest, so editing it is PACK001.
  The item key is `template:NAME`.
- A pack may excuse only its OWN atoms (PACK005 otherwise), as for
  `impossible`; a repository excuses any atom in a `template` entity of
  its model. Both feed one effective set; the check output
  (`grimble check --json`) lists and counts every excuse with its source
  (`pack:NAME@VERSION` or `model:TEMPLATE`).
- Built-in packs may ship templates. The three of milestone 2 ship none.
- A template is not `impossible`: `impossible` says the capability
  cannot exist in the language and is a detector fact (6.5,
  not-applicable); a template says the atom is set aside for selected
  code and the cell is `excused`. A detected use in excused code is
  CAP004 (grimble/binding.md 7.2), evaluated before the excuse, so a template
  can never mask a use. A template whose selection overlaps a model
  grant of the same atom (or an ancestor or descendant) is SYS012
  (grimble/binding.md 6.12).

### 12.7 The compute digest and the sibling contract

`compute_digest` (sibling-contract.md 3.3) exists so that two products
that BUILD U terms from the same file build the same terms. It covers
the six `[compute]` knobs because frob and grimble both read them. Packs
are not part of it, for three reasons: frob never reads a pack (D28; if
packs were in the digest frob would have to load them and every repository
using packs would see `compute digest differs`); a pack changes what
grimble DERIVES from U (effect sets, bindings) and not what U contains;
and the pack identity already has a better home.

Contribution of packs to the contract, all additive (sibling-contract.md
section 12.4: new optional keys do not move the major):

- `packs`: an array of `{name, version, digest}` sorted by name, one per
  enabled pack: the identity of the registry the run used (`name` is the
  pack id of 3.1, `digest` the pack digest of 2.5). Whether the run
  equalled the lock is not a key here; PACK001 findings carry it. frob
  prints the array in `doctor` and never validates it. The schema is
  `PackRef` in docs/schemas/sibling.json and the key is optional, present
  together with `packs_digest` (done by ticket 01M3ZAABA0DY25WGBZ8KDJD9BA).
- `packs_digest`: `blake3:` plus the hex blake3 of the canonical JSON of
  the `packs` array. It is the SIDE-INPUT digest of D30 (architecture.md,
  "findings are persisted per (file digest, rule id, rule version,
  side-input digest)") for every rule whose predicate reads the
  registry: CAP001, CAP002, CAP004, the NEAT effects rules, CI008 and CI009,
  and the binding rank 3 rows. Adding a pack or changing a pack digest
  therefore invalidates exactly those cached findings and no others.
- `fidelity[].capabilities` already carries atom ids pack-qualified with
  `typed`, `lexical`, `none` and `not_applicable` (sibling-contract.md
  3.4); the answer of 6.2 is what fills it, so `none` there is an
  atom with no available detector, one value per `(language, atom)`.
- `not_applicable_rules`: unchanged; atom cells that are not-applicable
  are listed in `capabilities`, never as findings.

The finding records for PACK rules use the standard `FindingRecord`
(sibling-contract.md 3.5) with `reason` `pack-unavailable` for PACK006
(a code now listed in sibling-contract.md 3.5, added by ticket 01M3ZAABA0DY25WGBZ8KDJD9BA).

### 12.8 The three built-in packs of milestone 2

Each pack is `crates/gob-ir/packs/NAME.toml` (3.2). Version `1.0.0`
for all three. The tables below are the content of the files; the
rationale, `cwe` and `safer_alternative` text of each row lives in the
file and is not repeated. Language ids are those of the adapter registry:
`rust`, `python`, `typescript` (the TypeScript adapter covers `.ts`,
`.tsx`, `.js`, `.mjs`, `.cjs`), `css`, `markdown`, `toml`, `json`,
`github-actions`, `dockerfile`, `shell`.

#### 12.8.1 core-effects

Shipped as data (ticket 867GGVJ): the pack lives in `packs/core-effects/`
(`pack.toml` version 1.0.0, `atoms.toml` with the atoms, parents, argument
kinds, aliases, vocabulary rows, detector rows, `[[receiver_family]]`
method gates and `[non_process]` crates). `gob_ir::core_pack` embeds and
parses it; `gob_packs::core_effects` digests it into the `core-effects`
entry of `grimble.packs.lock`, so any edit to the pack without a version
bump is a PACK001 lock drift finding. The `process.env` atom is now the
alias of `env.read`, and `exec` of `process.spawn`; the registry resolves
aliases to the canonical atom. TypeScript and C# vocabularies stay in
`gob-symbols` until the unknown-language ticket moves them.

Licence MIT; basis CWE-22, CWE-73, CWE-78, CWE-119, CWE-338, CWE-526,
CWE-668, CWE-918. Today 18 atoms (13 leaves, 5 parents); the v3 vocabulary (grimble-capabilities-v3.md section 3) extends this table with `fs.exec`, `fs.temp`, `net.resolve`, `net.tls`, `env.cwd`, `process.signal`, `thread`, `ffi`, `eval`, `deserialize`, `reflect`, `db`, `ipc`, `log` and `secret`, and the pack is versioned (v3 section 12.12), 37 vocabularies, 91
detector items (39 in the three source languages, 52 `impossible`),
146 lock items.

Severity convention: `CAP001/CAP002` (CAP003 is retired; CAP004 is a fixed Error and is not configurable). Effects that touch the
outside world or the host (`fs.*`, `net.*`, `env.write`, `process.spawn`,
`unsafe`) are `error/warn`; incidental effects that nearly
every node has (`env.read`, `clock`, `rng`, `stdio.*`, `exit`) are
`warn/warn`: still denied by default, but an ungranted use of an
incidental atom is a Warn, not an Error, so adoption is not a wall of
Errors (the model lists them where they are used); the repository raises
any of them with `[packs.severity]` (open question 11.10).

The `args` column names the atom's argument slots; their types, the extraction rule and the Unresolved verdict for each live in grimble-capabilities-v3.md section 3, which is the normative schema (`path` is a repo-relative or rooted path glob plus an operation set, `host` a host glob with port, scheme and address class, `name` an environment variable glob for `env.*` and a binary with argv shape and `shell` for `process.spawn`).

| Atom | Parent | `args` | CAP001 | CAP002 | cwe | Meaning |
|---|---|---|---|---|---|---|
| `fs` | | none | | | | any filesystem access (grouping atom) |
| `fs.read` | `fs` | path, ops | error | warn | CWE-22 | reads file content or directory listings or metadata |
| `fs.write` | `fs` | path, ops | error | warn | CWE-73 | creates, modifies, renames or removes files and directories |
| `net` | | none | | | | any network access (grouping atom) |
| `net.connect` | `net` | host, port, scheme, class | error | warn | CWE-918 | opens an outbound connection or sends a request |
| `net.listen` | `net` | bind, port, class | error | warn | CWE-668 | binds a socket or starts a server |
| `env` | | none | | | | process environment (grouping atom) |
| `env.read` | `env` | name | warn | warn | CWE-526 | reads environment variables (the working directory and executable path move to `env.cwd` in v3) |
| `env.write` | `env` | name | error | warn | CWE-454 | sets or removes environment variables or changes the working directory |
| `clock` | | none | warn | warn | | reads wall or monotonic time, or sleeps |
| `rng` | | none | warn | warn | CWE-338 | draws randomness |
| `stdio` | | none | | | | standard streams (grouping atom) |
| `stdio.read` | `stdio` | none | warn | warn | | reads standard input |
| `stdio.write` | `stdio` | none | warn | warn | | writes standard output or error |
| `exit` | | none | warn | warn | | terminates the process |
| `process` | | none | | | | process control (grouping atom) |
| `process.spawn` | `process` | bin, argv, shell, env | error | warn | CWE-78 | starts another program or a shell command (alias `exec`) |
| `unsafe` | | none | error | warn | CWE-119 | bypasses the language's memory or type safety |

Detectors, Rust (13 rows, kind `callee` with a typed match unless noted;
a trailing `!` is a macro call):

| Atom | Names (vocabulary class = atom name, lang `rust`) |
|---|---|
| `fs.read` | `std::fs::read`, `std::fs::read_to_string`, `std::fs::read_dir`, `std::fs::metadata`, `std::fs::File::open`, `tokio::fs::read`, `tokio::fs::read_to_string`, `tokio::fs::File::open` |
| `fs.write` | `std::fs::write`, `std::fs::create_dir`, `std::fs::create_dir_all`, `std::fs::remove_file`, `std::fs::remove_dir_all`, `std::fs::rename`, `std::fs::copy`, `std::fs::File::create`, `tokio::fs::write`, `tokio::fs::remove_file`, `tokio::fs::File::create` |
| `net.connect` | `std::net::TcpStream::connect`, `std::net::TcpStream::connect_timeout`, `std::net::UdpSocket::connect`, `tokio::net::TcpStream::connect`, `reqwest::get`, `reqwest::Client::*`, `ureq::get`, `ureq::post` |
| `net.listen` | `std::net::TcpListener::bind`, `std::net::UdpSocket::bind`, `tokio::net::TcpListener::bind`, `tokio::net::UdpSocket::bind` |
| `env.read` | `std::env::var`, `std::env::var_os`, `std::env::vars`, `std::env::current_dir`, `std::env::current_exe` |
| `env.write` | `std::env::set_var`, `std::env::remove_var`, `std::env::set_current_dir` |
| `clock` | `std::time::SystemTime::now`, `std::time::Instant::now`, `std::thread::sleep`, `tokio::time::Instant::now`, `tokio::time::sleep`, `chrono::Utc::now`, `chrono::Local::now` |
| `rng` | `rand::random`, `rand::thread_rng`, `rand::rng`, `getrandom::getrandom`, `uuid::Uuid::new_v4`, `std::hash::RandomState::new` |
| `stdio.read` | `std::io::stdin`, `tokio::io::stdin` |
| `stdio.write` | `std::io::stdout`, `std::io::stderr`, `println!`, `print!`, `eprintln!`, `eprint!`, `dbg!` |
| `exit` | `std::process::exit`, `std::process::abort` |
| `process.spawn` | `std::process::Command::new`, `tokio::process::Command::new` |
| `unsafe` | kind `query`, Q08 `attributes` with `names = ["unsafe"]` (the Rust adapter maps `unsafe` blocks, fns, impls and traits to an `unsafe` attribute node); `min_fidelity = "F2"` |

Detectors, Python (13 rows, kind `callee`, lang `python`):

| Atom | Names |
|---|---|
| `fs.read` | `open`, `pathlib.Path.read_text`, `pathlib.Path.read_bytes`, `pathlib.Path.open`, `pathlib.Path.iterdir`, `os.listdir`, `os.scandir`, `os.walk`, `os.stat` |
| `fs.write` | `open[mode~=[wax+]]`, `pathlib.Path.write_text`, `pathlib.Path.write_bytes`, `pathlib.Path.mkdir`, `pathlib.Path.unlink`, `os.remove`, `os.rename`, `os.mkdir`, `os.makedirs`, `shutil.copy`, `shutil.copytree`, `shutil.move`, `shutil.rmtree`, `tempfile.NamedTemporaryFile` |
| `net.connect` | `socket.create_connection`, `socket.socket.connect`, `requests.*`, `urllib.request.urlopen`, `httpx.*`, `http.client.HTTPConnection`, `http.client.HTTPSConnection`, `aiohttp.ClientSession` |
| `net.listen` | `socket.socket.bind`, `socket.socket.listen`, `http.server.HTTPServer`, `socketserver.TCPServer`, `asyncio.start_server`, `uvicorn.run` |
| `env.read` | `os.environ`, `os.getenv`, `os.getcwd` |
| `env.write` | `os.putenv`, `os.unsetenv`, `os.chdir`, `os.environ.setdefault`, `os.environ.update`, `os.environ.pop` |
| `clock` | `time.time`, `time.monotonic`, `time.perf_counter`, `time.sleep`, `datetime.datetime.now`, `datetime.datetime.utcnow`, `datetime.date.today` |
| `rng` | `random.*`, `secrets.*`, `os.urandom`, `uuid.uuid4`, `numpy.random.*` |
| `stdio.read` | `input`, `sys.stdin.read`, `sys.stdin.readline`, `sys.stdin.readlines` |
| `stdio.write` | `print`, `sys.stdout.write`, `sys.stderr.write` |
| `exit` | `sys.exit`, `os._exit`, `exit`, `quit` |
| `process.spawn` | `subprocess.run`, `subprocess.Popen`, `subprocess.call`, `subprocess.check_call`, `subprocess.check_output`, `os.system`, `os.popen`, `os.execv`, `os.spawnv`, `asyncio.create_subprocess_exec`, `asyncio.create_subprocess_shell` |
| `unsafe` | `ctypes.*`, `cffi.FFI`, `mmap.mmap` |

A Python callee that does not resolve through the scope graph (dynamic
import, attribute of an untyped value) is matched Lexically on its last
two segments and reported with that precision; `[compute] dynamic_calls`
governs the rest (universal-model.md 4.6).

Detectors, TypeScript (12 `callee` rows and one `impossible`, lang
`typescript`; a global member read such as `process.env` is a name):

| Atom | Names |
|---|---|
| `fs.read` | `fs.readFile`, `fs.readFileSync`, `fs.readdir`, `fs.readdirSync`, `fs.stat`, `fs.promises.readFile`, `fs.createReadStream`, `Deno.readTextFile`, `Deno.readFile`, `Bun.file` |
| `fs.write` | `fs.writeFile`, `fs.writeFileSync`, `fs.appendFile`, `fs.mkdir`, `fs.rm`, `fs.unlink`, `fs.rename`, `fs.copyFile`, `fs.promises.writeFile`, `fs.createWriteStream`, `Deno.writeTextFile`, `Deno.writeFile`, `Bun.write` |
| `net.connect` | `fetch`, `XMLHttpRequest`, `WebSocket`, `http.request`, `http.get`, `https.request`, `https.get`, `net.connect`, `net.createConnection`, `axios.*`, `undici.request` |
| `net.listen` | `net.createServer`, `http.createServer`, `https.createServer`, `net.Server.listen`, `http.Server.listen`, `Deno.serve`, `Bun.serve` |
| `env.read` | `process.env`, `process.cwd`, `Deno.env.get`, `Bun.env` |
| `env.write` | `process.chdir`, `Deno.env.set`, `Deno.env.delete` |
| `clock` | `Date.now`, `Date[argc=0]`, `performance.now`, `process.hrtime`, `setTimeout`, `setInterval` |
| `rng` | `Math.random`, `crypto.randomUUID`, `crypto.getRandomValues`, `crypto.randomBytes`, `crypto.randomInt` |
| `stdio.read` | `process.stdin.read`, `readline.createInterface`, `Deno.stdin.read`, `prompt` |
| `stdio.write` | `console.log`, `console.error`, `console.warn`, `console.info`, `console.debug`, `process.stdout.write`, `process.stderr.write`, `Deno.stdout.write` |
| `exit` | `process.exit`, `process.abort`, `Deno.exit` |
| `process.spawn` | `child_process.exec`, `child_process.execSync`, `child_process.execFile`, `child_process.spawn`, `child_process.spawnSync`, `child_process.fork`, `Deno.Command`, `Bun.spawn` |
| `unsafe` | `impossible`: "TypeScript has no memory-unsafe construct; `any` and casts are type-level facts reported by NEAT, not capabilities" |

Data languages (one declaration, 52 expanded items): `atoms = "*"`,
`langs = ["css", "markdown", "toml", "json"]`, `kind = "impossible"`,
`reason = "static data languages: nothing here can perform an effect"`.
Not declared, hence `unknown` until a pack says otherwise: `shell`,
`dockerfile`, `github-actions` and every other language (a shell script
can do any of these; a workflow's `run:` payload is opaque and is
handled by `ci-github`).

#### 12.8.2 ci-github

Licence MIT; basis docs/design/grimble/rule-families.md section 5 (CI007 to CI011), cicd-survey.md.
14 atoms (4 parents, 10 leaves), 8 vocabularies, 10 detector items in
`github-actions` and 70 `impossible` items, 102 lock items. CAP defaults
`error/warn/advisory` for every leaf (a publish, a token or a deploy
that no node declares is the finding class CI008 to CI011 and the
CI-to-repo join are built on).

| Atom | Parent | `args` | Meaning |
|---|---|---|---|
| `ci` | | none | anything a workflow does beyond building and testing (grouping) |
| `ci.publish` | `ci` | none | publishes an artifact to a registry (grouping; the vocabulary class `ci.publish` is `[ci] registries`) |
| `ci.publish.crates` | `ci.publish` | name | publishes a crate to crates.io |
| `ci.publish.pypi` | `ci.publish` | name | publishes a distribution to PyPI |
| `ci.publish.npm` | `ci.publish` | name | publishes a package to npm |
| `ci.publish.container` | `ci.publish` | name | pushes an image to a container registry |
| `ci.publish.release` | `ci.publish` | none | creates a GitHub release or uploads release assets |
| `ci.token` | `ci` | none | a step handles a credential (grouping) |
| `ci.token.secret` | `ci.token` | name | a step receives a secret whose name looks like a credential |
| `ci.token.github` | `ci.token` | none | a job's `GITHUB_TOKEN` carries a write permission |
| `ci.deploy` | `ci` | none | changes a running environment (grouping) |
| `ci.deploy.pages` | `ci.deploy` | none | deploys a static site |
| `ci.deploy.cloud` | `ci.deploy` | name | deploys to a cloud service or applies infrastructure |
| `ci.deploy.cluster` | `ci.deploy` | name | applies manifests or charts to a cluster |

Detectors, all lang `github-actions` (names use the `uses:` prefix for
an action reference, resolved through the Actions adapter, and `run:`
for a command-line prefix in an opaque shell payload, matched Lexically):

| Atom | Kind | Names or query |
|---|---|---|
| `ci.publish.crates` | callee | `uses:rust-lang/crates-io-auth-action`, `uses:katyo/publish-crates`, `run:cargo publish`, `run:cargo release` |
| `ci.publish.pypi` | callee | `uses:pypa/gh-action-pypi-publish`, `run:twine upload`, `run:uv publish`, `run:flit publish`, `run:poetry publish`, `run:maturin publish` |
| `ci.publish.npm` | callee | `uses:JS-DevTools/npm-publish`, `run:npm publish`, `run:pnpm publish`, `run:yarn npm publish`, `run:bun publish` |
| `ci.publish.container` | callee | `uses:docker/build-push-action[push=true]`, `uses:redhat-actions/push-to-registry`, `run:docker push`, `run:podman push`, `run:skopeo copy` |
| `ci.publish.release` | callee | `uses:softprops/action-gh-release`, `uses:ncipollo/release-action`, `uses:actions/create-release`, `uses:taiki-e/upload-rust-binary-action`, `run:gh release create`, `run:gh release upload` |
| `ci.token.secret` | query | Q13 `name_uses` with `args = { context = "secrets", name_re = "(?i)(token|pat|key|secret|password|credential)" }` over `env:` and `with:` of a step; `min_fidelity = "F3"` |
| `ci.token.github` | query | Q19 `keys` for `permissions.<scope>: write` or `write-all` at job or workflow level; `min_fidelity = "F2"` |
| `ci.deploy.pages` | callee | `uses:actions/deploy-pages`, `uses:peaceiris/actions-gh-pages`, `uses:JamesIves/github-pages-deploy-action` |
| `ci.deploy.cloud` | callee | `uses:aws-actions/amazon-ecs-deploy-task-definition`, `uses:google-github-actions/deploy-cloudrun`, `uses:azure/webapps-deploy`, `uses:superfly/flyctl-actions`, `run:gcloud run deploy`, `run:az webapp deploy`, `run:flyctl deploy`, `run:terraform apply`, `run:pulumi up` |
| `ci.deploy.cluster` | callee | `uses:azure/k8s-deploy`, `uses:azure/k8s-set-context`, `run:kubectl apply`, `run:kubectl rollout`, `run:helm install`, `run:helm upgrade` |

`impossible` (one declaration, 70 expanded items): `atoms = "*"`, `langs
= ["rust", "python", "typescript", "css", "markdown", "toml", "json"]`,
reason "CI steps exist only in CI files". `shell`, `dockerfile` and
other languages stay `unknown`. A CI file is bound to a node with
`owns ".github/workflows/**"` and the matrix row of that node is the
publish, token and deploy surface of the repository's workflows; CI008
and CI009 read `callee_vocab(github-actions, ci.publish)` (Q47), so the
repository's `[ci] registries` additions are part of the same
vocabulary.

#### 12.8.3 rust-ecosystem

Licence MIT; basis the Cargo reference. 7 atoms (3 parents, 4 leaves),
5 node kinds, 2 inference rules, 0 vocabularies, 5 Rust detector items,
24 `impossible` items, 43 lock items.

| Atom | Parent | Meaning | CAP001/2/3 |
|---|---|---|---|
| `build` | | build-time behaviour of a package (grouping) | |
| `build.script` | `build` | the package runs a `build.rs`: arbitrary code at build time with the builder's full privileges | warn / warn / advisory |
| `macro` | | compile-time code generation (grouping) | |
| `macro.proc` | `macro` | the crate is a procedural macro: arbitrary code inside the compiler | warn / warn / advisory |
| `ffi` | | the foreign function boundary (grouping) | |
| `ffi.export` | `ffi` | exports a C-ABI symbol (`#[no_mangle]`, `#[export_name]`, `extern "C" fn`) | warn / warn / advisory |
| `ffi.import` | `ffi` | declares foreign symbols (`extern` blocks, `#[link]`) | warn / warn / advisory |

Detectors (lang `rust`):

| Atom | Kind | Row |
|---|---|---|
| `build.script` | query | Q19 `keys` on the package manifest: `package.build` is set, or the artifact `build.rs` exists at the package root (Q01); `needs = ["manifest"]`, `min_fidelity = "F2"` |
| `macro.proc` | attribute | `names = ["proc_macro", "proc_macro_derive", "proc_macro_attribute"]` |
| `ffi.export` | attribute | `names = ["no_mangle", "export_name", "unsafe(no_mangle)"]` |
| `ffi.import` | attribute | `names = ["link", "link_name"]` |
| `ffi.import` (`#2`) | pattern | `engine = "gpol"`, `pattern = 'extern $ABI { $$$ITEMS }'` (extern blocks without `#[link]`); unavailable until gob-pattern (G17) ships, so PACK003 reports it and the `ffi.import` cell cannot claim absence |

`impossible` (one declaration, 24 items): `atoms = "*"`, `langs =
["python", "typescript", "css", "markdown", "toml", "json"]`, reason
"a Cargo and rustc concept". The unit that matters is `build.rs`: it is
an ordinary Rust file whose identities are owned by the package's node,
so its `fs`, `process` and `net` uses are ordinary cells of that node,
and `build.script` marks that the package executes them at build time (a
build script that spawns a process is `uses` on both `process.spawn` and
`build.script`).

Node kinds (a node declares `kind crate_lib;`): `crate_lib`,
`crate_bin`, `crate_proc_macro`, `crate_cdylib`, `crate_staticlib`, each
with the typed attribute `cargo::package` (string) and `crate_type`
(ident), the Cargo crate types.

Inference rules (rank 3, grimble/binding.md 2.3; requested with `attr infer =
rust_ecosystem::crate_owns_dir;`):

```toml
[[infer]]
id      = "crate_owns_dir"
applies = { entity = "node", attr = "cargo::package" }
role    = "owns"
from    = { adapter = "cargo-manifest", fact = "package.dir", match = "attr:cargo::package == package.name" }
status  = "may"
reason  = "a Cargo package owns its directory"

[[infer]]
id      = "bin_owns_target"
applies = { entity = "node", attr = "cargo::bin" }
role    = "owns"
from    = { adapter = "cargo-manifest", fact = "bin.path", match = "attr:cargo::bin == bin.name" }
status  = "may"
reason  = "a Cargo bin target owns its source path"
```

Both need the F2 manifest adapter (grimble/grmb-spec.md 20.2); without it
they yield nothing and the request is Unresolved `inference-unavailable`
(grimble/binding.md 2.3 item 6).

#### 12.8.4 Counts

| Pack | Atoms | Leaves | Vocab | Detector items | of which impossible | Other items | Lock items |
|---|---|---|---|---|---|---|---|
| core-effects | 18 | 13 | 37 | 91 | 52 | 0 | 146 |
| ci-github | 14 | 10 | 8 | 80 | 70 | 0 | 102 |
| rust-ecosystem | 7 | 4 | 0 | 29 | 24 | 7 (5 kinds, 2 infer) | 43 |

(Detector items: 91 = 39 + 52; 80 = 10 + 70; 29 = 5 + 24. Lock items
are atoms plus vocabularies plus detector items plus other items, so
`ci-github` is 14 + 8 + 80 = 102 and `rust-ecosystem` is 7 + 29 + 7 = 43.)
Total 40 atoms, 291 lock items.

#### 12.8.5 unity (opt-in, engine entry points)

`packs/unity.toml`, version `0.1.0`, is a built-in pack outside the
three of milestone 2. It is disabled by default and is enabled only by
the root `frob.toml`, never by an adapter:

```toml
[[packs.enable]]
name  = "unity"
paths = ["Assets/**"]   # optional; omit for the whole repository
```

(`[packs] enabled = ["unity"]` works too.) Unlike the three packs above
it holds no atoms or detectors: its `[[vocab]]` tables (`lang =
"csharp"`) name the code the engine calls itself, so no caller exists in
the repository. The manifest part (`[pack]`) is validated as any other
(PACK005); the `[[vocab]]` tables are split off by
`gob_packs::unity::UnityPack::parse` and loaded into a
`gob_ir::engine::EngineVocab`. The file is read through `include_str!`
in `gob-packs`; the `builtin_pack!` macro of 3.2 does not exist yet.

| Class | Names |
|---|---|
| `entry.message` | `Awake` `Start` `Update` `FixedUpdate` `LateUpdate` `OnEnable` `OnDisable` `OnDestroy` `OnValidate` `Reset` `OnGUI` `OnApplicationQuit` |
| `entry.message_prefix` | `OnDrawGizmos` `OnTrigger` `OnCollision` `OnMouse` |
| `entry.base` | `MonoBehaviour` `ScriptableObject` |
| `entry.method_attribute` | `RuntimeInitializeOnLoadMethod` `MenuItem` `ContextMenu` |
| `entry.type_attribute` | `InitializeOnLoad` `CreateAssetMenu` |
| `serialized.attribute` | `SerializeField` `SerializeReference` |
| `serialized.skip_attribute` | `NonSerialized` |
| `dynamic.call` | `SendMessage` `SendMessageUpwards` `BroadcastMessage` `Invoke` `InvokeRepeating` `StartCoroutine` `StopCoroutine` `CancelInvoke` `IsInvoking` |
| `dynamic.lookup` | `GameObject.Find` `GameObject.FindWithTag` `GameObject.FindGameObjectWithTag` `GameObject.FindGameObjectsWithTag` `Resources.Load` `Resources.LoadAsync` `Resources.LoadAll` |

A message is a root on a type that derives from an `entry.base`,
transitively through project-local base types, or that carries an
`entry.type_attribute`. A method with an `entry.method_attribute` is a
root. The static constructor of an `[InitializeOnLoad]` type is a root.
`frob-tests` `reach::engine_roots` computes the set; COV001 seeds its
reach with the roots and never reports them. With the pack disabled
nothing changes.

Serialized state has an external writer: the editor, a scene or a prefab
fills it, so no assignment exists in code. A field has one when it is not
`static`, `const` or `readonly`, carries no `serialized.skip_attribute`,
and either carries a `serialized.attribute` (on any type) or is a
`public` field of a type that derives from an `entry.base`
(`reach::engine_derived_types`: transitive through project-local bases,
partial parts merged by name, nested types do not inherit from their
container). An auto-property counts only through a `[field: ...]`
attribute. `frob_obligations::never_written_fields` lists the C# fields
and `[field:]` auto-properties that no code assigns (a lexical,
name-based scan of every `.cs` file: `=`, compound assignment, `++`/`--`,
`ref`/`out`, initializers; a same-named local only hides a report) and
that have no external writer. The exclusion applies only when the pack
is enabled and active for the file's path; with it disabled a
`[SerializeField]` field that is never assigned is listed. No rule
consumes the list yet.

Dynamic calls are resolved by the engine by name at run time, so no edge
to the method exists in the repository. They are already Unresolved call
edges (nothing declares `Invoke`); `gob_symbols::csharp_dynamic_calls`
names why. A `dynamic.call` name classifies a call whose first argument is
a string literal (any receiver), or a computed one on `this` or an
unqualified call; `Invoke()` with no argument and a delegate's `Invoke(x)`
on another receiver are ordinary calls. A `dynamic.lookup` entry
(`Type.Method`) classifies a call with any argument, matched on the type
written at the call. A literal name never turns into an edge and nothing
is resolved by guesswork. With the pack disabled the vocabulary is empty
and nothing is classified. UnityEvent wiring in scene and prefab YAML is
not read yet; only GUID references are in scope (code-model.md 3).

Counts: 1 vocabulary pack, 0 atoms, 9 vocabulary classes, 42 names.

### 12.9 The PACK rule family

Implementation note: PACK001 to PACK008 are declared (staged, no-op `check`) in `crates/grimble-capabilities/src/pack_rules`, with one mdtest page each. `pack_rules::evaluate` is the one pass: PACK001 over loaded packs only, PACK006 as an Unresolved (required when the pack is) for packs that could not be loaded, and PACK002 to PACK005, PACK007, PACK008 from per-pack issues. PACK009 stays retired.

Ids `FAMILYNNN`, new family PACK, registered in rules.md by the
implementation ticket; owner crate `grimble-capabilities`. Polarity is
universal-model.md 4.2; every rule declares polarity and `needs`
(docs/design/shared/rules.md section 2).

| Id | Alias | Polarity | Default | Condition (fires iff) | Unresolved when |
|---|---|---|---|---|---|
| PACK001 | PACK-LOCK-MISMATCH | P0 | Error | for an enabled pack the computed item or pack digest differs from the lock, or the lock lacks the pack or an item (`added`, `removed`, `changed`, `lock-missing`, `lock-stale`, `scheme`); one finding per item | the pack bytes cannot be read: PACK006 is raised instead and PACK001 does not evaluate that pack |
| PACK002 | PACK-UNKNOWN-ATOM | P+ | Error | an atom spelled in an attestation (`grimble:effects`), a `[packs.severity]` key, a pack's own claim template or infer `applies`, or an exceptions entry resolves to no atom of any enabled pack; MDL016 is the same predicate for atoms in .grmb files and PACK002 is suppressed where MDL016 fired for the same text (one root cause, one finding); a hint names an atom that exists in an installed but not enabled pack | an enabled pack failed to load (PACK006): the atom might be there, reason `pack-unavailable` |
| PACK003 | PACK-DETECTOR-UNAVAILABLE | P0 | Warn | a real detector row of an enabled pack for `(atom, lang)` is not AVAILABLE at the repository's fidelity for that language (6.2): engine missing (`pattern` before gob-pattern), adapter level below `min_fidelity`, or a `needs` unmet; once per `(pack, atom, lang)`; the cell degrades to `unknown` where it would claim absence | the adapter for the language is not installed, so its fidelity is unknown (reason `fidelity`) |
| PACK004 | PACK-DUPLICATE | P+ | Error | two enabled packs declare the same pack name, atom or alias, node kind, infer id, claim id or lattice gap, or disagree `impossible` versus a real detector for one `(atom, lang)` (3.5); the message names both packs and both items | never (the comparison is exact over loaded packs) |
| PACK005 | PACK-MALFORMED | P+ | Error | a pack file fails the schema or a semantic check of 2.6 (unknown key, parent atom missing, unknown Q-id, `impossible` without reason, `impossible` on another pack's atom, `infer` status other than `may`, bad semver) | never |
| PACK006 | PACK-UNAVAILABLE | none (Unresolved only) | Unresolved, required | an enabled pack cannot be loaded: a repository file missing, an external pack declared but not vendored, a vendored file whose pack digest differs from `grimble.toml` (the last is PACK001 for the lock but PACK006 for the declared digest) | it is itself Unresolved, reason `pack-unavailable`; it fails the gate under `fail_on_unresolved = "required"` |
| PACK007 | PACK-UNKNOWN-RULE | P+ | Error | an `attr infer = pack::rule;` names a pack not enabled or a rule the pack does not declare | the pack failed to load (PACK006) |
| PACK008 | PACK-REDUNDANT-OVERRIDE | P0 | Advisory | a repository override (`[packs.severity]`, `[neat.effects.<lang>]` name, `[ci] registries` name) equals the effective pack value, so it has no effect | never |

Notes:

- PACK001 is the drift-lock. It is Error because an unreviewed change of
  what the checker believes is exactly the failure the lock exists to
  prevent; the fix is `grimble packs update` (4.5), reviewed in the diff.
- PACK003 is Warn, not Error, because the cell degrades safely: a
  detector that cannot run produces `unknown` (and one Unresolved per
  node), never a clean cell. It is the visible form of "the pack knows
  more than this repository's tooling" and tells the user which adapter
  or engine would unlock it.
- A pack-derived finding of another family (CAP001 at a use a new
  detector found) carries the pack, the locked version and the item key
  in its provenance so `grimble explain` can say which pack row caused
  it.

### 12.10 Worked example: this repository

This repository has no `grimble.toml` yet; the file below is the one it
would carry, selecting the three built-in packs. It is an illustration:
the cell values below are what the registry of section 12.8 and the
algebra of docs/design/grimble/binding.md section 7 yield for the stated code facts, and are
verified by the G14 conformance corpus when it lands, not today.

`grimble.toml` (the packs part):

```toml
[packs]
enabled = ["grimble/core-effects", "grimble/ci-github", "grimble/rust-ecosystem"]

[packs.severity]
"unsafe"      = { CAP001 = "error" }       # already the default; kept as the repository's statement
"stdio.write" = { CAP001 = "off" }

[neat.effects.rust]
"fs.write" = ["gob_text::atomic_write"]    # a repository-internal chokepoint is an fs.write too
```

`grimble.packs.lock` after `grimble packs lock` has three `[[pack]]`
tables (146, 102 and 43 items, section 12.8.4) and a `[pack.severity]` row
per atom; the repository commits it. `design/frob.grmb` (grmb-spec section
13) gains the pin of each pack it names:

```
pack core_effects   { ref "grimble/core-effects";   version "1.0.0"; digest "blake3:6f1c...e90a"; }
pack ci_github      { ref "grimble/ci-github";      version "1.0.0"; digest "blake3:2b9d...41c7"; }
pack rust_ecosystem { ref "grimble/rust-ecosystem"; version "1.0.0"; digest "blake3:a07e...d3f2"; }

node exec : trusted {
  kind crate_lib;
  owns "crates/gob-exec/**";
  may fs.read at "crates/gob-exec/**";
  may process.spawn at "crates/gob-exec/**";
  may env.read at "crates/gob-exec/**";
  may unsafe at "crates/gob-exec/**";
}

node git : trusted {
  kind crate_lib;
  owns "crates/gob-git/**";
  may fs.read, fs.write at "crates/gob-git/**";
  may net.connect("github.com") at "crates/gob-git/**";
  may process.spawn at "crates/gob-git/**";
  may env.read at "crates/gob-git/**";
}
```

The two crates own Rust files plus `Cargo.toml` (language `toml`),
`README.md` and similar (`markdown`). Stated code facts: `gob-exec`
calls `std::process::Command::new` and `std::env::var_os`, reads files,
has no `unsafe` and no `build.rs`; `gob-git` reads and writes files,
connects to GitHub (through the HTTP client), reads the environment and
spawns one `git merge` (architecture.md). The matrix rows follow
(languages `toml` and `markdown` leave the subject set of every
core-effects and rust-ecosystem cell because those cells are
`impossible` there; `ci.*` cells are `not-applicable` for every Rust
node):

| Atom | node `exec` | node `git` |
|---|---|---|
| `fs.read` | uses | uses |
| `fs.write` | denied | uses |
| `net.connect` | denied | uses |
| `net.listen` | denied | denied |
| `env.read` | uses | uses |
| `env.write` | denied | denied |
| `clock` | denied | denied |
| `rng` | denied | denied |
| `stdio.read` | denied | denied |
| `stdio.write` | denied | denied |
| `exit` | denied | denied |
| `process.spawn` | uses | uses |
| `unsafe` | declared-unused (CAP002 Warn; Exact absence, so `grimble shrink` may remove the grant) | denied |
| `build.script` | denied | denied |
| `macro.proc` | denied | denied |
| `ffi.export` | denied | denied |
| `ffi.import` | unknown (PACK003: the pattern detector of `ffi.import` is unavailable) | unknown (same) |
| `ci.publish.*`, `ci.token.*`, `ci.deploy.*` | not-applicable | not-applicable |

Summary: each node carries ONE Unresolved (`no-detector`, listing
`ffi.import`) until gob-pattern ships; the `not-applicable` cells and the
`denied` cells produce none (no use was observed, so there is nothing
to report: a blank cell is "denied", not "unconsidered"). The two nodes
no longer say `excuses net` or `excuses net.listen`: not granting the
atom is the whole statement, and a later `TcpListener::bind` in
`gob-git` would be CAP001. Adding `"stdio.write"` to the node would
change nothing until a use is observed. If `crates/gob-exec/scripts/*.sh` existed, every
core-effects cell for the `shell` files would be `unknown` (no pack
declares `shell`), and the node would carry the same single Unresolved
until a repository pack adds shell detectors or a matrix-build template
excuses the atoms for `lang(shell)` with a reason (6.7); even then a
detected use is CAP004, never a pass.

An update scenario: a later `core-effects` 1.1.0 adds `fs.read` names
`std::fs::symlink_metadata` and a new atom `net.dns`. After upgrading
the binary, `grimble check` reports one PACK001 `changed` for
`vocab:rust/fs.read` (name count 8 to 9), one `added` for `atom:net.dns`,
one pack-level finding for the version, and nothing else changes until
`grimble packs update --dry-run` is reviewed and `grimble packs update
--write-model` commits the new lock and the three digests.

### 12.11 Open questions

1. Answer to grmb-spec open question 1 (trust and label lattices). A
   pack, not a model file, owns lattice extension: `[lattice.trust]` and
   `[lattice.label]` insert NEW elements into a gap of the existing
   total order (`above`, `below`, both existing), never remove or
   reorder, so every proof over the builtin elements stays valid. Why not
   a `lattice` item in the model: a lattice is shared by every node and
   flow, a model-local one makes a proof depend on file order and
   includes (MDL001 territory), and it would add grammar (D22 refuses
   new grammar for optional vocabulary). Two packs inserting in one gap
   are PACK004; a model naming an element of a disabled pack is MDL009.
   The built-in packs of milestone 2 insert nothing; the first user is
   an `isolation` pack with a `sandboxed` trust level between `foreign`
   and `authenticated`. The pack format reserves `[lattice.*]` now so a
   pack with lattices needs no format major later; implementing it can
   wait for that pack. Decision for review.
2. Answer to grmb-spec open question 11 (pin updates): see 4.6. Exact
   pins stay; `grimble packs update` rewrites the lock alone by default
   and the `version` and `digest` clauses of named `pack` entities only
   under `--write-model`; never as a side effect of another verb.
3. RESOLVED by ticket 01M3ZAABA0DY25WGBZ8KDJD9BA. Answer to sibling-contract.md open
   question 1 (rename of the grimble-prefixed contract name): YES, rename to the product-neutral
   `gob.sibling/1`, before any consumer exists. Reasons: crunk emits the
   same document and `product` already distinguishes the producer, so a
   `grimble.` prefix leaks one product's name into the other's wire
   format (D18: products never depend on each other and the substrate is
   `gob-*`); the schema file is already product-neutral
   (`docs/schemas/sibling.json`); and renaming after frob ships
   `ACCEPTED_SIBLING_MAJORS` is a major bump while renaming now is free.
   The grimble-owned `grimble.graph/1` export keeps its name (only
   grimble produces it). Packs add nothing to the argument either way;
   the `packs` and `packs_digest` keys of section 12.7 are additive under
   either name.
4. Is `description` really excluded from the digest? Excluding it keeps
   a typo fix from re-locking, but a rewritten `doc` can change the
   meaning of an atom without any item changing. The proposal relies on
   review of the pack diff and the version bump convention; the
   alternative (a separate non-gating `text` digest that produces an
   Advisory) is cheap to add later.
5. Item granularity of vocabularies. One PACK001 per vocabulary
   (language, class) says "changed" without the names. Per-name items
   would triple the lock for `core-effects`. Proposal: keep per
   vocabulary plus the name count, with name-level detail from
   `grimble packs diff` and release changelog fragments.
6. `impossible` for whole language sets is a strong claim made in
   data. `ci-github` declares seven languages impossible; a repository
   that generates workflows with a Python script would still produce
   `ci.publish` effects in the workflow, not in the script, so the
   claim holds, but a pack author could be wrong for a language this
   design did not foresee. Mitigation: the reason is in the digest and
   shown by `status --explain`; PACK004 catches contradiction by another
   pack; an author error is a pack bug fixed by a new version, and the
   lock makes the correction visible.
7. External packs trust only a digest. A signature (minisign or
   sigstore) would bind the digest to an identity. Deferred: milestone 2
   ships no external packs, and a vendored pack is reviewed in git like
   code.
8. Effective registry versus inventory (3.2): `registry::detectors()` as
   landed reads inventory only. Whether the product API is the
   `EffectiveRegistry` value everywhere or the free functions delegate
   to a process-wide effective registry installed at start-up is an
   implementation choice for G14; the specification only fixes the
   answers.
9. Claim templates and obligations are specified in format only (2.2);
   their semantics (how an obligation is discharged at a rung, how the
   proof ladder `L1`..`L5` of grmb-spec open question 5 applies) belong
   to the threat-pack design that first uses them.
10. Incidental atoms under deny-by-default (D75). `env.read`, `clock`,
    `rng`, `stdio.*` and `exit` are used by nearly every node, and a
    blank cell now means denied, so every node must grant them or carry
    a CAP001 Warn. Options: a model-level default grant set, a pack
    `default_grant` list, or accept the Warn. Left open; the pack
    default is `warn` so adoption is not blocked.

### 12.12 Changes to other documents

- docs/design/grimble/grmb-spec.md#20-the-model-and-the-substrate points here instead of repeating the pack
  description (done in this change); section 12.9.6 keeps the registry
  definition and gains one sentence pointing to section 12.3.2 here.
- README.md gains the index row and decision D68 (draft pending
  review).
- docs/design/shared/architecture.md section 1.6 gains, for the implementation ticket:
  `[packs] enabled`, `[packs] lock`, `[[packs.external]]`, `[packs.severity]`
  and `[neat.effects.exclude]` rows (owner `grimble-capabilities`;
  materialized: `enabled` and `lock`), plus the `grimble.packs.lock` row
  of the storage table; added by ticket 01M3ZAABA0DY25WGBZ8KDJD9BA.
- grimble/grmb-spec.md: the `pack` entity's `ref` grammar is the id of 3.1;
  atoms and infer rule ids are `ident` segments (2.2 here). Examples in
  other files that write kebab-case ids in `attr infer` (grimble/binding.md 2.3
  writes `cargo.crate-owns-dir`) are illustrative.
- sibling-contract.md: done by ticket 01M3ZAABA0DY25WGBZ8KDJD9BA: `pack-unavailable` in the
  reason codes of 3.5, the optional `packs` and `packs_digest` keys in
  3.2, and the rename of question 3 above.
- rules.md and charter.md 4.2.5: the PACK family (section 12.9, ids
  PACK001-PACK099) is registered by ticket 01M3ZAABA0DY25WGBZ8KDJD9BA.
- notes: no registry YAML survives from v1 (notes/v1/strata.md section 8);
  v1's `frob registry` drift-lock has no direct successor beyond the
  generated rule registry of docs/design/grimble/grmb-spec.md#20-the-model-and-the-substrate and this lock.

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D76

Accepted with changes (owner decision 2026-10-04, ~J8PJHKX): first-class plugins (packs-and-plugins.md). The standard library is built as packs on the same public mechanism third parties use; GRL is the one rule language for pattern and relational rules (no YAML form), so it must be intuitive (grl-spec.md, D80); built-in rules are compiled into the binary (GRL to Rust at build time) for speed and treated logically the same as plugin rules (same source, registry, metadata, config, lock entry, diagnostics, and a conformance test requiring identical findings against the plan form; overrides only by declared `replaces`); plugin GRL runs as cached plans on one executor built from the same operator library; tier 3 code rules are batched per-file WASM components with budgets that report Unresolved; tier 4 adapters are grammar plus declarative mapping and scope files; universal rules are checked to use only U; excuses and atoms are pack data; no dylibs, no per-node callbacks; no directory-scoped packs (path-scoped activation from the root config, `grimble config --for FILE`); repository packs may run tier 3 with any effect under a trust model (pure by default, declared and scoped effects, grants pinned to the pack digest, per-machine trust store, explicit CI trust, hard limits), subject to a pessimistic security audit (~1RH38WH)

### D68

Data packs and the registry drift-lock (packs-and-plugins.md, G04; draft pending review): a pack is one digest-pinned TOML document of atoms, detectors (query, callee, attribute, pattern, none, impossible), callee vocabularies shared with `[neat.effects]` and `[ci] registries`, May-only inference rules, claim templates and node kinds, never code or grammar; built-in packs are `gob-ir` inventory entries built from the same TOML, repository packs live in `packs/`, external packs by URL plus digest and are vendored; duplicate atom names are PACK004; `grimble.packs.lock` pins name, version, pack digest and per-item digests plus the materialized CAP severities, and a changed pack is one PACK001 per item, never silent; `grimble packs update` is the only writer and `--write-model` is the only way it touches a model (answers grmb-spec question 11); not-applicable is declared only by a pack's `impossible` detector; packs stay out of `compute_digest` and add `packs` and `packs_digest` to the sibling document; lattice extension is by pack (answers grmb-spec question 1); its proposed contract rename was settled by D69; PACK001-008
