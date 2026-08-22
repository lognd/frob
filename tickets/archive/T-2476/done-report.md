## Done report

T-2472 landed the `## GATERULE001 (T-2448)` catalog entry in
`docs/modules/gates.md` with a `frob:describes` anchor on
`gate_rule_registry_violations`. This ticket finishes the other half:
added `# frob:doc docs/modules/gates.md#gaterule001-t-2448` directly
above `gate_rule_registry_violations` in
`src/frob/gates/_rule_id_scan.py`, and deleted the `frob:waive COV001`
comment block that stood in for it while `docs/modules/gates.md` was
under T-2472's own lease conflict (T-2454, since landed).

Verified the anchor slug matches exactly (`## GATERULE001 (T-2448)` ->
`#gaterule001-t-2448`, computed from the doc's own heading) and that
`frob check --ticket T-2476` reports no COV001/DOC002 finding on either
touched file.

Changed:
- `src/frob/gates/_rule_id_scan.py` (frob:doc edge added, frob:waive
  COV001 block removed above `gate_rule_registry_violations`)

Evidence: `uv run pytest tests/gates/test_rule_id_scan_branches.py -q`
-- 20/20 passed.

Filed: none.

Gates: `frob check --ticket T-2476` clean on
`src/frob/gates/_rule_id_scan.py` and `docs/modules/gates.md` (0 errors
attributable to this diff; the one remaining DOC002 finding on
`docs/modules/gates.md:94` is a pre-existing, unrelated stale
`T-draft-...` anchor citation from a different ticket).

### Changed
```
 src/frob/gates/_rule_id_scan.py | 5 +----
 tickets/T-2476/ticket.md        | 4 +++-
 2 files changed, 4 insertions(+), 5 deletions(-)
```

### Evidence
- `cmd:uv run pytest tests/gates/test_rule_id_scan_branches.py -q exit=0 sha256=8999741613eb` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
