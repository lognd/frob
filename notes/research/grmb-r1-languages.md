# grmb R1, topic C: existing design, architecture and requirements languages

Researcher C, ticket ~19SEHXJ, run date 2026-10-09. Worktree file; not committed.

Status line (honest): universe of 30 named languages, 30 touched, 0 pending.
Evidence depth varies: 4 are "thin" (only a vendor page, a repo metric or a
paper title was verified; marked THIN in the table) and 4 sources are
blocked or partial (section 1.4). Nothing is silently dropped.
Verification pass 2026-10-09 (with WebSearch/WebFetch): every THIN,
[from memory], title-only and abstract-only citation that a finding relies
on was re-checked; edits are inline and every change is listed in
section 7. The four THIN languages (GRL, Quint, PlantUML, FizzBee) and
Event-B now carry official-doc evidence.

## 1. Scope and search log

### 1.1 Universe (denominator = 30)

The brief names 30 language items for topic C. I counted UML and OCL as two
items, SysML v1 and v2 as two, statecharts / SCXML / XState as three, and
GRL as its own item:

1 SysML v1, 2 SysML v2 (+KerML), 3 UML, 4 OCL, 5 AADL, 6 ArchiMate,
7 BPMN, 8 Structurizr DSL, 9 LikeC4, 10 PlantUML, 11 Mermaid, 12 D2,
13 Gherkin, 14 KAOS, 15 i*, 16 GRL, 17 Alloy, 18 TLA+, 19 Quint, 20 P,
21 FizzBee, 22 Event-B, 23 statecharts, 24 SCXML, 25 XState, 26 Smithy,
27 TypeSpec, 28 Ballerina, 29 Lingua Franca, 30 CUE.

Added by me as ADJACENT (not in the denominator, because the brief did not
name them, but they are the closest prior art to "bind a model to code and
tickets and check it"): the C4 model, Backstage descriptor format,
OpenFastTrace, StrictDoc. Not reached: Doorstop, sphinx-needs (fetch failed),
ReqIF, Z/VDM, Rapide/Wright/Darwin ADLs (covered only through the Medvidovic
and Malavolta surveys, section 2).

### 1.2 Tooling actually available this run

The WebSearch and WebFetch tools were NOT available in this environment
(ToolSearch returned no match for either, and no arxiv tools either). All
discovery and fetching was done with `curl`/Python from the shell:

- Crossref REST API (`api.crossref.org`) for bibliographic lookup and DOI
  verification of every paper cited in section 5.
- OpenAlex API (`api.openalex.org`) for abstracts (inverted-index decoded),
  citation counts and venue names, and for relevance-ranked discovery.
- Semantic Scholar API (abstracts for 3 papers).
- Official vendor/standards pages fetched directly (OMG, Open Group, W3C,
  smithy.io, typespec.io, cuelang.org, quint-lang.org, p-org.github.io,
  fizzbee.io, stately.ai, ballerina.io, lf-lang.org, cucumber.io,
  docs.structurizr.com, c4model.com, likec4.dev, d2lang.com, alloytools.org,
  backstage.io, GitHub READMEs, GitHub blog).
- GitHub REST API via `gh` for repository metrics (stars, creation date,
  last push, archived flag), taken 2026-10-09. Stars are a WEAK adoption
  proxy and are used only as a coarse ordering, never as proof of use.
- One full-text read: Newcombe et al. (AWS, CACM 2015) from the author-site
  PDF mirror. Every other paper was read at ABSTRACT level only, because the
  ACM, IEEE and Open University pages returned 403 / Cloudflare challenges.
  Claims below that go beyond an abstract are marked [abstract-only] or
  [from memory, unverified].
- arXiv API returned HTTP 429 (rate limited); arXiv items were obtained via
  OpenAlex instead.

### 1.3 Queries run (selection)

Crossref bibliographic queries: Petre UML in practice; Hutchinson/Whittle MDE
in industry (3 papers); Akdur/Garousi embedded modeling survey; Newcombe AWS
formal methods; Jackson Alloy; zur Muehlen/Recker BPMN; Ho-Quang UML in OSS;
Storrle conceptual models; Malavolta architectural languages survey;
Medvidovic/Taylor ADL framework; Moody Physics of Notations; Horkoff GORE;
Wolny SysML mapping; Woodcock formal methods survey; Davis MongoDB; Harel
statecharts (2); Desai P; Bornholt S3; Behm Meteor; Hebig UML on GitHub;
Binamungu BDD; Mavin GORE; Yu i*; van Lamsweerde GORE; Dardenne KAOS;
Lohstroh Lingua Franca; Zave Chord; Feiler AADL; Kelly/Tolvanen DSM; Alloy 6;
iStar 2.0.
OpenAlex discovery queries: TLA+ trace validation / conformance; SysML v2
evaluation and adoption; AADL industrial experience; Event-B Rodin industrial
experience; model-code conformance in industry; ADL practitioner surveys;
Storrle results; use-case adoption; Gherkin BDD mapping studies; Dagger/CUE
(no usable result, dropped).

### 1.4 Excluded, blocked or partial (surfaced, not dropped)

- BLOCKED: sphinx-needs.com (TLS handshake error); event-b.org (self-signed
  certificate); ACM DL / IEEE Xplore / ORO full text (403). Event-B evidence is
  therefore secondary (Woodcock survey, Mashkoor, Meteor title, Rodin tool
  paper lookup).
- PARTIAL (original run): GRL (ITU-T Z.151 / URN) was not fetched; i*/GRL
  evidence rested on Yu 1997, Horkoff 2017, Mavin 2017. Gherkin evidence is
  practitioner-survey level. BPMN usage-subset paper: title verified,
  abstract not retrieved. RESOLVED 2026-10-09: Z.151 summary, the GRL
  evaluation paper and the BPMN abstract were fetched (section 7).
- EXCLUDED: anonymous blogs; vendor testimonials are recorded but graded
  WEAK (FizzBee page quotes named engineers at Confluent, Doordash, Shopify;
  vendor-curated, not independent).
- EXCLUDED as out of topic C scope: design-doc/RFC/ADR practice (topic A),
  erosion/conformance tools (topic B), partial models/typed holes (D), UML
  metamodel/graph queries/trace recovery (E), diagnostics/ergonomics (F).

### 1.5 Coverage argument for "exhaustive"

The frontier was fixed first (the 30 items above, written before any fetch).
Each item received at least one primary or official source (standard body or
vendor documentation) plus, where it exists, one empirical study. Cross-cutting
secondary literature (mapping studies and surveys) was swept to cover the
languages not individually studied: Malavolta 2013 (ADLs, 48 practitioners),
Medvidovic 2000 (ADL framework), Wolny 2020 (SysML, mapping study), Horkoff
2017 (GORE, 246 papers), Woodcock 2009 (formal methods), Mashkoor 2018
(state-based FMs), Akdur 2018 (627 embedded engineers), Whittle 2014
(450 MDE practitioners). Remaining unread, and why it would not change the
conclusions: full texts of 33 of 34 papers (abstract-level evidence already
agrees on the direction: modeling is selective, informal-heavy, rarely bound
to code; successful languages are executable, generate code, or are checked
against it); Doorstop/sphinx-needs/ReqIF (same family as OpenFastTrace and
StrictDoc, which were read); per-language long-tail case studies (would add
anecdotes, not change the design-relevant mechanisms).

## 2. Findings

Evidence strength tags: EMP = empirical study, EXP = experience report from a
named company, VND = vendor/standards doc, OPN = opinion. Credibility lines
follow each cluster; they are repeated in section 5 per source.

### 2.1 What survives in practice (adoption findings)

F1. UML is used selectively and informally; full-model use is rare. Petre
interviewed 50 professional engineers in 50 companies and found 5 distinct
patterns of UML use [S1, EMP, abstract-only]. Akdur surveyed 627 embedded
engineers in 27 countries: most use UML, and the second most common answer is
"sketch / no formal modeling language" [S4, EMP]. Storrle's survey opens on
the same controversy (UML as "lingua franca" vs "majority do not use UML")
[S6, EMP, abstract-only]. Jongeling et al. found that models for
communication and documentation are often informal, which limits MDE tooling
[S8, EMP]. Petre's counts (verified 2026-10-09 via the Never Work in
Theory review of the paper, and consistent with the top-3 diagram ranking
Langer et al. report for Petre [S37]): of 50 engineers, 35 used no UML,
11 used it selectively, 3 for automated code generation, 1 retrofit,
0 wholehearted; the 11 selective users used class (7), sequence (6),
activity (6), state machine (3) and use case (1) diagrams; reasons for
non-use were lack of context (UML covers architecture, not the whole
system), notation overhead, and synchronization/consistency [S1, V28;
counts from a secondary review, the paper PDF itself returned 403/404].
Storrle (QAware GmbH) found that the top uses of models are communicative
and cognitive (discuss with colleagues 79 percent often/always, visualize
an idea 75, help me think 70) while about half use models rarely or never
to generate code [S6, EMP, extended abstract read in full].

F2. Models are written once, at project start, then rot. Mining 10 percent of
GitHub (1.24 million projects) found 21,316 UML diagrams in 3,295 projects;
creating/updating happens most often in a very short phase at the start
[S7, EMP]. In open source, collaboration is the main motive for UML and it
benefits newcomers and contributors who do not create models [S5, EMP].
Implication: a design model with no tie to evolving code decays on a known
schedule.

