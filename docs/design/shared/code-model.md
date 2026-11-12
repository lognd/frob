# Code model, symbolic binding, and the directive DSL

Status: current
Owner: gob
Decisions: D5, D43, D44, D49, D91, D96, D101, D94
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias).
Ownership after charter.md: sections 1-4 and 8-9 are `gob-symbols`,
`gob-directives` and `gob-cache` (shared by all three products);
section 5 is now a pointer to universal-model.md (`gob-ir`), and
sections 6-7 (binds, capability matrix) are grimble crates
(charter.md); all of them are Milestone 2 or later (D36). Inputs:
notes/v1/graph-lang-dsl.md, the universal-binding requirement in
charter.md, notes/research/rust-ecosystem.md.

## 1. What this layer owns

- Parsing every supported language into one normalized code model.
- Symbol identity (addresses) that are stable across formatting, usable
  from any language, doc, ticket, grimble node, or rule.
- Per-facet digests and the ack lock (`frob.lock`, `grimble.lock`; `gob-lock`);
  the digest scheme itself is universal-model.md 7.1.
- The directive DSL in comments, markdown, ticket bodies and .grmb files.
- A typed edge graph joining code, docs, tickets, invariants, tests, and
  rules; plus queries (why, affects, query). Grimble entities and `binds`
  edges reach frob only through `grimble --json` (charter.md 4.3.9).
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

### 2.1 Document anchors in `ref` (grimble/grmb-spec.md 4.5.1)

Moved here from grimble/grmb-spec.md 4.5.1; the grmb spec keeps a pointer. Section numbers below without a file name are grimble/grmb-spec.md sections.

A `ref` to a document is `PATH#ANCHOR` (the legacy spelling) or
`PATH::ANCHOR`; both name the same markdown unit. An ANCHOR is one of
three things, all in ONE namespace per document:

1. A heading slug. GitHub rules, the ones `gob-symbols` applies
   (`slugify`): lowercase; keep letters, digits, `-` and `_`; each space
   becomes `-`; every other character is dropped (so `&`, `/`, `.`, `(`
   and `:` vanish and the spaces around them stay, giving `--` for
   ` & `); link syntax keeps only its text. A code span keeps its CONTENT
   and loses only its backticks: the heading ``## The `foo.bar` API`` is
   `the-foobar-api` (the `.` is punctuation and is dropped), and
   ``## `a & b` ``  is `a--b`. A repeated slug in one file gets `-1`,
   `-2` in document order; the first keeps the bare slug. A heading whose
   slug is empty has no anchor.
2. An explicit anchor `{#ID}` at the end of a heading line, as in
   ``## `a & b` {#ab-pair}``. ID matches `[A-Za-z0-9_-]+`, is taken
   verbatim (no lowercasing, no suffixing), and REPLACES the heading's
   slug: the slug is then no anchor of that heading. Two explicit anchors
   with one ID in a file, or an ID equal to another anchor, are an
   ambiguous ref (SYS003 `ambiguous-singleton`), never silently the first.
3. A table-row id. In a markdown table the first cell of a body row is
   the row's id when it is a single token, bare or in one code span
   (``| `R-12` | ... |``, `| R-12 | ... |`). The anchor is that token
   slugged by rule 1 (`R-12` is `r-12`), or the ID of a trailing `{#ID}`
   in the same cell. A first cell of several words is not an id. Header
   and separator rows have no id. Row anchors are scoped to the document,
   not to the enclosing heading, and duplicate with rule 1's `-N`
   suffixing in document order.

An author who needs a ref that survives heading edits and reordering
uses rule 2, since slugs and `-N` suffixes move with the text. A `ref` with an
empty ANCHOR (`doc.md#`), more than one `#`, or an ANCHOR containing
whitespace or `{`, `}` is malformed and is MDL014 at load; a well-formed
anchor that matches no unit is SYS011 (grimble/binding.md 6.11), and one that
matches several is SYS003 `ambiguous-singleton`.

Status: the shipped adapter implements rule 1 only (headings, with code
spans, `&` and links handled as above); table-row ids, explicit `{#ID}`
and the malformed-ref finding are specified here and follow in ticket
~ADSY7K8.

### 2.2 Runner ids and the selectors that name them (grimble/grmb-spec.md 4.5.3)

Moved here from grimble/grmb-spec.md 4.5.3; the grmb spec keeps a pointer. Section numbers below without a file name are grimble/grmb-spec.md sections, except "section 2" which is this file.

A literal `verified_by` (or `runnable`) selector is `FILE::QUALNAME` (6.2); a runner reports a
different identifier, so the spec fixes how each maps. The segment text
of QUALNAME follows the unit qualnames of docs/design/shared/code-model.md section 2; a
segment holding characters outside a name (spaces, `>`, `/`) is written
in brackets, `[..]`, verbatim.

| Runner | Runner id | Selector | Rule |
|---|---|---|---|
| pytest | `tests/t.py::TestA::test_b` | `tests/t.py::TestA.test_b` | `::` after the file becomes `::`, further `::` become `.`; a parametrized suffix `[p]` is dropped |
| cargo test, integration | `--test check_verb error_finding` | `crates/frob/tests/check_verb.rs::error_finding` | `--test NAME` is the file `tests/NAME.rs` of the crate; the filter is the fn name |
| cargo test, in-source | `frob_check::tests::it_works` | `crates/frob-check/src/lib.rs::tests.it_works` | the module path after the crate name becomes dotted segments, and the FILE is the one that declares the module; the crate name is never in the qualname |
| vitest / jest | `web/e2e/gate.test.ts > gate > shows exit state` | `web/e2e/gate.test.ts::[gate > shows exit state]` | the file path, then the `describe` chain and the `it` or `test` title as ONE bracketed segment, joined by ` > `, titles verbatim |

The runner id is the human-facing key; the selector is the model-facing
one. The adapter query `test_items` (Q35) returns each test unit with
its runner id, so a tool can print the runner id for a selector and
accept a pasted runner id where a selector is expected (it is mapped by
this table, then resolved by Q22).

Recognition. A unit is a test unit when the language adapter says so;
the location is a hint, never the rule:

| Language | A test unit is |
|---|---|
| Rust | a `fn` carrying `#[test]` or a path ending `::test` (`#[tokio::test]`), anywhere: in `tests/`, or in a `#[cfg(test)] mod` inside `src/` |
| Python | a `test_*` function or method, or a `Test*` class member, in `test_*.py`, `*_test.py` or under a `tests` directory |
| TypeScript, JavaScript | an `it` or `test` call (including `.each`) in a `*.test.*`, `*.spec.*` file or under `__tests__` |

A unit in a file or module that matches none of these is not a test unit,
so a `verified_by` naming it is SYS011 `selects no test unit`.

Status: the shipped stand-in (`is_test_unit` in `grimble-bind`) is
path-and-qualname based: a path under `tests/`, a `*_test` or `test_*`
file stem, or a `test`/`tests` qualname segment. It covers Rust
in-source `mod tests` and Python, not TypeScript titles, `#[test]` fns
outside those places. A bracketed segment (a vitest/jest title) is a test
unit, and `FILE::[describe > title]` binds by scanning the file's
`describe`/`it`/`test` calls (`gob_languages::js_test_ids`; `.only` and
`.skip` count, `.each` and dynamic titles do not). A `verified_by` that names a
wrong id in an existing file is SYS011 and the message ends with
`; nearest real id: ...` when a real id is close. The real Q35 answer and
the pasted-runner-id mapping remain future work.

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
gob-symbols             the adapters that produce U terms for Rust, markdown, Python,
                        TypeScript, CSS and C# (conformance fixtures under
                        tests/corpus/csharp: a .NET solution and a Unity project)
                        (milestone 1: walkers, container model, symbol addresses,
                        facet digests, publicness, test-shape, adapter capability
                        matrix, imports with confidence, call graph, public-API
                        graph, effect sites; frob needs all of these: AFFECT, COV,
                        touched-set tests, INV forbidden-import, semver)
