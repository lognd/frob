# grmb R1, topic A (practice): what effective teams do in design

Ticket ~19SEHXJ, researcher A. Date of run: 2026-10-09. ASCII only.
Not committed (coordinator commits). Feeds docs/design/grmb-planning.md
(ticket ~83H49E3).

Verification pass 2026-10-09: citations, author standing and
practitioner gaps were re-checked with web search; section 7 lists
every change. In-place edits below are marked [v2026-10-09].

Honesty line (read first): this is NOT a provably exhaustive sweep.
Coverage is stated in section 1.4 with an explicit unread list. The
WebSearch/WebFetch tools were not available in this environment, so
discovery used the OpenAlex, Crossref, Semantic Scholar and arXiv
APIs plus direct curl fetches; general web search engines were
bot-blocked. Paywalled full texts (IEEE, ACM, Springer, Elsevier) were
mostly NOT read; for those only abstracts were read, and every claim
resting on an abstract alone is marked (abs).

---------------------------------------------------------------------

## 1. Scope and search log

### 1.1 Question

What do effective teams actually do from first idea to shipped
product, what do they abandon and why, and what does that imply for a
language (grmb planning layer) that must bind design to code and
tickets and CHECK it. Brief topic A list: design docs and RFCs,
ADRs, C4/arc42, event storming, domain storytelling, DDD, use cases,
story mapping, BDD/Gherkin, design reviews, and empirical studies of
modeling/documentation use.

### 1.2 Credibility scheme used in section 5

Per brief: peer-reviewed venue or standard/official vendor doc, plus
the authors' practical standing with a source. Grades:

- G1 = peer-reviewed empirical study (ICSE/FSE/ICSA/RE/ESEM/TSE/JSS/
  IEEE Software/EMSE/SoSyM class) with industrial participants or
  data.
- G2 = primary process document or experience report from a named
  organisation that shipped at scale (Google, Amazon, Uber, Rust,
  Python, Kubernetes, Swift, Basecamp, Thoughtworks, Microsoft/AWS
  vendor docs).
- G3 = practitioner/consultant opinion, or academic work without
  industrial validation, or preprint not yet peer reviewed.
- Excluded: anonymous blogs. Weak evidence is reported as weak.

### 1.3 Queries and corpora swept

Corpora actually queried (API or direct fetch):

- OpenAlex works search (about 45 queries), Crossref bibliographic
  search (about 20), Semantic Scholar by DOI (about 15), arXiv abs and
  pdf (6 papers read in full text via pdftotext: NaPiRE 1611.10288,
  Baltes/Diehl 1706.09172, Almeida et al. 2210.16089, Henderson
  1702.01715, plus abs pages for 2607.06471 and 2305.05567).
- Primary process documents fetched and read: Google "Design Docs at
  Google" (Ubl), Rust RFC 0002 and the rfcs README, PEP 1, Kubernetes
  KEP-0001 and kep.yaml template, Swift Evolution process.md, Google
  AIP-1 and api-linter README, Amazon "Working Backwards" (Vogels),
  Nygard ADR post, Thoughtworks Radar ADR entry, Azure Well-Architected
  ADR page, AWS Prescriptive Guidance ADR page, adr.github.io, C4
  site and FAQ, arc42 overview, Basecamp Shape Up ch. 2 and 4, Patton
  story-mapping page, Use-Case 2.0 Guide (full text via a web.archive.org
  copy of the Ivar Jacobson International PDF), Dan North "Introducing
  BDD", Cucumber Gherkin reference, Fowler "UML Mode", Pragmatic Engineer
  (Orosz) RFC/design-doc articles, iso-architecture.org 42010 pages.
- Queries run (representative, search log): "UML in practice
  Petre", "sketches and diagrams in practice", "UML open source
  practices perceptions", "software modelling survey Italian
  industry", "embedded MBE industrial survey", "software documentation
  issues", "technical debt practitioners", "naming the pain
  requirements engineering", "BDD maintenance", "documentation
  state of practice", "architecture documentation OSS", "ADR
  industry/MSR", "event storming empirical", "DDD SLR", "domain
  storytelling empirical", "BDD systematic mapping", "use case
  empirical", "requirements smells", "QUS user stories", "BDD
  quality smells", "architecture knowledge rationale survey",
  "architecture erosion practitioners", "traceability practice",
  "architecture and agile SMS", "whiteboard architects",
  "microservice decomposition DDD", "actor-driven decomposition".
- Excluded: anonymous blogs; vendor marketing pages with no process
  content; Medium posts (one, Y-statements, returned HTTP 403 and was
  not used); Stack Overflow opinion; any source not fetched or
  looked up in this run.

### 1.4 Coverage argument and what remains unread

Method: enumerate the topic-list families from the brief (13 named
practice families + empirical-study families), pick the primary
source or best peer-reviewed study for each, drain. Per family:

| Family | Primary/empirical source read | Depth |
|---|---|---|
| Design docs (Google) | Ubl post, SWE-at-Google paper (arXiv) | full text |
| RFC (Uber) | Orosz articles | full text (paywall cut at RFC section) |
| PR/FAQ (Amazon) | Vogels 2006 post | full text; Bryar/Carr book unread |
| Rust RFC, PEP, KEP, Swift, AIP | process docs | full text |
| ADR | Nygard, Radar, Azure, AWS, MSR study, Keeling | docs full; Keeling abstract only |
| C4 / arc42 | official sites | overview + FAQ |
| Event storming | official site | overview only; NO empirical study found |
| Domain storytelling | official site | overview only; NO empirical study found |
| DDD / bounded contexts | SLR (abs), GitHub MSR (arXiv abs) | abstracts only |
| Use cases | Use-Case 2.0 Guide | full text; Cockburn book unread |
| Story mapping | Patton page | partial |
| BDD/Gherkin | North, Cucumber ref, 3 studies | docs full; studies abs |
| Design reviews | Ubl, Orosz, KEP/Rust/PEP review stages | partial; no dedicated empirical study found |
| UML/modeling in practice | Petre, Baltes, Ho-Quang, Hebig, Whittle, Akdur, Malavolta | abs (Baltes full) |
| Documentation use/rot | Lethbridge, Aghajani, Wen | abs |
| Architecture knowledge | Tang, Capilla, Ernst, Wan | abs |
| Requirements practice | NaPiRE, QUS, Femmer, Kasauli, Wohlrab | NaPiRE full; others abs |

Unread (pending, not dropped) and why it would not change the
conclusions:

1. Petre 2013 full text and Petre 2014 SoSyM response (paywalled; I
   have only the abstract: 50 professionals, 50 companies, 5 patterns).
   The five pattern names/counts are NOT reported here. Conclusions
   rely instead on Baltes, Ho-Quang, Hebig, Whittle, Akdur which agree.
2. Liebel et al. 2016 SoSyM, Torchiano et al. 2013 JSS, Tofan 2013,
   Rost et al. 2013 ECSA, Hutchinson 2014 SCP (abstracts unavailable
   via the APIs used). Cited by title only, no findings claimed.
3. Books: Cockburn "Writing Effective Use Cases", Evans DDD,
   Brandolini EventStorming, Hofer/Schwentick Domain Storytelling,
   Patton "User Story Mapping", Adzic "Specification by Example",
   Smart "BDD in Action", Bryar/Carr "Working Backwards", Winters et
   al. SWE-at-Google book. Only publisher/author web pages read. The
   primary-source ideas are already carried by the web pages read.
4. Other proposal processes not read in depth: Go proposals (README
   fetched, not analysed), TC39 stages, IETF RFCs, Oxide RFDs,
   HashiCorp, Sourcegraph, Spotify, Meta. They follow the same
   skeleton (proposal, review, accept, implement, final); reading more
   would add instances, not new mechanisms. Residual risk: a mechanism
   unique to one of them (for example TC39 stage criteria with
   required test262 tests) is unexamined.
5. Design-review empirical literature (ATAM/SEI industrial studies,
   Babar and Gorton review practice): search returned no usable hit;
   SLR abstracts (Sensors 2022) say practitioners avoid heavyweight
   evaluation methods, which is G3 and not relied on.
6. Cherubini/whiteboard and Petre-van der Hoek design-thinking
   studies belong to researcher D (incompleteness) and were not swept
   here beyond Almeida et al. 2022.

---------------------------------------------------------------------

## 2. Findings

Format: F-id. Claim. [Evidence strength] (citations S-ids, section 5).
"(abs)" = abstract only.

### 2.1 Design docs, RFCs and proposal processes

F1. Google design docs are deliberately informal prose written
before coding; the useful skeleton is context/scope, goals AND
NON-goals (non-goals are things that could reasonably be goals but are
explicitly not), the design with trade-offs, alternatives considered
("one of the most important sections"), and cross-cutting concerns
(privacy, security, observability) that organisations standardise.
[experience report, G2] (S1)

F2. Google's own guidance: do not paste API or schema definitions
into design docs because they are "verbose, ... and quickly get out
of date"; link or summarise only the trade-off-relevant parts.
[experience report, G2] (S1)

F3. Design docs go stale: "In practice we humans are bad at updating
documents"; changes get isolated into new docs, giving "the US
constitution with a bunch of amendments", so authors are advised to
link amendments from the original. Yet engineers new to a system still
ask first "Where is the design doc?". [experience report, G2] (S1)

