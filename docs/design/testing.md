# Testing rules against the universal model (D106)

Status: current
Owner: gob
Decisions: D106, D103
Audience: rule author

Provenance: accepted, coordinator decision 2026-10-06 (owner: "make sure the
lints, mdtests, snapshots and so forth are designed with [the universal
model] in mind"). Evidence: notes/research/u-testing-audit.md (the audit
of D103 against U), notes/research/rule-testing.md (ruff, ty, clippy,
biome, oxc, rust-analyzer). Amends D103: ruff and ty test a two-valued
world (a case has diagnostics or not); U is not two-valued
(universal-model.md 4.1, 4.2), so the harness asserts U's outcomes, not
only the presence of findings.

## 1. Outcome classes

Every test case expects exactly one class, the vocabulary of grl-spec.md
section 9, shared by gob-mdtest, GRL examples and the grimble-bind corpus
(one example grammar for the whole project):

| Class | Meaning | What the runner checks |
|---|---|---|
| `fire` | the rule found what it looks for | the findings equal the markers |
| `clean` | the rule examined at least one subject and found nothing | zero findings of the rule at any severity, Unresolved included, and `subjects_examined >= 1` (or the stated `subjects=`), and the rule applied |
| `unresolved` | the rule could not decide | an Unresolved finding with the stated reason (`reason=`), required or not |
| `notapplicable` | the rule cannot apply to this artifact by construction | the rule reported NotApplicable with the stated reason, and no finding |

Modifiers `known-gap` (an Unresolved the project accepts, with a ticket)
and `fixed` (the case after applying the fix) come from grl-spec.md 9.

A clean result is certified, never inferred from silence: a rule that
examined nothing, did not apply, or was given a file no adapter reads does
not pass `clean`. This is universal-model.md 4.2 (subject accounting)
made executable.

The runner returns a `RuleReport` (rule, subjects total and examined,
not-applicable reason, findings) and every Unresolved finding carries a
typed reason (`Finding.reason`), never a reason parsed from message text.

## 2. Markers and strictness

Markers name the severity or class: `error:`, `warn:`, `advisory:`,
`unresolved[REASON]:` (optionally `required`), with optional column and
message text. A finding with no span (a rolled-up Unresolved, a repo-scope
finding) is asserted by a header expectation on the case.

