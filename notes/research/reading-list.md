# Reading list: modern language design and the mathematics of languages

A learning path, not a bibliography. Read the books in order; the
papers are grouped by the chapter of the path they belong to. Every
item is a primary source or a standard text. Free online versions are
noted where they exist (links are to the authors' or publishers' pages;
verify before citing in the design).

## Path overview

| Stage | Goal | Main text |
|---|---|---|
| 0 | Fluency in types and operational semantics | Pierce, Types and Programming Languages |
| 1 | Syntax with binding, judgements, the whole zoo of features | Harper, Practical Foundations for Programming Languages (PFPL) |
| 2 | Proofs about languages and why a core calculus is enough | Pierce et al., Software Foundations (volumes 1-2) |
| 3 | The lambda cube, dependent types, proof assistants | Nederpelt and Geuvers, Type Theory and Formal Proof; then the HoTT book selectively |
| 4 | Semantics as mathematics: categories, denotations, effects | Awodey, Category Theory; Winskel, Formal Semantics; Moggi and Plotkin-Pretnar papers |
| 5 | Compilers and IRs: how structure survives translation | Appel, Modern Compiler Implementation in ML; the LLVM/MLIR/GHC Core papers |
| 6 | Program analysis: what is decidable and how to approximate | Nielson, Nielson and Hankin, Principles of Program Analysis; Cousot and Cousot |
| 7 | Breadth: the paradigms that break the mold | Van Roy and Haridi, Concepts, Techniques and Models of Computer Programming |

## Books

1. Benjamin C. Pierce, Types and Programming Languages (MIT Press, 2002).
   The standard first text: untyped and simply typed lambda calculus,
   subtyping, recursive types, System F, F-omega, with implementations.
   Companion: Advanced Topics in Types and Programming Languages (2005)
   for substructural types, dependent types, effect types, type inference.
   https://www.cis.upenn.edu/~bcpierce/tapl/
2. Robert Harper, Practical Foundations for Programming Languages, 2nd ed.
   (Cambridge, 2016). Chapter 1 defines abstract binding trees (ABTs),
   the syntax-with-binding model this design adopts as its universal
   syntax; the rest is a systematic tour of language features as
   judgements and rules. Preview edition free from the author.
   https://www.cs.cmu.edu/~rwh/pfpl/
3. Benjamin C. Pierce et al., Software Foundations, vol. 1 Logical
   Foundations and vol. 2 Programming Language Foundations (free, in Coq).
   Learn to mechanize the proofs from stages 0-1.
   https://softwarefoundations.cis.upenn.edu/
4. Rob Nederpelt and Herman Geuvers, Type Theory and Formal Proof: An
   Introduction (Cambridge, 2014). The lambda cube from simple types to
   the Calculus of Constructions, carefully, with the decidability
   results stated.
5. The Univalent Foundations Program, Homotopy Type Theory: Univalent
   Foundations of Mathematics (2013, free). Read Part I (chapters 1-2)
   for Martin-Lof type theory as a language; the rest is optional.
   https://homotopytypetheory.org/book/
6. Steve Awodey, Category Theory, 2nd ed. (Oxford, 2010). Enough category
   theory to read Lambek-Scott, Moggi and the algebraic-effects papers.
   Alternative gentler start: Bartosz Milewski, Category Theory for
   Programmers (free). https://github.com/hmemcpy/milewski-ctfp-pdf
7. Glynn Winskel, The Formal Semantics of Programming Languages (MIT
   Press, 1993). Operational, denotational and axiomatic semantics and
   how they relate; domain theory in the right dose.
8. Andrew W. Appel, Modern Compiler Implementation in ML (Cambridge,
   1998). Intermediate representations, lowering, and why structure is
   lost on the way down. Pair with Simon Peyton Jones, The Implementation
   of Functional Programming Languages (1987, free), for lazy languages.
   https://www.microsoft.com/en-us/research/publication/the-implementation-of-functional-programming-languages/
9. Flemming Nielson, Hanne Riis Nielson and Chris Hankin, Principles of
   Program Analysis (Springer, 1999, corrected 2005). Data-flow,
   constraint-based, abstract interpretation and type-and-effect
   systems: the theory of what a linter can and cannot know.
10. Peter Van Roy and Seif Haridi, Concepts, Techniques, and Models of
    Computer Programming (MIT Press, 2004). One kernel language
    extended paradigm by paradigm (declarative, concurrent, lazy, logic,
    relational, object, dataflow). The closest existing book to the
    "universal model" idea.
11. Neil D. Jones, Computability and Complexity From a Programming
    Perspective (MIT Press, 1997, free). Rice's theorem, the halting
    problem and decidability stated in programming-language terms; the
    source for the "fail loudly with Unknown" boundary.
    https://www.diku.dk/~neil/comp2book2007/book-whole.pdf
12. Shriram Krishnamurthi, Programming Languages: Application and
    Interpretation (free). A lighter, implementation-first tour useful
    for the breadth stage. https://www.plai.org/