F4. Reviews are valued for catching issues while change is still
cheap and for pulling in cross-cutting concerns, but are called "a
dangerous trap of overhead"; Ubl says implementation starts once
"further reviews are unlikely to require major changes to the
design", and privacy/security reviews "are only required to be
completed by the time a project launches". [v2026-10-09: reworded;
the earlier "Google does not require design-review completion before
coding" overstated the source. Counterpoint S65: "Most teams at
Google require an approved design document before starting work on
any major project."] [experience report, G2] (S1, S65)

F5. Uber's trajectory: DUCK (service proposals, about 2013) to RFC
(mailing lists, "approver" fields, per-domain templates) to a tiered
Engineering Planning Process. At 2,000+ engineers the RFC process
failed on (a) noise (hundreds of RFCs weekly), (b) ambiguity about
which work needs an RFC, (c) discoverability (Google Docs scattered
across Drive/wiki). The fix was tooling (single searchable store,
approvers marked, approvals integrated with JIRA/Phabricator),
lightweight templates for team-scoped changes, heavyweight for
org-wide, and criticality tiers with weekly formal review only for
the most critical. Also: templates accreted checkpoints from past
failures (payments regional/legal, GDPR for data stores).
[experience report from a named company, G2] (S7)

F6. Facebook/Meta is cited as the counter-example with the least
documentation among big tech; the same author says he would not
recommend deliberately following it, especially with remote work.
[opinion with experience, weak] (S7b)

F7. Amazon "Working Backwards": write the press release and FAQ
first, then define the customer experience (mockups for UIs; use
cases with code snippets for services), then the user manual, so the
team shares one vision before building; the documents are explicitly
"closer to the implementation" at each step. [experience report from
Amazon CTO, G2; v2026-10-09: wording "For web services, we write use
cases, including code snippets" and "closer to the implementation"
re-confirmed on the page; CTO role confirmed by S8 official bio] (S8)

F8. Rust RFCs: "substantial" changes require an RFC merged into a repo
before implementation; accepted RFCs are "active" but imply no
priority or assignee; EVERY accepted RFC has an associated tracking
issue in the implementation repo, which is where priority is
triaged; accepted RFCs "should not be substantially changed"; larger
changes are new RFCs with a note back in the original; a "postponed"
label exists for good-idea-wrong-time. [project process doc, G2] (S2)

F9. Python PEPs: status enum Draft/Active/Accepted/Provisional/
Deferred/Rejected/Withdrawn/Final/Superseded. "Final" is set only
when the reference implementation is merged, and the final
implementation "must include test code and documentation". A
"Provisional" state exists in which a PEP can still be rejected even
after shipping in a release. A "Rejected Ideas" section is mandatory
to stop the same idea being re-proposed. [project process doc, G2] (S3)

F10. Kubernetes KEPs carry a machine-readable kep.yaml: status
(provisional|implementable|implemented|deferred|rejected|withdrawn|
replaced), replaces/see-also, stage (alpha|beta|stable), per-stage
milestones, feature-gate names with the components that must enable
them, metrics, owners/approvers. KEP number is assigned late
(draft-YYYYMMDD-title.md first) specifically to minimise merge
conflicts. GitHub issues are reserved for work in flight, not for
umbrella tracking. [project process doc, G2] (S4)

F11. Swift Evolution: proposals have a header with Status and
"Implementation: a comma-separated list of links to implementation
pull requests"; implementation review is independent of design
review; a prototype implementation is required before review for
language proposals; experimental features must be gated behind an
explicit flag. [project process doc, G2] (S5)

F12. Google AIP: API design guidance is itself a corpus of numbered,
statused design documents, and an api-linter enforces them on proto
files with suggested fixes. The linter is deliberately NOT semver
because "the addition or correction of virtually any rule is
'breaking'". [vendor process doc, G2] (S6)

Cross-cutting synthesis F13 (derived): every durable proposal process
converges on the same four mechanisms: a status enum with explicit
supersession, a pointer from the design record to implementation
artefacts (tracking issue, PR list, feature gate), a completion gate
that requires tests/docs, and tiering so the process cost is
proportional to risk. None of them mechanically checks that the
pointers stay true; they rely on editors (PEP editor, KEP editor).

### 2.2 ADRs

F14. ADR (Nygard 2011): short text file in the repo (doc/arch/adr-
NNN.md), sequential never-reused numbers, sections Title/Context/
Decision/Status/Consequences, one decision per record, reversed
decisions are kept and marked superseded. [practitioner post, G2/G3:
author of Release It! (Pragmatic Bookshelf 2007, 2nd ed. 2018;
confirmed v2026-10-09 via publisher/library records), Cognitect
blog] (S9)

F15. Thoughtworks Radar placed lightweight ADRs at Adopt (Nov 2017) and
recommends source control over wiki "as then they can provide a
record that remains in sync with the code itself". AWS Prescriptive
Guidance and the Azure Well-Architected Framework both prescribe the
same: states, immutable once accepted, new ADR supersedes; Azure also
asks to record a confidence level and to keep ADR append-only.
[vendor docs, G2] (S10, S11, S12)

F16. Reality check: an MSR study of GitHub finds ADR adoption is low;
about 50% of repositories with ADRs contain only one to five records
("tried but not definitively adopted"); the Nygard template dominates;
systematic users record decisions as a multi-author team activity over
time. [empirical MSR, G1-] (S14, abs; v2026-10-09 abstract
re-confirmed, author list completed). A 2026 ICSA follow-up over 921
of those repositories and about 5,800 ADRs finds about 63% (3,674)
were created already "accepted", skipping the deliberation ADRs are
meant to record, and only small correlations between ADR activity and
code smells or issue resolution time. [empirical, ICSA 2026, G1-;
abstract only] (S66)

F17. Rationale capture is valued but costly: 81 practitioners
recognise the importance of design rationale and use it, but report
barriers to documenting it (Tang 2005). A ten-year retrospective by
the same community concludes the capture cost "hampers a widespread
use" (Capilla 2016). [survey G1; retrospective G3/G1] (S46, S47; abs)

F18. Architectural decisions are the largest source of technical debt
in a 1,831-respondent survey of engineers and architects at three large
long-lived organisations; respondents found current tools unhelpful
for managing it. [empirical survey, G1; ACM SIGSOFT Distinguished
Paper; SEI authors confirmed v2026-10-09] (S48; abs)

### 2.3 Architecture description (C4, arc42) and standards

F19. C4: four hierarchical abstractions (system, container,
component, code) with matching diagrams, plus landscape, dynamic and
deployment views; notation- and tooling-independent. The author's FAQ
claims teams skip UML because it seems complicated, not agile, or
lacks tooling. arc42 gives 12 sections including building-block
view ("hierarchically refined", usually the largest), runtime
view ("important runtime scenarios"), cross-cutting concepts,
decisions, quality scenarios, risks and technical debt, and a
glossary ("ubiquitous language"). [practitioner/consultant sources,
G3] (S16, S17)

F20. In practice, OSS architecture documentation: in six projects
(VLC, OpenEHR, openKM, GIMP, Audacity, Home Assistant) natural
language dominates, diagrams are informal, most projects stay at
maturity level 1 of ArchCaMo, and only one documented design
decisions explicitly. [empirical, ICSA, G1] (S45; abs)

F21. ISO/IEC/IEEE 42010 (2nd ed., Nov 2022) models an architecture
description as AD elements plus CORRESPONDENCES governed by
CORRESPONDENCE RULES "used to express and enforce architecture
relations such as composition, refinement, consistency, traceability".
This is the standard-body precedent for rule-checked relations
between design elements. [standard body, site run by the editor,
G2] (S61)

### 2.4 Modeling, UML and documentation in practice (what is abandoned)

F22. UML in industry is not the lingua franca: Petre interviewed 50
professionals in 50 companies and found 5 patterns of use.
[v2026-10-09] Counts via Greg Wilson's review (S31b; paper itself
still unread): no UML 35, selective 11, automated code generation 3,
retrofit 1, wholehearted 0; reasons for non-use: lack of context
(UML covers architecture, not the whole system), notation overhead,
synchronisation and consistency between diagrams. Fowler's earlier taxonomy: UML as sketch / blueprint /
programming language; his observation was that UML 2's added
precision serves blueprint/language users and burdens sketchers.
[empirical G1 (abs); opinion G3] (S31, S62)

F23. Sketches and diagrams (394 survey respondents plus 3 company
case studies): most contain SOME UML elements but are informal; more
than half are drawn on paper/whiteboard and later revised; most live
more than a week and are archived; the majority relate to methods,
classes or packages "but not to source code artifacts with a lower
level of abstraction". [empirical, FSE, G1] (S33; abstract and full
text skim)

F24. UML in open source: a survey of 485 contributors in 458 projects
found collaboration the top motivation, benefiting new contributors
and non-modellers; a mining study of 1.24 million GitHub projects
found 21,316 UML diagrams in 3,295 projects and that creation/update
happens "most often during a very short phase at the project start".
[empirical, ICSE-SEIP and MODELS, G1] (S34, S35)

F25. MDE state of practice: survey of 450 practitioners plus 22
interviews: MDE is more widespread than believed but "developers
rarely use it to generate whole systems"; they apply it to key parts.
Embedded survey, 627 engineers in 27 countries: approaches from
informal sketches to formal models all in use and all effective
depending on need. [empirical, IEEE Software, JSA, G1] (S36, S38)

