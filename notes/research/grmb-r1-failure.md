# grmb R1, topic B: failure modes and architectural anti-pattern lints

Ticket ~19SEHXJ, researcher B. Date 2026-10-09. ASCII only. Not committed.

Verification pass 2026-10-09: citations, author standing and
practitioner gaps were re-checked with web search; section 7 lists
every change. In-place edits below are marked [v2026-10-09].

Honesty header: this is NOT a fully exhaustive sweep. The web-search and
arxiv MCP tools were not available in this run (ToolSearch returned no
match). All verification was done with curl against Crossref, OpenAlex,
Semantic Scholar, arxiv.org search, usenix.org and vendor doc sites. Unread
and unverified items are listed in section 1.4 and tagged in the
bibliography. Where a claim rests on a title only it says so.

## 1. Scope and search log

### 1.1 Field enumeration (Phase 0, done before reading)

Sub-fields of "what goes wrong in design and architecture", each treated as
a node; status at end of run:

| # | Node | Status |
|---|---|---|
| 1 | Erosion/drift/decay: definitions, causes, symptoms | done (mapping study + practitioner study + 3 primary) |
| 2 | Architectural smell catalogs and detectors (Garcia, Arcan, Designite, Mo hotspots) | done |
| 3 | Conformance checking: reflexion, DSMs, constraint languages, surveys of practice | done |
| 4 | Conformance tool docs: ArchUnit, import-linter, dependency-cruiser, jQAssistant | done (ArchUnit, import-linter, dependency-cruiser, jQAssistant fetched) |
| 5 | Fitness functions (Ford/Parsons/Kua) | blocked: book, not retrievable; concept covered through ArchUnit/jQAssistant docs |
| 6 | Architectural technical debt | done (Kruchten, Besker, de Toledo x2) |
| 7 | Microservice smells and anti-patterns | done (Taibi x2, Bogner, de Toledo) |
| 8 | Distributed-system failure studies (error handling, partitions, outages) | done (Yuan, Alquraan, Gunawi) |
| 9 | Requirements/use-case defects, traceability completeness | done (Femmer, Rempel/Maeder; Anda title only) |
| 10 | Ticket-to-code link quality | done (Bachmann, Herzig) |
| 11 | Documentation staleness | done (Aghajani) |
| 12 | Organisational causes (Conway) | partial: Nagappan located, abstract unreadable (paywalled) |
| 13 | LSP/Lattix/Structure101/Sonargraph/NDepend/Deptrac/Tach commercial lists | not read: no stable fetchable primary source this run |
| 14 | Visibility systems (Bazel visibility, Java modules) | blocked: Bazel doc page returned no usable text; not cited |

Denominator: 14 nodes. Done 10 (rows 1-4, 6-11). Partial 1 (row 12).
Blocked or unread 3 (rows 5, 13, 14). Pending 0 (every node has a status).

### 1.2 Queries run

- Crossref `query.bibliographic` lookups (title + authors) for every cited
  paper (about 55 queries); OpenAlex `works/doi:` for abstracts of 30+;
  Semantic Scholar `graph/v1/paper/DOI:` for 5 abstracts.
- arxiv.org/search (HTML) queries: "microservices anti-patterns taxonomy",
  "architectural smells Arcan", "architecture erosion symptoms",
  "architectural technical debt", "architecture conformance checking",
  "fitness functions evolutionary architecture", "architecture drift LLM
  coding agents", "architecture decision records empirical",
  "architectural violations detection tool evaluation industrial",
  "microservice smells detection tool", "design documentation outdated code
  inconsistency", "requirements to code traceability completeness defects",
  "architecture erosion mapping study", "architectural smells cyclic
  dependency hub-like". The arxiv search engine is noisy (it returned
  unrelated 2026 items for several queries); relevant hits were kept,
  noise discarded.
- Full-text reads (pdftotext): Taibi et al. taxonomy (arXiv 1908.04101),
  Li et al. practitioners (arXiv 2103.11392), Li et al. mapping study
  (arXiv 2112.10934), Yuan et al. OSDI 2014, Esposito et al. (arXiv
  2406.17354, for Arcan smell definitions).
- Vendor docs fetched: ArchUnit user guide (sections 1, 8.6, 10.4),
  import-linter contract types, dependency-cruiser rules reference
  (orphans, circular, reachable, moreUnstable, numberOfDependents),
  jQAssistant manual (baseline management).

### 1.3 Excluded and why

- Anonymous blogs and vendor marketing pages: excluded by brief.
- Papers I recall but could not look up (see 1.4): not cited as evidence.
- Pure code-smell literature (Fowler-style class-level smells): excluded
  except where it bears on architecture (Fontana 2019 shows architectural
  smells are NOT derivable from code smells, which is why grmb needs its
  own model-level predicates rather than reusing a code linter).
- Results concerning ML architecture drift or LLM-agent drift (arXiv
  2026): none of the hits was a venue-reviewed study on design/code drift;
  the topic is open (see 4.3 on why grimble is positioned for it).

### 1.4 Unread / unverified, and why it would not change conclusions

- Ford, Parsons, Kua "Building Evolutionary Architectures" (O'Reilly,
  fitness functions): book, not indexed in Crossref; concept is
  independently evidenced by ArchUnit/jQAssistant docs and by the rule
  forms in section 4.
- Nygard "Release It!" (stability patterns: timeouts, circuit breakers,
  bulkheads), Deutsch "Fallacies of distributed computing", Martin "Agile
  Software Development" (stable-dependencies principle): books/notes, not
  retrievable; the instability metric is verified second-hand through the
  dependency-cruiser `moreUnstable` doc (which quotes Martin) and the
  Arcan smell definition. The timeout/partition lint (FM-10) is grounded
  on Yuan/Alquraan/Gunawi instead.
- Bazel visibility, Lattix/Structure101/NDepend/Sonargraph/Deptrac/Tach
  docs: not retrievable; they are variants of rule forms already covered by
  ArchUnit, import-linter and dependency-cruiser.
- Mo/Cai/Kazman TSE full text and Rempel/Maeder method details: abstracts
  only. Thresholds are therefore left configurable, never hard-coded.
- Hotspot detector tool (DV8) docs: not fetched.

Coverage argument: the three families of conformance rule (dependency
direction/layering, cycles/instability/hubs, absence/convergence) are each
backed by at least one peer-reviewed study AND at least two independent
tools; the domain-specific families (error-handling, partition, ticket-link)
are backed by large empirical failure studies. Remaining unread items are
tool-doc variants and books whose content is represented by those sources.

## 2. Findings

Evidence grades: E = empirical study, X = experience/case report, V = vendor
doc, O = opinion. Credibility lines follow each citation group in the
bibliography (section 5).

F1. Implementations drift from intended architecture even in de novo
commercial development, during the initial implementation, and detecting
the divergence does not by itself cause its removal. Reflexion modelling in
that case study even concealed some inconsistencies. [E, in-vivo
longitudinal case study; v2026-10-09: the abstract scopes the
non-removal finding to "this small, informal team"] Rosik et al.
2010/2011 (SPE). Consequence for grmb:
a conformance finding is necessary but not sufficient; it must become a
tracked obligation (a ticket, a close guard), which is exactly the frob
join in the planning brief section 6.

F2. Reflexion models (Murphy, Notkin, Sullivan) compare a high-level model
with a source model via a mapping and report where the two agree and
disagree; applied to design conformance, change assessment and a
million-line Microsoft Excel reengineering. [E+X] TSE 2001. This is the
design-time ancestor of the grimble binding relation: a node->code mapping
(`owns`), declared flows, and a diff of declared against observed edges.

F3. In a systematic mapping of 73 studies, 34.2 percent of detection
approaches were consistency-based, and 14 of those 25 used architecture
conformance checking; erosion symptoms fall in four classes (structural,
violation, quality, evolution) and violation symptoms include "divergence"
(edge in code not in the design) and "absence" (edge in the design not in
code). Non-technical causes matter as much as technical ones. [E, SMS]
Li et al. 2022 (JSEP), read in full text (arXiv 2112.10934).

