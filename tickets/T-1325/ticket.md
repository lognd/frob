---
id: T-1325
title: 'strata: attr grammar cannot express colon-vocabulary (exposure:/subject:/jurisdiction:)
  needed by std.compliance'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- strata-core/src/parse/grammar_core.rs
- strata-core/src/parse/grammar_node.rs
- strata-core/src/parse/grammar_flow.rs
- tests/unit/strata/test_parse.py
- tickets/T-1325/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_parse.py
  reason: test coverage for the new STRING-quoted attrval surface, plus mod.rs::err()
    the already-scoped grammar_node/grammar_flow parsers call (SCOPE002 under-capture,
    pre-existing dependency not introduced by this change)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: strata-core/src/parse/mod.rs
  reason: test coverage for the new STRING-quoted attrval surface, plus mod.rs::err()
    the already-scoped grammar_node/grammar_flow parsers call (SCOPE002 under-capture,
    pre-existing dependency not introduced by this change)
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: strata-core/src/parse/mod.rs
  reason: 'revert: pulls in a large closure (lib.rs/docs) unrelated to this narrow
    grammar fix; SCOPE002 here is pre-existing (grammar_node.rs/grammar_flow.rs already
    called mod.rs::err before this ticket touched anything) -- not something this
    ticket should absorb'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1325/ticket.md
  reason: per-ticket state file the CLI itself writes at start/close; always in scope
    for its own ticket, same as tickets.md
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/strata/test_parse.py::TestParseModule::test_attr_accepts_string_quoted_colon_vocabulary
designated_repro_test: null
threat: null
component: null
---
Found while working T-1314 (sys gate compliance fold). The `std.compliance`
vocabulary (`exposure:public-web`, `privacy-policy`, `subject:*`,
`jurisdiction:*`, `retention=`, `covered-party`, `revocation`) documented in
`frob/strata/_compliance.py`'s module docstring as "opaque-string vocabulary
on the existing `attrs` tuples" has NO `.strata` grammar surface: the
`attr`/`attr` grammar keyword (`strata-core/src/parse/grammar_node.rs`,
`grammar_flow.rs`) calls `parse_attrval`, which requires a bare IDENT
(alphanumeric + `_` only, `strata-core/src/parse/lexer.rs`) -- colons and
dashes are lexed as separate symbol tokens, so `attr "exposure:public-web"`
or an unquoted `exposure:public-web` cannot be written in a real `.strata`
source file today. Confirmed by grep: zero hits for
`exposure`/`privacy-policy`/`subject:`/`jurisdiction:` anywhere under
`strata-core/src/**/*.rs`.

Practical effect: every COMPLIANCE00x/`evaluate_compliance` test in this
repo (including T-1314's own new gate-level regression tests) has to
construct a `KernelModel`/`Node` directly in Python, bypassing the `.strata`
parser entirely, because no author-writable `.strata` file can express the
compliance vocabulary at all. This means NO real hand-authored `.strata`
design file (including this repo's own `design/frob.strata`) can ever
trigger a compliance finding through `frob sys audit` or the new
`frob check` SELFAUDIT001 fold, regardless of the model's real posture --
the entire compliance-audit surface is reachable only from Python-
constructed test fixtures, not from the actual authoring surface strata
ships to users.

Mirrors the SAME class of gap `expect_ident_or_string`'s own code comment
in `strata-core/src/parse/grammar_core.rs` already flags for CWE/threat
catalog ids ("Claim ids are normally a bare IDENT ... need ':' and '-'
which IDENT cannot lex" -- solved there via a STRING-quoted alternate
surface). The compliance vocabulary needs the same treatment: either widen
`attr`'s grammar to accept a STRING-quoted attrval (mirroring
`expect_ident_or_string`'s precedent) or add a dedicated STRING-accepting
attr keyword, so a real `.strata` file can actually author
`exposure:public-web`/`subject:child`/etc.

Not touched by T-1314: strata-core grammar/Rust changes are outside that
ticket's declared scope (src/frob/gates/_sys.py, src/frob/strata/
_compliance.py, docs, tests only).