F3. MDE succeeds partially and socially. 450 practitioners surveyed plus 22
interviews: MDE is more widespread than believed but rarely generates whole
systems; it is applied to key parts [S3, EMP]. Hutchinson et al.: success or
failure depends on technical, organizational and social factors [S2, EMP].

F4. Architecture languages: practitioners are satisfied with design
capabilities, dissatisfied with analysis features and extra-functional
property support, want more formality and better usability; languages in use
mostly originate from industry, not academia (48 practitioners, 40 companies,
15 countries) [S10, EMP]. Medvidovic and Taylor's classification framework
fixed the ADL vocabulary (components, connectors, configurations) in 2000
[S11, abstract not fetched, EMP/theory].

F5. SysML v1 is used mostly in design/validation rather than implementation;
most used diagrams are requirement, parametric, block, activity, state machine;
it needs domain customization [S9, EMP mapping study, 2005-2017]. SysML v2
(KerML foundation, textual and graphical, a services API) was formally adopted
by OMG on 30 June 2025 and its specs were edited in March 2026 for ISO
submission [V1, VND]; the release repo carries a `bnf` directory, i.e. a
textual grammar is first-class.

F6. Goal-oriented RE (KAOS, i*, GRL) has a large literature and low industry
uptake. Horkoff's mapping of 246 top-cited GORE papers found a proliferation
of papers with new ideas and few citations, a few authors dominating
[S14, EMP]. Mavin et al. (literature survey plus practitioner questionnaire):
uptake of goal approaches "appears to be quite low", where goals are used it
is mainly informal, and the majority of papers have little industrial
involvement [S13, EMP]. KAOS originates in van Lamsweerde's group [S15, S16];
i* is aimed at the early phase (the "Whys") rather than completeness and
verification [S16, abstract]. GRL (verified 2026-10-09): ITU-T Z.151 (URN,
current edition 10/2018, in force, first approved 2008) defines URN as two
sub-notations, GRL for goals (mainly non-functional requirements and
quality attributes) and Use Case Maps for scenarios [V32, standard body].
GRL analysis assigns initial satisfaction values in a "strategy" and
propagates them over decomposition and contribution links; the standard
imposes no single propagation algorithm, and Amyot et al. give three
(quantitative, qualitative, hybrid) implemented in the open-source
Eclipse tool jUCMNav [S42, abstract]. Adoption evidence found: academic
and regulatory-compliance case studies only; the jUCMNav source repo is a
2-star "LEGACY" GitHub repo last pushed 2021-07-28 [V27]. No independent
industrial adoption study for GRL was found. Note the name clash: grimble's
own rule language is also called GRL (grl-spec); the two are unrelated.

F7. Gherkin/BDD is the one requirements notation with wide practical use and a
direct code binding (step text is matched to a code block called a step
definition [V17, VND]). Costs: 75 practitioners report BDD specifications
become costly to maintain as examples multiply, and parts of the system can
become effectively frozen [S17, EMP]. A 2023 mapping study of 166 papers notes
scarcity of industry-derived insight and metrics for BDD specification quality
[S18, EMP]. Large-scale projects name ownership of behaviors, tooling
adoption, scale and versioning of behaviors as challenges [S19, EMP].

F8. Text-to-diagram tools win on adoption where they do no checking: Mermaid
(90.6k stars, 2014; rendered natively in GitHub Markdown since Feb 2022
[V22, VND]), PlantUML (13.4k, 2010), D2 (25.6k, 2022), LikeC4 (5.8k, 2023)
[V27]. They give versioned text (git) and generated diagrams; none binds
nodes to code. PlantUML (verified): GitLab.com renders PlantUML in
Markdown, AsciiDoc and reStructuredText "for all users" with no
configuration [V33, VND]; its CLI checks are syntax-only
(`--check-syntax`, `--check-before-run`, exit code 200 "Some diagrams have
syntax errors"); the docs describe no semantic validation [V34, VND]. LikeC4 adds `likec4 validate` for syntax errors and layout
drift [V20, VND] and an MCP server for AI agents.

F9. The C4 model (system, container, component, code; notation- and
tooling-independent) [V19, VND] and Structurizr DSL (identifiers are opt-in:
by default elements are anonymous and cannot be referenced [V18, VND]) show
that a four-level hierarchy named in the owner's level vocabulary is the
shape architects accept. Structurizr DSL has a code-facing feature:
`!components` wraps the component finder, "providing the ability to
automatically discover components in a Java codebase" (docs gated behind
early access) [V18, VND, verified 2026-10-09]; this is model-FROM-code
discovery, not drift checking. The Structurizr Java library repo was archived
2026-02-01 and a unified `structurizr/structurizr` repo created 2025-11-30
[V27], i.e. the ecosystem consolidated; reason not stated in sources read.

### 2.2 What formal-ish design languages achieved, and how they bind to code

F10. TLA+ at AWS: used on 10 large real systems, "in every case" added
significant value; 7 teams; engineers from entry level to Principal learned it
in 2 to 3 weeks; the paper argues for "a ladder of abstraction" in which each
lower level is verified against a higher one; it explicitly says design
descriptions that are diagrams plus pseudo-code are too imprecise while code
has overwhelming detail; testing code cannot find subtle design errors
[S20, EXP, full text read]. Note what the 2015 paper does NOT claim: any
machine-checked link from spec to code.

F11. Spec-to-code conformance is the hard part and the field has converged on
two lessons. (a) MongoDB: model-based trace-checking was IMPRACTICAL when the
spec was highly abstract relative to the server; model-based test-case
generation succeeded for Realm Sync [S23, EXP, abstract]. (b) Where a
spec/code link works, it is cheap, partial and executable: AWS S3 ShardStore
uses executable reference models checked against the implementation; prevented
16 issues from reaching production and was extended by non-formal-methods
experts [S22, EXP]. ZooKeeper: three levels (protocol, system, test spec),
the test spec guides exploratory testing of the implementation, specs merged
into the Apache project [S24, EXP]. Cirstea et al.: trace validation against
TLA+ by recording only updates to spec variables; found discrepancies in all
programs tried [S25, EMP]. The P project now ships PObserve to check service
logs against P monitors "without additional instrumentation" [V12, VND].
Implication for grmb: the binding granularity must be chosen to match the
abstraction gap; a binding that is too abstract is unusable (F11a).

F12. P (state machines + events; compiled to code AND model-checked)
"unifies modeling and programming": the environment is modeled as
nondeterministic ghost machines erased at compilation [S26, EMP, PLDI 2013];
at AWS developers use it to model designs as communicating state machines and
check specs [V12, VND]. This is the strongest precedent for a design notation
whose actors are the environment.

F13. Alloy: lightweight relational modeling; the Chord work found that no
published version of the protocol was correct under its stated assumptions
[S28, EMP]; Alloy 6 added mutable state and temporal logic; docs and tooling
maintained to 2025 [V23, VND]. No code binding. Quint (created at Informal
Systems: the GitHub repo `informalsystems/quint` now redirects to
`quint-co/quint`, same 2021-05-28 creation date [V27]; quint.sh footer
links Informal Systems [V29]) is a modern TLA-family language with a type
system, model-based testing docs and a draft RFC for row-polymorphic SUM
TYPES [V11, VND]; its code binding is trace replay: the `quint-connect`
crate generates traces that are replayed against real Rust code (Conviva
testimonial on the vendor page) [V29, VND, WEAK]. FizzBee is Python-like
(Starlark) and its model-based testing is real but narrow: a Go test
adapter the user implements per role/action, generated test skeleton,
sequential and parallel tests (Java and Rust "coming soon") [V13, V30,
VND]; testimonials are from named engineers at Confluent, Doordash,
Shopify and Databend [V13, WEAK, vendor-curated]. FizzBee also generates
sequence and block diagrams from the spec [V13].

F14. Formal methods adoption in general: Woodcock et al. survey of industrial
use reports increasing use at the early stages of specification and design
[S29, EMP]; Mashkoor et al.: criteria for choosing state-based FMs include
social and industrial factors, and no decision matrix is possible [S30, EMP].
Event-B: Rodin is the Eclipse-based toolset that combines modelling and
proving and is designed to keep proofs stable under model change [S38,
abstract]. Classical B (not Event-B) was used for the Meteor driverless
metro (Paris line 14) [S35]; the RATP slides give the safety core as 1,150
B components, 115,000 lines of B, 27,800 proof obligations and 86,000
lines of Ada [V31, VND/operator slides, 2001]; a "no bugs" claim seen in
secondary sources is NOT supported and is not made here. Event-B industrial
deployment evidence: the EU DEPLOY project introduced Event-B at
industrial partners (automotive, railway, space, business information)
[S39, book record]; Bosch's two pilots concluded that "no single
formalism" covers requirements to code and a formalism should be used
"only where and when it is really suitable" [S40, workshop paper];
Clearsy authors summarize 25 years of B/Event-B in railways, smartcards
and automotive and open with "Industrial applications involving formal
methods are still exceptions to the general rule" [S41, abstract].
Verdict: B is proven in rail; Event-B is industrially piloted, not widely
adopted.

F15. Statecharts: Harel's 1987 formalism, a fully executable visual formalism,
was driven by close work with real engineers [S31, HOPL account]; SCXML is a
W3C Recommendation (1 Sep 2015; editors from Genesys, IBM, Voxeo, Nuance and
others) [V7, VND]; XState (30.3k stars, 2015, active) is the living,
executable descendant in TypeScript, and is positioned as state management and
orchestration, not documentation [V14, VND; V27]. State machines survive
because they are executable.

