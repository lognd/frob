# Programming-language paradigms and the structure a universal model must carry

Status: research note for code-model.md sections 2-5 and goals.md. Written
2026-10-02 from the author's knowledge; no web fetches were made (see
section 9 for what is unverified). ASCII only.

Reading guide. Section 1 is the checklist (the denominator). Section 2
holds cross-cutting decidability facts so the per-family answers can be
short. Section 3 answers the nine-question questionnaire per family:

  Q1 units of structure     Q2 binding and scope     Q3 evaluation and control
  Q4 types                  Q5 effects and boundaries Q6 calls and dependencies
  Q7 metaprogramming        Q8 syntax shape          Q9 linter: decidable vs not

Section 5 is the feature x paradigm table, section 6 the 10 features a
universal model must represent natively, section 7 the concrete gaps in
the current IrKind / symref / capability design.

## 0. Method

1. Phase 0 (breadth): the full list of languages named in the task, plus
   every family I could add, was written down first (section 1) before any
   family was analysed.
2. Phase 1 (drain): each family was taken one at a time with the same
   questionnaire; a language that revealed a structural feature not yet in
   the running feature list added a row to the synthesis table (the rows
   were grown, not fixed in advance; origin of each late row is noted).
3. Phase 2 (prove): section 4 lists languages checked that added nothing,
   and section 1 is reconciled against section 3 by a count (end of
   section 1).

"Structural feature" means something an IR must carry to represent the
program's shape without executing it: a kind of unit, a kind of binder, a
kind of edge, a phase, a region, an ordering discipline, a locator.

## 1. Checklist (denominator)

Each item is `[x] Name` with the family id where it is analysed. Items
marked (ext) are language extensions or sub-systems the task listed
separately.

F01 imperative/procedural: [x] C [x] Go [x] Zig
F02 object-oriented and prototype: [x] Java [x] C# [x] Smalltalk [x] Self [x] JavaScript
F03 multi-paradigm systems: [x] Rust [x] C++ [x] Swift [x] Kotlin [x] Scala
F04 functional strict: [x] OCaml [x] SML [x] F# [x] Clojure [x] Elixir
F05 functional lazy: [x] Haskell [x] GADTs(ext) [x] TypeFamilies(ext) [x] DataKinds(ext) [x] LinearTypes(ext) [x] Backpack(ext)
F06 dependent/proof assistants: [x] Agda [x] Lean4 [x] Coq/Rocq [x] FStar [x] ATS
F07 logic/relational: [x] Prolog [x] Mercury [x] Datalog [x] miniKanren [x] ASP [x] SQL
F08 concatenative: [x] Forth [x] Factor [x] Joy [x] PostScript
F09 array: [x] APL [x] J [x] K/q [x] BQN [x] Uiua
F10 actor/process: [x] Erlang/OTP [x] Pony [x] Akka
F11 dataflow/reactive/visual: [x] LabVIEW [x] Max/MSP [x] PureData [x] Scratch [x] Excel/LAMBDA [x] Observable
F12 hardware and shaders: [x] Verilog [x] VHDL [x] Chisel [x] GLSL [x] HLSL [x] WGSL [x] CUDA
F13 quantum: [x] Qiskit [x] Qsharp [x] Quipper
F14 configuration/data: [x] Nix [x] Dhall [x] CUE [x] Jsonnet [x] Starlark [x] YAML-templating [x] TOML [x] HCL
F15 markup/document: [x] Markdown [x] LaTeX [x] Typst [x] HTML
F16 build and shell: [x] Make [x] Bash [x] Nushell [x] PowerShell
F17 notebooks: [x] Jupyter
F18 term rewriting/homoiconic: [x] Lisp [x] Racket [x] Mathematica [x] Maude [x] Pure
F19 esoteric: [x] Brainfuck [x] Befunge [x] Malbolge [x] Whitespace [x] INTERCAL [x] Piet [x] Unlambda [x] LambdaCalculus [x] SKI [x] Iota [x] Jot [x] BLC
F20 newer weird-type: [x] Idris2 [x] Granule [x] Koka [x] Effekt [x] Unison [x] Dark [x] Kind [x] HVM [x] Mojo [x] Carbon [x] Vale [x] Austral [x] Flix [x] Verse [x] Roc [x] Gleam [x] Grain [x] Hazel [x] Cedar [x] Rego [x] Lustre [x] Esterel

Families I added (not in the task list), each analysed in section 3:

F21 scripting/dynamic: [x] Python [x] Ruby [x] Perl [x] PHP [x] Lua [x] Tcl [x] R [x] Julia [x] Raku
F22 legacy/enterprise/record-oriented: [x] COBOL [x] Fortran [x] PLI [x] RPG [x] ABAP [x] JCL [x] Ada/SPARK [x] Pascal/Delphi [x] Eiffel
F23 smart contracts: [x] Solidity [x] Move [x] Vyper [x] Cairo
F24 specification and verification: [x] TLA+ [x] Alloy [x] Dafny [x] Why3 [x] Isabelle [x] ACL2 [x] Twelf [x] P
F25 assembly and low-level IR: [x] x86-asm [x] LLVM-IR [x] WebAssembly [x] MLIR [x] JVM-bytecode [x] eBPF
F26 schema/IDL/query: [x] Protobuf [x] GraphQL [x] OpenAPI [x] JSON-Schema [x] SPARQL [x] Cypher [x] XSLT/XPath
F27 PLC/industrial: [x] IEC61131-3 (LD FBD ST IL SFC) [x] Simulink [x] Node-RED
F28 probabilistic/differentiable: [x] Stan [x] Pyro [x] WebPPL [x] JAX [x] Triton [x] Halide [x] Futhark
F29 constraint/solver: [x] MiniZinc [x] SMT-LIB [x] CLP(FD) [x] CHR [x] regex
F30 pattern/rule languages (meta): [x] CodeQL [x] Semgrep [x] Coccinelle [x] ast-grep [x] Stratego [x] K-framework
F31 visual/structure-editor extras: [x] UnrealBlueprints [x] Grasshopper [x] Sonic-Pi-like live-coding [x] Logo
F32 CI/build extras: [x] CMake [x] Bazel [x] Dockerfile [x] GitHubActions [x] Gradle [x] Just/Ninja [x] Pkl/KCL/Nickel/Bicep
F33 other typed-functional: [x] Elm [x] PureScript [x] ReScript [x] Idris1 [x] Dylan/CLOS [x] Rebol/Red [x] Io [x] Eff/OCaml5-effects

Count reconciliation is at the end of section 4 (computed with grep over
this file, not typed by hand).

## 2. Cross-cutting decidability baseline

These are the standard results every per-family Q9 leans on. A structural
linter that never runs code works with syntactic facts plus sound or
heuristic approximations; the facts below mark where approximation is
forced.

Rice-type limits (any Turing-complete language, so almost all of them):
- Exact call graph: undecidable once there are higher-order values,
  dynamic dispatch, eval, reflection, or computed names. Best static
  answer is an over-approximation (class-hierarchy, points-to, 0-CFA).
  Hence frob's edge confidence lattice is not a convenience but forced.
- Reachability, dead code, "function is never called", termination,
  purity, "no side effect", "raises X": all undecidable in general;
  decidable only on annotated or restricted fragments.
- Recursion detection: direct self-call decidable; mutual recursion
  through higher-order values or dispatch is not.
- Exact name resolution: decidable for lexical scope; undecidable (or
  stage-dependent) with eval, `with`, dynamic scope, macros that
  introduce binders, reader macros, or runtime `op/3`.
- Parse itself: undecidable or runtime-dependent for Perl 5, C++ (needs
  template/type knowledge: `a<b>c`), LaTeX/TeX (catcodes), Forth (parsing
  words), Prolog (`op/3`), Common Lisp (reader macros), Racket (`#lang`
  reader), Raku (user grammars), Bash (aliases, `shopt`), Haskell (layout
  rule uses parser feedback; fixity resolved after parse).

Type-system decidability (checking vs inference):
- Simply typed lambda calculus: checking and inference decidable.
- Hindley-Milner (ML, Haskell 98 core): inference decidable (DEXPTIME-
  complete in the worst case, linear in practice).
- System F: type checking with annotations decidable; inference
  undecidable (Wells 1994). Hence RankNTypes needs annotations.
- System F-omega / higher-kinded: checking decidable; full inference
  needs annotations; kind inference is decidable for plain kinds.
- Bounded quantification F<: : subtyping undecidable (Pierce 1994); Java
  generics subtyping undecidable (Grigore 2017); Scala, Kotlin variance
  corners likewise. TypeScript's type language is Turing-complete.
- C++ templates, Haskell type families with UndecidableInstances, Rust
  trait resolution (without recursion limit), Scala implicits, Lean/Coq
  typeclass resolution: type checking can diverge; compilers impose
  fuel/recursion limits, so "does it typecheck" is semi-decidable with an
  arbitrary cutoff.
- Dependent types (MLTT, CoC): checking decidable when the theory is
  strongly normalizing; elaboration (implicit-argument and universe
  unification) involves higher-order unification, undecidable (Huet 1975)
  so elaborators use heuristics (Miller patterns). `Type : Type` makes
  checking undecidable.
- Linear/affine/uniqueness: checking decidable (it is a usage analysis).
- Refinement / liquid types: decidable when predicates fall in an SMT
  decidable theory (QF linear arithmetic + uninterpreted functions);
  inference of refinements by predicate abstraction, decidable.
- Effect systems (row-based, Koka): inference decidable (row unification
  is decidable). Gradual typing: consistency is decidable.
- Session types: checking decidable; asynchronous subtyping undecidable
  (Lange and Yoshida 2017, Bravetti et al 2018).
- Datalog (no function symbols): everything is decidable, PTIME data
  complexity; adding function symbols or arithmetic recursion loses
  termination. Prolog: termination undecidable. SQL: equivalence of
  arbitrary queries undecidable; conjunctive-query containment NP-complete;
  recursive CTEs are Turing-complete.
- Total languages (Dhall, Agda in safe mode, Cedar, Datalog, Lustre):
  termination is guaranteed by construction, so more questions become
  decidable (equivalence of Cedar policies is decidable through SMT).

Source of these: Wells (1994) "Typability and type checking in System F
are equivalent and undecidable"; Pierce (1994) "Bounded quantification is
undecidable"; Huet (1975) higher-order unification; Veldhuizen (2003)
"C++ templates are Turing complete"; Grigore (2017) "Java generics are
Turing complete" (POPL). Cited from memory; URLs in section 9.

## 3. Per-family questionnaire

Notation: "tree-sitter: yes/partial/no" refers to a maintained grammar in
the tree-sitter ecosystem as far as I know (see section 9). Feature names
in CAPS-WITH-DASHES are the synthesis rows (section 5).

### F01 Imperative / procedural: C, Go, Zig

1. Units: file/translation unit (C: a TU is the preprocessed file, not the
   file on disk), function, struct/union/enum, typedef, global variable,
   macro (C). Go: package (a directory, not a file) containing files, func,
   method (receiver is declared outside the type), interface, struct. Zig:
   a file IS a struct (every `@import` returns a struct type), fn, const,
   test blocks, comptime values. All units are named; anonymous: function
   pointers, Go closures, Zig anonymous structs/tuples.
2. Binding: lexical block scope. C: file scope, internal vs external
   linkage (the same name can denote one entity across TUs), tag namespace
   separate from ordinary identifiers. Go: package scope spans files,
   `init()` may appear many times per package. Zig: no shadowing allowed,
   declaration order irrelevant at container level (lazy analysis).
3. Strict, sequential; C `setjmp/longjmp` and `goto`; Go goroutines +
   channels (CSP) + `select`, `defer` (scope-exit action), `panic/recover`;
   Zig `defer/errdefer`, `async` removed/reworked, `comptime` partial
   evaluation.
4. C: weak static, unsound casts; Go: static simple, structural interface
   satisfaction (no `implements` edge), generics since 1.18 (constraint
   interfaces); Zig: static, types are first-class comptime values (types
   as values, so generics are functions returning types). Checking is
   decidable for all (C `_Generic` is selection, not inference).
5. IO/state implicit everywhere. Capabilities: C has none; Go none but
   `unsafe`, `cgo`, `syscall`, `os/exec` imports are the signal; Zig
   explicit allocator passing and no hidden control flow (allocation is a
   visible parameter, which is a de-facto capability token); `extern`,
   `@cImport`.
6. Edges: direct call, call through function pointer (unresolved),
   Go interface method call (dispatch edge with candidate set = all
   implementers, which are inferred structurally, so computing candidates
   needs the whole package set), `go f()` (spawn edge), `defer f()`
   (deferred edge), Zig comptime call (executes at compile time).
7. C preprocessor: textual, unhygienic, runs before parsing, conditional
   compilation changes what exists (`#ifdef`), X-macros generate
   declaration lists, `#include` splices. Go: `//go:generate` (external),
   build tags/constraints (`//go:build`) select files, `cgo` preamble in a
   comment (language island: C inside a Go comment), `embed`. Zig: comptime
   is the only metaprogramming (no macros, no reflection other than
   `@typeInfo`); the shape of a generic type is unknown until comptime
   runs.
8. Syntax: C is context-free only after typedef-name disambiguation (the
   lexer hack: whether `a * b;` is a declaration depends on whether `a` is a
   type), preprocessor makes it non-CFG; Go is CFG with semicolon
   insertion (a lexer rule based on previous token), gofmt canonical; Zig
   CFG. tree-sitter: yes (C, Go, Zig).
9. Decidable: function/type inventory, includes/imports, direct call
   edges, exported-ness (Go: capitalized name, a lexical rule; C: `static`
   vs not), cyclomatic complexity, goroutine spawn sites, defer sites,
   unsafe/cgo import presence. Undecidable: which function a pointer calls,
   whether a channel op blocks forever, data races, preprocessor-conditional
   completeness (2^n configurations of `#ifdef`; a linter sees one
   configuration or must treat `#ifdef` regions as alternative branches),
   use-after-free, aliasing.

### F02 Object-oriented class-based and prototype-based: Java, C#, Smalltalk, Self, JavaScript

1. Units: Java: class/interface/enum/record, method, field, package (name
   only, mapped to directory by convention), module (JPMS). One public
   top-level type per file by rule. C#: namespace (not tied to file),
   class, struct, `partial` class (ONE type declared in many files, merged
   by the compiler), property, event, delegate, extension method (static
   method that reads as an instance method), record. Smalltalk: class and
   method (methods are compiled into an image; no file is primary; Tonel/
   Cypress files are exports), category/protocol grouping. Self: objects
   with slots; no classes at all. JS: object literal, function, class
   (sugar over prototype), module (ESM file), CJS module (function wrapper).
   Anonymous: lambdas, inner/anonymous classes (Java), object literals.
2. Binding: lexical for locals; fields via `this`/`self` (receiver
   binding is implicit). JS: `this` is dynamically bound per call site
   (unless arrow), `var` function-scoped with hoisting, `let/const` block
   with temporal dead zone, `with` (dynamic scope injection), closures.
   Smalltalk/Self: no globals except namespace/world lookup; parent slots
   give inheritance as delegation lookup.
3. Strict; exceptions; threads; C# `async/await` (state-machine CPS
   transform), `yield` iterators (coroutines); JS event loop + promises,
   generators; Smalltalk: control flow is message sends (`ifTrue:`,
   `whileTrue:` with block arguments), so there is NO control-flow syntax.
4. Java: nominal static, generics by erasure (subtyping undecidable in
   corner cases), checked exceptions (effects-lite in signatures), sealed
   hierarchies; C#: nominal, reified generics, nullable reference types
   (flow-typing), `dynamic`; Smalltalk/Self/JS: dynamic, none static
   (TypeScript adds structural gradual types, see F21 notes).
