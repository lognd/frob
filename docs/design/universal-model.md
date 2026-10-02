# The universal structural model (gob-ir)

Status: DRAFT under T-0001, for owner review. Supersedes code-model.md
section 5 when accepted. Evidence: notes/research/paradigms.md (202
languages, 33 families), notes/research/calculi.md (calculi, type
theories, universal cores, impossibility results),
notes/research/lint-requirements.md (every rule family mapped to the
queries it reads; 47 queries; capability table), and
notes/research/reading-list.md. The three research notes were written
without web access; their citations are from memory and the uncertain
ones are tagged `[verify]` inside them.

## 1. The claim, stated precisely

frob, grimble and crunk evaluate structural rules over source written in
any language. "Any language" must mean something provable, not a list
of tree-sitter grammars. This file defines one model, the universal
structural model U, and proves three things about it:

1. Totality. For every language L that has a computable parser, there is
   a total computable translation T_L from L's artifacts into U. Nothing
   is rejected; what cannot be understood becomes an explicit `opaque`
   node carrying the raw payload and a reason.
2. Adequacy. Every structural query the rules need (section 5) is a
   total, decidable function on U, polynomial in the size of the term.
   Rules written against U are written once and terminate on every
   input, and on the closed fragment (no opaque nodes, no dynamic
   references, no parse errors) their answers are exact.
3. Honesty. Every query whose true answer depends on execution, on
   undecidable inference, or on information the adapter does not provide
   returns a bounded or Unknown answer and never a definite answer that
   could be wrong. This is the boundary Rice's theorem imposes; the
   model does not pretend to cross it, and a rule that could not examine
   its subject reports Unresolved, never clean.

U is "LLVM in the other direction": LLVM is the meet of all languages
(what everything can be lowered to for execution); U is the join (what
everything can be lifted to for structure). It is not a semantics. It
carries what is needed to identify things, relate them, hash them and
locate them, and says Unknown for the rest.

## 2. Core definitions

### 2.1 Sorted abstract binding trees

U's syntax is the free algebra of sorted abstract binding trees (ABTs:
Harper, PFPL ch. 1; Allais et al. 2018), extended with identities,
locations, attributes and opaque leaves. Initial-algebra semantics
(Goguen et al. 1977) gives compositionality for free: any function
defined by structural recursion on U is well defined and total.

- A signature Sigma = (S, O, ar) has sorts S, operators O and an arity
  function assigning each operator a list of valences (s1..sk).t and a
  result sort. Valence (s1..sk).t binds k variables around a term of
  sort t. Variadic valences (a sequence of terms of one sort) are allowed
  so that containers need no encoding into binary nodes.
- Terms are the least set closed under variables and operator
  application, identified up to renaming of bound variables. Free
  variables, substitution and occurrence are total structural
  recursions.
- Universality remark: a signature with lam : (x.e) -> tm and app :
  (e; e) -> tm already contains the untyped lambda calculus, so U can
  express any computable structure. Rules never need this; it guarantees
  U is never the limiting factor.

### 2.2 The five primitives

Everything in U is one of five things (notes/research/calculi.md
section 10 arrives at the same five independently of the paradigm
survey's ten features in notes/research/paradigms.md section 6, which
are all expressible in them):

