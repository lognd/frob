---
id: T-3893
title: allow quoted positional directive values so a vitest title with spaces can
  be cited, reusing the existing attribute quoting
state: in-progress
kind: feature
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
- docs/guides/extending/comment-dsl-directives.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/dsl.py
  reason: extend positional directive values to accept quoted spans, reusing _ATTR_RE
    quoting convention; must survive to resolvers and frob fmt round trip
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/nodeid.py
  reason: extend positional directive values to accept quoted spans, reusing _ATTR_RE
    quoting convention; must survive to resolvers and frob fmt round trip
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: extend positional directive values to accept quoted spans, reusing _ATTR_RE
    quoting convention; must survive to resolvers and frob fmt round trip
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: extend positional directive values to accept quoted spans, reusing _ATTR_RE
    quoting convention; must survive to resolvers and frob fmt round trip
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/graph.md
  reason: directive doc pages referenced by dsl.py public symbols in scope
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/extending/comment-dsl-directives.md
  reason: directive doc pages referenced by dsl.py public symbols in scope
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: src/frob/nodeid.py
  reason: unused in the final implementation -- quoted target parsing lives entirely
    in dsl.py; keeping these two files in scope pulled in unrelated pre-existing doc/test
    closures via SCOPE002
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: src/frob/tickets/_evidence.py
  reason: unused in the final implementation -- quoted target parsing lives entirely
    in dsl.py; keeping these two files in scope pulled in unrelated pre-existing doc/test
    closures via SCOPE002
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/graph.md
  reason: no edit made to this doc; comment-dsl-directives.md is the doc actually
    updated for this ticket
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/gates.md
  reason: 'SCOPE002 closure: dsl.py carries other pre-existing symbols (fold_comment_runs,
    markdown_anchors, mask_frob_mentions, dedupe_slug, _attrs_verb_error_waive) whose
    doc/test targets live in these files; adding for closure, no edits planned to
    their content'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/graph.md
  reason: 'SCOPE002 closure: dsl.py carries other pre-existing symbols (fold_comment_runs,
    markdown_anchors, mask_frob_mentions, dedupe_slug, _attrs_verb_error_waive) whose
    doc/test targets live in these files; adding for closure, no edits planned to
    their content'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/gates_suite/test_waive.py
  reason: 'SCOPE002 closure: dsl.py carries other pre-existing symbols (fold_comment_runs,
    markdown_anchors, mask_frob_mentions, dedupe_slug, _attrs_verb_error_waive) whose
    doc/test targets live in these files; adding for closure, no edits planned to
    their content'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_graph.py
  reason: 'SCOPE002 closure: dsl.py carries other pre-existing symbols (fold_comment_runs,
    markdown_anchors, mask_frob_mentions, dedupe_slug, _attrs_verb_error_waive) whose
    doc/test targets live in these files; adding for closure, no edits planned to
    their content'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/gates/test_negexist.py
  reason: 'SCOPE002 closure: dsl.py carries other pre-existing symbols (fold_comment_runs,
    markdown_anchors, mask_frob_mentions, dedupe_slug, _attrs_verb_error_waive) whose
    doc/test targets live in these files; adding for closure, no edits planned to
    their content'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/graph/test_dsl_markdown_waive.py
  reason: 'SCOPE002 closure: dsl.py carries other pre-existing symbols (fold_comment_runs,
    markdown_anchors, mask_frob_mentions, dedupe_slug, _attrs_verb_error_waive) whose
    doc/test targets live in these files; adding for closure, no edits planned to
    their content'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/graph/test_dsl_mention_escape.py
  reason: 'SCOPE002 closure: dsl.py carries other pre-existing symbols (fold_comment_runs,
    markdown_anchors, mask_frob_mentions, dedupe_slug, _attrs_verb_error_waive) whose
    doc/test targets live in these files; adding for closure, no edits planned to
    their content'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/gates.md
  reason: 'revert: closure exploded via gates.md/graph.md describing the whole subsystem;
    SCOPE002 here is a pre-existing property of dsl.py being a large shared file,
    not caused by this diff -- investigating whether it predates this ticket'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/graph.md
  reason: 'revert: closure exploded via gates.md/graph.md describing the whole subsystem;
    SCOPE002 here is a pre-existing property of dsl.py being a large shared file,
    not caused by this diff -- investigating whether it predates this ticket'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/gates_suite/test_waive.py
  reason: 'revert: closure exploded via gates.md/graph.md describing the whole subsystem;
    SCOPE002 here is a pre-existing property of dsl.py being a large shared file,
    not caused by this diff -- investigating whether it predates this ticket'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/test_graph.py
  reason: 'revert: closure exploded via gates.md/graph.md describing the whole subsystem;
    SCOPE002 here is a pre-existing property of dsl.py being a large shared file,
    not caused by this diff -- investigating whether it predates this ticket'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/gates/test_negexist.py
  reason: 'revert: closure exploded via gates.md/graph.md describing the whole subsystem;
    SCOPE002 here is a pre-existing property of dsl.py being a large shared file,
    not caused by this diff -- investigating whether it predates this ticket'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/graph/test_dsl_markdown_waive.py
  reason: 'revert: closure exploded via gates.md/graph.md describing the whole subsystem;
    SCOPE002 here is a pre-existing property of dsl.py being a large shared file,
    not caused by this diff -- investigating whether it predates this ticket'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: tests/unit/graph/test_dsl_mention_escape.py
  reason: 'revert: closure exploded via gates.md/graph.md describing the whole subsystem;
    SCOPE002 here is a pre-existing property of dsl.py being a large shared file,
    not caused by this diff -- investigating whether it predates this ticket'
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DECISION 2026-09-05: extend the DSL's EXISTING quoting convention to
positional directive values, so a value containing spaces or other delimiters
can be written as one token. A distinct "do-not-resolve" sigil was considered
and explicitly REJECTED -- see the end of this body for why, so it is not
re-proposed later.

