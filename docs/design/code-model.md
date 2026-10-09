# Code model, symbolic binding, and the directive DSL

Status: DRAFT (T-0001, a v1-format id that migrates with an alias).
Ownership after products.md: sections 1-4 and 8-9 are `gob-symbols`,
`gob-directives` and `gob-cache` (shared by all three products);
section 5 is now a pointer to universal-model.md (`gob-ir`), and
sections 6-7 (binds, capability matrix) are grimble crates
(boundaries.md); all of them are Milestone 2 or later (D36). Inputs:
notes/v1/graph-lang-dsl.md, the universal-binding requirement in
goals.md, notes/rust-ecosystem.md.

## 1. What this layer owns

- Parsing every supported language into one normalized code model.
- Symbol identity (addresses) that are stable across formatting, usable
  from any language, doc, ticket, grimble node, or rule.
- Per-facet digests and the ack lock (`frob.lock`, `grimble.lock`; `gob-lock`);
  the digest scheme itself is universal-model.md 7.1.
- The directive DSL in comments, markdown, ticket bodies and .grmb files.
- A typed edge graph joining code, docs, tickets, invariants, tests, and
  rules; plus queries (why, affects, query). Grimble entities and `binds`
  edges reach frob only through `grimble --json` (boundaries.md 3.9).
- The universal structural model U that universal rules are written
  against (universal-model.md; section 5 here is a pointer; Milestone 2
  or later (D36)).

It does NOT validate foreign ids (ticket exists, invariant exists). That
join happens in `frob-obligations`, which keeps graph independent of the
ticket store (same cycle-avoidance rule as v1).

## 2. Symbol addresses (symrefs)

Grammar, authoritative here (identity is defined in universal-model.md
2.2 and 2.6). File-based symrefs are unchanged from v1 so directives
port 1:1; the other locator forms are additive:

```
symref   = locator [ "::" qualname ] [ "@" lang ]
locator  = path [ "#" fragment ]       ; path: repo-relative POSIX
fragment = slug                        ; a markdown anchor
         | "cell=" address             ; grid and notebook cells
         | adapter-text                ; adapter-declared locator
qualname = segment { "." segment }     ; "." nests containers
segment  = name [ "[" opaque "]" ]     ; Type[Trait].method, test[case]
         | "{" index "}"               ; anonymous unit: positional index
lang     = identifier                  ; optional explicit tag (rare)
```

Text inside `[...]` is opaque (same parser path as parametrized tests).
The anonymous-unit index `{n}` is computed on the alpha-normal form of
the enclosing unit (universal-model.md 2.6); it needs no new separator
because `#` stays the fragment mark and braces occur in no name. A
multi-part unit (signature plus equations, partial classes, Prolog
clauses) resolves to ONE identity and one symref; that is not the
ambiguity error below, which applies to two distinct identities
claiming one spelling. Open question 2 of universal-model.md (anonymous
identity: positional or content) gates leases and acks for anonymous
units only.

Changes from v1:

- One container model for all grammars: `namespace | type | impl |
  module | function`. Containers always push with "."; v1's Rust
  trait-impl `::` leak and the C++ namespace-free-function METHOD quirk
  are defined away. Impl members address as `Type.method` and, on a
  collision between impls, `Type[Trait].method` (bracket is opaque, same
  parser path as parametrized tests); the impl block itself is
  `Type[impl]` (inherent) or `Type[Trait]`. Every file also has a
  file-level Module node.
- Symbol kinds: `function | method | type | class | const | module |
  field | variant | macro`. v1 collapsed to five; `field`, `variant`,
  `macro`, `module` are added because grimble and rules need them.
- Resolution order is identical to v1 (exact, unique qualname, unique
  suffix; ambiguity is an error with candidates) and is a pure function
  of the snapshot, memoized.
- Symrefs are language-neutral by construction. Nothing above this
  layer needs to know the language of a target; the adapter that parsed
  the file owns that.

Digests: the facet scheme is universal-model.md 7.1 (scheme 2: BLAKE3
over the canonical facet stream, facets `sig | body | doc | attr |
contract`, trivia excluded). Milestone 1 as built is scheme 1 (D43):
three facets `sig | body | doc`, each the BLAKE3 of the facet's
whitespace-collapsed text; that normalization is superseded by D56 for
the facet scheme. Markdown anchors come from ATX headings only; setext
headings are not extracted yet (a known gap). `frob.lock` keeps v1's
shape (entries sorted by ref,facet; append-only ack_log with old/new
digest, reason, actor, date; mandatory non-boilerplate reason).
Locking is endpoint-only; body is always acked alongside sig except
for kinds with no body.

