---
id: T-4703
title: 'Directive ergonomics: multi-target headers, token-boundary wrapping, stack
  merge fix, noqa strip, separator canonicalization, derived bindings'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story. Measured 2026-09-19 18:15 across src/ and tests/: 30,915 `# frob:` directive lines;
5,663 (18%) carry a `# noqa` suffix; 1,712 runs of 3+ consecutive directive lines, the largest
73 lines; only 88 lines carry two or more directives. The directive DSL is unreadable at the
point of use. The existing machinery explains why, and every leaf must build on it rather than
rediscover it.

## What already exists (read before implementing anything)

- Continuation: the trailing-backslash form is ALREADY the parser's half-supported convention
  (`_fold_continuations` / `fold_comment_runs`, src/frob/graph/dsl.py:1431-1545, T-0286 /
  T-0441 / T-0987). This story adopts it as THE one continuation form and documents it as such.
  The indented-hash alternative floated in the brief is dropped, not built.
- Wrapping: `frob fmt` already canonicalizes directive runs
  (`frob.gates._fmt_directives.canonicalize_text` / `format_paths`, T-0441), FMT001 already
  warns on an over-long directive comment line, and `fix_fmt001_directive_wrap`
  (src/frob/gates/_fix_engine_text.py:113) is already a registered Tier-A handler. The wrap
  leaf is therefore a NARROWING of an existing wrapper, not a new one: `_wrap_cut_point`
  (src/frob/gates/_fmt_directives.py:417) cuts at ANY space (`rfind(" ", 0, budget)`), which is
  word-boundary, not token-separation.
- WHY THE 5,663 NOQA LINES PERSIST: `_rewrite_directive_run`
  (src/frob/gates/_fmt_directives.py:595-640) treats a run ending in `# noqa` as an
  unconditional "leave this run alone" marker. T-1987 deliberately reverted T-1605's
  self-retiring behaviour because rewrapping one noqa-suppressed physical line into four
  changed the PHYSICAL LINE COUNT of the enclosing function and tripped ARCH001 on two real
  lands (T-1970, T-1968). Any noqa-strip leaf must ANSWER that regression, not rediscover it.
  The answer this story commits to: reverse-copy removal, multi-target headers and stack merge
  all SHRINK physical line count, so the strip runs after them and its own acceptance includes
  "no new ARCH001 on any touched file".

## Owner decisions (binding on every leaf)

1. E501 stays real. No exemption of directive lines from E501, no 8000-character lines. People
   who run ruff by hand must not be broken. Long directives WRAP.
2. A break may land ONLY at token separation: between targets of a multi-target list, or
   between `key="value"` attributes. NEVER inside a symbol path, an anchor, or a quoted value.
   The parser joins continuation lines before tokenizing. A break inside a token is a DSL001
   finding that names its fix.
3. Multi-target directives: `# frob:tests a.py::A.m, b.py::B.n` and
   `# frob:doc path#a, path#b` -- same kind, comma-separated.
4. Stack lint plus Tier-A fix: a run of N+ directive lines (N configurable, default 4) above one
   symbol is a finding. The fix merges same-kind directives into the multi-target form, groups
   by kind preserving first-seen order (interleaved doc, tests, doc collapses to one doc header
   and one tests header), and wraps at token separation to fit the line length.
5. noqa strip: a Tier-A fix removes `# noqa: E501` and bare `# noqa` from directive lines that
   now fit; the lint flags a directive line carrying a noqa it no longer needs. The 5,663 must
   drop to the residue that genuinely cannot fit (a single token longer than the line), and that
   number is reported in the Done report.
6. Separator canonicalization: the parser accepts `path::Class.method`, `path::Class::method`
   and `path.Class.method`. Canonical is `path::Class.method` (what pytest prints). A lint plus
   Tier-A fix rewrites the other two spellings. NEVER refuse them -- token/grammar fixes, never
   lexical.
7. Derived bindings, not guessed. `frob ticket evidence ... --bind` writes the `frob:tests` line
   for the accepted symbol from the evidence it already records; the docs gates offer `--bind`
   for `frob:doc` where the anchor is already known. NO heuristic generator that guesses which
   test covers which symbol, ever.

## Reverse-binding direction: owner decision, and the contradiction it must resolve

OWNER DECISION (2026-09-19, supersedes the planner's read of the current code): the reverse
`frob:tests` copy on the PRODUCTION symbol is not needed. The TEST FILE's declaration is the
single source, and the graph builds the reverse edge internally at build time -- one declaration
replaces two parses. This is its own leaf, sequenced BEFORE the stack-merge leaf because it
removes most stacks outright.

The leaf that implements it must resolve a live contradiction between two subsystems, both
measured here, both cited by file:line so the implementer does not have to re-derive them:

- The TESTS edge is DIRECTIONAL today. `src` is the implementation symbol the directive sits on,
  `target` is the test it names -- src/frob/gates/_tdd_order.py:465-487. TDD001 (T-4260)
  explicitly classifies an edge whose `src` looks like a test path and whose `target` does not
  as BACKWARDS, a malformed directive, and refuses to compute an ordering verdict for it
  (src/frob/gates/_tdd_order.py:481-490). A test-side declaration is therefore NOT today an
  equivalent spelling of the production-side directive: it is a TDD001 finding. Moving the
  declaration to the test side REQUIRES the graph build to emit the edge in the canonical
  (implementation -> test) orientation from a test-side declaration, so TDD001 keeps seeing the
  orientation it validates. Emitting the raw test-side orientation would turn every migrated
  binding into a TDD001 backwards finding.
- Exactly one consumer is direction-agnostic and will not notice either way:
  src/frob/gates/_coverage.py:420-426 unions BOTH sides (`for side in (edge.src, edge.target)`)
  into `tested_symrefs`.
- A second, independent contradiction the same leaf inherits: src/frob/graph/dsl.py:1401-1420
  documents `target == src` (a test function naming itself) as "this repo's own widespread,
  deliberate convention" and deliberately does NOT reject it, while TDD001 T-4260 now
  classifies `src == target` as malformed and skips it entirely. Once declarations live on the
  test side, the self-referential shape becomes the common case, so the leaf must settle which
  of the two is right and say so in docs -- not leave both standing.