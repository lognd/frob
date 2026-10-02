# Calculi and universal cores: foundations for a universal STRUCTURE model

Status: research note for docs/design/code-model.md sections 2-5.
Provenance caveat (read first): this session had no live web tools
(WebSearch/WebFetch were not available), so every citation below is from
memory of primary sources. URLs are canonical landing pages I am confident
exist, but NONE were fetched or re-verified in this pass. Items I am less
sure of are tagged [verify]. Treat the decidability facts as textbook
results (high confidence) and the tool/product claims (Semantic, bblfsh,
UniAST, Glean details) as medium confidence.

Contents
  0. Framing and the two theorems that matter
  1. The lambda cube and beyond
  2. Substructural, modal, ownership, sessions
  3. Effects and evaluation order
  4. Other universal cores
  5. Categorical and algebraic semantics
  6. The decidability boundary
  7. Prior art: universal / multi-language IRs
  8. Synthesis: (a) primitive set, (b) coverage theorem, (c) impossibility
  9. Implications for code-model.md
 10. Checklist, considered-and-subsumed list, open questions

Reading convention per item: Def / Binders / Decidable / Verdict, where
Verdict is "what the universal model must take from it".

---------------------------------------------------------------------------
## 0. Framing

### 0.1 What "universal language" can mean (three different claims)

U1 (semantic universality). Every computable language semantics embeds in
   one calculus. TRUE and cheap: Church-Turing thesis plus Kleene's s-m-n
   theorem. Given a language L with interpreter I_L (a partial computable
   function), T_L(p) = "I_L applied to the source text of p, as data" is a
   total computable translation into untyped lambda calculus (or SKI, or
   interaction combinators, or Turing machines) that preserves observable
   behaviour. Futamura projections are the same fact seen from compilers.
   It preserves NO structure: the image of a function body is a blob of
   data, so no structural question about L survives translation.

U2 (structure-preserving universality). Every language's STRUCTURE (scoping,
   containment, call sites, declaration/reference, visibility, effect
   sites) embeds in one core such that structural predicates are preserved
   and reflected. This is the claim the owner wants. It is true under
   explicit hypotheses (section 8b) and false without them (section 8c).