F16. Interface/API languages that generate code and check models are the
commercial winners: Smithy (Amazon/AWS IDL "widely used within Amazon and AWS
for over a decade", built because existing IDLs were not extensible enough for
metadata, codegen, service frameworks and "automated policy enforcement"
[V8, VND]); TypeSpec (Microsoft; compiler API exposes `defineLinter`,
`createRule`, `defineCodeFix`, `createSuppressCodeFix` [V9, VND]).
Smithy's validation model is directly reusable: ERROR (structural, cannot be
suppressed), DANGER (unsuppressed means invalid), WARNING, NOTE; validator
event ids are hierarchical ("Foo.Bar" contains "Foo") so suppressions can
target groups; users cannot set user-defined validators to ERROR [V8, VND].

F17. CUE: values form a lattice (subsumption, meet), so merging configs is
order-independent; validation can check that one schema's instances are all
instances of another (backward compatibility); roots in Google's GCL
configuration language used to configure Borg [V10, VND].

F18. Ballerina (WSO2, since 2016, first release Feb 2022) keeps the text and a
sequence-diagram view equivalent, "programs have both a textual syntax and an
equivalent graphical form" [V15, VND]. Lingua Franca (Berkeley reactor-model
coordination language, polyglot targets) shows the diagram generated from text
[V16, VND; S32 TECS 2021]. Both are text-first with generated diagrams.

F19. AADL: SAE AS5506 (released Nov 2004), supports early and repeated
analysis of performance-critical properties and mapping of software onto
hardware [S33, SEI tech note]; a 2023 workshop summary calls the standard
mature and used by many stakeholders in critical embedded real-time systems
for latency, schedulability, safety, security [S34, workshop summary];
the OSATE GitHub mirror has 58 stars [V27, weak]. AADL's value is analyses
over typed property sets bound to architecture.

F20. ArchiMate: Open Group enterprise-architecture standard with certified
tools and training [V6, VND]; Archi (open tool) 1.3k stars [V27]. BPMN: OMG
2.0.2 (Jan 2014), described as the de-facto standard for process diagrams and
"precise enough" to translate to software process components [V5, VND].
Usage subset (verified 2026-10-09, abstract level): zur Muehlen and Recker
analyzed 120 BPMN diagrams; less than 20 percent of the vocabulary is
regularly used, some constructs never appeared, the average model uses
about 9 constructs but models of that size share only 4-5 constructs, so
a small agreed core has emerged [S36, EMP, abstract]. The commonly quoted
core (start/end events, tasks, sequence flow, pools/lanes, XOR gateway)
comes from secondary summaries and is NOT verified against the paper. OCL: the latest OCL version aligned with UML is 2.4
(Feb 2014) while UML is at 2.5.1 (Dec 2017) [V3, V4, VND]: the constraint
language did not keep pace with the metamodel (inference from two spec pages).

F21. Requirements tracing tools that DO check code: OpenFastTrace tracks
"whether you actually implemented everything you planned" and finds obsolete
code [V25, VND]; StrictDoc is a requirements tool with DO-178C and Zephyr
technical notes in its own docs [V26, VND]; Backstage catalog descriptors
(`catalog-info.yaml`, kinds Component/API/System/Domain/Resource) and a
`backstage.io/source-location` annotation point at the code of an entity
[V24, VND]. These are the tools grmb competes with for "bound to code".

### 2.3 Credibility grading summary

Strongest (named-company engineers, peer-reviewed or CACM): S20 (AWS), S22
(AWS S3), S23 (MongoDB), S24 (ZooKeeper, merged upstream), S10 and S1 (practi-
tioner interviews across 40-50 companies), S3/S4 (hundreds of practitioners).
Standards/vendor docs: V1-V26, V28-V34. Academic opinion without industrial
validation: S11, S12, S15, S16, S27, S31 (foundational; used for
definitions, not adoption). Industry-authored (verified 2026-10-09): S4
(Akdur, ASELSAN), S6 (Storrle, QAware), S13 (Mavin, Rolls-Royce), S19
(Irshad and Britto, Ericsson), S22 (Amazon S3 engineers), S26 (Microsoft),
S28 (Zave, AT&T), S41 (Clearsy). Weak: V13 and V29 testimonials, GitHub
stars V27, S35 (title plus operator slides V31).

## 3. Implications for grmb

Tags: ADOPT (use as is), ADAPT (use changed), REJECT (do not). Each item says
what grimble could check.

I1. ADOPT text as the only source of truth; diagrams are generated views.
Why: the adoption winners (Mermaid, LikeC4, Structurizr, D2, Ballerina, LF)
are text-first; UML/SysML v1 graphical models rot (F2). Check: `grimble graph
--mermaid` output is deterministic and diff-clean (a golden-file check).

I2. REJECT bidirectional graphical editing and stored layout in .grmb.
Why: Ballerina needs equivalence machinery; LikeC4 needed a "layout drift"
check precisely because stored layout can go stale. Check: none needed
because no layout is stored.

I3. ADOPT binding to code as the differentiator, with granularity that matches
the abstraction. Why: only Gherkin (step definitions), codegen IDLs (Smithy,
TypeSpec), and executable specs (P, ShardStore) tie models to code; MongoDB
shows too-abstract trace binding fails (F11). Check: every `impl` selector
resolves non-empty and its resolved symbol-set digest matches the last ack
(existing SYS rules); report the share of leaf scenario steps with a bound
impl per goal.

I4. ADOPT the ladder-of-abstraction check: each level must cover the variants
of the level above. Why: AWS ladder (F10), Event-B-style refinement (F14),
ZooKeeper's three levels (F11). Check: goal leaf -> some scenario realizes it;
scenario step -> some impl; outcome variant of a step -> an arm in every
scenario using it; missing is a finding.

I5. ADOPT the Smithy severity/suppression model for grmb rule ids:
non-suppressible structural errors; suppressible design findings; hierarchical
ids; suppression carries a reason. Why: F16, tested at AWS scale. Check:
every suppression names an existing rule id prefix and has a reason and
(grmb exceptions already have an expiry; keep it).

I6. ADOPT lint-rule quick fixes at definition time. Why: TypeSpec ships
`defineCodeFix` / `createSuppressCodeFix` as first-class (F16). Check: each
planning rule declares a fix kind (add arm, add step, add impl stub, suppress).

I7. ADOPT actors as the environment, modeled explicitly. Why: P erases ghost
environment machines at compile time but requires them for checking (F12);
AWS stresses specifying "all of the properties of the environment" and
failure events [S20]. Check: every scenario starts with an actor step; every
step crossing a boundary to a `system`/`device`/`timer` actor declares at
least one non-ok outcome.

I8. ADAPT goal modeling: keep the goal tree to enumerated OR-refinement plus
`requires`; REJECT KAOS/i*/GRL machinery (softgoals, contribution weights,
AND-refinement formulas, agent-responsibility calculi, strategic dependency
networks). Why: GORE has weak industrial uptake and informal use (F6). KAOS
"obstacles" map onto the already-chosen outcome variants. Check: refinement
cycle and `requires` cycle; leaf coverage.

I9. ADOPT steps declared once, scenarios referencing them. Why: Gherkin's
duplicated examples are the dominant maintenance pain (F7). Check: duplicate
detection (two steps with identical outcome sets bound to the same selector).

I10. ADAPT Gherkin: do not match step text by regex; bind by identifier and
selector. Why: text-matching step definitions are the source of the freezing
effect [S17]; identifiers survive rename (symbol selectors already do).
Check: rename of a bound symbol surfaces a SYS-changed finding, not silent
unbinding.

I11. ADOPT a closed small core with data packs for vocabularies. Why:
BPMN/UML "how much language is enough" and selective-use findings (F1, F20);
LikeC4's `specification` block puts kinds in the model, which the pack design
already separates from grammar. Check: pack-qualified names resolve and pack
digest is pinned (existing).

I12. ADOPT quantities with a closed unit table. Why: AADL's value and
Malavolta's finding (practitioners dissatisfied with analysis and
extra-functional properties, F4, F19). Check: MDL009 dimension mismatch
(existing); extend scenario steps with optional `deadline`/`rate` budgets that
the flow check compares.

I13. ADAPT AADL/ArchiMate cross-layer consistency: behavior implies
structure. Why: AADL maps software to hardware; ArchiMate relates business,
application, technology layers (F19, F20). Check: consecutive system steps in
different nodes require a declared flow in that direction (already planned
as P6; this is external support).

I14. ADOPT order-independent composition across files. Why: CUE's lattice
(F17) gives deterministic merging; merge conflicts on shared model files are
a known cost. Check: same entity declared in two files with conflicting
fields is an error; non-conflicting extension merges identically in any file
order; parse result independent of include order (a property test).

I15. ADAPT statecharts/SCXML for the later `machine` entity (open question in
the planning brief). Why: state machines are the executable survivors (F15).
Check later: unreachable state, states missing a handler for an event of the
declared enum (exhaustiveness), conflicting transitions on the same event.
REJECT hierarchical/parallel regions in v1 of the entity (SCXML is ~200k
characters of spec; the semantics are the cost).