Lock mechanics (`gob-lock`). The file records `digest_scheme` (an
integer, default 1 for a file that predates the field), separate from
`LOCK_VERSION`, which versions only the file format; a scheme change
makes every entry stale (DRIFT, re-ack required) instead of silently
rewriting digests. Entries become typed: `kind = symbol | flow`, with
an optional `attr` facet and, for flow entries, the role (producer,
consumer, contract) and the flow key; `frob.lock` uses `symbol`
entries only, `grimble.lock` uses both. The ack planner moves from
frob-ack to gob-lock (ticket G05) and `LOCK_VERSION` is bumped with a
reader for version 1. Consumer `frob.lock` import (migration.md)
happens only after the scheme is final; this repository's own
`frob.lock` is empty today and is regenerated at that point.

As built (milestone 1, `gob-lock` and `frob-ack`): a lock entry carries
a `targets` vector (the endpoints the ack covers); `frob ack` commits
`frob.lock` on the current branch; DRIFT001 reports one finding per
drifted facet; AFFECT001 fires when a symbol is public (in the
public-API graph), its signature changed since its lock entry, and at
least one dependent lacks a later ack. The facet set that DRIFT001 and
`frob:describes (facet)` enumerate is the scheme's: three facets under
scheme 1, five under scheme 2.

Normalized signature model (new): `Sig { name, params: [(name, Type,
default?)], ret: Type, visibility, async, generics }` where `Type` is a
small cross-language lattice (`int | float | str | bytes | bool | list
of T | map K V | optional T | named(path) | unknown`). Its digest is the
`contract` facet, used for the `binds` edge (section 6) and for
cross-language comparison (SYS006); the `sig` facet stays language-
specific so same-language acks are exact.

## 3. Language adapters

One registry, data-driven, one crate per language family:

```
gob-languages           Language registry, grammar loading, extension dispatch;
                        grammar crates behind features: python, rust, ts
                        (typescript tsx javascript jsx), c-family (c cpp cuda),
                        jvm (java kotlin), dotnet (csharp), misc (zig bash
                        css scss html vue), markdown, toml, actions, dockerfile
gob-ir                  U terms (universal-model.md): sorted ABTs, scope graph with
                        Must/May/Unknown, canonical facet stream, query interface,
                        Kleene evaluator, answer lattice, atom registry; below
                        gob-symbols and linked by frob and grimble (D56);
                        Milestone 2 or later (D36)
gob-symbols             the adapters that produce U terms for Rust and markdown
                        (milestone 1: walkers, container model, symbol addresses,
                        facet digests, publicness, test-shape, adapter capability
                        matrix, imports with confidence, call graph, public-API
                        graph, effect sites; frob needs all of these: AFFECT, COV,
                        touched-set tests, INV forbidden-import, semver)
grimble-model           the .grmb design language (its own parser, no tree-sitter);
                        frob sees .grmb only through `grimble graph --json`
                        (grimble-model.md 9.3)
```

Layering: gob-languages < gob-ir < gob-symbols < gob-directives < the
frob and grimble crates. `Language` is an open registry of inventory
entries, not a closed enum, so an adapter in a later feature (or a
product adapter) registers itself without editing gob-languages.
Milestone 1 (D36) enables the `rust`, `markdown` and `toml` features
only; the Actions and Dockerfile grammars arrive behind features
`actions` and `dockerfile` (cicd.md).

A `LanguageAdapter` provides, as ONE struct of functions (v1 kept these
in five parallel tables that drifted):

| Member | Purpose |
|---|---|
| `extensions` | dispatch by extension (plus shebang fallback) |
| `grammar` | tree-sitter `Language` |
| `walk` | tree -> `Vec<RawSymbol>` + `Vec<RawComment>` using the container model |
| `publicness` | per-language visibility rule |
| `comment_kinds` | node kinds that are comments |
| `imports` | resolved import edges with confidence |
| `test_shape` | is-this-a-test rule (collector token or lexical) |
| `runner` | default test runner template and id spelling |
| `rho` | the signature morphism: concrete tree kinds -> Sigma_U operators plus role attributes, `opaque` as the default clause (universal-model.md 3.1) |
| `bind` | the declared binding discipline producing the scope graph with Must/May/Unknown edges |
| `cap` | which facets, edges and queries this adapter implements: `Implemented`, `NotApplicable(reason)` or `Gap(ticket)` |

