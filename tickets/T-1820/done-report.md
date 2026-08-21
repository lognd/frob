## Done report

Re-verified this WIRE001 follow_up anchor after T-2746 (WIRE001's new
property/attribute-access tracing in src/frob/gates/_wire.py). This
ticket's disposition is DIFFERENT from T-1831/T-2451/T-1778 (per the
coordinator's caution, read the body before assuming it is the same
shape): `frob quality bind`'s `--list-bindings`/`--list-sources`/`--json`
argparse dests are not merely untraceable to the callgraph -- they are
permanently unwired BY DESIGN. `frob.__main__._dispatch` special-cases
`quality bind` and hands raw argv to `bind_runner.run` BEFORE `AppConfig`
is ever built (T-1567), so the parsed dests are never read by anything;
they exist purely so `--help` can discover and document the flags.
T-2746's property/attribute-access extension does not change this --
there is no property access involved at all, and no amount of better
callgraph tracing would ever find a real reader for these dests, because
none exists or ever will. Disposition unchanged: (b) genuinely dead by
design, not a detector blind spot.

The three waivers in src/frob/_cli_parsers/_quality.py (lines 92, 104,
114) already state the actual mechanism, not just the rule name:
"dispatch bypasses AppConfig construction for 'quality bind' (T-1567),
so these dests are read by nothing, by design."

Positive control, both directions, measured directly:
1. `frob check --only gates --no-cache` over the whole repo: zero WIRE001
   findings in src/frob/_cli_parsers/_quality.py -- the existing waivers
   hold.
2. Planted `_t1820_planted_dead_control` (a genuinely dead function, no
   caller anywhere) at the end of src/frob/_cli_parsers/_quality.py,
   re-ran the same check: WIRE001 fired on it immediately
   (`src/frob/_cli_parsers/_quality.py:143 WIRE001: ... is new in this
   diff and has no caller`). Confirms the gate is not blinded on this
   file -- removed the plant before landing, tree is clean.

No code change: the waivers and anchor metadata are already correct on
main. This ticket stays anchor=True/queued forever (T-1856): WIRE002
requires a real, non-terminal ticket id as follow_up, and closing this
ticket would orphan the three citations in _quality.py.

Filed: none.

### Changed
```
 tickets/T-1820/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 18 error(s), 828 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
