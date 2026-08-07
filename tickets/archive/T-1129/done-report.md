## Done report

Changed:
src/frob/gates/_tickets_gate.py::_tick011_disclosed_cuts_without_ticket (new, TICK011)
src/frob/gates/_tickets_gate.py::_tick011_disclosure_hits (new)
src/frob/gates/_tickets_gate.py::_tick011_preceded_by_technical_token (new)
src/frob/gates/_tickets_gate.py::tickets_gate (wired TICK011 in)
src/frob/gates/_waive.py (_KNOWN_GATE_RULES += "TICK011")
docs/modules/gates.md#tick011-t-1129 (new section) + summary table row
docs/modules/tickets.md#decision-record-t-0162 (AFFECT001: tickets_gate's docstring changed, noted TICK011 is unrelated to the id-collision decision this section documents)
design/frob.strata (sys sync-interface: +TestTick011DisclosedCutWithoutTicket)

New WARN-tier TICK011 rule: a Done report's prose disclosing deferred/cut
work (a conservative, multi-word disclosure-phrase scan -- "left for/as a
follow-up", "not yet/not ticketed", "deferred to/as/for a follow-up",
bare "residue"/"residual", "scope cut"/"cut from/for this/the
pass/scope/ticket") fires unless a T-####/T-draft-<hex> id resolving to a
real ledger block, or an explicit no-ticket-needed reason, appears within
300 chars of the disclosure (mirrors TICK006's own claim-window
precedent). One finding per ticket (first uncited occurrence), not one
per phrase hit -- conservative on noise for a WARN-tier first turn-on.

Calibrated against THIS repo's live ledger per the wave instruction
("frob's own ledger findings fixed or dispositioned in the same land"):
running the new rule cold against tickets.md found exactly ONE false
positive (T-1111's Done report used "residue"/"residual" as this
codebase's own term of art for "remaining finding count" -- "7
residual", "WARN residue", "REG010 residue", "gate:WAIVE residue" --
never disclosed leftover scope). Fixed by excluding a "residue"/
"residual" hit whose immediately-preceding word is a technical token (a
digit, an ALL-CAPS/rule-id-shaped word, or a `namespace:NAME` colon)
rather than ordinary prose, not just a narrower fixed-digit lookback (a
digit-only exclusion still fired on "WARN residue"/"gate:WAIVE
residue"). Verified: TICK011 fires 0 findings against this repo's real
`tickets.md`/`tickets-archive.md` after the fix (measured via a direct
`_tick011_disclosed_cuts_without_ticket(queue, archived)` call against
this checkout).

Evidence:
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_not_yet_ticketed_with_no_citation_fires
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_explicit_no_ticket_needed_reason_is_silent
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_no_disclosure_phrase_is_silent
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_one_finding_per_ticket_not_per_phrase
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure
8/8 pass: `pytest tests/test_gates.py -k Tick011 -q` (measured: "........  [100%]").
Acceptance [0] bound to the real-citation-suppresses test; acceptance
[1] (new, T-0756/T-1155's new-gate-rule-acceptance policy for the new
TICK011 entry in _KNOWN_GATE_RULES -- a before-fails/after-passes fixture
proof through the PRODUCTION tickets_gate() invocation) bound to
test_disclosed_follow_up_with_no_citation_fires: this fixture fires 0
findings against the pre-T-1129 tickets_gate (no TICK011 check existed)
and 1 finding against the post-T-1129 tickets_gate.

Filed: none

Gates: `frob check --ticket T-1129` chunked (gates-fast, gates-native,
gates-security, lint, static) all 0 errors for files this diff touches.
gates-security initially flagged 4 real PII012 name-signature false
positives on 'token' in my own new code (the same "lexical token from
prose, not a credential" class frob.gates._docptr already carries a
waiver for) and a SELFAUDIT001 interface drift -- both fixed in this
same land (frob:waive PII012 x2 sites, frob sys sync-interface run and
committed). lint shows pre-existing ruff-format/ruff-check findings in
unrelated files only; my five touched files (src/frob/gates/
_tickets_gate.py, src/frob/gates/_waive.py, tests/test_gates.py,
docs/modules/gates.md, docs/modules/tickets.md) are ruff-check/
ruff-format clean.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_not_yet_ticketed_with_no_citation_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_explicit_no_ticket_needed_reason_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_no_disclosure_phrase_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_one_finding_per_ticket_not_per_phrase` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
