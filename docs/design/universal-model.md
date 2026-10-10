# The universal structural model (gob-ir)

Status: current
Owner: gob
Decisions: D56
Audience: contributor

Provenance: DRAFT under T-0001; decision D56 is accepted (2026-10-04) and this
file supersedes code-model.md section 5 (now a pointer here). Evidence: notes/research/paradigms.md (202
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
2. Identities: every `unit` has a stable identity anchored on its
   symref and separate from its content (grimble-model.md 9.2: a rename
   is a new identity whose body facet equals a vanished one; a change is
   the same identity with a new facet). Adapters may anchor identity
   differently where the language does (Unison hashes, cell addresses,
   generated node ids). The content hash is a facet of the identity, not
   the identity. Symrefs (2.6) are the human names of identities.
3. The resolution relation: a scope graph (scopes, declarations,
   references, labelled edges) built by the adapter's declared binding
   discipline. Each resolution edge carries a status Must | May |
   Unknown. Lexical nesting is one derived view of it; unification,
   dynamic dispatch, dictionary lookup and late binding are others, at
   lower status.
4. Opaque: `opaque(reason, payload)` at any sort. Every structural and
   binding query returns Unknown or NotApplicable on it; nothing is ever
   computed through it. The one exception is lexical facts, which are
   exact: the `text`, `literals` and `prose` queries (section 5) read the
   opaque payload's bytes, so a rule that scans text (CI007 over a shell
   `run:` body, DK004, secret literals) works on an opaque region and its
   "clean" claim is stated over the scanned set (4.2).
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
morphism, so the universal structural rules of grimble-lints ("sort
inside a loop"; rules.md section 3, level 2) still have something to
match without U committing to control flow semantics.

### 2.5 Locations are not byte offsets

A location is a value of an adapter-declared address sort with a total
order and a containment relation: text (artifact, byte range); grid
(sheet or board, row, column); graph (document, node id, port); stream
(artifact, sequence number); notebook (notebook, cell, byte range);
pointer (artifact, JSON pointer). Digests, spans, snippets, leases and
scopes are defined over locations. Markdown anchors are the first
non-byte address already in use.

### 2.6 Symrefs over identities

The authoritative grammar is the EBNF in code-model.md section 2
(locators, roles, anonymous-unit indexes); this section states only the
model it serializes. A symref names an identity: `<locator>::<Qual>.<Name>`
where the locator is a path for file-based languages, `path#slug` for
documents, `path#cell=A1` or `notebook#cell=7` for grid and cell
sources, and an adapter-declared locator otherwise. Multi-part units
(Prolog clauses of one predicate, Haskell signature plus equations,
partial classes) resolve to ONE identity and one symref (this is not
the ambiguity error of code-model.md section 2); their parts are `unit`
nodes with roles. Anonymous units get the enclosing symref plus a
positional index computed on the alpha-normal form (stable under edits
inside the unit, not under reordering of anonymous siblings; see open
question 2, which gates leases and acks for anonymous units).

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
precisions plus, once per language, the rules that are NotApplicable
there (4.2); the README's language table is generated from it (open
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
  skip rather than nag. It is a QUERY ANSWER only and never a finding.

Predicates use Kleene's strong three-valued logic over Yes/No/Unknown.
Resolution returns Must(x) | May({x1..xn}) | Unknown.

Glossary (one meaning per word across the design set): Unknown is a
query answer; Unresolved is a finding severity (orthogonal to the
Error/Warn/Advisory threshold, see 4.2 and cli.md section 2);
UnresolvedExit is an exception state (exceptions.md); Unmeasured is an
evidence verdict (tickets.md section 9); NotApplicable is a query answer
and a capability-cell state, never a finding.

### 4.2 Rule polarity and subject accounting

A rule declares its polarity, which fixes which bound it may fire on
and which bound lets it certify clean. This table is the authoritative
copy (notes/research/lint-requirements.md section 3.2 is the evidence):

| Polarity | Rule shape | Fires when | Certified clean when | Else |
|---|---|---|---|---|
| P+ presence | forbidden import, secret literal, broken link, undeclared capability | an offender is in `lo` | no offender in `hi` | Unresolved, listing `hi` minus `lo` as the maybe-set |
| P- absence | undocumented public, untested, dead, selector matches nothing, grant never observed | `hi` contains no good thing | `lo` contains a good thing | Unresolved |
| P0 equality | digest drift, set equality, signature equality | both sides `Exact` and differ | both `Exact` and equal | Unresolved if either side is not `Exact` |
| Pn threshold | `lines > N` (max-type), fewer than N tests (min-type) | max-type: measured `lo > N`; min-type: `hi < N` | max-type: `hi <= N`; min-type: `lo >= N` | Unresolved |
| Pc closure | a cycle exists, A reaches B | a path inside `lo` edges | no path inside `hi` edges | Unresolved naming the poisoned frontier |

Consequences, stated once. Over-approximated edges (name-only,
ambiguous candidates) are legal for P- rules and "affects" lists and
illegal as the sole basis of a P+ finding; under-approximated edges are
the reverse. A rule receives an `Answer<Set>`, never a bare set, and
the framework applies the table, so "the adapter could not see X and
the rule read that as none" cannot be written. A May edge elsewhere in
a crate does not make a Pc or Pn rule Unresolved when its own bound
already decides (a Must-edge cycle fires CYCLE; a 400-line function
fires NEAT001 even with one unexpanded macro, because `lo` already
exceeds N); only P0 requires Exact on both sides.

Subject accounting. Every rule outcome carries `subjects_examined` and
its Unresolved sites.
- A subject whose answer is Unknown is unexamined: the rule reports
  Unresolved (rolled up per rule and artifact, naming the reason code),
  never clean.
- A subject whose answer is NotApplicable is excluded from the subject
  set. A rule whose whole scope is NotApplicable in a language emits no
  findings at all; it is listed once per language in the fidelity report
  (`frob doctor --languages` and the check summary) as not applicable.
  A Markdown-only repository therefore carries no permanent Unresolved
  for code rules, and a CSS-only node no Unresolved for `net.connect`.
- A rule that examined zero subjects over a scope that was not wholly
  NotApplicable (every query Unknown) reports Unresolved("vacuous"),
  never clean. This closes the silent pass of "public symbol with no
  test" on a language without a test convention.
- A rule whose scope contains an opaque subject reports no Error or
  Warn on it and one Unresolved naming the reason code (P+ and P- alike;
  4.6); only a rule whose scope holds no opaque subject certifies clean.

The gate. Unresolved is a finding severity orthogonal to the
Error/Warn/Advisory threshold; the one mechanism by which it can fail
a run (`[check] fail_on_unresolved`, the three `required` cases, exit 1)
is defined in cli.md section 2 and is not restated here. A rule flagged
`must_measure` in its derive is one of the three required cases when it
examined zero subjects.

Exceptions and Unresolved. An Unresolved finding can be parked only by
`defer` (with a ticket) or `baseline`, never by `accept`: accepting a
loud "could not examine" would silence the failure without the
declaration that fixes it (EXC016, exceptions.md section 6). A site
whose rule outcome was Unresolved is never STALE (exceptions.md
section 3).

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
containment, lexical binding, occurrences, attachments, the facet
digests (7.1), and the graph digest.

### 4.4 Capabilities

Facts that are not syntactic come only through declared capabilities
with a precision (section 5 is the 47-query table; the 33 that need a
language feature each name it in the research note):

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
| `project_model` | packages, file ownership, package edges, aliases: Exact / Unknown; an import outside every package is Unknown with reason External or Unbound | manifest (Cargo, pyproject, .sln/.csproj, package.json workspaces with tsconfig paths and extends); language-engines.md 2 |
| `markup`, `style` | element and declaration views over U (section 5.1): attributes and `var()` references at May, spreads May, computed values Unknown | adapter lowering (TSX/JSX first); language-engines.md 2 |

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

### 4.6 Computability by construction: annotate or be opaque

Theorem 3 says what cannot be decided. This subsection says what the
tool does about it, and it is a rule, not a hope: wherever a query's
precision depends on information that is undecidable to infer but
cheap to declare, the adapter REQUIRES the declaration and treats its
absence as `opaque` with the reason `annotation-required`. The finding
that results is loud (an Unresolved with a remedy naming the exact
annotation), never a silent widening to May.

Instances, each a materialized knob under `[compute]` so a repository
can tighten or loosen it explicitly (no invisible variables). The keys
are `public_signatures`, `effects`, `dynamic_calls`, `expansion_steps`,
`normalization` and `notebook_order`; every key except `expansion_steps`
(an integer step budget) takes `"warn-unresolved"` (the default: the
declaration is absent, the site is opaque and reported Unresolved, not
required) or `"required"` (an absent declaration is a required
Unresolved that fails the gate, cli.md section 2). The table with
defaults is in architecture.md section 6; `[compute]` has one home and
is read identically by every product (architecture.md section 6):

| Question | Undecidable or expensive without | Required declaration | Reason code |
|---|---|---|---|
| Types of public items in languages with inference | System F-style inference (Wells 1999); whole-program HM | type annotations on the public surface (`[compute] public_signatures`) | `annotation-required:signature` |
| Purity or honesty of a function (section 5 of notes/research/neatness.md) | effect inference in a language without an effect system | a language-native effect marker where one exists (Verse specifiers, D `pure`, Nim `func`, Rust `const fn`, Haskell types) or a `frob:effects ...` directive (`[compute] effects`) | `annotation-required:effects` |
| Targets of dynamic dispatch, reflection, `eval`, late binding | runtime state | a `frob:calls <symref>...` directive on the call site or an adapter capability at May precision (`[compute] dynamic_calls`) | `dynamic:unresolvable` |
| Macro and template expansion | termination of expansion (Veldhuizen 2003 for templates) | expansion within the adapter's step budget (`[compute] expansion_steps`), else the `phase` node stays unexpanded | `expansion:budget` |
| Dependent type checking | normalization of open terms with general recursion | the language's own termination checker must accept the definition; otherwise the body is opaque (`[compute] normalization`) | `normalization:unverified` |
| Notebook and spreadsheet evaluation order | the user's execution history | a recorded execution order (notebook metadata) or declared dependency order (`[compute] notebook_order`) | `order:unrecorded` |
| Shell and build-script word splitting, `eval`, dynamic includes | string semantics at run time | none possible; the region is opaque and the enclosing unit's edges are May | `dynamic:string-code` |

Rules read the reason code and degrade with it: on an opaque subject a
P+ rule reports no Error or Warn (it cannot prove an offender) and
reports one Unresolved, rolled up per rule and artifact, naming the
reason code and the remedy; a P- rule does the same; only a rule whose
scope contains no opaque subject certifies clean, so a repository that
wants the rule to certify clean must add the declaration. An
`annotation-required` opaque on the public surface is a required
Unresolved when the matching `[compute]` key is `"required"`; with
`"warn-unresolved"` it is reported and counted but does not fail. This
is the mechanical form of
"require type annotations": the cost of analysis is paid once, in the
source, where a reader benefits from it too, and the analysis stays
polynomial because it never infers what it can read.

## 5. The universal query interface

Forty-seven queries in five groups: pure syntax 19, binding 7, graph 11,
digests 6, language escape 4. This table is the interface (notes/research/lint-requirements.md
section 4 keeps the full signatures as evidence). Kind: `syntactic` is
total on any language with a grammar (Theorem 2); `capability` is
gated by the adapter's declaration and may answer NotApplicable or
Unknown; `lexical` is exact over an opaque payload's bytes (2.2 item 4).

| Id | Query | Group | Answer form | Kind |
|---|---|---|---|---|
| Q01 | `artifacts()` | syntax | Exact | syntactic |
| Q02 | `parse_status(a)` | syntax | Exact (Ok, Partial, Failed, NoText, Unsupported) | syntactic |
| Q03 | `text(loc), size(a, unit), line_col` | syntax | Exact or None; reads an opaque payload | lexical |
| Q04 | `symbols(a)` | syntax | Exact, or Bounds when macros or splices may hide symbols | syntactic |
| Q05 | `symbol_at, enclosing, following` | syntax | Option of symbol | syntactic |
| Q06 | `kind(sym)` | syntax | Exact (closed core plus escape) | syntactic |
| Q07 | `visibility(sym)` | syntax | Yes/No/Unknown/NotApplicable | capability |
| Q08 | `attributes(sym)` | syntax | Exact | capability |
| Q09 | `doc(sym)` | syntax | Exact | capability |
| Q10 | `comments(a), comments_near` | syntax | Exact | capability |
| Q11 | `prose(a): headings, links, fences, spans, tables` | syntax | Exact; reads an opaque payload | lexical |
| Q12 | `import_decls(a)` | syntax | Exact | capability |
| Q13 | `name_uses(scope), call_sites` | syntax | Exact (classification may be unclassified) | capability |
| Q14 | `literals(scope, kind)` | syntax | Exact; reads an opaque payload | lexical |
| Q15 | `members, params, returns, fields` | syntax | Exact | capability |
| Q16 | `control(sym): loop and branch roles, nesting` | syntax | Exact | capability |
| Q17 | `opaque_regions(scope)` | syntax | Exact (an empty answer is a claim the adapter makes) | syntactic |
| Q18 | `embedded(a)` | syntax | Exact | capability |
| Q19 | `keys(a) for TOML, JSON, YAML` | syntax | Exact | syntactic |
| Q20 | `binds_to(use)` | binding | One, Candidates, External or Unknown | capability |
| Q21 | `resolve_import(decl)` | binding | Internal, External, Candidates or Unknown | capability |
| Q22 | `resolve_symref(text)` | binding | One, Ambiguous or NotFound | syntactic |
| Q23 | `package_of, module_path` | binding | Option | capability |
| Q24 | `const_value(expr)` | binding | Known or Unknown | capability |
| Q25 | `type_of, impls_of, dispatch_targets` | binding | Bounds | capability |
| Q26 | `external_ref(use or import)` | binding | Option of package, version, item | capability |
| Q27 | `contains, parent, ancestors` | graph | Exact | syntactic |
| Q28 | `edges(sym, kinds)` | graph | Bounds with Must/May/Unknown status | capability |
| Q29 | `referrers(target, kinds)` | graph | Bounds | capability |
| Q30 | `closure, reaches` | graph | Bounds, or Yes/No/Unknown with the frontier | capability |
| Q31 | `scc(kinds, scope)` | graph | Bounds | capability |
| Q32 | `select(selector), owner(sym)` | graph | Bounds; One, Ambiguous or Foreign | capability |
| Q33 | `public_api(scope), re-exports included` | graph | Bounds | capability |
| Q34 | `effects(sym)` | graph | Bounds over the atom registry | capability |
| Q35 | `test_items(scope)` | graph | Exact or Bounds; NotApplicable without a convention | capability |
| Q36 | `binds(sym) (grimble supplies)` | graph | Bounds | capability |
| Q37 | `entrypoints(scope)` | graph | Exact | capability |
| Q38 | `facet_digest(sym, Sig, Body, Doc, Attr, Contract)` | digests | Exact, Absent or Unknown | syntactic |
| Q39 | `contract(sym): the normalized language-neutral signature` | digests | Exact or Unknown | capability |
| Q40 | `shape_digest(sym, rung), defuse` | digests | Exact | capability |
| Q41 | `section_digest, file_digest, region_digest` | digests | Exact | syntactic |
| Q42 | `by_digest(facet, d)` | digests | Exact | syntactic |
| Q43 | `at_revision(rev), diff_symbols(old, new)` | digests | Exact | syntactic |
| Q44 | `pattern(scope, lang, pat) (ast-grep shape)` | escape | Exact with respect to the tree | syntactic |
| Q45 | `ts_query(scope, scm)` | escape | Exact | syntactic |
| Q46 | `ir_pattern(scope, pat) over U operators and role attributes` | escape | Exact over mapped operators | capability |
| Q47 | `callee_vocab(lang, class)` | escape | Exact; empty is NotApplicable, never no hits | capability |

Notes. Edges are `Calls` a subset of `References`, with kinds
`Contains, Imports, Calls, References, Instantiates, Extends, Binds`;
`Instantiates` is a kind, and `public_api` includes re-exports.
Facet digests are defined over a canonical facet stream, never over
collapsed text (section 7). Two features gate most of the interface:
names (8 queries) and statically resolvable references or calls (7);
they are the first two questions to ask of any new language. The 33
queries that need a language feature each name it in the research
note.

Mapping of landed rule families to queries: TODO (comments, directives),
DOC (attributes, doc, prose links, symbols), REF and TICK (directives,
ledger side input), INV (imports, attributes), COV (public_api,
test_items, reaches with May edges and the P- polarity), DRIFT and
AFFECT (facet digests, lock side input, referrers), TEST (directives,
test_items), SCOPE (locations against lease globs), EXC (directives,
digests), PARSE and DSL (comments and attributes), PROC (pattern),
CFG, GEN, PERF, TOOL (side inputs outside U). grimble SYS, CAP, BIND, ARCH,
GPOL, NEAT and the crunk families, and the CI and DK families, are
mapped in the research notes and in neatness.md and cicd.md.

### 5.1 Web-engine queries (D96)

Four capability queries extend the table for markup, style and constant
facts (language-engines.md section 2). They are answer types and queries
in `gob-ir` (`markup`, `style`, `const_value`); adapters lower into the
forms below and every product reads them through GRL.

| Id | Query | Answer form | Kind |
|---|---|---|---|
| Q48 | `markup`: elements (tag, kind intrinsic / component / unknown), attributes, children, text | Exact per element; an attribute spread is an attribute at status May | capability |
| Q49 | `style`: rules (selector), declarations (property, raw value, component values), at-rules, custom properties, `var()` references | Exact; a `var()` reference is May (the cascade decides) | capability |
| Q50 | `const_value(expr)` | Known, OneOf, Fragments (known parts and Unknown rest) or Unknown, within a step budget (default 256) | capability |
| Q51 | `class_tokens(attr)`, derived from Q48 and Q50 | Known tokens (Must, or May through `clsx`, `cn`, `classnames`, `classNames` matched by name) plus a dynamic flag | derived |

Lowering into U, using the thirteen universal operators plus two
`Sigma_L` families (`markup`, `style`):

- element: `apply(element)`, child 0 the head: `lit(tag, name)` for an
  intrinsic tag, `ref(name)` for a component (so a use is a reference
  edge), anything else is an unknown tag; remaining children are
  attributes, `lit(text)`, child elements and expressions;
- attribute: `markup.attribute` named after the attribute, optional child 0
  the value (absent means `true`); spread: `markup.spread` over the
  expression, status May;
- style rule: `unit(style-rule)` named by its selector; at-rule:
  `unit(at-rule)` with attribute `prelude`; custom property:
  `unit(custom-property)` named `--x`; declaration: `style.declaration`
  named by its property with attributes `raw` and `important`; component
  values are `lit(kind)` children, `var(--x)` a `ref(--x)`;
- const forms: `lit(str|int|bool|null)`, `ref` to a `unit(const)`, and
  `apply(op)` with head `lit(op, lexeme)` for `+`, `?:`, `&&`, `template`,
  `array`, `object` (entries `prop`).

The declaration and attribute use `Sigma_L` operators rather than `bind`
because `bind` scopes over child 0 (2.3) and these are named arguments
and properties, not binders.

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
  NotApplicable: it emits no findings and the fidelity report lists it
  once for the language (4.2).

## 7. Gaps in the landed code this model resolves

Found by reading the crates (lint-requirements.md section 9, G1-G19).
The first three (G7-G9, the digest scheme of 7.1) must be settled
before any consumer repository imports a `frob.lock`, because they
change digests:

- G7: outer attributes are outside the sig digest, so `#[deprecated]`
  or `#[pyfunction]` changes are invisible to DRIFT. Fix: an Attr facet
  and attributes in the canonical sig stream.
- G8: comments inside a body, including `frob:` directives, change the
  body digest. Fix: digests over the canonical facet stream with trivia
  excluded (v1 behaviour).
- G9: a markdown heading's body digest includes nested subsections, so a
  child edit changes every ancestor. Proposed: section-local body plus a
  separate subtree digest; this is open question 5 and blocks the
  scheme-2 freeze.
- G1-G4: unresolved calls are dropped instead of poisoning callers;
  "Resolved" means unique name in the crate with no status field;
  a function passed as a value is no edge. Fix: edge status Must | May
  | Unknown and references as a superset of calls.
- G10, G11, G19: public_api ignores re-exports; partial parses are
  invisible to rules (parse_status must be a query and a `hole`);
  any non-Rust file looks like an empty one instead of F0 opaque.
- Directive binding assumes a comment that starts a line; languages
  without line comments need the `attr` path.
- The whitespace-collapsed normalization of digest scheme 1 (code-model.md
  section 2, D43) is wrong for indentation-sensitive languages; it is
  superseded by the canonical facet stream of 7.1.

### 7.1 The digest scheme (scheme 2, authoritative)

- Digests are BLAKE3 over the adapter's canonical facet stream: the
  alpha-normal token stream of the facet with trivia (whitespace and
  comments, including `frob:` directives) excluded and with literals
  kept exact. Reformatting never changes a digest; a token change
  always does; indentation-sensitive languages are handled because the
  stream carries structure, not collapsed text.
- Facets: Sig, Body, Doc, Attr and Contract. Sig is the declared
  signature including outer attributes' effect on it; Attr is the
  attribute and decorator set of the unit (G7); Doc is the doc comment
  or docstring; Body is the unit's content; Contract is the normalized,
  language-neutral rendering of the signature (name, parameters with
  types over the cross-language lattice, return, visibility, async,
  generics), the input of SYS006 contract skew. Contract replaces the
  earlier separate normalized-signature query. A facet the unit lacks is Absent.
- The lock records `digest_scheme` (gob-lock, code-model.md section 2);
  scheme 1 is the three-facet text scheme of milestone 1 (D43, superseded as
  the facet scheme).
  Changing the scheme makes every entry stale (DRIFT, re-ack required)
  and reports why through the recorded scheme; it never silently
  rewrites a digest.
- Consumer `frob.lock` import (migration.md) happens only after the
  scheme is final (open question 5 closed); this repository's own
  `frob.lock` is empty today and is regenerated at that point.

## 8. Consequences for crates (milestone 2)

Layering (D56, restated by boundaries.md and architecture.md):
gob-languages < gob-ir < gob-symbols < gob-directives < the frob and
grimble crates. gob-ir sits BELOW gob-symbols because the adapters that
produce U terms live in gob-symbols; frob links gob-ir (digests, COV
polarity over May edges, the CI and DK adapters). Milestone order is
the one statement in build-test-ci.md, Milestone 2; it is not repeated
here.

- gob-ir: Tm(Sigma_U + Sigma_L), the scope graph with edge status, the
  alpha-normal printer and canonical facet stream (7.1), the query
  interface of section 5, the FO+LFP evaluator with Kleene semantics
  and polarity, the answer lattice types, the atom registry and the
  callee vocabularies (grimble-model.md 9.6). Depends on gob-text and
  gob-languages only.
- gob-languages: location sorts; the F0 constant parser; rho_L checked
  against node-types.json at build time; the Actions and Dockerfile
  grammars and readers behind features `actions` and `dockerfile`
  (cicd.md).
- gob-symbols: becomes the Rust and markdown F3/F4 adapter over U (and
  hosts the Actions and Dockerfile adapters); SymbolRecord is the
  `unit` view; its call graph becomes `apply_targets` at precision "by
  name within project, May".
- gob-directives: binds to `comment` and `attr` nodes; drops the
  line-start assumption where the language has no line comments.
- gob-rules: `Finding` keeps Unresolved and gains `subjects_examined`,
  `source_rule` and a `location`; rules declare polarity and needs; the
  derive gains `polarity = P+ | P- | P0 | Pn | Pc` (rules.md section 2).
- Locations (2.5) are not byte offsets, but `Finding` and
  `FindingRecord` are. The change set: gob-text keeps `TextRange` for
  text locations; gob-rules defines a `Location` enum with text,
  pointer, grid and graph variants; gob-diagnostics' `FindingRecord`
  replaces its file, line, column triple with a `location` object (the
  triple stays as a derived text view); SARIF maps pointer, grid and
  graph locations to `logicalLocations`.
- Parse artifact cache keys (architecture.md section 2, code-model.md
  section 8) gain a digest of the `[compute]` configuration, and the
  scope graph is a repository-scope artifact keyed by the graph digest,
  because both change U terms.
- frob doctor: `--languages` prints fidelity, capability precision and
  the per-language NotApplicable rule list (3.3, 4.2); the README table
  is generated from it.
- grimble capability matrix: a `not-applicable` cell (the adapter's
  detector declares the capability impossible, such as CSS and network)
  is reported in the matrix and is never Unresolved; an `unknown` cell
  is Unresolved (grimble-model.md 9.6).

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
5. Digest scheme G9: should a markdown heading's body digest be
   section-local with a separate subtree digest (proposed in 7), or
   remain subtree-inclusive? This blocks freezing digest scheme 2 and
   therefore any consumer `frob.lock` import (7.1, migration.md).
