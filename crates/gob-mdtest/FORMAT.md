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

A line holding a comment (`//`, `#`, or `<!--`) followed by
`error: RULE` or `warn: RULE` asserts a finding of that rule and severity
on that very line (1-based within the block). Findings are compared
exactly against the markers: extra or missing findings fail the case.

- `expect=fire` with markers: findings must equal the markers.
- `expect=fire` without markers: at least one finding of the rule.
- `expect=clean`: zero findings; markers are not allowed.

## Positive controls

Every rule id named by a block must have, in the same file, at least one
`expect=fire` block and one `expect=clean` block. Otherwise the file fails
with `MissingControl` naming the rule and the missing kind.
