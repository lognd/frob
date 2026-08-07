## Done report

Registered `_UNION_ZONES` (T-1002) for the three chronic conflict hotspots
named in docs/audits/coordination-churn.md item 3: `frob.toml`'s
`[gates.severity]` block, `_KNOWN_GATE_RULES` in `src/frob/gates/__init__.py`,
and `docs/audits/*.md` remediation logs. Each keyed-lines zone is delimited
by `# frob-zone-start <name> T-1002` / `# frob-zone-end <name> T-1002`
marker comments (not `frob:` prefixed, to avoid tripping the directive
scanner); the `docs/audits/*.md` zone is unmarked (whole-file append-only).

Land-side resolution lives entirely in `_land.py`, hooked into
`_auto_resolve_out_of_scope_conflicts` (shared by both the merge-main-into-
worktree and squash-onto-root conflict paths) BEFORE the existing in/out-of-
scope split, so a zone file that is itself in the landing ticket's own
scope (e.g. a ticket editing `[gates.severity]`) still gets union-merged
instead of being left as a hard in-scope conflict:

- `_resolve_conflict_blocks` parses git's own `<<<<<<</=======/>>>>>>>`
  conflict markers directly out of the working-tree file (diff3 `|||||||`
  base block tolerated but ignored) and resolves each block via the zone's
  strategy.
- `kind="keyed_lines"` (`_union_keyed_chunks`/`_chunk_by_key`): each side is
  split into per-key chunks (leading comments stay attached to the entry
  they annotate); every key present on either side survives; a key present
  on BOTH sides with differing chunk text is a TRUE CONTRADICTION and
  refuses (returns `None`) rather than guessing -- the file is left
  conflicted exactly as before this ticket, falling through to the existing
  manual-resolution abort path.
- `kind="append_only"` (`_union_append_only`): pure concatenation of both
  sides' new content (used for `docs/audits/*.md`).
- A keyed-lines zone additionally refuses (leaves conflicted) if ANY
  conflict block in the file falls outside its `marker_start`/`marker_end`
  region -- a conflict there is not this zone's business to silently
  resolve.

Acceptance criterion (two sequential lands with distinct appends needing
zero manual resolution) is exercised by `test_resolve_stages`, which builds
a real git-conflicted `frob.toml` (two branches each appending a distinct
severity entry) and asserts `_resolve_union_zone_conflicts` stages a merged
file with both entries present and no leftover conflict markers, no manual
step. `test_keyed_lines_union_refuses` covers the true-contradiction refusal
half of the acceptance criterion (two different severities for one rule).

Cut: this ticket does not touch `git.attributes`/a merge-driver -- resolution
happens land-side only (the ticket body explicitly offered "land-side union
merge ... or a merge driver" as alternatives; land-side was chosen since
`_land.py` already owns every other conflict-resolution decision point in
this repo, e.g. tickets.md's splice).

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 8253 warning(s), 333 waived
- error-findings: none (measured, zero errors)
