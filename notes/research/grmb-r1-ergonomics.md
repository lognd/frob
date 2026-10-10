# grmb R1 topic F: quality-of-life language ergonomics

Ticket ~19SEHXJ, researcher F. ASCII only. Not committed (coordinator
commits). Inputs read: docs/design/grmb-spec.md (sections 2.5-2.7, 3.3,
9.3, 11 in full), the planning-layer brief (sections 3-4, 6).

## 1. Scope and search log

### 1.1 Honest tooling statement

- WebSearch and WebFetch were NOT available: ToolSearch returned "no
  matching deferred tools" for both ("select:" and keyword forms), and no
  arxiv MCP was offered. All lookups below were done with `curl`/Python
  from Bash against primary hosts. Consequence: there was no free-text
  web search; discovery was by (a) enumerating the field from the topic
  brief, (b) Crossref `query.bibliographic` lookups (DOI-verified), (c)
  OpenAlex and Semantic Scholar abstract lookups, (d) direct fetch of
  official language documentation and surveys. The arXiv API timed out
  and was dropped; one guessed arXiv id (2204.00540) turned out to be an
  unrelated speech paper and was discarded, never cited.
- Every item in the bibliography (section 5) was fetched or resolved in
  this run unless marked [unverified]. Where only metadata (not abstract
  or body) was resolved it says "metadata only".

### 1.2 Field enumeration (the denominator)

Topic F asks for six sub-fields. Enumerated first, then drained:

| Sub-field | Items enumerated | Read in this run |
|---|---|---|
| F1 Rust/Zig mechanisms | exhaustive match, diagnostics, suggestions, editions, local inference, comptime, error unions/try, labeled blocks, shadowing, fmt, LSP | Rust book match chapter, rustc-dev-guide diagnostics + error codes, Rust blog "Shape of errors to come", RFC 2008, RFC 2052, Edition Guide, cargo-fix, lint levels, Clippy index; Zig language reference (error sets, inferred error sets, try, shadowing, labeled blocks, switch); LSP 3.17 spec |
| F2 Other languages | Elm, Gleam, Roc, Kotlin, Swift, TypeScript, Go, Python | Gleam tour, Roc FAQ, Kotlin sealed docs, Swift SE-0192, TS narrowing handbook, gofmt blog, Go "splash" design article, PEP 20, PEP 8. Elm: see 1.3 |
| F3 Config-like languages | Nix, Dhall, CUE, HCL, Starlark, Pkl, KDL, TOML | all eight official pages fetched (Pkl page was nav-only, see 1.3) |
| F4 Annoyance evidence | Rust survey, Stack Overflow survey, Go survey; PLATEAU/CHI/OOPSLA/Onward/ICSE usability studies; Cognitive Dimensions | Rust 2024 survey post, SO 2024 technology page, Go 2024 H2 survey; Barik ICSE17, Wrenn Onward17, Becker ITiCSE-WGR19, Stefik TOCE13, Myers CHI16 SIG, Coblenz OOPSLA20, Pane IJHCS01, Zhu ICSE22, Johnson ICSE13, Sadowski ICSE15/CACM18, Green&Petre JVLC96 (metadata), Omar POPL19, Newcombe CACM15 |
| F5 Prediction | 7 named annoyances in the brief | section 3 |
| F6 Mitigation | defaults, inference, sugar, quick-fixes, fmt, LSP actions, progressive disclosure | section 3 and 4 |

### 1.3 Excluded or unreadable, and why it does not change conclusions

