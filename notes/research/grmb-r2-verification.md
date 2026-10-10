# grmb research cycle R2, topic G: verification and traceability practice

Ticket ~5QA6P6W (R2 early). Researcher G. Date 2026-10-09.

Question: how do teams that ship tie verification to goals, and what does
that mean for the grmb level pairing

    goal       -> acceptance test          (customer_test)
    scenario   -> system / e2e test        (system_integration_test_plan)
    flow       -> integration / contract   (no verified_by today)
    impl       -> unit test                (component_unit_test)

and for `grimble trace` showing the V with pass/fail.

Baseline not repeated here (R1 established it): traceability completeness
predicts defect rate and pays at task level (synthesis K12: Rempel and
Maeder TSE 2017; Maeder and Egyed EMSE 2015); links decay and link
maintenance is the main cost (E:F21-F22; Wohlrab et al. RE 2018, A:F39);
BDD costs are example duplication and frozen specs, so Gherkin binds by
selector and is never grmb syntax (K21, A:I28); per-arm verification
obligations, not test generation (K22, X11); PLAN005/PLAN006 as drafted;
completeness ratios and ratchet (C20); stale design PLAN022 (C21); moving
target PM040 (C22); skipped test PLAN-P21 (A). This note builds on those.

Grades used below. Evidence kind: STD (standard or regulator text), EMP
(peer-reviewed empirical study), EXP (named-company experience report),
VEN (official vendor or tool documentation), OPN (practitioner opinion).
Credibility grade: G1 primary text read in this run, peer-reviewed or
normative; G2 primary abstract or official doc read, or practitioner at
scale with a named employer; G3 secondary only, small sample, or vendor
self-study. [unverified] marks anything not confirmed in this run.

---------------------------------------------------------------------

## 1. Scope and search log

### 1.1 Strata enumerated first

1. Regulated V-model standards: DO-178C (+ CAST-15, DO-333), ISO 26262-6,
   IEC 62304 (+ FDA General Principles of Software Validation, AAMI
   TIR45), Automotive SPICE 4.x, ISO/IEC/IEEE 29148 and 29119, IEEE 829,
   NASA SE Handbook, SEBoK and Forsberg/Mooz Vee.
2. Requirements and ALM tools and their link-liveness mechanics: IBM
   DOORS Next (link validity), Siemens Polarion (suspect links), Jama
   Connect (suspect links, Trace Score, benchmark), Xray for Jira
   (coverage status), Azure DevOps (requirements traceability), Serenity
   BDD (requirements reports), Pact.
3. Agile acceptance practice: ATDD/FIT, specification by example, BDD
   (Cucumber discovery/formulation/automation, example mapping), GOOS
   double loop, subcutaneous tests, test cases as requirements.
4. Timing evidence: TDD test-first vs test-last, observed developer
   testing, BDD co-evolution.
5. Test shape: pyramid, ice-cream cone, hourglass, honeycomb, trophy;
   test size vs scope; flakiness by size; definitions of unit vs
   integration.
6. Contract testing: consumer-driven contracts, Pact, case studies and
   the 2025 SLR.
7. Industrial traceability and RE-test alignment: six-company RE-VV
   study, REST taxonomy, mapping study, automotive traceability, Eiffel
   at Ericsson, R-Scrum at QUMAS, scaled agile for safety, safety+agile
   mapping/SLR, event-based traceability, trace link evolution, test-to-
   code link recovery, grand challenges.
8. Adequacy of requirements-based testing: requirements coverage metrics
   (UFC), DO-178C structural coverage resolution, cost of low-level
   testing.

### 1.2 Queries run (WebSearch unless noted)

- DO-178C 6.4 low-level testing duplication; DO-178C structural coverage
  resolution derived requirements dead code; CAST-15 merging HLR LLR.
- Automotive SPICE 4.0 SWE.4/5/6 traceability; vda-qmc PAM download
  (PAM 4.1 preview PDF fetched and read via pdftotext).
- ISO 26262-6 unit verification requirements-based test; ISO 26262-6
  clauses 9-11 test environments.
- IEC 62304 5.7 traceability; FDA GPSV (PDF fetched, read via pdftotext).
- NASA SE Handbook verification methods (SP-2016-6105 Rev2 PDF fetched
  and read); ISO 29148 verification methods; ISO 29119 test levels.
- Forsberg Mooz Vee; SEBoK Vee (page 404 on fetch).
- AAMI TIR45; SafeScrum; Steghofer et al. scaled agile safety (arXiv PDF
  read); Fitzgerald et al. R-Scrum ICSE 2013.
- Bjarnason et al. RE-VV six companies (arXiv abstract); test cases as
  requirements (arXiv abstract, IST 2016).
- Melnik Maurer executable acceptance tests; Haugset Hanssen FIT.
- Fucci et al. TDD dissection; Beller et al. developer testing; Nagappan
  et al. TDD at Microsoft and IBM.
- Google SWE book ch. 11 (fetched); Just Say No to More E2E Tests
  (fetched, body partly via comments); Where do our flaky tests come
  from; Taming Google-scale continuous testing (OpenAlex abstract).
- Trautsch et al. unit vs integration JSS 2020; Trautsch and Grabowski
  ICST 2017 (OpenAlex abstract); Contan et al. AQTR 2018 (Crossref).
- Spotify testing of microservices (fetched); Kent C. Dodds testing
  trophy (search); Fowler SubcutaneousTest (search excerpt).
- Robinson consumer-driven contracts (fetched); Pact docs (fetched);
  Lehva et al. PROFES 2019 (Crossref); Schwarz, Quast, Riehle STVR 2025
  (PDF fetched and read); Waseem et al. (search, cited secondhand).
- Zampetti et al. BDD in OSS (abstract fetched); Pereira et al. BDD XP
  2018 (OpenAlex abstract); Cucumber BDD and Example Mapping docs
  (fetched); Adzic SBE (publisher TOC); GOOS (official TOC via search).
- Jama suspect links help (fetched), Trace Score and 2022 benchmark
  press release (fetched); Polarion suspect API (search); DOORS Next
  link validity (search, Jazz forum); Xray coverage status (search);
  Azure DevOps requirements traceability (search of Microsoft Learn);
  Serenity BDD (search; official site refused connection).
- Cleland-Huang et al. event-based traceability TSE 2003 (OpenAlex
  abstract); Rahimi and Cleland-Huang EMSE 2017 TLE (search + dissertation
  record); Grand Challenges of Traceability 2017 (arXiv abstract); Van
  Rompaey and Demeyer CSMR 2009; White and Krinke TCTracer EMSE 2022.
- Staats et al. NFM 2010 requirements coverage (NTRS record fetched);
  Whalen et al. ISSTA 2006 (search); Sun et al. arXiv 2017 DO-178
  requirements-based testing (PDF read).
- Crossref API (curl) for DOIs and venues of ~20 items; OpenAlex API
  (curl) for abstracts and affiliations (rate-limited part-way, 429).

### 1.3 Exclusions

- Anonymous or SEO blogs and vendor marketing without a named method
  (many "test pyramid vs trophy" posts): excluded.
- Tool-vendor whitepapers (Parasoft, LDRA, Rapita, QA Systems, VectorCAST)
  used only to locate clause numbers, never as sole support for a claim
  about what a standard requires; where only such sources exist the
  claim is marked G3.
