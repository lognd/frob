## Done report

T-1670 had two distinct evidence-binding defects, both diagnosed only at
land time. This lands PART 1 (explicit repro designation) in full; PART 2
(node-id shape validation) is investigated below and split into a residue
ticket rather than implemented as literally worded, because the literal
ask would have broken correct, tested behavior.

PART 1 -- explicit repro designation (implemented):

`_designated_repro_test` (`frob.gates._mutation_evidence`) always took the
FIRST pytest-node-id in `ticket.evidence` as BUG002's repro test -- an
invisible bind-ORDER dependency (T-1652/T-1653/T-1635 all hit it: a
pre-existing, already-passing test bound first, the real new repro test
bound second, so BUG002 checked the wrong test and refused land for a
reason unrelated to evidence quality).

Fix: a new `Ticket.designated_repro_test: str | None` field, set via
`frob ticket evidence <id> --designate-repro NODE-ID`
(`set_designated_repro_test` in `frob.tickets._setters`, exported from
`frob.tickets`). `_designated_repro_test` now reads this field first (only
if it still resolves against `ticket.evidence` -- a designation whose id
was since `--replace`d falls back to the old positional rule rather than
checking a test no longer bound at all), falling back to the positional-
first rule for every ticket that never designates one, so pre-T-1670
behavior is unchanged by default. `set_designated_repro_test` refuses
(`Err(DesignatedReproNotInEvidence)`) designating an id not already bound
as evidence, naming the bind-first recipe. `frob ticket show` now prints a
`designated_repro_test: <id>` line whenever one is set, so the current
designation is visible without `--json`.

PART 2 -- node-id shape validation (investigated, NOT implemented as
worded; split to a residue ticket):

T-1670's text asks to "reject the pytest ::-separated form" at bind time
in favor of a dotted `path::Class.method` convention. Investigation found
this cannot be implemented as literally stated without breaking real,
tested behavior:
- `ticket.evidence` resolves against real pytest node ids
  (`matches_collected`) via an EXACT match against `collected`, which is
  always pytest's native `path::Class::method` (double-`::`) form --
  never dotted. Rejecting that form would make it impossible to bind
  evidence using a real id copied verbatim from `pytest --collect-only`.
- `normalize_evidence_separator` (T-0293) already converts DOTTED input
  INTO the pytest `::` form for storage -- the opposite direction from
  what the literal ask implies.
- The real CLI path (`_apply_evidence`) already resolves every id against
  a live collected set and rejects unresolvable/non-passing ids
  (`UnknownEvidence`/`EvidenceNotPassing`) -- most of "verify the test
  actually exists at bind time" is already true today.

Filed T-1706 (renumbers at land) with this investigation and a
narrower, safe follow-up plan: reject only genuinely malformed 3+-segment
ids at the schema layer, and separately investigate whether `frob ticket
evidence` should hint the dotted `frob:tests`-directive form of a newly-
bound id (a directive-authoring UX gap, distinct from `ticket.evidence`'s
own resolution-critical storage format).

Evidence: `tests/test_gates_mutation_evidence.py::TestDesignatedReproTest`
(2 new cases: explicit designation wins over bind order; a stale
designation not in evidence falls back to positional) and
`tests/test_ticket_evidence.py::TestSetDesignatedReproTest` (2 new cases:
designates a bound id; refuses an id not in evidence). Full
`tests/test_ticket_evidence.py` + `tests/test_gates_mutation_evidence.py`
+ `tests/test_tickets.py` (188 tests) pass unmodified elsewhere.

### Changed
```
 docs/modules/tickets.md                    |  84 ++++----
 src/frob/_cli_parsers/_ticket/_progress.py |  16 --
 src/frob/app/_config_external.py           |   2 -
 src/frob/app/config.py                     |  10 -
 src/frob/app/ticket_runner/_land_cmd.py    |   5 +-
 src/frob/tickets/_land.py                  | 198 ++++++++++--------
 tests/unit/test_land_already_landed.py     |  90 ++++++--
 tickets.md                                 | 317 ++++++++++++++++++++++++++++-
 8 files changed, 548 insertions(+), 174 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_explicit_designation_wins_over_bind_order` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestDesignatedReproTest::test_explicit_designation_not_in_evidence_falls_back_to_positional` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetDesignatedReproTest::test_designates_a_bound_evidence_id` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetDesignatedReproTest::test_refuses_an_id_not_in_evidence` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 6247 warning(s), 717 waived
- error-findings: none (measured, zero errors)