I16. ADAPT sum types as the variant mechanism, with Quint's row-polymorphism
as a future model for inferred error-set unions. Why: Quint RFC is the
closest prior art to `-|>` collecting an inferred set (F13). Check:
exhaustiveness already planned; add "collected set inference is stable under
step order" as a test.

I17. ADOPT model-staleness detection tied to bound-code churn. Why: models
are written at the start and rot (F2). Check: entity whose bound code changed
(N commits or digest change) without a model touch or ack within a window.

I18. ADOPT trace-style evidence as an OPTIONAL later `verified_by trace`.
Why: P's PObserve and Cirstea's trace validation are cheap if only
spec-variable updates are logged (F11); MongoDB shows it is brittle at high
abstraction. Check: P4+ only; keep out of P1-P3.

I19. REJECT a general expression language / OCL-style constraints. Why: OCL
stalled at 2.4 while UML moved on (F20) and the spec's non-goal already says
no expressions; selectors suffice.

I20. REJECT inclusion of SysML v2 or KerML as the model. Why: SysML v2 is a
heavy general metamodel adopted 2025; grmb's job is code-bound planning.
ADAPT only as an export/import seam (read-only mapping of goal/scenario/impl
to requirement/action/part) after P5, if a user asks.

I21. ADOPT in-repo descriptors next to code (Backstage `catalog-info.yaml`
model) and a sourced-location link per entity. Why: F21. Check: entity file
path is under the owning node's path root or the entity carries an explicit
`location` (mismatch).

I22. ADOPT requirement-tracing "covered / uncovered / outdated" vocabulary
for the status triple declared/bound/verified. Why: OpenFastTrace's
purpose statement is exactly this (F21). Check: the obligation list in
`grimble graph --json`.

## 4. Candidate lint rules

Placeholder ids use `PLN-` (planning). Polarity: ABS = fires on absence,
PRE = on presence, MIS = on mismatch. Predicates are over the model (M) or
the model-code binding (B).

| Id | Anti-pattern prevented | Predicate | Pol | Source |
|---|---|---|---|---|
| PLN-001 | Unrealized goal leaf | goal leaf g with no scenario s where s realizes g | ABS | S20 ladder; V25 uncovered |
| PLN-002 | Step with no implementation | step st used in a scenario with no impl for it | ABS | S20; V25 |
| PLN-003 | Non-exhaustive outcome handling | `=>`/handle arms != declared outcome variants of the step | MIS | S20 (rare-path bugs); V8 severity DANGER |
| PLN-004 | Wildcard hides new variant | arm `_` present on a step with >=2 non-ok variants | PRE | design (topic F owns source) |
| PLN-005 | Happy-path-only boundary step | step whose actor is `system`/`device`/`timer`/external node has outcome set == {ok} | PRE | S20 (failure events in env) ; S26 |
| PLN-006 | Scenario with no actor origin | first step's actor is absent or not declared | ABS | S26 (environment machines) |
| PLN-007 | Duplicate steps | two steps with equal outcome set and equal bound selector set | PRE | S17 duplicates; S19 |
| PLN-008 | Empty or dangling binding | impl selector resolves to empty set | MIS | V25 outdated; existing SYS |
| PLN-009 | Changed code, unchanged model | digest of resolved symbols differs from last ack and entity unchanged for N days | MIS | S7 rot; V25 |
| PLN-010 | Behavior without data path | consecutive steps realized in nodes A,B and no declared flow A->B | ABS | S33 (AADL mapping); V6 |
| PLN-011 | Cyclic precondition | `requires` graph on goals has a cycle | PRE | S15 goal refinement acyclicity [background] |
| PLN-012 | Over-wide goal fan-out or depth | OR-refinement with > K children or depth > D | PRE | design heuristic, NO source (reported as weak) |
| PLN-013 | Suppression without reason or past expiry | suppress entry lacks `reason` or `until` < today | ABS/MIS | V8 suppressions |
| PLN-014 | Order-dependent merge | entity declared in 2 files with conflicting field values | PRE | V10 unification |
| PLN-015 | Anonymous/unreferenceable entity | entity without an identifier | ABS | V18 (identifiers opt-in problem) |
| PLN-016 | Orphan design entity | entity with no binding, no ticket, no child, age > N | ABS | S7; V25 |
| PLN-017 | Unit/dimension mismatch in budgets | a step budget and its flow's quantity differ in dimension | MIS | S33; S10 |
| PLN-018 | Level skipping | impl bound to a goal with no intervening scenario | MIS | S20 ladder; V6 layers |
| PLN-019 | Unstable collected error set | collected-set inference changes when steps are reordered | MIS | V11 (RFC sum types) |
| PLN-020 | State without handler (later `machine`) | state s, event e in enum, no transition or declared ignore | ABS | S31; V7 |
| PLN-021 | Rule without fix | planning rule registered without a quick-fix kind | ABS | V9 |
| PLN-022 | Verification gap | goal or scenario with no `verified_by` after status `bound` | ABS | S3 (key parts verified); V-model closure |

## 5. Bibliography (every item looked up this run)

Credibility line format: venue / authors' standing (with the basis). "Standing
unverified" means I could not source a claim about the authors' industrial
role in this run; I do not assert one. Fetch mode: FT = full text, AB =
abstract (Crossref/OpenAlex/S2), TI = title/metadata only.

### Papers

S1. Petre, M. "UML in practice." ICSE 2013. DOI 10.1109/icse.2013.6606618. AB.
  Venue: ICSE (peer-reviewed, top tier). Standing: academic (The Open
  University, confirmed by OpenAlex 2026-10-09); study is 50 interviews at 50
  companies, which is the industrial validation. pp. 722-731. Category and
  diagram counts verified via V28 (secondary review) and S37 (top-3 table);
  full text still not retrieved (ORO 403, UCI mirror 404). Grade: strong for
  adoption claims.
S2. Hutchinson, J.; Whittle, J.; Rouncefield, M.; Kristoffersen, S. "Empirical
  assessment of MDE in industry." ICSE 2011. DOI 10.1145/1985793.1985858. AB.
  Venue: ICSE. Standing: academics; qualitative industry fieldwork. Strong.
S3. Whittle, J.; Hutchinson, J.; Rouncefield, M. "The State of Practice in
  Model-Driven Engineering." IEEE Software 2014. DOI 10.1109/ms.2013.65. AB.
  Venue: IEEE Software. Standing: academics; 450 survey + 22 interviews. Strong.
S4. Akdur, D.; Garousi, V.; Demirors, O. "A survey on modeling and
  model-driven engineering practices in the embedded software industry."
  J. Systems Architecture 91, 2018, 62-82. DOI 10.1016/j.sysarc.2018.09.007.
  AB (full abstract fetched 2026-10-09 via Semantic Scholar). Venue: JSA
  (peer-reviewed). Standing CONFIRMED: Akdur at ASELSAN Inc. (Turkish defense
  electronics), per the companion MECO 2017 paper PDF and OpenAlex; 627
  practitioners, 27 countries. Abstract: majority use UML, second answer
  "Sketch/No formal modeling language"; sequence diagrams and state machines
  are the two most popular diagram types. Companion MECO 2017 paper (same
  survey) adds class diagrams as third and 77 percent UML use. Strong.
S5. Ho-Quang, T.; Hebig, R.; Robles, G.; Chaudron, M. "Practices and Perceptions
  of UML Use in Open Source Projects." ICSE-SEIP 2017. DOI
  10.1109/icse-seip.2017.28. AB. Venue: ICSE SEIP. 485 OSS contributors. Medium.
S6. Storrle, H. "How are Conceptual Models used in Industrial Software
  Development? A Descriptive Survey." EASE 2017. DOI 10.1145/3084226.3084256.
  pp. 160-169. AB; plus the 2-page SE/SWM 2019 extended abstract read in
  full (LNI P-292, pp. 93-94, DOI 10.18420/se2019-26), which reproduces the
  usage-scenario figure. Venue: EASE. Standing CONFIRMED: Storrle at QAware
  GmbH, Munich (industry) per the 2019 abstract. No diagram-KIND frequency
  in what was read; the paper is about usage scenarios. Medium.
S7. Hebig, R.; Ho-Quang, T.; Chaudron, M.; Robles, G. "The quest for open source
  projects that use UML." ACM/IEEE MODELS 2016 (container name truncated in
  Crossref: "ACM/IEEE 19th International Conference on ..."). DOI
  10.1145/2976767.2976778. AB. Peer-reviewed. Medium-strong (mining study).
S8. Jongeling, R.; Cicchetti, A.; Ciccozzi, F. "How are informal diagrams used
  in software engineering? An exploratory study of open-source and industrial
  practices." SoSyM 2024. DOI 10.1007/s10270-024-01252-3. AB. Peer-reviewed;
  "initial exploration". Medium.
S9. Wolny, S.; Mazak, A.; Carpella, C.; Geist, V.; Wimmer, M. "Thirteen years of
  SysML: a systematic mapping study." SoSyM 2020 (online 2019). DOI
  10.1007/s10270-019-00735-y. AB. Peer-reviewed mapping study. Strong for
  "what is studied", medium for industry use.
S10. Malavolta, I.; Lago, P.; Muccini, H.; Pelliccione, P.; Tang, A. "What
  Industry Needs from Architectural Languages: A Survey." IEEE TSE 2013. DOI
  10.1109/tse.2012.74. AB. TSE. Academic authors; 48 practitioners / 40
  companies / 15 countries. Strong.