grimble-model           the .grmb design language (its own parser, no tree-sitter);
                        frob sees .grmb only through `grimble graph --json`
                        (grimble/grmb-spec.md section 20.2)
```

Layering: gob-languages < gob-ir < gob-symbols < gob-directives < the
frob and grimble crates. `Language` is an open registry of inventory
entries, not a closed enum, so an adapter in a later feature (or a
product adapter) registers itself without editing gob-languages.
Milestone 1 (D36) enables the `rust`, `markdown` and `toml` features
only; the Actions and Dockerfile grammars arrive behind features
`actions` and `dockerfile` (rule-families.md section 3).

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
languages page (notes/research/documentation.md section 3) comes from it.

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
(rules.md) replace waive and debt:

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
(notes/research/documentation.md section 3), and the registry entry (via `inventory`).
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
(grimble binding, docs/design/grimble/grmb-spec.md section 20), `may` (capability
binding, section 7), and the milestone-2 claim verbs below. Namespace
ownership: the parser in `gob-directives` is namespace-parametric and
one registry holds every verb; a verb is namespaced by what it says,
and a product evaluates only the verbs its rules consume. The binding
and capability verbs describe the model and are written `grimble:binds`,
`grimble:node`, `grimble:channel`, `grimble:boundary` (frob never parses
them, D28); accounting verbs stay `frob:ticket`, `frob:doc`,
`frob:tests`; crunk has `crunk:accept` and `crunk:defer`. Claim verbs (effects,
roles, dynamic call targets) are claims about the design of code and are
`grimble:` verbs: a directive is namespaced by its consumer (D120,
rule-families.md section 2.4), and frob never consumes them. They are read
through the shared gob-directives registry; grimble ignores `frob:ticket`,
`frob:doc` and the other accounting verbs. Every directive must pass the
admission tests of rule-families.md 2.4 (not derivable, not an exception in
disguise, consumed by two rules or verified).

Milestone-2 directives (none is parsed in milestone 1; DSL001 flags
them until their milestone):

| Verb | Surface | Target | Meaning | Evaluated by |
|---|---|---|---|---|
| `grimble:effects <set> [because "..."]` | code | unit or model node | the owner's effect claim; the set is `none`, `honest`, `io`, `any` or a list of atoms from rule-families.md 1.2 (`reads(X)`, `writes(Y)`, `clock`, `rng`, `env`, `fs`, `net`, `stdio`, `exit`, `panic`, `diverge`, optional `total`), atoms resolving through the shared registry (docs/design/grimble/binding.md section 7); the single spelling that merges the former frob effects and grimble effect verbs (D120) | NEAT rules (grimble-lints) |
| `grimble:core`, `grimble:shell` | code | unit | functional-core or imperative-shell role claim, verified by the effects rules | NEAT014-016, COH002 |
| `grimble:calls <symref>...` | code | call site | declares the targets of a dynamic call (May precision) | gob-ir resolution, every product |

Dropped by D120: the pure and honest aliases (spell `grimble:effects none`
or `honest`), the hook marker (inferred from gob-frameworks; bridge a gap
with `accept` on NEAT030), the dispatcher marker (`accept` on NEAT031),
the trusted marker (`accept` on the UNVERIFIED finding) and the
idempotent marker (the `frob:tests` binding of kind `idempotent` already
states it). Old spellings parse for one minor release with a DSL
deprecation finding and an automatic fix.

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
with the scaffold feature, charter.md 4.2.6).

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

Moved to [grimble/binding.md](../grimble/binding.md) section 15 (the `binds(a, b, via)`
edge, BIND001 and BIND002, and the Must/May/Unknown call-graph vocabulary
with the "selection incomplete" rule).

## 7. Capability binding and the matrix

Moved to [grimble/binding.md](../grimble/binding.md) section 7 (the cell set and the
matrix as a view over B, the atom registry and detectors in 7.5, and the
lexical directive scan for files with no grammar in 7.6).

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
  (docs/design/shared/architecture.md section 2). Writes happen from the command layer
  after queries return, are best-effort, and a failed write is a logged
  miss, never an error.
- Assembling the snapshot in milestone 1 is plain parallel functions over those
  memo tables. From milestone 2 it is a salsa query graph (`salsa` 0.28,
  `gob-db`): file digest -> parsed artifact -> edges -> resolved graph ->
  per-rule findings, so `frob check` on a one-file change re-derives
  only the dependents. Milestone 2 or later (D36).
- Parallel parse with `rayon` (docs/design/shared/architecture.md section 1.9); one process;
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

## 11. The U encoding of .grmb

Moved here from docs/design/grimble/grmb-spec.md section 9 and 10; subsection numbers are kept so
existing citations ("grmb-spec 9.2") still resolve by number.

`grimble-model` owns the adapter A_grmb = (parse, rho, bind, cap) with
the fidelity F4 (universal-model.md 3.3): units and roles, a scope graph
with Must edges for every reference, attributes, comments bound to
targets. It is total (Theorem 1): invalid input yields `hole` and
`opaque`, never a refusal.

### 9.1 Locations

A location is `text(artifact, byte range)` with an ANCHOR: the logical
location `kind/full-name` for entities (`node/cli`), and
`kind/full-name/clause-key[i]` for the i-th clause of that key
(`node/cli/owns[0]`). The anchors are the stable addresses findings,
`design:` ticket links and the sibling JSON use; byte ranges are the
spans (every construct has one: the v1 regex-located spans are gone).
The artifact is the repo-relative path of the file.

### 9.2 Encoding table

Language tag `grmb`; language parameter `grimble="2"` (the edition) on
every node. S = sort of the produced node.

Placement inside an entity unit (this fixes which facet a clause lands
in; the facet table below is derived from it, and gob-ir classifies a
child by this placement alone):

- Sig parts are direct children of the unit marked `ir.facet = "sig"`:
  the trust attr, the flow `connect` apply, the boundary `endorse` or
  `declassify` apply, the vmodel `kind` and `level` attrs, and the
  `label`, `producer`, `consumer`, `contract`, `shape` and `versioning`
  clauses.
- Body parts are every other clause (`owns`, `surface`, `may`,
  `clearance`, the other flow fields, claim and vmodel
  clauses, links, pack clauses, `alias`, `renamed_from`), all inside one
  `group(unordered)` child of the unit. `attr(name=owns)` and its
  siblings therefore sit in that group, not directly under the unit.
- Attr parts are the `attr K` clauses and the exception clauses
  (`accept`, `defer`, `hotfix`), left as direct children of the unit;
  gob-ir classifies every `attr` child that is not `doc` and not a sig
  part as Attr.
- Doc is the `attr(name=doc)` child; comments are trivia.
- The Contract facet is not a separate placement: it is the Sig parts
  with names erased.

| Construct | U term | Sort | Notes |
|---|---|---|---|
| file | `unit(kind=module)` with body `group(unordered)(items)` | decl | the file-level Module unit every file has |
| `grimble = "2";` | `attr(name=grimble-version)(file unit; lit(string, "2"))` | decl | also the language parameter |
| `module X;` / `part of X;` | `attr(name=module)(file unit; lit(ident, X))` | decl | the model name; a pack's `module` and `part of` attrs use the same `attr(name=module)` (D73) |
| `use "p" ...;` (or `include "p"`) | `apply(kind=include)(ref("p"))` (U KIND names of units and applies are frozen and do not follow surface renames, D178; the attr NAMES of clauses respelled in cycles 1-3 follow the current word, see the note below this table, D186) | exp | Must edge to the included file's module unit; a glob gives May edges to each match (Must when exactly one); unresolved is an Unknown edge and MDL002 |
| `... as P` | `bind(kind=mount, mode=prefix)(P . scope; rhs=apply(include))` | exp | P binds the prefix over the included file's entities (the one non-unit binder) |
| `namespace N { }` | `unit(kind=namespace)` | decl | containment only |
| `node` | `unit(kind=node, role=declaration)`, body `group(unordered)(clauses)` | decl | one per entity |
| `extend node X { }` | `unit(kind=node, role=extension)` | decl | same identity as X (universal-model.md 2.6 multi-part) |
| `flow` `contract` `claim` `vmodel` `boundary` `pack` | `unit(kind=flow/contract/claim/vmodel/boundary/pack, role=declaration or extension)` | decl | |
| `: trusted` | `ref(trusted)` as `attr(name=trust)(unit; ref)` | decl | Must edge to the trust-lattice element in the builtin scope |
| `clearance L` | `attr(name=clearance)(unit; ref(L))` | decl | label lattice element |
| `kind K` | `attr(name=kind)(unit; lit(ident, K))` | decl | |
| `owns SEL` | `attr(name=owns)(unit; apply(kind=select)(...))` | decl | selector terms below; May edges from the `select` node to every unit it matches (6.4 status); the edges are the binding relation of section 10 |
| `surface SEL` | `attr(name=surface)(unit; apply(kind=select))` | decl | |
| `may A(args) at SEL` | `attr(name=may)(unit; apply(kind=grant)(ref(A); group(unordered)(lit(string)...); apply(kind=select)))` | decl | `ref(A)` is a Must edge to the registry atom (`ref(pack::A)` through the pack); unknown atom is an Unknown edge and MDL016 |
| `template N { }` | `unit(kind=template, role=declaration)`, body `group(unordered)(excuse clauses)` | decl | one per entity; no `extend` of a template (a template is replaced whole) |
| `excuse A for SEL because=".."` | `attr(name=excuse)(template unit; group(unordered)(ref(A); apply(kind=select); attr(name=because)(.; lit(string))))` | decl | `ref(A)` is a Must edge to the registry atom (unknown is an Unknown edge and MDL016); the `select` is the units the excuse covers (May edges, 6.4); a Body part of the template, listed in `check --json` |
| flow `: A -> B` | `apply(kind=connect)(ref(A); ref(B))` in the flow body | exp | two Must edges to the nodes |
| `label`, `rate`, `age`, `size`, `fanout`, `growth`, `condition`, `transport` | `attr(name=<key>)(unit; lit or ref)` | decl | quantities are `lit(quantity, "100 req/s")` |
| `producer SEL` `consumer SEL` | `attr(name=producer\|consumer)(unit; apply(kind=select))` | decl | |
| `contract NAME;` (in a flow) | `attr(name=contract)(unit; ref(NAME))` | decl | Must edge to the contract entity |
| `shape SEL` | `attr(name=shape)(unit; apply(kind=select))` | decl | |
| `versioning k=v ...` | `attr(name=versioning)(unit; group(unordered)(attr(name=k)(.; lit)...))` | decl | |
| `noflow A -> B` `reach A -> B` | `apply(kind=noflow\|reach)(ref(A); ref(B))` in the claim body | exp | |
| `bound M T <= Q` | `apply(kind=bound)(lit(ident, M); ref(T); lit(quantity, Q))` | exp | |
| `proof L` | `attr(name=proof)(unit; lit(ident, L))` | decl | |
| `attests "S" [on N]` | `apply(kind=attests)(lit(string, S); ref(N)?)` in the claim body | exp | |
| `assumed because=.. until=.. owner=.. [ticket=..]` | `attr(name=assumed)(unit; group(unordered)(attr(because), attr(until), attr(owner), attr(ticket)?))` | decl | the bridged `review=` produces `attr(until)` (one digest for both spellings) |
| `verified_by SEL [for e.v]`, `verified_by manual because=..` | `attr(name=verified_by)(unit; apply(kind=select) or attr(name=manual)(lit(string)); apply(kind=arm_ref)(ref(e); lit(ident, v))?)` | decl | the deprecated `evidence tests SEL`, `evidence ref "S"` and the `runnable` of a test vmodel produce the same term (one digest for both spellings) |
| vmodel `kind`, `level` | `attr(name=kind)`, `attr(name=level)` with `lit(ident)` | decl | alias levels print canonical |
| `ref "S"` | `attr(name=ref)(unit; ref(S))` | decl | |
| `verifies X` etc. | `apply(kind=verifies\|satisfies\|refines\|allocates\|decides\|supersedes\|blocked_by)(ref(X))` in the body | exp | one Must edge each; `because=` is an `attr` on the apply's enclosing clause |
| `boundary b endorse f : A -> B when ".."` | `unit(kind=boundary)` with body `apply(kind=endorse\|declassify)(ref(f); ref(A); ref(B); lit(string))` | decl, exp | |
| `pack` clauses | `attr(name=ref\|version\|digest)(unit; lit(string))` | decl | |
| `attr K = V` | `attr(name=attr:K)(unit; lit or group(ordered)(lit...))` | decl | a bracketed list is `group(ordered)`; a bare marker has an empty `group(unordered)` payload |
| `alias`, `renamed_from` | `attr(name=alias\|renamed_from)(unit; lit(ident))` | decl | the name is also an alias declaration in the scope graph |
| `accept\|defer\|hotfix RULE ...` | `attr(name=accept\|defer\|hotfix)(unit; group(unordered)(ref(RULE); attr(because); attr(ticket); attr(until)))` | decl | `ref(RULE)` is a Must edge to the rule registry; a top-level `accept ... on REF` hangs on the file unit (a direct child of it, outside the item group) with a `ref(on)` payload child, which is the Must edge to the resolved unit (D71) |
| selector `"glob"` | `lit(glob, lexeme)` | exp | the lexeme is the unescaped string |
| selector `lang(l)`, `kind(..)`, `attr(..)` | `apply(kind=pred)(ref(lang\|kind\|attr); lit...)` | exp | `ref` resolves into the predicate registry (Must) |
| selector `a & b`, `a \| b`, `!a` | `apply(kind=and\|or\|not)(group(unordered)(operands))` | exp | operands unordered: `a & b` and `b & a` have one digest |
| `//` `/* */` | `comment(text)` | trivia | attached to the item per 8.1; comments never merge or drop (D72) |
| `///` | `attr(name=doc)(unit or attr; lit(prose))` | decl | the Doc facet; a `///` comment is never trivia and never a `comment` node (D72) |
| directive in a comment | `attr(name="<ns>:<verb>")(target; payload)` | decl | exactly as for code units (docs/design/shared/code-model.md section 4) |
| syntax error | `hole(kind=parse-error)` | any | resynchronizes at the next `;` or at the `}` closing the current block; the rest of the file still parses |
| not UTF-8, or a file the lexer cannot start | `opaque(reason=not-utf8\|binary, payload)` | any | the whole file; all queries Unknown on it |
| (not produced) `anon`, `region`, `phase` | none | | the language has no anonymous entities (every entity is named), no embedded-language islands (a selector is a string literal parsed by gob-walk, not an island) and no macros; `use` is an `apply`, not a `phase`, because a used file is its own artifact with its own units, whereas a `phase` rewrites text in place |

