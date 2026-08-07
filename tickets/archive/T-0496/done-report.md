## Done report

Root cause confirmed at the exact repro (`docs/audits/strata.md` G5):
`FactBase.reachable`'s single `_NON_TRANSITIVE_ATTRS` set (`krb_no_transit`,
`utility`) was honored identically for BOTH `through_barriers` modes, but
`through_barriers=False` (the confidentiality `noflow` closure,
`_claims.py::_first_noflow_witness`) is the ONLY caller that omits
`through_barriers` -- confirmed by grep, every other caller (`reach`/
`independent`/`readers`/krb-movement/breach) explicitly passes
`through_barriers=True`. So `utility`'s terminal-edge effect was, in
practice, felt EXCLUSIVELY by the security-critical confidentiality check,
never by any capacity/availability closure (`demand`/`worst_age` do not
even consult `_NON_TRANSITIVE_ATTRS` -- they build a different edge shape
entirely).

`strata-core/src/lib.rs::reachable`'s BFS: once a node is reached ONLY via
a non-transitive edge, it is added to `paths` (so it counts as "reached")
but NOT enqueued into the frontier -- so its OWN further outgoing edges,
even fully transitive ones, are never explored. The repro (`log_hub{utility}`
secret_store->logger, then a real `leak` edge logger->foreign_sink) hits
this exactly: `logger` is reached via the terminal `utility` edge, so
`leak` is never walked, and `noflow(secret_store, foreign_sink)` PROVED
despite a genuine two-hop leak.

