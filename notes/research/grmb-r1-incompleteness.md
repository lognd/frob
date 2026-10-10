# grmb R1, topic D: reasoning with incremental and incomplete models

Ticket ~19SEHXJ, researcher D. Date 2026-10-09. ASCII only. Not committed.

Honest status line: this is NOT a fully exhaustive sweep. WebSearch and
WebFetch were not available in this run (ToolSearch found no such tools),
so discovery used the Crossref, OpenAlex, Semantic Scholar and arXiv HTTP
APIs and direct downloads via curl. Of the ~75 works looked up, 12 had
their full text or an author-written primary document read, ~14 had an
abstract read, the rest are metadata-verified only (existence, authors,
venue, year, DOI). Claims resting on recall rather than on text read in
this run are tagged [recalled]. Two items could not be looked up
(rate-limited, section 1.4) and are tagged [unverified]. Nothing below
is pending in the sense of an unexplored node; what remains unread is
enumerated in section 1.5.

## 1. Scope and search log

### 1.1 Question

What does the evidence say about (a) working with models that are
incomplete or uncertain and (b) how designers actually proceed
incrementally, such that a checked design language (grmb, with frob's
existing Must/May/Unknown status and lo/hi bounds) can support early,
partial, changing designs without either lying or drowning the user in
errors?

### 1.2 Field enumeration (Phase 0), then drain

Denominator = the topic list in the brief plus two expansion passes.
Clusters and how each was drained:

| Cluster | Nodes enumerated | Read level |
|---|---|---|
| Partial models / design-time uncertainty (Famelis, Salay, Chechik) | ICSE 2012; FASE 2012; SoSyM 2017 / MODELS 2017; JOT 2015 refinement; Famelis PhD thesis 2016; Mu-Mmint ICSE 2015; MISE 2012; MODELS 2013 transformation | thesis full text (grep-read); JOT 2015 full text (grep-read); ICSE 2012 abstract; rest metadata |
| Modal transition systems, 3-valued checking | Larsen-Thomsen 1988; Huth-Jagadeesan-Schmidt ESOP 2001; Godefroid-Huth-Jagadeesan CONCUR 2001; Bruns-Godefroid CAV 1999; Chechik et al TOSEM 2003; Dams-Gerth-Grumberg TOPLAS 1997; Antonik et al 2010; Benes et al 2009; Uchitel-Chechik FSE 2004; Uchitel-Brunet-Chechik TSE 2009; Fischbein et al 2006; Ben-David et al 2013; Sagiv-Reps-Wilhelm TOPLAS 2002 | metadata only (all located except two, see 1.4) |
| Multi-valued / inconsistency | Belnap 1977; Van Gelder-Ross-Schlipf JACM 1991; Easterbrook-Chechik ICSE 2001; Balzer ICSE 1991; Nuseibeh-Easterbrook-Russo JSS 2001; Spanoudakis-Zisman 2001; Egyed TSE 2011 | Balzer and Egyed abstracts; rest metadata |
| Gradual typing and verification | Siek-Taha 2006 (via SNAPL text); Siek et al SNAPL 2015; Takikawa et al POPL 2016; Gao-Bird-Barr ICSE 2017; Wadler-Findler 2009; Bader-Aldrich-Tanter VMCAI 2018; Wise et al OOPSLA 2020; arXiv 2311.07559 | SNAPL 2015 full text (abstract+intro read); Takikawa and Gao abstracts; arXiv abstract |
| Typed holes / program sketching | Omar et al POPL 2017 (Hazelnut), POPL 2019 (Hazel Live); Zhao et al POPL 2024; GHC user guide; Agda docs; Rust clippy `todo`; Solar-Lezama 2013 | Hazel Live full text (abstract+intro read); GHC, Agda, clippy docs read; others metadata |
| Refinement | Back-von Wright 1998; Hoare et al 1987; Morgan-Vickers 1990; Abadi-Lamport 1991; Abrial 2010 (Event-B) | metadata only |
| Bidirectional transformations | Czarnecki et al ICMT 2009; Foster et al TOPLAS 2007; Stevens SoSyM 2008; Diskin et al ICMT 2010; Sendall-Kozaczynski 2003; Murphy-Notkin-Sullivan TSE 2001 (reflexion, reused from topic B) | metadata only |
| Notation usability | Green-Petre JVLC 1996; Blackwell et al 2001; Blackwell-Green 2003; Green-Blackwell 1998 tutorial | 1998 tutorial read (primary, Cambridge-hosted); rest metadata |
| How designers work / sketching | Cherubini et al CHI 2007; Mangano et al TSE 2015; Baltes-Diehl FSE 2014; Petre ICSE 2013; Petre-van der Hoek 2016 (book); Petre CACM 1995; Curtis-Krasner-Iscoe CACM 1988; Guindon HCI 1990; Parnas-Clements TSE 1986 | Baltes full text (abstract+findings read); abstracts of Cherubini, Mangano, Petre 2013; rest metadata |
| Industry modeling practice | Hutchinson et al ICSE 2011; Whittle et al IEEE Software 2014; Hebig et al MODELS 2016; Stoerrle EASE 2017; Newcombe et al CACM 2015 | abstracts |
| Uncertainty in adaptive systems (adjacent) | Garlan FoSER 2010; Ramirez-Jensen-Cheng SEAMS 2012; Perez-Palacin-Mirandola ICPE 2014; Esfahani-Malek 2013 | metadata only |

Queries run (Crossref bibliographic queries, ~75; OpenAlex DOI abstract
pulls, 23; Semantic Scholar DOI pulls, 10; arXiv API title queries, 4;
direct page fetches of vendor docs, 6; direct PDF fetches, 9). Search
terms: author+title strings for every node above plus "MAVO partial
models uncertainty Famelis", "typed holes", "gradual verification",
"design-time uncertainty", "sketches and diagrams Baltes".

### 1.3 Excluded and why

- Anonymous blogs (owner rule). No blog is cited.
- Paywalled full texts that could not be fetched (ICSE 2012 partial
  models, CHI 2007, TSE 2015, ICSE 2013, ICSE 2011, MODELS 2016): used
  abstracts only; claims are limited to what the abstracts state.
- Uncertainty in self-adaptive/runtime systems (environmental
  uncertainty): different problem (runtime), listed in the bibliography
  only to bound the scope; Famelis's thesis itself draws this line.
- Proof-assistant internals (Lean, Coq tactic states): out of scope; the
  idea (a hole is a first-class unknown) is covered by Agda/GHC/Hazel.

### 1.4 Lookups that failed

Benes-Kretinsky-Larsen-Srba ICTAC 2009 and Larsen-Thomsen LICS 1988:
Crossref returned HTTP 429; no retry was made. They are cited only as
[unverified] pointers and no finding depends on them.
[Verification pass 2026-10-09: both now resolved, see section 7.]

### 1.5 Unread remainder and why it would not change conclusions

- Full texts of the ~60 metadata-only items. The conclusions below use
  them only for well-known headline results ([recalled]) that are not
  contested in the surveyed literature (e.g. MTS refinement preserves
  definite truth); an error in recall would alter wording, not the
  design consequences, because every grmb consequence is separately
  grounded in a text actually read (thesis, Hazel, SNAPL, CD tutorial,
  Baltes, vendor docs).
- Petre-van der Hoek "Software Design Decoded" (book, 66 heuristics):
  not retrievable; coverage of designer thinking relies on its
  articles' abstracts (Mangano) and on Guindon/Curtis/Parnas metadata.
  A later pass should read the book; risk: it may add heuristics (for
  example "experts borrow", seen only as a chapter title via Crossref)
  that suggest more lint rules, not fewer.
  [Verification pass 2026-10-09: the publicly available content (chapter
  list, publisher-listed insights) is now in F19; the insight bodies are
  still not public. Guindon/Curtis/Parnas are now read at abstract or
  full-text level, see F14.]
- Industrial case evidence for partial-model tooling beyond
  Mu-Mmint/Famelis case studies: none found. This is itself a finding
  (F12).

## 2. Findings

Evidence grades: E = empirical study, X = experience report, V = vendor
or official documentation, T = formal theory, O = opinion.
Credibility grading per source is in the bibliography.