- Elm "Compiler Errors for Humans" and "Compilers as Assistants"
  (elm-lang.org/news): pages are client-rendered JavaScript; the fetch
  returned only the page title; the Wayback copy was the same. Elm's
  influence is therefore cited only through the Rust blog post that states
  its debt to Elm (verified text), and through Wrenn & Krishnamurthi and
  Marceau et al., which are the academic follow-ups. Elm's own claims are
  not asserted here. Effect on conclusions: none; the diagnostics
  recommendations are independently supported by Barik (eye tracking) and
  rustc's documented practice.
  [2026-10-09: resolved. The page sources are in the elm/elm-lang.org
  GitHub repository (pages/news/*.elm, markdown embedded); three posts
  were read in full and are now F-26.]
- Green & Petre 1996 and the CD tutorial site (cl.cam.ac.uk, HTTP 403):
  the 1996 paper was resolved by DOI (metadata only, no abstract). The 14
  dimension definitions used below were read from the Wikipedia article
  "Cognitive dimensions of notations" (secondary source, flagged weak);
  the framework itself is by Green and Petre and is listed with metadata.
  [2026-10-09: replaced. Green and Blackwell's own tutorial (v1.2,
  1998) was fetched and read; F-19 now quotes its definitions and the
  Wikipedia source is withdrawn.]
- Pkl: the fetched page was navigation chrome only. Pkl is cited as a
  named comparator only; no claim rests on it.
- Brindescu et al. ICSE 2014 (DVCS and software changes): resolved, but
  its abstract says nothing about merge conflicts; dropped, not cited.
- Not read: Rust annual survey raw data, Stack Overflow "most dreaded"
  numbers, Go survey free-text, PLATEAU proceedings beyond what Crossref
  surfaced, Hazel's later usability work, GQL/OCL ergonomics (topic E),
  design-doc practice (topic A). They would sharpen magnitudes, not flip
  any recommendation here, because every recommendation below is backed
  by at least one verified primary mechanism document.

### 1.4 Credibility grading used

- A: peer-reviewed venue (ICSE, OOPSLA/PACMPL, Onward, POPL, CACM,
  TOCE, IJHCS, JVLC) and/or official language/vendor documentation by the
  language owner.
- B: official docs from a language steering body, with large-scale
  practitioner use (counted as vendor doc).
- C: secondary (Wikipedia) or metadata-only; reported as weak.
- Practitioner standing is stated per source in section 5 only when the
  source itself (byline, text) establishes it. Where I know a person's
  standing but did not fetch a source for it, that is said so rather than
  asserted.

## 2. Findings

Evidence strength tags: EMP (empirical study), EXP (experience report),
DOC (official language/vendor doc), OPN (opinion/rationale text).

### 2.1 Exhaustive handling, and the cost of adding a variant

F-01. Rust, Gleam, Kotlin and TypeScript all make exhaustiveness a
compile-time check whose stated purpose is exactly grmb's: Gleam says
exhaustiveness checking gives "confidence that your logic is up-to-date
for the design of the data you are working with"; Kotlin sealed `when`
needs no `else` when all cases are covered; TypeScript uses a `never`
assignment in `default` to turn a missed case into an error. Strength:
DOC. [Gleam tour; Kotlin sealed docs; TS handbook narrowing]
Maranget (JFP 2007) is the standard algorithm for the exhaustiveness and
redundancy warnings (metadata only here). Strength for the algorithm: A.

F-02. The ergonomic hazard of exhaustiveness is the wildcard. Clippy
ships `wildcard_enum_match_arm` (restriction, allow by default) with the
rationale "New enum variants added by library updates can be missed", and
`match_wildcard_for_single_variants` (pedantic) with the same rationale.
That is: the language's own linter team treats wildcard arms as a latent
bug and still leaves them legal and off by default. Strength: DOC.

F-03. Swift solved the "wildcard hides new variants" vs "adding a variant
must not break clients" tension with `@unknown default` (SE-0192): it
matches anything like `default`, but "the compiler will produce a warning
if all known elements of the enum have not already been matched", and it
is a warning (not an error) "so that adding new elements to the enum
remains a source-compatible change". The proposal also records, under
"Post-acceptance revision", that "the rollout plan turned out to be a
little too aggressive": "the diagnostic for omitting `@unknown default:`
or `@unknown case _:` will only be a warning", and "in Swift 4 mode
there will be no diagnostic at all". Status: "Implemented (Swift 5.0)".
[Re-verified 2026-10-09.] Strength: DOC
(language-evolution process document; design rationale is primary).

F-04. Rust RFC 2008 (`#[non_exhaustive]`) motivates a marker for "this
variant set may grow" so that library authors can add variants without it
being a breaking change, and forces downstream matches to carry a
wildcard. The two-sided contract (owner marks open; consumer must then
write a catch-all) is the model for externally owned outcome sets such as
a payment gateway's declined reasons. Strength: DOC.
[Re-verified 2026-10-09; start date 2017-05-24. Quotes: the attribute
"will force downstream crates to add a wildcard arm to `match`
statements", so "we can add as many variants as we want without
breaking any downstream matches"; within the defining crate "this
attribute is essentially ignored, so that the current crate can
continue to exhaustively match the enum". Consequence for I-03: `open`
must only relax matches written outside the owning actor/pack; the
owner's own scenarios stay exhaustive.]

F-05. Zig's inferred error sets (`!T`) are documented with their own
limits: the function becomes generic, they are "incompatible with
recursion", cannot give a stable set across targets, and the doc
recommends: "start with an empty error set and let compile errors guide
you toward completing the set". `try x` is defined as "if it is an error,
it returns from the current function with the same error. Otherwise, the
expression results in the unwrapped value." Error return traces exist so
that "it [is] practical to use try everywhere and then still be able to
know what happened". Strength: DOC.
Implication: the planning brief's inferred collected set under `-|>` is
the Zig design; the Zig doc itself says to switch to an explicit set at
boundaries (recursion, stable interfaces) and to let diagnostics
construct it. grmb has `fails with` as that explicit boundary.

F-06. Roc has principal type inference and open tag unions: its FAQ
shows `[Loading, Loaded(Artist), Errored(LoadingErr)]`, says types are
inferred with no annotations needed, and has no `null`/`Option`
(convention: `Try` with an error type). Roc's FAQ explicitly rejects
features where inference would need annotations. Strength: DOC/OPN.
Implication: structural, inferred, open variant sets are mainstream in a
current language; grmb's step outcome sets can be inferred from usage,
with `step ... -> { ... }` as optional documentation.

### 2.2 Diagnostics and suggestions

F-07. Barik et al., ICSE 2017: eye tracking, 56 participants; they read
error messages, reading difficulty is comparable to reading source and
predicts task performance, and 13%-25% of task time goes to reading error
messages. Strength: EMP (A). Conclusion stated by the authors: the data
"justif[ies] the need to improve compiler error messages".

F-08. Becker et al., ITiCSE-WGR 2019: a historical survey of error
message research; diagnostics "present substantial difficulty and could
be more effective, particularly for novices". Strength: EMP/survey (A).
Wrenn & Krishnamurthi, Onward! 2017: treat an error report as a
classifier, measure it with precision and recall; Marceau et al., SIGCSE
2011 (metadata): measured effectiveness of novice-designed messages.
Strength: EMP (A).

F-09. rustc practice (rustc-dev-guide): every diagnostic has a primary
span, optional secondary spans and labels; most errors carry a stable
code with a mandatory long-form explanation (`--explain E0123`);
suggestions carry an `Applicability` of MachineApplicable,
HasPlaceholders, MaybeIncorrect or Unspecified so tools know what may be
applied mechanically; style guide: the error line itself "should not
suggest how to fix the problem" (the fix goes in a separate help).
The 2016 Rust blog "Shape of errors to come" states the design principle
"errors should focus on the code you wrote" and credits Elm for the
`--explain` style. Strength: DOC/EXP.

F-10. Static-analysis adoption: Johnson et al. (ICSE 2013, 20 developer
interviews): "false positives and the way in which the warnings are
presented" are barriers, and an interactive mechanism to help fix is
needed. Sadowski et al. (Tricorder, ICSE 2015; Google): a platform
designed around developer workflow and an in-situ evaluation; the CACM
2018 lessons paper opens "developers must feel they benefit from and
enjoy using it". Strength: EMP/EXP (A); Google engineers on a system used
company-wide (byline and paper text). Implication: noise on incomplete
models kills adoption; fixes must be attached to findings.

### 2.3 Evolution, formatting, tooling

F-11. Rust editions (RFC 2052; Edition Guide): breaking changes are
opt-in per crate; "crates in one edition must seamlessly interoperate
with those compiled with other editions"; changes are "skin deep" because
all editions lower to the same internal representation; migration is
largely automated (`cargo fix --edition`, which applies rustc's
MachineApplicable suggestions); RFC 2052 principle: most code with
warnings on edition N "should, after running rustfix, compile on edition
N+1 and have the same behavior"; and it names "Limiting churn" as a cost
even with tooling. Strength: DOC.

F-12. gofmt: stated goals "easier to write: never worry about minor
formatting concerns", "easier to read", "uncontroversial: never have a
debate about spacing or brace position ever again". The Go 2024 H2 survey
(vendor survey, self-selected, 4,156 responses, Alice Merrick, 2024-12-20)
reports the most common team challenges as "maintaining consistent
coding standards across our Go codebase (58%)", tied with identifying
performance issues (58%); 21% chose it as the challenge whose solution
would benefit their team most; write-ins attribute it to members with
"varying levels of experience with Go" from "different programming
backgrounds". [Corrected 2026-10-09: the earlier "58% of those asked"
implied a subset; the post gives no n for this chart.] The 2025 survey
(5,379 responses, Todd Kulesza, 2026-01-21) repeats the theme:
respondents "asked for help with identifying and applying best
practices", with "Ensuring our Go code follows best practices / Go
idioms" reported by 33%. Strength: DOC plus survey
(self-selected; weak-to-moderate). Implication: a formatter ends style
debate but does not enforce idiom; idiom needs lints (Clippy-style).

F-13. LSP 3.17 defines `textDocument/codeAction` with kinds including
`quickfix`; a language server can offer fixes for any diagnostic.
Strength: DOC (Microsoft-owned open spec used by every major editor).
Implication: one server gives VS Code, Neovim, Helix, JetBrains, Zed the
same quick-fixes; no per-editor work beyond the generated grammar the
spec already plans (grmb-spec 2.6).

F-14. Rust 2024 survey: slow compilation tops productivity limiters;
tooling that is "slow or resource intensive (rust-analyzer and rustfmt)"
appears in open answers; top worry for the future remains that Rust "will
become too complex" even though users find current complexity manageable;
Rust is the most-admired language in the 2024 SO survey.
[2026-10-09: 2024 figures re-verified (9,450 started, 7,310 completed).
The 2025 survey (7,156 responses, published 2026-03-02) is newer:
"resource usage (slow compile times and storage usage) is still up
there"; "concerns persist about the language becoming more and more
complex"; and, against the team's prior assumption, "many Rust users
actually do find compiler error code explanations useful" (`--explain`).
The last item is direct, if self-selected, support for I-12.] Strength:
self-selected surveys (weak individually; DOC for the figures). Zhu et
al. (ICSE 2022, metadata and truncated abstract only) is the peer-
reviewed study of Rust learning and programming challenges; Crichton
(HATRA/SPLASH 2020) is the argued account of why the borrow checker is a
learning barrier and says errors are hard because the user cannot tell
"unsound" from "analyser limitation". Strength: A for Zhu, OPN/EXP for
Crichton (single author, teaching experience).
Implication: the checker's incompleteness (what the analysis cannot
decide) must be labelled in diagnostics, else users cannot distinguish
"your model is wrong" from "grimble cannot see this" (grmb already has
Unresolved/Advisory severities, spec section 11).

### 2.4 Usability of languages, notations and non-programmers

F-15. Stefik & Siebert (TOCE 13(4), Article 19, 2013; full text read in
the 2026-10-09 pass). What it measured: two surveys of subjective
"intuitiveness" ratings (0-10) of candidate words and symbols, by
programmers and non-programmers; then two randomized controlled trials
(Study 3: 18 participants, Study 4: 72) with university students from
non-computing classes who had never programmed. Each participant got
one of six languages (Ruby, Java, Perl, Python, Quorum, and Randomo,
whose keywords were "randomly" chosen from the ASCII table as a
placebo), studied code samples, and WROTE six small programs
(conditionals, loops, functions) in 6-10 minutes each; output was
scored per component against an answer key ("percent correct"). Main
result: "languages using a more traditional C-style syntax (both Perl
and Java) did not afford accuracy rates significantly higher than a
language with randomly generated keywords, but ... languages which
deviate (Quorum, Python, and Ruby) did". Token-level findings cut both
ways for keywords: `==` was used correctly by 1 of 48 novices (single
`=` by 67%), and `for`/`while`/`foreach` were rated least intuitive by
non-programmers, but Quorum's English keywords `then` and `end` had
some of the worst accuracy, Ruby's terse conditionals appeared most
successful (the authors' reading), and
the authors conclude that "simply adding extra words to make the
syntax more English-like (e.g., in, then) does not necessarily benefit
novices". Their own threats section: tasks "are also simple and not
representative of what professionals do". Strength: EMP (A venue),
small N, novice writers only. Arrow operators of the kind grmb uses
(`->`, `=>`) were not tested. Implication (revised 2026-10-09): the
study shows that some symbols (`==`) and some keywords (`then`, `end`)
are each error-prone for first-time writers; it does NOT show that
keyword spellings beat symbol spellings, and says nothing about readers
(PMs reviewing a model) or about experienced users. It supports testing
the concrete tokens with target users, not a keyword-first rule.

F-16. Pane, Ratanamahatana & Myers (IJHCS 2001; metadata only here):
studied how non-programmers describe solutions to programming problems.
Strength: EMP (A) for existence; findings not verified in this run, so
no claim rests on its content except as the canonical citation to read
before finalising novice-facing vocabulary.

F-17. Coblenz et al. (OOPSLA/PACMPL 2020, 20 participants): an
advanced type system (ownership, assets, typestate) in Obsidian "can be
usable": Obsidian users completed more tasks than Solidity users and
Solidity users inserted asset bugs that Obsidian caught at compile time.
Strength: EMP (A, small N). Implication: strong static checking is not
itself the annoyance; poor feedback and ceremony are.

F-18. Myers et al., CHI 2016 SIG, and "Programmers are users too" (IEEE
Computer 2016): programming languages have had little human-factors
evaluation; use human-centred methods on tools. Strength: OPN/survey
(A, short). Implication: grmb should be tested with think-aloud sessions
(PM, designer, embedded engineer) before the grammar freezes.

F-19. Cognitive Dimensions (Green & Petre, JVLC 7(2):131-174, 1996, the
founding paper; definitions below are quoted from the framework
authors' own tutorial, Green & Blackwell, "Cognitive Dimensions of
Information Artefacts: a tutorial", v1.2, October 1998, read in full
text on 2026-10-09, replacing the Wikipedia summary). The tutorial's
summary table: viscosity "resistance to change"; premature commitment
"constraints on the order of doing things"; progressive evaluation
"work-to-date can be checked at any time"; diffuseness "verbosity of
language"; hidden dependencies "important links between entities are
not visible"; hard mental operations "high demand on cognitive
resources"; error-proneness "notation invites mistakes";
role-expressiveness "the purpose of a component is readily inferred";
closeness of mapping "closeness of representation to domain";
consistency "similar semantics are expressed in similar syntactic
forms"; secondary notation "extra information in means other than
formal syntax"; provisionality "degree of commitment to actions or
marks"; visibility "ability to view components easily"; abstraction
"types and availability of abstraction mechanisms". Sub-types:
repetition viscosity (one goal-level change needs many repetitive
actions) and knock-on viscosity ("one change 'in the head' entails
further actions to restore consistency"). The tutorial rates viscosity
"acceptable" for transcription and incrementation but "harmful" for
modification and exploration, says "the worst problems come when
viscosity is combined with premature commitment", and that viscosity
is "a property of the system as a whole" so tools can alleviate it.
Strength: OPN/T framework by its authors, widely applied (JVLC paper
1,253 citations per OpenAlex); definitions now primary (grade A for
the definitions, previously C).

F-20. Hazel / typed holes (Omar et al., POPL 2019): programs with holes
get static and dynamic meaning so "feedback ... [has no] gaps" while code
is incomplete; empty holes stand for missing expressions or types.
Strength: A (formal PL). Implication: an unfinished arm, step or impl
should be a first-class hole with defined semantics, not a syntax error;
grmb-spec already has `hole` as a file-level concept (spec 9.3 item 6)
but only for syntax errors; here it should also be a deliberate
authoring tool.

F-21. Newcombe et al. (CACM 2015, Amazon Web Services, byline and text):
"Engineers from entry level to Principal have been able to learn TLA+
from scratch and get useful results in 2 to 3 weeks, in some cases just
in their personal time ... without help or training"; 7 teams use it;
PlusCal (a pseudo-code front end, translated to TLA+ "with a single key
press") was preferred by several engineers. Strength: EXP at scale (A,
named company, principal engineers; only the learn-time, team-count and
PlusCal claims are quoted). Implication: a specification notation can be learnt
by non-specialists in weeks if there is a familiar front end; progressive
disclosure (pseudo-code layer first) is a proven adoption lever.

F-22. Config-language design rationales (all DOC, all vendor/author
text): Dhall is "not Turing-complete" and total (safety by design); CUE
makes evaluation order-independent ("independently of order") through
lattice unification; Starlark is deterministic, Python-like and
"simpler and reduces the number of concepts"; HCL is "designed to be
easily read and written by humans" while keeping a JSON variant for
machines; TOML is "minimal ... easy to read due to obvious semantics" and
maps "unambiguously to a hash table"; KDL calls itself "small, pleasant"
with node-level comments (slashdash); Nix is a pure, lazy, functional,
declarative language. Common lesson: config-like languages that stay
non-Turing-complete, order-independent and with a machine-readable twin
keep tooling (fmt, diff, merge) tractable. grmb already is order-
independent (spec 3.3) and has a canonical fact stream (U, spec 9).
Strength: DOC (design intent, not usage measurements).

F-23. Python ergonomics: PEP 20 ("Readability counts", and the "should
be one obvious way" ethos) and PEP 8's "A Foolish Consistency is the
Hobgoblin of Little Minds" (consistency within a module outranks the
style guide). Strength: OPN by language owners (DOC).

F-26. (Added 2026-10-09.) Elm's error-message work, by its designer
Evan Czaplicki, read from the page sources in the elm/elm-lang.org
repository. "Compiler Errors for Humans" (Elm 0.15.1, 2015-06-30):
"you can make a shockingly huge difference just by thinking about the
user experience"; "The error shows the code exactly as you wrote it"
with its line numbers; "Every message has a useful hint"; color and
layout, with general context above the code and specific hints below
("reveal detail as needed"); `--report=json` so editor plugins can show
errors in place; and a technical note that the specific messages
"required no significant changes to the type inference algorithm and
imposed no noticeable performance cost". "Compilers as Assistants"
(Elm 0.16, 2015-11-19): "Compilers should be assistants, not
adversaries"; the release added detection of incomplete pattern
matches, "type diffs" that hide matching parts of large types and
highlight the difference, expected-vs-actual wording where it makes
sense, and beginner hints (e.g. `+` on strings suggests `++`); most
improvements came from user reports in a public "error message
catalog" repository. "The Syntax Cliff" (Elm 0.19.1, 2019-10-21):
syntax errors that point to where the parser got stuck, show correct
examples, and link to a page explaining the construct. The Rust team
states its `--explain` style draws "heavy inspiration from the Elm
approach" (Rust blog 2016, re-verified). Strength: EXP/OPN by the
language designer; no measured user outcome is reported in these
posts. Implications: ADOPT a public grmb error-message catalog (a
repo of user-reported confusing findings, each turned into a
conformance test); ADOPT an "outcome-set diff" in non-exhaustive
findings (show only the missing/extra variants, the type-diff analogue);
ADOPT example-plus-link syntax errors for the grmb parser; ADOPT JSON
findings output (frob already has `--json`).

### 2.5 Names: identifiers vs strings, shadowing, labeled blocks

F-24. Zig forbids shadowing: "Variables are never allowed to shadow
Identifiers from an outer scope" (DOC). grmb already has MDL015
(Advisory) for entity shadowing across levels; the Zig precedent supports
promoting it to Warn for the new scenario/step names only if refactoring
cost stays low (see A-05).

F-25. Labeled blocks/break-with-value (Zig) have no planning-layer
counterpart; `retry STEP max N` and `handle { ... }` are the grmb
analogues. No evidence either way for user pain in this run; not pursued.
Strength: none; listed for completeness (gap, not finding).

## 3. Predicted annoyances in .grmb and mitigations

Each: the prediction, the evidence basis (finding numbers), what grimble
could check, and a concrete mitigation tagged ADOPT/ADAPT/REJECT.

### A-01 Verbosity of exhaustive handling (every `=>` and `handle` must list all variants)

- Basis: F-01, F-02, F-05, F-06; CD diffuseness; F-15.
- Prediction: a scenario with 6 steps each returning 3 variants yields a
  long arm list that is mostly `-> end err(x)` boilerplate; authors will
  reach for `_` which the planning brief already Warns on.
- Mitigations:
  1. ADOPT `-|>` collection (already designed): the common case is zero
     arms written. Measure it: a lint (L-ERG-03) that fires when a
     scenario writes more than N identical terminal arms, suggesting `-|>`
     plus one `handle`.
  2. ADAPT Swift: add an `unknown` catch-all arm form (not `_`). It is
     clean when every known variant is also listed, but the instant a new
     variant is not listed, the arm swallows it AND a finding is raised
     naming the variant and the sites (F-03). `_` stays as the Warn form
     the brief decided. Reason: this keeps design-change propagation
     (the whole point of the layer) without forcing an edit in every
     scenario in the same commit.
  3. ADOPT inference: derive each step's outcome set from the arms and
     `fails with` clauses already written; `step x -> { ... }` becomes
     optional documentation and a checked declaration only when present
     (Roc/Zig). Checkable: declared set vs inferred set mismatch (L-ERG-06).
  4. ADOPT "default policy per actor kind" in the pack: e.g. a `human`
     actor's `timeout` defaults to `retry max 3 then end err(timeout)`
     unless overridden; defaults are printed by `grimble fmt --expand` and
     LSP inlay hints, never silently hidden.

### A-02 String vs identifier names (the mockup used kebab strings)

- Basis: F-15 (some symbols, e.g. `==`, are error-prone for first-time
  writers; equally some keywords are; see the 2026-10-09 revision),
  F-24, grmb-spec 2.7.
- Prediction: PMs and designers will write `"place order"` or
  `place-order`, get MDL000, and perceive the rule as pedantry; they also
  rename titles often, which as an identifier rename breaks bindings
  (spec 5.5 `renamed_from`).
- Mitigations:
  1. ADOPT the identifier rule (it protects refactoring and U identity)
     and ADD an LSP `quickfix`: "convert `place-order` to
     `place_order title "place order"`" (F-09 Applicability
     MachineApplicable analogue). The error text states the rule once and
     the fix, not the rule alone (F-09 style guide).
  2. ADOPT mandatory-optional `title "..."` (planning brief 3) for the
     human label; reports (mermaid, status) show the title, never the
     ident, when present. Lint L-ERG-02 flags a missing title only in
     entities that appear in rendered output, as Advisory.
  3. ADAPT: accept ident-with-hyphen as a lexical alias? REJECT. It would
     create two spellings of one name and break "one obvious way" (F-23)
     and the fmt fixed point (spec 9.3).

### A-03 Ceremony for small models

- Basis: F-21 (PlusCal front end), F-22 (TOML/KDL minimal), F-23, CD
  diffuseness, premature commitment.
- Prediction: to model a 3-step script you must declare `system`, an
  `actor`, a `goal`, a `step` list, a `scenario` and an `impl`, plus
  version header and root registration (spec 3.1, 3.4) before getting a
  single useful finding. Small teams will abandon.
- Mitigations:
  1. ADOPT progressive disclosure by level: each level is optional; a
     file with only a `scenario` and inline steps must parse, with the
     missing `system`/`actor`/`goal` synthesised as holes that produce
     Advisory "unrealized goal" obligations, not Errors. (Hazel F-20,
     CD progressive evaluation.)
  2. ADOPT inline step declaration: a step used in a scenario without a
     prior `step` line is declared implicitly with outcome `{ ok }`
     (checked by L-ERG-01 if the arms say otherwise). `grimble fmt`
     hoists nothing; an LSP action "declare step with outcomes from arms"
     writes the line.
  3. ADOPT `grimble new scenario NAME` scaffolds and a single-file
     "sketch" mode (one root, no pack, no header needed beyond a default
     version) with an edition-style upgrade (F-11): `grimble fix` adds the
     header and registrations. This is the PlusCal move: a thin front end
     over the strict core.
  4. ADAPT: zero-ceremony defaults for the root and version header when
     there is exactly one `.grmb` file (spec 3.1/3.4 currently require a
     declared entry). Needs an owner decision on MDL007/MDL021 behaviour;
     recorded as a question, not decided here.

### A-04 Refactor cost when a variant is added

- Basis: F-02, F-03, F-04, CD viscosity (knock-on, repetition).
- Prediction: adding `declined(Fraud)` to `enters_payment` yields one
  Error per handling scenario in one run; in a 40-scenario model that is
  a wall of findings the author did not ask to resolve now.
- Mitigations:
  1. ADOPT grouping: one root cause, one finding with a site list (the
     spec already does this for MDL005/SYS001). The finding id is keyed
     on (step, variant) so frob can turn it into one ticket with the
     sites as scope (planning brief 6).
  2. ADOPT bulk quick-fix: "add arm `fraud -> todo` to all N sites" as
     an LSP `quickfix` and `grimble fix --rule NEW-VARIANT`
     (MachineApplicable when the target is `todo`, MaybeIncorrect
     otherwise, F-09).
  3. ADOPT `todo` as a typed-hole arm body: parses, counts as an
     obligation (Advisory, escalating to Warn after an `until` date
     reusing the exception mechanism, spec 7), never silently passes.
  4. ADOPT open/closed variant sets (F-04): outcomes owned by an external
     actor of kind `system` may be declared `open`; consumers then need
     an `unknown` arm (A-01) and a new variant is Advisory, not Error.
     Closed (default for owned steps) stays Error.
  5. ADOPT lint-level control per family (Rust allow/warn/deny/forbid,
     verified in the lint-levels doc) so a team can stage the new variant
     finding as warn during a migration and deny afterwards.

### A-05 Merge conflicts on shared files

- Basis: spec 3.3 (set union + additive `extend`), 9.3 (canonical order,
  sorts list clauses), Accioly et al. EMSE 2017 (metadata only; the
  concept that line-based merge conflicts concentrate in structured
  edits is background, not verified here), Apel et al. FSE 2011
  semistructured merge (metadata).
- Prediction: scenarios are one tall block with ordered steps and arms;
  two people adding arms to `checkout` conflict textually even when the
  edits commute; `fmt` sorting list clauses moves lines and produces diff
  noise (spec 9.3 item 3) which makes it worse; a single goals file
  becomes a hot spot.
- Mitigations:
  1. ADOPT one-construct-per-file convention encouraged by `grimble new`
     and a lint (L-ERG-08) that warns when a file holds more than K
     scenarios or K lines; the spec's order independence already allows
     the split.
  2. ADAPT: `impl` and arms as `extend`-style additive clauses so that a
     second author adds an `impl` in a new file instead of editing the
     scenario (the spec already has `extend`, 4.9). Needs a check that
     `extend impl` does not alter ordered scenario flow.
  3. ADOPT one arm per line, trailing separators, and no alignment
     padding in `fmt` output (git's line-based merge works at line
     granularity; this is DOC-level reasoning, not an empirical claim).
     Sorting applies only to unordered clauses; step sequences and arm
     lists keep source order (arms are keyed by variant name, so sort by
     variant is safe and gives stable append positions; step sequences
     must never be sorted).
  4. ADOPT a merge driver that parses U and unions facets
     (`grimble merge-driver`); out of scope for grmb syntax, but the
     canonical stream (spec 9) is what makes it possible. REJECT inventing
     a structured diff format.

### A-06 Error noise on incomplete models

- Basis: F-07, F-10, F-20, CD progressive evaluation and premature
  commitment, spec 11 preamble ("a rule whose subject sits inside a
  `hole` or an `opaque` reports one Unresolved ... instead of an Error").
- Prediction: while a designer sketches, a missing actor produces
  "unknown actor", "first step not an actor step", "unreachable step"
  and "path never terminates" for the same scenario: four findings for
  one gap, drowning the real one. This is the "cascading error" failure
  every compiler fights.
- Mitigations:
  1. ADOPT cascade suppression: a scenario that contains an unresolved
     reference reports ONE Unresolved for that scenario and suppresses
     downstream reachability/termination rules for it (extends the
     existing hole rule in spec 11 to unresolved refs, MDL006).
  2. ADOPT severity staging by maturity: new constructs start at
     `status draft` (inline attribute, defaulting to draft), where
     obligations are Advisory; flipping to `status ready` escalates to
     the strict table. Cognitive-dimensions rationale: lets the user work
     in any order (premature commitment) while keeping the final bar.
  3. ADOPT "explain" on every finding: a stable id plus
     `grimble explain MDLnnn` long form (rustc `--explain`, F-09), and
     labels that point at the code/model span the author wrote, with fix
     text in a separate help line.
  4. ADOPT precision discipline: each new rule ships with a measured
     false-positive budget on the repo's own models (Tricorder practice,
     F-10; Wrenn "classifier" framing, F-08). A rule over the budget
     defaults to Advisory.
  5. ADOPT incompleteness labelling (Crichton, F-14): findings produced
     because grimble cannot see something (selector resolves to
     `opaque`) are Unresolved, never Error, so users can tell "model
     wrong" from "tool blind".

### A-07 Learning curve for non-programmers (PMs, designers)

- Basis: F-15, F-16, F-17, F-18, F-21, CD closeness of mapping and
  role-expressiveness.
- Prediction: `goal`/`actor`/`scenario` read well; `->`, `=>`, `-|>`,
  `-?>` and `handle` do not. PMs will write scenarios but not the
  right-hand arms; designers will want diagrams, not text; embedded
  engineers will want `isr`/`device` steps first. The operator zoo is the
  most likely adoption failure point.
- Mitigations:
  1. [REVISED 2026-10-09; the original text recommended keyword
     canonical with symbolic input sugar, citing F-15 as "evidence
     leans keyword". The verified paper does not support that: it
     measured first-time writers, did not test arrow operators, and
     found English keywords such as `then`/`end` as error-prone as
     `==`.] New recommendation: keep ONE spelling per operator with no
     alias dialect in R1 (the brief's symbolic forms are acceptable;
     nothing in the evidence prefers either); serve non-programmers
     through the prose/diagram renderer (mitigation 2), where they
     read rather than write; and put the concrete operator tokens into
     the think-aloud study (mitigation 4), scoring per-token accuracy
     the way Stefik & Siebert did. Revisit keyword spellings only if
     that study shows specific symbols failing. Still an owner
     decision; the evidence is now neutral, not keyword-leaning.
  2. ADOPT two reading levels (F-21): `grimble show --prose scenario
     checkout` renders to numbered English steps and a mermaid sequence
     diagram (planning brief 7), so PMs review prose and diagrams while
     engineers edit text. The rendering is derived from U, so the review
     artefact cannot drift.
  3. ADOPT quick-fix-first diagnostics (F-09, F-10): a non-exhaustive
     match offers "add missing arms" with `todo` bodies (A-04), so a PM
     never has to author syntax from scratch.
  4. ADOPT a 10-line "first scenario" tutorial and a think-aloud study
     (3 PMs, 3 designers, 3 embedded engineers) before freezing the
     grammar (F-18). Success metric: unaided author of a 3-step scenario
     with one failure branch in under 15 minutes; failures logged as
     candidate lint ids. Newcombe reports 2-3 weeks to useful results for
     TLA+; grmb should beat that by an order of magnitude because it has
     no logic to learn.
  5. REJECT a GUI-first/visual editor in R1: CD hidden-dependency and
     viscosity costs of diagram editors, and the model must stay
     text/diffable/mergeable (A-05). Revisit after the prose renderer
     exists.

### A-08 Further predicted annoyances (not in the brief's list)

- A-08a Formatter surprises. If `fmt` reorders anything semantically
  ordered it is a bug; if it reorders anything unordered it is noise.
  Mitigation: golden tests that formatting never changes the U digest
  (spec 9.3 item 2) extended to the new constructs, plus a property test
  that `fmt` leaves arm and step order intact. Source: F-12 (formatter as
  law needs trust).
- A-08b `requires` cycle messages. A `requires` cycle is an MDL error
  with no obvious culprit. Mitigation: report the minimal cycle path with
  one label per edge (rustc multi-span, F-09), and a quick-fix to drop
  the weakest edge is NOT offered (design decision, not mechanical).
- A-08c Edition/version churn. When the grmb grammar evolves, every model
  breaks. Mitigation: the spec's version header (3.4) plus `grimble fix
  --edition` backed by MachineApplicable rewrites (F-11); keep changes
  "skin deep" (all editions lower to the same U), and ship the migration
  with the language change (RFC 2052 principle).
- A-08d Slow feedback. Rust users rank compile time and slow tooling at
  the top (F-14); grmb's `check` over a large repo with selectors could be
  slow. Mitigation: LSP on the model alone (no code walk) gives instant
  MDL feedback; SYS/binding findings are computed asynchronously and
  labelled stale until fresh.

## 4. Implications for grmb (tagged) and candidate lint rules

### 4.1 Grammar, rule and binding consequences

| # | Consequence | Tag | One-line reason |
|---|---|---|---|
| I-01 | `unknown` catch-all arm that stays silent only while all known variants are listed, else raises a propagation finding | ADAPT (Swift) | keeps design-change propagation without forcing same-commit edits (F-03) |
| I-02 | bare `_` arm: Warn (brief) with a quick-fix to `unknown` | ADOPT | Clippy treats wildcard as latent bug (F-02) |
| I-03 | `open` outcome sets for externally owned steps; consumers need `unknown` | ADOPT (RFC 2008) | owner can add variants without breaking consumers (F-04) |
| I-04 | infer outcome sets; declared sets are checked documentation | ADOPT (Zig/Roc) | cuts verbosity (F-05, F-06) |
| I-05 | explicit `fails with` set required at boundaries and recursion | ADOPT (Zig doc) | inferred sets break on recursion/stable interfaces (F-05) |
| I-06 | `todo` arm/step body as a typed hole with defined semantics (Advisory, escalates by `until`) | ADOPT (Hazel) | progressive evaluation (F-20) |
| I-07 | `status draft|ready` per construct gating severity | ADAPT | staged strictness; no direct precedent, CD premature commitment (F-19) |
| I-08 | per-family lint levels allow/warn/deny/forbid | ADOPT (rustc) | teams stage migrations (lint-levels doc) |
| I-09 | one canonical spelling per operator, no alias dialect in R1; token choice decided by the think-aloud study (revised 2026-10-09, was "keyword canonical, symbols input sugar") | ADOPT one spelling / DEFER keyword-vs-symbol | F-15 verified: neither keywords nor symbols are reliably easier; arrows untested |
| I-10 | grouped findings per cause (variant, step), bulk quick-fix | ADOPT | viscosity (F-04 context); spec already groups MDL005/SYS001 |
| I-11 | machine-applicable fixes tagged by applicability; `grimble fix` applies only MachineApplicable | ADOPT (rustc) | safe automation (F-09, F-11) |
| I-12 | `grimble explain RULE` long form for every finding id | ADOPT (rustc) | learning aid (F-09) |
| I-13 | `fmt` must not sort ordered constructs (step sequences); may sort arms by variant | ADOPT | correctness of semantics, merge stability (spec 9.3, A-05) |
| I-14 | optional `title` string, ident names mandatory; hyphenated aliases | ADOPT / REJECT | protects identity and fmt fixed point (A-02) |
| I-15 | sketch mode (single-file, implicit header/root, implicit steps) with `grimble fix` upgrade path | ADAPT | PlusCal-style front end (F-21); needs owner decision on MDL007/MDL021 |
| I-16 | cascade suppression; one Unresolved per unresolved subject | ADOPT | mirrors spec 11 preamble (F-10) |
| I-17 | ban shadowing of step/scenario names (error) | REJECT for now | MDL015 Advisory is enough; Zig's ban is language-wide, no grmb pain evidence |
| I-18 | labeled blocks / break-with-value | REJECT | no use case in planning layer (F-25) |
| I-19 | LSP-first: diagnostics, hover (outcome set, bound/verified status), code actions, inlay hints for inferred sets | ADOPT | codeAction is the vehicle for every mitigation (F-13) |
| I-20 | visual editor in R1 | REJECT | text, diff, merge first (A-07) |

### 4.2 Candidate lint rules

Ids are placeholders (ERGnnn); the coordinator assigns the family.
Polarity: P+ fires on presence, P- fires on absence, M on mismatch.

| Id | Anti-pattern prevented | Predicate over model / binding | Polarity | Source |
|---|---|---|---|---|
| ERG001 | step used but never declared, with arms that contradict inferred `{ok}` | step has an implicit outcome set != union of arm variants and `fails with` sets | M | F-05, F-06 |
| ERG002 | missing human label in rendered output | entity is `goal|scenario|step` and appears in a render target and has no `title` | P- (Advisory) | A-02 |
| ERG003 | boilerplate arms instead of `-|>` | scenario has >= 3 `=>` arms whose bodies are only `end err(v)` of the same step family | P+ (Advisory) | A-01 |
| ERG004 | wildcard hides a variant | `_` arm exists on a match whose scrutinee has >= 1 variant not otherwise listed | P+ (Warn) | F-02 (Clippy) |
| ERG005 | `unknown` arm swallowing a new variant | `unknown` arm is the only arm covering variant v | P+ (Warn, names v and sites) | F-03 (Swift) |
| ERG006 | declared vs inferred outcome set drift | declared `step -> {...}` set != set implied by uses | M | F-05 |
| ERG007 | open outcome set matched without `unknown` | step's outcome is `open` and a consumer match has no `unknown` arm | P- | F-04 (RFC 2008) |
| ERG008 | hot-spot files | file contains > K scenarios or > L lines | P+ (Advisory) | A-05 |
| ERG009 | `todo` left past its date | `todo` body present, with `until` passed or no `until` after N days | P+ (Warn after date) | F-20 |
| ERG010 | unresolved-reference cascade | a rule fires on a scenario that already has an Unresolved subject | meta (suppression, not a finding) | A-06 |
| ERG011 | explicit `fails with` missing on a recursive `include` | scenario includes itself transitively and has no explicit `fails with` | P- | F-05 (Zig inferred sets and recursion) |
| ERG012 | variant added with no handler anywhere (propagation) | variant v added to step s since last lock; scenarios that handle s have no arm for v | M (aggregated per v) | F-02, F-04 |
| ERG013 | `fmt` changed ordered construct | `fmt(x)` reorders a step sequence or an ordered arm list (test-time property, not a runtime lint) | M | A-08a, spec 9.3 |
| ERG014 | operator-dialect drift | file mixes keyword and symbolic spellings after `fmt` (should be impossible; a conformance test). Needed only if aliases are ever added (I-09 revised) | M | I-09 |
| ERG015 | binding silently stale after rename | `renamed_from` absent while an `impl` names a step that no longer exists | M | spec 5.5 |

Note: ERG004/ERG005/ERG007/ERG012 realise the brief's single wildcard
Warn as a graduated family; the brief's `_` Warn is kept as ERG004.

## 5. Bibliography and credibility

Format: citation; URL or DOI; fetched? ; credibility line. "Standing" is
given only if the source's own text or byline establishes it.

### 5.1 Peer-reviewed (graded A)

1. Barik, Smith, Lubick, Holmes. "Do Developers Read Compiler Error
   Messages?" ICSE 2017. DOI 10.1109/icse.2017.59. Abstract fetched
   (OpenAlex). Venue: ICSE (A). Standing: academic eye-tracking study,
   56 student participants; no industrial deployment claimed.
2. Wrenn, Krishnamurthi. "Error Messages Are Classifiers: A Process to
   Design and Evaluate Error Messages." Onward! 2017. DOI
   10.1145/3133850.3133862. Abstract fetched. Venue: Onward! (A). Standing:
   academic (Brown PL group; affiliation not re-verified here).
3. Becker, Denny, Pettit, Bouchard et al. "Compiler Error Messages
   Considered Unhelpful: The Landscape of Text-Based Programming Error
   Message Research." ITiCSE-WGR 2019. DOI 10.1145/3344429.3372508.
   Abstract fetched. Venue: ITiCSE working-group report (A-). Standing:
   multi-institution education research; survey, no product.
4. Marceau, Fisler, Krishnamurthi. "Measuring the Effectiveness of Error
   Messages Designed for Novice Programmers." SIGCSE 2011. DOI
   10.1145/1953163.1953308. Metadata only. Venue: SIGCSE (A).
5. Stefik, Siebert. "An Empirical Investigation into Programming
   Language Syntax." ACM TOCE 13(4), Article 19, November 2013, 40 pp.
   DOI 10.1145/2534973. Abstract fetched; 2026-10-09 full text read
   (author copy hosted at
   https://www.vidarholen.net/~vidar/An_Empirical_Investigation_into_Programming_Language_Syntax.pdf ,
   matching the ACM DOI and pagination; the ACM page returned 403).
   Venue: TOCE (A). Standing: academic (UNLV); Stefik designed Quorum,
   one of the languages compared, which is a potential conflict of
   interest the paper does not hide. N = 18 and 72 never-programmed
   students; writing tasks only.
6. Pane, Ratanamahatana, Myers. "Studying the language and structure in
   non-programmers' solutions to programming problems." IJHCS 2001. DOI
   10.1006/ijhc.2000.0410. Metadata only; findings unread. Venue: IJHCS
   (A). Standing: Myers directs CMU HCI research (not source-verified).
7. Coblenz, Aldrich, Myers, Sunshine. "Can advanced type systems be
   usable? An empirical study of ownership, assets, and typestate in
   Obsidian." PACMPL (OOPSLA) 2020. DOI 10.1145/3428200. Abstract fetched.
   Venue: OOPSLA (A). Standing: academic; N = 20.
8. Myers, Stefik, Hanenberg, Kaijanaho. "Usability of Programming
   Languages." CHI 2016 Extended Abstracts (SIG). DOI 10.1145/2851581.
   2886434. Abstract fetched. Venue: CHI EA (A-, short). Standing:
   academic.
9. Myers, Ko, LaToza, Yoon. "Programmers Are Users Too: Human-Centered
   Methods for Improving Programming Tools." IEEE Computer 2016. DOI
   10.1109/mc.2016.200. Abstract fetched. Venue: IEEE Computer (A-).
10. Zhu, Zhang, Qin, Xiong et al. "Learning and Programming Challenges
    of Rust: A Mixed-Methods Study." ICSE 2022. DOI
    10.1145/3510003.3510164. Abstract truncated (first lines only).
    Venue: ICSE (A). Findings beyond the motivation were not read; used
    only as the pointer for Rust learning difficulty.
11. Johnson, Song, Murphy-Hill, Bowdidge. "Why Don't Software Developers
    Use Static Analysis Tools to Find Bugs?" ICSE 2013. DOI
    10.1109/icse.2013.6606613. Abstract fetched. Venue: ICSE (A).
    Standing: 20 developer interviews; authors include Bowdidge (Google
    at the time of publication is not source-verified here).
12. Sadowski, Van Gogh, Jaspan, Soderberg, et al. "Tricorder: Building a
    Program Analysis Ecosystem." ICSE 2015. DOI 10.1109/icse.2015.76.
    Abstract fetched. Venue: ICSE (A). Standing: Google engineers
    describing a Google-wide system; byline and abstract ("used by
    developers across Google").
13. Sadowski, Aftandilian, Eagle, Miller-Cushon, Jaspan. "Lessons from
    Building Static Analysis Tools at Google." CACM 61(4), 2018. DOI
    10.1145/3188720. One-line abstract fetched; body not read. Venue:
    CACM (A). Standing: Google tool authors (byline).
14. Omar, Voysey, Chugh, Hammer. "Live Functional Programming with
    Typed Holes." POPL 2019 (PACMPL 3). DOI 10.1145/3290327. Abstract
    fetched. Venue: POPL (A). Standing: academic PL (Michigan group;
    affiliation not re-verified).
15. Newcombe, Rath, Zhang, Munteanu, Brooker, Deardeuff. "How Amazon
    Web Services Uses Formal Methods." CACM 58(4), 2015. DOI
    10.1145/2699417. Full text fetched (PDF via lamport.azurewebsites.net/
    tla/formal-methods-amazon.pdf). Venue: CACM (A). Standing: AWS
    engineers; text names Principal engineers and "7 teams using TLA+".
16. Maranget. "Warnings for Pattern Matching." J. Functional
    Programming 17(3), 2007. DOI 10.1017/s0956796807006223. Metadata only.
    Venue: JFP (A).
17. Green, Petre. "Usability Analysis of Visual Programming
    Environments: A 'Cognitive Dimensions' Framework." J. Visual
    Languages & Computing 7(2), 1996. DOI 10.1006/jvlc.1996.0009.
    Metadata only (paper page 403). Venue: JVLC (A). Standing: Green
    (Cambridge MRC APU) and Petre (Open University), academics. Used for
    dimension NAMES only; definitions are from item 29.
    [2026-10-09: definitions now from item 29a, not item 29. Pages
    131-174 per the search index; the paper body is still unread.]
18. Accioly, Borba, Cavalcanti. "Understanding semi-structured merge
    conflict characteristics in open-source Java projects." Empirical
    Software Engineering 2017. DOI 10.1007/s10664-017-9586-1. Metadata
    only, abstract unavailable; not relied on for any claim.
19. Apel, Liebig, Brandl, Lengauer. "Semistructured Merge: Rethinking
    Merge in Revision Control Systems." ESEC/FSE 2011. DOI
    10.1145/2025113.2025141. Metadata only; not relied on for any claim.
20. Cherubini, Venolia, DeLine, Ko. "Let's Go to the Whiteboard: How and
    Why Software Developers Use Drawings." CHI 2007. DOI
    10.1145/1240624.1240714. Metadata only; pointer to topic D.

### 5.2 Official language and vendor documentation (graded B, DOC)

21. Rust Project. "Announcing the 2024 State of Rust Survey Results."
    https://blog.rust-lang.org/2025/02/13/2024-State-Of-Rust-Survey-
    results/ . Fetched. Self-selected survey of Rust users (weak
    representativeness, official source).
22. Rust Project. "Shape of errors to come" (S. J. Turner, 2016-08-10).
    https://blog.rust-lang.org/2016/08/10/Shape-of-errors-to-come/ .
    Fetched.
23. Rust Project. rustc-dev-guide, "Diagnostics" and "Error codes".
    https://rustc-dev-guide.rust-lang.org/diagnostics.html and
    .../diagnostics/error-codes.html . Fetched.
24. Rust RFC 2008 non_exhaustive.
    https://rust-lang.github.io/rfcs/2008-non-exhaustive.html . Fetched.
25. Rust RFC 2052 epochs/editions and Edition Guide.
    https://rust-lang.github.io/rfcs/2052-epochs.html ;
    https://doc.rust-lang.org/edition-guide/editions/index.html . Fetched.
26. The Rust Book ch. 6.2 "match" and rustc lint levels doc.
    https://doc.rust-lang.org/book/ch06-02-match.html ;
    https://doc.rust-lang.org/rustc/lints/levels.html . Fetched.
27. Rust Clippy lint index (wildcard_enum_match_arm,
    match_wildcard_for_single_variants).
    https://rust-lang.github.io/rust-clippy/master/index.html . Fetched.
28. Zig Software Foundation. Zig Language Reference (master): error
    sets, inferred error sets, try, shadowing.
    https://ziglang.org/documentation/master/ . Fetched.
29. [WITHDRAWN 2026-10-09] Wikipedia, "Cognitive dimensions of
    notations". Replaced by 29a; no claim rests on it any longer.
29a. Green, T. R. G., Blackwell, A. F. "Cognitive Dimensions of
    Information Artefacts: a tutorial." Version 1.2, October 1998
    (prepared for the BCS HCI Conference 1998).
    https://www.cl.cam.ac.uk/~afb21/CognitiveDimensions/CDtutorial.pdf .
    Fetched and read 2026-10-09 (75 pages; summary table and viscosity
    chapter quoted in F-19). Venue: tutorial by the framework's authors,
    hosted on Blackwell's University of Cambridge page (primary, not
    peer reviewed). Standing: Green co-authored the framework (ex-APU
    Cambridge, then Leeds, per the author note); Blackwell, Cambridge.
    Grade A for definitions (authoritative primary).
30. Swift Evolution SE-0192 "Handling Future Enum Cases".
    https://github.com/swiftlang/swift-evolution/blob/main/proposals/
    0192-non-exhaustive-enums.md . Fetched.
31. JetBrains. Kotlin docs, "Sealed classes and interfaces".
    https://kotlinlang.org/docs/sealed-classes.html . Fetched.
32. Gleam. Language tour, case expressions.
    https://tour.gleam.run/everything/ . Fetched.
33. Roc. FAQ. https://www.roc-lang.org/faq . Fetched.
34. Microsoft. TypeScript Handbook, Narrowing (the `never` type).
    https://www.typescriptlang.org/docs/handbook/2/narrowing.html .
    Fetched.
35. Go Team. "go fmt your code" (gofmt blog).
    https://go.dev/blog/gofmt . Fetched. "Go at Google: Language Design
    in the Service of Software Engineering" (Pike).
    https://go.dev/talks/2012/splash.article . Fetched (not directly
    quoted; supports the "simplicity as a design goal at Google scale"
    background; Pike is a Go co-designer at Google per the article).
36. Go Team. "Go Developer Survey 2024 H2 Results."
    https://go.dev/blog/survey2024-h2-results . Fetched. Self-selected.
    (2026-10-09: author Alice Merrick, 2024-12-20, 4,156 responses.)
37. Stack Overflow. 2024 Developer Survey, Technology.
    https://survey.stackoverflow.co/2024/technology . Fetched. Self-
    selected; used only for "Rust most admired".
38. Python. PEP 20 (Zen of Python) and PEP 8.
    https://peps.python.org/pep-0020/ ;
    https://www.python.org/dev/peps/pep-0008/ . Fetched.
39. Microsoft. Language Server Protocol 3.17 specification.
    https://microsoft.github.io/language-server-protocol/specifications/
    lsp/3.17/specification/ . Fetched.
40. Config-language documents (all fetched): Dhall
    https://docs.dhall-lang.org/discussions/Safety-guarantees.html ;
    CUE https://cuelang.org/docs/concept/the-logic-of-cue/ ;
    Starlark https://github.com/bazelbuild/starlark/blob/master/design.md ;
    HCL https://github.com/hashicorp/hcl/blob/main/README.md ;
    Nix language https://nix.dev/manual/nix/latest/language/ ;
    KDL https://kdl.dev/ ; TOML https://toml.io/en/ ;
    Pkl https://pkl-lang.org/main/current/introduction/index.html
    (nav-only page, no claim rests on it).

43. Czaplicki, E. "Compiler Errors for Humans" (2015-06-30);
    "Compilers as Assistants" (2015-11-19); "The Syntax Cliff"
    (2019-10-21). Elm blog, https://elm-lang.org/news/compiler-errors-for-humans ,
    .../compilers-as-assistants , .../the-syntax-cliff ; read 2026-10-09
    from the page sources at
    https://github.com/elm/elm-lang.org/tree/master/pages/news
    (author and date are in each file's metadata). Official project
    blog by the language designer (DOC/EXP); no user outcome measured.
44. Rust Survey Team. "2025 State of Rust Survey Results" (2026-03-02).
    https://blog.rust-lang.org/2026/03/02/2025-State-Of-Rust-Survey-results .
    Fetched 2026-10-09. Self-selected, 7,156 responses.
45. Kulesza, T. (Go team). "Results from the 2025 Go Developer Survey"
    (2026-01-21). https://go.dev/blog/survey2025 . Fetched 2026-10-09.
    Self-selected, 5,379 responses.

### 5.3 Weaker (graded C, flagged)

41. Crichton, W. "The Usability of Ownership." HATRA @ SPLASH 2020.
    arXiv:2011.06171, https://doi.org/10.48550/arXiv.2011.06171 .
    Abstract fetched. Workshop paper, single author, "drawing on my
    experience with using and teaching Rust". OPN/EXP, no controlled
    study.
42. Self-selected surveys (items 21, 36, 37) are cited as DOC for what
    they report, never as evidence of effect sizes.

## 6. Coverage verdict

- Denominator: 6 sub-fields x the named language/venue list in the
  brief. Languages named in the brief: Rust, Zig, Elm, Gleam, Roc,
  Kotlin, Swift, TypeScript, Go, Python, Nix, Dhall, CUE, HCL, Starlark,
  Pkl, KDL, TOML = 18. Read: 17 (Elm unreadable, see 1.3; Pkl page
  nav-only so counts as listed, not read). Surveys named: Rust, Stack
  Overflow, Go = 3 of 3 read. Venues named: PLATEAU, CHI, OOPSLA, Onward,
  Cognitive Dimensions: Onward (2), OOPSLA (1), CHI (2 short items),
  CD (metadata), PLATEAU not directly reached (EVALUATE/PLATEAU
  workshop papers surfaced only as proceedings metadata).
- Pending/blocked: none silently dropped. Blocked: Elm primary pages
  (JS-only), Green & Petre full text (403), Pkl body (nav-only), arXiv
  API (timeout), WebSearch/WebFetch (tool not offered). Unread-but-
  relevant: Zhu et al. body, Pane et al. body, PLATEAU papers, Rust
  survey raw data. None of these would reverse a recommendation in
  section 4 because each recommendation rests on a verified mechanism
  document or an A-grade study; they could change magnitudes (for
  example, the N in ERG003/ERG008) and the choice in I-09.
- Weak points to report: A-05 (merge conflicts) rests on reasoning from
  the spec plus metadata-only citations, so it is the least evidenced
  prediction; I-07 (`status draft|ready`) has no direct precedent;
  I-09 (keyword vs symbol) rests on one novice study (Stefik) and is a
  recommendation for owner decision.

## 7. Verification pass (2026-10-09)

Done by a second agent with WebSearch/WebFetch available (the original
run had none). Every citation the coordinator flagged, and every
metadata/abstract-only or secondary source that a finding relied on,
was re-checked against a primary text. Changes, by kind:

Fixed (re-verified; wording corrected in place):
- F-03 Swift SE-0192: quotes re-verified; "too aggressive" corrected to
  the proposal's "a little too aggressive" under "Post-acceptance
  revision"; status "Implemented (Swift 5.0)" added.
- F-04 Rust RFC 2008: quotes re-verified; added that the attribute is
  "essentially ignored" inside the defining crate, which refines I-03
  (`open` relaxes only matches outside the owner).
- F-12 Go 2024 H2 survey: "58% of those asked" corrected to 58% of
  respondents, tied with performance diagnosis; the post gives no n for
  that chart; author, date and total responses added.
- F-14 Rust 2024 survey: figures re-verified (9,450 started, 7,310
  completed).
- F-19 Cognitive Dimensions: Wikipedia definitions replaced by
  quotations from Green and Blackwell's own tutorial (v1.2, 1998), read
  in full; bibliography item 29 withdrawn, 29a added; item 17 notes
  that the JVLC paper body is still unread.
- 1.3 exclusions: the Elm and CD-tutorial blocks are marked resolved.

Downgraded:
- F-15 Stefik & Siebert: full text read. The study measured writing
  accuracy of never-programmed students (N = 18 and 72) on six small
  tasks in six languages, scored per component; arrow operators were not
  tested; English keywords `then`/`end` were among the least accurate
  tokens and the authors say extra English-like words "do not
  necessarily benefit novices". The original implication ("keyword
  forms read better to novices") is withdrawn as unsupported.
- A-02 basis wording narrowed accordingly.

Flipped recommendation:
- I-09 / A-07 mitigation 1 (keyword vs symbol operators). Was: keyword
  spelling canonical, symbols as input sugar, "evidence leans keyword".
  Now: one spelling per operator and no alias dialect in R1; the
  keyword-vs-symbol choice is DEFERRED to the think-aloud study
  (A-07.4) with per-token accuracy scoring; non-programmers are served
  by the prose/diagram renderer. Rationale: the only cited evidence is
  neutral on this question. ERG014 becomes conditional on aliases ever
  being added.

Added:
- F-26 Elm error-message work (three posts by Czaplicki, 2015-2019,
  read from the elm/elm-lang.org repository sources), with four
  ADOPT implications: public error-message catalog feeding conformance
  tests, outcome-set diffs in non-exhaustive findings, example-plus-
  link parser errors, JSON findings output. Graded EXP/OPN (no
  measured outcomes).
- F-12: 2025 Go survey (best practices/idioms reported by 33%).
- F-14: 2025 Rust survey; respondents found `--explain` useful,
  contrary to the team's prior assumption, which supports I-12
  (`grimble explain`).
- Bibliography items 29a, 43, 44, 45; item 5 expanded with method,
  N, and the authors' stake in Quorum.

Removed:
- Wikipedia (item 29) as a source for any claim.

Not done / still open:
- Green & Petre 1996 body (JVLC; publisher page 403); the definitions
  no longer depend on it.
- Pane et al 2001, Zhu et al 2022 bodies, PLATEAU papers: not in this
  pass's remit; no recommendation rests on them.

Revised coverage verdict: all 18 brief-named languages are now covered
(Elm read via repository sources; Pkl remains nav-only, no claim on
it). All three named surveys are read, plus the newer 2025 Rust and Go
editions. Cognitive Dimensions definitions are now primary. The weakest
remaining points are A-05 (merge conflicts, reasoning plus metadata
only) and I-07 (`status draft|ready`, no direct precedent). I-09 is no
longer a recommendation backed by evidence; it is an explicit open
question with a specified test. No other recommendation in section 4
changed direction.