The capability matrix is a `const` table checked at compile time where
possible and by a fixture-driven conformance test for every adapter
(each adapter ships `fixtures/*.{ext}` with expected symbols, digests,
U terms, imports: the fidelity corpus of universal-model.md 3.3). A cell can be `Implemented`, `NotApplicable(reason)`, or
`Gap(ticket)`. `frob doctor --languages` prints it, and the generated
languages page (documentation.md section 3) comes from it.

Grammar crates are feature-gated (`--features lang-jvm`) so the default
build and test of one adapter never compiles the others. Partial parses
are salvaged AND reported (PARSE002 keeps firing; Kotlin's silent-zero
case cannot recur because an adapter returning zero symbols from a tree
with ERROR nodes is a conformance failure).

### Packages and project files

A package is the unit that owns files and bounds reach: a Cargo crate (the
directory of the nearest `Cargo.toml`) or a .NET project (the repo-relative
path of the nearest enclosing `.csproj`). `gob-symbols` models .NET projects
in `dotnet.rs` and exposes them through the same `CrateDeps` queries
(`crate_of`, `transitive_deps`, `can_reach`, `extern_crates`), so ownership,
reach and test selection work unchanged.

- A `.sln` lists projects (solution folders are recorded and dropped); a
  `.csproj`, SDK-style or legacy, yields `AssemblyName`, `RootNamespace`,
  `TargetFramework(s)`, `LangVersion`, `ImplicitUsings`, `PackageReference`
  names and `ProjectReference` targets.
- A `.cs` file belongs to the nearest enclosing project directory. SDK-style
  projects compile `**/*.cs` by default (dot directories excluded) and then
  apply `Compile` include, exclude and remove items; legacy projects compile
  only what they list. `bin/` and `obj/` directly under the project are build
  output: such files belong to no project.
- A `ProjectReference` is a package dependency edge; a `.cs` file can only
  reach files in its own project and in projects it references transitively.
  Reach between a .NET file and a Cargo file is never ruled out.
- `ImplicitUsings` plus `<Using>` items yield the project-wide namespaces
  (`CrateDeps::implicit_usings_of`), per SDK (base, Web, Worker), for import
  resolution.
- A malformed `.csproj` or `.sln` is never dropped: `BuildStats` lists it in
  `malformed_projects` with the reason, its project stays Unresolved, and
  reach into or out of it is never ruled out.