1. ABT terms over Sigma_U + Sigma_L (the universal signature below plus
   the language's own operators).
2. Identities: every `unit` has an identity independent of its name,
   file and position (content hash of its alpha-normal form by default;
   adapters may supply a stable id such as a Unison hash, a cell
   address or a generated node id). Symrefs (2.6) are names FOR
   identities, not the identities themselves.
3. The resolution relation: a scope graph (scopes, declarations,
   references, labelled edges) built by the adapter's declared binding
   discipline. Each resolution edge carries a status Must | May |
   Unknown. Lexical nesting is one derived view of it; unification,
   dynamic dispatch, dictionary lookup and late binding are others, at
   lower status.
4. Opaque: `opaque(reason, payload)` at any sort. Every query returns
   Unknown or NotApplicable on it; nothing is ever computed through it.
   An opaque region may carry `may_define` and `may_read_scope` hints
   (for example Template Haskell splices, `eval`, preprocessor regions)
   so that surrounding resolution is correctly downgraded to May.
5. Provenance and attributes: a location (2.5), the language tag and
   the language parameter (edition, `#lang`, pragmas, `#version`),
   trivia, and structured attributes (visibility, grades or
   multiplicities, effect labels, types, contracts, capability lists)
   that are carried but not checked. Attributes are outside digests
   unless a facet asks for them.

### 2.3 The universal signature Sigma_U

| Operator | Valences | Meaning |
|---|---|---|
| `unit(kind, role)` | (x1..xn . body) -> decl | A nameable entity: module, function, type, class, predicate, cell, word, actor, process, kernel, rule, table, target. `role` distinguishes multi-declaration parts of one identity (signature, equation, interface, implementation, partial, extension, stub). |
| `anon(kind)` | (body) -> decl | An entity with no source name (lambda, tacit train, anonymous block, Pd object); identity from content and position. |
| `ref(name)` | () -> use | A use of a name. Resolution lives in the scope graph, not in syntax. |
| `apply(kind)` | (head; args...) -> exp | Application in the widest sense: call, message send, rule invocation, cell reference, instantiation, data flow. Edge status comes from resolving `head`. |
| `bind(kind, mode)` | (x . scope; rhs?) -> exp | Any non-unit binder: let, pattern or logic variable, loop or implicit variable. `mode` carries multiplicity or grade when the language has one. |
| `group(order)` | (e1..en) -> exp | A container with an ordering discipline: sequence, unordered, topological, concurrent, backtracking, clocked, user-driven history (notebooks), unknown. |
| `lit(kind, lexeme)` | () -> exp | A literal. |
| `attr(name)` | (target; payload) -> decl | Attribute, annotation, decorator, pragma, type signature, doc comment attached to a target. |
| `comment(text)` | () -> trivia | A comment; directives are parsed from these and from `attr` payloads. |
| `region(kind)` | (body) -> exp | A boundary rules care about: unsafe, FFI, effect handler, transaction, clocked block, circuit, embedded language island (with its own language tag). |
| `phase(kind)` | (template; expansion?) -> exp | A metaprogramming site: macro, preprocessor, template, comptime, staging, plan. `expansion` is present only when the adapter expanded it within its step budget; otherwise the site is opaque to resolution. |
| `hole(kind)` | () -> any | A typed hole, parse error node or missing piece: first-class partial programs. |
| `opaque(reason, payload)` | () -> any | Everything else. |

Every node carries a location, a language tag and a language parameter.
Adapter operators (`rust.impl`, `prolog.clause`, `verilog.always`,
`apl.train`) extend Sigma_U; universal rules see them only through
their universal sort, language rules may match them directly.

### 2.4 Why no semantics in the signature

Evaluation order beyond `group(order)`, types, effects, ownership and
control flow are deliberately absent. Any of them would make T_L partial
for some language and partiality is what Theorem 1 forbids. They enter
only as attributes (carried) or capabilities (section 4, three-valued).
Roles such as loop, branch, return, assignment are attributes on
`group`, `apply` and `bind` nodes, provided by the adapter's operator
morphism, so the universal POL rules of rules.md ("sort inside a loop")
still have something to match without the IR committing to control
flow semantics.

### 2.5 Locations are not byte offsets

A location is a value of an adapter-declared address sort with a total
order and a containment relation: text (artifact, byte range); grid
(sheet or board, row, column); graph (document, node id, port); stream
(artifact, sequence number); notebook (notebook, cell, byte range);
pointer (artifact, JSON pointer). Digests, spans, snippets, leases and
scopes are defined over locations. Markdown anchors are the first
non-byte address already in use.

### 2.6 Symrefs over identities

The symref grammar of code-model.md section 2 is generalized: a symref
is `<locator>::<Qual>.<Name>` where the locator is a path for
file-based languages, `path#slug` for documents, `path#cell=A1` or
`notebook#cell=7` for grid and cell sources, and an adapter-declared
locator otherwise. Multi-part units (Prolog clauses of one predicate,
Haskell signature plus equations, partial classes) share one identity
and one symref; their parts are `unit` nodes with roles. Anonymous
units get the enclosing symref plus a positional index computed on the
alpha-normal form (stable under edits inside the unit, not under
reordering of anonymous siblings; see open question 2).

## 3. The translation T_L and the totality theorem

### 3.1 What an adapter provides

A language adapter A_L = (parse_L, rho_L, bind_L, cap_L):

- parse_L : Artifact -> ConcreteTree, total and computable. Tree-sitter
  with error recovery for grammar languages; a medium reader for grids,
  graphs and binaries; the constant one-leaf tree when nothing is known.
- rho_L : a signature morphism from L's concrete operators to Sigma_U +
  Sigma_L, with `opaque` as the default clause. For tree-sitter
  languages rho_L is checked against the grammar's node-types.json so an
  unmapped kind is a build-time finding, not a runtime surprise.
- bind_L : the declared binding discipline producing the scope graph
  (scope constructors, declaration and reference sites, edge labels,
  and which reference kinds are run-time dependent and therefore May or
  Unknown).
- cap_L : the capability declaration (section 4.3).

### 3.2 Theorem 1 (totality)

For every adapter, T_L = fold(rho_L, bind_L) o parse_L is total,
computable, and yields a finite term plus a finite scope graph in time
linear in the concrete tree.

Proof. parse_L is total by requirement. The fold is a primitive
recursion over a finite tree whose default clause is `opaque`; the scope
graph construction visits each node once. Composition of total
computable functions is total and computable; the output has at most
one U node per concrete node. QED.

The theorem is cheap on purpose: its value is that no language can make
the pipeline fail. The worst case is one `opaque` node on which every
query is Unknown and every rule Unresolved. That is "fail loudly".

### 3.3 Fidelity levels

Totality is trivially satisfied by mapping everything to `opaque`, so
adapters are graded and the grade is checked by a corpus per language
(gob-mdtest): for each universal operator the adapter claims, a sample
and the expected U term plus scope graph.

- F0: opaque only. Queries: locations and whole-artifact digests.
- F1: units, roles and containment.
- F2: F1 plus binders, references and a scope graph with Must edges for
  the lexical fragment.
- F3: F2 plus `apply` edges resolved to the adapter's declared status.
- F4: F3 plus attributes, comments bound to targets, regions, phases.

`frob doctor --languages` prints the level and the capability
precisions; the README's language table is generated from it (open
question 3). A rule needing a level the adapter lacks is Unresolved for
that language.