F1. Developers facing an open design decision have two bad options:
wait (under-using tools) or commit provisionally and track the
provisional decisions by hand, risking costly re-engineering. The
partial-model alternative defers the decision while checks still run.
Evidence: the Famelis thesis abstract and introduction (thesis p. v,
sec 1.2); grade E (pilot user study) + T. Source: [Famelis2016].
Note the thesis states that provenance of a provisional decision can be
forgotten so it silently becomes permanent (thesis sec 1.2, around
"the provisional character of a decision may be forgotten").

F2. When asked to express uncertainty in a free-form modeling task,
people mark it inside the artifact, close to the existing notation,
using question marks, ellipses and dashed lines. Grade E (pilot user
study, Famelis and Santosa 2013, reported in the thesis). Source:
[Famelis2016] chapter 3. Consequence: an uncertainty marker should be a
short in-line token of the base language, not a separate document.

F3. A partial model is a base model plus a May-formula; a property check
over all concretizations returns True, False or Maybe. MAVO (May, Abs,
Var, OW) adds more kinds of partiality, but full MAVO reasoning handled
models an order of magnitude smaller and took an order of magnitude
longer than Maybe-only reasoning (thesis ch. 4, discussion of
Saadatpanah et al. 2012 experiments with CSP, SMT, ASP and Alloy
solvers). Grade E (benchmark experiments on generated models).
Sources: [Famelis2016], [FamelisSalayChechik2012], [SalayFamelisChechik2012].
Consequence: Must/May (Maybe-only) is the cheap, useful point; grmb
should not grow variable-multiplicity and open-world annotations.

F4. The Maybe-only checks gave the expected three-way verdicts with
mixed speedups relative to enumerating concretizations (thesis sec 4.3:
for checks evaluating to True or False the best recorded speedup was
42.90, while for checks evaluating to Maybe the speedups were small and
erratic, with an average of 0.74 in one size class, i.e. slower). Grade
E. Source: [Famelis2016]. Consequence: a Maybe verdict is the
expensive/imprecise outcome; the design should make True/False the
common case by keeping the number of May sources small and by
refining quickly.

F5. Refinement must provably reduce uncertainty: a partial-model
refinement step is valid only if the refined model's concretizations
are a subset of the original's, and this is checkable. Grade T + E
(case study). Source: [SalayChechikFamelisGorzny2015] (full text:
introduction and sec 2 read), [SalayFamelisChechik2012]. Consequence:
each lower level of the V (goal -> scenario -> impl) is a refinement of
the one above; narrowing is verifiable and a widening edit is a
distinct, reportable event.

F6. Modal transition systems carry must-transitions (definitely in
every implementation) and may-transitions (permitted in some); a
refinement turns may into must or removes it; logic results are
three-valued (true, false, maybe) and a definite verdict at an abstract
level is preserved by every refinement. Grade T. Sources:
[HuthJagadeesanSchmidt2001], [GodefroidHuthJagadeesan2001],
[BrunsGodefroid1999] [recalled; metadata verified]. The exact
correspondence to frob's lo/hi: lo = must, hi = must + may, and
Unknown = no information. Sources for the three-valued shape in program
analysis: [SagivRepsWilhelm2002], [DamsGerthGrumberg1997].
Consequence: verdict monotonicity is the invariant to protect (F8).
[Verified 2026-10-09 against the full text of [Antonik2008], a survey
co-authored by K. Larsen (co-inventor of MTS) and M. Huth. Confirmed:
MTS "transitions come in two flavours: those that any refinement of the
given specification must possess, and those that it may, but is not
required to, have" (introduced in [LarsenThomsen1988]); refinement
preserves all required behaviour and permits only allowed behaviour;
"a positive model check ... certifies that all implementations ...
satisfy" the property, while a failed pessimistic check leaves it
unknown. Three corrections to the wording above: (a) the preserved
result is the definite one computed by the pessimistic (must) semantics,
and it holds only for consistent specifications: "if (M, s) is
inconsistent, then Val (M, s, phi) is true for all phi", so a
consistency check is needed to rule out vacuity; (b) structural
("modal") refinement implies inclusion of implementation sets
("thorough" refinement) but not conversely; (c) deciding thorough
refinement is EXPTIME-complete [Benes2009, title-verified], so a
practical checker uses the structural relation. The [recalled] tag is
removed; grade T, source read at full text.]

F7. Gradual typing's central criterion is the gradual guarantee: two
programs that differ only in the precision of their annotations behave
identically unless the more-annotated one reports a type error; making
a program less annotated (more partial) never makes a good program bad.
The original 2006 definition was, per the 2015 paper, an incomplete
formal characterization. Grade T + survey of designs. Source:
[SiekVitousekCiminiBoyland2015] (abstract and introduction read in
full text). Consequence: the same property can be stated for grmb: a
more-partial model must produce verdicts that are no stronger (only
Unresolved where previously Pass or Fail), and a more-complete model
may only add a Fail where a binding is wrong.

F8. Gradual approaches have an empirical record: static types in
JavaScript detected a measurable share of real bugs (TypeScript and
Flow each detected about 15 percent of sampled public bugs) even
though only partially applied, and sound enforcement at typed/untyped
boundaries had very high run-time cost in Typed Racket benchmarks.
Grade E. Sources: [GaoBirdBarr2017], [TakikawaFelteyGreenmanNew2016]
(abstract: "disastrous numbers"). Consequence: partial checking is
worth having (benefit without full coverage), and a boundary between
bound and unbound regions must not be policed with expensive
uniform checking; check what is bound, report the boundary once.

F9. Typed holes are a mainstream mechanism for incompleteness. GHC
reports a hole as a compile error that states the expected type, the
relevant local bindings and valid fits, and can defer the error so the
rest runs (-fdefer-typed-holes). Agda treats the content of a hole as
unknown and the type checker ignores it. Grade V. Sources: [GHCGuide],
[AgdaDocs]. Hazel goes further: every editor state has some possibly
incomplete type, evaluation proceeds around holes tracking hole
closures, and fill-and-resume avoids recomputation after filling a hole
(abstract and intro of the full text read). Grade T + implementation
(no user study in the paper). Source: [OmarVoyseyChughHammer2019].
Consequences: (i) a hole must be a named, typed placeholder; (ii) its
diagnostic should offer candidates (GHC-style fits); (iii) results
that do not depend on the hole must still be computed (Hazel), with
dependents reported as Unresolved naming the hole.

F10. Production policy treats holes as temporary: Clippy's
restriction lint clippy::todo says the todo! macro "indicates the
presence of unfinished code, so it should not be present in production
code". Grade V. Source: [ClippyTodo]. Consequence: placeholders are
legal and necessary in development and must be gate-able at a release
boundary; they must never be silent.

F11. Inconsistency should be tolerated with tracking, not forbidden.
Balzer's technique softens a constraint by treating violations as
temporary exceptions that will eventually be corrected, marks the
offending data with guards, and notifies the responsible humans.
Egyed shows inconsistencies in design models can be detected and
tracked incrementally in real time: 1.4 ms average re-evaluation per
change over 34 models of up to 162,237 elements. Grade E for Egyed
(evaluation on 34 models), X for Balzer. Sources: [Balzer1991],
[Egyed2011]; the "respectable inconsistency" position is
[NuseibehEasterbrookRusso2001] [recalled; 2026-10-09: title and
metadata verified via OpenAlex, no abstract available, so only the
position named in the title is attributed]. Consequence: the existing
`until=` and `review=` dates on excuses are the right shape; make them
mandatory for any provisional marker and check incrementally.

F12. In industrial practice, models are used selectively, early and
informally. Whittle et al (survey of 450 practitioners plus 22
in-depth interviews): MDE is more widespread than commonly believed but
developers rarely generate whole systems; they apply it to key parts.
Hebig et al mined ~10 percent of GitHub (1.24 million projects): 21,316
diagrams in 3,295 projects, and models are created or updated mostly
in a very short phase at project start. Baltes and Diehl (exploratory
study in three companies plus an online survey, 394 participants):
most sketches and diagrams contain some UML elements but are
informal, and relate to methods, classes or packages, not lower-level
code artifacts. Petre interviewed 50 professional engineers and found
five patterns of UML use (abstract only; patterns not enumerated here).
Grade E for all. Sources: [Whittle2014], [Hebig2016], [BaltesDiehl2014],
[Petre2013], [Stoerrle2017] (descriptive survey; abstract only).
Consequence: the model must be useful from the first sketch and be kept
alive by binding to code; models not tied to code are created once and
abandoned.