THE GAP, MEASURED. The directive parser already quotes ATTRIBUTE values:

    src/frob/graph/dsl.py:178
        _ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

and its surrounding comments already reason correctly about quoted spans (a '#'
inside a quoted attribute value is consumed by this regex before the T-0309
comment-tail strip looks at the leftover). So the parser can already hold an
opaque run of text. What it cannot do is hold one in POSITIONAL position -- the
`frob:tests` target, the `frob:todo` note -- where values are whitespace-split.

WHAT THIS BLOCKS TODAY, both already filed:
  - F-047 / T-3847: `frob:tests` cannot cite a vitest test title containing
    spaces. vitest ids are a file plus a describe/it string written by humans,
    so spaces are the norm, not an edge case. Every non-pytest framework has
    this shape problem to some degree: gtest `Suite.Case`, ctest bare names,
    junit FQCN#method, pytest's own parametrized `[015-python-3.11.4]`.
  - T-3856: DSL001 rejects a free-text `frob:todo` note outside Python, because
    the note reaches `_parse_attrs` and is judged bad attribute syntax.

THE CHANGE: allow a double-quoted span wherever a positional value is read, with
the same lexical rules the attribute form already uses. Reuse `_ATTR_RE`'s
quoting semantics rather than writing a second quoting mechanism -- two ways to
quote is a desync waiting to happen, and the whole reason this design was chosen
over a new sigil is that the convention already exists.

ANSWER THESE BEFORE IMPLEMENTING; they are the actual design work:
  1. NESTED QUOTES. `"[^"]*"` cannot express a value containing a double quote,
     and vitest titles are prose, so this will happen. Decide: a backslash
     escape, a raw form with a chooseable delimiter, or an explicit refusal
     with a clear message. A refusal is acceptable IF it names the problem --
     silently truncating at the inner quote is not.
  2. WHERE IT IS HONOURED. A quoted `frob:tests` target must survive all the way
     to `matches_collected` / the per-framework resolvers, not just past the
     parser. A quoted value the parser accepts and the resolver then fails to
     match is worse than a parse error, because it looks like a missing test.
     Enumerate every positional-value reader and confirm each handles it.
  3. INTERACTION WITH THE CONTINUATION RULE. T-3889 concerns how `frob fmt`
     wraps long directive lines. A quoted span that gets wrapped mid-string must
     round-trip: written by fmt, read back by the parser, same value. Coordinate
     with that ticket; a fixture for the round trip belongs in one of them and
     should not be written twice.

WHY THE "DO-NOT-RESOLVE" SIGIL WAS REJECTED, recorded so it is not revisited
without new information. The proposal was a Zig-style `@"..."` literal meaning
"this text is not a pointer, do not resolve it". It was dropped because THE
MECHANISM ALREADY EXISTS AND IS STRICTLY BETTER: DOC006's own message documents
`frob:waive DOC006 reason="..."` for the "intentionally
external/illustrative/future-facing" case, and Series FB measured that an
inline waive adjacent to a body citation works (zero DOC006 findings on its
branch, including a deliberately unresolvable citation it had waived). A sigil
would say the same thing while carrying LESS information -- no reason field --
and for the one construct whose job is suppressing a check, dropping the
justification is a strict downgrade. The three motivating cases each have a
better-typed answer already: de-backticking for text that was never a pointer,
the planned marker for design-first forward references, and T-3843's landed fix
for frontmatter titles.

MUST-FIRE FIXTURES:
  - an unquoted positional value containing a space is still an error (no
    silent acceptance of a truncated value)
  - whatever the nested-quote decision is, its failure case produces a clear
    message naming the value
MUST-STAY-QUIET FIXTURES:
  - a quoted vitest-style title with spaces parses as ONE value and resolves
  - every existing unquoted directive in this repo parses unchanged (no
    regression -- frob's own source is full of them)
  - the attribute form `key="value"` is untouched

ACCEPTANCE
- Quoting supported in positional position, reusing the existing convention.
- The three design questions answered explicitly in the done report.
- The full list of positional-value readers enumerated and each confirmed.
- All fixtures committed.