Fix (entirely within `src/frob/strata/_facts.py`, no Rust change needed,
matching the ticket's declared scope): split the non-transitive attr set
by `through_barriers` mode. Added `_NOFLOW_NON_TRANSITIVE_ATTRS =
frozenset({"krb_no_transit"})` -- `utility` is excluded from it.
`reachable()` now picks `_NON_TRANSITIVE_ATTRS` (unchanged, both attrs)
when `through_barriers=True`, and `_NOFLOW_NON_TRANSITIVE_ATTRS` (`krb_no_
transit` only) when `through_barriers=False`. `krb_no_transit` keeps its
existing behavior in both modes (no known equivalent gap for it named by
the ticket, and no caller currently reaches it through the confidentiality
path anyway -- `_krb.py`'s synthesized flows feed the `through_barriers=
True` movement closures). `utility` becomes fully transitive for
confidentiality `noflow` specifically, closing the vacuous-discharge gap;
it keeps its original T-0226 terminal-edge behavior for the existential
`reach`/`independent`/`readers`/krb-movement closures, which never relied
on it defeating a genuine downstream edge the way `noflow` did.

Counterexample-first:
- `tests/unit/strata/test_claims.py::TestNoFlow.
  test_real_leak_through_a_utility_hub_still_refutes` is the ticket's own
  repro, verbatim, at the claim-evaluation level: before this fix, PROVED
  (vacuous); after, REFUTED with the full two-hop witness path.
- `tests/unit/strata/test_claims.py::TestNoFlow.
  test_utility_hub_with_no_further_edges_still_discharges` proves the fix
  is not a blanket weakening: an innocuous hub with nothing further
  downstream still lets `noflow` prove clean, the original T-0226 case.
- `tests/unit/strata/test_facts.py::TestClosure.
  test_utility_attr_does_not_stop_chaining_for_confidentiality_noflow` /
  `test_krb_no_transit_still_terminal_for_confidentiality_noflow` /
  `test_utility_attr_stops_chaining_past_that_hop` cover the same litmus at
  the `reachable()` unit level, for both attrs and both `through_barriers`
  modes.

T-0226's own end-to-end litmus pair (`tests/unit/strata/litmus/
utility_hub_hardened.strata` + `test_litmus_utility_hub.py`) turned out to
BE the exact G5 vulnerability shape: its "hardened" fixture's `f_logs_
server` edge is a real, fully-transitive path landing exactly on the
`noflow` claim's own target (`server`), not an unrelated hub detour --
T-0226's premise that marking the FIRST hop `utility` alone could safely
discharge that claim was unsound from the start. Corrected the fixture to
discharge via a REAL `ENDORSE` boundary on `f_logs_server` instead (the
same mechanism `managed_hardened.strata` and `test_claims.py`'s own
boundary-cuts-the-path test already use) -- the `utility` marker is still
present on `f_tui_logs` but is now inert for this claim, which the test's
updated docstring says explicitly. The "vuln" twin (`utility_hub_vuln.
strata`) needed no behavior change (never marks `utility`) and got a
one-line note only. Test method names were kept IDENTICAL to their
pre-fix names (not renamed to something more "accurate") specifically so
`T-0226`'s own archived ticket evidence (`tickets-archive.md`, append-only)
does not dangle -- confirmed via `frob check --ticket T-0496`: renaming
first tripped 2 new COV003s citing T-0226's evidence, reverted before
finishing.

Registry/REG gates: `frob check --ticket T-0496` surfaces 16 pre-existing
REG003 errors on `docs/design/registry/weaknesses.yaml`'s `SEC-CVE-
FINGERPRINT-*` entries (`deferred:T-0439`, now a closed ticket) -- these
predate this ticket entirely (present on `main`, not touched by this
change; confirmed via `git diff main -- docs/design/registry/
weaknesses.yaml` showing zero diff) and are a genuine oversight from
closing T-0439 earlier this session (that file was already in T-0439's
OWN declared scope, and its dispositions should have been reconciled to
`handled_by:SEC-CVE-FINGERPRINT-001` then). Not Filed T-draft-92456503 (never refiled) for
the careful per-entry reconciliation (not a blind sweep -- 9 of the 16
entries map 1:1 to the shipped catalog, 7 do not) rather than folding it
into this unrelated ticket.

Verification:
- `uv run pytest tests/unit/strata -q`: all green except `test_export_
  golden.py::TestExportGolden::test_seccomp`, confirmed pre-existing
  (unrelated golden-drift failure, reproduces identically with this
  ticket's changes checked out to their pre-change state via the same
  checkout+patch-file method T-0503/T-0439 used, never `git stash`).
- `uv run pytest tests/unit/strata/test_selfconform.py::TestRealGateGreen
  -q`: green (1 passed) -- confirmed `utility` is never actually used in
  `design/frob.strata` itself (only mentioned in a prose comment), so this
  fix has zero effect on the repo's own self-audit.
- `uv run ruff check` / `uv run ruff format --check` on every touched
  file: clean.
- `uv run frob check --ticket T-0496`: 0 NEW errors from this ticket's
  change. Remaining errors are all confirmed pre-existing/out of scope:
  6x COV003 (T-0421/T-0470/T-0483 evidence referencing non-existent
  `tests/test_gates.py` node ids, same known ledger-reconstruction gap
  noted in T-0439's Done report), 16x REG003 (T-0439's registry gap, not filed
  as T-draft-6ec0fb9f (never refiled) above), 1x DOC003 (pre-existing THREAT003 CWE-78 gap
  on the `gates` design node, unrelated to compliance/facts), and SCOPE001
  noise from T-0503/T-0439's own already-closed, already-verified files
  (an artifact of doing three tickets sequentially in one un-merged
  worktree branch, not a new violation).

Filed: T-draft-92456503 (never refiled) (weaknesses.yaml SEC-CVE-FINGERPRINT-*
reconciliation, out-of-scope discovery from closing T-0439 earlier this
session).

### Changed
```
 .frob-release.json                                 |    6 +-
 CHANGELOG.md                                       |   40 +
 pyproject.toml                                     |    2 +-
 src/frob/gates/__init__.py                         |   10 +
 src/frob/gates/_cve_fingerprint_scan.py            |  177 ++++
 src/frob/strata/_audit.py                          |   19 +-
 src/frob/strata/_compliance.py                     |   34 +
 src/frob/strata/_cve_fingerprint.py                |   78 ++
 src/frob/strata/_facts.py                          |   84 +-
 .../unit/strata/litmus/utility_hub_hardened.strata |   30 +-
 tests/unit/strata/litmus/utility_hub_vuln.strata   |    6 +-
 tests/unit/strata/test_audit.py                    |   67 +-
 tests/unit/strata/test_claims.py                   |   44 +
 tests/unit/strata/test_cve_fingerprint_scan.py     |  148 +++
 tests/unit/strata/test_facts.py                    |   48 +-
 tests/unit/strata/test_litmus_audit_hardened.py    |    8 +-
 tests/unit/strata/test_litmus_utility_hub.py       |   27 +-
 tickets.md                                         | 1003 +++++++++++++++++++-
 uv.lock                                            |    2 +-
 19 files changed, 1750 insertions(+), 83 deletions(-)
```

### Evidence
- `tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_does_not_stop_chaining_for_confidentiality_noflow` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_facts.py::TestClosure::test_krb_no_transit_still_terminal_for_confidentiality_noflow` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_stops_chaining_past_that_hop` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_claims.py::TestNoFlow::test_real_leak_through_a_utility_hub_still_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_claims.py::TestNoFlow::test_utility_hub_with_no_further_edges_still_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_litmus_utility_hub.py::TestUtilityHubHardenedLitmus::test_marked_utility_hub_edge_lets_the_noflow_claim_prove` (pytest node id, verified passing when recorded)
