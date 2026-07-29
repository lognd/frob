# Ticket kinds and states

<!-- frob:describes src/frob/tickets/_models.py::TicketState -->

## What it is and where it lives

`src/frob/tickets/_models.py` holds eight `StrEnum` registries. The three
most relevant to this guide: `TicketState` (the six-state queue state
machine: `queued`, `planned`, `in-progress`, `blocked`, `done`,
`dropped`), `TicketKind` (what a ticket represents: `feature`, `bug`,
`security`, `ux`, `docs`, `invariant`, `incident`), and `Stride` (STRIDE
threat categories, used only on `kind=security` tickets: `spoofing`,
`tampering`, `repudiation`, `info-disclosure`, `denial-of-service`,
`elevation-of-privilege`). `TicketTier` (T-0715) is a separate registry
governing the epic -> story -> ticket hierarchy: `epic`, `story`,
`ticket` (default). The remaining four (`Priority`, `Origin`,
`ScopeChangeOp`, `ReviewVerdict`) are out of this guide's scope. The
full state machine diagram and transition rules live in
`docs/modules/tickets.md#state-machine` -- this guide covers only how to
add a new enum member; that doc is the reference for the machine itself.

## Add-an-entry recipe (new kind or state)

1. Add the `StrEnum` member in `_models.py`.
2. Grep for every exhaustive `match`/`if`-chain over the enum (`TicketState`
   in particular is matched exhaustively in `_store.py`'s transition
   validator and in the CLI's `frob ticket` subcommand dispatch) and add
   the new arm. There is no `Literal`-based exhaustiveness check today --
   a missed arm falls through to a default case rather than a type error.
3. If the new state changes the state machine's legal-transition graph
   (adding a state is almost always a state-machine change, not just an
   enum change), update the transition table in `_store.py` and the
   diagram in `docs/modules/tickets.md#state-machine`.
4. If the new kind needs kind-specific fields (the way `security` tickets
   carry a `Stride` category), add the field to `Ticket` as
   `<field> | None = None` and validate it is set exactly when
   `kind == <new kind>` (mirrors how `Stride` is required only for
   `kind="security"`).

## Drift-locks that fire

- No dedicated gate enforces enum-exhaustiveness across every consumer
  (the "grep for every match arm" step above is manual). A new state that
  is legal per `_models.py` but has no transition-table entry in
  `_store.py` will be rejected at ticket-transition time with a runtime
  error, not a `frob check` failure.
- **COV001/TEST00x** apply normally to the new enum member and any new
  field.
- **DOC001/DOC002** applies normally for the `frob:doc` edge into
  `docs/modules/tickets.md#data-models`.

## Worked example

`Stride` (STRIDE categories) is the worked example already in the
codebase: it was added as a `security`-kind-only field, required exactly
when `TicketKind.SECURITY` is set, validated in `Ticket`'s pydantic model
via a `model_validator`, and documented in
`docs/modules/tickets.md#data-models` alongside `TicketKind`/`TicketState`.

## Common mistakes

- Adding a new `TicketState` without updating the transition table --
  `frob ticket doable` and `frob ticket start/close` both consult the
  transition table, not just the enum, so a new state that "exists" per
  the type system but has no legal transitions in or out of it is a dead
  end no ticket can ever reach or leave.
- Reusing `dropped` semantics for a new "cut but might resume" state
  instead of adding a real new state -- `dropped` is terminal by design
  (`docs/modules/tickets.md#state-machine`); a resumable cut needs its own
  state, not an overload of an existing terminal one.

## See also

- `docs/modules/tickets.md#state-machine` -- the full transition diagram
  and per-state semantics.
- `docs/modules/tickets.md#data-models` -- `Ticket`, `TicketKind`,
  `TicketState`, `Stride` field-level reference.