## 4. Queries, answers and the honesty boundary

### 4.1 The answer lattice

Every query returns one of:

- `Exact(v)`: the value is known and complete.
- `Bounds{lo, hi}`: the true set lies between lo and hi (may/must; the
  abstract-interpretation reading, Cousot and Cousot 1977).
- `Unknown`: no claim.
- `NotApplicable`: the language has no such feature (no comments, no
  visibility, no tests, no files); distinct from Unknown so rules can
  skip rather than nag.

Predicates use Kleene's strong three-valued logic over Yes/No/Unknown.
Resolution returns Must(x) | May({x1..xn}) | Unknown.

### 4.2 Rule polarity and subject accounting

A rule declares its polarity, which fixes which bound it may fire on
and which bound lets it certify clean (notes/research/lint-requirements.md
section 2):

- P+ (fires on presence of an offender): fires on `lo`, clean only if
  `hi` contains none.
- P- (fires on absence of something required): fires only if `hi` lacks
  it, clean if `lo` contains it.
- P0 (equality of digests or sets), Pn (threshold on a count), Pc
  (closure or cycle): evaluated on `Exact` only, otherwise Unresolved.

Subject accounting: a rule that examined zero subjects (every query
answered Unknown or NotApplicable) reports Unresolved, never clean. This
closes the most dangerous silent pass the survey found: "public symbol
with no test" reading as "all untested" or "all fine" on a language
without a test convention.

### 4.3 Theorem 2 (adequacy)