F13. Design drawings are transient. Cherubini et al (semi-structured
interviews validated by a structured survey): most diagrams had a
transient nature because of the cost of changing whiteboard sketches
into electronic renderings; diagrams documented decisions but were
externalized as temporary drawings and then lost. Mangano et al (14
hours of whiteboard activity by eight pairs of professional designers,
over 4000 events coded): sketches support conversation, designers use
general-purpose notations, constantly shift between sketches and
mental simulation, and the activity of mental simulation, review and
considering alternatives often leaves no trace. Grade E. Sources:
[Cherubini2007], [Mangano2015]. Consequence: capturing a decision and
the alternatives considered costs effort at the moment of use; grmb
needs a cheap way to record "alternatives considered, one chosen".

F14. Design is not a rational top-down process; it is opportunistic,
and the rational form is documented after the fact. Guindon's
protocol study of designers found opportunistic thought. Parnas and
Clements argue to "fake" the rational process in documentation.
Curtis, Krasner and Iscoe field-studied large-system design and found
fluctuating requirements and domain-knowledge gaps as driving
problems [recalled; metadata verified]. Grade E (Guindon, Curtis), O
(Parnas, a well-cited position by authors with shipped systems, see
bibliography). Sources: [Guindon1990], [Curtis1988], [ParnasClements1986].
Consequence: do not enforce order of authoring; allow bottom-up
(code first, model later) and middle-out; derive the level from the
construct, never from file order.
[Verified 2026-10-09; [recalled] removed. Curtis et al abstract
(OpenAlex): interviews with personnel from 17 large projects; three
problems analysed: "the thin spread of application domain knowledge,
fluctuating and conflicting requirements, and communication
bottlenecks and breakdowns". Guindon: her own 1991 Stanford seminar
abstract states the early stages of software design "have been
observed to be opportunistic", that this is "not noise or resulting
from bad design practices" but "an intrinsic consequence of the
ill-structuredness of early design problems", and "beneficial"; the
HCI 1990 paper itself was not read (method details such as number of
designers are not asserted here). Parnas-Clements: full text read
(NRL authors; the A-7E module guide and interface documents are their
cited worked examples). Two statements matter for grmb: "We will never
see a software project that proceeds in the 'rational' way" because
details "only become known to us as we progress in the implementation"
and "some of the things that we learn invalidate our design and we must
backtrack"; and their documentation policy: "We make a policy of
recording all of the design alternatives that we considered and
rejected. For each, we explain why it was considered and" why rejected.
That second statement is direct support for I6 (`choice` with
`rejected because=`).]

F15. Cognitive dimensions of notations give a vocabulary to evaluate
this. From Green and Blackwell's tutorial (read in full text): viscosity
is "resistance to change"; knock-on viscosity is "one change in the
head entails further actions to restore consistency"; the worst
problems come when viscosity is combined with premature commitment,
because the user makes an early guess and finds correcting it costly;
viscosity is acceptable for transcription and incrementation but
"harmful" for modification and exploratory design; viscosity is a
property of the whole system (notation, medium, editor), so tooling
(aggregate operations) can reduce it. Other dimensions defined there:
hidden dependencies ("important links between entities are not
visible"), progressive evaluation ("work-to-date can be checked at any
time"), provisionality ("degree of commitment to actions or marks"),
premature commitment ("constraints on the order of doing things"),
secondary notation, diffuseness. Grade O/T (framework with broad
adoption; the tutorial is by the framework's authors; JVLC 1996
paper has >1,200 citations per OpenAlex). Sources: [GreenBlackwell1998],
[GreenPetre1996], [Blackwell2001]. Consequence: grmb's variant-add
propagation (every handler of a changed step gets a finding) is
knock-on viscosity by design; it is justified only if the tooling
removes the manual restoration work (fix actions).

F16. Bidirectional transformation theory warns that round-tripping
needs well-behavedness laws (lens laws) and, for models, delta
alignment (Diskin et al show the state-based vs delta-based
distinction; Czarnecki et al survey cross-discipline). Hutchinson et al
(interviews and questionnaires) found MDE success depends on social and
organizational factors as much as technical ones. Grade T/E. Sources:
[Czarnecki2009], [Foster2007], [Diskin2010], [Hutchinson2011]
[recalled for the lens laws; metadata verified]. Consequence: keep the
model-to-code relation one-directional for checking (code facts check
the model), and generate tickets from the model as a read-only
"get"; never regenerate the model from code in place.
[Verified 2026-10-09; [recalled] removed. Foster et al TOPLAS 2007 full
text: Definition 3.2 "Well-behaved lenses" states GetPut (putting back
an unmodified view returns the original source) and PutGet (getting
after a put returns the put view). Diskin, Xiong, Czarnecki ICMT 2010
full text, abstract: existing bidirectional model transformation
languages "are mainly state-based ... but alignment relationships
between the models are not specified", which causes "three major
problems"; they propose a delta-based framework. Hutchinson et al ICSE
2011 abstract (ICSE 2011 site and Lancaster eprints): twelve-month
mostly qualitative study (questionnaires, interviews) of technical,
organizational and social factors in MDE success. Czarnecki 2009
remains metadata-only (survey pointer). The consequence stands.]

F17. Software reflexion models (Murphy, Notkin, Sullivan) compare an
engineer-supplied high-level model with a source model through a
partial mapping and report convergences, divergences and absences; the
mapping is refined iteratively [recalled; metadata verified]. Grade E
(TSE 2001, with industrial case studies). Source: [Murphy2001].
Consequence: this is the established ancestor of grmb's binding
relation with Must/May/Unknown; the iterative refinement of the map is
the supported workflow.
[Verified 2026-10-09; [recalled] removed. FSE 1995 conference version,
full text from Murphy's UBC page: the engineer defines a high-level
model and a declarative map; a tool computes where the model "agrees
with and where it differs from a model of the source"; the technique
page names the three categories convergences, divergences and absences;
the paper reports that an engineer "may specify a partial" map and
"iteratively refine" it, starting from "a rough and partial map".
TSE 2001 abstract (OpenAlex): applied to "design conformance, change
assessment, and an experimental reengineering of the million-lines-of-
code Microsoft Excel product". Grade E/X with a named industrial case
(Microsoft Excel).]

F18. No industrial deployment evidence for partial-model tooling was
found beyond the Mu-Mmint research tool and case studies by its
authors. Weak evidence by absence; not a refutation. Newcombe et al
(Amazon Web Services engineers) report TLA+ for subtle design bugs,
used on critical protocols, an industrial datapoint that lightweight
formal design checking is adopted when incremental and targeted. Grade
X. Sources: [Famelis2016], [Newcombe2015].

F19. (Added 2026-10-09.) Petre and van der Hoek's "Software Design
Decoded" is organized as 66 insights in chapters whose titles are
public (Crossref chapter DOIs 10.7551/mitpress/10612.003.0001 to
.0016): Experts Keep it Simple, Collaborate, Borrow, Break the Rules,
Work with Uncertainty, Iterate, Test, Reflect, Keep Going, Sketch, Are
Not Afraid. The publisher description (Google Books listing) quotes
these individual insights: "Experts generate alternatives", "Experts
prefer simple solutions", "Experts see error as opportunity", "Experts
involve the user", "Experts take inspiration from wherever they can",
"Experts design throughout the creation of software", "Experts draw the
problem as much as they draw the solution". It describes each insight as
distilled from years of studying professional designers, and mentions
a companion website with an annotated bibliography; that site could not
be located (no URL in any listing; no Wayback capture for the likely
domain). The insight bodies are not public. Grade O (book, not peer
reviewed) resting on the authors' empirical work (e.g. [Mangano2015],
[Petre2013]). Consequences, all consistent with F1, F13, F14: a whole
chapter on working with uncertainty supports first-class partiality
(I1, I2); "generate alternatives" supports `choice` (I6); "design
throughout the creation of software" supports no authoring order and
code-first entry (I7, PLN-INC12 at Advisory only); "draw the problem as
much as the solution" supports goals and scenarios being modelable
before any impl exists (I8). It adds no new lint rule.

