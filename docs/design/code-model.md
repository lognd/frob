# Code model, symbolic binding, and the directive DSL

Status: DRAFT (T-0001, a v1-format id that migrates with an alias).
Ownership after products.md: sections 1-4 and 8-9 are `gob-symbols`,
`gob-directives` and `gob-cache` (shared by all three products);
sections 5-7 (IR, binds, capability matrix) are `gob-ir` plus grimble
crates (boundaries.md) and are Milestone 2 or later (D36). Inputs:
notes/v1/graph-lang-dsl.md, the universal-binding requirement in
goals.md, notes/rust-ecosystem.md.

## 1. What this layer owns

- Parsing every supported language into one normalized code model.
- Symbol identity (addresses) that are stable across formatting, usable
  from any language, doc, ticket, grimble node, or rule.
- Per-facet digests and the ack lock (`frob.lock`, `grimble.lock`; `gob-lock`).
- The directive DSL in comments, markdown, ticket bodies and .grmb files.
- A typed edge graph joining code, docs, tickets, invariants, tests, and
  rules; plus queries (why, affects, query). Grimble entities and `binds`
  edges reach frob only through `grimble --json` (boundaries.md 3.9).
- The structural IR that universal rules are written against (section 5;
  Milestone 2 or later (D36)).

It does NOT validate foreign ids (ticket exists, invariant exists). That
join happens in `frob-obligations`, which keeps graph independent of the
ticket store (same cycle-avoidance rule as v1).

## 2. Symbol addresses (symrefs)

Grammar, unchanged in spirit from v1 so directives port 1:1:

```
<path>                       whole file, repo-relative POSIX
<path>::<Qual>.<Name>        a symbol; "." nests containers
<path>#<slug>                a markdown anchor
<path>::<Qual>.<Name>[case]  parametrized test; bracket text is opaque
<path>::<Qual>.<Name>@<lang> optional explicit language tag (rare)
```

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

Digests: three facets `sig | body | doc`, each the BLAKE3 of the
facet's whitespace-collapsed text (milestone 1; not NUL-joined leaf
tokens, so a reformat does not change a digest while a token change
does). Markdown anchors come from ATX headings only; setext headings
are not extracted yet (a known gap). `frob.lock` keeps v1's shape (entries sorted by ref,facet; append-
only ack_log with old/new digest, reason, actor, date; mandatory non-
boilerplate reason). Locking is endpoint-only; body is always acked
alongside sig except for kinds with no body. As built (milestone 1,
`gob-lock` and `frob-ack`): a lock entry carries a `targets` vector (the
endpoints the ack covers); `frob ack` commits `frob.lock` on the current
branch; DRIFT001 reports one finding per drifted facet; AFFECT001 fires
when a symbol is public (in the public-API graph), its signature changed
since its lock entry, and at least one dependent lacks a later ack.

Normalized signature model (new): `Sig { name, params: [(name, Type,
default?)], ret: Type, visibility, async, generics }` where `Type` is a
small cross-language lattice (`int | float | str | bytes | bool | list
of T | map K V | optional T | named(path) | unknown`). Used for the
`binds` edge (section 6) and for cross-language sig comparison; never
used for digests, so acks stay stable.

## 3. Language adapters

One registry, data-driven, one crate per language family:

```
gob-languages           Language enum, grammar loading, extension dispatch;
                        grammar crates behind features: python, rust, ts
                        (typescript tsx javascript jsx), c-family (c cpp cuda),
                        jvm (java kotlin), dotnet (csharp), misc (zig bash
                        css scss html vue), markdown, toml
gob-symbols             walkers, container model, symbol addresses, three-facet
                        digests, publicness, test-shape, adapter capability matrix,
                        imports with confidence, call graph, public-API graph,
                        effect sites (frob needs all of these: AFFECT, COV,
                        touched-set tests, INV forbidden-import, semver)
gob-ir                  structural IR only (IrNode, IrKind, ir_map); needed by
                        grimble, frob builds without it; Milestone 2 or later (D36)
grimble-model           the .grmb design language (its own parser, no tree-sitter)
```

Milestone 1 (D36) enables the `rust`, `markdown` and `toml` features only.

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
| `ir_map` | tree-sitter node kinds -> structural IR node kinds (section 5) |
| `capabilities` | which facets/edges this adapter implements, N/A with reason, or known gap |

The capability matrix is a `const` table checked at compile time where
possible and by a fixture-driven conformance test for every adapter
(each adapter ships `fixtures/*.{ext}` with expected symbols, digests,
IR, imports). A cell can be `Implemented`, `NotApplicable(reason)`, or
`Gap(ticket)`. `frob doctor --languages` prints it, and the generated
languages page (documentation.md section 3) comes from it.

Grammar crates are feature-gated (`--features lang-jvm`) so the default
build and test of one adapter never compiles the others. Partial parses
are salvaged AND reported (PARSE002 keeps firing; Kotlin's silent-zero
case cannot recur because an adapter returning zero symbols from a tree
with ERROR nodes is a conformance failure).

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
(grimble binding, grimble-model.md), `may`/`excuses` (capability
binding, section 7). Namespace ownership: the parser in `gob-directives`
is namespace-parametric; a verb belongs to the product that consumes it,
so the binding and capability verbs are written `grimble:binds`,
`grimble:node`, `grimble:channel`, `grimble:effect`, while accounting
verbs stay `frob:ticket`, `frob:doc`, `frob:tests`, and crunk has
`crunk:accept` and `crunk:defer`. A product never parses another
product's namespace. Ticket ids in `frob:ticket`, `frob:todo` and
`ticket=` are full ULIDs: a fixer expands a `~handle`, a TICK rule flags
an abbreviation, and v1 `T-0042` aliases resolve until `frob migrate
directives` rewrites them. In milestone 1 the parser's DSL002 flags any
abbreviated id, including a v1 `T-####`, with the remedy `frob ticket
expand`. The `[directives] namespaces` knob is not yet a `ConfigTable`
(Milestone 2 note); milestone 1 hard-codes the `frob` namespace. Milestone 1 (D36) parses the `frob:`
namespace only; `grimble:` and `crunk:` are Milestone 2 or later (D36).
Dropped unless a consumer commits: protocol/transition/requires/acquire/
release/escapes (typestate DSL), scaffold managed-block markers (dropped
with the scaffold feature, boundaries.md 2.6).