U3 (semantics-preserving AND structure-preserving). A core small enough to
   be useful and rich enough that each source construct maps to a local
   core construct with the same behaviour. FALSE in general: Felleisen's
   expressiveness theory ("On the expressive power of programming
   languages", 1991) shows constructs such as first-class continuations,
   mutable state, or exceptions are not macro-eliminable into a language
   lacking them. Any core must either contain the union of all such
   effects (a kitchen sink) or treat them via CPS/monadic translation,
   which is global (non-local) and so destroys structure.

Lesson: frob should claim U2 only, indexed by an explicit structural
logic, and carry "Opaque/Unknown" for everything that needs U3.

### 0.2 Landin's precedent

Landin, "The next 700 programming languages" (CACM 1966,
https://dl.acm.org/doi/10.1145/365230.365257) proposed ISWIM: a family of
languages as sugar over lambda calculus with a "where" and a set of
primitives. Same ambition for semantics (U3 for functional cores) but it
explicitly parametrised the family by primitives: a precedent for a core
with an extensible operator signature instead of a fixed term grammar.

### 0.3 The two theorems that matter most for the design

T-A (Rice, 1953): every non-trivial semantic property of programs in a
    Turing-complete language is undecidable. Hence no total structural
    tool can decide semantic questions; it needs a third answer.
T-B (Turing, 1936 / Church, 1936): halting and beta-equality of untyped
    terms are undecidable. Hence normalisation-based canonical forms are
    not available for the untyped sublanguage; a canonical form must be a
    SYNTACTIC one (alpha-normal tree), not a semantic one.

---------------------------------------------------------------------------
## 1. The lambda cube and beyond

Common vocabulary. Church-style terms carry type annotations on binders
(type checking decidable, inference is a separate question); Curry-style
terms do not. "Decidable" below always says which of: TC (type checking,
given the full annotated term), INF (inference/typability, unannotated),
NORM (does normalization terminate / is beta-equality decidable).

### 1.1 Untyped lambda calculus (Church 1936; Barendregt 1984)
Def: terms t ::= x | \x.t | t t; rule (\x.t) u -> t[u/x].
Binders: one binder form, \x, binding in its body. Alpha-equivalence is
  decidable in linear time on named terms (rename to de Bruijn).
Decidable: beta-convertibility UNDECIDABLE (Church 1936); normal-form
  existence undecidable; confluence holds (Church-Rosser). Y combinator
  gives general recursion. Turing complete.
Consistent as a logic: no (every type is inhabited via fixpoint, there
  are no types).
Verdict: the minimal binding-carrying syntax. The core must have exactly
  this much binding machinery (a binder with scope and alpha-equivalence)
  and need not have its reduction.

### 1.2 Simply typed lambda calculus, lambda-> (Church 1940)
Def: types A ::= o | A -> A; terms Church-annotated \x:A.t.
Binders: as 1.1, plus types on binders.
Decidable: TC decidable (linear); INF decidable with principal types
  (Hindley 1969, Milner 1978 via unification, Robinson 1965). NORM:
  strong normalization (Tait 1967 reducibility); normalization is
  decidable but with NON-ELEMENTARY cost (Statman 1979, "The typed
  lambda-calculus is not elementary recursive"). Not Turing complete
  (cannot express Y; all programs terminate).
Consistent: yes (propositional intuitionistic implication, Curry-Howard).
Add `fix` and you get PCF (Plotkin 1977, "LCF considered as a programming
  language"): Turing complete, logically inconsistent.
Verdict: types are an ANNOTATION layer on the binding skeleton; the core
  should treat a type as an optional child sort, not part of binding.

### 1.3 Hindley-Milner / ML let-polymorphism
Def: lambda-> plus let-bound type schemes, rank-1 prenex polymorphism.
Decidable: INF decidable, principal types (Damas-Milner 1982), but
  DEXPTIME-complete (Kfoury-Tiuryn-Urzyczyn 1990; Mairson 1990).
Verdict: shows inference can be decidable yet exponential; a linter must
  not assume type inference is cheap or even available per language.

### 1.4 System F / lambda2 (Girard 1972; Reynolds 1974)
Def: types A ::= a | A -> A | forall a. A; terms add type abstraction
  /\a.t and type application t [A]. Second-order propositional logic by
  Curry-Howard. The polymorphic (impredicative) lambda calculus.
Binders: TWO binder namespaces, term variables and type variables, with
  independent substitution (type substitution into terms).
Decidable: TC decidable (Church-style). INF (typability) UNDECIDABLE
  (Wells 1999, "Typability and type checking in System F are equivalent
  and undecidable", APAL 98;
  https://www.macs.hw.ac.uk/~jbw/papers/). Type inhabitation undecidable
  (Loeb 1976). Strongly normalizing (Girard 1972), but the SN proof is not
  formalizable in second-order Peano arithmetic (that is the strength of
  the system: it proves the totality of every function provably total in
  PA2). Not Turing complete; every definable function is total. Rank-2
  fragment has decidable INF (Kfoury-Wells 1994); rank >= 3 undecidable.
Consistent: yes (relative to PA2 strength).
Which "System F" people mean: (i) pure System F above; (ii) "System F"
  as shorthand for the F-family: F<: (bounded quantification, Cardelli-
  Wegner 1985; subtyping UNDECIDABLE, Pierce 1994 "Bounded quantification
  is undecidable"), F-omega (1.5), System Fc (1.6); (iii) System F in
  compiler texts = "typed core with explicit type abstraction/application
  that survives optimization" (GHC Core, 1.6). The owner's "system-V" is
  not a standard name (Roman numeral V is not a calculus; "System U" and
  "System U-minus" are Girard's inconsistent PTS); read it as System F
  family. [verify with owner]
Verdict: explicit type abstraction/application is an ordinary pair of
  operators with a binder; nothing new for structure. Note the TWO
  binding namespaces: the core's names must be sorted (term vs type vs
  module), which ABT sorts give for free.

### 1.5 System F-omega (Girard 1972)
Def: F plus type-level lambda: kinds K ::= * | K => K; type operators
  \a:K.A and applications; types are simply-typed lambda terms modulo
  beta-eta at the type level.
Binders: term level, type level (a whole lambda calculus one level up).
Decidable: TC decidable; strongly normalizing; type-level beta decidable
  (type level is STLC). Not Turing complete. Subtyping variant F-omega-<:
  undecidable (inherits Pierce 1994).
Verdict: structure is stratified syntax (terms/types/kinds); a sort
  system on the core (term, type, kind, pattern, ...) is exactly right.

### 1.6 System Fc / FC / GHC Core (explicitly requested)
Def: Sulzmann, Chakravarty, Peyton Jones, Donnelly, "System F with type
  equality coercions", TLDI 2007
  (https://www.microsoft.com/en-us/research/publication/system-f-with-type-equality-coercions/).
  Adds coercions g : t1 ~ t2, casts e |> g, to model GADTs and type
  families. Extended to FC-pro with kind equalities (Weirich, Hsu,
  Eisenberg, "System FC with explicit kind equality", ICFP 2013) and to
  Dependent Haskell (Eisenberg, PhD thesis, UPenn 2016,
  https://richarde.dev/). GHC Core datatype Expr: Var, Lit, App, Lam, Let
  (rec or nonrec), Case (with scrutinee binder), Cast, Tick, Type,
  Coercion. Eight-ish constructors for all of Haskell after desugaring.
Binders: lambda, let, case-alternative pattern binders, type-level
  forall, coercion binders (a third namespace).
Decidable: Core type checking decidable (it is a lint pass,
  -dcore-lint). Core is NOT normalizing (letrec, unrestricted recursive
  newtypes, Type:Type in FC-pro; coercion axioms may be inconsistent, so
  consistency of coercions is a user-facing proof obligation: "coercion
  consistency", Weirich et al.). Turing complete.
Verdict: the best existence proof that a ~10-constructor typed core
  suffices to receive a whole real language (Haskell) with binding
  respected; but it is a COMPILER core: sugar is erased, source structure
  (module layout, instance declarations as written) is lost. For STRUCTURE
  we need the core BEFORE desugaring, with spans.

### 1.7 lambda-P / LF (Harper-Honsell-Plotkin 1993)
Def: STLC with dependent function types Pi x:A.B (types depend on terms).
  The Edinburgh Logical Framework; implementation Twelf, Beluga.
Binders: Pi and lambda; HOAS-friendly (object-language binders encoded as
  meta-lambda).
Decidable: TC decidable; strongly normalizing; consistent. Not Turing
  complete (as a computation language) but it is a universal language for
  specifying syntax and judgements.
Verdict: LF is the proof-of-concept that ONE tiny dependent calculus can
  represent the syntax-with-binding and judgements of arbitrary formal
  languages (adequacy theorems). Direct precedent for "universal
  signature language". Harper-Honsell-Plotkin, "A framework for defining
  logics", JACM 40(1), 1993.

### 1.8 Calculus of Constructions, lambda-C (Coquand-Huet 1988)
Def: the top of the lambda cube: terms and types in one syntax; sorts
  Prop and Type; rules (s1,s2) in {(*,*),(*,[]),([],*),([],[])}.
Decidable: TC decidable; SN (Coquand 1985; Geuvers 1995 for the cube);
  consistent (cannot prove False). Not Turing complete. No inductive
  types (only impredicative Church encodings, with no usable induction
  principle without extension; Geuvers 2001).
Verdict: confirms "terms = types = one syntactic category" is workable;
  the core should not hard-wire a term/type split.

### 1.9 The lambda cube (Barendregt 1991, "Introduction to generalized type
systems", JFP 1(2))
Def: eight systems from three independent axes: terms depending on types
  (polymorphism, F), types depending on types (type operators, omega),
  types depending on terms (dependent types, P). Corners: lambda->, F,
  lambda-omega (weak), F-omega, lambda-P, lambda-P2, lambda-P-omega, CoC.
Decidable/SN/consistency: all eight are strongly normalizing, have
  decidable type checking and are consistent; none is Turing complete.
Verdict: a uniform presentation of what a binder can bind (term, type,
  both) and what it can be indexed by; already captured by 1.10.

### 1.10 Pure type systems (Barendregt; Terlouw 1989; Berardi 1988)
Def: a PTS is a triple (S, A, R): sorts S, axioms A subset of S x S
  (s1 : s2), rules R subset of S x S x S for Pi formation. One term
  syntax: t ::= x | s | t t | \x:t.t | Pi x:t.t. All cube systems are
  PTSs on S = {*, []}.
Binders: exactly two binder forms (lambda, Pi), both with annotated
  binder type; ONE namespace.
Decidable: type checking is decidable for FUNCTIONAL, NORMALIZING PTSs
  (algorithmic via beta-normalization; van Benthem Jutting-McKinna-Pollack
  1993 "Checking algorithms for pure type systems"). Normalization is
  a property of the particular (S,A,R): Type:Type (Martin-Loef 1971) and
  System U, U-minus (Girard 1972 thesis, "Girard's paradox"; Hurkens 1995
  simplified) are inconsistent and non-normalizing in the logic sense;
  Coquand 1986 "An analysis of Girard's paradox".
Verdict: PTS is the right way to say "one syntax, a parametrized family of
  sort disciplines". The core's SORT table plays the role of (S, A, R):
  data, not code. A language adapter declares its own sorts.

### 1.11 Calculus of Inductive Constructions, CIC (Coquand-Paulin 1990;
Paulin-Mohring 1993; Coq/Rocq)
Def: CoC plus a cumulative universe hierarchy Type_i, Prop/SProp, and
  user-declared inductive and coinductive types with eliminators, plus
  (co)fixpoints under syntactic guard conditions (structural recursion
  decreasing on an inductive argument; productivity for cofix) and a
  strict positivity check.
Binders: lambda, Pi, let, match (pattern binders), fix (binds the
  function name and its decreasing argument), cofix.
Decidable: TC decidable if the guard condition is decidable (it is: a
  syntactic check). SN holds with the guard (Barras 2010). Consistency
  relative to ZFC plus inaccessibles (Werner 1997; Lee-Werner 2011).
  NOT Turing complete: all functions total; you cannot write a
  self-interpreter (Godel II / Turner). Partiality recovered via
  coinductive delay monad (Capretta 2005), fuel, or Acc (well-founded
  recursion).
Verdict: shows the "totality bargain": general recursion is exactly what
  you must give up to have decidable normalization; every real language
  gives it back, so for real languages the core cannot normalize.

### 1.12 Martin-Loef type theory with universes (Martin-Loef 1972, 1984
"Intuitionistic type theory", Bibliopolis)
Def: dependent types: Pi, Sigma, Id (identity), N, W (well-founded
  trees), plus a universe tower U_0 : U_1 : ... (Russell or Tarski
  style).
Variants: INTENSIONAL (MLTT; judgemental and propositional equality
  differ) vs EXTENSIONAL (reflection rule): ETT has UNDECIDABLE type
  checking (Hofmann 1995; Castellan-Clairambault-Dybjer 2020 "Undecidability
  of equality in the free locally cartesian closed category").
Decidable: ITT TC decidable, SN holds (Martin-Loef 1975 normalization),
  consistent (proof-theoretic strength via W, universes; Rathjen).
Verdict: even a "logic" can have undecidable TC depending on the equality
  rule: a decidability claim is always about a SPECIFIC rule set.

### 1.13 Homotopy type theory and cubical type theory
Def: HoTT = MLTT + univalence + higher inductive types (Univalent
  Foundations Program, "Homotopy Type Theory", 2013,
  https://homotopytypetheory.org/book/). Univalence as an axiom breaks
  canonicity (closed terms of N need not reduce to numerals). Cubical TT
  (Cohen-Coquand-Huber-Moertberg, "Cubical type theory: a constructive
  interpretation of the univalence axiom", 2016, arXiv:1611.02108)
  restores canonicity by interval variables i, de Morgan algebra,
  Kan composition and Glue types. Implementations: cubicaltt, Agda
  --cubical, Cubical Agda, redtt, cooltt, Arend (variant).
Binders: lambda, Pi, plus path-lambda <i>t binding an INTERVAL name
  (a third binder sort), plus partial-element systems with face
  formulas.
Decidable: cubical TT has canonicity, normalization (Sterling-Angiuli
  2021 "Normalization for cubical type theory", LICS) and decidable type
  checking. Not Turing complete.
Verdict: binders can bind objects of NON-term sorts (intervals, faces);
  sorted binders must be first class. Nothing in HoTT adds structure
  beyond that.

### 1.14 Observational type theory (Altenkirch-McBride-Swierstra 2007
"Observational equality, now!", PLPV; Pujet-Tabareau 2022 "Observational
equality: now for good", POPL; Pujet-Tabareau 2023 "Impredicative
observational equality", POPL)
Def: equality defined by recursion on types (observationally), with
  funext, propositional extensionality and quotients definitional or
  admissible while keeping canonicity and decidable TC. Implemented in
  Rocq's SProp-based prototype and in a recent Agda-like experiments.
Verdict: no new structure; evidence that equality is a PARAMETER of the
  system, so equality is not something to bake into a structural core.

### 1.15 Dedukti / lambda-Pi calculus modulo rewriting (Cousineau-Dowek
2007; Assaf et al.; https://deducteam.github.io/)
Def: LF plus user-declared rewrite rules, used as a universal proof
  checker into which Coq, HOL, Matita, Agda, PVS proofs are translated.
Decidable: TC decidable iff the rewrite system is confluent and
  terminating (undecidable to check in general, so the system's author
  supplies it).
Verdict: strongest evidence that a universal TARGET for many distinct
  type theories is achievable and has real tooling (Logipedia). The
  translations are per-source-logic programs (like frob adapters), and
  correctness is per-translation, not global. Exactly our shape.

### 1.16 Other type-theoretic ingredients worth one line each
- Lean 4 kernel: bvar, fvar, mvar, sort, const, app, lam, forallE, letE,
  lit, mdata, proj; quotient and inductive types built in; proof
  irrelevance; universe levels; no general recursion (structural plus
  Acc). De Moura-Ullrich CADE 2021. Known: definitional equality in Lean
  is not guaranteed to terminate or be transitive in all cases (Carneiro,
  "The type theory of Lean", MSc 2019; verify). Verdict: `mdata` is an
  annotation node, `proj` shows structure projection as primitive.
- Coq Gallina: term grammar of CIC with Notation/Sections/Modules layer
  outside the kernel. Verdict: separate kernel terms from surface layer
  (what frob calls adapter vs core).
- Agda: dependent pattern matching, copatterns; surface is richly
  structured, core is Agda.Syntax.Internal. Same lesson.
- Refinement types (Liquid Haskell, Rondon-Kawaguchi-Jhala PLDI 2008):
  decidable via SMT on quantifier-free fragments; types carry predicates
  as annotations. Verdict: annotation layer again.
- Gradual typing (Siek-Taha 2006): dynamic type `?` as a type that is
  consistent with everything. Verdict: `?` is the TYPE-level analogue of
  Unknown in section 6; an adapter for Python/JS gives `?` to unannotated
  binders.
- Subtyping/object calculi (Abadi-Cardelli 1996, "A theory of objects";
  Featherweight Java, Igarashi-Pierce-Wadler 2001; DOT, Amin et al. 2016
  "The essence of dependent object types"): classes/objects are encodable
  but nominal subtyping, overriding and virtual dispatch make exact call
  targets type-dependent. DOT is the calculus underlying Scala 3; its
  type-checking/subtyping is undecidable in general. Verdict: method
  resolution is a RELATION computed from a hierarchy, not a binder.

Section 1 summary table

| Calculus        | TC     | INF      | SN   | Consistent | Turing |
|-----------------|--------|----------|------|------------|--------|
| untyped lambda  | n/a    | n/a      | no   | no         | yes    |
| STLC            | dec    | dec      | yes  | yes        | no     |
| HM              | dec    | dec,EXP  | yes  | n/a        | no     |
| System F        | dec    | UNDEC    | yes  | yes        | no     |
| F-omega         | dec    | undec    | yes  | yes        | no     |
| F<:             | n/a    | undec    | yes  | yes        | no (subtyping undec) |
| lambda-P        | dec    | partial  | yes  | yes        | no     |
| CoC / cube      | dec    | undec    | yes  | yes        | no     |
| PTS (normalizing)| dec   | varies   | yes  | varies     | no     |
| PTS Type:Type/U | dec*   | -        | NO   | NO         | yes    |
| CIC             | dec    | partial  | yes  | yes (rel.) | no     |
| ITT/MLTT        | dec    | partial  | yes  | yes        | no     |
| ETT             | UNDEC  | -        | yes  | yes        | no     |
| Cubical TT      | dec    | partial  | yes  | yes        | no     |
| PCF / +fix      | dec    | dec      | NO   | NO         | yes    |
| System Fc/Core  | dec    | n/a      | NO   | NO         | yes    |
(*decidable only if the term normalizes; Type:Type TC is semi-decidable
in general because conversion may diverge.)

Section 1 verdict: the whole cube/PTS family agrees on ONE syntactic
skeleton: terms built from operators over binders with two or three
sorts of variable. They disagree only on the RULES (typing), which are
semantic and which the structural core delegates to the adapter. Take:
(1) a binder with alpha-equivalence; (2) sorted names; (3) typing as an
annotation layer; (4) rules/sorts as DATA (PTS triple); (5) no
normalization in the core.

---------------------------------------------------------------------------
## 2. Substructural, modal, ownership, sessions

### 2.1 Linear logic and linear lambda calculus
Def: Girard, "Linear logic", TCS 50, 1987. Resources: exchange only by
  default; no weakening (use at least once) or contraction (use at most
  once) unless marked by the exponential !A. Connectives: tensor, par,
  with, plus, lollipop, !, ?. Linear lambda calculus: Abramsky 1993
  "Computational interpretations of linear logic"; Wadler 1993 "A taste
  of linear logic" (MFCS); Barber 1996 DILL (dual intuitionistic linear
  logic, Edinburgh tech report).
Binders: lambda with a USAGE discipline: each variable used exactly once
  (checked by splitting the context across subterms). Binding is
  standard; the resource rules are a context-splitting judgement, not new
  syntax.
Decidable: multiplicative linear logic (MLL) decidable (NP-complete);
  MELL decidability is OPEN (Ackermann-hardness of fragments shown by
  Lazic-Schmitz 2015 [verify]); full propositional LL is UNDECIDABLE, Lincoln-Mitchell-Scedrov-Shankar 1992 "Decision problems
  for propositional linear logic"). Linear lambda calculus type
  checking decidable (needs context splitting; made algorithmic via
  input/output contexts, Cervesato-Pfenning). SN yes. Linear Haskell
  (Bernardy-Boespflug-Newton-Peyton Jones-Spiwack, POPL 2018,
  https://arxiv.org/abs/1710.09756): linearity on function arrows.
Verdict: USAGE counts are annotations on binders (1 / 0 / omega). The
  core binder should have an optional multiplicity slot.

### 2.2 Affine, relevant, ordered (the substructural square)
- Affine: weakening yes, contraction no (use at most once). Rust moves,
  Cyclone, Alms (Tov-Pucella, POPL 2011).
- Relevant: contraction yes, weakening no (use at least once).
- Ordered / Lambek: neither plus no exchange (stack/queue discipline).
  Lambek 1958 "The mathematics of sentence structure"; Polakow-Pfenning
  1999 "Natural deduction for intuitionistic non-commutative linear
  logic".
- Bunched implications (O'Hearn-Pym 1999): two context combinators
  (spatial and additive); basis of separation logic (Reynolds 2002,
  O'Hearn-Reynolds-Yang 2001).
Decidable: each substructural fragment's type CHECKING for lambda
  calculi is decidable; the logics' provability varies as above.
Verdict: all are the same binder with different structural rules on the
  CONTEXT; none changes the syntax. Core stays unchanged, adds
  a usage-mode attribute.

### 2.3 Quantitative type theory, QTT (Atkey, "Syntax and semantics of
quantitative type theory", LICS 2018,
https://bentnib.org/quantitative-type-theory.html; McBride, "I got plenty
o' nuttin'", 2016)
Def: dependent type theory in which every binder carries a multiplicity
  drawn from a PARTIAL SEMIRING (R, 0, 1, +, *): x :^r A. Typical R =
  {0, 1, omega}: erased, linear, unrestricted. Judgement: contexts are
  scaled/added like vectors; 0 means "usable only in types/proofs" i.e.
  compile-time-only. Idris 2 (Brady, ECOOP 2021, "Idris 2: quantitative
  type theory in practice", arXiv:2104.00480) implements it.
Binders: lambda/Pi annotated with a multiplicity r. A term's type
  mentions variables at multiplicity 0.
Decidable: TC decidable (usage checking is a linear-size pass over the
  PTS judgement); SN/consistency as underlying MLTT.
Verdict: the clean unification of linear/affine/relevant/erased under
  one binder annotation; adopt "binder carries a grade" as the generic
  hook. Rust ownership, C++ constexpr (grade 0), Idris `0` all fit.

### 2.4 Graded modal types and coeffects
Def: Granule (Orchard-Liepelt-Eades, "Quantitative program reasoning with
  graded modal types", ICFP 2019, https://granule-project.github.io/):
  graded necessity modality []_r A with r in a semiring-like structure
  (nat intervals, security levels, privacy, sets); contexts annotated
  with grades; Gaboardi-Katsumata-Orchard-Breuvart-Uustalu, "Combining
  effects and coeffects via grading", ICFP 2016; Petricek-Orchard-
  Mycroft, "Coeffects: a calculus of context-dependent computation",
  ICFP 2014; Abel-Bernardy, "A unified view of modalities in type
  systems", ICFP 2020. Grades in types: !_r A. Effects (outputs) and
  coeffects (context demands) are dual: graded monads vs graded
  comonads.
Binders: lambda with graded variable; box/unbox introduce grades.
Decidable: type checking decidable provided the grade structure has
  decidable constraints (Granule discharges via an SMT solver for
  arithmetic grades; Z3).
Verdict: a SECOND dimension to attach to nodes: effect grade (output)
  and usage grade (input). In a structural linter this is exactly the
  "capability" dimension (code-model section 7): sites carry a grade.

### 2.5 Uniqueness types (Clean: Barendsen-Smetsers, "Uniqueness typing for
functional languages with graph rewriting semantics", MSCS 1996;
Wadler 1990 "Linear types can change the world"; Marshall-Vollmer-Orchard
"Linearity and uniqueness: an entente cordiale", ESOP 2022)
Def: a value of unique type has exactly ONE reference NOW; the system
  may destructively update. Linearity restricts the CONSUMER's future
  use; uniqueness is a guarantee about the PAST (no aliasing). Dual
  modalities; with subtyping unique <: shared in one direction, linear
  <: unrestricted in the other; both fit a grade lattice.
Decidable: type inference with uniqueness attributes decidable via
  constraint solving (Clean compiler).
Verdict: aliasing facts are a type annotation lattice; again an
  annotation not a syntax change.

### 2.6 Ownership and borrowing: Rust (relationship to all above)
Rust's ownership is AFFINE types (values moved; drop = weakening is
implicit), plus BORROWS (references with lifetimes) that make aliased
read access safe: shared references give contraction for read-only use,
mutable references are UNIQUE (uniqueness types). Lifetimes are regions
(Tofte-Talpin 1997; Cyclone). So Rust = affine + uniqueness + region
types + traits.
Formal models:
- Oxide (Weiss-Patterson-Matsakis-Ahmed, "Oxide: the essence of Rust",
  arXiv:1903.00982): syntactic type-system model of ownership and
  borrowing with provenances; type-checks borrows as aliasing constraints
  (loans) without lifetimes variables in the surface.
- RustBelt (Jung-Jourdan-Krebbers-Dreyer, "RustBelt: securing the
  foundations of the Rust programming language", POPL 2018,
  https://plv.mpi-sws.org/rustbelt/): lambda-Rust, a core with
  explicit lifetimes, memory, borrow, and an Iris-based semantic model
  of types as ownership predicates; proves unsafe-code libraries
  (Arc, Mutex, RefCell, ...) safe under a semantic criterion.
- Stacked Borrows (Jung et al., POPL 2020) and Tree Borrows (Villani-
  Jung-Ahmed et al., PLDI 2025 [verify]): operational aliasing models for
  unsafe Rust; Miri implements them.
- Polonius (Matsakis; Datalog formulation of NLL borrow check,
  https://github.com/rust-lang/polonius): borrow checking as a Datalog
  least fixpoint over a control-flow graph of facts. DIRECT precedent:
  a hard analysis stated as Datalog facts extracted from an IR.
- Featherweight Rust (Pearce, TOPLAS 2021) and Aeneas (Ho-Protzenko,
  ICFP 2022, "Aeneas: Rust verification by functional translation"):
  translating Rust (post-MIR) into a PURE lambda-calculus-like language
  by eliminating borrows with "backward functions". Shows ownership is
  a STRUCTURAL discipline that can be checked statically and then erased.
Verdict: ownership information (move/borrow/lifetime sites) is
  structural facts extractable per function; it need not be in the core
  syntax, only as annotations plus a few relations (moved-from, borrows).

### 2.7 Session types and the pi-calculus
Def: Milner-Parrow-Walker, "A calculus of mobile processes I, II",
  Information and Computation 100, 1992: processes P ::= 0 | x(y).P |
  x<y>.P | P|Q | (nu x)P | !P; names communicate names (mobility).
  Binders: input x(y) binds y; restriction (nu x) binds x. Structural
  congruence is the equational theory (scope extrusion).
  Session types: Honda 1993; Honda-Vasconcelos-Kubo, "Language primitives
  and type discipline for structured communication-based programming",
  ESOP 1998; Honda-Yoshida-Carbone, multiparty session types, POPL 2008.
  Types describe protocols: !A.S, ?A.S, S+S, S&S, end, mu.
  Curry-Howard: Caires-Pfenning, "Session types as intuitionistic linear
  propositions", CONCUR 2010; Wadler, "Propositions as sessions",
  ICFP 2012 / JFP 24(2-3) 2014
  (https://homepages.inf.ed.ac.uk/wadler/papers/propositions-as-sessions/):
  classical linear logic propositions = session types, cut = parallel
  composition with a private channel, proofs = deadlock-free processes
  (CP calculus). 
Decidable: pi-calculus is Turing complete; barbed/bisimilarity and
  reachability UNDECIDABLE for the full calculus; decidable for finite-
  control and replication-free fragments (Dam 1996; Busi-Gabbrielli-
  Zavattaro 2009 survey of decidability of pi fragments). Session
  typing is decidable and entails deadlock freedom by construction in
  the CP fragment (but only for tree-shaped topologies, a real
  restriction).
Verdict: channels are first-class names that can be sent; so name
  RESOLUTION cannot be purely static (mobility). The core must treat
  "dynamic name" as a possible resolution status. Session types are a
  protocol annotation.

### 2.8 Section 2 summary
All of linear/affine/relevant/ordered/QTT/graded/uniqueness/ownership are
a CONTEXT discipline over the same binders: grade (or multiplicity) per
variable occurrence plus a structural rule set. They need no new syntax;
they need (a) an annotation slot on binders and occurrences, and
(b) per-language "rule data" if one ever wants to check them. For a
STRUCTURE linter the only relevant features are *use sites* (move,
borrow, drop, capture) as a relation over name occurrences.

---------------------------------------------------------------------------
## 3. Effects and evaluation order

### 3.1 Monads (Moggi)
Def: Moggi, "Computational lambda-calculus and monads", LICS 1989, and
  "Notions of computation and monads", Information and Computation 93,
  1991. A computational effect is a strong monad T; the computational
  lambda calculus (lambda_c) adds `let x = e1 in e2` (sequencing) and
  `[v]` (unit) separating values from computations. Wadler, "The
  essence of functional programming", POPL 1992; "Monads for functional
  programming" 1995. Haskell's IO and do-notation.
Binders: let-binding is the sequencing construct; `do` is sugar for
  nested let-binds (a CHAIN of binders).
Decidable: TC decidable; semantics depends on the monad. A monad
  transformer stack is a type-level computation (decidable, undecidable
  with instance resolution extensions).
Verdict: "let x = e1 in e2" as a primitive sequencing form; monadic
  syntax is just that, a binder. Sugar like do/async-await/generators
  all desugar to it (a total, local translation: this is the
  type of translation we want).

### 3.2 Algebraic effects and handlers (Plotkin-Power, Plotkin-Pretnar)
Def: Plotkin-Power, "Algebraic operations and generic effects", Applied
  Categorical Structures 11, 2003: effects as operations of an
  algebraic theory (op : A ~> B), monads arising as free-model monads
  of the equations. Plotkin-Pretnar, "Handlers of algebraic effects",
  ESOP 2009; LMCS 9(4) 2013 "Handling algebraic effects": handlers are
  homomorphisms from the free model, with a delimited continuation.
  Terms: perform op(v), handle e with { return x -> ..; op(x,k) -> .. }.
  Languages:
  - Eff (Bauer-Pretnar, "Programming with algebraic effects and
    handlers", JLAMP 2015; https://www.eff-lang.org/).
  - Koka (Leijen, "Type directed compilation of row-typed algebraic
    effects", POPL 2017; https://koka-lang.github.io/): row-typed effects
    <exn,div|e>, evidence-passing compilation.
  - Effekt (Brachthaeuser-Schuster-Ostermann, "Effects as capabilities:
    effect handlers and lightweight effect polymorphism", OOPSLA 2020;
    https://effekt-lang.org/): second-class capabilities instead of
    effect rows.
  - Frank (Lindley-McBride-McLaughlin, "Do be do be do", POPL 2017):
    effect handling by multihandlers with ambient ability.
  - OCaml 5 (Sivaramakrishnan et al., "Retrofitting effect handlers onto
    OCaml", PLDI 2021): UNTYPED effects (no effect rows), one-shot
    continuations, runtime stacks.
  - Scoped effects (Wu-Schrijvers-Hinze, Haskell 2014; Yang et al., ESOP
    2022 "Structured handling of scoped effects") and hefty algebras
    (Poulsen-van der Rest, "Hefty algebras: modular elaboration of
    higher-order algebraic effects", POPL 2023): higher-order operations
    (catch, local, once) are not algebraic.
Binders: handler clauses bind the operation payload x and continuation
  k (a binder that captures the rest of the computation); `resume`.
Decidable: effect inference decidable for rows with Hindley-Milner-like
  unification (Koka); typing decidable; handler semantic termination is
  NOT (effects can encode general recursion, e.g. via state).
Verdict: an effect is an OPERATION SITE (perform) plus a HANDLER scope.
  The structural core needs (a) an operator form for "perform"
  (a call-like site, possibly to an unresolved handler), (b) handler as
  binder of a continuation. This is exactly frob's "effect sites"
  (code-model section 3: gob-symbols effect sites).

### 3.3 Row-typed effects, capability passing, graded monads
- Rows (Remy 1989; Leijen 2005 scoped labels): extensible records and
  variants; effect rows are the same technology.
- Capability-passing: effects are values you hold (Effekt, Scala 3
  capture checking Boruch-Gruszecki et al. 2023 "Capturing types",
  TOPLAS; object-capability languages: E, Pony, Wyvern, Gordon-Hu).
  Structural fact: whether a function REFERS to a capability name is
  syntactic; capture sets are free-variable sets (computable).
- Graded monads (Katsumata, "Parametric effect monads and semantics of
  effect systems", POPL 2014; Orchard-Petricek-Mycroft 2014): monad
  indexed by an ordered monoid of effect grades: T_e A with return :
  A -> T_1 A and bind : T_e A -> (A -> T_f B) -> T_(e.f) B.
Decidable: effect-grade checking decidable when the grade monoid has
  decidable order; over-approximation = the lattice of the grades.
Verdict: effect = an element of a lattice, composed along sequencing;
  the analyser computes a join over the (static) call graph. This is the
  abstract-interpretation frame (5.8). Grades = "capabilities" in
  frob's matrix.

### 3.4 Call-by-push-value, CBPV (Levy)
Def: Levy, "Call-by-push-value: a subsuming paradigm", TLCA 1999;
  "Call-by-push-value: a functional/imperative synthesis", Springer 2004
  (https://www.cs.bham.ac.uk/~pbl/cbpv.html). Two syntactic categories:
  VALUES (A ::= U B | 1 | A x A | A + A | ..; V ::= x | thunk M | ..)
  and COMPUTATIONS (B ::= F A | A -> B | B & B | ..; M ::= return V |
  M to x. N | force V | \x.M | M V | ..). Principle: "a value IS, a
  computation DOES". CBV: translate A -> B as U(A -> F B); CBN: translate
  A -> B as U B -> B. Both embed faithfully, with the equational theory
  preserved: so CBPV is a strict superset subsuming both orders, with
  effects (state, exceptions, nondeterminism) added uniformly as
  computation-type structure. Related: Moggi's lambda_c; Egger-Moeller-
  Schuermann, "Enriched effect calculus", LICS 2010; Forster-Schuermann-
  Kammar-Lindley-Sabry (expressiveness of effects), "On the expressive
  power of user-defined effects", JFP 2019.
Binders: lambda (computation binder), `to x.` (sequencing binder),
  case/split binders, `rec`.
Decidable: TC decidable; operational semantics deterministic.
Verdict: the evaluation-order dimension is a PROPERTY, not a syntax
  difference: CBPV shows CBV/CBN/lazy/strict languages share ONE syntax
  skeleton modulo "where are the thunks/forces". For structure, record
  evaluation-order as a per-language attribute, not in the core.

### 3.5 CPS and ANF as canonical forms
- CPS: Plotkin, "Call-by-name, call-by-value and the lambda-calculus",
  TCS 1(2), 1975: two CPS translations, one per evaluation order, that
  make the evaluation order independent of the host. Reynolds,
  "Definitional interpreters for higher-order programming languages",
  1972 (HOSC 1998). Fischer 1972. Sabry-Felleisen 1993 "Reasoning about
  programs in continuation-passing style". Kennedy, "Compiling with
  continuations, continued", ICFP 2007 (arguing for a typed direct-style
  with explicit continuation binders, a middle path).
- ANF: Flanagan-Sabry-Duba-Felleisen, "The essence of compiling with
  continuations", PLDI 1993: every non-trivial subexpression named by a
  let; arguments are atoms. Sabry-Wadler, "A reflection on call-by-
  value", TOPLAS 1997: ANF = monadic normal form = CPS minus
  continuations; the equivalence is exact.
- SSA = functional programming (Appel, "SSA is functional programming",
  SIGPLAN Notices 1998; Kelsey 1995 "A correspondence between CPS and
  SSA"; Chakravarty-Keller-Zadarnowski 2003): SSA phi-nodes are block
  parameters, which is how MLIR represents them.
Decidable: all are SYNTACTIC translations, total and computable, linear
  size; preserve alpha-equivalence classes and evaluation order.
Verdict: a CANONICAL FORM exists per evaluation-order semantics:
  A-normalisation is a total, computable, local-ish rewrite to a form
  where every call has atomic arguments. For a linter, ANF is the right
  normal form for "call site" and "data-flow edge" predicates (e.g.
  "sort inside loop"). Offer it as a DERIVED view, not as the stored IR.

### 3.6 Abstract machines: SECD, CEK, Krivine, and the functional
correspondence
- SECD: Landin, "The mechanical evaluation of expressions", Computer
  Journal 6(4), 1964: Stack, Environment, Control, Dump.
- CEK: Felleisen-Friedman, "Control operators, the SECD machine, and the
  lambda-calculus", 1987: Control, Environment, Kontinuation as data;
  CESK adds a Store (Felleisen-Friedman; Van Horn-Might "Abstracting
  abstract machines", ICFP 2010 = systematic derivation of
  control-flow analysis by abstracting the CESK machine's store).
- Krivine machine: Krivine, "A call-by-name lambda-calculus machine",
  HOSC 20, 2007 (circa 1985): environment machine with
  closures-as-pairs and a stack, call-by-name; de Bruijn indices.
- Functional correspondence: Ager-Biernacki-Danvy-Midtgaard, "A
  functional correspondence between evaluators and abstract machines",
  PPDP 2003: interpreter -> CPS -> defunctionalize -> machine, each step
  a mechanical total transformation.
- Also: Warren abstract machine for Prolog (Warren 1983), STG machine
  for Haskell (Peyton Jones 1992), JVM/CLR bytecode machines, WASM.
Decidable: machines are deterministic transition systems; reachability
  on infinite state UNDECIDABLE; with abstraction (finite store) becomes
  decidable (AAM).
Verdict: abstract machines are SEMANTIC; the structural core does not
  contain one. But "AAM: the machine is the analysis" shows that a
  sound call-graph analysis is just "the same semantics with a finite
  abstraction of the store", so if frob later adds a precise call graph
  it should come from an abstracted evaluator, not a hand-rolled
  heuristic.

---------------------------------------------------------------------------
## 4. Other universal cores

### 4.1 SKI and BCKW combinators
Def: Schoenfinkel 1924 ("Ueber die Bausteine der mathematischen Logik"),
  Curry 1930s: S x y z = x z (y z); K x y = x; I x = x (I = S K K). BCKW:
  B x y z = x (y z), C x y z = x z y, K, W x y = x y y; BCKW (without
  W) = affine; BCK = affine linear fragment, BCI = linear. A single
  combinator suffices (Iota, Barker 2001; Jot; Tromp's binary lambda
  calculus and combinatory logic, "Binary lambda calculus and
  combinatory logic", 2006/2010).
Binders: NONE. Variable-free: binding is compiled away by bracket
  abstraction (Curry-Feys 1958; Turner 1979 "Another algorithm for
  bracket abstraction", with optimizations giving O(n log n) output).
Decidable: Turing complete; conversion undecidable; normal-order
  reduction is normalizing for terms that have a normal form.
Verdict: proves binders are ELIMINABLE for computation but at the cost of
  losing scope structure; the translation is global (non-local), so it is
  the wrong target for STRUCTURE. The structure model keeps binders.

### 4.2 Interaction nets and interaction combinators
Def: Lafont, "Interaction nets", POPL 1990; "Interaction combinators",
  Information and Computation 137, 1997: graphs of agents with
  principal and auxiliary ports; rewrite only at active pairs (two
  principal ports connected); local, deterministic, strongly
  confluent (one-step diamond), no global control. Interaction
  combinators: three agents (constructor gamma, duplicator delta,
  eraser epsilon) are UNIVERSAL for interaction nets. Lambda calculus
  encodes (Lafont; Mackie; Lamping 1990 "An algorithm for optimal
  lambda calculus reduction", POPL; Asperti-Guerrini 1998 "The optimal
  implementation of functional programming languages"). Implementations:
  HVM / HVM2 / Bend (Taelin, HigherOrderCO,
  https://github.com/HigherOrderCO/HVM), Kind (dependently typed,
  compiles to HVM), Inpla. Parallel by construction (GPU).
Binders: none (sharing/duplication is explicit graph structure);
  variables become wires.
Decidable: Turing complete; reduction non-terminating in general;
  termination undecidable. Linear-logic proof nets are the typed
  fragment (Girard 1987; strongly normalizing).
Verdict: excellent as an EXECUTION substrate (local, parallel), irrelevant
  as a structure representation (source nesting and names are gone).
  Take: graph-based IRs can make dataflow edges first class.

### 4.3 Turing machines, register machines, mu-recursive functions
Def: Turing 1936 (a-machines); Post machines; Minsky 1961 and
  Shepherdson-Sturgis 1963 register machines (counters with inc,
  dec-jump-if-zero; two counters suffice, Minsky); Kleene 1936
  mu-recursive functions (zero, successor, projections, composition,
  primitive recursion, minimisation mu). Godel-Herbrand recursive
  functions; Church's lambda-definability (equivalent: Kleene 1936,
  Turing 1937). Church-Turing thesis.
Binders: none (indices, states, registers).
Decidable: all undecidable semantically (halting); syntax trivially
  decidable (finite tables).
Verdict: confirm U1. A language whose programs can be turned into a
  machine configuration is covered semantically; irrelevant
  structurally.

### 4.4 Explicit substitutions
Def: Abadi-Cardelli-Curien-Levy, "Explicit substitutions", POPL 1990
  / JFP 1991: the lambda-sigma calculus makes substitution a first-class
  term t[s] with closure-like substitutions s ::= id | shift | t . s |
  s o s; Curien 1991 "An abstract framework for environment machines";
  Kesner's lambda-x, Bloo-Rose lambda-x (preservation of strong
  normalisation, PSN, fails for lambda-sigma, Mellies 1995 "Typed
  lambda-calculi with explicit substitutions may not terminate").
Binders: lambda with de Bruijn indices plus substitution terms.
Decidable: confluence on closed terms; on open terms lambda-sigma not
  confluent (a variant lambda-sigma-SP is).
Verdict: do NOT put substitution inside the structure model; it is
  a semantic device. Useful insight: scoping = a substitution-
  environment relation; environment = scope chain.

### 4.5 Variable representations: de Bruijn indices/levels, locally
nameless, HOAS, PHOAS, nominal
- de Bruijn indices (de Bruijn 1972, "Lambda calculus notation with
  nameless dummies"): variable = number of binders between occurrence
  and binder. Canonical (alpha-equivalent terms are syntactically equal)
  but shifting makes substitution error prone and the form destroys
  original names. De Bruijn LEVELS: count from the outermost binder, so
  stable under weakening (used in NbE and in cubical implementations).
- Locally nameless (McKinna-Pollack 1993; Gordon 1994; Chargueraud, "The
  locally nameless representation", JAR 49, 2012): bound variables as
  indices, free variables as names; opening/closing operations; the
  popular mechanization choice (Coq metalib, Lean).
- HOAS (Pfenning-Elliott, "Higher-order abstract syntax", PLDI 1988;
  Miller-Nadathur lambda-Prolog): object binder = meta-level lambda.
  Gives alpha and substitution for free; makes induction/ recursion over
  terms hard ("exotic terms"). PHOAS (Chlipala, "Parametric higher-order
  abstract syntax for mechanized semantics", ICFP 2008): parametrize
  the variable type, ruling out exotic terms via parametricity.
- Nominal techniques (Gabbay-Pitts, "A new approach to abstract syntax
  with variable binding", Formal Aspects of Computing 13, 2002; Pitts,
  "Nominal sets", CUP 2013): atoms (names) with permutation action,
  freshness (a # x), the name-abstraction [a]x as a data constructor,
  alpha-equivalence = equality of abstractions; FreshML (Shinwell-Pitts-
  Gabbay, ICFP 2003); nominal unification (Urban-Pitts-Gabbay 2004,
  decidable in polynomial time, Calves-Fernandez 2008); Nominal Isabelle
  (Urban-Tasson 2005); alphaProlog; alphaKanren.
- Binding libraries: Unbound / unbound-generics (Weirich-Yorgey-Sheard,
  "Binders unbound", ICFP 2011); RepLib; bound (Kmett; de Bruijn with
  Scope monads, Bird-Paterson 1999 "de Bruijn notation as a nested
  datatype"); Scrap your boilerplate; Moniker (Rust, Brendan Zabarauskas).
Decidable: alpha-equivalence is decidable in LINEAR time in every
  representation (convert to canonical form). Free variables computable.
Verdict: TWO representations needed: names for humans/diagnostics and
  provenance (the symref), and a CANONICAL nameless form for digests
  (alpha-invariant digest). Choose locally nameless or nominal atoms
  (unique ids) for storage; compute de Bruijn only to hash. The
  hashing result is exactly Unison's design (4.8.1/7.14).

### 4.6 Abstract binding trees (ABTs; Harper, "Practical Foundations for
Programming Languages", CUP 2012, 2nd ed. 2016, Chapters 1-2,
https://www.cs.cmu.edu/~rwh/pfpl/)
Def: ASTs are ordered trees whose nodes are operators o of declared ARITY
  (s1, ..., sn)s: an operator of sort s takes n arguments of sorts s_i.
  ABTs generalize with VALENCES: argument i of sort s_i binds k_i
  variables of sorts s_i1..s_ik_i: the arity of an operator is a list of
  valences (s1.. sk) . s. Terms: x | o(x1..x1'.a1; ...; xn..xn'.an).
  PFPL ch.1 gives: abstract syntax tree, ABT signature, alpha-
  equivalence, substitution, structural induction, "generic
  judgements" (hypothetical/generic); ch.2 inductive definitions.
  The language T / PCF / FPC / etc. in PFPL are all defined as ABT
  signatures plus statics/dynamics (judgement forms).
  Implementations: the Standard ML "abt" library of Harper and students;
  Jon Sterling's abbot (https://github.com/jonsterling/abbot)
  and RedPRL/cooltt's bindlib; Haskell abt (Wren Romano,
  https://hackage.haskell.org/package/abt); Nuprl and JonPRL's term
  structure; OCaml `abt`; Rust crates for ABTs are ad hoc. Nuprl uses
  the same notion (Constable et al., "Implementing mathematics with the
  Nuprl proof development system", 1986: operators with arities and
  bound variables, "opid" and "bound terms").
Binders: the SINGLE binder-introducing construct is the abstractor
  x.e; operators declare which argument positions bind which sorted
  variables. Binding structure is therefore STATIC DATA of the
  signature, not code.
Decidable: alpha-equivalence, free variables, capture-avoiding
  substitution: all decidable, linear/quadratic. Well-formedness
  ("is this tree a valid ABT of signature S") decidable by arity check.
  Initial-algebra view: ABT(S) is the initial algebra of the binding
  signature (Fiore-Plotkin-Turi 1999, see 5.6).
Verdict: THE candidate. An ABT signature is the smallest structure that
  carries node kinds, ordered children, sorts and binding. Adopt as the
  core, then ADD a nominal-name layer and an Opaque operator
  (section 8a).

### 4.7 Mechanized metatheory / logical-framework treatments of syntax
- Harper-Licata, "Mechanizing metatheory in a logical framework", JFP 17,
  2007: LF encodings of programming-language syntax with HOAS and
  adequacy.
- Lee-Crary-Harper, "Towards a mechanized metatheory of Standard ML",
  POPL 2007 (Twelf): a whole real language (SML) with its binding and
  static semantics mechanized in LF.
- Aydemir et al., "Mechanized metatheory for the masses: the POPLmark
  challenge", TPHOLs 2005 (https://www.seas.upenn.edu/~plclub/poplmark/):
  the standard benchmark; revealed binding representation as the main
  pain point; comparisons of de Bruijn, locally nameless, nominal, HOAS.
- Rouvoet-Poulsen-Krebbers-Visser, "Intrinsically-typed definitional
  interpreters for linear, session-typed languages", CPP 2020 and the
  Statix work for scope graphs (4.10).
  [The "Harper/Crary" attribution in the task prompt is best read as the
   Lee-Crary-Harper SML mechanization and Harper-Licata; verify.]
Verdict: binding is the thing every mechanization effort finds hardest;
  hence it deserves to be a PRIMITIVE of the core rather than encoded.

### 4.8 Universe-of-syntaxes frameworks
- Allais-Atkey-Chapman-McBride-McKinna, "A type and scope safe universe of
  syntaxes with binding: their semantics and proofs", ICFP 2018, JFP 31
  2021 (https://dl.acm.org/doi/10.1145/3236785,
  https://github.com/gallais/generic-syntax): a DESCRIPTION language
  Desc I (sums, products, `sigma`, `X` with a binding extent: argument
  positions annotated by the list of sorts they bind, `Var`) whose
  interpretation is a scope- and type-safe syntax with renaming and
  substitution generically derived (Kripke semantics, fold, NbE); one
  generic proof of the "syntactic framework" laws gives renaming,
  substitution, normalisation by evaluation for EVERY described syntax.
  This is essentially ABT signatures with sorts expressed as a
  (typed, scoped, intrinsically correct) universe.
- Data types a la carte (Swierstra, JFP 18(4), 2008): open sum of
  functors f :+: g with injection classes; terms Fix f; used by Semantic
  (7.8).
- Fiore-Hur "Second-order algebraic theories" (2010), Fiore-Szamozvonak
  (2022) formal theories of binding.
- Scope-graph frameworks (4.10).
Decidable: well-scopedness decidable; framework generic functions total.
Verdict: if the core is a described universe, then renaming,
  substitution and (alpha-)hashing are written ONCE; in Rust this is a
  trait over a signature table rather than dependent types, but the idea
  transfers: generic algorithms over arity data.

### 4.9 Scope graphs and stack graphs (name RESOLUTION as language-independent data)
- Neron-Tolmach-Visser-Wachsmuth, "A theory of name resolution",
  ESOP 2015: a scope graph = scopes (nodes), declarations and
  references (data), edges (parent P, import I, ...), and a RESOLUTION
  calculus: a path from reference to declaration, well-formed by a
  regular expression over edge labels, with shadowing order
  (specificity). Expresses lexical scope, modules, imports, inheritance,
  qualified names, for many languages. Antwerpen-Neron-Tolmach-Visser-
  Wachsmuth, "A constraint language for static semantic analysis based
  on scope graphs", PEPM 2016; "Scopes as types", OOPSLA 2018 (Statix).
  Spoofax / NaBL / NaBL2 (Konat-Kats-Wachsmuth-Visser 2012).
- GitHub stack graphs (Creager and van Antwerpen, "Stack graphs: name
  resolution at scale", arXiv 2211.01224,
  https://github.com/github/stack-graphs): incremental, file-at-a-time
  construction of per-file partial paths with a push/pop-symbol
  pushdown resolution (a Dyck language), used for precise code
  navigation across Python, JavaScript/TypeScript, Java, ... in
  github.com. Name resolution as pushdown-automaton reachability =
  decidable, and incremental because partial paths compose.
  (Repository status: stack-graphs was archived in 2025 [verify].)
- Flatt, "Binding as sets of scopes", POPL 2016: macro-hygiene model
  where each identifier carries a SET of scopes and binding = the
  binder whose scope set is the largest subset of the reference's set;
  used by Racket.
- Kohlbecker-Friedman-Felleisen-Duba, "Hygienic macro expansion",
  LFP 1986; Dybvig-Hieb-Bruggeman, "Syntactic abstraction in Scheme",
  LASC 1993 (syntax-case); Clinger-Rees 1991.
Decidable: resolution is decidable (reachability in a finite graph with
  regular-language path constraints), polynomial for stack graphs; but
  construction of the graph for languages with dynamic features (eval,
  macros, reflection) is not complete.
Verdict: the most direct precedent. Lexical abstractors cover only the
  tree-shaped binders; real languages (modules, imports, inheritance,
  `from m import *`, namespaces split across files, trait impls) need a
  GRAPH relation on top of the tree. Decision: the core stores a
  scope graph (sets of nodes and labelled edges) derived by adapters,
  alongside the ABT. Then "symref resolution" (code-model section 2) is
  exactly scope-graph resolution.

### 4.10 Logic-programming cores
- Horn clauses (Horn 1951) and resolution (Robinson 1965, "A machine-
  oriented logic based on the resolution principle"); SLD resolution
  (Kowalski 1974, "Predicate logic as programming language"); Prolog
  (Colmerauer-Roussel 1972; Warren 1983 WAM).
  Binders: clause variables are implicitly universally quantified
  (clause-level scope); no nested binders. Decidable: Horn-clause
  satisfiability of FIRST-ORDER Horn clauses UNDECIDABLE (Turing
  complete; Tarnlund 1977); propositional Horn SAT is linear time.
- Datalog (Abiteboul-Hull-Vianu, "Foundations of databases", 1995,
  http://webdam.inria.fr/Alice/; Ceri-Gottlob-Tanca 1989): function-free
  Horn clauses; semantics = LEAST FIXPOINT of the immediate-
  consequence operator T_P (van Emden-Kowalski 1976; Knaster-Tarski
  1955). Decidable: evaluation is in PTIME in the size of the data
  (data complexity PTIME-complete), EXPTIME-complete in combined
  complexity; with stratified negation (Apt-Blair-Walker 1988) and
  well-founded semantics (Van Gelder-Ross-Schlipf 1991) still
  decidable; Datalog containment of recursive programs undecidable
  (Shmueli 1987); uniform containment decidable (Sagiv 1988).
  Engines: Souffle (Jordan-Scholz-Subotic, CAV 2016,
  https://souffle-lang.github.io/), Differential Datalog, Datafrog
  (Rust, used in Polonius), Ascent (Rust), Crepe (Rust), Doop (Bravenboer-
  Smaragdakis, "Strictly declarative specification of sophisticated
  points-to analyses", OOPSLA 2009), IncA, Flix (Madsen-Tip-Lhotak
  "Fixpoints for the masses", PLDI 2016), Formulog, CodeQL's QL.
  Binders: none (variables bound per rule).
- Decidability bonus: Datalog = fixpoint logic on finite relations
  (Immerman-Vardi: PTIME = FO + LFP on ordered structures); so any
  structural query phrased as a Datalog program over the tree and
  binding relations is polynomial and always terminates. THIS is the
  structural-predicate class P in section 8b.
Verdict: FACT STORE + Datalog is the right query layer: the core is a
  set of relations (node, child, label, binds, ref, decl, span) and
  predicates are Datalog/FO+LFP formulas. It guarantees termination of
  every predicate by construction and gives incremental view
  maintenance (DRed, Gupta-Mumick-Subrahmanian 1993).

### 4.11 Relational algebra and databases
Def: Codd, "A relational model of data for large shared data banks",
  CACM 13(6), 1970. Operators: select, project, join, union, difference,
  rename. Codd's theorem: relational algebra = relational calculus (safe
  FO queries). SQL as a language with its own structure (nested
  queries, CTEs).
Binders: relational calculus has quantifiers; algebra has none but has
  attribute renaming.
Decidable: query evaluation is AC0 in data complexity, PSPACE-complete
  in combined complexity; satisfiability and equivalence of FO queries
  UNDECIDABLE (Trakhtenbrot 1950), but decidable for conjunctive
  queries (NP-complete containment, Chandra-Merlin 1977).
  Recursive extension = Datalog.
Verdict: use RA/FO as a query semantics; confirms evaluation over a
  given finite structure is cheap even when "does any model exist"
  questions are undecidable (a lint is model checking, not
  satisfiability).

### 4.12 Term rewriting systems (TRS)
Def: Baader-Nipkow, "Term rewriting and all that", CUP 1998; Terese
  2003; first-order terms over a signature with rules l -> r;
  higher-order variants: HRS (Nipkow 1991), CRS (Klop 1980), ERS, and
  Rewriting Logic (Meseguer 1992) with Maude (http://maude.cs.illinois.edu/).
  K framework (Rosu-Serbanuta, "An overview of the K semantic framework",
  JLAP 2010, https://kframework.org/): language semantics as
  configuration-rewriting rules on labelled-cell terms; the C semantics
  (Ellison-Rosu, POPL 2012), Java, EVM, JavaScript in K. K IS the
  existing industrial attempt at "give every language a rewriting
  semantics in one framework". Also Rascal (Klint-van der Storm-Vinju,
  SCAM 2009), Spoofax, Stratego, TXL, Ott (Sewell et al., JFP 2010),
  Lem, Redex (Felleisen-Findler-Flatt, "Semantics engineering with PLT
  Redex", MIT Press 2009).
Binders: first-order TRS none; HRS/CRS via meta-lambda.
Decidable: termination UNDECIDABLE (Huet-Lankford 1978) even for one-rule
  systems (Dershowitz 1987); confluence undecidable in general but
  decidable for terminating systems via critical pairs (Knuth-Bendix
  1970); joinability of ground terms undecidable; for GROUND TRS,
  termination and confluence DECIDABLE (Dauchet-Tison). Word problem
  undecidable (Markov-Post).
Verdict: K/Redex/Maude demonstrate the economics: giving *semantics* to
  each language costs man-years (K's C semantics was a PhD-scale
  project) and is still partial. Structure is far cheaper. Keep
  semantics as an OPTIONAL per-language add-on in a different layer
  (the "dynamics" in PFPL's terms).

### 4.13 Process calculi beyond pi
- CCS (Milner 1980, "A calculus of communicating systems"; 1989
  "Communication and concurrency"): processes with action prefix,
  choice, parallel, restriction, relabelling; bisimulation (Park 1981);
  CSP (Hoare 1978). Binders: restriction only; values via value-passing
  CCS. Decidable: bisimilarity decidable for finite-state processes,
  undecidable for CCS with recursion (Turing complete via counters);
  for BPP and pushdown fragments decidable in places (Moller et al.).
- Join calculus (Fournet-Gonthier, "The reflexive chemical abstract
  machine and the join-calculus", POPL 1996): locality; join patterns
  J |> P bind names with multiple message patterns (a pattern binder over
  multiple channels). Implementations: JoCaml, Polyphonic C#, Scala Joins.
- Actors (Hewitt-Bishop-Steiger 1973; Agha, "Actors: a model of concurrent
  computation in distributed systems", 1986; Agha-Mason-Smith-Talcott
  1997 "A foundation for actor computation"): addresses are first-class
  values; mailbox; `become`. Erlang/Elixir, Akka, Pony. Decidable:
  reachability undecidable (Turing complete); deadlock freedom
  undecidable in general.
Binders: actor behaviours bind the message pattern and the acquaintance
  addresses.
Verdict: all process models have DYNAMIC addresses -> structural
  "who calls whom" becomes a may-analysis. For concurrency, a structural
  linter records spawn/send/receive SITES and their channel NAMES and
  gives Unknown for the peer.

### 4.14 Concatenative and stack calculi
Def: Kerby, "The theory of concatenative combinators", 2002
  (http://tunes.org/~iepos/joy.html): programs are concatenations of
  words; juxtaposition = function composition; quotation [..] gives
  first-class programs; combinators dup, swap, drop, cat, cons, i, dip;
  an exact correspondence with combinatory logic (a concatenative
  basis [dip; zap; dup; cons...] is Turing complete). von Thun's Joy
  1990s; Cat (Diggins); Factor; Forth, PostScript, dc, Kitten, Uiua,
  WebAssembly's stack discipline. Stack effects ( a b -- c ) as types
  (Cat, Kitten; Diggins 2008; Stay-at-home-types).
Binders: NONE (point-free). Local variables exist in Factor (`::`), Forth
  locals, which re-introduce binders as sugar.
Decidable: Turing complete; stack-effect inference decidable for
  Joy-like simple types (Hindley-Milner variant with row-polymorphic
  stacks, Cat); polymorphic recursion makes it undecidable.
Verdict: structure = sequences with quotation (nested lists); a call
  graph requires knowing the arity (stack effect) to know which tokens
  are arguments. The core must allow operators with VARIADIC/NO static
  arity (a sequence sort) and mark argument binding as Unknown.

### 4.15 Array calculi
Def: Iverson, "Notation as a tool of thought", CACM 23(8), 1980, Turing
  Award lecture (APL, J, K, BQN, Uiua); rank polymorphism: scalars,
  vectors, matrices handled by one function via frame/cell lifting;
  Remora (Slepak-Shivers-Manolios, "An array-oriented language with
  static rank polymorphism", ESOP 2014; Slepak et al. "The Semantics of
  Rank Polymorphism", arXiv:1907.00509): dependent shape indices;
  Dex (Paszke et al., POPL 2021 "Getting to the point"), Futhark
  (Henriksen et al. PLDI 2017), Accelerate, SaC; NumPy broadcasting
  (not statically typed). Array fusion = deforestation.
Binders: APL has dynamic scope for dfns? (lexical in Dyalog dfns); J
  trains are tacit (no binders). Shape-indexed types add index
  binders.
Decidable: shape checking decidable for Remora when index language is
  decidable (Presburger-like), undecidable for arbitrary shape terms.
  Execution Turing-complete.
Verdict: "rank-lifted application" means a call site's cost model and
  loop structure are IMPLICIT (an array op is a loop): a "loop"
  structural predicate does not see array loops. Tag array-operator
  nodes with an implicit-iteration attribute; do not unfold.

### 4.16 Synchronous dataflow and Kahn networks
Def: Kahn, "The semantics of a simple language for parallel
  programming", IFIP 1974: processes as continuous functions on streams
  (least fixpoint, Scott-continuity); Lee-Messerschmitt "Synchronous
  data flow", Proc. IEEE 1987 (SDF: fixed rates, static schedule);
  Lustre (Caspi-Pilato-Raymond-Halbwachs, POPL 1987; Halbwachs et al.,
  Proc. IEEE 1991): equations over streams x = 0 -> pre y, CLOCKS
  (boolean streams) to sample; clock calculus = type system for
  causality of when a stream is present; SCADE, Esterel (Berry-Gonthier
  1992), Signal, Lucid (Wadge-Ashcroft 1985), Lucy-n (n-synchrony,
  Mandel-Plateau-Pouzet). Reactive: FRP (Elliott-Hudak 1997), Rx.
Binders: equation-defined variables, recursive (stream names; no order).
  Local nodes with clocks.
Decidable: Lustre/Esterel are finite-state: ALL properties decidable by
  model checking (Kind 2, Lesar); the clock calculus is decidable;
  causality (instantaneous cycles) decidable. Kahn networks Turing
  complete in general; SDF scheduling decidable (Lee).
Verdict: declarative equations without order: structure is a SET of
  equations not a sequence. The core's children sort must allow
  UNORDERED collections (sets/multisets) for such languages, or
  adapters impose source order and mark it semantically irrelevant.

### 4.17 Quantum lambda calculi and ZX
- Selinger-Valiron, "A lambda calculus for quantum computation with
  classical control", MSCS 16, 2006: linear lambda calculus, qubits as
  linear resources (no cloning), quantum data / classical control; also
  Altenkirch-Grattage 2005 QML ("A functional quantum programming
  language", LICS), van Tonder 2004, Quipper (Green et al., PLDI 2013,
  https://www.mathstat.dal.ca/~selinger/quipper/), Q#, Silq (Bichsel et
  al., PLDI 2020, automatic uncomputation), Qimaera.
  Binders: linear lambda + `new`/`measure` binding qubits. Decidable:
  type checking decidable (linearity); Turing complete classically;
  quantum circuits (circuit model) are finite.
- ZX-calculus (Coecke-Duncan, "Interacting quantum observables",
  ICALP 2008 / NJP 2011): graphical language: Z and X spiders, Hadamard,
  wires; diagrammatic rewriting; complete for stabilizer, universal
  fragment (Jeandel-Perdrix-Vilmart 2018, LICS; Hadzihasanovic-Ng-Wang;
  Vilmart 2019 for ZX complete for Clifford+T). Completeness gives
  semi-decidability of diagram equality by rewriting; general circuit
  equivalence is intractable (QMA/coNP-hard flavours) [verify]. Symmetric monoidal
  categories with compact structure (dagger-compact).
Binders: ZX has NONE (wires connect ports; string diagrams = morphisms
  of a PROP).
Verdict: graph-shaped (string-diagram) structure appears even in
  "languages". A tree-with-binders core can host a circuit as an
  operator applied to a LIST of gates plus a wire-index relation. Wires
  = names (each wire is bound once, used once = linear).

### 4.18 Cellular automata and 2D/esoteric semantics
Def: von Neumann 1966 (self-reproducing CA); Conway's Life Turing
  complete (Berlekamp-Conway-Guy, "Winning ways", 1982; Rendell 2002);
  Rule 110 universal (Cook, "Universality in elementary cellular
  automata", Complex Systems 15, 2004; Wolfram 2002). 2D languages:
  Befunge (Pressey 1993), Piet (Morgan-Bryant 2001), Wireworld; "Fungeoids";
  Brainfuck (Mueller 1993; a TM variant: 8 instructions on a tape);
  Malbolge; Whitespace (Brady and Morris 2003); INTERCAL; Hexagony; Funges.
  Program text = grid with 2D control flow; the instruction pointer has a
  direction and wrap-around.
Binders: none (global memory); some use a stack.
Decidable: Turing complete; the parse is trivial but control flow is a
  PROGRAM-dependent dynamical system: "which instruction follows this
  one" requires simulation.
Verdict: for such languages, the tree shape is the character grid; the
  adapter yields a flat sequence of opaque nodes with 2D position
  attributes. Structural claims shrink to containment-by-file. Good
  negative control: our framework must still produce SOME answer
  (Unknown) rather than crash.

### 4.19 Reversible computing
Def: Landauer 1961 ("Irreversibility and heat generation in the
  computing process"); Bennett 1973 (reversible Turing machines);
  Janus (Lutz 1986; Yokoyama-Gluck, "A reversible programming language
  and its invertible self-interpreter", PEPM 2007): `if e then s1 else s2
  fi e'` with an assertion e' for the join, `from e do s loop s' until e'`
  with entry and exit assertions; `x += e` (reversible update);
  invertible by construction: inverse program reverses statement order
  and flips operators. RFUN (Yokoyama-Axelsen-Gluck 2011), Theseus
  (James-Sabry, POPL 2012, "Theseus: a high level language for reversible
  computing"), ReVerC, Bennett's pebbling, reversible circuits (Toffoli-
  Fredkin gates, Toffoli 1980).
Binders: local vars; Janus has global variables only (procedures with no
  recursion limit though).
Decidable: reversible TMs are as powerful as TMs (Bennett 1973, Lecerf
  1963); reachability still undecidable; but the inverse program is a
  total computable syntactic transform.
Verdict: introduces a structural dual (program/inverse); a core that
  carries "operator + its inverse operator" per node helps; low priority.

### 4.20 Probabilistic lambda calculi
Def: Saheb-Djahromi 1978/1980; Kozen 1981 "Semantics of probabilistic
  programs" (JCSS); Jones-Plotkin 1989 "A probabilistic powerdomain of
  evaluations"; Ramsey-Pfeffer, "Stochastic lambda calculus and
  monads of probability distributions", POPL 2002; Giry monad (1982);
  Church (Goodman-Mansinghka-Roy-Bonawitz-Tenenbaum, UAI 2008); Stan,
  Pyro, Anglican; Borgstrom-Dal Lago-Gordon-Szymczak, "A lambda-calculus
  foundation for universal probabilistic programming", ICFP 2016
  (sample/score; trace semantics); Staton-Wood-Yang-Heunen-Kammar
  ("Semantics for probabilistic programming: higher-order functions,
  continuous distributions, and soft constraints", LICS 2016);
  Bichsel-Gehr-Vechev "Fine-grained semantic..." etc.
Binders: `let x = sample d in ..` (monadic binding into a distribution
  monad); `observe` / `score` statements.
Decidable: almost-sure termination is Pi^0_2-complete, positive
  almost-sure termination Sigma^0_2-complete (Kaminski-Katoen,
  "On the hardness of analyzing probabilistic programs", Acta Inf.
  2019); equivalence undecidable; exact inference undecidable in
  general. Syntax is a monadic let.
Verdict: probabilistic is ANOTHER effect (random choice) sited at
  `sample`; same binder plus an effect label; nothing structural.

### 4.21 Other cores considered (one-liners)
- Petri nets (Petri 1962): places/transitions; reachability decidable
  (Mayr 1981; Kosaraju 1982; Leroux 2012; Ackermann-complete by
  Czerwinski-Orlikowski and Leroux 2021 [verify]) but nonprimitive recursive; structure = bipartite graph
  not tree. Verdict: subsumed by "graph relation over nodes".
- Statecharts/UML state machines (Harel 1987), BPMN, Simulink: graph +
  hierarchy; subsumed by tree + edges.
- Attribute grammars (Knuth 1968): synthesized/inherited attributes on
  parse trees; circularity testing is EXPTIME-complete (Jazayeri-Ogden-
  Rounds 1975). Verdict: the formalism for "derived facts attached to
  tree nodes"; our IR query layer is an attribute grammar evaluated
  lazily; use well-definedness (non-circular) rules.
- Lambda-mu / Curien-Herbelin sequent calculus (lambda-bar-mu-mu~, ICFP
  2000): symmetric duality of values and continuations (call-by-value
  vs call-by-name as duals); Wadler "Call-by-value is dual to call-by-
  name", ICFP 2003; Downen-Ariola 2018 "A tutorial on computational
  classical logic and the sequent calculus", JFP. Verdict: another
  evaluation-order-agnostic form, like CBPV.
- Effect-free "Core ML" (Standard ML's Definition of SML, Milner-Tofte-
  Harper-MacQueen 1997): a whole language specified with 100+ typing
  rules; "bare language" vs "derived forms" (Appendix of the Definition:
  derived forms as syntactic sugar translated to bare forms by a
  total function). This IS the pattern T_L: "Definition of SML"
  Appendix A is a total computable translation from derived forms to
  the Bare language; an existence proof for a REAL industrial language.
- Featherweight languages (Java, Go (Griesemer et al., OOPSLA 2020), Rust
  (Pearce), C (Ellison), Python (Politz et al., "Python: the full monty",
  OOPSLA 2013, lambda-py), JavaScript (Guha-Saftoiu-Krishnamurthi, "The
  essence of JavaScript", ECOOP 2010: lambdaJS)): per-language cores
  small enough to mechanize; each ~10-50 constructs plus lots of
  `desugar`. Python "full monty" translated Python to lambda-py (a core
  with ~ 40 forms) with a desugaring that is TOTAL, and tested against
  the CPython test suite. Direct evidence for the claim that
  per-language total desugaring to a small core is feasible, BUT NOTE
  the core there is per-language (lambda-py), not shared.
Verdict: the feasibility of T_L (per language, to a small core) is
  empirically established over and over; the novelty (and risk) is
  sharing ONE core across them.

---------------------------------------------------------------------------
## 5. Categorical and algebraic semantics (the shared-model candidates)

### 5.1 Cartesian closed categories (Lambek)
Def: Lambek, "From lambda-calculus to cartesian closed categories", in
  Seldin-Hindley (eds), To H.B. Curry, 1980; Lambek-Scott, "Introduction
  to higher-order categorical logic", CUP 1986. Simply typed lambda
  calculus with products and unit IS the internal language of a CCC:
  terms-in-context are morphisms, beta-eta is the equational theory, the
  syntactic category is the free CCC on the signature. Extended by:
  dependent types <-> locally cartesian closed categories (Seely 1984;
  Hofmann 1995 coherence) ; linear lambda <-> symmetric monoidal closed
  (Mac Lane; Barr *-autonomous for classical LL); polymorphism <->
  indexed/fibred or parametric models (Hyland-Robinson-Rosolini
  realizability toposes).
Binders: a lambda is currying (an adjunction); variables are projections
  out of a context object.
Decidable: equality in the free CCC (beta-eta with surjective pairing
  and unit) decidable (Cubric-Dybjer-Scott 1998 NbE; Lambek's problem);
  for free LCCC (extensional TT) UNDECIDABLE (see 1.12).
Verdict: a precise sense in which "STLC = the free structure", but it
  models SEMANTICS (equations between programs), not source structure;
  taking it as the core makes source structure irrelevant by design
  (quotients away all syntax differences). Not our target; but supplies
  the vocabulary (syntactic category, free model, functorial semantics).

### 5.2 Freyd categories, premonoidal categories, arrows
Def: Power-Robinson, "Premonoidal categories and notions of
  computation", MSCS 7, 1997; Power-Thielecke 1999; Levy-Power-Thielecke,
  "Modelling environments in call-by-value programming languages", I&C
  2003: a Freyd category = a cartesian category C (values), a
  premonoidal category K (computations) and an identity-on-objects
  functor J : C -> K centrally; sequencing is composition in K and
  evaluation order is visible in the failure of interchange.
  Hughes, "Generalising monads to arrows", SCP 37, 2000; Paterson's arrow
  notation (proc/do, 2001) as sugar; Atkey, "What is a categorical model
  of arrows?", MSFP 2008/EPTCS 2011: arrows = Freyd categories (enriched);
  McBride-Paterson "Applicative programming with effects", JFP 2008 =
  idioms/applicative = lax monoidal functors.
Hierarchy by power: functor < applicative < arrow < monad (Lindley-Wadler-
  Yallop, "Idioms are oblivious, arrows are meticulous, monads are
  promiscuous", ENTCS 2011): the three forms differ in whether control
  flow can depend on computed values; CBPV/Freyd correspond.
Verdict: effectful sequencing has a categorical normal form; confirms
  that evaluation-order-sensitive structure (sequence of binds) is a
  list of computations. Nothing new for the core's syntax.

### 5.3 Lawvere theories and monads
Def: Lawvere 1963 (PhD, "Functorial semantics of algebraic theories",
  http://www.tac.mta.ca/tac/reprints/articles/5/tr5.pdf): an algebraic
  theory = a category with finite products generated by the operations
  and equations; a model = product-preserving functor to Set. Finitary
  monads on Set <-> Lawvere theories (Linton 1966); Hyland-Plotkin-
  Power, "Combining effects: sum and tensor", TCS 357, 2006: effects
  combine as sum and tensor of theories (modular effects without
  monad transformers); Hyland-Power, "The category theoretic
  understanding of universal algebra: Lawvere theories and monads",
  ENTCS 172, 2007.
Decidable: word problem of a finitely presented algebraic theory is
  undecidable in general; for given equation-free theories (free
  monad) trivially decidable.
Verdict: A SIGNATURE (operations with arities) generates a free monad;
  that is precisely the core's "operator with arity" data. Equations
  are optional extras and must not be required.

### 5.4 Free monads, cofree comonads, freer monads
Def: free monad over a functor F: Free F A = A + F (Free F A) =
  Fix (A + F -); a term syntax with variable leaves; Swierstra DTALC
  2008; Kiselyov-Ishii, "Freer monads, more extensible effects", Haskell
  2015; cofree comonad: Cofree F A = A x F (Cofree F A): annotated trees
  (attribute grammars as cofree; "annotated AST" in Semantic); Uustalu-
  Vene "Comonadic notions of computation", ENTCS 2008; recursion
  schemes: Meijer-Fokkinga-Paterson, "Functional programming with
  bananas, lenses, envelopes and barbed wire", FPCA 1991 (cata, ana,
  hylo, para); Hinze, Wu, Gibbons "Unifying structured recursion
  schemes", ICFP 2013; Gibbons.
Binders: free monads are SUBSTITUTION MONADS: bind = substitution of
  variables by terms; this is precisely the "bound" library: Scope b f a
  adds the abstraction.
Decidable: all total functions by catamorphism: guaranteed termination on
  finite trees (fold is total).
Verdict: Fix of a signature functor = the syntax; Cofree = the syntax
  decorated with computed facts (spans, resolutions, types); a fold = a
  structural lint. The Rust analogue: `enum Node<R> { ... children: R }`
  with `R = Box<Node>` or arena ids, and annotation as a second
  type parameter. Design guidance: write passes as folds so they are
  total and parallelizable.

### 5.5 Bidirectional typing as the elaboration discipline
Def: Pierce-Turner, "Local type inference", TOPLAS 22(1), 2000;
  Dunfield-Krishnaswami, "Bidirectional typing", ACM Computing Surveys 54
  (5), 2021 (arXiv:1908.05839); Coquand 1996 "An algorithm for type-
  checking dependent types"; Dunfield-Krishnaswami "Complete and easy
  bidirectional typechecking for higher-rank polymorphism", ICFP 2013.
  Two modes: synthesize (infer) type from term (eliminations), check term
  against type (introductions); annotations only at mode switches. Gives
  decidable checking for rank-N, GADTs, dependent types where full
  inference is undecidable.
Decidable: by design total on terms with enough annotation.
Verdict: ELABORATION from surface to core is itself a bidirectional,
  syntax-directed, total pass if the surface is annotated enough; where
  the surface is unannotated (Python, JS) the mode switch point is
  `unknown`. This is the cleanest rationale for graded confidence in
  frob's "imports with confidence".

### 5.6 Syntax as free algebra: initial algebra semantics and binding
Def: Goguen-Thatcher-Wagner-Wright (ADJ), "Initial algebra semantics and
  continuous algebras", JACM 24(1), 1977: the syntax of a language = the
  INITIAL Sigma-algebra T_Sigma; semantics = the unique homomorphism to
  any other Sigma-algebra (compositionality = homomorphism); Lambek's
  lemma: the initial algebra of a functor F is an isomorphism
  F(mu F) ~ mu F, the formal "unfold one level" (hence induction). With
  BINDING: Fiore-Plotkin-Turi, "Abstract syntax and variable binding",
  LICS 1999: syntax with binding = initial algebra of a binding
  signature functor on the presheaf category [F, Set] (F = finite
  cardinals and injections/renamings); the context-extension functor
  delta (X(n) = X(n+1)) models abstraction; Gabbay-Pitts (same LICS) on
  nominal sets (Schanuel topos); Hofmann, "Semantical analysis of higher-
  order abstract syntax", LICS 1999 (presheaves, HOAS); Fiore-Hur 2010
  (second-order theories); Fiore-Turi 2001; Staton 2013 (algebraic
  theories with binding). All three equivalent in the sense that
  they give the SAME initial object for first-order binding.
Decidable: syntax equality and alpha equality decidable (structure
  recursion); equality of models is not.
Verdict: the theoretical justification for ABT: sorted ABTs with arities
  ARE the initial algebra, so ANY compositional (folds over the tree)
  analysis factors uniquely through the core: if the translation T_L
  hits each L-construct with exactly one core operator, every fold on L
  has a fold on the core. That is the actual content of the "universal"
  claim: universality of the INITIAL object, not of any particular
  semantics.

### 5.7 Sorted ABTs with arities as a universal syntax
Putting 4.6, 4.8, 5.6 together: a signature is Sigma = (Sorts, Ops,
arity: Ops -> (list of valences) x Sorts) with valence (s1..sk).s.
Every context-free language with a computable binding discipline
(variable occurrences resolve to binders statically) is the carrier of an
ABT signature (the concrete grammar's productions become operators,
non-terminals become sorts). For two languages L1, L2 the DISJOINT UNION
of signatures is again a signature; a "universal signature" can then be
taken as the colimit (open union) over all languages; this works because
signatures are closed under coproducts (cf. Swierstra a-la-carte,
5.4). So the "universal language" at the level of structure is merely an
OPEN SIGNATURE plus a set of language-neutral SORT ROLES (declaration,
reference, scope, call, loop, ...) that individual operators are tagged
with. Roles are the "mapping to IrKind" of code-model section 5. This is
formally a sorted-signature MORPHISM rho_L : Sigma_L -> Sigma_U, a
functor between free syntactic categories; the translation T_L is the
unique extension of rho_L by initiality (fold with operator renaming).
Total and computable, preserves arity and binding by construction.
Caveat: rho_L is NOT in general injective or surjective; the lossy case
(many L-ops -> one U-role) is where the `Other`/Opaque node and the
retained `ts_kind` come in.

### 5.8 Galois connections and abstract interpretation (a linter is an
abstraction)
Def: Cousot-Cousot, "Abstract interpretation: a unified lattice model
  for static analysis of programs by construction or approximation of
  fixpoints", POPL 1977; "Systematic design of program analysis
  frameworks", POPL 1979; "Abstract interpretation frameworks", JLC 1992.
  Concrete domain (C, <=), abstract (A, <=), alpha : C -> A, gamma :
  A -> C monotone with alpha(c) <= a  iff  c <= gamma(a): a Galois
  connection. Soundness: alpha(f(c)) <= f#(alpha(c)). Fixpoint transfer;
  widening/narrowing guarantee termination for infinite-height domains.
  Instances: Interval, polyhedra, octagons (Mine), pointer analysis,
  type inference (Cousot 1997 "Types as abstract interpretations").
  Astree (Blanchet et al., PLDI 2003), Infer, IKOS, Frama-C EVA, Clousot.
  Structural lint as abstract interpretation: the concrete semantics of
  "a program" is its set of executions; the TREE/GRAPH extracted is
  alpha(program), a finite approximation (forget values, keep names and
  nesting); a predicate on the tree is sound for the concrete property
  if it factors through that abstraction. "May" properties (call graph
  over-approximation) are alpha with gamma-above; "must" properties
  are the dual (under-approximation); a structural fact that depends on
  forgotten information has abstract value TOP = Unknown.
Decidable: abstract fixpoints are computable on finite-height or
  widened domains; the abstraction is never complete (alpha(f(c)) <
  f#(alpha(c)) typical): completeness of abstract interpretation is
  itself the subject of "completeness refinement" (Giacobazzi-Ranzato-
  Scozzari 2000, "Making abstract interpretations complete", JACM).
Verdict: the rigorous way to say "what frob computes is an abstraction":
  write A = (nodes, edges, resolution) as the abstract domain, state
  soundness of each lint for the property it claims, and let TOP be the
  third answer.

### 5.9 Other categorical structures one-liners
- Monoidal categories / string diagrams (Joyal-Street 1991; Selinger "A
  survey of graphical languages for monoidal categories", 2011): graph
  syntax for circuits, ZX, quantum, concurrency (Petri nets as free
  commutative monoidal categories, Meseguer-Montanari 1990). Verdict:
  shows a tree-with-binders model is incomplete for graph-shaped
  syntax unless a wire relation is allowed (4.17).
- Operads and PROPs: operations with many inputs/one output = trees;
  PROPs add many outputs: the algebra of ABT signatures is an operad
  (colored operad = multi-sorted signature). Verdict: matches "operator
  with arity" exactly; colored operads give the sort discipline.
- Institutions (Goguen-Burstall, "Institutions: abstract model theory for
  specification and programming", JACM 39, 1992): a universal framework
  of logics (signature, sentences, models, satisfaction) with a
  satisfaction condition under signature morphisms; heterogeneous
  specification (Hets, Mossakowski-Maeder-Luettich, TACAS 2007).
  Verdict: the closest existing "universal language of languages" at the
  semantic level; precisely a parametrization by signature morphisms;
  confirms the rho_L design, and that universality is by translation
  (comorphisms) between systems, not by a single super-system.
- Coalgebra (Rutten, "Universal coalgebra: a theory of systems", TCS
  249, 2000): behaviour of reactive systems; bisimulation as the
  notion of equality: appropriate for processes/objects, whereas
  syntax is initial. Verdict: syntax = initial algebra; run-time
  objects = final coalgebra; structural linter lives on the algebra side.

---------------------------------------------------------------------------
## 6. The decidability boundary

### 6.1 The undecidable core (all semantic)
- Rice (1953, "Classes of recursively enumerable sets and their
  decision problems", Trans. AMS 74): every non-trivial extensional
  property of the partial function computed by a program is undecidable.
  Any question of the form "does this code ever do X" (reach, terminate,
  call f, throw, write to the filesystem at runtime) is undecidable for
  Turing-complete L.
- Halting (Turing 1936); Church 1936 (equivalence/normal forms of
  lambda terms); Post 1946 (PCP); Hilbert's 10th (Matiyasevich 1970)
  for diophantine-flavored typing.
- Limits of typing: System F typability (Wells 1999); F<: subtyping
  (Pierce 1994); extensional MLTT type checking (Hofmann; Castellan et
  al. 2020); dependent type checking with general recursion/Type:Type is
  semi-decidable at best (conversion needs evaluation; Cayenne,
  Augustsson ICFP 1998, accepted nontermination of the type checker);
  Java generics subtyping (Grigore, "Java generics are Turing complete",
  POPL 2017); Scala/DOT; C++ templates Turing complete (Veldhuizen,
  "C++ templates are Turing complete", 2003); Haskell with
  UndecidableInstances; Rust trait solver (can overflow, recursion
  limit, ); TypeScript conditional types
  (reported Turing complete [verify]); Scala implicit search.
- Macro expansion: C++ templates above; Rust `macro_rules!` is Turing
  complete (recursion_limit as the guard); Scheme `syntax-rules`;
  Lisp `defmacro`; TeX (expansion = execution); the C preprocessor is
  NOT Turing complete (no recursion; Prosser/Kiselyov). Hence macro
  expansion is not total in general and structure AFTER expansion is
  Unknown without a fuel bound.
- Parsing itself: Perl 5 cannot be parsed statically (Kegler 2008
  "Perl and undecidability"; BEGIN blocks execute during parse),
  C++ (templates make disambiguation depend on instantiation), TeX,
  Raku. Context-free grammar ambiguity and equivalence are undecidable
  (Hopcroft-Ullman 1979), so "do these two grammars give the same
  structure" is undecidable; per-file parsing of a fixed grammar is
  fine.
- Static analysis: exact alias/points-to is undecidable (Landi 1992
  "Undecidability of static analysis", ACM LOPLAS; Ramalingam 1994 "The
  undecidability of aliasing", TOPLAS); context-sensitive data-
  dependence (Reps 2000, "Undecidability of context-sensitive data-
  dependence analysis", TOPLAS); exact dead-code/reachability.
- Exact call targets under first-class functions/dynamic dispatch/
  reflection: reduces to halting (the target of `f(x)` where f is
  computed is an arbitrary computable function of the input).

### 6.2 Decidable structural questions (on syntax plus a STATIC discipline)
1. Parsing a context-free (or deterministic/GLR/PEG/tree-sitter LR) grammar:
   O(n) to O(n^3); partial parse with ERROR nodes is total.
2. Alpha-equivalence, free variables, capture-avoiding substitution on
   ABTs: linear.
3. Lexical name resolution under a static binding discipline: decidable;
   with a scope graph, resolution = reachability over a finite labelled
   graph with a regular (or Dyck) path-language: polynomial
   (Neron et al. 2015; Creager-van Antwerpen 2022).
4. Reachability on a finite graph: NL-complete (Savitch: O(log^2 n)
   space; BFS linear time); over a call graph with CFL matching
   (context-sensitive reachability, Reps-Horwitz-Sagiv, POPL 1995
   "Precise interprocedural dataflow analysis via graph reachability";
   IFDS/IDE): cubic, still decidable. Pushdown-system reachability
   decidable (Bouajjani-Esparza-Maler, CONCUR 1997; Finkel-Willems-
   Wolper 1997).
5. Call-graph OVER-approximation: CHA (Dean-Grove-Chambers, ECOOP 1995),
   RTA (Bacon-Sweeney, OOPSLA 1996), VTA (Sundaresan et al. OOPSLA 2000),
   0-CFA (Shivers 1988 PhD, CMU "Control flow analysis in Scheme", PLDI
   1988; Heintze-McAllester, "On the cubic bottleneck in subtransitive
   CFA", 1997), Andersen's (1994 PhD) and Steensgaard's (POPL 1996)
   points-to, Class-based. All polynomial; k-CFA for functional
   languages is EXPTIME-complete for k >= 1 (Van Horn-Mairson, "Deciding
   kCFA is complete for EXPTIME", ICFP 2008); 0-CFA is PTIME-complete
   (Van Horn-Mairson 2007). Survey: Midtgaard, "Control-flow analysis of
   functional programs", ACM Computing Surveys 44(3), 2012; Smaragdakis-
   Balatsouras "Pointer analysis", FnT PL 2015.
6. Datalog/FO/MSO/FO+LFP queries on finite structures (4.10, 4.11): FO
   is AC0 data complexity; MSO on finite trees is linear data complexity
   (Courcelle for bounded treewidth; Thatcher-Wright 1968, Doner 1970:
   MSO on trees = tree automata), though non-elementary in the formula.
7. Dominators/CFG properties, cyclic dependency detection (SCC,
   Tarjan 1972), import cycles, visibility, layering, naming rules:
   linear.
8. Syntactic termination checks (structural recursion, size-change
   principle, Lee-Jones-Ben-Amram, POPL 2001; decidable though PSPACE-
   complete): a SOUND but incomplete termination test; decidable.
9. Syntactic effect-site detection (calls to a named API): decidable
   modulo resolution of the name.

### 6.3 What over-approximation buys (soundness regimes)
Let the concrete property be Q (program set -> bool) and the analysis a
function A returning an element of {No, Yes, Unknown}.
- MAY analysis: A returns Yes only if Q holds; No only if it surely does
  not; for the sound-over-approximate regime: No is trustworthy ("no
  path exists even in the over-approximation"), Yes means "maybe"
  (alarm). Used by call graphs: absence of an edge in the over-
  approximation is conclusive; presence is not.
- MUST analysis: dual, under-approximation: Yes trustworthy, No is
  "maybe not". Incorrectness logic (O'Hearn, "Incorrectness logic",
  POPL 2020): under-approximate reasoning, no false positives.
- Soundiness (Livshits et al., "In defense of soundiness: a manifesto",
  CACM 58(2), 2015): real tools are sound modulo explicitly listed
  unsound features (reflection, eval, native code, dynamic loading,
  exceptions); the manifesto asks the tool to LIST them. This is exactly
  what an adapter's capability matrix (code-model section 3, `Gap`) is.
- Soundness-completeness trade (Rice-compatible): the sets {Yes} and {No}
  decided by A are subsets of the true sets; the rest is Unknown; no
  total computable A can have {Unknown} empty for a non-trivial semantic
  Q (Rice). So Unknown is NECESSARY, not a defect.

### 6.4 Three-valued answers and Kleene logic
- Strong Kleene K3 (Kleene, "Introduction to metamathematics", 1952,
  section 64): truth values {F, U, T} ordered by INFORMATION (U below
  both F and T) and by truth (F < U < T). Connectives: not swaps T/F,
  fixes U; and = min, or = max (truth ordering). Monotone with respect to
  information ordering: refining an Unknown to a known value never
  flips a determinate answer. Properties: no tautologies from excluded
  middle (U or not U = U), so DO NOT treat "not Yes" as "No".
  Weak Kleene / Bochvar B3: U is infectious (any U argument gives U): the
  right semantics for "expression depends on an opaque sub-expression".
  Lukasiewicz L3 (implication differs). Belnap's four-valued logic
  FOUR (1977, "A useful four-valued logic"): adds Both (conflict) -
  useful when two adapters disagree (information lattice with join =
  union of evidence).
- Three-valued abstract interpretation and model checking: Bruns-
  Godefroid, "Model checking partial state spaces with 3-valued
  temporal logics", CAV 1999; Godefroid-Huth-Jagadeesan "Abstraction-
  based model checking using modal transition systems", CONCUR 2001;
  Larsen-Thomsen, modal transition systems, LICS 1988 (may/must
  transitions: the formal structure of "may call" vs "must call");
  Kripke structures with partial valuations; Sagiv-Reps-Wilhelm, "Parametric
  shape analysis via 3-valued logic", POPL 1999/TOPLAS 2002 (TVLA):
  the canonical use of K3 in static analysis, 1/2 as "unknown".
- Gradual/typed: `?` dynamic type; `any`/`unknown` in TypeScript,
  `Any` in Python typing, `_` holes in Agda/Lean (metavariables).
- Datalog with Unknown: model as two relations (may, must) with
  must <= may; query answer Yes iff must, No iff not may, else
  Unknown (exactly modal transition systems; also "possible and certain
  answers" for incomplete databases: Imielinski-Lipski 1984; Libkin
  2016 "SQL's three-valued logic and certain answers", ACM TODS 41).
  SQL itself uses K3 for NULL and its WHERE keeps only True rows.
Verdict: every edge in the structural graph carries a CONFIDENCE tag
  {must, may} (frob already has "imports with confidence"); every
  predicate returns K3; composition uses Kleene operators; "unknown" is
  produced exactly by (a) opaque nodes, (b) unresolved/dynamic names,
  (c) macro-expanded or generated code not available, (d) parse ERROR
  regions, (e) fuel exhaustion. Rule design: a lint fires on {Yes};
  suppressions/ratchets treat {Unknown} separately and report counts;
  never fold Unknown into No.

---------------------------------------------------------------------------
## 7. Prior art: universal and multi-language IRs, for STRUCTURE

For each: what it is, what it got right, what it got wrong or is
irrelevant for a structure linter.

### 7.1 LLVM IR (Lattner-Adve, CGO 2004, https://llvm.org/docs/LangRef.html)
SSA, typed, low-level; three forms (in-memory, bitcode, text). RIGHT: one
IR with a verifier, total structural invariants (dominance). WRONG for
structure: erases source structure (loops, scopes, names, modules);
"LLVM in reverse" is the OPPOSITE problem: LLVM goes down to the
machine, we go up to syntax. LLVM's type system is not enough to
reconstruct source types (opaque pointers since 15). Debug info
(DWARF metadata) is the retrofitted structure channel: spans, scopes,
types as METADATA on the side. Take: structure as a side channel
(attributes) attached to a minimal core, with a verifier that checks
well-formedness.

### 7.2 MLIR (Lattner et al., "MLIR: scaling compiler infrastructure for
domain-specific computation", CGO 2021, arXiv:2002.11054,
https://mlir.llvm.org/)
Dialects (namespaced op/type/attr sets), operations with operands,
results, attributes, regions (nested blocks with block arguments),
locations on every op, trait/interface mechanism, `--allow-unregistered-
dialect` (opaque ops are accepted and round-tripped). RIGHT: the only
production IR designed as an OPEN SIGNATURE: ops are data (name,
arity, regions), generic traversals and printing work on any dialect,
opaque (unregistered) ops are legal, and locations are mandatory. Binding via SSA values and symbol tables
(SymbolTable op trait, symbol references as attributes). That is a
nominal + ABT hybrid. Take: this is the nearest industrial analogue of
sorted ABT + Opaque + spans; operations nest through REGIONS (valence)
and symbol references are by name through scoped symbol tables.

### 7.3 WebAssembly and the Component Model (Haas et al., "Bringing the
web up to speed with WebAssembly", PLDI 2017; Rossberg et al., "Bringing
the web up to speed", CACM 2018; Rossberg, WebAssembly 2.0/3.0 spec;
https://github.com/WebAssembly/component-model)
Core Wasm: a small formally specified stack machine with structured
control, validated in linear time; the spec is mechanized (WasmCert,
Watt et al., FM 2021 / CPP 2019). Component model: WIT interface types
(record, variant, list, option, result, resource, own/borrow handles)
and a canonical ABI to bind modules compiled from different languages;
a language-neutral interface description for cross-language calls.
Take: for code-model section 6 (cross-language `binds`) the WIT type
grammar is a ready-made neutral `Type` lattice with resource ownership;
better than inventing `int|float|str|...|unknown` (consider aligning).
Weakness: interface only, not bodies.

### 7.4 GHC Core / FC: see 1.6. Take: Core Lint (verifier) discipline, plus
`Tick` (source-note) nodes which preserve spans through optimization;
negative: desugaring loses source-level structure.

### 7.5 Lean 4 kernel terms and Coq Gallina
See 1.16. Lean 4: Expr (bvar, fvar, mvar, sort, const, app, lam,
forallE, letE, lit, mdata, proj) plus a SEPARATE Syntax type for
surface macros ("syntax objects", hygienic, with info trees giving
source positions and elaboration state: `InfoTree` maps elaborated
terms back to syntax ranges: an explicit span/provenance side table).
Coq: Gallina term constr (Rel, Var, Evar, Sort, Cast, Prod, Lambda,
LetIn, App, Const, Ind, Construct, Case, Fix, CoFix, Proj, Int, Float,
Array) plus Vernacular and notations outside the kernel. Take: the
kernel/surface split; the info-tree (elab-to-syntax provenance
map); `mdata` as a generic annotation node.

### 7.6 GraalVM Truffle (Wuerthinger et al., "One VM to rule them all",
Onward! 2013; "Self-optimizing AST interpreters", DLS 2012;
https://www.graalvm.org/latest/graalvm-as-a-platform/language-implementation-framework/)
Each language has its OWN AST node classes (Node subclasses with
@Specialization); universal only via the Interop protocol (messages
such as read member, execute, isInstantiable) and SourceSection
(source spans) with instrumentation tags (StandardTags: StatementTag,
CallTag, RootTag, ExpressionTag, ...). Take: instrumentation TAGS are
language-neutral ROLES attached to language-specific nodes: exactly
the `ir_map` idea (IrKind as tag over ts_kind), proven at industrial
scale (debugger and profiler work on all Truffle languages through
tags). Lesson: universality at the ROLE and INTEROP boundary, not at the
node-class level.

### 7.7 tree-sitter (Brunsfeld; https://tree-sitter.github.io/)
Incremental GLR-ish LR parser generator; produces a CST with named and
anonymous nodes, FIELD names, byte/point ranges, ERROR/MISSING nodes
(error recovery), queries as S-expressions with captures and predicates
(#eq?, #match?), `node-types.json` (a machine-readable ABT-like arity/
sort table: each node kind's fields, children, subtypes/supertypes!).
Per-grammar `locals.scm` (scope/definition/reference captures: a tiny
scope-graph vocabulary: @local.scope, @local.definition,
@local.reference), `tags.scm` (symbol definitions/references for code
navigation, used by GitHub's old search-based navigation).
RIGHT: total (always returns a tree), incremental, 100+ grammars,
lossless (every byte covered). WRONG/absent for our purposes: no binding
(only the locals.scm hack), kind names are per-grammar and unstable, no
sorts beyond supertypes, no cross-language vocabulary, grammar
versions drift. Take: node-types.json IS an arity/sort table: the
adapter's rho_L : Sigma_L -> Sigma_U can be GENERATED/validated from it;
supertypes give sorts; fields give valence positions; locals.scm shows
a minimal binding annotation per grammar.

### 7.8 Semantic (GitHub; Rix, Thomson et al.;
https://github.com/github/semantic)
Haskell; tree-sitter parse -> per-language syntax types assembled from
"a la carte" functors (Data types a la carte, Swierstra 2008) ->
language-agnostic abstract interpretation (based on "Abstracting
definitional interpreters", Darais-Labich-Nguyen-Van Horn, ICFP 2017)
-> import graphs, call graphs, diffs, symbol tables, for Python, Ruby,
JavaScript/TypeScript, Go, PHP, Java, Haskell. Served github.com's
"Symbols" ... Stated lessons (Rix, Strange Loop 2017/ "Semantic
code" talks): the cost of per-language syntax types and the
difficulty of effect-handler-based evaluators; the open union of
functors is the right abstraction but compile times and
maintenance exploded; the repo was archived (reported 2024-2025
[verify]). Take: confirms the architecture (shared algebraic signature,
per-language injections, abstract interpretation) AND the failure mode:
trying to give SEMANTICS (interpretation) uniformly was too costly;
structural extraction (stack-graphs was the follow-up that
actually shipped) won.

### 7.9 Glean (Meta; https://glean.software/; Angle query language)
Fact store: schemas per language (cxx, hack, flow, java, python, rust...)
declared in Angle (a Datalog-like, typed, with `predicate` declarations and
derived predicates); facts are immutable, typed, content-addressed
in RocksDB-backed DBs; incrementality by DB STACKING (a diff DB on top of
a base); queries are logic programs. Indexers per language reuse the
compilers (clang, flow, javac). RIGHT: facts + Datalog; per-language
schemas with cross-language links in a shared "codemarkup" schema (an
abstraction layer: entities, locations, relations common to all
languages, derived from the per-language ones). Take: THE closest
architecture to code-model sections 6, 8: per-language facts plus a
derived shared predicate layer, incremental by stacking. Cost: heavy,
requires compiler-grade indexers.

### 7.10 CodeQL (Semmle, de Moor et al.; Avgustinov et al., "QL:
object-oriented queries on relational data", ECOOP 2016;
https://codeql.github.com/)
Per-language extractor -> relational database (dbscheme: tables for
AST nodes, expressions, statements, edges, plus control-flow and data-
flow layered in QL) -> QL (object-oriented Datalog with stratified
recursion, classes as predicates, abstract classes, overriding;
Datalog with types). Languages: C/C++, C#, Java/Kotlin, JS/TS, Python,
Go, Ruby, Swift, Rust. Shared libraries per language for DataFlow
(ParameterizedModule, "shared library" approach: a language-parametric
dataflow implementation parameterized over a signature, SSA, type
tracking, taint tracking: github/codeql/shared/dataflow). RIGHT:
per-language databases JOINED by shared parametric LIBRARIES (the
language provides a module satisfying a signature; the shared analysis is
instantiated); parameterized modules = functors over signatures.
WRONG for us: databases are heavyweight (must build the project); not
incremental at file granularity. Take: SHARE THE ANALYSIS, NOT THE
SCHEMA: universal rules written against a signature that each
language implements (this is a trait in Rust: the adapter trait).
Proves "per-language IR + shared analysis" is viable at scale.

### 7.11 Kythe (Google; https://kythe.io/docs/schema/)
Graph of NODES identified by a VName {signature, corpus, root, path,
language} and typed EDGES (defines/binding, ref, ref/call, childof,
param, typed, overrides, extends, completes...). Language-specific
indexers emit a protobuf entry stream; schema covers a ~language-neutral
vocabulary (record, sum, function, variable, package, anchor, doc, ...)
with per-language facets. RIGHT: explicit symbol ADDRESS (the VName is
the analogue of a symref), anchors = spans, edge kinds standardized.
Take: borrow edge vocabulary and the "anchor" concept (span-bound node
that refs/defines others).

### 7.12 SCIP and LSIF (Sourcegraph, https://github.com/sourcegraph/scip;
Microsoft LSIF, https://microsoft.github.io/language-server-protocol/
specifications/lsif/0.6.0/specification/)
Index = documents with OCCURRENCES (range, symbol string, symbol_roles
bitset: Definition, Import, WriteAccess, ReadAccess, Generated, Test,
ForwardDefinition), SymbolInformation (documentation, relationships:
is_implementation, is_reference, is_type_definition, is_definition),
symbol strings with a grammar `scheme manager package version descriptors`
(descriptor suffixes: / namespace, # type, . term, () method, [] type
param, ! macro). Protobuf, human-readable symbols (SCIP replaced LSIF's
opaque numeric vertex IDs, 4-10x smaller). RIGHT: symbol-string grammar
independent of language, role bitset, documentation attached;
descriptors encode the container kinds (namespace, type, term, method,
type-parameter, macro) = exactly code-model's container model. Take:
adopt compatible descriptor kinds; consider emitting SCIP as an
export so existing tooling reads frob's symbol graph.

### 7.13 srcML (Collard-Decker-Maletic, "srcML: an infrastructure for the
exploration, analysis, and manipulation of source code", ICSM 2011;
https://www.srcml.org/)
XML annotation of the ORIGINAL text (tags wrap source; whitespace and
comments preserved: round-trip exact); C, C++, C#, Java (and Objective-C);
XPath/XQuery as the query language; a shared tagset across the four
languages (function, call, block, decl_stmt, expr, name). RIGHT:
lossless; one tagset for related languages; XPath = tree queries.
WRONG: only four languages; no binding or resolution; tag vocabulary
fixed by hand; XML size. Take: lossless source retention and a
shared tagset within a language family (C-like) works; it does NOT
generalize across paradigms without Opaque.

### 7.14 Universal ASTs: Babelfish/bblfsh (source{d}; the project is
dormant since the company wound down, ~2020; https://github.com/bblfsh/bblfsh)
and UniAST (ByteDance/CloudWeGo ABCoder, "Universal AST specification",
https://github.com/cloudwego/abcoder [verify])
bblfsh: per-language drivers run in containers, parse with the
language's native parser, emit a "native AST", then an annotation
pass maps native node types to a UNIVERSAL ROLE set (Identifier,
Function, Declaration, Call, If, Loop, Block, Literal... 100+ roles) and
`internal_type`; the UAST is thus native tree + role tags (a lossless
tag-over-tree design); queried with XPath-like (libuast). WRONG
(by its own retrospective): drivers per-language heavyweight
(Docker); role taxonomy grew with no semantics; no binding or resolution;
project died (commercial, not technical, reasons chiefly, [verify]).
UniAST (ABCoder): a repo-level universal description (modules,
packages, files, functions, types, vars with dependencies by
identity) for LLM code understanding: a SYMBOL GRAPH not a full AST;
languages Go, Rust, Python, TS, Java (reported). Take: role-tagging
over native nodes (bblfsh) is the same pattern as Truffle tags;
symbol-graph level (UniAST/SCIP/Kythe) is the pragmatic cross-language
sweet spot, matching code-model section 2.

### 7.15 Unison (Chiusano-Bjarnason; https://www.unison-lang.org/docs/
the-big-idea/; "The Unison language", Unison Computing)
Code stored as a content-addressed database of ABTs: each definition's
hash is computed over its ABT with variable names erased (de Bruijn-like
canonical form) and references to other definitions replaced by THEIR
hashes; mutually recursive definitions hashed as a unit
(strongly connected component, with positions in the cycle); names are
metadata in a separate namespace mapping name -> hash (rename is a
metadata edit; no dependency breakage; no builds).
RIGHT: ABT with alpha-canonical hashing is a working industrial design;
separating identity (hash) from name; dependencies as hash edges give
semantic-change detection for free; type-directed search. Take: frob
digests today hash whitespace-collapsed TEXT (code-model section 2); an
ABT-based digest (alpha-normalized, comment-free, spans-free) would make
a rename of a local variable or reformat not alter body digest. Trade-off:
requires full tree for every language; for text-fallback languages keep
whitespace-collapsed digests. Note the one-way constraint: Unison can do
this because it controls the language; we cannot erase names whose
meaning is dynamic (Python attribute names).

### 7.16 Pandoc (MacFarlane; https://pandoc.org/; Text.Pandoc.Definition)
Document AST: Pandoc Meta Blocks; Block (Para, Header level attr inlines,
CodeBlock attr text, BulletList, Table, Div attr blocks, RawBlock format
text, ...), Inline (Str, Emph, Strong, Link attr inlines target, Code,
RawInline format text, Span attr inlines, Cite...). Readers (~40
input formats) -> AST -> Writers (~60 output formats), so N+M instead of
N*M converters. Extension points: Attr = (id, classes, key-value
pairs) on many nodes, RawBlock/RawInline = (format tag, uninterpreted text)
= an Opaque node carrying a language/format tag, `Div`/`Span` generic
containers; Lua filters over the AST; lossy by design (Pandoc says so:
the AST is the intersection-plus-extension of what most formats can do).
Take: the cleanest existing precedent for exactly the design we propose:
a SMALL common vocabulary, a generic `Attr` bag, and tagged RAW nodes
for what doesn't fit, with the N+M converter argument. Pandoc admits
lossiness and accepts it: so should frob.

### 7.17 Spoofax/Rascal/language workbenches
Spoofax (Kats-Visser, OOPSLA 2010): SDF3 syntax + NaBL/Statix name binding
and typing via scope graphs + Stratego/DynSem; Rascal (Klint-van der
Storm-Vinju, SCAM 2009); MPS (JetBrains projectional editing: ASTs ARE the
source); Xtext; Language workbench challenge. They solve "define a language
once, get IDE"; they give per-language binding specs in a DSL (NaBL).
Take: the binding discipline is declared DATA per language (NaBL rules /
locals.scm), not hand-written walkers; this reduces `walk`/`imports` in the
adapter to a declarative table plus a generic resolver.

### 7.18 Others one-liners
- JetBrains PSI, Roslyn syntax/semantic models, rust-analyzer HIR, Eclipse
  JDT, clang AST: per-language rich semantic ASTs; excellent but
  non-portable. Take: rust-analyzer's separation (CST rowan -> AST ->
  HIR with name resolution via DefMap, salsa incremental) is a model for
  the language-internal pipeline (code-model section 8).
- ast-grep / Comby / Semgrep (Semgrep generic AST "ast_generic" across
  30+ languages with `Other` constructs (OtherExpr) = Opaque nodes with a
  tag; Semgrep's ast_generic.ml is the closest open-source universal AST
  to the proposed IrKind, with `Other` escape hatches exactly as designed
  in code-model section 5; https://github.com/semgrep/semgrep, file
  semgrep-core/src/ast_generic [verify path]): Take: study ast_generic's
  `Other*` constructors and what had to be added over the years
  (class-like, decorators, pattern kinds, `DotAccess`, `ParenExpr`,
  `OtherExpr(string, any list)`).
- Infer (Facebook): SIL/HIL, per-frontend translation (Clang, javac,
  OCaml,...) into a small intermediate language `SIL` for separation-
  logic analysis: a successful "translate many frontends into one small
  IR for ANALYSIS". Verdict: confirms per-frontend total translation
  with fallback unknown instructions (`Unknown` expression).
- Soot/Jimple, WALA IR, Doop's fact format: ditto for JVM.
- Kotlin/Swift/Go SSA IRs (go/ssa, Swift SIL): per-language.
- OpenAPI/Protobuf/IDL/Thrift: neutral interface IDLs for cross-language
  binding (relevant to code-model section 6).
- LSP/Language Server Index Format: see 7.12.
- BAP/Ghidra P-code (binary lifting): universal low-level IRs for
  machine code, orthogonal.
- K and Redex/Ott (4.12): semantics frameworks.
- Boogie / Why3 / Viper (verification IRs: Leino 2008; Filliatre-Paskevich
  2013; Mueller-Schwerhoff-Summers 2016): intermediate verification
  languages that many front-ends (Dafny, Spec#, VCC, Chalice,
  Prusti, Creusot, Gobra) translate into; show the many-to-one pattern
  works for verification, again with per-frontend semantics encoding
  and "assume/havoc" as Unknown.
- Nuprl term structure (4.6) and Metamath (all math in a tiny substitution
  calculus; Megill) as precedents for a minimal universal syntax.

Section 7 verdict: successful systems share the pattern
(per-language extractor) + (small shared vocabulary of roles/edge kinds)
+ (opaque escape hatch with tag) + (spans everywhere) + (Datalog-ish
query layer) + (analysis written once against a signature). Failures
(Semantic, bblfsh) over-invested in uniform SEMANTICS or per-language
containers. Nobody shares the grammar, and nobody tried to.

---------------------------------------------------------------------------
## 8. Synthesis

### 8a. The smallest set of primitive forms for a universal STRUCTURE
calculus

Notation. U = the universal structural calculus ("Ustruct").

P1. SORTS and OPERATORS (sorted ABT signature).
    Sorts s in a set S (open; language families extend it). An operator
    o has arity ((s_1^1..s_1^k1).s_1, ..., (s_n^1..s_n^kn).s_n) s
    exactly as PFPL ch.1 valences: argument i is an ABSTRACTOR binding
    k_i variables of the listed sorts. Terms:
      t ::= x | o(a_1, .., a_n)        a_i ::= x_1..x_k . t
    Also allow list-sorted arguments (variadic: o(t*)) for sequences
    (blocks, parameter lists, concatenative programs) and optionally
    unordered collections (equation sets), both expressible as an
    operator family cons/nil or a bag sort.
    Rationale: sections 1.10, 4.6, 5.6 (initial algebra), 7.2 (MLIR ops
    with regions), 7.7 (node-types.json).

P2. NAMES (nominal atoms) with two scopes of use.
    (i) Bound names: atoms a, with alpha-equivalence = equality of
    abstractions (Gabbay-Pitts). Store as unique atom ids for
    identity, with a separate spelling for display. Digest by
    de Bruijn canonicalization.
    (ii) Global names: ABSOLUTE symbol paths (the symref), with kinds
    {namespace, type, term, method, macro, ...} (SCIP descriptors,
    Kythe VName, code-model section 2). A global name is NOT a binder
    but a key into the scope/definition relation.
    Rationale: 4.5, 4.9, 7.11, 7.12, 7.15.

P3. REFERENCE RESOLUTION as a RELATION with a K3 status.
    A relation Resolve(ref_occurrence, declaration) in a scope graph
    (Neron et al.): scopes, declaration nodes, reference nodes, labelled
    edges P (parent), I (import), M (module/member), with resolution =
    path in a regular language. Each Resolve edge carries status
    {Must, May, Unknown/Dynamic} and a confidence. It extends P1/P2
    because abstractors capture only tree-shaped lexical binding; modules,
    imports, inheritance, overloading, wildcards need a graph.
    Lexical abstractors in P1 are an OPTIMIZATION of P3 (a lexical binder
    is a scope with one declaration), so P1 and P3 must be consistent:
    the adapter may express ALL binding in P3 and treat P1's abstractors
    as a derived view.
    Rationale: 4.9, 7.8, 7.17.

P4. OPAQUE operator.
    opaque_L(tag, payload, t_1..t_n) with tag = (language, native kind),
    payload = uninterpreted bytes/text (e.g. the ts_kind plus slice),
    children = the sub-terms the adapter DID understand, with the
    arity "list of any sort", binding behaviour = none (treated as
    binding nothing, using everything free below it; sound for a
    may-analysis of free variables when children are scanned for
    names). Every analysis must give a defined (K3 Unknown) result on
    an opaque node; this is the formal home of `Other`, ERROR, macros
    unexpanded, generated code, language-specific attributes.
    Rationale: 7.2 (unregistered ops), 7.16 (RawBlock), 7.18 (Semgrep
    Other), 7.6.

P5. PROVENANCE (spans, trivia, attributes) as a total side function.
    prov : Node -> (file, byte-range, concrete-syntax pointer),
    attr : Node -> bag of (key, value) (visibility, async, mutability,
    usage grade/multiplicity, effect grade, decorators), attached
    comments/trivia. NOT part of identity/digest unless asked.
    Rationale: 7.1 (debug metadata), 7.5 (info trees), 7.6
    (SourceSection), 7.16 (Attr), 2.3/2.4 (grades), 7.13 (lossless).

That is five forms. Everything else is DERIVED:
  - Roles (Call, Loop, Branch, Decl, Import, Lambda, ...) = a map
    role : Operator -> Role (a morphism rho_L to the universal role
    signature, 5.7); not new syntax.
  - Call graph, public-API graph, dominator, effect-site relation =
    Datalog over P1-P5.
  - ANF, CPS, desugarings = derived views computed on demand.
  - Types = an attribute / child sort in P1 with Type-lattice, never
    required.
  - Evaluation order, linearity, ownership = attributes (P5).
  - Semantics (reduction): NOT in the core at all.
Compare to code-model section 5: IrKind is P1's role map; Name is P2/P3
without resolution; Other = P4; span = P5; MISSING: abstractors (binding
structure), resolution relation (P3), and status values (K3). These are
the three additions recommended in section 9.

Minimality argument (why not fewer):
 - Without abstractors/binding: cannot state alpha-invariant predicates
   (shadowing, unused variable, capture) universally; every adapter
   would re-implement scoping (v1's mistake).
 - Without the global-name key: cannot join across files or languages.
 - Without P3 graph: cannot represent imports/inheritance/modules.
 - Without Opaque: totality of T_L fails (Perl, macros, 2D languages).
 - Without provenance: lints cannot report, digests cannot be computed.
Why not more: reduction rules (semantics), types, evaluation order,
effects are undecidable-to-apply or language-specific; including them
destroys totality (Rice) and locality (Felleisen).

### 8b. The coverage theorem (what can honestly be proved)

Definitions.
 D1. A LANGUAGE ADAPTER is a tuple L = (Sigma_L, parse_L, bind_L, rho_L)
     where
       Sigma_L   is a finite sorted-ABT signature for L's concrete
                 syntax (e.g. generated from tree-sitter node-types.json
                 plus an Error operator);
       parse_L   : Bytes -> Tree(Sigma_L) is a TOTAL COMPUTABLE function
                 (partial parses produce Error subtrees; salvage);
       bind_L    : Tree(Sigma_L) -> ScopeGraph is a TOTAL COMPUTABLE
                 function, the declared static binding discipline: it
                 outputs declarations, references, scopes, labelled edges,
                 plus the set Dyn of reference occurrences whose
                 resolution depends on run-time information
                 (eval, reflection, dynamic scope, wildcard import of
                 non-static modules, macros not expanded...);
       rho_L     : Ops(Sigma_L) -> Ops(U) union {opaque} is a signature
                 morphism (renaming of operators to universal roles,
                 preserving arity where defined, mapping the rest to
                 opaque).
 D2. A STRUCTURAL PREDICATE over a structure M = (Nodes, child, next,
     label, scopes, decl, ref, resolve, span) is a sentence of
     FO+LFP (equivalently stratified Datalog with negation), or MSO on
     the tree plus the resolve relation, evaluated on a finite M. Call
     this class SP. Examples: "node x is a Call whose callee resolves to
     a declaration in module m", "Loop contains Call to a name in S",
     "symbol is reachable from public API through the static call
     relation", "import graph acyclic", "declaration unused" (no
     resolving reference).
 D3. T_L : Bytes -> Core is T_L(b) = fold_rho_L (parse_L b) with scope
     graph bind_L(parse_L b) attached and spans attached.
 D4. Truth values K3 = {Yes, No, Unknown} with Kleene connectives.
     For an SP formula phi, its three-valued evaluation [[phi]]_3 on a
     core structure with May/Must edges and opaque nodes: atoms over
     opaque nodes, Dyn references, ERROR regions evaluate to Unknown;
     all else classically; connectives strong Kleene; quantifiers as
     iterated and/or; LFP as the least fixpoint in the information
     ordering (monotone, so exists, computable in polynomial time).

THEOREM (structural coverage). For every language L with a computable
parse_L, a computable declared binding discipline bind_L and a signature
morphism rho_L (D1) there is a TOTAL COMPUTABLE translation T_L (D3)
into the universal core U such that for every file b and every
predicate phi in SP_L (the sentences over L's own structure M_L(b)
built from parse_L(b), bind_L(parse_L(b))), writing phi^rho for its
rho_L-translation:
 (1) Preservation/Reflection (exact part). If [[phi^rho]]_3 (T_L b)
     is Yes then M_L(b) |= phi, and if it is No then M_L(b) |/= phi,
     i.e. the three-valued core answer is sound: the core never answers
     Yes or No incorrectly about the SOURCE STRUCTURE. When T_L b
     has no opaque node, Dyn is empty and the parse is error-free (the
     "closed fragment") the answer is never Unknown and the core's
     answer is EXACTLY M_L(b) |= phi (preservation and reflection,
     iff).
 (2) Alpha-invariance. phi^rho evaluates identically on alpha-
     equivalent inputs (the core quotient by alpha).
 (3) Compositionality. T_L is a homomorphism of signatures (a fold), so
     T_L(C[t]) = rho(C)[T_L(t)] for contexts C: structure of a part
     does not depend on the whole: incremental recomputation per
     subtree is valid, modulo bind_L's scope-graph edges, which
     are file-local plus cross-file import edges.
 (4) Complexity. Evaluating phi^rho on T_L b is polynomial in |b|
     (data complexity PTIME for FO+LFP; AC0 for FO; exponential only in
     |phi| for MSO), terminating by construction.
 (5) Semantic predicates. For any semantic property Q that is non-trivial
     (Rice), there is no sound-and-complete total computable decision
     procedure over any such core; the three-valued evaluation of any
     syntactic over-approximation phi_Q of Q is sound for Q in the
     sense of may/must (No for may-analyses is conclusive) but is
     Unknown on the opaque/Dyn/error cases; the set of inputs with
     Unknown cannot be made empty uniformly (Rice) unless Q is
     syntactic.

Proof sketch.
 (1) Define the 3-valued interpretation by structural induction on phi
     using the information order. Every atom of phi^rho over a node
     without opaque/Dyn/error ancestors reads exactly the same relation
     as in M_L (because rho_L, parse_L, bind_L are the same data); by
     monotonicity of Kleene operators in the information ordering, if
     the three-valued value is T or F it equals the value obtained by
     ANY refinement of the Unknown atoms, in particular the true one.
     LFP: Kleene fixpoint iteration on a finite lattice of subsets of
     tuples under the information order converges (Knaster-Tarski plus
     finite domain).
 (2) alpha-equivalence is built into P2 (nominal atoms).
 (3) fold uniqueness from initiality (Goguen et al. 1977; Fiore-Plotkin-
     Turi 1999); scope-graph edges are local by construction (stack
     graphs: per-file partial paths composed at query time).
 (4) Immerman-Vardi / Abiteboul-Hull-Vianu complexity of FO+LFP and
     stratified Datalog on finite structures.
 (5) Rice 1953 applied to the set of programs whose semantics satisfy Q;
     a decision procedure that is sound and complete for every file
     would decide Q.
 The theorem is DELIBERATELY unambitious about what T_L means for
 behaviour: it is a theorem about structure only. For semantic
 preservation add the optional hypothesis that L has a mechanised
 semantics and T_L is the identity on the fragment (e.g. via CBPV/ANF
 desugaring); then preservation of semantic predicates holds only on
 that fragment (Felleisen 1991: otherwise no local translation exists).

What this theorem does NOT claim, honestly:
 - It does not claim bind_L is CORRECT for the real language; that is
   a per-language conformance obligation (fixtures; compare with the
   language's own tool, e.g. rustc name resolution, Python's symtable,
   tsc's binder). The theorem is relative to bind_L, the declared
   discipline. A wrong bind_L yields a wrong but still total, sound-
   w.r.t.-itself answer. This is the largest honest gap.
 - It does not claim parse_L matches the language's real grammar
   (tree-sitter grammars are approximations; Perl/C++/TeX parse depends
   on execution/templates); it claims totality with Error nodes.
 - It does not claim the translation is surjective or invertible;
   it is lossy by design, with provenance pointing back.
 - It is not a claim about every PL ever defined: languages with no
   computable parse or no static binding discipline fall in the opaque
   fragment entirely (Unknown for every non-trivial predicate), but
   T_L remains total.
 - Cross-language predicates (binds edges across Rust and TS) depend on
   additional declared interface data (WIT-like), outside the theorem.
 Proof-status note: this statement is mine, assembled from the cited
 results; it is a design-level theorem (the proof is routine) rather than
 a published theorem. The only nontrivial content is the K3 soundness
 (monotonicity) and the explicit hypothesis list.

Corollary (necessity of Unknown): Because of (5), a core that returns only
{Yes, No} for semantic predicates is either unsound or incomplete
everywhere; frob must keep Unknown in its public result type.

Corollary (trivialization): If one drops the structural predicate class
SP (so predicates may refer to the meaning of subterms), T_L can be
the constant "interpreter applied to source" map (U1), which is total and
semantics-preserving but preserves/reflects no structural predicate
other than "is a program". The structure-preservation hypothesis is what
makes U2 non-vacuous.

### 8c. Impossibility results that bound any stronger claim

I1. Rice 1953: no decision procedure for non-trivial semantic properties.
I2. Halting (Turing 1936) / Church 1936 (undecidable Entscheidungsproblem
    and lambda-conversion): no total decision procedure for
    termination or equality of programs in a Turing-complete core.
I3. Godel 1931 (second incompleteness) and Girard: a total (strongly
    normalizing) core cannot prove its own normalization or contain
    its own interpreter; so a core that is total (to keep all queries
    decidable) cannot be universal for languages with general
    recursion (Turner, "Total functional programming", JUCS 10(7),
    2004). Hence: the core must be a SYNTAX calculus without reduction.
I4. Felleisen 1991: expressive-power hierarchy; constructs such as
    first-class continuations, shared state, and exceptions are not
    local-macro-eliminable; a structure-AND-semantics-preserving local
    translation into a fixed small core does not exist for all L.
I5. Wells 1999 (System F typability), Pierce 1994 (F<: subtyping),
    Hofmann/Castellan et al. (extensional TT), Grigore 2017 (Java
    generics), Veldhuizen 2003 (C++ templates): type-level properties
    of mainstream languages are undecidable; the core cannot promise
    types.
I6. Landi 1992, Ramalingam 1994, Reps 2000: exact points-to/alias/
    data-dependence undecidable; call graphs are over-approximations only.
I7. Kegler 2008 (Perl), C++ templates and TeX: parsing itself can
    require execution: parse_L is not computable for them (so only
    approximate adapters); CFG ambiguity/equivalence undecidable (Hopcroft-
    Ullman 1979): structural equivalence of two grammars is undecidable.
I8. Macro/metaprogramming expansion termination is undecidable (Turing
    complete macro languages: Rust macro_rules, C++ templates, Scheme
    syntax-rules, TeX, Lisp); hence post-expansion structure requires
    fuel and may be Unknown.
I9. Huet-Lankford 1978 (TRS termination), Markov-Post (word problem):
    rewriting-based canonical forms are unavailable in general.
I10. Lincoln et al. 1992: full propositional linear logic undecidable;
    Mayr/ Leroux for reachability in Petri nets: nonelementary lower
    bounds (Cardoza-Lipton-Meyer 1976 EXPSPACE-hard; Czerwinski et al.
    2019 TOWER-hard; Leroux 2021 / Czerwinski-Orlikowski 2021
    Ackermann-complete): even decidable behavioural questions can be
    infeasible, so decidability of a question is not by itself
    enough.
I11. Statman 1979 (non-elementary
    cost of normalizing STLC) and Hindley-Milner DEXPTIME (Mairson 1990):
    inference can be decidable and unusable.
I12. Dynamic binding: eval, getattr, reflection, `import *` of runtime-
    computed modules, dynamic scope (Emacs Lisp, bash, early Lisps), and
    pi-calculus name mobility make name resolution depend on run-time
    state: bind_L cannot be total-and-exact; it can only be total-and-
    flagged (Dyn). Consequence of Rice.
I13. Coverage of "all languages" is not even well-defined: there is no
    effective enumeration of "all programming languages" other than via
    an effective presentation (parse_L as a program), and any universal
    translation T must receive that presentation as input: a single
    fixed T cannot be correct for a language it has never been told
    about (this is why the theorem quantifies over adapters, the Dedukti/
    institution pattern). Universality is by a uniform METHOD (generate
    T_L from L's presentation), not by one fixed map.
I14. No a priori sharing of the semantics of binding: hygienic macros
    (sets of scopes, Flatt 2016) vs syntactic closure vs C's textual
    macros are three incompatible binding models; no one discipline
    covers all (Dybvig; Clinger-Rees). So P3 must be a DECLARATIVE
    format into which per-language disciplines are compiled.

---------------------------------------------------------------------------
## 9. Implications for docs/design/code-model.md (concrete suggestions)

Section 2 (symrefs). Keep. Align container kinds with SCIP descriptors
 (namespace, type, term, method, type-parameter, macro) so a SCIP export
 is a trivial map (7.12). Symref = P2(ii) global name. Consider a
 content digest option based on alpha-canonical ABT hash (Unison 7.15)
 for languages with a complete adapter; keep text-based digests as
 fallback; make the digest facet declare its method.
Section 3 (adapters). Add to `LanguageAdapter` a `binding` member: a
 declarative scope-graph table (like NaBL/locals.scm: scope-introducing
 kinds, declaration kinds, reference kinds, import kinds) interpreted by
 ONE generic resolver (7.17); this is bind_L of D1. `ir_map` becomes the
 signature morphism rho_L, and should be validated against the grammar's
 node-types.json (a conformance test: every named node kind maps to a role
 or explicitly to Opaque, never silently dropped).
 The capability matrix doubles as the "soundiness list" (6.3).
Section 5 (IR). Add: (a) Abstractor/binding info to IrNode or an
 accompanying scope graph; (b) every Name reference carries
 Resolution = Resolved(decl, Must|May) | Ambiguous(cands) |
 Dynamic | Unresolved; (c) a three-valued query result type
 {Yes, No, Unknown}, with Unknown reasons enumerated (Opaque, Dynamic,
 ParseError, MacroUnexpanded, Fuel); (d) `Other` renamed Opaque and made
 to carry (lang, ts_kind, payload) plus recognized children; (e) a
 role set derived from Truffle tags / SCIP roles / bblfsh roles rather
 than ad hoc: statement, expression, call, declaration, definition,
 reference, loop, branch, jump, try, throw, async boundary, generic
 container.
Section 6 (cross-language). Consider WIT's type grammar as the neutral
 `Type` lattice (7.3) and keep `unknown` as K3 Unknown.
Section 8 (storage). A fact store of relations (node, child, label, scope,
 decl, ref, resolve, span) with Datalog evaluation (Ascent/Crepe/datafrog
 in Rust; Differential Dataflow for incrementality) fits 4.10 and 7.9.
Design rule distilled: universal rules are written against a
 SIGNATURE (trait) that each language implements (CodeQL's shared
 libraries, 7.10), not against a shared concrete schema; the IR holds
 the minimal common vocabulary and everything else is Opaque + Attr.

---------------------------------------------------------------------------
## 10. Checklist, subsumption, open questions

### 10.1 Coverage checklist (every requested item; [x] = covered in a numbered item)
1 Lambda cube and beyond:
 [x] untyped lambda 1.1   [x] STLC 1.2   [x] System F 1.4 (variants)
 [x] F-omega 1.5   [x] System Fc / GHC Core 1.6   [x] lambda-P 1.7
 [x] CoC 1.8   [x] CIC 1.11   [x] MLTT + universes 1.12
 [x] HoTT / cubical 1.13   [x] OTT 1.14   [x] PTS 1.10   [x] cube 1.9
 [x] "system-V" note 1.4   [x] Dedukti 1.15
2 Substructural and modal:
 [x] linear 2.1   [x] affine/relevant/ordered 2.2   [x] QTT 2.3
 [x] Granule/graded 2.4   [x] uniqueness 2.5   [x] Rust (Oxide, Stacked
 Borrows, RustBelt/lambda-Rust) 2.6   [x] session types, pi, Propositions
 as Sessions 2.7
3 Effects:
 [x] monads 3.1   [x] algebraic effects/handlers, Koka, Effekt, Eff,
 OCaml 5, Frank 3.2   [x] row effects, capabilities, graded monads 3.3
 [x] CBPV 3.4   [x] CPS, ANF 3.5   [x] SECD/CEK/Krivine 3.6
4 Other cores:
 [x] SKI/BCKW 4.1   [x] interaction nets/combinators, HVM/Kind 4.2
 [x] TM/register/mu-recursive 4.3   [x] explicit substitution 4.4
 [x] de Bruijn, locally nameless, HOAS, PHOAS, nominal, Unbound 4.5
 [x] ABT 4.6   [x] mechanized metatheory 4.7   [x] generic syntax 4.8
 [x] scope graphs 4.9   [x] Horn/resolution/Datalog 4.10
 [x] relational algebra 4.11   [x] TRS 4.12   [x] pi/CCS/join/actors
 4.13 (+2.7)   [x] concatenative 4.14   [x] array 4.15
 [x] SDF/Kahn/Lustre 4.16   [x] quantum/ZX 4.17   [x] CA/2D 4.18
 [x] reversible/Janus 4.19   [x] probabilistic 4.20
5 Categorical and algebraic:
 [x] CCC/Lambek 5.1   [x] Freyd/arrows 5.2   [x] Lawvere/monads 5.3
 [x] free monads 5.4   [x] bidirectional 5.5   [x] Galois/abstract
 interpretation 5.8   [x] initial algebra 5.6   [x] sorted ABT universal
 syntax 5.7   [x] Allais et al. 4.8   [x] PFPL ch. 1 4.6
6 Decidability: [x] Rice, halting, 6.1   [x] decidable structural 6.2
 [x] over-approximation 6.3   [x] Kleene three-valued 6.4
7 Prior art: [x] LLVM 7.1  [x] MLIR 7.2  [x] Wasm/component 7.3
 [x] GHC Core 7.4  [x] Lean/Coq 7.5  [x] Truffle 7.6  [x] tree-sitter 7.7
 [x] SCIP/LSIF 7.12  [x] Semantic 7.8  [x] Glean 7.9  [x] CodeQL 7.10
 [x] Kythe 7.11  [x] srcML 7.13  [x] bblfsh/UniAST 7.14  [x] Unison 7.15
 [x] Pandoc 7.16
Synthesis: [x] 8a primitives  [x] 8b theorem  [x] 8c impossibilities
Output items: [x] per-item verdicts  [x] considered-and-subsumed (10.2)

### 10.2 Considered and subsumed
- All eight cube systems, CIC, MLTT, cubical, OTT: SUBSUMED by PTS-style
  "sorts and rules as data" (1.10): structure-wise they are one ABT
  skeleton; the rules live outside the core.
- System F / F-omega / Fc / F<: : subsumed by sorted binders (term, type,
  kind, coercion namespaces) plus annotation.
- Linear/affine/relevant/ordered, QTT, graded, uniqueness, ownership:
  subsumed by binder/occurrence ATTRIBUTES (grades) in P5.
- Monads, algebraic effects, graded monads, row effects: subsumed by
  "operation site + handler scope" operators and an effect-grade
  attribute; derived relations (effect sites) are Datalog.
- CBPV, CPS, ANF, SECD/CEK/Krivine: DERIVED VIEWS/semantics, not stored.
- SKI, BCKW, combinatory logic: REJECTED as storage (binders lost);
  retained as proof of U1.
- Interaction nets/combinators, TM, register machines, mu-recursive, CA,
  Petri nets: execution substrates; REJECTED as structure carriers.
- Explicit substitution, de Bruijn/levels, locally nameless: REPRESENTATION
  details beneath P2 (used for digests).
- HOAS/PHOAS: a Rust-hostile encoding; REJECTED; nominal atoms chosen.
- Nominal sets: ADOPTED as the semantic basis of P2.
- ABT/universe of syntaxes/free monad/initial algebra: ADOPTED as the
  theory behind P1.
- Horn clauses, Datalog, relational algebra: ADOPTED as the QUERY layer
  (FO+LFP).
- TRS/K/Redex/Maude: optional semantics layer; REJECTED for the core.
- pi/CCS/join/actors: subsumed by Opaque + Dyn resolution status for
  mobile names; spawn/send/recv are operators.
- Concatenative: subsumed by variadic sequence sorts + Unknown arity.
- Array, SDF/Lustre, quantum/ZX, reversible, probabilistic: subsumed by
  operators plus attributes (implicit iteration, clock, linear wire,
  inverse, sample); graph-shaped ones (ZX, Petri, SDF) need an
  explicit edge relation (covered by P3-style relations or list+index).
- CCC, Freyd, Lawvere, institutions: provide VOCABULARY and justification
  (functorial semantics, signature morphisms); not implemented as such.
- Galois connections: ADOPTED as the soundness frame for lints.
- Kleene K3 (plus optionally Belnap FOUR): ADOPTED as the result type.
- Scope graphs / stack graphs / sets of scopes: ADOPTED (P3).
- LLVM/MLIR/Wasm/Lean/Coq/Core: design lessons (open signature, opaque ops,
  verifier, spans, kernel/surface split).
- Truffle tags, bblfsh roles, SCIP roles, Kythe edges: the ROLE vocabulary.
- Semantic, Glean, CodeQL, srcML, Unison, Pandoc: architecture lessons.
- Pending verification (no web access this session): all URLs and the
  [verify]-tagged claims.

### 10.3 Open questions for the owner
 Q1. "system-V": confirm it means the System F family (1.4).
 Q2. Is a (partial) alpha-canonical ABT digest wanted for languages with a
     complete adapter (7.15), or keep whitespace-collapsed text digests
     everywhere to keep acks stable?
 Q3. Should the core store the scope graph (P3) eagerly per file or
     compute on demand (stack-graph style partial paths)? Recommendation:
     per-file partial paths cached with the parse artifact.
 Q4. Which query language: Datalog (Ascent/Crepe in Rust) or a bespoke
     matcher (code-model section 5)? Theorem 8b(4) argues for Datalog
     semantics even if the surface syntax is a small matcher.
 Q5. Unknown policy for gates: should a lint fire on Unknown? Recommended
     no (report counts), but make it a per-rule setting.
 Q6. Should a verified tree-sitter node-types.json sweep be automated to
     check ir_map totality (all named nodes mapped)? Recommended yes.