13. Richard Bird and Philip Wadler, Introduction to Functional
    Programming (1988) and Simon Marlow's Parallel and Concurrent
    Programming in Haskell (2013) for the lazy and effectful practice
    behind stage 7 (optional).

## Papers by stage

### Stage 0-1: syntax, binding, core calculi
- Alonzo Church, "An Unsolvable Problem of Elementary Number Theory"
  (1936): the lambda calculus and the first undecidability result.
- Nicolaas de Bruijn, "Lambda calculus notation with nameless dummies"
  (1972): de Bruijn indices.
- Conor McBride and James McKinna, "Functional pearl: I am not a number,
  I am a free variable" (2004): locally nameless representation.
- Murdoch Gabbay and Andrew Pitts, "A New Approach to Abstract Syntax
  with Variable Binding" (2002): nominal techniques.
- Frank Pfenning and Conal Elliott, "Higher-Order Abstract Syntax" (1988);
  Adam Chlipala, "Parametric Higher-Order Abstract Syntax" (2008).
- Guillaume Allais, Robert Atkey, James Chapman, Conor McBride, James
  McKinna, "A type and scope safe universe of syntaxes with binding"
  (ICFP 2018): a generic, mechanized universe of syntaxes; the paper
  closest to "one syntax to hold all languages".
- Robert Harper, Furio Honsell, Gordon Plotkin, "A Framework for
  Defining Logics" (LF, 1993): syntax and judgements as a dependent
  type theory.
- Gordon Plotkin, "A Structural Approach to Operational Semantics"
  (1981, republished 2004): small-step semantics.
- Andrew Wright and Matthias Felleisen, "A Syntactic Approach to Type
  Soundness" (1994): progress and preservation.

### Stage 2-3: polymorphism, dependent types, the lambda cube
- Jean-Yves Girard, "Interpretation fonctionnelle et elimination des
  coupures" (1972) and John Reynolds, "Towards a theory of type
  structure" (1974): System F, discovered twice.
- Henk Barendregt, "Lambda calculi with types" (Handbook of Logic in
  Computer Science, 1992): the lambda cube and pure type systems.
- Thierry Coquand and Gerard Huet, "The Calculus of Constructions"
  (1988).
- Per Martin-Lof, "Intuitionistic Type Theory" (Bibliopolis, 1984).
- Joe Wells, "Typability and type checking in System F are equivalent
  and undecidable" (1999): the inference boundary.
- Luis Damas and Robin Milner, "Principal type-schemes for functional
  programs" (1982): the decidable fragment every ML uses.
- Martin Sulzmann, Manuel Chakravarty, Simon Peyton Jones, Kevin
  Donnelly, "System F with Type Equality Coercions" (2007): GHC Core
  (System Fc), the real-world universal core of a lazy language.
- Edwin Brady, "Idris 2: Quantitative Type Theory in Practice" (2021)
  and Robert Atkey, "Syntax and Semantics of Quantitative Type Theory"
  (2018).
- Cyril Cohen, Thierry Coquand, Simon Huber, Anders Mortberg, "Cubical
  Type Theory: a constructive interpretation of the univalence axiom"
  (2016) (optional).
- Jana Dunfield and Neel Krishnaswami, "Bidirectional Typing" (ACM
  Computing Surveys, 2021): the elaboration discipline modern checkers use.

### Stage 4: semantics, categories, effects
- Joachim Lambek and Philip Scott, Introduction to Higher Order
  Categorical Logic (1986): lambda calculus is the internal language of
  cartesian closed categories.
- Eugenio Moggi, "Notions of computation and monads" (1991).
- Philip Wadler, "Monads for functional programming" (1992) and
  "Propositions as Types" (CACM 2015): the Curry-Howard essay.
- Gordon Plotkin and John Power, "Algebraic Operations and Generic
  Effects" (2003); Gordon Plotkin and Matija Pretnar, "Handlers of
  Algebraic Effects" (2009).
- Paul Blain Levy, "Call-by-Push-Value: A Functional/Imperative
  Synthesis" (2003 book; 1999 paper): one calculus for strict and lazy.
- John Hughes, "Generalising Monads to Arrows" (2000); John Power and
  Hayo Thielecke, "Closed Freyd- and kappa-categories" (1999).
- Jean-Yves Girard, "Linear Logic" (1987); Philip Wadler, "Propositions
  as Sessions" (2012); Robin Milner, Communicating and Mobile Systems:
  the pi-Calculus (1999).
- Yves Lafont, "Interaction Combinators" (1997): the universal model
  behind HVM/Kind.
- Joseph Goguen, James Thatcher, Eric Wagner, Jesse Wright, "Initial
  Algebra Semantics and Continuous Algebras" (1977): syntax as the
  initial algebra, the formal basis for "structure first".

