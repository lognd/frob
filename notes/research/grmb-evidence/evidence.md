# grmb evidence record

The one durable evidence record for the .grmb language design
(docs/design/grmb-spec.md). Every design change made by the audit/fix
cycles of ticket ~MHGA5VN cites rows of this file, and every such change
has a decision in docs/decisions/decisions.toml that names the rows. The
per-cycle log is [cycles.md](cycles.md).

Rules of this file:

- A row in section 1 was fetched and read (gh api, clone, curl) in the
  review of 2026-10-31 against commit 577c8e00c2. The "Author" column says
  why the source counts: a language or tool designer, a standards body or
  a team with several large shipped projects.
- A source that was not fetched or could not be read is listed in section
  3 and is never used as support.
- "Q" tags the question the row bears on: (a) one spelling per meaning,
  (b) contextual vs reserved words, (c) stories, flows and the V-model in
  one model, (d) status, rollup and coverage, (e) fallible and error
  edges, (p) pipelines and placeholders.
- Corpus counts (rows U1-U4) are measurements of this repository, not
  outside evidence; they count as usage data only.

## 1. Verified sources

| Id | Source (locator) | Author / why it counts | Finding (short quote or figure) | Date | Q |
|---|---|---|---|---|---|
| E01 | rust-lang/rfcs PR #243, text/0243-trait-based-exception-handling.md | glaebhoerl; merged by Rust lang team (Matsakis et al.) | "Requiring an explicit `?` operator ... lets the reader determine at a glance where an exception may" occur; 592 comments | 2014-09 to 2016-02 | e, a |
| E02 | rust-lang/rfcs PR #2388, 2388-try-expr.md | Centril; Rust lang team | Reserves `try` in edition 2018. "Whatever keyword is chosen, it can't be contextual": `<word> { .. }` collides with a struct named `<word>` | 2018-04/05 | b |
| E03 | rust-lang/rfcs PR #2052, 2052-epochs.md | Aaron Turon (Rust core team) | New keywords are "the only kind of *breaking* change" an edition can make; `catch` "cannot be added even as a contextual keyword without potential breakage" | 2017-07/09 | b |
| E04 | rust-lang/rfcs PR #2151, 2151-raw-identifiers.md | Josh Stone; Rust lang team | `r#ident` escape so code written before a keyword was reserved keeps working | 2017-09 to 2018-02 | b |
| E05 | rust-lang/rfcs PR #2008, 2008-non-exhaustive.md | clarfonthey; merged by lang team | `#[non_exhaustive]` "will force downstream crates to add a wildcard arm ... ensuring that adding new variants is not a breaking change" | 2017-05/08 | e, d |
| E06 | rust-lang/rust issue #89554 | Rust lang team tracking issue | `non_exhaustive_omitted_patterns` lint (warn when a known variant falls only into `_`) still unstable, open since 2021-10 | 2021 to now | e |
| E07 | rust-lang/rust #57640 (512 comments); boats.gitlab.io "A final proposal for await syntax" | withoutboats (Rust lang team, async design lead) | Postfix `.await` chosen: "The primary argument in favor of postfix was its better composability with methods and the ? operator" | 2019-01 to 2019-05-06 | p, a |
| E08 | golang/go #32437 "A built-in Go error check function, try" | Robert Griesemer (Go co-designer, V8, HotSpot) | Declined ahead of schedule; 816 comments, 353 up / 823 down; missed "implications for adding debugging prints and analyzing code coverage" | 2019-06/07 | e |
| E09 | golang/go #71203 "reduce error handling boilerplate using ?" | Ian Lance Taylor (Go team, gccgo, gold) | Declined; 252 comments, 236 up / 500 down | 2025-01 | e |
| E10 | go.dev/blog/error-syntax "[ On \| No ] syntactic support for error handling" | Robert Griesemer | "For the foreseeable future, the Go team will stop pursuing syntactic language changes for error handling"; "None of the error handling proposals reached anything close to a consensus" | 2025-06-03 | e |
| E11 | go.dev/blog/errors-are-values | Rob Pike (Go, Plan 9, UTF-8) | "Errors are values. Values can be programmed" | 2015-01-12 | e |
| E12 | swiftlang/swift docs/ErrorHandlingRationale.md (first commit 229df4d230) | John McCall (Swift/Clang compiler lead) | "marked propagation" = something at the call site; "unmarked propagation ... makes it impossible to directly see what operations can produce errors"; error kinds: simple domain, recoverable, universal, logic failure | 2015-04 | e |
| E13 | swift-evolution SE-0413 typed throws (Swift 6.0) | Doug Gregor (Swift generics, C++ concepts/variadic templates) et al. | Errors "are generally propagated and rendered, but rarely handled exhaustively, and are prone to changing over time"; typed throws only where "the set of potential failure conditions must be relatively fixed" | 2023/24 | e |
| E14 | joeduffyblog.com/2016/02/07/the-error-model | Joe Duffy (Midori OS lead, .NET TPL/PLINQ) | "Bugs Aren't Recoverable Errors!" Abandonment for bugs, checked exceptions for recoverable errors; Java critique: "there is no indication at callsites what calls might throw" | 2016-02-07 | e |
| E15 | ziglang.org/documentation/0.14.0 "Error Set Type", "Inferred Error Sets" | Andrew Kelley (Zig) | Same error name declared twice "gets assigned the same integer value"; `A \|\| B` merges sets; inferred sets "are incompatible with recursion" | 0.14.0 | e |
| E16 | ziglang/zig src/main.zig `info_zen` | Andrew Kelley | "Only one obvious way to do things." "Favor reading code over writing code." "Compile errors are better than runtime crashes." | current | a |
| E17 | python/peps pep-0020 | Tim Peters (CPython core, Timsort) | "There should be one-- and preferably only one --obvious way to do it." | 2004 | a |
| E18 | JetBrains/kotlin-web-site docs/topics/keyword-reference.md | Kotlin team (JetBrains) | Three keyword classes: hard ("cannot be used as identifiers"), soft ("act as keywords in the context in which they are applicable"), modifier | current | b |
| E19 | dotnet/csharplang proposals/csharp-14.0/field-keyword.md; issue #140 (425 comments) | C# LDM (Hejlsberg's language team) | "The existence of the `field` contextual keyword within property accessor bodies is a potentially breaking change"; escape is `@field`; scope narrowed to primary expressions to shrink the break | 2017 to 2024 | b |
| E20 | python/peps pep-0622 / pep-0634 | Guido van Rossum, Brandt Bucher et al. | `match`/`case` are soft keywords "(and stay!)" because `match` is a popular name; cost: "third-party parsers which are not 'PEG-compatible' will have a hard time" | 2020 | b |
| E21 | open-std.org WG21 P0056R0 "Soft Keywords"; cppreference keyword list | Gor Nishanov (C++ coroutines lead, Microsoft) | `await, concept, requires, module ...` "are used as names" in real code; C++20 shipped `co_await` as hard keywords while `module`, `import`, `override`, `final`, C++26 `pre`/`post` are "identifiers with special meaning" | 2015-09; current | b |
| E22 | cucumber/gherkin commit 0a6f11d0 (#416); CHANGELOG 6.0; gherkin.berp; gherkin-languages.json | Aslak Hellesoy (Cucumber creator) | `Rule` added to align with Example Mapping, "the first major change to the Gherkin grammar in 8 years"; grammar `Feature := ... ScenarioDefinition* Rule*`; English synonyms: scenario = `Example`/`Scenario`, feature = `Feature`/`Business Need`/`Ability`, steps accept `*` | 2018-06 | c, a |
| E23 | dannorth.net/blog/introducing-bdd | Dan North (BDD originator, JBehave) | Story "Customer withdraws cash" has several scenarios: in credit, overdrawn within limit, overdrawn past limit. Each is a separate Given/When/Then path; "Both scenarios are based on the same event" | 2006-09-20 | c |
| E24 | Systems-Modeling/SysML-v2-Pilot-Implementation @a9676a3, SysML.xtext | OMG SysML v2 submission team (reference implementation) | One keyword per trace relation: `satisfy`, `verify`, `allocate`, `include` (use case), `then`/`succession`, `flow`, `message`; `refine`/`derive`/`trace` are not grammar keywords (generic `dependency`); about 137 reserved words, escaped by `'quoted names'` (UNRESTRICTED_NAME) | 2026-10-28 head | a, b, c |
| E25 | same repo, sysml.library/Systems Library/VerificationCases.sysml | as 24 | `enum def VerdictKind { pass; fail; inconclusive; error; }` | current | d |
| E26 | structurizr/structurizr.github.io dsl/71-language.md, dsl/07-implied-relationships.md; structurizr/structurizr DynamicView.java L230 | Simon Brown (U4 model) | One relationship arrow `->`; dynamic views show "_instances_ of relationships that are defined in the static model"; code throws "A relationship between X and Y does not exist in model."; implied relationships created by default | current | c, a |
| E27 | mermaid-js/mermaid docs syntax/flowchart.md; issue #1444 | Mermaid maintainers (Knut Sveidqvist) | "Typing 'end' in all lowercase letters will break the Flowchart"; "A---oB" lexes as a circle edge; about ten arrow spellings (`-->`, `-.->`, `==>`, `--o`, `--x`, ...) | 2020-06; current | b, a |
| E28 | doorstop-dev/doorstop docs/reference/item.md, docs/cli/validation.md | Jace Browning (doorstop author; repo since 2013) | Each link stores the parent's fingerprint; "When the fingerprint of a parent item changes, the link is reported as suspect"; `derived` items exempt from needing a parent | current | d |
| E29 | useblocks/sphinx-needs functions/common.py `check_linked_values` | useblocks (sphinx-needs, used in automotive ASPICE work) | Status rollup is user-chosen: all linked needs must match (default) or `one_hit=True` (exists) | current | d |
| E30 | strictdoc-project/strictdoc grammar/type_system.py | Stanislav Pankevich (StrictDoc) | One generic link (`Parent`/`Child`) plus a free `ROLE` string; code-side markers `@relation(REQ, scope=...)` | current | a, c |
| E31 | OAI/OpenAPI-Specification versions/3.1.0.md "Responses Object" | OpenAPI TSC | Not "expected to cover all possible HTTP response codes"; `default` covers the rest; "the explicit code definition takes precedence over the range definition" | 2021 | e |
| E32 | matthiasn/talk-transcripts Hickey_Rich/Spec_ulation.md | Rich Hickey (Clojure, Datomic) | "Breaking changes are broken ... Avoid _breakage_ by turning it into _accretion_" | 2016-12 | b |
| E33 | leanprover/lean4 src/Init/Tactics.lean, Init/Notation.lean | Leo de Moura (Lean, Z3) | `sorry` stubs a proof; "Lean will give a warning whenever a proof uses `sorry`"; dependents found via `#print axioms` (`sorryAx`) | current | d |
| E34 | erlang/otp system/doc/design_principles/sup_princ.md "Maximum Restart Intensity" | Erlang/OTP team (Armstrong, Virding lineage) | "If more than `MaxR` number of restarts occur in the last `MaxT` seconds, the supervisor terminates all the child processes and then itself"; the parent then decides | current | e |
| E35 | ponylang/pony-tutorial code-samples/errors-partial-functions.pony | Pony core team (Sylvan Clebsch) | Partial function declared `fun f(): T ?`; every call site must write `f(x)?` | current | e |
| E36 | w3.org/TR/scxml | W3C (Barnett et al.; Harel statecharts) | Two platform error events, `error.communication` and `error.execution`; "The set of error events may be extended" | 2015 | e |
| E37 | cuelang.org/docs/reference/spec | Marcel van Lohuizen (CUE; Google GCL/Borg config) | Unification "is commutative, associative, and idempotent. As a consequence, order of evaluation is irrelevant" | current | a |
| E38 | haskell.org Haskell 2010 report 2.7 Layout | Haskell committee (Peyton Jones, Hudak, Wadler) | Layout is optional sugar for braces and semicolons; "Because layout is not required, Haskell programs can be straightforwardly produced by other programs" | 2010 | a |
| E39 | osate/osate2 Aadl2.xtext (PortConnection, FlowPathSpec, EndToEndFlow) | SEI/CMU (Feiler; AADL SAE AS5506) | `->` means data transfer only: port connection, `flow path in -> out`, and end-to-end flow `a -> conn -> b`; declarations are `name : kind` | current | a, c |
| E40 | dafny-lang/dafny docs/DafnyRef/Specifications.md | Rustan Leino (Dafny, Boogie, Spec#) | `requires` = precondition, `ensures`, `decreases`, `reads`, `modifies`: one clause word per contract role | current | a |
| E41 | ada-auth.org Ada 2012 RM 6.1.1 "Preconditions and Postconditions" | ISO Ada RM | Contracts are aspects `Pre`/`Post` on declarations (page existence verified; text not quoted) | 2012 | a |
| E42 | AlloyTools org.alloytools.alloy parser/Alloy.lex | Daniel Jackson (Alloy) | Distinct words for distinct roles: `fact`, `pred`, `fun`, `assert`, `check`, `run`, `expect` | current | a, d |
| E43 | rfc-editor RFC 2119 (Bradner), RFC 8174 (Leiba) | IETF BCP 14 | Key words count only "when, and only when, they appear in all capitals"; RFC 8174 added that because lowercase use was ambiguous | 1997; 2017 | b |
| E44 | tc39/proposal-pipeline-operator README, HISTORY.md, issue #91, wiki "Bikeshedding the Hack topic token" | TC39 champions (J. S. Choi, Tab Atkins-Bittner, Ron Buckton) | Hack style (explicit topic) reached Stage 2 on 2021-08-31 after F# style stalled 2017-2021; a Mozilla user study found "no difference ... significant enough"; topic token still open (#91: 823 comments since 2018-02); `$` blocked because it "may unexpectedly shadow outer variable `$`" (jQuery); `%` drew "pushback from implementor due to parsing complexity" | 2015 to now | p |
| E45 | wch/r-source doc/NEWS.Rd | R Core | 4.1.0: native `\|>` "inserts the left-hand side as the first argument"; 4.2.0: placeholder `_` only as a named argument, "can only appear once"; 4.3.0: `_` as the head of an extraction chain | 2021 to 2023 | p |
| E46 | elixir-lang/elixir lib/elixir/lib/kernel.ex `\|>/2` docs | Jose Valim (Elixir) | First-argument insertion; docs list "two common pitfalls" (precedence, anonymous functions) and offer `then/2` | current | p |
| E47 | clojure/clojure core.clj | Rich Hickey | `->` (second position), `->>` (last), `as->` (user-named binding), `some->` (stop at nil), `cond->`: five threading forms | 1.0 to 1.5 | p, e |
| E48 | ocaml/ocaml stdlib/stdlib.mli `( \|> )` | OCaml team (Leroy et al.) | `x \|> f \|> g` "is exactly equivalent to `g (f (x))`": unary functions, no placeholder | current | p |
| E49 | jqlang/jq docs manual.yml | jq maintainers (Dolan) | "The \| operator combines two filters by feeding the output(s) of the one on the left into the input of the one on the right"; `.` is the implicit topic | current | p |
| E50 | gleam-lang/language-tour lessons "Pipelines", "Function captures" | Louis Pilfold (Gleam) | `rocket \|> launch(1, 2)` becomes `launch(rocket, 1, 2)`; when the value is not first, a capture `f(a, _, b)` uses `_` as placeholder | current | p |
| E51 | Crossref 10.1145/2534973, Stefik and Siebert, ACM TOCE 13(4) (abstract) | Andreas Stefik (Quorum; empirical PL research) | Novices using Perl or Java were not significantly more accurate than with "Randomo" (random keywords); Quorum, Python and Ruby were | 2013-11 | a, p |
| E52 | guide.elm-lang.org/error_handling | Evan Czaplicki (Elm) | "you will not see runtime errors in practice ... because Elm treats errors as data" | current | e |
| E53 | GHC user guide "Typed holes"; Rocq refman `Admitted` | GHC team; Rocq team | GHC: `_`/`_foo` holes produce an error naming the expected type; Rocq: `Admitted` turns the goal into an axiom with warning "A proof was admitted" | current | d |

### Corpus measurements (this repository)

| Id | Measurement | Where |
|---|---|---|
| U1 | 11 of 11 domain mockups, written by three authors without coordination, declare `system X { ... }` on one line and every planning item at top level after it; under the longest-prefix rule every item is MDL031 (about 80 findings) | notes/research/grmb-corpus/domains/d01-d11 at 577c8e00c2 |
| U2 | 10 of 12 `retry` uses in the 222 .grmb files of the repository target the element the arm matched; 7 of those 12 restate the default `else end err(v)` | corpus d01, d02, d04, d06, d08, d11, f07, f16; crates/grimble-model/tests/corpus/plan (web_app, u-step-scenario-chain; exceptions thermostat, mdl027-clean) |
| U3 | 5 domain mockups invent a trailing step fact (`-> { ok, e } idempotent;`); nobody wrote the specified `{ ... }` step body; 3 timer actors invent `{ period 1 s; }` | d02, d03, d06, d08, d11; d02, d07, d08 |
| U4 | the corpus guessed `budget` twice in two shapes (`budget latency 50 ms;`, `budget retry_window 30 s;`) and `goal x as one_of { }` once; zero uses of `one_of [exclusive] { }` | d10, f07; d10 |

## 2. Evidence to decision

One row per design decision of the cycles. "Support" lists the rows that
back the decision; "Against" lists rows that cut the other way and how the
decision answers them. A decision with no outside support says so and
states its internal-consistency ground.

| Decision | Change | Support | Against, and the answer | Grade |
|---|---|---|---|---|
| D150 | one evidence clause `verified_by SEL [for STEP.VARIANT]` and `verified_by manual because="..."` on every entity; `evidence tests`, `evidence ref` and the `vmodel kind test` + `runnable` form are deprecated spellings of it (audit R1, M1, C2) | E24 (SysML v2: one keyword `verify` per trace relation), E30 (StrictDoc: one generic link plus code-side marker), E16, E17 (one obvious way) | none found | supported |
| D151 | the computed rung is `covered` (`declared < bound < covered`) everywhere; `verified` is reserved for frob's overlay; planning JSON keys `design_status`, `design_status_hi` (audit R3, M2, C4) | E25 (SysML verdicts are a separate enum `pass fail inconclusive error`; grmb's overlay adds its own `not-run`, i.e. "ran and passed" is a different fact from "is traced"), E28 (doorstop link state separate from test result) | no standard defines "covered" vs "verified"; the split rests on grmb's own reasoning (evidence 2(d) Open) | partly supported |
| D152 | `->` means "follows / moves to" only; `=>` maps a pattern to its consequence, in match arms and in outcome maps, read left to right; a step's outcome type follows `:`; a waypoint chain is an ordered statement list; `via FLOW` on hops is dropped (audit R5, R9 first half, S2, C8, C9) | E39 (AADL: `->` is data transfer only, `name : kind` declarations), E24 (SysML: one keyword per relation), E26 (Structurizr: one `->`; behaviour must instance declared relations, so restating the flow is redundant), E27 (Mermaid: many arrow spellings collide) | D139 fixed the token set; the change keeps every token and removes meanings, not spellings | supported |
| D153 | one bounded-repeat grammar `retry [STEP] max N [within T] [else ...]` for scenario arms and ambient policies; the default target is the element the arm matched; the default `else end err(v)` is never spelled (`grimble fmt` drops it) (audit R8, M8, GAPS G3) | E34 (OTP restart intensity `MaxR` within `MaxT`, escalation to the parent), E45, E50 (R and Gleam: omit the obvious operand), U2 (10 of 12 retries name the matched step, 7 of 12 restate the default) | none found | supported |
| D154 | no `$` (or any) placeholder token in grmb; chains thread no value; restatement is removed by defaults instead (pipeline verdict) | E44 (TC39: no consensus on a topic token after 823 comments; `$` blocked by an existing meaning), E45, E50 (placeholder only where needed, a free token), E47 (five threading forms), U2 | quartzite keeps its own `$` question; grmb does not decide it | supported |
| D155 | one generated keyword table with every word and its class (reserved, item head, planning body word, selector predicate, include marker), including every rev 2 word; identifier escape `r#name`; `chain` becomes a planning body word; a pack realization kind may not equal a planning word; the `outcome` clause word is gone with D152 | E2 (Rust RFC 2388: `<word> {` cannot be contextual), E3 (reserve before users), E4 (`r#` raw identifiers), E18-E21 (Kotlin, C#, Python, C++ soft keywords and their costs), E19 (C# `@field` escape), E24 (SysML quoted-name escape), E27 (Mermaid global `end`), E32 (accretion over breakage) | E20 (soft keywords cost tool authors): the table is generated so highlighters read one source | supported |
| D156 | the FILE include is spelled `use "path"`; `include` keeps exactly one meaning, scenario invocation; `include "path"` stays accepted through major 2 with MDL012 (audit S3; audit R6 rejected) | E24 (SysML v2 keeps `include` for use-case inclusion) | audit R6 proposed the opposite (drop scenario `include`); E24 contradicts it | supported (R6 rejected) |
| D157 | a file's top level joins a system by `system NAME;` or by declaring exactly one braced `system` at top level; `system.X` keeps naming the enclosing system's reaction step (audit R2, S1, C1) | no outside evidence either way; ground: U1 (every independent author wrote the file-header shape) and internal consistency (one membership rule per file, order-independent) | none | internal consistency |
| D158 | `budget` is not a construct; a time or rate target is a `claim` with `bound METRIC TARGET <= Q` whose TARGET may be a planning entity; PLAN024 and PLAN025 are retired (audit R4, M3, C7) | no outside evidence; ground: U4 (two incompatible guessed shapes) and one construct per job (E16, E17 state the principle, not this case) | none | internal consistency |
| D159 | the human label is the `///` doc comment (Doc facet); `title` is no longer a planning word (audit R10, M5) | no outside evidence; ground: the Doc facet already exists and is digested apart from Body (D72) | none | internal consistency |
| D160 | one debt key set `because= until= ticket= owner=` (strings, a date for `until`) shared by `assumed`, `defer`, `hotfix` and `sorry`; `review=` is the major-2 spelling of `until=`; `ticket=` is a string everywhere (audit R11, M4, S5, C11) | no outside evidence; ground: three forms carried one idea with three key sets | E33, E53 (Lean `sorry`, Rocq `Admitted`) support the hole itself (D142), not the key names | internal consistency |
| D161 | small spellings: `on page P` replaces `requires page P` so `requires` is only goal precedence; actors locate with `in node N`; `because="..."` is canonical; `renamed_from` takes an identifier only; `cli` joins the core realization vocabulary; `sorry` may replace a whole planning body; `verified_by` is not a `system` clause; underscore joins one keyword, a space joins a phrase of keywords (audit R12, S4, M6) | E40 (Dafny: `requires` is precondition only, one clause word per role), E16, E17 (E41 dropped in cycle 2: its text was not read) | none | supported for `on page`; internal consistency for the rest |
| D162 | a `one_of` group rolls up with the join ("any one alternative holds"); `all` groups and every other rollup keep the meet | E29 (sphinx-needs offers the meet by default and `one_hit` for exists) | none | supported |
| D163 | a grmb `scenario` is a use-case-level flow; each arm path is what Gherkin calls a Scenario; grmb `goal` maps to a Gherkin Rule; the name stays (no rename) | E22 (Gherkin `Rule` -> `Example`/`Scenario`, one path each), E23 (North: one story, several scenarios on one event) | the word clash is real; renaming would churn every model for an interop concern no user has raised | supported (mapping); rename deferred |
| D164 | derived V-model edges reuse the surface words (`realizes`, `impl_of`, `impl_for`, `on_page`, `refines` for goal refinement); the vmodel link verbs stay as they are (audit R7 partly applied) | E24 (SysML keeps `satisfy`, `verify`, `allocate` as keywords and drops `refine`, `derive`, `trace`), E30 | E24 contradicts R7's proposal to drop `satisfies` and `allocates`; it backs only three of the seven kept verbs, the other four (`refines`, `decides`, `supersedes`, `blocked_by`) are kept on internal grounds | partly supported (R7 trim rejected) |
| D165 | documentation consolidation: the planning layer merges into grmb-spec.md; decision text lives in decisions.toml with one-line home headings; outcome-map rules ERR002-ERR005 are renumbered PLAN041, PLAN042, PLAN044 (ERR001-ERR003 belong to grimble-lints, rules.md); PLAN-G01..G10 become PLAN050-PLAN059; raw R1 notes retired (audit DOC1-DOC8) | process change, no outside evidence needed; ground: the audit's measured duplication and the rule-id collision | none | not a language change |
| D166 | the keyword table is complete: `via` reserved, a deprecated class (`title`, `review`), `system` in both contextual classes, markers only `outside` and `lang` | E2 (a word the parser must recognise has to be in its word list), E4 | none | supported |
| D167 | one precedence between mount and `system REF;` membership | no outside evidence; internal consistency (one full name per text) | none | internal consistency |
| D168 | a closed MDL012 bridge equal to what P1 read, kept through major 2 | E3 (a keyword change is the breaking change an edition exists for), E32 (accretion over breakage) | none | supported |
| D169 | PLAN016 covers arm and ambient retries; AMB002 retired (D182 says which ambient word) | no outside evidence; one fact, one severity | none | internal consistency |
| D170 | MDL014 drops level pairing on the deprecated form; duplicate evidence is MDL017 only | no outside evidence; one finding per root cause (spec 12.9 law 3) | none | internal consistency |
| D171 | evidence ladder: missing file `planned`, wrong id SYS011 | no outside evidence; mirrors MDL005 ("a model may describe code that does not exist yet") | none | internal consistency |
| D172 | one `pair` spelling of a step-qualified variant | no outside evidence | none | internal consistency |
| D173 | a satisfied `one_of` has no per-alternative obligation | E29 (the exists rollup: one hit satisfies the group) | none | supported |
| D174 | PLAN013 for an unused `for *` impl | no outside evidence; spec 12.9 law 2 (levels optional) | none | internal consistency |
| D175 | an EBNF for files and architecture items | no outside evidence | none | internal consistency |
| D176 | one meaning per keyword (`for`, `kind`, `on`, `in`, `as`); goal dimension as `attr`; no `page` realization kind | E16, E17 (one obvious way), E24 (one keyword per relation) | none | supported in principle |
| D177 | ambient surface: one policy, an evidence body, no per-class or node override; AMB006 retired | E34 (OTP escalates to the parent; here the parent is outside the model) | none | partly supported |
| D178 | frozen U kind names, opaque `ticket=`, explicit `else` under `_`/`unknown`, `route`/`topic` take a name | no outside evidence | none | internal consistency |
| D179 | SYS016 Unresolved over Unknown nodes | the spec's own polarity law (binding.md 6, universal-model.md 4.2); no outside source | none | internal consistency |
| D180 | `sorry` is its own U sort, three positions | E33, E53 (a hole primitive that checks with a warning and taints dependents; neither blocks formatting) | none | supported |
| D181 | `page` planning word, top-level `use`, PLAN007 affordances, `attr_value` | no outside evidence | none | internal consistency |
| D182 | ambient `retry` keeps state and repeats system steps; `restart` loses state | E34 (OTP restarts a child process, state lost, under an intensity bound) | none | supported for `restart` |
| D183 | waypoints bind like realizations | no outside evidence | none | internal consistency |
| D184 | one evidence fact per pair; PLAN043 retired | no outside evidence; one finding per root cause | none | internal consistency |
| D185 | PLAN041 owns the opaque error set | no outside evidence | none | internal consistency |
| D186 | respelled clauses take their current attr names; one restamp | no outside evidence; mirrors the digest-scheme rule of grmb-spec 3.4 | none | internal consistency |

## 3. Unverified, not used

Not fetched or not readable in the 2026-10-31 review; listed so a later
cycle can fetch them, never cited as support:

- Wirth, "What can we do about the unnecessary diversity of notation for
  syntactic definitions?", CACM 1977 (doi 10.1145/359863.359883) and
  Iverson, "Notation as a tool of thought", CACM 1980 (doi
  10.1145/358896.358899): metadata only, content not read.
- Cockburn use-case template (archive URL 404); Hoare "Hints on
  programming language design" (PDF fetched, no text extractor); Leveson
  STPA Handbook; Gojko Adzic; ISO 26262, DO-178C and IEC 62304 trace
  clauses; UML 2.5 and SysML v1 specs; OCL; BPMN 2.0 error boundary
  events; ArchiMate; PlantUML syntax history; Harel 1987; Petri nets;
  Event-B/Z; TLA+/PlusCal; Eiffel; Koka; Unison; Nix; Dhall; Pkl;
  Bazel/Make; SQL; Prolog/Datalog; APL beyond metadata; Forth; Smalltalk;
  Lisp macros; Idris/Agda holes; F# (only through the TC39 README);
  magrittr `%>%`; Scala/Kotlin `let`; Nim UFCS; Unix pipes; Verilog
  blocking vs non-blocking; VHDL/Chisel; music, chess, railway, FMEA and
  fault-tree notations; any frequency count of multi-argument threading
  in real code.

## 4. Retired R1 raw notes

The six raw R1 research notes were deleted in cycle 1 (DOC6). Their
findings, with primary sources, are distilled in
notes/research/grmb-r1-synthesis.md, whose citations (`[A:F22]`) resolve
against the notes at commit 577c8e00c2:

| Key | Note | Lines | Bibliography section | Retrieve |
|---|---|---|---|---|
| A | grmb-r1-practice.md | 1387 | 5 (L738-1128) | `git show 577c8e00c2:notes/research/grmb-r1-practice.md` |
| B | grmb-r1-failure.md | 1035 | 5 (L464-669) | `git show 577c8e00c2:notes/research/grmb-r1-failure.md` |
| C | grmb-r1-languages.md | 1053 | 5 (L536-838) | `git show 577c8e00c2:notes/research/grmb-r1-languages.md` |
| D | grmb-r1-incompleteness.md | 1073 | 5 (L546-981) | `git show 577c8e00c2:notes/research/grmb-r1-incompleteness.md` |
| E | grmb-r1-graphs.md | 1295 | 5 (L657-1100) | `git show 577c8e00c2:notes/research/grmb-r1-graphs.md` |
| F | grmb-r1-ergonomics.md | 1019 | 5 (L718-917) | `git show 577c8e00c2:notes/research/grmb-r1-ergonomics.md` |

Their bibliographies were graded by their own authors on 2026-10-09
(section 7 of each, "verification pass") and were not re-fetched in the
2026-10-31 review, so no cycle decision rests on them alone.
