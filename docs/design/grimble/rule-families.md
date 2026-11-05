# Rule families: NEAT, COH, CI and DK

Status: draft
Owner: grimble
Decisions: D59, D60, D118, D120, D121
Audience: rule author

The grimble rule families that judge code and repository structure, each
stated once under one template: Purpose (what it judges and why),
Rules (the catalogue), Knobs (configuration and implementation
status), Decided and Open. NEAT lives in `grimble-lints`, COH beside it
(they judge code structure, not work accounting; docs/design/shared/charter.md section 1)
and CI and DK in `grimble-ci`; frob runs them only through the sibling
protocol (grmb-spec.md 20.2) and `[[check.tool]]` stages. This file
replaces neatness.md, cohesion.md and cicd.md (docs/MOVED.toml). Type
precision (D119, formerly cohesion section 2) is in
[shared/universal-model.md](../shared/universal-model.md) section 10. Decision text is
in [decisions.toml](../../decisions/decisions.toml); the headings at the
end are its anchors.

Depends on shared/universal-model.md (answer lattice, polarity, capabilities,
section 4.6 annotate-or-opaque) and shared/rules.md. Evidence:
notes/research/neatness.md (NEAT), notes/research/lint-catalogue-2026-10-08
(ranking), notes/research/cicd-survey.md (CI and DK, 1069 repositories),
notes/review/formal-review-2026-10-08.md (COH).

## 1. NEAT: neatness

### 1.1 Purpose

Four principles, each traceable to a source and each turned into rules
that are decidable on structure or that require a declaration:

