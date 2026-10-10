# grmb R1, topic E: lessons from graph and modeling languages

Ticket ~19SEHXJ, researcher E. Date of run: 2026-10-09. Audience: the
author of docs/design/grmb-planning.md (ticket ~83H49E3).

Reading guide. Section 1 says what was searched and, honestly, what could
not be read. Section 2 holds the findings (each graded). Section 3 turns
them into ADOPT / ADAPT / REJECT consequences for grmb, including the
minimal graph core asked for by the brief. Section 4 lists candidate lint
rules. Section 5 is the bibliography with a credibility line per source.
Section 6 states what remains unread. Section 7 is the 2026-10-09
verification pass (web-enabled) and lists every change made to this file.

Citation keys are [n]; the bibliography is numbered in the same order as
the findings use them only loosely, so always resolve through section 5.

## 1. Scope and search log

### 1.1 Tooling limits of this run (read first)

- The WebSearch, WebFetch and arxiv tools named in the brief were NOT
  available: ToolSearch returned no matching deferred tool for "web",
  "fetch", "search" or "arxiv". Discovery and verification were done with
  `curl` / `urllib` against: the Crossref REST API (title and DOI
  lookup), the OpenAlex API (titles, venues, affiliations, abstracts),
  arxiv.org abstract pages, and vendor/standards pages fetched as HTML
  and stripped to text.
- Consequence 1: for most peer-reviewed papers only the ABSTRACT was
  obtainable (Springer, ACM, Wiley, Elsevier, IEEE, the OU repository,
  CACM and iso.org returned a bot challenge or HTTP 403). A finding that
  rests on an abstract says so ("abstract only"). No claim below reports a
  number or result that is not in a fetched abstract or fetched vendor
  page, except where tagged [background, unverified].
- Consequence 2: `[unverified]` in the bibliography means the work was
  found in a bibliographic index (so title, authors, venue, year, DOI are
  real) but nothing beyond the record was read.

### 1.2 Queries run (grouped by sub-topic of E)

About 95 lookups in total. Each group lists the corpus swept.

1. UML metamodel and which parts survive: Crossref + OpenAlex queries for
   "UML in practice", "conceptual models industrial", "UML open source",
   "How UML is used", "industrial adoption of MDE", "MDE practices in
   industry", "state of practice MDE", "embedded modeling survey",
   "UML diagram usage frequency"; OMG About pages for UML 2.5.1, OCL 2.4,
   MOF 2.5.1.
2. OCL / MOF / EMF: OpenAlex searches for OCL usage, OCL comprehension,
   OCL semantics; EMF EReference javadoc; Willink's retrospective.
3. Graph query (Cypher/GQL, Datalog/Souffle, CodeQL QL): Crossref for
   Cypher (SIGMOD 2018), GQL pattern matching (SIGMOD 2022), graph query
   foundations survey, PG-Schema; gqlstandards.org; Souffle site and
   rules page; CodeQL language reference; Glean and Kythe docs; code
   property graphs; Doop, bddbddb, codeQuest, Datalog survey;
   jQAssistant and ArchUnit docs.
4. Graph rewriting and model transformation: Ehrig algebraic graph
   transformation; Henshin; GROOVE; Czarnecki and Helsen; Mens and Van
   Gorp; two empirical studies of model transformation languages.
5. Traceability (Cleland-Huang school, link recovery): Gotel and
   Finkelstein; FOSE 2014 roadmap; Antoniol; Borg mapping; Rempel and
   Maeder; Maeder and Egyed; Rath; Guo; Maro; Fucci; Tian mapping study.
6. Model-based testing: Utting taxonomy; Dalal; Grieskamp (Spec
   Explorer at Microsoft); Alegroth practitioner interviews; Hughes
   QuickCheck experiences.
7. Variability / feature models: FODA; Batory; Benavides review; Berger
   survey, TSE study of Kconfig/CDL, MODELS 2014 cases; kernel Kconfig
   language doc.
8. Sum types and exhaustiveness in design notations and languages:
   Maranget; rustc dev guide; Rust reference (`non_exhaustive`); Zig
   langref; Swift SE-0192; Java JEP 409; Kotlin sealed classes; Alloy
   language reference and TOSEM paper; P manual and PLDI paper; Quint
   manual; AWS TLA+ and P practice papers.
9. Incomplete / inconsistent models and three-valued logic (overlap with
   topic D, kept only where it constrains the graph core): Egyed (two
   papers), Nuseibeh et al., Libkin (SQL 3VL), reflexion models.
10. Incremental queries over models: EMF-IncQuery, VIATRA Rete, Hawk,
    Differential Datalog (the last one did not resolve to the original
    paper; see section 6).

### 1.3 Coverage argument for "exhaustive"

The field was enumerated first as nine sub-topics (list above, mirroring
the topic-E brief line by line), then each was drained to: (a) at least
one survey, taxonomy or standard where one exists, (b) at least one
empirical industry study where one exists, (c) at least one primary
vendor or standard document for each tool-like item. Denominator for the
brief's explicit items: UML metamodel and diagrams; OCL; MOF/EMF; Cypher;
GQL; Datalog/Souffle; CodeQL QL; graph rewriting; traceability (including
recovery); model-based testing; feature models; sum types in Alloy,
TLA+, P and sealed hierarchies; minimal graph core = 12 items, 12
touched. TLA+ proper has no sum types (see F28); that statement rests on
the Quint manual describing sum types as an addition modelled on TLA+ and
on the AWS paper, not on a TLA+ manual page (not fetched).

Excluded and why: anonymous blogs and Medium posts (owner rule); vendor
marketing; LLM-for-UML papers (not about the language design question);
theses without a peer-reviewed counterpart; papers on a single tool
without evaluation.

The honest limit: this is a sweep of indexes plus abstracts plus vendor
docs, not a read of the full text of the 40-odd papers. Section 6 lists
the unread remainder and why it should not change the conclusions.

## 2. Findings

Evidence strength vocabulary: EMP = empirical study (survey, interview,
mining, experiment); EXP = experience report from a named organisation;
VEN = vendor / standard / official language documentation; OPN = opinion
or theory. "(abs)" = only the abstract was read.

### 2.1 What modelling practice looks like (UML and MDE)

F1. UML is used selectively, not wholesale. Petre interviewed 50
professional engineers in 50 companies and found 5 patterns of UML use;
the paper's framing is that evidence does not support UML as the "lingua
franca". EMP (abs). [1] Verified 2026-10-09 (secondary, [74] and [75]):
35 of 50 used no UML, 11 selectively, 3 for code generation, 1 retrofit,
0 wholehearted; selective users drew class (7), sequence (6), activity
(6), state machine (3), use case (1) diagrams.

F2. Where models exist in open source they are written at the start and
then stop being updated. Hebig et al. mined 10 percent of GitHub (1.24M
projects), found 21,316 UML diagrams in 3,295 projects, and report that
creating/updating "happens most often during a very short phase at the
project start"; 12 percent of the models had duplicates. EMP. [3]

F3. The motivation for models in open source is collaboration: 485
answers from 458 projects; collaboration is the most important
motivation; models benefit new contributors and contributors who do not
create models. EMP (abs). [4]

F4. MDE is applied to key parts of systems, rarely to generate whole
systems. A study of 450 practitioners plus 22 interviews. EMP (abs). [5]
Success and failure of MDE adoption are driven by organisational and
social factors more than technical ones; success needs a progressive and
iterative approach, transparent commitment, integration with existing
organisational processes and a clear business focus (three commercial
case studies). EMP (abs). [6]

F5. Which UML diagram kinds survive (GAP in the original run; CLOSED by
the 2026-10-09 pass, details in 7.2). Dobing and Parsons (full text, 171
usable responses, 2003-2004): used in two-thirds or more of projects:
class 73 percent, use case diagram 51, sequence 50, use case narrative
44; collaboration least used and most redundant; use case diagram rated
least useful for new information. EMP. [7] Akdur et al. (627 embedded
engineers): sequence and state machine most popular. EMP (abs). [76]
Langer et al. (121 open models, full text): classes 100 percent, use
cases 47, interactions 39, activities 4th, state machines last; 73
percent of models use at most 3 language units. EMP. [75] Consensus:
structure and sequence views survive everywhere; state machines only in
reactive/embedded work; use case and communication diagrams add little.

F6. UML separates its abstract syntax from its notation: OMG ships the
abstract-syntax metamodel and a distinct "Diagram Interchange Metamodel"
as separate normative artifacts (UML 2.5.1). VEN. [9]

### 2.2 OCL, MOF, EMF

F7. MOF 2.5.1 "is based on a simplification of the UML2 class modeling
capabilities" and adds identifiers, a generic tag capability and
reflective operations. VEN. [11]

F8. EMF's reference metamodel distinguishes containment references from
other references and gives the container side explicit well-formedness
constraints (the Ecore annotation names `SingleContainer`,
`ConsistentOpposite`, `ConsistentKeys`). VEN (javadoc of EReference). [13]
So an element has at most one container: the containment structure is a
tree laid over a general graph.

