---
id: T-0838
title: 'tickets ledger: schema-extending features brick their own land (extra_forbidden
  on new fields, empty collections serialized)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/__init__.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestQueue::test_unknown_frontmatter_key_is_tolerated
- tests/test_tickets.py::TestQueue::test_unknown_field_with_malformed_known_field_still_errs
- tests/test_tickets.py::TestEmptyCollectionOmission::test_dict_without_empty_collections_returned_unchanged
- tests/test_tickets.py::TestEmptyCollectionOmission::test_empty_list_and_tuple_values_dropped
- tests/test_tickets.py::TestEmptyCollectionOmission::test_reviews_empty_never_serialized
- tests/test_tickets.py::TestEmptyCollectionOmission::test_reviews_populated_still_serializes
- tests/test_tickets.py::TestEmptyCollectionOmission::test_ticket_with_empty_reviews_round_trips_through_ledger
- tests/test_tickets.py::TestUnknownFieldForwardCompat::test_unknown_field_loads_without_exception
- tests/test_tickets.py::TestUnknownFieldForwardCompat::test_unknown_field_logs_warning_named
- tests/test_tickets.py::TestUnknownFieldForwardCompat::test_unknown_field_preserved_verbatim_on_reserialize
- tests/test_tickets.py::TestUnknownFieldForwardCompat::test_known_field_still_validated_strictly
designated_repro_test: null
threat: null
component: null
---
Hit live twice: T-0571's original land (yesterday, donor branch) and its
salvage land today both broke because the feature adds a new Ticket
field (reviews:) to the ledger schema, and land/close run the ROOT
checkout's OLD frob build, whose pydantic model is extra_forbidden --
MalformedFrontmatter, then NotFound at land. Any schema-extending
feature bricks its own landing; today's workaround was hand-deleting the
empty `reviews: []` line from the worktree ledger before close.

Fix (two halves):
1. Serializer: omit empty/default collection fields when rendering
   ledger blocks (reviews: [] should never be written), so additive
   fields only appear once populated.
2. Parser forward-compat: ledger Ticket model should tolerate UNKNOWN
   fields with a loud warning naming the field and the likely
   cause (older frob reading a newer ledger) instead of hard-failing
   extra_forbidden -- preserve-and-round-trip unknown fields so a land
   by an older binary does not strip data recorded by a newer one.
   Keep validation strict for KNOWN fields.