F4. Practitioners rarely have dedicated erosion tools; they detect erosion
through symptoms, and causes cited include lack of management skills, lack
of knowledge of the current architecture, lack of communication, high
turnover, technical debt accumulation, and business/time pressure. [E,
online-community mining + 10 survey + 4 interviews; small n] Li et al.
ICPC 2021. Consequence: checks must run where developers already are
(CI, review) and speak in symptoms they recognise (cycle, hub, violation).

F5. In 21,274 reviewed code-review comments from OpenStack Nova and
Neutron, 502 discussed erosion; the most frequent symptoms were
architectural violation, duplicate functionality and cyclic dependency;
reviews usually fixed them but a few were ignored. [E] Li et al. ICSA 2022.
Ranks the lint rules by real-world frequency: violation, duplication,
cycle.

F6. Practitioner interviews (19 engineers) show architecture-consistency
checking is mostly informal; barriers are inability to quantify the effect,
near-invisibility to customers, reluctance to fix, and the large effort of
mapping the system to the architecture for formal tools. Tools should
support services and metadata artefacts, not only code. [E, interviews]
Ali et al. 2017 (EMSE). Consequence: mapping cost is the adoption killer;
grimble's selectors with specificity-ordered `owns` and FOREIGN-as-Warn
(binding.md 6.1) are the right shape; a first-run baseline is mandatory
(F13). Services/metadata being first-class entities argues for node kinds
and flow contracts in the core.

F7. Architectural smells are largely independent of code smells (very low
correlation across 19 code smells and 4 architectural smells), so code
linters do not substitute for design-level checks. [E] Fontana et al. 2019
(JSS). [v2026-10-09: abstract confirmed via the Tampere repository;
corpus is the 111 Qualitas Corpus projects per the authors' dataset.]

F8. Arcan (Fontana et al., ICSA-W 2017) detects dependency-based
architectural smells with graph-database queries and was perceived as
useful by real developers; later reported validation [v2026-10-09
corrected]: manual validation on ten OSS and four industry projects, and
100 percent precision with 63 percent recall in two industrial case
studies judged by the developers, the misses being smells involving
external components outside the tool's scope (secondary statement,
arXiv 2303.17862; primary tables unread). Smells used: Unstable Dependency (a stable
component depends on a less stable one), Hub-Like Dependency (an
abstraction with many incoming and outgoing dependencies), Cyclic
Dependency. [E/V] The detection is a query over a dependency graph: the
same substrate as grimble's symbol graph + owner map.

F9. Architecture anti-patterns defined from design-rule theory (Baldwin and
Clark) and detected from structure plus revision history, including Unstable
Interface and Implicit Cross-module Dependency (files that co-change
without a declared structural dependency), are significantly associated
with bug-proneness and change-proneness over 19 large projects; the more
anti-patterns a file is in, the worse; Unstable Interface and Crossing
contribute most. An industrial case study confirmed the detector found the
architects' known pain points. [E] Mo et al. WICSA 2015 and TSE 2021.
Only evidence in this note that a history-aware (git) rule predicts
defects; it justifies a co-change rule (FM-12).

F10. The microservice anti-pattern catalog from interviews with
practitioners (72 developers for the 11 smells of IEEE Software 2018; a
taxonomy of 20 anti-patterns in the 2019 chapter). Perceived harmfulness
(0-10, Table 1.1): Hardcoded Endpoints 8, Wrong Cuts 8, Cyclic Dependency
7, API Versioning 6.05, Shared Persistence 6.05, ESB Usage 6, Megaservice
6, Inappropriate Service Intimacy 5, No API-Gateway 5, Shared Libraries 4,
Microservice Greedy 3. [E, interview/survey; perception not measured
defects] Taibi et al. Detection hints given there are structural (e.g.
"lack of semantic versions in APIs").

F11. Industry case studies of architectural technical debt in microservices
(about 1000 services in one large company; 25 interviews at seven large
companies) found business logic in the communication layer, large numbers
of point-to-point connections, shared databases that break services on
schema change, and bad API design that couples teams. [X/E] de Toledo et
al. TechDebt 2019 and JSS 2021. Evidence for the shared-persistence and
point-to-point predicates.

F12. Microservice practitioners (17 interviews at 10 companies + 295 grey
literature items) rely on guidelines and test automation; they did not
mention architectural or service-oriented tools or metrics although their
hardest problems (service cutting, integration) were architectural; the
authors call for tools for continuous evaluation of service granularity and
dependencies. [E] Bogner et al. 2021 (EMSE). A gap grimble's node/flow
model fills.

F13. Rule roll-out in grown code bases produces hundreds to thousands of
violations; both ArchUnit (FreezingArchRule) and jQAssistant (baseline
file checked into VCS, entries auto-removed when no longer detected) ship a
ratchet: record existing violations, report only new ones, shrink when
fixed. [V] ArchUnit user guide 8.6; jQAssistant manual. Consequence: the
`accept` mechanism must be a ratchet with auto-staleness (a stale accept is
itself a finding).

F14. ArchUnit fails by default a rule whose should-part is evaluated
against an empty set ("somebody renames the package old to newer; the rule
now always passes and checks nothing"). [V] ArchUnit user guide 10.4. This
is exactly grimble's must_measure/vacuity design (binding.md section 6
header, SYS004); independent confirmation that deny-on-vacuity is the right
default.

F15. Tool rule vocabularies converge: import-linter has Forbidden,
Protected, Layers, Independence, Acyclic siblings contract types and
per-contract import ignore lists that error when unmatched;
dependency-cruiser has forbidden/allowed/required rules with conditions
circular, orphan, reachable, numberOfDependentsLessThan/MoreThan,
moreUnstable, couldNotResolve, dependencyTypes, scope folder-level.
ArchUnit adds layers, slices, cyclic dependency checks, and architecture
metrics. [V] vendor docs. These are the de facto feature set of the
conformance-check family; DCL (Terra and Valente 2009, SPE) is the
academic counterpart (a dependency constraint language so that violations
cannot erode silently). [E: real HR-system case]

F16. Catastrophic failures in distributed data-intensive systems (198
user-reported failures in Cassandra, HBase, HDFS, MapReduce, Redis): 92
percent of catastrophic failures were due to incorrect handling of
non-fatal errors; 58 percent could have been detected by simple testing of
error handling; 35 percent fall into three trivial patterns: handler empty
or only logging, handler aborts the cluster on an over-general exception,
handler contains FIXME or TODO. A static checker (Aspirator) found 143 bugs
and bad practices in 9 systems. [E] Yuan et al. OSDI 2014. Direct support
for the planning-layer decisions that arms are exhaustive and that wildcard
arms are warned, and for new rules about swallowed outcomes (FM-08).

