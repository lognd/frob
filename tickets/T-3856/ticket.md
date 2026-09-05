---
id: T-3856
title: DSL001 rejects frob:todo free-text notes outside Python, and its hash-tail
  guard swallows any leftover beginning with a hash
state: queued
kind: bug
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as typani FROBLEMS T-017. Verified, and probing the parser turned up a
SECOND, latent issue in the same function. They share a fix site but are
different defects -- keep them distinct in the done report.

FINDING 1 -- THE REPORTED ONE: per-language divergence in free-text notes.

  site: crates/typani-core/src/result.rs
        // frob:todo T-0010 cache the _rebuild_err lookup in a PyOnceLock
  observed: "DSL001 malformed frob: directive: bad attribute syntax:
            'cache the _rebuild_err lookup in a PyOnceLock'"
  but the identical form is ACCEPTED in Python comments -- frob's own source
  carries it at src/frob/perf/_dup_spawn.py:83 and :87 --
        # frob:todo T-0919 non-python (typescript/rust/cpp) coverage for PERF012
  and docs/modules/graph.md documents the form as `frob:todo T-0043 [note]`.

PROBED THE PARSER DIRECTLY (scratchpad/dsl_probe.py, calling
frob.graph.dsl._parse_attrs). Every free-text form is rejected there, INCLUDING
a bare ticket id with no note at all:

    MALFORMED  'T-0010 cache the lookup in a PyOnceLock'
    MALFORMED  'T-0919 non-python (typescript/rust/cpp) coverage'
    MALFORMED  'T-0010'                    <- bare id alone also rejected

So `_parse_attrs` is NOT the function that understands `frob:todo <id> <note>`.
The ticket id and note must be consumed by a per-verb path UPSTREAM of it, and
the Python walker reaches that path while the Rust walker hands the whole
remainder to `_parse_attrs`. THAT UPSTREAM DIVERGENCE IS THE BUG -- find where
the Python path strips id+note and make the non-Python walkers take the same
path. Do not fix it by loosening `_parse_attrs`; that would weaken attribute
validation for every verb in every language to solve a walker-routing problem.

Check c/cpp/typescript/tsx/kotlin/csharp too, not just Rust. The reporter
guessed the whole non-Python set is affected; confirm per language and report a
table rather than fixing Rust alone.

FINDING 2 -- LATENT: a leftover that BEGINS with a hash is silently swallowed.

  src/frob/graph/dsl.py:781
      leftover = leftover.split("#", 1)[0].strip()

  Probe result:
      accepted   '# T-0010 everything after a leading hash'  ->  {}

That line is the T-0309 accommodation letting a directive share a physical line
with a ruff `noqa` marker. Its comment explains carefully why a '#' inside a
QUOTED attribute value is safe (the attr regex has already consumed it). It does
not consider a leftover whose FIRST character is a hash: `split("#", 1)[0]` then
returns the empty string, `leftover` is falsy, and the directive is accepted as
carrying no attributes -- whatever malformed text followed.

HOW BAD THIS IS DEPENDS ON A FACT I DID NOT ESTABLISH: whether any comment text
reaches `_parse_attrs` with its comment marker still attached. If a Python
comment ever arrives as "# frob:todo ..." rather than marker-stripped, DSL001 is
VACUOUS for Python -- a silent-zero in the directive validator for the primary
language. My probe shows the function's behaviour in isolation, NOT that the
pipeline feeds it that shape. MEASURE THAT FIRST; it decides whether this is a
landmine or a live hole, and the two deserve different priorities.

Either way the guard is too broad as written: it should strip a trailing
comment tail, not everything from the first hash onward. A tail is a hash
PRECEDED by whitespace and followed by a linter-style marker; a leading hash is
malformed input, not a tail.

MUST-FIRE FIXTURES:
  - genuinely bad attribute syntax that begins with a hash is still flagged
  - genuinely bad attribute syntax with no hash anywhere is still flagged
MUST-STAY-QUIET FIXTURES:
  - the real T-0309 case: a valid directive with a trailing ruff noqa tail
  - a '#' inside a quoted attribute value (the case the existing comment
    defends -- must not regress)
  - `frob:todo T-0010 free text note` accepted in Rust, and in every other
    non-Python language brought into scope
  - the same still accepted in Python (no regression)

ACCEPTANCE
- The upstream per-verb routing divergence found and named with file:line, not
  worked around in `_parse_attrs`.
- A per-language table: which walkers accept `frob:todo <id> <note>` before and
  after.
- The leading-hash question measured against the real pipeline, with a stated
  verdict on whether DSL001 is vacuous for any language today.
- All fixtures committed.
