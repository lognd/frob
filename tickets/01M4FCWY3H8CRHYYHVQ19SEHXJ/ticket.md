+++
id = "01M4FCWY3H8CRHYYHVQ19SEHXJ"
title = "grmb research cycle R1: exhaustive cited audits of design practice, failure modes, languages, incompleteness and graph languages"
type = "docs"
category = "in-progress"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-09T03:56:43Z"
updated = "2026-10-10T01:40:09Z"
labels = ["grimble"]
scope = ["notes/research/grmb-*", "changelog.d/**"]

[[acceptance]]
text = "Given the five topics A-E, when R1 completes, then notes/research/grmb-r1-{practice,failure,languages,incompleteness,graphs}.md exist with a search log, coverage argument, findings with evidence strength, ADOPT/ADAPT/REJECT implications, candidate lint rules and a bibliography where every source was looked up or is marked [unverified]"
bound = true

[[acceptance]]
text = "Given the five notes, when the synthesis lands, then notes/research/grmb-r1-synthesis.md lists the design changes for grmb-planning.md, each with citations"
bound = true

[[acceptance]]
text = "Given topic F, when R1 completes, then notes/research/grmb-r1-ergonomics.md covers Rust, Zig and other languages' quality-of-life semantics with cited user evidence, lists predicted .grmb annoyances and gives a concrete mitigation for each"
bound = true
+++

# Research brief: grimble planning language, cycle R1 (exhaustive, cited)

Goal: ground the .grmb planning layer (docs/design/grmb-planning.md, ticket
~83H49E3) in evidence about software design practice. The language must
bind design to real code and tickets and CHECK it; every recommendation
you make must say what grimble could check and how.

Output: ONE file per researcher, notes/research/grmb-r1-<topic>.md, in the
worktree you are given (never the primary checkout). Structure:
1. Scope and search log (queries run, venues and corpora swept, what was
   excluded and why; the coverage argument for "exhaustive").
2. Findings, each: claim, evidence strength (empirical study / experience
   report / vendor doc / opinion), citation(s).
3. Implications for grmb: concrete grammar, rule or binding consequences,
   each tagged ADOPT / ADAPT / REJECT with a one-line reason.
4. Candidate lint rules: id placeholder, the anti-pattern prevented, the
   predicate over the model or the model-code binding, polarity
   (fires on presence / absence / mismatch), and the source.
5. Bibliography: full citations with URL or DOI. Every source must be
   fetched or looked up during this run (WebSearch/WebFetch, the arxiv
   tools via ToolSearch). An unverified citation carries [unverified];
   never invent a title, author, year or DOI. Prefer primary sources
   (papers, specs, official docs) over blogs; experience reports from
   named companies count.

Source credibility (owner requirement): cite only reputable sources and
grade each one. For every source record a credibility line: venue
(peer-reviewed ICSE/FSE/ICSA/ECSA/RE/MODELS/ESEM/TSE/TOSEM/IEEE Software,
standard body OMG/ISO/IEEE, or official vendor doc) and the authors'
practical standing: have they built or led design on large teams or large
products (name the company, product or system, with a source for that
claim)? Rank practitioner evidence from people who shipped at scale
(e.g. design-doc practice from Google engineers, architecture practice
from Amazon/Microsoft/Uber/Netflix principal engineers, SEI/industry
studies with named partner companies) above academic opinion with no
industrial validation, and both above anonymous blogs, which are excluded.
A claim supported only by weak sources is reported as weak, not dropped.

Exhaustive means: enumerate the field first (surveys, systematic
mapping studies, standards, tool lists), then drain it, then state what
remains unread and why it would not change the conclusions.

Rules: ASCII only, no emojis. No code changes. Do not commit; the
coordinator commits. Do not touch other researchers' files.

Topics (one per researcher):

A practice: what effective teams actually do in design, from first
  idea to shipped product: design docs and RFCs (Google, Uber, Amazon
  PR/FAQ, Rust RFCs, Python PEPs), ADRs, C4 and arc42, event storming,
  domain storytelling, DDD bounded contexts, use cases (Cockburn, Use
  Case 2.0), user story mapping, BDD/Gherkin, design reviews; empirical
  studies of modeling and documentation use in industry (Petre's UML in
  practice, MSR/ICSE/ICSA/ESEM studies), what is abandoned and why.

B failure: problems teams hit in design and architecture: architecture
  erosion and drift, architectural smells and anti-patterns (catalogs,
  detection tools: Arcan, Designite, ArchUnit, jQAssistant,
  dependency-cruiser, import-linter, Lattix/DSM), reflexion models and
  conformance checking, fitness functions, technical debt in
  architecture, distributed-system anti-patterns, microservice smells;
  turn each into a checkable predicate over a design model bound to code.

C languages: existing design/architecture/requirements languages and
  what happened to them: SysML v1/v2 (KerML textual), UML (+OCL),
  AADL, ArchiMate, BPMN, Structurizr DSL, LikeC4, PlantUML, Mermaid, D2,
  Gherkin, KAOS, i*, GRL (goal-oriented RE), Alloy, TLA+, Quint, P,
  FizzBee, Event-B, statecharts/SCXML/XState, Smithy/TypeSpec, Ballerina,
  Lingua Franca, CUE. For each: what it models, levels, binding to code,
  checking, adoption evidence, why it succeeded or failed.

D incompleteness: reasoning with incremental and incomplete models:
  partial models and uncertainty (Famelis/Chechik MAVO), modal transition
  systems, three-valued and abstraction-based checking, gradual typing,
  typed holes (Hazel), refinement (Event-B, refinement calculus),
  bidirectional transformations and round-tripping, cognitive dimensions
  of notations (Green and Petre), sketching and whiteboard studies
  (Cherubini et al.), how designers really think (Petre and van der
  Hoek, "Software Design Decoded"), premature commitment, viscosity.

E graphs: lessons from graph and modeling languages: UML metamodel and
  diagram kinds (which survive in practice), OCL, MOF/EMF, graph query
  (Cypher/GQL, Datalog/Souffle, CodeQL QL), graph rewriting, model
  traceability (Cleland-Huang, trace link recovery), model-based testing,
  variability modeling (feature models), sum types and exhaustiveness in
  design notations (algebraic data types in Alloy/TLA+/P, sealed
  hierarchies), and what a minimal, composable graph core for grmb
  should be.

F ergonomics: quality-of-life semantics that make languages pleasant:
  what Rust and Zig do (exhaustive match with good diagnostics, error
  messages with suggestions (rustc, Elm's error message work), editions
  for evolution, inference that stays local, comptime, error unions and
  `try`, labeled blocks, shadowing, formatter as law, LSP-first tooling),
  and what others teach (Elm, Gleam, Roc, Kotlin, Swift, TypeScript,
  Go's gofmt and simplicity, Python's readability, Nix/Dhall/CUE/HCL/
  Starlark for config-like languages, Pkl, KDL, TOML). Collect evidence
  of what users find annoying (language surveys: Rust annual survey,
  Stack Overflow, Go survey; usability studies at PLATEAU/CHI/OOPSLA/
  Onward; Cognitive Dimensions). Then predict what would be annoying in
  .grmb (verbosity of exhaustive handling, string vs identifier names,
  ceremony for small models, refactor cost when a variant is added, merge
  conflicts on shared files, error noise on incomplete models, learning
  curve for non-programmers such as PMs and designers) and give a
  concrete mitigation for each (defaults, inference, sugar, quick-fixes,
  `grimble fmt`, LSP code actions, progressive disclosure).