F26. What practitioners want from architecture languages (48
practitioners, 40 companies, 15 countries): satisfied with design
capabilities, DISsatisfied with analysis features and extra-functional
properties; used languages mostly come from industry, not academia;
they want more formality and better usability. [empirical, TSE, G1]
(S39)

F27. Documentation rot is expected and tolerated: developers
typically do not update documentation as timely as process people
advocate, but out-of-date docs remain useful in many circumstances
(Lethbridge, IEEE Software). A taxonomy of documentation issues from
878 artefacts (ICSE 2019) and a study of 1.3 billion AST-level
changes over 1,500 systems (code-comment inconsistencies, ICPC 2019)
characterise when code changes do not trigger doc updates.
[empirical, G1] (S42, S43, S44; abs)

F28. Architects' practice problems cluster on management,
documentation, tooling and process (32 practitioners, 21 organisations;
Wan, Zhang, Xia, Jiang, Lo, ESEC/FSE 2023; Huawei among the
affiliations; three continents).
[empirical, G1] (S49; abs)

F29. Whiteboard architecture meetings (architect survey plus
interviews; arXiv preprint, authors include A. van der Hoek):
[v2026-10-09: still an arXiv preprint; no published venue found]
76.09% of architects always or mostly document the meeting; top
documentation reasons are follow-up discussion, evidence of decisions,
forgetting, communicating outcomes. After the whiteboard the aspects
that most often change are: interfaces of major components,
implementation details, a handful of components, detailed modules, DB
schema. Aspects most often MISSING from whiteboard discussions:
sufficient problem information, relative priority of design
considerations, metrics defining success, validity of assumptions at
implementation time, envisioned implementation details. [empirical,
preprint, G3] (S50; full text read)

### 2.5 Requirements, use cases, stories, BDD

F30. Requirements problems (NaPiRE: 228 companies, 10 countries):
most frequently cited are incomplete and/or hidden requirements,
communication flaws between team and customer and within the team, and
moving targets. [empirical, EMSE, G1] (S51; full text read)

F31. Use-Case 2.0: a use case is told as a basic flow plus alternative
flows (the alternatives are optional, additive detours from the basic
flow); stories are threads through use cases; the unit of building is
a "use-case slice" whose test cases "are the most important part of
the slice's description"; slice states Scoped, Prepared, Analyzed,
Implemented, Verified, with explicit note that this is not waterfall
because slices progress in parallel. [practitioner guide, G2/G3: IJI
authors; standing not verified beyond byline] (S19)

F32. Agile requirements in the wild: about 90% of agile practitioners
use user stories and about 70% of those follow the "As a / I want /
so that" template (survey figures quoted by the authors); about 50% of
real-world stories carry easily preventable defects; a 13-criterion
Quality User Story framework and the AQUSA tool, evaluated on 1,023
stories from 18 companies, detects defects and suggests remedies
(recall below 100%). Requirements smells (Smella) achieved average
precision 59% and recall 82% over three industrial and one university
context, "as a supplement to reviews". [empirical, RE journal and
JSS, G1] (S52, S53, S52b; abs)

F33. Practitioner survey (84 practitioners): most use natural
language and specify requirements as use cases and scenario
descriptions, and neglect using requirements for higher-level
reasoning. [survey in an MDPI journal, G3-] (S52c; abs)

F34. BDD: benefits are domain-specific terms, stakeholder
communication, executability and comprehension; costs are the usual
test-suite maintenance problems, with "parts of the system
effectively frozen due to the challenges of finding and modifying the
examples" (75 practitioners from 26 countries). A mapping study of 166
papers notes scarcity of industry insight and "acute shortage of
metrics" for BDD specification quality; a quality-criteria survey
found no formal definition of a high-quality BDD suite. North's
origin story: BDD started as a "ubiquitous language for analysis"
(borrowing Evans), with a story's behaviour being its acceptance
criteria. [empirical G1 (abs); origin story G2/G3] (S28, S29, S30, S25)

F35. Story mapping / shaping: Patton argues a flat backlog is a
poor explanation of what a system does and uses a 2D map (activities
across, detail down, releases as slices). Basecamp's Shape Up says
specs fail at both extremes ("wireframes are too concrete, words are
too abstract") and shapes work to be rough, solved and bounded using
breadboards (places, affordances, connection lines) and fat-marker
sketches, with an "appetite" and explicit no-gos/rabbit holes.
[practitioner, G2/G3] (S18, S21)

F36. Event storming and Domain Storytelling are workshop formats
whose sources are the creators' own sites; NO peer-reviewed
effectiveness study was found in this run (the OpenAlex queries
returned only unrelated hits). Evidence strength: weak (vendor/
author claim). (S22, S23) [v2026-10-09: web search for an empirical
EventStorming study (ICSE/ESEM/RE/REFSQ) again found none. Adoption
signal only: Thoughtworks Radar moved EventStorming Trial (Nov 2015,
Apr 2016) to Adopt (Nov 2018) (S73). Practitioner reports found were
small-consultancy facilitator posts, excluded as not shipped-at-scale.
Verdict unchanged: weak.]

F37. DDD in the literature and on GitHub: an SLR of 36 peer-reviewed
studies reports benefits (notably microservice decomposition) but
challenges in onboarding and need for expertise and that some studies
lack empirical evaluation; an MSR of 2,502 verified DDD repositories
finds long-lived projects, Layered/Clean architecture dominant, C#
and TypeScript leading, and that 25.3% record NO explicit business
context, "a persistent gap between how domain intent is designed and
how it is preserved in version control", calling for "lightweight
architectural traceability standards". [SLR in JSS G1 (abs); MSR
arXiv preprint G3] (S56, S57)

F38. An actor-driven decomposition methodology for microservices
(TOSEM 2023) complements DDD by using actors to find boundaries.
[academic, G3 for our purpose] (S64; abs)

### 2.6 Traceability and agile at scale

F39. Traceability in practice (24 individuals, 15 industrial
projects): the challenges are collaboration across team and tool
boundaries, conveying the benefits, and maintenance; some rigor is
needed for benefits to materialise; approaches are requirements-
centred, developer-driven or mixed. Large-scale agile systems RE
(seven companies, 20 interviews, 5 focus groups) lists 24 challenges
in six themes. [empirical, RE and JSS, G1] (S54, S55; abs)

F40. Architecture and agile: an SMS of 54 studies (2001-2014) examines
the combination; Keeling (IEEE Software column) argues ADRs are what
finally connected architecture and agile teams. [SMS G1; column G3,
v2026-10-09: downgraded to title-only, abstract unread] (S59, S15)

---------------------------------------------------------------------

## 3. Implications for grmb

Tag: ADOPT / ADAPT / REJECT. Each implication states what grimble
could check and how. "Stage" below means an authored maturity marker
(sketch, draft, committed) per entity or per file; see I6.

### 3.1 Process shape and lifecycle

I1. ADAPT. Do not add an authored workflow status to goals/scenarios/
impls; keep the computed ladder declared -> bound -> verified, which
mirrors the Use-Case 2.0 slice states Implemented/Verified and the PEP
"Final requires implementation + tests" gate (F9, F31). Authored
status exists only on DECISION entities (I2) where there is no code to
compute it from. Check: bound = all selectors resolve non-empty;
verified = Evidence relation passes.

I2. ADAPT. Add a `decision` entity (ADR) with title, context,
chosen option, status (proposed|accepted|superseded|rejected),
`supersedes`, `consequences`, and `affects SELECTOR`. Reason: ADR is
the only documentation practice with direct adoption evidence of
survival close to the code (F14, F15), and the reported failure is
disuse, not harm (F16). Binding `affects` to code addresses
Thoughtworks' "in sync with the code" and the DDD finding that domain
intent is lost in VCS (F37). Check: accepted decision body unchanged
vs git base (immutability); `affects` resolves; superseded decisions
have a live successor.

I3. ADOPT. Make non-goals first-class (`non_goal NAME;` under a
system or goal). Google's definition (not negated goals) is exact
(F1). Check: a scenario or impl that realizes a non_goal is a
conflict finding; a non_goal with no rationale is Advisory.

I4. ADAPT. Alternatives-considered as a typed field on decisions
(F1, F9 Rejected Ideas, F15 Azure "options considered"). Check:
decision at stage committed with fewer than two options is Advisory.
Never Error, because Google says docs for obvious solutions are
overhead.

I5. ADAPT. Cross-cutting concerns as a PACK-defined checklist
(security, privacy, observability, cost), not grammar (F1, F5 GDPR/
payments accretion). Check: for each concern whose trigger predicate
matches the model (for example a node holding a restricted data label,
a flow crossing a boundary) there must be an `addresses` link or an
accepted exception. Packs grow checkpoints "from past failures" just as
Uber's templates did.

I6. ADOPT. Progressive strictness via stages (sketch, draft,
committed) and tiers. Evidence: Uber's friction (F5), Google's
"mini design doc" (F1), Shape Up "rough" (F35), the 4-way split in
modeling practice from sketch to formal (F25), Malavolta's request for
usability (F26). Check: rule severities are a function of stage
(sketch: only syntax and reference errors; draft: add exhaustiveness
as Advisory; committed: add binding and verification obligations).
A committed entity depending on a sketch entity is a finding (P10).

