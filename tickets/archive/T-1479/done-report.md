## Done report

Narrowed the ticket's mega-glob scope (src/frob/serve/**) to the actual
files touched before starting, per the coordinator's directive: src/frob/
serve/_tools.py, src/frob/serve/_socketd.py (server-side RPC + dispatch
table), src/frob/app/map_runner.py (the one CLI runner this pass wires,
outside src/frob/serve/** entirely -- the doc's own "CLI daemon proxy"
section already discloses that wiring the client side touches frob.app,
same as T-1128/T-1147's own precedent), plus docs/modules/serve.md,
docs/modules/app.md, docs/modules/render.md (AFFECT001's closure), and
tests/test_app_daemon_proxy.py.

Subset chosen (disclosed per the ticket's own explicit allowance): `frob
map --json`, via a new `frob_map` RPC (src/frob/serve/_tools.py) wired
into `_TOOL_DISPATCH` (src/frob/serve/_socketd.py) and a new
`_try_map_via_daemon` CLI-side helper (src/frob/app/map_runner.py),
matching the frob_stats/frob_exports (T-1127) precedent -- both sides
dump the identical `MapResult` pydantic model, so no CLI-side reshape was
needed. Restricted to the daemon's own served root (cfg.map_path unset
or "."), not `frob_exports`'s subdirectory-echo convention -- disclosed,
not silently narrower than it looks.

Two things found and corrected along the way, not part of the ticket's
own stated ask but directly adjacent to the doc section this ticket
edits:
- The doc's "Scope cut (disclosed)" section claimed outline/map/xref
  were scheduled for removal by T-0802's navigation-command sunset --
  T-0802 was actually DROPPED 2026-07-29 (superseded: the user chose
  regrouping over sunset, T-1238 un-deprecated all three under `frob
  explore`) well before this ticket started, so that claim was stale and
  would have justified never wiring `frob map` for a reason that no
  longer holds. Corrected in place.
- The doc's "Five CLI commands... today" count undercounted even before
  this ticket's own change: `frob_exports`/`frob_doable_tickets` were
  already CLI-wired (confirmed via grep across src/frob/app/*.py) but
  not named in that sentence. Corrected the count/list alongside adding
  `frob_map`.

Real gate gap found and NOT waived around silently: WIRE001's dict-table
wiring pattern (T-1684's own precedent, src/frob/gates/_wire.py::_wire_
reach_patterns) only matches a BARE name immediately after a dict
entry's colon -- every _TOOL_DISPATCH row in this file uses the
module-qualified form (`_tools.frob_map`), so EVERY entry in that table
(not just this ticket's new one) has zero real callers WIRE001's own
regex can see; the rest are grandfathered only because WIRE001 is
diff-scoped (checks newly-added symbols only). Filed T-1807 (real id,
promoted from a draft via `frob ticket promote` before this ticket's own
land so the waiver below could cite it) for the regex fix, and waived
WIRE001 on `frob_map` with `follow_up="T-1807"` -- a disclosed, evidenced
false-positive waiver naming its own fix, not an admission of unwired
code (frob_map genuinely is wired, through the same convention this
whole file already uses).

### Changed
```
 tickets/T-1479/ticket.md           | 72 ++++++++++++++++++++++++++++++++++++--
 tickets/T-draft-3febf1a9/ticket.md | 48 +++++++++++++++++++++++++
 2 files changed, 118 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_map_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 840 warning(s), 732 waived
- error-findings: none (measured, zero errors)