- Pirated DO-178C PDFs that surfaced in search: not opened.
- MBT and test generation: covered by R1 E (X11), not re-opened.

### 1.4 Coverage argument

The strata in 1.1 cover the three ways an organisation can tie
verification to goals: by regulation (stratum 1), by tool (2), and by
team practice (3-6), plus the empirical evidence on whether the ties
hold (7-8). Within each stratum the anchor sources were found and, where
free, read in primary form: three normative or regulator texts were read
in full text this run (FDA GPSV 2002, ASPICE PAM 4.1 preview, NASA SE
Handbook Rev2), which between them state the level pairing, the timing of
test planning and the allowed verification methods. The paywalled
standards (DO-178C, ISO 26262, IEC 62304, ISO 29148/29119, TIR45) were
reached only through secondary sources; each claim drawn from them is
corroborated by at least two independent secondaries or graded G3. The
empirical strata were drained through their mapping studies and most-
cited primaries (RE-VV alignment, traceability in automotive, Eiffel,
R-Scrum, TDD process, BDD in OSS, CDC SLR, unit/integration definitions).

Unread and why it would not change the conclusions:
- Normative texts of DO-178C, ISO 26262-6, IEC 62304, 29148, 29119,
  TIR45: the free texts (FDA, ASPICE, NASA) already state each point the
  recommendations rest on (pairing, early planning, non-test methods,
  results traceable to measures); the paywalled texts are cited only for
  the cross-level allowance, which two independent secondaries agree on.
- Books: Adzic "Specification by Example", Smart "BDD in Action", Pugh
  "Lean-Agile ATDD", Freeman and Pryce GOOS body text, SafeScrum book,
  Martraire "Living Documentation": they are practitioner method books;
  R1 already took their main claims from abstracts and TOCs, and no
  recommendation here depends on a claim only they make.
- Full texts of Bjarnason et al. EMSE 2014, Wohlrab et al., Waseem et al.
  survey, Melnik thesis: abstracts are used; detail would refine but not
  reverse the direction (alignment needs change communication and
  living links).
- No study was found that measures defect detection by test level
  against goals in industry; the absence is itself a finding (F17).

---------------------------------------------------------------------

## 2. Findings

### 2.1 The V pairing in regulated practice

F1. The pairing is stated almost verbatim by the regulator. FDA GPSV
(2002, still current except section 6) lists traceability analyses
"Unit (Module) Tests to Detailed Design", "Integration Tests to High
Level Design", "System Tests to Software Requirements"; it also requires
source code to trace back to design and to risk analysis, tests for
modules to trace to design and to source code. This matches grmb's
impl->unit, (flow/architecture)->integration, scenario->system, with
goal->acceptance from the acceptance test plan of the requirements
phase.
STD, G1 (full text read). Credibility: US FDA guidance document, the
reference commentary for IEC 62304 practice. [S1]

F2. Automotive SPICE 4.x states the same pairing as processes and
names "verification measures", not tests. SWE.4 verifies units against
the detailed design; SWE.5 verifies components against the architecture
and integration "including the interfaces of, and interactions between,
the software components" (note 1: "correct dataflow and dynamic
interaction between software components ... the correct interpretation
of data by all software components using an interface"); SWE.6 verifies
the integrated software against the software requirements; VAL.1
validates the end product against stakeholder requirements in the
operational environment. Every verification process requires
bidirectional traceability between measures and the left-arm artifact
AND between results and measures, and selection of measures "according
to the release scope" including regression criteria. Unit verification
measures explicitly include "static analysis, code reviews, and unit
tests" (SWE.4 note 1). Note 4 in SWE.4 and SWE.6: "Traceability alone,
e.g., the existence of links, does not necessarily mean that the
information is consistent."
STD, G1 (PAM 4.1 preview text read; 4.0 wording agrees per UL and
Synopsys secondaries). Credibility: VDA QMC, the assessment model used
by German OEMs on their suppliers. [S2, S3]

F3. Validation at the goal level is not test-only. ASPICE VAL.1 gives
pass/fail criteria "if applicable"; note 2 says where stakeholder
requirements change frequently, "repeated validation of (often rapidly
developed) increments" refines them; note 3 says validation also
confirms "less formally expressed ... subjective tests" of user
satisfaction. NASA separates verification (against "shall" statements,
Appendix D matrix) from validation (against stakeholder expectations,
Appendix E matrix) and defines four methods: Analysis, Demonstration,
Inspection, Test, with test "the most resource-intensive".
STD, G1 (both read). Credibility: VDA QMC; NASA SP-2016-6105 Rev2. [S2, S4]

F4. Higher-level tests may discharge lower-level verification. Two
secondaries on the systemsafety list (Dewi Daniels, NCC Group, a DO-178
practitioner; Steve Tockey) quote DO-178C: requirements-based tests
"can be hardware/software integration tests, software integration tests
or low-level tests" and structural coverage "can be achieved through a
combination" of them (figure 6-1); the note to 6.4.1 says low-level
testing is needed where coverage needs "more precise control and
monitoring of the test inputs" than integration allows. For IEC 62304, a
commentary reports that clauses 5.6.4 and 5.7.1 note that "one set of
tests can satisfy" both integration and system verification.
STD via secondary, G3 for exact wording (standard not read), but two
independent secondaries agree; consistent with Sun et al. below. [S5,
S6, S7]

F5. Merging levels is allowed but watched. CAST-15 (FAA-published
Certification Authorities Software Team position paper) exists because
applicants merged high- and low-level requirements "for simple products"
without meeting the objectives of both levels; DO-178C section 5.0 then
added a note that an applicant may need to justify a single level of
requirements; EASA CM-SWCEH-002 carries the same content.
STD via secondary, G3 (Wikipedia summary of an FAA document; the paper
itself not fetched). [S8]

F6. Low-level (unit) requirement testing is costly and perceived low
value even in avionics. Industrial authors from Rolls-Royce, Altran UK
and Rapita Systems estimate "on average, two days per procedure/
function" for LLR tests, 50 person-years for a 250 KLOC project, and
cite "the generally held view that low-level testing is of relatively
low value"; DO-333 allows proof instead of low-level tests but few use
it. Their DO-178 summary: requirements-based tests "must not use
internal structure"; "Inadequate structural coverage ... indicates
that requirements are missing or that implementation behaviour is
unspecified".
EXP + method, G2 (arXiv preprint read; authors' employers named on the
paper). [S9]

F7. Structural coverage closes the loop from code back to requirements.
DO-178C 6.4.4.3 resolves uncovered code as one of: shortcomings in
requirements-based tests, inadequate requirements (add a derived
requirement), extraneous/dead code (remove), or deactivated code (show
the configuration). FDA asks the same in prose: code "can be traced back
to an element in the software design specification".
STD via vendor secondaries (QA Systems, Rapita), G3 for DO-178C wording;
G1 for the FDA half. [S1, S10]

F8. Requirements coverage alone is a weak adequacy criterion. Staats,
Whalen, Heimdahl and Rajan (NASA Formal Methods 2010) evaluated three
requirements coverage metrics over LTL-formalised requirements: only
Unique First Cause coverage was rigorous enough that satisfying suites
reliably beat random suites of similar size; more rigorous metrics found
more faults.
EMP, G2 (NTRS record abstract). Credibility: University of Minnesota
group with long NASA and Rockwell Collins avionics collaboration
[standing from the ISSTA 2006 avionics example, S12]. [S11, S12]

