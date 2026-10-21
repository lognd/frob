# mdtest corpus format

A markdown file is a suite. Fenced code blocks are test cases.

## Naming

`#` and `##` headings name the cases beneath them. A block is reported as
`Heading / Subheading #N (line L)` where `L` is the fence line in the file.

## Suite header

An HTML comment outside any fence sets a default for the blocks after it:

    <!-- mdtest: rule=MDT001 -->

### Snapshot diagnostics

    <!-- mdtest: snapshot-diagnostics -->

(also accepted alone as `<!-- snapshot-diagnostics -->`, and combined,
e.g. `<!-- mdtest: rule=MDT001 snapshot-diagnostics -->`). Every block after
the header, once its markers pass, also renders all findings the runner
returned with the full text renderer of `gob-diagnostics` (no color; source
excerpt, labels, help) and asserts the text with insta. One snapshot per
block, in `snapshots/` beside the markdown file, named
`<file-stem>__<heading-path>_<ordinal>.snap` (the fence line is not part of
the name). Clean blocks snapshot the empty rendering. A changed rendering
fails the case and insta prints the diff on stderr. Write or refresh
snapshots with `INSTA_UPDATE=always` (or `cargo insta review`); CI runs with
`INSTA_UPDATE=no`, so a missing snapshot fails.

## Info string

    ```rust rule=MDT001 expect=fire file=src/lib.rs config="a = 1"

- first token: the language (`rust`, `py`, `toml`, ...).
- `rule=ID`: rule under test; required unless the suite header sets it.
- `expect=fire|clean|unresolved|notapplicable`: required; see Outcome classes.
- `reason=TEXT`: unresolved or notapplicable only; for unresolved a reason
  code (`hole`), for notapplicable a substring of the reported reason.
- `subjects=N` / `subjects>=N`: assert the rule's examined subject count
  exactly or at least. `expect=clean` defaults to `subjects>=1`.
- `rules=A,B`: extra rules the case selects; see Strict mode.
- `fidelity=` / `parse=`: recorded for the language matrix; not yet enforced.
- `known-gap=~TICKET`: expect=unresolved only; the block records a gap that
  the ticket will close.
- `fixed`: expect=clean only; the block is the regression for a former gap.
- `config=<inline toml>`: optional; quote with `"` when it has spaces.
- `file=<name>`: optional; defaults to `case.<ext>` chosen by language.

## Markers

A comment (`//`, `#`, or `<!--`) holding a marker word asserts a finding.
The full form is

    // WORD: [COL] RULE "substring"

- `WORD` is `error`, `warn`, `advisory` or `unresolved`; it asserts that
  severity. `unresolved[REASON]:` also asserts the finding's Unresolved
  reason code (`unresolved[hole]:`); `unresolved[REASON, required]:` also
  asserts the finding carries a required reason; a bare `unresolved:` accepts
  any reason. A differing severity or reason fails the case.
- `[COL]` (optional) is the 1-based byte column the finding's span starts at.
- `RULE` (optional) is the rule id; omitted, it is the rule under test (the
  block `rule=` or the suite default), so a bare `error:` means that rule.
- `"substring"` (optional) must occur in the finding message. No escapes;
  the string ends at the next `"`.

Placement: a marker after code on a line asserts a finding on that very line
(1-based within the block). A marker alone on its line (only whitespace
before the comment) applies to the next line that is not itself an own-line
marker, blank lines included; markers stacked on consecutive lines all apply
to that one line, so one line may assert several findings. An own-line marker
with no later line is a parse error, as is a malformed `[COL]` (non-numeric
or `[0]`) or an unterminated string.

Findings are compared against the markers as a multiset: each marker needs a
distinct finding that satisfies every part it states, and extra or missing
findings fail the case with an expected-vs-actual table (`!` rows), showing
column and message for unmatched findings.

- `expect=fire` with markers: findings must equal the markers.
- `expect=fire` without markers: at least one Error/Warn finding of the rule.
- `expect=clean`: certified clean, see below; markers are not allowed.

## Strict mode

