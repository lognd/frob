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
- `expect=fire|clean`: required.
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
- `expect=fire` without markers: at least one finding of the rule.
- `expect=clean`: zero findings; markers are not allowed.

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

`frob-check`, `grimble-check` and `crunk-check` each carry a
`tests/rule_coverage.rs` calling `assert_product_coverage`; the failure
names every uncovered rule. Known gaps are listed in
`crates/gob-mdtest/coverage-allowlist.toml`, one `[[gap]]` per rule with
`product`, `rule` and a `ticket` handle (one umbrella ticket per product).
The list may only shrink: an entry whose rule is now covered, no longer
registered, or without a `~XXXXXXX` handle fails the test.