Strict mode (ty's "unexpected error") counts every class: an Unresolved
or Advisory finding of a selected rule that no marker matches fails the
case, so a corpus author can never silence honesty to make a test pass.

## 3. Required cases per rule

Derived from `RuleMeta` (polarity, tier, `must_measure`, `needs`) and
checked by the coverage meta-test, with a shrink-only allowlist keyed by
(product, rule, case kind), each entry naming a ticket:

| Rule property | Required cases |
|---|---|
| every rule | `fire`; `clean` over at least one subject |
| polarity P+ | `unresolved`: the offender is reachable only through a May edge or sits in an opaque region |
| polarity P- | `unresolved`: the good thing is present only on a May edge, or the needed answer is Unknown |
| polarity P0 | `unresolved`: one side is not Exact |
| polarity Pn | `unresolved`: the count is only bounded (lo <= N < hi) |
| polarity Pc | `unresolved`: the path runs only through May edges; the poisoned frontier is named |
| `must_measure` | `unresolved reason=vacuous required`: zero subjects is Unresolved, never clean |
| tier Universal | the language matrix of section 4 |
| lexical rule (`needs = Lexical`: text, literals, prose only) | `opaque_fire`: an `expect=fire cell=island` block, a `fire` inside an opaque region, beside an `unresolved` structural rule over the same region |

Each rule's fire and clean cases live in one suite file.

## 4. The language matrix for universal rules

A universal rule is tested in every fidelity class, not only in the
language it was written for: Rust (F3), Python (F2), TypeScript (F2), C#
(F1), markdown (F4), a text file with no adapter (F0), a binary file and
an embedded opaque island. The expected class of each cell is derived
from the rule's `needs` and the adapter's capability cells; a written
expectation that disagrees with the derived one fails, so the matrix
cannot be satisfied by copying. Parity cases render one logical shape in
three languages with one expectation.

The harness is `gob_mdtest::matrix` (blocks carry `cell=` and `parity=`); gaps are
`[[matrix_gap]]` entries in `crates/gob-mdtest/coverage-allowlist.toml`, each with a
ticket, and the list may only shrink.

An artifact with no adapter yet is `unresolved` with reason `fidelity`
for capability rules, rolled up to one finding per rule and language
(universal-model.md 3.3, 6: the worst case is F0 with everything
Unresolved). `notapplicable` is reserved for binary artifacts and for
languages that lack the feature by construction (a declared
NotApplicable capability cell).

## 5. Fidelity is measured, not claimed

An adapter's fidelity level is derived from its conformance corpus
(universal-model.md 3.3: F1 units and containment, F2 Must lexical edges,
F3 apply edges with declared status, F4 attributes, bound comments,
regions and phases); the test fails when the declared level differs from
the measured one in either direction. Every adapter ships a capability
matrix snapshot, a garbage-input case (no panic; Unresolved or
NotApplicable) and a partial-parse case. `frob doctor --languages`, the
languages page and the README table are generated from the same data.

## 6. Fixes and snapshots

The fix invariants run for every case with a fixable finding (ruff's
harness): a fixpoint within 10 rounds, a reparse after each round with
parse status and opaque or hole counts never degrading, no fixable finding
left, and no finding changing class from `fire` to `unresolved` (a fix
that hides code inside a macro or an opaque region fails).

Snapshots render the outcome class, the Unresolved reason in words and its
remedy, and the fix diff with its tier. The snapshot update mode never
changes a case's outcome class silently; a class change needs an explicit
second switch.

## 7. Polarity conformance and the ecosystem layer

A standard small repository per polarity (a May-only edge, a Must edge,
an opaque region, an Unknown visibility) is run against every shipped
rule, so "the rule behaves as its declared polarity says" is a test, not a
claim (universal-model.md 4.5, Theorem 3: never an Error or Warn whose
premise is false). The ecosystem check (build-test-ci.md 6) reports files
and subjects examined per rule and language, and a drop in subjects
examined is a regression even when the finding count falls.

## 8. Incompleteness: the oracle column (cohesion.md 2.3)

Honesty keeps frob from a false answer, not from answering Unknown too often,
so a corpus case also carries the true answer, known by construction. A case
(`gob_check::incompleteness`) names a language, a capability, the `oracle`
answer (`yes`, `no`, or `unknown` when genuinely undecidable) and the
`observed` answer. Per language and capability the harness reports the
false-Unknown rate: cases answered Unknown while the oracle is decided, over
all cases whose oracle is decided (undecidable oracles are not counted).

The gate compares that rate with a committed baseline
(`crates/gob-check/tests/fixtures/incompleteness/baseline.toml`):

- a rate above the baseline's fails like a regression; a lower rate passes and
  the baseline is then refreshed with `Report::to_baseline_toml`;
- a cell with no baseline is held to zero; a baselined cell that no longer has
  a decidable case fails as unmeasured (the same rule as a drop in subjects
  examined, section 7);
- a false Must (a decided answer that differs from the oracle, or a decided
  answer to an undecidable question) fails always and is never baselined.

Each case also carries a probe (`file`, `query`, `source`) that the real
adapter reads (`gob_check::incompleteness_live`): `visibility` is the symbol's
declared visibility, `imports` is whether the complete parse lists the target,
`resolve_ref` is Yes only for a proven (Must) call edge, and a capability the
language's adapter does not provide is Unknown. The test `oracle_live` fails
when the committed `observed` column differs from these live answers (a source
that no adapter parses is an error, not a verdict, so a flaky parse never
flips the column). Regenerate the column deliberately with
`FROB_BLESS_ORACLE=1 cargo test -p gob-check --test oracle_live`, then review
the diff and refresh `baseline.toml` by hand if a rate moved.
