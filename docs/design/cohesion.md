# Function cohesion ("one job per function"), type precision and directive admission (D118-D121)

Status: draft
Owner: grimble
Decisions: D118-D121
Audience: rule author

Ownership note: grimble. The COH rules live beside NEAT in grimble-lints (they
judge code structure, not work accounting; products.md section 1), with
knobs under `[coh]` in `grimble.toml`. frob runs them only through the
sibling protocol.

Provenance: accepted direction, owner questions 2026-10-08: "enforce a one
job per function rule, where we don't mix logic; how would you detect
that in the cross-language linter?" and "do we account for Python being
typed or untyped; will we ever mark something decidable as undecidable
because of types?" Builds on universal-model.md (Bounds, May/Must,
section 4.6 annotate-or-opaque), neatness.md (effects, NEAT010-019,
NEAT031) and grimble-model.md (layers). Reviewed by the formal review of 2026-10-08
(notes/review/formal-review-2026-10-08.md, section 5), whose findings
are applied here; citations are in its section 7. Beck's Composed
Method could not be fetched and is related work only.

## 1. What "one job" means, operationally (D118)

"Does one thing" is not a syntactic property, so no single metric
decides it. It is decomposed into four signals, each a computable
question over U with Bounds, each its own rule so a finding says which
kind of mixing it saw. All are P+ (fire only on proof), report
Unresolved between their bounds, and are Warn by default.