## 3. Implications for grmb

Tags: ADOPT, ADAPT, REJECT. Each says what grimble checks and how.

I1. ADOPT Maybe-only partiality and nothing more. Keep exactly
Must / May / Unknown (existing S, universal-model.md 5) and lo/hi
bounds. Reason: F3 shows full MAVO is an order of magnitude more
expensive and F2 shows users want one in-line marker. Check: verdict
algebra over (lo, hi) already defined; add no Var/Abs/OW annotations.

I2. ADOPT a first-class, typed hole. Syntax proposal: `todo NAME
: SHAPE until=DATE ticket=ID;` usable wherever a goal leaf, step,
outcome variant, impl, or binding is expected; SHAPE is the contract or
outcome-set the hole must satisfy (GHC prints the expected type; we
require it so the checker can say what fits). Reason: F9, F10. Check:
the hole contributes Unknown to dependents; dependents are
Unresolved naming the hole once (poisoned-frontier pattern already in
universal-model.md Pc closure).

I3. ADAPT the Hazel property: results independent of holes are still
computed. Reason: F9. Check: the evaluator runs per connected
component of the dependency graph, not per file; a finding depends on
a hole iff the hole is in its support set (provenance of lo/hi).

I4. ADOPT the gradual guarantee as an explicit grmb law and test it.
Statement: replacing any binding or entity by a less precise one
(Must -> May, May -> Unknown, bound -> declared, removing a
`verified_by`) may only move a verdict toward Unresolved; making a
model more precise may add Fail only where the new precision is wrong.
Reason: F7, F6. Check: a property test in the conformance corpus that
generates model pairs related by precision and asserts the verdict
order Pass/Fail >= Unresolved.

I5. ADOPT temporal bounds on every provisional marker. `todo`, `May`
bindings declared by the user (as opposed to computed), `draft` and
`choice` carry `until=`/`review=` (dates already exist in the lexical
spec) and an owner ticket. Reason: F1 (silent permanence), F11. Check:
expiry compared with CI date (a clock source must be an input to the
kernel so results are reproducible; use the commit date).

I6. ADAPT alternatives-considered as a `choice` entity: a set of named
alternatives with at most one `chosen`; unchosen members stay as May
until resolved or declared `rejected because="..."`. Reason: F1, F13
(decisions and alternatives are lost). Check: more than one member
remains May after `until`; chosen member's bindings must resolve;
rejected members' bindings must NOT resolve to live code (a rejected
design still bound is a smell).

I7. ADOPT level-by-construct and no authoring order. Reason: F14, F15
(premature commitment = constraints on order). Check: the parser and
fmt accept any order (grmb-spec section on fmt sorting already moves
this way); no rule requires a goal before an impl, but a missing parent
is an obligation, not a parse error.

I8. ADOPT unbound-but-declared as a legitimate resting state for a
long time, with no error noise: `declared` status is silent at
default severity inside a `stage draft` scope and Advisory elsewhere.
Reason: F12, F13 (models must be cheap to start). Check: severity is a
function of (scope stage, age of entity); the planning brief's status
ladder declared/bound/verified is the carrier.

I9. ADAPT knock-on propagation (variant-add produces findings in each
handler) with auto-fix. Reason: F15 (knock-on viscosity is harmful for
modification unless aggregate operations exist). Check/action:
`grimble fix --add-arm` inserts `VARIANT -> todo(...)` in every
non-exhaustive handler as a typed hole with a ticket, so a variant
addition is one command and every new gap is a visible, dated hole
rather than a wildcard (the wildcard-arm Warn from the planning brief
stays).

I10. ADOPT one-way flow for generation. Model -> tickets (get only);
code -> model verdicts (check only); no in-place model regeneration.
Reason: F16. Check: forbid in the CLI design any verb that rewrites
`.grmb` from code; allow `grimble suggest` that prints a patch.

I11. ADOPT incremental evaluation as a requirement (progressive
evaluation dimension). Reason: F11 (Egyed: ms-level incremental
checking is feasible), F15. Check: a budget test: re-check after a
single-entity edit must be below a stated threshold on the corpus
(placeholder: 50 ms for 10k entities), tracked in CI.

I12. ADAPT the reflexion-model workflow for the first binding. Reason:
F17. Check: `grimble bind --suggest` proposes a selector; the map is
reported as convergence (bound and code edge exists), divergence
(code edge exists, no declared flow), absence (declared flow, no code
edge) which are the existing SYS rules.

