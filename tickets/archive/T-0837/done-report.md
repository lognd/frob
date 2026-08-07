## Done report

Changed:
- docs/modules/tickets.md -- new `## Structured review channel (T-0571)`
  section (anchor `#structured-review-channel-t-0571`), placed after the
  `## Public API` listing. Covers `frob ticket review` CLI usage
  (--verdict/--reviewer/--findings-file/--commit, the blank-findings and
  unresolvable-commit error behavior), `close --strict` combined with
  `[tickets] require_review_for_close` in frob.toml (both must be true to
  gate), and the `ReviewVerdict`/`ReviewEntry`/`Ticket.reviews` shape plus
  the three review-specific `TicketError` variants.
- src/frob/tickets/__init__.py::record_review -- `frob:doc` repointed from
  `#public-api` to `#structured-review-channel-t-0571`.
- src/frob/app/ticket_runner.py::_review -- `frob:doc` repointed from
  `#public-api` to `#structured-review-channel-t-0571`.

Not touched (left as-is, not part of the disclosed T-0571 workaround):
`ReviewVerdict`/`ReviewEntry` already pointed at `#data-models`;
`load_require_review_for_close` and `has_approved_review_for_commit`
in src/frob/tickets/__init__.py keep their existing `#public-api` anchor
(their own established convention, not the two anchors T-0571's Done
report named as the workaround).

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(docs-only ticket, no new pytest surface of its own -- CLI-dispatch
integration test per playbook section 5, ran green:
`uv run pytest tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches -q`
-> 1 passed).

Filed: none.

Gates: `uv run frob check --ticket T-0837 --only lint` -- 2 ty errors,
both pre-existing native-extension `unresolved-import` failures
(`strata_core`/`frob_core`) unrelated to this change (worktree has no
`make core` build), not touching any scoped file.
`uv run frob check --ticket T-0837 --only static` -- 0 errors (warnings
only, all pre-existing frob-exports/frob-arch/frob-dup noise unrelated to
scope).
`uv run frob check --ticket T-0837 --only gates-fast` -- after refreshing
the pre-work sweep (`frob ticket sweep T-0837`, PRE001 was stale from the
scope addition), gate:PRE clean; gate:COV/gate:DRIFT FAIL counts are
pre-existing repo-wide findings, none in the three files this ticket
touched (verified: no `record_review`/`_review`/new-anchor line appears
in either gate's error list; the only DRIFT001 hits in
src/frob/tickets/__init__.py are the pre-existing waived `doable`/
`transition` T-0453 entries, untouched by this ticket). No new anchor
(`#structured-review-channel-t-0571`) produced a docanchor/DOC/COV
violation.