Let the structural relations of a U term be: operator and sort of each
node, parent, child order, attachment (attr, comment), the scope graph
with edge status, location order and containment, and the facet digests.
Then every rule predicate expressible in first-order logic with least
fixpoints (equivalently stratified Datalog) over these relations is
decidable, total, and evaluable in time polynomial in the term; its
three-valued answer is sound (never a wrong Yes or No about the source
structure); and on the closed fragment (no `opaque`, no `hole`, no May
or Unknown edges in the rule's dependency cone) it is exact: preserved
and reflected by T_L.

Proof sketch. The relations are finite and computed by structural
recursion (Theorem 1). Stratified Datalog over finite relations has
polynomial data complexity (Immerman, Vardi). Soundness: evaluate under
Kleene logic where an atom that touches an `opaque`, `hole` or
non-Must edge is Unknown; by induction on the formula a Yes or No is
derived only from atoms whose truth is fixed by the syntax, which T_L
preserves because rho_L is a morphism and bind_L is total. Exactness on
the closed fragment: every atom is then Exact and the evaluation is
classical. Alpha-invariance follows because all relations are defined
on the alpha-normal form. QED.

The syntactic queries this covers are the ones the landed crates already
compute for Rust and markdown, restated over U: units and symrefs,
containment, lexical binding, occurrences, attachments, the three facet
digests, and the graph digest.

### 4.4 Capabilities

Facts that are not syntactic come only through declared capabilities
with a precision (lint-requirements.md section 3 has the full 47-query
table; the 33 that need a language feature each name it):

| Capability | Answer | Precision ladder |
|---|---|---|
| `resolve_ref` | Must / May / Unknown | lexical; plus imports; plus nominal types; plus instances or dispatch (May) |
| `apply_targets` | May set / Unknown | by name in unit, artifact, project (may-call); type-directed where decidable |
| `visibility` | Yes/No/Unknown/NotApplicable | keyword; build-system aware |
| `effects(region)` | Bounds / Unknown | declared; inferred |
| `test_items` | Exact / Unknown / NotApplicable | attribute scan; framework registry |
| `imports` | Exact / Unknown | syntactic; resolved to artifacts |
| `expand(phase)` | term / Unknown | none; bounded steps |
| `order(group)` | Exact / Unknown | declared discipline; notebooks are user-driven history |
| `const_value`, `type_of`, `dispatch_targets`, `external_ref`, `entrypoints`, `binds` | per table | as declared |

Soundness contract: Must and Exact are only returned when the adapter
can prove uniqueness or completeness; May sets must contain the true
referents (over-approximation); otherwise Unknown. Two features gate
most of the interface: names (8 queries) and statically resolvable
references or calls (7 queries); they are the first two questions to
ask of any new language.

### 4.5 Theorem 3 (honesty)

(a) No total computable query on U decides a non-trivial property of
the behaviour of the programs its terms denote (Rice 1953). Exact call
targets under first-class values, termination, reachability of runtime
states, macro expansion termination, type inference for System F (Wells
1999) and type checking for dependent types with general recursion are
undecidable in general.

(b) Under the contracts of 4.1-4.4, every rule evaluated over U is
sound: it never emits an Error or Warn whose premise is false, and the
only cost of undecidability is Unresolved findings and widened bounds.

Proof. (a) Rice's theorem applied to any Turing-complete source
language, which includes U itself (2.1). (b) Induction on the rule
formula under Kleene logic, as in Theorem 2, with capability answers
treated as atoms whose soundness is the adapter's contract. QED.

What "computable" buys: where the source language's own type system
decides a question (Hindley-Milner inference, Rust trait resolution,
Haskell instance resolution without the undecidable extensions), an
adapter may run that decision procedure and promote precision (May to
Must). Where decidability holds only under a condition the adapter
cannot verify (dependent type checking under normalization), it must
verify or answer Unknown. Where it is undecidable, no adapter may claim
Must. The theorem does not and cannot prove that a given bind_L is
correct for its language; that is a per-language conformance
obligation discharged by the fidelity corpus (3.3).

## 5. The universal query interface

Forty-seven queries in five groups (full signatures and answer forms in
notes/research/lint-requirements.md section 3; summarized here so a rule
author can see the whole surface):

- Pure syntax (19): artifacts, parse_status, text and size, symbols,
  symbol_at / enclosing / following, kind, visibility, attributes, doc,
  comments, prose, import_decls, name_uses and call_sites, literals,
  members / params / fields, control (roles), opaque_regions, embedded,
  keys. All Theorem 2.
- Binding (7): binds_to, resolve_import, resolve_symref, package_of /
  module_path, const_value, type_of / dispatch_targets, external_ref.
  Scope graph plus capabilities.
- Graph (11): contains, edges(sym, kinds) where references are a
  superset of calls and `Instantiates` is a kind, referrers, closure /
  reaches, scc, select / owner, public_api (re-exports included),
  effects, test_items, binds (grimble), entrypoints.
- Digests (6): facet_digest over a canonical facet stream (not
  collapsed text) for Sig, Body, Doc, Attr; norm_sig; shape_digest;
  section / file / region digest; by_digest; at_revision / diff_symbols.
- Language escape (4): pattern (ast-grep shape), ts_query, ir_pattern,
  callee_vocab. An empty vocabulary is NotApplicable, never "no hits".

Mapping of landed rule families to queries: TODO (comments, directives),
DOC (attributes, doc, prose links, symbols), REF and TICK (directives,
ledger side input), INV (imports, attributes), COV (public_api,
test_items, reaches with May edges and the P- polarity), DRIFT and
AFFECT (facet digests, lock side input, referrers), TEST (directives,
test_items), SCOPE (locations against lease globs), EXC (directives,
digests), PARSE and DSL (comments and attributes), PROC (pattern),
CFG, GEN, PERF, TOOL (non-IR side inputs). grimble SYS, CAP, BIND, ARCH,
POL and the crunk families are mapped in the research note.

## 6. Paradigm coverage

For each family: units, binders and scope, apply edges and their status,
locations, first-adapter fidelity, and what is Unknown by nature. The
full matrix is notes/research/paradigms.md section 5; the worked
examples with per-rule outcomes are notes/research/lint-requirements.md
section 7.

| Family | Units | Scope graph | apply status | Location | Fidelity reachable | Unknown by nature |
|---|---|---|---|---|---|---|
| Imperative, OO class-based (C, Go, Java, C#) | module, type, function, method | lexical plus nominal members | Must for static calls; May for virtual dispatch (class hierarchy bound) | text | F4 | targets through reflection or function pointers |
| Multi-paradigm systems (Rust, C++, Swift) | plus impl/extension roles, generics | lexical, nominal, trait or template | Must within crate for free fns; May for trait methods and templates until instantiated; `phase` for macros | text | F4 (Rust today F3) | proc-macro output without expansion |
| Strict functional (OCaml, F#, Clojure, Elixir) | module, function, type | lexical; modules as scopes | Must for direct, May for higher-order | text | F4 | targets of first-class functions |
| Lazy functional, Haskell | module, function (signature + equations as roles), class, instance, family | lexical; instances resolved by type; `where` as nested scope | Must for direct calls; May over instances for class methods; Template Haskell as `phase` with opaque expansion | text | F3-F4 | instance selection with UndecidableInstances; TH-generated declarations (opaque may_define) |
| Dependent and proof assistants (Agda, Idris 2, Lean 4, Coq) | definition, inductive, instance, tactic block; mixfix notations as `phase`-declared syntax | lexical with implicit arguments as `bind(mode=implicit)`; QTT grades as modes | Must for named application; instance search May; tactic blocks `region` | text | F3 | elaboration results; termination; what a tactic produced |
| System F and the lambda cube as languages | anon terms, type abstraction as `bind(kind=type)` | de Bruijn or named, lexical only | Must (pure lexical) | text | F4 | type inference for F is undecidable; checking is syntactic given annotations |
| Logic and relational (Prolog, Datalog, miniKanren, SQL) | predicate (clauses as roles), rule, table, query | logic variables are clause-scoped `bind(kind=logic)`; unification is resolution with May; Datalog stratification gives Exact dependency graphs | May for Prolog goals (predicate by name/arity is Must; which clause matches is Unknown); Exact for Datalog and SQL references | text | F3 | call/N, assert/retract, cut semantics |
| Concatenative (Forth, Factor) | word | global dictionary scope (redefinable: May), stack effects as attributes | May by dictionary order; Unknown after runtime redefinition | text | F2-F3 | stack effects unless declared |
| Array (APL, J, BQN) | named function; tacit trains as `anon` | lexical; point-free has no parameters | references are a superset of calls; Must for named, structural for trains | text | F3 | rank polymorphism outcomes |
| Actor and process (Erlang, Pony) | module, function, process spec | lexical; message sends `apply(kind=send)` with May targets by registered name | May | text | F3 | which process receives |
| Dataflow, reactive, visual (Pd, LabVIEW, Scratch, Observable) | node or object (anon, positional identity), patch | wires are `apply(kind=dataflow)` with Must edges; no names | Must (graph is explicit) | graph | F3 | timing |
| Spreadsheets | cell (unit, address identity), named range, LAMBDA | cell references Must; indirect references May | Must / May | grid | F3 | INDIRECT, volatile functions |
| Notebooks (Jupyter) | cell (unit, index identity), definitions inside cells | implicit global scope across cells; `group(order=user-history)` | May (depends on execution order) | notebook | F2-F3 | which definition was live at run time |
| Hardware and shaders (Verilog, VHDL, GLSL) | module, always block (`region(kind=clocked)`), kernel | lexical; instantiation is `apply(kind=instantiate)` Must | Must | text | F4 | timing, synthesis |
| Quantum (Qiskit, Q#) | circuit (`region(kind=circuit)`), gate | lexical | Must for gate application | text | F3 | measurement outcomes |
| Config and data (Nix, Dhall, CUE, HCL, YAML templates) | attribute set, function, resource | lexical with lazy evaluation; templating as `phase` | Must within file; May across imports resolved by evaluation | text, pointer | F2-F3 | values that need evaluation |
| Markup and documents (Markdown, LaTeX, Typst, .grmb) | heading or section, macro, node | section nesting; LaTeX macros as `phase` | references by anchor Must | text (anchors) | F4 | none beyond macros |
| Build, shell, CI (Make, Bash, Bazel, Actions) | target, function, job, step | targets Must; shell variables dynamic (May) | May | text | F2-F3 | word splitting, eval |
| Term rewriting and homoiconic (Lisp, Racket, Mathematica) | definition; macros as `phase` | lexical after expansion; `phase` before | Must after bounded expansion else Unknown | text | F3 | unbounded expansion, eval |
| Esoteric 1D (Brainfuck, Whitespace, Unlambda) | one anonymous unit; brackets as `group(order=sequence)` | none | none | stream | F1 | everything else |
| Esoteric 2D (Befunge, Piet) | one unit per program; instruction pointer paths are not syntax | none | Unknown | grid | F0-F1 | control flow is runtime |
| Projectional and visual editors (Scratch, MPS) | node (generated id identity) | explicit references Must | Must | graph | F3 | none specific |

The table shows the two outcomes the owner asked for: every family maps
(no language falls outside U; the worst case is F0 with everything
Unresolved), and the families where structure is genuinely runtime
(Befunge, redefinable Forth, notebooks, Prolog clause selection) are
exactly where the model says Unknown rather than guessing.

### 6.1 Worked examples (condensed)

- Haskell `instance Show T where show = ...`: `unit(kind=instance,
  role=implementation)` with identity (class Show, type T); a call
  `show x` is `apply` whose head resolves May over the instances of
  Show in scope; COV001 for `show` of T counts a test reaching it only
  if the May set is a singleton or the test names it. A `$(derive ...)`
  splice is `phase(kind=th)` with `may_define = Unknown`, so every
  unresolved reference in the module becomes May, and DRIFT on symbols
  that may be TH-generated is Unresolved.
- Prolog `append([],L,L). append([H|T],L,[H|R]) :- append(T,L,R).`:
  one identity `append/3`, two `unit(kind=predicate, role=clause)`
  parts; body goals are `apply(kind=goal)` resolved Must to the
  predicate identity by name and arity, May to clauses; variables are
  `bind(kind=logic)` scoped per clause. REF, TODO and DOC work; COV
  needs a test convention (plunit) declared as a capability or it is
  NotApplicable.
- APL `avg <- +/ div tally` as a train: `unit(avg)` whose body is an
  `anon(kind=train)` with references (not calls) to the primitives and
  to `tally`; edges are Must; digests are over the canonical token
  stream, which also fixes the indentation-language problem.
- Jupyter notebook: units are cells with index identity; a definition
  in cell 3 used in cell 1 is a May edge because `group(order =
  user-history)`; frob reports COV and AFFECT as Unresolved unless the
  notebook records an execution order (then the adapter promotes to
  Must along that order).
- Spreadsheet: `Sheet1!B2` is `unit(kind=cell)` at grid location (1,2,2)
  with a formula body; `=SUM(A1:A9)` is `apply` with Must edges to nine
  cells; `=INDIRECT(C1)` is May over the sheet. Leases and scopes are
  ranges; digests are per cell.
- Verilog: `module m` is a unit; `always @(posedge clk)` is
  `region(kind=clocked)` with `group(order=concurrent)` outside and
  `sequence` inside; `m2 inst(.a(x))` is `apply(kind=instantiate)` Must;
  assignments carry an `attr(delayed)` for `<=`.
- Brainfuck: one `anon` unit, brackets as nested `group(order=sequence)`,
  everything else `lit`; F1; every rule except SCOPE and digests is
  NotApplicable, which the report shows as such.

## 7. Gaps in the landed code this model resolves

Found by reading the crates (lint-requirements.md section 9, G1-G19).
The first three must be settled before any consumer repository commits
a `frob.lock`, because they change digests:

- G7: outer attributes are outside the sig digest, so `#[deprecated]`
  or `#[pyfunction]` changes are invisible to DRIFT. Fix: an Attr facet
  and attributes in the canonical sig stream.
- G8: comments inside a body, including `frob:` directives, change the
  body digest. Fix: digests over the canonical facet stream with trivia
  excluded (v1 behaviour).
- G9: a markdown heading's body digest includes nested subsections, so a
  child edit changes every ancestor. Decide: section-local body plus a
  separate subtree digest.
- G1-G4: unresolved calls are dropped instead of poisoning callers;
  "Resolved" means unique name in the crate with no status field;
  a function passed as a value is no edge. Fix: edge status Must | May
  | Unknown and references as a superset of calls.
- G10, G11, G19: public_api ignores re-exports; partial parses are
  invisible to rules (parse_status must be a query and a `hole`);
  any non-Rust file looks like an empty one instead of F0 opaque.
- Directive binding assumes a comment that starts a line; languages
  without line comments need the `attr` path.
- Whitespace-collapsed normalization is wrong for indentation-sensitive
  languages; the canonical facet stream replaces it.

## 8. Consequences for crates (milestone 2)

- gob-ir: Tm(Sigma_U + Sigma_L), the scope graph with edge status, the
  alpha-normal printer and canonical facet stream, the FO+LFP evaluator
  with Kleene semantics and polarity, the answer lattice types.
- gob-languages: location sorts; the F0 constant parser; rho_L checked
  against node-types.json at build time.
- gob-symbols: becomes the Rust and markdown F3/F4 adapter over U;
  SymbolRecord is the `unit` view; its call graph becomes
  `apply_targets` at precision "by name within project, May".
- gob-directives: binds to `comment` and `attr` nodes; drops the
  line-start assumption where the language has no line comments.
- gob-rules: `Finding` keeps Unresolved; rules declare polarity; the
  derive gains `polarity = P+ | P- | P0 | Pn | Pc`.
- frob doctor: `--languages` prints fidelity and capability precision;
  the README table is generated from it.
- grimble capability matrix: an `n/a` cell is a declared Unknown and is
  reported as Unresolved, never clean (code-model.md section 7).

## 9. Open questions for the owner

1. Is `apply(kind=dataflow)` enough for dataflow, reactive and
   spreadsheet edges, or does a rule need a separate universal relation?
   No landed or designed rule distinguishes them today.
2. Anonymous units: positional identity (stable under internal edits,
   unstable under sibling reordering) or content identity (Unison
   style; stable under moves, collides on duplicates)? Leases and acks
   depend on the choice.
3. Should "language support" in the README be generated from `frob
   doctor --languages` so the claim can never exceed the measured
   fidelity?
4. The research notes were written without web access. Before this
   file is accepted, the `[verify]` items in the three notes should be
   checked, in particular the decidability citations the theorems rely
   on (Rice, Wells, Immerman and Vardi).