A case selects rules: the block rule, every rule named by a marker, and any
rules listed in `rules=A,B` on the info string. Findings of unselected rules
(a runner may evaluate more than it was asked) are ignored; a selected
finding that nothing matches fails the case with `unexpected findings`, one
line each giving `class=` (`fire`, `advisory` or `unresolved`), `severity=`,
`reason=`, rule, line, column and message. So a second rule that co-fires
needs a marker naming it (or `rules=` to forbid it), and in a block without
markers an optional Unresolved or an Advisory finding under `expect=fire`, or any finding of a
`rules=` rule, is unexpected. An `expect=unresolved` header matches the
block rule's Unresolved and Advisory findings, including a rolled-up spanless
Unresolved (assert its code with `reason=`).

## Outcome classes

- `fire`: the rule reports a finding (an optional Unresolved finding alone
  does not count; a required Unresolved finding fails the gate, so it does).
- `clean`: certified clean. The rule examined at least one subject (when the
  runner reports subject accounting), was applicable, and produced zero
  findings at any severity. A rule that examines nothing fails.
- `unresolved`: the rule could not decide. Only Unresolved (and Advisory)
  findings are allowed and at least one Unresolved is required; an Error
  fails. `unresolved[REASON]:` markers and `reason=` assert the reason code.
- `notapplicable`: the runner reports the rule does not apply to the
  subject, with a reason, and no findings. A NotApplicable result fails an
  `expect=clean` block.

Runners returning a bare `Vec<Finding>` report no subject accounting, so
only an explicit `subjects=` constraint is checked for them.

## Positive controls

Every rule id named by a block must have, in the same file, at least one
`expect=fire` block and one `expect=clean` block. Otherwise the file fails
with `MissingControl` naming the rule and the missing kind.

## Rule coverage

`gob_mdtest::coverage` (`docs/design/build-test-ci.md` 6, D98) checks every
registered rule of a product, from the `inventory` registry:

- covered by an mdtest suite under any `crates/*/tests/mdtest/` holding at
  least one `expect=fire` and one `expect=clean` block for the rule, or
- covered by a fixture `crates/*/resources/test/fixtures/<FAMILY>/<RULE>.<ext>`
  with its diagnostics snapshot `<RULE>.snap` beside it.

Alias rules (`RULE_ALIASES`, e.g. `COV003` for `TEST001`) are never emitted and
are exempt: the target's coverage stands for them.

Each rule also needs the cases its `RuleMeta` demands: `fire`, `clean`, an
`unresolved` case shaped by its polarity (P+, P-, P0, Pn, Pc) and, for a
`must_measure` rule, a vacuous case (`expect=unresolved reason=vacuous`).
Universal-tier matrix rows are enforced by the language matrix gate below.

`frob-check`, `grimble-check` and `crunk-check` each carry a
`tests/rule_coverage.rs` calling `assert_product_coverage`; the failure
names every missing case as `RULE POLARITY kind` (e.g. `COV001 P- unresolved`).
Known gaps are listed in `crates/gob-mdtest/coverage-allowlist.toml`, one
`[[gap]]` per rule and case kind with `product`, `rule`, `kind` (`fire`,
`clean`, `unresolved`, `vacuous`) and a `ticket` handle.
The list may only shrink: an entry whose case now exists, whose rule is no
longer registered, or without a `~XXXXXXX` handle fails the test.
A rule that never emits an Unresolved finding keeps its `unresolved` entry until the
product gives it one; such entries name the ticket that tracks the change.

Runner hooks that make the unresolved cases reachable: the frob-pm corpus DSL lines
`unreadable` (reopen the ledger over an unreadable index) and `bad_config` (corrupt
`frob.toml`); the frob-check tool runner takes a first line `# parser: NAME` to bind an
output parser to the stage, and the ticket-branch runner a `stale-reindex` scenario.

## Language matrix

`cell=NAME` (one of `rust python typescript csharp markdown text binary island`) places a block
in the language matrix of a Universal rule (`docs/design/testing.md` section 4). The expected
class of each cell is derived from the rule's needs and the capability matrix by an injected
deriver (`gob_mdtest::matrix`); a block whose `expect=` contradicts it fails. `parity=NAME`
groups blocks of one rule stating the same case in several languages: every group member in an
Examine cell must agree on fire versus clean.

Every Universal rule needs a block in every cell, or a `[[matrix_gap]]` entry in
`coverage-allowlist.toml` with `product`, `rule`, `cell` (a name or `*`) and a `~XXXXXXX`
`ticket`. The list may only shrink: an entry whose cell is now filled fails the test.
`crates/frob-check/tests/rule_matrix.rs` wires the real deriver.