F9. OCL, the OMG constraint language, is regarded by its most active
tool implementer as "fatally flawed from the outset" in the OCL 2.0
specification (imprecise draft adopted), yet "remains the language of
choice for specifying model constraints"; he proposes an OCL 3.0.
OPN by a practitioner-implementer (abs). [12] No empirical study of OCL
usage or comprehension was retrieved (searches returned only metric and
generation papers). The OCL evidence base here is therefore weak: one
informed retrospective.

F10. Consistency rules over design models can be checked incrementally
at edit time: Egyed's approach re-evaluates consistency after a change in
1.4 ms on average, on 34 models of up to 162,237 elements and 24 rule
types, by observing which model elements a rule reads; rules may be
written in any language. EMP (abs). [14] His companion paper integrates
the checker with IBM Rational Rose, adds choices for fixing an
inconsistency, and evaluates on 48 case studies. EMP (abs). [15]

F11. Teams tolerate inconsistent models in practice; the argument of
Nuseibeh et al. is that inconsistency should be managed ("made
respectable"), not forbidden, and that practitioners tolerate it; the
framework is based on experience in large-scale projects. OPN/EXP
(abstract via search snippets of the AMiner-hosted PDF, 2026-10-09). [16] Egyed's abstract
agrees from the tooling side: "Even if engineers are willing to tolerate
inconsistencies, they are better off knowing about their existence."
EMP (abs). [14]

### 2.3 Model transformation and graph rewriting

F12. Model-transformation approaches differ along a feature model of
design choices (Czarnecki and Helsen: a classification framework given
as a feature model, with a few major categories). OPN/taxonomy (abs). [17]
Graph transformation is one category and has a mature theory (typed
attributed graphs, node-type inheritance, double-pushout rewriting) in
Ehrig et al. (book not read). OPN (theory) [21][22]. GROOVE and Henshin
are the long-lived tools (title level). [23][24]

F13. The claimed advantages of dedicated transformation languages are
mostly unsubstantiated. A systematic literature review of 58
publications grouped claims into 14 categories and concluded there is
insufficient evidence for claimed advantages and disadvantages. EMP
(SLR, abs). [19] A follow-up interview study with 56 participants from
research and industry found that general-purpose expressiveness,
domain-specific capability and tooling dominate opinions. EMP (abs). [20]

### 2.4 Graph query languages and Datalog

F14. Property graph versus edge-labelled graph, graph patterns versus
navigational (path) expressions, and the evaluation semantics (what a
path match means) are the three axes of modern graph query languages, and
the choice of semantics changes complexity. EMP/survey (abs). [25]

F15. GQL is now an ISO standard: ISO/IEC 39075:2024, published
2024-04-17 per the standards committee site. VEN. [28] Cypher's design
is documented in a SIGMOD paper by Neo4j and university authors. [26]
GQL pattern matching and SQL/PGQ share a pattern language. [27] Schema
support was limited in GQL version 1; PG-Schema proposes node/edge types
with multi-inheritance and key constraints for the second version.
EMP/theory (abs). [29]

F16. Practical architecture checking has already been built on graph
queries: jQAssistant stores a code graph in Neo4j and expresses rules in
Cypher, with groups, concepts (derived facts), constraints (violations),
severity, rule dependencies, parameters, and baseline management; ArchUnit
instead expresses rules as ordinary unit tests over a code structure
imported from bytecode, with composable predicates and ignore/priority.
VEN (doc tables of contents and overview). [30][31] Both separate "a
derived concept" from "a rule that fails".

F17. Datalog is the dominant substrate for program-analysis queries.
Souffle is a Datalog synthesis tool for static analysis [32][33]; its rule semantics require
that rules with negation be stratifiable, forbid circular negation, and
state that "negated literals do not bind variables". VEN [33] CodeQL's QL
compiles to Datalog yet offers classes and methods "reinterpreted in
logical terms (classes are logical properties describing sets of values,
subclassing is implication)", and has been used for analyses that "scale
to millions of lines of code". EXP/EMP (abs) [34]; the CodeQL doc
describes QL as "a declarative, object-oriented query language optimized
for hierarchical data structures, in particular databases representing
software artifacts". VEN [35] Code property graphs merge AST, CFG and PDG
in one graph database and model vulnerability templates as traversals;
the authors found 18 previously unknown Linux kernel vulnerabilities.
EMP (abs). [36]

F18. Two industrial code-fact systems show the shape of a long-lived
code graph. Glean (Meta): facts about code, typed schemas, facts form a
DAG and are deduplicated by the storage backend, derived facts by rules
in the Datalog-like language Angle, designed to be deployed at scale.
VEN. [37] Kythe: every node must carry a `node/kind` fact "to participate
in the rest of the schema"; edge kinds are namespaced; the schema
document is itself part of the test suite ("the graphs provided are the
graphs that are actually output"). VEN. [38]

F19. Three-valued evaluation is the accepted way to work over incomplete
data. Libkin shows SQL's three-valued logic can be repaired so that
answers are classified as certainly true, certainly false or unknown,
with a certainty guarantee. EMP/theory (abs). [39] This is the same
three-way split that GRL's polarity table uses (grl-spec 7.2).

F20. Live queries over models need incremental matching: EMF-IncQuery
(live model queries), VIATRA's Rete-based incremental pattern matching and
Hawk model indexing are the tooling line. [40][41] The VIATRA abstract
(read 2026-10-09) confirms the mechanism: an incremental engine "explicitly
stores existing matches" and maintains them under model change by an
adaptation of RETE networks. EMP (abs). [41] EMF-IncQuery and Hawk remain
title-only.

### 2.5 Traceability

F21. Traceability is valued and rarely maintained. The FOSE 2014 roadmap
says it is "often conducted in an ad-hoc, after-the-fact manner" so its
benefits "are not always fully realized". OPN (expert roadmap, abs). [42]
Completeness matters: across 24 medium to large open-source projects,
more complete requirements traceability significantly lowers the defect
rate for three of four studied activities (Poisson regression). EMP (abs).
[43]

F22. Links decay and are costly. In six open-source projects only ~60
percent of commits were linked to an issue; a classifier recommends
missing issue tags at 96 percent recall and only 33 percent precision.
EMP (abs). [44] A mapping study of 63 studies finds change management the
most-supported activity, and creating and maintaining links "the main
cost"; it calls for stronger industrial evidence. EMP (mapping, abs).
[45] An industry-academia report from a large telecom: the requirement to
test links were missing and that blocked the quality work; a "cautionary
tale". EXP (abs). [46] Recovery by information retrieval works on the
premise that programmers use meaningful names for program items (TSE
2002). EMP (abs). [47]

### 2.6 Model-based testing

F23 (MBT). MBT derives tests from models of the system under test and/or
its environment; the Utting taxonomy classifies approaches by model,
test selection, generation, execution. OPN/taxonomy (abs). [48] Large
industrial uses exist: combinatorial test generation on systems with
millions of lines of code at Bellcore (four case studies, tooling and
methods). EXP (abs). [49] Microsoft's Windows protocol documentation
program used model-based testing ("a success story"); [50] is title-only,
but the STVR journal paper by the same team (abstract read 2026-10-09)
states that "MBT works and that it scales, provided it is accompanied by
sound tool support and clear methodological guidance". EXP (abs). [77] [50] Adoption is sparse, and the reasons are mostly non-technical:
17 MBT experts gave 23 best-practice guidelines for adopting, using or
abandoning MBT with graphical models. EMP (abs). [51]

### 2.7 Variability and feature models

F24. Industrial variability models differ from academic ones. The study of
128 models in 12 open-source projects written in Kconfig and CDL
"challenge[s] assumptions about size and complexity of variability models
made in academic papers" and finds requirements "not commonly considered
in academic techniques". EMP (abs). [52] A practitioner questionnaire
covers application scenarios, notations, tools, model scale and
challenges. EMP (abs). [53] The kernel's own Kconfig language shows what
industry needed: `depends on` visibility, `select`/`imply`, defaults,
tristate values. VEN. [54]

F25. Automated analysis of feature models is a mature topic (Benavides
review; Batory's feature-model-as-grammar-plus-propositional-formula
result; FODA 1990 as origin). Titles only. [55][56][57] The standard
analyses (void model, dead feature, false optional, redundant constraint)
are background knowledge from that literature, [background, unverified].

### 2.8 Sum types, exhaustiveness and closed variant sets

F26. Exhaustiveness and redundancy are one problem. Maranget's algorithm
detects both useless clauses and non-exhaustive matches and was
integrated in the OCaml compiler. EMP/theory (abs). [58] rustc applies
the same "usefulness" check to match, let, let-else and function
arguments: it detects unreachable branches and ensures exhaustiveness.
VEN. [59]

F27. Mature languages give two escape hatches with different guarantees.
Rust: `non_exhaustive` marks that a type or variant "may have more fields
or variants added in the future". VEN. [60] Zig: a non-exhaustive enum has
a trailing `_` prong, and "with a `_` prong the compiler errors if all the
known tag names are not handled". VEN. [61] Swift: `@unknown default`
matches any value but "the compiler will produce a warning if all known
elements of the enum have not already been matched", chosen as a warning
"so that adding new elements to the enum remains a source-compatible
change"; in the first rollout the diagnostic for omitting it was an
error and was relaxed to a warning because "the rollout plan turned out
to be a little too aggressive". VEN (language evolution proposal). [62]
Java sealed classes (JEP 409) let the author list permitted subclasses so
that "code written to test whether an instance ... remains exhaustive",
and state the goal of supporting "exhaustive analysis of patterns". VEN.
[63] Kotlin's `when` over a sealed class is checked exhaustively without
`else`. VEN. [64]

F28. Design notations vary in how they treat closed alternatives. Alloy:
`abstract sig` "is constrained to hold only those elements that belong to
the signatures that extend it"; extension signatures are disjoint; and
"if it has no extensions, the abstract keyword is likely an indication
that the model is incomplete" (the reference itself treats that as a
smell). `in` signatures are overlapping subsets. VEN. [65][66] P has
enums, tuples and named tuples, maps/sets/seqs, and events; no tagged
union type in the datatype manual; handlers are per state with `on E do`,
`defer`, `ignore` clauses. VEN. [67][68] Quint adds sum types
(`type T = L1(T1) | ... | Ln(Tn)`) with a `match` eliminator and an RFC
for row-polymorphic sum types. VEN. [69] I found no manual statement
that P checks handler completeness at compile time; treat it as not
established.

F29. Formal design notations have real industrial standing at named
companies. Amazon engineers describe using TLA+ "to prevent serious but
subtle bugs from reaching production". EXP. [70] A 2025 CACM paper by AWS
authors describes systems correctness practices including lightweight
formal and semi-formal methods (abstract only; P is the language of one
of the authors' earlier work at Microsoft [68]). EXP (abs). [71]

## 3. Implications for grmb

Notation: each item has a tag, a one-line reason, and "Check:" saying what
grimble could check and how. I = implication number.

### 3.1 The minimal composable graph core

Proposal (I1). The model is ONE typed property graph with three closed
vocabularies and derived relations in a stratified fragment:

- Node(id, kind, level, attrs): kind is a closed sum type in Rust
  (the existing keyword table is the source); level is derived from kind
  (system/actor -> requirements, goal -> requirement_spec, scenario ->
  system_spec, impl -> design) as in the planning brief.
- Edge(src, label, dst): label is a closed enum of about a dozen
  structural labels: contains, refines, requires, performs
  (actor -> step), outcome (step -> variant), arm (scenario site ->
  variant -> next), includes, realizes, implements, verifies, flows_to,
  and `binds` (entity -> selector -> code symbol; the only edge with
  Must/May status because it crosses into code). Each label has a
  signature (allowed source kinds, target kinds, multiplicity), which is
  the MOF/PG-Schema idea at minimum size.
- Containment is a tree over the graph: every entity has at most one
  container (EMF SingleContainer) and the qualified name is the path
  through containers; all other edges are cross references.
- Variant sets are first-class: VariantSet(owner), Variant(set, name,
  payload contract?), Match site with arms; exhaustiveness is a set
  difference (see I6).
- Derived relations are Datalog-style, stratified: S0 declared facts;
  S1 binding (selectors resolve to code); S2 verified (evidence passes);
  S3 obligations (negation over S0..S2); S4 rollups (counts). Negation
  only over lower strata; recursion only positive (reachability of
  `requires`, `includes`, `contains`).

Tag: ADOPT. Reason: this is the common denominator of Kythe (kind fact
plus labelled edges), Glean (typed facts plus derived rules), MOF/EMF
(typed class graph with containment), PG-Schema (types with
inheritance) and Souffle (stratified negation); it adds no feature that
grmb-spec does not already imply (scope graph, Must/May edges, no new
type system). [11][13][29][33][37][38]
Check: MDL006 generalises to "edge signature violation" (wrong source or
target kind or multiplicity), computed from the label table; MDL for
"entity with two containers" and "containment cycle"; a compile-time
stratification check on every derived relation and GRL rule (circular
negation is an error, as in Souffle).

### 3.2 Language-shape consequences

I2. ADOPT: keep the constraint language bounded and terminating (GRL:
no recursion, `within N`), NOT an OCL-like general expression language.
Reason: the only retrievable practitioner assessment of OCL calls the
specification fatally flawed while conceding no alternative displaced it
[12]; GRL's finite non-recursive form is what lets Egyed-style incremental
re-checking work [14] and what makes cost classes printable.
Check: `grimble rule check` prints the cost class; a rule that is not
stratifiable or not bounded is a compile error.

I3. ADAPT: incremental evaluation with read-sets. For LSP-first checking,
record per (rule, binding) the set of model elements read, and re-run
only rules whose read-set intersects a change. Egyed reports 1.4 ms
average re-check on models up to 162k elements by exactly this idea [14];
GRL's finite structure makes read-sets precise. Reason: adapt, not adopt,
because Egyed observes rule behaviour at run time while GRL can derive
read-sets statically from the rule text.
Check: a conformance test that edits one entity and asserts that the set
of re-evaluated rules equals the statically computed dependents.

I4. ADOPT: separate abstract model from rendering, as UML separates its
abstract syntax from diagram interchange [9]. Mermaid output is derived
(planning brief section 7) and never read back. Check: `grimble graph
--mermaid` is a pure function of the model digest (golden test).

I5. REJECT: a user-facing graph-rewrite or transformation language.
Reason: no verified evidence it pays off (SLR of 58 papers finds claims
unsubstantiated [19]; interviews say expressiveness and tooling dominate
[20]), and grmb's transformations are a closed set: `frob plan
--from-design`, renames (`renamed_from`) and quick-fix edits. ADAPT only
the discipline from graph transformation theory for the fixes: a `fix`
should be a LOCAL rewrite (delete/add a small subgraph) with a negative
application condition, so applying it cannot create a new finding of the
same rule [21][22]. Check: for each rule with a `fix`, a golden test that
the fixed model produces zero findings for that rule (GRL already makes
examples tests; this adds the "fix is idempotent and removes the finding"
assertion).

### 3.3 Variant handling and exhaustiveness (the planning layer's core)

I6. ADOPT: exhaustiveness as a flat set difference, no nested patterns.
Arms name a variant (and optionally bind its payload); the check is
`outcomes(step) minus arms(site)`. Reason: Maranget's general algorithm
is needed only for nested patterns [58]; flat variants reduce it to set
difference, which makes the diagnostic trivially explainable and
incremental. Check: MDL "non-exhaustive match" (absence polarity, P-),
"redundant arm" (arm repeats a covered variant: Maranget's useless
clause), "arm names a variant the step does not declare" (Error).

I7. ADAPT: give `_` the Swift/Zig semantics, and add a second spelling.
The planning brief makes a wildcard accepted-but-Warn. The evidence
suggests two distinct constructs: (a) `else` (Rust wildcard): matches
everything, hides future variants, always Warn; (b) `unknown` (Swift
`@unknown default` / Zig `_` prong): REQUIRES every currently known
variant to be handled, matches future ones, and when a variant is added
later it produces a WARN (not an Error) at that site, so adding a
variant is source-compatible across files owned by other people. Reason:
Swift made exactly that choice, and softened an initial error to a
warning because the rollout was too aggressive [62]; Zig errors if known
tags are unhandled even with `_` [61]; Rust's `non_exhaustive` is the
declaration-side equivalent [60]. This also answers the "refactor cost
and merge conflicts when a variant is added" worry: the owner of the
variant set decides, per set, whether downstream matches may use
`unknown`. Check: variant sets carry `closed` (default; adding a variant
is an Error in every plain match) or `open` (Rust `non_exhaustive`:
downstream matches must use `unknown` or `else`; a plain match over an
open set is an Error). `unknown` arm that omits a known variant: Error.
Variant added since the last lock and not yet listed at an `unknown`
site: Warn (mismatch against `grimble.lock`).

I8. ADOPT: distinguish "alternatives that need all-of realization" from
"alternatives where one suffices". Feature-model groups (mandatory /
optional / or / xor) and Alloy's extends (disjoint) versus in
(overlapping) show that "a set of children" is ambiguous. In the planning
brief a `goal` block reads like a Rust enum, but the first example
(`place_order`, `track_order`, `browse_items` for a customer) is a set of
capabilities that must ALL be realized, while the nested example
(`guest; account;`) is a set of alternatives. Proposal: default group
kind `all` (every leaf needs a realizing scenario); `one_of { ... }` for
alternatives (at least one leaf realized, and exactly one if declared
`exclusive`); the checker reports the group kind it assumed. Reason: this
removes the ambiguity "KAOS OR-refinement vs Rust enum" at no cost to
the common case. Check: unrealized leaf of an `all` group (Advisory
obligation); `one_of` group with zero realized leaves (Advisory);
`one_of` group with two realized leaves and `exclusive` (Error). (sources: F24, F25, F28: [52][55][65][66])

I9. ADOPT with a boundary rule: choose "goal variant" versus "scenario
arm" by the discriminant. A variant that is chosen by an INPUT (which
user intent, which actor role: guest versus account) is variability and
belongs in the goal tree; a variant that is chosen by an OUTCOME of a
step (declined, timeout) is behaviour and belongs in a scenario arm.
Derived from the contrast between feature-model variability [52][55] and
sum-typed outcomes [58][62]; this answers the planning brief's open
question 8.4, but it is my synthesis (OPN), not an empirical finding.
Check: a scenario whose `realizes` target is a goal variant AND whose
arms re-enumerate sibling variants of that goal is flagged "variant
duplicated as arm" (Advisory); a goal variant set with exactly one
realizing scenario that contains a top-level match on an actor attribute
is flagged likewise.

I10. ADAPT: use the empty-abstract smell. Alloy's own reference states
an abstract signature with no extensions "is likely an indication that the
model is incomplete" [66]. Same predicate for grmb: a variant set with no
variants, an `actor` that performs no step, a goal block with no leaves,
a step used by no scenario. Check: absence polarity, Advisory, and
`unresolved when` semantics for models marked `draft`.

I11. REJECT: generic payload types and a new type system. P gets by with
enums, tuples and events [67]; Alloy models structure with signatures and
relations only [65]. Payloads stay `contract` entities bound to code
types. Check: arm payload binds only if the variant declares a contract
(MDL: arm binds payload of a payload-less variant is an Error).

### 3.4 Query, binding and traceability

I12. ADAPT, do not adopt, GQL/Cypher: GRL stays the query layer.
Reason: Cypher/GQL need a database and a declared semantic choice for
paths (walk, trail, simple path) which changes complexity [25]; the
code-graph tools that did adopt Cypher (jQAssistant) bundle Neo4j [30].
Take over only: the concept/constraint split (a named derived relation
versus a rule that fails), group and severity, and baselines [30] (GRL
`def`, `rule`, severity, and grimble-ratchet already do this). Make
`reaches ... within N` and `requires*` closure semantics explicit as SET
reachability (no path enumeration), written in the grl-spec. Check: a
doc test that every closure verb names its semantics.

I13. ADOPT: kinds are mandatory and checked on every node, as in Kythe
("node/kind ... is the one fact every node must have") [38]; the schema
doc contains executable examples (Kythe: "the graphs provided are the
graphs that are actually output") [38] which matches GRL's "examples
are tests". Check: the catalog generator fails if an entity kind has no
doc example, and if an example does not produce the shown findings.

I14. ADOPT: links are derived and checked, not hand-maintained.
Evidence: only 60 percent of commits carry issue links; recovery gives 33
percent precision; link maintenance is the main cost; a telecom study
found missing links blocked the quality work [44][45][46]. grmb already
makes the binding a relation (selectors) and the ticket link a single
source of truth (`implements`). Add completeness as a first-class
metric: for each level, the ratio of entities that are bound, verified
and implemented. Rempel and Maeder show completeness predicts defect rate
[43]. Check: `grimble status` prints per-level completeness, and a
ratchet rule (Advisory, Pn) fires when a level's completeness falls
below the locked value.

I15. ADAPT: name-similarity recovery as a SUGGESTION only. Antoniol's
premise (identifiers carry domain names) [47] supports an LSP quick fix
"unbound impl: candidate symbols" ranked by name similarity; the 33
percent precision [44] says never auto-bind. Check: the fix is marked
not machine-applicable; a test asserts `grimble` never writes a binding
without an explicit user action.

I16. ADOPT: per-arm test obligation instead of test generation. MBT
generation has sparse adoption for non-technical reasons [51], so grmb
should not generate tests. Scenario arms are the structural coverage
units that MBT taxonomies use (test selection by model coverage) [48];
check only that each arm has bound evidence (`verified_by`) or an
explicit exception with a ticket. Dalal and Grieskamp show model-derived
tests at industrial scale [49][50]; the cost there was the model upkeep,
which is exactly what binding to code reduces. Check: per-arm coverage in
`grimble graph --json` obligations; rule "arm without evidence".

I17. ADAPT: treat incompleteness as three-valued, severity by lifecycle.
Libkin's certainly-true/false/unknown [39], Nuseibeh's managed
inconsistency [16] and Egyed's "better to know" [14] together imply: a
model under construction should produce Unresolved/Advisory obligations,
never hard failures, until an entity is declared `ready`; only
binding-contradiction (`bound` yet the selector resolves to nothing)
fails. Check: GRL polarity table already gives this; add a `draft`
attribute on goals/scenarios that downgrades obligations of that entity
to Unresolved, and a finding if `draft` outlives its ticket (stale
marker).

### 3.5 Adoption and survival

I18. ADOPT: every level independently useful and checkable. Evidence:
MDE is applied to key parts, not whole systems [5]; adoption succeeds
when progressive, iterative and integrated with existing process [6];
UML use is selective [1]. grmb should allow a model with only goals, or
only impl blocks, with no error for the absent levels (the absent level
is an Advisory obligation at most). Check: a conformance fixture per
level subset that must parse and check clean of Errors.

I19. ADOPT: tie model survival to code change. Models are written at the
project start and then abandoned [3]; reflexion-model work was designed
around exactly that drift [72]. grmb's counter is the binding relation.
Check: "stale design entity" (mismatch polarity): the bound code changed
in k commits since the entity's own span last changed, with k a knob
(see E12 in section 4).

I20. ADOPT: render for readers who do not edit. Models help new
contributors and non-authors [4]; `grimble status` (design tree with
bound/verified counts) and mermaid output serve them. Check: status JSON
is stable (`grimble.graph/1` schema) and covered by a golden file.

## 4. Candidate lint rules

Id placeholders are E-nn; the coordinator will assign MDL/PLN ids.
Polarity: P+ fires on presence, P- on absence, Pm on mismatch, Pn on a
count, Pc on a closure property. "New" means not already in the planning
brief section 4/5.

| Id | Anti-pattern | Predicate over model / binding | Polarity | Source | New |
|---|---|---|---|---|---|
| E-01 | Non-exhaustive match | exists variant v in outcomes(step) with no arm v and no `else`/`unknown` at the site | P- | [58][59][61][62] | no |
| E-02 | Redundant arm | arm v at a site where v is already covered by an earlier arm | P+ | [58][59] | yes |
| E-03 | Arm for a foreign variant | arm v where v not in outcomes(step) | P+ (Error) | [58] | yes |
| E-04 | Wildcard hides variants | `else` arm present while outcomes(step) has >= 1 variant not otherwise listed | P+ (Warn) | [59][62] | partly |
| E-05 | `unknown` arm incomplete | `unknown` arm present and some known variant has no arm | P- (Error) | [61][62] | yes |
| E-06 | `unknown` arm stale | variant added since lock and absent at an `unknown` site | Pm (Warn) | [62] | yes |
| E-07 | Plain match over an open set | variant set declared `open`, site has neither `else` nor `unknown` | P- (Error) | [60] | yes |
| E-08 | Closed set grew silently | variant set `closed`, variants differ from lock, some site has no arm | Pm | [60][62] | yes |
| E-09 | Empty container | variant set with no variants; goal block with no leaves; actor performing no step | P- (Advisory) | [66] | yes |
| E-10 | Dead step | step declared, referenced by no scenario | P- (Advisory) | [66] | yes |
| E-11 | Unrealized leaf in an `all` group | leaf of group kind `all` with no realizing scenario | P- (Advisory obligation) | [52][65] | no (group kind new) |
| E-12 | Empty `one_of` | `one_of` group with zero realized leaves | P- | [55][65] | yes |
| E-13 | Exclusive violated | `exclusive` `one_of` with >= 2 realized leaves | P+ (Error) | [65] | yes |
| E-14 | Redundant `requires` | edge a requires c where a requires b and b requires* c already hold | P+ (Advisory) | [55][56] | yes |
| E-15 | Variant duplicated as arm | scenario realizing goal variant g has arms that re-enumerate siblings of g | Pm (Advisory) | I9 (derived) | yes |
| E-16 | Edge signature violation | edge label L from kind K1 to K2 not in the label's signature, or multiplicity broken | P+ (Error) | [11][29] | yes (generalises MDL006) |
| E-17 | Two containers / containment cycle | entity with >1 container, or contains-closure cycle | P+ (Error) | [13] | yes |
| E-18 | Unstratifiable derived relation | negation inside a recursive component of the derived-relation graph | P+ (compile error) | [33] | yes |
| E-19 | Level completeness regression | completeness(level) < locked value | Pn (Advisory ratchet) | [43] | yes |
| E-20 | Arm without evidence | non-ok arm of a scenario with no bound `verified_by` and no exception | P- | [48][49] | partly (P4) |
| E-21 | Payload mismatch | arm binds payload but variant declares none, or contract unresolved | P+ (Error) | [67] | yes |
| E-22 | Overbroad binding | impl selector matches more than K symbols, or one symbol is bound by more than K impls | Pn (Advisory) | [44] (precision matters), [72] | yes |
| E-23 | Stale design entity | bound code changed in >= k commits since the entity's span last changed | Pm (Advisory) | [3][72] | yes |
| E-24 | Draft outlives its ticket | entity `draft` while its implementing ticket is done/closed | Pm | [14][16] | yes |
| E-25 | Fix not idempotent | rule `fix` applied to its own example leaves findings of that rule | test-time | [21] | yes (conformance, not a user rule) |
| E-26 | Code change outside any design entity | commit on bound code by a ticket whose `implements` list is empty | Pm (Advisory) | [44] (only 60 percent linked) | yes (frob side) |
| E-27 | Closure without declared semantics | a closure verb in a rule lacking set/path semantics in the catalog | P- (catalog build error) | [25] | yes |

## 5. Bibliography and credibility

Format per entry: citation. URL or DOI. Credibility line: venue class,
authors' practical standing (only what was verified in this run), and
read depth. Ranking rule applied: practitioners at scale > academic with
industrial validation > academic only; anonymous blogs excluded (none
used).

[1] Petre, M. "UML in practice." Proc. 35th ICSE, 2013.
    DOI 10.1109/ICSE.2013.6606618.  Peer-reviewed, ICSE. Author:
    Open University, Centre for Research in Computing (OpenAlex
    affiliation); the study is 50 interviews in 50 companies, so the
    evidence is breadth over practitioners, not the author shipping a
    product. pp. 722-731. Read: abstract; counts verified secondarily via
    [74] and [75] (PDF 403/404).

[2] Storrle, H. "How are conceptual models used in industrial software
    development? A descriptive survey." Proc. EASE 2017.
    DOI 10.1145/3084226.3084256. Peer-reviewed, EASE, pp. 160-169.
    Author at QAware GmbH (industry), per the SE/SWM 2019 extended
    abstract (DOI 10.18420/se2019-26), read in full 2026-10-09. Content:
    usage SCENARIOS (communication and cognition top: 70-79 percent
    often/always), NOT diagram kinds. Not a source for F5.

[3] Hebig, R., Quang, T. H., Chaudron, M., Robles, G. "The quest for open source projects that use UML: mining
    GitHub." Proc. MODELS 2016. DOI 10.1145/2976767.2976778.
    Peer-reviewed, MODELS. Mining of 1.24M projects (a sample of 10
    percent of GitHub); empirical, no industrial team claim. The author
    list in Crossref shows four names; the OpenAlex first-three display
    is Hebig, Quang, Chaudron, Robles. Read: abstract.

[4] Ho-Quang, T., Hebig, R., Robles, G., Chaudron, M. R. V.
    "Practices and perceptions of UML use in open source projects."
    Proc. ICSE-SEIP 2017. DOI 10.1109/ICSE-SEIP.2017.28.
    Peer-reviewed, ICSE SEIP track (industry-practice track). Survey of
    485 contributors. Read: abstract.

[5] Whittle, J., Hutchinson, J., Rouncefield, M. "The state of practice
    in model-driven engineering." IEEE Software, 2013.
    DOI 10.1109/MS.2013.65. Peer-reviewed practitioner-facing journal.
    Lancaster University authors; survey of 450 practitioners plus 22
    interviews. Read: abstract.

[6] Hutchinson, J., Rouncefield, M., Whittle, J. "Model-driven
    engineering practices in industry." Proc. ICSE 2011.
    DOI 10.1145/1985793.1985882. Peer-reviewed, ICSE. Three commercial
    organisations studied by interview. Also cited: Hutchinson, Whittle,
    Rouncefield, Kristoffersen, "Empirical assessment of MDE in
    industry", ICSE 2011, DOI 10.1145/1985793.1985858 (abstract read:
    twelve-month qualitative study of technical, organisational and
    social factors). Read: abstracts.

[7] Dobing, B., Parsons, J. "How UML is used." Communications of the
    ACM 49(5), 2006, pp. 109-113. DOI 10.1145/1125944.1125949.
    CACM. Academic authors (affiliations not checked); survey
    distributed with OMG support; 171 usable + 11 responses. Read: FULL
    TEXT (PDF course mirror, 2026-10-09). Medium-strong; dated (UML
    1.5).

[8] (unused; numbering kept stable)

[9] Object Management Group. "Unified Modeling Language (UML) 2.5.1."
    https://www.omg.org/spec/UML/2.5.1/About-UML . Standard body OMG.
    Read: About page listing normative artifacts (abstract syntax, primitive
    types, standard profile, Diagram Interchange metamodel); the
    specification text was not read.

[10] Object Management Group. "Object Constraint Language 2.4", Feb 2014.
    https://www.omg.org/spec/OCL/2.4/About-OCL . Standard body OMG. Read:
    About page only (aligned with UML 2.4.1 and MOF 2.4.1).

[11] Object Management Group. "Meta Object Facility (MOF) 2.5.1."
    https://www.omg.org/spec/MOF/2.5.1/About-MOF . Standard body OMG.
    Read: About page (scope statement quoted in F7).

[12] Willink, E. D. "Reflections on OCL 2." Journal of Object Technology,
    2020. DOI 10.5381/jot.2020.19.3.a17. Peer-reviewed JOT.
    Author affiliation in index: Willink Transformations Ltd. Standing
    CONFIRMED: Eclipse MDT OCL committer from 2009 and project lead from
    June 2010 (Eclipse mdt/mdt-ocl mailing-list archives, found
    2026-10-09); current role not checked. Opinion by the tool's lead
    implementer. Read: abstract.

[13] Eclipse Modeling Framework, EReference interface javadoc (EMF
    2.9.0). https://download.eclipse.org/modeling/emf/emf/javadoc/2.9.0/org/eclipse/emf/ecore/EReference.html
    Official vendor/project doc. Read: member list and the constraint
    annotation names.

[14] Egyed, A. "Automatically detecting and tracking inconsistencies in
    software design models." IEEE TSE, 2011.
    DOI 10.1109/TSE.2010.38. Peer-reviewed TSE. Evaluated on 34 models
    up to 162,237 elements. Industrial deployment is claimed only through
    [15]. Read: abstract.

[15] Egyed, A. "Fixing inconsistencies in UML design models." Proc. ICSE
    2007. DOI 10.1109/ICSE.2007.38. Peer-reviewed ICSE. Tool integrated
    into IBM Rational Rose; 48 case studies. Read: abstract.

[16] Nuseibeh, B., Easterbrook, S., Russo, A. "Making inconsistency
    respectable in software development." Journal of Systems and
    Software, 2001. DOI 10.1016/S0164-1212(01)00036-X.
    Peer-reviewed JSS 58, pp. 171-180. Read: abstract-level content via
    search snippets of the AMiner PDF (2026-10-09).

[17] Czarnecki, K., Helsen, S. "Feature-based survey of model
    transformation approaches." IBM Systems Journal, 2006.
    DOI 10.1147/sj.453.0621. Peer-reviewed; IBM-published venue; authors'
    affiliations not verified in this run. Read: abstract.

[18] Mens, T., Van Gorp, P. "A taxonomy of model transformation."
    Electronic Notes in Theoretical Computer Science, 2006.
    DOI 10.1016/j.entcs.2005.10.021. Peer-reviewed workshop proceedings.
    [unverified] (title and venue only).

[19] Gotz, S., Tichy, M., Groner, R. "Claimed advantages and
    disadvantages of (dedicated) model transformation languages: a
    systematic literature review." Software and Systems Modeling, 2020.
    DOI 10.1007/s10270-020-00815-4. Peer-reviewed SoSyM. SLR of 58
    publications. Read: abstract.

[20] Hoppner, S., Haas, Y., Tichy, M. "Advantages and disadvantages of
    (dedicated) model transformation languages." Empirical Software
    Engineering, 2022. DOI 10.1007/s10664-022-10194-7. Peer-reviewed
    EMSE. Interview study, 56 participants from research and industry.
    Read: abstract.

[21] Ehrig, H., Ehrig, K., Prange, U. "Fundamentals of
    Algebraic Graph Transformation." Springer EATCS Monographs, 2006.
    DOI 10.1007/3-540-31188-2. Standard theory text. [unverified]
    beyond the index record (OpenAlex lists Ehrig, Ehrig, Prange).

[22] Ehrig, H., Golas, U., Taentzer, G. "Fundamental theory for
    typed attributed graph transformation." ICGT 2004.
    DOI 10.1007/978-3-540-30203-2_13. Peer-reviewed. [unverified]
    (record only).

[23] Rensink, A. "The GROOVE simulator: a tool for state space
    generation." AGTIVE 2003, LNCS 3062, 2004.
    DOI 10.1007/978-3-540-25959-6_40. Peer-reviewed. [unverified].

[24] Arendt, T., Biermann, E., Jurack, S., Krause, C. "Henshin: advanced concepts and tools for in-place EMF model
    transformations." MODELS 2010, LNCS 6394.
    DOI 10.1007/978-3-642-16145-2_9. Peer-reviewed MODELS. [unverified].

[25] Angles, R., Arenas, M., Barcelo, P., Hogan, A. "Foundations of modern query languages for graph
    databases." ACM Computing Surveys, 2017.
    DOI 10.1145/3104031. Peer-reviewed CSUR (survey). Read: abstract.

[26] Francis, N., Green, A., Guagliardo, P., Libkin, L., Lindaaker, T.,
    Marsault, V., et al. "Cypher: an evolving query language for property graphs." SIGMOD
    2018. DOI 10.1145/3183713.3190657. Peer-reviewed SIGMOD. Authors
    include Neo4j engineers (Green, Lindaaker; OpenAlex affiliations) and
    University of Edinburgh. Read: abstract (OpenAlex, 2026-10-09:
    Cypher 9, governed by openCypher, used by several commercial
    products, with a formal semantics of core read queries).

[27] Deutsch, A., Francis, N., Green, A., Hare, K., Li, B., Libkin, L.,
    et al. "Graph pattern matching in GQL and SQL/PGQ." SIGMOD
    2022. DOI 10.1145/3514221.3526057. Peer-reviewed SIGMOD. Authors
    include GQL standard contributors from Neo4j, TigerGraph, Google and
    LDBC (OpenAlex affiliations). Read: abstract.

[28] "GQL Standard", gqlstandards.org, entry "April 17, 2024 - The GQL
    Standard is published ... ISO/IEC 39075:2024 Information technology
    - Database languages - GQL". https://www.gqlstandards.org/home .
    Standards-committee site (ISO/IEC JTC1 SC32 WG3 per the site; the
    ISO page itself returned 403). Read: the news entry.

[29] Angles, R., Bonifati, A., Dumbrava, S., Fletcher, G., Green, A.,
    Hidders, J., et al. "PG-Schema: schemas for property graphs."
    Proc. ACM on Management of Data (SIGMOD 2023), 2023.
    DOI 10.1145/3589778. Peer-reviewed. Authors from universities and
    LDBC (OpenAlex). Read: abstract.

[30] jQAssistant user documentation (current).
    https://jqassistant.github.io/jqassistant/current/ . Official
    project doc (open-source tool). Read: overview and table of contents
    (concepts, constraints, groups, severity, baseline).

[31] ArchUnit user guide. https://www.archunit.org/userguide/html/000_Index.html
    . Official project doc. Read: overview and table of contents.

[32] Jordan, H., Scholz, B., Subotic, P. "Souffle: on synthesis of
    program analyzers." CAV 2016, LNCS 9780.
    DOI 10.1007/978-3-319-41540-6_23. Peer-reviewed CAV. Index
    affiliations: Innsbruck, Sydney, UCL; the paper states parts of the
    work were done while visiting Oracle Labs Australia, and its abstract
    (via search snippets, 2026-10-09) says Souffle is used for Java
    security analyses at Oracle Labs; the project wiki is under
    github.com/oracle. Standing: industrial use CONFIRMED (Oracle Labs).

[33] Souffle documentation, "Rules" page.
    https://souffle-lang.github.io/rules . Official project doc. Read:
    negation and stratification paragraph.

[34] Avgustinov, P., de Moor, O., Peyton Jones, M., Schaefer, M. "QL:
    object-oriented queries on relational data." ECOOP 2016, LIPIcs 56.
    DOI 10.4230/LIPIcs.ECOOP.2016.2. Peer-reviewed ECOOP. Authors are
    affiliated with Oxford and NTU in the index. Standing CONFIRMED for
    de Moor: CEO and co-founder of Semmle, acquired by GitHub 2019, whose
    QL became CodeQL (TechCrunch 2019-09-18, Wikipedia "CodeQL"; press,
    secondary). Other authors' Semmle roles unconfirmed. The
    abstract itself states the analyses scale to millions of lines of
    code. Read: abstract.

[35] CodeQL documentation, "About the QL language".
    https://codeql.github.com/docs/ql-language-reference/about-the-ql-language/
    . Official vendor doc (GitHub/CodeQL). Read: the page.

[36] Yamaguchi, F., Golde, N., Arp, D., Rieck, K. "Modeling and
    discovering vulnerabilities with code property graphs." IEEE S&P
    2014. DOI 10.1109/SP.2014.44. Peer-reviewed S&P (top security
    venue). Academic authors; validation is 18 new Linux kernel
    vulnerabilities. Read: abstract.

[37] Glean documentation, "Introduction".
    https://glean.software/docs/introduction/ . Official project doc.
    Meta origin CONFIRMED 2026-10-09: site footer "Copyright (c) Meta
    Platforms, Inc."; repo is facebookincubator/Glean. Read: the page.

[38] Kythe documentation, "Schema reference".
    https://kythe.io/docs/schema/ . Official project doc. Google origin
    confirmed SECONDARILY (Wikipedia "Google Kythe": derived from Google's
    internal Grok; a 2018 source{d} announcement names Michael Fromberger,
    8 years on Grok at Google, as instrumental in releasing it as Kythe).
    Read: first sections (namespace, node/kind, test-suite note).

[39] Libkin, L. "SQL's three-valued logic and certain answers." ACM TODS,
    2016. DOI 10.1145/2877206. Peer-reviewed TODS. Academic
    (Edinburgh), no industrial team claim. Read: abstract.

[40] Ujhelyi, Z., Bergmann, G., Hegedus, A., Horvath, A., et al.
    "EMF-IncQuery: an integrated development environment for live model
    queries." Science of Computer Programming, 2015.
    DOI 10.1016/j.scico.2014.01.004. Peer-reviewed SCP. [unverified]
    beyond the record.

[41] Bergmann, G., Okros, A., Rath, I., Varro, D. "Incremental pattern matching in the VIATRA model transformation
    system." GraMoT 2008. DOI 10.1145/1402947.1402953. Peer-reviewed
    workshop; abstract read 2026-10-09 (RETE adaptation). Also: Barmpis, K., Kolovos, D. "Hawk: towards a scalable
    model indexing architecture", BigMDE 2013, DOI
    10.1145/2487766.2487771. [unverified] (records only).

[42] Cleland-Huang, J., Gotel, O., Huffman Hayes, J., Maeder, P.
    "Software traceability: trends and future directions."
    FOSE at ICSE 2014. DOI 10.1145/2593882.2593891. Peer-reviewed
    invited roadmap (Future of Software Engineering track). Authors are
    the field's principal researchers; some industrial collaboration is
    [background, unverified]. Read: abstract.

[43] Rempel, P., Maeder, P. "Preventing defects: the impact of
    requirements traceability completeness on software quality." IEEE
    TSE, 2017. DOI 10.1109/TSE.2016.2622264. Peer-reviewed TSE.
    24 open-source projects, multi-level Poisson regression. Observational,
    so association not proof. Read: abstract.

[44] Rath, M., Rendall, J., Guo, J., Cleland-Huang, J.
    "Traceability in the wild: automatically augmenting incomplete trace
    links." ICSE 2018. DOI 10.1145/3180155.3180207. Peer-reviewed ICSE.
    Six open-source projects. Read: abstract.

[45] Tian, F., Wang, T., Liang, P., Wang, C., Khan, A. A., Babar, M. A.
    "The impact of traceability on software maintenance and evolution: a
    mapping study." arXiv:2108.02133, 2021.
    https://arxiv.org/abs/2108.02133 . Preprint of a systematic mapping
    study; 63 studies (2000 to May 2020). Re-checked 2026-10-09: no
    journal version found; treat as preprint. Read: abstract page.

[46] Fucci, D., Alegroth, E., Axelsson, T. "When traceability goes awry:
    an industrial experience report." Journal of Systems and Software, 2022. DOI 10.1016/j.jss.2022.111389; arXiv:2206.04462. Peer-
    reviewed JSS. Industry-academia project with a large telecom company
    (company not named in the abstract). Read: abstract (arXiv page).

[47] Antoniol, G., Canfora, G., Casazza, G., De Lucia, A.
    "Recovering traceability links between code and documentation."
    IEEE TSE, 2002. DOI 10.1109/TSE.2002.1041053. Peer-reviewed
    TSE. Two case studies (C++ onto manual pages; Java to functional
    requirements). Read: abstract.

[48] Utting, M., Pretschner, A., Legeard, B. "A taxonomy of model-based
    testing approaches." Software Testing, Verification and Reliability,
    2011 (online; DOI year). DOI 10.1002/stvr.456. Peer-reviewed STVR.
    Standing: Legeard CONFIRMED as co-founder and scientific adviser of
    Smartesting (conference profiles, 2026-10-09); Utting co-authored
    LEIRIOS Test Designer work but a company role is UNCONFIRMED.
    Read: abstract.

[49] Dalal, S. R., Jain, A., Karunanithi, N., Leaton, J. M., et al.
    "Model-based testing in practice."
    Proc. ICSE 1999. DOI 10.1145/302405.302640. Peer-reviewed ICSE.
    Bellcore authors (OpenAlex affiliation), applying to systems with
    millions of lines of code. Read: abstract.

[50] Grieskamp, W. "Microsoft's protocol documentation program: a
    success story for model-based testing." Lecture Notes in
    Computer Science, 2010. DOI 10.1007/978-3-642-15585-7_3. Peer-reviewed. Author at Microsoft
    Windows Interoperability Engineering (OpenAlex affiliation), the
    program is an internal shipped product effort. Read: title only.

[51] Alegroth, E., Karl, K., Rosshagen, H., et al. "Practitioners' best practices to adopt, use or abandon
    model-based testing with graphical models for software-intensive
    systems." Empirical Software Engineering, 2022.
    DOI 10.1007/s10664-022-10145-2. Peer-reviewed EMSE. 17 experts from
    industry. Read: abstract.

[52] Berger, T., She, S., Lotufo, R., Wasowski, A. "A
    study of variability models and languages in the systems software
    domain." IEEE TSE, 2013. DOI 10.1109/TSE.2013.34.
    Peer-reviewed TSE. 128 Kconfig and CDL models from 12 open-source
    projects. Read: abstract.

[53] Berger, T., Rublack, R., Nair, D., Atlee, J. M. "A survey of variability modeling in
    industrial practice." VaMoS 2013. DOI 10.1145/2430502.2430513.
    Peer-reviewed workshop (VaMoS). Practitioner questionnaire. Read:
    abstract.

[54] The Linux kernel documentation, "Kconfig Language."
    https://docs.kernel.org/kbuild/kconfig-language.html . Official
    project doc. Read: menu entries and dependency sections.

[55] Benavides, D., Segura, S., Ruiz-Cortes, A. "Automated analysis of
    feature models 20 years later: a literature review." Information
    Systems, 2010. DOI 10.1016/j.is.2010.01.001. Peer-reviewed.
    [unverified] beyond the record (very highly cited per OpenAlex).

[56] Batory, D. "Feature models, grammars, and propositional formulas."
    SPLC 2005, LNCS 3714. DOI 10.1007/11554844_3. Peer-reviewed.
    [unverified] beyond the record.

[57] Kang, K. C., Cohen, S. G., Hess, J. A., Novak, W. E. "Feature-oriented domain analysis (FODA) feasibility study."
    CMU/SEI-90-TR-21, 1990. DOI 10.21236/ADA235785. SEI technical report.
    [unverified] beyond the record.

[58] Maranget, L. "Warnings for pattern matching." Journal of
    Functional Programming, 2007. DOI 10.1017/S0956796807006223.
    Peer-reviewed JFP. Author at INRIA; algorithm integrated in the
    OCaml compiler (abstract). Read: abstract.

[59] Rust Compiler Development Guide, "Pattern and exhaustiveness
    checking." https://rustc-dev-guide.rust-lang.org/pat-exhaustive-checking.html
    . Official project doc. Read: the page.

[60] The Rust Reference, "Type system attributes: the non_exhaustive
    attribute." https://doc.rust-lang.org/reference/attributes/type_system.html
    . Official language reference. Read: the section.

[61] Zig Language Reference (master), "switch" and "Non-exhaustive
    enum." https://ziglang.org/documentation/master/ . Official language
    reference. Read: the non-exhaustive enum paragraph.

[62] Swift Evolution SE-0192, "Handling Future Enum Cases."
    https://github.com/swiftlang/swift-evolution/blob/main/proposals/0192-non-exhaustive-enums.md
    . Official language-evolution proposal (accepted, with a recorded
    post-acceptance revision). Read: the @unknown default and revision
    paragraphs.

[63] JEP 409: Sealed Classes. https://openjdk.org/jeps/409 . Official
    OpenJDK proposal; reviewed by Alex Buckley, endorsed by Brian Goetz
    (per the page header). Read: summary, goals, motivation.

[64] Kotlin documentation, "Sealed classes and interfaces."
    https://kotlinlang.org/docs/sealed-classes.html . Official language
    doc. Read: the `when` exhaustiveness paragraph.

[65] Alloy language reference. https://alloytools.org/spec.html .
    Official language reference. Read: sig declarations, abstract,
    extends/in sections.

[66] Jackson, D. "Alloy: a lightweight object modelling notation." ACM
    TOSEM, 2002. DOI 10.1145/505145.505149. Peer-reviewed TOSEM.
    Author at MIT (OpenAlex, confirmed 2026-10-09). Read: abstract.
    The "likely an indication that the model is incomplete" sentence is
    from [65], not from this paper.

[67] P language manual, "P DataTypes."
    https://p-org.github.io/P/manual/datatypes/ . Official project doc.
    Read: type list and grammar.

[68] P language manual, "P State Machines."
    https://p-org.github.io/P/manual/statemachines/ and Desai, A., Gupta,
    V., Jackson, E., Qadeer, S., Rajamani, S., Zufferey, D. "P: safe
    asynchronous event-driven programming." PLDI 2013.
    DOI 10.1145/2491956.2462184. Peer-reviewed PLDI. Authors are
    Microsoft researchers (OpenAlex affiliations); P was built for
    asynchronous driver-like code. Read: manual page; abstract of PLDI.

[69] Quint language manual. https://quint-lang.org/docs/lang . Official
    project doc. Read: sum type section and navigation (RFC for
    row-polymorphic sum types).

[70] Newcombe, C., Rath, T., Zhang, F., Munteanu, B., Brooker, M.,
    Deardeuff, M. "How Amazon Web Services uses formal methods."
    Communications of the ACM, 2015. DOI 10.1145/2699417.
    Peer-reviewed CACM practice article. Amazon engineers (OpenAlex
    affiliations for Rath, Munteanu, Brooker, Deardeuff). Read: one-line
    abstract only; the claim "TLA+ is used to prevent serious but subtle
    bugs" is the abstract's.

[71] Brooker, M., Desai, A. "Systems correctness practices at Amazon Web
    Services." Communications of the ACM, 2025.
    DOI 10.1145/3729175. Peer-reviewed CACM. Both authors at AWS
    (OpenAlex affiliation). Read: abstract (one line, "Leveraging formal
    and semi-formal methods"); full text returned 403.

[72] Murphy, G. C., Notkin, D., Sullivan, K. "Software reflexion models:
    bridging the gap between design and implementation." IEEE TSE, 2001. DOI 10.1109/32.917525. Peer-reviewed TSE. Abstract states use
    on an experimental reengineering of Microsoft Excel (million lines).
    Read: abstract. (Topic B owns the main treatment.)

[73] Hughes, J. "Experiences with QuickCheck: testing the hard stuff and
    staying sane." LNCS 9600, 2016. DOI 10.1007/978-3-319-30936-1_9.
    Peer-reviewed. Industrial QuickCheck experience, [unverified]
    beyond the record. Cited only in section 6.

[74] "UML in Practice", It Will Never Work in Theory (curated review site,
    Greg Wilson et al.), 2013-06-13.
    https://neverworkintheory.org/2013/06/13/uml-in-practice-2.html .
    Named secondary review of [1]; gives the category and diagram counts.
    Medium. Added 2026-10-09.

[75] Langer, P., Mayerhofer, T., Wimmer, M., Kappel, G. "On the Usage of
    UML: Initial Results of Analyzing Open UML Models." Modellierung
    2014, LNI 225, pp. 289-304. https://dl.gi.de/handle/20.500.12116/20946
    . Peer-reviewed (GI). Academic (TU Wien). Read: FULL TEXT. 121
    Enterprise Architect models; Table 1 compiles top-3 diagram kinds
    from Dobing/Parsons, Grossman et al., Reggio et al., Petre and
    Hutchinson et al. Added 2026-10-09.

[76] Akdur, D., Garousi, V., Demirors, O. "A survey on modeling and
    model-driven engineering practices in the embedded software
    industry." J. Systems Architecture 91, 2018, 62-82.
    DOI 10.1016/j.sysarc.2018.09.007. Peer-reviewed. Standing: Akdur at
    ASELSAN (defense electronics; OpenAlex and the companion MECO 2017
    paper header). 627 engineers, 27 countries. Read: full abstract
    (Semantic Scholar) plus the MECO 2017 companion paper (full text:
    class diagrams third; 77 percent use UML). Strong. Added 2026-10-09.

[77] Grieskamp, W., Kicillof, N., Stobie, K., Braberman, V. "Model-based
    quality assurance of protocol documentation: tools and methodology."
    Software Testing, Verification and Reliability 21(1), 2011.
    DOI 10.1002/stvr.427. Peer-reviewed. Microsoft Windows Protocol
    Engineering Team (per abstract). Read: abstract. Strong practitioner
    evidence. Added 2026-10-09.

## 6. What remains unread, and why it should not change the conclusions

Unread or only abstract-read (all of F1..F29 except the vendor docs):

- Full texts of all paywalled papers (about 40). The conclusions that
  depend on numbers use only numbers that appear in the fetched abstracts.
  Full text could sharpen magnitudes, not reverse the direction of any
  claim, because the implications in section 3 are design rules (closed
  vs open variant sets, stratification, derived links) whose justification
  is mostly the vendor language documents, which WERE read in full for the
  cited sections.
- [RESOLVED 2026-10-09, see F5 and 7.2] UML per-diagram-kind frequency
  (F5, the "which diagram kinds survive" item). Not retrievable in the
  original run. A later pass with PDF access should read
  Storrle EASE 2017 [2], Dobing and Parsons [7] and Akdur, Garousi and
  Demirors, "A survey on modeling and model-driven engineering practices
  in the embedded software industry", J. Systems Architecture 2018,
  DOI 10.1016/j.sysarc.2018.09.007, and the collaborative-MDE
  survey by David, Aslam and Malavolta, JSS 2023, DOI 10.1016/j.jss.2023.111626
  (both found in the index, abstracts unavailable, [unverified]). The
  planning brief's level table does not depend on the ranking: each level
  has its own justification in topic A.
- OCL empirical usage. No study found; the claim stays weak (F9).
- Scanniello et al., "Do software models based on the UML aid in
  source-code comprehensibility? Aggregating evidence from 12 controlled
  experiments", EMSE 2018, DOI 10.1007/s10664-017-9591-4: found, abstract
  unavailable, [unverified]. It bears on "do models help at all", which
  is topic A/D territory.
- Graph rewriting theory (Ehrig book [21], Henshin [24], GROOVE [23]) and
  critical-pair/confluence results (Heckel, Kuester, Taentzer; the search
  did not resolve to the paper): I3/I5 use them only to justify "local
  rewrite with a negative application condition", a design guideline.
- Differential Datalog (Ryzhyk and Budiu, Datalog 2.0 workshop 2019): the
  search resolved only to an unrelated 2023 interpreter preprint, so the
  original is not cited. Incremental evaluation is argued from Egyed [14]
  and the GRL finiteness property instead.
- Datalog survey (Green, Huang, Loo, Zhou, 2013, DOI 10.1561/1900000017),
  Doop (Bravenboer and Smaragdakis, OOPSLA 2009, DOI
  10.1145/1640089.1640108), bddbddb (Whaley et al., 2005, DOI
  10.1007/11575467_8), codeQuest (Hajiyev et al., ECOOP 2006, DOI
  10.1007/11785477_2): found in the index; unread. They corroborate F17
  (Datalog for program analysis) and cannot contradict the stratification
  advice, which is stated by the Souffle documentation [33].
- Gotel and Finkelstein 1994 (DOI 10.1109/ICRE.1994.292398), Borg et al.
  EMSE 2013 (DOI 10.1007/s10664-013-9255-y), Maeder and Egyed EMSE (DOI
  10.1007/s10664-014-9314-z), Maro et al. JSS 2018 (DOI
  10.1016/j.jss.2018.03.060), Guo et al. ICSE 2017 (DOI
  10.1109/ICSE.2017.9): found; abstracts unavailable or not read;
  [unverified]. They are the standard traceability references and agree
  in direction with F21/F22 as far as the read abstracts show.
- Berger et al. MODELS 2014 "Three cases of feature-based variability
  modeling in industry" (DOI 10.1007/978-3-319-11653-2_19): title only.
- Hughes 2016 [73] and Grieskamp 2010 [50]: titles and affiliations only;
  the MBT claims in F23 that rest on them are limited to "industrial
  uses exist".
- ISO/IEC 39075:2024 itself (paywalled); only the committee news entry
  was read.
- Standards texts (UML 2.5.1, OCL 2.4, MOF 2.5.1): About pages only.
- TLA+ itself: no manual page fetched. Statements about TLA+ having no
  sum types are inferred from Quint's manual and are marked as such.
- Not searched: Event-B/ProB, Dafny-style ADTs, Haskell/Scala ADT
  literature, PlantUML/Structurizr internals (topic C owns the languages).

Why this should not change the conclusions: the load-bearing parts of the
recommendations (closed/open variant sets, flat exhaustiveness,
stratified negation, mandatory node kinds, derived rather than
hand-written links, completeness as a metric, per-arm evidence) are each
backed by at least one fully-read official language or tool document
[33][38][59][60][61][62][63][65], and by at least one abstract-level
empirical result in the same direction [43][44][46][58]. The weakest
areas, flagged in the text, are: UML diagram survival (F5, a gap), OCL
(F9, one opinion), I9 (a synthesis, not a finding), and the industrial
credibility of several academic authors where only university
affiliations could be verified.

## 6b. Follow-ups suggested for the coordinator (not decisions)

- Decide the closed/open spelling of variant sets (I7) before the grammar
  freezes; it changes arm syntax (`unknown`).
- Decide the goal group kinds `all` / `one_of` (I8) or explicitly record
  that the planning brief means "all" and that alternatives are modeled as
  separate goals.
- A second pass with PDF access for the paywalled items listed in
  section 6, prioritising [2], [7] and the Akdur survey for the
  diagram-kind question.

## 7. Verification pass (2026-10-09)

Done by a second agent WITH WebSearch/WebFetch (the original run had
neither), plus Crossref, OpenAlex, Semantic Scholar, the GitHub API and
pdftotext on reachable PDFs. Scope: every [unverified], [background,
unverified], title-only or abstract-only citation that a finding relies
on, author-standing claims, and the diagram-kind gap (F5). Structural
note: the pre-existing "7. Follow-ups" was renumbered "6b" so this
section can carry the number 7.

### 7.1 Changes, by kind

FIXED (verified, text updated in place)
- F1 Petre [1]: counts added (35 none, 11 selective, 3 codegen, 1
  retrofit, 0 wholehearted; class 7, sequence 6, activity 6, state 3,
  use case 1). Secondary-verified via [74] and [75]; the PDF itself was
  not reachable (403/404).
- F5 diagram kinds: GAP closed. Dobing and Parsons [7] read in FULL
  (upgraded from a one-sentence fragment); Langer et al. [75] read in
  full; Akdur [76] abstract plus companion paper. See 7.2.
- F11 Nuseibeh [16]: upgraded from title-only to abstract-level content.
- F20 VIATRA [41]: Rete mechanism now sourced from the abstract (was
  [background, unverified]).
- F23 Microsoft MBT: [77] STVR 2011 added; "MBT works and scales" is now
  an abstract-level claim by the practitioners, not a title.
- [26] Cypher: abstract now read.
- [45] Tian et al.: re-checked, still a preprint (no journal version).
- Author standing CONFIRMED with a source: [2] Storrle (QAware GmbH),
  [12] Willink (Eclipse MDT OCL project lead from 2010), [32] Souffle
  (in use at Oracle Labs; work done visiting Oracle Labs), [34] de Moor
  (Semmle CEO/co-founder; QL became CodeQL; press source), [37] Glean
  (Meta copyright on the site), [38] Kythe (Google Grok origin;
  secondary sources only), [48] Legeard (Smartesting co-founder), [66]
  Jackson (MIT), [76] Akdur (ASELSAN).

DOWNGRADED / CORRECTED
- [2] Storrle is NOT a source for diagram kinds (it reports usage
  scenarios); section 6 previously listed it as a priority read for F5.
- [38] Kythe's Google origin rests on Wikipedia plus a company
  announcement: graded secondary.
- [48] Utting: company role UNCONFIRMED (only LEIRIOS co-authorship).

REMOVED
- Nothing removed; no fabricated citation found (all checked DOIs and
  titles resolved to matching index records).

ADDED
- [74]-[77].

STILL [unverified] (not load-bearing, left as is): [21]-[24] graph
rewriting texts and tools (records only; used for a design guideline),
[40] EMF-IncQuery and Hawk (titles), [55]-[57] feature-model analyses
(records; F25 already marks the standard analyses as background), [18]
now has an abstract (Dagstuhl working-group taxonomy) but is not cited
by any finding, [73] Hughes.

### 7.2 Which diagram kinds survive (settled)

| Source | N / basis | Top kinds | Bottom kinds |
|---|---|---|---|
| Dobing and Parsons 2006 [7] | 171+11 survey, UML 1.5 | class 73 percent, use case 51, sequence 50 (regular use) | collaboration (least used, most redundant) |
| Petre 2013 [1][74] | 11 selective of 50 | class 7, sequence 6, activity 6 | use case 1 |
| Akdur et al. 2018 [76] | 627 embedded | sequence, state machine, class | n/a in abstract |
| Langer et al. 2014 [75] | 121 open models | classes 100, use cases 47, interactions 39 | state machines last |
| Hutchinson et al. 2011 (via [75] Table 1) | MDE survey | class, activity, use case | n/a |

Robust across all five: a structural view and the sequence/interaction
view. State machines are domain-dependent (top in embedded, bottom in
open models). Use case diagrams are common but rated least informative
(Dobing). Communication/collaboration diagrams are dead. Typical models
use 2-3 kinds (Langer).

Consequence for grmb (extends I4 and I20; tag ADOPT): render a sequence
diagram per scenario (actors as lifelines, steps as messages, outcome
arms as `alt` fragments), one structural view (systems/nodes and declared
flows), and the goal tree as a plain tree; render state diagrams only for
the later `machine` entity; do NOT render use-case or communication
diagrams. Check: golden test per render kind; the sequence render of a
scenario contains exactly one `alt` branch per handled non-ok outcome
(so the picture is itself an exhaustiveness witness).

### 7.3 Effect on recommendations

- No ADOPT/ADAPT/REJECT tag flips. I4 and I20 gain a concrete render list
  (7.2), which the original note explicitly refused to give.
- I16 (per-arm obligations instead of test generation) is slightly
  weakened, not flipped: [77] shows MBT generation "works and scales" at
  Microsoft with strong tooling. The cost argument (model upkeep, tool
  investment) still favors obligations-not-generation for grmb v1; a
  generator stays a later option.
- I3 (incremental read-sets) gains direct support from [41] (stored
  matches maintained incrementally).
- Naming caution: this note uses "GRL" for grimble's rule language; ITU-T
  Z.151 also defines a "GRL" (Goal-oriented Requirement Language) for
  goal models, and grmb adds goals. The topic C note records the clash.

### 7.4 Revised coverage verdict

12 of 12 brief items touched (unchanged). The one declared GAP (F5) is
closed with two full-text reads and one strong abstract. Full-text reads
rise from 0 papers to 3 (Dobing and Parsons, Langer et al., Akdur MECO
companion) plus the Storrle extended abstract. Author standing is now
sourced for 9 more authors/projects; 2 remain unconfirmed (Utting's
company role; Semmle roles of QL co-authors other than de Moor).
Remaining weakest areas: OCL usage (F9, still one informed opinion; not
re-searched in this pass), graph-rewriting
texts (records only, guideline use), and I9 (synthesis). Verdict:
exhaustive for topic E at abstract-plus-vendor-doc depth, with the
diagram-kind question now evidence-backed.
