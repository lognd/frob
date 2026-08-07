## Done report

Per docs/audits/check-performance.md (T-0928), implemented the one
quick-win the audit's ranked table left genuinely open in `src/frob/
gates/**`/`src/frob/check/**` scope (rust-candidate rows static/archgate/
pii_structural/dead_symbols stayed untouched, per T-0930's ownership;
Finding 4's cross-gate shared walk is T-0946; test_gate's isolated
profile is T-0949), and re-verified two rows the audit already flagged as
possibly-resolved without confirming.

**Fixed -- row 10, `tickets` gate (2.09s, python-optimizable).**
`tickets_gate` (`src/frob/gates/__init__.py`) dispatches 8 TICK00x
rules; `_tick001_duplicate_ids`, `_tick003_stale_archive`, and
`_tick006_phantom_filing` each independently called `frob.tickets.
_store.load_all`/`load_archive`, which re-reads+re-parses the FULL
`tickets.md`/`tickets-archive.md` ledger text with no cache -- 3
redundant `load_all` + 2 redundant `load_archive` calls per
`tickets_gate` invocation, the same "same expensive input recomputed N
times, no shared cache" shape the audit's meta-gap Finding (E)
describes, one level down inside a single gate. `tickets_gate` now
loads `active`/`archived` ONCE and passes the `Result` values to all
three rules; none of the three call `load_all`/`load_archive`
themselves anymore.

Before/after (`uv run frob check --only tickets`, same checkout,
natives built, warm cache):
```
before (audit baseline, docs/audits/check-performance.md row 10): tickets=2.09s
after (2 back-to-back runs):                                       tickets=1.10s / 1.13s
after (inside full `--ticket T-0929` run, 2 more runs):             tickets=1.20s / 1.21s / 1.26s
```
~40-47% reduction, consistent across 5 measured runs.

**Verified already resolved, no code change -- row 4, `perf` gate
(9.50s).** `perf_rules` (`src/frob/perf/_rules.py`) already builds
exactly ONE shared `_EffectGraph` for PERF008+PERF012
(`shared_effect_graph = _EffectGraph(files)`, T-0919, landed before
this audit); `EffectGraph.summary`/`reachable_effect`
(`src/frob/perf/_effect_summaries.py`) memoize per-symref and per-file.
Read directly rather than assumed -- the remedy this row asks to
"investigate" is already in place. No-op, recorded so a future pass
does not re-investigate it as open.

**Verified already resolved via the T-0414 parse memo, no code
change -- row 6, `coverage` gate (5.04s).** Isolated `coverage_gate(...)`
call bracketed with `frob.lang.reset_parse_cache()`/`parse_cache_stats()`
showed 1978-1979 cache hits against only 646-648 real parses --
`_cov006`'s ~2000-call `parse_file` pattern T-0410 flagged is real in
call COUNT but already absorbed into cache hits by T-0414's memo,
matching the audit's own "0s if already memo'd" estimate. Also observed
the SAME isolated-call-slower-than-in-context anomaly Finding 5
describes for `test_gate` (isolated wall ~56-60s vs the 5.04s
`gate-summary` bracket for the same gate in a real run) -- not
root-caused here (T-0949's scope), noted in docs/audits/
check-performance.md's remediation log only so it is not rediscovered
as new.

**Not attempted, explicitly out of this ticket's scope**: row 2 (`test`
gate, T-0949's own scope), Finding 4's sys/secrets/pii_structural shared
walk (touches the rust-candidate `pii_structural` row, T-0946's scope),
and every rust-candidate row (static/archgate/pii_structural/
dead_symbols, T-0930's scope).

Doc-drift closed: `docs/audits/check-performance.md` gained a
"Remediation log (T-0929)" section with the above; `docs/modules/
gates.md`'s TICK006 section and `docs/modules/tickets.md`'s T-0162
decision record each got a short "T-0929 (perf, no behavior change)"
note (AFFECT001 fired on both `_tick006_phantom_filing`'s and
`tickets_gate`'s doc closures; both re-verified, not just re-acked).
Ticket scope was extended (`frob ticket scope T-0929 --add ...`) to
cover these three doc files, since the dispatch instruction explicitly
asked for the audit-doc append.

Changed:
- `src/frob/gates/__init__.py`: `tickets_gate`, `_tick001_duplicate_ids`,
  `_tick003_stale_archive`, `_tick006_phantom_filing` (signatures
  changed to accept pre-loaded ledger `Result`s instead of each loading
  independently); added `TicketError` to the `frob.tickets._models`
  import (needed for the new type annotations).
- `docs/audits/check-performance.md`: remediation log appended.
- `docs/modules/gates.md`, `docs/modules/tickets.md`: doc-drift notes for
  the two AFFECT001 closures above.

Evidence: `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::
test_above_default_error_threshold_errors`, `tests/test_tickets_
collision.py::TestRealLedgerIntegrity::test_no_duplicate_ids_within_or_
across_ledgers`, `tests/test_gates.py::TestTick006PhantomFiling::
test_phantom_filed_colon_fires` (all pass; full `tests/test_gates_
tickets_hygiene.py` + `tests/test_tickets_collision.py`, 20 tests, and
full `tests/test_gates.py`, 543 tests, also run and pass unchanged).

Filed: none (all out-of-scope items above were already filed as T-0930/
T-0946/T-0949 by T-0928's own Done report; nothing new found needing a
ticket).

Gates: `frob check --ticket T-0929` clean (0 errors, 4154 warnings, 219
waived -- pre-existing warning population, none new from this change).
`git diff main --diff-filter=D --stat` empty.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestRealLedgerIntegrity::test_no_duplicate_ids_within_or_across_ledgers` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_phantom_filed_colon_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4125 warning(s), 219 waived
- error-findings: none (measured, zero errors)