### Stage 5: compilers and intermediate representations
- Chris Lattner and Vikram Adve, "LLVM: A Compilation Framework for
  Lifelong Program Analysis and Transformation" (CGO 2004).
- Chris Lattner et al., "MLIR: Scaling Compiler Infrastructure for
  Domain Specific Computation" (CGO 2021): dialects as a family of IRs.
- Andreas Haas et al., "Bringing the Web up to Speed with WebAssembly"
  (PLDI 2017): a formally specified, mechanized low-level language.
- Cormac Flanagan, Amr Sabry, Bruce Duba, Matthias Felleisen, "The
  Essence of Compiling with Continuations" (1993): ANF versus CPS.
- Simon Peyton Jones and Andre Santos, "A transformation-based optimiser
  for Haskell" (1998): optimizing on a typed core.
- Andrew Kennedy, "Compiling with Continuations, Continued" (2007).
- Max Brunsfeld, tree-sitter (documentation and the "Tree-sitter: a new
  parsing system for programming tools" talk, 2018): incremental GLR
  parsing with error recovery, the front end this design uses.
- Paul Chiusano and Runar Bjarnason, Unison: "The Unison language"
  documentation on content-addressed code and abstract binding trees.

### Stage 6: analysis, decidability, approximation
- Henry Gordon Rice, "Classes of Recursively Enumerable Sets and Their
  Decision Problems" (1953): Rice's theorem.
- Patrick Cousot and Radhia Cousot, "Abstract Interpretation: A Unified
  Lattice Model for Static Analysis of Programs" (POPL 1977) and
  "Systematic Design of Program Analysis Frameworks" (POPL 1979).
- Olin Shivers, "Control-Flow Analysis of Higher-Order Languages" (PhD,
  1991): k-CFA and why call graphs for first-class functions are
  approximations.
- Thomas Reps, Susan Horwitz, Mooly Sagiv, "Precise Interprocedural
  Dataflow Analysis via Graph Reachability" (POPL 1995).
- Stephen Kleene, Introduction to Metamathematics (1952), section on
  three-valued logic (the Yes/No/Unknown lattice).
- Michael Sipser, Introduction to the Theory of Computation (3rd ed.,
  2012), chapters 4-5, if Jones (book 11) is too compressed.

### Stage 7: paradigms beyond the mainstream
- John Backus, "Can Programming Be Liberated from the von Neumann
  Style?" (Turing Award lecture, 1978): FP and function-level programming.
- Kenneth Iverson, "Notation as a Tool of Thought" (Turing Award
  lecture, 1980): array languages.
- Robert Kowalski, "Predicate Logic as Programming Language" (1974) and
  Alain Colmerauer and Philippe Roussel, "The birth of Prolog" (1993).
- Carl Hewitt, Peter Bishop, Richard Steiger, "A Universal Modular ACTOR
  Formalism for Artificial Intelligence" (1973); Gul Agha, Actors (1986).
- Gilles Kahn, "The Semantics of a Simple Language for Parallel
  Programming" (1974): Kahn process networks, the dataflow model.
- Nicolas Halbwachs, Paul Caspi, Pascal Raymond, Daniel Pilaud, "The
  synchronous data flow programming language LUSTRE" (1991).
- Peter Selinger and Benoit Valiron, "A lambda calculus for quantum
  computation with classical control" (2006).
- Brent Kerby, "The Theory of Concatenative Combinators" (2002, online):
  stack languages as combinator calculi.
- Eelco Dolstra, "The Purely Functional Software Deployment Model" (PhD,
  2006): Nix, configuration as a lazy functional language.
- Daniel Jackson, Software Abstractions (Alloy, 2nd ed., 2012) and
  Leslie Lamport, Specifying Systems (TLA+, 2002): specification
  languages as languages, relevant to grimble's model language.

## Courses and lecture notes (free)
- Oregon Programming Languages Summer School (OPLSS) lecture videos,
  yearly; start with the type theory and category theory tracks.
- Frank Pfenning, CMU 15-814 Types and Programming Languages, lecture
  notes. https://www.cs.cmu.edu/~fp/courses/15814-f22/
- Andrej Bauer, "How to implement dependent type theory" blog series
  and the PL Zoo (small interpreters for many calculi).
  http://plzoo.andrej.com/
- David Christiansen, "Checking Dependent Types with Normalization by
  Evaluation: A Tutorial" (2019).
- Xavier Leroy, College de France lectures on programming language
  semantics and verified compilation (slides in English).

## How this list feeds the design
- Stages 1 and 6 justify the two halves of the universal model: ABTs
  as the total syntactic layer (PFPL ch. 1, Allais et al.) and
  three-valued, abstract-interpretation-style answers for anything
  semantic (Cousot, Rice, Kleene).
- Stage 3 supplies the decidability table the model must respect:
  System F inference undecidable (Wells), dependent type checking
  decidable only under normalization, general recursion breaks it.
- Stage 7 is the test suite of paradigms the coverage theorem must
  survive; see notes/research/paradigms.md.
