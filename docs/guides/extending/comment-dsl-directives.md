# Comment DSL directives

<!-- frob:describes src/frob/graph/dsl.py::parse_directives -->

## What it is and where it lives

<!-- frob:enumerates src/frob/graph/dsl.py::_VERB_TABLE members="doc,uses-contract,invariant,ticket,todo,waive,debt,deprecated,tests,decision,channel,boundary,secret,enforces,protocol,transition,requires,acquire,release,escapes,enumerates,until" -->
`frob:<verb> <target> [key="value" ...]` is the in-source obligation
language (`docs/modules/graph.md#comment-dsl`). Verbs map to `EdgeKind`
values via `_VERB_TABLE` in `src/frob/graph/dsl.py`. Current verbs (22):
`doc`, `uses-contract`, `invariant`, `ticket`, `todo`, `waive`, `debt`,
`deprecated`, `tests`, `decision`, `channel`, `boundary`, `secret`,
`enforces`, `protocol`, `transition`, `requires`, `acquire`, `release`,
`escapes`, `enumerates` (T-1227 -- doc-claimed collection-member drift,
see docs/modules/gates.md#docenum001-t-1227), `until` (T-1229 --
negative-existence claim binding, see
docs/modules/gates.md#negexist001-gate-t-1229).
Parsing is language-agnostic:
`frob.lang`'s seven walkers (python, cpp, c, typescript/tsx, rust, kotlin,
strata; `src/frob/lang/_extract.py:60`) strip comment delimiters first, so
`dsl.py` only ever sees the bare `frob:...` text regardless of `#`, `//`,
or `/* */` origin.

### `frob:waive` vs `frob:debt` (T-0412)

Two directives suppress a gate finding at a site, with deliberately
different lifetimes:

```
frob:waive <RULE> reason="..."
frob:debt <RULE> reason="..." ticket="T-####" [until="YYYY-MM-DD" | until="X.Y.Z"]
```

