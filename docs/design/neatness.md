# Neatness: the NEAT rule family

Status: draft
Owner: grimble
Decisions: D59
Audience: rule author

Provenance: DRAFT under T-0001; decision D59 is accepted (2026-10-04).
Ownership note: grimble. The NEAT rules live in `grimble-lints` (boundaries.md
section 2.5), their knobs under `[neat]` in `grimble.toml`, and frob
only orchestrates the bound tool stages that feed them. Evidence:
notes/research/neatness.md (Logan Smith's channel, 13 videos; Tony Van
Eerd, Sean Parent, Robert Martin, Verse effect specifiers; adjacent
sources; what clippy, ruff, eslint, golangci-lint, clang-tidy, PMD and
checkstyle already enforce; the 37-rule catalogue with decidability).
Depends on docs/design/universal-model.md (answer lattice, polarity,
capabilities, section 4.6 annotate-or-be-opaque).

## 1. What "neat" means here

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

## 2. The ruff PR as the canonical example

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

## 3. Effects: the annotation vocabulary

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
  (code-model.md section 4 has the table and the namespace rule).
- The atoms are the shared registry's (grimble-model.md 9.6), which is
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

## 4. The catalogue (37 rules; the first ten ship first)

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
finding; rules.md section 4) rather than re-implementing it; the universal implementation is for languages
without such a tool. Rule pages say which applies.

## 5. Decided and open

Decided (decision-log row D59, accepted 2026-10-04): grimble owns the
family (D4 of the 2026-10-04 consistency pass; README D63), the four
principles and the annotation vocabulary above; NEAT never penalizes small functions; CQS
off by default (Smith's `remove_if` is honest, Meyer's rule disagrees);
unverified effect claims report Unresolved; thresholds materialized.

Open for the owner:
1. Should `[neat] require_effects` default to on for the public surface
   of this repository from milestone 2 (dogfooding section 4.6), with
   the Rust adapter promoting precision by analysis so most units need
   no directive?
2. NEAT031's dispatcher-by-shape heuristic (a body that is mostly
   guarded calls) will have false positives on state machines; is
   an `accept` exception on NEAT031 acceptable as the opt-out (D120), or should the rule be
   Advisory until the heuristic is measured on this repository?