1. Honesty (Smith, after Van Eerd): a function touches the outside world
   only through its signature. Pure is the special case with no
   mutation. Dishonesty is infectious upward, so honest functions live
   at the leaves and the dishonest shell sits at the roots (Bernhardt's
   functional core and imperative shell; Seemann's impureim sandwich).
2. One level of abstraction per function (Smith's golden rule; Martin's
   SRP; Parent's no raw loops; Van Eerd's separate producing data from
   acting on it). Section comments inside a body and dispatchers that
   grow logic are the structural smells.
3. Be nice to the caller: few positional parameters, no boolean flags,
   parameter objects, accept the weakest sufficient type, encode
   preconditions in types (newtypes, receipts, parse-don't-validate).
4. Thin hooks: framework entry points (`main`, `update`, handlers,
   dispatch tables) glue to right-side-up functions and hold no logic.

What is explicitly NOT lintable, and the family never pretends to:
whether an abstraction level is the right one, whether a name is good,
whether a responsibility is single, where to stop encoding invariants
in types, and idempotence without evidence (notes/research/neatness.md
section 9). The family also never fires on "too few" or "too small"
functions: Ousterhout's shallow-module objection stands, so NEAT has no
inverse of the extraction rules.

#### The ruff PR as the canonical example

astral-sh/ruff PR 29076: a scope check inside the AST dispatcher
(`checkers/ast/analyze/expression.rs`) grew from a one-line guard into a
condition with its own reasoning. The reviewer asked for it to move into
the rule function (`builtin_variable_shadowing`), and the merged diff
leaves the dispatcher as a plain `if rule enabled { call rule }` while
the rule owns the class-scope logic with a comment explaining it. That
is NEAT031 dispatch-site-owns-logic: a unit whose body is, by shape, a
sequence of guarded calls to peer units (a dispatcher) must not contain
a conditional or loop whose body does more than guard a call. The
remedy is always the same: move the logic to the callee or to a named
predicate.


### 1.2 Rules

#### Effects: the annotation vocabulary

Honesty is undecidable in general (Theorem 3 of the universal model),
so under section 4.6 the adapter reads it or requires it:

- Native markers map in where the language has them: Verse `<computes>`
  is `none`; D weak `pure`, Nim `func`, SPARK `Global => null` are
  `honest`; Haskell non-IO types are `none`; Rust `const fn` is `none`.
- Otherwise a directive on the unit: `grimble:effects <set>` where the set
  is `none`, `honest`, `io`, `any`, or a list of atoms `reads(X)`,
  `writes(Y)`, `clock`, `rng`, `env`, `fs`, `net`, `stdio`, `exit`,
  `panic`, `diverge`, optionally suffixed `total` (no panic, no
  divergence). `none` and `honest` are the sets that were once spelled
  as separate pure and honest verbs; there is one spelling per fact.
  Role markers: `grimble:core`, `grimble:shell`. Hooks are inferred from
  the framework vocabulary, an intentional dispatcher or an unverified
  claim the owner owns is an `accept` exception with a reason and
  expiry, and an idempotence claim is discharged by a bound `frob:tests`
  of kind `idempotent`; none of these has a dedicated marker (D120).
  The directives are in the `grimble:` namespace and evaluated here
  ([shared/code-model.md](../shared/code-model.md) section 4 has the table and the namespace rule).
- The atoms are the shared registry's ([binding.md](binding.md) section 7.5), which is
  hierarchical (`fs` covers `fs.read` and `fs.write`); there is one
  callee-vocabulary table per language and external symbols get effect
  sets from the `[neat.effects]` tables, which are views over it (clock,
  rng, env, fs, net, stdio, exit vocabularies, with defaults generated
  for Rust, Python, TypeScript, Go), so grimble's capability detectors
  and NEAT never disagree about what `std::fs::write` is.

The adapter's `effects(unit)` capability returns Bounds{lo, hi}: lo is
what the body provably does (direct calls to vocabulary symbols, reads
of mutable globals from the scope graph), hi is the closure over callees
with Unknown edges widening hi to `any`. A declared claim is then
VERIFIED (claim >= hi), CONTRADICTED (claim < lo, an Error) or
UNVERIFIED (between, reported Unresolved with the remedy to annotate the
callee or narrow the claim). An unverified claim is never clean; this is
the honesty boundary applied to honesty itself.

#### The catalogue (37 rules; the first ten ship first)

The first ten are ordered by evidence (lint-catalogue-2026-10-08: C is
the practitioner consensus factor, E_det the evidence a mechanical rule
can act on): NEAT004, NEAT003, NEAT012, NEAT031 and NEAT030 come before
NEAT006 and NEAT007, which have the weakest support. NEAT001, NEAT006 and
NEAT009 are contested or low-evidence: Advisory, and bound-tool only
where a tool exists.

Numbering: this table is authoritative. notes/research/neatness.md
section 6 used NEAT026 for must-use-missing and NEAT041 for
enum-glob-in-match; the design numbering keeps NEAT026 as exhaustive-match
(the merge request used the design numbering), and those two research
rules map to the language-level must-use row (NEAT032-037) and to the
bound clippy `enum_glob_use` under NEAT026; research ids are superseded.

Full table with predicates, knobs and per-language tool coverage in the
research note section 7. Severity defaults are Warn or Advisory; every
threshold is a materialized knob under `[neat]`.

| Id | Rule | Polarity | Needs | Evidence (catalogue C, E_det) | First ten |
|---|---|---|---|---|---|
| NEAT001 | function-too-long (lines or statements) | Pn | syntax | contested; K36 C 0.5, E_det 0.23 | bound tool only, Advisory, off |
| NEAT002 | parameter-count over `max_params` (default 5) | Pn | syntax | K35 C 1.77, E_det 0.48 | 1 |
| NEAT003 | boolean-flag-parameter (positional bool) | P+ | syntax, types where available | K35 C 1.77, E_det 0.48 | 3 |
| NEAT004 | nesting-depth over `max_depth` (default 3) | Pn | syntax | K04 C 1.78, E_det 2.8 (highest) | 2 |
| NEAT005 | cognitive-complexity (Sonar definition) | Pn | syntax | K04 C 1.78, bound | bound tool only |
| NEAT006 | raw-loop: a loop whose body exceeds `raw_loop_statements` and is not a named unit | Pn | syntax | contested (ADV007), weakest | 9, Advisory, bound only |
| NEAT007 | section-comment: comments that label phases inside one body | P+ | syntax | no source beyond one voice, weak | 10 |
| NEAT008 | parameter-object-candidate: the same N parameters repeated across units | Pn | syntax | unmeasured in the catalogue | later |
| NEAT009 | magic-value | P+ | syntax | K25 E_det 0.63, low | bound tool only, Advisory, off |
| NEAT010 | effect-ceiling-exceeded: a unit marked core or honest whose lo exceeds its claim | P+ | effects capability | unmeasured in the catalogue | 8 |
| NEAT011 | effects-undeclared: public unit without a claim where `[neat] require_effects` is on | P- | syntax | unmeasured in the catalogue | 8 |
| NEAT012 | hidden-state-read: read or write of a mutable global from a unit not marked shell | P+ | scope graph | K12 C 2.25 (consensus high, mined low), E_det 0.63 | 4 |
| NEAT013 | ambient-source-call: clock, rng, env, fs, net, stdio, exit called from a unit not marked shell | P+ | callee vocabulary | K13 C 1.23, E_det 0.2 | 7 |
| NEAT014-018 | shell-depth, core-calls-shell, io-in-leaf, injected-dependency-missing, materialize-instead-of-visit | mixed | effects, scope graph | unmeasured in the catalogue | later |
| NEAT019 | command-query-separation | P+ | effects | unmeasured in the catalogue | off by default |
| NEAT020-026 | type rules: weakest-type-parameter, newtype-candidate, precondition-in-type, receipt-type, strong-id, parse-dont-validate, exhaustive-match (NEAT026; bound clippy wildcard_enum_match_arm, ts-eslint switch-exhaustiveness-check, IDE0010/0072) | mixed | types capability | unmeasured in the catalogue | later |
| NEAT027-029 | boundary rules: ad-hoc-data-structure, incidental-structure, duplicate-shape | Pn | syntax, digests | unmeasured in the catalogue | later |
| NEAT030 | thin-hook: a unit marked hook (or matched by the framework vocabulary) with more than `hook_statements` statements of logic | Pn | syntax | consensus-led, ranked after NEAT031 | 6 |
| NEAT031 | dispatch-site-owns-logic (the ruff PR pattern) | P+ | syntax | consensus-led (ruff PR pattern) | 5 |
| NEAT032-037 | language-level: const-fn-candidate, must-use, nodiscard, unnecessary-mutation, global-init, effect-row-widening | mixed | per language | unmeasured in the catalogue | bound tools |

Where an existing linter implements a rule better per language (clippy
too_many_arguments and cognitive_complexity, ruff PLR0913 and C901,
eslint max-params and complexity, golangci gocognit and funlen), frob's
`[[check.tool]]` stage binds that tool's finding under the NEAT id
(parser owned by gob-check, id map by frob-check, `source_rule` kept on the
finding; docs/design/shared/rules.md section 4) rather than re-implementing it; the universal implementation is for languages
without such a tool. Rule pages say which applies.


### 1.3 Knobs

Every threshold is a materialized knob under `[neat]` in `grimble.toml`:
`max_params` (5), `max_depth` (3), `raw_loop_statements`,
`hook_statements`, `guard_weight` (2), `require_effects` (off) and the
`[neat.effects]` callee vocabularies, which are views over the one atom
registry (binding.md 7.5).


Implementation status (grimble-lints `neat` module, Rust only): NEAT010 and
NEAT031 ship first. `neat::scan` reads each function as a unit and takes
`frob:honest`, `frob:pure`, `frob:core`, `frob:effects ATOMS`, `frob:shell`,
`frob:trusted` and `frob:dispatcher` from the comments above it. The
`effects(unit)` capability answers `gob_ir::Answer<EffectSet>` from a callee
vocabulary (`neat::Options::vocabulary`, matching a call path or its trailing
segments) with local callees followed transitively: Exact when every callee
resolved, otherwise Bounds whose `hi` is open. A `lo` outside the ceiling is
Contradicted and fires NEAT010 at Warn (the older wording "Error" is
superseded by this table); an open `hi` is Unverified, reported unresolved
and never clean. NEAT031 treats a function as a dispatcher when it is marked
or matches on one of its own parameters, and fires on a branch whose
condition weighs more than `guard_weight` (default 2): calls, plus 2 per
closure or nested branch group, plus the weight of any local feeding the
condition. The remaining syntax rules also ship for Rust: NEAT001 (`max_fn_lines`),
NEAT002 (`max_params`), NEAT003 (positional `bool` parameter), NEAT004
(`max_depth`), NEAT005 (`max_cognitive`, Sonar scoring), NEAT006
(`raw_loop_statements`), NEAT007 (two or more phase-label comments in one
body), NEAT008 (`param_object_params` repeated `(name, type)` pairs across
units), NEAT009 (`magic_values`), NEAT011 (`require_effects`), NEAT012 (a
`static mut` or interior-mutable static touched from a non-shell unit),
NEAT013 (a vocabulary call in a unit with no claim; claimed units are covered
by NEAT010) and NEAT030 (a `frob:hook` unit or one named with a
`hook_prefixes` prefix holding more than `hook_statements` statements). The
bound-tool-only rules NEAT001, 005, 006 and 009 are off by default (limit 0 or
flag false). `neat::Options::from_config` materializes the `[neat]` table from
its entries: the number, flag and list knobs above, `core_paths` (files whose
unclaimed units count as `frob:core`, applied by `neat::scan_at`) and
`effects.<path> = atom` vocabulary entries. Not yet done: Python and
TypeScript, NEAT031 `movable` wording, NEAT003 call-site part, NEAT012
captured reads, the bound-tool entries and `grimble check` wiring.


### 1.4 Decided

Decided (decision-log row D59, accepted 2026-10-04): grimble owns the
family (D4 of the 2026-10-04 consistency pass; README D63), the four
principles and the annotation vocabulary above; NEAT never penalizes small functions; CQS
off by default (Smith's `remove_if` is honest, Meyer's rule disagrees);


### 1.5 Open

Open for the owner:
1. Should `[neat] require_effects` default to on for the public surface
   of this repository from milestone 2 (dogfooding section 4.6), with
   the Rust adapter promoting precision by analysis so most units need
   no directive?
2. NEAT031's dispatcher-by-shape heuristic (a body that is mostly
   guarded calls) will have false positives on state machines; is
   an `accept` exception on NEAT031 acceptable as the opt-out (D120), or should the rule be
   Advisory until the heuristic is measured on this repository?


## 2. COH: function cohesion

### 2.1 Purpose

Provenance: accepted direction, owner questions 2026-10-08: "enforce a one
job per function rule, where we don't mix logic; how would you detect
that in the cross-language linter?" and "do we account for Python being
typed or untyped; will we ever mark something decidable as undecidable
because of types?" Builds on shared/universal-model.md (Bounds, May/Must,
section 4.6 annotate-or-opaque), section 1 of this file (effects, NEAT010-019,
NEAT031) and grmb-spec.md (layers). Reviewed by the formal review of 2026-10-08
(notes/review/formal-review-2026-10-08.md, section 5), whose findings
are applied here; citations are in its section 7. Beck's Composed
Method could not be fetched and is related work only.