F17. Of 136 network-partition failures in 25 distributed systems, the
majority had catastrophic effects (data loss, reappearing deleted data,
broken locks), manifested with little client input, and "the majority could
have been avoided by design reviews". [E] Alquraan et al. OSDI 2018.
[v2026-10-09: quote re-confirmed; the abstract adds they "could have been
discovered by testing with network-partitioning fault injection".] The
outage study of 32 services (597 outages, 2009-2015) catalogues causes and
impacts. [E] Gunawi et al. SoCC 2016. Design-time lesson: a step that
crosses a node boundary can fail (timeout, partition); a scenario whose
cross-node step has outcome {ok} only is a design omission detectable at
design time (FM-09).

F18. Requirements/design text can be linted: Requirements Smells (Smella)
reached average precision 59 percent and recall 82 percent (high variation)
across three industrial and one university case, "some smells were not
clearly distinguishable". [E] Femmer et al. 2017 (JSS). Natural-language
rules are noisy; use sparingly and as Advisory.

F19. Traceability completeness measurably reduces defects: across 24
medium-to-large OSS projects, multi-level Poisson regression showed that
traceability completeness for three of four studied activities
significantly lowers defect rate. [E, large] Rempel and Maeder 2017 (TSE).
Direct evidence for rolling goal->scenario->impl->code->test link
completeness into a checked metric.

F20. Links between issue trackers and code are unreliable: in an
exhaustively annotated 493-commit sample, links between bugs and bug-fix
commits are a biased sample (Bachmann et al. FSE 2010); in a manual study of
7000+ issue reports, 33.8 percent of bug reports were misclassified (feature,
doc or refactoring) (Herzig et al. ICSE 2013). [E] Consequence: frob must
not derive "ticket implements entity" from commit messages or ticket type;
the canonical `implements` field plus graph validation (planning brief
section 6) is the right design. A rule on ticket kind vs entity level is a
cheap sanity check on top.

F21. Documentation defects are mostly staleness/incorrectness, found by
mining 878 artefacts (mailing lists, Stack Overflow, issues, PRs); creation
and maintenance of documentation is "often neglected". [E] Aghajani et al.
ICSE 2019. Supports grimble's lock/ack drift rules (SYS006-SYS008) as the
mechanism that keeps design text honest.

F22. Code decay is statistically real in long-lived industrial code (15+
years of change history of a telephone switching system, millions of
lines), with perfective maintenance possibly retarding it. [E] Eick et al.
2001 (TSE). Design erosion causes (van Gurp and Bosch 2002 JSS; Perry and
Wolf 1992 as classic definition source) are cited for terminology only
(their abstracts were not retrievable, so no finding is attributed).

F23. Dependency-structure analysis at scale: DSM-based modularity metrics
distinguished Linux from Mozilla and showed a purposeful Mozilla redesign
increased modularity. [E] MacCormack, Rusnak, Baldwin 2006 (Management
Science); Sangal et al. OOPSLA 2005 (Lattix origin; abstract not read,
title only). Supports a numeric "propagation"/coupling rollup over the
node graph as an Advisory report, not a gate.

F24. Technical debt as a catch-all must be structured: Kruchten, Nord,
Ozkaya organise the landscape; Besker, Martini, Bosch unify a model of
architectural TD and review the literature (abstract unreadable, title and
venue only). [O/E, weak for details] Use only to justify that design
findings carry principal/interest-style severity and a ratchet, not to
justify any specific predicate.

## 3. Implications for grmb

Tags: ADOPT, ADAPT, REJECT. "Check" says what grimble evaluates.

I1. ADOPT the reflexion trichotomy as the vocabulary of the architecture
check: convergence (declared flow with matching code edge), divergence
(code edge between owners with no declared flow = SYS013), absence
(declared flow with no code edge). Check: edges of the symbol graph
projected through owner(i) against declared flows. Reason: F2, F3; absence
is the one half not in SYS001-SYS013 today.

I2. ADOPT findings-to-obligations, not findings-only: every divergence or
absence finding must be turnable into a ticket (frob plan) and a done
ticket may not close over an unresolved one. Check: frob close guard over
graph JSON. Reason: F1 (detection alone did not prompt removal).

I3. ADOPT first-run baseline ratchet with stale-entry detection for
`accept`. Check: every accept entry must still match a live finding, else
finding "stale accept". Reason: F13, F6.

I4. ADOPT deny-on-vacuity for every rule and selector (already designed).
Check: rule examined zero subjects while scope non-empty -> Unresolved.
Reason: F14.

I5. ADOPT cycle, hub, unstable-dependency, shared-persistence and
point-to-point checks as model-level rules over the node/flow graph (design
time) and as owner-projected rules over code edges (implementation time).
Check: graph algorithms on nodes+flows; the same on owner-projected edges.
Reason: F5, F8, F10, F11, F15.

I6. ADAPT instability and hub thresholds: never hard-code numbers; put
them in pack/profile config with default Advisory. Check: I = Ce/(Ca+Ce)
over node flows (formula quoted in dependency-cruiser doc from Martin).
Reason: F8, F15; thresholds unvalidated across domains.

I7. ADAPT history-aware co-change rule as an optional rule needing
`git log` (not part of the pure model-code binding): Implicit
Cross-module Dependency and Unstable Interface. Check: co-change count of
file pairs owned by different nodes with no declared flow; edits to a
`surface` selector that co-change with many dependents. Reason: F9 is the
strongest predictive evidence here, but cost and git dependence argue for
opt-in.

I8. ADOPT error-path obligations at the scenario level: no empty
arm, no wildcard arm without justification, no non-ok variant mapped to
`end ok` without a compensating step, cross-node steps may not have
outcome {ok} only. Reason: F16, F17. This extends the planning brief's
well-formedness rules with semantic lints that Yuan et al. showed
catastrophic in production.

I9. ADOPT traceability completeness as a first-class report and a
threshold rule (per level, per goal). Check: ratio of goals with
>=1 scenario, scenarios with >=1 impl, impls with non-empty selector,
each level with `verified_by`. Reason: F19; the planning brief already has
the obligations list, this adds the ratio and a configurable floor.

I10. ADOPT canonical-link-only for tickets and add a kind-vs-level sanity
check; REJECT commit-message or title heuristics as link source. Reason:
F20.

I11. ADAPT natural-language lint of `title` strings as an optional
Advisory pack; REJECT as core. Reason: F18 (precision 59 percent).

I12. REJECT organisational-metric rules (turnover, team ownership) in core.
Reason: F3/F4 say non-technical causes matter, but grimble has no reliable
signal; keep an `owner` attribute with a rule "node without owner" at most.

I13. ADAPT layering as sugar over flows: a `layer N` attribute on nodes
with the lint "flow against layer order"; do not make layers the only
mechanism. Reason: F15 (import-linter Layers; ArchUnit layers).

I14. ADAPT protected/visibility: a node's other-node-visible API is its
`surface` selector (SYS014); an edge into a non-surface symbol of a
different owner is a violation. Reason: F15 (import-linter Protected;
dependency-cruiser dependencyTypes). Needs the reserved SYS014.

I15. ADOPT orphan and reachability rules on the design graph: goal leaf
with no realizing scenario (already), impl never reached from an entry
step, page/entity with no inbound, impl bound to code with no inbound
references (dead realization). Reason: F15 (orphans, reachable doc says
orphans are "unused leftovers from a refactoring").

I16. REJECT absorbing microservice-specific smells (local logging, no
CI/CD, ESB usage) into the core; put them in a `microservices` pack keyed
on node kinds. Reason: F10 smells depend on deployment kinds that core
refuses to know (grimble-model.md 5 pack vocabulary).

## 4. Candidate lint rules

Format: id placeholder, anti-pattern, predicate, polarity (P+ fires on
presence, P- on absence, P0 on mismatch, per binding.md section 6), source,
default severity. All are Unknown/Unresolved-aware per binding.md section 6:
a subject with Unknown answer reports Unresolved, never clean.

### 4.1 Architecture (design model and binding)

| Id | Anti-pattern | Predicate | Pol | Source | Sev |
|---|---|---|---|---|---|
| FM-01 node-cycle | Cyclic dependency among nodes | the digraph of declared flows over nodes (and, separately, the owner-projected code-edge digraph) has a strongly connected component of size >= 2; one finding per SCC listing members; `via` allowlist for known knots | P+ | F5, F8, F10, F15 (Arcan CD, import-linter Acyclic siblings, dependency-cruiser circular) | Warn; Error under strict |
| FM-02 flow-absent | Declared flow with no observed code edge (reflexion absence) | flow A->B where A has code (owner non-empty) and B has code, and no symbol edge from A-owned to B-owned units exists in either direction; Unresolved if either owner has an opaque cone or F0 fidelity | P- | F2, F3 | Warn |
| FM-03 undeclared-edge | Divergence | existing SYS013; keep as-is, list here so FM-02 and SYS013 share one report | P+ | F2, F3 | Error |
| FM-04 hub-node | Hub-like dependency / god node | fan_in(n)+fan_out(n) over flows >= T_hub (profile config), n not marked `kind gateway` or `hub` | P+ | F8 (HL), F15 (numberOfDependentsMoreThan), F10 (Megaservice) | Advisory |
| FM-05 unstable-dep | Stable depends on unstable | for flow A->B with I(A) < I(B) (A more stable), by I = Ce/(Ca+Ce) on the node flow graph or an explicit `stability` attribute | P+ | F8 (UD), F15 (moreUnstable) | Advisory |
| FM-06 shared-store | Shared persistence | a node of kind `store` (pack vocabulary) is written or read by flows from >1 distinct non-store nodes outside an allowlist (`shared_by`) | P+ | F10, F11 | Warn |
| FM-07 uncontracted-boundary-flow | Missing API contract/versioning | a flow whose endpoints are in different nodes (or cross a `boundary`) has no `contract`, or its contract has no `version` facet | P- | F10 (API Versioning), F11 (bad API design) | Warn |
| FM-08 chatty-pair | Inappropriate service intimacy / wrong cut | pair of nodes with flows in both directions, or a scenario whose consecutive steps alternate between the same two nodes >= K times | P+ | F10 (Inappropriate Service Intimacy, Wrong Cuts), F11 (point-to-point explosion: count point-to-point flows per node over T_p2p) | Advisory |
| FM-09 scattered-goal | Scattered functionality (feature smeared over many nodes) | the impls realizing steps of ONE goal leaf span > T_scatter distinct nodes; dual: one node's impls realize steps of > T_conc unrelated top-level goals (feature concentration) | P+ | F10 (Wrong Cuts), F8/F23 (modularity); thresholds unvalidated | Advisory |
| FM-10 layer-inversion | Flow against layer order | node attr `layer` is totally ordered; flow from lower to higher layer not marked `callback` | P+ | F15 (Layers), Terra DCL | Warn |
| FM-11 surface-bypass | Deficient encapsulation / reaching past the API | edge from unit u (owner X) to unit v (owner Y != X) where v is not in the `surface` selector of Y | P+ | F15 (Protected); needs SYS014 | Warn |
| FM-12 implicit-coupling | Implicit cross-module dependency | for node pair (X,Y) with no declared flow in either direction, co-change rate of owned files over the last N commits >= T_cc (opt-in; needs git history) | P+ | F9 | Advisory |
| FM-13 stale-accept | Baseline entry that no longer fires | every `accept` entry matched against current findings; unmatched entry is a finding | P- | F13 | Warn |
| FM-14 vacuous-clause | Rule/selector that silently checks nothing | rule's subject set empty while scope not wholly NotApplicable (existing must_measure); extend to `verified_by` and `impl` selectors | P- | F14 | Error under must_measure |
| FM-15 orphan-impl | Unused leftovers | an `impl` whose bound code has no inbound edge from any entry-reachable unit, or a `page` with no inbound navigation edge | P- | F15 (orphans, reachable) | Advisory |

### 4.2 Scenario and planning layer (the grmb planning brief)

| Id | Anti-pattern | Predicate | Pol | Source | Sev |
|---|---|---|---|---|---|
| FM-20 swallowed-outcome | Handler that silences an error (Yuan pattern i) | an arm for a non-ok variant whose body is `end ok` with no intervening step, or empty | P+ | F16 | Warn |
| FM-21 wildcard-arm | Catch-all hides a new variant (already in brief) | arm `_` present in `=>` or `handle` | P+ | F16 (over-general catch) | Warn |
| FM-22 unmodeled-failure | Remote step cannot fail | step S realized in node N2 reached from a previous step in node N1 != N2, with outcome set {ok} only | P- | F17 | Warn |
| FM-23 unbounded-retry | Retry without bound/backoff | `retry` with no `max`, or `max` above T_retry; or retry of a step whose impl is not marked `idempotent` | P+ | F17 (partition/retry duplicates), weak (inference from failure studies) | Warn |
| FM-24 todo-arm | Unfinished handler (Yuan pattern iii) | an arm body, or a `title`/`note`, contains a placeholder marker, or the arm is bound to a ticket that is not done and whose entity is declared | P+ | F16 | Advisory |
| FM-25 happy-path-goal | Missing alternate flows | a goal leaf whose realizing scenarios' union of `end err(..)` and handled variants is empty | P- | F16, F17; Anda and Sjoberg (title only) as use-case-inspection precedent | Advisory |
| FM-26 unrealized-leaf-ratio | Traceability incompleteness | per level, completeness ratio = linked / total below profile floor | P- | F19 | Warn |
| FM-27 chain-gap | Broken goal->scenario->impl->code->test chain | any goal leaf with no path to a passing `verified_by` through scenario, impl | P- | F19 | Warn |
| FM-28 ticket-level-mismatch | Wrong link semantics | ticket `implements` points at an entity whose level (goal/scenario/impl) does not match the ticket kind (epic/story/task), or an `implements` target does not exist in graph JSON | P0 | F20 | Error for dangling; Warn for mismatch |
| FM-29 done-without-code | Closed ticket that left the entity unbound | ticket done, entity still `declared`, or diff touches none of the entity's bound code (already in brief) | P0 | F1, F20 | Warn (Error under strict) |
| FM-30 vague-title | Requirements smell | `title` contains a term from a configurable vague-word list | P+ | F18; precision ~59 percent, so Advisory and opt-in | Advisory |

### 4.3 Notes on polarity and false positives

- P- rules (absence) require Exact absence; a May-only or F0/F1 fidelity
  basis gives Unresolved (binding.md 6.1 pattern).
- Rules sourced to weak evidence (FM-09 thresholds, FM-23, FM-30, FM-12 in
  the absence of non-OSS validation) ship Advisory and off in strict
  profiles until measured on real models.
- The agentic angle (not an evidence-backed finding): LLM coding agents
  amplify drift because they edit code without the design in context; a
  checked binding plus lock/ack (SYS006-SYS008) is the mechanism that
  catches that. No venue-reviewed study was found in this run.

## 5. Bibliography and credibility grades

Every entry was located in Crossref/OpenAlex/Semantic Scholar/arxiv/usenix or
a vendor site during this run. Practical standing is stated only where the
fetched record itself supports it; otherwise "affiliation per record".
Tier A: peer-reviewed venue with industrial validation or large empirical
base. Tier B: peer-reviewed, academic or small-n. Tier V: vendor doc.

1. Murphy GC, Notkin D, Sullivan K. Software reflexion models: bridging the
   gap between design and implementation. IEEE TSE 27(4), 2001.
   DOI 10.1109/32.917525. Grade A. Venue: TSE. Standing: the abstract
   reports application to a million-line Microsoft Excel reengineering;
   author affiliations not verified.
2. Rosik J, Le Gear A, Buckley J, Ali Babar M, Connolly D. Assessing
   architectural drift in commercial software development: a case study.
   Software: Practice and Experience, 2010 (online; issue 2011).
   DOI 10.1002/spe.999. Grade B (commercial system, small informal team;
   abstract says so). Venue: SPE. [v2026-10-09: fifth author Connolly
   (IBM) added; abstract re-read via OpenAlex.]
3. Li R, Liang P, Soliman M, Avgeriou P. Understanding software architecture
   erosion: a systematic mapping study. J. Software: Evolution and Process,
   2022. DOI 10.1002/smr.2423; arXiv 2112.10934. Grade B+ (73 studies,
   full text read). Venue: JSEP. Standing: no company claim made.
4. Li R, Liang P, Soliman M, Avgeriou P. Understanding architecture erosion:
   the practitioners' perceptive. ICPC 2021. DOI 10.1109/icpc52881.2021.00037;
   arXiv 2103.11392. Grade B (small n survey/interviews, online posts).
5. Li R, Soliman M, Liang P, Avgeriou P. Symptoms of architecture erosion in
   code reviews: a study of two OpenStack projects. ICSA 2022.
   DOI 10.1109/icsa53651.2022.00011. Grade B+ (21,274 comments; OpenStack is
   a large industrial-backed OSS project but company claim not verified
   here).
6. Ali N, Baker S, O'Crowley R, Herold S, Buckley J. Architecture
   consistency: state of the practice, challenges and requirements.
   Empirical Software Engineering 23:224-258, 2018 (online May 2017).
   DOI 10.1007/s10664-017-9515-3. Grade A- (19 experienced practitioners
   from companies). Venue: EMSE. [v2026-10-09: author list completed;
   an erratum exists (open-access correction only).]
7. Garcia J, Popescu D, Edwards G, Medvidovic N. Identifying architectural
   bad smells. CSMR 2009. DOI 10.1109/csmr.2009.59. Grade A- (abstract:
   eighteen grid technologies reverse-engineered and refactoring of one
   large industrial system). Also: Toward a catalogue of architectural bad
   smells. QoSA 2009, DOI 10.1007/978-3-642-02351-4_10 (located, abstract not
   read).
8. Arcelli Fontana F, Pigazzini I, Roveda R, Tamburri D, Zanoni M, Di
   Nitto E. Arcan: a tool for architectural smells detection. ICSA
   Workshops 2017 [v2026-10-09: authors Zanoni and Di Nitto added].
   DOI 10.1109/icsaw.2017.16. Grade B+ (evaluated with real developers;
   later commercial product at arcan.tech per the Esposito et al. text).
9. Arcelli Fontana F, Lenarduzzi V, Roveda R, Taibi D. Are architectural
   smells independent from code smells? An empirical study. JSS 2019.
   DOI 10.1016/j.jss.2019.04.066. Grade B+.
10. Esposito M, Robredo M, Arcelli Fontana F, Lenarduzzi V. On the
    correlation between architectural smells and static analysis warnings.
    arXiv 2406.17354 (preprint; used only for the smell definitions and the
    Arcan validation sentence). Grade B- (preprint).
11. Mo R, Cai Y, Kazman R, Xiao L. Hotspot patterns: the formal definition
    and automatic detection of architecture smells. WICSA 2015.
    DOI 10.1109/wicsa.2015.12. Grade A- (abstract reports industrial case
    study with architect confirmation). Venue: WICSA.
12. Mo R, Cai Y, Kazman R, Xiao L, Feng Q. Architecture anti-patterns:
    automatically detectable violations of design principles. IEEE TSE
    47(5):1008-1028, 2021. DOI 10.1109/tse.2019.2910856. Grade A- (19
    large projects). [v2026-10-09] Standing: affiliations per record are
    academic (Central China Normal, Drexel, Univ. of Hawaii, Stevens);
    no industrial standing claimed; evidence base is 19 large projects
    plus the industrial case in item 11.
13. Taibi D, Lenarduzzi V. On the definition of microservice bad smells. IEEE
    Software 35(3), 2018. DOI 10.1109/ms.2018.2141031. Grade B+ (72 developers
    interviewed per abstract).
14. Taibi D, Lenarduzzi V, Pahl C. Microservices anti-patterns: a taxonomy.
    In Microservices: Science and Engineering, Springer 2019.
    DOI 10.1007/978-3-030-31646-4_5; arXiv 1908.04101 (read in full).
    Grade B (perception-based, practitioner interviews; harmfulness scores
    are opinions).
15. de Toledo SS, Martini A, Przybyszewska A, Sjoberg DIK. Architectural
    technical debt in microservices: a case study in a large company.
    TechDebt 2019. DOI 10.1109/techdebt.2019.00026. Grade A- (about 1000
    services, large international company; abstract). And: de Toledo SS,
    Martini A, Sjoberg DIK. Identifying architectural technical debt,
    principal, and interest in microservices: a multiple-case study. JSS
    2021. DOI 10.1016/j.jss.2021.110968. Grade A- (25 interviews, seven
    large companies).
16. Bogner J, Fritzsch J, Wagner S, Zimmermann A. Industry practices and
    challenges for the evolvability assurance of microservices. Empirical
    Software Engineering 2021. DOI 10.1007/s10664-021-09999-9. Grade A-
    (10 companies, 17 interviews, 295 grey literature items).
17. Yuan D, Luo Y, Zhuang X, Rodrigues GR, Zhao X, Zhang Y, et al. Simple
    testing can prevent most critical failures: an analysis of production
    failures in distributed data-intensive systems. USENIX OSDI 2014.
    https://www.usenix.org/conference/osdi14/technical-sessions/presentation/yuan
    (full text read). Grade A (OSDI; Cassandra, HBase, HDFS, MapReduce,
    Redis; 198 failures).
18. Alquraan A, Takruri H, Alfatafta M, Al-Kiswany S. An analysis of
    network-partitioning failures in cloud systems. USENIX OSDI 2018.
    https://www.usenix.org/conference/osdi18/presentation/alquraan
    Grade A. [v2026-10-09: authors (all University of Waterloo)
    confirmed from the USENIX page.]
19. Gunawi HS, Hao M, Suminto RO, Laksono A, Satria AD, Adityatama J,
    Eliazar KJ [v2026-10-09: full list]. Why does the cloud stop
    computing? Lessons from hundreds of service outages. ACM SoCC 2016.
    DOI 10.1145/2987550.2987583. Grade A- (597 outages of 32 services from
    public post-mortems).
20. Femmer H, Mendez Fernandez D, Wagner S, Eder S. Rapid quality assurance
    with requirements smells. JSS 2017. DOI 10.1016/j.jss.2016.02.047;
    arXiv 1611.08847. Grade B+ (three industrial contexts).
21. Rempel P, Maeder P. Preventing defects: the impact of requirements
    traceability completeness on software quality. IEEE TSE 43(8), 2017.
    DOI 10.1109/tse.2016.2622264. Grade A- (24 projects).
22. Maeder P, Egyed A. Do developers benefit from requirements traceability
    when evolving and maintaining a software system? Empirical Software
    Engineering 20(2):413-441, 2015. DOI 10.1007/s10664-014-9314-z.
    [v2026-10-09] Abstract content confirmed via JKU and GI records
    (https://research.jku.at/en/publications/do-developers-benefit-from-requirements-traceability-when-evolvin/):
    controlled experiment, 71 subjects, real maintenance tasks on two
    third-party projects; with traceability 24 percent faster and 50
    percent more correct solutions. Grade A- (controlled experiment,
    student-and-practitioner subjects mix not checked). Now supports F19.
23. Bachmann A, Bird C, Rahman F, Devanbu P, Bernstein A. The missing
    links: bugs and bug-fix commits. ACM FSE 2010. DOI 10.1145/1882291.1882308
    [v2026-10-09: Crossref lists five authors; Bernstein was missing].
    Grade B+ (Apache HTTP server, 493 commits).
24. Herzig K, Just S, Zeller A. It's not a bug, it's a feature: how
    misclassification impacts bug prediction. ICSE 2013.
    DOI 10.1109/icse.2013.6606585. Grade A- (7000+ reports, five projects).
25. Aghajani E, Nagy C, Vega-Marquez OL, Linares-Vasquez M, et al. Software
    documentation issues unveiled. ICSE 2019. DOI 10.1109/icse.2019.00122.
    Grade B+ (878 artefacts).
26. Eick SG, Graves TL, Karr AF, Marron JS, et al. Does code decay?
    Assessing the evidence from change management data. IEEE TSE 27(1),
    2001. DOI 10.1109/32.895984. Grade A (15+ year change history of a
    telephone switching system, per abstract).
27. MacCormack A, Rusnak J, Baldwin CY. Exploring the structure of complex
    software designs. Management Science 52(7), 2006.
    DOI 10.1287/mnsc.1060.0552. Grade B+ (Linux vs Mozilla).
28. Sangal N, Jordan E, Sinha V, Jackson D. Using dependency models to
    manage complex software architecture. OOPSLA 2005 (ACM SIGPLAN Notices).
    DOI 10.1145/1103845.1094824. Located; abstract not read. Grade B.
29. Terra R, Valente MT. A dependency constraint language to manage
    object-oriented software architectures. Software: Practice and
    Experience 2009. DOI 10.1002/spe.931. Grade B.
30. Passos L, Terra R, Valente MT, Diniz R, Mendonca NC. Static
    architecture-conformance checking: an illustrative overview. IEEE
    Software 27(5), 2010 (online 2009). DOI 10.1109/ms.2009.117. Grade B
    (overview of DSM, source query languages, reflexion).
    [v2026-10-09: fifth author added; abstract read.]
31. Knodel J, Popescu D. A comparison of static architecture compliance
    checking approaches. WICSA 2007. DOI 10.1109/wicsa.2007.1.
    [v2026-10-09] Abstract read (OpenAlex): compares reflexion models,
    relation conformance rules and component access rules along 13
    dimensions. Grade B. Supports F15 (rule vocabulary convergence).
32. Kruchten P, Nord RL, Ozkaya I. Technical debt: from metaphor to theory
    and practice. IEEE Software 29(6):18-21, 2012. DOI 10.1109/ms.2012.167.
    Grade B (landscape paper). [v2026-10-09] Standing: Kruchten,
    professor at UBC; Nord and Ozkaya,
    principal researchers at the CMU SEI (later bios). Affiliations at
    publication time not checked.
33. Besker T, Martini A, Bosch J. Managing architectural technical debt: a
    unified model and systematic literature review. JSS 2018.
    DOI 10.1016/j.jss.2017.09.025. Located; abstract unreadable. Grade B.
34. Perry DE, Wolf AL. Foundations for the study of software architecture.
    ACM SIGSOFT SEN 17(4), 1992. DOI 10.1145/141874.141884. Located only;
    cited for terminology. van Gurp J, Bosch J. Design erosion: problems and
    causes. JSS 2002. DOI 10.1016/s0164-1212(01)00152-2. Located only.
35. Nagappan N, Murphy B, Basili V. The influence of organizational structure
    on software quality: an empirical case study. ICSE 2008, pp. 521-530.
    DOI 10.1145/1368088.1368160; also MSR-TR-2008-11
    (https://www.microsoft.com/en-us/research/?p=153188). [v2026-10-09]
    Abstract content confirmed: on Windows Vista, organisational metrics
    were statistically significant predictors of failure-proneness, with
    precision and recall higher than churn, complexity, coverage,
    dependency and pre-release-bug metrics. Grade A (Microsoft
    Research authors, Microsoft product data); caveat: one company.
    Now a finding (F25, section 7).
36. Anda B, Sjoberg D. Towards an inspection technique for use case models.
    SEKE 2002. DOI 10.1145/568760.568785. [v2026-10-09] Abstract read:
    a taxonomy of use-case-model defects and a checklist inspection,
    evaluated with undergraduate students. Grade B- (student subjects).
    FM-25 support stays weak.
37. Newcombe C, Rath T, Zhang F, Munteanu B, Brooker M, Deardeuff M
    [v2026-10-09: full list; AWS engineers; the 2014 preprint reports use
    on 10 large systems]. How Amazon Web Services

    uses formal methods. CACM 58(4), 2015. DOI 10.1145/2699417. Located;
    abstract only: "Engineers use TLA+ to prevent serious but subtle bugs
    from reaching production." Relevant to topics C/D, cited here only as
    industrial evidence that design-time checking of failure modes is
    practiced. Grade A- by venue and company.
38. ArchUnit User Guide. https://www.archunit.org/userguide/html/000_Index.html
    (sections 1, 8.6 Freezing Arch Rules, 10.4 Fail Rules on Empty Should).
    Fetched. Tier V.
39. import-linter documentation, Contract types.
    https://import-linter.readthedocs.io/en/stable/contract_types/ Fetched.
    Tier V.
40. dependency-cruiser rules reference.
    https://raw.githubusercontent.com/sverweij/dependency-cruiser/main/doc/rules-reference.md
    Fetched (orphans, reachable, circular, moreUnstable, numberOfDependents).
    Tier V.
41. jQAssistant User Manual, Baseline Management.
    https://jqassistant.github.io/jqassistant/current/ Fetched. Tier V.

Credibility summary: strongest practitioner-scale evidence is Yuan (OSDI),
Gunawi (SoCC), Alquraan (OSDI), de Toledo (large companies), Ali (EMSE,
practitioners), Bogner (10 companies), Murphy (Excel). Weakest: perception
surveys (Taibi, Li ICPC), preprints (Esposito), and rules whose only
support is a located title (Anda, Besker, Sangal).

## 6. Phase-2 verdict

- Denominator 14 nodes; done 10; partial 1 (organisational causes, abstract
  paywalled); blocked/unread 3 (fitness-function book, commercial tool
  docs, Bazel visibility). No nodes pending.
- Completeness against the brief's list: ArchUnit, jQAssistant,
  dependency-cruiser, import-linter covered; Arcan, Designite (cited
  record only, abstract read), Lattix/DSM (Sangal and MacCormack; Lattix
  tool docs unread), reflexion models, fitness functions (via ArchUnit
  only), technical debt, distributed-system anti-patterns (via failure
  studies) and microservice smells covered. Not read: Designite
  architecture-smell definitions in full (only the tool abstract),
  Structurizr/Sonargraph conformance.
- Verdict: PARTIAL coverage, conclusions robust for the top candidates
  (FM-01..05, 11, 13, 14, 20..22, 26..29); lower-confidence candidates
  flagged Advisory.
- Strongest single recommendation: implement reflexion absence (FM-02) and
  the cross-node fallibility lint (FM-22) because they are the two checks
  the existing SYS rules and planning brief do not already cover and both
  have strong empirical backing (F2/F3 and F16/F17).

## 7. Verification pass (2026-10-09)

Verifier had WebSearch/WebFetch plus Crossref/OpenAlex/Semantic
Scholar APIs. Every [unverified] or "located only" entry, every
abstract-only source a finding relies on, and every author-standing
claim was re-checked. In-place edits carry the marker [v2026-10-09].

### 7.1 Fixed (in place)

- F1/item 2 Rosik: fifth author (Connolly) added; the non-removal
  finding is now scoped to "this small, informal team", as the
  abstract says. Year 2010 online, 2011 issue.
- F7/item 9 Fontana 2019: abstract confirmed; corpus is 111 Qualitas
  Corpus projects.
- F8/item 8 Arcan: two authors (Zanoni, Di Nitto) added; validation
  figures CORRECTED: manual validation was on ten OSS and four industry
  projects, and the 100% precision / 63% recall comes from two
  industrial case studies judged by developers (secondary source;
  primary tables unread). Earlier text said "ten OSS and two industry".
- F17/item 18 Alquraan: author list filled in (Takruri, Alfatafta,
  Al-Kiswany; Waterloo); quote re-confirmed.
- Item 1 Murphy et al.: the Excel claim is confirmed in the TSE
  abstract ("experimental reengineering of the million-lines-of-code
  Microsoft Excel product"). Affiliations still not checked.
- Item 6 Ali et al.: fifth author (Buckley), volume and pages added.
- Item 12 Mo et al.: fifth author (Feng) and pages added; affiliations
  are academic. The "[unverified]" industrial standing is resolved as
  "none claimed".
- Item 19 Gunawi: full seven-author list.
- Item 23 Bachmann: fifth author (Bernstein) was missing.
- Item 30 Passos: fifth author (Mendonca) added; online 2009.
- Item 31 Knodel/Popescu: was "abstract not read"; abstract now read.
- Item 32 Kruchten/Nord/Ozkaya: volume/pages; standing (see 7.2).
- Item 35 Nagappan: was "located only"; abstract content now
  confirmed and promoted to finding F25.
- Item 36 Anda/Sjoberg: abstract read; student subjects only.
- Item 37 Newcombe: full author list (adds Brooker, Deardeuff).
- Item 22 Maeder/Egyed: was "title only"; abstract content confirmed
  and promoted to finding F26.
- Section 6 named "Designite (cited record only, abstract read)" with
  no bibliography entry. Fixed: see item 49 and F36. Its architecture
  smell definitions are still unread.

### 7.2 Author standing

| Claim | Status | Source |
|---|---|---|
| Nord, Ozkaya at CMU SEI | CONFIRMED (principal researchers, later bios) | search results citing SEI bios |
| Kruchten at UBC | CONFIRMED (professor) | same |
| Ernst et al. SEI (practice file S48) | CONFIRMED | sei.cmu.edu library page |
| Kazman SEI | NOT CLAIMED; record lists Univ. of Hawaii | Stevens research record |
| Nagappan, Murphy (B.) at Microsoft Research | CONFIRMED (MSR technical report MSR-TR-2008-11) | microsoft.com/en-us/research |
| Sangal founded Lattix | WEAK (one profile site; MIT copy of the paper lists Sangal and Jordan at Lattix, Inc.) | groups.csail.mit.edu PDF; yourstory.com |
| Newcombe et al. at AWS | CONFIRMED by title and CACM abstract | cacm.acm.org |
| Nygard wrote Release It! | CONFIRMED (Pragmatic Bookshelf 2007, 2nd ed. 2018) | O'Reilly listing |
| Builders' Library retries author | PARTIAL: page byline "Marc", AWS employee; surname only in an excluded secondary summary | builder.aws.com |
| Gluck (Uber) | CONFIRMED on page: Sr. Software Engineer II, engineering strategy team | uber.com blog |
| Salzberg (Shopify) | CONFIRMED on page: Staff Developer | shopify.engineering |
| Westeinde, Ong, McGibbon (Shopify) | byline only, role not stated | shopify.engineering |
| Paul, Wang (Thoughtworks) | byline only, role not stated | thoughtworks.com |
| Ford/Parsons/Kua/Sadalage | authors confirmed; published as a Thoughtworks book; individual titles not checked | O'Reilly, thoughtworks.com |

### 7.3 Downgraded

- None of the findings F1-F24 had to be downgraded on substance. F8's
  numbers were corrected (7.1). FM-25's support stays weak (student
  subjects).

### 7.4 Removed

- Nothing removed. All DOIs resolved, titles matched.

### 7.5 Added findings (practitioner and tool gaps)

F25. Organisational structure predicts failures: on Windows Vista,
organisational metrics (for example number of engineers, number of
ex-engineers, edit frequency) were statistically significant
predictors of failure-proneness and beat churn, complexity, coverage,
dependency and pre-release-bug metrics on precision and recall.
[E, Microsoft Research on Microsoft data, one company] Nagappan,
Murphy, Basili ICSE 2008 (item 35).

F26. Traceability pays at the task level: in a controlled experiment
(71 subjects, real maintenance tasks on two third-party projects),
subjects with traceability were 24% faster and produced 50% more
correct solutions. [E, controlled experiment] Maeder and Egyed EMSE
2015 (item 22). Adds causal evidence to the correlational F19.

F27. Fitness functions: "An architectural fitness function provides
an objective integrity assessment of some architectural
characteristic(s)" (Ford's own workshop slides, search excerpt only;
the O'Reilly chapter returned 403). Thoughtworks practice (Paul and Wang): fitness
functions are agreed BEFORE implementation with business, compliance,
operations, security, infrastructure and development stakeholders,
written as tests with objective metrics, and run in delivery
pipelines as gates. Examples include observability (health endpoint,
tracing ids, parseable logs), resiliency (error rate during a rolling
update), compliance (no personal data in logs) and operability
(runbook exists). [X/O, consultancy with large-client practice, G2/G3]
(items 42, 43)

F28. Lattix design rules are Can Use, Cannot Use and Must Use; "Must
Use" fires when a required dependency is ABSENT. Rules set on a
subsystem are inherited by its children, and "inherited rules can be
overridden by new rules at lower levels". Exceptions carry a
description. An update report lists all, new and resolved violations,
and the command-line runner fits CI. [V] (item 44) This is a
commercial instance of reflexion absence (FM-02) and of hierarchical
rule scoping.

F29. Structure101 (Sonar since Oct 2024): layered architecture
diagrams of cells; dependencies point down by default; an "allows"
override is an approved exception; a Strict property limits a cell to
the level directly beneath; an Enforce property lets a diagram stay
unenforced while still being drafted; the headless check can fail the
build on violations, optionally only on NEW ones relative to a
baseline snapshot. [V] (items 45, 46)

F30. Bazel visibility: target visibility defaults to private (or the
package default_visibility); a violation fails the build at analysis
time; package_group names the allowed audience; transitive visibility
restricts even indirect dependents; .bzl load visibility exists since
Bazel 6.0. Stated purpose: separate a library's public API from its
implementation, and deprecate a public API by allowlisting existing
users while blocking new ones. Best practice: do not default to
public. [V, Google-originated build system] (item 47)

F31. Shopify Wedge (2019): in one of the largest Rails codebases
(more than a thousand developers, about 6,000 classes inventoried),
components were cut by business concept, each with a public interface
and exclusive data ownership; a CI tool built call graphs and
reported a per-component isolation score plus violation list;
enforcement was deliberately deferred until a component reached full
isolation. [X, named company] (item 48)

F32. Shopify Packwerk (2020) and its retrospective (2024): packages
with dependency and privacy checks and a per-package file listing
existing violations so that only new ones fail CI. Retrospective
lessons from the team that built it: privacy checks were REMOVED in
3.0 because they broke Rails conventions and "transformed Packwerk
into something it was never intended to be: an API design tool";
violation lists grew with each feature and "the rate at which
Packwerk was identifying problems ... vastly outpaced their capacity
to actually fix them"; a bug left stale entries unremoved; static
analysis missed require/autoload, runtime constants, routes and
fixtures, so a package with zero violations could still fail at
runtime; the clear success was isolating one base package to zero
violations and holding it with CI; Shopify has discussed removing
the tool. [X, named company, co-author a Staff Developer] (items 48b,
48c)

F33. Uber DOMA (2020): about 2,200 critical microservices grouped
into about 70 domains in five layers (infrastructure, business,
product, presentation, edge) with the rule "Layers only depend on the
layers under them"; each domain exposes a gateway, "a single
entry-point into a collection of underlying services"; "each domain
should be agnostic to other domains", with extensions instead of
cross-domain logic. Motivating pain: a root cause needing work across
about 50 services and 12 teams, roughly 10 touchpoints for a simple
feature, "networked monoliths". [X, named company and named engineer]
(item 50)

F34. Amazon Builders' Library on retries: "our best practice is to
retry at a single point in the stack" (five layers of three retries
multiply load 243x); "APIs with side effects aren't safe to retry
unless they provide idempotency"; limit retries locally with a token
bucket; derive timeouts from downstream latency percentiles (for
example p99.9 for a 0.1% false-timeout rate). [X/V, AWS first-party;
byline "Marc", AWS employee] (item 51)

F35. Architectural smells in industry persist: across nine embedded
C/C++ projects at a large industry partner and more than 30 releases
per project, smell instances were tracked for persistence and
overlap; 12 developers and architects said they hurt long-term
maintainability. [E, EMSE 2022] Sas, Avgeriou, Uyumaz (item 52).

F36. Design-smell catalogues and Designite: a 25-smell catalogue of
structural design smells organised by four design principles
(Suryanarayana, Samarthyam, Sharma, 2014); Designite flags
implementation, design and architecture smells (ICSE 2018 technical
briefing). Architecture-smell definitions not read. [O/V, weak]
(item 49)

### 7.6 Implication changes (including flips)

- FLIP, FM-11 surface-bypass: Warn -> Advisory, opt-in. Reason: F32,
  Shopify REMOVED privacy checks after they made Packwerk an API-design
  tool and produced unfixable violation piles; the success stories
  (F31 base package, F33 gateways, F29/F30 layering and visibility)
  enforce boundaries at a COARSE grain (domain gateway, package,
  layer), not per symbol. Revised I14: the core rule is "edge into a
  node group that bypasses its declared gateway node" (FM-38);
  per-symbol `surface` privacy stays available as an opt-in pack rule.
- FLIP, I12 (organisational metrics): REJECT -> ADAPT as an opt-in
  pack. Reason: F25 shows organisational metrics beat code metrics
  at Microsoft. grimble already has `owner` and git authorship, so
  FM-36 below is computable. Still Advisory: one-company evidence.
- STRENGTHENED, FM-02 reflexion absence: Lattix "Must Use" (F28) is a
  shipped commercial form of the same check. Recommendation to build
  FM-02 first is unchanged.
- STRENGTHENED, I3/FM-13 ratchet: Structure101 (F29), Lattix (F28)
  and Packwerk (F32) all baseline. Packwerk adds two cautions: stale
  entries were not removed (FM-13 is right to exist) and the baseline
  grew faster than it shrank. New FM-34 baseline-growth.
- UPGRADED, FM-23 unbounded-retry: from weak inference to a G2
  first-party AWS source (F34). Severity stays Warn. New FM-35
  retry-amplification.
- NEW, I17 ADOPT: hierarchical rule scoping. A rule attached to a node
  is inherited by its sub-nodes; a lower level may override it only
  with an explicit `allow` that carries a reason (F28 Lattix
  inheritance, F29 "allows" override). Check: an override without a
  reason is a finding.
- NEW, I18 ADOPT: Strict vs loose layering as a profile option of
  FM-10 (F29 Strict; F33 "layers only depend on the layers under
  them" is the loose form).
- NEW, I19 ADAPT: fitness functions are exactly "goal attribute +
  verified_by pointing at an executable check", agreed before
  implementation (F27). Check FM-36b: a goal-level quality attribute
  (budget, SLO, compliance label) with no verified_by is a finding at
  committed stage.
- NEW, I20 ADOPT: deprecation by allowlist (F30): a node or gateway
  marked `deprecated` lists current dependents; any new dependent is a
  finding (FM-37).
- NEW, I21 ADAPT: during migration report isolation as a ratio per
  node (F31) rather than failing; enforce only once a node reaches zero
  (mirrors Shopify's deferred enforcement and Structure101's Enforce
  flag, and lines up with the practice file's stage ladder I6).
- UNCHANGED: I1, I2, I4-I10, I13, I15, I16, FM-01..10, FM-20..30.

### 7.7 Added candidate lint rules

| Id | Anti-pattern | Predicate | Pol | Source | Sev |
|---|---|---|---|---|---|
| FM-34 baseline-growth | Ratchet that only grows | count(accept entries) increased over the last N commits while fixes (entries removed) stayed zero; or per-node accept count above profile T | P+ | F32 | Advisory |
| FM-35 retry-amplification | Retries at several layers | on one scenario path, more than one step carries `retry` toward the same downstream node (nested retry) | P+ | F34 | Warn |
| FM-36 ownership-spread (opt-in pack) | Organisational complexity on one node | distinct authors of the node's owned files in the window above T, or owner field names a departed owner | P+ | F25 | Advisory |
| FM-36b unverified-quality-attr | Fitness function declared but not executable | goal attr of kind budget/slo/compliance at committed stage with empty verified_by | P- | F27 | Warn |
| FM-37 deprecated-new-dependent | New use of a deprecated API | edge into a `deprecated` node or surface from a unit not in its frozen dependents list | P+ | F30 | Warn |
| FM-38 gateway-bypass | Reaching past a domain gateway | edge from outside node group G into a node of G that is not G's declared gateway | P+ | F33, F31, F30 | Warn |
| FM-39 override-without-reason | Silent exception to an inherited rule | `allow` at a lower node overriding an inherited rule with no reason text | P- | F28, F29 | Warn |

Revised severities: FM-11 surface-bypass Warn -> Advisory (opt-in);
FM-23 source upgraded to G2.

### 7.8 New bibliography entries

42. Neal Ford, Rebecca Parsons, Patrick Kua, Pramod Sadalage.
    "Building Evolutionary Architectures", 2nd ed. O'Reilly, Nov 2022.
    https://www.oreilly.com/library/view/building-evolutionary-architectures/9781492097532/
    (chapter 2 "Fitness Functions" returned 403; definition read from
    Ford's own slides
    https://nealford.com/downloads/Evolutionary_Architectures_workshop_by_Neal_Ford.pdf
    , seen as a search-result excerpt, not fetched; the same
    wording appears in a second excerpt, with "any mechanism" for
    "function").
    Thoughtworks book page
    https://www.thoughtworks.com/insights/books/building-evolutionaryarchitectures-second-edition .
    Tier: practitioner book, consultancy with large-client practice.
43. Paula Paul, Rosemary Wang. "Fitness function-driven development."
    Thoughtworks Insights, 2019.
    https://www.thoughtworks.com/insights/articles/fitness-function-driven-development
    Tier V/X (consultancy article; roles not stated).
44. Lattix. User Guide, "Monitoring and Enforcing Architecture" and
    "Rules Import/Export".
    https://docs.lattix.com/lattix/userGuide/Monitoring_and_Enforcing_Architecture.html ;
    https://docs.lattix.com/lattix/userGuide/RulesImportExport.html .
    Tier V. Lattix origin: Sangal, Jordan, Sinha, Jackson OOPSLA 2005
    (item 28; MIT copy https://groups.csail.mit.edu/sdg/pubs/2005/oopsla05-dsm.pdf
    now located; abstract summary: DSM extracted from code, design
    rules checked as code evolves, LDM tool, Haystack case study).
45. Structure101 Studio docs (Sonar): architecture perspective, diagram
    editor, diagram properties, headless check-architecture.
    https://docs.sonarsource.com/structure101/java/studio6/content/perspectives/architecture ;
    https://www.sonarsource.com/structure101/docs/cpa/studio7/content/perspectives/diagram-properties ;
    https://docs.sonarsource.com/structure101/java/studio6/content/cli/headless-checkarch .
    Tier V.
46. Sonar press release "Sonar Acquires Structure101 to Strengthen
    Code Quality Offering", 15 Oct 2024.
    https://www.sonarsource.com/de/company/press-releases/sonar-acquires-structure101-to-strengthen-code-quality-offering/
    Tier V.
47. Bazel documentation, "Visibility".
    https://bazel.build/concepts/visibility . Tier V (official).
48. Kirsten Westeinde. "Deconstructing the Monolith: Designing Software
    that Maximizes Developer Productivity." Shopify Engineering, 21 Feb
    2019. https://shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity
    Tier X (first-party; role not stated on page).
48b. Maple Ong. "Enforcing Modularity in Rails Apps with Packwerk."
    Shopify Engineering, 23 Sep 2020.
    https://shopify.engineering/enforcing-modularity-rails-apps-packwerk
    Tier X/V.
48c. Gannon McGibbon, Chris Salzberg (Staff Developer). "A Packwerk
    Retrospective." Shopify Engineering / Rails at Scale, 26 Jan 2024.
    https://shopify.engineering/a-packwerk-retrospective ;
    https://railsatscale.com/2024-01-26-a-packwerk-retrospective/ .
    Tier X (first-party post-mortem by the tool's builders).
49. Girish Suryanarayana, Ganesh Samarthyam, Tushar Sharma.
    "Refactoring for Software Design Smells: Managing Technical Debt."
    Morgan Kaufmann, 2014. https://www.oreilly.com/library/view/-/9780128013977/ .
    Designite: ICSE 2018 technical briefing "Detecting and Managing Code
    Smells: Research and Practice"
    https://2024.esec-fse.org/details/icse-2018/icse-2018-Technical-Briefings/8/Detecting-and-Managing-Code-Smells-Research-and-Practice-
    (Sharma: more than seven years at Siemens Research, per that page).
    Tier B-/V; smell list not read.
50. Adam Gluck. "Introducing Domain-Oriented Microservice Architecture."
    Uber Engineering, 23 Jul 2020.
    https://www.uber.com/en/blog/microservice-architecture/ . Tier X
    (first-party; author on Uber's engineering strategy team).
51. AWS Builders' Library. "Timeouts, retries, and backoff with jitter."
    https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
    (redirects to https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter ).
    Tier X/V (AWS first-party; byline "Marc").
52. Darius Sas, Paris Avgeriou, Umut Uyumaz. "On the evolution and
    impact of architectural smells - an industrial case study."
    Empirical Software Engineering 27, 2022.
    https://doi.org/10.1007/s10664-022-10132-7 ; arXiv 2203.08702.
    Grade A- (industrial, nine projects; partner unnamed).
53. Secondary source for the Arcan figures: arXiv 2303.17862
    ("Architecture Smells vs. Concurrency Bugs: an Exploratory Study
    and Negative Results"). Used only for F8's numbers.

### 7.9 Revised node status and coverage verdict

| # | Node | Before | After |
|---|---|---|---|
| 5 | Fitness functions | blocked | done (official excerpt via author slides + Thoughtworks article; book chapter 403) |
| 12 | Organisational causes | partial | done (Nagappan abstract content) |
| 13 | Commercial tools | not read | partial: Lattix and Structure101 done; Sonargraph, NDepend, Deptrac, Tach still unread |
| 14 | Visibility systems | blocked | done (Bazel); Java modules unread |
| new | Practitioner boundary enforcement at scale | - | done (Shopify x3, Uber, AWS) |

Denominator 15 nodes: done 14, partial 1 (row 13). Remaining unread:
Sonargraph/NDepend/Deptrac/Tach docs (variants of the Lattix/
Structure101/ArchUnit rule forms already covered), Java module
system, Designite architecture-smell definitions, "Release It!"
content, Deutsch fallacies, Besker et al. and van Gurp/Bosch
abstracts (no abstract in any index queried; machine-generated
summaries were not used). None of these is the sole support for a
rule.

Verdict: PARTIAL -> SUBSTANTIALLY COMPLETE. Top recommendation
unchanged (FM-02 reflexion absence and FM-22 cross-node fallibility
first). Two recommendations flip: FM-11 per-symbol privacy becomes
opt-in Advisory, replaced in core by coarse gateway-bypass FM-38
(Packwerk retrospective); organisational metrics move from REJECT to
an opt-in Advisory pack (Nagappan). FM-23 is upgraded to G2.