F9. Planning verification happens on the left arm, at the same time as
the artifact. FDA GPSV lists "System Test Plan Generation" and
"Acceptance Test Plan Generation" as requirements-phase tasks and
"Module Test Plan Generation", "Integration Test Plan Generation" as
design-phase tasks; "Test plans and test cases should be created as
early in the software development process as feasible." NASA: "The
verification approach to use should be included as part of requirements
development ... to ensure that the requirements are verifiable"; the
Appendix D matrix pairs every "shall" with a method. SEBoK summarises
the Vee as "the need to define verification plans during requirements
development". ASPICE BP1 in every verification process is "Specify ...
verification measures", including pass/fail criteria.
STD, G1 (FDA, NASA, ASPICE read); SEBoK G3 (search snippet, page 404).
[S1, S2, S4, S13]

F10. Agile under regulation keeps the V but makes links "living".
R-Scrum at QUMAS (ICSE-SEIP 2013) introduced "continuous compliance" and
"living traceability"; SafeScrum (SINTEF, IEC 61508) splits safety
requirements into a separate backlog and was accepted by certification
bodies in 2015; Steghofer et al. (PROFES 2019; Chalmers with automotive
experts) define living traceability as developers "actively and
continuously create, maintain, and delete trace links while they go
about their development work", and report the open problems: choosing
a traceability information model, tracing between sibling safety
requirements, and tracing review status and decisions. They also state:
"More fine-grained artefacts (lower-level artefacts) should contain
links that link to more abstract artefacts", and "A common
misunderstanding of bidirectional traceability is that trace links
must exist in both directions -- instead, tools must exist that can
reconstruct one direction from the other". AAMI TIR45 (FDA-recognised)
reconciles agile with 62304 through a definition of done that includes
verification per increment [secondary only].
EXP + EMP, G1 for Steghofer (full text read), G2 for R-Scrum (abstract),
G3 for TIR45 (consultancy summaries). Mapping and SLR context: Kasauli
et al. SEAA 2018 (six large Swedish companies), Heeager and Nielsen IST
2018. [S14-S19]

### 2.2 Tools: how links are kept alive

F11. Every major ALM tool implements the same liveness device: the
suspect link. Jama: a link becomes suspect when an upstream item
changes, "Only updates to certain fields trigger suspect links" (admin-
configured), and a human clears it (Clear / Clear All) after review.
Polarion exposes isSuspect/setSuspect on linked work items and marks test
cases linked to a changed item as suspect until "unsuspected". DOORS
Next replaced "suspicion" by "Link Validity": a link is Valid or Invalid
by explicit user statement, otherwise Suspect; validity is computed from
the content of both ends. IBM RQM has a "Reconcile" action for test
cases after a requirement change.
VEN, G2 (Jama help read); G3 for Polarion and DOORS (API page and Jazz
forum answer by an IBM developer). [S20-S22]

F12. Tools report requirement status from test runs, with a small
status vocabulary. Xray computes a requirement coverage status (OK when
all linked tests pass, NOK, NOTRUN for unexecuted); Azure DevOps groups
pipeline test results by linked requirement and has a widget for
requirements with no tests; Serenity BDD builds a requirements hierarchy
from feature directories and reports per requirement which scenarios
cover it and their status.
VEN, G3 (community answers and search snippets of Microsoft Learn and
Serenity; official pages not fully read). [S23-S25]

F13. Vendor benchmark: trace completeness is low in practice and
correlates with test outcomes. Jama (press release 2022, over 40,000
projects): top decile average Trace Score 87%; top quartile 2.5x faster
test execution and defect detection than bottom quartile, nearly 2x more
completed and passed tests; 57% of companies have projects in more than
one quartile; median 35% (webinar snippet only). Trace Score =
established / expected relationships under the project's relationship
rules.
VEN self-study, G3 (method undisclosed, correlational, seller of the
tool). Consistent in direction with Rempel and Maeder (R1 K12). [S26]

F14. Pipelines can generate the links. Eiffel (Ericsson; Stahl, Hallen
of Ericsson with Bosch, EMSE 2017) emits CI/CD events that link
artifacts, and reduced traceability data acquisition "from days to
minutes"; interviewees regard traceability as a prerequisite for large-
scale CI/CD. Cleland-Huang et al. (TSE 2003) proposed event-based
traceability because links "erode over [the system's] lifetime"; Rahimi
and Cleland-Huang (EMSE 2017) evolve requirement-code links from change
patterns, more accurately and cheaply than regenerating them.
EXP + EMP, G2 (abstracts). Credibility: Ericsson authors on the Ericsson
system; Cleland-Huang leads the traceability field (Grand Challenges
2017, CoEST). [S27-S30]

F15. Test-to-code links are recoverable when names follow conventions,
less so otherwise. Van Rompaey and Demeyer (CSMR 2009): "test
conventions yield highly accurate results", and calls before asserts are
the best fallback. TCTracer (White and Krinke, EMSE 2022): MAP 85% for
test-to-function and 92% for test-class-to-class links on five large OSS
systems by combining static and dynamic signals.
EMP, G2 (abstracts). [S31, S32]

### 2.3 Agile acceptance practice

F16. Acceptance criteria are agreed before development, as rules with
examples. Cucumber's BDD is "a three-step, iterative process" of
Discovery, Formulation, Automation, implementing behaviour "starting
with an automated test"; tests and docs are "nice side-effects". Example
Mapping (Wynne and Tooke) runs "before a user story is pulled into
development": yellow story card, blue rule cards (acceptance criteria),
green example cards ("a good basis for acceptance tests"), red question
cards. GOOS (Freeman and Pryce): "Start Each Feature with an Acceptance
Test", first a walking skeleton tested end to end.
VEN/OPN, G2 (Cucumber docs read; GOOS official TOC). Credibility:
Cucumber is the reference BDD toolchain; Wynne co-founded Cucumber Ltd
[from Cucumber docs authorship; not separately verified]. [S33-S35]

F17. In practice tests are written during or after the code, and the
test-first order is not what pays. Zampetti et al. (IST 2020): 27% of
50,000 popular OSS projects use BDD frameworks (68% in Ruby), often for
unit testing; scenarios co-evolve with code in about 37% of cases and
"changes to scenarios and fixtures often happen together or after
changes to source code"; most of 31 surveyed developers write tests
during or after coding. Beller et al. (TSE 2019; 2,443 engineers over
2.5 years): TDD "is not widely practiced"; half the developers do not
test at all in the IDE; developers think they test half their time and
actually spend about a quarter. Fucci et al. (TSE 2017; 39 professionals
at two companies): quality and productivity gains associate with
granularity and uniformity, sequencing (test-first vs test-last) had no
important influence. Nagappan et al. (EMSE 2008; three Microsoft teams
and one IBM team): pre-release defect density 40-90% lower with TDD at a
15-35% initial time cost.
EMP, G1/G2 (abstracts; Fucci arXiv). Credibility: Nagappan was at
Microsoft Research with Microsoft product teams; Beller et al. data from
real IDE use. [S36-S39]