"Does one thing" is not a syntactic property, so no single metric
decides it. It is decomposed into four signals, each a computable
question over U with Bounds, each its own rule so a finding says which
kind of mixing it saw. All are P+ (fire only on proof), report
Unresolved between their bounds. COH001-COH003 are Advisory until
measured precision (the precision ledger, N16) clears the ceiling: the
evidence is weak (five voices, no data; C21 is 0.5 percent and C23 0.4
percent of mined review comments), so Warn is earned, not defaulted. The
Bounds design is unchanged.


### 2.2 Rules

| Id | Mixing | Question over U | Needs |
|---|---|---|---|
| COH001 | independent jobs | the body's statements split into two or more data slices that share no variable other than parameters (output slices, Bieman and Ott 1994; Ott and Thuss 1993) | binders and refs (F2), def-use within the body, may-alias |
| COH002 | decision with effects | the unit both computes decisions (branches whose conditions depend on computed data) and performs effects in those branches, and is not marked `frob:shell` or `frob:dispatcher` (functional core, imperative shell; extends NEAT014-016) | effects capability, def-use |
| COH003 | mixed abstraction levels | the callees span layers further apart than `[coh] max_level_spread`: domain-level calls next to helpers of a lower project layer in one body (built-in operators and std string/slice methods are layer-neutral) (single level of abstraction; related to Beck's Composed Method) | apply_targets, layer of callee from the grimble model or module depth |
| COH004 | mixed vocabularies | identifiers and callees cluster into disjoint domain vocabularies (after the class-level conceptual cohesion of Marcus and Poshyvanyk 2005, applied to functions) | syntax; Advisory only (a heuristic, never Warn) |

NEAT031 (dispatch-site-owns-logic) stays the dispatcher-specific case.
COH adds no directive (section 2.4). A unit with a declared role
(`grimble:shell`, `grimble:core`) is judged against its role, so an
imperative shell may mix decisions and effects; the role claim itself is
verified by the effects rules. A unit that mixes on purpose without a
role (an intentional dispatcher, a deliberately fused hot loop) takes an
exception on the specific finding (`accept` with a reason, shared/rules.md),
which is visible, counted and expires; there is no opt-out marker.

#### COH001 with bounds

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

#### Cross-language

Every input is a universal capability, so the rules are written once
(`applies = universal`, shared/rules.md) and run wherever the adapter
declares the capabilities: def-use needs F2, COH002 needs `effects`,
COH003 needs `apply_targets` and a layer source. A language without the
capability gets Unresolved with the missing capability named, never a
silent pass (Theorem 3).

The COH003 layer source (`grimble_check::layers`) is tried in this order
and the two are never mixed, because their scales are not comparable:

1. The grimble model. A `node` with `attr layer = N;` and `owns SEL;`
   puts every function defined in a file the selector surely matches on
   layer `N`. Nodes with a missing, non-numeric or repeated-different
   layer, or an unparsable selector, are skipped with a warning. A file
   owned by nodes with different layers has no layer. Once the model
   declares any layer it is the sole source: files it leaves out stay
   unplaced instead of falling back to depth.
2. Module depth, only when the model declares no layer. A deeper
   directory is a lower layer: the deepest file sits one above the
   primitive layer, each directory level up adds one, and equal depths
   share a layer. When every file has one depth (a single-module repo)
   depth says nothing and nothing is placed.

A callee is mapped by its last path segment to the layer of the files
defining it. A name defined in no walked file is external (a library call)
and is ignored; a name defined on several different layers, or in a file
no layer places, is left out: it cannot prove a spread, so it never fails
or warns (the names are logged at debug level). Built-in operators (`[]`,
slices) and std string/slice methods (`find`, `trim`, `strip`) are
layer-neutral, as is a method call on any receiver other than
`self`/`this`/`cls`; test files are not judged.


### 2.3 Knobs

Ownership note: grimble. The COH rules live beside NEAT in grimble-lints (they
judge code structure, not work accounting; docs/design/shared/charter.md section 1), with
knobs under `[coh]` in `grimble.toml`. frob runs them only through the
sibling protocol.

Status: COH001 is a registered rule (`grimble-check`, `src/rules/coh001.rs`) run by the same
pass as COH002 and COH003 (`coh_pass::analyze`). Its knobs are `[coh] min_slice_statements`
(default 2) and `[coh] trivial`, which adds to COH001's built-in logging vocabulary. COH002 is a registered rule (`grimble-check`, `src/rules/coh002.rs`) run by
`grimble check`. COH002 decides what is an effect from the language's effects capability
(`grimble-check`, `src/effects.rs`), which classifies a call from its qualified path: `fs.write`,
`os.remove`, `subprocess.run` are effects, `console.log`, `logging.info` are trivial. Every fact
the capability holds is registry data: IO qualifiers from the fs/net/process atoms, and the
non-atom `coh002.methods`, `coh002.qualifiers` (persistence modules such as `sqlite3`,
`localStorage`), `coh002.trivial.qualifiers` and `coh002.trivial.names` vocabulary classes of
`packs/core-effects/atoms.toml`. A call the
capability cannot place (an aliased or imported bare name, an unknown receiver) leaves the verdict
Unresolved, and so does any language without an effects capability. The `[coh]` table holds two
keys, `effect_calls` and `trivial`: project overrides that add to the capability (matched on the
callee's last path segment); both default to empty, a name in both lists is trivial. Unknown
`[coh]` keys are rejected. The capability tables live in grimble-check until the adapters declare
the `Effects` capability themselves.
The `[coh]` table also holds `max_level_spread` (default 1), the largest layer distance
COH003 tolerates between the callees of one unit; `min_slice_statements` (default 2) is the COH001
floor for a component to count as a job. COH003 is registered and runs in the same pass as COH002
(`coh_pass::analyze`): the pass first folds every file, collects the functions each defines, asks
`layers::coh003_options` for the callee layers (grimble model first, module depth otherwise),
then judges each unit. A repo where no layer source places a callee (no layered model node and
every file at one directory depth) raises no COH003 finding; the unplaced callees are only
logged at debug level. Callees that no walked file defines (`console.log`, library calls) are
external and never placed. The
report cache key carries a `coh001-v3` tag, the COH001 and COH002 vocabularies
`min_slice_statements` and `max_level_spread`, so a change to any of them (or to a `.grmb` file, which is part of the
walk digest) recomputes the report. Every cached grimble report (binding, architecture,
PATH-family, COH and LOG) is also keyed on a digest of its rule table (id, version, severity,
gates, nature, applicability), so adding or re-versioning a rule misses stale reports. A unit carrying a `grimble:core` or `grimble:shell`
directive on its function is judged against that role (COH002 reads it from the
directive; a unit with no directive is judged as written). Both on one unit is a
conflict and the stricter `core` wins. A `grimble:shell` claim is reported as
Unresolved until an effects rule verifies it.


### 2.4 Decided

#### Consequences

- New capability fields: `dependence(unit)`, the data and control
  dependence graph with Must/May edges (F2),
  `type_precision` on every type-dependent answer, Unknown reason
  classes (extending the typed Unresolved reason of ~YR7MCXF, D106).
- Python adapter: a bound-tool importer for ty or pyright types
  (hullbreach platform already has `ty.toml`); TypeScript: tsc types;
  C#: Roslyn semantic model through the dotnet adapter (shared/code-model.md).
- COH001-004 ship after the GRL executor so they are written in GRL
  where expressible (D76); COH001's component counting is a catalog
  relation (`slices(unit)`) the executor exposes.

#### Directive admission (D120)

Directives are the comment DSL every product reads, and each one is
something a user must learn, an agent must emit correctly and a parser
must keep. The same discipline as verb admission (shared/cli-contract.md 4.0, D104)
applies: a directive exists only if it passes all three tests, and a
registry test fails when a registered verb has no row naming them.

1. Not derivable: it states a fact the tools cannot compute from code,
   config or the model (a framework entry point that gob-frameworks
   detects is not a directive; an effect claim on an unanalysable body
   is).
2. Not an exception: if its only effect is to silence one rule at one
   place, it is an `accept` exception on that rule (shared/rules.md:
   reason, owner, expiry, counted), never a dedicated marker.
3. Consumed: at least two rules consume it, or it is a claim that a rule
   verifies (VERIFIED, CONTRADICTED or UNVERIFIED, section 1.2).

Namespace rule, restated: a directive is namespaced by its consumer.
Work accounting (tickets, todos, doc and test bindings, exceptions) is
`frob:`; claims about the design of code (effects, roles, model
bindings) are `grimble:`; design-system verdicts are `crunk:`. The
previous placement of claim verbs under `frob:` (shared/code-model.md section
4) is reversed: frob never consumes them.

Applied to the current registry (docs/design/shared/code-model.md section 4 milestone-2
table, docs/design/grimble/binding.md section 12 binding verbs):

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

#### Purity and honesty: inferred first, claimed only where inference cannot reach (D121)

Owner question 2026-10-08: "can we detect purity; is a purity or
honesty directive useless?" Definitions (notes/research/neatness.md
PF-1): pure = no effect at all (`none`); honest = touches the outside
world only through its parameters (it may mutate what it is given,
never globals, clock, randomness, IO or singletons).

Detection is the effects capability of section 1.2: `effects(unit)`
returns Bounds{lo, hi}. lo is what the body provably does; hi is the
closure over every callee, where an unresolved call, an opaque body
(FFI, `unsafe`, `eval`, reflection), a dynamic site (docs/design/shared/universal-model.md section 10) or an
external symbol without a vocabulary entry widens hi to `any`.

- Proven pure: hi = none. Proven honest: hi contains only effects on
  storage reachable from parameters (`writes(param)`), which needs the
  may-alias facts of section 2.2 to tell a parameter from a global.
- Proven impure or dishonest: lo exceeds the class.
- Otherwise Unknown, with the widening call sites as witnesses.

So yes, purity is detectable wherever the call closure is resolvable,
and every unit gets an inferred class with no annotation: in Rust most
safe code resolves (with a vocabulary for interior mutability: `Cell`,
`RefCell`, atomics, `static mut`); in C# and Java most of it does with
types; in Python and TypeScript precision follows docs/design/shared/universal-model.md section 10 (checked
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


### 2.5 Open

None recorded. COH001 to COH003 stay Advisory until the precision ledger
(N16) clears the ceiling.

## 3. CI and DK: CI/CD and deployment languages

### 3.1 Purpose

#### What the field does

The sample is stars-ranked, not usage-ranked, and detection is YAML
heuristics, so every figure carries a few points of error. The shape is
clear anyway (percent of the 930 repositories on GitHub Actions unless
stated):

| Practice | Prevalence | Reading |
|---|---|---|
| GitHub Actions as the CI | 87.0 percent of all 1069 | the one platform worth first-class support |
| `push` and `pull_request` triggers; matrix builds; `workflow_dispatch` | 95.1, 93.1, 77.3, 71.6 | universal shape: build on both events, across OS and versions |
| every external action pinned to a commit SHA | 23.4 (58.8 percent of all `uses:` refs) | the largest gap between advice and practice |
| top-level `permissions` in every workflow | 21.6 | least privilege is rare |
| `concurrency` declared | 54.9 | half cancel superseded runs |
| `timeout-minutes` on every job | 2.6 (75 percent of jobs have none) | almost nobody bounds a hung job |
| zizmor: at least one high-severity finding | 88.9 | `unpinned-uses` 73.0, `excessive-permissions` 72.8, `artipacked` 85.8, `template-injection` 47.7 |
| provenance attestations; sigstore; SBOM; scorecard; zizmor in CI | 12.3, 5.9, 6.3, 7.2, 10.5 | supply-chain evidence is the frontier, not the norm |
| trusted publishing (OIDC) among PyPI publishers; among crates.io publishers | 72, 68 | token-less publishing has won where registries support it |
| Dockerfiles present; Helm; Terraform; Ansible; Pulumi or CDK | 38 percent of repos; 3.9; 3.7; 1.4; 0 | containers are common, infrastructure languages rare in tool repos |

What a repository cannot show, so no rule may claim it: branch
protection, required checks, the default token permission setting,
environment secrets, rulesets. Rules about these are Unresolved by
construction and say so.

#### What the practices protect against

| Threat or failure | Practices that address it |
|---|---|
| Compromised third-party action (supply chain) | SHA pinning, Dependabot or Renovate on actions, scorecard, zizmor |
| Token exfiltration and privilege escalation | top-level `permissions: contents: read`, job-level grants, no `pull_request_target` with head checkout, `persist-credentials: false` |
| Script injection through event data | no `${{ github.event.* }}` inside `run:`; env indirection |
| Release mistakes and forged artifacts | publish only from tags or releases, OIDC trusted publishing, provenance attestations, signing, SBOM |
| Hung or runaway CI cost | `timeout-minutes`, `concurrency` with cancel-in-progress |
| Platform regressions | OS and version matrices, MSRV jobs, cross-compilation |
| Dependency and licence drift | Dependabot, Renovate, cargo-deny, lockfiles committed |
| Docs rot and unreproducible builds | pages deploy from CI, pinned toolchains, Nix flakes, devcontainers |

#### Decision: bind the security tools, own the policy and consistency rules

The design goblin does not rebuild zizmor, actionlint, hadolint,
checkov, tflint, kube-linter or ansible-lint. Their checks overlap the structural
security rules almost entirely and parity would be a treadmill against
GitHub's schema. frob orchestrates them through `[[check.tool]]` stages
with JSON parsers (zizmor `--format json-v1`, actionlint `-format '{{json
.}}'`) so their findings carry frob ids, exceptions, evidence and
Unresolved semantics. Two bindings are mandatory lessons from the
corpus: actionlint's `runner-label` noise needs the repository's custom
labels passed in, and a tool that lags the GitHub schema returns
Unresolved, not a violation.

grimble owns (family CI and DK) what those tools cannot see: presence and policy rules that a
repository decides (which permissions, which timeouts, publish only from
tags, OIDC required) and cross-file consistency between CI and the
repository (the toolchain pinned in CI equals rust-toolchain.toml; the
lint command in CI equals the one frob runs; a workflow that publishes a
crate exists for every publishable crate; Dependabot covers every
ecosystem present). These are joins over the universal model between
the workflow language and the manifests (CI012 reads the manifests
through the F2 manifest adapter, grmb-spec.md 20.2), which is
exactly the cross-language structure the universal model exists for.


### 3.2 Rules

#### CI/CD files as languages in the universal model

GitHub Actions YAML: a workflow is a `unit(kind=workflow)` with
`group(order=concurrent)` of jobs; each job is a `unit` with
`group(order=sequence)` of steps; `uses:` is `apply(kind=instantiate)`
whose head resolves to an external identity (owner/repo@ref) with
status Must when SHA-pinned, May when tag-pinned (the referent can
move); `needs:` is `apply(kind=dependency)`; triggers are entrypoints
(`attr(on)`); `permissions`, `concurrency`, `timeout-minutes` are
`attr` nodes; `${{ }}` expressions are a `region(kind=embedded,
lang=actions-expr)` with references into the event context (a scope
the adapter models as an external, May-status scope); `run:` bodies are
`region(kind=embedded, lang=shell)` and shell is a language with
string-code opaqueness (shared/universal-model.md 4.6). Reusable workflows and
composite actions are units in other artifacts; `secrets: inherit` is a
flow edge the model can see.

Dockerfile: one `unit` per stage (`FROM ... AS name`), `FROM` is
`apply(kind=instantiate)` to an image identity (Must when digest-pinned,
May for tags, Unknown for `latest`), `COPY --from` is a dependency edge
between stages, `RUN` is an embedded shell region, `USER`, `EXPOSE`,
`HEALTHCHECK` are attributes.

Implementation status: `gob-symbols` ships `ActionsAdapter`
(`.github/workflows/*.yml|yaml`) and `DockerfileAdapter` (`Dockerfile`,
`Dockerfile.*`, `*.dockerfile`) at F2, selected by path through
`adapter_for_entry`. Jobs and stages are units; `uses:`, `FROM` and
`COPY --from=image` become `Instantiates` edges (Must for a commit SHA or
digest, May for a tag or branch, Unknown with `GapReason::Floating` when
unpinned or `latest`); `needs:`, `FROM stage` and `COPY --from=stage|index`
become `Depends` edges (Must, or Unknown when the target is missing).
Steps, `${{ }}` expression regions and shell regions are not modelled yet,
which is the gap to F3.

Terraform and Helm: resources and templates are units; references are
Must inside a module, May across providers until schemas are loaded;
both need an external binary or provider schema for anything beyond
F2, which is why they are bound rather than owned.

Fidelity targets: GitHub Actions F3 first (a CST-preserving YAML
reader with the `gha-expr` and shell islands as regions; the survey,
section 9.4) and F4 once comments and pin comments bind to targets,
Dockerfile F3 (own adapter, small grammar), Terraform and Helm F1 through tree-sitter with
bound tools for the rest.

#### The CI and DK rule families

Each rule names its threat, a decidable predicate over the U encoding
in section 3.2, its polarity (shared/universal-model.md 4.2), a default severity
and who implements it. Corpus rates are in the research note
(notes/research/cicd-survey.md section 9.3, the numbering authority:
ids are permanent, D32). A repository overrides severity with
`[rules.<id>] severity` (there is no separate severity table). Every
threshold and list is a materialized knob under `[ci]` in
`grimble.toml`. The survey's severity "note" is Advisory here.

| Id | Rule and predicate | Polarity | Default | Implemented by |
|---|---|---|---|---|
| CI001 | pinned-ref: no external `uses:` whose ref is not a 40-hex SHA unless the owner is in `allow_tag_pins_for` | P+ | Warn | bind zizmor `unpinned-uses`; grimble fallback |
| CI002 | permissions-declared: a workflow with no top-level `permissions` and not every job declaring `permissions` | P- | Warn | grimble |
| CI003 | no-top-level-write: top-level `permissions` contains a `write` scope or `write-all` | P+ | Warn | grimble (zizmor overlaps) |
| CI004 | concurrency-on-pr: a push or pull_request workflow with no `concurrency` at workflow or job level | P- | Advisory | grimble |
| CI005 | job-timeout: a job (not a reusable-workflow call) without `timeout-minutes`, or above `max_timeout` | P- | Advisory | grimble |
| CI006 | no-prt-head-checkout: a `pull_request_target` or `workflow_run` workflow with a checkout whose ref or repository names the PR head | P+ | Error | bind zizmor `dangerous-triggers`; grimble fallback |
| CI007 | no-event-interpolation-in-run: a `run:` text containing an expression whose context is in the `contexts` set (title, body, head ref, commit message and similar); a lexical scan of the opaque shell payload (shared/universal-model.md 2.2) | P+ | Error (narrow set), Advisory (broad) | bind zizmor `template-injection` |
| CI008 | publish-only-from-tag: a registry publish step in a workflow triggered by pull_request, pull_request_target or an untagged push | P+ | Warn | grimble (`registries` vocabulary) |
| CI009 | publish-via-oidc: a publish job for a trusted-publishing registry that uses a token-named secret and lacks `id-token: write` | P+ | Advisory (Warn in strict) | grimble |
| CI010 | checkout-no-persist: `actions/checkout` without `persist-credentials: false` in a workflow that uploads artifacts or runs third-party code | P+ | Advisory | bind zizmor `artipacked` |
| CI011 | prt-least-token: a `pull_request_target` workflow without explicit read-only `permissions` | P- | Error | grimble |
| CI012 | ci-repo-consistency: toolchain pin file versus workflow toolchain, `rust-version` versus the matrix, Dependabot ecosystems versus manifests, CODEOWNERS covering `.github/**`, frob verbs versus workflow commands | P0 | Warn | grimble (the unique join, through the F2 manifest adapter) |
| CI013 | no-secrets-inherit: a job calling an external reusable workflow with `secrets: inherit` | P+ | Advisory | native fallback (job-level `uses:` of a non-local callee with the scalar `secrets: inherit`); a bound zizmor `secrets-inherit` finding replaces it |
| CI014 | gha-syntax-and-schema: any actionlint finding other than an unknown runner label when labels are not configured | P+ | Warn | native structural subset (no `on`, no jobs, job without `runs-on`/`uses` or steps, call job with `steps`, step without exactly one of `run`/`uses`); a bound actionlint stage covers the rest and replaces it |
| CI015 | action-currency: an external action from an archived repository or on an end-of-life Node runtime (an offline table; "pin behind the latest release" is covered by Dependabot or Renovate presence under CI012, and an opt-in online check is `frob audit --online`, open question 3) | P+ | Advisory | native offline table of archived actions and end-of-life Node majors; SHA, branch, expression, local and docker refs are not judged; a bound zizmor `archived-uses` finding replaces it |
| CI016 | trust-from-protected-ref: a `pull_request_target` or `workflow_run` workflow runs frob, grimble or crunk with any trust other than `--trust-from` a protected ref (shared/security.md 2.11, D82). Conservative: fires on `check` with no `--trust-from`, on a head-ref value (HEAD, `refs/pull/`, `pull_request.head.*`), on another `--trust*` flag and on the `trust` verb; `--skip-tools` is exempt; an unclassifiable expression or variable value, or an `if:` on `head.repo.fork` or `ref_protected`, is Unresolved; a literal ref is taken as protected | P+ | Error | native |
| DK001 | docker-non-root: the final stage has no `USER` other than root or 0 | P- | Advisory | grimble or hadolint DL3002 |
| DK002 | docker-base-pinned: an external `FROM` without an `@sha256:` digest | P+ | Off (opt-in; needs automation) | grimble |
| DK003 | docker-no-latest: an external `FROM` with no tag or `:latest` | P+ | Warn | grimble or hadolint DL3006 and DL3007 |
| DK004 | docker-no-pipe-to-shell: a `RUN` text in which `curl` or `wget` output is piped to `sh` or `bash`; a lexical scan of the opaque shell payload; allowlist by URL host | P+ | Advisory | grimble or hadolint |


### 3.3 Knobs

### 5.1 One report per rule and file (tool versus native)

`grimble check` runs `grimble_ci::analyze` over the walk on every run
(uncached, because CI012 reads files outside the walk) and reports its
findings with the other grimble families. Where a rule has both a bound
tool stage and a native lexical fallback (CI001, CI006, CI007, CI010
with zizmor), the two are never both reported for one workflow: the
tool finding is authoritative for a (rule, file) pair, and the native
finding for that pair is dropped before severity overrides and
exceptions apply. Line numbers and messages are not compared, since the
sources never agree on them. When the tool reports nothing for the pair,
or is not installed, the native finding stands. `[rules.<id>]` overrides
(including off) apply to whichever finding remains. The `[ci]` knob
table is not read yet; the defaults of `CiConfig` apply.

Terraform, Helm, Kubernetes and Ansible: bind checkov, tflint,
kube-linter and ansible-lint; nothing is owned there until a
repository in the fleet needs it.

Implementation status (grimble-ci): the crate `grimble-ci` implements CI001, CI002, CI003, CI004, CI005,
CI006, CI007, CI008, CI009, CI010, CI011, CI012 (toolchain pin, `rust-version` floor, Dependabot ecosystems, CODEOWNERS
coverage of `.github`, and the `frob` verbs `run:` scripts invoke against a static verb table) and DK001 to DK004 as `#[rule]` declarations with mdtest pages. It is a library
that `grimble check` runs through `grimble_ci::analyze` (section 3.3); its verdicts are the `Verdict` type shared with
grimble-arch from grimble-verdict, so the two passes do not depend on each other. CI001, CI006, CI007 and CI010 are
native lexical fallbacks for the zizmor-bound rules (they do not parse the shell); `CiConfig`
gains `allow_tag_pins_for` (owners exempt from CI001) and `contexts` (extra narrow CI007
contexts). CI013 to CI015 are native structural fallbacks for the zizmor and actionlint findings (the tool stage dedupes against them by `dedupe_ci`), and CI016 is native; none needs the network.


### 3.4 Decided

#### Where this lands

CI and DK are grimble families (D4 of the 2026-10-04 consistency pass,
README D63): the placement test of shared/charter.md holds because these
rules make sense in a repository with no tickets, docs policy or release
process. They are implemented in a new crate `grimble-ci`; NEAT stays in
`grimble-lints`. The GitHub Actions and Dockerfile adapters live in
gob-languages behind features `actions` and `dockerfile`, with
gob-symbols adapters producing the U terms. frob orchestrates through
the sibling contract (grmb-spec.md 20.2) and through `[[check.tool]]`
stages. The adapters are milestone-2 tickets after gob-ir (shared/build-test-ci.md,
Milestone 2 item 7); this repository adopts zizmor and actionlint
through frob's `[[check.tool]]` stage first, before the adapters exist,
with their JSON parsers in gob-check (`tool_parse.rs`) and id maps in frob-check.


### 3.5 Open

1. Default severities: should CI006 and CI007 (injection and token
   theft) be Error from the start even though a quarter of top
   repositories would fail, or Warn with a ratchet?
2. Should frob ship a generated "CI baseline" for new repositories
   (`frob init --ci`: pinned actions, read-only permissions, timeouts,
   concurrency, OIDC publish templates per ecosystem), given that the
   survey shows the defaults are what most repositories never fix?
3. CI015 needs the network to know the latest release; keep it offline-
   Unresolved and rely on Dependabot presence, or allow an opt-in online
   check?


## Decision records

The decisions homed here. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D59

NEAT rule family (rule-families.md section 1): honesty with a grimble:effects vocabulary (spelled frob:effects when accepted; D120) and native markers, verified/contradicted/unverified claims where unverified is never clean; one level of abstraction (raw loops, section comments, dispatchers that own logic); caller-friendly signatures; thin hooks; never penalizes small functions; command-query separation off by default; existing linters bound where better per language; first ten rules named (accepted 2026-10-04 on the owner's instruction to resume implementation after review)

### D60

CI/CD (rule-families.md section 3): bind zizmor, actionlint, hadolint, checkov, tflint, kube-linter and ansible-lint through tool stages with JSON parsers; frob owns policy and CI-to-repository consistency rules (CI001-015, DK001-004) over GitHub Actions and Dockerfile adapters in U; infrastructure languages bound only; this repository adopts the zizmor and actionlint bindings first (accepted 2026-10-04 on the owner's instruction to resume implementation after review)

### D118

One job per function: COH001 output-slice groups over the data and control dependence graph with lo/hi bounds, COH002 decision with effects, COH003 mixed abstraction levels, COH004 vocabularies (Advisory); owned by grimble

### D120

Directive admission: a directive must be not derivable, not an exception in disguise, and consumed by two rules or verified; directives are namespaced by consumer (frob: accounting, grimble: design claims, crunk: design verdicts); frob:effects, grimble:effect, frob:pure, frob:honest merge into grimble:effects; core, shell, calls move to grimble:; dispatcher, trusted, idempotent, hook dropped

### D121

Purity and honesty are inferred from effects Bounds; NEAT037 ratchets inferred classes against the base without annotation; grimble:effects claims are for opaque boundaries and public contracts, and answers that rely on an unverified claim are conditional (reason assumed:claim), clean in CI, Unresolved at release