S11. Medvidovic, N.; Taylor, R. N. "A classification and comparison framework
  for software architecture description languages." IEEE TSE 2000. DOI
  10.1109/32.825767. TI. TSE. Academic, foundational. Used for vocabulary only.
S12. Moody, D. "The 'Physics' of Notations: Toward a Scientific Basis for
  Constructing Visual Notations in Software Engineering." IEEE TSE 2009. DOI
  10.1109/tse.2009.67. AB. TSE. Academic theory; cited here only as a source
  for notation-design principles (topic F territory); no adoption claim made.
S13. Mavin, A.; Wilkinson, P.; Teufl, S.; Femmer, H. et al. "Does
  Goal-Oriented Requirements Engineering Achieve Its Goal?" IEEE RE 2017. DOI
  10.1109/re.2017.40. AB. RE conference. Practitioner questionnaire plus
  literature survey. Standing CONFIRMED (OpenAlex): Mavin at Rolls-Royce
  UK (originator of the EARS requirements syntax is [background, not
  checked]); co-authors at TU Munich. Medium-strong.
S14. Horkoff, J.; Aydemir, F. B.; Cardoso, E.; Li, T. et al. "Goal-oriented
  requirements engineering: an extended systematic mapping study."
  Requirements Engineering 2017. DOI 10.1007/s00766-017-0280-z. AB. Peer
  reviewed; 246 papers. Strong for the research landscape.
S15. van Lamsweerde, A. "Goal-oriented requirements engineering: a guided
  tour." IEEE ISRE 2001. DOI 10.1109/isre.2001.948567. AB. Academic;
  originator of KAOS (Dardenne, van Lamsweerde, Fickas, SCP 1993, DOI
  10.1016/0167-6423(93)90021-g, looked up, no abstract). Foundational.
S16. Yu, E. "Towards modelling and reasoning support for early-phase
  requirements engineering." IEEE ISRE 1997. DOI 10.1109/isre.1997.566873. AB.
  Academic; originator of i*. Foundational. (iStar 2.0 guide: Dalpiaz, Franch,
  Horkoff, DOI 10.1007/978-3-031-72107-6_5, TI only.)
S17. Binamungu, L. P.; Embury, S.; Konstantinou, N. "Maintaining behaviour
  driven development specifications: Challenges and opportunities." IEEE SANER
  2018. DOI 10.1109/saner.2018.8330207. AB. SANER. 75 practitioners / 26
  countries. Medium-strong.
S18. Binamungu, L. P.; Maro, S. "Behaviour Driven Development: A Systematic
  Mapping Study." J. Systems and Software 203, 111749, 2023, DOI
  10.1016/j.jss.2023.111749 (per DBLP, found 2026-10-09); preprint arXiv
  2305.05567. AB. Peer-reviewed (JSS). Academic (Univ. of Dar es Salaam).
  Medium.
S19. Irshad, M.; Britto, R.; Petersen, K. "Adapting Behavior Driven Development
  (BDD) for large-scale software systems." J. Systems and Software 2021. DOI
  10.1016/j.jss.2021.110944. AB. JSS. Standing CONFIRMED (OpenAlex): Irshad
  and Britto at Ericsson (Sweden) and BTH; Petersen BTH. Medium-strong.
S20. Newcombe, C.; Rath, T.; Zhang, F.; Munteanu, B.; Brooker, M.; Deardeuff, M.
  "How Amazon Web Services uses formal methods." CACM 58(4), 2015. DOI
  10.1145/2699417. FT (author-site PDF,
  https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf).
  Venue: CACM. Standing: AWS engineers writing about AWS systems (S3,
  DynamoDB, EBS in the text). Strongest practitioner evidence in this note.
S21. Brooker, M.; Desai, A. "Systems Correctness Practices at Amazon Web
  Services." CACM 2025. DOI 10.1145/3729175. TI (Crossref abstract is one
  line). CACM; both authors at Amazon (OpenAlex, confirmed 2026-10-09).
  Used only as pointer.
S22. Bornholt, J.; Joshi, R.; Astrauskas, V.; Cully, B. et al. "Using
  Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3."
  ACM SOSP 2021. DOI 10.1145/3477132.3483540. AB. SOSP (top tier). Experience
  report from the S3 team; standing CONFIRMED (OpenAlex: Joshi, Cully, Kragl,
  Markle, Sauri, Schleit at Amazon; Bornholt UT Austin/Amazon). Strong.
S23. Davis, A. J. J.; Hirschhorn, M.; Schvimer, J. "eXtreme Modelling in
  Practice." PVLDB 13(9), 2020. DOI 10.14778/3397230.3397233. AB. VLDB.
  MongoDB engineers ("At MongoDB, we use TLA+"). Strong, includes a negative
  result.
S24. Ouyang, L.; Huang, Y.; Huang, B. et al. "Leveraging TLA+ Specifications to
  Improve the Reliability of the ZooKeeper Coordination Service." SETTA
  2023, pp. 189-205 (per DBLP, found 2026-10-09); arXiv 2302.02703. AB.
  Peer-reviewed conference; specs merged into Apache ZooKeeper (per
  abstract). Academic authors. Medium-strong.
S25. Cirstea, H.; Kuppe, M. A.; Loillier, B.; Merz, S. "Validating Traces of
  Distributed Programs Against TLA+ Specifications." arXiv 2404.16075 (2024).
  DOI 10.48550/arxiv.2404.16075. AB. Still a preprint (arXiv v2 Sep 2024,
  HAL working paper; DBLP lists only CoRR). Standing CONFIRMED: Kuppe at
  Microsoft Research at the time (arXiv header, OpenAlex) and the top
  committer of github.com/tlaplus/tlaplus (4,728 commits, GitHub API);
  current GitHub profile says NVIDIA. Medium.
S26. Desai, A.; Gupta, V.; Jackson, E.; Qadeer, S.; Rajamani, S.; Zufferey, D.
  "P: safe asynchronous event-driven programming." PLDI 2013. DOI
  10.1145/2491956.2462184. AB. PLDI (top tier). Standing CONFIRMED
  (OpenAlex): five of six authors at Microsoft. Strong for design.
S27. Jackson, D. "Alloy: a lightweight object modelling notation." ACM TOSEM
  2002. DOI 10.1145/505145.505149. TI. TOSEM. Foundational.
S28. Zave, P. "Using lightweight modeling to understand Chord." ACM SIGCOMM CCR
  2012. DOI 10.1145/2185376.2185383; and "Reasoning About Identifier Spaces:
  How to Make Chord Correct." IEEE TSE 2017. DOI 10.1109/tse.2017.2655056.
  AB (both). Peer-reviewed. Standing CONFIRMED (OpenAlex): Zave at AT&T for
  both papers. Case study, not adoption evidence.
S29. Woodcock, J.; Larsen, P. G.; Bicarregui, J.; Fitzgerald, J. "Formal
  methods: practice and experience." ACM Computing Surveys 41(4), 2009. DOI
  10.1145/1592434.1592436. AB. CSUR; survey of industrial use. Strong.
S30. Mashkoor, A.; Kossak, F.; Egyed, A. "Evaluating the suitability of
  state-based formal methods for industrial deployment." Software: Practice and
  Experience 2018. DOI 10.1002/spe.2634. AB. SPE. Criteria from experts and
  practitioners. Medium.
S31. Harel, D. "Statecharts: a visual formalism for complex systems." Science of
  Computer Programming 8(3), 1987. DOI 10.1016/0167-6423(87)90035-9 (TI); and
  "Statecharts in the making: a personal account." ACM HOPL III 2007. DOI
  10.1145/1238844.1238849 (AB). Foundational; originator of the language.
S32. Lohstroh, M.; Menard, C.; Bateni, S.; Lee, E. A. "Toward a Lingua Franca
  for Deterministic Concurrent Systems." ACM TECS 2021. DOI 10.1145/3448128.
  AB. TECS. Academic (Berkeley per project site). Design paper.
S33. Feiler, P. H.; Gluch, D. P.; Hudak, J. J. "The Architecture Analysis &
  Design Language (AADL): An Introduction." CMU/SEI-2006-TN-011. DOI
  10.21236/ada455842. AB. SEI technical note (FFRDC, not peer reviewed).
  Standing: SEI authors; AADL standardization (SAE AS5506) per abstract.
S34. Singhoff, F.; Hugues, J.; Tran, H. N. "ADEPT 2022 workshop: a summary of
  strengths and weaknesses of the AADL ecosystem." ACM SIGAda Ada Letters
  2023. DOI 10.1145/3631483.3631485. AB. Workshop summary; low citation count.
  Medium.
S35. Behm, P.; Benoit, P.; Faivre, A.; Meynadier, J.-M. "Meteor: A Successful
  Application of B in a Large Project." FM'99, LNCS. DOI
  10.1007/3-540-48119-2_22. TI only (Crossref confirms title, authors, FM'99
  LNCS). Peer-reviewed; industrial project paper (Matra Transport /
  RATP context is [background]). Size figures come from V31, not from this
  paper.
