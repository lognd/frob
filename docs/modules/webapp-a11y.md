# frob.webapp._a11y_substrate -- A11Y tree-query helpers

One sentence: `frob.webapp._a11y_substrate` is the one shared tree-sitter
query library every A11Y rule in the `T-5140` web-app epic (missing `alt`,
missing `aria-label`, skipped heading levels, a document-less `<html
lang>`) calls instead of hand-rolling its own node walk against html,
vue's `<template>` shell, or jsx.

## Why this module takes a `Node`, not a `Path`

`frob.webapp` is a leaf layer in `[arch.layering]` (`frob.toml`) with no
allowed imports of its own (the same table T-5302's `_detect.py` lives
in) -- this module never imports `frob.lang`. Callers (A11Y rule modules
under `frob.gates`, which ARE allowed to import both `lang` and `webapp`)
call `frob.lang.raw_tree`/`parse_file` themselves and hand this module the
resulting `tree_sitter.Node` root, the parsed `ParsedFile.language` label,
and the raw source bytes.

## Grammar families

- **html-family** (`language in {"html", "vue"}`): vue's own tree-sitter
  grammar reuses html's node shapes verbatim inside a `<template>` block
  (`element`, `start_tag`/`self_closing_tag`, `attribute`,
  `attribute_name`, `quoted_attribute_value`) -- no nested sub-parse -- so
  both languages route through one walk.
- **jsx-family** (`language in {"javascript", "typescript"}`, covering
  `.jsx`/`.tsx` per `frob.lang.language_for_extension`): `jsx_element`/
  `jsx_self_closing_element`, `jsx_opening_element`, `jsx_attribute`,
  `property_identifier`.

An unrecognized `language` returns `Err(A11ySubstrateError.UnsupportedLanguage)`
from every query function below.

## Query helpers

- `elements_with_attribute(root, language, source, tag_names, attribute)`
  -> `Result[tuple[ElementMatch, ...], A11ySubstrateError]`: every element
  under `root` (any nesting depth) whose tag is in `tag_names` AND that
  carries `attribute` -- the `img[alt]`/`input[aria-label]` query shape.
- `elements_missing_attribute(root, language, source, tag_names, attribute)`
  -> same shape, inverted: elements matching `tag_names` that do NOT
  carry `attribute` -- what a "missing alt/aria-label" violation rule
  queries.
- `heading_sequence(root, language, source)` ->
  `Result[tuple[HeadingMatch, ...], A11ySubstrateError]`: every `h1`..`h6`
  heading in document order, each carrying its level (1-6), flattened
  text, and span -- what a "skipped heading level" rule queries.
- `html_lang(root, language, source)` -> `Result[str | None,
  A11ySubstrateError]`: the top-level `<html lang="...">` value, or
  `Ok(None)` if no `<html>` element is present or it has no `lang`
  attribute. For a jsx-family `language` (no `<html>` root ever exists)
  this returns `Ok(None)` rather than an error -- "no `<html>` element
  here" is a legitimate answer, not a substrate failure.

## Data shapes

- `ElementMatch(tag: str, attributes: dict[str, str], span: tuple[int, int])`
- `HeadingMatch(level: int, text: str, span: tuple[int, int])`
- `A11ySubstrateError` (`ErrorSet`): `UnsupportedLanguage`

`span` is always a 1-based, inclusive-line `(start, end)` pair.

## Fixtures

`tests/fixtures/webapp/a11y1xx/` holds one clean (positive-control) and
one violating (negative-control) sample per query shape, across all three
grammar families:

- `html_alt/{clean,violation}.html` -- `<img alt>` present/missing.
- `jsx_aria_label/{clean,violation}.jsx` -- `<input aria-label>`
  present/missing.
- `vue_headings/{clean,violation}.vue` -- an unbroken `h1`->`h2`->`h3`
  sequence vs. a skipped `h1`->`h3`.
- `html_lang/{clean,violation}.html` -- `<html lang="en">` vs. a bare
  `<html>`.

`tests/unit/test_webapp_a11y_substrate.py` exercises all eight fixtures
plus an unsupported-language negative case.

## Follow-up

A single later ticket links this doc (and its five WEBSEC-family
siblings) from `docs/modules/webapp.md`'s own body -- not done here to
avoid seven concurrent leases colliding on that one file.