Respelled clauses (D186). The attr name of a clause respelled in cycles
1-3 is its CURRENT word, and the bridged spelling produces the same term:
`verified_by` (from `evidence` and the test vmodel's `runnable`),
`until` (from `review`), `in_node` (from the actor's `node`), `on_page`
(from `requires_page`), `attr:dimension` (from `goal ... as K`), and the
`///` Doc facet (from `title`, which the P1 fold put in Body). So the
Body or Attr digest of each such entity changes ONCE, when the parser
ticket lands; `grimble ack` restamps it and the lock entry records the
reason "respelling (D186)", like a digest-scheme change (3.4). The graph
export's edge names follow the same words (17.1). Kinds stay frozen
(`apply(kind=include)`), so the change is bounded to these attrs.

Scope graph. Entity declarations (names, aliases, `renamed_from`, packs)
are declarations in the model's root scope (nested by namespace and mount
prefix); every `ref` in the table is a reference with the resolution of
5.3, status Must; every `select` node has May edges to the identities it
matches (status per 6.4). Lattice elements, atoms, rules, units and
predicates are declarations in a builtin scope that every file's scope
inherits.

Facets (universal-model.md 7.1, computed over the canonical facet
stream; trivia and directives excluded, literals exact):

| Facet | Content for a .grmb entity |
|---|---|
| Sig | kind, full name, plus the sig parts of the placement above: trust, flow endpoints `: A -> B`, boundary direction and endpoints, `level` and `kind` of a vmodel, and for flow and contract entities `label`, `producer`, `consumer`, `contract`, `shape`, `versioning` (D74: a superset of the list the first draft gave) |
| Body | every clause that is not a sig part and not an `attr K` or exception clause, in canonical order |
| Doc | the `///` text |
| Attr | `attr K` clauses and the exception clauses |
| Contract | the Sig parts with names erased: on a `contract` entity `shape` and `versioning`; on a `flow` the canonical `(from, to, label, producer, consumer, contract)`; on other entities whatever sig parts they have (trust, vmodel `kind` and `level`, the boundary apply) |

### 9.3 What `grimble fmt` guarantees

`grimble fmt` is the alpha-normal printer for `grmb`: a fixed point of
parse then print, defined on the canonical facet stream.

1. Idempotent: `fmt(fmt(x)) = fmt(x)`.
2. Digest-preserving: for every entity and facet, the digest of
   `fmt(x)` equals that of `x`. Reformatting never changes a digest
   (universal-model.md 7.1); a semantic edit always does.
3. Canonical order: items of a file in the order module/part, `use` items
   (by path), packs, namespaces, entities by (kind order node, flow,
   contract, claim, vmodel, boundary, template; then name, a declaration before
   its `extend`), then top-level exceptions (D70); clauses of an entity
   in a fixed order (kind, clearance, owns, may, surface,
   producer, consumer, contract, flow fields, what, proof, assumed,
   verified_by, links, attrs by key, exceptions by (kind, rule), aliases);
   operands of `&` and `|` sorted by their printed form; list-valued
   clauses sorted by printed form and de-duplicated (a duplicate is
   MDL017 Advisory before printing); a duplicate is removed only when
   it carries no comments or docs (D72).
4. Canonical spelling: one space around `:`, `->`, `=`; quantities as
   `N unit` with `%` attached; level and unit aliases replaced by the
   canonical names; keywords lowercase; strings with minimal escapes;
   dates as written.
5. Comments and directives travel with their item and keep their text;
   a comment is never deleted, merged or reflowed; doc comments stay
   directly above the item.
   A comment block followed by a blank line is a floating banner (a
   section header, "the clauses below"): it keeps its slot, so it is
   printed above whatever item (or clause) lands at the position it had
   among its siblings, with its blank line, instead of travelling with
   the item that follows it in the source. Within a block of comments
   the banner is the run up to the last comment followed by a blank
   line; the comments after it, with no blank line before the item, are
   attached and follow the item or clause as before. `///` doc comments
   are never floating. A banner whose slot is past the last printed
   clause (after a duplicate was dropped) lands on the last clause.
6. A file that contains a `hole(kind=parse-error)` or an `opaque` is not
   rewritten (`fmt` exits 1 naming the hole) so that a syntax error is
   never "formatted away". A `sorry` is not a hole (9.5) and is printed.
7. Multi-file: fmt formats each file in place and never moves an item
   to another file (item order is a per-file concern, 3.3).

### 9.4 Locations

Entity anchors as 9.1 (`step/web_app.customer.enters_payment`).
Clause anchors add, on a scenario, `chain` (the main chain), the arm
anchor `arm[OWNER.STEP.VARIANT]` for the arm that matches a pair (a
`_` arm is `arm[OWNER.STEP._]`, an `unknown` arm `arm[OWNER.STEP.unknown]`), and `handle[VARIANT]` for handle arms. On an impl, `wp[NAME]` addresses a named waypoint and `wp[K]` (0-based position) an unnamed one; fmt never reorders a chain (9.6), so both are stable under fmt; `wp[K]` renumbers when a waypoint is inserted before it, like every `clause-key[i]` (9.1), so a waypoint that carries a map, evidence or a finding should be named (D195).
`OWNER.STEP.VARIANT` is the `pair` of 11.1 with the step written in full
relative to the system (`customer.pays.declined`), so an anchor and a
pattern spell a pair the same way.

### 9.5 Encoding table

| Construct | U term | Sort | Notes |
|---|---|---|---|
| `system S { }` | `unit(kind=system, role=declaration)`; body `group(unordered)(items, clauses)` | decl | a unit and a containment prefix (a mount at S is the same scope) |
| `system S;` | `unit(kind=system, role=extension)` of S's identity, on the file unit | decl | the file-membership marker (11.2); in an unmounted file it declares S when no declaration exists; under a mount it never declares |
| `actor A : K` | `unit(kind=actor)`; sig `attr(name=kind)(unit; ref(K))` | decl | `ref(K)` is a Must edge into the actor-kind vocabulary (builtin plus packs) |
| actor `in node N` | `attr(name=in_node)(unit; ref(N))` | decl | Must edge; the major-2 spelling `node N;` gives the same term |
| `goal P { attr dimension = K; .. }` (or the bridged `goal P as K`) | `unit(kind=goal, role=extension)` of P's identity; Attr `attr(name=attr:dimension)(lit(ident, K))`; body `group(unordered)(variants)` | decl | a variant set is an extension part of the actor or goal it refines (9.2 multi-part), so several blocks are one identity |
| goal variant `v requires X` | `unit(kind=goal, role=declaration)`; body `apply(kind=requires)(ref(X))` | decl, exp | Must edge per ref |
| `step O.n : [open] { ... } [idempotent]` | `unit(kind=step)`; sig `attr(name=owner)(ref(O) or lit(ident, system))` and `attr(name=outcome)(group(unordered)(apply(kind=variant)(lit(ident, v); ref(C)?)...))`, `attr(name=open)` and `attr(name=idempotent)` markers | decl | the outcome and its openness are Sig: a new variant changes the Sig and Contract facets; `idempotent` is Body |
| `scenario s realizes G fails with { }` | `unit(kind=scenario)`; sig `apply(kind=realizes)(ref(G)...)`, `attr(name=fails)(group(unordered)(lit(ident)...))` | decl | |
| main chain | `attr(name=chain)(unit; group(ordered)(elements and links))` in the body | decl | ORDERED: a chain is a sequence |
| link `->` `-!>` | `apply(kind=seq\|try)(left; right)` | exp | right-nested |
| step element | `ref(step)` | exp | Must edge |
| `include s` (element) | `apply(kind=invoke)(ref(s))` | exp | distinct from the file `use` (`apply(kind=include)`) |
| `e => { arms }` | `apply(kind=match)(e; group(unordered)(arms))` | exp | arms unordered (12.3) |
| arm `p => c` | `apply(kind=arm)(pattern; chain)`; pattern `lit(ident, v)`, `ref(e) . lit(ident, v)` or `lit(wildcard)` | exp | |
| `handle { }` | `attr(name=handle)(unit; group(unordered)(arms))` | decl | |
| `end ok`, `end err(v)` | `apply(kind=end)(lit(ident, ok))`, `apply(kind=end)(apply(kind=err)(lit(ident, v)))` | exp | |
| `retry [e] max N [within T] [else c]` | `apply(kind=retry)(ref(e); lit(number, N); lit(quantity, T)?; chain?)` | exp | `ref(e)` is the resolved target, written or default (12.5), so both spellings have one digest; an omitted `else` is the default chain |
| `ambient P` | `attr(name=ambient)(unit; apply(kind=policy)(...))` | decl | Body facet |
| `sorry k=v ...` | `apply(kind=sorry)(group(unordered)(attr(because)?, attr(until)?, attr(ticket)?, attr(owner)?))` | exp; as a whole body (15.3) the one `apply(kind=sorry)` Body child standing where the main chain (scenario) or the realizations (impl, page) would be, never inside `attr(name=chain)`; other Body children keep their rows (decl) | its own sort, NOT a `hole`: fmt prints it and MDL rules judge the text around it; taint is a property of this node, followed over the scope graph (15.3, D180) |
| `one_of [exclusive] { }` | `group(unordered)` with `attr(name=one_of)` and an optional `attr(name=exclusive)` | decl | |
| `non_goal n;` | `unit(kind=goal)` with `attr(name=non_goal)` | decl | |
| `impl e for s` | `unit(kind=impl)`; sig `apply(kind=realize)(ref(e); ref(s) or lit(any))` | decl | full name per 11.7 |
| realization `K n = SEL` | `attr(name=realization)(unit; group(unordered)(ref(K); lit(ident, n)?; apply(kind=select)))` | decl | `ref(K)` into the realization vocabulary; May edges from `select` as 9.2 |
| `on page P`, `in node N` | `attr(name=on_page)(unit; ref(P))`, `attr(name=in_node)(unit; ref(N))` | decl | Must edges; the major-2 `requires page P` gives the same term |
| `chain { waypoints }` | `attr(name=chain)(unit; group(ordered)(waypoints))` | decl | ORDERED (14.1) |
| waypoint `K n = SEL { .. }` | `attr(name=waypoint)(group(unordered)(ref(K); lit(ident, n)?; apply(kind=select); map entries; verified_by))` | decl | |
| map entry `S1, S2 => v` | `apply(kind=maps)(group(unordered)(lit or ref sources); lit(ident, v))` | exp | `_` source is `lit(wildcard)` |
| `page p` | `unit(kind=page)`; `attr(name=entry)` marker; `apply(kind=from)(ref(a))` | decl | |

Facets: Sig holds actor kind, step owner and outcome, scenario
`realizes` and `fails`, impl step and target; Body holds
chains, handles, arms, realizations, `requires`, `from`, `entry`,
`verified_by`; Doc holds the `///` label; Attr holds `attr` (the goal dimension included: a report key never changes a goal's identity) and exceptions. Contract is the
Sig with names erased, so a step's Contract digest is its outcome type.

### 9.6 What `grimble fmt` guarantees for planning items

9.3 applies, with: planning items print after templates in the
kind order system, actor, goal, step, scenario, impl, page; chains are
NEVER reordered (ordered group): a scenario chain prints one link per line
with the link token leading the line, continuation indent two spaces past
the first element, and a waypoint chain prints one waypoint statement per
line; arms of a `=>` or `handle` are sorted by printed pattern with `_`
and `unknown` last, ONE ARM PER LINE and `=>` NOT aligned (C27: an
alignment change would touch every line of a diff); a scenario chain that
ends with `}` prints no `;`. Defaults are never printed (D153): a `retry`
target equal to the matched element and an `else` equal to `end err(v)`
are dropped. Deprecated spellings print in their current form (`use`,
`on page`, `in node`, `:` outcome types, `=>` arms, `until=`). A name
written as a string is rewritten to a bare name by a quick-fix (C26).

## 12. The formal relation to code

### 10.1 Sets

- E: the set of entities of a model (the units of every entity kind of
  sections 4 and 11, templates and planning kinds included, of the U term
  of 9.2 and 9.5), each with a full name and an identity (5.5).
- I: the identities of the code term (universal-model.md 2.2): every
  `unit` of every artifact in the snapshot, including the units of the
  model's own .grmb files (the model is part of the code it describes).
- S = {Must, May, Unknown}, ordered Must > May > Unknown.

### 10.2 Binding

Binding is a relation

```
B  subset of  E x I x S
```

where `(e, i, s) in B` means entity e is bound to identity i with status
s, and `Unknown` is represented by a residual pair `(e, hidden(r), Unknown)`
for each unseen remainder r of 6.4 step 4, never by a missing row. For
each e the set `B(e)` is the union over the entity's binding clauses:
`owns` of a node, `producer` and `consumer` of a flow (to the nodes'
code), `shape` of a contract, `ref` of a vmodel, and `verified_by` of any
entity; `may ... at` and `surface` bind capability
and surface sets and are queried, not stored in B.

### 10.3 The four ranked sources and conflict rules

| Rank | Source | Contributes | Status |
|---|---|---|---|
| 1 | `grimble:binds` directives (in code or in .grmb, 8.2) | `(e, i)` for the named entity and symref | Must |
| 2 | model selectors (`owns`, `producer`, ...) through `sel` (6.4) | `(e, i)` for every identity in `lo` (Must) and `hi \ lo` (May) | Must or May |
| 3 | pack inference from names and attributes (declared by a data pack) | `(e, i)` | May |
| 4 | nothing | the residual `(e, hidden(r), Unknown)`; an empty selector is reported (MDL005, SYS004), never clean | Unknown |

Conflict rules, applied per identity i and per binding KIND (ownership,
producer, consumer, shape, evidence):

1. HIGHER RANK WINS. If a pair at rank r exists for i, lower ranks are not
   consulted for that kind, except that a lower-rank pair for a DIFFERENT
   entity is kept as an advisory "overridden" fact (shown by
   `grimble explain`, not a finding).
2. WITHIN RANK 2, MOST SPECIFIC WINS by the total order of 6.5; a tie is
   SYS002 and the owner is Unknown. Within rank 1, two entities bound to
   the same identity for ownership is SYS003 (explicit contradiction; grimble/binding.md
   2.1 and 2.5 refine this rule, see the note after the conflict rules).
3. WITHIN RANK 3, a tie yields no owner (May on both) and no finding;
   inference never creates SYS002.
4. STATUS COMBINES by maximum over sources of the same rank and entity
   (a pair reached by a Must glob and a May glob is Must).
5. UNOWNED (FOREIGN) is `Exact(None)` only when no source mentions i and i
   has no unseen remainder; otherwise Unknown. A FOREIGN identity is Warn
   until `[grimble] strict = true`, as decided in docs/design/grimble/grmb-spec.md section 20.1.
6. ONE OWNER PER IDENTITY: `owner(i)` of 6.5 is a function; B may relate
   an identity to several entities of different kinds (a function is
   owned by a node and is the producer of a flow), but to one node.

Rules over B are stated with polarity over the `(lo, hi)` of `B(e)` in
G02; this file fixes only the relation, the sources and the conflict
rules.

G02 (grimble/binding.md) landed after this section and refines it: the relation gains
a role, rank 1 against a different Must at rank 2 is the finding SYS003
`directive-selector` (rule 1 above kept it advisory), two rank 1 nodes on one
identity are SYS003 (rule 2), and the owner function has the possible-worlds
reading of grimble/binding.md 2.2. Where they differ, grimble/binding.md wins (its 11.3).

## 13. Language engines: what lives in gob, what lives in a product

Merged from the former code-model.md.

Provenance: accepted, coordinator decision 2026-10-06 under the owner's
delegation; owner prompt: "Make sure the language engines make sense
(for example, what from JSX/TSX goes in gob or crunk? Don't we need it
for grimble as well?). We want both universal capabilities and
whatnot." Extends docs/design/shared/code-model.md section 3, universal-model.md sections
4.4 and 5, and docs/design/shared/charter.md section 3; supersedes the crunk-local
placement of JSX extraction and framework discovery in notes/v1/crunk.md
section 13.4.

### 13.1 The placement rule

One test decides every case:

- A fact about **what is written** (syntax, names, scopes, imports,
  calls, elements, attributes, style declarations, constant values,
  project and package layout, framework entry points) is a language or
  repository fact. It lives in `gob-*`, is answered through a
  capability with Must/May/Unknown honesty (universal-model.md 4.4),
  and is visible to every product and to GRL.
- A judgement about **what it means for one product's domain** (a
  ticket obligation, an architecture violation, a palette or spacing
  scale, a Tailwind utility's theme value, a WCAG contrast ratio) lives
  in that product's crates.

Corollaries:

1. No product crate parses a language or walks a syntax tree. A product
   that needs a new fact asks for a capability in gob.
2. A product vocabulary that is itself a small language used by only
   that product (Tailwind utility candidates, the crunk.toml spec, .grmb)
   stays in the product until a second product needs it; then it moves
   down without changing its API.
3. Every capability is reachable from GRL through the relation catalog
   (docs/design/shared/grl-spec.md section 6), so a rule in any product's pack uses the same
   words: an A11Y rule in crunk-web and an XSS rule in grimble-websec both
   say `element(.tag = "img")` and `attribute(.name = "alt")`.

### 13.2 Universal capabilities added by this decision

universal-model.md 4.4 lists the structural capabilities. Four more are
needed for web, UI and project facts. Each is an answer type and query
set in `gob-ir`, implemented per language by an adapter in
`gob-symbols` (or `gob-frameworks`, section 4), with a capability-matrix
cell `Implemented`, `NotApplicable(reason)` or `Gap(ticket)` per
language.

| Capability | What it answers | Lowering into U | Languages (first adapters, later ones) |
|---|---|---|---|
| `markup` | element tree: element (tag, kind intrinsic / component / unknown), attributes (name, value as a `const_value` answer, spread), children, text | JSX/HTML element = `apply(kind=element)`; a component tag (capitalised or member expression) has a `ref` head resolved through the scope graph, so component usage is a call edge for grimble; attributes are named args; a spread is an attribute set with status May | TSX, JSX, HTML; later Vue and Svelte templates (as `region` islands), Unity UXML, XAML, Razor |
| `style` | rules (selector), declarations (property, raw value, component values), at-rules, custom property definitions and `var()` references, layers | rule = `unit(kind=style-rule)`, declaration = `bind(kind=property)`, custom property = `unit(kind=custom-property)`, `var(--x)` = `ref` with status May (the cascade decides at runtime); SCSS variables and mixins are `phase` | CSS, SCSS, inline JSX `style={{...}}` objects, CSS-in-JS template literals as `region` islands tagged css; later Unity USS, Less |
| `const_value` | bounded static value of an expression: `Known(v)`, `OneOf(set)`, `Fragments(known parts, Unknown rest)`, `Unknown` | evaluates `lit`, `ref` to a const binding, concatenation, template literals, conditional and object/array literals within a step budget; anything else is Unknown | TS/JS first (className strings, style objects, route paths), then Python, Rust, C# |
| `project_model` | packages and their files, package dependencies, path aliases, entry files | packages are `unit(kind=package)`; aliases feed `imports` resolution | Cargo, pyproject, .sln/.csproj (~ECEBCQ1), package.json workspaces, tsconfig paths and baseUrl; later Unity .asmdef (~C8HB0GQ) |

`const_value` reaches beyond one file through an `ExternalRefs` hook
(~C2F4ZMQ): a name the scope graph cannot resolve is followed through
the module graph when it answers Must with one `const` unit, in that
file's own term, charging the same step budget; a reference cycle or an
exhausted budget leaves `Unknown` and the evaluation says which
(`Unresolved`), with the origin span of every constant consulted. A
call is read only when its callee is a class-name joiner (`clsx`,
`classnames`, or a repository function whose body calls one, such as a
`cn` wrapper; a `twMerge` wrapper is read as the plain join, a superset).

Class tokens are a derived query over `markup` and `const_value`, not a
capability of their own: `class_tokens(attr)` returns the Known tokens
of a `class`/`className` attribute (through `clsx`, `cn`,
`classnames` and template literals by name, May) and says Unknown for
the rest. crunk's Tailwind rules read them; grimble does not need them.

### 13.3 Placement of every web item

| Item | Layer | Crate | Consumers |
|---|---|---|---|
| TS, TSX, JS, JSX, CSS, SCSS, HTML grammars and comment scanners | language | gob-languages | all |
| TS/JS adapter: units, exports, imports (ESM, CJS, dynamic import as May), calls, tests (vitest, jest, playwright) | language | gob-symbols | frob (COV, AFFECT, touched tests), grimble (graph, layering) |
| CSS adapter: rules, declarations, custom properties, at-rules, waivers | language | gob-symbols | crunk, grimble (WEBPERF assets) |
| `markup`, `style`, `const_value` answer types and queries | model | gob-ir | all, through GRL |
| JSX `markup` and inline `style` lowering | language | gob-symbols | crunk (tokens, A11Y), grimble (WEBSEC sinks such as `dangerouslySetInnerHTML`, `href="javascript:"`, `target=_blank` without `rel`) |
| package.json workspaces, tsconfig paths | repository | gob-symbols (`project_model`) | all |
| Framework discovery and routes (react-router, Next.js app and pages dirs, later Express, FastAPI, ASP.NET) | repository | gob-frameworks (new, above gob-symbols) | crunk (pages for SEO, LAUNCH, gallery), grimble (ROUTE, WEBSEC authorization) |
| ProjectStyles, bucket and organization model | domain | crunk-ingest, a thin mapping from `style` and `markup` answers | crunk |
| CSS value math (colour, length, contrast, palette distance) | domain | crunk-values | crunk |
| Tailwind candidates and theme mapping, node runtime bridge | domain | crunk-tailwind | crunk |
| Token model and export | domain | crunk-tokens | crunk |

### 13.4 gob-frameworks

Frameworks are not languages, so their discovery does not belong in an
adapter, but the facts (this file is a page at `/settings`, this
function handles `POST /api/orders`) are repository facts both crunk
and grimble consume. `gob-frameworks` sits above `gob-symbols` and
below every product:

- `Framework` is an open inventory registry (like `Language`); a
  framework adapter declares detection (package.json dependency,
  config file, directory convention), searched per workspace member,
  never the repository root only (the v1 lesson ~5E0V6W3).
- Answers: `routes` (path pattern, method, handler unit, page
  component, layout chain, each with status), `entrypoints` (Q-table
  `entrypoints`), and per-framework conventions (Next.js `use client`
  boundaries as an attribute on the unit).
- The capability matrix gains framework rows, generated into the same
  languages page.
- Implemented in `crates/gob-frameworks` (~AVXTRHX): `detect` walks every
  `package.json`, `analyze` folds the TypeScript sources over the module
  graph and runs each detected framework. Route patterns use `:name`,
  `:name+` and `:name*`; a path that `const_value` cannot resolve gives
  a route with no pattern and status Unknown, a `OneOf` path or a
  conditional or mapped `<Route>` gives May. react-router reads route
  objects handed to `createBrowserRouter`-style calls (also through a
  named constant or an import, with `basename`) and `<Route>` elements;
  Next.js reads `app` and `pages` (also under `src/`).

### 13.5 Consequences

- Tickets ~17ZVW3R, ~6KKJF80, ~C2F4ZMQ and ~Z8V73JM (grammars, TS
  adapter, constant evaluation, CSS adapter) move from the crunk epic to
  the shared web-engine epic; their crate placement was already right.
- ~8JGRZY3 (crunk-ingest JSX style and className) is rescoped to a thin
  mapping over `markup`, `style` and `class_tokens`; the extraction
  itself is the gob work.
- ~XPMQ50D (crunk-adapters FrameworkAdapter) moves to gob-frameworks; the
  crunk-adapters crate is not created.
- The GRL relation catalog gains `element`, `attribute`, `style_rule`,
  `declaration`, `custom_property`, `route` and `package` kinds with
  their fields, each naming its query and the languages that answer it.
- Unity: UXML and USS ride on `markup` and `style` once the C#
  epic (~GJVPDC0) lands; no Unity-specific style engine is designed.
- The owner's platform repository (Python, TS/TSX, CSS, crunk.toml) is
  the first real consumer, so the web engine is scheduled before the
  crunk rule tickets that need it.

## 14. C#, .NET and Unity: the C# adapter and the Unity vocabulary

Merged from the former code-model.md.

Provenance: accepted direction, owner request 2026-10-05: run frob on the
owner's project-hullbreach repositories. `game` is a Unity 6 project
(6000.0.43f1, URP, Input System): 129 C# files in 17 assembly
definitions, 274 NUnit `[Test]` and 17 `[UnityTest]` tests through the
Unity Test Framework, MonoBehaviour messages (`Awake`, `Update`,
`FixedUpdate`, `LateUpdate`, `OnDestroy`, ...), shaders. `platform` is
Python with some TS/TSX and CSS and a `crunk.toml`. Both run frob v1
today. Python is covered by the first-party adapter (epic ~HKNM4VV);
TS/TSX and CSS ingest is crunk's 0.537.0 work. This design adds the
missing piece: C#, the .NET project model, and Unity's engine contract.

### 14.1 Layers

| Layer | What | Where |
|---|---|---|
| Language | C# grammar, comments, symbols, imports, calls, attributes, XML doc comments, test detection | gob-languages, gob-symbols (first-party adapter, same fidelity bar as Rust and Python, code-model.md) |
| Project model | which files form one assembly and what it references: `.sln` and `.csproj` for .NET, `.asmdef` and `.asmref` for Unity (Unity generates `.csproj` files and they are not committed) | gob-symbols project discovery, mapped to the existing package/unit notion so ownership, reach and test selection work unchanged |
| Engine vocabulary | the Unity contract: which methods the engine calls, which fields the editor writes, which calls are dynamic | a `unity` vocabulary pack (packs-and-plugins.md, D76), opt-in, auto-suggested by `frob init` when `ProjectSettings/ProjectVersion.txt` exists |
| Test runners | `dotnet test` (TRX) and Unity's test runner in batch mode (NUnit 3 XML) | frob-evidence providers `dotnet` and `unity`, frob test selection |

Project model details (implemented in `unity_project.rs`): a package per
`.asmdef` with `name`, `references` (name or `GUID:`), `includePlatforms`,
`excludePlatforms`, `defineConstraints`, `precompiledReferences`,
`overrideReferences`, `autoReferenced` and `allowUnsafeCode`; an assembly is
editor-only when `includePlatforms` is `[Editor]`, and a test assembly when it
has `UNITY_INCLUDE_TESTS` and a `UnityEngine.TestRunner` reference, with mode
decided by a `PlayMode` or `EditMode` path segment, else editor-only means
EditMode and anything else PlayMode. Implicit assemblies reference every
auto-referenced asmdef (and the editor variants the runtime ones). Unresolved
GUIDs, malformed definitions and dangling `.asmref`s are findings.

Nothing here is Unity-specific below the vocabulary pack: plain .NET
repositories get the language, project model and `dotnet` provider
without it.

### 14.2 The C# adapter

Grammar: tree-sitter-c-sharp, pinned like the other grammars. Units:
namespaces (file-scoped and block), types (class, struct, record,
interface, enum, delegate), members (methods, constructors, properties,
indexers, events, fields, operators, local functions); partial types
merge into one unit with several spans. Imports: `using`, `using
static`, aliases, global usings. Calls: invocations with qualifiers,
extension methods resolved where the receiver type is known, otherwise
Unresolved (never clean). Attributes become attributes on the unit.
`///` XML doc comments feed the DOC rules. Test detection: NUnit
(`[Test]`, `[TestCase]`, `[TestCaseSource]`, `[UnityTest]`), xUnit
(`[Fact]`, `[Theory]`) and MSTest (`[TestMethod]`); a test id is the
fully qualified method name, the form both runners filter by.
Preprocessor symbols (`#if UNITY_EDITOR`): both branches are scanned
and units carry the condition, so editor-only code is not reported as
dead in player builds or the reverse.

### 14.3 The Unity vocabulary

- Engine entry points are reach roots: MonoBehaviour and
  ScriptableObject messages (`Awake`, `Start`, `Update`, `FixedUpdate`,
  `LateUpdate`, `OnEnable`, `OnDisable`, `OnDestroy`, `OnValidate`,
  `OnTrigger*`, `OnCollision*`, `OnGUI`, ...) on types deriving from
  those bases, plus `[RuntimeInitializeOnLoadMethod]`,
  `[InitializeOnLoad]`, `[MenuItem]`, `[ContextMenu]`. Coverage and
  reach rules treat them as called by the engine, not as dead code.
- Editor-written state: `[SerializeField]` and public serialized fields
  are written from outside the code (scenes, prefabs, the Inspector);
  effect and flow rules see an external writer.
- Dynamic dispatch: `SendMessage`, `Invoke("name")`, `UnityEvent`
  wiring in assets and string-keyed lookups are dynamic calls, reported
  Unresolved per the compute policy, never resolved by guesswork. The
  pack's `dynamic.call` and `dynamic.lookup` vocabularies name them
  (`gob_symbols::csharp_dynamic_calls`, packs-and-plugins.md 8.5); a literal method
  name never becomes an edge. COV001 reads them through
  `frob_tests::reach::dynamic_calls`: an unresolved report whose call the
  pack classifies (inside the pack's gate) adds the named reason, for
  example "the engine resolves a literal method name at run time". UnityEvent wiring in scene and prefab YAML is
  not read yet (only GUID references are in scope).
- Asset hygiene: every tracked file under `Assets/` and `Packages/` has
  its `.meta`, and no `.meta` is orphaned; a duplicate GUID is an error.
  This is a small UNITY rule family in the pack.
- Hot context: the `hot(region)` capability (universal-model.md 4.4)
  takes `Update`, `FixedUpdate`, `LateUpdate` and `OnGUI` as hot roots;
  UNITY2xx rules fire only in code reachable from them.
  UNITY201 and UNITY202 are implemented (see rules.md, ~9XDR1GY);
  UNITY301 and UNITY302 too (~T08HTWJ).
- Version gate: the engine version is read from
  `ProjectSettings/ProjectVersion.txt`; `Find*` lookups and `foreach`
  allocation behaviour changed across versions, so rules that depend on
  them are gated by version.
- Rule ranges (family UNITY): UNITY0xx `.meta` and GUID hygiene; UNITY1xx
  bound Microsoft.Unity.Analyzers findings (UNT rules, `source_rule` kept);
  UNITY2xx own hot-context rules (GetComponent, Find*, Camera.main and
  managed allocation in hot code), Advisory; UNITY3xx own input and
  physics rules (legacy Input in an Input System project, Rigidbody forces
  or moves in Update). PAIR001 carries the Unity vocabulary (`+=` in
  `OnEnable` without `-=` in `OnDisable` or `OnDestroy`, Addressables
  Load/Release).
- Out of scope at first: scene and prefab YAML contents beyond GUID
  references, ShaderLab and HLSL (opaque F0 files, as today).

### 14.4 Evidence and test selection

`dotnet` provider: runs `dotnet test --logger trx` with a filter built
from test ids, parses TRX per test, through gob-exec and the shared
redact, scrub and escape paths, allowlisted like pytest. `unity`
provider: runs the Unity editor in batch mode
(`-batchmode -runTests -testPlatform EditMode|PlayMode -testResults`
with `-testFilter`), parses the NUnit 3 XML. The editor path comes from
config (`[evidence.unity] editor`), defaulting to the version in
`ProjectSettings/ProjectVersion.txt` under the standard Unity Hub
install locations; a missing editor or license refuses with a remedy,
never a silent skip. PlayMode tests need a graphics-less runner flag
and are slower; the provider runs EditMode by default and PlayMode when
the selected tests need it. `frob test` maps touched C# symbols to test
ids through the same reach graph as Rust and Python.

### 14.5 Sequencing

1. C# language and symbols (adapter, fixtures, fidelity row), and the
   `.csproj`/`.asmdef` project model.
2. `dotnet` evidence provider and C# test selection.
3. The `unity` vocabulary pack (entry points, serialized fields,
   dynamic calls, `.meta` hygiene).
   3b. Before any own Unity rule, bind Roslyn and
   Microsoft.Unity.Analyzers through `dotnet build` SARIF with the USP
   suppressor set on, so stock IDE rules stop firing on engine-called
   messages and serialized fields; the findings map to UNITY1xx.
4. The `unity` evidence provider (needs a Unity editor; proven on the
   owner's Windows side through goway, one run at a time).
5. Migrate project-hullbreach `game` and `platform` from frob v1 to v2
   (migration.md) and run them as the post-0.532.0 real-world trial.

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D5

Symbol addresses are language-neutral; cross-language `binds` edge; capability matrix; the node-level reasoned `excuses` of this row is superseded by D75 (deny by default, excuses only in matrix-build templates)

### D43

Symbols (T-0013): impl members are `Type.method`, `Type[Trait].method` on collision, impl blocks `Type[impl]` or `Type[Trait]`; one file-level Module node per file; facet digests hash whitespace-collapsed text, not NUL-joined tokens (this is digest scheme 1; superseded by D56 for the facet scheme); markdown setext headings are not extracted (gap)

### D44

Directives (T-0014): a directive must start a comment line (languages without line comments use the `attr` path, D56); markdown and inner doc comments bind to the enclosing section or file; all four exception verbs spell the reason `because=`; DSL002 flags any abbreviated id including v1 `T-####`; `[directives] namespaces` is not yet a ConfigTable (Milestone 2)

### D49

Ack (T-0021): lock entries carry a `targets` vector (the facet count follows the digest scheme: three in scheme 1, five in scheme 2); AFFECT001 fires for a public symbol whose signature changed since its lock entry while a dependent lacks a later ack; DRIFT001 is one finding per facet; `ack` commits `frob.lock` on the current branch

### D91

Inert ledger text (~JTV288R): the ticket ledger tree (the configured `[tickets] dir`) is data written through the ledger write path and text in it is never a live directive; one structural classification (`gob_walk::FileRole`, decided per path by `Roles`) makes directive and comment scanning skip ledger files while ledger-specific rules (TICK, PM, privacy) keep applying; separately, markdown scanning reads only HTML comments outside code and outside a leading YAML or TOML front matter block

### D96

Owner prompt 2026-10-06 ("what from JSX/TSX goes in gob or crunk? Don't we need it for grimble as well?"): facts about what is written (syntax, scopes, imports, calls, elements, attributes, style declarations, constant values, packages, framework routes) live in gob behind capabilities with Must/May/Unknown honesty and GRL catalog words; domain judgements (tokens, Tailwind theme values, contrast, architecture, obligations) live in products; no product crate parses a language. New capabilities `markup`, `style`, `const_value` (bounded, with Fragments), `project_model`; new crate gob-frameworks above gob-symbols for framework detection and routes; crunk-ingest becomes a thin mapping and crunk-adapters is not created; UXML and USS ride on markup and style

### D101

Web-engine implementation decisions accepted 2026-10-06: (1) TS imports: a literal `import("m")` is May with its target resolved, a computed specifier is Unknown, a top-level `require` is Must and a conditional one May (~6KKJF80); (2) imports into `node_modules`, declared dependencies and Node builtins are Unknown edges with reason External, anything else unresolvable stays Unbound (~C3DEAQX); `exports` conditions are tried in a fixed order and a workspace entry under dist/build/lib/out is also tried under src; (3) an Unknown inline-style value is one `lit(unknown)` component, a JSX fragment is a `group` with `markup.group=fragment` (~VGKB025); (4) const evaluation: `||` follows JavaScript truthiness, a `twMerge` wrapper is a plain join (a superset of surviving tokens), a spread of an Unknown value makes the whole array or object Unknown, and `clsx`/`cn` are recognised by import binding, never by name (~C2F4ZMQ); (5) CSS symrefs normalise selector whitespace and bracket dotted names (~Z8V73JM)

Also logged against: docs/reference/fidelity.md.

### D94

Owner request 2026-10-05 (project-hullbreach: a Unity 6 game and a Python/TS platform): C#, .NET and Unity support (code-model.md). A first-party C# adapter at the Rust and Python fidelity bar; assemblies from `.sln`/`.csproj` and Unity `.asmdef`/`.asmref` mapped onto the existing package notion; Unity's engine contract as an opt-in vocabulary pack (`unity`, packs-and-plugins.md) rather than core: MonoBehaviour messages and editor attributes are reach roots, serialized fields have an external writer, string dispatch is dynamic (Unresolved), and a UNITY family checks `.meta` pairing and GUID uniqueness; evidence providers `dotnet` (TRX) and `unity` (editor batch mode, NUnit 3 XML), with a missing editor or license refused, never skipped. Also: milestone 0.532.0 criterion 2 relaxed by the owner to cloc and mdcat with clean ledgers at cut time; the project-hullbreach trial follows the release
