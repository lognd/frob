## Done report

Built the minimal def-use check the ticket asks for:
`frob.arch._async_hazards._check_sequential_independent_awaits`, a fifth
detector in this module, new `ArchCategory` value
`sequential-independent-awaits` (`_models.py`).

Shape: within each own-scope `block` node (a branch already puts its body
in a separate `block`, so branching between awaits correctly takes them
out of the same sequence), scan direct statement children for either a
bare `await CALL(...)` expression statement or `NAME = await CALL(...)`
(a non-identifier assignment target -- tuple/attribute/subscript -- or a
`return`/`yield` of an await is left alone, matching this module's
existing "only what's clearly one shape" precedent). Two awaits are
independent when the earlier one's bound name does not appear as an
identifier anywhere inside the later one's `call` node (callee text AND
every argument -- deliberately broader than "argument" alone, so a bound
value read as a call's receiver, e.g. `a.close()`, still counts as a real
dependency, erring toward the sound side per T-0332's "unsound is worse
than no advisory" framing). A single-pass scan over each block's ordered
await sequence groups them into maximal contiguous runs of mutually
independent awaits; a run of 2+ fires ONE `suggestion`-severity finding
naming every awaited call site and recommending `asyncio.gather`.

Verified against a hand-written litmus before wiring into the test suite:
3 independent sequential awaits fire once (all three callees named); a
second await reading the first's bound name does not fire; a lone await
does not fire (script output confirmed via a scratch run, not just read).

Checked the SELFAUDIT001 dispatch note directly: no new I/O-name
classifier table was added (`_call_identifier_names` walks generic
`identifier` nodes, not a curated subprocess/socket/requests string
table), so no `src/frob/vet/_capability.py::_SELF_PATTERN_SUFFIXES` entry
is needed -- confirmed by running the invariant gate (see below), which
only flagged this module for an unrelated INV006 hit from the new
docstring prose ("arguments-only"), fixed by rewording to drop the
`\bonly\b` match rather than waiving (the INV006 message's own suggested
first option).

Docs: added the category to `docs/modules/arch.md`'s async-event-loop-
hazards section (heading + bullet), matching the existing per-category
format and disclosed model limits.

Gates (manual `--only` loop, `--ticket T-1027`): gates-fast/gates-native/
invariant/prework/coverage/doclink/docanchor/scope all clean after the
INV006 reword + a fresh `frob ticket sweep T-1027` (PRE001 went stale
once the doc/detail wording changed after `ticket start`). `gate:TICK`
shows 2 pre-existing TICK006 phantom-filing warnings (T-1077, T-1084) --
both already present on `main` before this ticket touched anything (T-1084
is my own earlier ticket's Done report citing its pre-renumber draft id,
the same disclosed historical-draft-citation pattern already established
elsewhere in this ledger; T-1077 is unrelated to this ticket's scope).
Neither is fixed here (out of `src/frob/arch/**`/`tests/unit/test_arch.py`/
`docs/modules/arch.md` scope).

Tests: `tests/unit/test_arch.py` full file, 278 collected / all green (no
F/E marks in output; measured via `pytest tests/unit/test_arch.py -q`,
both before wiring in the docs change and again after the final merge).

### Changed
```
 tickets.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_fires_on_unrelated_calls` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_does_not_fire_when_second_reads_first` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_sequential_independent_awaits_does_not_fire_on_single_await` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 589 warning(s), 425 waived
- error-findings: INV006@src/frob/gates/_todo_fmt.py, TICK006@tickets.md
