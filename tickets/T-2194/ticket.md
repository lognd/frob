---
id: T-2194
title: 'T-2187 follow-up: no permanent full-corpus regression test for walk_strata''s
  grammar-vs-locator reconciliation (manual verification only, prose in a closed ticket)'
state: queued
kind: invariant
origin: human
created: '2026-08-16'
priority: medium
parent: T-2187
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_lang_strata.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2187 follow-up. `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols`
has two minimal repro tests (a quoted-string claim id, a `resource`
declaration) plus unit coverage of `_locate_declared_items`'s fail-closed
contract, but no PERMANENT regression test walking the whole real
`.strata` corpus. T-2187's own Done report verified this manually
(all 64 tracked `.strata` files walk with zero `Err` under the fix) but
that verification is prose in a closed ticket, not a checked-in guard --
nothing stops a future change to `_walk_strata.py` or a new `.strata`
construct kind from silently reintroducing drift with no test catching it.

Why this wasn't done in T-2187 itself: a corpus-wide test needs
`subprocess.run(["git", "ls-files", "*.strata"])` (or an equivalent
directory walk) plus `Path.read_text()` over every match. Both calls
inside `tests/unit/test_lang_strata.py` trip
`frob.strata._effects.py`'s SYS100 self-conformance scan for that file's
`testsuite` node -- the design does not declare an `exec`/`fs.read`
capability grant for this specific file, only for a curated allowlist
(`design/frob.strata`'s `may "eval"/"exec" via "tests/..."` clauses).
Granting it requires editing `design/frob.strata`, which was outside
T-2187's declared scope (`src/frob/lang/_walk_strata.py`,
`tests/unit/test_lang_strata.py`).

WANTED:

1. Add a `may` clause to `design/frob.strata`'s `testsuite` node granting
   `tests/unit/test_lang_strata.py` the specific capability(ies) the new
   test needs (`exec` for `subprocess.run`, `fs.read` for `.read_text()`
   -- or route through an existing helper that already carries the grant,
   if one exists, to avoid widening the allowlist at all).
2. Add a permanent test to `TestGrammarAuthoritativeSymbols` (or a new
   class) that walks every `git ls-files '*.strata'` result and asserts
   `walk_strata(source).is_ok` for all of them -- the same check T-2187's
   Done report ran manually, made durable.
3. Verify `frob.strata._effects.py`'s self-conformance suite
   (`test_conform_eval_needle.py`, `test_selfconform.py`) still passes
   with the new grant -- confirms the grant is scoped narrowly enough not
   to leak capability to unrelated code in the same file.

Acceptance: the new corpus-wide test must FAIL if reverted against
T-2187's fix (i.e. it genuinely exercises the grammar-vs-locator
reconciliation across the real corpus, not a synthetic single-file
check) -- confirm by running it against `_walk_strata.py`'s pre-T-2187
shape (`git show <T-2187-parent>:src/frob/lang/_walk_strata.py`) and
observing failures on the same 16 files T-2187's Done report already
named.
