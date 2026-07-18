# Comment DSL directives

<!-- frob:describes src/frob/graph/dsl.py::parse_directives -->

## What it is and where it lives

`frob:<verb> <target> [key="value" ...]` is the in-source obligation
language (`docs/modules/graph.md#comment-dsl`). Verbs map to `EdgeKind`
values via `_VERB_TABLE` in `src/frob/graph/dsl.py`. Current verbs: `doc`,
`uses-contract`, `invariant`, `ticket`, `todo`, `waive`, `tests`,
`decision`, `channel`, `boundary`, `secret`. Parsing is language-agnostic:
`frob.lang`'s five walkers strip comment delimiters first, so `dsl.py`
only ever sees the bare `frob:...` text regardless of `#`, `//`, or
`/* */` origin.

## Add-an-entry recipe (new verb)

1. Add the `EdgeKind` member in `src/frob/graph/_models.py`.
2. Add the verb -> kind mapping to `_VERB_TABLE`.
3. If the verb takes required attrs (like `tests` requiring a `kind=` in
   `unit|integration|e2e`, see `_TESTS_KINDS`), add the attr validation in
   `_parse_line` (or wherever `_ATTR_RE` results are consumed for that verb)
   and a `MalformedDirective` reason string for the missing/bad-attr case.
4. Add the corresponding gate consumer if the new verb needs enforcement
   (e.g. a new COV/TEST/SYS-family rule reading the new `EdgeKind`).
5. Document the verb in `docs/modules/graph.md#comment-dsl`.

## Drift-locks that fire

- A malformed directive (unknown verb, missing required attr, `waive`
  without `reason=`) becomes a `MalformedDirective`, surfaced by
  `frob.gates` rather than silently dropped -- `WAIVE001` specifically for
  a `waive` missing `reason=`.
- **DOC002** if a new `doc` edge's target doesn't resolve to a real
  heading slug or `<a id>` anchor in the target file.
- Adding a verb without a graph-side consumer is legal (it parses) but
  pointless -- nothing will ever read the edge; there is no automatic
  drift-lock for "verb defined but never consumed," so this is a manual
  review item, not a build failure.

## Worked example

`channel`/`boundary`/`secret` landed in T-0080 specifically so
`frob.gates`' SYS family (SYS001-004) could join code to a `.strata`
design model without `frob.graph` itself learning strata vocabulary --
the verbs were added to `_VERB_TABLE`, given their own `EdgeKind` members,
and the SYS family was added as a *separate* consumer module
(`src/frob/strata/_code_binding.py` / `bind_code`), keeping the DSL
generic and the strata-specific semantics out of `frob.graph`.

## Common mistakes

- Adding strata-specific validation logic directly inside `dsl.py` instead
  of a separate consumer -- this is the exact layering `channel`/
  `boundary`/`secret` were designed to avoid; `dsl.py` stays vocabulary-only.
- Forgetting `WAIVE001`/`WAIVE002`: any new verb that can itself be waived
  (most can, since `frob:waive` targets a rule id, not a verb) still needs
  the waiver boundary respected -- a waiver for a rule id that structurally
  cannot fire on that line is itself a violation, not a no-op.