I7. ADAPT. Approval and discoverability (Uber F5): grimble already
has a searchable graph JSON; add `owner` and use `grimble ack` as the
approval record. Check: a committed-stage entity whose content hash
differs from the last ack by its owner (or an owner glob) is a
finding; non-blocking by default (Google F4: reviews are an overhead
trap).

I8. ADOPT. Supersede, do not edit in place, for accepted decisions
(F3, F8, F14, F15). Amendment chains degrade readability (F3), so
check chain depth and that old records link forward.

I9. ADOPT. Never restate contracts: reference by selector. Google
(F2) and the doc-rot evidence (F27) agree. Check: a `contract`
declaring fields must match the bound code type (existing binding
mechanics); a doc string that embeds a code block is Advisory.

I10. ADAPT. Use C4 level names and arc42 section names as RENDER
targets, not as grammar (F19). The planning levels already map: system
and actor = context, node = container, impl = component, selector = code. arc42 runtime view = `scenario`, building-block
view = node tree, decisions = `decision`, quality requirements =
typed attrs/budgets (I17), risks and technical debt = open
obligations, glossary = I16. `grimble graph --mermaid` is already the
planned vehicle.

I11. ADOPT. The scenario construct is the Cockburn/Jacobson
basic-flow-plus-alternatives structure with a type system on top
(F31). Slice thinking supports the P4 per-arm `verified_by`: the test
cases ARE the slice's definition. Check: each outcome arm of a
scenario bound at stage committed has a verified_by or an accepted
exception; coverage reported as a ratio.

I12. ADAPT (small). Working Backwards (F7) maps onto existing
constructs: PR/FAQ is a doc-anchored vmodel artifact for a goal. Do
NOT add press-release grammar. Allow `doc "path#anchor"` on goal and
check the anchor exists (already the vmodel `ref` check).

I13. ADAPT, weak evidence (practitioner only). Shape Up "appetite" as
an optional typed attribute with units on a goal (grmb attrs already
carry units) so frob can compare it to the summed estimates of
implementing tickets. Advisory only. Reason for the hedge: one
company's method (F35).

I14. ADOPT. Breadboard vocabulary (places, affordances, connection
lines) is the planned `page`/`ui`/navigation graph; keep reachability
checks (MDL006 for missing pages). Evidence is practitioner (F35).

I15. ADAPT. Binding granularity: sketches relate to methods/classes/
packages, and what changes after the whiteboard is component
interfaces and implementation details (F23, F29). So L1-L3
bindings should be allowed at file/module/package granularity
(selector `::` optional); only L4 needs symbols. Provide a
non-semantic `attach "docs/sketch.png"` for round-tripping photos of
whiteboards (F23: sketches archived and revised); the only check is
that the file exists and is inside the repo.

I16. ADAPT, weak evidence. Optional `term` (glossary) entity (arc42
section 12, DDD ubiquitous language, North F34). Check only when a
glossary exists in the model: step and goal names not found among
terms are Warn. Evidence is practitioner/opinion; keep opt-in.

I17. ADOPT. Ship analysis before rendering: practitioners are
dissatisfied exactly with analysis and extra-functional property
support in architecture languages (F26); Uber and Google templates
ask for SLAs and cross-cutting properties (F1, F5); the whiteboard
study lists "metrics that delineate success" as commonly missing
(F29). Allow typed attributes with units on steps and goals
(`budget p99 200 ms`). Check: the sum of step budgets along any
scenario path must not exceed the goal budget (P11).

I18. ADAPT. Requirements-quality lint is useful but imprecise:
Smella precision 59% (F32). So text lints on titles are Advisory,
never Error, and grammar-level structure should absorb most of the
QUS criteria (one actor per step, unique ids, explicit dependencies
via `requires`, completeness via exhaustiveness). The 13 QUS criteria
list was not read; a follow-up should map them one by one.

I19. ADOPT. Justify the layer with the NaPiRE top problems (F30):
incomplete requirements -> exhaustiveness (unrealized leaf, unhandled
outcome); moving targets -> stable identifiers, `renamed_from`,
`supersedes`, and a finding when a goal changes after an implementing
ticket started (frob join, P17); communication flaws -> renderings
for PM/designers.

I20. ADOPT. Traceability: maintenance is the pain, benefit
communication is the second pain (F39). Keep the decision that links
are COMPUTED from selectors and the ticket `implements` field is the
single canonical link; expose "what would a change to X affect" in
`grimble status` so the benefit is visible without effort.

I21. ADOPT. Pin rule-sets and ratchet: the AIP linter explicitly
rejects semver because adding a rule breaks users (F12). grmb packs
carry versions and baselines; adding a planning rule must be
Advisory first and graduate through the ratchet lock.

I22. ADOPT. Names, not counters (KEP draft-then-number, F10): grmb
entities are identifiers and tickets are hash ids, so no central
number is needed; this removes the merge-conflict class that KEP
works around.

I23. ADAPT. Feature-flag / rollout binding (KEP stage, feature-gates,
F10; Swift experimental flags F11). As a pack vocabulary: `rollout
stage alpha gate "MyFeature"`. Check: the gate name resolves in code
(selector) and a stable-stage entity has no remaining gate.

I24. ADOPT. "Unjustified design" and "orphan" kernel closure rules
are directly supported: 25.3% of DDD repos record no business context
(F37). Check: node with no realizing impl or no path from a goal.

I25. ADAPT. Completion gate: PEP Final requires tests+docs (F9) and
Swift lists implementation PRs in the proposal header (F11). The
planned close guard (ticket cannot close while `implements` entity is
declared) is the same mechanism with a computed check instead of an
editor.

I26. ADAPT. Provisional state (F9, F10): allow an entity or decision
to be `provisional` (accepted but may still be revoked after release)
as a stage, and flag provisional entities older than N cycles.

I27. REJECT. Event storming and Domain Storytelling grammars. Reason:
workshop formats with no empirical effectiveness evidence (F36); the
output they produce (events, actors, policies, stories) maps to
existing actor, step, outcome and scenario constructs. Possible later
`grimble import` is out of scope.

I28. REJECT. Gherkin Given/When/Then as design-layer syntax. Reason:
BDD maintenance costs and frozen specs (F34); the scenario construct
already has typed outcomes. ADAPT instead: let `verified_by` select
Gherkin scenarios by name/tag so existing feature files are bound,
not duplicated.

I29. REJECT. Whole-system generation from the model and mandatory
full-system coverage. Reason: MDE is applied to key parts, models are
mostly created at project start and rarely updated (F24, F25).
Instead report coverage as ratios, allow partial scope (scope marker
per subtree), and never fail a build for absence of coverage outside
declared scope.

I30. REJECT. Free-form prose design document as grmb content.
Reason: Google keeps design docs informal because prose carries
trade-offs better than formal media (F1). grmb should ANCHOR to the
prose doc (I12), not absorb it.

I31. ADAPT. Review gates should be lightweight and non-blocking by
default with tiered escalation (F4, F5). Rule severity for missing
ack scales with stage and tier.

---------------------------------------------------------------------

## 4. Candidate lint rules

Id placeholders PLAN-Pnn (family to be chosen per rules.md). Polarity:
P = fires on presence, A = fires on absence, M = fires on mismatch.
Severity is a suggestion, never Error unless noted.

| Id | Anti-pattern prevented | Predicate over model / binding | Pol | Source |
|---|---|---|---|---|
| PLAN-P01 | Edited-in-place accepted decision (history lost) | decision.status in {accepted} and content_hash(decision) != hash recorded at acceptance (git base or lock) | M | F8, F14, F15 |
| PLAN-P02 | Decision floating free of code | decision.status == accepted and decision.affects is empty | A | F15, F37 |
| PLAN-P03 | Decision relied on after supersession | decision.superseded_by set and any entity still `cites` it as live; or superseded_by target missing / cyclic | M | F3, F9, F14 |
| PLAN-P04 | Decision without alternatives | committed decision with fewer than 2 options | A | F1, F15 |
| PLAN-P05 | Realizing a declared non-goal | exists scenario/impl that realizes an entity under a `non_goal` | M | F1 |
| PLAN-P06 | Cross-cutting concern forgotten | for pack concern C with trigger T: T matches an entity and no `addresses C` link or accepted exception | A | F1, F5 |
| PLAN-P07 | Stage inversion | committed entity references (requires/realizes/uses) an entity at lower stage | M | F5, F25 |
| PLAN-P08 | Unreviewed change to committed design | committed entity content hash != last ack by owner | M | F4, F5 |
| PLAN-P09 | Orphan goal leaf / scenario | goal leaf with no realizing scenario; scenario realizing nothing | A | F30, I24 |
| PLAN-P10 | Unhandled outcome variant | step outcome variant with no arm / no collected handler (already planned MDL rows) | A | F30 |
| PLAN-P11 | Latency / budget overrun | for each scenario path: sum(step.budget) > goal.budget (same dimension, units checked) | M | F26, F5, F29 |
| PLAN-P12 | Verified without per-arm evidence | entity at committed with verified_by missing for some outcome arm | A | F31 |
| PLAN-P13 | Unjustified design element | node/impl with no path from any goal via realizes/impl | A | F37 |
| PLAN-P14 | Stale design vs churning code | bound code selectors changed in >= N commits since last ack and entity unchanged | M | F3, F27 |
| PLAN-P15 | Moving target under implementation | goal/scenario content changed after an implementing ticket entered in-progress (frob join over ledger) | M | F30 |
| PLAN-P16 | Glossary violation (opt-in) | glossary present and step/goal identifier not in terms | A | F19, F34 |
| PLAN-P17 | Over-long scenario | scenario step count > threshold (default 15) or fan-out of arms > threshold | P | F1 (split), weak |
| PLAN-P18 | Broken sketch attachment | `attach` path missing / outside repo | M | F23 |
| PLAN-P19 | Dead rollout gate | declared gate name not found in bound code; or stable stage with a gate still declared | M | F10, F11 |
| PLAN-P20 | Forever-provisional | entity stage provisional for > N cycles | P | F9, F10 |
| PLAN-P21 | Skipped or ignored acceptance test | verified_by selects a test marked skip/ignore/pending (needs test-runner facts) | M | F34 |
| PLAN-P22 | Vague title (text smell) | title matches smell patterns (passive, vague quantifier, "etc."); precision about 59%, Advisory only | P | F32 |
| PLAN-P23 | Restated contract | doc/description embeds field list that also appears in bound contract (diff) | M | F2 |
| PLAN-P24 | Unlinked ADR chain | superseded decision chain depth > N (amendment pile) | P | F3 |

