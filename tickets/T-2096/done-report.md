## Done report

`renumber_one_v2` already rewrites `tickets/**/*.md` prose citations
(`_scan_v2_reference_files`) and code `frob:`-directive/registry-
disposition lines (`_scan_code_references`), by design never touching
free-form docstring prose outside a directive line or commit-message-
adjacent text (rewriting arbitrary prose risks mangling unrelated text;
a commit message is immutable history that could never be rewritten
regardless). This ticket's own description offered two directions:
widen the rewrite, or build a surfacing mechanism. Implemented the
surfacing direction, the safer of the two.

`_unrewritten_source_citations` (new, `_renumber_v2.py`) reuses the same
search space `renumber_one_v2` already scans (`_v2_reference_files`,
`_scan_code_references`'s own `_tracked_files`), plus the already-computed
rewritten text for any file in `ref_changes`/`code_changes`, and counts
residual whole-word occurrences of `old_id` after the rewrite that WILL
be persisted. `_log_unrewritten_citations` logs one WARNING naming every
file and its leftover count -- both on `dry_run` (so a preview shows the
gap before anything is written) and on a real renumber. No new rewrite
logic was added; nothing that used to be silently dropped is now
force-rewritten -- it is disclosed instead, closing exactly the
T-2079/T-2060 hand-fix incident this ticket describes.

Positive control: a renumber whose citations are fully covered by the
existing mechanism (the renamed ticket's own `id:` field plus a sibling's
ledger-prose citation) surfaces NO warning -- the new disclosure only
fires on a genuine gap.

### Changed
```
 src/frob/tickets/_renumber_v2.py | 94 ++++++++++++++++++++++++++++++++++++++++
 tests/test_tickets_collision.py  | 65 +++++++++++++++++++++++++++
 tickets/T-2096/ticket.md         | 14 +++++-
 3 files changed, 171 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_unrewritten_docstring_prose_citation_is_surfaced` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRenumberOneV2::test_fully_rewritten_renumber_surfaces_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