5. Effects: exceptions in signature (Java `throws`), `unsafe` (C#),
   reflection and `native`/JNI/P-Invoke FFI, `eval`; JS `eval`,
   `Function`, dynamic `import()`. Capability signals: imports of IO,
   network, process, reflection (`java.lang.reflect`, `Class.forName`).
6. Edges: static call, virtual/interface dispatch (candidate set via class
   hierarchy analysis), constructor, inheritance/implements edge,
   override edge, field access, annotation use, JS property call with
   computed names (`obj[k]()`), prototype chain mutation, Smalltalk
   message send (every operation; receiver class unknown), Smalltalk
   `doesNotUnderstand:` and Self delegation (lookup path at runtime).
7. Java annotation processors and Lombok-style bytecode rewriting
   (generated members absent from source), reflection, classloaders,
   `MethodHandle`; C# source generators (code added at compile time),
   attributes, Roslyn analyzers, `partial` methods; JS Proxy, `eval`,
   decorators, bundler transforms; Smalltalk reflection is total (classes
   are objects, `become:`, `perform:`), Self likewise (slots addable at
   runtime). What cannot be known before expansion: members added by
   processors/generators, runtime-added slots.
8. Syntax: CFG with generics ambiguity (`a < b > c` in Java/C#), contextual
   keywords (C# `var`, `async`, `record`), JS ASI and regex-vs-divide
   ambiguity (lexer needs parser state), JSX embedded; Smalltalk: tiny
   grammar (keyword messages); Self: similar. tree-sitter: yes for Java,
   C#, JS/TS, partial Smalltalk.
9. Decidable: class/method inventory, inheritance graph (syntactic edges),
   visibility, annotations, `partial` merge (if all files are seen),
   unused imports (modulo reflection). Undecidable: the target of a
   virtual call, whether a method is overridden by a runtime-loaded class,
   what reflection touches, `this` binding in JS, prototype chain shape,
   Smalltalk image state. Linter implication: "file defines type X" breaks
   for C# partial and Smalltalk; a unit may have N declaration fragments.

### F03 Multi-paradigm systems: Rust, C++, Swift, Kotlin, Scala

1. Units: Rust: crate (build unit), module tree (declared by `mod`, which
   MAY map to a file but need not: inline `mod x { }` or `#[path]`), fn,
   struct/enum/union, trait, `impl` block (a nameless unit attached to a
   type, possibly with a trait: `impl<T> Tr for Ty`), macro_rules, proc
   macro, const, static, associated items. C++: header/TU, namespace
   (reopenable across files), class/struct, function/overload set,
   template, concept, module (C++20), `using`. Swift: module (target),
   struct/class/enum/protocol/actor, `extension` (retroactive members and
   conformances, may live in another file/module), property wrapper,
   result builder, macro. Kotlin: package, class, object (singleton),
   companion, top-level functions (file-level class `FooKt`), extension
   functions, `expect/actual` (one logical declaration with per-target
   fulfilments). Scala: package (reopenable), object, class, trait,
   `given/implicit`, `extension`, `opaque type`, top-level defs (Scala 3).
   Anonymous: closures, anonymous classes/objects, `impl Trait` return
   types (existential, unnameable), lambdas.
2. Binding: lexical; Rust: modules + `use` + hygiene for `macro_rules`
   (partial hygiene: locals hygienic, items not); name resolution has a
   fixed point with globs and macro-expanded `use`. C++: ADL (argument-
   dependent lookup: a call `f(x)` looks in x's namespaces; the binding
   depends on argument TYPES), two-phase lookup for templates, overload
   resolution; Swift: protocol witness tables; Kotlin: receivers (`this@`
   labels), implicit receivers in DSL lambdas (`T.() -> Unit`: names in
   scope depend on the lambda's receiver type); Scala: implicit scope
   includes companions of types involved (binding depends on types).
3. Strict; Rust `async` = state machine; C++20 coroutines; Swift
   structured concurrency and actors; Kotlin coroutines (`suspend`, CPS
   transformed); Scala futures/effect libs (cats-effect, ZIO as embedded
   effect DSLs).
4. Rust: affine ownership, borrowing with lifetimes (region inference;
   decidable, NLL/Polonius), traits with coherence/orphan rule, GATs,
   const generics, specialization; trait solving can hit recursion limits.
   C++: templates (Turing-complete, Veldhuizen), SFINAE, concepts,
   overloads; undefined behavior as semantic hole. Swift: protocols with
   associated types, `~Copyable` (noncopyable/affine), actor isolation
   checking. Kotlin: nullability in types, variance, smart casts (flow-
   sensitive), `reified` with `inline`. Scala 3: path-dependent types,
   higher-kinded, union/intersection, match types (type-level computation),
   givens (implicit search), capture checking (experimental effect/
   capability tracking). All checks decidable only up to fuel limits.
5. Effects: Rust `unsafe` blocks/fns/traits (a syntactic marker),
   `extern "C"`, `std::fs/net/process` paths, `Send/Sync` auto-traits (a
   concurrency capability via the type system); C++ no marker; Swift
   `unsafe*` APIs, `throws/async` in signatures (effects-lite, both are
   syntactic), `@objc`; Kotlin `suspend` coloring, `@Throws`; Scala
   `throws` experimental, capture checking. Cap detection via path/API
   names plus type-level markers.
6. Edges: static call, trait method call (dispatch resolved by type:
   needs the trait solver to know the callee; a linter can only offer
   candidate impls), `dyn Trait` dynamic edge, operator overloading (an
   operator token is a call), `Deref` auto-call, `Drop` implicit call at
   scope end (call edge without a call site!), `Into/From` via `?`,
   macro expansion (an edge to a macro definition), derive (generated
   impl), C++ template instantiation (an edge per instantiation, absent
   in source), implicit constructors/conversions, destructors at scope
   end, Swift extension/protocol default, Kotlin extension call (static
   dispatch looks like member call), Scala implicit resolution (use edge
   to an instance found by search), `given` instances.
7. Rust: `macro_rules` (pattern-based, partly hygienic), declarative
   macros 2.0 (unstable), procedural macros (derive, attribute, function-
   like: arbitrary Rust run at compile time over token streams; the
   expansion is unknowable without compiling the proc-macro crate), `cfg`
   attributes (conditional existence), `build.rs`, const eval. C++:
   preprocessor + templates + constexpr/consteval + (C++26) static
   reflection. Swift: macros (freestanding/attached, run as separate
   processes), property wrappers, result builders (syntactic rewrite of
   closure bodies into builder calls). Kotlin: compiler plugins, KSP/kapt
   annotation processing, `inline`. Scala 3: `inline`, quotes and splices
   (typed staging, `'{}` and `${}`), macros as compile-time functions;
   Scala 2: reflective macros. Unknown before expansion: derive output,
   proc-macro output, template instantiations, KSP-generated classes.
8. Syntax: Rust CFG with some contextual parsing, macro invocations are
   token trees (opaque inside `!(...)`; e.g. `println!` args are
   parsed as expressions only by convention, per-macro grammar); C++
   famously needs semantic info to parse (most vexing parse, `>>`,
   `a<b>(c)`), preprocessor first; Swift CFG; Kotlin CFG with newline
   sensitivity, string templates nest expressions; Scala 3 optional
   braces/indentation-sensitive (significant indentation, `end` markers),
   Scala 2 and 3 grammars differ. tree-sitter: yes for all five (C++
   grammar is approximate; macros and templates not understood).
9. Decidable: items, visibility, derive lists, trait impl headers
   (syntactically which trait for which type), `unsafe` placement,
   attribute sets, public-API surface (modulo macro-generated items and
   re-exports through globs, which need name resolution), async/suspend
   marks. Undecidable or needing compiler: trait dispatch targets,
   template instantiation set, macro-generated items, borrow-check
   outcome, Drop order effects, Scala implicit selection, ADL targets.
   Linter implication: for Rust the public-API graph is only sound after
   macro expansion; frob must label items "pre-expansion" and mark macro
   call sites as potential item generators.

### F04 Functional strict: OCaml, SML, F#, Clojure, Elixir

1. Units: OCaml: file = module (compilation unit named by filename,
   capitalized), `module`/`module type`/`functor` (a second language
   layer of values-of-modules), `.mli` interface file paired with `.ml`,
   `let` bindings, type, exception, class (rarely), first-class modules,
   `ppx` extensions. SML: `structure`, `signature`, `functor`, `fun`, `val`,
   `datatype`; no per-file convention (ML Basis `.mlb`/`.cm` files order
   them). F#: namespace, module, type, `let`, computation expressions,
   file ORDER is semantic (the project file lists files; later files see
   earlier ones; no forward references across files). Clojure: namespace
   (one per file by convention), var (`def`, `defn`), protocol, record,
   multimethod, macro. Elixir: module (`defmodule`, many per file allowed),
   function clause groups by name/arity (`def f/2`), macro, protocol,
   behaviour, struct. Anonymous: lambdas/`fn`, pattern-matching lambdas,
   point-free pipelines. Identity includes arity in Elixir (`f/2`) and
   Erlang (see F10).
2. Binding: lexical, de-Bruijn-equivalent; pattern variables bind in
   `match`/`case`/function heads (binding is by structure, non-linear
   patterns disallowed in ML); `let rec` mutual recursion; shadowing is
   normal. Clojure: lexical + namespace-qualified vars + dynamic vars
   (`binding`, thread-local dynamic scope) + reader-resolved aliases.
   Elixir: lexical, pin operator `^` (match instead of rebind), hygiene
   context in macros (`var!` breaks it). F#: active patterns bind via
   user-defined functions. OCaml: labels (`~x`) and optional args are a
   second binding mechanism (names are part of calls).
3. Strict (F# lazy via `lazy`/seq, Clojure lazy seqs, Elixir `Stream`);
   tail calls; exceptions; OCaml 5 effect handlers (untyped); Elixir
   processes (see F10); Clojure STM/atoms/agents/core.async (CSP).
4. OCaml/SML/F#: HM with extensions: ML modules (signature matching,
   sealing, functor application with applicative or generative semantics),
   GADTs (OCaml), polymorphic variants and row-polymorphic objects
   (structural row types), `let`-polymorphism with value restriction;
   inference decidable. F#: units of measure (dimension types, an abelian
   group inside types), type providers (types generated at compile time
   from external schemas), active patterns, flexible types. Clojure/Elixir:
   dynamic; Elixir typespecs `@spec` (checked by Dialyzer success typing,
   not sound) and, in 1.17+, gradual set-theoretic types (the exact status
   is unverified, section 9); Clojure `spec`/Malli runtime contracts.
5. Effects: ML refs, exceptions (unchecked); F# async/task CEs; Clojure
   host interop (`.method`), `System`/Java FFI, `eval`; Elixir NIFs, ports,
   `Code.eval_string`, `apply/3`. Capabilities detected by module path
   (`Unix`, `File`, `System.IO`, `:os`).
6. Edges: function application (curried: `f a b` is two applications,
   partial application creates anonymous closures), pipeline `|>`
   (argument-threading syntax; callee is on the RIGHT), module access
   `M.f`, functor application `F(M)` (a call at the module level that
   yields a module; edges between modules), Clojure macro expansion,
   multimethod dispatch (dispatch function chooses the method at runtime:
   candidate set = all `defmethod` for the multimethod, scattered across
   files), protocol dispatch (candidates = all `extend`/`defimpl`),
   Elixir `apply(M, F, A)` (dynamic), `use Mod` (calls `__using__` macro
   which injects code), `import/alias/require`.
7. OCaml: ppx rewriters (syntax extensions `[%name ...]`, attributes
   `[@@deriving ...]`: the AST is transformed by external programs, output
   unseen), camlp5 historically; SML none (some implementation-specific);
   F#: type providers, quotations (`<@ @>` code as data), computation
   expressions (desugar `let!`/`do!` into builder method calls, i.e. user-
   defined control syntax), inline IL; Clojure: homoiconic macros
   (unhygienic by default, gensym/auto-gensym `x#` for hygiene), reader
   conditionals (`#?(:clj ... :cljs ...)` in `.cljc`: one file, several
   languages' views), `eval`, `defmacro`; Elixir: AST macros
   (`quote/unquote`, hygienic by default, compile-time code execution in
   module body, `@before_compile`, `use` pattern), so code is generated
   freely at module-compile time. Unknown pre-expansion: ppx output,
   Clojure macro output, Elixir `use`d injected functions and `__using__`.
8. Syntax: OCaml CFG with precedence tables, `;` vs `;;` quirks; SML CFG;
   F# offside rule (indentation-sensitive with light syntax), Clojure:
   S-expression + reader macros (`#()`, `@`, `^` metadata); Elixir: CFG
   with `do ... end` blocks and many optional parens (call-without-parens
   ambiguity), sigils `~r/.../` (user-defined literal syntaxes, language
   islands). tree-sitter: yes for OCaml, SML(partial), F#(partial),
   Clojure, Elixir.
9. Decidable: module/signature inventory, `.mli` vs `.ml` consistency
   (name level), open/import graph, ppx attribute presence, dependency
   order (F# file order, OCaml topological via `ocamldep`: parsing for
   module references is an approximation), exhaustive-match checking
   (decidable in ML types; a lint can approximate with constructor sets).
   Undecidable: protocol/multimethod dispatch target, macro-generated
   units, `apply` targets, process message flow. F# file-order is a
   structural constraint a linter must model as a total order on units.

### F05 Functional lazy: Haskell, with GADTs, TypeFamilies, DataKinds, LinearTypes, Backpack

1. Units: module (file = module, name matches path), top-level
   function/value bindings (clauses of one function are multiple equations,
   must be contiguous), data/newtype/type synonym, `class`, `instance`
   (nameless unit; globally visible even when imported only transitively,
   so instances are NOT scoped by imports: coherence is global), type
   family (open: equations scattered across modules; closed: ordered
   equations in one place), pattern synonym, `foreign import`, `deriving`
   clauses, Template Haskell splices, `.hs-boot` files (forward interface
   for cyclic imports), Backpack: signatures (`.hsig`), `unit` stanzas,
   mixin linking in the cabal file (module-level parametrization:
   an "indefinite" package is a function from modules to a package).
2. Binding: lexical, `where` clauses scope over guards (bindings can follow
   uses), pattern variables, `let` polymorphism (NoMonoLocalBinds),
   operator sections, fixity declarations bind syntax not values and can
   appear AFTER uses within a module (so parse-then-resolve), ImplicitParams
   (`?x` dynamically scoped typed variables, a third kind of binding),
   typeclass dictionaries as implicit arguments, `RecordWildCards`
   (`C{..}` binds all field names implicitly: the set of bound names depends
   on the type), `OverloadedRecordDot`, `DuplicateRecordFields`.
3. Lazy (call-by-need; strictness via bang patterns, `seq`), purity
   enforced by the IO monad; `unsafePerformIO` hole; STM; `mdo`, arrows
   (`proc` notation), ApplicativeDo, monad comprehensions.
4. HM + type classes (dictionary passing: classes are the implicit-
   argument mechanism), higher-kinded (F-omega fragment), RankN (annotation
   needed), GADTs (type refinement by pattern match; inference needs
   annotations; OutsideIn(X)), TypeFamilies (type-level functions; with
   UndecidableInstances/UndecidableSuperClasses can diverge), DataKinds/
   PolyKinds (promote values to types; types indexed by data: a lightweight
   dependent typing), TypeInType unified kinds with types, `TypeApplications`
   and visible `forall`, LinearTypes (`a %1 -> b`, multiplicity-annotated
   arrows, linearity checking is decidable usage counting), Safe Haskell
   (module trust levels as a capability layer), Typeable/Generic
   (structural reflection), Liquid Haskell (refinements in `{-@ @-}`
   comments).
5. Effects: IO monad in types (effect as type constructor; IO-ness visible
   in signatures, so a linter CAN read purity off signatures), `IORef`,
   exceptions (imprecise), FFI `foreign import ccall`, `unsafe*` functions,
   `Safe`/`Trustworthy` pragmas. Capability detection partly via types:
   a function with no `IO` in its result type cannot perform IO except via
   `unsafePerformIO` or `trace`.
6. Edges: application, operator use, type class method call (resolved by
   instance search: a USE edge to an instance that is found by type-
   directed search, possibly in a distant module; orphan instances),
   `deriving` (generates instances), superclass edges, default-method
   edges, DerivingVia/DeriveAnyClass, TH splice edge, `import` edges with
   hiding/qualified/as, re-exports (module exports another module's
   names), CPP conditional imports.
7. Template Haskell (typed `Code` and untyped; splices `$(...)` run at
   compile time with IO allowed; declaration-group staging: code before a
   top-level splice cannot see what follows), QuasiQuotes `[name| ... |]`
   (arbitrary syntax inside, user-defined parser at compile time = embedded
   language island), CPP, `{-# LANGUAGE ... #-}` (a per-file language
   parameter: the same text means different things under different
   extension sets), `{-# RULES #-}` rewrite rules, plugins (GHC source/
   typechecker plugins), Generics. Unknown pre-expansion: TH-declared
   names, generated instances.
8. Syntax: layout rule (indentation-sensitive with implicit braces; the
   `parse-error(t)` clause makes correct layout parsing need parser
   feedback), user fixity, unicode syntax, many extensions alter the
   grammar (`LambdaCase`, `MultiWayIf`, `Arrows`, `TypeApplications`
   `@`). tree-sitter-haskell exists and is good but not exact on fixity
   and extensions.
9. Decidable: module graph, exported names, instance heads (syntactic),
   pragma sets, IO-in-signature, use of `unsafe*`/`trace`, data/class
   inventory, orphan-instance detection (syntactic: instance's module vs
   class and type modules, needs import resolution). Undecidable: which
   instance a polymorphic call selects after specialization, whether a
   type family reduces, laziness/strictness behavior, termination,
   space leaks. Backpack: whether a unit instantiation is well-formed
   needs signature matching, which a structural linter can only check
   at the declared-name level.

### F06 Dependent types and proof assistants: Agda, Lean 4, Coq/Rocq, F*, ATS (Idris 2 in F20)

1. Units: module (Agda: file = top module, plus nested and PARAMETERIZED modules whose parameters are implicit lambdas over contents), definition, data/record, theorem/lemma (a definition whose type is a proposition), axiom/postulate, instance, notation/syntax declaration, tactic/macro/elab (Lean), hint database entries (Coq `Hint`), universe declarations. Coq: Section/Variable (variables are abstracted AFTER the section closes: arity of a definition is decided at `End`), Module Type/Functor, vernacular commands. Lean 4: namespace/section/`variable` (auto-bound), `structure/class ... extends`, `@[simp]` attributes (registering global state), commands like `#eval/#check` (side-effecting commands inside a file). ATS: `.sats` (static interface) / `.dats` (dynamic implementation) split, `dataprop/dataview` (proof-level data). F*: `.fsti` interface + `.fst`, effects as declared units.
2. Binding: lexical with de Bruijn internally; implicit arguments (Agda `{}`, instance args `{{}}`, Lean `{}`/`[]`/auto-bound, Coq `{}`/`Set Implicit Arguments`, so call sites supply FEWER args than the signature has); named arguments; pattern matching with dependent elimination (`with`, `match ... return`); mutual blocks (Agda `mutual`: order inside irrelevant, outside declare-before-use); holes `?`, `{! !}`, `_`, `sorry`, `admit` (a program with holes is meaningful: a node kind "hole" with a type context).
3. Evaluation is conversion/normalization used at type-check time; programs may be total (strong normalization enforced by termination/guardedness/positivity checkers) or `partial/unsafe` (Lean); extraction to OCaml/Haskell/C erases proofs; erasure/irrelevance annotations (`@0`, `.x`, Prop) split compile-time from run-time parts of ONE term.
4. CoC/MLTT with universe hierarchy (cumulative or not), inductive families, W/M types, (co)inductive types, quotients, cubical interval (Cubical Agda), sized types, QTT (Idris 2), Prop/impredicativity (Coq/Lean), K axiom flags (`--without-K`). Checking decidable when normalization holds; elaboration undecidable (higher-order unification); typeclass resolution can loop (tabled in Lean 4); `Type : Type` unsound. F* adds Dijkstra-monad effects (Tot/Div/ST/Pure pre post) and SMT-discharged refinements; ATS dependent types over a static sort language with linear views.
5. Effects: mostly none inside the logic; `postulate/axiom/sorry/Admitted/Axiom` are the trust boundary (a linter-relevant effect: "this theorem depends on an axiom", transitively); `unsafe`, `implemented_by`, `extern`, FFI (Lean `@[extern]`, Agda `{-# FOREIGN #-}`, `{-# COMPILE GHC #-}`). The equivalent of a capability matrix is an AXIOM-DEPENDENCY matrix (`#print axioms`).
6. Edges: constant reference, implicit-argument instance search (use edge to an instance found by type-directed search), coercion insertion (invisible call), notation expansion (parse-level), tactic invocation (script calls tactics which synthesize terms; the final term is NOT in source), `simp`-set lookup, `Hint`/`@[simp]` registration edges, canonical structures (unification hints), rewrite rules (Agda `REWRITE`).
7. Metaprogramming is first class: Lean 4 `syntax/macro_rules/elab/declare_syntax_cat` (hygienic, extensible parser and elaborator, the grammar itself is user-extensible per file), Coq Ltac/Ltac2/MetaCoq/Elpi, Agda `macro` + reflection (`quoteGoal`, TC monad), Idris elaborator reflection, F* tactics/Meta-F*, `Program`/`Equations`. A proof script (`by ... ` / `Proof. ... Qed.`) is a program whose product is a term; the script is the only source artifact. Transparent vs opaque (`Defined.` vs `Qed.`, `irreducible`) changes what later code can compute.
8. Syntax: Agda MIXFIX (`_+_`, `if_then_else_`, user-declared operator names and precedence, unicode everywhere, whitespace-significant tokens because `a+b` is one identifier), Lean 4 and Coq user-extensible notation with scopes (`%nat` delimiters); parse of a file depends on notations declared EARLIER in the file or in imports; literate formats (`.lagda`, `.lagda.md`, Lean doc-gen). tree-sitter: Agda yes (approximate, mixfix unparsed as application), Lean 4 yes (approximate), Coq partial, F*/ATS no/partial.
9. Decidable: declaration inventory, imports, `sorry/postulate/admit` presence (a first-class lint), unsafe flags/pragmas, theorem vs def classification (syntactic keyword), axiom dependency closure (needs name resolution). Undecidable/needs the kernel: whether a proof checks, whether an implicit argument is resolved, tactic output, termination in general, whether a term is propositionally equal. Mixfix means even Agda expression structure is unknown until operators are resolved: a structural IR must keep "flat operator sequence" nodes pending resolution (same as Haskell fixity, Prolog `op/3`, Maude).

### F07 Logic and relational: Prolog, Mercury, Datalog, miniKanren, ASP, SQL

1. Units: Prolog: clause, predicate IDENTIFIED BY name/arity (`foo/2` and `foo/3` are different predicates; a "function" is a group of clauses, possibly non-contiguous, possibly across `discontiguous` declarations), module (`:- module`), directive (`:- ...`, executed at load: part of program state), DCG rule. Mercury: module (file) with interface and implementation SECTIONS inside one file, `pred`/`func` with mode and determinism declarations separate from clauses, typeclass, instance. Datalog (Souffle, Datomic, Flix, Logica): relation declaration (`.decl`), rule, fact, component/template, input/output directives. miniKanren: relations are ordinary host functions returning goals; no syntax of its own. ASP (clingo): rule, fact, integrity constraint (`:- body.`), choice rule `{a;b}`, aggregate, `#show`, `#minimize`, program parts (`#program`). SQL: table/view/index/trigger/sequence/schema/procedure/function/type (DDL objects living in a catalog, with the FILE being a script that mutates it), query (SELECT as an expression of relational algebra), CTE (named subquery), migration file.
2. Binding: logic variables (clause-scoped, bound by unification, single assignment up to backtracking; the SAME name inside one clause denotes one variable, so repeated occurrence = equality constraint: non-linear patterns), `_` anonymous; rule-local in Datalog (safety condition: every head variable occurs positively in the body); miniKanren `fresh` introduces variables, host-language lexical scope otherwise; ASP grounding instantiates variables over finite domains; SQL: column references resolve against FROM-clause scope (correlated subqueries, aliasing, CTE scope, `SELECT *` expansion depends on the catalog, so NOT knowable from the query text alone), parameters (`$1`, `:name`, `?`).
3. Prolog: SLD resolution, depth-first, backtracking, cut (`!` prunes choice points, a control edge not visible in clause graph), `findall/bagof/setof`, negation as failure `\+`, `assert/retract` (the program mutates itself), coroutining (`freeze`, attributed vars, CLP(FD)), tabling, exceptions. Mercury: deterministic by analysis (det/semidet/multi/nondet/erroneous/failure, committed-choice `cc_`), declarative I/O via unique `io.state` threading. Datalog: bottom-up least fixpoint, order of rules irrelevant (unordered set), stratified negation. miniKanren: interleaving (fair) complete search. ASP: guess-and-check, stable models. SQL: declarative set/bag semantics; optimizer chooses plan; three-valued NULL logic.
4. Prolog untyped (Ciao/Logtalk add assertions/objects); Mercury strong static types, MODES (in/out/di/uo, unique and mostly-unique modes = substructural), determinism and purity checking (decidable conservative analyses); Datalog typed domains (Souffle) or untyped; SQL: static schema types but dialects differ, implicit casts. Termination: Datalog guaranteed (no function symbols), Prolog undecidable, SQL non-recursive total, recursive CTE Turing-complete. Query containment/equivalence: Datalog undecidable in general (even for fixed programs), conjunctive queries NP-complete.
5. Effects: Prolog IO built-ins, assert/retract (global state), `consult`, foreign interface; Mercury pure vs impure marked in the signature (`impure`, `semipure`), io.state in types; SQL: DDL/DML vs SELECT (read-only vs write), triggers (invisible control flow on writes), stored procedures, dynamic SQL strings (EXEC, `format()`), COPY/LOAD file IO, extension functions (`pg_read_file`), roles/GRANT as a DB-side capability matrix; Datalog engines: `.input/.output` IO directives.
6. Edges: goal -> predicate (call by name/arity: the callee is a SET of clauses), unification edges (two terms constrained equal, no direction), `call/N` and `=..` (computed callee), DCG expansion, `assert` (dynamic clause creation), term_expansion/goal_expansion (macros), Datalog rule head<-body dependency graph (predicate dependency graph with positive/negative edges: stratification is a graph property, decidable), ASP likewise (positive-negative dependency), SQL: view->table dependency, FK edges, trigger->table, query->tables read/written, `JOIN` edges, migration ordering. miniKanren: `==` goals, relation calls = host function calls.
7. Prolog: `op/3` (change the parser at runtime), `term_expansion`, `goal_expansion`, flags (`double_quotes`), `:- initialization`, meta-predicates, reflection (`clause/2`, `current_predicate`), `consult` at runtime. SQL: dynamic SQL, `EXECUTE`, templating (dbt Jinja, ORMs build strings: SQL as a language island in host strings), views (macro-like), PL/pgSQL. Datalog: Souffle components/functors (extern C++). ASP: `#script`, grounding as metaprogramming. miniKanren: embedded, relational interpreters (eval written as a relation; programs generated by running backward).
8. Syntax: Prolog: operator-precedence grammar with USER-DEFINED operators (parse depends on runtime state; a clause can change how later text is read), `.` ends a clause (ambiguity with `X = a.b`), 0'c char syntax, quoted atoms; Mercury Prolog-like with declaration forms; Datalog/ASP: small CFG; SQL: CFG per dialect (huge, dialect-forked, keywords contextual, `;` delimiter vs procedural bodies containing `;`); miniKanren: S-expressions. tree-sitter: Prolog yes (approximate, no op/3), SQL multiple dialect grammars (approximate), Datalog/Souffle yes (community), ASP partial, Mercury no.
9. Decidable: predicate inventory by name/arity, call graph over literal goals, recursion (SCCs of the predicate graph), stratification (Datalog/ASP/Rego), unused predicates (modulo `call/N`), singleton variables, unsafe rules, mode/determinism declarations vs presence, SQL referenced tables/columns IF a catalog (DDL) is given, read vs write classification. Undecidable: termination (Prolog), cut semantics effect, assert-generated code, dynamic SQL, `SELECT *` shape without schema, Datalog query equivalence/containment, which clauses fire. Key insight: the unit "function" is wrong here; the unit is predicate/relation with a clause set, and edges between clauses are unification constraints, not calls.

### F08 Concatenative / stack: Forth, Factor, Joy, PostScript

1. Units: word (Forth: a dictionary entry created by `:` ... `;`, also `variable`, `constant`, `create ... does>`, `defer`), vocabulary/wordlist (search order is state), blocks (historical), file only as an input stream. Factor: vocabulary (`IN:`, `USING:`), word (`:`), generic (`GENERIC:`, `M:`), tuple, quotation (anonymous code block `[ ... ]` as a value), syntax word (`SYNTAX:`). Joy: definition in `DEFINE`, quotations (lists = programs). PostScript: procedure (executable array `{ }`) stored in dictionaries by `def`; dictionaries are scopes; whole document = program. Most code is ANONYMOUS and positional: stack effects, not names, relate parts; locals optional.
2. Binding: NO lexical variables by default: values flow through an implicit stack (positional binding; the "variable" is the stack slot). Forth: global dictionary with shadowing by redefinition (later definition hides earlier for LATER words only; earlier compiled words keep the old binding: binding time is definition time), return-stack tricks (`>r r>`), `locals|`, `value/to`. Factor: lexical variables via `::`/`[let`/`fry`/`locals` as sugar. PostScript: DYNAMIC scope via the dictionary stack (`begin/end`), bindings resolved at execution time by name lookup (late binding) unless `bind` used.
3. Strict, stack machine; Forth has TWO interpreter states (interpret vs compile, `[`, `]`, `immediate`, `postpone`, `state`), so the same token has different effect by mode; control structures (`if/else/then`, `do/loop`, `begin/until`) are ordinary immediate words that compile branch code; Joy: combinators (`i`, `dip`, `ifte`, `linrec`, `primrec`) take quotations; PostScript: operand/execution/dictionary stacks, `exec`, `stopped`.
4. Forth untyped (stack-effect comments `( a b -- c )` are comments, not checked); Factor: stack effects DECLARED and INFERRED/checked (decidable for the inferable subset; `call` of unknown quotation needs effect annotation `call( a -- b )`); Joy untyped; Cat/Kitten typed concatenative with row-polymorphic stack types (inference decidable for the basic calculus). Concatenation = function composition, so a program is a morphism in a category; no application node exists.
5. Effects: unrestricted; Forth direct memory access (`@ !`, `allot`), `execute`, system words; Factor FFI, `io.*` vocabularies; PostScript file ops (`file`, `deletefile`, `run`) which sandboxes disable (`-dSAFER`: a capability toggle outside the language); DSC comments `%%` carry document structure (a comment DSL precedent).
6. Edges: word occurrence -> definition by dictionary lookup at compile time (Forth) or runtime (PostScript name lookup), `execute/'/[']`, `call` on quotations (dynamic), `does>` behavior sharing, `defer/is` (late-bound), Factor generic dispatch on the top-of-stack type, syntax-word parsing.
7. Forth: the whole language is metaprogramming: parsing words read the input stream (`parse-name`, `'`, `create`), `immediate` words run at compile time, `evaluate`, `[ ... ]`, `postpone`, `compile,`; user can define new defining words and new control structures; Factor: parsing words (SYNTAX:), `MACRO:`, `fry`; PostScript: code = data (executable arrays), `cvx`. Nothing about word boundaries/structure is known without the dictionary state at that point of the stream.
8. Syntax: tokens separated by whitespace, essentially no grammar (Forth's grammar is "whatever the words do"); Factor adds literal syntax via parsing words; PostScript `/name`, `{ }`, `( )` strings, `%` comments; Joy `[ ]`. tree-sitter: Forth (community, approximate), Factor (partial), PostScript (partial), Joy no.
9. Decidable: word definitions (a `:` token to a `;` token, subject to `immediate`/`postpone` tricks), tokens, literal numbers, simple stack-effect comment vs inferred effect for plain words. Undecidable/state-dependent: what a token parses as, stack-balance of loops with `?dup`, `execute`, `pick`; whether a word is immediate; Factor stack-checking only for declared quotations. A structural IR must represent "token sequence with unknown word classes" as the base case and layer definitions on top by heuristic.

### F09 Array languages: APL, J, K/q, BQN, Uiua

1. Units: mostly NOTHING named at the micro level: expressions are chains of primitive functions over arrays (tacit/point-free: trains, forks `f g h`, hooks). Named: assignments (`name <- expr`), explicit functions (APL `{ }` dfn with `a` `w`; nabla-glyph tradfn; J `3 : 0` explicit defs; K `{x+y}` implicit args `x y z`; BQN `{ }` blocks with `x w` (written with math-italic glyphs in BQN); Uiua `name <- ...` (left-arrow glyph) and functions as stack-signature-checked), namespaces/classes (Dyalog `:Namespace`, `:Class`), q: tables and keyed tables (`([] a:1 2 3)`) as first-class values, `\l` script files, `.z` handlers. Q/kdb+: namespaces `.ns.name`, in-memory global state mutated by assignments (`set`).
2. Binding: APL: lexical for dfns, tradfns use DYNAMIC scoping (locals visible to callees) and quad-prefixed system variables; J: names have runtime-determined PART OF SPEECH (noun/verb/adverb/conjunction), tacit definitions assign verbs, `=:` global vs `=.` local; BQN: the part of speech is fixed LEXICALLY by identifier case/underscores (lowercase subject, Uppercase function, `_mod` 1-modifier, `_mod_` 2-modifier), which makes BQN statically parseable; K: implicit arguments by name `x y z`, globals pervasive; Uiua: stack-based with named bindings, array-oriented, inline signature inference.
3. Strict array-at-a-time evaluation, rank polymorphism (implicit looping over leading axes: control flow is implicit in the shapes), right-to-left (APL/J/K) or right-to-left with trains (BQN), scan/reduce/each; no loops usually; Uiua is concatenative-array hybrid. SIMD/GPU mapping natural.
4. Dynamic (types are element classes: bool/int/float/char/box); RANK is the key static property, checkable in shape-typed variants (Remora: rank-polymorphic dependent-ish; Futhark, Dex, SaC); Uiua has compile-time function signature (stack args/outputs) checking; BQN has role checking. General shape inference: decidable only for restricted fragments; in APL/J shapes are runtime values.
5. Effects: system functions quad-prefixed names and `1!:` foreign conjunction in J, `\` system commands in K, q IPC (`hopen`, handles, `.z.pg` callbacks), file IO; FFI (`quad-NA`, `15!:0`); kdb+ process model with ports.
6. Edges: function application is JUXTAPOSITION with context-dependent parsing (monad vs dyad is decided by whether a left argument exists), trains (implicit composition), operators/modifiers (`f/`, `f` with each-glyph, `f` with rank-glyph `k`) take functions: callee is passed implicitly; q: table/column references in queries `select ... from t` (SQL-like inside the language).
7. J adverb/conjunction definition (`1 : 0`), APL execute-glyph (APL execute), quad-FX (fix: define a function from text at runtime), K `.` eval, q `value`/`parse`; Uiua macros (`^` placeholders, stack-based macros). The glyph set itself is a user-invisible lexicon (Uiua formatter converts ASCII names to glyphs; two textual spellings of one program).
8. Syntax: dense glyph-based, unicode, symbol soup, right-to-left; APL `{}` dfns, J ASCII digraphs (`=:`, `^:`, `&.`) with inflection `.` `:`, K/q whitespace-sensitive (`-1` vs `- 1`, comments need preceding space), BQN CFG-ish with lexical roles; Uiua glyph source. tree-sitter: APL partial community, J partial, K/q partial, BQN yes (community), Uiua yes (community). Byte vs char width matters (APL code pages).
9. Decidable: lexical tokens, definitions (assignment forms), BQN roles, Uiua signatures, count of primitives, explicit loops (none), q table/namespace inventory. Undecidable/runtime: J/APL/K part of speech, whether an expression is monadic/dyadic in J without evaluating names, shapes/ranks at runtime, execute-glyph/quad-FX. Linter implication: the "call" node is not usable; a train/fork node, a modifier-application node and an "array literal as unit" are needed. Complexity metrics (cyclomatic) are meaningless; token count/glyph count replace them.

### F10 Actor and process languages: Erlang/OTP, Pony, Akka

1. Units: Erlang: module (file = module, name must match), function identified by name/arity (`f/2`, clauses grouped), attribute (`-export`, `-behaviour`, `-record`, `-define`, `-spec`, `-type`), process (runtime entity identified by pid, NOT by any source construct), application/release (`.app.src`, `rebar.config`), supervisor tree (a RUNTIME structure declared in code as child specs: structure lives in data), behaviour callbacks (`init/1`, `handle_call/3`...) which together form a "process type". Pony: actor (declaration with behaviours `be`, async, and functions `fun`, synchronous), class, primitive, trait, interface, `use` packages. Akka: Actor classes (classic) or `Behavior[T]` values (typed), `ActorSystem`, props, routers, streams (Akka Streams graph DSL: sources/flows/sinks wired programmatically).
2. Binding: Erlang: single-assignment variables, pattern matching in heads and receive, variable names capitalized, no shadowing in funs except via fun heads (warns), module-qualified calls `M:F(A)` with M possibly a variable; process identity by pid or registered name (global namespace of atoms `register/2`); Pony: lexical + capability-guarded fields; Akka: actor paths (`/user/a/b`, a hierarchical NAME space at runtime) and `ActorRef`s as capabilities (possession of a ref IS permission to send).
3. Concurrency = isolated processes with private heaps, asynchronous message passing, selective `receive` with pattern matching on a mailbox (ordering by pattern, not arrival), links/monitors/supervision ("let it crash"), hot code loading (two module versions coexist; fully-qualified call `?MODULE:f()` switches version), ETS tables (shared mutable state in-VM), distribution (messages across nodes transparently). Pony: causal messaging, per-actor GC, no data races by type system. Akka: dispatcher/threads, mailboxes, typed protocols, `ask` pattern.
4. Erlang untyped at runtime; `-spec/-type` checked by Dialyzer (success typing: no false positives, intentionally unsound-complete tradeoff), Gradualizer, eqWAlizer; Pony: static with REFERENCE CAPABILITIES (iso, trn, ref, val, box, tag: a substructural/ownership type system proving data-race freedom and deadlock freedom of behaviours), checking decidable; Akka typed: protocol types `Behavior[Msg]` (session types in research: Typed Akka-like, Scribble); session types for protocols decidable checking, async subtyping undecidable.
5. Effects: message send is THE effect (the boundary between processes), spawn, links, ports/NIFs/ports to OS, `os:cmd`, `erlang:apply`, distribution (`net_adm`, `rpc:call`, remote spawn), `code:load_file`; Pony `FFI` + `@` extern calls, `AmbientAuth` (a capability object required to touch files/network: object-capability model built in: `FileAuth`, `NetAuth` derived from `AmbientAuth`); Akka: remoting, persistence. Pony shows a language whose capability matrix is already in the type system.
6. Edges: function call, `spawn(M,F,A)` (spawn edge: process creation with an entry function; computed through `apply` forms), message send `Pid ! Msg` (send edge whose target is a runtime value; candidate receivers = processes whose receive clauses match the message shape: a MATCHING edge, often the only static link between sender and receiver is the message TERM shape), `gen_server:call(Name, Req)` -> `handle_call` callback in module registered under Name (behaviour dispatch via registry), supervisor child specs (start edges), monitors/links, Pony `be` calls (async send), Akka `tell/ask`, router/stream graph edges.
7. Erlang: preprocessor macros (`-define`, `?MACRO`, textual unhygienic, epp), `parse_transform` (user code rewriting the whole module AST at compile time), `-include`, `code:` hot loading, `apply/3`, `erl_eval`; Elixir macros (F04); Pony: none (no macros), traits; Akka: reflection/Props, classloading; Erlang is homoiconic-lite via abstract format (`erl_parse` terms).
8. Syntax: Erlang: CFG with `.` terminator, `-attributes`, `,;.` separators giving clause structure (semantic punctuation); Pony: indentation-insensitive, `end` keywords; Akka: host language (Scala/Java). tree-sitter: Erlang yes, Pony yes (community).
9. Decidable: module/function-by-arity inventory, exports, behaviour callbacks present, spawn/send sites, supervision declaration as data in source (child specs literal), `-spec` presence, process-shape smells (selective receive without timeout: syntactic), Pony capability annotations (syntactic and checkable). Undecidable: who receives a message, deadlock/livelock, mailbox overflow, supervision tree at runtime (when specs computed), hot-upgrade compat, `apply` targets. Message-protocol conformance needs session types or Dialyzer-like inference.

### F11 Dataflow, reactive and visual: LabVIEW, Max/MSP, Pure Data, Scratch, Excel/LAMBDA, Observable

1. Units: LabVIEW: VI (virtual instrument, a binary `.vi` file with a front panel AND a block diagram), subVI, wire, node, structure (while/for/case/sequence frames), type definition; Max/MSP: patcher (`.maxpat`, JSON), object box, message box, patch cord with inlet/outlet indices, subpatcher `[p name]`, abstraction (a patcher file used as an object), `bpatcher`; Pure Data: `.pd` TEXT file of lines `#X obj x y name args;` and `#X connect src outlet dst inlet;` where objects are IDENTIFIED BY THEIR POSITION (index) in the file, i.e. anonymous and positional; Scratch: sprites, scripts of stacked blocks (`.sb3` zip of JSON), hat blocks (event entry points), custom blocks, broadcasts; Excel: workbook, sheet, cell (address `Sheet1!B3`), named range, table (structured refs `Table1[Col]`), LAMBDA + LET + named LAMBDA in Name Manager, dynamic-array spill ranges; Observable: notebook of cells, each cell one named value (or anonymous), `viewof`, `mutable`.
2. Binding: wires (explicit edge = binding, no name needed: LabVIEW, Max, Pd); cell references by address or name (Excel A1/R1C1, relative vs absolute refs `$A$1`, copy-paste semantics rewrite relative refs: a reference is position-relative), Observable: references by NAME to other cells, resolved reactively regardless of cell order, one definition per name; LET/LAMBDA lexical inside a formula; Scratch variables (global per project / per sprite / "for this sprite only"), cloud variables; Max `send/receive` named buses (global string-keyed channels) and `#1` argument substitution in abstractions, `value`, `pv`, `coll` named shared buffers; Pd `$1` args, `[s name]/[r name]`, `[table name]` (global names).
3. Dataflow: a node fires when inputs are ready (LabVIEW, data-driven; structure frames impose local order; error wires thread sequencing); Max: control-rate messages with ORDER defined by spatial layout (right-to-left, then depth-first, historically; `trigger` object to make it explicit) plus signal-rate audio graph (MSP) on a clocked DSP chain; Pd likewise (order of creation for fan-out is implicit, a known hazard); Scratch: event-driven threads cooperatively scheduled per frame; Excel: topological recalculation over the dependency DAG (calc chain), volatile functions (`NOW`, `RAND`, `OFFSET`, `INDIRECT`) recalc always and make dependencies DYNAMIC; iterative calc enables cycles; Observable: reactive topological runtime, generators/promises per cell.
4. Mostly untyped/dynamic; LabVIEW has strongly typed wires (colour-coded, polymorphic VIs, malleable VIs); Excel: value types with errors (`#REF!`) as values, LAMBDA recursion possible (Turing-complete with LAMBDA, Excel is Turing-complete since 2021), arrays; Max: untyped atoms (int/float/symbol), signal vs control cords differ. Type checking trivial; the interesting property is acyclicity and fan-out ordering.
5. Effects: LabVIEW hardware drivers (DAQ, VISA), file IO, call-by-reference and shared variables; Max: audio/MIDI/file/js/`shell`, `js`/`node.script` embedded scripting, Java; Scratch extensions (pen, music, network via extensions); Excel: external data (`WEBSERVICE`, Power Query), `INDIRECT`, macros/VBA (a language embedded in the file container), LAMBDA is pure; Observable: `fetch`, `require`/`import`, secrets. Capability signals are node TYPES (object names) instead of imports: e.g. Max objects `[shell]`, `[udpsend]`.
6. Edges: wire/cord (typed by port), cell reference (formula -> cell/range/name: includes RANGE references `A1:A10` as a set edge, structured refs, 3-D refs across sheets, external workbook links `[Book.xlsx]Sheet!A1`), `send/receive` name-matching edges (a string is the link), subpatcher containment, abstraction loading by filename (the object name IS a file reference, resolved via a search path), Scratch broadcast message names, Observable free-variable references.
7. Metaprogramming is weak but present: LabVIEW scripting (VI Server, scripting), Max `thispatcher` messages (patch edits itself), `js` objects, `poly~`/`gen~` (code in a sub-language), Excel `INDIRECT` (string -> reference), dynamic array formulas, VBA; Scratch none; Pd: dynamic patching with messages to `pd-patchname`. Computed references are the dynamic-edge case.
8. Syntax: NON-TEXTUAL or 2D: the geometric layout (x,y) can carry semantics (Max/Pd execution order; LabVIEW structure nesting by containment, i.e. spatial containment is the parent-child relation; Scratch block stacking: vertical adjacency is sequence), saved formats: binary (LabVIEW), JSON (Max, Scratch, Observable `.ojs`/notebook JSON), text lines (Pd), XML in zip (Excel `.xlsx`: sheet XML + shared strings + defined names + calcChain). Formula language in Excel: CFG with locale-dependent separators (`,` vs `;`), implicit intersection (`@`), whitespace as intersection operator. tree-sitter: not applicable to the container; Excel formula grammars exist (community, partial); Observable JS is JS (tree-sitter yes with cell wrappers).
9. Decidable: unit inventory (cells/objects/blocks), dependency graph from literal references, cycle detection (without volatile refs), unused cells/objects (no outgoing edges), fan-out ordering hazards (Max/Pd: two cords from one outlet, order by geometry), named-bus mismatch (send without receive by literal name), hardcoded constants. Undecidable: `INDIRECT/OFFSET` targets, dynamic patching, hardware behavior, timing (audio dropouts), LAMBDA recursion termination. Linter implication: source locators must handle non-byte-range (cell address, object index, XML path, JSON pointer, geometric position), and the unit graph is explicit rather than inferred.

### F12 Hardware description and GPU/shader languages: Verilog, VHDL, Chisel, GLSL, HLSL, WGSL, CUDA

1. Units: Verilog/SystemVerilog: module (with ports; module instantiation creates hierarchy), `always`/`initial`/`assign` blocks (concurrent processes, not functions), generate blocks, interface, package, class (SV verification), task/function, `define macros, `include; VHDL: entity (interface) + architecture (body; many per entity) + configuration + package + package body + component; process (concurrent), signal, generic; Chisel: Scala classes extending `Module` (hardware generator: a Scala PROGRAM that, when elaborated, builds a netlist: structure is produced by execution of host code); Bluespec: module with RULES (guarded atomic actions, unordered scheduling by compiler); Clash/Amaranth/MyHDL: HDL embedded in Haskell/Python. Shaders: GLSL/HLSL/WGSL: entry points (vertex/fragment/compute stages; `@vertex @fragment @compute` in WGSL, `main` with layout qualifiers in GLSL), functions, uniforms/buffers/textures/samplers bindings (`@group(0) @binding(1)`: binding slots are the interface to host code, an implicit cross-language edge), structs, workgroup size attributes. CUDA: `__global__` kernel, `__device__`/`__host__` functions, launch `kern<<<grid,block,shmem,stream>>>(args)` (a call with extra execution-configuration syntax), `__shared__/__constant__` memory spaces, streams, graphs; OpenCL/SYCL/HIP/Metal/Triton analogous.
2. Binding: lexical, but SIGNALS are the connective tissue: Verilog nets/regs are module-scoped, hierarchical references (`top.u1.sig` cross-module dotted names by instance path: binding by elaborated hierarchy, not by lexical scope), port connection by name or by position (`.clk(clk)` vs positional) ; VHDL: library/use clauses, signals vs variables (different update semantics), generics/generate; shaders: global in/out/uniform variables bound by LOCATION INDEX or NAME to the host pipeline; CUDA: `threadIdx/blockIdx` builtins give each thread an implicit identity (SPMD binding: the same code, per-thread values).
3. Hardware: concurrent processes + clocked/event-driven simulation: sensitivity lists, delta cycles, blocking `=` vs non-blocking `<=` assignment (semantics differ, classic race source), `always_ff/always_comb/always_latch`, reset styles (sync/async), clock-domain crossings, `wait`; synthesis semantics differ from simulation semantics (a synthesizable SUBSET, so "same code, two meanings"). Shaders/CUDA: SPMD across thousands of threads, lockstep warps/wavefronts with divergence, barriers (`__syncthreads()`, `barrier()`, `workgroupBarrier()`), atomics, memory hierarchies, no (or restricted) recursion and dynamic allocation, loops should be uniform; Triton/Halide separate ALGORITHM from SCHEDULE (two structures describing one computation).
4. Verilog: weak (bit vectors, 4-state logic 0/1/X/Z, implicit nets: undeclared identifiers silently become 1-bit wires unless `default_nettype none`); VHDL: strong static, bounded-range types, resolution functions; Chisel: static via Scala types for hardware values (`UInt(8.W)`, `Bundle`, `Vec`) plus width inference (a constraint solver over bit widths, decidable); shader languages: static, vector/matrix types with swizzles, precision qualifiers, address spaces (WGSL `ptr<function, T>`), uniformity analysis (WGSL requires uniform control flow for barriers and derivatives; checked statically and conservatively). CUDA: C++ types + execution space qualifiers (`__host__`/`__device__` act as an effect annotation: which side may call which, checked by the compiler).
5. Effects: HW: `$display/$finish/$fopen`, DPI-C/VPI/PLI (calls into C), testbench-only constructs (delays `#10`, `initial`) are non-synthesizable (a purity-like subset marker); shaders: textures/buffers writes, atomics; CUDA: device memory allocation, host-device copies (`cudaMemcpy`), streams, `cudaMalloc`, dynamic parallelism, unified memory, NCCL/MPI; capability set: which memory space, which kernel launches.
6. Edges: module instantiation (instance edge with parameter overrides and port maps: the "call" is structural, creating a hierarchy), signal drivers/loads (multi-driver conflicts), function call, `generate` expansion, VHDL entity-architecture binding via configuration, `bind` (SV, attach a checker module to another), kernel launch (host -> device edge with grid config), shader stage interfaces (varying out of vertex -> in of fragment, matched by location), resource-binding edges to host code, Chisel: Scala call -> hardware instance (elaboration-time).
7. Verilog preprocessor (`define, `ifdef, `include; textual), `generate`/`for`/`if` elaboration-time structure, `parameter/localparam/defparam` (override after the fact), SV macros/UVM; VHDL generics/generate, `attribute`; Chisel/Clash/Amaranth: the host language is the metaprogramming layer (hardware is a generated artifact of a program; the netlist is unknown pre-elaboration); shaders: preprocessor in GLSL/HLSL, specialization constants, WGSL `override` constants, shader variants permuted by `#define`s (combinatorial explosion), CUDA templates, `constexpr`, PTX inline asm.
8. Syntax: Verilog CFG with preprocessor and context-dependent keywords per standard version (1364-2005 vs SV 1800), VHDL verbose Ada-like CFG case-insensitive, Chisel = Scala, shaders C-like CFG (GLSL version pragma `#version 450` selects the language! another per-file language parameter; HLSL semantics `: SV_Position`; WGSL attributes), CUDA = C++ plus `<<<>>>` and qualifiers. tree-sitter: Verilog/SV yes, VHDL yes, GLSL yes, HLSL yes, WGSL yes, CUDA yes (C++ grammar variant), Chisel via Scala.
9. Decidable: module hierarchy from instantiation, port lists, clock/reset signals by naming, blocking vs non-blocking in `always` (a classic lint), latch inference (assignment-completeness in `always_comb`, decidable on the CFG of the block), multi-driver, undeclared nets, width mismatches (constant), kernel inventory and launch configs literal, `__shared__` + barrier placement vs branches (conservative), implicit-net detection. Undecidable: timing closure, CDC correctness, deadlock in handshakes, thread divergence at barriers, data races in kernels, floating-point results, equivalence of two designs (decidable for combinational in bounded width by SAT, undecidable in general sequential unbounded). Elaboration-time generators (Chisel) need the host language executed.

### F13 Quantum: Qiskit, Q#, Quipper

1. Units: Qiskit: Python program building `QuantumCircuit` objects (circuit = a data value constructed by method calls), registers, gates, parametrized circuits, transpiler passes, OpenQASM 2/3 text (`qreg`, gate definitions, `OPENQASM 3` has classical control, timing, subroutines); Q#: namespace, `operation` (may have quantum effects) vs `function` (pure classical), `newtype`, `adjoint`/`controlled` functor specializations (auto-generated or user-supplied `adjoint auto`), `use q = Qubit()` scoped allocation, `borrow`; Quipper (Haskell eDSL): circuit-generating functions in the `Circ` monad, `box`/`unbox`, `reverse_generic`, `classical_to_quantum`.
2. Binding: qubits are LINEAR resources (no-cloning theorem): each qubit variable must be consumed/used exactly once per gate sequence in the abstract model; in practice languages manage via scoping (Q# `use` block releases at end; must be in `|0>` state), registers indexed positionally; Qiskit circuit wires are integers (indices); parameters by name (`Parameter('theta')`).
3. Circuit model: a static, finite DAG of gates over wires (no loops in the circuit itself; loops live in the host program that generates it); measurement is the only classical interface; mid-circuit measurement and classical feedforward (dynamic circuits, OpenQASM 3 `if (c==1)`); Q# supports classical control flow with quantum ops inside (hybrid; runtime-dependent), repeat-until-success; adjoint = reversal of the gate sequence; uncomputation (Silq automatically uncomputes temporaries, Qrisp too). Reversibility is a structural property: every unitary block has an inverse structure.
4. Qiskit/OpenQASM: dynamic/untyped hosts, circuit width checked at append time; Q#: static with `Qubit` type, operation characteristics `is Adj + Ctl` (EFFECT-like annotations: which functors are supported), Result/Bool/Int; Silq: type system tracks qubit/classical/`const`/`qfree`/`mfree` annotations (qfree = no superposition-changing ops, enables automatic uncomputation: an effect system); QWIRE/Quipper: linear types for wires (Quipper checks lifting classical to quantum at "circuit generation time" vs "circuit execution time": TWO-LEVEL staging). Checking linearity is decidable.
5. Effects: measurement (collapse), qubit allocation/reset, classical IO via host, hardware backends (cloud submit: network capability), randomness; capability = which backend/hardware provider, shots; Q# distinguishes function (pure) vs operation by keyword (syntactic effect marker).
6. Edges: gate application (edge from circuit-builder code to gate), operation call, functor application (`Adjoint Op(q)`, `Controlled Op([c], q)` call edges to generated specializations), circuit composition/append (`compose`), subcircuit definitions (OpenQASM `gate foo q {}`), transpiler pass pipeline, the HOST-LEVEL data dependency (a circuit value flows through Python code to a `run`/`execute` call).
7. Qiskit: circuits are generated by arbitrary Python (metaprogramming = ordinary Python); Q#: partial evaluation/compile-time resource estimation; adjoint/controlled specialization auto-derivation (compiler-generated members); Quipper: generic circuit-producing combinators, Template Haskell for classical-to-reversible lifting (`build_circuit`). Unknown pre-run: the circuit's actual gate list for Python-built circuits.
8. Syntax: OpenQASM 3 CFG; Q# CFG (C#/F#-like), Qiskit/Quipper = host languages. tree-sitter: Q# yes (community), OpenQASM yes (community), Python/Haskell as hosts.
9. Decidable: for OpenQASM and Q#: operation/function inventory, adjoint/controlled declarations, qubit allocation sites and release scoping, no-cloning violations (linear usage; decidable), measurement sites, gate-set conformance to a backend. Undecidable: circuit equivalence in general (QMA-ish; exact unitary equivalence is hard but decidable for fixed size), whether a Python-built circuit has depth N, amplitude behavior. Linter implication: linear (use-exactly-once) binder kind is native; "builder-code vs built-artifact" is the same two-phase structure as hardware generators (Chisel) and Terraform plans.

### F14 Configuration and data languages: Nix, Dhall, CUE, Jsonnet, Starlark, YAML/TOML with templating, HCL (Terraform)

1. Units: Nix: the FILE is one expression (usually a function from attrset to attrset; `default.nix`, `flake.nix`), attrset (the universal record/module/namespace), `let` binding, function (single-argument, curried; attrset-pattern args `{ a, b ? 1, ... }`), derivation (build recipe value), NixOS module (a function returning `{ options, config, imports }`; the module SYSTEM is a library-level fixed-point merge), overlay (`final: prev: {...}`), path literal (`./foo`, a first-class value resolved relative to the file), flake outputs. Dhall: file = expression, type annotations, imports (local/remote/env, content-hash-pinned `sha256:`), union types, `let`. CUE: package (directory-wide, many files unify into one), struct/field/definition (`#Def`), constraint, disjunction, default `*`, comprehensions, `let`; values ARE types (a lattice). Jsonnet: object with fields, `local`, function, `self`, `super`, hidden fields `::`, mixin `+`, imports, `std.*`, top-level arguments (`--tla-str`) and external variables (`std.extVar`). Starlark (Bazel, Buck, Tilt): `.bzl` module (loaded with `load("//pkg:f.bzl", "sym")`), `def`, rule/macro/provider/aspect (Bazel semantic layer), BUILD file (a list of target declarations), label `//pkg:name` as address of a target (not a file; addressable unit separate from source layout). HCL/Terraform: block types with labels (`resource "aws_s3_bucket" "b" { ... }`, `variable`, `output`, `module`, `locals`, `provider`, `data`), attributes, expressions, `for_each/count/dynamic`; address `aws_s3_bucket.b` (type.name) is the identity; module call = directory. YAML/Helm/Kustomize/Ansible: documents, anchors, resource identity = (apiVersion, kind, namespace, name) in K8s; a Helm chart template is Go-template text that renders to YAML. TOML/JSON/YAML pure data: tables, keys, arrays: units are keypaths (`[tool.frob] key`), no functions.
2. Binding: Nix lexical but `with expr;` (imports an attrset's names into scope: names depend on a runtime VALUE), `rec { }` recursive attrsets, `inherit`, `<nixpkgs>` angle-bracket lookup path (impure, environment-dependent), `import ./f.nix` (path resolution), laziness makes binding order irrelevant; fixpoints (`lib.fix`, `extends`, overlays, module merging: `config` referring to itself lazily). Jsonnet: `self`/`super` late binding in objects (open recursion). CUE: unification is order-independent; references resolve lexically by field path and by package. HCL: references `var.x`, `local.y`, `module.m.out`, `aws_x.name.attr` form an IMPLICIT DEPENDENCY GRAPH: order in file is irrelevant, the graph decides order. Starlark: lexical with `load` bindings frozen after module evaluation (immutability across modules, deterministic). YAML anchors `&a`/`*a` and merge keys `<<:` (aliasing, structural sharing). Template engines (Jinja, Go templates, Helm `.Values`, Ansible `{{ var }}`): dynamic context dictionaries.
3. Nix: lazy, pure functional; Dhall: total, normalizing (strong normalization: no general recursion; equivalence by normal form); CUE: constraint unification (monotonic, order independent, no side effects, bottom `_|_` on conflict; a finite-domain declarative language, mostly decidable fragments, though CUE with comprehensions/recursion is not guaranteed total); Jsonnet: lazy, pure, deterministic; Starlark: deterministic, hermetic, no while loops / recursion by default (guaranteed termination in strict mode; Go/Rust implementations allow recursion flags), freezing; HCL: declarative with expression language; "unknown values" until apply: plan-time vs apply-time evaluation (two-phase) ; Helm: template render then YAML parse then apply (three phases).
4. Nix untyped (dynamic; a type system is a long-standing research item; module system has its own option types with merge semantics); Dhall: simply typed + System-F-like polymorphism, no inference of polymorphism for functions (annotations), decidable; CUE: gradual constraint types (types and values in one lattice; subsumption); Jsonnet untyped; Starlark dynamic (Bazel `rule(attrs=...)` gives attribute schemas); HCL: dynamic type system with conversions (`list(string)`, `object({...})`, `any`) and `type` constraints on variables, inference for complex types; JSON Schema/CUE/Dhall as the typing layer for YAML/JSON; TOML typed literals (datetime).
5. Effects: Nix IFD (import-from-derivation: evaluation triggers builds), `builtins.fetchurl`/`fetchGit` (network at eval, pure only with hashes), `builtins.exec` (disabled by default), `readFile`/`getEnv` (impure unless pure-eval mode flake); Dhall remote imports (network at resolution; hash makes them cacheable) ; Jsonnet `importstr`, `std.native` callbacks; Starlark hermetic (no IO except `load` and rule-API actions; actions run later); Terraform providers perform ALL real effects at apply: the HCL file is an effect-free DESCRIPTION whose capabilities are the provider and resource types referenced (`aws_iam_role` means IAM-write capability) plus `provisioner "local-exec"`, `external` data source, `http` data source, `file()`.
6. Edges: attrset attribute selection `a.b.c`, function application, `import`, derivation input edges (a derivation depends on other derivations via string-context tracking: string interpolation of a store path creates a dependency edge: an EDGE CARRIED BY A STRING VALUE), Terraform resource references and `depends_on`, module inputs/outputs, `for_each` expansions (N instances from one block), Bazel label deps (`deps = [":x", "//y:z"]`) and `load` edges, Kustomize bases/patches (patch targets by name+kind), Helm `include`/subcharts, YAML alias edges, K8s `ownerReferences`/selectors/`serviceName` string-matching links (label selectors link resources by labels: a QUERY edge, set-valued).
7. Nix: fixpoint-based metaprogramming (overlays, `callPackage` introspects function argument names with `functionArgs`: BINDING BY ARGUMENT NAME, reflective dependency injection), `builtins.*` reflection, string-to-expression `import`/`eval` (via `builtins.readFile` + parse in some libs), `lib.mkIf/mkMerge` priorities; Dhall: none beyond functions and imports; CUE: comprehensions, `#Def` closed structs, embedding; Jsonnet: functions + `std.mergePatch`, `std.manifestYaml`, mixin inheritance `+`; Starlark: macros are functions called in BUILD files; Bazel rules/aspects/transitions; Terraform: `dynamic` blocks, `for_each`, `count`, `templatefile()`, `jsonencode/yamlencode`, module expansion; Helm/Jinja: text templating (code that is not valid in the target syntax until rendered); YAML itself: tags (`!!python/object` is dangerous: deserialization = eval).
8. Syntax: Nix CFG with string interpolation `${}`, indented strings `''...''`, path literals (lexer-level special tokens), `//` update operator (also a comment in other languages; Nix uses `#` for comments), no semicolon after last binding rules; Dhall CFG with unicode forms lambda and forall glyphs; CUE CFG, newline/comma insertion, optional field markers `?`, `!`; Jsonnet CFG (JSON superset); Starlark = Python subset, indentation-sensitive; HCL: block/attribute CFG with heredocs and interpolation `${ }` and template directives `%{ if }`; YAML: indentation-sensitive, context-dependent scalars (the Norway problem `no` -> false in YAML 1.1; multi-document `---`); Helm: Go template delimiters `{{ }}` embedded in YAML (NOT valid YAML pre-render; a linter must treat template regions as islands); TOML CFG. tree-sitter: Nix yes, Dhall yes, CUE yes (community), Jsonnet yes, Starlark yes (via Python variants), HCL yes, YAML yes, TOML yes; Helm templates partial.
9. Decidable: key inventory, imports/loads/module graph, resource and target inventory, reference graphs from literal traversals, cycle detection in HCL, anchors/aliases expansion (YAML bomb detection), schema validity of literal data (against JSON Schema/CUE: decidable), Starlark deterministic evaluation (can be fully executed, so a linter MAY legitimately execute these languages; the "never execute" stance has a principled exception for total/deterministic languages: Dhall, CUE, Jsonnet, Starlark, pure Nix modulo IO), Terraform provider capability inference from resource type prefixes. Undecidable (or impure): Nix with IFD/fetch/getEnv, `with` scope contents before evaluation, `<nixpkgs>` content, Terraform unknown-at-plan values, Helm values-dependent rendering (the template output depends on the values file), `dynamic` expansion counts, YAML `!!tag` semantics.

### F15 Markup and document languages: Markdown, LaTeX, Typst, HTML

1. Units: Markdown: document, heading section (anchors from ATX/setext headings: the section is a named unit by slug; duplicates get suffixes `-1`), fenced code block (language-tagged island), link reference definitions (`[id]: url`, positional-independent), front matter (YAML/TOML island), HTML blocks, footnotes, MDX (JSX + ESM imports in markdown), Obsidian wikilinks `[[note#heading|alias]]`, tags, frontmatter keys. LaTeX: document class + preamble + body, `\section` etc. (numbered hierarchy), `\label{...}` / `\ref{...}` (cross-ref via AUX file from a previous run: cross-references resolved across compilation PASSES), `\newcommand/\def` macros, environments `\begin{env}...\end{env}`, `\input/\include/\usepackage` (file splicing), BibTeX `.bib` entries with `\cite{key}`. Typst: markup with `#let` bindings, `#show` and `#set` rules (rule-based styling), functions, labels `<lab>` and `@lab` refs, `#import`, math mode, `#context` expressions. HTML: element tree with `id`, `class`, `name`, custom elements, `<script>`/`<style>` islands, `<template>`, forms/links by id/for/href fragment (`#id`), SVG/MathML islands; templating (Jinja, Handlebars, JSX, Blade, ERB, Vue SFC `<template><script><style>`).
2. Binding: Markdown: reference links resolve by label (case-insensitive, whitespace-normalized), headings by slug, cross-file by path+anchor; LaTeX: TeX MACROS bound at expansion time, GROUPS `{ }` scope assignments (dynamic-ish scoping of `\def` within group), counters, catcodes (a per-character lexer table changeable at runtime: `\catcode`), labels by string; Typst: lexical scoping of `let`, `set` rules scope until end of enclosing block, `show` rules apply to later content (context-sensitive), Typst `context` for position-dependent values (counter, locate), labels global to document; HTML: `id` global to document, CSS selectors bind rules to elements by structure (the cascade; specificity; inheritance of custom properties is DYNAMIC scoping along the DOM tree), `for=`/`aria-labelledby`/`href="#x"` by-id edges, forms by `name`.
3. Markdown: no evaluation (parse-only, with flavor differences: CommonMark vs GFM vs MDX vs Pandoc); LaTeX: macro expansion engine (TeX is a Turing-complete token-rewriting machine; expansion vs execution; multiple passes: LaTeX, BibTeX, makeindex, LaTeX again); Typst: functional expression evaluation producing layout, incremental compiler with constraint-based layout convergence ("introspection" re-runs until stable, max 5 iterations); HTML: parse into DOM (error-recovering algorithm, never fails), CSS cascade, JS events.
4. Mostly untyped; LaTeX has none (expl3 has a convention-based type prefix `\l_`, `\g_`, `_int`, `_tl`); Typst: dynamically typed with a type system for arguments and a `type()`; HTML: content models validated by schema/DTD-like rules (nesting constraints); accessibility rules; Markdown none.
5. Effects: LaTeX `\write18`/shell-escape (the file is a program with OS access; TeX distributions restrict via `shell_escape=p`), `\openin/\openout`, `\input` of arbitrary paths, `\directlua` (LuaTeX); Typst: `read()`, `image()`, package imports from a registry (`@preview/...`), no shell; HTML: `<script>`, `<iframe>`, `<link>`, `<form action>`, `<object>`, CSP as capability; Markdown with MDX/Jupyter: code execution at render time (Quarto, MDX `import`, Docusaurus plugins), raw HTML passthrough (XSS capability).
6. Edges: link (inline/ref/wikilink/autolink) to file/anchor/URL (edges with a TARGET that may be missing, i.e. dead links: the main structural lint), image/asset embed, include/transclusion (`![[note]]`, `\input`, `<!-- include -->`, Typst `#include`), macro invocation (`\foo`), `\ref`, `\cite`, CSS selector -> element set, `href` fragments, Typst `show` rule -> element kind it matches, HTML `import map`/ES module edges from `<script type=module>`.
7. LaTeX is wholly metaprogramming (macros that define macros, `\expandafter`, `\csname`, catcode changes, packages that redefine core commands; the TeX grammar is whatever macros are defined at that moment; static analysis requires tracking definitions: texlab/tex-fmt approximate); Typst: user-defined functions, `show`/`set`, scripting, `eval(mode: "markup")`; Markdown: extension syntax (admonitions, directives `:::`, MyST roles/directives, Pandoc filters) = user-extensible by tooling, not by the file; HTML: custom elements, web components, templating languages as islands; XSLT (F26).
8. Syntax: Markdown is line-oriented with a two-phase block/inline algorithm and NO syntax errors (everything parses as something; ambiguity resolved by priority rules; CommonMark spec has ~650 examples); LaTeX: not context-free; Typst: modes (markup, code via `#`, math via `$`) with a CFG per mode; HTML: forgiving, spec-defined error recovery, not a CFG parse; indentation-sensitive blocks in Markdown (lists, code). tree-sitter: Markdown yes (two grammars: block + inline, embedded injections), LaTeX yes (approximate, partial for macro-defined constructs), Typst yes (community), HTML yes (tolerant).
9. Decidable: headings/anchors, dead intra-repo links, duplicate anchors/labels, undefined label refs (LaTeX `\ref` vs `\label` in the same file set: decidable if no computed labels), fenced code block languages, front-matter keys, orphaned notes (no inbound edges), spelling-free structural checks. Undecidable: LaTeX parse in general, what a macro expands to, rendered output, Typst layout convergence, template-dependent HTML shape. frob already has markdown anchors as symrefs (`path#slug`): the generalization is that documents and code share an addressing scheme and edge model; code blocks inside Markdown are language islands that must be dispatched to a language adapter with a mapped span.

### F16 Build and shell: Make, Bash, Nushell, PowerShell

1. Units: Make: rule (`target: prereqs` + recipe), pattern rule (`%.o: %.c`), variable, `include`d makefile, phony target, `define` multi-line macro; Bash: command (the only construct: everything is a command invocation), function, alias, variable, `source`d file, script file with shebang, pipeline, here-doc; Nushell: `def` custom command with typed signature, module (`module`/`use`), closure, `$env`, table/record values (structured pipeline data); PowerShell: function/cmdlet/advanced function (Verb-Noun), module (`.psm1/.psd1`), class, script, DSC configuration, pipeline of OBJECTS. Also Just/Ninja/CMake/Bazel/Dockerfile/GitHub Actions (F32).
2. Binding: Make: variables expand LAZILY (`=` recursive, expanded at use) or immediately (`:=`/`::=`), target-specific variables, automatic variables `$@ $< $^`, `$(eval)` and `$(call)`; implicit rules database; second expansion; VPATH search; two phases (read-in builds the graph, then updates run recipes). Bash: DYNAMIC scoping (`local` is visible to callees), global by default, word-splitting and globbing expansions happen AFTER parse so the same text yields a variable number of args, `export` crosses process boundary into env, `$IFS`, positional parameters `$1`, `declare -n` namerefs, command lookup order (alias > function > builtin > PATH) so a name's meaning is runtime state. Nushell: lexical scope, `$env` is scoped, constants known at parse time (`source` and `use` require constant paths so the whole program is statically parseable: a design choice enabling analysis); PowerShell: dynamic scope with modifiers (`$global:`, `$script:`, `$private:`), `$using:` for remoting, provider drives (`HKLM:`, `Env:`), variable syntax `${...}`.
3. Make: declarative dependency DAG + imperative shell recipes (each recipe line is its own shell unless `.ONESHELL`); timestamps; parallel `-j`. Bash: sequential command execution, exit-status control flow (`&&`, `||`, `set -e` with notoriously subtle semantics), subshells `( )` copy state, process substitution, traps, background jobs `&`, pipelines with `pipefail`. Nushell: pipelines of structured values, streaming, closures, error values. PowerShell: object pipeline, terminating vs non-terminating errors, `$ErrorActionPreference`, jobs/runspaces.
4. Make/Bash: untyped strings (Bash has arrays and assoc arrays, integer attribute); Nushell: gradual static types with signatures `[x: int] -> string`, structured types (record, table), checked at parse time; PowerShell: dynamic with type accelerators and attributes, `[ValidateSet]`; `Set-StrictMode`.
5. Effects: they ARE the language: process spawn, filesystem, env, network via commands; Bash: every external command is a capability by NAME (`curl`, `rm`, `ssh`, `sudo`) found in PATH, sourced scripts, `eval`, command substitution, `trap`; Nushell: external commands via `^cmd`, `run-external`; PowerShell: cmdlet-level (Invoke-WebRequest, Remove-Item), execution policy, constrained language mode, `Invoke-Expression` (eval), .NET reflection; Make recipes: arbitrary shell. This is the family where frob's capability detectors match on COMMAND NAMES, not imports.
6. Edges: Make prerequisite edge (file-level, the unit is a FILE PATH, not a symbol; target -> prereqs, plus includes), recipe -> external commands; Bash: command word -> function/builtin/external program, `source` -> file, pipeline stage edges, `$(...)` nesting, `trap` handlers, `exec`; Nushell: command call (resolved statically via module scope), `use` edges; PowerShell: cmdlet call (resolved at runtime by command discovery: aliases, functions, cmdlets, external, module auto-loading), dot-source, `Import-Module`.
7. Make: `$(eval ...)` generating rules at runtime, `$(shell ...)` in the read phase, pattern rules, `include` of generated makefiles (restart semantics: make re-execs itself when an included file is rebuilt), GNU Make Guile; Bash: `eval`, `source`, aliases, `declare -f`, `PROMPT_COMMAND`, `trap DEBUG`, indirect expansion `${!name}`, arithmetic `$(( ))` with variable names in it; Nushell: `source` and `use` constant-path rule limits it deliberately; plugins; PowerShell: `Invoke-Expression`, `Add-Type` (C# at runtime), scriptblocks as values, AST available through `[System.Management.Automation.Language.Parser]` (a first-party parser API), dynamic parameters. Unknown pre-run: Make eval-generated rules, shell-computed names.
8. Syntax: Make: line-oriented, TAB-significant, two-level (Make syntax + embedded shell recipe text, `$` doubling `$$` to pass to shell: language island with escaping); Bash: context-sensitive POSIX shell grammar with quoting rules, expansions inside strings, heredocs delimiters that need lookahead, `[[ ]]` vs `[ ]`, `case` patterns, alias expansion at parse time, `{a,b}` brace expansion; Nushell: CFG-like with typed signatures and spans; PowerShell: expression mode vs argument mode (the same text parses differently by first token), here-strings, backtick escapes. tree-sitter: Make yes, Bash yes (good; ShellCheck uses its own parser: an indication that tree-sitter coverage is not enough for semantics), Nushell yes (community), PowerShell yes (community, partial).
9. Decidable: command-name inventory (literal first words), function/variable definitions, `eval`/`source` presence, unquoted expansions (ShellCheck SC2086 class), `set -e` presence, here-doc islands, Make target and prerequisite literal graph, `.PHONY` consistency, unused Make variables, Nushell types. Undecidable: what `$cmd` runs, word-splitting results (value dependent), alias state, exit-status flow with `set -e` interactions, whether a Make recipe produces its target, whether a dependency list is complete (missing prereqs: requires tracing builds, e.g. via strace/ninja deps), PowerShell dynamic command resolution.

### F17 Notebooks: Jupyter (and Pluto, marimo, Quarto, org-babel, WEB/CWEB)

1. Units: Jupyter `.ipynb` is JSON: ordered list of CELLS (code/markdown/raw), each with `source`, `outputs`, `execution_count`, metadata, and (nbformat 4.5+) a stable cell `id`; kernel = separate process holding state. Units are cells (anonymous unless id/tag), not functions; the file also stores OUTPUTS and execution history (derived data inside the source artifact). Pluto.jl: `.jl` file with cell delimiters, each cell exactly one expression, dependency DAG derived from references, one definition per global name (so order is irrelevant and reactive). marimo: plain `.py` file where each cell is `@app.cell def _(x): ... return y` (parameters = cell inputs, returns = cell outputs: the data flow is explicit in the signature). Quarto/R Markdown: markdown with fenced executable chunks `{python}` with options. Org-babel/WEB/CWEB literate programming: NAMED CHUNKS `<<name>>=` defined in several fragments anywhere in the doc and concatenated ("tangle"), referenced by `<<name>>` inside other chunks: ONE unit defined in non-contiguous fragments, and a document order that differs from program order.
2. Binding: Jupyter: ONE implicit global namespace per kernel; a name's value depends on which cells ran, in what order, how many times (hidden state; `In[n]`/`Out[n]`/`_`, `_i`); IPython magics `%`, `%%`, `!` shell escapes (NOT valid Python: a pre-transformation of source), `?` help; Pluto/marimo/Observable forbid multiple definitions and compute order from references (binding discipline fixes the problem).
3. Evaluation: user-driven, out-of-order, re-executable; reproducibility is a property of the saved execution order (`execution_count` monotonic?) not of the file; reactive notebooks (Pluto, marimo, Observable) rerun dependents automatically; Quarto renders top to bottom (freeze option).
4. Types: those of the cell language; nbformat has a JSON schema; marimo cell signatures are inferred.
5. Effects: arbitrary: kernels have full process capabilities; magics (`%pip install`, `!curl`, `%run`), network, `pickle` loading, widgets (JS execution in the browser: output cells can carry `text/html` with scripts, a classic notebook-injection vector), outputs embed images/HTML/JS.
6. Edges: cell -> names it reads/defines (only recoverable by analyzing the cell code; for Jupyter the true order is runtime), `%run other.ipynb`, imports, `papermill` parameters cell (a cell tagged `parameters` is an interface), `nbconvert` exporters, chunk references `<<name>>`.
7. Magics and cell magics change the language of a cell (`%%bash`, `%%sql`, `%%html`, `%%writefile`): each cell can be a DIFFERENT language island; kernel_spec selects the notebook-level language; widgets, `eval`.
8. Syntax: container is JSON, content is code in cells with IPython extensions; marimo/Pluto are text-first (diff-friendly); tree-sitter: Python/Julia/Markdown yes per cell, IPython magics need a preprocessing step; no grammar for the whole ipynb beyond JSON.
9. Decidable: cell inventory, per-cell imports/defs/uses (static), duplicate definitions across cells (marimo/Pluto error), unused cells, out-of-order `execution_count`, stale outputs vs source (mismatched hash if recorded), magics inventory, cells with secrets in outputs, large outputs. Undecidable: actual run-order dependence, reproducibility, hidden state. Linter implication: a unit that has an ORDER (execution log) separate from its position, and derived artifacts (outputs) co-located with source.

### F18 Term rewriting and homoiconic languages: Lisp, Racket, Mathematica, Maude, Pure

1. Units: Common Lisp: package (symbol namespace, runtime object with `in-package` state), `defun/defmacro/defgeneric/defmethod/defclass/defvar`, ASDF system (`.asd`); methods belong to GENERIC FUNCTIONS, not classes (multiple dispatch: a method is a unit attached to a generic function, defined anywhere); Scheme (R5RS/R6RS/R7RS-small/large): top-level define, library `(define-library ...)`; Racket: MODULE (a file, whose first line `#lang racket` / `#lang typed/racket` / `#lang scribble/manual` SELECTS the reader and module language: the language is a per-file declared parameter and can be user-defined), submodules (`module+ test`), phase levels; Clojure in F04. Mathematica/Wolfram: expressions only (`Head[arg1, ...]`), definitions are RULES attached to the head symbol (DownValues, UpValues, OwnValues, SubValues: "function definition" = a rule set stored on a symbol; `f[x_] := ...` adds a rule; contexts (namespaces) and packages `.wl/.m`, notebooks `.nb` (expressions as boxes)). Maude: module (`fmod ... endfm` functional, `mod ... endm` system, `omod`), sorts, subsorts, operators with attributes (`assoc comm id: e`), equations, rewrite rules `rl/crl`, memberships, theories/views (parameterization), strategies, META-LEVEL. Pure: term rewriting with `=` rules and pattern matching plus LLVM JIT; modules.
2. Binding: Lisp: lexical + SPECIAL (dynamic) variables via `defvar` (the same `let` is dynamic or lexical depending on a global proclamation: the binding kind is a property of the NAME declared elsewhere), packages decide which symbol a name reads as (read-time interning: names are resolved by the READER), Lisp-2 (separate function and value namespaces: `(f f)`), Scheme Lisp-1 with hygienic macros (`syntax-rules`: renaming guarantees; `syntax-case`: procedural), Racket: sets of scopes (Flatt 2016) for hygiene across macro expansion and phases; Mathematica: `Module` simulates lexical scope via unique renaming (`x$123`), `Block` is dynamic, `With`, pattern variables `x_`, `x__` (sequence), `x___`, conditions `/;`, named patterns `x:pattern`; Maude: variables are declared per sort and used in equations as pattern variables, matching MODULO equational attributes (associativity, commutativity, identity); rule order not fixed (system modules are nondeterministic).
3. Evaluation: Lisp strict, `call/cc` (Scheme), conditions/restarts (CL: handlers run BEFORE unwinding, restarts as a second-level control), tail calls (Scheme required); Racket: continuations, delimited continuations, parameters (dynamic binding objects), threads, places; Mathematica: evaluation is REPEATED REWRITING UNTIL A FIXED POINT (standard evaluation sequence with attributes `HoldAll`, `Orderless`, `Flat`, `Listable`; infinite evaluation possible), symbolic by default (unbound symbol evaluates to itself); Maude: equations are confluent/terminating by user obligation (checked by Church-Rosser checker, MTT), rules explore a state space (`search`, `rew [n]`, `frewrite`, model checker LTL); Pure: lazy-ish rewriting with `eval`.
4. Lisp untyped (CL has declarations; Typed Racket occurrence typing, Typed Clojure; Shen sequent-calculus types), Racket contracts (higher-order contracts as runtime wrappers, blame assignment), Mathematica none (patterns as dynamic structural checks), Maude: order-sorted algebra (subsorts, kinds, memberships): sort checking is decidable under conditions (sort-decreasingness checks), ACL2 (F24) first-order untyped with guards.
5. Effects: Lisp global mutation, image-based dev (save-lisp-and-die), FFI (CFFI), `eval`, `compile`, `load`, `read-eval` (`#.` read-time evaluation: arbitrary code at read time: reading data can execute code); Racket: `#lang` modules, security guard, sandbox (`racket/sandbox`), custodians; Mathematica: `Import/Export/Run/URLExecute/ToExpression`, kernel session state, `$Path`, paclets; Maude: `external objects` (I/O), META-LEVEL.
6. Edges: function call by symbol (resolved at runtime via the symbol's function cell: late binding, redefinable at any time), generic function dispatch on ALL arguments (multimethod: edge candidate set is every method in the generic, in definition-site-independent places; `call-next-method`, method combination `:before/:after/:around`), macro expansion (call position resolved to a macro: the edge is to compile-time code), `funcall/apply` with computed symbols, Racket `require/provide` and `for-syntax` (module edges tagged with PHASE level), Mathematica: symbol -> rules attached (definition is found by head symbol, not by lexical lookup; `UpValues` attach rules to ARGUMENT symbols), Maude: rewriting steps between terms; inheritance between modules (`including/extending/protecting` with different guarantees).
7. Lisp is the canonical case: code = data (S-expressions), `defmacro` unhygienic (variable capture), reader macros (`set-macro-character`: user-defined LEXICAL syntax at read time, `#+/#-` feature expressions: conditional reading), compiler macros, `eval-when` (explicit phase control), `load-time-value`, MOP (metaobject protocol: classes are programmable); Scheme: `syntax-rules/syntax-case/er-macro`, `eval`, `environment`; Racket: macros with phases, syntax objects with lexical context and source location, `syntax-parse` (macro grammars with error reporting), `#lang` implementation via readers, `define-syntax-rule`, language-oriented programming (a program is a tower of DSLs), `local-expand`; Mathematica: `Hold`, `ReleaseHold`, `Function` with `Slot`, `ToExpression`, `Replace`, `Rule`, symbolic metaprogramming is default; Maude: reflection (`META-LEVEL` module: modules and terms as terms, `upModule`, `metaReduce`), user-defined strategies.
8. Syntax: S-expressions (CL/Scheme/Racket/Clojure: trivial READ but reader macros extend; `#lang` can replace the entire syntax); Mathematica: operator-precedence with full-form equivalence (`a+b` = `Plus[a,b]`), notebooks use box expressions; Maude: MIXFIX (user-declared operator syntax `op _+_ : Nat Nat -> Nat [assoc comm]`, parsed by Earley-style ambiguity-resolving parser with sort info); Pure: Haskell/ML-like. tree-sitter: Lisp/Scheme/Racket/Clojure yes (structure only), Mathematica partial community, Maude partial community, Pure no.
9. Decidable: top-level definition inventory (`defun`, `define`), S-expression structure, `require/provide`, package exports (`defpackage`), macro definitions, `eval` presence, `#lang` line. Undecidable: macro expansion results, what a symbol call dispatches to, Mathematica rule applicability (pattern matching with conditions), Maude termination/confluence in general (checked by external tools for sufficient conditions), reader-macro effects. Linter implication: S-expression trees give a trivially parsable shell but ZERO semantics until macros expand; for macro-heavy languages the unit and binding structure is only known post-expansion, so the IR needs an "unexpanded form" node with the head symbol, and a registry of known macro heads with their binding behavior (e.g. `let`, `defun`, `loop`, `with-*`).

### F19 Esoteric languages: Brainfuck, Befunge, Malbolge, Whitespace, INTERCAL, Piet, Unlambda, lambda calculus, SKI, Iota, Jot, binary lambda calculus

1. Units: Brainfuck: none (a flat string of 8 commands `+-<>[].,`; loops by matched brackets are the only structure; tape cells are unnamed, indexed by pointer). Befunge: 2D grid of characters, the "program" is a torus; no units. Malbolge: a trinary self-modifying program in a memory image; no units. Whitespace: only space/tab/LF count; all other characters are COMMENTS (the source is mostly invisible; labels are bit strings of spaces/tabs; instruction set with IMP prefixes: stack, arithmetic, heap, flow, I/O). INTERCAL: numbered or labeled statements `(10) DO ...`, each optionally prefixed `PLEASE`, with `NOT/%` probabilistic execution; units are labels. Piet: a PICTURE; program counter walks blocks of same-colored pixels (codels), instructions are encoded by hue/lightness CHANGE between adjacent blocks; no text. Unlambda: applicative terms over combinators `s k i`, with `` ` `` application prefix, `.x` print, `r`, `d` (delay), `c` (call/cc), `e`, `v`. SKI: terms over S, K, I and application. Iota: ONE combinator (iota) from which all else derives. Jot: every binary string is a valid program (no syntax errors); a string denotes a combinator by folding `0`/`1` as two builders. Lambda calculus: terms `x | \x.M | M N`; binding by names with alpha-equivalence; BLC (Tromp): lambda terms encoded as bits (`00` abstraction, `01` application, `1^n 0` de Bruijn index n), I/O via lazy bit streams.
2. Binding: BF: none (tape position). Befunge: none (stack + grid memory, `p`/`g` read/write the program itself). Whitespace: stack and heap positions; labels. INTERCAL: variables by number-sigils (`.1` 16-bit, `:1` 32-bit, `,1` arrays, `;1` 32-bit arrays), ignoring states (`IGNORE/REMEMBER`). SKI/Iota/Jot/Unlambda: NO variables: bracket abstraction eliminates binders (combinatory logic is the variable-free form of lambda calculus). Lambda calculus: named binders with alpha-conversion, capture-avoiding substitution; alternatives: de Bruijn indices (nameless; binding = distance to binder), de Bruijn levels, locally nameless (bound = indices, free = names), HOAS (binders as host functions), nominal (names as atoms with swapping). BLC uses de Bruijn indices in unary.
3. Evaluation: BF: imperative on a tape; Befunge: instruction pointer moves in 4 directions across a wrapping grid, `?` random direction, `p` self-modifying (so control flow graph is dynamic); Malbolge: `crazy` op, code encrypts itself after each instruction; Whitespace: stack machine with labels/jumps; INTERCAL: `COME FROM label` (the control transfer is declared at the DESTINATION: an edge pointing from the target back to... any line that follows the label), `NEXT/RESUME/FORGET` (computed return stack), `ABSTAIN FROM/REINSTATE` (dynamic enable/disable of statements by label or type: statement validity is a runtime flag); Piet: block-walking with direction pointer + codel chooser; lambda calculus family: beta reduction, strategy-dependent (normal order vs applicative; Church-Rosser confluence; normalization undecidable; typed variants normalize); Unlambda: strict applicative order with `d` for promises and `c` for continuations.
4. Types: none (all except typed lambda calculi: simply typed, System F, CoC are the foundation of F05/F06). SKI/lambda: untyped terms with Turing-completeness; type inference for untyped lambda (simple types) is decidable (unification), typability of arbitrary terms is not guaranteed.
5. Effects: BF `,` `.` byte IO; Befunge file/system calls in some dialects (`=` execute in Funge-98); Malbolge IO ops; INTERCAL IO via Turing text model; Piet in/out; SKI none (Unlambda has `.x`, `@`, `?x`, `|`); lambda calculus pure. Capability detection is trivial: no instruction set carries capabilities except Funge-98 `=`/`i`/`o`.
6. Edges: BF: loop bracket pairs (matched statically; CFG exact except pointer behavior); Befunge: static CFG impossible if `p` used; neighbors in 4 directions; Whitespace labels; INTERCAL: line labels + `COME FROM` (reverse-direction edge) + `ABSTAIN`; Piet: block adjacency graph (color blocks and boundaries); lambda calculus: application (the only edge) and variable-to-binder edges (resolved by index); SKI: application tree.
7. Metaprogramming: BF none (but interpreters of BF are standard test programs); Befunge `p` self-modification, Malbolge self-encryption, Whitespace none, INTERCAL none (compiler options), lambda calculus: Church/Scott/Mogensen-Scott encodings represent data and code as terms (reflection by encoding, e.g. self-interpreter in BLC is ~210 bits); Jot/Iota: Goedel numbering.
8. Syntax: BF 8 chars (every other character ignored: text IS comments; commonly commented `+-` hazards in prose), Befunge 2D (grid, a "line" has no meaning, columns do), Whitespace 3 chars, INTERCAL natural-ish with politeness rule (too few or too many PLEASE refuses compilation: a lint on statement counts), Piet image formats (PNG/GIF), Unlambda prefix ASCII, Jot/BLC bit strings (no syntax errors in Jot; BLC has a prefix-free grammar). tree-sitter: Brainfuck community, Befunge no (2D), Whitespace no, others negligible; lambda calculus in any generic parser.
9. Decidable: bracket balance (BF), tokenization, instruction counts, static unreachable code in BF/Whitespace (partially), alpha-equivalence of lambda terms, beta-normal form check (syntactic), free variables, closed-term check, size, de Bruijn conversion. Undecidable: halting, equivalence of lambda terms (Church/Rosser/Scott: the word problem), dead code in Befunge with `p`, program output. Linter implication: these never need new LINT SEMANTICS but they stress the IR in three ways: (a) no names at all (anonymous/positional units), (b) 2D and image locators, (c) invisible-source languages (Whitespace) where "comments" are most of the file; plus lambda calculus itself shows the minimal universal binding forms (named, de Bruijn, none).

### F20 Newer "weird type" languages (Idris 2, Granule, Koka, Effekt, Unison, Dark, Kind, HVM, Mojo, Carbon, Vale, Austral, Flix, Verse, Roc, Gleam, Grain, Hazel, Cedar, Rego, Lustre, Esterel)

Each entry gives the features not already covered by F01-F19 (Q1 units, Q2 binding, Q3 evaluation, Q4 types, Q5 effects, Q6 edges, Q7 meta, Q8 syntax, Q9 linter limits, as relevant).

- Idris 2: Q4 Quantitative Type Theory: every binder has a multiplicity 0 (erased), 1 (linear), or omega (unrestricted), so one dependent system also carries linearity and erasure (McBride/Atkey QTT); elaborator reflection; `%` pragmas (`%default total`, `%hint`, `%foreign`); `export` vs `public export` decides whether a definition reduces in types (visibility affects typing, so a visibility lint is semantic). Q2 implicit `{n : Nat}` and `auto` implicits (search), idiom brackets and bang notation (syntax desugaring). Q8 layout-ish (indentation after `where`/`of`), tree-sitter community (partial).
- Granule: Q4 GRADED MODAL types: types carry grades from a semiring (`a [2]`, `[0..1]`, privacy levels, security lattices, sensitivity `Fuzz`-style); linear by default, grades describe how often/how a value is used; checking via SMT (Z3) solving grade constraints (decidable for supported semirings); Q9: grade annotations are structural data a linter can read, checking needs the solver. Q8 Haskell-like, no tree-sitter.
- Koka: Q4/Q5 ROW-POLYMORPHIC EFFECT TYPES: every function type lists its effects `() -> <exn,div,console> int`, handlers (`with handler`) remove effects, `pure/total` = empty row; effect inference decidable (row unification); `fip`/`fbip` (functional but in-place) checking; Perceus reference counting makes allocation reuse part of the semantics; Q6: an operation call is an edge to the nearest enclosing HANDLER (dynamic, but lexically scoped in Effekt). Q8 braces and indentation, tree-sitter community.
- Effekt: Q2/Q4: effect handlers with LEXICALLY scoped capabilities (effects are second-class capability parameters: a block parameter `{ exc: Exception }` passes the capability); `region`s; effect polymorphism by "contextual" treatment of block arguments. Same edge structure as Koka but handler binding is lexical (statically resolvable: operation -> handler edge is decidable).
- Unison: Q1 DEFINITIONS ARE IDENTIFIED BY HASH of their abstract syntax tree (names are just metadata in a codebase DATABASE, not source text); renaming doesn't change identity; no builds, no dependency conflicts; the `.u` scratch file is an editor buffer that `ucm` adds to the codebase; Q4 ABILITIES (effects) in types `{IO, Abort}`; Q6 call edges are by hash; Q7 distributed computing by shipping closures between nodes (`Remote`), so "where code runs" is first class. Q9: a linter over `.u` files sees only a window onto the codebase DB; source locator = hash/namespace path, not file+span. Structural lessons: (a) identity can be CONTENT-ADDRESSED; (b) a name is an attribute of a unit, not its identity; (c) no files.
- Dark (Darklang): structured editor + hosted backend; code is stored in a runtime, edited by a projectional editor (originally no text), deployless ("feature flags" for versions, traces as inputs); source is an AST in a database; Q8 non-textual (the F# rewrite adds a text syntax; the current status is unverified, section 9). Structural lessons: projectional/non-textual source; HTTP handlers, workers, cron, datastores as first-class unit KINDS (a unit is a handler bound to a route, not a function).
- Kind (and Kind2) / HVM / Bend: Q3 INTERACTION NETS / INTERACTION COMBINATORS (Lafont): programs are graphs of agents with ports and rewrite rules on principal-port pairs; reduction is local, confluent, massively parallel (HVM runs on GPU), OPTIMAL evaluation of lambda terms (Lamping/Levy), no garbage collector (linear dup/erase with explicit duplication nodes `&` labels); Kind: dependent types (a proof language) compiling to HVM; Bend: Python-like surface language, `bend`/`fold`/`fork` constructs expressing parallelism by data-structure recursion. Q2 variables are LINEAR in the net (each variable occurs exactly once; copying is explicit via duplication nodes `dup`), so affine/linear binder use is the baseline, not an extension. Q9: net structure is a graph (no tree), duplication labels matter for correctness (a label-mismatch lint class).
- Mojo: Q4/Q5 superset-of-Python surface with `fn` (strict typed, ownership conventions `read/mut/owned/out`, previously `borrowed/inout`) vs `def` (dynamic Python-like); `struct` (static, value) vs `class` (dynamic); `@parameter`/compile-time parameters in `[ ]` (a compile-time metaprogramming layer: generics are value parameters evaluated at compile time, like Zig comptime); `SIMD[DType, n]` first-class vector type, MLIR dialects inline via `__mlir_op`, Python interop via `Python.import_module`; `raises` as an effect annotation (checked); borrow checker with origins/lifetimes (evolving). Q8 indentation-sensitive. Two languages in one file (`def` vs `fn` modes differ in semantics): per-DECLARATION language dialect.
- Carbon: Q1 packages with API files and implementation files (`api` / `impl` in the file name or declaration), explicit `library "..."` partitions; `class`, `interface`, `impl T as I`, `choice`, `mixin`, `namespace`; Q4 GENERICS CHECKED AT DEFINITION (checked generics via interfaces, unlike C++ templates), `where` constraints; Q6 interop with C++ (`import Cpp library "header.h"`): cross-language edge by import; Q7 template generics available as an escape hatch (`template` keyword); Q8 CFG designed for tooling (no context-sensitive parsing: a deliberate decision), tree-sitter community (status unverified). Lesson: a language designed to be PARSEABLE WITHOUT SEMANTIC INFORMATION; an API/impl file split again.
- Vale: Q2/Q4 GENERATIONAL REFERENCES (each allocation has a generation counter, checked on dereference: memory safety without GC or borrow checker), REGIONS (isolating sub-heaps with a pure-function-based "region borrow checker": inside a `pure` function, immutable region data are freely aliasable, no checks), `inl`/`imm` mutability annotations, linear types opt-in ("higher RAII", types that must be explicitly consumed). Structural: a region/ownership annotation on references; "pure" marker is an effect-like flag.
- Austral: Q1 every module has an INTERFACE FILE (`.aui`) and BODY FILE (`.aum`); Q4 LINEAR TYPES (`Linear` universe vs `Free`), capabilities are linear values (`RootCapability` threaded to code that needs FS/network; `Region`/borrow `&[T, R]`, `&![T, R]` (mutable)), so the capability matrix is IN THE TYPE SYSTEM (like Pony's AmbientAuth), checked by a simple linearity checker; no implicit conversions, no operator overloading, no macros, deliberately small spec so that the whole language is checkable by a small tool. Q8 CFG, Pascal-like keyword blocks.
- Flix: Q3/Q6 DATALOG CONSTRAINTS AS FIRST-CLASS VALUES inside a functional language: `#{ Edge(1,2). Path(x,y) :- Edge(x,y). }` constraint sets are values, composed with `<+>` and solved with `solve`/`query`; Q4 HM + type classes (traits) + algebraic effects + `Pure/Impure` purity polymorphism (effect system with `\ ef` set-based effects `IO`, `Net`, etc., recent versions) and region-based mutable state; Q5 effect sets are a checked capability signal; Q6 BOTH a function call graph AND a predicate dependency graph live in one program. Q8 braces. tree-sitter: community. Lesson: mixed-paradigm units (function + constraint system) in one file.
- Verse (Epic Games, UEFN/Fortnite): Q3 functional-logic language with FAILURE and CHOICE: expressions can FAIL (failure contexts `if (cond)`, `for`, `<decides>`), `a | b` is CHOICE (all alternatives, a sequence of values), `?` queries an option, `:=` defines, `=` UNIFIES/compares, speculative execution with ROLLBACK of effects in failure contexts (`<transacts>`), `<suspends>` (async, structured concurrency: `sync`, `race`, `rush`, `branch`, `spawn`), `<decides>`, `<varies>`, `<computes>`, `<converges>` as EFFECT SPECIFIERS ordered in a lattice (`<computes>` < `<varies>` < `<transacts>` etc.), the Verse Calculus (Augustsson et al, ICFP 2023) as core; Q4 types as functions that fail; Q2 indentation-sensitive blocks with `:` and `.`; Q6 calls plus failure edges. Lesson: control can be "fall through on failure" rather than if/else; effect specifiers are a lattice annotated per function; a statement's value is a SEQUENCE of choices.
- Roc: Q1 APPS vs PLATFORMS: an app is pure Roc code; the PLATFORM (written in Zig/Rust/C) provides effects, the `Task`/effect interface and the main loop: the app's capabilities are fixed by the platform it targets (a build-level capability boundary); Q4 HM with structural tag unions, open records, abilities (typeclass-like, no HKT), opaque types; no mutation, no exceptions; Q8 indentation + curly braces. Lesson: capability boundary = which platform.
- Gleam: Q4 static HM, NO typeclasses/macros/exceptions; `Result` + `use x <- f()` (syntactic callback flattening, a desugaring rewriting the rest of the block into a closure: control-flow syntax that introduces a binder and an anonymous function); labelled arguments; `@external(erlang, "mod", "fun")` and `@external(javascript, ...)` (FFI: ONE declaration with per-target implementations: multi-target unit like Kotlin expect/actual); targets BEAM and JS. tree-sitter: yes (community).
- Grain: ML-like typed language targeting WebAssembly; `module`, `provide`/`from ... include`; Q5 WASM host imports are the effect boundary (`foreign wasm`); nothing structurally new beyond F04 + F25.
- Hazel: Q8/Q1 TYPED HOLES everywhere: an incomplete program is a meaningful program (empty hole `?`, non-empty hole wrapping an ill-typed expression); every editor state has a type and an evaluation result ("live programming": hole closures, evaluation proceeds around holes, results contain indeterminate expressions); structure (projectional) editor (cursor-based; text is a rendering); gradual typing (`?` dynamic type; cast calculus); livelits (GUI widgets embedded in source). Lesson: HOLE is a first-class node kind; tolerance for partial/ill-formed code is a semantic feature (Agda goals, Lean `sorry`, Coq `admit`, tree-sitter ERROR nodes are all the same idea).
- Cedar (AWS): Q1 policies: `permit|forbid (principal, action, resource) when {...} unless {...};` plus a SCHEMA of entity types/actions; Q3 no loops/recursion/user functions, so evaluation is total and linear; `forbid` overrides `permit`, default deny; Q4 validated against the schema; Q9: decidable analysis by SMT (equivalence, implication, "does policy A allow anything B does not"); policy set is an UNORDERED set; entity references `User::"alice"`. Lesson: a unit that is a RULE with (subject, verb, object, condition) shape; no call graph at all, edges are entity-type references.
- Rego / OPA: Q1 rules in packages (`package a.b`), `import`, partial rules (`allow[x] { ... }` sets, objects), complete rules (single value), `default`, functions, `with` (mock/override input or data for a single evaluation: a scoped dynamic rebind); Q2 DATALOG-like: unification `=`, assignment `:=` (local), comparison `==`; every variable must be SAFE (bound by a positive expression); undefined (not false) propagates and `not` is negation as failure; Q3 queries evaluate as conjunction with backtracking over iteration `x := arr[_]`, no recursion unless explicit (recursion allowed but checked), termination by stratified negation; the documents `input` and `data` are the ambient external state. Q6 edges: rule reference `data.pkg.rule` (global dotted path, can reference ANY rule by path: a computed global namespace), `with` rebinding. Q9: decidable safety/stratification/recursion checks; evaluation depends on input.
- Lustre / Esterel (and SCADE, Signal, Lucid, Blech, Cea): Q3 SYNCHRONOUS languages: time is a sequence of logical instants; Lustre: DATAFLOW with streams as values (`x = 0 -> pre y + 1;` where `pre` delays one instant, `->` initialization, `when/current` for sub-clocks), NODES as units (reactive functions) with inputs/outputs, equations (UNORDERED, single-assignment per variable per instant), CLOCK CALCULUS (a type-like analysis: every stream has a clock; operands must be on the same clock; checked statically), CAUSALITY analysis (no instantaneous cycles), bounded memory and time by construction; Esterel: IMPERATIVE synchronous: signals (pure or valued), `emit`, `present`, `await`, `abort ... when`, `suspend`, `trap/exit`, parallel `||` with instantaneous broadcast, constructive causality (a cycle is accepted only if the constructive semantics resolve it), compiles to circuits or finite automata. Q4 clock types, signal types. Q5 sensors/actuators via declared interface; Q9: EVERYTHING is decidable (finite state; bounded), including reachability, determinism, and equivalence of nodes by model checking (e.g. Kind 2 for Lustre, `Lesar`): the most analyzable family in this note. Q6 edges: node instantiation (with static fan-in), variable-to-equation dependency (instantaneous vs delayed `pre` edges: two edge LABELS, the acyclicity check applies only to instantaneous edges). Lesson: edges carry TEMPORAL labels (instantaneous vs delayed), also relevant for HDL (clocked vs combinational), Excel (volatile), Max (control vs signal).

### F21-F33 Added families (delta form: only what differs from F01-F20)

Format: Q-numbers where the family differs materially; everything else is "as F0x".

F21 Scripting and dynamic (Python, Ruby, Perl, PHP, Lua, Tcl, R, Julia, Raku)
- Q1: file/module = unit; a CLASS or function can be (re)opened and extended anywhere (Ruby open classes, Python monkey patching, Lua metatables), so a unit's member list is not closed by its declaration. Julia: methods belong to generic functions (multiple dispatch, like CL), modules, `@kwdef`, macros `@name`. R: functions are the unit; packages with NAMESPACE files; S3/S4/R5 classes where S3 dispatch is by naming convention `print.foo`. Perl: package + `bless` (a class is a package; objects are blessed references), `use`/`require`, typeglobs, `local` (dynamic scope), contexts (list vs scalar decided by call site). Raku: grammars as first-class declarations, multi-dispatch `multi`, roles, `use`-lines select language version. Tcl: EVERYTHING IS A STRING; commands are the only construct; `proc`, `namespace`; `uplevel/upvar` (stack-frame-relative variable binding: dynamic).
- Q2: Python LEGB with `global/nonlocal`, class bodies are scopes not visible to methods, comprehension scopes; `import` executes code (a module = a side-effecting script); Ruby: no block-local scope leakage, `binding`, `instance_eval/class_eval` rebind `self`; Lua `_ENV` upvalue (the global environment is an explicit variable, so sandboxing = replacing it); R: lexical + LAZY promise arguments + non-standard evaluation (`substitute`, `quote`, formulas, `with`, tidyverse data-masking: a name inside `dplyr::filter(x > 3)` means a column, not a variable: binding depends on the callee's semantics); Julia: global/soft/hard local scope rules; PHP: no closures capture by default (`use ($x)`, arrow fn auto-captures), variable variables `$$x`, `extract`, `compact`.
- Q4: dynamic; gradual annotations (Python type hints PEP 484 non-enforced; `.pyi` stubs are a SECOND FILE declaring the types of the first: another interface/implementation split; `typing.overload`, `Protocol` structural types, `TypedDict`, `ParamSpec`, `TypeVarTuple`; mypy/pyright undecidability corners), TypeScript (structural, Turing-complete type language, `any`/`unknown`, declaration merging, `.d.ts`), Hack, Sorbet/RBS (Ruby types in separate `.rbs`/sigs), Luau, Julia parametric types with dispatch, R none; checking decidable only with limits.
- Q5/Q7: `eval/exec/compile`, `__import__`, `importlib`, `ctypes/cffi`, `subprocess`, `pickle` (arbitrary code on load), `__getattr__/method_missing/AUTOLOAD/__index` (calls to names that DO NOT EXIST in source), decorators (rewrite a function at definition time), metaclasses, descriptors, `setattr`, Ruby `define_method`, DSL via blocks, PHP `include` of computed paths, magic methods, Perl source filters/`BEGIN` blocks (code at parse time: parse and run interleave), Lua `load`, Tcl `eval/uplevel`. Name-resolution: a call to an attribute can be created at runtime.
- Q6: call edges via names; decorators and descriptors add invisible indirection; framework magic (Django/Rails/Spring: routes, signals, ORMs, dependency injection by name or type annotation) create edges that exist only in framework semantics (pytest fixtures are injected BY PARAMETER NAME: call edge from test to fixture function resolved by argument name, see also Nix `callPackage`).
- Q8: Python indentation-sensitive (INDENT/DEDENT tokens from the lexer), f-string nesting (3.12 grammar change), soft keywords (`match`, `case`, `type`), walrus; Ruby: heredocs, optional parens, `%w` literals, ambiguity solved by parser state; Perl: undecidable parse (Kegler's argument: parsing Perl 5 is undecidable, because BEGIN blocks and prototypes run code during parsing), PHP embedded in HTML (`<?php ?>` islands), R CFG with `%op%` user operators (user-defined infix by name), Lua small CFG. tree-sitter: all yes (Perl/R/Raku approximate).
- Q9: decidable: definitions, imports, decorators, syntactic call sites, global/nonlocal statements, `eval` presence; undecidable: attribute existence, monkey-patch effects, dispatch targets, tainted data, import side effects. Unit-inventory soundness is lost for open classes and runtime-added members.

F22 Legacy, enterprise, record-oriented (COBOL, Fortran, PL/I, RPG, ABAP, JCL, Ada/SPARK, Pascal/Delphi, Eiffel)
- COBOL: units = programs (`IDENTIFICATION DIVISION. PROGRAM-ID.`), four DIVISIONS (identification, environment, data, procedure) as a fixed structure, SECTIONS and PARAGRAPHS (named labels; `PERFORM para THRU para2` calls a RANGE of paragraphs, so the call target is an interval of source text and fall-through between adjacent paragraphs is control flow), COPYBOOKS (`COPY` textual inclusion with `REPLACING`: a preprocessor), DATA as a HIERARCHY of level numbers (01..49, 66, 77, 88 condition names) with PICTURE clauses (the data declaration is a layout of bytes: `REDEFINES` overlays one storage area with several types, `OCCURS DEPENDING ON`), fixed-format columns (cols 7 indicator, 8-72 code); `CALL 'PGM' USING BY REFERENCE`, CICS/SQL embedded (`EXEC SQL ... END-EXEC`, `EXEC CICS`: islands with host variables `:var`). `ALTER` (self-modifying goto) in old dialects. Binding: all data is global to the program (WORKING-STORAGE) unless LOCAL-STORAGE; names qualify `X OF Y` (hierarchical qualification: a name denotes a path in the record tree). Decidable: paragraph graph (with PERFORM THRU intervals), data hierarchy, copybook expansion, EXEC islands. Undecidable: ALTER, dynamic CALL (`CALL identifier`).
- Fortran: program units (program, module, subroutine, function, block data), `COMMON` blocks (named shared storage, overlaying with different declared shapes across units: aliasing by position), implicit typing (names starting I-N are integer unless `implicit none`), fixed vs free source form, `EQUIVALENCE`, coarrays/DO CONCURRENT/OpenMP directives as comments `!$omp` (directive islands in comments: precedent for frob's comment DSL), preprocessor (cpp). Array syntax is first-class (like F09). Calls are by reference; `INTENT(in/out/inout)` is a checked effect-like contract on parameters.
- PL/I, RPG, ABAP, JCL: RPG has an implicit program CYCLE (main loop reads a record, runs calculation specs, writes: control flow is not in the source) and fixed-column specification forms (H, F, D, C specs) with INDICATORS (global boolean flags `*IN01`) as the control mechanism; ABAP: event blocks (`START-OF-SELECTION`), classes, internal tables, Open SQL embedded, transport requests as code deployment units, repository objects stored in a DB (no files: like Smalltalk/Unison); JCL: job steps `//STEP1 EXEC PGM=...` with DD statements binding logical names to datasets (indirection: program uses a DDNAME, JCL maps it to a file: the file edge lives OUTSIDE the program in another language). Structural lessons: column-positional syntax, implicit control cycles, external binding tables (DD names, environment), repository without files.
- Ada/SPARK: package SPEC (`.ads`) and BODY (`.adb`) (another spec/impl split), generic packages (instantiated explicitly: `package I is new G (Int)`), tasks and protected objects (rendezvous entries, `select` with guards), representation clauses (layout), subtypes with range constraints and discriminants (a dependent-ish type feature), exceptions, pragmas/aspects (`with Pre => ..., Post => ..., Global => ...`: contracts in source; SPARK PROVES them: `Global`/`Depends` flow contracts are a checked data-flow capability annotation), `Ravenscar` profile restricting tasking. Decidable: package graph, contracts present; flow analysis by SPARK tools; undecidable: proof obligations in general (SMT discharges many).
- Pascal/Delphi: `unit` with `interface` and `implementation` sections in ONE file; `uses` clauses ordered; Eiffel: classes, design-by-contract (`require/ensure/invariant` as syntax), multiple inheritance with `rename/redefine/select`, `once` routines, SCOOP concurrency; contracts are first-class syntactic structure (like Ada aspects, JML, Dafny). A contract clause on a unit is a feature the IR should carry (pre, post, invariant, frame/`modifies`).

F23 Smart contracts (Solidity, Move, Vyper, Cairo)
- Solidity: `contract` (class-like, deployed state container with persistent storage), `modifier` (code wrapper inlined with `_;` placeholder), `event`, `library`, `interface`, `payable/view/pure` state-mutability specifiers (an EFFECT ANNOTATION in the signature: pure < view < nonpayable < payable), visibility `public/external/internal/private`, `delegatecall` (runs callee code in caller's storage: binding of storage by slot layout), fallback/receive functions, inline `assembly` (Yul island), reentrancy as the headline bug class. Move: modules and scripts, RESOURCES with abilities (`copy`, `drop`, `store`, `key`): a type without `drop` must be consumed (linear), without `copy` is not duplicable (affine/linear), `acquires` annotation lists global resources a function touches (a checked effect-like list), Move Prover specs (`spec` blocks, `ensures`, `aborts_if`, `invariant`: verification conditions in the language). Vyper: Python-like, no inheritance/modifiers/recursion, bounded loops (analyzable gas). Cairo: provable computation, felt arithmetic, ownership/borrow, `#[derive]`, `#[starknet::contract]`, gas accounting. Q5: external calls and storage writes are the boundary (capability: sending value, calling untrusted code, selfdestruct, tx.origin). Q9: gas bounds decidable in loop-free/bounded code; reentrancy partially detectable syntactically (check-effects-interactions pattern on the CFG). Edges: external call to address (unresolved target through interface type), `delegatecall`, `emit`.

F24 Specification and verification (TLA+, Alloy, Dafny, Why3, Isabelle, ACL2, Twelf, P)
- TLA+: modules, definitions, ACTIONS (relations between state `x` and next state `x'`: PRIMED variables, not assignments), `Init`, `Next`, temporal formulas `[]<>`, `Spec == Init /\ [][Next]_vars`, invariants checked by TLC (finite model) or proved by TLAPS; PlusCal (pseudocode compiled to TLA+, embedded in a comment block: comment island). A spec is a NONDETERMINISTIC TRANSITION RELATION: units are predicates over pairs of states. No execution. Decidable: syntax/definitions/prime discipline; undecidable: validity in general; bounded by TLC.
- Alloy: signatures `sig` (types as sets with fields as relations), facts, predicates, assertions, `run`/`check` commands with BOUNDS (scope); relational logic + transitive closure; bounded model checking via SAT (decidable by bounding). Dafny: methods/functions with `requires/ensures/reads/modifies/decreases` clauses, ghost code (specification-only statements, erased at compile time), lemmas, loop invariants; Why3/WhyML similar; verification conditions via Boogie/Z3 (undecidable in general; "unknown" outcomes and timeouts are first-class results). Isabelle: `.thy` theory files with TWO LEVELS of syntax (outer command syntax, inner term syntax in quotation marks `"..."`/cartouches, antiquotations `@{term ...}`, ML embedded `ML \<open> ... \<close>`), locales (parametrized contexts with assumptions), Isar structured proofs (`proof ... qed`, `have`, `show`, `obtain`), `sledgehammer`. ACL2: Lisp subset, `defun` with `:guard`, `defthm` (theorems must be proved from earlier events: event history is a total order: the "world" is state, like Lean/Coq), measure for termination (admission), `encapsulate`. Twelf: LF signatures (types as judgments, higher-order abstract syntax: object-language binders are meta-language functions; `%mode`, `%worlds`, `%total` declarations check coverage and termination of relational definitions: logic programming in LF). P: state machines with events, typed message passing, model checking via systematic testing of schedules (an actor language for protocol verification).
- Structural lessons: (1) contracts/specs attach to code as first-class clauses (requires/ensures/invariant/modifies/decreases/ghost); (2) ghost/erased code exists only for verification: a node flag `phase=spec`; (3) "event history" files (ACL2, Lean, Coq, Isabelle theory sequences) evolve a state; (4) proofs-as-source need an "obligation" entity (verification condition) with status (proved/unknown/failed/admitted) that a linter can list without proving.

F25 Assembly and low-level IR (x86-asm, LLVM IR, WebAssembly, MLIR, JVM bytecode, eBPF)
- Units: labels, sections (`.text/.data`), directives, macros (assembler macro languages are Turing-complete, MASM/NASM `%macro`/`.macro`), local labels (`1f/1b` numeric forward/backward refs: position-relative binding), symbols with linkage (global/weak/local), relocations (symbolic references resolved at LINK time: the link edge is a separate phase). No types (assembly), registers as global mutable variables (binding = register name; calling conventions are an external ABI doc).
- LLVM IR: SSA (every value defined exactly once; dominance determines scope), basic blocks, `phi` nodes (merge of values by predecessor: binding by control-flow edge), functions, globals, metadata, intrinsics, attributes (`nounwind`, `readonly`: effect annotations!), typed (first-order types, opaque pointers), calling conventions. WASM: module with imports/exports (the capability interface: a module can only call what its host imports: CAPABILITY-BASED by construction), structured control flow (blocks/loops with LABEL DEPTH branches `br 1`: de Bruijn-style label binding), stack machine with VALIDATION (type-checked stack discipline, decidable in linear time), linear memory, tables (indirect calls through a typed table: dispatch edge set = table elements with matching type), WAT text format (S-expressions), component model (WIT interface types, worlds: a typed IDL for module composition). MLIR: dialects (ops registered by users: the IR itself is EXTENSIBLE), REGIONS nested inside ops (block structure inside operations: `scf.for`, `linalg.generic`, `func.func` all have regions), attributes, types per dialect, passes/lowering; the nearest existing thing to "a universal IR with user-defined structure" (NB: LLVM and MLIR both go DOWN to machine code; frob goes UP, but MLIR's op+region+attribute+dialect design is the best prior art for an EXTENSIBLE structural core). JVM bytecode: class files (constant pool, methods, verification by stack maps), `invokedynamic` (call site bound at first execution by a bootstrap method: call edge resolved at RUNTIME by user code), `invokevirtual/interface/special/static`. eBPF: verified bytecode (the kernel verifier proves termination/memory safety: a decidable restricted language by design, bounded loops, helper function allow-list per program type = capability set).
- Q9: decidable: control-flow graph from labels, section/symbol inventory, import/export lists (WASM/BPF capability sets), type-valid stack (WASM); undecidable: indirect jump targets, self-modifying code, JIT behavior. Structural lessons: relocation/linking is a late binding phase; capability = import list (WASM, eBPF helpers); SSA/phi and label-depth are alternative binding disciplines.

F26 Schema, IDL and query languages (Protobuf, GraphQL, OpenAPI, JSON Schema, SPARQL, Cypher, XSLT/XPath)
- Units: message/enum/service/rpc (Protobuf: FIELD NUMBERS are the wire identity, names are cosmetic: identity by number; `reserved` ranges; package + import graph), GraphQL type/field/query/mutation/subscription/fragment/directive, OpenAPI paths + operations + components + `$ref` JSON pointers (by-reference graph, cyclic), JSON Schema `$ref/$defs/$dynamicRef/$anchor`, `allOf/oneOf/anyOf/not` (schema combinators = type algebra), SPARQL: graph patterns (triple patterns with variables over an RDF graph: unification-like), `OPTIONAL/UNION/FILTER/GRAPH`, property paths (regular expressions over predicates); Cypher: `MATCH (a)-[:R]->(b)` ASCII-art patterns (2D-ish textual syntax), `MERGE/CREATE`; XSLT: TEMPLATES with match patterns (pattern-directed rewriting of an XML tree), `apply-templates` (dispatch by pattern + priority + mode), XPath expressions, keys; XPath/XQuery as functional query languages.
- Binding/edges: `$ref`/import/qualified type names (resolve across files and URLs), service->rpc->message type edges, resolvers in GraphQL servers (code bound to schema fields by NAME: schema-first cross-language binding, directly relevant to frob's `binds` edge design), codegen outputs (generated stubs in other languages from the schema: schema is the source of truth, generated code is derived, per-language outputs bound to one schema element), XSLT template rule edges (match patterns select tree nodes at runtime), SPARQL variables shared between patterns (join by shared variable).
- Q4: schema/type systems with unions, optionality, defaults, versioning rules (backward/forward compatibility is a diff property: a linter can compare two schema versions: breaking-change detection = decidable structural diff, protobuf field-number reuse, GraphQL field removal). Q9: decidable: inventory, ref resolution, cycles, compatibility diffs, dead definitions (unreferenced types); undecidable: JSON Schema satisfiability in general (decidable for fragments), query emptiness (SPARQL/XSLT general: undecidable for XSLT; XPath containment decidable for fragments), runtime resolver behavior.

F27 PLC and industrial/graphical (IEC 61131-3: LD, FBD, ST, IL, SFC; Simulink; Node-RED)
- Units: POU (program organization unit: PROGRAM, FUNCTION, FUNCTION_BLOCK with instances: instance data is part of the caller's declaration), global variable lists, tasks (cyclic/event with priority and interval: configuration binds POUs to tasks and to I/O addresses `%IX0.0`: binding of names to hardware addresses is explicit and located in the declaration `AT %IX0.0`), Ladder Diagram (rungs of contacts and coils in a 2D diagram; left rail power flow), Function Block Diagram (blocks and wires, execution order by position or explicit numbering), Structured Text (Pascal-like), Instruction List (assembly-like, deprecated), Sequential Function Chart (steps, transitions, actions: a Petri-net-like state machine). PLCopen XML is the interchange format (standard XML serialization of all five languages including graphical layout). Simulink: block diagrams (`.slx` zip of XML, `.mdl` text) with hierarchical subsystems, signals (typed, sample-time attributed), Stateflow charts (hierarchical state machines), libraries/model references, mask parameters; Node-RED: JSON flows of nodes with wires (`[{id, type, wires: [[ids]]}]`, ids are random strings: identity is a generated ID, names cosmetic).
- Evaluation: SCAN CYCLE (read inputs -> run program top to bottom, left to right -> write outputs, repeat; implicit infinite loop and implicit I/O image: the "main" loop is in the runtime), rung ordering semantic, timers/counters as stateful function blocks (`TON`, `CTU`), edge detection (`R_TRIG`), SFC token flow. Simulink: discrete/continuous solvers with sample times and execution ORDER derived by sorting (algebraic loops are errors; solver-determined semantics: the same diagram means different things under different solver settings stored in the model config).
- Q9: decidable: POU graph, I/O address map conflicts (two writes to the same coil: multiple-coil rule), unused variables, naming, scan-time estimation partially; undecidable: timing behavior, plant interaction. Safety standards (IEC 61508, MISRA-like for ST) are structural rulesets. Lesson: 2D diagram semantics, hardware address binding, implicit scan loop, interchange XML as the canonical text for non-textual languages.

F28 Probabilistic and differentiable (Stan, Pyro/Turing, WebPPL, JAX, PyTorch, Triton, Halide, Futhark)
- Stan: program BLOCKS in fixed order (`functions`, `data`, `transformed data`, `parameters`, `transformed parameters`, `model`, `generated quantities`): the section a variable is declared in determines its ROLE (observed data vs latent parameter) and semantics; a program denotes a log-density, not a procedure. Pyro/Turing/WebPPL/Gen/Anglican: `sample` and `observe`/`condition` are EFFECTS handled by an inference engine (effect-handler architecture: the same model code run under different handlers: forward sampling, MCMC, VI); programs are ordinary host-language code with random primitives. Q9: model structure (declared vs used variables, constrained parameters) is syntactic; posterior properties are undecidable/numeric.
- JAX: pure functions required for `jit/grad/vmap/pmap` (transformations compose: function -> function), TRACING executes Python once with abstract values to build a jaxpr (an IR: staged computation), control flow must use `lax.cond/scan/while_loop` for traced values, pytrees, PRNG keys threaded explicitly; PyTorch eager (define-by-run autograd tape: graph exists only at runtime) vs `torch.compile`/TorchScript (capture); Triton: Python-embedded GPU kernels, block-level programming (`tl.program_id`, tile semantics); Halide: ALGORITHM (pure functional pixel pipeline) separate from SCHEDULE (`tile`, `vectorize`, `parallel`, `compute_at`): TWO PROGRAMS about ONE computation, scheduling never changes meaning; Futhark: array language (F09-ish) with SOACs (`map/reduce/scan`), UNIQUENESS TYPES for in-place updates (`*[]i32`), size types (shape-dependent types, checked), compiles to GPU. Structural lessons: staged/traced programs (host program builds an IR), transformation-as-function (grad, vmap), separation of algorithm and schedule, shape as a type-level quantity, sections with roles (Stan blocks).

F29 Constraint, solver and pattern-of-text languages (MiniZinc, SMT-LIB, CLP(FD), CHR, Picat, regex)
- MiniZinc: model with `var` decision variables, parameters, constraints, `solve satisfy/minimize`, predicates, data in `.dzn` (model/data split across files), compiled to FlatZinc (flattening phase: expansion of comprehensions and global constraints into a flat constraint list; solver-specific redefinitions): pure declarative: unit = constraint; order irrelevant. SMT-LIB: S-expression commands (`declare-fun`, `define-fun`, `assert`, `push/pop`, `check-sat`, `get-model`) forming a STATEFUL SCRIPT with assertion-stack scopes (a file is a command sequence mutating solver state, like notebooks/Lean). CLP(FD): constraints posted into a store inside Prolog (propagation = reactive dependency graph of variables and propagators; labeling = search). CHR (Constraint Handling Rules): multi-headed rules `h1, h2 <=> guard | body` (simplification), `==>` (propagation), `\` (simpagation): rule heads match SETS of constraints in a store (multiset rewriting; confluence/termination analyses exist: decidable for fragments). Picat: Prolog-ish with pattern matching and tabling.
- Regex (PCRE, RE2, POSIX, ECMAScript): a language island in strings: units = groups (numbered/named capture groups: positional AND named binding, referenced by backreference `\1` or `(?P=name)`), alternation, quantifiers, lookaround, backrefs make matching NP-hard and non-regular (backreferences beyond regular languages), possessive/atomic groups, flags `(?i)`; RE2 guarantees linear time by dropping backrefs. Lints: ReDoS (catastrophic backtracking) is decidable for the NFA structure (ambiguity analysis: exponential vs polynomial is decidable for pure regexes, undecidable-ish/harder with extensions). Dialect differences make the island's parser a per-host choice. Regexes are a prime example of a language island needing its own adapter and appearing in nearly every host.

F30 Pattern, rule and query languages used on code (CodeQL, Semgrep, Coccinelle, ast-grep, Stratego, K framework, tree-sitter queries)
- CodeQL (QL): object-oriented Datalog: classes are SETS defined by characteristic predicates (not types with constructors), predicates, `exists`, recursion, `from ... where ... select`, module system, queries over a relational DATABASE extracted from code (extractor builds the DB: a different representation per language, language-specific libraries). Semgrep: pattern-in-target-syntax with metavariables `$X`, ellipsis `...`, `pattern-either/pattern-inside/pattern-not`, taint mode (sources/sinks/sanitizers); Coccinelle: SmPL semantic patches (`@@ metavariable decl @@`, `- old`, `+ new`, `...` as a path-sensitive wildcard over control-flow); ast-grep: tree-sitter pattern with `$VAR` and `$$$ARGS`; Stratego/Spoofax: rewrite rules + programmable STRATEGIES (`topdown(try(r))`); K framework: language semantics as rewrite rules over configurations (a language DEFINED as rules; one definition yields interpreter, verifier, ...); tree-sitter queries `(call_expression function: (identifier) @f)`.
- Relevance: frob's own rule layer IS this family. Lessons: (1) meta-variables with sequence wildcards, (2) patterns are written in the TARGET syntax (cannot be language-neutral without an IR), which is the argument for the IR in code-model.md section 5; (3) taint/path-sensitive rules require a CFG/dataflow layer the tree does not provide; (4) rules over a relational fact base (CodeQL, Datalog) scale to cross-file reasoning, so a fact-table IR (entities + edges) is directly queryable.

F31 Visual and projectional extras (Unreal Blueprints, Grasshopper, Houdini/TouchDesigner, live-coding, Logo/turtle, structure editors)
- Blueprints: graph of nodes with EXEC (white) wires giving control flow AND data (colored) wires giving values: two edge families in one graph; events as entry points, `Branch`, `Sequence`, `ForEach`, delays/latent nodes; assets are binary `.uasset` (diffing difficulty; text export "copy as text" exists); functions/macros/collapsed graphs as sub-units; casts and interfaces; identity by node GUID. Grasshopper/Houdini/TouchDesigner: dataflow graphs with data TREES (paths of lists) and lazy re-evaluation on parameter change. Live coding (Sonic Pi, TidalCycles, Strudel, ChucK): code re-evaluated while running; TIME is a primary construct (`sleep`, patterns of cycles); programs are edited as they execute (the file is a score, not a spec). Logo/turtle: procedures + implicit drawing state (turtle position/heading) as ambient mutable state; `repeat`, `to ... end`, dynamic scope. Projectional/structure editors (JetBrains MPS, Hazel, Dark, Lamdu, Unison, Scratch): the persisted form is an AST/graph, text is a view; no parsing; identity by node ID; language composition without grammar ambiguity (MPS allows embedding languages freely).
- Edge families to carry: control edges vs data edges (Blueprints exec vs value pins; LabVIEW structure vs wires; Simulink signal vs trigger), edge LABELS (temporal, kind, port).

F32 Build, CI and infra extras (CMake, Bazel, Dockerfile, GitHub Actions, Gradle, Just/Ninja, Pkl/KCL/Nickel/Bicep/CloudFormation)
- CMake: its own scripting language (command-oriented like Bash: `command(arg ...)`, variables with string/list semantics, all values strings, `function/macro` where macro has TEXTUAL arg substitution), targets (`add_library`, `target_link_libraries` with PUBLIC/PRIVATE/INTERFACE propagation: transitive usage requirements, a dependency edge with visibility class), generator expressions `$<...>` (evaluated at generate time: a third phase), `find_package` (probe; environment-dependent), `include`, `add_subdirectory` (scope nesting), `ExternalProject`. Bazel: BUILD (Starlark) + labels `@repo//pkg:target`, `visibility` attribute (an access-control list on a target: a CAPABILITY-like structural edge restriction: who may depend on whom: `//visibility:public`, package groups; checkable statically), `select()` (configuration-dependent attribute values: conditional edges), macros vs rules, aspects, `bzlmod` MODULE.bazel, query language (`deps()`, `rdeps()`: a built-in graph query DSL: `bazel query` is the direct precedent for frob's why/affects/query). Dockerfile: ordered INSTRUCTIONS (`FROM ... AS stage`, `RUN`, `COPY --from=stage`, `ARG` vs `ENV`, `ENTRYPOINT`), each producing a LAYER (order = cache semantics), multi-stage graph, heredoc RUN islands in shell, `ARG` before `FROM`. GitHub Actions: YAML with `jobs.<id>.needs` DAG, `steps`, `uses: owner/repo@ref` (external action edge pinned by tag/SHA: supply-chain capability), `run:` shell islands, expression language `${{ }}` (contexts `github`, `secrets`, `needs`, `matrix`; a mini-language inside YAML strings), `permissions:` block (token capability set!), reusable workflows `workflow_call`, matrix expansion (one job -> N), `if:` conditions. Gradle: Groovy/Kotlin DSL where blocks are closures with DELEGATE objects (name resolution depends on the delegate: `dependencies { implementation(...) }`), plugin application, configuration vs execution phases, task graph, `settings.gradle` multi-project. Just/Ninja: Ninja is a low-level generated-file format with NO logic (pure DAG of build edges with rules and `depfile`); Just: command runner with recipes and parameters, `set shell`, backtick evaluation. Pkl/KCL/Nickel/Bicep/CloudFormation: config languages with types/contracts (Nickel merge operator `&` + contracts, Pkl classes and amends/extends modules, Bicep resources with implicit dependency via references like HCL, CloudFormation `!Ref`/`Fn::GetAtt` intrinsic functions inside YAML/JSON).
- Structural lessons: transitive visibility classes on dependency edges, conditional edges (select, matrix, if), phases (configure/generate/build), permission blocks as declared capability sets in the file itself (GitHub `permissions:`, Bazel `visibility`, WASM imports, Move `acquires`), and graph query languages as first-class.

F33 Other typed/functional extras (Elm, PureScript, ReScript, Idris 1, Dylan/CLOS, Rebol/Red, Io, OCaml 5 effects, Eff, Links, Racket Typed)
- Elm: no typeclasses, no user-level effects, MODEL-UPDATE-VIEW architecture (The Elm Architecture): commands/subscriptions as the effect boundary (the runtime performs effects; the program returns descriptions: effects as DATA, like Roc/Cedar); PureScript: row polymorphism for records and effects (`Eff`/`Effect` rows), typeclasses, FFI by sibling `.js` file with the same module name (a file-pair binding convention: `Foo.purs` + `Foo.js`, name-matched foreign imports). ReScript: OCaml semantics with JS output; `@module` externals. Dylan/CLOS: multimethods and generic functions (see F18). Rebol/Red: DIALECTS: block-structured data that is interpreted by different "dialect" evaluators (`parse` dialect, `draw`, `VID` GUI): the SAME BLOCK SYNTAX IS RE-INTERPRETED per call site (embedded DSL by data, no host-syntax change), words bound late to contexts (a binding is a property of a word value, `bind`, so a word can carry its context around). Io: prototype language with message passing everywhere (like Self/Smalltalk), no keywords. OCaml 5 effects: untyped algebraic effects (`perform`, `try_with`), Eff/Links/Helium: typed effect handlers (like Koka). Twelf/Beluga in F24.

## 4. Languages considered and found not to add a new structural feature

Each reduces to features already catalogued; the right-hand side names
the reduction so the claim is checkable.

- Brainfuck dialects (Ook!, Spoon, Cow, Brainfuck++), Underload, Thue,
  Wierd, Taxi, Velato (MIDI), Folders (directories as program): instruction
  soups, tape/stack/rewrite machines, or non-textual encodings; reduce to
  F19 Brainfuck/Piet/Whitespace (no names, flat, non-textual locator).
- Funge-98/Trefunge, `><>` (Fish), Hexagony, Marbelous: 2D (or 3D, hex)
  grids; the locator generalizes (x,y[,z] or hex axial coords), same
  2D-source feature as Befunge/Piet.
- Shakespeare, Chef, LOLCODE, Rockstar, ArnoldC, Piet-like image variants:
  natural-language surface over imperative/stack machines; only the SYNTAX
  differs (a different tokenizer/grammar); structurally F01.
- Malbolge variants (Malbolge Unshackled), self-modifying assemblers: same
  as Befunge `p`: dynamic CFG.
- Grain, ReScript, Elm, PureScript (beyond FFI sibling file), Gleam (beyond
  `use` and `@external`): F04/F20 plus FFI forms already recorded.
- Java vs C# vs Kotlin vs Scala vs Swift for plain class/interface
  structure: same as F02/F03 once partial classes, extensions and expect/
  actual are carried (multi-fragment unit).
- PHP, Lua, Ruby, Julia, R, Raku, Perl, Tcl: F21 (open units, dynamic
  names, runtime-created members, language-per-statement quirks).
- Pascal/Delphi, Modula, Oberon: unit with interface/implementation
  sections: F22 spec/impl split.
- Dylan, Io, Self (beyond F02), Rebol/Red (beyond dialect note), Newspeak:
  object/message or dialect forms already covered.
- Eff, Links, Helium, OCaml 5 effects: F20 effect handlers (Koka/Effekt).
- Typed Racket, Typed Clojure, Shen: F18 + F04 gradual/contract layers.
- Prolog dialect families (SWI, SICStus, GNU, Ciao, Logtalk), Souffle,
  Logica, Datomic datalog, Mangle: F07.
- Zig comptime vs D `mixin`/CTFE vs Nim templates/macros vs Crystal macros:
  all compile-time function evaluation producing code or types: F01/F03
  "expansion phase" feature (Nim macros operate on typed ASTs; D string
  mixins on text; both are "expansion site" nodes).
- Odin, V, Hare, Jai, C3, Nim, Crystal, D, Vale (beyond regions): imperative/
  systems families; no new unit/binding/edge kind.
- Haxe, Dart, Groovy, Objective-C (message sends = Smalltalk style on a C
  base; `@selector`/`NSSelectorFromString` computed dispatch), Fantom,
  Ceylon: F02/F03.
- Clojure dialects (ClojureScript, Babashka, Janet, Fennel, Hy), Scheme
  dialects (Guile, Chicken, Gambit, Chez), Shen, Arc, PicoLisp, Emacs
  Lisp (buffer-local and dynamic binding by default historically; same as
  CL special variables): F18.
- J/K/Q clones (Kona, ngn/k, Klong, ivy, Nial, A+, Dyalog): F09.
- Forth family (Gforth, Retro, colorForth, 8th, Uxntal, dc, RPL, Cat,
  Kitten, Min, Raven, Om): F08 (colorForth encodes parts of speech by
  COLOR, an extreme non-textual form of the syntax-by-word-class idea
  already in Forth parsing words).
- Verilog-AMS, SystemC, Bluespec, Clash, Amaranth, MyHDL, nMigen, SpinalHDL:
  F12 (embedded HDL = host language as elaboration layer).
- Metal, OpenCL C, SYCL, HIP, Slang, Cg, ISPC, OpenMP/OpenACC pragmas:
  F12 (pragmas as comment/annotation islands like Fortran `!$omp`).
- Cirq, PennyLane, Qrisp, Silq, QASM variants, Quil: F13.
- Dockerfile variants (Containerfile), Compose, Helm, Kustomize, Ansible,
  Puppet, Chef, Salt, Pulumi (general-purpose host language as IaC, F13
  builder-vs-built), CDK: F14/F32.
- RST, AsciiDoc, Org, Pandoc Markdown, MyST, Textile, DocBook, TEI, SVG,
  XML families with XSD/DTD: F15/F26.
- Zsh, Fish, dash, ksh, csh, Elvish, Oil/YSH, Xonsh: F16 (YSH is an
  attempt at a statically parseable shell, like Nushell).
- Mathcad, Maple, Sage, MATLAB/Octave, Wolfram (beyond F18), R: F21/F18/F09
  and notebooks F17 (MATLAB command/function syntax duality `hold on` vs
  `hold(on)`: parse depends on whether an identifier is a variable: a
  smaller instance of the J part-of-speech problem).
- Smalltalk dialects (Pharo, Squeak, Cuis, GemStone), Self/Newspeak: F02.
- ABAP, RPG, PL/SQL, T-SQL, PL/pgSQL, MUMPS, Natural, Easytrieve, ColdFusion
  CFML, 4GLs: F22/F07 (record-oriented, embedded SQL, repositories).
- Solidity siblings (Yul, Huff, Sway, Michelson, Plutus/Aiken, Clarity,
  Scilla): F23/F25/F04 (Michelson is typed stack; Clarity is deliberately
  decidable, no recursion: analyzable-by-design, like Cedar, Lustre).

Count reconciliation (computed by grep over section 1, not typed by hand):

- items checked in section 1: 202
- of which task-listed (F01-F20): 119 including the five Haskell
  extensions listed separately; added by me (F21-F33): 83.
- every checklist item appears by name in section 3 (families F01-F20 in
  full questionnaire form, F21-F33 in delta form where a language is
  grouped under a family heading). Items grouped in delta form carry
  fewer than nine answers each; where a language was not given its own
  nine answers it is because section 3 states it differs from a named
  family only in the listed respects.
- DENOMINATOR CAVEAT: the universe of "all programming languages" is not
  finite or enumerable; completeness here means every PARADIGM FAMILY
  that I could identify was analysed and every named language in the task
  was ticked. The falsifiable claim is: no language examined in section 4
  or section 3 required a structural feature outside the synthesis table
  rows of section 5.

## 5. Synthesis: structural feature x paradigm

Columns are families F01..F20 (two-digit ids): 01 imperative, 02 OO and
prototype, 03 multi-paradigm systems, 04 functional strict, 05 functional
lazy, 06 dependent/proof, 07 logic/relational (incl. SQL), 08 concatenative,
09 array, 10 actor, 11 dataflow/visual, 12 hardware/shader/GPU, 13 quantum,
14 config/data, 15 markup, 16 build/shell, 17 notebooks, 18 rewriting/
homoiconic, 19 esoteric, 20 weird-type (newer). Added families F21-F33
share the profile of the nearest column except where noted below the
tables.

Legend: Y = native, central; p = partial, optional or encodable with loss;
- = absent.

```
                              01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20
named unit                     Y  Y  Y  Y  Y  Y  Y  Y  p  Y  p  Y  Y  Y  Y  Y  p  Y  p  Y
anonymous unit                 p  Y  Y  Y  Y  Y  p  Y  Y  p  Y  p  Y  Y  -  p  Y  Y  Y  Y
file-less unit                 -  Y  -  -  -  p  Y  Y  p  p  Y  -  -  -  -  p  Y  Y  p  Y
lexical binding                Y  Y  Y  Y  Y  Y  p  p  p  Y  p  Y  Y  Y  p  p  -  Y  p  Y
non-lexical binding            p  Y  p  p  p  p  Y  Y  Y  p  Y  Y  p  Y  Y  Y  Y  Y  Y  Y
static call edge               Y  Y  Y  Y  Y  Y  Y  Y  p  Y  -  Y  Y  p  -  Y  p  Y  p  Y
dynamic dispatch edge          p  Y  Y  Y  Y  p  p  Y  -  Y  p  p  -  p  -  Y  -  Y  p  Y
unification edge               -  -  p  -  p  Y  Y  -  -  p  -  -  -  Y  -  -  -  Y  -  Y
cell/dataflow edge             -  p  p  p  p  -  p  -  -  p  Y  Y  Y  Y  -  Y  Y  -  p  Y
macro expansion phase          Y  p  Y  Y  Y  Y  Y  Y  p  Y  -  Y  p  p  Y  Y  p  Y  -  p
user-defined syntax            p  -  p  p  p  Y  Y  Y  -  -  -  -  -  -  Y  -  -  Y  -  p
dependent types                p  -  p  p  p  Y  -  -  p  -  -  -  -  -  -  -  -  -  -  Y
substructural types            -  -  Y  p  p  Y  p  -  -  Y  -  -  Y  -  -  -  -  -  p  Y
effect annotations             -  p  p  -  Y  Y  p  -  -  -  -  p  Y  -  -  -  -  -  -  Y
implicit instance search       -  p  Y  -  Y  Y  -  -  -  -  -  -  -  -  -  -  -  p  -  Y
2D/visual syntax               -  -  -  -  -  -  -  -  p  -  Y  -  p  -  p  -  p  -  Y  p
implicit global state          p  p  p  p  -  Y  Y  Y  Y  p  Y  -  p  -  p  Y  Y  Y  Y  p
non-textual source             -  -  -  -  -  -  -  -  -  -  Y  -  p  -  -  -  p  -  p  p
```

Rows discovered while analysing (not in the task's list of 18; each one
was forced by at least one family, named in the last column):

```
                              01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20  forced by
multi-fragment unit            p  Y  Y  p  Y  Y  Y  -  -  -  -  Y  -  Y  p  p  Y  Y  -  Y  C# partial, CLOS, VHDL, WEB
interface/impl split           Y  p  Y  Y  Y  Y  Y  -  -  p  -  Y  -  -  -  -  -  p  -  Y  .h/.c .mli .ads .sats .pyi
embedded-language island       p  Y  Y  Y  Y  Y  Y  p  p  p  Y  Y  p  Y  Y  Y  Y  p  -  p  JSX, SQL strings, Helm, TH QQ
per-file language parameter    p  p  Y  p  Y  Y  Y  Y  p  p  -  Y  p  p  Y  Y  Y  Y  -  Y  #lang, LANGUAGE, #version
hole / partial program         -  -  p  -  p  Y  -  -  -  -  -  -  -  -  -  -  -  -  -  Y  Agda ?, Lean sorry, Hazel
temporal edge label            -  -  -  -  -  -  p  -  -  p  Y  Y  p  p  -  p  Y  -  -  Y  Lustre pre, HDL clk, notebooks
contract / spec clause         p  p  p  p  p  Y  p  p  p  p  -  Y  p  Y  -  p  -  p  -  Y  Ada aspects, Eiffel, Dafny
content-addressed identity     -  -  -  -  -  -  -  -  -  -  p  -  -  p  -  -  -  -  -  Y  Unison, Dhall hash, Pd index
capability in language itself  -  p  p  -  p  p  p  -  -  Y  -  p  -  p  p  p  -  p  -  Y  Pony, Austral, Roc, Cedar
multi-target declaration       Y  Y  Y  Y  Y  Y  -  -  -  -  -  Y  -  p  -  -  -  -  -  Y  expect/actual, @external, cgo
unordered declarations         -  p  p  -  Y  Y  Y  -  -  -  Y  Y  -  Y  Y  p  Y  -  -  Y  Datalog, Nix, HCL, Pluto
environment-threaded commands  -  p  -  -  -  Y  Y  Y  Y  -  -  -  -  -  -  Y  Y  Y  p  p  Lean/Coq, Prolog, SMT-LIB, ipynb
```

Notes on families F21-F33 relative to the columns: F21 scripting is 02 with
more "dynamic edges" and "multi-fragment units" (open classes) and more
"embedded islands" (HTML in PHP); F22 legacy is 01 plus "implicit control
cycle" (RPG, PLC scan) and "external binding tables" (JCL DD names), both
encodable as non-lexical binding plus phase; F23 smart contracts is 03 with
`effect annotations` Y (state mutability) and `substructural` Y (Move); F24
verification is 06 with `contract clause` Y and a ghost/spec PHASE; F25
low-level IR is 01 with `linking` as a late binding phase and capability =
imports (WASM); F26 schema/query is 14/07 with `content-addressed
identity` p (protobuf field numbers) and `multi-target declaration` Y
(codegen); F27 PLC/Simulink is 11 with `implicit global state` (scan image)
Y; F28 probabilistic/tensor is 03/09 with a staged (trace) PHASE; F29 solvers
is 07; F30 pattern languages is 07 and needs `embedded island` (patterns
written in target syntax); F31 visual extras is 11 with two EDGE FAMILIES
(exec vs data); F32 build/CI is 16 with `capability in language itself` Y
(permissions, visibility) and conditional edges (select, matrix, if); F33
is 04/05/20.

## 6. What a universal model MUST represent natively

Criterion for "native": the feature cannot be recovered by an encoding
over a model that lacks it WITHOUT losing a question a structural linter
wants to answer (where is X defined, what depends on X, what may X do,
what does this region mean). Encodable features are in 6.2.

### 6.1 The 10 native features

1. ENTITY with identity decoupled from name, file and position. An entity
   is a record with a stable key plus zero or more NAMES (aliases;
   possibly none: anonymous, positional as in Pd object index or de
   Bruijn, content-addressed as in Unison hash, generated ID as in
   Node-RED/Blueprints), zero or more FRAGMENTS (see 9), and a kind
   drawn from an extensible set (module, function, type, predicate/
   relation with arity, rule, cell, word, actor/behaviour, kernel, table,
   node/port, hole). `path::Qual.Name` (code-model.md section 2) becomes
   one VIEW of an entity, not its identity. Forced by F07, F08, F11, F19,
   F20 (Unison), F22, F26 (protobuf numbers).
2. BINDING as an explicit relation with a BINDER KIND, not as nesting.
   Binder kinds seen: lexical, dynamic, positional (stack slot, de
   Bruijn, tape cell), wire/port, cell address, logic variable
   (unification), pattern variable, implicit argument, instance (search),
   by-name injection (pytest fixtures, Nix `callPackage`), hierarchical
   instance path (Verilog), late-bound symbol cell (Lisp), label-depth
   (WASM). Each binder carries a MULTIPLICITY/MODE attribute (0, 1,
   affine, omega, borrowed, unique, capability-ref). A scope GRAPH (in the
   sense of Neron et al. / Visser's scope graphs) is the right shape;
   a tree with symbol tables is not (Haskell instances are global, Nix
   `with`, Verilog hierarchy, Excel absolute-vs-relative references all
   break the tree).
3. TYPED EDGES with RESOLUTION STATUS and CANDIDATE SETS. Edge kinds:
   call, spawn, send, dispatch (virtual/trait/multimethod/protocol/
   behaviour), unify, reference (cell/name/path), instantiate (template,
   module instantiation, functor application), expand (macro use ->
   definition), derive/generate, import, include/transclude, link/ref,
   contain, extends/implements/overrides, binds (cross-language), inject
   (by name), match (selective receive, template rule), depends (Make,
   HCL, Bazel, Nix string context). Every edge carries status `Certain |
   ImportVerified | NameOnly` (already in code-model.md section 6) PLUS
   `Candidates(n)` for dynamic dispatch and `PhaseDependent` for edges
   whose target exists only after expansion/instantiation, plus a LABEL
   set (instantaneous vs delayed, exec vs data, plan vs apply,
   PUBLIC/PRIVATE/INTERFACE visibility class). Decidability results in
   section 2 are the reason: exact edges are impossible, so the status is
   part of the data model, not a refinement.
4. PHASES and EXPANSION SITES. A source file denotes a program only after
   zero or more expansion phases (preprocessor, macro, proc macro, reader
   macro, template, TH splice, comptime, derive, Helm render, LaTeX
   expansion, Terraform plan, Chisel elaboration, JAX tracing, Make read
   phase, CMake generate). The model needs: EXPANSION SITE node (head,
   arguments as an opaque token tree, declared effect on binding:
   hygienic or not, may-introduce-items or not), PHASE tag on units
   (runtime, compile-time, spec/ghost, build, test), and a record of
   whether the expansion output was observed (expanded) or not (opaque).
   Soundness rule: any unit set computed without expansion is labelled
   `pre-expansion`.
5. LANGUAGE REGIONS (islands) as a tree of (locator, language, dialect/
   version parameters). Covers SQL in strings, JSX, Markdown fences,
   QuasiQuotes, Helm/Jinja templates, shell in Make recipes and CI `run:`,
   cgo preambles, `!$omp` and ACSL and Liquid Haskell comment specs,
   DSC comments, IPython magics, PHP-in-HTML, regex literals, `asm`
   blocks, frob's own directive comments. Also the PER-FILE language
   parameter (`#lang`, LANGUAGE pragmas, Rust edition, `#version`,
   shebang, `shopt`, `set_prolog_flag`, flags in Agda/Coq/Lean): the
   language of a region is a (family, dialect, parameters) tuple, not a
   file extension.
6. ORDERING DISCIPLINE on every container: sequence (statements), ordered
   with fall-through (COBOL paragraphs, Make recipe lines), unordered set
   (Datalog, Cedar, HCL, Nix attrsets, Excel cells, Lustre equations),
   topological (derived from references: Pluto, Excel, Terraform),
   concurrent (processes, kernels, always blocks), nondeterministic/
   backtracking (Prolog, Verse), clocked (HDL, synchronous), user-driven
   history (notebooks, Lean commands, SQL migrations). Rules such as "no
   statement after return", "order-dependent initialization", or "this
   set must be sorted" mean different things per discipline and need the
   tag. The discipline also fixes which edges are labelled instantaneous
   vs delayed (feature 3).
7. ANNOTATION LAYER: structured, typed ATTACHMENTS on units and binders
   whose content is carried but not checked: type, effect row/set/
   specifier (IO, `throws`, `suspend`, Koka rows, Verse specifiers,
   `pure/view/payable`, Pony caps, `__device__`), multiplicity/grade,
   mode and determinism (Mercury), stack effect, contract clauses (pre,
   post, invariant, modifies, decreases, ghost), refinement predicates,
   lifetime/region/ownership marks, visibility/export lists,
   permissions/capabilities/visibility ACLs (Bazel, GitHub permissions,
   WASM imports, Move acquires), attributes/decorators/pragmas/
   annotations. A universal linter reads these and compares them to what
   detectors observe (this IS the capability matrix of code-model.md
   section 7, generalized beyond imports).
8. ENVIRONMENT-THREADED SEQUENCES: a "file" can be a command stream that
   evolves a mutable environment (Lean/Coq/Isabelle/ACL2 events, Prolog
   directives, SMT-LIB scripts, SQL migrations, notebooks, Forth source,
   shell scripts, Make includes, `using`/`open` order, F# file order,
   Go `init()`). The model needs "event-sequence" containers whose
   elements have declared reads/writes on named environments (type
   environment, operator table, dictionary, DB catalog, kernel state) so
   that order-dependent meaning (what a later token parses as, what a
   name means after that line) is representable.
9. MULTI-DECLARATION of one entity and INTERFACE/IMPLEMENTATION roles:
   N fragments with roles (spec, impl, stub, extension, merge, forward
   decl, expect, actual, generated, test), possibly across files,
   languages and phases: C# partial, Rust `impl` blocks, Swift extension,
   CLOS methods on a generic, WEB chunks, TS declaration merging, `.pyi`,
   `.mli`, `.ads/.adb`, Carbon api/impl, Austral `.aui/.aum`, Haskell
   `.hs-boot` and Backpack `.hsig`, VHDL entity/architecture, Erlang
   clauses, Prolog discontiguous clauses, Mathematica rule sets,
   `binds` across languages (code-model.md section 6 is the cross-
   language special case of the general fragment relation).
10. LOCATOR abstraction and PARTIAL/HOLE tolerance. A node's source
    position is a LOCATOR: byte range in a text file, grid coordinate
    (Befunge, Piet), image region, JSON pointer (ipynb, Scratch, Max),
    XML path (xlsx, PLCopen), cell address, object index (Pd), DB key or
    hash (Unison, Dark, Smalltalk image, ABAP repository), generated-from
    (macro output with provenance). Nodes may be HOLES or ERROR regions
    that retain a type context (Hazel, Agda goals, Lean `sorry`, tree-
    sitter ERROR): partial programs are normal input, matching code-
    model.md section 3's PARSE002 salvage rule, and must be first-class.

### 6.2 Features that can be ENCODED over the 10 (do not add as primitives)

- Classes, objects, prototypes, traits/typeclasses/protocols/interfaces:
  record-of-members entity + `extends/implements` edges + dispatch edges
  with candidates (feature 3); methods as functions with a receiver
  binder.
- Modules/namespaces/packages/crates/vocabularies/dictionaries/Racket
  submodules: containers (entities with members) + import edges;
  functors/parameterized modules/Backpack/generics/templates: containers
  with parameter binders and `instantiate` edges.
- Closures/lambdas/blocks/quotations/anonymous classes: anonymous entities
  with captured-binder edges.
- Loops, recursion, branches, `goto`, COME FROM, exceptions, defer,
  coroutines, async/await, CPS, continuations, effect handlers: control
  structure over the ordering discipline plus edges (handler edges for
  effects); the concrete control forms stay as `ts_kind`-labelled
  `Other` where a rule does not need them (matches the IrKind Other
  design).
- Rules/clauses/predicates (logic), equations (Lustre), constraints,
  policies (Cedar), templates (XSLT), rewrite rules: entities of kind
  `rule` with head/body children in an unordered container; the call
  graph is a rule-dependency graph (edges labelled positive/negative).
- Cells/spreadsheets/notebook cells/Observable: entities in an unordered
  or topological container with `reference` edges.
- Actors/processes/behaviours/kernels/tasks/POUs: functions plus an
  EXECUTION-MODEL attribute (ordered/async/spmd/concurrent/scan) on the
  entity, spawn/send edges.
- Tables/DDL objects/messages/schemas: type-like entities.
- Types in all their sophistication (System F, dependent, refinement,
  session, row): NOT represented as checked structure, only as attachments
  (feature 7) with an opaque subtree and a role tag; frob does not
  type-check, it carries and compares annotations.
- Hygiene algorithms (scope sets, renaming): not represented; only the
  hygiene CLASS of an expansion site (hygienic, unhygienic, unknown).
- Termination, confluence, totality, determinism: results of external
  analyses recorded as facts with provenance, never computed by the core.
- Numeric details (UB, widths, precision): out of scope, attributes only.

### 6.3 Why exactly these ten (minimality argument)

Dropping any single one forces a family out of coverage:
(1) without anonymous/positional/hash identity: Pd, lambda calculus, BF,
Unison; (2) without explicit binders with kinds: Prolog, Forth, Excel, Rego,
Nix `with`; (3) without edge status and candidates: every dynamic language
and every trait-based one; (4) without phases: Rust derive, TH, C
preprocessor, LaTeX, Terraform; (5) without regions: any real repo (SQL,
shell, YAML in CI); (6) without ordering: Datalog vs imperative lint rules
conflict; (7) without annotations: capability/effect/contract lints; (8)
without environment threading: Lean, Prolog `op/3`, notebooks; (9)
without multi-declaration: C#, Rust impls, Ada, `.pyi`, binds; (10) without
locators and holes: Piet, Excel, Unison, and the rule that partial parses
are salvaged and reported.

## 7. Consequences for code-model.md (concrete gaps found)

Against sections 2-5 and 7 of docs/design/code-model.md as read for this
note (observations; no design decision is taken here):

- Symref grammar (section 2): `<path>::<Qual>.<Name>` presumes a file and a
  unique textual name. Gaps: identity by NAME/ARITY (Prolog, Erlang,
  Elixir), by position (Pd index, de Bruijn), by hash (Unison, Dhall
  import), by address (`Sheet!A1`, JSON pointer), and by label (`//pkg:t`
  in Bazel). Suggest the grammar keeps its text form but an entity key
  is separate from the symref, and `[...]` brackets (already opaque) can
  hold `/arity`, `#n`, or `@hash`.
- Container model (section 2): `namespace | type | impl | module |
  function` omits `rule/predicate`, `relation/table`, `cell`, `actor`,
  `kernel`, `word`, `target` (Make/Bazel/CMake), `policy`, `chunk`
  (literate), `cell` (notebook), `block` (Terraform `resource.type.name`
  addresses), and `project/crate/package` as build units. These can all be
  `type`/`function` plus a `kind` string if the kind set is extensible.
- Symbol kinds: `function | method | type | class | const | module | field |
  variant | macro` has no `rule`, `predicate`, `trait/interface`,
  `instance` (nameless impl: addressed as Type[Trait], which covers Rust
  but also needs Haskell instances and Scala givens), `hole`, `contract`,
  `target`.
- IrKind (section 5): `Module | Function | Class | Block | Loop | Branch |
  Call | Assign | Return | Try | Lambda | Literal | Name | Attribute |
  Import | Comment | Other`. Missing for the families above: Rule/Clause
  (head, body), Unify (`=` goals), Pattern (match arms, pattern vars),
  Binder (with kind and multiplicity), ExpansionSite (macro use), Island
  (embedded language region), Hole, Contract (pre/post/invariant),
  Send/Spawn (actor), Wire/Edge (visual), Cell/Reference, Quote/Splice
  (staging), Handler/Perform (effects), Phase marker. The `Other` + `ts_kind`
  escape hatch is the correct mechanism for these until a rule needs them;
  rules that need them (e.g. "sort call in loop") are mostly about
  imperative/functional families and are safe with the current kinds.
- `Call{callee: Path, args}`: only for syntactic application. Juxtaposition
  with unknown part of speech (APL/J), pipeline `|>` (callee on right),
  curried application, implicit calls (Drop, operator overload, ADL,
  `Deref`, implicit conversions, `__getattr__`), message sends and
  unification are not calls; need `Call.kind` (direct, pipeline, operator,
  implicit, message, unify, spawn).
- Callee-vocabulary table (section 5): its premise (what `sort` is named
  per language) works for F01-F05, F21, but families without names for
  operations (array glyphs, stack words with arity-based identity, visual
  nodes) need vocabulary keyed by (family, token, arity, rank).
- Adapter capability matrix (section 3): the cells `Implemented/
  NotApplicable/Gap` are right; add that "NotApplicable" occurs by FAMILY
  for whole facets (e.g. `publicness` is N/A for Datalog, Cedar, HCL
  resources, notebooks, Pd), `test_shape` is N/A for config and visual
  languages, `imports` is replaced by `loads/includes/refs` kinds.
- Capability detectors (section 7): detection basis differs per family.
  The matrix needs a DETECTOR KIND column:
  - import/API path: F01-F05, F21 (modules named in imports).
  - command name: F16 (Bash `curl`, `rm`), CI `run:` steps, Makefile recipes.
  - resource/type name: Terraform `aws_iam_role`, K8s kinds, SQL
    statements (DDL vs DML vs SELECT), Max object names.
  - signature/type marker: Rust `unsafe`, `async`, Koka rows, Haskell IO,
    Verse specifiers, Solidity mutability, Q# operation, `__device__`.
  - host-interface list: WASM imports, eBPF helper list, Roc platform,
    Austral capability params, Pony `AmbientAuth`, Cedar actions.
  - declared permission block: GitHub `permissions:`, Bazel `visibility`,
    Android manifests, Move `acquires`.
  - value-flow: Nix IFD/fetch, notebooks (outputs), Helm values.
  An atom with no detector for a family is already modelled as `n/a`; add
  that EXECUTION-FREE detection is impossible for some atoms in some
  families (dynamic names) and must be recorded as `unknown-by-design`
  rather than `n/a`, so the matrix never reads as clean.
- Digests (section 2): whitespace-collapsed text is fine for whitespace-
  insensitive languages but WRONG for indentation-sensitive (Python,
  Haskell layout, YAML, Makefile tabs, Whitespace, Nim, F#, Scala 3):
  collapse must be per-language (adapter-supplied normalizer); for 2D/
  visual/JSON-container sources the digest needs the canonical serialization
  of the subgraph (and layout excluded or included per adapter), and for
  macro-generating languages the digest of source is not the digest of
  expanded meaning (record both when expansion is available).
- Directive DSL (section 4): "directive must start a comment line" assumes
  line comments; Forth `\ ` and `( )`, Whitespace (no comments: everything
  not 3 chars is a comment), Piet (none), JSON (no comments), ipynb
  (cell-level), Excel (cell comments/notes), Max (comment boxes), and
  YAML-with-templates (template regions) need per-language carriers for the
  directive: sidecar files keyed by locator, or metadata fields.
- Salvage rule (section 3, PARSE002): good for CFG languages; for Forth,
  LaTeX, Perl, Bash-with-aliases, Prolog `op/3` there is NO tree-sitter-
  clean parse to compare against, so the conformance test "zero symbols
  from a tree with ERROR nodes" should be a per-adapter flag (some adapters
  are heuristic by design and report `heuristic` confidence for ALL
  symbols).
- Call graph: add edge status `Candidates(n)` and `PhaseDependent` (section
  6 above, feature 3); bounded BFS for closure/affects must treat
  candidate-set edges as weighted by n.
- Priority guidance (not requirements): the families whose frob-relevant
  structure is closest to the current model are F01-F05, F21 (Rust, Python,
  TS, Go, Java, C family are all already in scope). The next cheapest
  wins in terms of new features per adapter are: F16 shell/Make (command-
  name capabilities, island recipe text), F14 config (HCL/YAML/TOML: unit =
  keypath/address, edge = reference), F15 markdown (already in) plus
  language islands from fences, F26 schemas (protobuf/OpenAPI/GraphQL:
  best fit for the `binds` edge), F07 SQL (catalog entities; read vs
  write capability detection by statement kind), F32 CI (permissions
  blocks, `uses:` edges). The features that are expensive per family are
  F12 HDL (hierarchy elaboration), F18 homoiconic (macros), F06 dependent
  (elaboration), F11 visual (container formats and locators).

## 8. Open questions for the owner (found, not resolved)

1. Should the model keep "unit = textual symbol" as a restriction for
   Milestone 1-2 and treat non-textual/anonymous families as adapters that
   synthesize stable keys, or should entity keys be generalized now?
2. Which phases does frob attempt to observe: pre-expansion only (cheap,
   unsound for Rust/C++/Scala), or optional expansion through the host
   compiler (rust-analyzer-style, `cargo expand`, `clang -E`)? The IR
   should record which view a fact comes from either way.
3. Are executed analyses allowed for total and deterministic languages
   (Starlark, Dhall, CUE, Jsonnet, Nix-pure, Datalog, Cedar, Lustre)? The
   "never execute" rule has a principled exception there; the decision
   changes what a config-language adapter can promise.
4. Is Rice's-theorem honesty visible in the output (every dynamic edge has
   a status) so that a clean report never means "nothing there" when it
   means "not analyzable"? Section 6.1 item 3 and section 7 detector
   `unknown-by-design` are proposals.

## 9. Sources and what could NOT be verified

No web fetch was performed for this note; everything was written from the
author's background knowledge (cutoff June 2026) and is therefore
labelled by confidence below. Primary references (plain URLs; from
memory, the URLs were not opened in this session):

- Wells, "Typability and type checking in System F are equivalent and
  undecidable", APAL 1999 (conference 1994):
  https://www.macs.hw.ac.uk/~jbw/papers/
- Pierce, "Bounded quantification is undecidable", POPL 1992 / Information
  and Computation 1994: https://www.cis.upenn.edu/~bcpierce/papers/
- Huet, "A unification algorithm for typed lambda-calculus", TCS 1975.
- Veldhuizen, "C++ templates are Turing complete", 2003:
  https://www.researchgate.net/publication/2476121
- Grigore, "Java generics are Turing complete", POPL 2017:
  https://arxiv.org/abs/1605.05274
- Lange and Yoshida, "On the undecidability of asynchronous session
  subtyping", FoSSaCS 2017; Bravetti et al., "Asynchronous session
  subtyping is undecidable" (2018): https://arxiv.org/abs/1611.05716
- Atkey, "Syntax and semantics of quantitative type theory", LICS 2018
  (Idris 2 QTT): https://bentnib.org/quantitative-type-theory.html
- Augustsson et al., "The Verse Calculus", ICFP 2023:
  https://simon.peytonjones.org/verse-calculus/
- Flatt, "Binding as sets of scopes", POPL 2016 (Racket):
  https://www-old.cs.utah.edu/plt/scope-sets/
- Neron, Tolmach, Visser, Wachsmuth, "A theory of name resolution", ESOP
  2015 (scope graphs): https://link.springer.com/chapter/10.1007/978-3-662-46669-8_9
- "Perl parsing is undecidable" (argument popularized by Jeffrey Kegler;
  attribution of the original proof unverified):
  https://www.perlmonks.org/?node_id=663393
- Lamping, "An algorithm for optimal lambda calculus reduction", POPL 1990;
  Lafont, "Interaction nets", POPL 1990 (HVM background).
- Tromp, "Binary lambda calculus and combinatory logic":
  https://tromp.github.io/cl/cl.html
- Barker, "Iota and Jot": https://en.wikipedia.org/wiki/Iota_and_Jot
- Wolfram Language reference (evaluation, attributes, DownValues):
  https://reference.wolfram.com/language/
- Unison documentation (content-addressed code): https://www.unison-lang.org/docs/
- Austral spec: https://austral-lang.org/spec/spec.html
- Pony reference capabilities: https://tutorial.ponylang.io/reference-capabilities/
- Cedar: https://www.cedarpolicy.com/ ; OPA/Rego: https://www.openpolicyagent.org/docs/latest/policy-language/
- Koka: https://koka-lang.github.io/koka/doc/book.html ; Effekt: https://effekt-lang.org/
- Granule: https://granule-project.github.io/ ; Hazel: https://hazel.org/
- MLIR language reference (dialects, regions): https://mlir.llvm.org/docs/LangRef/
- WebAssembly spec (validation, imports): https://webassembly.github.io/spec/core/
- Carbon design: https://github.com/carbon-language/carbon-lang/tree/trunk/docs/design

NOT verified (stated from memory; could have changed or be inexact):

1. Current project status of young languages: Dark (the original hosted
   Dark was sunset and the project restarted as a new Darklang in F#; the
   details of its present text syntax unverified), Kind vs Kind2, Bend/HVM
   versions (HVM2 on GPU), Mojo (ownership keyword renames: `borrowed/inout`
   to `read/mut`; open-source status), Carbon (still experimental), Vale
   (maintenance status), Roc (compiler rewrite; platform/ability details),
   Grain, Austral (stable?), Gleam (version-specific `use` and `@external`
   syntax), Flix (current effect system syntax), Verse (specifier lattice
   exact ordering is paraphrased).
2. tree-sitter availability per language: every "tree-sitter: yes/partial/
   no" is from memory of the grammar ecosystem; maintenance quality and
   completeness (especially for Nix, Haskell fixity, C++ templates, Lean 4,
   Agda, Coq, Forth, Prolog, Mercury, Typst, Factor) were not checked.
3. Elixir gradual set-theoretic types (1.17+ type inference of patterns and
   guards): described as "gradual set-theoretic types, status unverified".
4. Excel Turing-completeness via LAMBDA (widely stated since 2021): not
   re-verified; Max/Pd cord-execution-order details are historical and
   version-dependent.
5. Exact decidability classes: DEXPTIME-completeness of ML type inference,
   NP-completeness of conjunctive-query containment, and the claim that
   Datalog query equivalence is undecidable are standard but were quoted
   from memory; the F-omega inference statement is informal.
6. Starlark recursion/while: Bazel's dialect disallows both by default;
   other implementations (starlark-go, starlark-rust) gate them by flags;
   details unverified.
7. Specific syntax and semantics claims paraphrased from memory: Nix `//`
   update operator, Whitespace token set, INTERCAL politeness rule (the
   exact acceptable ratio of PLEASE statements was not stated here), Piet
   codel semantics summarized, Max/Pd execution-order rules.
8. Language-specific counts (`CommonMark ~650 examples` is approximate;
   BLC self-interpreter ~210 bits is from Tromp's page, not re-read).
9. No claim here was checked against a running toolchain, per the task's
   instruction not to run cargo or frob.