Notes: P01, P08, P14, P15 need a "last ack / base" reference, which
grimble ack and the git base already supply. P11 needs unit-typed
attrs (already in the grmb type system). P06 depends on pack
triggers being declarative predicates over labels and boundaries, as
packs.md already allows.

---------------------------------------------------------------------

## 5. Bibliography with credibility lines

Format: id. Citation. URL/DOI. Credibility: venue grade; author
standing with source. All entries fetched or looked up in this run
unless marked [unverified].

### Process documents and experience reports

S1. Malte Ubl. "Design Docs at Google." Industrial Empathy, 6 Jul 2020.
https://www.industrialempathy.com/posts/design-docs-at-google/
Credibility: G2. Author's blog lists him as CTO of Vercel
(vercel.com blog byline "Malte Ubl, CTO, Vercel", verified); the
post speaks as a Google engineer ("at Google"); Gergely Orosz's
reply on the page calls it an overview of design docs "at Google".
[v2026-10-09] Google role confirmed: his About page
(https://www.industrialempathy.com/about/) states Principal Engineer
for Google Search Rendering, later Engineering Director for Google
Search; a post "11 years at Google" (Mar 2022). Google Cloud Next
speaker page (https://www.googlecloudevents.com/next-vegas/speaker/2149308/malte-ubl)
credits him as creator of AMP. The earlier "AMP tech lead" wording is
replaced by these titles.

S2. Rust project. RFC 0002 "RFC process" and rust-lang/rfcs README.
https://raw.githubusercontent.com/rust-lang/rfcs/master/text/0002-rfc-process.md
https://raw.githubusercontent.com/rust-lang/rfcs/master/README.md
Credibility: G2, official project process.

S3. Python project. PEP 1 "PEP Purpose and Guidelines."
https://raw.githubusercontent.com/python/peps/main/peps/pep-0001.rst
Credibility: G2, official project process (Steering Council).

S4. Kubernetes project. KEP-0000 "KEP process" README and kep.yaml
template. https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/sig-architecture/0000-kep-process/README.md
https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/NNNN-kep-template/kep.yaml
Credibility: G2, official project process.

S5. Swift project. "Swift Evolution Process."
https://raw.githubusercontent.com/swiftlang/swift-evolution/main/process.md
Credibility: G2, official project process.

S6. Google. "AIP-1: AIP Purpose and Guidelines" https://google.aip.dev/1
and googleapis/api-linter README
https://raw.githubusercontent.com/googleapis/api-linter/main/README.md
Credibility: G2, official Google API governance docs.

S7. Gergely Orosz. "Engineering Planning with RFCs, Design Documents
and ADRs", The Pragmatic Engineer newsletter.
https://newsletter.pragmaticengineer.com/p/rfcs-and-design-docs
(read through the Uber section; remainder paywalled).
S7b. Gergely Orosz. "Companies Using RFCs or Design Docs and Examples
of These." https://blog.pragmaticengineer.com/rfcs-and-design-docs/
Credibility: G2/G3. Author's About page: 4 years at Uber heading
mobile, web and backend teams, previously Skyscanner and Skype/
Microsoft (https://blog.pragmaticengineer.com/about/, verified).
Reports Uber events first-hand; company list is crowd-sourced.

S8. Werner Vogels. "Working Backwards." All Things Distributed,
1 Nov 2006. https://www.allthingsdistributed.com/2006/11/working_backwards.html
Credibility: G2, first-party Amazon description. [v2026-10-09] Role
confirmed: official bio https://allthingsdistributed.com/about.html
("Chief Technology Officer at Amazon.com"; joined Amazon 2004 from
Cornell).

S9. Michael Nygard. "Documenting Architecture Decisions." Cognitect
blog, 15 Nov 2011.
https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions
Credibility: G2/G3. Origin of the ADR practice. [v2026-10-09]
Authorship of "Release It! Design and Deploy Production-Ready
Software" (Pragmatic Bookshelf, 2007; 2nd ed. Jan 2018) confirmed via
https://www.oreilly.com/library/view/release-it-2nd/9781680504552/
and library records; publisher bio: architect who delivered systems
for government, banking, finance, retail. Shipped-at-scale standing:
practitioner/consultant, no single named large product confirmed.

S10. Thoughtworks Technology Radar. "Lightweight Architecture Decision
Records" (Nov 2017, Adopt).
https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records
Credibility: G2, consultancy publication with named large-client
practice; opinion-grade.

S11. Microsoft. "Maintain an architecture decision record (ADR)",
Azure Well-Architected Framework.
https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
Credibility: G2, official vendor doc.

S12. AWS. "Architectural decision record process", AWS Prescriptive
Guidance.
https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
Credibility: G2, official vendor doc.

S13. ADR GitHub organisation. https://adr.github.io/
Credibility: G3, community site.

S14. Buchgeher, Schoberl, Geist, Dorninger, Haindl, Weinreich. "Using
Architecture Decision Records in Open Source Projects - An MSR Study
on GitHub." IEEE Access 11:63725-63740, 2023.
https://doi.org/10.1109/access.2023.3287654 ; abstract at
https://research.jku.at/en/publications/using-architecture-decision-records-in-open-source-projects-an-ms/
Credibility: G1-, peer-reviewed open-access journal; SCCH and JKU
Linz authors; (abs). [v2026-10-09: sixth author Weinreich added.]

S15. Michael Keeling. "Love Unrequited: The Story of Architecture,
Agile, and How Architecture Decision Records Brought Them Together."
IEEE Software 39(4):90-93, 2022. https://doi.org/10.1109/ms.2022.3166266
(dblp https://dblp.org/pid/49/7592 confirms venue/pages).
Credibility: G3, practitioner column; author of "Design It!"
(Pragmatic Bookshelf 2017). [v2026-10-09: employer (often reported
as IBM) NOT confirmed by any fetched source; standing = book author,
unconfirmed industrial role. Abstract still unread; F40's Keeling
clause rests on the title only and is downgraded accordingly.]

### Architecture description and standards

S16. Simon Brown. C4 model site and FAQ. https://c4model.com/ ,
https://c4model.com/faq. Credibility: G3, creator's own site.
[v2026-10-09] Standing: independent consultant, creator of C4 and
founder of Structurizr, author of "Software Architecture for
Developers" (DDD Europe 2025 bio
https://2025.dddeurope.com/speakers/simon-brown). No shipped-at-scale
product role; consultant grade.

S17. arc42 template overview. https://arc42.org/overview
Credibility: G3, consultant-maintained template "proven in practice
since 2005" (self-claim).

S61. ISO/IEC/IEEE 42010:2022 site (concepts, correspondences,
correspondence rules). http://www.iso-architecture.org/42010/
Credibility: G2, standards body topic; the site is operated by the
standard's editors (iso.org page itself was blocked).

S45. Muszynski, Lugtigheid, Castor, Brinkkemper. "A Study on the
Software Architecture Documentation Practices and Maturity in Open-
Source Software Development." ICSA 2022.
https://doi.org/10.1109/icsa53651.2022.00013
Credibility: G1, ICSA; Utrecht University; (abs).

### Modeling and documentation in practice

S31. Marian Petre. "UML in practice." ICSE 2013.
https://doi.org/10.1109/icse.2013.6606618. Credibility: G1, ICSE;
The Open University; 50 professionals in 50 companies (abs only;
full text paywalled).
S31b. Greg Wilson. "UML in Practice" (review), Never Work in Theory,
13 Jun 2013. https://neverworkintheory.org/2013/06/13/uml-in-practice-2.html
[v2026-10-09] Credibility: G3 secondary summary by an established
SE-research communicator (Software Carpentry founder); used only for
the five pattern counts in F22.
S32. Marian Petre. "'No shit' or 'Oh, shit!': responses to observations
on the use of UML in professional practice." SoSyM 2014.
https://doi.org/10.1007/s10270-014-0430-4 (not read; no abstract).
[v2026-10-09] Open University record https://oro.open.ac.uk/41542
confirms it summarises the debate following S31: responses split
between "familiar and unsurprising" and "threatening long-held
beliefs about UML as the de facto standard". No finding rests on it.

S33. Sebastian Baltes, Stephan Diehl. "Sketches and diagrams in
practice." FSE 2014. https://doi.org/10.1145/2635868.2635891 ;
arXiv https://arxiv.org/abs/1706.09172. Credibility: G1, FSE;
Universitat Trier; three companies plus 394-person survey.

S34. Ho-Quang, Hebig, Robles, Chaudron, Fernandez. "Practices and
Perceptions of UML Use in Open Source Projects." ICSE-SEIP 2017.
https://doi.org/10.1109/icse-seip.2017.28 . Credibility: G1; Chalmers/
Gothenburg/URJC; (abs).

S35. Hebig, Ho-Quang, Chaudron, Robles, Fernandez. "The quest for open
source projects that use UML." MODELS 2016.
https://doi.org/10.1145/2976767.2976778 . Credibility: G1; (abs).

S36. Whittle, Hutchinson, Rouncefield. "The State of Practice in
Model-Driven Engineering." IEEE Software 2013.
https://doi.org/10.1109/ms.2013.65 . Credibility: G1; Lancaster
University; survey of 450 and 22 interviews (abs).
S37. Hutchinson, Whittle, Rouncefield. "Model-driven engineering
practices in industry: Social, organizational and managerial factors
that lead to success or failure." Sci. Comput. Program. 2014.
https://doi.org/10.1016/j.scico.2013.03.017 . Title only; abstract
unavailable; no finding claimed.

S38. Akdur, Garousi, Demirors. "A survey on modeling and model-driven
engineering practices in the embedded software industry." J. Syst.
Archit. 2018. https://doi.org/10.1016/j.sysarc.2018.09.007 .
Credibility: G1; authors from Aselsan (Turkish defence electronics),
Izmir Inst. Tech., UNSW and Wageningen (OpenAlex affiliations); 627
engineers, 27 countries (abs).

S39. Malavolta, Lago, Muccini, Pelliccione, Tang. "What Industry Needs
from Architectural Languages: A Survey." IEEE TSE 2013.
https://doi.org/10.1109/tse.2012.74 . Credibility: G1; Swinburne, L'Aquila,
VU Amsterdam; 48 practitioners in 40 companies in 15 countries (abs).

S40. Liebel, Marko, Tichy, Leitner, Hansson. "Model-based engineering
in the embedded systems domain: an industrial survey on the
state-of-practice." SoSyM 17(1):91-113, 2018 (online 2016).
https://doi.org/10.1007/s10270-016-0523-3 ; abstract via
https://research.chalmers.se/en/publication/502019 . [v2026-10-09]
G1; 113 respondents, mostly practitioners; MBE used mainly for
simulation, code generation, documentation; shortcomings: tool
interoperability, training effort, usability.
S41. Torchiano, Tomassetti, Ricca, Tiso, Reggio. "Relevance, benefits,
and problems of software modelling and model driven techniques - A
survey in the Italian industry." JSS 86(8):2110-2126, 2013.
https://doi.org/10.1016/j.jss.2013.03.084 ; full text
https://iris.polito.it/handle/11583/2506343 . [v2026-10-09] G1; 155
Italian professionals; obstacles: effort and limited perceived
usefulness slow adoption, lack of competencies and tools block it.
(Both now support F25; see section 7 F25a.)

S42. Lethbridge, Singer, Forward. "How software engineers use
documentation: the state of the practice." IEEE Software 2003.
https://doi.org/10.1109/ms.2003.1241364 . Credibility: G1; University
of Ottawa, NRC Canada, Deloitte (OpenAlex affiliations); (abs).

S43. Aghajani et al. "Software Documentation Issues Unveiled." ICSE
2019. https://doi.org/10.1109/icse.2019.00122 . G1; 878 artifacts (abs).

S44. Wen, Nagy, Bavota, Lanza. "A Large-Scale Empirical Study on
Code-Comment Inconsistencies." ICPC 2019.
https://doi.org/10.1109/icpc.2019.00019 . G1; USI; (abs).

S46. Tang, Babar, Gorton, Han. "A Survey of the Use and Documentation
of Architecture Design Rationale." WICSA 2005.
https://doi.org/10.1109/wicsa.2005.7 . G1; Swinburne, Data61 (NICTA),
UNSW; 81 responses (abs).

S47. Capilla, Jansen, Tang, Avgeriou, Babar. "10 years of software
architecture knowledge management: Practice and future." JSS 2016.
https://doi.org/10.1016/j.jss.2015.08.054 . G1/G3 (retrospective);
includes Philips (OpenAlex affiliation); (abs).

S48. Ernst, Bellomo, Ozkaya, Nord, Gorton. "Measure it? Manage it?
Ignore it? Software practitioners and technical debt." ESEC/FSE 2015,
pp. 50-60. https://doi.org/10.1145/2786805.2786848 . G1; 1,831
respondents, three large organisations (abs). [v2026-10-09] SEI
affiliation confirmed: SEI library entry
https://sei.cmu.edu/library/measure-it-manage-it-ignore-it-software-practitioners-and-technical-debt
and SEI author page https://sei.cmu.edu/authors/ian-gorton ; an SEI
presentation describes the sample as two large industry and one
government organisation. ACM SIGSOFT Distinguished Paper.

S49. Zhiyuan Wan, Yun Zhang, Xin Xia, Yi Jiang, David Lo. "Software
Architecture in Practice: Challenges and Opportunities." ESEC/FSE
2023. https://doi.org/10.1145/3611643.3616367 ; arXiv
https://arxiv.org/abs/2308.09978 . G1; Zhejiang University, Hangzhou
City University, Huawei, SMU; 32 practitioners from 21 organizations
on three continents (abs). [v2026-10-09: author list completed
(David Lo added); venue confirmed on the FSE 2023 program.]

S50. Almeida, Ahmed, van der Hoek. "Let's Go to the Whiteboard
(Again): Perceptions from Software Architects on Whiteboard
Architecture Meetings." arXiv 2210.16089 (2022).
https://arxiv.org/abs/2210.16089 . G3 as a preprint; full text read.
[v2026-10-09] Authors: Eduardo Santana de Almeida, Iftekhar Ahmed,
Andre van der Hoek. No published venue found (IEEE-journal
formatting only). van der Hoek's co-authorship of "Software Design
Decoded" is now confirmed (S70).

### Requirements, use cases, stories, BDD, DDD

S51. Mendez Fernandez, Wagner, Kalinowski, Felderer, Mafra, et al.
"Naming the pain in requirements engineering: contemporary problems,
causes, and effects in practice." Empirical Software Engineering 2016.
https://doi.org/10.1007/s10664-016-9451-7 ; arXiv
https://arxiv.org/abs/1611.10288 . G1; multi-institution; 228
companies, 10 countries; full text read.

S52. Lucassen, Dalpiaz, van der Werf, Brinkkemper. "Improving agile
requirements: the Quality User Story framework and tool." Requirements
Engineering 2016. https://doi.org/10.1007/s00766-016-0250-x . G1;
Utrecht; 1,023 stories, 18 companies (abs).
S52b. Dalpiaz, Brinkkemper. "Agile Requirements Engineering with User
Stories" (tutorial). RE 2018. https://doi.org/10.1109/re.2018.00075 .
G1/G3; source of the 90%/70%/50% figures, stated by the authors (abs).
S52c. Ozkaya, Akdur, Toptani, Kocak. "Practitioners' Perspectives
towards Requirements Engineering: A Survey." Systems (MDPI) 2023.
https://doi.org/10.3390/systems11020065 . G3-, MDPI journal; 84
practitioners (abs).

S53. Femmer, Mendez Fernandez, Wagner, Eder. "Rapid quality assurance
with Requirements Smells." JSS 2016. https://doi.org/10.1016/j.jss.2016.02.047 .
G1; TU Munich, Stuttgart; precision 59%, recall 82% (abs).

S54. Wohlrab, Knauss, Steghofer, Maro, et al. "Collaborative
traceability management: a multiple case study from the perspectives
of organization, process, and culture." Requirements Engineering
25:21-45, 2020 (online Nov 2018). https://doi.org/10.1007/s00766-018-0306-1 .
G1; Chalmers, Gothenburg, Systemite; 24 individuals, 15 projects
(abs). [v2026-10-09: full author list is Wohlrab, Knauss,
Steghofer, Maro, Anjorin, Pelliccione; issue year added; open access
CC-BY.]

S55. Kasauli, Knauss, Horkoff, Liebel, Gomes de Oliveira Neto.
"Requirements engineering challenges and practices in large-scale
agile system development." JSS 172:110851, 2021 (online 2020).
https://doi.org/10.1016/j.jss.2020.110851 ; abstract
https://research.chalmers.se/publication/522021 . G1; Chalmers;
seven large-scale systems companies (Software Center partners;
names not read), 20 interviews, 5 focus groups, 8 cross-company
workshops (abs). [v2026-10-09: fifth author and volume added.]

S56. Ozkan, Babur, van den Brand. "Domain-Driven Design in software
development: A systematic literature review on implementation,
challenges, and effectiveness." JSS 2025.
https://doi.org/10.1016/j.jss.2025.112537 . G1; TU Eindhoven;
36 studies (abs). [v2026-10-09] Confirmed: JSS vol. 230 (Dec 2025);
preprint arXiv 2310.01905 v4. Strongest DDD elements reported:
Ubiquitous Language, Bounded Context, Domain Events.
S57. Ozkan, Babur, van den Brand. "Domain-Driven Design in Practice: A
Large-Scale Empirical Characterisation of the Open-Source Ecosystem."
arXiv 2607.06471 (submitted 7 Jul 2026). https://arxiv.org/abs/2607.06471 .
G3 preprint; abstract read; 2,502 verified repositories.
[v2026-10-09: abstract re-fetched; "25.3%" and "lightweight
architectural traceability standards" quotes confirmed.]

S58. Li, Liang, Soliman, Avgeriou. "Understanding Architecture
Erosion: The Practitioners' Perceptive." ICPC 2021.
https://doi.org/10.1109/icpc52881.2021.00037 . G1 (abs); belongs to
topic B; cited only as pointer.

S59. Yang, Liang, Avgeriou. "A systematic mapping study on the
combination of software architecture and agile development." JSS 2016.
https://doi.org/10.1016/j.jss.2015.09.028 . G1; 54 studies (abs).

S60. Fergus Henderson. "Software Engineering at Google." arXiv
1702.01715 (2017). https://arxiv.org/abs/1702.01715 . G2, Google
authored catalogue; full text read (only incidental mentions of
design reviews, code owners and readability found).

S19 [v2026-10-09 standing]: Ivar Jacobson originated use cases at
Ericsson (Objectory/OOSE), co-designed UML at Rational, founded IJI
2004 (https://en.wikipedia.org/wiki/Ivar_Jacobson ; ICSE 2018 keynote
https://conf.researchr.org/details/icse-2018/icse-2018-Keynotes/2/50-years-of-software-engineering-so-now-what- ).
Standing upgraded: method originator with industrial (Ericsson AXE)
history; still G2/G3 because the guide is a method text, not a study.
S19. Jacobson, Spence, Bittner. "Use-Case 2.0: The Guide to Succeeding
with Use Cases." Ivar Jacobson International, Dec 2011. Read via
https://web.archive.org/web/2019/https://www.ivarjacobson.com/sites/default/files/field_iji_file/article/use-case_2_0_jan11.pdf
Companion: Jacobson, Spence, Kerr. "Use-Case 2.0." CACM 2016.
https://doi.org/10.1145/2890778 (abstract only). Credibility: G2/G3,
practitioner method guide; author standing beyond the byline not
verified.

S21. Jeff Patton. "The New Backlog" / story mapping.
https://www.jpattonassociates.com/the-new-backlog/ . G3, practitioner.

S18. Basecamp. Shape Up, ch. 2 "Principles of Shaping" and ch. 4
"Find the Elements". https://basecamp.com/shapeup/1.1-chapter-02 ,
https://basecamp.com/shapeup/1.3-chapter-04 . G2, first-party
company method (Basecamp product team).

S22. EventStorming. https://www.eventstorming.com/ . G3, creator site.
[v2026-10-09] Creator Alberto Brandolini (Avanscoperta, consultancy;
idea dated 2013); book "Introducing EventStorming", Leanpub,
unfinished (https://leanpub.com/introducing_eventstorming).

S23. Domain Storytelling. https://domainstorytelling.org/ . G3, creator
site. (Also https://domainstorytelling.org/quick-start-guide)
S24. Domain Language. "DDD Reference."
https://www.domainlanguage.com/ddd/reference/ (fetched; page body
not captured; no claim rests on it).

S25. Dan North. "Introducing BDD." https://dannorth.net/blog/introducing-bdd/
G2/G3, originator account.
S26. Cucumber. "Gherkin Reference."
https://cucumber.io/docs/gherkin/reference/ . G2, official tool doc.
S27. Gojko Adzic. "Specification by Example" (book page; 2011; claims
50+ projects). https://gojko.net/books/specification-by-example/ . G3;
book itself unread.

S28. Binamungu, Embury, Konstantinou. "Maintaining behaviour driven
development specifications: Challenges and opportunities." SANER 2018.
https://doi.org/10.1109/saner.2018.8330207 . G1; Manchester; 75
practitioners, 26 countries (abs).
S29. Binamungu, Embury, Konstantinou. "Characterising the Quality of
Behaviour Driven Development Specifications." XP 2020 workshops, LNBIP.
https://doi.org/10.1007/978-3-030-49392-9_6 . G1-; (abs).
S30. Binamungu, Maro. "Behaviour Driven Development: A Systematic
Mapping Study." JSS 2023; arXiv https://arxiv.org/abs/2305.05567 .
G1; 166 papers.

S62. Martin Fowler. "UML Mode." 28 May 2003.
https://martinfowler.com/bliki/UmlMode.html . G3 opinion.
[v2026-10-09] Standing: Chief Scientist at Thoughtworks, on its
global leadership team since 2017 (https://martinfowler.com/aboutMe.html).

S64. Camilli, Colarusso, Russo, Zimeo. "Actor-Driven Decomposition of
Microservices through Multi-level Scalability Assessment." ACM TOSEM
2023. https://doi.org/10.1145/3583563 . G3 for our purposes; (abs).

---------------------------------------------------------------------

## 6. Top implications (for the coordinator)

1. Computed status plus a small authored decision log: keep
   declared/bound/verified computed, add only a `decision` (ADR)
   entity as authored status with immutability and supersession checks
   (I1, I2, P01-P03).
2. Progressive strictness by stage is mandatory: Uber's RFC collapse
   and the sketch-to-formal modeling spread show a single strictness
   level will be abandoned (I6).
3. The checkable value is analysis, not drawing: practitioners are
   dissatisfied with analysis and extra-functional support; ship
   exhaustiveness, binding, budgets and close-guard first, render
   later (I17, I19, P11).
4. Doc rot is the base rate: bind by selector, never restate contracts,
   detect stale-vs-churn and moving-target-under-implementation (I9,
   P14, P15).
5. Reject workshop/whole-system formats lacking evidence (event
   storming, Gherkin as design syntax, whole-system generation) and
   keep coverage a ratio over declared scope (I27-I29).

---------------------------------------------------------------------

## 7. Verification pass (2026-10-09)

Verifier had WebSearch/WebFetch plus Crossref/OpenAlex/Semantic
Scholar APIs. Every [unverified] tag, every abstract-only source that
a finding relies on, and every author-standing claim was re-checked.
In-place edits above carry the marker [v2026-10-09].

### 7.1 Fixed (citation metadata or wording corrected in place)

- F4/S1: "Google does not require design-review completion before
  coding" overstated Ubl; replaced with his exact wording, and the
  counterpoint from S65 (most Google teams require an approved design
  doc before major work) added.
- S1: Ubl's Google role corrected from "AMP tech lead" [unverified] to
  Principal Engineer, Google Search Rendering, later Engineering
  Director, Google Search (his About page), with AMP creator credit
  from a Google Cloud Next speaker page.
- S14: sixth author (Weinreich), volume and pages added.
- S15: venue pages added (dblp); Keeling's employer not confirmed.
- S31: five-pattern counts added to F22 from a secondary review
  (S31b), clearly labelled; S32 now has an abstract-level summary.
- S40, S41: were "title only"; now fully cited with abstracts read
  (see F25a below).
- S48: pages, award and SEI affiliation added.
- S49: author list completed (David Lo was missing); arXiv id added.
- S50: authors expanded; venue search found no publication (stays a
  preprint, G3).
- S54: full author list and 2020 issue year added (online 2018).
- S55: fifth author, volume and year corrected (JSS 172, 2021; online
  2020); method details added.
- S56: JSS volume confirmed; S57: abstract quotes re-confirmed.

### 7.2 Author standing confirmed or marked

| Claim | Status | Source |
|---|---|---|
| Ubl was a senior Google engineer | CONFIRMED (Principal Engineer, then Eng Director, Search; about 11 years) | industrialempathy.com/about |
| Ubl is Vercel CTO | CONFIRMED (already) | vercel.com byline |
| Vogels is Amazon CTO | CONFIRMED | allthingsdistributed.com/about.html |
| Nygard wrote Release It! | CONFIRMED (Pragmatic Bookshelf 2007, 2nd ed. 2018) | O'Reilly listing, library record |
| Orosz led teams at Uber | CONFIRMED (already) | blog.pragmaticengineer.com/about |
| Ernst/Bellomo/Ozkaya/Nord/Gorton at SEI | CONFIRMED | sei.cmu.edu library and author pages |
| Keeling at IBM | UNCONFIRMED (book author only) | dblp, O'Reilly |
| Fowler standing | CONFIRMED (Thoughtworks Chief Scientist) | martinfowler.com/aboutMe |
| Jacobson standing | CONFIRMED (Ericsson, Rational, IJI) | Wikipedia, ICSE 2018 keynote |
| Simon Brown standing | CONFIRMED as consultant/creator, no product role | DDD Europe bio |
| Brandolini standing | CONFIRMED as consultant/creator | eventstorming.com, Leanpub |
| Petre / van der Hoek | CONFIRMED academics (Open University; UC Irvine) | MIT Press Bookstore listing, ISR UCI |
| Josef Blake (Spotify) role | UNCONFIRMED (byline only, no title) | Spotify engineering post |
| Adam Gluck (Uber) role | CONFIRMED on page (Sr. Software Engineer II, engineering strategy team) | Uber blog |

### 7.3 Downgraded

- F40 Keeling clause: abstract never read; now title-only (G3, weak).
- S15 standing: "practitioner" kept, employer claim withdrawn.
- F36 (EventStorming): stays weak. Web search over ICSE/ESEM/RE/REFSQ
  found no empirical study; the only signal is the Thoughtworks Radar
  ring (Adopt, Nov 2018), which is consultancy opinion.

### 7.4 Removed

- Nothing removed. No citation turned out fabricated; all DOIs
  resolved and titles matched.

### 7.5 Added findings (practitioner gaps)

F41. Google, as a company norm: "Most teams at Google require an
approved design document before starting work on any major
project"; docs are archived after launch and re-reviewed against
their goals before launch; documentation is "treated as code" with
owners ("Documents without owners become stale"); Google attaches
"freshness dates" with automated email reminders, and adding a "Last
reviewed by..." byline "led to increased adoption". [Google-authored
book, G2] (S65)

F42. HashiCorp: company-wide two-document flow, a PRD (problem) then
an RFC (solution); RFC background is "a paragraph or two",
implementation "a couple of pages"; anyone may comment, team leads
must approve; implementation starts after approval; skip the RFC when
implementing is faster than writing it, and write it afterwards.
[first-party company doc, G2; unsigned, quotes named staff including
co-founder Mitchell Hashimoto] (S67)

F43. Spotify (Creator team): decisions come out of RFCs or meetings;
for large changes "Write an RFC!" first, then an ADR records the
outcome; small decisions get an ADR directly; implicit undocumented
standards are "backfilled" as ADRs, often surfaced in peer review;
ADRs reduced context loss when system ownership moved between teams.
[company engineering blog, G2; author's role not stated] (S68)

F44. Stripe: a cross-org API review board sets API guidelines and
reviews public-facing changes; 20-page design docs are "not unusual"
in API review; CI checks that required steps (OpenAPI spec, client
library generation) ran before public API changes ship. [WEAK:
second-hand Postman developer-relations write-up of a talk by a
Stripe developer advocate, G3] (S69)

F45. Expert designers (Petre and van der Hoek, MIT Press 2016): 66
insights distilled from decades of observing professional designers.
Insight titles confirmed in publisher/retailer copies: "Experts
generate alternatives", "Experts draw the problem as much as they
draw the solution", "Experts design throughout the creation of
software", "Experts involve the user", "Experts prefer simple
solutions", "Experts see error as opportunity". [expert synthesis of
empirical observation, G3; official MIT Press page returned 403 and no
companion site resolved, so the full insight list is unread] (S70)

F46. Whiteboard sketching (8 pairs of professional designers, 14 hours,
4,000+ coded events): designers use general-purpose notations, invent
syntax as needed, work across groups of complementary sketches, and
the reasoning activities (mental simulation, review of progress,
consideration of alternatives) "often leave no trace and rarely lead
to sketch creation". [empirical, TSE, G1] (S71)

F25a. Two more modelling-practice surveys now read at abstract level:
113 embedded MBE respondents use models mainly for simulation, code
generation and documentation, and complain of tool interoperability,
training effort and usability (S40); 155 Italian professionals rate
modelling as relevant, with effort and low perceived usefulness
slowing adoption and lack of skills and tools blocking it (S41).
[empirical, SoSyM and JSS, G1] These agree with F25.

Cross-references to the failure file (section 7 there): Uber DOMA
layers and gateways, Shopify Wedge/Packwerk, Amazon Builders' Library
retries, fitness functions (Thoughtworks/Ford et al.), Lattix,
Structure101 and Bazel visibility. Those are failure/conformance
evidence and are not duplicated here.

### 7.6 Implication changes

- I4 (alternatives) STRENGTHENED: F45 and F46 (alternatives are
  generated but leave no trace) and S66 (63% of ADRs created already
  "accepted"). Keep Advisory. New rule PLAN-P25 below.
- I7 and I31 (review gates) TIGHTENED, not flipped: F41 (Google) and
  F42 (HashiCorp) show approval BEFORE implementation is the norm for
  major work. Revised: at the highest tier, an unacked committed entity
  blocks its implementing ticket from entering in-progress (a frob
  join); lower tiers stay non-blocking as before (Ubl F4, Uber F5).
- I32 NEW, ADOPT: `owner` plus last-reviewed metadata per committed
  entity; time-based freshness lint PLAN-P26 complements churn-based
  P14. Reason: F41 (freshness dates, owner bylines increased
  adoption).
- I33 NEW, ADAPT: keep problem and solution separate, as in PRD then
  RFC (F42), PR/FAQ (F7) and "draw the problem" (F45): goals carry the
  problem and decisions/scenarios the solution. Check: PLAN-P27.
- I34 NEW, ADOPT: ADR backfill is legitimate (F43): a decision may
  carry `recorded_after` so P04 and P25 do not fire on retroactive
  records.
- I15 STRENGTHENED by F46 (general-purpose notations, groups of
  sketches): keep `attach` non-semantic, allow several per entity.
- I27 (reject EventStorming grammar) UNCHANGED; I29 (reject
  whole-system modelling) STRENGTHENED by the Petre counts (35 of 50
  no UML, 0 wholehearted) and F25a.

### 7.7 Added candidate lint rules

| Id | Anti-pattern prevented | Predicate | Pol | Source |
|---|---|---|---|---|
| PLAN-P25 | Decision born accepted (deliberation skipped) | decision's first appearance in git history already has status accepted, fewer than 2 options, and no `recorded_after` | P | S66, F45, F46 |
| PLAN-P26 | Unowned or unreviewed design ages out | committed entity with no `owner`, or last ack older than profile N days | A | F41 |
| PLAN-P27 | Solution without a problem | accepted decision or committed scenario with no path to a goal | A | F42, F7, F45 |
| PLAN-P28 | Implementation started before approval (top tier only) | ticket implementing a tier-1 committed entity entered in-progress before the entity's owner ack | M | F41, F42 |

### 7.8 New bibliography entries

S65. Tom Manshreck (ed. Riona MacNamara). "Documentation", ch. 10 of
T. Winters, T. Manshreck, H. Wright (eds.), "Software Engineering at
Google", O'Reilly 2020; free online
https://abseil.io/resources/swe-book/html/ch10.html . Credibility:
G2, Google-authored book about Google practice.

S66. Garcia de Santana Junior, Figueiredo, Peixoto, Araujo (IBM
Research), Prazeres, Machado, da Mota Silveira Neto, Almeida.
"Architecture Decision Records: Adoption, Impact, and Developer
Engagement in Open-Source Software." ICSA 2026 research track.
https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou
Credibility: G1-, ICSA; mostly academic (UFBA, UFRPE) plus IBM
Research; abstract only.

S67. HashiCorp. "Writing Practices and Culture", How HashiCorp Works.
https://www.hashicorp.com/how-hashicorp-works/articles/writing-practices-and-culture
Credibility: G2, first-party company process doc; no byline.

S68. Josef Blake. "When Should I Write an Architecture Decision
Record." Spotify Engineering, 14 Apr 2020.
https://engineering.atspotify.com/2020/4/when-should-i-write-an-architecture-decision-record
Credibility: G2, first-party company engineering blog; author's
role not stated.

S69. Joyce (Postman senior director of developer relations). "How
Stripe Builds APIs." Postman blog, 18 Jul 2022.
https://blog.postman.com/how-stripe-builds-apis/ . Credibility: G3,
second-hand vendor write-up of a Stripe talk; used only as weak
evidence.

S70. Marian Petre, Andre van der Hoek. "Software Design Decoded: 66
Ways Experts Think." MIT Press, 2016, ISBN 9780262035187
(paperback 9780262553049). Looked up via
https://mitpressbookstore.mit.edu/book/9780262035187 and
https://isr.uci.edu/node/2709.html ; mitpress.mit.edu returned 403.
Credibility: G3, expert synthesis by two academics (Open University;
UC Irvine) who study professional designers.

S71. Nicolas Mangano, Thomas D. LaToza, Marian Petre, Andre van der
Hoek. "How Software Designers Interact with Sketches at the
Whiteboard." IEEE TSE 41(2), 2015.
https://doi.org/10.1109/tse.2014.2362924 . Credibility: G1, TSE;
professional designers as subjects; abstract read.

S73. Thoughtworks Technology Radar. "Event Storming" (Trial Nov 2015,
Apr 2016; Adopt Nov 2018).
https://www.thoughtworks.com/radar/techniques/event-storming .
Credibility: G2/G3, consultancy adoption signal, not evidence of
effectiveness.

### 7.9 Revised coverage verdict

Before: "not provably exhaustive", with six named unread families.
After: all [unverified] tags in this file are resolved except two
(Keeling's employer; Spotify author's role), both on G3/G2 sources
whose content is not disputed. Practitioner gaps filled for Google
(SWE book), Amazon (CTO bio), Spotify, HashiCorp, Uber (via the
failure file), Shopify (via the failure file); Stripe only
second-hand (weak); Netflix: no first-party design-doc or RFC process
post was found by search (gap recorded, not filled). EventStorming
remains without empirical evidence after a targeted search.
Still unread: Petre 2013 full text, Bryar/Carr "Working Backwards",
the full Software Design Decoded insight list, Cockburn and Evans
books. None of these would flip a recommendation: the decision-
relevant claims (ADR adoption gap, doc rot, progressive strictness,
analysis over drawing) are each supported by at least two
independent G1/G2 sources after this pass.
Verdict: SUBSTANTIALLY COMPLETE for the decisions grmb has to make;
not exhaustive for the long tail of company processes.
Recommendations that flip: none. Recommendations that change: I7/I31
tightened (approval before implementation at the top tier), I32-I34
and P25-P28 added.