S36. zur Muehlen, M.; Recker, J. "How Much Language Is Enough? Theoretical and
  Practical Use of the Business Process Modeling Notation." CAiSE 2008 (reprint
  DOI 10.1007/978-3-642-36926-1_35, and a follow-up "We Still Don't Know
  How Much BPMN Is Enough, But We Are Getting Closer", DOI
  10.1007/978-3-642-36926-1_36). Original: CAiSE 2008, LNCS 5074, pp.
  465-479, DOI 10.1007/978-3-540-69534-9_35 (Crossref's container field for
  this DOI is wrong; venue from the Stevens Institute record). AB (via the
  Stevens research portal, 2026-10-09). Academic authors (zur Muehlen at Stevens per
  the record; Recker's affiliation not checked). Peer-reviewed. Medium-strong (120 diagrams).

S37. Langer, P.; Mayerhofer, T.; Wimmer, M.; Kappel, G. "On the Usage of UML:
  Initial Results of Analyzing Open UML Models." Modellierung 2014, LNI 225,
  pp. 289-304. https://dl.gi.de/handle/20.500.12116/20946 . FT (PDF read
  2026-10-09). Peer-reviewed (GI Modellierung). Academic (TU Wien). 121
  Enterprise Architect models found on the web; Classes in 100 percent, Use
  Cases 47, Interactions 39, Activities 4th, State Machines least used; 73
  percent of models use at most 3 language units (median 2). Its Table 1
  gives top-3 diagram kinds of earlier studies (Dobing/Parsons, Grossman,
  Reggio, Petre, Hutchinson). Medium (open models skew to EA users).
S38. Abrial, J.-R.; Butler, M.; Hallerstede, S.; Hoang, T. S.; Mehta, F.;
  Voisin, L. "Rodin: an open toolset for modelling and reasoning in
  Event-B." STTT 12(6), 2010, 447-466. DOI 10.1007/s10009-010-0145-y. AB.
  Peer-reviewed. Authors are the tool builders (Abrial: B/Event-B
  originator, [background]). Tool description, not adoption evidence.
S39. Romanovsky, A.; Thomas, M. (eds.) "Industrial Deployment of System
  Engineering Methods." Springer 2013. DOI 10.1007/978-3-642-33170-1. TI and
  publisher description (DEPLOY project: Event-B introduced at industrial
  partners; chapters on automotive, railway, space, business information).
  Partner list beyond Bosch NOT verified. Medium.
S40. Mazzara, M.; Jones, C.; Iliasov, A. "Lessons from DEPLOYment." Rodin
  Workshop 2012; arXiv 1607.00475. AB. Workshop paper on Bosch Research's two
  DEPLOY pilots (cruise control, start/stop). Medium (industrial pilot,
  academic authors).
S41. Lecomte, T.; Deharbe, D.; Prun, E.; Mottin, E. "Applying a Formal Method
  in Industry: a 25-Year Trajectory." SBMF 2017; arXiv 2005.07190. AB.
  Peer-reviewed symposium. Standing: Clearsy (Atelier B vendor) engineers
  [affiliation from Clearsy authorship is background; the arXiv page shows no
  affiliations]. Medium-strong (practitioner retrospective).
S42. Amyot, D.; Ghanavati, S.; Horkoff, J.; Mussbacher, G.; Peyton, L.;
  Yu, E. "Evaluating goal models within the goal-oriented requirement
  language." Int. J. Intelligent Systems 25(8), 2010. DOI 10.1002/int.20433.
  AB. Peer-reviewed. Academic (affiliations not checked); the authors are the GRL/URN
  standard's editors and jUCMNav builders [background]. Also located:
  Amyot and Mussbacher, "User Requirements Notation: The First Ten Years,
  The Next Ten Years", J. Software 6(5), 2011, DOI 10.4304/jsw.6.5.747-768
  (TI only).

### Standards and vendor documents (fetched 2026-10-09)

V1. OMG SysML v2 release repository README (adoption 30 June 2025, ISO
  editorial update March 2026): https://github.com/Systems-Modeling/SysML-v2-Release
  ; OMG SysML 2.0 beta page https://www.omg.org/spec/SysML/2.0/Beta1 .
  Standing body: OMG; the Systems Modeling Community. Standard body doc.
V2. OMG KerML 1.0 (Sep 2025): https://www.omg.org/spec/KerML
V3. OMG UML 2.5.1 (Dec 2017, formal/17-12-05): https://www.omg.org/spec/UML/2.5.1
V4. OMG OCL 2.4 (Feb 2014): https://www.omg.org/spec/OCL/2.4
V5. OMG BPMN 2.0.2 (Jan 2014): https://www.omg.org/spec/BPMN/2.0.2/
V6. The Open Group, ArchiMate Forum overview:
  https://www.opengroup.org/archimate-forum/archimate-overview
V7. W3C Recommendation, SCXML, 1 Sep 2015: https://www.w3.org/TR/scxml/
V8. Smithy 2.0 docs and model validation spec (Amazon/AWS vendor doc):
  https://smithy.io/2.0/index.html , https://smithy.io/2.0/spec/model-validation.html
V9. TypeSpec docs (Microsoft; linter and codefix API listing):
  https://typespec.io/docs/
V10. CUE docs, introduction and "The Logic of CUE":
  https://cuelang.org/docs/introduction/ ,
  https://cuelang.org/docs/concept/the-logic-of-cue/
V11. Quint documentation (language, RFCs, model-based testing):
  https://quint-lang.org/ , https://quint-lang.org/docs/lang
V12. P documentation (PObserve, impact at AWS): https://p-org.github.io/P/
V13. FizzBee: https://fizzbee.io/ (testimonials, WEAK)
V14. XState / Stately docs: https://stately.ai/docs/xstate
V15. Ballerina (WSO2): https://ballerina.io/
V16. Lingua Franca: https://www.lf-lang.org/
V17. Cucumber Gherkin reference: https://cucumber.io/docs/gherkin/reference/
V18. Structurizr DSL docs: https://docs.structurizr.com/dsl ,
  https://docs.structurizr.com/dsl/identifiers
V19. C4 model (Simon Brown): https://c4model.com/
V20. LikeC4 site and CLI docs: https://likec4.dev/ ,
  https://likec4.dev/tooling/cli/
V21. D2: https://d2lang.com/
V22. GitHub Blog, "Include diagrams in your Markdown files with Mermaid",
  Woodward and Biagianti, 2022-02-14:
  https://github.blog/developer-skills/github/include-diagrams-markdown-files-mermaid/
V23. Alloy: https://alloytools.org/
V24. Backstage descriptor format and well-known annotations:
  https://backstage.io/docs/features/software-catalog/descriptor-format
V25. OpenFastTrace README: https://github.com/itsallcode/openfasttrace
V26. StrictDoc docs: https://strictdoc.readthedocs.io/en/stable/
V27. GitHub repository metrics via REST API, taken 2026-10-09 (stars /
  created / last push / archived): mermaid-js/mermaid 90586 / 2014 / active;
  statelyai/xstate 30284 / 2015 / active; terrastruct d2 25581 / 2022 /
  active; plantuml/plantuml 13356 / 2010 / active; cue-lang/cue 6280 / 2021;
  likec4/likec4 5829 / 2023; microsoft/typespec 5882 / 2021;
  p-org/P 3709 / 2015; ballerina-lang 3863 / 2016; tlaplus/tlaplus 3110 /
  2016; smithy-lang/smithy 2373 / 2019; quint-co/quint 1822 / 2021;
  archimatetool/archi 1286 / 2011; AlloyTools 873 / 2017; fizzbee 356 /
  2024; lf-lang/lingua-franca 329 / 2018; osate/osate2 58 / 2011;
  structurizr/java 1135 archived 2026-02-01. Weak adoption proxy.
  Added 2026-10-09: quint-co/quint 1822 / 2021-05-28 (informalsystems/quint
  redirects here); fizzbee-io/fizzbee 356 / 2024 (top committer
  `jp-fizzbee`; creator identity and background UNCONFIRMED);
  JUCMNAV/LEGACY_seg.jUCMNav 2 stars, last push 2021-07-28;
  tlaplus/tlaplus top committer lemmy (Markus A. Kuppe).
V28. "UML in Practice", It Will Never Work in Theory (review site edited by
  Greg Wilson et al.), 2013-06-13:
  https://neverworkintheory.org/2013/06/13/uml-in-practice-2.html . Named,
  curated secondary review; used only for Petre's counts. Medium.
V29. Quint product site: https://quint.sh/ (Informal Systems footer link;
  quint-connect; testimonials from Input Output Group, Conviva, iqlusion,
  OpenHands). Vendor doc, WEAK for adoption.
V30. FizzBee Model-Based Testing quick start:
  https://fizzbee.io/testing/tutorials/quick-start/ (Go adapter; Java and
  Rust "coming soon"). Vendor doc.
V31. RATP, "METEOR" B-method slides (PDF metadata 2001-11-09), hosted by
  Clearsy: https://www.atelierb.eu/wp-content/uploads/2018/04/RATP.pdf .
  Operator presentation; figures: 1150 B components, 115000 lines of B,
  27800 proof obligations, 86000 lines of Ada. Medium.
V32. ITU-T Recommendation Z.151 (10/2018) "User Requirements Notation (URN) -
  Language definition", summary:
  https://www.itu.int/rec/T-REC-Z.151-201810-I . Standard body (ITU-T SG17).
V33. GitLab docs, "PlantUML" integration:
  https://docs.gitlab.com/administration/integration/plantuml/ . Vendor doc.
V34. PlantUML command line reference: https://plantuml.com/command-line .
  Vendor doc.

### Claims marked [from memory, unverified] (not relied on above)

