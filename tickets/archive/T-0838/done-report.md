## Done report

Fixed the two halves of the schema-extending-feature/land brick:

1. Serializer: added `omit_empty_collections` (src/frob/tickets/_models.py)
   plus a `Ticket` `model_serializer(mode="wrap")` that filters any
   empty list/tuple field out of the rendered dict before it hits YAML --
   systematic (every default-empty tuple field: blocked_by, scope_changes,
   evidence, reviews, attachments, acceptance, labels), not a reviews-only
   special case. `reviews: []` (and its peers) now never appear in a fresh
   ledger block; populating any of them still serializes normally.

2. Parser forward-compat: `Ticket.model_config` changed from
   `extra="forbid"` to `extra="allow"`. Unknown ledger keys land in
   pydantic's own `__pydantic_extra__` capture, a new `model_validator(mode
   ="after")` (`_warn_unknown_extras`) logs a WARNING naming the ticket id
   and the unknown field(s), and they round-trip back out automatically on
   the next `model_dump` (pydantic includes `__pydantic_extra__` in the base
   dump the wrap-serializer wraps) -- so an OLDER frob binary landing a
   NEWER worktree's ledger preserves data it cannot interpret instead of
   stripping it. Known-field validation is untouched: a malformed known
   field (e.g. `state: not-a-real-state`) still fails MalformedFrontmatter
   even alongside an unknown field.

Updated the one pre-existing test that asserted the OLD extra_forbidden
behavior (`test_unknown_frontmatter_key_is_err` -> renamed/rewritten as
`test_unknown_frontmatter_key_is_tolerated`, plus a new sibling test that
keeps known-field strictness covered) and added two new test classes:
`TestEmptyCollectionOmission` (serializer half) and
`TestUnknownFieldForwardCompat` (parser half, including the exact incident
reconstruction: an unknown `reviews_v2:` field parses without exception,
logs a WARNING naming it, round-trips byte-for-byte on re-serialization via
`_render_section`, and a malformed known field alongside it still errors).

TicketSpec (construction-time input, never loaded from a ledger) was left
`extra="forbid"` -- the forward-compat relaxation only applies to the
ledger-loaded `Ticket` model, which is the actual land/close hazard.

Deviations: none from the ticket's stated plan. DoneReportClaims/render_
claims_block (T-0754/T-0832) were read and left untouched -- they are a
sibling BaseModel unaffected by this ticket's scope, unmeasured-marker
rendering still passes its existing tests.

Gates: `frob check --ticket T-0838` chunked over lint/static/gates-fast/
gates-native/gates-security all report 0 errors (measured after `frob
ticket sweep T-0838` to refresh PRE001 following late test edits). ruff
check/format clean under both PATH ruff and `uv run ruff`. `git diff main
--diff-filter=D --stat` is empty.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets.py::TestQueue::test_unknown_frontmatter_key_is_tolerated` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestQueue::test_unknown_field_with_malformed_known_field_still_errs` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEmptyCollectionOmission::test_dict_without_empty_collections_returned_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEmptyCollectionOmission::test_empty_list_and_tuple_values_dropped` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEmptyCollectionOmission::test_reviews_empty_never_serialized` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEmptyCollectionOmission::test_reviews_populated_still_serializes` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEmptyCollectionOmission::test_ticket_with_empty_reviews_round_trips_through_ledger` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestUnknownFieldForwardCompat::test_unknown_field_loads_without_exception` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestUnknownFieldForwardCompat::test_unknown_field_logs_warning_named` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestUnknownFieldForwardCompat::test_unknown_field_preserved_verbatim_on_reserialize` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestUnknownFieldForwardCompat::test_known_field_still_validated_strictly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 1201 warning(s), 209 waived