Carried unchanged from v1 (notes/v1/graph-lang-dsl.md section 8.1): a
per-file size cap and parse timeout (a file over either yields a PARSE
finding, never a hang); a directive binds to the symbol that follows it
within 2 lines in preference to the enclosing symbol; and the canonical
reorientation of `frob:tests` edges.

## 5. Structural IR (what universal rules see)

A thin, lossless-enough normalization over tree-sitter trees so a rule
such as "sort call inside a loop" is written once:

```
IrNode { kind: IrKind, span, children, lang, ts_kind, text_slice }
IrKind = Module | Function | Class | Block | Loop{kind} | Branch |
         Call{callee: Path, args} | Assign | Return | Try | Lambda |
         Literal{kind} | Name | Attribute | Import | Comment | Other
```

Each adapter supplies `ir_map` (tree-sitter kind -> IrKind, plus how to
find callee/args). Unmapped kinds become `Other` and keep `ts_kind`, so
language-specific rules can still match exactly. Universal rules query
the IR with a small matcher (ancestor/descendant/sibling, kind, callee
name sets, arity) and a per-language "callee vocabulary" table (what
`sort` is called in Python, Rust, JS, Java...). Language-specific
rules use tree-sitter queries (`.scm`) or ast-grep style patterns
directly against the raw tree (`ast-grep-core` as the pattern engine,
decided pending a spike ticket that unifies its tree-sitter version with
the workspace pin and proves an IR adapter for its `Doc` trait; until
then the IR matcher is our own small one).

The IR is built lazily per file (in `gob-ir`) and cached with the
parse artifact under the same key. Universal and language rules that
consume it live in `grimble-lints` (boundaries.md). Milestone 2 or later
(D36).

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
extract both sides' normalized `Sig` and compare arity, names, and
the type lattice; mismatch is `BIND001`, missing counterpart `BIND002`.
This replaces v1's `frob bind` regex, FFI001 pyi scanning, and the pyi
docstring pragma. `affects`, drift, and test-evidence reach traverse
`binds` edges, so a Python test bound to a Rust symbol through PyO3 is
REACHES rather than UNKNOWN when the call graph crosses a binds edge.
frob traverses `binds` edges only through the edge list in `grimble
--json` and reports Unresolved when grimble is absent.

Call graph: one resolver, import-verified by default, every edge
carrying confidence `Certain | ImportVerified | NameOnly`. Public
callees are real edges (v1 omitted them, which caused the COV006 false
positives). Bounded BFS for closure and affects as in v1.

## 7. Capability binding and the matrix

Capabilities (crate `grimble-capabilities`) are a closed, extensible
set of atoms declared in Rust:

```rust
#[derive(Capability)]
#[capability(family = "fs", mode = "write")]
/// Writes to the filesystem outside the repo's own cache dir.
struct FsWrite;
```

Each language adapter contributes detectors (IR patterns or tree-sitter
queries, or declarative rule files per rules.md section 3) that
attribute capability atoms to symbols. A grimble node binds
to symbols (grimble-model.md) and declares `may fs.write;` for what it needs.
The matrix is nodes x capabilities:

| Cell value | Meaning |
|---|---|
| `uses` | detector found it and the node declares it: fine |
| `undeclared` | detector found it, node did not declare: CAP001 (alias CAP-EXCEEDS), Error |
| `declared-unused` | declared, never observed: CAP002 (alias CAP-STALE), Warn, shrink-only fix |
| `excused(reason)` | node explicitly excludes it with a reason (`excuses net.connect reason="offline tool"`) |
| `n/a` | the node's languages have no detector for this atom (adapter matrix says NotApplicable); reported as one Unresolved per node in the summary, never as a clean cell and never as an error |
| (applicable, neither granted nor excused) | CAP003 (alias CAP-UNEXCUSED); a newly shipped atom's CAP003 starts as Advisory for one release through the baseline kind |

The v1 practice the user liked, waiving irrelevant capabilities with a
reason, is kept as `excuses`. Scaling: a new capability atom needs one
Rust item and detectors in the adapters that can observe it; nodes see
it as `n/a` until a detector exists, and once a detector ships its
CAP003 is Advisory for one release, so nothing breaks repo-wide on day
one; `grimble check --census capabilities` lists which cells changed.
The finding ids and their conditions are the one table in
grimble-model.md section 4. Milestone 2 or later (D36).

## 8. Graph storage and incrementality

- Parse artifacts (symbols, comments, IR, imports) keyed by
  `(blake3(file), adapter_id, grammar_version, schema_version)` in the
  SQLite file of the worktree (`.frob/cache.sqlite`) through `gob-cache`
  (`rusqlite` bundled, WAL readers, `busy_timeout`). The adapter_id is
  the crate version plus a build hash, so a stale parser cannot yield a
  fresh key.
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