I13. REJECT a fourth truth value for conflict (Belnap's Both). Reason:
conflict between design and code is a Fail finding with both sources
cited, not a value; a fourth value costs checking complexity (F3)
and no surveyed practice needs it. Where several viewpoints disagree
(Easterbrook-Chechik multi-valued reasoning), report a finding per
viewpoint pair.

I14. REJECT sound runtime-style boundary enforcement between bound and
unbound regions. Reason: F8 Typed Racket boundary cost; grmb is static
and does not run code. Check instead: edge-level statuses (May edge at
a boundary).

I15. ADOPT error de-duplication around unknowns. Reason: F9 (Hazel
reports around holes), F15 (error-proneness, diffuseness). Check:
group Unresolved findings by their root hole/unknown adapter fact;
print the root once with a count of dependents.

I16. ADAPT cognitive-dimension audit as a review artifact for grmb
itself: before freezing the grammar, fill the CD questionnaire (a PDF
exists on the CD resource site) for the planning layer. Reason: F15.
Check: a checklist in docs/design (not a lint rule).

## 4. Candidate lint rules

Ids are placeholders (family PLN-INC). Polarity: P = fires on presence,
A = on absence, M = on mismatch.

| Id | Anti-pattern prevented | Predicate over model or model-code binding | Pol | Source |
|---|---|---|---|---|
| PLN-INC01 | Hole with no owner or deadline (silent permanence of a provisional decision) | `todo`/`choice`/`draft` entity E has no `ticket=` or no `until=` | A | F1, F11; Balzer |
| PLN-INC02 | Placeholder left in a released scope | entity of kind hole reachable from a scope with `stage release` or a frozen tag | P | F10; clippy::todo |
| PLN-INC03 | Expired provisional marker | `until`/`review` date < commit date and the marker is still present or still May | M | F11; I5 |
| PLN-INC04 | Hole without an expected shape | hole has no contract/outcome set to fill | A | F9 (GHC expected type) |
| PLN-INC05 | Undecided choice past its date | `choice` with more than one non-rejected member after `until` | M | F1; Famelis |
| PLN-INC06 | Rejected alternative still live | `rejected` member with a binding whose `lo` is non-empty | P | F13; I6 |
| PLN-INC07 | Precision-monotonicity violation | between base and head model, a verdict moved from Unresolved to Fail with no new binding, or Pass to Fail with no code change | M | F7 gradual guarantee; test-time property, not user lint |
| PLN-INC08 | Duplicate noise around one unknown | more than one Unresolved finding with the same root hole | P (meta, collapses output) | F9, I15 |
| PLN-INC09 | Design model abandoned after start | model file last-changed commit older than N bound-code changes (code churn in its `lo` set vs model touches in git history) | M | F12 Hebig; mining-based |
| PLN-INC10 | Declared forever | entity in status `declared` for more than N cycles in a non-draft scope | M | F12, F13 |
| PLN-INC11 | Wildcard hides a new variant | wildcard arm on a handler whose step outcome set grew since the handler was written | P | planning brief; F15 viscosity (already specified, listed for the family) |
| PLN-INC12 | Level skipping (code-first) without trace | impl or bound code with no scenario/goal above it | P at Advisory only | F14 (legit but should be visible) |
| PLN-INC13 | Hole hides a dependency | binding or flow whose endpoint is a hole while claims depend on it (claim Pass computed over a hole's hi) | P | F9; Pc closure |
| PLN-INC14 | Refinement widens | a refining entity's bound set (hi) is not a subset of its parent's bound set where a parent bound exists | M | F5; F6 |
| PLN-INC15 (added 2026-10-09) | Vacuous Pass from an inconsistent partial model | some entity or edge has must-content not contained in its may-content (lo not a subset of hi), or a `choice` whose chosen member is also `rejected`; any Pass computed over it is suppressed and the inconsistency reported | M | F6 as verified (Antonik et al: Val is true for all properties on an inconsistent specification) |

PLN-INC14 is the direct analogue of the Salay et al refinement check
(subset of concretizations) and of MTS refinement; it is the only rule
on this list that needs an explicit parent/child bound relation and so
depends on the planning-layer realization edges.
(2026-10-09) PLN-INC14 must stay a structural, per-entity subset test
(the analogue of modal refinement). Its semantic counterpart (inclusion
of all concretizations, "thorough" refinement) is EXPTIME-complete for
MTS [Benes2009], and modal refinement implies thorough refinement but
not conversely [Antonik2008]; so PLN-INC14 may report a widening that
is not semantically one, and its message must say "structural".

## 5. Bibliography

Each entry: citation, URL/DOI, how verified in this run, then a
credibility line (venue; authors' practical standing). Practical
standing is stated only where a source in this run supports it; where
it rests on author affiliations printed in the paper's metadata it says
"per affiliations in metadata" and where it is general knowledge not
re-checked it says [standing not re-verified].

Grading key: A = practitioner evidence from people who shipped at scale
or industry studies with named partners; B = peer-reviewed, strong
venue, industrial validation or large empirical base; C = peer-reviewed
theory or academic study without industrial validation; V = official
vendor/project documentation.

[Famelis2016] M. Famelis. "Managing Design-Time Uncertainty in Software
Models." PhD thesis, University of Toronto, 2016.
https://utoronto.scholaris.ca/bitstreams/551ff8ec-9a8c-415b-a2bd-f631aff3f4e7/download
Read: abstract, ch. 1, 2 (partial), 3, 4.3, discussion of MAVO scaling.
Credibility: doctoral thesis at a top CS department; supervised by M.
Chechik (ICSE/TSE/TOSEM record, see below). Includes a pilot user study
and benchmark experiments, plus case studies by the authors. Grade C+
(academic, with an open-source case study; no industrial validation).

[FamelisSalayChechik2012] M. Famelis, R. Salay, M. Chechik. "Partial
models: Towards modeling and reasoning with uncertainty." ICSE 2012.
doi:10.1109/icse.2012.6227159. Verified via Crossref and OpenAlex
(abstract read; garbled but states an experimental comparison and a
case study on open source software). Credibility: ICSE, the flagship
venue. Grade C+.

[SalayFamelisChechik2012] R. Salay, M. Famelis, M. Chechik. "Language
Independent Refinement Using Partial Modeling." FASE 2012.
doi:10.1007/978-3-642-28872-2_16. Crossref. Credibility: FASE (ETAPS
peer-reviewed). Grade C.

[SalayChechikFamelisGorzny2015] R. Salay, M. Chechik, M. Famelis, J.
Gorzny. "A Methodology for Verifying Refinements of Partial Models."
Journal of Object Technology 14(3), 2015.
doi:10.5381/jot.2015.14.3.a3; http://www.jot.fm/issues/issue_2015_03/article3.pdf
Full text downloaded, intro read. Credibility: JOT, peer-reviewed.
Grade C.

[FamelisChechik2019] M. Famelis, M. Chechik. "Managing design-time
uncertainty." Software and Systems Modeling (2017/2019); also MODELS
2017. doi:10.1007/s10270-017-0594-9 (Crossref lists 2017). Metadata
only. Credibility: SoSyM; MODELS. Grade C.

[HuthJagadeesanSchmidt2001] M. Huth, R. Jagadeesan, D. Schmidt. "Modal
Transition Systems: A Foundation for Three-Valued Program Analysis."
ESOP 2001, LNCS 2028. doi:10.1007/3-540-45309-1_11. Crossref only.
Credibility: ESOP (ETAPS). Grade C (theory).

[GodefroidHuthJagadeesan2001] P. Godefroid, M. Huth, R. Jagadeesan.
"Abstraction-Based Model Checking Using Modal Transition Systems."
CONCUR 2001. doi:10.1007/3-540-44685-0_29. Crossref only. Credibility:
CONCUR. Godefroid is the author of VeriSoft and SAGE (fuzzing deployed
at Microsoft) [standing not re-verified]. Grade C+.

[BrunsGodefroid1999] G. Bruns, P. Godefroid. "Model Checking Partial
State Spaces with 3-Valued Temporal Logics." CAV 1999.
doi:10.1007/3-540-48683-6_25. Crossref only. Credibility: CAV. Grade C.

[SagivRepsWilhelm2002] M. Sagiv, T. Reps, R. Wilhelm. "Parametric shape
analysis via 3-valued logic." ACM TOPLAS 24(3), 2002.
doi:10.1145/514188.514190. Crossref only. Credibility: TOPLAS. Grade C.

[DamsGerthGrumberg1997] D. Dams, R. Gerth, O. Grumberg. "Abstract
interpretation of reactive systems." ACM TOPLAS 19(2), 1997.
doi:10.1145/244795.244800. Crossref only. Grade C.

[Chechik2003] M. Chechik, B. Devereux, S. Easterbrook, A. Gurfinkel.
"Multi-valued symbolic model-checking." ACM TOSEM 12(4), 2003.
doi:10.1145/990010.990011. Crossref only. Credibility: TOSEM. Grade C.

[UchitelChechik2004] S. Uchitel, M. Chechik. "Merging partial
behavioural models." FSE 2004. doi:10.1145/1029894.1029904. Crossref
only. Grade C.

[UchitelBrunetChechik2009] S. Uchitel, G. Brunet, M. Chechik.
"Synthesis of Partial Behavior Models from Properties and Scenarios."
IEEE TSE 35(3), 2009. doi:10.1109/tse.2008.107. Crossref only.
Credibility: TSE. Grade C.

[Antonik2010] A. Antonik, M. Huth, K. Larsen, U. Nyman, A. Wasowski.
"Modal and mixed specifications: key decision problems and their
complexities." Mathematical Structures in Computer Science 20, 2010.
doi:10.1017/s0960129509990260. Crossref only (the title I searched,
"20 years of modal and mixed specifications", EATCS Bulletin 2008, was
not found; this journal paper is a different, verified work). Grade C.

[LarsenThomsen1988] K. G. Larsen, B. Thomsen. "A modal process logic."
Proc. Third Annual Symposium on Logic in Computer Science (LICS 1988),
IEEE. doi:10.1109/lics.1988.5119. Verified 2026-10-09 via Crossref
(title, authors, venue) and OpenAlex abstract (a logic for
nondeterministic and concurrent processes with "a refinement ordering
between formulas"). The must/may reading is confirmed through
[Antonik2008]. Credibility: LICS, top logic venue; Larsen is a
co-author of UPPAAL [standing not re-verified]. Grade C (theory).

[Benes2009] N. Benes, J. Kretinsky, K. G. Larsen, J. Srba. "Checking
Thorough Refinement on Modal Transition Systems Is EXPTIME-Complete."
ICTAC 2009, LNCS. doi:10.1007/978-3-642-03466-4_7. Verified 2026-10-09
via Crossref and Semantic Scholar (title, authors, year; no abstract
available; the result is stated in the title). Journal version: "EXPTIME-
completeness of thorough refinement on modal transition systems,"
Information and Computation, 2012, doi:10.1016/j.ic.2012.08.001
(Crossref). Note: the first author is N. (Nikola) Benes, not J. as
previously written. Grade C (theory).

[Antonik2008] A. Antonik, M. Huth, K. G. Larsen, U. Nyman, A. Wasowski.
"20 Years of Modal and Mixed Specifications." Bulletin of the EATCS 95,
2008, pp. 94-129. https://vbn.aau.dk/ws/files/16474238/BEATCS2008.pdf
(publisher's version on Aalborg University repository). Added
2026-10-09; full text read (introduction, definitions 1-2, refinement,
thorough refinement, sec. 7 Sat/Val and the pessimistic/optimistic
semantics). Credibility: EATCS Bulletin survey column (invited, edited,
not a full peer-review venue) by the originators of the field. Grade C+
(authoritative theory survey).

[Belnap1977] N. Belnap. "A Useful Four-Valued Logic." In Modern Uses of
Multiple-Valued Logic, 1977. doi:10.1007/978-94-010-1161-7_2. Crossref
only. Grade C (logic classic).

[VanGelder1991] A. Van Gelder, K. Ross, J. Schlipf. "The well-founded
semantics for general logic programs." J. ACM 38(3), 1991.
doi:10.1145/116825.116838. Crossref only. Grade C. Relevance: a
three-valued (true/false/undefined) semantics for recursive rules with
negation, the natural semantics if grmb rules are Datalog-like.

[EasterbrookChechik2001] S. Easterbrook, M. Chechik. "A framework for
multi-valued reasoning over inconsistent viewpoints." ICSE 2001.
doi:10.1109/icse.2001.919114. Crossref only. Grade C.

[Balzer1991] R. Balzer. "Tolerating inconsistency (software
development)." ICSE 1991. doi:10.1109/icse.1991.130638. Abstract read
via OpenAlex. Credibility: ICSE; Balzer was a long-standing USC
Information Sciences Institute researcher [standing not re-verified].
Grade C+/X.

[NuseibehEasterbrookRusso2001] B. Nuseibeh, S. Easterbrook, A. Russo.
"Making inconsistency respectable in software development." Journal of
Systems and Software 58(2), 2001. doi:10.1016/s0164-1212(01)00036-x.
Crossref only. Grade C.

[Egyed2011] A. Egyed. "Automatically Detecting and Tracking
Inconsistencies in Software Design Models." IEEE TSE 37(2), 2011.
doi:10.1109/tse.2010.38. Abstract read via OpenAlex (34 models, up to
162,237 elements, 1.4 ms average). Credibility: TSE; evaluation on
industrial-size models per the abstract. Grade B.

[SpanoudakisZisman2001] G. Spanoudakis, A. Zisman. "Inconsistency
management in software engineering: survey and open research issues."
In Handbook of Software Engineering and Knowledge Engineering, 2001.
doi:10.1142/9789812389718_0015. Crossref only. Grade C (survey).

[SiekVitousekCiminiBoyland2015] J. Siek, M. Vitousek, A. Cimini, J.
Boyland. "Refined Criteria for Gradual Typing." SNAPL 2015, LIPIcs 32,
pp. 274-293. doi:10.4230/LIPIcs.SNAPL.2015.274;
https://drops.dagstuhl.de/storage/00lipics/lipics-vol032-snapl2015/LIPIcs.SNAPL.2015.274/LIPIcs.SNAPL.2015.274.pdf
Abstract and introduction read in full text. Credibility: SNAPL (peer
reviewed, Dagstuhl LIPIcs); Siek is the originator of gradual typing
(Siek-Taha 2006, referenced in the paper). Grade C+ (theory with
mechanized proof; broad adoption of the term).

[TakikawaFelteyGreenmanNew2016] A. Takikawa, D. Feltey, B. Greenman, M.
New et al. "Is sound gradual typing dead?" POPL 2016.
doi:10.1145/2837614.2837630. Abstract read via OpenAlex (Crossref lists
Takikawa, Feltey, Greenman, New; further authors not verified). Credibility: POPL; evaluation on Typed Racket
benchmarks. Grade C+.

[GaoBirdBarr2017] Z. Gao, C. Bird, E. Barr. "To Type or Not to Type:
Quantifying Detectable Bugs in JavaScript." ICSE 2017.
doi:10.1109/icse.2017.75. Abstract read via OpenAlex (Flow and
TypeScript each detect about 15 percent of public bugs). Credibility:
ICSE; evaluation on public project histories. Grade B.

[WadlerFindler2009] P. Wadler, R. Findler. "Well-Typed Programs Can't Be
Blamed." ESOP 2009. doi:10.1007/978-3-642-00590-9_1. Crossref only.
Grade C.

[BaderAldrichTanter2018] J. Bader, J. Aldrich, E. Tanter. "Gradual
Program Verification." VMCAI 2018. doi:10.1007/978-3-319-73721-8_2.
Crossref only; related arXiv:2311.07559 abstract read (gradual
verification supports explicitly partial specifications and makes
verification more incremental and gives earlier feedback). Grade C.

[OmarVoyseyChughHammer2019] C. Omar, I. Voysey, R. Chugh, M. Hammer.
"Live Functional Programming with Typed Holes." PACMPL 3(POPL), 2019.
doi:10.1145/3290327; arXiv:1805.00155 (extended version, read:
abstract, introduction). Credibility: POPL; prototype implemented as
the Hazel environment; no user study in the paper. Grade C+.

[OmarHazelnut2017] C. Omar, I. Voysey, M. Hilton, J. Aldrich, M.
Hammer. "Hazelnut: a bidirectionally typed structure editor calculus."
POPL 2017. doi:10.1145/3009837.3009900. Crossref only. Grade C.

[Zhao2024] "Total Type Error Localization and Recovery with Holes."
Zhao, Maroof, Dukkipati, Blinn et al. PACMPL POPL 2024.
doi:10.1145/3632910. Crossref only (author list truncated by
Crossref query; not fully verified). Grade C.

[GHCGuide] GHC User's Guide, "Typed Holes."
https://downloads.haskell.org/ghc/latest/docs/users_guide/exts/typed_holes.html
Fetched and read. Credibility: official compiler documentation (grade
V); GHC is the reference Haskell compiler.

[AgdaDocs] Agda documentation, "Lexical Structure" (Holes).
https://agda.readthedocs.io/en/latest/language/lexical-structure.html
Fetched and read. Grade V.

[ClippyTodo] Rust Clippy lint index, `clippy::todo` (restriction).
https://rust-lang.github.io/rust-clippy/master/index.html (anchor
`todo`). Fetched and read; text quoted in F10. Grade V (official Rust
project tooling).

[SolarLezama2013] A. Solar-Lezama. "Program sketching." Int. J. on
Software Tools for Technology Transfer 15, 2013.
doi:10.1007/s10009-012-0249-7. Crossref only. Grade C. Relevance:
holes filled by synthesis; not adopted.

[BackWright1998] R. Back, J. von Wright. "Refinement Calculus: A
Systematic Introduction." Springer, 1998. doi:10.1007/978-1-4612-1674-2
(chapters located on Crossref). Metadata only. Grade C (textbook).

[AbadiLamport1991] M. Abadi, L. Lamport. "The existence of refinement
mappings." Theoretical Computer Science 82(2), 1991.
doi:10.1016/0304-3975(91)90224-p. Crossref only. Credibility: TCS;
Lamport is the author of TLA+, used at AWS [Newcombe2015]. Grade C+.

[Abrial2010] J.-R. Abrial. "Modeling in Event-B: System and Software
Engineering." Cambridge University Press, 2010.
doi:10.1017/cbo9781139195881. Crossref only. Grade C+ (the Event-B
method is used in industrial railway systems per the author's own
claims; not re-verified).

[HoareEtAl1987] C.A.R. Hoare, I. Hayes, H. Jifeng, C. Morgan et al.
"Laws of programming." CACM 30(8), 1987. doi:10.1145/27651.27653.
Crossref only. Grade C.

[MorganVickers1990] C. Morgan, T. Vickers. "Types and invariants in the
refinement calculus." Science of Computer Programming 14, 1990.
doi:10.1016/0167-6423(90)90024-8. Crossref only. Grade C.

[Czarnecki2009] K. Czarnecki, N. Foster, Z. Hu, R. Laemmel et al.
"Bidirectional Transformations: A Cross-Discipline Perspective."
ICMT 2009. doi:10.1007/978-3-642-02408-5_19. Crossref only. Grade C.

[Foster2007] N. Foster, M. Greenwald, J. Moore, B. Pierce, A.
Schmitt. "Combinators for bidirectional tree transformations." ACM
TOPLAS 29(3), 2007. doi:10.1145/1232420.1232424. Crossref only
(Crossref lists four authors; I added Schmitt from my query and it is
not confirmed). 2026-10-09: Schmitt confirmed as fifth author by
Semantic Scholar and the paper's title page; full text read at
https://www.cis.upenn.edu/~bcpierce/papers/lenses-toplas-final.pdf
(Definition 3.2, GetPut/PutGet). Grade C.

[Stevens2008] P. Stevens. "Bidirectional model transformations in QVT:
semantic issues and open questions." SoSyM 9, 2010 (Crossref lists
2008 for the first online version).
doi:10.1007/s10270-008-0109-9. Crossref only. Grade C.

[Diskin2010] Z. Diskin, Y. Xiong, K. Czarnecki. "From State- to
Delta-Based Bidirectional Model Transformations." ICMT 2010.
doi:10.1007/978-3-642-13688-7_5. 2026-10-09: full text fetched from
https://gsd.uwaterloo.ca/sites/default/files/ICMT10_0.pdf (abstract and
introduction read). Grade C.

[SendallKozaczynski2003] S. Sendall, W. Kozaczynski. "Model
transformation: the heart and soul of model-driven software
development." IEEE Software 20(5), 2003. doi:10.1109/ms.2003.1231150.
Crossref only. Credibility: IEEE Software; authors from an industrial
research lab [standing not re-verified]. Grade B-.

[Murphy2001] G. Murphy, D. Notkin, K. Sullivan. "Software reflexion
models: bridging the gap between design and implementation." IEEE TSE
27(4), 2001. doi:10.1109/32.917525. Crossref; 2026-10-09 abstract read
via OpenAlex (Microsoft Excel reengineering named). Credibility: TSE.
Grade B (industrial case named in the abstract; [recalled] removed).

[Murphy1995] G. Murphy, D. Notkin, K. Sullivan. "Software Reflexion
Models: Bridging the Gap between Source and High-Level Models." Proc.
3rd ACM SIGSOFT Symposium on the Foundations of Software Engineering
(FSE 1995), pp. 18-28.
https://www.cs.ubc.ca/~murphy/papers/rm/reflexion_model_fse95.pdf ;
technique page https://www.cs.ubc.ca/~murphy/software/rmtool/rms.html .
Added 2026-10-09; full text read (abstract, sec. on partial maps and
iteration, Excel case). Credibility: FSE; Excel work done with
Microsoft engineers per the paper. Grade B.

[GreenBlackwell1998] T. Green, A. Blackwell. "Cognitive Dimensions of
Information Artefacts: a tutorial." Version 1.2, October 1998.
https://www.cl.cam.ac.uk/~afb21/CognitiveDimensions/CDtutorial.pdf
Downloaded and read (definitions of viscosity, premature commitment,
hidden dependencies, provisionality, progressive evaluation).
Credibility: primary document by the framework's authors (University
of Cambridge, hosted on Blackwell's departmental page). Grade C+/O.

[GreenPetre1996] T. Green, M. Petre. "Usability Analysis of Visual
Programming Environments: A 'Cognitive Dimensions' Framework." Journal
of Visual Languages and Computing 7(2), 1996.
doi:10.1006/jvlc.1996.0009. Crossref and OpenAlex (1,253 citations).
Credibility: JVLC; the founding CD paper. Grade B- (widely applied,
including by commercial product designers per the CD resource page).

[Blackwell2001] A. Blackwell, C. Britton, A. Cox, T. Green, C. Gurr, G.
Kadoda, M. Kutar, M. Loomes, C. Nehaniv, M. Petre, C. Roast, C. Roe, A.
Wong, R. Young. "Cognitive Dimensions of Notations: Design Tools for
Cognitive Technology." Cognitive Technology 2001, LNCS 2117.
doi:10.1007/3-540-44617-6_31. Crossref only. Grade C.

[BlackwellGreen2003] A. Blackwell, T. Green. "Notational Systems: The
Cognitive Dimensions of Notations Framework." In HCI Models, Theories,
and Frameworks, 2003. doi:10.1016/b978-155860808-5/50005-8. Crossref
only. Grade C.

[Cherubini2007] M. Cherubini, G. Venolia, R. DeLine, A. Ko. "Let's go to
the whiteboard: how and why software developers use drawings." CHI
2007. doi:10.1145/1240624.1240714. Abstract read via OpenAlex.
Credibility: CHI; interview study with a survey validation; authors
Cherubini, Venolia and DeLine were at Microsoft Research per the
paper's affiliations in metadata [not re-fetched]. Grade B.

[Mangano2015] N. Mangano, T. LaToza, M. Petre, A. van der Hoek. "How
Software Designers Interact with Sketches at the Whiteboard." IEEE TSE
41(2), 2015. doi:10.1109/tse.2014.2362924. Abstract read via OpenAlex
(Crossref lists Mangano, LaToza, Petre, van der Hoek). Credibility: TSE;
study of professional designers; Petre and van der Hoek are the authors
of [PetreVanDerHoek2016]. Grade B.

[BaltesDiehl2014] S. Baltes, S. Diehl. "Sketches and diagrams in
practice." FSE 2014. doi:10.1145/2635868.2635891; arXiv:1706.09172.
Full text downloaded and read (abstract, findings: 394 survey
participants, three-company exploratory study). Credibility: FSE;
mixed-methods with practitioner participants across 32 countries.
Grade B.

[Petre2013] M. Petre. "UML in practice." ICSE 2013.
doi:10.1109/icse.2013.6606618. Abstract read via OpenAlex (interviews
with 50 professional engineers, five patterns of use). Credibility:
ICSE; Petre is an Open University professor with decades of studies of
professional design practice [standing not re-verified]. Grade B.

[PetreVanDerHoek2016] M. Petre, A. van der Hoek (with Y. Quach).
"Software Design Decoded: 66 Ways Experts Think." MIT Press, 2016.
doi:10.7551/mitpress/10612.001.0001 (Crossref lists Petre, van der
Hoek, Quach). Not read; metadata only. Credibility: book based on
studies of professional designers [recalled]. Grade B- (unread).
2026-10-09: chapter titles verified via Crossref (chapter DOIs
10.7551/mitpress/10612.003.0001-0016); publisher description and
sample insights read on the Google Books listing
https://books.google.com/books/about/Software_Design_Decoded.html?id=EVE4DQAAQBAJ
(the description itself states the insights are distilled from years
of studying experts at work, so [recalled] is removed). MIT Press and
Open Research Online pages returned HTTP 403; the companion website
named in the description was not found. Insight bodies unread. Grade
O for content (book, not peer reviewed), resting on B-grade studies by
the same authors.

[Petre1995] M. Petre. "Why looking isn't always seeing: readership
skills and graphical programming." CACM 38(6), 1995.
doi:10.1145/203241.203251. Crossref only. Grade C+.

[Curtis1988] B. Curtis, H. Krasner, N. Iscoe. "A field study of the
software design process for large systems." CACM 31(11), 1988.
doi:10.1145/50087.50089. 2026-10-09: abstract read via OpenAlex
(interviews with personnel from 17 large projects; three problems
named). Credibility: CACM; field study of real large-system projects
(the MCC shareholder-company setting is [recalled], not re-verified;
an MCC report seen only as a search snippet gives 19 projects, the
published abstract says 17). Grade B.

[Guindon1990] R. Guindon. "Designing the design process: exploiting
opportunistic thoughts." Human-Computer Interaction 5(2-3), 1990.
doi:10.1207/s15327051hci0502&3_6. Crossref; 2026-10-09: claims
checked against Guindon's own abstract for the Stanford Seminar on
People, Computers, and Design, 3 April 1991,
https://hci.stanford.edu/seminar/abstracts/90-91/910403-guindon.html
(she was at MCC's Human-Computer Interface and Software Technology
programs). The paper body was not read. Grade C+ (observational
study; method details unverified).

[ParnasClements1986] D. Parnas, P. Clements. "A rational design
process: How and why to fake it." IEEE TSE 12(2), 1986.
doi:10.1109/tse.1986.6312940. 2026-10-09: full text read (author
copy, https://users.ece.utexas.edu/~perry/education/SE-Intro/fakeit.pdf)
and abstract via OpenAlex. Credibility: TSE; both authors at the Naval
Research Laboratory, and the A-7E module guide and interface
specifications are cited as the worked documents (verified in the
reference list; [recalled] removed). Grade B- (position paper).

[Hutchinson2011] J. Hutchinson, J. Whittle, M. Rouncefield, S.
Kristoffersen. "Empirical assessment of MDE in industry." ICSE 2011.
doi:10.1145/1985793.1985858. Abstract read via OpenAlex (twelve-month
study, questionnaires and interviews). Credibility: ICSE; industrial
partner organizations. Grade B.

[Whittle2014] J. Whittle, J. Hutchinson, M. Rouncefield. "The State of
Practice in Model-Driven Engineering." IEEE Software 31(3), 2014.
doi:10.1109/ms.2013.65. Abstract read via OpenAlex (450 survey
respondents, 22 interviews). Credibility: IEEE Software; large
practitioner sample. Grade B.

[Hebig2016] R. Hebig, T. Ho-Quang, M. Chaudron, G. Robles, M.
Fernandez. "The quest for open source projects that use UML: mining
GitHub." MODELS 2016. doi:10.1145/2976767.2976778 (Crossref lists
Hebig, Quang, Chaudron, Robles for this DOI). Abstract read via
OpenAlex (21,316 diagrams, 3,295 projects, ~1.24 million projects
scanned at 10 percent). Credibility: MODELS; very large corpus, open
source only (not industrial). Grade B.

[Stoerrle2017] H. Stoerrle. "How are Conceptual Models used in
Industrial Software Development? A Descriptive Survey." EASE 2017.
doi:10.1145/3084226.3084256. Abstract (partial) read via OpenAlex.
Credibility: EASE. Grade C+.

[Newcombe2015] C. Newcombe, T. Rath, F. Zhang, B. Munteanu, M.
Brooker, M. Deardeuff. "How Amazon Web Services uses formal methods."
CACM 58(4), 2015. doi:10.1145/2699417. Crossref and OpenAlex (abstract
"Engineers use TLA+ to prevent serious but subtle bugs from reaching
production"). Credibility: CACM; authors are AWS engineers (Crossref
lists Newcombe, Rath, Zhang, Munteanu). Grade A (experience report at
named company, large scale).

[Garlan2010] D. Garlan. "Software engineering in an uncertain world."
FoSER 2010. doi:10.1145/1882362.1882389. Crossref only. Grade C.
Scope-bounding only.

[Ramirez2012] A. Ramirez, A. Jensen, B. Cheng. "A taxonomy of
uncertainty for dynamically adaptive systems." SEAMS 2012.
doi:10.1109/seams.2012.6224396. Crossref only. Scope-bounding only.

[PerezPalacinMirandola2014] D. Perez-Palacin, R. Mirandola.
"Uncertainties in the modeling of self-adaptive systems." ICPE 2014.
doi:10.1145/2568088.2568095. Crossref only. Scope-bounding only.

## Appendix: coverage verdict

Denominator: 14 clusters / ~75 enumerated works. Read at full-text or
primary-document level: Famelis thesis, Salay JOT 2015, Hazel Live,
SNAPL 2015, Green-Blackwell tutorial, Baltes-Diehl, GHC, Agda and
Clippy docs (9 works). Abstract level: 14. Metadata-only: ~50. Failed:
2 (marked [unverified]). Two findings (F6, F14 partly, F16, F17) rest on
recall of well-known results and are marked [recalled]. Strongest
evidence for the conclusions is the thesis (F1-F4), Hazel (F9), SNAPL
(F7), the CD tutorial (F15) and Baltes/Whittle/Hebig/Cherubini (F12,
F13). Weakest: F6 and F17 (theory/recall), F18 (absence of evidence).
Verdict: topic D is covered to the depth needed to set the design
consequences in section 3; it is not exhaustive at full-text level and
should not be described as such.

## 7. Verification pass (2026-10-09)

Done by a second agent with WebSearch/WebFetch available (the original
run had none). Every [unverified] and [recalled] tag that a finding
relied on was checked against a primary text. Section numbering skips
6 to match the sibling notes. Changes, by kind:

Fixed (verified, tag removed, wording corrected):
- F6 (MTS): verified against the full text of [Antonik2008] (survey by
  Larsen and Huth among others). Three wording corrections added in
  place: the preserved verdict is the pessimistic/must one; it is only
  sound for consistent specifications (inconsistent ones make every
  property valid); modal refinement implies thorough refinement but not
  conversely.
- F14 (design is opportunistic): Curtis et al abstract read (17
  projects, three named problems); Guindon checked against her own 1991
  seminar abstract (paper body still unread, so no method claims);
  Parnas-Clements full text read, with two quotes added, including
  their policy of recording rejected design alternatives with reasons.
- F16 (bidirectional transformations): lens laws GetPut/PutGet read in
  Foster et al TOPLAS 2007 (Definition 3.2); Diskin et al ICMT 2010
  abstract and introduction read; Hutchinson et al abstract re-read.
- F17 (reflexion models): FSE 1995 full text and TSE 2001 abstract
  read; convergence/divergence/absence, partial maps and iterative
  refinement confirmed; Microsoft Excel case confirmed (a Microsoft
  engineer applied the technique).
- [LarsenThomsen1988]: resolved (doi:10.1109/lics.1988.5119), abstract
  read.
- [Benes2009]: resolved (doi:10.1007/978-3-642-03466-4_7); first author
  initial corrected from J. to N. (Nikola); journal version added.
- [Foster2007]: fifth author Schmitt confirmed.
- [ParnasClements1986], [Curtis1988], [Murphy2001], [Guindon1990],
  [PetreVanDerHoek2016]: verification level and grades updated in the
  bibliography.

Downgraded:
- F11: the Nuseibeh-Easterbrook-Russo "respectable inconsistency"
  position is title-level only (no abstract available); the finding
  still rests on Balzer and Egyed, which were read.
- [Curtis1988]: the MCC/industrial-participant setting remains
  [recalled]; only the abstract content is now asserted.

Removed:
- Nothing removed. No source contradicted the claim it was cited for.

Added:
- [Antonik2008] (full text) and [Murphy1995] (full text) to the
  bibliography.
- F19: the public content of "Software Design Decoded" (chapter titles
  via Crossref; seven insights quoted in the publisher description).
  The companion website mentioned by the publisher could not be found;
  the insight bodies are not public. It reinforces I1, I2, I6, I7, I8
  and adds no rule.
- PLN-INC15 (consistency check, lo subset of hi; suppress Pass on an
  inconsistent model), from the verified vacuity result in F6.
- A note on PLN-INC14: it must be a structural (modal) subset check;
  the semantic (thorough) version is EXPTIME-complete.

Recommendation changes: none flip. I6 (`choice` with `rejected
because=`) gains a direct practitioner-position source (Parnas and
Clements, NRL, A-7E). I4 (gradual guarantee) is unchanged but should
be read with the F6 caveat: monotonicity holds only for consistent
models, which PLN-INC15 enforces.

Revised coverage verdict: of the four [recalled] findings, all four
(F6, F14, F16, F17) now rest on primary text read in this pass (full
text for F6, F16, F17 and Parnas; abstracts for Curtis and Guindon).
No finding depends on an [unverified] citation. Still unread at full
text: the original MTS papers (Larsen-Thomsen, Huth et al, Godefroid et
al, Bruns-Godefroid; covered through the originators' own survey),
Guindon 1990 and Curtis 1988 bodies, the Green-Petre 1996 paper (the
authors' 1998 tutorial is the read primary source), the Petre-van der
Hoek insight texts, and the ~45 remaining metadata-only theory items.
None of these is cited for a claim beyond what was read. Topic D is now
covered at primary-source level for every finding that carries a grmb
consequence; it remains non-exhaustive at full-text level for the
metadata-only theory tail, which is used only as pointers.
