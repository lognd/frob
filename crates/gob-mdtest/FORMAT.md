# mdtest corpus format

A markdown file is a suite. Fenced code blocks are test cases.

## Naming

`#` and `##` headings name the cases beneath them. A block is reported as
`Heading / Subheading #N (line L)` where `L` is the fence line in the file.

## Suite header

An HTML comment outside any fence sets a default for the blocks after it:

    <!-- mdtest: rule=MDT001 -->

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