- Unity projects (`ProjectSettings/ProjectVersion.txt`, or any `.asmdef`
  above a file) use `unity_project.rs` instead: each `.asmdef` is a package
  (id: its repo-relative path), `references` by name or `GUID:<guid>` (resolved
  through the target's `.asmdef.meta`) are package edges, an `.asmref` adds its
  folder to the assembly it names, and files with no asmdef above them under
  `Assets/` or `Packages/` belong to the virtual packages
  `unity:Assembly-CSharp`, `-Editor`, `-firstpass` and `-Editor-firstpass`.
  `Library`, `Temp`, `obj`, hidden and `~` folders are ignored and so are
  vendored asmdefs outside `Assets/` and `Packages/`. A malformed asmdef, an
  unknown GUID or a dangling `.asmref` is reported in `malformed_projects`
  and leaves the package Unresolved; a name matching no repository assembly
  (engine or registry package) is external, listed on the assembly, not an edge.
- MSBuild conditions are not evaluated, `$(Property)` references in item
  paths are not expanded, and files linked from outside the project
  directory are not assigned.

## 4. The directive DSL

Grammar unchanged: `frob:<verb> <target> [key="value" ...]` in any
comment, where the directive must start a comment line (text before it
on the same comment line makes it prose); markdown HTML-comment form
binding to the preceding heading (markdown comments and inner doc
comments, `//!`, bind to the enclosing section or file);
backslash continuation; `frob:quote(...)` escape; never silently drop a
malformed line.

What changes is how verbs are declared. v1 had a verb table, per-verb
validators, regex tail checks, and at least eight independent
`frob:waive` readers. v2 declares each verb once; the exception verbs
(exceptions.md) replace waive and debt:

```rust
#[derive(Directive)]
#[directive(verb = "defer", surfaces(code, markdown, ticket))]
/// Park one rule's finding at this site until a ticket pays it.
struct Defer {
    #[target] rule: RuleId,
    #[attr(required)] because: Text,
    #[attr(required)] ticket: TicketRef,   // opaque to every product but frob (D28)
    #[attr] until: Option<Until>,          // date | metric target
}
```

`accept` is declared the same way with `because` (an ADR, a style anchor
or one sentence) and no `ticket`; all four exception verbs spell the
reason `because=`; `hotfix` carries `because` and `ticket`; `baseline` is declared in its pool file, never inline.

The derive generates: the parser arm, typed attribute validation and its
error messages, the JSON schema, the generated directives page row
(documentation.md section 3), and the registry entry (via `inventory`).
Surfaces are explicit: `code`, `markdown`, `ticket`, `grimble`.
Ticket-body markers (`no-behavior-change`, `must-still-pass`,
`env-absent`) and reserved markers (`raises`, `callee-raises`,
`used-by`, `secret-fake`) become ordinary directives with a `surface`
and a typed target; no gate parses raw text itself.

Verb set carried from v1 (semantics unchanged): doc, describes(facet),
uses-contract, invariant(+attrs), ticket, todo, deprecated, tests(kind),
enforces, enumerates(members), until, decision. Replaced by the
exception verbs: waive and debt become `accept`, `defer` and `hotfix`.
Added: `binds` (section 6), `node`/`channel`/`boundary`/`effect`
(grimble binding, grimble-model.md), `may` (capability
binding, section 7), and the milestone-2 claim verbs below. Namespace
ownership: the parser in `gob-directives` is namespace-parametric and
one registry holds every verb; a verb is namespaced by what it says,
and a product evaluates only the verbs its rules consume. The binding
and capability verbs describe the model and are written `grimble:binds`,
`grimble:node`, `grimble:channel`, `grimble:effect` (frob never parses
them, D28); accounting verbs stay `frob:ticket`, `frob:doc`,
`frob:tests`; crunk has `crunk:accept` and `crunk:defer`. The claim
verbs describe work accounting and claims about code that the owner
makes, so they are in the `frob:` namespace, but their consumer is the
NEAT family in grimble-lints, which reads them through the shared
gob-directives registry; grimble ignores `frob:ticket`, `frob:doc` and
the other accounting verbs.

Milestone-2 directives (none is parsed in milestone 1; DSL001 flags
them until their milestone):

| Verb | Surface | Target | Meaning | Evaluated by |
|---|---|---|---|---|
| `frob:effects <set>` | code | unit | the owner's effect claim; the set is `none`, `honest`, `io`, `any` or a list of atoms from neatness.md 3 (`reads(X)`, `writes(Y)`, `clock`, `rng`, `env`, `fs`, `net`, `stdio`, `exit`, `panic`, `diverge`, optional `total`), atoms resolving through the shared registry (grimble-model.md 9.6) | NEAT rules (grimble-lints) |
| `frob:pure`, `frob:honest` | code | unit | aliases of `frob:effects none` and `frob:effects honest` | NEAT |
| `frob:core`, `frob:shell` | code | unit | functional-core or imperative-shell marker | NEAT |
| `frob:hook [kind]` | code | unit | framework entry point, subject to the thin-hook rule | NEAT030 |
| `frob:dispatcher` | code | unit | intentional dispatcher; opts out of NEAT031 | NEAT031 |
| `frob:idempotent` | code | unit | a claim discharged only by bound evidence: a passing `frob:tests` binding of kind `idempotent` (a test that applies the unit twice); unbound it is unverified (Unresolved) | NEAT and frob-evidence |
| `frob:trusted` | code | unit | an unverified claim the owner owns; never counted as verified | NEAT |
| `frob:calls <symref>...` | code | call site | declares the targets of a dynamic call (May precision) | gob-ir resolution, every product |

Ticket ids in `frob:ticket`, `frob:todo` and
`ticket=` are full ULIDs: a fixer expands a `~handle`, a TICK rule flags
an abbreviation, and v1 `T-0042` aliases are accepted by the parser and
resolve through the `aliases` field the importer sets on a ticket (REF001
names an alias no ticket carries) until `frob migrate directives` rewrites
them. The parser's DSL002 flags every other abbreviated id with the remedy
`frob ticket expand`. The `[directives] namespaces` knob is a `ConfigTable`
(gob-directives `DirectivesConfig`, default namespaces `frob`, `grimble`,
`crunk`); frob-check, frob-ack and frob-obligations still scan with
`ScanConfig::default()` (frob only) until grimble and crunk register verbs. Milestone 1 (D36) parses the `frob:`
namespace only; `grimble:` and `crunk:` are Milestone 2 or later (D36).
Dropped unless a consumer commits: protocol/transition/requires/acquire/
release/escapes (typestate DSL), scaffold managed-block markers (dropped
with the scaffold feature, boundaries.md 2.6).

Carried unchanged from v1 (notes/v1/graph-lang-dsl.md section 8.1): a
per-file size cap and parse timeout (a file over either yields a PARSE
finding, never a hang); and the canonical reorientation of `frob:tests`
edges.

Binding order (Rust): a directive binds to the symbol that follows its
directive block in preference to the enclosing symbol. The block is the
directive's own line plus the lines after it that are directives, ordinary
or doc comments, or attributes (also multi-line ones); the item may start on
the first line after that run. Every directive in a stacked block binds to
the same item, so several `frob:tests` lines above one `#[test]` all bind. A
blank line ends the block: the directive then binds to its enclosing symbol,
else to the file. A `frob:tests` directive that attaches to no item is
reported as PARSE001 ("directive is not attached to an item: put it directly
above the function or heading it describes") rather than as an unknown
symref. Markdown HTML comments bind to the heading section that contains
them (the preceding heading), so stacked comments agree by construction.

Inert text (D91, ~JTV288R). Two things never yield directives. (1) The
ticket ledger tree, the configured `[tickets] dir`, is data written through
the ledger write path: gob-walk classifies every path once into a `FileRole`
(`Source` or `Ledger`, `gob_walk::Roles`), and directive and comment scanning
skips `Ledger` files, so a `frob:waive` quoted in an imported ticket body or
event is text. Ledger rules (TICK, PM, privacy) read the ledger directly and
still apply; the `ticket`-surface markers of a ticket body are read by the
ledger, not by the file scanner. (2) In any markdown file only HTML comments
outside code are directives: prose, code spans and fences, and a leading
`---` (YAML) or `+++` (TOML) front matter block are never scanned, because
front matter is data in another language.

## 5. Structural IR (pointer)

Superseded by D56. The structural model that universal rules are
written against is universal-model.md: sections 2-3 define the
operators (Sigma_U), the scope graph and the adapter contract
(`rho`, `bind`, `cap`), section 4 the answer lattice and polarity, and
section 5 the query interface. There is no closed node-kind enum; a loop, branch or
call is a role attribute on a `group`, `bind` or `apply` node, and an
unmapped construct is an `opaque` node with a reason, never a silent
catch-all. U terms are built lazily per file in `gob-ir` and cached
with the parse artifact (section 8). Level-2 rule syntax is in rules.md
section 3; the ast-grep engine status is stated once there.
Milestone 2 or later (D36).

## 6. Cross-language symbolic binding

New first-class edge kind `binds(a, b, via)`, resolved in
`grimble-bind`. It is inferred from binding attributes and stubs
(`#[pyfunction]`, `.pyi`, `wasm_bindgen`, ...); the directive is written
only for `manual` bindings or to override an inference:

```
// grimble:binds crates/kernel/src/lib.rs::closure via="manual"
```
Milestone 2 or later (D36).

Semantics: symbol `a` (where the directive sits) is the same logical
interface as symbol `b` across a language boundary. Per-`via` adapters
(`pyo3`, `pybind11`, `ctypes`, `wasm-bindgen`, `jni`, `napi`, `manual`)
extract both sides' `contract` facet (the normalized `Sig`) and compare
arity, names, and the type lattice; mismatch is `BIND001`, missing counterpart `BIND002`.
This replaces v1's `frob bind` regex, FFI001 pyi scanning, and the pyi
docstring pragma. `affects`, drift, and test-evidence reach traverse
`binds` edges, so a Python test bound to a Rust symbol through PyO3 is
a reached (Must) edge rather than an Unknown one when the call graph crosses a binds edge.
frob traverses `binds` edges only through the edge list in `grimble
--json` and reports Unresolved when grimble is absent.

Call graph: one resolver, import-verified by default. One edge-status
vocabulary across the design set: `Must | May | Unknown`
(universal-model.md 2.2). The landed gob-symbols variants map as
`Resolved` to Must, `Ambiguous` to May (the candidates), `Unresolved`
to Unknown; the earlier `Certain | ImportVerified | NameOnly`
confidences map to Must, Must and May. Public callees are real edges
(v1 omitted them, which caused the COV006 false positives). Bounded BFS
for closure and affects as in v1. A selection built from this graph
(`check --ticket`, `frob test`) is a lower bound whenever an Unknown
edge leaves a touched symbol: the run reports one Unresolved
("selection incomplete: N unresolved call sites") and widens to the
file's crate (rules.md section 4, build-test-ci.md).

## 7. Capability binding and the matrix

Capabilities are atoms in one open registry, not a closed Rust enum:
the atom registry and the per-language callee vocabularies live in
`gob-ir` as inventory entries (data packs add atoms through the same
registry with a pack-qualified id such as `pii.collect`), and atoms are
hierarchical (`fs` covers `fs.read` and `fs.write`). The `Capability`
derive in `grimble-capabilities` documents an atom and gives it an id:

```rust
#[derive(Capability)]
#[capability(family = "fs", mode = "write")]
/// Writes to the filesystem outside the repo's own cache dir.
struct FsWrite;
```

Each language adapter contributes detectors (queries over U, callee
vocabulary rows, attributes, pack-declared patterns, or declarative
rule files per rules.md section 3) that attribute atoms to symbols. A
grimble node binds to symbols (grimble-model.md) and declares
`may fs.write;` for what it needs. The matrix is nodes x capabilities.
The cell set (uses, undeclared, declared-unused, denied,
excused, not-applicable, unknown), the detector row schema, the registry and
the Unresolved accounting are defined once in grimble-model.md 9.6;
this section does not restate them.

Capabilities are denied by default (D75): a node's ungranted atom is
denied and its observed use is CAP001; a blank cell means denied. The v1
practice of waiving irrelevant capabilities with a reason is no longer a
node clause; it survives only as a matrix-build template excuse (grmb-spec
4.7, packs.md 6.7) that shapes how an atom applies to a kind of code, and
an excuse never masks an observed use (CAP004). Scaling: a new atom
needs one registry entry and detectors in the adapters that can
observe it; until a detector exists the cell is `unknown` (reported,
never clean), and once a detector ships its first ungranted use is
CAP001 at the pack's per-atom severity (a pack may ship a new atom at a
lower severity for one release, packs.md 4.4); `grimble check --census
capabilities` lists which cells changed. The finding ids and their
conditions are the one table in grimble-model.md section 4. Milestone 2
or later (D36).

## 8. Graph storage and incrementality

- Parse artifacts (symbols, comments, U terms, imports) keyed by
  `(blake3(file), adapter_id, grammar_version, schema_version,
  compute_config_digest)` in the
  SQLite file of the worktree (`.frob/cache.sqlite`) through `gob-cache`
  (`rusqlite` bundled, WAL readers, `busy_timeout`). The adapter_id is
  the crate version plus a build hash, so a stale parser cannot yield a
  fresh key. The compute-config digest hashes the `[compute]` table,
  because flipping a key (for example `public_signatures`) changes which
  nodes are opaque; the scope graph is a repository-scope artifact keyed
  by the graph digest, because resolution crosses files.
- Per-file findings are persisted keyed by (file digest, rule id, rule
  version, side-input digest); repo-scope findings add a graph digest
  (architecture.md section 2). Writes happen from the command layer
  after queries return, are best-effort, and a failed write is a logged
  miss, never an error.
- Assembling the snapshot in milestone 1 is plain parallel functions over those
  memo tables. From milestone 2 it is a salsa query graph (`salsa` 0.28,
  `gob-db`): file digest -> parsed artifact -> edges -> resolved graph ->
  per-rule findings, so `frob check` on a one-file change re-derives
  only the dependents. Milestone 2 or later (D36).
- Parallel parse with `rayon` (architecture.md section 9); one process;
  no derived-state lock dance across worker processes (v1's deadlock
  class disappears).
- Typed endpoints: `Endpoint = Symbol | Doc | Ticket | Invariant |
  Rule | GrimbleEntity | Capability | Text`. A `GrimbleEntity` is opaque
  to frob and resolved only through `grimble --json`. No more "which
  kind of string is this" parsing downstream.

## 9. Queries kept

`graph query|affects` and `explore outline|map|xref|docs` are thin
views over the snapshot exposed by both frob and grimble; `frob graph
why` and `frob ack` (frob-ack) are frob only, semantics unchanged.
Rename candidates (same body digest, same qualname) carried over.

## 10. Open questions

Decided 2026-10-02: `describes` keeps facet selection; `binds` is
inferred from binding attributes and stubs with the directive only for
`manual` or to override; the human symref grammar is canonical and a
SCIP-shaped id is derived for export and import.