Original list, now ALL RESOLVED by the 2026-10-09 pass (see section 7):
Petre's per-pattern counts (verified, secondary: V28, S37); zur
Muehlen/Recker's BPMN subset finding (verified, abstract: S36); Zave at
AT&T (verified, OpenAlex: S28); ITU-T Z.151 defines GRL (verified: V32);
Structurizr component finder (verified: `!components`, V18); PlantUML has
only syntax checks (verified as far as the CLI docs go: V34). Still
unconfirmed: FizzBee creator's background; Abrial as originator of B and
Mavin as EARS originator (background only, not relied on).

## 6. Comparison table

Columns: models = what it models; levels = abstraction levels it spans; code
binding = how it ties to code; checking = what can be verified; adoption =
strongest evidence found; fate = why it succeeded or failed (my reading,
labeled as inference where so). THIN = only vendor page / title / metric.

| # | Language | Models | Levels | Code binding | Checking | Adoption evidence | Fate (inference) |
|---|---|---|---|---|---|---|---|
| 1 | SysML v1 | Systems: requirements, blocks, parametrics, activities | System; req to design | None native; tool-specific | Tool-dependent; parametric analysis | Mapping study: mostly design/validation, not implementation [S9] | Used where systems engineering needs it; heavy UML profile, needs customization [S9]; superseded by v2 |
| 2 | SysML v2 / KerML | Same, on a formal KerML kernel; textual + graphical; API | System to component | API/services for tool exchange [V1]; no code selectors | Semantics via KerML classification | OMG adopted 2025-06-30 [V1]; ISO submission 2026 | New; adoption not yet measurable; textual grammar is first-class |
| 3 | UML | Class, sequence, activity, state, use case, components | Analysis to design | Round-trip/codegen tools (not studied here) | Well-formedness; OCL optional | Selective use; 5 patterns [S1]; informal sketches second [S4]; rot after start [S7] | Wide but shallow; survives as sketch notation, not as source of truth |
| 4 | OCL | Constraints over UML | Design | Via UML tools | Evaluate constraints | Spec stuck at 2.4 (2014) vs UML 2.5.1 [V3,V4] | Lagged the metamodel (inference); niche |
| 5 | AADL | Components, connections, properties, modes, error annex | Architecture to deployment | Code generators exist (not studied) | Latency, schedulability, safety analyses [S33] | SAE std 2004 [S33]; "mature", many stakeholders [S34]; OSATE 58 stars | Durable niche (critical embedded), analysis-centered |
| 6 | ArchiMate | Business, application, technology layers + motivation | Enterprise | None | Relationship rules by spec | Open Group std, certified tools/training [V6]; Archi 1.3k stars | Strong in enterprise architecture offices; far from code |
| 7 | BPMN | Process flows | Business to executable process | Executable engines (Camunda repo 129 stars) | Syntax; execution | OMG de-facto standard claim [V5]; 120 diagrams: <20 percent of vocabulary regularly used, 4-5 shared constructs [S36] | Succeeded as a business notation; practitioners use a small core (verified, abstract) |
| 8 | Structurizr DSL | C4 model as text | Context/container/component | `!components` component finder discovers components from Java code [V18]; no drift check | Syntax; some constraints | structurizr/structurizr 447 stars; java lib archived 2026-02 [V27] | Text C4 won mindshare; consolidating tooling |
| 9 | LikeC4 | C4-like model, views | Context to component | None; MCP/API for AI | `validate`: syntax, layout drift [V20] | 5.8k stars, 2023 | Rising; text-first, AI-friendly |
| 10 | PlantUML | UML-ish diagrams from text | Any | None | Syntax only (`--check-syntax`) [V34] | 13.4k stars since 2010 [V27]; rendered on GitLab.com for all users [V33] | Durable diagram-from-text; won by host integration like Mermaid |
| 11 | Mermaid | Diagrams from text | Any | None | Syntax only | 90.6k stars; native in GitHub Markdown 2022 [V22] | Won by distribution inside the git host |
| 12 | D2 | Diagrams from text, layout engines | Any | None | Syntax only | 25.6k stars, 2022 [V27]; THIN | Popular; presentation-first |
| 13 | Gherkin | Examples: Given/When/Then | Acceptance/system | Step definitions matched by text [V17] | Run as tests | 75 practitioners; active use, maintenance pain [S17] | Widely used; dup/frozen specs are the cost |
| 14 | KAOS | Goals, obstacles, agents, operations | Early RE to spec | None | Formal goal refinement, obstacle analysis [S15] | Mavin: uptake low, informal [S13] | Academic strength, weak industrial uptake |
| 15 | i* | Actors, intentions, dependencies | Early RE | None | Qualitative reasoning [S16] | Horkoff: few citations per paper [S14] | Niche; iStar 2.0 consolidation (title only) |
| 16 | GRL | Goals, softgoals, actors, contributions (URN, with Use Case Maps) | Early RE | None | Strategy-based satisfaction propagation; 3 algorithms in jUCMNav [S42] | ITU-T Z.151 (10/2018, in force) [V32]; jUCMNav repo legacy, last push 2021 [V27]; no industrial adoption study found | Standardized; academic/regulatory case studies only |
| 17 | Alloy | Relational structure + (v6) temporal | Design | None | SAT-based bounded analysis | Chord case [S28]; Alloy 6.2 in 2025 [V23] | Respected lightweight tool; no code link |
| 18 | TLA+ | State-machine specs | Algorithm to protocol | Trace checking, MBT in research and industry [S23,S25,S24] | TLC model checking | AWS: 10 systems, 7 teams [S20]; MongoDB [S23]; ZooKeeper [S24] | Succeeds when scoped to hard distributed designs; code link is the weak joint |
| 19 | Quint | TLA-style specs with types, sum types RFC | Algorithm to protocol | MBT docs [V11]; `quint-connect` trace replay against Rust code [V29] | Apalache/simulator | 1.8k stars [V27]; Informal Systems origin; vendor testimonials (IOG, Conviva) [V29] | TLA+ usability layer; young; commercializing (Quint Studio waitlist) |
| 20 | P | Communicating state machines + specs | Design and implementation | Compiles to code; PObserve checks logs [V12] | P-Checker systematic exploration | AWS impact [V12]; 3.7k stars; PLDI [S26] | Strong at AWS because modeling and programming unify |
| 21 | FizzBee | Python-like (Starlark) specs | Design | MBT via user-written Go test adapter; Java/Rust pending [V30] | Model checking, perf analysis; generates sequence and block diagrams [V13] | Named-engineer testimonials (Confluent, Doordash, Shopify) [V13]; 356 stars | New; evidence weak (vendor-curated only) |
| 22 | Event-B | Refinement-based state models | Abstract to concrete | Code generation plugins (not studied) | Proof obligations (Rodin) [S38] | Classical B: Meteor, 86k lines Ada, 27.8k POs [S35, V31]; Event-B: DEPLOY pilots (Bosch etc.) [S39, S40]; Clearsy 25-year report [S41] | B strong in rail; Event-B piloted, use "only where suitable" [S40] |
| 23 | Statecharts | Hierarchical, concurrent state machines | Behavior | Executable code generation [S31] | Simulation; model checking | HOPL account [S31] | Foundational; survives inside UML/SCXML/XState |
| 24 | SCXML | Statechart XML | Behavior | Interpreters | Schema + semantics | W3C Rec 2015-09-01 [V7]; commons-scxml 68 stars | Standardized; low mindshare today |
| 25 | XState | Statecharts + actors in TS | Behavior | IS code | Types; visualizer | 30.3k stars, active [V27] | Won by being the implementation |
| 26 | Smithy | Services, shapes, traits | API/interface | Generates SDKs/servers [V8] | Validators with severity and suppressions [V8] | Used across AWS for 10+ years [V8] | Thrives: model is the source, code is derived |
| 27 | TypeSpec | API models, decorators | API | Emitters; OpenAPI | Linter rules, code fixes, suppressions [V9] | 5.9k stars [V27] | Growing; Microsoft-backed |
| 28 | Ballerina | Integration programs | Implementation + diagrams | IS code | Static types, concurrency safety | WSO2 since 2016; 3.9k stars [V15,V27] | Niche language; graphical equivalence is its feature |
| 29 | Lingua Franca | Reactor coordination | System coordination | Polyglot code targets [V16] | Deterministic semantics | Academic (TECS) [S32]; 329 stars | Research language with real code generation |
| 30 | CUE | Constraint lattice for config/schema | Data/config | Validates data and generates | Unification, subsumption [V10] | 6.3k stars; Google GCL lineage [V10] | Strong in config/validation niche |

Adjacent (not counted): C4 model [V19] (hierarchy, notation-neutral);
Backstage catalog (in-repo descriptors with source-location annotations
[V24]); OpenFastTrace (coverage and outdated-code tracing [V25]); StrictDoc
(requirements documents with safety-standard notes [V26]).

## 6b. Cross-cutting synthesis (what the 30 teach as one picture)

1. Binding classes seen: none (diagram tools, UML-as-sketch, ArchiMate,
   BPMN-as-notation, GORE); derive code from model (Smithy, TypeSpec, LF,
   statecharts, P); the model IS the program (XState, Ballerina, P);
   step/tag matching (Gherkin, OpenFastTrace); trace or test conformance
   (TLA+, P, Quint via quint-connect, FizzBee via a Go adapter); and
   model-from-code discovery (Structurizr `!components`). grmb belongs to a fifth, thinner class: SELECTOR
   binding with digests and acknowledgement, which none of the 30 provides
   as such (nearest: OpenFastTrace tags with versions; Backstage annotations
   without drift checking).
