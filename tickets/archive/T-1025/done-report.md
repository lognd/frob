## Done report

_shared_store_write_violations/check_resource_contention (SYS203) now
accept an optional `module: Module | None` parameter. When a store id in
`store_ids` is ALSO a `Module.resources` id declaring a real arbiter
(`arbitrated_by`/`lock`), its shared-store-write finding is now skipped
entirely, the SAME discharge condition `_access.py::resource_contention_
violations` (SYS204) already applies. `module=None` (the default) keeps
every pre-existing caller's behavior byte-for-byte unchanged -- purely
additive, no signature break. New helper `_arbitered_resource_ids(module)`
mirrors `_access.py::_resource_arbiters`'s lookup.

Tests (tests/unit/strata/test_contention.py, 18 total -- 14 pre-existing
+ 4 new):
- New litmus fixture tests/unit/strata/litmus/contention_store_
  arbitered.strata: two writers into a store that DOES declare
  `resource shared_store { lock "shared.lock"; }`.
- test_arbitered_store_discharges: passing module= discharges the
  finding entirely.
- test_arbitered_store_still_fires_without_module: the OLD call shape
  (no module=) against the SAME arbitered fixture still fires -- proves
  the change is additive, not a silent behavior flip for existing
  callers.
- test_unarbitered_store_still_fires_with_module: passing module= does
  NOT blanket-discharge every store -- contention_store_vuln.strata's
  store (no resource block at all) still fires even with module
  supplied.

DISCLOSED GAP (not silently left incomplete -- the ticket's stated goal
of dropping the five design/frob.strata SYS203:tickets_ledger waivers is
NOT done this round): neither of the two LIVE callers
(src/frob/gates/__init__.py's SELFAUDIT001 gate, src/frob/app/
sys_runner.py's `frob sys audit` CLI report) passes `module=` today, and
neither has an in-scope path to source one -- src/frob/strata/
_design_load.py's DesignIds carries only elaborated KernelModels and a
merged store-id set, never the raw parsed Module (or its `.resources`).
Wiring that through touches src/frob/gates/__init__.py, which is
contested turf this wave (a sibling gates-family-splitter ticket holds
much of it) -- all three files (gates/__init__.py, sys_runner.py,
_design_load.py) are outside T-1025's own declared scope. VERIFIED
directly rather than assumed: calling check_resource_contention(model,
store_ids=...) the SAME way the live gate does (no module=) against the
CURRENT design/frob.strata still reports all five tickets_ledger
findings -- dropping the waivers now would regress `frob check --only
sys` from clean to five errors. The five waivers therefore stay in
design/frob.strata unchanged. Filed T-1146 ("strata: wire
check_resource_contention's module= param into SELFAUDIT001/sys_runner,
drop tickets_ledger SYS203 waivers") as the exact follow-up; cite its
REAL renumbered id (grep tickets.md after landing) in any status report.

docs/strata/host.md: new "SYS203 arbiter-awareness (T-1025)" subsection
under "Resource contention (SYS2xx, T-0699)" documents the capability
and the disclosed gap above, with the exact verification command.

Gate verification (all foreground, chunked):
- uv run pytest tests/unit/strata/test_contention.py -q: 18 passed.
- uv run frob check --ticket T-1025 --only gates-native: 0 errors.
- uv run frob check --ticket T-1025 --only gates-security: 0 errors.
- uv run frob check --ticket T-1025 --only static: 0 errors.
- uv run frob check --ticket T-1025 --only gates-fast: 26 remaining
  errors, ALL pre-existing/unrelated -- 24 COV003 findings citing
  strata-core/src/parse.rs::tests::* evidence on FIVE unrelated,
  already-closed tickets (T-0138/T-0226/T-0629/T-0700/T-0702); these
  became stale because T-1099 (landed on main before this ticket
  started, unrelated to T-1025) split parse.rs into strata-core/src/
  parse/*.rs, moving those Rust tests out from under their old path --
  verified this predates T-1025 (T-1099 is a sibling wave-18 ticket, not
  touched by this diff). 1 COV001 on src/frob/gates/_tracked_files.py
  (untouched by this diff). 1 TICK006 on T-1114's own phantom draft
  citation (different, already-landed ticket's residue).
- uv run frob check --ticket T-1025 --only lint: 0 errors in this
  ticket's own files; the 6 remaining ruff-check errors are pre-existing
  in src/frob/vet/_capability.py and src/frob/vet/_supplychain.py.
- git diff main --diff-filter=D --stat: empty.

### Changed
```
 docs/strata/host.md                                |  34 ++
 src/frob/strata/_contention.py                     |  71 ++-
 .../litmus/contention_store_arbitered.strata       |  38 ++
 tests/unit/strata/test_contention.py               |  47 ++
 tickets.md                                         | 480 ++++++++++++++++++++-
 5 files changed, 657 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_arbitered_store_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_arbitered_store_still_fires_without_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_unarbitered_store_still_fires_with_module` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