F18. Test cases can be the requirements, in five variants. Bjarnason,
Unterkalmsteiner, Borg, Engstrom (IST 2016; three companies, 14
interviews, 2 focus groups): variants de facto, behaviour-driven,
story-test driven, stand-alone strict, stand-alone manual, which differ
in when requirements are documented and how far tests are executable
specifications; the fit depends on number of stakeholders and rate of
change. Six-company RE-VV study (EMSE 2014; 30 practitioners): weak
alignment causes "new requirements going untested or outdated ones
being wrongly verified" when testers are not told of changes; human
cooperation, change control and "externally enforced traceability"
drive alignment. Earlier FIT studies: Hanssen and Haugset (HICSS 2009)
and Haugset and Hanssen (Agile 2008) found automated acceptance tests
"may improve important parts of an agile process" with open costs;
Ricca et al. student experiments found FIT tables improve requirement
understanding.
EMP, G2 (abstracts). Credibility: Lund/BTH/Chalmers group with named
industrial partners over a decade (REST taxonomy TOSEM 2014, mapping
study ICSTW 2011). [S40-S45]

F19. Acceptance tests need not run through the UI. Fowler's
"subcutaneous test" operates "just under the UI", for end-to-end
behaviour that is hard to test through the UI, "usually ... much
faster"; the risk is UI-resident logic left untested. Adzic's SBE has a
key pattern "Automating validation without changing specifications"
[chapter content unverified].
OPN, G2 (Fowler: Thoughtworks chief scientist; search excerpt). [S46,
S47]

### 2.4 Test shape and size

F20. Test size and test scope are different axes. Google SWE book ch.
11 (Adam Bender): "there are two distinct dimensions for every test
case: size and scope"; target mix "around 80%" narrow-scoped unit, 15%
integration, 5% end-to-end; anti-patterns ice-cream cone (mostly e2e,
"slow, unreliable, and difficult to work with") and hourglass (few
integration tests). Wacker (Google Testing Blog 2015): an e2e-centred
strategy fails on its feedback loop; suggests 70/20/10 "The exact mix
will be different for each team, but ... it should retain that pyramid
shape."
EXP, G2. Credibility: Google engineers on Google's own practice. [S48,
S49]

F21. Larger tests are flakier; failing tests are close to their code.
Listfield (Google 2017): of about 4.2M tests, ~63k had a flaky run in a
week; "the larger the test (as measured by binary size, RAM use, or
number of libraries built), the more likely it is to be flaky." Micco
(2016): ~1.5% of runs flaky, ~16% of tests have some flakiness. Memon et
al. (ICSE-SEIP 2017, Google co-authors incl. Micco): "very few of our
tests ever fail, but those that do are generally 'closer' to the code
they test".
EXP + EMP, G2. [S50, S51]

F22. The pyramid is not universal and level labels are unreliable.
Spotify (Schaffer and Dybeck, 2018) proposes a honeycomb for
microservices: "focus on Integration Tests, have a few Implementation
Detail Tests and even fewer Integrated Tests" (integrated = depends on
another system's correctness). Dodds's testing trophy puts most weight on
integration tests for UI code [standing as Testing Library author not
verified]. Contan et al. (AQTR 2018) found none of five agile projects
had a pyramid shape [abstract via secondary]. Trautsch, Herbold,
Grabowski (JSS 2020; 38,782 Java tests classified by the IEEE
definitions, mutation testing): "no evidence that one test type is more
capable of detecting certain defect types", and propose usage-based
definitions; Trautsch and Grabowski (ICST 2017; 70K revisions, 10 Python
projects): "developers believe that they are developing more unit tests
than they actually do" and the chosen definition changes the count.
EXP (Spotify, G2), OPN (Dodds, G3), EMP (Trautsch, G1/G2). [S52-S56]

### 2.5 Contract testing

F23. Consumer-driven contracts verify interoperability, not function,
and need a cooperating counterpart. Robinson (martinfowler.com 2006)
defines a consumer-driven contract as one "closed and complete with
respect to the entire set of functionality demanded of it by its
existing consumers", with each expectation an automated check in the
provider's build. Pact: "a technique for testing an integration point
by checking each application in isolation"; provider-contract testing
against an OpenAPI document alone does not show consumers call it
correctly. Schwarz, Quast, Riehle (STVR 2025; SLR plus action research):
CDCT can "(partially) replace integration tests"; defect seeding caught
41 of 53 incompatibilities; but "CDC tests cannot validate the
functional behaviour", developers "could not replace the service
black-box tests but only complement them"; it is impossible against an
external system without control (C1), adoption is sparse (Waseem et
al., secondhand), changes in validity ranges escape (C9), contract
exchange needs a broker (C7). Lehva, Makitalo, Mikkonen (PROFES 2019)
case study: most adoption time went to learning.
EMP (STVR G1 full text; PROFES G2 Crossref + abstract), OPN (Robinson
G2), VEN (Pact G2). [S57-S60]

---------------------------------------------------------------------

## 3. What contradicts the pairing (read this first)

X1. "verifies between unpaired levels" as an Error contradicts the
standards. grmb-spec 4.5 makes a `verifies` between unpaired levels a
model-load error (MDL014). DO-178C lets integration-level tests verify
low-level requirements and achieve coverage (F4), IEC 62304 lets one test
set satisfy integration and system verification (F4), and Trautsch et al.
show the unit/integration label does not track what a test detects
(F22). The pairing is right as a DEFAULT and as the reading of the trace
(F1, F2), wrong as a constraint.

X2. scenario -> "e2e" conflates scope with size. A system-level scenario
claim needs system SCOPE evidence (the integrated behaviour), not a
large, UI-driven test (F20 size vs scope; F19 subcutaneous; F22
honeycomb). Per-arm verification (PLAN006) done as e2e tests produces
the ice-cream cone Google warns against (F20, F21). Arms are best
evidenced at the lowest scope that exercises the handling (Memon: failing
tests are closer to the code; F21).

X3. goal -> "acceptance test" is validation, and validation is not
test-only (F3). A goal can be validated by demonstration, inspection of
analytics, or stakeholder sign-off; grmb's `verified_by` resolves only
to test units (planning 5.8) while claims already admit `evidence ref`
(grmb-spec 4.4).

X4. flow -> "contract test" covers interoperability only and is
impossible toward external actors (F23). Flow evidence must accept
integration tests, contract tests, and for external counterparts a
schema/recorded-stub check; function stays with the scenario.

X5. impl -> "unit test" is not the only acceptable low-level measure:
ASPICE lists static analysis and code review (F2), DO-333 proof (F6), and
low-level tests are where effort is least valued (F6).