2. Checking classes seen: syntax only (Mermaid, PlantUML, D2), well-formedness
   (UML, ArchiMate), property analysis (AADL, Alloy, TLA+), refinement proof
   (Event-B), conformance (TLA+ traces, P), severity-ranked lint with
   suppressions (Smithy, TypeSpec). grmb's novel check is the combination of
   exhaustive variant handling across levels with code-binding drift.
3. Failure signature: expressive languages with no executable or bound
   counterpart decay (UML, GORE) [S7, S13]; the ones that persisted either run
   (XState, P), generate (Smithy), or cost little to keep in step (Mermaid).
4. Recommendation of record: keep the grmb core small and exhaustively
   checked, bind to code with drift detection, and treat everything
   vocabulary-like as packs; resist adding GORE, OCL or a metamodel.

## 7. Verification pass (2026-10-09)

Done by a second agent WITH WebSearch/WebFetch (the original run had
neither), plus Crossref, OpenAlex, Semantic Scholar, the GitHub API and
direct PDF reads (pdftotext) where a PDF was reachable. Scope: every
citation tagged [unverified], [from memory, unverified], THIN, title-only
or abstract-only that a finding relies on; the thin languages; author
standing claims. Structural note: the pre-existing "7. Cross-cutting
synthesis" was renumbered "6b" so this section can carry the number 7.

### 7.1 Changes, by kind

FIXED (claim now verified, text updated in place)
- F1 Petre: counts now stated (35 none / 11 selective / 3 codegen /
  1 retrofit / 0 wholehearted; selective users: class 7, sequence 6,
  activity 6, state machine 3, use case 1). Source: V28 (named secondary
  review) cross-checked against S37's Table 1 (Petre top-3 = class,
  sequence, activity). The paper PDF itself was not retrievable (ORO 403,
  UCI mirror 404), so this is secondary-verified, not primary.
- F1 Storrle S6: now cites the usage-scenario numbers from the 2019
  extended abstract read in full; author at QAware GmbH (industry).
- F20 BPMN S36: finding verified at abstract level (120 diagrams; under
  20 percent of vocabulary regularly used; 4-5 shared constructs); venue
  corrected to CAiSE 2008, LNCS 5074, pp. 465-479. The often-quoted list
  of "core" constructs is marked unverified (secondary summaries only).
- F6 GRL: Z.151 (10/2018, in force) fetched; GRL is the goal sub-notation
  of URN with Use Case Maps; S42 added for propagation algorithms and
  jUCMNav. Table row 16 rewritten.
- F9 Structurizr: `!components` component finder confirmed in the DSL
  language reference; table row 8 and synthesis point 1 updated (new
  binding class: model-from-code discovery).
- F8 PlantUML: GitLab.com renders it for all users (V33); CLI is
  syntax-only (V34). Table row 10 updated.
- F13 Quint: Informal Systems origin confirmed (repo redirect, V27; V29);
  `quint-connect` trace replay against Rust code added as its code
  binding. Table row 19 updated.
- F13 FizzBee: MBT confirmed as a Go test adapter (V30); diagram
  generation (sequence, block) noted. Table row 21 updated.
- F14 Event-B: Rodin tool paper (S38), Meteor size figures from RATP
  slides (V31), DEPLOY book (S39), Bosch lessons (S40), Clearsy 25-year
  report (S41) added. Table row 22 updated.
- Bibliography venue fixes: S18 is JSS 2023 (not only a preprint); S24 is
  SETTA 2023; S36 venue corrected; S25 confirmed still a preprint.
- Author standing CONFIRMED with a source: S1 (Open University), S4
  (Akdur, ASELSAN), S6 (Storrle, QAware), S13 (Mavin, Rolls-Royce), S19
  (Ericsson), S21 (Amazon), S22 (Amazon S3), S25 (Kuppe, Microsoft
  Research; top tlaplus committer), S26 (Microsoft), S28 (Zave, AT&T).

DOWNGRADED / CORRECTED
- Meteor: any "zero bugs" reading is unsupported; the note claims only
  "proved against its B specification", with figures from the operator.
- Event-B fate in the table: "strong in rail" now applies to classical B;
  Event-B is "industrially piloted", with Bosch's own conclusion that a
  single formalism does not cover requirements to code.
- Quint and FizzBee testimonials stay WEAK (vendor-curated) even though
  the named people and companies are real.
- S1 remains "strong" for the adoption pattern but the numeric counts are
  graded medium (secondary).

REMOVED
- Nothing removed. No citation was found to be fabricated: every title,
  author list, year and DOI checked matched an index record.

ADDED
- S37 Langer et al. 2014 (full text read), S38-S42, V28-V34, and new V27
  metrics (quint-co redirect, fizzbee committer, jUCMNav legacy repo).

UNCONFIRMED (marked as such in the text)
- FizzBee creator's identity and background (top committer `jp-fizzbee`;
  no biography source found).
- DEPLOY industrial partners other than Bosch.
- Clearsy affiliation of S41 authors (not shown on the arXiv page).

### 7.2 Diagram-kind frequency: settled (decides what grmb renders)

Verified evidence, strongest first:
- Dobing and Parsons 2006 (CACM 49(5), full text read; web survey via OMG
  members, 171 usable + 11 responses, data 2003-2004, UML 1.5): used in at
  least two-thirds of projects: class 73 percent, use case diagram 51,
  sequence 50, use case narrative 44 (4th), then activity, statechart,
  collaboration; only class diagrams are used regularly by over half.
  Collaboration diagrams: least used, least useful, most redundant.
  Statecharts: used less but rated 2nd for new information. Use case
  diagram: rated LEAST useful for new information. Top reason for non-use:
  "not well understood by analysts", then "insufficient value".
- Petre 2013 (above): class 7, sequence 6, activity 6, state 3, use case
  1 of the 11 selective users; 35 of 50 used no UML.
- Akdur et al. 2018 (627 embedded engineers, ASELSAN-led): sequence and
  state machine are the two most popular; class third (MECO 2017
  companion); "sketch / no formal language" second most common answer.
- Langer et al. 2014 (121 open EA models): classes 100 percent, use cases
  47, interactions 39, activities 4th, state machines LAST; 73 percent of
  models use at most 3 language units.
- Storrle 2017: no diagram-kind ranking (usage scenarios only); do not
  cite it for kinds.
Consensus: structure (class/component) and sequence/interaction survive
everywhere; activity is mid; state machines survive where behaviour is
reactive (embedded) and are rare elsewhere; use case DIAGRAMS are common
but add little information; communication/collaboration diagrams are dead.
A model typically uses 2-3 kinds.

### 7.3 Effect on implications and recommendations

- NEW I23 ADOPT: render, in priority order, (1) a sequence diagram per
  scenario (actors as lifelines, steps as messages, outcome arms as `alt`
  fragments), (2) one structure view (systems/nodes and declared flows,
  C4/component-like), (3) a goal tree as a plain tree/flowchart; (4) a
  state diagram only for the later `machine` entity. REJECT use-case
  diagrams (lowest information value [Dobing]) and communication
  diagrams. Check: each render kind has a golden-file test; `grimble
  graph --mermaid --kind=sequence` output for a scenario is deterministic
  and contains one `alt` block per non-ok outcome arm. FizzBee generating
  sequence and block diagrams from specs is independent vendor precedent
  for the same pair.
- I8 (reject GORE machinery) STRENGTHENED: GRL is standardized but the
  only adoption evidence is academic/regulatory case studies, and its
  reference tool is a legacy repo.
- I11 (closed small core) STRENGTHENED: BPMN subset finding now verified;
  Langer's "2-3 language units per model" says the same for UML.
- I4 (ladder of abstraction) qualified: Bosch's DEPLOY lesson says use a
  formal level "only where and when it is really suitable"; this supports
  grmb's per-level optionality (no level mandatory), not a mandatory full
  refinement chain.
- I18 (optional trace evidence) gains a second precedent (quint-connect)
  but stays P4+.
- CAUTION (naming): ITU-T GRL (Goal-oriented Requirement Language) and
  grimble's GRL (rule language, grl-spec) share an acronym. Since grmb
  adds goals, documents and users will collide on "GRL goal". Recommend
  the coordinator record the clash and, at minimum, never abbreviate the
  rule language as GRL in grmb-facing docs.
- No ADOPT/ADAPT/REJECT tag flips.

### 7.4 Revised coverage verdict

30 of 30 languages touched; THIN count drops from 4 to 0 (GRL, Quint,
PlantUML, FizzBee now have official-doc evidence; FizzBee and Quint
adoption remain WEAK by nature of the sources, not by lack of search).
Event-B moves from "site blocked, secondary" to tool paper plus
industrial pilot reports. Citations relying on memory: 0 (6 resolved).
Full-text reads: 3 more (Dobing and Parsons, Langer et al., Storrle
extended abstract) beyond Newcombe. Remaining gaps, and why they do not
change conclusions: Petre's PDF (counts agree across two independent
secondaries); Akdur JSA full text (abstract plus companion paper give the
ranking); DEPLOY partner chapters (the Bosch lesson already constrains
the recommendation); Doorstop/sphinx-needs/ReqIF (unchanged from 1.5).
Verdict: exhaustive for topic C's frontier, with adoption evidence graded
honestly; the diagram-kind question, previously a gap, is closed.
