## Done report

The deletion filter asked a lexical question in place of a semantic one.

_deletion_glob_too_broad decided whether a scope entry may authorize a
deletion by testing `"/" not in stripped`. The intent (D-12) is to refuse
a bare top-level DIRECTORY like `src` (expanded to `src/**`), which would
silently authorize deleting anything beneath it. But the property it
actually tested was punctuation, so it also refused every exact
root-level FILE path -- `FROBLEMS.md`, `tickets.md`, `README.md` -- while
continuing to trust `src/frob/tickets/**`, which matches hundreds of
files. The narrowest possible authorization was treated as the broadest.

The consequence was unsatisfiable: the refusal printed the scope
containing the exact path and then told the operator to add that path to
scope. No root-level file could be deleted through a scoped land at all.
T-1612 (removing the tracked FROBLEMS.md artifact) could not land.

FIX

Breadth is now decided by what the pattern MATCHES. A pattern with no
wildcard metacharacter (`*`, `?`, `[`) is exact -- it authorizes exactly
one path -- and is trusted at any depth, root included. The pre-existing
refusals are untouched: `src/**`, `docs/**`, `.`, and `*` are still
over-broad, and a deep glob like `src/frob/tickets/**` is still trusted.

Two regression tests lock the distinction rather than leaving it to be
re-derived: one for exact paths (including that an exact path authorizes
ONLY itself), one asserting the wildcard breadth rules are unchanged, so
a future edit cannot quietly loosen the guard while "fixing" it.

VERIFIED, NOT ASSUMED

I predicted `_deletion_glob_too_broad("src")` should be True and
`("docs/**")` False; the test disagreed on both and was right. Bare `src`
never reaches this function -- `_scope_globs` expands directory entries
to `/**` upstream -- and `docs/**` IS a bare top-level directory glob,
correctly refused by D-12. Only the exact-file case was a genuine defect.

COLLATERAL: MAIN WAS RED

The T-1619/T-1618 land put three gate errors onto main that this ticket
also fixes, since a red main blocks every subsequent land:

- ARCH001 `refuse_if_land_in_progress` (90 lines) -- extracted
  `_land_flock_probe`, then `_refuse_for_held_land_lock` when the first
  extraction tripped ARCH103, and dropped a redundant `str(path)` so the
  probe no longer mixes I/O with string-formatting.
- ARCH001 `_land_precheck` (70 lines) -- the bulk was a docstring passage
  explaining `check_already_landed`'s default, which belongs on
  `_check_already_landed` itself. Moved rather than trimmed, and the
  docs section now leads with T-1675's point: the opt-in default is a
  symptom of a signal that cannot distinguish "already landed" from
  "docs-only ticket", not a design conclusion.
- PII012 `_leases.py:984` -- renamed a `token` loop variable to `arg`.

### Changed
(no changed files detected)

### Evidence
- `tests/test_evidence_integrity.py::TestD12DeletionFilterBroadScope::test_exact_root_level_file_authorizes_its_own_deletion` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestD12DeletionFilterBroadScope::test_wildcard_breadth_rules_are_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 650 warning(s), 717 waived
- error-findings: none (measured, zero errors)