| Id | Mixing | Question over U | Needs |
|---|---|---|---|
| COH001 | independent jobs | the body's statements split into two or more data slices that share no variable other than parameters (output slices, Bieman and Ott 1994; Ott and Thuss 1993) | binders and refs (F2), def-use within the body, may-alias |
| COH002 | decision with effects | the unit both computes decisions (branches whose conditions depend on computed data) and performs effects in those branches, and is not marked `frob:shell` or `frob:dispatcher` (functional core, imperative shell; extends NEAT014-016) | effects capability, def-use |
| COH003 | mixed abstraction levels | the callees span layers further apart than `[coh] max_level_spread`: domain-level calls next to primitives of a lower layer (string slicing, index arithmetic, raw IO) in one body (single level of abstraction; related to Beck's Composed Method) | apply_targets, layer of callee from the grimble model or module depth |
| COH004 | mixed vocabularies | identifiers and callees cluster into disjoint domain vocabularies (after the class-level conceptual cohesion of Marcus and Poshyvanyk 2005, applied to functions) | syntax; Advisory only (a heuristic, never Warn) |

NEAT031 (dispatch-site-owns-logic) stays the dispatcher-specific case.
COH adds no directive (section 4). A unit with a declared role
(`grimble:shell`, `grimble:core`) is judged against its role, so an
imperative shell may mix decisions and effects; the role claim itself is
verified by the effects rules. A unit that mixes on purpose without a
role (an intentional dispatcher, a deliberately fused hot loop) takes an
exception on the specific finding (`accept` with a reason, exceptions.md),
which is visible, counted and expires; there is no opt-out marker.

### 1.1 COH001 with bounds

Definition (output slices, Bieman and Ott 1994): the outputs of a unit
are its returned values (each component of a returned tuple or record
separately), the parameters it writes, and each non-trivial effect it
performs. A job is a group of output slices connected by shared
statements; COH001 counts the groups.

The dependence graph is the program dependence graph (Weiser 1984;
Ferrante, Ottenstein and Warren 1987), not def-use alone:

- Statement granularity: a simple statement is a node; a compound
  statement's condition is a node and every statement in its body is
  control-dependent on it.
- Edges: data dependence (a read reached by a write, including every
  reaching definition across branches) and control dependence (a
  statement on its guarding condition). Both are Must: Must means a
  static dependence, not a certain execution.
- May edges are reserved for what static dependence cannot see:
  aliasing and heap writes, mutation through a method call on a
  parameter, closures captured by reference, dynamic attributes
  (`setattr`, `**kwargs`), and calls whose effects are unknown. The May
  edge set must be complete; an Unknown resolution widens to "may touch
  anything reachable" (it is never dropped; formal review H1).
- Glue: a parameter connects nothing only while no statement writes it
  or may write it; a written parameter is an output and its writes are
  ordinary edges.
- Trivial statements (calls in a configured vocabulary: logging,
  metrics, asserts) are removed before counting and add no edges, so
  logging never glues two jobs together (removing one can split a
  component; that is intended). A slice with no output is dead code,
  left to a dead-code rule. Slices below `[coh] min_slice_statements`
  do not count.

Let `k_must` be the number of groups using only Must edges and `k_may`
the number when every May edge also connects. Adding edges only merges
groups, so `k_may <= k_true <= k_must`: `lo = k_may`, `hi = k_must`.
COH001 fires when `lo >= 2` (two jobs in every completion of the May
edges), is clean when `hi <= 1`, and is Unresolved otherwise with the
May edges as witnesses ("these two parts look independent unless
`self.cache` aliases `buf`").

The fix COH001 suggests is the slice extraction itself (an extract-unit
edit per group), the slice-based extract-method refactoring of
Tsantalis and Chatzigeorgiou 2011.

### 1.2 Cross-language

Every input is a universal capability, so the rules are written once
(`applies = universal`, rule-authoring.md) and run wherever the adapter
declares the capabilities: def-use needs F2, COH002 needs `effects`,
COH003 needs `apply_targets` and a layer source. A language without the
capability gets Unresolved with the missing capability named, never a
silent pass (Theorem 3).

## 2. Type precision and gradual typing (D119)

Types make many questions decidable that are not decidable without
them: call targets under dispatch, effects of callees, aliasing and
mutability, nullability, exhaustiveness. The model must use types where
they exist, without trusting types that do not hold.

### 2.1 Precision is per site, not per language

A language is not "typed" or "untyped"; a program point is. Python with
some annotations, TypeScript with `any`, C# with `dynamic`, Rust with
`dyn Trait` all mix precise and imprecise sites. A type-dependent answer
carries two coordinates (formal review 5.3):

- provenance, a set: `checker`, `annotation`, `local-inference`,
  `none`. It composes by union along a chain and is what `rule why`
  prints.
- status: Must, May or Unknown, the existing chain, computed by a policy
  from provenance, the trust setting and closure conditions. It composes
  by meet along a dispatch chain; a May hop composes relationally (the
  union of downstream sets); an Unknown hop widens everything downstream
  to the top, never ends the chain.

Rules for status:

| Provenance | Status |
|---|---|
| checker, under whole-program closure (2.2) | Must where the type is concrete; May over the closed implementor set otherwise |
| local-inference (literal types, constructor calls, isinstance or typeof narrowing) | Must within the flow fact, only if the program has no write to the class attribute or prototype (`setattr`, prototype assignment); otherwise May; with an opaque `eval`, Unknown |
| annotation without checker closure | Unknown with the annotated candidates as a ranked hint; it narrows explanations and ordering, never the May set (an unverified annotation can exclude the true target) |
| none (`Any`, `dynamic`, unannotated, reflection) | Unknown, reason `dynamic-site` |

When an annotation and local inference disagree, the answer is Unknown
with reason `conflict:annotation-vs-inference`, surfaced as a likely bug
(the one place where Belnap's fourth value, "both", is useful; it stays
an Unresolved reason, not a value rule authors see).

### 2.2 Types that lie, and when a checker makes a type exact

In Python and TypeScript an annotation is a claim, not a guarantee:
types are erased, so `cast`, `# type: ignore`, `any`, untyped
dependencies and runtime patching can break it, and a strict-clean file
can still receive a wrong value from an unchecked caller (sound gradual
typing needs runtime checks at the typed-untyped boundary: Siek and Taha
2006; Tobin-Hochstadt and Felleisen 2006, 2008; Takikawa et al. 2016
measure what erasure avoids). So:

- `[types] trust = "checked"` (default): a type fact is checker-exact
  only under whole-program closure: every module that can reach the site
  through the import graph is checked clean in the checker's strictest
  configuration (pyright `strict`, mypy `--strict`; ty has no strict
  flag, so a ty configuration with every rule at error level), and no
  `Any`, `cast` or ignore comment flows into the site. Otherwise the
  fact counts as an annotation.
- `"annotated"`: annotations count as May (explicitly unsound when they
  lie; every report and finding produced under it says so).
- `"none"`: annotations are hints only.

The checker is a bound tool under the existing tool-binding rules
(versions pinned, output parsed, failures Unresolved), so frob never
implements a type checker; it consumes one. How the per-site types are
obtained is fixed in tool-binding.md section 4 (D122): `ty server` over
LSP for Python (`dmypy inspect` for mypy repositories), a Node helper on
`@typescript/typescript6` for TypeScript, both behind a latency spike.

### 2.3 Will something decidable be marked undecidable? Yes, and that is bounded and visible

The honesty theorem guarantees one direction only: frob never reports
clean or a finding without proof. It does not guarantee that Unknown is
minimal; no analysis can (any fixed analysis of a Turing-complete
language is incomplete, Rice's theorem). Unknown answers that a better
analysis could decide come from four places, each with a remedy:

1. The checker was not run or not trusted: run it (section 2.2).
2. The adapter's own inference is weaker than possible: improve the
   adapter; measured by the incompleteness metric below.
3. The program is decidable but only with whole-program reasoning frob
   does not do (for example a call target fixed by a value set far
   away): Unknown names the site and the annotation that would decide
   it (section 4.6 annotate-or-opaque); `frob:` directives such as
   `frob:effects` let the author state it once and have it verified.
4. Genuinely undecidable: stays Unknown with that reason.

Every Unknown carries its reason class (`not-run`, `untrusted-type`,
`dynamic-site`, `analysis-limit`, `undecidable`) and the cheapest
remedy, so a user can tell "frob could not" from "nobody could".

Incompleteness is measured, not assumed: testing.md's corpora gain an
oracle column (the true answer, known by construction) and CI reports
the false-Unknown rate per language and capability; a rise is a
regression like a failing test. A false Must or a wrong finding is a
soundness bug and fails the build.

## 3. Consequences

- New capability fields: `dependence(unit)`, the data and control
  dependence graph with Must/May edges (F2),
  `type_precision` on every type-dependent answer, Unknown reason
  classes (extending the typed Unresolved reason of ~YR7MCXF, D106).
- Python adapter: a bound-tool importer for ty or pyright types
  (hullbreach platform already has `ty.toml`); TypeScript: tsc types;
  C#: Roslyn semantic model through the dotnet adapter (dotnet-unity.md).
- COH001-004 ship after the GRL executor so they are written in GRL
  where expressible (D76); COH001's component counting is a catalog
  relation (`slices(unit)`) the executor exposes.

## 4. Directive admission (D120)

Directives are the comment DSL every product reads, and each one is
something a user must learn, an agent must emit correctly and a parser
must keep. The same discipline as verb admission (cli.md 4.0, D104)
applies: a directive exists only if it passes all three tests, and a
registry test fails when a registered verb has no row naming them.

1. Not derivable: it states a fact the tools cannot compute from code,
   config or the model (a framework entry point that gob-frameworks
   detects is not a directive; an effect claim on an unanalysable body
   is).
2. Not an exception: if its only effect is to silence one rule at one
   place, it is an `accept` exception on that rule (exceptions.md:
   reason, owner, expiry, counted), never a dedicated marker.
3. Consumed: at least two rules consume it, or it is a claim that a rule
   verifies (VERIFIED, CONTRADICTED or UNVERIFIED, neatness.md 3).

Namespace rule, restated: a directive is namespaced by its consumer.
Work accounting (tickets, todos, doc and test bindings, exceptions) is
`frob:`; claims about the design of code (effects, roles, model
bindings) are `grimble:`; design-system verdicts are `crunk:`. The
previous placement of claim verbs under `frob:` (code-model.md section
4) is reversed: frob never consumes them.

Applied to the current registry (code-model.md section 4 milestone-2
table, grimble-model.md binding verbs):

| Verb today | Decision | Why |
|---|---|---|
| `frob:effects <set>` and `grimble:effect ATOM because` | merge into one `grimble:effects <set> [because "..."]` on a unit or a model node | the same claim about the same atom registry in two namespaces; consumer is grimble |
| `frob:pure`, `frob:honest` | drop (aliases) | two spellings of `grimble:effects none` and `grimble:effects honest`; one spelling per fact |
| `frob:core`, `frob:shell` | keep as `grimble:core`, `grimble:shell` | role claims consumed by NEAT014-016, COH002 and verified by the effects rules |
| `frob:dispatcher` | drop | its only effect is to silence NEAT031: an `accept` exception |
| `frob:trusted` | drop | an unverified claim the owner owns is an `accept` on the UNVERIFIED finding, with a reason and expiry |
| `frob:idempotent` | drop | the claim is discharged only by a `frob:tests` binding of kind `idempotent`; that binding already states it |
| `frob:hook [kind]` | drop, inferred | framework entry points come from gob-frameworks (`entrypoints`); an undetected framework is a gob-frameworks gap, bridged meanwhile by `accept` on NEAT030 |
| `frob:calls <symref>...` | keep as `grimble:calls` | not derivable (dynamic call targets); consumed by gob-ir resolution for every rule that reads call edges |
| `grimble:binds`, `grimble:node`, `grimble:channel`, `grimble:boundary` | keep | model bindings, not derivable, consumed by the SYS and binding rules |
| `frob:ticket`, `frob:todo`, `frob:doc`, `frob:tests`, `frob:describes`, `frob:waive`/`accept`/`defer`, `frob:quote` | unchanged here | accounting; reviewed separately against the same three tests |

Net: eight claim-verb spellings become three (`grimble:effects`,
`grimble:core`, `grimble:shell`) plus `grimble:calls`. Old spellings
parse for one minor release with DSL deprecation findings and an
automatic fix, then go.

## 5. Purity and honesty: inferred first, claimed only where inference cannot reach (D121)

Owner question 2026-10-08: "can we detect purity; is a purity or
honesty directive useless?" Definitions (notes/research/neatness.md
PF-1): pure = no effect at all (`none`); honest = touches the outside
world only through its parameters (it may mutate what it is given,
never globals, clock, randomness, IO or singletons).

Detection is the effects capability of neatness.md 3: `effects(unit)`
returns Bounds{lo, hi}. lo is what the body provably does; hi is the
closure over every callee, where an unresolved call, an opaque body
(FFI, `unsafe`, `eval`, reflection), a dynamic site (section 2) or an
external symbol without a vocabulary entry widens hi to `any`.

- Proven pure: hi = none. Proven honest: hi contains only effects on
  storage reachable from parameters (`writes(param)`), which needs the
  may-alias facts of section 1.1 to tell a parameter from a global.
- Proven impure or dishonest: lo exceeds the class.
- Otherwise Unknown, with the widening call sites as witnesses.

So yes, purity is detectable wherever the call closure is resolvable,
and every unit gets an inferred class with no annotation: in Rust most
safe code resolves (with a vocabulary for interior mutability: `Cell`,
`RefCell`, atomics, `static mut`); in C# and Java most of it does with
types; in Python and TypeScript precision follows section 2 (checked
types resolve dispatch; `Any` and dynamic attributes widen).

What an annotation adds, and why it passes D120's tests:

1. A boundary where inference cannot reach. A body that is FFI,
   generated, reflective or dynamically dispatched leaves every caller
   Unknown. A `grimble:effects none` claim on that boundary lets the
   callers' answers be computed as conditional answers: a caller is
   reported pure "assuming the claim at X" (reason `assumed:<claim>`),
   so honesty holds (Theorem 3: an answer derived from an unverified
   claim carries it as a premise, and a false claim can never produce
   an unconditional clean). The claim itself stays UNVERIFIED unless the
   body becomes analysable. Conditional answers count as clean in check
   and CI and as Unresolved at the release gate, like the human tier
   (crunk.md 4.1). This is the main use.
2. A contract on public API. A library promising its users that a
   function is pure states it; CONTRADICTED is an Error the moment a
   change adds an effect, at the function, not at some distant caller.

What it is not needed for: keeping an inferred-pure function pure.
That is a ratchet without annotation: NEAT037 (effect-row-widening)
fires when a unit's inferred class gets worse against the base branch
(`--base`), so a pure helper that starts reading the clock is caught in
review with no comment in the source. Projects that want the inferred
classes visible get them from `grimble explain UNIT` and the effects
column of `grimble graph`.

Consequences: `grimble:effects` stays (one verb, D120) and its typical
density is low: boundaries and public contracts only. NEAT011
(effects-undeclared, off by default) must not require annotations on
units whose class is already proven; it applies only to public units
whose inferred class is Unknown, which is exactly where a claim helps.
A rule PURE-candidate is not added: "this function could be pure" is
just its inferred class, shown, not a finding.
