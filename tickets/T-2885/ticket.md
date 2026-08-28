---
id: T-2885
title: 'OPAQUE001/sys false positives: module docstring not excluded when a comment
  precedes it'
state: in-progress
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_core.py
- tests/test_vet_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_vet_capability.py
  reason: added must-fire/must-stay-quiet fixtures for the leading-comment docstring
    fix
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working the red-tail sweep's OPAQUE001 finding on
src/frob/gates/_refs.py:31 (T-2879's follow-up dispatch). Investigation-
only ticket, no fix attempted here per explicit instruction not to patch
high-blast-radius shared detection code in the same breath as filing --
this touches `_non_executable_byte_spans`, a primitive shared by
OPAQUE001, the `sys` capability scanner, and possibly others.

## Reproduced directly (not inferred)

`frob.vet._capability._opaque_indirection_findings(Path("src/frob/gates/
_refs.py"))` returns ONE finding at line 31 -- a textual mention of
`importlib.import_module(...)` -- but line 31 is INSIDE the module's
own docstring (lines 9-113, confirmed by counting `"""` occurrences),
describing that construct as an EXAMPLE of the opacity concern the gate
itself detects, not a real call anywhere near that line.

Isolated the cause empirically: copied `_refs.py` to a temp file with
its leading 8-line `frob:waive LARGE001` comment block (lines 1-8,
BEFORE the module docstring) stripped out, re-ran the same finder --
0 findings. Restoring the leading comment reproduces the 1 finding
again. This isolates the defect to the file's SHAPE (a comment
preceding the module docstring), not the docstring's content.

## Root cause (read the query, not guessed)

`_PY_DOCSTRING_QUERY_SRC` (`src/frob/vet/_capability_core.py`) anchors
the module-docstring capture as `(module . (string) @doc)` / `(module .
(expression_statement (string) @doc))` -- the `.` anchor requires the
docstring to be tree-sitter's IMMEDIATE first named child of `module`.
When a comment (e.g. any `frob:waive`/`frob:ticket` header block, common
across this repo) precedes the docstring in the same file, the anchor
does not match, `_docstring_byte_spans_from_tree` returns no span for
that docstring, and `_non_executable_byte_spans` (shared by OPAQUE001,
and per its own docstring, the `sys` scanner) fails to exclude the ENTIRE
docstring's text from needle-scanning -- any capability-shaped substring
mentioned in prose (an example, a rejected alternative, a described
incident) becomes a live false-positive risk for every needle-scan gate
that relies on this exclusion.

## Blast radius (measured, not assumed empty)

A quick `git grep` for files carrying a leading `frob:waive`-shaped
comment block immediately before their module docstring found several
more candidates sharing the vulnerable shape, confirmed by file
inspection (not exhaustively verified against OPAQUE001/sys findings
each, which is exactly the measurement this ticket should do before any
fix): `src/frob/app/_config_external.py`, `src/frob/app/check_runner.py`,
`src/frob/app/config.py`. This is very likely NOT limited to these three
-- any file starting with ANY top-of-file comment (not only
`frob:waive`) before its module docstring is structurally exposed the
same way; a repo-wide count was not attempted here (out of this
ticket's investigation-only scope) and is exactly what the fix pass
should measure first.

## Why this needs its own ticket, not a rushed patch here

`_non_executable_byte_spans`/`_PY_DOCSTRING_QUERY_SRC` is a shared
primitive with a documented multi-caller history (T-1210's own docstring
lists five call sites that used to independently re-walk this same
tree). A query-shape fix here has to be verified against every one of
those callers, not just OPAQUE001 -- exactly the kind of high-blast-
radius change that deserves its own scoped ticket, positive/negative
control fixtures (a file WITH a leading comment whose docstring must
still be excluded; a file with a real, non-docstring `importlib.
import_module` call preceded by a comment, which must still fire), and
a repo-wide before/after finding count, not a single-file patch bundled
into an unrelated red-tail sweep ticket.

## Suggested fix shape (not implemented, for the next agent)

Either loosen the tree-sitter query to tolerate a preceding `comment`
node (tree-sitter's `.` anchor already treats a grammar's declared
`extra` nodes as transparent in SOME query engines -- confirm whether
python's tree-sitter grammar marks `comment` as `extra` and whether this
project's Query binding honors that before relying on it), or compute
the module-docstring span by first-STATEMENT-not-first-CHILD semantics
(skip leading comment nodes explicitly before checking for a string
statement) rather than the anchor primitive. Either fix needs the
positive/negative fixtures named above before landing.

## What was fixed instead, narrowly, in this ticket's absence

T-2879's own follow-up dispatch waived the single _refs.py:31 OPAQUE001
finding directly (citing this ticket by id) rather than touching the
shared query -- see that finding's own frob:waive reason for detail.