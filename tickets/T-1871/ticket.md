---
id: T-1871
title: Make duplicate bracket-attr values a strata PARSE ERROR, then delete SYS108
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- strata-core/src/parse/grammar_core.rs
- src/frob/strata/_selfconform.py
- src/frob/gates/_waive.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
OWNER DIRECTIVE, 2026-08-08: interface entries should be unique. The
owner asked whether to swap the bracket-list surface `interface=[...]`
for Python set syntax `interface={...}`. Recommendation taken: do NOT
swap the sigil; enforce uniqueness in the PARSER instead. Reasons, in
case this is revisited:

- `{` is already the block delimiter throughout the grammar (node
  bodies, every construct in `strata-core/src/parse/grammar_flow.rs`).
  A brace value form after `=` needs lookahead to disambiguate and
  degrades the error message on the commonest typo.
- Python set literals SILENTLY DEDUP: `{a, a}` becomes `{a}`. That is
  the intuition the sigil imports, and silent dedup is strictly worse
  than the status quo because it destroys the signal instead of raising
  it. Choosing a sigil whose everyday meaning contradicts the rule is a
  trap for every future reader.
- The bracket form is NOT interface-specific. `attr foo=[a, b, c]` is
  generic sugar expanding to `foo=a`/`foo=b`/`foo=c` for any key
  (`grammar_core.rs::parse_attrval`, T-1198). A brace variant would add
  a second surface form for one concept, or special-case one key name in
  the grammar. Both are parser duplication.

REQUIRED: make a repeated value for the same key inside `[...]` a PARSE
ERROR, naming the key and the duplicated value.

    attr interface=[Foo, Bar, Foo];
                              ^^^ duplicate value for key 'interface'

The change is small and local: `parse_attrval` already loops building
`values`; a seen-set check inside that loop is the whole fix. No
downstream consumer changes, because the elaborated model for accepted
input is byte-for-byte what it is today.

WHY PARSE-TIME BEATS THE GATE IT REPLACES. SYS108
(`_duplicate_interface_violations`, T-1624) currently checks this at gate
time. Parse-time is earlier, fires everywhere the parser runs rather than
only under `frob check`, and is UNWAIVABLE -- SYS108 has a waiver channel
(`_waive.py:900-909`, T-1800). Most importantly it makes the bad state
UNREPRESENTABLE rather than merely detected.

SO DELETE SYS108 AS PART OF THIS, and its `_KNOWN_GATE_RULES` entry, its
row in `docs/modules/gates.md`, its member in that file's
`frob:enumerates` list (these two must move together or DOCENUM001
fires), and its waiver precedent. That is the standing directive -- prefer
deleting a rule over keeping a mechanism to manage it -- and it only
becomes available once the state cannot be written at all. Audit for
existing `frob:waive SYS108` sites before cutting; if any exist they are
now parse errors and must be fixed, not carried.

SCOPE DECISION THE IMPLEMENTER MUST NOT MAKE ALONE: this makes
uniqueness apply to EVERY bracket attr (`may=`, `assume=`, ...), not just
`interface=`. That is believed correct -- a repeated `may=exec` is
equally meaningless -- but it is a language-wide change. Run it against
all 64 tracked `.strata` files FIRST and report any existing duplicates
before landing; a real duplicate somewhere is evidence the assumption is
wrong, and it must be surfaced rather than auto-removed.

SEQUENCING: after T-1870 (both touch `docs/strata/surface.md`, and
deleting SYS108 only makes sense once the sync mirror is gone).