- `frob:waive` is PERMANENT: a genuine, forever-acceptable exception (a
  sort that runs once, not in a loop; scan-pattern data that looks like a
  secret but isn't). It never expires and carries no ticket.
- `frob:debt` is TEMPORARY: an accepted gap that is TRACKED as owed.
  `ticket="T-####"` is REQUIRED (never optional, unlike a waiver's
  ticket-free reason) and must name a currently OPEN ticket -- DEBT002
  fails a debt bound to a missing or closed ticket, since a debt pointing
  at nothing owed is a lie about what is still tracked. An optional
  `until=` (a `YYYY-MM-DD` date or an `X.Y.Z` semver) escalates the debt
  to a hard ERROR (DEBT003) once that boundary passes. A debt missing
  either `reason=` or `ticket=` is DEBT001, the malformed-directive
  counterpart to WAIVE001.

Critically, `frob release`'s REL001 check refuses to bless a release
while ANY `frob:debt` is still open at all -- expired or not. Debt is
collected and re-raised BEFORE shipping, never silently carried forward
as a de facto permanent waiver. `frob debt` lists every currently-recorded
entry (rule, site, ticket, until, expired) for a human/agent to work
through; there is no `--apply`/auto-fix -- resolving a debt means fixing
the underlying gap and removing the directive, not running a command over
it.

**Migration guidance (not yet done in bulk, T-0412's own follow-up):** a
`frob:waive` whose `reason=` literally names a ticket as the excuse (e.g.
`reason="visit_Constant 75.0% branch cover, debt T-0160"`) is DEBT-shaped,
not a genuine permanent exception -- convert it to `frob:debt <RULE>
reason="..." ticket="T-0160"` (add `until=` if there is a real target
date/version) so the gap is tracked and collected, rather than left as an
un-audited waiver that never expires. This repo has ~143 such debt-shaped
waivers as of T-0412; converting them is a deliberate follow-up burndown
ticket, not a mass find-and-replace done here -- migrating that many
directives at once, sight-unseen, risks silently mis-binding several to
the wrong ticket or an already-closed one, which is exactly the failure
mode DEBT002 exists to catch. Convert them incrementally, verifying each
one's ticket is real and open as you go.

### `frob:deprecated` (T-0576): `frob:debt` generalized to the API surface

```
frob:deprecated <since> sunset="YYYY-MM-DD" ticket="T-####" [reason="..."]
```

Where `frob:debt` suppresses a GATE FINDING (the symptom), `frob:deprecated`
is about a public symbol's continued EXISTENCE (a dated exit for something
still callable today). `<since>` is free text (typically the version the
symbol was deprecated in); `sunset=` is REQUIRED and must be a plain
`YYYY-MM-DD` calendar date -- never a semver, since a real-world sunset is a
date regardless of how the release train moves. `ticket=` is REQUIRED, same
posture as `frob:debt`, and must name a currently OPEN ticket -- DEPR002
fails a deprecation bound to a missing or closed ticket for the same
reason DEBT002 does. Missing either attribute, or a non-date `sunset=`, is
DEPR001, the malformed-directive counterpart to DEBT001/WAIVE001.

Unlike `frob:debt` (silent while valid), `frob.gates.deprecated_gate` warns
the moment the directive exists and is still inside its window (DEPR003),
so a live-but-scheduled deprecation stays visible in ordinary `frob check`
output rather than only surfacing once the date arrives; DEPR003
escalates to a hard ERROR (DEPR004) once `sunset` has passed. `frob
release`'s REL001 check refuses to bless a release while ANY
`frob:deprecated` is past its sunset -- but, unlike debt, one still inside
its warning window does NOT block a release; the point is only that an
unenforced sunset never quietly survives past its own date.
`frob.gates.list_deprecated` reports every currently-recorded entry
(symref, since, sunset, ticket, expired); there is no CLI subcommand or
`--apply` wired to it yet (T-0576 scoped only the graph/gates/docs/tests
layer -- a CLI surface, if wanted, is its own follow-up).

## Multi-line directives (backslash continuation)

A directive can span multiple physical comment lines by ending each line
but the last with a trailing backslash (`\`); `parse_directives` folds
the run into one logical line before dispatching to `_parse_line`
(`_fold_continuations` in `src/frob/graph/dsl.py`, T-0286). This exists
because a self-explaining `frob:waive ... reason="..."` routinely collides
with the 88-column ruff limit, forcing reasons to be truncated to fit --
continuation removes that pressure.

Mechanics:

- Detection is on the right-stripped line: a line continues if, after
  trailing whitespace is removed, the last character is `\`.
- Only the trailing `\` is removed; joining uses the **empty string**, not
  a space -- a continuation that wants a space at the join point must put
  it before the backslash. A line ending `...that \` keeps the space when
  folded onto the next line; a line ending `...that\` does not.
- The reported line number and symbol binding (`src`) for a folded
  directive are always the FIRST physical line of the run, never a
  continuation line -- this holds for both well-formed edges and
  `MalformedDirective`s.
- Works uniformly for `#`, `//`, and `/* */` comments. Stacked `#`/`//`
  lines are separate `RawComment`s per physical line (`frob.lang` does not
  merge adjacent line comments into one span), so folding operates on a
  flattened, file-ordered stream of physical lines rather than within a
  single comment's text -- a continuation only folds if the next physical
  line is immediately adjacent (`lineno + 1`); a gap breaks the run.
- A trailing backslash on the LAST physical line available to continue
  into (end of file, or the next line isn't adjacent) is a **dangling
  backslash**, and is treated LITERALLY -- left in place, unfolded, not
  reported as malformed. A lone trailing `\` is content, not necessarily a
  broken continuation.
- CRLF-safe: a trailing `\r` before the line break is stripped along with
  the backslash handling, so Windows-style line endings never leak a
  stray `\r` into the folded text.

Worked example -- a waive reason too long for one 88-column line:

```python
# frob:waive PERF004 reason="benchmarked against the naive loop; the \
# comprehension form is 3x faster here and the rule's general heuristic \
# doesn't apply to this hot path"
```

This parses as a single `waive` edge targeting `PERF004` with
`reason` equal to the full concatenated sentence (no extra spaces at the
join points because each continued line ends with a space before its `\`).

## Add-an-entry recipe (new verb)

1. Add the `EdgeKind` member in `src/frob/graph/_models.py`.
2. Add the verb -> kind mapping to `_VERB_TABLE`.
3. If the verb takes required attrs (like `tests` requiring a `kind=` in
   `unit|integration|e2e|property`, see `_TESTS_KINDS`), add the attr validation in
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
