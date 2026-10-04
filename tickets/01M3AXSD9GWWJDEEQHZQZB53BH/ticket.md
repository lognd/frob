+++
id = "01M3AXSD9GWWJDEEQHZQZB53BH"
title = "DOC006: ticket-body pointers inside the ticket's own or blocker's scope are future-facing, not findings"
type = "task"
category = "triage"
priority = "high"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6448"]
labels = ["milestone:0.535.0", "v1-cluster:F1"]
scope = ["src/frob/gates/_docptr.py", "tests/test_docptr_ticket_scope.py", "tests/fixtures/docptr_ticket_scope/", "docs/modules/gates.md"]
+++

Measured 2026-09-25: T-5372's land was refused by DOC006 on a SIBLING
ticket's body (tickets/T-5880/ticket.md:73, 'docs/modules/store.md' is
not a tracked file). The land promotes queued sibling drafts and lints
their bodies as touched files; a freshly filed feature ticket naturally
names the module, doc and fixture paths it will CREATE, so 39 of the 52
STORE tickets filed that night carried pointers to files that do not
exist yet. The only remedy today is a `frob:waive DOC006` line pasted
into every body, which is a command where automatic behaviour is
guaranteed safe (owner directive: automatic over commands; tiered
safety).

Deliver:
- DOC006 (and DOC004 if it shares the resolver) treats a pointer in a
  tickets/<id>/ticket.md body as future-facing, NOT a finding, when the
  path falls inside that ticket's own declared scope (or its parent's
  derived scope), or inside the scope of any ticket the pointer's ticket
  is blocked by (the scaffold-creates-it case). Log the exemption at
  debug with the matching scope glob.
- A pointer outside every such scope still fires, so a genuine typo in a
  body is still caught.
- Positive control: fixture with three tickets -- a scaffold owning
  src/frob/x/, a leaf blocked by it that names src/frob/x/_y.py (must
  NOT fire), and a leaf naming docs/modules/typo.md outside every scope
  (must fire).
- docs/modules/gates.md DOC006 row documents the scope-based exemption
  and its tier (automatic).