X6. Planning-doc mismatch: the brief pairs flow -> integration, but
grmb-planning 6.3 pairs scenario -> `system_integration_test_plan` and
page -> `subsystem_integration_test_plan`, and flows/contracts carry no
`verified_by` (grmb-spec 4.2-4.3). ASPICE SWE.5 and FDA ("Integration
Tests to High Level Design") put integration verification on the
architecture, i.e. grmb's flows and contracts.

Nothing found contradicts: the default pairing itself (F1, F2), per-arm
obligations (ASPICE SWE.6 note 1 names negative testing and fault
injection; DO-178C robustness cases, F6), the computed ladder, or the
trace as the main view (F10-F12).

---------------------------------------------------------------------

## 4. Implications for grmb

I1. ADOPT the pairing as the derived default level of each entity's
evidence, with flows and contracts added: goal (actor parent)
`customer_test`, goal refinement `customer_test_plan`, scenario
`system_integration_test_plan`, flow and contract (new)
`subsystem_integration_test_plan`, page as now, impl
`component_unit_test`. Reason: FDA GPSV and ASPICE state exactly this
(F1, F2). Check: `level` in graph JSON per entity (exists, planning 9).

I2. ADAPT: add `verified_by SEL;` to `flow` and `contract` (Body facet,
same Evidence relation as 6.2). A flow is "integration-verified" when its
evidence resolves; contract-test evidence on a contract covers every flow
naming that contract. Reason: X4, X6; ASPICE SWE.5 note 1 (dataflow and
interface interpretation), Robinson/Pact. Check: PLAN-G02 below.

I3. REJECT unpaired-level evidence as an Error for planning entities (and
recommend the kernel downgrade MDL014's unpaired `verifies` to the same
Advisory). Replace with a level-mismatch Advisory that the trace shows.
Reason: X1. Check: PLAN-G01.

I4. ADAPT how a test's level is known: derive it from what the test is
bound to (the entity whose `verified_by` selects it, or the `frob:tests`
target), never from directory names; optionally refine by frob's touched-
set (a test whose touched units span more than one node is not unit
scope). Reason: Trautsch ICST 2017 and JSS 2020 (labels unreliable),
Google size vs scope (F20, F22). Check: graph JSON `evidence[].level` and
`evidence[].scope` (single impl / single node / multi node).

I5. ADAPT evidence kinds: `verified_by` accepts `test SEL` (default, as
now), `review "SYMREF"`, `analysis "SYMREF"`, `demo "SYMREF"`, mirroring
the claim's `evidence ref` (grmb-spec 4.4) and NASA's four methods. Non-
test evidence counts toward `verified` only with a recorded verdict (a
frob evidence record or ack with date and author); under the release
profile it must be fresh (newer than the entity's last Body change).
Reason: X3, X5; F2, F3. Check: PLAN-G06.

I6. ADAPT goals: show validation separately from verification. A goal's
trace row has two columns: verification (rollup of its scenarios) and
validation (its own `verified_by`, any kind). Reason: NASA and ASPICE
separate the two (F3). Check: rendering only; PLAN005 unchanged.

I7. ADOPT arm evidence at any level, and show the level. PLAN006 is
satisfied by any evidence `for STEP.VARIANT`, whether the test is bound
on the scenario or on the impl that handles the variant (an impl-level
`verified_by ... for STEP.VARIANT`); the trace shows the lowest scope that
covers each arm. Reason: X2; Memon, Google (F20, F21); ASPICE negative
testing (F2). Check: extends 6.2 so an impl clause may carry `for`.

I8. ADAPT the status name. `verified` in planning 5.8 means "verification
is bound", which ASPICE note 4 and Staats et al. warn is not consistency
or adequacy (F2, F8). Rename the computed rung to `covered` (declared <
bound < covered) and reserve `verified` for the frob overlay when every
bound evidence item has a passing (or acked, for non-test) verdict at
the evaluated commit. Reason: avoid presenting link existence as
assurance. Check: 5.8 and 10.2 vocabulary.

I9. ADOPT suspect evidence. When an entity's semantic digest changes
(Sig facet, outcome set, arms, `realizes`; NOT `title` or comments), each
of its evidence links becomes suspect until the bound test's own content
changes or `grimble ack` clears it. Reason: the universal ALM liveness
device (F11), the RE-VV failure "outdated ones wrongly verified" (F18),
Jama's field-scoped triggers. Check: PLAN-G03, lock-based like PLAN022.

I10. ADOPT planning verification with the artifact, not test-first. Ask
for a `verified_by` clause (possibly a selector that does not resolve
yet: "planned") by the time an implementing ticket starts, and for
resolving, passing evidence by the time it closes. Do not check whether
tests were written before code. Reason: FDA/NASA/ASPICE plan on the left
arm (F9), Example Mapping happens before development (F16), but test-
first order shows no effect and is rarely practised (F17). Check:
PLAN-G04 and the close-guard option PLAN-G05.

I11. ADOPT links stored at the fine-grained end where possible. Prefer
`frob:tests <anchor>` on unit and integration tests (the link moves with
the test and survives refactors) and `verified_by` selectors on the
entity for system and acceptance suites (Gherkin features, e2e specs);
both are one relation (6.2), and the trace reconstructs either direction.
Reason: Steghofer et al. (F10), test-to-code recovery is reliable only
under conventions (F15). Check: none new; document the guideline.

I12. ADOPT the trace vocabulary of the tools, extended: per evidence row
`uncovered` (no evidence), `planned` (selector resolves empty), `not-run`
(no evidence record at this commit), `pass`, `fail`, `flaky`, `suspect`
(I9), `stale` (PLAN022). An entity is green only if all its rows are
`pass`. Reason: Xray/Azure DevOps/Serenity statuses (F12), Google
flakiness (F21). Check: `grimble trace --json` schema; verdicts come from
frob evidence (D130: grimble never runs tests).

I13. ADOPT release-scoped trace. `grimble trace --scope <goal|release>`
filters to entities in the scope and shows which evidence was selected
for regression. Reason: ASPICE "selected according to the release scope
... including criteria for regression verification" (F2). Check:
rendering plus the existing `frob test` touched-set.

I14. ADAPT regulated-profile level separation. Under a `regulated`
profile, an impl and its scenario whose evidence sets are identical
(no level-specific measure) is reported, because CAST-15 shows merged
levels lose objectives (F5); default profile silent, because DO-178C and
62304 allow shared tests when coverage is shown (F4). Check: PLAN-G07.

I15. ADAPT reverse trace from code. Under the `regulated` profile only,
report public units of a node owned by a system that no impl realization,
flow end or contract shape selects ("untraced code": a derived
requirement or dead code in DO-178C terms; FDA's code-to-design
analysis). Default off: noisy on ordinary repos and R1 C35 requires a
measured false-positive budget first. Reason: F7. Check: PLAN-G08.

I16. REJECT a test-shape ratio rule as a default. Evidence for any
specific ratio is practitioner opinion (Google 80/15/5, Wacker 70/20/10,
Spotify honeycomb, trophy) and the one shape study is small (Contan).
Offer only a report: counts of evidence by derived level per scenario,
and an opt-in Advisory for scenarios whose arms are covered only at
system scope. Reason: F20, F22. Check: PLAN-G09 (off).

I17. ADOPT contract evidence semantics. Contract evidence on a flow does
not count toward the scenario's functional verification; a flow to an
`external` actor (R1 C28) accepts schema-validation or recorded-stub
evidence and is never asked for consumer-driven contract tests. Reason:
F23 (C1, D1). Check: level of contract evidence is
`subsystem_integration_test_plan` only.

I18. ADOPT Example Mapping as the seeding shape of `frob plan
--from-design` (planning 10.5 already seeds one Given/When/Then per
arm): story = scenario, rule = arm, example = test to write, question =
`todo` hole (R1 C8). Reason: F16 (before development), F18 (behaviour-
driven variant of test-cases-as-requirements). Check: none new.

I19. REJECT requiring both directions of a link to be stored or both
spellings to agree. Bidirectional means reconstructable (F10). Check:
unchanged 6.2 union semantics.

---------------------------------------------------------------------

## 5. Candidate rules

Ids are placeholders (PLAN-Gnn). Polarity: P+ fires on presence, P- on
absence, P0 on mismatch. Severity is the shipping default; R1 C35 applies
(ship Advisory, graduate by ratchet).

| Id | Name | Predicate | Polarity | Default | Source |
|---|---|---|---|---|---|
| PLAN-G01 | LEVEL-MISMATCH | an evidence item of entity e whose derived scope (I4) differs from the paired level of e (I1); reported in the trace, never blocks | P0 | Advisory | F1, F2 (default pairing); F4, F22 (why not Error) |
| PLAN-G02 | FLOW-UNVERIFIED | a flow whose two ends are in different nodes, both ends bound (producer and consumer resolve), carrying no `verified_by` and whose contract (if any) has none | P- | Advisory | ASPICE SWE.5 note 1; FDA "Integration Tests to High Level Design"; Robinson 2006 |
| PLAN-G03 | SUSPECT-EVIDENCE | entity semantic digest (Sig, outcome set, arms, realizes) at HEAD differs from the lock value recorded when each evidence item's test content last changed or was acked | P0 (vs lock) | Advisory; Warn under release profile | Jama, Polarion, DOORS link validity; Bjarnason et al. EMSE 2014 |
| PLAN-G04 | VERIFICATION-UNPLANNED (PM family) | a ticket that `implements` a scenario or goal leaf enters in-progress while that entity has no `verified_by` clause at all | P- | Advisory | FDA GPSV 5.2.2, 5.2.5; NASA 4.2 note; ASPICE BPx specify measures; Example Mapping |
| PLAN-G05 | design_verified close guard (opt-in) | a ticket reaches `done` only if each entity it implements has every evidence row `pass` (or acked non-test) at the closing commit; Unresolved when frob has no evidence record | P- | opt-in guard (regulated profile default) | ASPICE BP3 results with pass/fail; IEC 62304 5.7.4 (secondary) |
| PLAN-G06 | NONTEST-EVIDENCE-UNRECORDED | `review`/`analysis`/`demo` evidence with no recorded verdict, or a verdict older than the entity's last semantic change | P- / P0 | Advisory; Warn under release profile | NASA methods; ASPICE SWE.4 note 1, VAL.1 |
| PLAN-G07 | MERGED-LEVELS | regulated profile: impl i of scenario s where Evidence(i) is empty and every arm of s handled by i is covered only by Evidence(s), or Evidence(i) = Evidence(s) | P0 | off; Advisory under regulated | CAST-15; DO-178C 5.0 note (secondary) |
| PLAN-G08 | UNTRACED-CODE | regulated profile: a public unit owned by a node of a system with planning entities, selected by no impl realization, flow end, or contract shape | P- | off; Advisory under regulated | DO-178C 6.4.4.3 (secondary); FDA GPSV source-code traceability |
| PLAN-G09 | ARM-SYSTEM-ONLY | a non-ok arm whose only covering evidence has system or acceptance scope | P+ | off by default | Google SWE book ch. 11; Memon et al. 2017; weak (no ratio evidence) |
| PLAN-G10 | FLAKY-EVIDENCE (overlay) | an evidence item whose frob record is flaky in the window; entity verdict is not `pass` | P+ | Advisory (overlay, not a grimble rule) | Listfield 2017; Micco 2016 |

Not proposed as rules: test-first ordering (F17 shows no effect),
pyramid ratios (I16), a requirement that both link spellings exist (I19).

---------------------------------------------------------------------

## 6. `grimble trace`: the V view (sketch)

```
grimble trace web_app.checkout            (commit 1a2b3c, release r12)
LEFT ARM                         LEVEL               RIGHT ARM                          VERDICT
goal customer.place_order        requirements        validation: demo docs/uat.md#r12   pass (acked 2026-10-01)
  scenario checkout              system_spec         tests/e2e/checkout.spec.ts         pass
    arm reserves_stock.out_of..  (arm)               impl: tests/api/test_stock.py::oos unit-scope  pass
    arm pay.declined             (arm)               -                                  uncovered  PLAN006
    flow f_api_pay               system_design       contract payments_v1 (stub)        suspect    PLAN-G03
    impl system.shows_total      component_design    tests/api/test_orders.py::test_total*  flaky
```

Rows come from U (entities, levels, evidence bindings); verdicts from frob
evidence records (D130). `--reverse` starts from tests (orphan tests,
kernel). `--json` carries `level`, `scope`, `kind`, `verdict`, `suspect`.

---------------------------------------------------------------------

## 7. Bibliography

Credibility line after each entry: venue; authors' standing.

[S1] U.S. FDA. "General Principles of Software Validation; Final
Guidance for Industry and FDA Staff." 2002 (section 6 superseded 2025).
https://www.fda.gov/media/73141/download . Full text read. Regulator
guidance; reference commentary for IEC 62304.

[S2] VDA QMC. "Automotive SPICE Process Assessment / Reference Model,
Version 4.1 (Preview)", 2026-04-16.
https://vda-qmc.de/wp-content/uploads/2026/04/Automotive-SPICE-PAM-4.1_Preview.pdf .
Read (SWE.4, SWE.5, SWE.6, VAL.1, SYS.2-4). Standard body of the German
automotive industry. 4.0 wording cross-checked only via [S3].

[S3] UL Solutions. "Automotive SPICE Pocket Guide" and SWE.5/SWE.6
process pages. https://www.ul.com/sites/default/files/2024-10/Automotive_Spice_Pocket_Guide.pdf ;
https://ul.com/sis/resources/process-swe-5 . Search snippets. Assessment
consultancy; secondary.

[S4] NASA. "NASA Systems Engineering Handbook", SP-2016-6105 Rev2.
https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf .
Read (Methods of Verification box, 4.2 note, Appendices D-E). Agency
handbook.

[S5] D. Daniels, S. Tockey, P. Bishop. systemsafety mailing list thread,
8-9 Aug 2024.
https://lists.techfak.uni-bielefeld.de/pipermail/systemsafety/attachments/20240809/4f29a82f/attachment-0001.html .
Read. Practitioner list; Daniels and Bishop with NCC Group/Adelard
(employers per the message); quotes of DO-178C are secondhand.

[S6] RTCA. DO-178C "Software Considerations in Airborne Systems and
Equipment Certification", 2011. [not read; paywalled; cited via S5, S9,
S10]

[S7] jamb documentation, "IEC 62304 Traceability Requirements".
https://jamb.readthedocs.io/en/latest/iec-62304/traceability.html and
commentary on clauses 5.6.4/5.7.1 (search snippet,
https://meddevice.substack.com/p/v-and-v-deep-dive-part-3-software).
G3 secondary; IEC 62304 itself [not read].

[S8] Wikipedia. "CAST-15". https://en.wikipedia.org/wiki/CAST-15 .
Search summary. G3; summarises an FAA-published CAST position paper and
EASA CM-SWCEH-002 [primaries not fetched].

[S9] Y. Sun, M. Brain, D. Kroening, A. Hawthorn, T. Wilson, F. Schanda,
F. J. Guzman Jimenez, S. Daniel, C. Bryan, I. Broster. "Functional
Requirements-Based Automated Testing for Avionics." arXiv:1707.01466,
2017. Read. Preprint; co-authors from Rolls-Royce, Altran UK, Rapita
Systems (on the paper).

[S10] QA Systems, "Automated low level requirements testing for
DO-178C" (slides) https://www.slideshare.net/slideshow/automated-low-level-requirements-testing-for-do178c/240142230 ;
Rapita Systems, "Seven roadblocks to structural coverage"
https://rapitasystems.com/files/MC-WP-007%20Seven%20roadblocks%20to%20structural%20coverage_4.pdf .
Search snippets. Vendor material; used only for 6.4.4.3 categories.

[S11] M. Staats, M. W. Whalen, M. P. E. Heimdahl, A. Rajan. "Coverage
Metrics for Requirements-Based Testing: Evaluation of Effectiveness."
NASA Formal Methods Symposium 2010. https://ntrs.nasa.gov/citations/20100018531 .
Record read. Peer-reviewed symposium; University of Minnesota.

[S12] M. W. Whalen, A. Rajan, M. P. E. Heimdahl, S. P. Miller.
"Coverage metrics for requirements-based testing." ISSTA 2006.
https://experts.umn.edu/en/publications/coverage-metrics-for-requirements-based-testing/ .
Search. Peer-reviewed; Miller at Rockwell Collins (author list; affiliation
[unverified]); avionics example per abstract.

[S13] SEBoK. "Vee (V) Model" glossary and "Vee Life Cycle Model".
https://sebokwiki.org/wiki/Vee_(V)_Model_(glossary) . Search snippets
(life-cycle page returned 404). INCOSE/IEEE-CS/SERC body of knowledge.
K. Forsberg, H. Mooz, "The relationship of system engineering to the
project cycle", INCOSE 1991, doi:10.1002/j.2334-5837.1991.tb01484.x
[not read].

[S14] B. Fitzgerald, K.-J. Stol, R. O'Sullivan, D. O'Brien. "Scaling
agile methods to regulated environments: an industry case study."
ICSE 2013 (SEIP), pp. 863-872.
https://2013.icse-conferences.org/content/scaling-agile-methods-regulated-environments-industry-case-study.html .
Abstract. ICSE SEIP; O'Sullivan and O'Brien of QUMAS (on the paper).

[S15] G. K. Hanssen, T. Stalhane, T. Myklebust. "SafeScrum - Agile
Development of Safety-Critical Software." Springer, 2018.
doi:10.1007/978-3-319-99334-8 . Record plus SINTEF page
https://www.sintef.no/en/digital/departments/software-engineering-safety-and-security/system-safety/safescrum/ .
Book; SINTEF and NTNU with IEC 61508 industry partners.

[S16] J.-P. Steghofer, E. Knauss, J. Horkoff, R. Wohlrab. "Challenges of
Scaled Agile for Safety-Critical Systems." PROFES 2019, LNCS 11915,
pp. 350-366. doi:10.1007/978-3-030-35333-9_26 ; arXiv:1911.12590.
Full text read. Peer-reviewed; focus group with three automotive
industry experts.

[S17] R. Kasauli, E. Knauss, B. Kanagwa, A. Nilsson, G. Calikli.
"Safety-Critical Systems and Agile Development: A Mapping Study." SEAA
2018. doi:10.1109/seaa.2018.00082 . Abstract (OpenAlex). Workshop with
six large Swedish companies.

[S18] L. T. Heeager, P. A. Nielsen. "A conceptual model of agile
software development in a safety-critical context: A systematic
literature review." IST 2018. doi:10.1016/j.infsof.2018.06.004 .
Abstract.

[S19] AAMI TIR45:2012 "Guidance on the use of AGILE practices in the
development of medical device software." [not read]; secondary:
Johner Institute https://blog.johner-institute.com/iec-62304-medical-software/tir-45-agile-software-development/ ;
Greenlight Guru https://www.greenlight.guru/blog/aami-tir45 . G3.

[S20] Jama Software. "Clear suspect links" (Jama Connect help).
https://help.jamasoftware.com/en/manage-content/coverage-and-traceability/relationships/clear-suspect-links.html .
Read. Official vendor doc.

[S21] Siemens Polarion scripting API, ILinkedWorkItemStruct
(isSuspect/setSuspect).
https://testdrive.polarion.com/polarion/sdk/doc/scripting-api/pages/com_polarion_alm_tracker_model_ilinkedworkitemstruct.html ;
SimPol connector https://extensions.polarion.com/extensions/318-simpol-simulink-polarion-connector .
Search snippets. Vendor docs.

[S22] Jazz forum, "Suspect links for DOORS 7"
https://jazz.net/forum/questions/277872/suspect-links-for-doors-7 ; IBM
Ideas ENGRMDN-I-1165. Search snippets. Community answer by an IBM
developer [identity not verified]; G3.

[S23] Atlassian Community and eazyBI docs on Xray requirement coverage.
https://docs.eazybi.com/eazybijira/learn-more/learn-eazybi-through-examples/xray-requirement-coverage .
Search. G3.

[S24] Microsoft Learn. "Requirements traceability" (Azure Pipelines).
https://learn.microsoft.com/en-ie/azure/devops/pipelines/test/requirements-traceability?view=azure-devops .
Search snippets. Official vendor doc.

[S25] Serenity BDD. "Introducing Serenity." https://serenity-bdd.info/docs/serenity/ .
Search snippet only (fetch refused). Official tool doc; G3 here.

[S26] Jama Software. "Requirements Traceability Measured & Benchmarked
for the First Time." Press release, 2022-03-24.
https://www.jamasoftware.com/company/press/requirements-traceability-measured-benchmarked-for-the-first-time ;
report PDF https://www.jamasoftware.com/media/2024/01/requirements-traceability-benchmark.pdf
[not read]. Vendor self-study; method undisclosed; G3.

[S27] D. Stahl, K. Hallen, J. Bosch. "Achieving traceability in large
scale continuous integration and delivery: deployment, usage and
validation of the Eiffel framework." EMSE 22(3):967-995, 2017.
doi:10.1007/s10664-016-9457-1 . Abstract. Ericsson authors on Ericsson's
framework.

[S28] J. Cleland-Huang, C. K. Chang, M. Christensen. "Event-based
traceability for managing evolutionary change." IEEE TSE 29(9), 2003.
doi:10.1109/tse.2003.1232285 . Abstract (OpenAlex). Christensen at the
FAA (affiliation per OpenAlex).

[S29] M. Rahimi, J. Cleland-Huang. "Evolving software trace links
between requirements and source code." EMSE 2018 (online 2017).
doi:10.1007/s10664-017-9561-x . Search and dissertation record
https://curate.nd.edu/articles/thesis/Leveraging_Change_Patterns_and_Software_Traceability_to_Support_the_Evolution_of_Safety-Critical_Systems/24735300 .

[S30] G. Antoniol, J. Cleland-Huang, J. Huffman Hayes, M. Vierhauser.
"Grand Challenges of Traceability: The Next Ten Years."
arXiv:1710.03129, 2017. Abstract. Community roadmap.

[S31] B. Van Rompaey, S. Demeyer. "Establishing Traceability Links
between Unit Test Cases and Units under Test." CSMR 2009, pp. 209-218.
doi:10.1109/CSMR.2009.39 . Abstract
https://win.uantwerpen.be/~sdemey/Pubs/summ/VanRompaeyCSMR2009.html .

[S32] R. White, J. Krinke. "TCTracer: Establishing test-to-code
traceability links using dynamic and static techniques." EMSE 27(3),
2022. doi:10.1007/s10664-021-10079-1 . Search (figures via search).

[S33] Cucumber. "Behaviour-Driven Development." https://cucumber.io/docs/bdd/ .
Read. Official tool doc.

[S34] Cucumber. "Example Mapping." https://cucumber.io/docs/bdd/example-mapping/ .
Read. Official tool doc (method by M. Wynne and S. Tooke, linked there).

[S35] S. Freeman, N. Pryce. "Growing Object-Oriented Software, Guided
by Tests." Addison-Wesley, 2009. TOC
https://growing-object-oriented-software.com/toc.html . Search only.
Practitioner book.

[S36] F. Zampetti, A. Di Sorbo, C. A. Visaggio, G. Canfora, M. Di Penta.
"Demystifying the adoption of behavior-driven development in open source
projects." IST 2020. doi:10.1016/j.infsof.2020.106311 . Abstract
(https://fair.unifg.it/handle/11369/462736).

[S37] M. Beller, G. Gousios, A. Panichella, S. Proksch, S. Amann,
A. Zaidman. "Developer Testing in the IDE: Patterns, Beliefs, and
Behavior." IEEE TSE 45(3), 2019. doi:10.1109/TSE.2017.2776152 . Abstract.

[S38] D. Fucci, H. Erdogmus, B. Turhan, M. Oivo, N. Juristo. "A
Dissection of the Test-Driven Development Process: Does It Really
Matter to Test-First or to Test-Last?" IEEE TSE 43(7), 2017.
arXiv:1611.05994 . Abstract. Professionals from two companies.

[S39] N. Nagappan, E. M. Maximilien, T. Bhat, L. Williams. "Realizing
quality improvement through test driven development: results and
experiences of four industrial teams." EMSE 13(3), 2008. Microsoft
Research summary
https://www.microsoft.com/en-us/research/blog/exploding-software-engineering-myths/ .
Abstract via secondaries. Microsoft Research and Microsoft/IBM teams.

[S40] E. Bjarnason, M. Unterkalmsteiner, M. Borg, E. Engstrom. "A
multi-case study of agile requirements engineering and the use of test
cases as requirements." IST 77:61-79, 2016.
doi:10.1016/j.infsof.2016.03.008 ; arXiv:2308.11747 . Abstract.

[S41] E. Bjarnason, P. Runeson, M. Borg, M. Unterkalmsteiner,
E. Engstrom, B. Regnell, G. Sabaliauskaite, A. Loconsole, T. Gorschek,
R. Feldt. "Challenges and practices in aligning requirements with
verification and validation: a case study of six companies." EMSE
19(6):1809-1855, 2014. doi:10.1007/s10664-013-9263-y ; arXiv:2307.12489 .
Abstract.

[S42] M. Unterkalmsteiner, R. Feldt, T. Gorschek. "A taxonomy for
requirements engineering and software test alignment." ACM TOSEM 2014.
doi:10.1145/2523088 . Crossref record only.

[S43] Z. A. Barmi, A. H. Ebrahimi, R. Feldt. "Alignment of Requirements
Specification and Testing: A Systematic Mapping Study." ICSTW 2011.
doi:10.1109/icstw.2011.58 . Crossref record only.

[S44] G. K. Hanssen, B. Haugset. "Automated Acceptance Testing Using
Fit." HICSS 2009. doi:10.1109/HICSS.2009.83 ; B. Haugset, G. K. Hanssen,
"Automated acceptance testing: A literature review and an industrial
case study", Agile 2008. Abstracts (SINTEF). SINTEF with an industrial
case.

[S45] F. Ricca, M. Torchiano, M. Ceccato, P. Tonella. FIT tables
experiments (2007-2009). https://profs.scienze.univr.it/ceccato/papers/2007/iwpse2007.pdf .
Search snippet. Student experiments; G3 for industry.

[S46] M. Fowler. "SubcutaneousTest." bliki, 2011.
https://martinfowler.com/bliki/SubcutaneousTest.html . Search excerpt.
Thoughtworks chief scientist.

[S47] G. Adzic. "Specification by Example." Manning, 2011. Publisher
TOC https://oreilly.com/library/view/specification-by-example/9781617290084 .
Chapter content [unverified].

[S48] T. Winters, T. Manshreck, H. Wright (eds.); ch. 11 "Testing
Overview" by A. Bender. "Software Engineering at Google." O'Reilly,
2020. https://abseil.io/resources/swe-book/html/ch11.html . Read. Google
engineers on Google practice.

[S49] M. Wacker. "Just Say No to More End-to-End Tests." Google Testing
Blog, 2015-04-22.
https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html .
Fetched (body partly via quoted comments). Google engineer.

[S50] J. Listfield. "Where do our flaky tests come from?" Google Testing
Blog, 2017-04. https://testing.googleblog.com/2017/04/ ; J. Micco,
"Flaky Tests at Google and How We Mitigate Them", 2016-05
https://testing.googleblog.com/2016/05/ . Search snippets. Google
engineers (Micco led Google's CI per S51 authorship).

[S51] A. Memon, Z. Gao, B. Nguyen, S. Dhanda, E. Nickell, R. Siemborski,
J. Micco. "Taming Google-scale continuous testing." ICSE-SEIP 2017.
doi:10.1109/icse-seip.2017.16 . Abstract. Five Google authors.

[S52] A. Schaffer, R. Dybeck. "Testing of Microservices." Spotify
Engineering, 2018-01-11.
https://engineering.atspotify.com/2018/01/11/testing-of-microservices .
Read. Spotify engineers on Spotify practice.

[S53] K. C. Dodds. "The Testing Trophy and Testing Classifications."
https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications .
Search. Individual practitioner; standing [unverified]; G3.

[S54] V. Contan, N. Dehelean, L. Miclea. "Test automation pyramid from
theory to practice." AQTR 2018. doi:10.1109/aqtr.2018.8402699 .
Crossref record; finding via secondary (arXiv:2010.03896). G3.

[S55] F. Trautsch, S. Herbold, J. Grabowski. "Are unit and integration
test definitions still valid for modern Java projects? An empirical
study on open-source projects." JSS 159, 2020.
doi:10.1016/j.jss.2019.110421 . Abstract.

[S56] F. Trautsch, J. Grabowski. "Are There Any Unit Tests? An Empirical
Study on Unit Testing in Open Source Python Projects." ICST 2017.
doi:10.1109/icst.2017.26 . Abstract (OpenAlex).

[S57] I. Robinson. "Consumer-Driven Contracts: A Service Evolution
Pattern." martinfowler.com, 2006-06-12.
https://martinfowler.com/articles/consumerDrivenContracts.html . Read.
Practitioner article; standing [unverified this run].

[S58] Pact Foundation. "Introduction" (Pact docs). https://docs.pact.io/ .
Read. Official tool doc.

[S59] G.-D. Schwarz, F. Quast, D. Riehle. "Ensuring Syntactic
Interoperability Using Consumer-Driven Contract Testing." STVR 35(5),
e70006, 2025. doi:10.1002/stvr.70006 . Full text read. Peer-reviewed;
FAU Erlangen; action research on a university open-source project
(convenience sample, stated by the authors).

[S60] J. Lehva, N. Makitalo, T. Mikkonen. "Consumer-Driven Contract
Tests for Microservices: A Case Study." PROFES 2019, LNCS.
doi:10.1007/978-3-030-35333-9_35 . Crossref record and abstract snippet.

Context sources from R1 relied on, not re-read: Rempel and Maeder TSE
2017; Maeder and Egyed EMSE 2015; Wohlrab et al. RE 2018
(doi:10.1007/s00766-018-0306-1); Pereira et al. XP 2018
(doi:10.1145/3234152.3234167, abstract re-read via OpenAlex); Binamungu et
al. SANER 2018; Femmer et al. JSS 2017.
